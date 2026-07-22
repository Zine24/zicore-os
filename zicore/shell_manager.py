"""
ZICORE Shell Manager — Interactive SSH Terminal Sessions
Generic SSH client: accepts connection params from user, no stored credentials.
Signed by ZineMotion. CC BY-NC-SA 4.0
"""
from __future__ import annotations
import time
import uuid
import threading
import logging
from typing import Optional

try:
    import paramiko
except ImportError:
    paramiko = None

logger = logging.getLogger("zicore.shell")

SESSION_TIMEOUT = 600
READ_BUFFER = 4096
READ_INTERVAL = 0.02


class ShellSession:
    """An interactive SSH shell session via paramiko PTY."""

    def __init__(self, host: str, port: int, user: str, password: str,
                 session_id: str = None):
        if paramiko is None:
            raise ImportError("paramiko not installed")

        self.host = host
        self.port = port
        self.user = user
        self.session_id = session_id or f"shell-{uuid.uuid4().hex[:12]}"
        self.client: Optional[paramiko.SSHClient] = None
        self.channel: Optional[paramiko.Channel] = None
        self.last_activity = time.time()
        self.connected = False
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._output_callback = None
        self._loop = None
        self._password = password

    def connect(self, cols: int = 120, rows: int = 40) -> dict:
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                self.host,
                port=self.port,
                username=self.user,
                password=self._password,
                timeout=10,
                allow_agent=False,
                look_for_keys=False,
            )
            self.channel = self.client.invoke_shell(
                term="xterm-256color", width=cols, height=rows,
            )
            self.channel.settimeout(0.0)
            self.connected = True
            self.last_activity = time.time()

            self._stop_event.clear()
            self._reader_thread = threading.Thread(
                target=self._reader_loop, daemon=True,
                name=f"shell-reader-{self.session_id}",
            )
            self._reader_thread.start()

            logger.info(f"Shell connected: {self.session_id} -> {self.user}@{self.host}:{self.port}")
            return {"success": True, "session_id": self.session_id}
        except Exception as e:
            logger.error(f"Shell connect failed: {e}")
            self.connected = False
            return {"success": False, "error": str(e)}

    def send_input(self, data: str):
        if not self.connected or not self.channel:
            return
        try:
            self.channel.send(data)
            self.last_activity = time.time()
        except Exception:
            self.disconnect()

    def resize(self, cols: int, rows: int):
        if not self.connected or not self.channel:
            return
        try:
            self.channel.resize_pty(width=cols, height=rows)
        except Exception:
            pass

    def disconnect(self):
        self._stop_event.set()
        self.connected = False
        try:
            if self.channel:
                self.channel.close()
        except Exception:
            pass
        try:
            if self.client:
                self.client.close()
        except Exception:
            pass
        logger.info(f"Shell disconnected: {self.session_id}")

    def is_idle(self) -> bool:
        return (time.time() - self.last_activity) > SESSION_TIMEOUT

    def get_info(self) -> dict:
        return {
            "session_id": self.session_id,
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "connected": self.connected,
            "idle_seconds": int(time.time() - self.last_activity),
            "timeout": SESSION_TIMEOUT,
        }

    def _reader_loop(self):
        while not self._stop_event.is_set():
            try:
                if self.channel and self.channel.recv_ready():
                    data = self.channel.recv(READ_BUFFER).decode("utf-8", errors="replace")
                    if data and self._output_callback:
                        self.last_activity = time.time()
                        try:
                            import asyncio
                            if self._loop and self._loop.is_running():
                                asyncio.run_coroutine_threadsafe(
                                    self._output_callback(self.session_id, data), self._loop
                                )
                        except Exception:
                            pass
                elif self.channel and self.channel.closed:
                    self.connected = False
                    if self._output_callback and self._loop:
                        try:
                            import asyncio
                            asyncio.run_coroutine_threadsafe(
                                self._output_callback(self.session_id, None), self._loop
                            )
                        except Exception:
                            pass
                    break
                else:
                    time.sleep(READ_INTERVAL)
            except Exception:
                time.sleep(READ_INTERVAL)
                continue


class ShellManager:
    """Manages all active shell sessions."""

    def __init__(self):
        self._sessions: dict[str, ShellSession] = {}
        self._lock = threading.Lock()

    def create_session(self, host: str, port: int, user: str, password: str,
                       cols: int = 120, rows: int = 40,
                       output_callback=None, loop=None) -> dict:
        session = ShellSession(host, port, user, password)
        session._output_callback = output_callback
        session._loop = loop
        result = session.connect(cols=cols, rows=rows)
        if result["success"]:
            with self._lock:
                self._sessions[session.session_id] = session
        return result

    def get_session(self, session_id: str) -> Optional[ShellSession]:
        return self._sessions.get(session_id)

    def close_session(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session:
            session.disconnect()
            return True
        return False

    def close_all(self):
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for s in sessions:
            s.disconnect()

    def list_sessions(self) -> list:
        return [s.get_info() for s in self._sessions.values()]

    def cleanup_idle(self) -> int:
        closed = 0
        idle_ids = []
        with self._lock:
            for sid, session in self._sessions.items():
                if session.is_idle():
                    idle_ids.append(sid)
        for sid in idle_ids:
            self.close_session(sid)
            closed += 1
        return closed


shell_manager = ShellManager()

"""
ZICORE Shell Manager — Interactive SSH Terminal Sessions
Provides paramiko-based PTY shell sessions for the web terminal.
Signed by ZineMotion. CC BY-NC-SA 4.0
"""
from __future__ import annotations
import os
import sys
import time
import uuid
import select
import threading
import logging
from typing import Optional

try:
    import paramiko
except ImportError:
    paramiko = None

logger = logging.getLogger("zicore.shell")

# Server credentials — same as ADMIN_SERVERS in web_server.py
SHELL_SERVERS = {
    ".85": {
        "name": ".85 Primary",
        "ip": "192.168.1.85",
        "port": 22,
        "user": "z",
        "password": "Jilo1981",
        "role": "Web Server + Materializer",
        "color": "#00ff88",
    },
    ".68": {
        "name": ".68 Ollama",
        "ip": "192.168.1.68",
        "port": 22,
        "user": "zinemotion",
        "password": "Jilo1981",
        "role": "Ollama Server + Zichat",
        "color": "#7c4dff",
    },
    "vps": {
        "name": "VPS Oracle",
        "ip": "160.34.209.208",
        "port": 22,
        "user": "oracle-admin",
        "password": "zicore2026",
        "role": "ARM64 + Ollama",
        "color": "#00e5ff",
    },
}

# Session config
SESSION_TIMEOUT = 600       # 10 min idle timeout
READ_BUFFER = 4096         # bytes per read
READ_INTERVAL = 0.02       # seconds between reads
PING_INTERVAL = 30         # keepalive ping seconds


class ShellSession:
    """An interactive SSH shell session via paramiko PTY."""

    def __init__(self, server_key: str, session_id: str = None):
        if paramiko is None:
            raise ImportError("paramiko not installed — pip install paramiko")
        if server_key not in SHELL_SERVERS:
            raise ValueError(f"Unknown server: {server_key}")

        self.server_key = server_key
        self.server = SHELL_SERVERS[server_key]
        self.session_id = session_id or f"shell-{uuid.uuid4().hex[:12]}"
        self.client: Optional[paramiko.SSHClient] = None
        self.channel: Optional[paramiko.Channel] = None
        self.last_activity = time.time()
        self.connected = False
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._output_callback = None  # async callback for output
        self._loop = None  # asyncio event loop reference

    def connect(self, cols: int = 120, rows: int = 40) -> dict:
        """Establish SSH connection and open PTY."""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                self.server["ip"],
                port=self.server["port"],
                username=self.server["user"],
                password=self.server["password"],
                timeout=10,
                allow_agent=False,
                look_for_keys=False,
            )
            self.channel = self.client.invoke_shell(
                term="xterm-256color",
                width=cols,
                height=rows,
            )
            self.channel.settimeout(0.0)
            self.connected = True
            self.last_activity = time.time()

            # Start reader thread
            self._stop_event.clear()
            self._reader_thread = threading.Thread(
                target=self._reader_loop, daemon=True, name=f"shell-reader-{self.session_id}"
            )
            self._reader_thread.start()

            logger.info(f"Shell connected: {self.session_id} → {self.server_key} ({self.server['ip']})")
            return {"success": True, "session_id": self.session_id, "server": self.server_key}
        except Exception as e:
            logger.error(f"Shell connect failed: {e}")
            self.connected = False
            return {"success": False, "error": str(e), "session_id": self.session_id}

    def send_input(self, data: str):
        """Send keyboard input to the PTY."""
        if not self.connected or not self.channel:
            return
        try:
            self.channel.send(data)
            self.last_activity = time.time()
        except Exception:
            self.disconnect()

    def resize(self, cols: int, rows: int):
        """Resize the PTY."""
        if not self.connected or not self.channel:
            return
        try:
            self.channel.resize_pty(width=cols, height=rows)
        except Exception:
            pass

    def disconnect(self):
        """Close the session cleanly."""
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
        """Check if session has exceeded idle timeout."""
        return (time.time() - self.last_activity) > SESSION_TIMEOUT

    def get_info(self) -> dict:
        """Return session metadata."""
        return {
            "session_id": self.session_id,
            "server_key": self.server_key,
            "server_name": self.server["name"],
            "ip": self.server["ip"],
            "user": self.server["user"],
            "connected": self.connected,
            "idle_seconds": int(time.time() - self.last_activity),
            "timeout": SESSION_TIMEOUT,
        }

    def _reader_loop(self):
        """Background thread: read from SSH channel, send to WebSocket."""
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

    def create_session(self, server_key: str, cols: int = 120, rows: int = 40,
                       output_callback=None, loop=None) -> dict:
        """Create and connect a new shell session."""
        session = ShellSession(server_key)
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
        """Close sessions that exceeded idle timeout. Returns count closed."""
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


# Global instance
shell_manager = ShellManager()

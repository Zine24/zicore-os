"""ZIO CommandBus — unified system command registry for ZICORE.

Lets ZIO (and any module) execute registered system actions safely:
  - Register commands with metadata + permission level
  - Execute with strict allowlisting (no arbitrary shell)
  - Parse [COMMAND:name] tokens emitted by the LLM (autonomous mode)
  - Log every execution for audit

Commands are registered by the web server at startup (see web_server.py,
_commandbus registration block). This module only defines the framework.
"""
import asyncio
import inspect
import json
import re
import threading
import time
import logging
from typing import Callable, Any, Dict, List, Optional

logger = logging.getLogger("zicore.commandbus")

# Permission levels
PERM_READ = "read"
PERM_ACTION = "action"
PERM_SYSTEM = "system"


class SystemCommandBus:
    """Thread-safe registry of executable system commands for ZIO."""

    def __init__(self):
        self._commands: Dict[str, Dict[str, Any]] = {}
        self._log: List[Dict[str, Any]] = []
        self._log_max = 200

    # ── Registration ──────────────────────────────────────────────────────
    def register(self, name: str, handler: Callable, description: str = "",
                 params: Optional[Dict] = None, permission: str = PERM_READ,
                 category: str = "system"):
        """Register a command. handler(**params) -> dict result."""
        self._commands[name] = {
            "name": name,
            "handler": handler,
            "description": description,
            "params": params or {},
            "permission": permission,
            "category": category,
        }
        logger.info(f"Command registered: {name} [{permission}]")

    def unregister(self, name: str):
        self._commands.pop(name, None)

    # ── Query ─────────────────────────────────────────────────────────────
    def list(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": c["name"],
                "description": c["description"],
                "params": list(c["params"].keys()),
                "permission": c["permission"],
                "category": c["category"],
            }
            for c in sorted(self._commands.values(), key=lambda x: (x["category"], x["name"]))
        ]

    def exists(self, name: str) -> bool:
        return name in self._commands

    def describe(self, name: str) -> Optional[Dict[str, Any]]:
        c = self._commands.get(name)
        if not c:
            return None
        return {k: c[k] for k in ("name", "description", "params", "permission", "category")}

    # ── Execution ─────────────────────────────────────────────────────────
    def execute(self, name: str, permission: str = PERM_READ, **kwargs) -> Dict[str, Any]:
        """Execute a registered command with allowlisting (sync wrapper).

        Handles both sync handlers and coroutine-returning handlers:
        outside a running event loop the coroutine is run via asyncio.run;
        inside a running loop it is run in a dedicated worker thread.
        """
        cmd = self._commands.get(name)
        if cmd is None:
            return {"ok": False, "command": name, "error": f"unknown command: {name}"}
        if permission not in (PERM_READ, PERM_ACTION, PERM_SYSTEM):
            return {"ok": False, "command": name, "error": f"invalid permission: {permission}"}
        if _perm_level(cmd["permission"]) > _perm_level(permission):
            return {"ok": False, "command": name, "error": f"permission denied: {name} requires {cmd['permission']}"}

        started = time.time()
        try:
            result = cmd["handler"](**kwargs)
            if inspect.iscoroutine(result):
                result = _run_coro(result)
        except Exception as e:
            logger.error(f"Command '{name}' error: {e}", exc_info=True)
            self._log_command(name, kwargs, {"ok": False, "error": str(e)}, started)
            return {"ok": False, "command": name, "error": str(e)}
        elapsed = round((time.time() - started) * 1000, 1)
        self._log_command(name, kwargs, {"ok": True, "result": result}, started)
        return {"ok": True, "command": name, "elapsed_ms": elapsed, "result": result}

    async def async_execute(self, name: str, permission: str = PERM_READ, **kwargs) -> Dict[str, Any]:
        """Async execution path: awaits coroutine-returning handlers in-place.

        Preferred when called from an async context (FastAPI handlers) so the
        coroutine runs on the current event loop without extra threads.
        """
        cmd = self._commands.get(name)
        if cmd is None:
            return {"ok": False, "command": name, "error": f"unknown command: {name}"}
        if permission not in (PERM_READ, PERM_ACTION, PERM_SYSTEM):
            return {"ok": False, "command": name, "error": f"invalid permission: {permission}"}
        if _perm_level(cmd["permission"]) > _perm_level(permission):
            return {"ok": False, "command": name, "error": f"permission denied: {name} requires {cmd['permission']}"}

        started = time.time()
        try:
            result = cmd["handler"](**kwargs)
            if inspect.iscoroutine(result):
                result = await result
        except Exception as e:
            logger.error(f"Command '{name}' error: {e}", exc_info=True)
            self._log_command(name, kwargs, {"ok": False, "error": str(e)}, started)
            return {"ok": False, "command": name, "error": str(e)}
        elapsed = round((time.time() - started) * 1000, 1)
        self._log_command(name, kwargs, {"ok": True, "result": result}, started)
        return {"ok": True, "command": name, "elapsed_ms": elapsed, "result": result}

    def _log_command(self, name: str, kwargs: Dict, outcome: Dict, started: float):
        safe_kwargs = {}
        for k, v in (kwargs or {}).items():
            safe_kwargs[k] = str(v)[:200] if isinstance(v, (str, int, float)) else json.dumps(v)[:200] if not isinstance(v, (str, int, float)) else v
        self._log.append({
            "command": name,
            "params": safe_kwargs,
            "ok": outcome.get("ok", False),
            "error": outcome.get("error"),
            "ts": started,
        })
        if len(self._log) > self._log_max:
            self._log = self._log[-self._log_max:]

    def history(self, limit: int = 20) -> List[Dict[str, Any]]:
        return list(reversed(self._log[-limit:]))

    def clear_history(self):
        self._log.clear()

    # ── [COMMAND:...] token parsing (autonomous mode) ─────────────────────
    COMMAND_RE = re.compile(r"\[COMMAND:(\w[\w-]*)(?:\|([^\]]*))?\]")

    def parse_tokens(self, text: str) -> List[Dict[str, str]]:
        """Extract [COMMAND:name] / [COMMAND:name|k=v,k2=v2] tokens from LLM output."""
        tokens = []
        if not text:
            return tokens
        for m in self.COMMAND_RE.finditer(text):
            name = m.group(1)
            params_raw = m.group(2)
            params = {}
            if params_raw:
                for part in params_raw.split(","):
                    part = part.strip()
                    if "=" in part:
                        k, v = part.split("=", 1)
                        params[k.strip()] = v.strip()
                    elif part:
                        params[part] = ""
            tokens.append({"command": name, "params": params})
        return tokens

    def run_tokens(self, text: str, permission: str = PERM_READ) -> List[Dict[str, Any]]:
        """Parse and execute all [COMMAND:...] tokens found in text. Returns results."""
        results = []
        for tok in self.parse_tokens(text):
            results.append(self.execute(tok["command"], permission=permission, **tok["params"]))
        return results

    async def async_run_tokens(self, text: str, permission: str = PERM_READ) -> List[Dict[str, Any]]:
        """Async variant of run_tokens for use inside event-loop contexts."""
        results = []
        for tok in self.parse_tokens(text):
            results.append(await self.async_execute(tok["command"], permission=permission, **tok["params"]))
        return results


def _perm_level(p: str) -> int:
    return {PERM_READ: 1, PERM_ACTION: 2, PERM_SYSTEM: 3}.get(p, 0)


def _run_coro(coro):
    """Run a coroutine to completion regardless of surrounding event loop.

    - Outside a running loop: use asyncio.run.
    - Inside a running loop (e.g. FastAPI handler calling a sync bus.execute):
      run it in a dedicated thread so it never blocks/conflicts with the loop.
    """
    try:
        asyncio.get_running_loop()
        in_loop = True
    except RuntimeError:
        in_loop = False
    if not in_loop:
        return asyncio.run(coro)
    box = {}

    def _runner():
        try:
            box["result"] = asyncio.run(coro)
        except Exception as e:  # noqa: BLE001
            box["error"] = e

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join()
    if "error" in box:
        raise box["error"]
    return box["result"]


# Shared singleton bus (populated by the web server at startup)
bus = SystemCommandBus()

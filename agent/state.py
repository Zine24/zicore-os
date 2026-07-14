"""
ZIO Agent State Manager - Session persistence, context memory, tool registry
"""
import time
import json
import logging
import hashlib
import os
import shlex
import subprocess
from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger("zicore.agent.state")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = PROJECT_ROOT / "data" / "agent_state"
STATE_DIR.mkdir(parents=True, exist_ok=True)

DENIED_PATH_PARTS = {
    ".git", ".agents", ".codex", ".pytest_cache", "__pycache__",
    "node_modules", ".venv", "venv", "env", "dist", "build",
}
MAX_READ_BYTES = 1_000_000
MAX_WRITE_BYTES = 500_000


def _workspace_path(path: str = ".") -> Path:
    raw = Path(path or ".")
    p = raw if raw.is_absolute() else PROJECT_ROOT / raw
    resolved = p.resolve()
    if resolved != PROJECT_ROOT and PROJECT_ROOT not in resolved.parents:
        raise ValueError("Path outside zicore-system workspace is not allowed")
    parts = {part.lower() for part in resolved.relative_to(PROJECT_ROOT).parts}
    if parts & DENIED_PATH_PARTS:
        raise ValueError("Path is inside a protected workspace directory")
    return resolved


class ToolRegistry:
    """Registry of callable tools the agent can use."""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, fn: Callable, description: str = "", params: dict = None):
        self._tools[name] = {
            "fn": fn,
            "description": description,
            "params": params or {},
        }
        logger.info(f"Tool registered: {name}")

    def call(self, name: str, **kwargs) -> Any:
        tool = self._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        return tool["fn"](**kwargs)

    def list_tools(self) -> List[Dict[str, str]]:
        return [
            {"name": k, "description": v["description"], "params": list(v["params"].keys())}
            for k, v in self._tools.items()
        ]

    def exists(self, name: str) -> bool:
        return name in self._tools


class ContextMemory:
    """Short-term + long-term context memory for conversations."""

    def __init__(self, max_short: int = 50, max_long: int = 500):
        self.short_term: List[Dict[str, Any]] = []
        self.long_term: List[Dict[str, Any]] = []
        self.max_short = max_short
        self.max_long = max_long
        self.entity_memory: Dict[str, Any] = {}
        self.summary: str = ""

    def add(self, role: str, content: Any, metadata: dict = None):
        entry = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }
        self.short_term.append(entry)
        if len(self.short_term) > self.max_short:
            overflow = self.short_term[:self.max_short // 2]
            self.short_term = self.short_term[self.max_short // 2:]
            self.long_term.extend(overflow)
            if len(self.long_term) > self.max_long:
                self.long_term = self.long_term[-self.max_long:]

    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        return self.short_term[-n:]

    def get_context_window(self) -> str:
        lines = []
        for entry in self.short_term[-20:]:
            role = entry["role"].upper()
            content = entry["content"]
            if isinstance(content, dict):
                content = json.dumps(content)[:200]
            elif isinstance(content, list):
                content = str(content)[:200]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def remember_entity(self, key: str, value: Any):
        self.entity_memory[key] = value

    def recall_entity(self, key: str) -> Optional[Any]:
        return self.entity_memory.get(key)

    def summarize(self) -> str:
        if not self.short_term:
            return "No conversation history."
        topics = set()
        for entry in self.short_term:
            content = str(entry.get("content", ""))
            for word in content.split():
                if len(word) > 4:
                    topics.add(word.lower())
        self.summary = f"Topics discussed: {', '.join(list(topics)[:10])}"
        return self.summary

    def clear(self):
        self.short_term.clear()
        self.long_term.clear()
        self.entity_memory.clear()
        self.summary = ""


class AgentSession:
    """Complete agent session with state, memory, and tools."""

    def __init__(self, session_id: str):
        self.id = session_id
        self.created = time.time()
        self.last_active = time.time()
        self.memory = ContextMemory()
        self.tools = ToolRegistry()
        self.state: Dict[str, Any] = {
            "mode": "auto",
            "current_module": None,
            "active_task": None,
            "preferences": {},
        }
        self._register_default_tools()

    def _register_default_tools(self):
        self.tools.register("infer", self._tool_infer, "Run dual-engine inference", {"module": str, "instruction": str})
        self.tools.register("trajectory", self._tool_trajectory, "Calculate trajectory", {"type": str})
        self.tools.register("status", self._tool_status, "Get system status", {})
        self.tools.register("hierarchy", self._tool_hierarchy, "Get module hierarchy", {})
        self.tools.register("web_search", self._tool_web_search, "Search the web", {"query": str})
        self.tools.register("read_file", self._tool_read_file, "Read a file", {"path": str})
        self.tools.register("write_file", self._tool_write_file, "Write a file", {"path": str, "content": str})
        self.tools.register("list_files", self._tool_list_files, "List files in directory", {"path": str})
        self.tools.register("run_command", self._tool_run_command, "Run an allowlisted workspace command", {"command": str})
        self.tools.register("calculate", self._tool_calculator, "Evaluate math expression", {"expression": str})
        self.tools.register("timestamp", self._tool_timestamp, "Get current timestamp", {})
        self.tools.register("random", self._tool_random, "Generate random number", {"min": float, "max": float})
        self.tools.register("generate_image", self._tool_generate_image, "Generate image through ZIO", {"prompt": str})
        self.tools.register("generate_sound", self._tool_generate_sound, "Generate sound through ZIO", {"prompt": str})
        self.tools.register("generate_video", self._tool_generate_video, "Generate video through ZIO", {"prompt": str})
        self.tools.register("generate_3d", self._tool_generate_3d, "Generate 3D mesh through ZIO", {"prompt": str})

    def _tool_infer(self, module: str = "zinav", instruction: str = "status", **kw):
        return {"module": module, "instruction": instruction, "status": "queued"}

    def _tool_trajectory(self, type: str = "hohmann", **kw):
        return {"type": type, "status": "queued"}

    def _tool_status(self, **kw):
        return {"status": "online", "session": self.id}

    def _tool_hierarchy(self, **kw):
        return {"hierarchy": "ZiNav > ZiAXIS > GPD"}

    def _tool_web_search(self, query: str = "", **kw):
        """Search the web using a simple API."""
        try:
            import httpx
            # Use a simple search API (DuckDuckGo instant answers)
            url = f"https://api.duckduckgo.com/?q={query}&format=json"
            r = httpx.get(url, timeout=10)
            data = r.json()
            results = []
            if data.get("Abstract"):
                results.append({"title": "Abstract", "text": data["Abstract"]})
            for topic in data.get("RelatedTopics", [])[:5]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append({"title": topic.get("Text", "")[:50], "text": topic.get("Text", "")})
            return {"query": query, "results": results, "source": "duckduckgo"}
        except Exception as e:
            return {"query": query, "error": str(e), "results": []}

    def _tool_read_file(self, path: str = "", **kw):
        """Read file contents."""
        try:
            p = _workspace_path(path)
            if not p.exists():
                return {"error": f"File not found: {path}"}
            if not p.is_file():
                return {"error": "Path is not a file"}
            if p.stat().st_size > MAX_READ_BYTES:
                return {"error": f"File too large (>{MAX_READ_BYTES} bytes)"}
            content = p.read_text(encoding="utf-8", errors="replace")
            return {"path": str(p.relative_to(PROJECT_ROOT)), "content": content[:10000], "size": p.stat().st_size}
        except Exception as e:
            return {"error": str(e)}

    def _tool_write_file(self, path: str = "", content: str = "", **kw):
        """Write content to a file."""
        try:
            if len(content.encode("utf-8")) > MAX_WRITE_BYTES:
                return {"error": f"Content too large (>{MAX_WRITE_BYTES} bytes)"}
            p = _workspace_path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"path": str(p.relative_to(PROJECT_ROOT)), "size": len(content), "status": "written"}
        except Exception as e:
            return {"error": str(e)}

    def _tool_list_files(self, path: str = ".", **kw):
        """List files in a directory."""
        try:
            p = _workspace_path(path)
            if not p.exists():
                return {"error": f"Directory not found: {path}"}
            if not p.is_dir():
                return {"error": "Path is not a directory"}
            entries = []
            for item in sorted(p.iterdir())[:50]:
                entries.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0,
                })
            return {"path": str(p.relative_to(PROJECT_ROOT)), "entries": entries, "count": len(entries)}
        except Exception as e:
            return {"error": str(e)}

    def _tool_run_command(self, command: str = "", **kw):
        """Run a small allowlist of non-destructive workspace commands."""
        try:
            args = shlex.split(command, posix=(os.name != "nt"))
            if not args:
                return {"error": "Empty command"}
            allowed = (
                args[:2] == ["python", "-m"] and len(args) >= 3 and args[2] in {"pytest", "compileall"}
            ) or args[0] in {"pytest", "rg"} or (
                args[0] == "git" and len(args) > 1 and args[1] in {"status", "diff", "log", "show"}
            ) or (
                args[:2] == ["npm", "run"] and len(args) > 2 and args[2] in {"build", "test"}
            )
            if not allowed:
                return {"error": "Command not allowed for ZIO tool execution", "allowed": [
                    "python -m pytest", "python -m compileall", "pytest", "rg",
                    "git status/diff/log/show", "npm run build/test",
                ]}
            result = subprocess.run(
                args, shell=False, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=30
            )
            return {
                "command": command,
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:2000],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out (30s)"}
        except Exception as e:
            return {"error": str(e)}

    def _tool_generate_image(self, prompt: str = "", **kw):
        try:
            from agent.generator import generator
            return generator.generate_image(prompt or "zicore system")
        except Exception as e:
            return {"error": str(e)}

    def _tool_generate_sound(self, prompt: str = "", **kw):
        try:
            from agent.generator import generator
            return generator.generate_sound(prompt or "zicore tone")
        except Exception as e:
            return {"error": str(e)}

    def _tool_generate_video(self, prompt: str = "", **kw):
        try:
            from agent.generator import generator
            return generator.generate_video(prompt or "zicore sequence")
        except Exception as e:
            return {"error": str(e)}

    def _tool_generate_3d(self, prompt: str = "", **kw):
        try:
            from agent.generator import generator
            return generator.generate_3d(prompt or "zicore model")
        except Exception as e:
            return {"error": str(e)}

    def _tool_calculator(self, expression: str = "", **kw):
        """Evaluate a math expression safely."""
        import math
        allowed_names = {
            "abs": abs, "round": round, "min": min, "max": max,
            "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
            "tan": math.tan, "pi": math.pi, "e": math.e,
            "log": math.log, "log10": math.log10, "pow": pow,
            "radians": math.radians, "degrees": math.degrees,
        }
        try:
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return {"expression": expression, "result": result}
        except Exception as e:
            return {"expression": expression, "error": str(e)}

    def _tool_timestamp(self, **kw):
        """Get current timestamp."""
        import datetime
        now = datetime.datetime.now()
        return {
            "timestamp": time.time(),
            "iso": now.isoformat(),
            "utc": now.utcnow().isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
        }

    def _tool_random(self, min_val: float = 0, max_val: float = 100, **kw):
        """Generate a random number."""
        import random
        result = random.uniform(min_val, max_val)
        return {"min": min_val, "max": max_val, "result": round(result, 4)}

    def touch(self):
        self.last_active = time.time()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created": self.created,
            "last_active": self.last_active,
            "state": self.state,
            "memory_size": len(self.memory.short_term),
            "tools": [t["name"] for t in self.tools.list_tools()],
        }


class AgentStateManager:
    """Global state manager for all agent sessions."""

    def __init__(self):
        self.sessions: Dict[str, AgentSession] = {}
        self.global_state: Dict[str, Any] = {
            "total_sessions": 0,
            "total_messages": 0,
            "started": time.time(),
        }

    def create_session(self, session_id: str = None) -> AgentSession:
        if session_id is None:
            session_id = f"session_{int(time.time())}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:6]}"
        session = AgentSession(session_id)
        self.sessions[session_id] = session
        self.global_state["total_sessions"] += 1
        logger.info(f"Session created: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        return self.sessions.get(session_id)

    def get_or_create(self, session_id: str) -> AgentSession:
        if session_id not in self.sessions:
            return self.create_session(session_id)
        self.sessions[session_id].touch()
        return self.sessions[session_id]

    def delete_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session deleted: {session_id}")

    def list_sessions(self) -> List[dict]:
        return [s.to_dict() for s in self.sessions.values()]

    def get_global_status(self) -> dict:
        return {
            "active_sessions": len(self.sessions),
            "total_sessions": self.global_state["total_sessions"],
            "total_messages": self.global_state["total_messages"],
            "uptime": time.time() - self.global_state["started"],
        }

    def cleanup_stale(self, max_age: float = 3600):
        now = time.time()
        stale = [sid for sid, s in self.sessions.items() if now - s.last_active > max_age]
        for sid in stale:
            self.delete_session(sid)
        if stale:
            logger.info(f"Cleaned {len(stale)} stale sessions")

    def save_session(self, session_id: str):
        session = self.sessions.get(session_id)
        if not session:
            return
        data = {
            "id": session.id,
            "created": session.created,
            "state": session.state,
            "history": session.memory.short_term[-50:],
            "entities": session.memory.entity_memory,
        }
        path = STATE_DIR / f"{session_id}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def load_session(self, session_id: str) -> Optional[AgentSession]:
        path = STATE_DIR / f"{session_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        session = AgentSession(session_id)
        session.created = data.get("created", time.time())
        session.state = data.get("state", {})
        for entry in data.get("history", []):
            session.memory.add(entry.get("role", "user"), entry.get("content", ""), entry.get("metadata", {}))
        session.memory.entity_memory = data.get("entities", {})
        self.sessions[session_id] = session
        return session


# Global instance
state_manager = AgentStateManager()

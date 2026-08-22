"""
ZIO Agent State Manager - Session persistence, context memory, tool registry
"""
import time
import json
import logging
import hashlib
import os
import re
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
        self._active_plans: Dict[str, List[Dict]] = {}
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
        self.tools.register("analyze_image", self._tool_analyze_image, "Analyze image with OpenVision", {"image_path": str})
        self.tools.register("capture_webcam", self._tool_capture_webcam, "Capture and analyze webcam frame", {"device_index": int})
        self.tools.register("web_fetch", self._tool_web_fetch, "Fetch and read content from a URL", {"url": str})
        self.tools.register("weather", self._tool_weather, "Get real-time weather for a city", {"city": str})
        self.tools.register("edit_file", self._tool_edit_file, "Edit file with targeted string replacement", {"path": str, "old_string": str, "new_string": str})
        self.tools.register("grep_code", self._tool_grep_code, "Search file contents with regex", {"pattern": str, "path": str, "include": str})
        self.tools.register("glob_files", self._tool_glob_files, "Find files matching a glob pattern", {"pattern": str, "path": str})
        self.tools.register("git_operation", self._tool_git_operation, "Run git commands (status/diff/commit/branch/log/checkout)", {"operation": str, "args": str})
        self.tools.register("plan_task", self._tool_plan_task, "Create or update a task plan with steps", {"action": str, "goal": str, "step": str, "step_num": int})
        # Document tools
        self.tools.register("ocr_image", self._tool_ocr_image, "Extract text from an image using Tesseract OCR", {"image_path": str, "lang": str})
        self.tools.register("read_pdf", self._tool_read_pdf, "Extract text and metadata from a PDF file", {"pdf_path": str, "pages": str})
        self.tools.register("read_document", self._tool_read_document, "Read any text/document file (txt, md, csv, json, code, etc.)", {"path": str, "max_chars": int})
        self.tools.register("analyze_document", self._tool_analyze_document, "Analyze any file: OCR images, read PDFs, extract text from documents", {"file_path": str, "instruction": str})
        # Memory & utility tools
        self.tools.register("store_memory", self._tool_store_memory, "Store a key-value pair in long-term memory", {"key": str, "value": str})
        self.tools.register("recall_memory", self._tool_recall_memory, "Recall a value from long-term memory by key", {"key": str})
        self.tools.register("conversation_summary", self._tool_conversation_summary, "Get a summary of recent conversation topics", {})
        self.tools.register("send_notification", self._tool_send_notification, "Send a push notification to the user", {"title": str, "body": str})
        self.tools.register("create_reminder", self._tool_create_reminder, "Create a timed reminder", {"message": str, "minutes": int})
        self.tools.register("set_alarm", self._tool_set_alarm, "Set an alarm for a specific time", {"time_str": str, "label": str})
        self.tools.register("system_command", self._tool_system_command, "Execute a registered ZICORE system command (status, diagnostics, list_volumes, list_drives, media_rescan, media_search, media_play, media_stop, generate_image/3d/sound, convert_model, backup)", {"name": str, "params": dict})

    def _tool_infer(self, module: str = "zinav", instruction: str = "status", **kw):
        return {"module": module, "instruction": instruction, "status": "queued"}

    def _tool_trajectory(self, type: str = "hohmann", **kw):
        return {"type": type, "status": "queued"}

    def _tool_status(self, **kw):
        return {"status": "online", "session": self.id}

    def _tool_system_command(self, name: str = "", params: dict = None, **kw):
        """Execute a registered ZICORE system command via the shared CommandBus."""
        if not name:
            try:
                from agent.commands import bus
                return {"commands": [c["name"] for c in bus.list()], "hint": "pass name=... to execute"}
            except Exception as e:
                return {"error": f"commandbus unavailable: {e}"}
        try:
            from agent.commands import bus
            permission = "action" if name in ("media_play", "media_stop", "generate_image", "generate_3d", "generate_sound", "convert_model", "media_rescan", "backup") else "read"
            result = bus.execute(name, permission=permission, **(params or {}))
            return result
        except Exception as e:
            return {"error": str(e)}

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

    def _tool_web_fetch(self, url: str = "", **kw):
        """Fetch content from a URL and return text."""
        try:
            import urllib.request
            import urllib.error
            import re as _re
            if not url or not url.startswith(("http://", "https://")):
                return {"error": "Invalid URL. Must start with http:// or https://"}
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (ZICORE/5.0; +https://zicore.space)",
                "Accept": "text/html,application/xhtml+xml,text/plain,application/json",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                content_type = resp.headers.get("Content-Type", "")
                raw = resp.read(500000)  # max 500KB
                if "json" in content_type:
                    import json as _json
                    data = _json.loads(raw)
                    text = _json.dumps(data, indent=2, ensure_ascii=False)[:10000]
                elif "text" in content_type or "html" in content_type:
                    text = raw.decode("utf-8", errors="replace")
                    # Strip HTML tags for readability
                    text = _re.sub(r'<script[^>]*>.*?</script>', '', text, flags=_re.DOTALL | _re.IGNORECASE)
                    text = _re.sub(r'<style[^>]*>.*?</style>', '', text, flags=_re.DOTALL | _re.IGNORECASE)
                    text = _re.sub(r'<[^>]+>', ' ', text)
                    text = _re.sub(r'\s+', ' ', text).strip()[:10000]
                else:
                    text = f"[Binary content: {content_type}, {len(raw)} bytes]"
            return {"url": url, "content_type": content_type, "text": text, "size": len(raw)}
        except urllib.error.HTTPError as e:
            return {"url": url, "error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"url": url, "error": str(e)}

    def _tool_weather(self, city: str = "auto", **kw):
        """Fetch real-time weather from wttr.in (free, no API key)."""
        try:
            import urllib.request, urllib.parse, json as _json
            url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
            req = urllib.request.Request(url, headers={"User-Agent": "ZICORE/5.0 Weather"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read().decode())
            cur = data.get("current_condition", [{}])[0]
            area = data.get("nearest_area", [{}])[0]
            loc = area.get("areaName", [{}])[0].get("value", city)
            country = area.get("country", [{}])[0].get("value", "")
            desc = cur.get("weatherDesc", [{}])[0].get("value", "Unknown")
            return {
                "location": f"{loc}, {country}",
                "description": desc,
                "temp_c": cur.get("temp_C", "?"),
                "temp_f": cur.get("temp_F", "?"),
                "feels_like_c": cur.get("FeelsLikeC", "?"),
                "humidity": cur.get("humidity", "?"),
                "wind_kph": cur.get("windspeedKmph", "?"),
                "wind_dir": cur.get("winddir16Point", ""),
                "uv_index": cur.get("uvIndex", "?"),
                "visibility_km": cur.get("visibility", "?"),
            }
        except Exception as e:
            return {"error": f"Weather fetch failed: {str(e)}"}

    def _tool_edit_file(self, path: str = "", old_string: str = "", new_string: str = "", **kw):
        """Edit a file by replacing old_string with new_string (targeted edit)."""
        try:
            p = _workspace_path(path)
            if not p.exists():
                return {"error": f"File not found: {path}"}
            if not p.is_file():
                return {"error": "Path is not a file"}
            content = p.read_text(encoding="utf-8", errors="replace")
            if old_string not in content:
                return {"error": f"old_string not found in {path}", "file_size": len(content)}
            count = content.count(old_string)
            if count > 1:
                return {"error": f"Found {count} matches for old_string. Provide more surrounding context to make it unique."}
            new_content = content.replace(old_string, new_string, 1)
            if len(new_content.encode("utf-8")) > MAX_WRITE_BYTES:
                return {"error": f"Result would be too large (>{MAX_WRITE_BYTES} bytes)"}
            p.write_text(new_content, encoding="utf-8")
            return {"path": str(p.relative_to(PROJECT_ROOT)), "status": "edited", "old_len": len(old_string), "new_len": len(new_string)}
        except Exception as e:
            return {"error": str(e)}

    def _tool_grep_code(self, pattern: str = "", path: str = ".", include: str = "", **kw):
        """Search file contents using regex pattern."""
        try:
            p = _workspace_path(path)
            if not p.exists():
                return {"error": f"Path not found: {path}"}
            matches = []
            regex = re.compile(pattern, re.IGNORECASE)
            search_files = []
            if p.is_file():
                search_files = [p]
            else:
                glob_pattern = f"**/*{include}" if include else "**/*"
                for f in p.glob(glob_pattern):
                    if f.is_file() and f.stat().st_size < MAX_READ_BYTES:
                        rel = str(f.relative_to(PROJECT_ROOT))
                        if not any(d in rel for d in DENIED_PATH_PARTS):
                            search_files.append(f)
            for f in search_files[:200]:
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                    for i, line in enumerate(text.splitlines(), 1):
                        if regex.search(line):
                            matches.append({
                                "file": str(f.relative_to(PROJECT_ROOT)),
                                "line": i,
                                "content": line.strip()[:200],
                            })
                            if len(matches) >= 100:
                                break
                except Exception:
                    continue
                if len(matches) >= 100:
                    break
            return {"pattern": pattern, "matches": matches[:100], "total": len(matches)}
        except Exception as e:
            return {"error": str(e)}

    def _tool_glob_files(self, pattern: str = "**/*", path: str = ".", **kw):
        """Find files matching a glob pattern."""
        try:
            p = _workspace_path(path)
            if not p.exists():
                return {"error": f"Path not found: {path}"}
            files = []
            for f in sorted(p.glob(pattern)):
                if f.is_file():
                    rel = str(f.relative_to(PROJECT_ROOT))
                    if not any(d in rel for d in DENIED_PATH_PARTS):
                        files.append({"path": rel, "size": f.stat().st_size})
                if len(files) >= 500:
                    break
            return {"pattern": pattern, "files": files, "count": len(files)}
        except Exception as e:
            return {"error": str(e)}

    def _tool_git_operation(self, operation: str = "status", args: str = "", **kw):
        """Run git operations: status, diff, log, commit, branch, checkout, stash."""
        allowed_ops = {"status", "diff", "log", "show", "branch", "checkout", "commit", "stash", "merge", "rebase"}
        if operation not in allowed_ops:
            return {"error": f"Git operation '{operation}' not allowed. Use: {', '.join(sorted(allowed_ops))}"}
        try:
            cmd = ["git", operation]
            if args:
                cmd.extend(shlex.split(args, posix=(os.name != "nt")))
            result = subprocess.run(cmd, shell=False, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=30)
            return {
                "operation": operation,
                "stdout": result.stdout[:5000],
                "stderr": result.stderr[:2000],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": "Git command timed out (30s)"}
        except Exception as e:
            return {"error": str(e)}

    def _tool_plan_task(self, action: str = "create", goal: str = "", step: str = "", step_num: int = 0, **kw):
        """Create, update, or list task plans. Actions: create, add_step, complete_step, list, get."""
        plan_id = f"plan_{hashlib.md5(goal.encode()).hexdigest()[:8]}" if goal else "default"
        if action == "create":
            if not goal:
                return {"error": "goal is required for create"}
            self._active_plans[plan_id] = [{"step": 1, "description": goal, "status": "pending"}]
            return {"plan_id": plan_id, "status": "created", "steps": self._active_plans[plan_id]}
        if action == "add_step":
            if plan_id not in self._active_plans:
                self._active_plans[plan_id] = []
            num = len(self._active_plans[plan_id]) + 1
            self._active_plans[plan_id].append({"step": num, "description": step or f"Step {num}", "status": "pending"})
            return {"plan_id": plan_id, "step": num, "status": "added"}
        if action == "complete_step":
            if plan_id in self._active_plans and 1 <= step_num <= len(self._active_plans[plan_id]):
                self._active_plans[plan_id][step_num - 1]["status"] = "done"
                return {"plan_id": plan_id, "step": step_num, "status": "completed"}
            return {"error": f"Step {step_num} not found in plan"}
        if action == "list":
            plans = {pid: {"steps": len(steps), "completed": sum(1 for s in steps if s["status"] == "done")} for pid, steps in self._active_plans.items()}
            return {"plans": plans}
        if action == "get":
            if plan_id in self._active_plans:
                return {"plan_id": plan_id, "steps": self._active_plans[plan_id]}
            return {"error": "Plan not found"}
        return {"error": f"Unknown action: {action}. Use: create, add_step, complete_step, list, get"}

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
            ) or args[0] in {"pytest", "rg", "ruff", "mypy", "flake8", "black", "isort", "pylint", "node", "npm", "npx"} or (
                args[0] == "git" and len(args) > 1 and args[1] in {"status", "diff", "log", "show", "branch", "checkout", "commit", "stash", "merge", "rebase", "add", "reset"}
            ) or (
                args[:2] == ["npm", "run"] and len(args) > 2 and args[2] in {"build", "test", "lint", "typecheck", "start"}
            ) or (
                args[:2] == ["npm", "install"] and len(args) > 2
            ) or (
                args[:2] == ["pip", "install"] and len(args) > 2
            ) or (
                args[0] == "ls" or args[0] == "pwd" or args[0] == "which" or args[0] == "echo"
            )
            if not allowed:
                return {"error": "Command not allowed for ZIO tool execution", "allowed": [
                    "python -m pytest/compileall", "pytest", "rg", "ruff", "mypy", "flake8", "black",
                    "git status/diff/log/show/branch/checkout/commit/stash/add/reset",
                    "npm run build/test/lint", "npm install X", "pip install X",
                    "ls", "pwd", "which", "echo",
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

    def _tool_analyze_image(self, image_path: str = "", **kw):
        try:
            from zicore.openvision import openvision as ov
            if image_path:
                return ov.analyze_media(image_path)
            captures_dir = Path(__file__).parent.parent / "data" / "vision" / "captures"
            if captures_dir.exists():
                caps = sorted(captures_dir.glob("*.jpg"), reverse=True)
                if caps:
                    return ov.analyze_media(str(caps[0]))
            return {"error": "No image specified and no captures available"}
        except Exception as e:
            return {"error": str(e)}

    def _tool_capture_webcam(self, device_index: int = 0, **kw):
        try:
            from zicore.openvision import openvision as ov
            return ov.capture_webcam(device_index=device_index)
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

    def _tool_ocr_image(self, image_path: str = "", lang: str = "spa+eng", **kw):
        """Extract text from an image using Tesseract OCR."""
        try:
            import pytesseract
            from PIL import Image
            if not image_path:
                return {"error": "No image path specified"}
            try:
                safe_path = _workspace_path(image_path)
            except ValueError as e:
                return {"error": f"Path not allowed: {e}"}
            img = Image.open(safe_path)
            text = pytesseract.image_to_string(img, lang=lang)
            return {"image_path": str(safe_path), "text": text.strip(), "language": lang, "characters": len(text)}
        except ImportError:
            return {"error": "pytesseract not installed. Run: pip install pytesseract && apt install tesseract-ocr"}
        except Exception as e:
            return {"error": f"OCR failed: {str(e)}"}

    def _tool_read_pdf(self, pdf_path: str = "", pages: str = "", **kw):
        """Extract text and metadata from a PDF file using PyMuPDF."""
        try:
            import fitz
            if not pdf_path:
                return {"error": "No PDF path specified"}
            try:
                safe_path = _workspace_path(pdf_path)
            except ValueError as e:
                return {"error": f"Path not allowed: {e}"}
            doc = fitz.open(safe_path)
            metadata = doc.metadata or {}
            total_pages = len(doc)
            # Parse page range
            page_indices = []
            if pages:
                for part in pages.split(","):
                    part = part.strip()
                    if "-" in part:
                        start, end = part.split("-", 1)
                        page_indices.extend(range(int(start) - 1, min(int(end), total_pages)))
                    else:
                        idx = int(part) - 1
                        if 0 <= idx < total_pages:
                            page_indices.append(idx)
            else:
                page_indices = list(range(min(total_pages, 20)))  # first 20 pages max
            extracted = []
            for idx in page_indices:
                page = doc[idx]
                text = page.get_text()
                if text.strip():
                    extracted.append({"page": idx + 1, "text": text.strip()})
            doc.close()
            full_text = "\n\n".join(p["text"] for p in extracted)
            return {
                "pdf_path": str(safe_path),
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "total_pages": total_pages,
                "pages_extracted": len(extracted),
                "text": full_text[:10000],
                "characters": len(full_text),
            }
        except ImportError:
            return {"error": "PyMuPDF not installed. Run: pip install PyMuPDF"}
        except Exception as e:
            return {"error": f"PDF read failed: {str(e)}"}

    def _tool_read_document(self, path: str = "", max_chars: int = 10000, **kw):
        """Read any text/document file."""
        try:
            import os
            if not path:
                return {"error": "No path specified"}
            try:
                safe_path = _workspace_path(path)
            except ValueError as e:
                return {"error": f"Path not allowed: {e}"}
            p = safe_path
            if not p.exists():
                return {"error": f"File not found: {path}"}
            ext = p.suffix.lower()
            # Binary file detection
            binary_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico",
                           ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac",
                           ".mp4", ".avi", ".mkv", ".mov", ".webm",
                           ".stl", ".obj", ".glb", ".gltf", ".fbx",
                           ".zip", ".tar", ".gz", ".rar", ".7z",
                           ".exe", ".dll", ".so", ".dylib", ".bin"}
            if ext in binary_exts:
                size = p.stat().st_size
                return {"path": str(p), "type": "binary", "extension": ext,
                        "size_bytes": size, "note": f"Binary file ({ext}). Cannot read as text."}
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_chars)
            return {
                "path": str(p),
                "type": "text",
                "extension": ext,
                "size_bytes": p.stat().st_size,
                "characters": len(content),
                "text": content,
                "truncated": p.stat().st_size > max_chars,
            }
        except Exception as e:
            return {"error": f"Read failed: {str(e)}"}

    def _tool_analyze_document(self, file_path: str = "", instruction: str = "", **kw):
        """Universal document analyzer — routes to the right tool based on file type."""
        try:
            import os
            if not file_path:
                return {"error": "No file path specified"}
            try:
                safe_path = _workspace_path(file_path)
            except ValueError as e:
                return {"error": f"Path not allowed: {e}"}
            p = safe_path
            if not p.exists():
                return {"error": f"File not found: {file_path}"}
            ext = p.suffix.lower()
            # Image → OCR
            image_exts = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".tif"}
            if ext in image_exts:
                return self._tool_ocr_image(str(p))
            # PDF → PyMuPDF
            if ext == ".pdf":
                return self._tool_read_pdf(str(p))
            # Everything else → read as text
            return self._tool_read_document(str(p))
        except Exception as e:
            return {"error": f"Document analysis failed: {str(e)}"}

    def _tool_store_memory(self, key: str = "", value: str = "", **kw):
        if not key:
            return {"error": "Key is required"}
        self.memory.remember_entity(key, value)
        return {"stored": True, "key": key, "value": value[:200]}

    def _tool_recall_memory(self, key: str = "", **kw):
        if not key:
            return {"error": "Key is required"}
        val = self.memory.recall_entity(key)
        if val is None:
            return {"found": False, "key": key, "message": f"No memory found for '{key}'"}
        return {"found": True, "key": key, "value": str(val)[:500]}

    def _tool_conversation_summary(self, **kw):
        summary = self.memory.summarize()
        recent = self.memory.get_recent(5)
        topics = []
        for entry in recent:
            c = str(entry.get("content", ""))[:100]
            if c:
                topics.append(c)
        return {
            "summary": summary,
            "recent_count": len(self.memory.short_term),
            "long_term_count": len(self.memory.long_term),
            "recent_topics": topics,
        }

    def _tool_send_notification(self, title: str = "ZIO Alert", body: str = "", **kw):
        if not body:
            body = title
            title = "ZIO Alert"
        self.memory.remember_entity("_last_notification", {"title": title, "body": body, "time": time.time()})
        return {"sent": True, "title": title, "body": body[:200], "note": "Notification queued (will display on next client poll)"}

    def _tool_create_reminder(self, message: str = "", minutes: int = 5, **kw):
        if not message:
            return {"error": "Reminder message is required"}
        trigger_at = time.time() + (minutes * 60)
        reminder = {"message": message, "trigger_at": trigger_at, "minutes": minutes, "created": time.time()}
        existing = self.memory.recall_entity("_reminders") or []
        if not isinstance(existing, list):
            existing = []
        existing.append(reminder)
        self.memory.remember_entity("_reminders", existing)
        return {"created": True, "message": message, "in_minutes": minutes, "total_active": len(existing)}

    def _tool_set_alarm(self, time_str: str = "", label: str = "", **kw):
        if not time_str:
            return {"error": "Alarm time is required (e.g. '07:30', 'in 30 minutes')"}
        if not label:
            label = f"Alarm at {time_str}"
        alarm = {"time_str": time_str, "label": label, "created": time.time()}
        existing = self.memory.recall_entity("_alarms") or []
        if not isinstance(existing, list):
            existing = []
        existing.append(alarm)
        self.memory.remember_entity("_alarms", existing)
        return {"set": True, "time": time_str, "label": label, "total_alarms": len(existing)}

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

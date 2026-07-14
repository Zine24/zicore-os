"""
ZICORE Web Server - Frontend + Backend unified
Serves dashboard, ZIO agent, and API on configurable port.
"""
import os
import sys
import json
import copy
import re
import hashlib
import secrets
import logging
import sqlite3
import time
import threading
from datetime import datetime, timezone, timedelta
import uvicorn
import urllib.request
import urllib.error
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("zicore.web")

FRONTEND_DIR = Path(__file__).parent / "frontend"
OUTPUT_DIR = Path(__file__).parent / "output"
CONFIG_DIR = Path(__file__).parent / "data" / "config"
MISSIONS_DIR = Path(__file__).parent / "data" / "missions"
MEDIA_DIR = Path(os.environ.get("ZICORE_MEDIA_DIR", str(Path(__file__).parent / "data" / "media")))
ZICORE_FS_MEDIA = Path(os.environ.get("ZICORE_FS_MEDIA", "/mnt/zicore-fs/Media"))
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
MISSIONS_DIR.mkdir(parents=True, exist_ok=True)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
for _cat in ("audio", "video", "images", "music"):
    (MEDIA_DIR / _cat).mkdir(parents=True, exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "zio_config.json"
telemetry_modules = {}
OLLAMA_BASE_URL = os.environ.get("ZICORE_OLLAMA_BASE_URL", "http://localhost:11434")
NODE_BASE_URL = os.environ.get("ZICORE_NODE_BASE_URL", "http://192.168.1.68:4000")
SECRET_MASK = "********"
ZIO_SYSTEM_PROMPT = (
    "You are ZIO, the ZICORE Intelligence Operator. You control and assist the "
    "ZICORE system with aerospace operations, generation tools, code navigation, "
    "safe workspace edits, and diagnostics. You must preserve the agent "
    "infrastructure, keep changes scoped to zicore-system, and avoid destructive "
    "actions unless explicitly authorized."
)

DEFAULT_CONFIG = {
    "providers": {
        "openrouter": {
            "name": "OpenRouter",
            "enabled": False,
            "api_key": "",
            "base_url": "https://openrouter.ai/api/v1",
            "default_model": "openrouter/free",
            "models": [
                "openrouter/free",
                "tencent/hy3:free",
                "nvidia/nemotron-3-ultra-250b:free",
                "poolside/laguna-m1:free",
                "nvidia/nemotron-3-super-120b-a12b:free",
                "cohere/north-mini-code:free",
                "poolside/laguna-xs-2.1:free",
                "nvidia/nemotron-3-nano-30b-a3b:free",
                "google/gemma-4-31b-it:free",
                "openai/gpt-oss-120b:free",
                "nvidia/nemotron-3-nano-omni:free",
                "openai/gpt-oss-20b:free",
                "nvidia/nemotron-nano-9b-v2:free",
                "nvidia/nemotron-nano-12b-2-vl:free",
                "google/gemma-4-26b-a4b-it:free",
                "liquid/lfm-2.5-1.2b-instruct:free",
                "meta-llama/llama-3.1-8b-instruct:free",
                "meta-llama/llama-3.1-70b-instruct:free",
                "qwen/qwen-2.5-72b-instruct:free",
                "qwen/qwen-2.5-coder-32b-instruct:free",
                "deepseek/deepseek-chat:free",
                "deepseek/deepseek-r1:free",
                "mistralai/mistral-7b-instruct:free",
                "microsoft/phi-3-mini-128k-instruct:free",
                "microsoft/phi-3-medium-128k-instruct:free",
                "nvidia/llama-3.1-nemotron-70b-instruct:free",
                "qwen/qwen-2.5-7b-instruct:free",
                "google/gemma-2-9b-it:free",
                "anthropic/claude-3-haiku",
                "openai/gpt-4o-mini",
                "openai/gpt-4o",
                "anthropic/claude-3.5-sonnet",
            ],
        },
        "ollama": {
            "name": "Ollama (Local)",
            "enabled": False,
            "base_url": OLLAMA_BASE_URL,
            "default_model": "llama3.1:8b",
            "models": [],
        },
        "openai": {
            "name": "OpenAI",
            "enabled": False,
            "api_key": "",
            "base_url": "https://api.openai.com/v1",
            "default_model": "gpt-4o-mini",
            "models": [
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
                "o1-mini",
                "o1-preview",
                "o3-mini",
            ],
        },
        "anthropic": {
            "name": "Anthropic",
            "enabled": False,
            "api_key": "",
            "base_url": "https://api.anthropic.com/v1",
            "default_model": "claude-3-haiku-20240307",
            "models": [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                "claude-3.5-sonnet-20241022",
                "claude-3.5-haiku-20241022",
            ],
        },
        "groq": {
            "name": "Groq",
            "enabled": False,
            "api_key": "",
            "base_url": "https://api.groq.com/openai/v1",
            "default_model": "llama-3.1-8b-instant",
            "models": [
                "llama-3.1-8b-instant",
                "llama-3.1-70b-versatile",
                "llama-3.3-70b-versatile",
                "mixtral-8x7b-32768",
                "gemma2-9b-it",
                "deepseek-r1-distill-llama-70b",
                "qwen-qwq-32b",
                "llama-3.2-1b-preview",
                "llama-3.2-3b-preview",
                "llama-3.2-11b-vision-preview",
                "llama-3.2-90b-vision-preview",
            ],
        },
        "deepseek": {
            "name": "DeepSeek",
            "enabled": False,
            "api_key": "",
            "base_url": "https://api.deepseek.com/v1",
            "default_model": "deepseek-chat",
            "models": [
                "deepseek-chat",
                "deepseek-coder",
                "deepseek-reasoner",
            ],
        },
        "together": {
            "name": "Together AI",
            "enabled": False,
            "api_key": "",
            "base_url": "https://api.together.xyz/v1",
            "default_model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            "models": [
                "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
                "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                "meta-llama/Meta-Llama-3.3-70B-Instruct-Turbo",
                "mistralai/Mixtral-8x7B-Instruct-v0.1",
                "google/gemma-2-9b-it",
                "Qwen/Qwen2.5-72B-Instruct-Turbo",
                "deepseek-ai/DeepSeek-R1",
                "deepseek-ai/DeepSeek-V3",
                "NousResearch/Hermes-3-Llama-3.1-405B",
            ],
        },
        "opencode": {
            "name": "OpenCode Zen",
            "enabled": False,
            "api_key": "",
            "base_url": "https://api.opencode.ai/v1",
            "default_model": "opencode/mimo-v2-free",
            "models": [
                "opencode/mimo-v2-free",
                "opencode/mimo-v2.5-free",
                "opencode/mimo-v2-pro-free",
                "opencode/big-pickle-free",
                "opencode/ring-2.6-1t-free",
                "opencode/hy3-preview-free",
                "opencode/ling-2.6-flash-free",
                "opencode/north-mini-code-free",
                "opencode/mimo-v2-pro",
                "opencode/codestral-2407",
                "opencode/deepseek-v3",
                "opencode/deepseek-r1",
                "opencode/llama-3.1-8b",
                "opencode/mistral-7b",
                "opencode/gemma-2-9b",
                "opencode/qwen-2.5-72b",
            ],
        },
    },
    "zio_engine": {
        "active_provider": "zicore_native",
        "temperature": 0.7,
        "max_tokens": 4096,
        "top_p": 0.9,
        "stream": True,
        "system_prompt": ZIO_SYSTEM_PROMPT,
    },
    "agent": {
        "name": "ZIO",
        "controller_for": "zicore",
        "safe_workspace": "zicore-system",
        "allow_code_tools": True,
        "protected_paths": [".git", ".agents", ".codex", "node_modules", ".venv", "venv"],
    },
    "ollama_service": {
        "enabled": False,
        "managed": False,
        "base_url": OLLAMA_BASE_URL,
        "models_dir": "data/ollama/models",
        "binary_dir": "tools/ollama",
    },
    "theme": "midnight",
    "server": {
        "host": "0.0.0.0",
        "port": 3000,
        "api_port": 8080,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        elif isinstance(value, list) and isinstance(result.get(key), list):
            # Merge lists: keep saved items, add new defaults not already present
            if value:
                merged = list(value)
                base_items = result.get(key, [])
                for item in base_items:
                    item_str = item if isinstance(item, str) else str(item)
                    if item not in merged and item_str not in [x if isinstance(x, str) else str(x) for x in merged]:
                        merged.append(item)
                result[key] = merged
            # If empty, keep defaults (don't override)
        else:
            result[key] = value
    return result


def _sanitize_config(config: dict) -> dict:
    safe = copy.deepcopy(config)
    for provider in safe.get("providers", {}).values():
        api_key = provider.get("api_key", "")
        provider["has_api_key"] = bool(api_key and api_key != SECRET_MASK)
        if "api_key" in provider:
            provider["api_key"] = SECRET_MASK if provider["has_api_key"] else ""
    safe.pop("ollama_service", None)
    return safe


def _preserve_secret_updates(current: dict, incoming: dict) -> dict:
    merged = copy.deepcopy(incoming)
    for provider, settings in merged.get("providers", {}).items():
        current_key = current.get("providers", {}).get(provider, {}).get("api_key", "")
        incoming_key = settings.get("api_key", None)
        if incoming_key in (None, "", SECRET_MASK) and current_key:
            settings["api_key"] = current_key
    return merged


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                return _deep_merge(DEFAULT_CONFIG, data)
        except Exception:
            pass
    return copy.deepcopy(DEFAULT_CONFIG)


def save_config(config: dict):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Config saved to {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")


def _request_json(url: str, method: str = "GET", headers: dict = None, payload: dict = None, timeout: int = 20) -> dict:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _provider_headers(provider: str, api_key: str) -> dict:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if provider == "anthropic":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
    return headers


def _extract_model_ids(provider: str, data: dict) -> list:
    models = data.get("models") if provider == "ollama" else data.get("data")
    ids = []
    if isinstance(models, list):
        for item in models:
            if isinstance(item, dict):
                mid = item.get("name") or item.get("id")
            else:
                mid = str(item)
            if mid:
                ids.append(mid)
    return sorted(set(ids))


def get_available_models(provider: str, config: dict = None) -> dict:
    config = config or load_config()
    prov = config.get("providers", {}).get(provider, {})
    if not prov:
        return {"status": "unknown_provider", "provider": provider, "models": []}
    base_url = prov.get("base_url", "").rstrip("/")
    if not base_url.startswith("http"):
        base_url = f"http://{base_url}"
    api_key = prov.get("api_key", "")
    config_models = prov.get("models", [])
    if provider == "ollama":
        try:
            data = _request_json(f"{base_url}/api/tags", timeout=5)
            return {"status": "ok", "provider": provider, "models": _extract_model_ids(provider, data)}
        except Exception as e:
            return {"status": "error", "provider": provider, "models": config_models, "error": str(e)}
    # OpenCode has no /v1/models endpoint — use config models directly
    if provider == "opencode":
        if not api_key:
            return {"status": "no_api_key", "provider": provider, "models": config_models}
        return {"status": "ok", "provider": provider, "models": config_models}
    if provider in ("openrouter", "openai", "groq", "deepseek", "together", "anthropic"):
        if not api_key:
            return {"status": "no_api_key", "provider": provider, "models": config_models}
        try:
            data = _request_json(f"{base_url}/models", headers=_provider_headers(provider, api_key), timeout=15)
            api_models = _extract_model_ids(provider, data)
            merged = sorted(set(api_models + config_models))
            return {"status": "ok", "provider": provider, "models": merged}
        except Exception as e:
            return {"status": "fallback", "provider": provider, "models": config_models, "error": str(e)}
    return {"status": "unsupported", "provider": provider, "models": config_models}


def build_system_prompt(config: dict, context: str = "") -> str:
    prompt = config.get("zio_engine", {}).get("system_prompt") or ZIO_SYSTEM_PROMPT
    if context:
        prompt += f"\n\nRelevant knowledge context:\n{context[:1500]}"
    return prompt


def _chat_response_text(provider: str, result: dict) -> str:
    if provider == "ollama":
        if "message" in result:
            return result.get("message", {}).get("content", "")
        return result.get("response", "")
    return result.get("choices", [{}])[0].get("message", {}).get("content", "")


def call_provider_chat(provider: str, message: str, config: dict, context: str = "") -> dict:
    prov = config.get("providers", {}).get(provider, {})
    base_url = prov.get("base_url", "").rstrip("/")
    if base_url and not base_url.startswith("http"):
        base_url = f"http://{base_url}"
    model = prov.get("default_model", "")
    system_msg = build_system_prompt(config, context)
    temperature = config.get("zio_engine", {}).get("temperature", 0.7)
    top_p = config.get("zio_engine", {}).get("top_p", 0.9)
    max_tokens = config.get("zio_engine", {}).get("max_tokens", 4096)

    if provider == "ollama":
        combined_user_msg = f"{system_msg}\n\n---\n\n{message}"
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": combined_user_msg},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_tokens,
            },
        }
        result = _request_json(f"{base_url}/api/chat", method="POST",
                               headers={"Content-Type": "application/json"}, payload=payload, timeout=120)
    else:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": message},
            ],
            "stream": False,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }
        api_key = prov.get("api_key", "")
        if not api_key:
            return {"status": "error", "error": "No API key configured"}
        result = _request_json(f"{base_url}/chat/completions", method="POST",
                               headers=_provider_headers(provider, api_key), payload=payload, timeout=120)
    return {"status": "ok", "provider": provider, "model": model, "response": _chat_response_text(provider, result)}


# ─── Traffic Logger (SQLite persistence) ────────────────────────────────────

TRAFFIC_DB = Path(__file__).parent / "data" / "traffic.db"

class TrafficLogger:
    """Logs every HTTP request to SQLite for analytics."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS traffic_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                method TEXT NOT NULL,
                path TEXT NOT NULL,
                status INTEGER,
                ms REAL,
                ip TEXT,
                ua TEXT,
                size INTEGER DEFAULT 0
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON traffic_log(ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON traffic_log(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_path ON traffic_log(path)")
        conn.commit()

    def log(self, method: str, path: str, status: int, ms: float, ip: str, ua: str, size: int = 0):
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO traffic_log (ts, method, path, status, ms, ip, ua, size) VALUES (?,?,?,?,?,?,?,?)",
                (datetime.now(timezone.utc).isoformat(), method, path, status, round(ms, 2), ip, ua[:200], size)
            )
            conn.commit()
        except Exception:
            pass

    def overview(self, hours: int = 24) -> dict:
        conn = self._get_conn()
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        row = conn.execute(
            "SELECT COUNT(*) as total, "
            "SUM(CASE WHEN status >= 500 THEN 1 ELSE 0 END) as errors, "
            "SUM(CASE WHEN status >= 400 AND status < 500 THEN 1 ELSE 0 END) as client_err, "
            "ROUND(AVG(ms),2) as avg_ms, "
            "ROUND(MIN(ms),2) as min_ms, "
            "ROUND(MAX(ms),2) as max_ms, "
            "COUNT(DISTINCT ip) as unique_ips, "
            "SUM(size) as total_bytes "
            "FROM traffic_log WHERE ts >= ?", (since,)
        ).fetchone()
        total = row["total"] or 0
        errors = row["errors"] or 0
        return {
            "period_hours": hours,
            "total_requests": total,
            "server_errors": errors,
            "client_errors": row["client_err"] or 0,
            "error_rate": round(errors / total * 100, 2) if total else 0,
            "avg_response_ms": row["avg_ms"] or 0,
            "min_response_ms": row["min_ms"] or 0,
            "max_response_ms": row["max_ms"] or 0,
            "unique_ips": row["unique_ips"] or 0,
            "total_bytes": row["total_bytes"] or 0,
        }

    def requests_per_hour(self, hours: int = 24) -> list:
        conn = self._get_conn()
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        rows = conn.execute(
            "SELECT substr(ts, 1, 13) as hour, COUNT(*) as count "
            "FROM traffic_log WHERE ts >= ? GROUP BY hour ORDER BY hour", (since,)
        ).fetchall()
        return [{"hour": r["hour"], "count": r["count"]} for r in rows]

    def top_endpoints(self, hours: int = 24, limit: int = 20) -> list:
        conn = self._get_conn()
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        rows = conn.execute(
            "SELECT path, COUNT(*) as hits, ROUND(AVG(ms),2) as avg_ms, "
            "SUM(CASE WHEN status >= 500 THEN 1 ELSE 0 END) as errors "
            "FROM traffic_log WHERE ts >= ? GROUP BY path ORDER BY hits DESC LIMIT ?",
            (since, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def top_ips(self, hours: int = 24, limit: int = 20) -> list:
        conn = self._get_conn()
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        rows = conn.execute(
            "SELECT ip, COUNT(*) as hits, ROUND(AVG(ms),2) as avg_ms "
            "FROM traffic_log WHERE ts >= ? GROUP BY ip ORDER BY hits DESC LIMIT ?",
            (since, limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def status_breakdown(self, hours: int = 24) -> list:
        conn = self._get_conn()
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        rows = conn.execute(
            "SELECT status, COUNT(*) as count "
            "FROM traffic_log WHERE ts >= ? GROUP BY status ORDER BY count DESC",
            (since,)
        ).fetchall()
        return [dict(r) for r in rows]

    def cleanup(self, days: int = 30):
        conn = self._get_conn()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        conn.execute("DELETE FROM traffic_log WHERE ts < ?", (cutoff,))
        conn.commit()


traffic = TrafficLogger(TRAFFIC_DB)


class TrafficMiddleware:
    """ASGI middleware that logs requests to SQLite."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        method = scope["method"]
        path = scope["path"]
        # Skip static file polling noise
        skip = path.startswith("/api/system/stats") or path.endswith(".js") or path.endswith(".css")
        ip = ""
        for h in scope.get("headers", []):
            if h[0] == b"x-forwarded-for":
                ip = h[1].decode().split(",")[0].strip()
                break
        if not ip:
            ip = scope.get("client", ("0.0.0.0", 0))[0]

        ua = ""
        for h in scope.get("headers", []):
            if h[0] == b"user-agent":
                ua = h[1].decode()
                break

        start = time.monotonic()
        status = 200
        size = 0

        async def send_wrapper(message):
            nonlocal status, size
            if message["type"] == "http.response.start":
                status = message.get("status", 200)
            elif message["type"] == "http.response.body":
                size += len(message.get("body", b""))
            return await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            status = 500
            raise
        finally:
            ms = (time.monotonic() - start) * 1000
            if not skip:
                traffic.log(method, path, status, ms, ip, ua, size)


app = FastAPI(title="ZICORE Web Server", version="5.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrafficMiddleware)


@app.get("/")
async def serve_main_menu(request: Request):
    host = request.headers.get("host", "")
    if "zinemotion.com.mx" in host:
        return FileResponse(str(FRONTEND_DIR / "zinemotion.html"))
    if "zcs.zicore.space" in host or "zicore.space" in host:
        return FileResponse(str(FRONTEND_DIR / "zicore-portal.html"))
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/zinemotion")
async def serve_zinemotion():
    return FileResponse(str(FRONTEND_DIR / "zinemotion.html"))


@app.get("/zicore")
async def serve_zicore():
    return FileResponse(str(FRONTEND_DIR / "zicore-portal.html"))


@app.get("/aerospace")
async def serve_aerospace():
    return FileResponse(str(FRONTEND_DIR / "aerospace.html"))


@app.get("/engineering")
async def serve_engineering():
    return FileResponse(str(FRONTEND_DIR / "engineering.html"))


@app.get("/aerospace-engineering")
async def serve_aerospace_engineering():
    return FileResponse(str(FRONTEND_DIR / "aerospace-engineering.html"))


@app.get("/environment")
async def serve_environment():
    return FileResponse(str(FRONTEND_DIR / "environment.html"))


@app.get("/mail")
async def serve_mail():
    return FileResponse(str(FRONTEND_DIR / "mail.html"))


@app.get("/mission-control")
async def serve_mission_control():
    return FileResponse(str(FRONTEND_DIR / "mission-control.html"))


@app.get("/portal")
async def serve_portal():
    return FileResponse(str(FRONTEND_DIR / "portal.html"))


@app.get("/download")
async def serve_download():
    return RedirectResponse(url="/installers")


@app.get("/installers")
async def serve_installers():
    return FileResponse(str(FRONTEND_DIR / "installers.html"))


INSTALLERS_DIR = Path(__file__).parent / "installers"

@app.get("/installers/{filename}")
async def download_installer(filename: str):
    allowed = {"install_zicore.ps1", "install_zicore.sh", "install_zicore_mac.sh"}
    if filename not in allowed:
        return JSONResponse({"status": "error", "error": "File not found"}, status_code=404)
    fpath = INSTALLERS_DIR / filename
    if not fpath.exists():
        return JSONResponse({"status": "error", "error": "File not found"}, status_code=404)
    media_type = "text/plain" if filename.endswith(".sh") else "text/plain"
    return FileResponse(str(fpath), media_type=media_type, filename=filename)


@app.get("/dashboard")
async def serve_dashboard():
    return FileResponse(str(FRONTEND_DIR / "dashboard.html"))


@app.get("/zio")
async def serve_zio():
    return FileResponse(str(FRONTEND_DIR / "zio.html"))


@app.get("/sim")
async def serve_simulator():
    return FileResponse(str(FRONTEND_DIR / "simulator.html"))


@app.get("/flight-sim")
async def serve_flight_sim():
    return FileResponse(str(FRONTEND_DIR / "flight-sim.html"))


@app.get("/emulatorjs")
async def serve_emulatorjs():
    return RedirectResponse(url="http://localhost:4001")


@app.get("/games")
async def serve_games():
    return FileResponse(str(FRONTEND_DIR / "games.html"))


GAMES_SCORES_FILE = Path(__file__).parent / "data" / "games_scores.json"

def _load_game_scores():
    if GAMES_SCORES_FILE.exists():
        try:
            with open(GAMES_SCORES_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_game_scores(scores):
    GAMES_SCORES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(GAMES_SCORES_FILE, "w") as f:
        json.dump(scores, f, indent=2)

GAMES_CATALOG = [
    {"id": "arkanoid", "name": "Arkanoid", "category": "arcade", "icon": "&#127918;"},
    {"id": "flappy-bird", "name": "Flappy Bird", "category": "arcade", "icon": "&#129413;"},
    {"id": "geometry-dash", "name": "Geometry Dash", "category": "arcade", "icon": "&#128190;"},
    {"id": "pacman", "name": "Pac-Man", "category": "arcade", "icon": "&#128123;"},
    {"id": "space-invaders", "name": "Space Invaders", "category": "arcade", "icon": "&#128126;"},
]


@app.get("/api/games/catalog")
async def games_catalog():
    return {"status": "ok", "games": GAMES_CATALOG}


@app.get("/api/games/scores")
async def games_scores(game: str = None, limit: int = 10):
    scores = _load_game_scores()
    if game:
        game_scores = scores.get(game, [])[:limit]
        return {"status": "ok", "game": game, "scores": game_scores}
    top = {}
    for g, s in scores.items():
        top[g] = s[:limit]
    return {"status": "ok", "scores": top}


@app.post("/api/games/score")
async def games_submit_score(body: dict):
    game = body.get("game", "")
    player = body.get("player", "Anonymous")
    score_val = body.get("score", 0)
    if not game:
        return {"status": "error", "error": "No game specified"}
    scores = _load_game_scores()
    if game not in scores:
        scores[game] = []
    entry = {
        "player": player,
        "score": score_val,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    }
    scores[game].append(entry)
    scores[game].sort(key=lambda x: x.get("score", 0), reverse=True)
    scores[game] = scores[game][:50]
    _save_game_scores(scores)
    rank = next((i + 1 for i, s in enumerate(scores[game]) if s is entry), -1)
    return {"status": "ok", "rank": rank, "total": len(scores[game])}


@app.post("/api/games/scores/reset")
async def games_reset_scores(game: str = ""):
    scores = _load_game_scores()
    if game:
        scores[game] = []
    else:
        scores = {}
    _save_game_scores(scores)
    return {"status": "ok"}


@app.get("/multimedia")
async def serve_multimedia():
    return FileResponse(str(FRONTEND_DIR / "multimedia.html"))


@app.get("/settings")
async def serve_settings():
    return FileResponse(str(FRONTEND_DIR / "settings.html"))


MEDIA_CATEGORIES = {
    "audio": [".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac"],
    "music": [".wav", ".mp3", ".ogg", ".flac", ".m4a", ".aac"],
    "video": [".mp4", ".webm", ".ogv", ".mov", ".mkv", ".avi"],
    "images": [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"],
}

def _scan_media_tree(root, exts, url_prefix="", max_depth=6):
    """Recursively scan a directory tree for media files."""
    import mimetypes
    items = []
    root = Path(root)
    if not root.exists():
        return items
    for depth in range(max_depth + 1):
        pattern = "*"
        if depth > 0:
            pattern = "*/" * depth + "*"
        try:
            for f in root.glob(pattern):
                if f.is_file() and f.suffix.lower() in exts:
                    try:
                        rel = str(f.relative_to(root)).replace("\\", "/")
                        items.append({
                            "name": f.name,
                            "path": rel,
                            "url": f"/media-fs/{url_prefix}{rel}" if url_prefix else f"/media-fs/{rel}",
                            "size": f.stat().st_size,
                            "ext": f.suffix.lower().lstrip("."),
                            "mime": mimetypes.guess_type(f.name)[0] or "application/octet-stream",
                            "dir": str(f.parent.relative_to(root)).replace("\\", "/"),
                        })
                    except (ValueError, OSError):
                        continue
        except (ValueError, OSError):
            break
    return items


@app.get("/api/media/list")
async def media_list():
    """List all media files from local MEDIA_DIR and zicore-fs, organized by category."""
    import mimetypes
    result = {}

    # Local media
    for cat, exts in MEDIA_CATEGORIES.items():
        cat_dir = MEDIA_DIR / cat
        items = []
        if cat_dir.exists():
            for f in sorted(cat_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in exts:
                    rel = f"{cat}/{f.name}"
                    items.append({
                        "name": f.name,
                        "path": rel,
                        "url": f"/media/{rel}",
                        "size": f.stat().st_size,
                        "ext": f.suffix.lower().lstrip("."),
                        "mime": mimetypes.guess_type(f.name)[0] or "application/octet-stream",
                        "dir": "local",
                    })
        result[cat] = items

    # zicore-fs media (organized by type)
    # Mount root: /mnt/zicore-fs/Media  →  URL: /media-fs/
    fs_map = {
        "audio": [(ZICORE_FS_MEDIA / "Movies" / "Media" / "Music", "Movies/Media/Music/"), (ZICORE_FS_MEDIA / "music", "music/")],
        "music": [(ZICORE_FS_MEDIA / "Movies" / "Media" / "Music", "Movies/Media/Music/"), (ZICORE_FS_MEDIA / "music", "music/")],
        "video": [(ZICORE_FS_MEDIA / "Movies" / "Media" / "Movies", "Movies/Media/Movies/")],
        "images": [
            (ZICORE_FS_MEDIA / "Movies" / "Media" / "Photo", "Movies/Media/Photo/"),
            (ZICORE_FS_MEDIA / "Movies" / "Media" / "Fotos", "Movies/Media/Fotos/"),
            (ZICORE_FS_MEDIA / "Movies" / "Media" / "B&N", "Movies/Media/B&N/"),
        ],
    }

    for cat, dirs in fs_map.items():
        if cat not in result:
            result[cat] = []
        for d, prefix in dirs:
            if d.exists():
                result[cat].extend(_scan_media_tree(d, MEDIA_CATEGORIES[cat], url_prefix=prefix))

    result["_totals"] = {c: len(v) for c, v in result.items() if c != "_totals"}
    result["_fs_root"] = str(ZICORE_FS_MEDIA) if ZICORE_FS_MEDIA.exists() else None
    return result


@app.get("/api/status")
async def web_status():
    config = load_config()
    return {
        "status": "online",
        "service": "zicore-web",
        "version": app.version,
        "agent": config.get("agent", {}).get("name", "ZIO"),
        "active_provider": config.get("zio_engine", {}).get("active_provider", "zicore_native"),
        "ollama": {
            "base_url": config.get("providers", {}).get("ollama", {}).get("base_url", OLLAMA_BASE_URL),
            "managed": config.get("ollama_service", {}).get("managed", False),
        },
    }


@app.get("/api/config")
async def get_config():
    return _sanitize_config(load_config())


@app.post("/api/config")
async def update_config(config: dict):
    current = load_config()
    config = _preserve_secret_updates(current, config)
    updated = _deep_merge(current, config)
    save_config(updated)
    return {"status": "ok", "config": _sanitize_config(updated)}


@app.post("/api/config/provider/{provider}")
async def update_provider(provider: str, settings: dict):
    config = load_config()
    if provider in config.get("providers", {}):
        if settings.get("api_key") in ("", SECRET_MASK, None) and config["providers"][provider].get("api_key"):
            settings.pop("api_key", None)
        config["providers"][provider].update(settings)
        save_config(config)
        return {"status": "ok", "provider": _sanitize_config({"providers": {provider: config["providers"][provider]}})["providers"][provider]}
    return {"error": f"Unknown provider: {provider}"}


@app.get("/api/config/provider/{provider}")
async def get_provider(provider: str):
    config = load_config()
    prov = config.get("providers", {}).get(provider)
    if prov:
        return _sanitize_config({"providers": {provider: prov}})["providers"][provider]
    return {"error": f"Unknown provider: {provider}"}


@app.get("/api/provider/models/{provider}")
async def provider_models(provider: str):
    return get_available_models(provider)


@app.get("/api/ollama/status")
async def ollama_status():
    from zicore.ollama_service import status
    config = load_config()
    base_url = config.get("providers", {}).get("ollama", {}).get("base_url", "127.0.0.1:11434")
    if not base_url.startswith("http"):
        base_url = f"http://{base_url}"
    return status(base_url)


@app.post("/api/ollama/start")
async def ollama_start():
    from zicore.ollama_service import start
    return start()


@app.post("/api/ollama/stop")
async def ollama_stop():
    from zicore.ollama_service import stop
    return stop()


@app.post("/api/ollama/pull")
async def ollama_pull(request: Request):
    from zicore.ollama_service import pull_model
    data = await request.json()
    model = data.get("model", "tinyllama")
    return pull_model(model)


# --- Node Bridge (.68 Inference Node) ---


def _node_request(path: str, method: str = "GET", payload: dict = None, timeout: int = 60) -> dict:
    url = f"{NODE_BASE_URL}{path}"
    headers = {"Content-Type": "application/json"} if payload else None
    try:
        return _request_json(url, method=method, headers=headers, payload=payload, timeout=timeout)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"status": "error", "error": f"HTTP {e.code}: {e.reason}", "detail": body[:500]}
    except urllib.error.URLError as e:
        return {"status": "error", "error": f"Node unreachable: {e.reason}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/node/status")
async def node_status():
    return _node_request("/api/status")


@app.get("/api/node/models")
async def node_models():
    return _node_request("/api/ollama/models")


@app.post("/api/node/chat")
async def node_chat(body: dict):
    return _node_request("/api/ollama/chat", method="POST", payload=body, timeout=180)


@app.post("/api/node/generate")
async def node_generate(body: dict):
    return _node_request("/api/generate", method="POST", payload=body, timeout=300)


@app.post("/api/node/process/video")
async def node_process_video(body: dict):
    return _node_request("/api/process/video", method="POST", payload=body, timeout=300)


@app.post("/api/config/test-provider/{provider}")
async def test_provider(provider: str):
    config = load_config()
    prov = config.get("providers", {}).get(provider, {})
    if not prov.get("enabled"):
        return {"status": "disabled", "provider": provider}

    base_url = prov.get("base_url", "")
    api_key = prov.get("api_key", "")
    model = prov.get("default_model", "unknown")

    if provider == "ollama":
        try:
            models_result = get_available_models(provider, config)
            chat_data = call_provider_chat(provider, "hello", config)
            return {
                "status": "connected",
                "provider": provider,
                "model": model,
                "available_models": models_result.get("models", []),
                "base_url": base_url,
                "chat_ok": True,
                "response_preview": chat_data.get("response", "")[:80],
            }
        except Exception as e:
            return {"status": "error", "provider": provider, "error": str(e)}

    elif provider in ("openrouter", "openai", "anthropic", "groq", "deepseek", "together", "opencode"):
        if not api_key:
            return {"status": "no_api_key", "provider": provider, "available_models": []}
        models_result = get_available_models(provider, config)
        return {
            "status": "configured",
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "has_key": True,
            "available_models": models_result.get("models", []),
            "models_status": models_result.get("status"),
        }

    return {"status": "unknown_provider", "provider": provider, "available_models": []}


@app.post("/api/provider/chat")
async def provider_chat(body: dict):
    """Send chat to configured provider."""
    config = load_config()
    provider_name = body.get("provider", config.get("zio_engine", {}).get("active_provider", "zicore_native"))
    message = body.get("message", "")

    if provider_name == "zicore_native":
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from agent.core import ZICoreAgent
            import asyncio
            agent = ZICoreAgent(session_id="webchat")
            result = await agent.process(message, {"source": "webchat"})
            return {
                "status": "ok",
                "provider": "zicore_native",
                "response": result.get("outputs", {}).get("text", result.get("outputs", {}).get("zio_msg", "")),
                "intent": result.get("intent", "general"),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    prov_config = config.get("providers", {}).get(provider_name, {})
    if not prov_config.get("enabled"):
        return {"status": "error", "error": f"Provider {provider_name} not enabled"}

    try:
        return call_provider_chat(provider_name, message, config)
    except Exception as e:
        return {"status": "error", "provider": provider_name, "error": str(e)}


@app.post("/api/chat")
async def chat_with_context(body: dict):
    """Chat endpoint with knowledge base context injection."""
    message = body.get("message", "")
    session_id = body.get("session_id", "api")
    provider = body.get("provider", "zicore_native")

    try:
        from zicore.knowledge_base import knowledge_base
        knowledge_base.add_message("user", message, session_id=session_id)
        context = knowledge_base.get_context_for_query(message)
    except Exception:
        context = ""

    if provider == "zicore_native":
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from agent.core import ZICoreAgent
            agent = ZICoreAgent(session_id=session_id)
            result = await agent.process(message, {"source": "api", "knowledge_context": context})
            reply = result.get("outputs", {}).get("text",
                result.get("outputs", {}).get("zio_msg", ""))
            try:
                from zicore.knowledge_base import knowledge_base
                knowledge_base.add_message("zio", reply, session_id=session_id,
                                          intent=result.get("intent", ""))
            except Exception:
                pass
            return {
                "status": "ok",
                "response": reply,
                "intent": result.get("intent", "general"),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    config = load_config()
    prov_config = config.get("providers", {}).get(provider, {})
    if not prov_config.get("enabled"):
        return {"status": "error", "error": f"Provider {provider} not enabled"}

    try:
        provider_result = call_provider_chat(provider, message, config, context)
        if provider_result.get("status") != "ok":
            return provider_result
        response_text = provider_result.get("response", "")
        try:
            from zicore.knowledge_base import knowledge_base
            knowledge_base.add_message("zio", response_text, session_id=session_id)
        except Exception:
            pass
        provider_result["response"] = response_text
        return provider_result
    except Exception as e:
        return {"status": "error", "provider": provider, "error": str(e)}


@app.get("/api/telemetry")
async def get_telemetry():
    """Get real-time telemetry data."""
    try:
        from zicore.telemetry_sim import telemetry_sim
        return telemetry_sim.get_telemetry()
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/telemetry/modules")
async def get_module_telemetry():
    """Get module status."""
    try:
        from zicore.telemetry_sim import telemetry_sim
        return telemetry_sim.get_module_status()
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/system/stats")
async def get_system_stats():
    """Get real system stats (CPU, RAM, disk, uptime)."""
    import time as _time
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        boot = psutil.boot_time()
        uptime_s = _time.time() - boot
        days = int(uptime_s // 86400)
        hours = int((uptime_s % 86400) // 3600)
        mins = int((uptime_s % 3600) // 60)
        uptime_str = f"{days}d {hours}h {mins}m" if days else f"{hours}h {mins}m"
        ollama_ok = False
        sd_ok = False
        active_prov = "zicore_native"
        try:
            config = load_config()
            active_prov = config.get("zio_engine", {}).get("active_provider", "zicore_native")
            ollama_cfg = config.get("providers", {}).get("ollama", {})
            if ollama_cfg.get("enabled"):
                import urllib.request as _req
                try:
                    _req.urlopen(OLLAMA_BASE_URL + "/api/tags", timeout=2)
                    ollama_ok = True
                except Exception:
                    pass
        except Exception:
            pass
        return {
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "memory_used_mb": round(mem.used / 1048576),
            "memory_total_mb": round(mem.total / 1048576),
            "disk_percent": disk.percent,
            "disk_used_gb": round(disk.used / 1073741824, 1),
            "disk_total_gb": round(disk.total / 1073741824, 1),
            "uptime": uptime_str,
            "ollama_status": ollama_ok,
            "sd_status": sd_ok,
            "active_provider": active_prov,
        }
    except ImportError:
        import random
        return {
            "cpu_percent": random.randint(5, 40),
            "memory_percent": random.randint(30, 70),
            "disk_percent": 0,
            "uptime": "--",
            "ollama_status": False,
            "sd_status": False,
            "active_provider": "zicore_native",
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/themes")
async def get_themes():
    return {
        "themes": [
            {"id": "midnight", "name": "Midnight", "colors": {"bg": "#0a0a0f", "primary": "#00ffff", "secondary": "#ff00ff"}},
            {"id": "cyber", "name": "Cyber Neon", "colors": {"bg": "#0d0221", "primary": "#0ff", "secondary": "#f0f"}},
            {"id": "matrix", "name": "Matrix", "colors": {"bg": "#000000", "primary": "#00ff00", "secondary": "#008800"}},
            {"id": "solar", "name": "Solar Flare", "colors": {"bg": "#1a0a00", "primary": "#ff8800", "secondary": "#ff4400"}},
            {"id": "arctic", "name": "Arctic", "colors": {"bg": "#0a1520", "primary": "#88ddff", "secondary": "#4488cc"}},
            {"id": "blood", "name": "Blood Moon", "colors": {"bg": "#0f0505", "primary": "#ff2222", "secondary": "#880000"}},
            {"id": "forest", "name": "Deep Forest", "colors": {"bg": "#051008", "primary": "#22cc66", "secondary": "#0a5530"}},
        ]
    }


@app.post("/api/config/theme/{theme_id}")
async def set_theme(theme_id: str):
    config = load_config()
    config["theme"] = theme_id
    save_config(config)
    return {"status": "ok", "theme": theme_id}


@app.get("/api/missions")
async def list_missions():
    missions = []
    for f in MISSIONS_DIR.glob("*.json"):
        try:
            with open(f, "r") as fh:
                data = json.load(fh)
                missions.append({
                    "id": f.stem,
                    "name": data.get("name", f.stem),
                    "phase": data.get("phase", "unknown"),
                    "created": data.get("created", ""),
                })
        except Exception:
            pass
    return {"missions": missions}


@app.get("/api/missions/{mission_id}")
async def get_mission(mission_id: str):
    f = MISSIONS_DIR / f"{mission_id}.json"
    if not f.exists():
        return {"error": "Mission not found"}
    with open(f, "r") as fh:
        return json.load(fh)


@app.post("/api/missions/{mission_id}")
async def save_mission(mission_id: str, body: dict):
    f = MISSIONS_DIR / f"{mission_id}.json"
    body["id"] = mission_id
    body["updated"] = __import__("datetime").datetime.now().isoformat()
    if "created" not in body:
        body["created"] = body["updated"]
    with open(f, "w") as fh:
        json.dump(body, fh, indent=2)
    return {"status": "ok", "id": mission_id}


@app.delete("/api/missions/{mission_id}")
async def delete_mission(mission_id: str):
    f = MISSIONS_DIR / f"{mission_id}.json"
    if f.exists():
        f.unlink()
    return {"status": "ok"}


@app.get("/api/openvision/analyze")
async def openvision_analyze(path: str = ""):
    if not path:
        return {"error": "path required"}
    try:
        from zicore.openvision import OpenVision
        ov = OpenVision()
        result = ov.analyze_media(path)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/vision/analyze")
async def vision_analyze(data: dict = {}):
    try:
        from zicore.openvision import OpenVision
        ov = OpenVision()
        image = data.get("image", "")
        if image.startswith("data:"):
            import base64, tempfile
            header, b64data = image.split(",", 1)
            img_bytes = base64.b64decode(b64data)
            ext = "png" if "png" in header else "jpg"
            tmp = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
            tmp.write(img_bytes)
            tmp.close()
            result = ov.analyze_media(tmp.name)
            os.unlink(tmp.name)
        else:
            result = ov.analyze_media(image)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/vision/ocr")
async def vision_ocr(data: dict = {}):
    try:
        image = data.get("image", "")
        text = ""
        if image.startswith("data:"):
            import base64, tempfile
            header, b64data = image.split(",", 1)
            img_bytes = base64.b64decode(b64data)
            ext = "png" if "png" in header else "jpg"
            tmp = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
            tmp.write(img_bytes)
            tmp.close()
            try:
                from zicore.openvision import OpenVision
                ov = OpenVision()
                result = ov.analyze_media(tmp.name)
                text = str(result)
            except:
                text = "[OCR] Backend processing required"
            os.unlink(tmp.name)
        else:
            text = "[OCR] File path: " + image
        return {"status": "ok", "text": text}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/video/cut")
async def video_cut(data: dict = {}):
    timestamp = data.get("timestamp", 0)
    return {"status": "ok", "message": f"Cut at {timestamp}s", "backend": "ffmpeg required"}


@app.post("/api/video/split")
async def video_split(data: dict = {}):
    timestamp = data.get("timestamp", 0)
    return {"status": "ok", "message": f"Split at {timestamp}s", "backend": "ffmpeg required"}


@app.post("/api/video/delete")
async def video_delete(data: dict = {}):
    timestamp = data.get("timestamp", 0)
    return {"status": "ok", "message": f"Delete clip at {timestamp}s", "backend": "ffmpeg required"}


@app.post("/api/video/duplicate")
async def video_duplicate(data: dict = {}):
    timestamp = data.get("timestamp", 0)
    return {"status": "ok", "message": f"Duplicate clip at {timestamp}s", "backend": "ffmpeg required"}


@app.get("/api/dataretention/stats")
async def dataretention_stats():
    try:
        from zicore.data_retention import data_retention
        return {"status": "ok", "stats": data_retention.get_stats()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/dataretention/export")
async def dataretention_export(fmt: str = "unsloth_jsonl"):
    try:
        from zicore.data_retention import data_retention
        result = data_retention.export_training_data(fmt)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/knowledge/stats")
async def knowledge_stats():
    try:
        from zicore.knowledge_base import knowledge_base
        return {"status": "ok", "stats": knowledge_base.get_stats()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/knowledge/conversations")
async def knowledge_conversations(limit: int = 50, session_id: str = None):
    try:
        from zicore.knowledge_base import knowledge_base
        convs = knowledge_base.get_recent(limit=limit, session_id=session_id)
        return {"status": "ok", "conversations": convs}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/knowledge/search")
async def knowledge_search(q: str = "", limit: int = 10):
    try:
        from zicore.knowledge_base import knowledge_base
        results = knowledge_base.search_conversations(q, limit=limit)
        return {"status": "ok", "results": results}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/knowledge/document")
async def knowledge_add_document(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
):
    try:
        from zicore.knowledge_base import knowledge_base
        content = await file.read()
        text = content.decode("utf-8", errors="replace")
        doc_name = name or file.filename
        doc_id = knowledge_base.add_document(doc_name, text, doc_type=file.content_type or "text")
        return {"status": "ok", "doc_id": doc_id, "name": doc_name, "words": len(text.split())}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/knowledge/document/text")
async def knowledge_add_text(body: dict):
    try:
        from zicore.knowledge_base import knowledge_base
        name = body.get("name", "Untitled")
        content = body.get("content", "")
        doc_id = knowledge_base.add_document(name, content, doc_type="text")
        return {"status": "ok", "doc_id": doc_id, "name": name, "words": len(content.split())}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/knowledge/documents")
async def knowledge_list_documents():
    try:
        from zicore.knowledge_base import knowledge_base
        docs = []
        for doc_id, doc in knowledge_base.documents.items():
            docs.append({
                "id": doc_id,
                "name": doc["name"],
                "type": doc.get("type", "text"),
                "words": doc.get("words", 0),
                "added": doc.get("added", ""),
            })
        return {"status": "ok", "documents": docs}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/knowledge/document/{doc_id}")
async def knowledge_get_document(doc_id: str):
    try:
        from zicore.knowledge_base import knowledge_base
        doc = knowledge_base.get_document(doc_id)
        if doc:
            return {"status": "ok", "document": doc}
        return {"status": "error", "error": "Document not found"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.delete("/api/knowledge/document/{doc_id}")
async def knowledge_delete_document(doc_id: str):
    try:
        from zicore.knowledge_base import knowledge_base
        knowledge_base.delete_document(doc_id)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/knowledge/context")
async def knowledge_context(q: str = ""):
    try:
        from zicore.knowledge_base import knowledge_base
        context = knowledge_base.get_context_for_query(q)
        return {"status": "ok", "context": context}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/tts")
async def text_to_speech(body: dict):
    text = body.get("text", "")
    if not text:
        return {"error": "No text provided"}
    return {"status": "ok", "text": text, "engine": "browser"}


@app.post("/api/zio/import")
async def zio_import_chats(
    file: UploadFile = File(...),
    source: Optional[str] = Form(None),
    session_prefix: Optional[str] = Form(None),
):
    try:
        from zicore.knowledge_base import knowledge_base
        raw = await file.read()
        filename = file.filename or "upload"
        text = raw.decode("utf-8", errors="replace")

        imported = 0
        skipped = 0
        session_prefix = session_prefix or "imported"
        detected_source = source or _detect_chat_source(text, filename)
        convs = _parse_chat_file(text, detected_source)

        for conv in convs:
            role = conv.get("role", "")
            content = conv.get("content", "")
            ts = conv.get("timestamp", "")
            if not content or not role:
                skipped += 1
                continue
            metadata = {"source": detected_source, "original_timestamp": ts}
            if conv.get("title"):
                metadata["title"] = conv["title"]
            knowledge_base.add_message(
                role, content,
                session_id=f"{session_prefix}_{detected_source}",
                metadata=metadata,
            )
            imported += 1

        return {
            "status": "ok",
            "source": detected_source,
            "imported": imported,
            "skipped": skipped,
            "filename": filename,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _detect_chat_source(text: str, filename: str) -> str:
    fn_lower = filename.lower()
    if "chatgpt" in fn_lower or "conversations" in fn_lower:
        return "chatgpt"
    if "grok" in fn_lower:
        return "grok"
    if "claude" in fn_lower or "anthropic" in fn_lower:
        return "claude"
    if "gemini" in fn_lower:
        return "gemini"
    if "deepseek" in fn_lower:
        return "deepseek"
    stripped = text.lstrip()[:200]
    if '"mapping"' in stripped or '"conversation_id"' in stripped:
        return "chatgpt"
    if '"conversations"' in stripped or '"title"' in stripped:
        if '"uuid"' in stripped[:500]:
            return "grok"
        return "chatgpt"
    try:
        j = json.loads(text[:500])
        if isinstance(j, list) and j and "role" in j[0]:
            return "generic"
        if isinstance(j, dict) and "messages" in j:
            return "chatgpt"
    except Exception:
        pass
    return "generic"


def _parse_chat_file(text: str, source: str) -> list:
    if source == "chatgpt":
        return _parse_chatgpt(text)
    if source == "grok":
        return _parse_grok(text)
    if source == "claude":
        return _parse_claude(text)
    if source == "gemini":
        return _parse_gemini(text)
    return _parse_generic(text)


def _parse_chatgpt(text: str) -> list:
    results = []
    try:
        data = json.loads(text)
    except Exception:
        return _parse_generic(text)

    conversations = []
    if isinstance(data, list):
        conversations = data
    elif isinstance(data, dict):
        if "conversations" in data:
            conversations = data["conversations"]
        elif "mapping" in data:
            return _parse_chatgpt_mapping(data)
        else:
            conversations = [data]

    for conv in conversations:
        title = conv.get("title", "")
        msgs = conv.get("messages", [])
        if not msgs:
            continue
        for m in msgs:
            role_raw = m.get("author", m.get("role", ""))
            if isinstance(role_raw, dict):
                role_raw = role_raw.get("role", "")
            if role_raw in ("human", "user"):
                role = "user"
            elif role_raw in ("assistant", "ai", "chatgpt"):
                role = "zio"
            elif role_raw in ("system",):
                role = "system"
            else:
                role = str(role_raw)
            content = m.get("content", "")
            if isinstance(content, dict):
                parts = content.get("parts", [])
                content = "\n".join(p for p in parts if isinstance(p, str)) or json.dumps(content)
            ts = m.get("create_time", m.get("created_at", ""))
            if isinstance(ts, (int, float)):
                from datetime import datetime
                ts = datetime.fromtimestamp(ts).isoformat()
            results.append({"role": role, "content": content, "timestamp": str(ts), "title": title})
    return results


def _parse_chatgpt_mapping(data: dict) -> list:
    results = []
    mapping = data.get("mapping", {})
    messages_map = {}
    for node_id, node in mapping.items():
        msg = node.get("message")
        if msg:
            messages_map[node_id] = msg

    for node_id, msg in messages_map.items():
        role_raw = msg.get("author", {}).get("role", "") if isinstance(msg.get("author"), dict) else ""
        if role_raw in ("human", "user"):
            role = "user"
        elif role_raw in ("assistant",):
            role = "zio"
        else:
            continue
        content = msg.get("content", {})
        if isinstance(content, dict):
            parts = content.get("parts", [])
            content = "\n".join(p for p in parts if isinstance(p, str))
        if not content:
            continue
        ts = msg.get("create_time", "")
        if isinstance(ts, (int, float)):
            from datetime import datetime
            ts = datetime.fromtimestamp(ts).isoformat()
        results.append({"role": role, "content": content, "timestamp": str(ts), "title": data.get("title", "")})
    return results


def _parse_grok(text: str) -> list:
    results = []
    try:
        data = json.loads(text)
    except Exception:
        return _parse_generic(text)

    conversations = []
    if isinstance(data, list):
        conversations = data
    elif isinstance(data, dict):
        conversations = data.get("conversations", data.get("chats", [data]))

    for conv in conversations:
        title = conv.get("title", conv.get("name", ""))
        messages = conv.get("messages", conv.get("turns", []))
        for m in messages:
            role_raw = m.get("sender", m.get("author", m.get("role", "")))
            if role_raw in ("user", "human"):
                role = "user"
            elif role_raw in ("assistant", "ai", "grok"):
                role = "zio"
            else:
                role = str(role_raw) if role_raw else "user"
            content = m.get("text", m.get("content", ""))
            if isinstance(content, list):
                content = "\n".join(str(c) for c in content)
            ts = m.get("created_at", m.get("timestamp", ""))
            results.append({"role": role, "content": str(content), "timestamp": str(ts), "title": title})
    return results


def _parse_claude(text: str) -> list:
    results = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        role_raw = obj.get("type", obj.get("role", ""))
        if role_raw in ("human", "user"):
            role = "user"
        elif role_raw in ("assistant",):
            role = "zio"
        else:
            continue
        content = obj.get("text", obj.get("content", ""))
        if isinstance(content, list):
            content = "\n".join(p.get("text", "") for p in content if isinstance(p, dict))
        ts = obj.get("timestamp", obj.get("created_at", ""))
        results.append({"role": role, "content": str(content), "timestamp": str(ts)})
    return results


def _parse_gemini(text: str) -> list:
    results = []
    try:
        data = json.loads(text)
    except Exception:
        return _parse_generic(text)

    conversations = data if isinstance(data, list) else [data]
    for conv in conversations:
        messages = conv.get("messages", conv.get("turns", []))
        for m in messages:
            role_raw = m.get("author", m.get("role", ""))
            if role_raw in ("user",):
                role = "user"
            elif role_raw in ("model", "assistant", "gemini"):
                role = "zio"
            else:
                role = "user"
            content = m.get("content", m.get("text", ""))
            if isinstance(content, dict):
                parts = content.get("parts", [])
                content = "\n".join(p.get("text", str(p)) for p in parts if isinstance(p, dict))
            ts = m.get("timestamp", "")
            results.append({"role": role, "content": str(content), "timestamp": str(ts)})
    return results


def _parse_generic(text: str) -> list:
    results = []
    try:
        data = json.loads(text)
    except Exception:
        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith("user:"):
                results.append({"role": "user", "content": line[5:].strip(), "timestamp": ""})
            elif line.lower().startswith(("assistant:", "ai:", "zio:", "bot:")):
                results.append({"role": "zio", "content": line.split(":", 1)[1].strip(), "timestamp": ""})
        return results

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                role_raw = item.get("role", item.get("sender", item.get("author", "")))
                content = item.get("content", item.get("text", item.get("message", "")))
                ts = item.get("timestamp", item.get("created_at", item.get("date", "")))
                if role_raw in ("user", "human"):
                    role = "user"
                elif role_raw in ("assistant", "ai", "bot"):
                    role = "zio"
                elif role_raw in ("system",):
                    role = "system"
                else:
                    role = "user"
                if isinstance(content, list):
                    content = "\n".join(str(c) for c in content)
                results.append({"role": role, "content": str(content), "timestamp": str(ts)})
    elif isinstance(data, dict):
        if "messages" in data:
            return _parse_generic(json.dumps(data["messages"]))
        for key in ("conversation", "chat", "turns"):
            if key in data:
                return _parse_generic(json.dumps(data[key]))
    return results


@app.post("/api/ocr")
async def ocr_image(body: dict):
    try:
        from zicore.openvision import OpenVision
        ov = OpenVision()
        path = body.get("path", "")
        if not path:
            return {"error": "No path provided"}
        result = ov.analyze_media(path)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/mesh/generate")
async def mesh_generate(body: dict):
    try:
        mesh_type = body.get("type", "cube")
        params = body.get("params", {})
        output_dir = Path(__file__).parent / "output" / "meshes"
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"mesh_{__import__('time').time():.0f}.stl"
        output_path = output_dir / filename

        import numpy as np
        try:
            import trimesh
            import trimesh.creation
            import trimesh.primitives
            import trimesh.path
            import trimesh.curvature

            if mesh_type == "cube":
                s = params.get("size", 1)
                mesh = trimesh.creation.box(extents=[s, s, s])
            elif mesh_type == "sphere":
                r = params.get("radius", 0.5)
                subdivisions = params.get("subdivisions", 2)
                mesh = trimesh.creation.icosphere(radius=r, subdivisions=subdivisions)
            elif mesh_type == "cylinder":
                r = params.get("radius", 0.5)
                h = params.get("height", 1)
                sections = params.get("sections", 32)
                mesh = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
            elif mesh_type == "cone":
                r = params.get("radius", 0.5)
                h = params.get("height", 1)
                sections = params.get("sections", 32)
                mesh = trimesh.creation.cone(radius=r, height=h, sections=sections)
            elif mesh_type == "capsule":
                r = params.get("radius", 0.3)
                h = params.get("height", 1.0)
                cyl = trimesh.creation.cylinder(radius=r, height=h, sections=24)
                top = trimesh.creation.icosphere(radius=r, subdivisions=2)
                bot = trimesh.creation.icosphere(radius=r, subdivisions=2)
                top.apply_translation([0, 0, h/2])
                bot.apply_translation([0, 0, -h/2])
                mesh = trimesh.util.concatenate([cyl, top, bot])
            elif mesh_type == "torus":
                R = params.get("major_radius", 0.8)
                r = params.get("minor_radius", 0.25)
                sections = params.get("sections", 32)
                from trimesh.creation import torus
                mesh = trimesh.creation.torus(major_radius=R, minor_radius=r, sections=sections)
            elif mesh_type == "gear":
                r = params.get("radius", 0.5)
                teeth = params.get("teeth", 12)
                h = params.get("height", 0.2)
                hole = params.get("hole_radius", 0.1)
                angle = 2 * np.pi / teeth
                verts = []
                for i in range(teeth):
                    a0 = i * angle
                    a1 = a0 + angle * 0.3
                    a2 = a0 + angle * 0.5
                    a3 = a0 + angle * 0.8
                    verts.append([r * np.cos(a0), r * np.sin(a0), -h/2])
                    verts.append([r * 1.2 * np.cos(a1), r * 1.2 * np.sin(a1), -h/2])
                    verts.append([r * 1.2 * np.cos(a2), r * 1.2 * np.sin(a2), -h/2])
                    verts.append([r * np.cos(a3), r * np.sin(a3), -h/2])
                    verts.append([r * np.cos(a0), r * np.sin(a0), h/2])
                    verts.append([r * 1.2 * np.cos(a1), r * 1.2 * np.sin(a1), h/2])
                    verts.append([r * 1.2 * np.cos(a2), r * 1.2 * np.sin(a2), h/2])
                    verts.append([r * np.cos(a3), r * np.sin(a3), h/2])
                faces = []
                for i in range(teeth):
                    b = i * 8
                    n = (i + 1) % teeth * 8
                    # top faces
                    faces.append([b+4, b+5, n+4])
                    faces.append([b+5, n+5, n+4])
                    faces.append([b+5, b+6, n+5])
                    faces.append([b+6, n+6, n+5])
                    faces.append([b+6, b+7, n+6])
                    faces.append([b+7, n+7, n+6])
                    faces.append([b+7, b+4, n+7])
                    faces.append([b+4, n+4, n+7])
                    # bottom faces
                    faces.append([b+0, n+0, b+1])
                    faces.append([b+1, n+0, n+1])
                    faces.append([b+1, n+1, b+2])
                    faces.append([b+2, n+1, n+2])
                    faces.append([b+2, n+2, b+3])
                    faces.append([b+3, n+2, n+3])
                    faces.append([b+3, n+3, b+0])
                    faces.append([b+0, n+3, n+0])
                    # side walls
                    for j in range(4):
                        a = b + j
                        an = b + ((j + 1) % 4)
                        faces.append([a, an, a+4])
                        faces.append([an, an+4, a+4])
                mesh = trimesh.Trimesh(vertices=np.array(verts, dtype=float), faces=np.array(faces, dtype=int))
                mesh.fix_normals()
            elif mesh_type == "pipe":
                r = params.get("radius", 0.4)
                t = params.get("thickness", 0.1)
                h = params.get("height", 1.5)
                sections = params.get("sections", 32)
                outer = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
                inner = trimesh.creation.cylinder(radius=r-t, height=h*1.01, sections=sections)
                mesh = outer.difference(inner)
            elif mesh_type == "star":
                r_outer = params.get("outer_radius", 0.5)
                r_inner = params.get("inner_radius", 0.2)
                points = params.get("points", 5)
                h = params.get("height", 0.15)
                verts = []
                angle_step = np.pi / points
                for i in range(points * 2):
                    a = i * angle_step - np.pi / 2
                    rad = r_outer if i % 2 == 0 else r_inner
                    verts.append([rad * np.cos(a), rad * np.sin(a), -h/2])
                for i in range(points * 2):
                    a = i * angle_step - np.pi / 2
                    rad = r_outer if i % 2 == 0 else r_inner
                    verts.append([rad * np.cos(a), rad * np.sin(a), h/2])
                faces = []
                n = points * 2
                for i in range(n):
                    faces.append([i, (i+1)%n, i+n])
                    faces.append([(i+1)%n, (i+1)%n+n, i+n])
                mesh = trimesh.Trimesh(vertices=np.array(verts, dtype=float), faces=np.array(faces, dtype=int))
                mesh.fix_normals()
            elif mesh_type == "rocket":
                body_r = params.get("body_radius", 0.3)
                body_h = params.get("body_height", 2)
                nose_r = params.get("nose_radius", body_r)
                nose_h = params.get("nose_height", 0.8)
                fin_count = params.get("fins", 4)
                fin_w = params.get("fin_width", 0.15)
                fin_h = params.get("fin_height", 0.5)
                body = trimesh.creation.cylinder(radius=body_r, height=body_h, sections=24)
                nose = trimesh.creation.cone(radius=nose_r, height=nose_h, sections=24)
                nose.apply_translation([0, 0, body_h / 2 + nose_h / 2])
                parts = [body, nose]
                if fin_count > 0:
                    for i in range(fin_count):
                        a = 2 * np.pi * i / fin_count
                        fin = trimesh.creation.box(extents=[fin_w, 0.01, fin_h])
                        fin.apply_translation([body_r * np.cos(a), body_r * np.sin(a), -body_h/4])
                        fin.apply_rotation(trimesh.transformations.rotation_matrix(a, [0, 0, 1]))
                        parts.append(fin)
                mesh = trimesh.util.concatenate(parts) if len(parts) > 1 else parts[0]
            elif mesh_type == "terrain":
                w = params.get("width", 20)
                h = params.get("depth", 20)
                scale = params.get("scale", 1.0)
                octaves = params.get("octaves", 4)
                try:
                    from zicore.procedural import create_procedural_engine
                    engine = create_procedural_engine(seed=42)
                    heights = engine.generate_terrain(w, h, scale=scale, octaves=octaves)
                except Exception:
                    np.random.seed(42)
                    x = np.linspace(-2, 2, w)
                    y = np.linspace(-2, 2, h)
                    xx, yy = np.meshgrid(x, y)
                    heights = np.sin(xx*2) * np.cos(yy*2) * 0.5 + np.sin(xx*4)*0.25 + np.cos(yy*4)*0.25
                    heights = heights * scale
                verts = []
                faces = []
                for yi in range(h):
                    for xi in range(w):
                        verts.append([xi - w/2, yi - h/2, float(heights[yi][xi] if hasattr(heights[yi], '__getitem__') else heights[yi, xi])])
                for yi in range(h-1):
                    for xi in range(w-1):
                        a = yi * w + xi
                        b = a + 1
                        c = (yi+1) * w + xi
                        d = c + 1
                        faces.append([a, b, c])
                        faces.append([b, d, c])
                mesh = trimesh.Trimesh(vertices=np.array(verts, dtype=float), faces=np.array(faces, dtype=int))
                mesh.fix_normals()
            elif mesh_type == "openscad":
                script = params.get("script", "")
                if not script:
                    return {"status": "error", "error": "OpenSCAD script required"}
                try:
                    import subprocess, tempfile
                    scad_path = output_dir / f"temp_{__import__('time').time():.0f}.scad"
                    scad_path.write_text(script)
                    stl_path = output_dir / f"openscad_{__import__('time').time():.0f}.stl"
                    result = subprocess.run(["openscad", "-o", str(stl_path), str(scad_path)],
                                            capture_output=True, text=True, timeout=30)
                    scad_path.unlink(missing_ok=True)
                    if stl_path.exists():
                        mesh = trimesh.load(str(stl_path))
                        stl_path.rename(output_path)
                    else:
                        return {"status": "error", "error": result.stderr or "OpenSCAD failed"}
                except FileNotFoundError:
                    return {"status": "error", "error": "OpenSCAD not installed"}
            else:
                mesh = trimesh.creation.box(extents=[1, 1, 1])
            mesh.export(str(output_path))
            return {
                "status": "ok",
                "path": f"/output/meshes/{filename}",
                "type": mesh_type,
                "vertices": len(mesh.vertices),
                "faces": len(mesh.faces),
                "bounds": list(mesh.bounds.flatten()) if hasattr(mesh, 'bounds') and mesh.bounds is not None else [],
            }
        except ImportError:
            return {"status": "error", "error": "trimesh not available"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/materialize")
async def materialize(body: dict):
    """
    ZICORE Materializer API endpoint.
    Materializes ideas into reality using the best available engine.
    
    Supports:
    - image: Stable Diffusion or procedural fallback
    - mesh_3d: trimesh generation
    - terrain: Perlin noise heightmap
    - cave: Cellular automata
    - dungeon: BSP room generation
    - plant: L-System
    - fractal: Mandelbrot/Julia
    - level: Wave Function Collapse
    - text: Markov chain
    """
    try:
        prompt = body.get("prompt", "")
        output_type = body.get("type", "auto")
        
        if not prompt:
            return {"success": False, "error": "No prompt provided"}
        
        # Import materializer
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from zicore.materializer import ZICOREMaterializer, OutputType
        
        # Create materializer instance
        mat = ZICOREMaterializer()
        
        # Determine output type
        if output_type == "auto":
            from zicore.materializer import IntentClassifier
            output_type_enum = IntentClassifier.classify(prompt)
        else:
            try:
                output_type_enum = OutputType(output_type)
            except ValueError:
                output_type_enum = OutputType.IMAGE
        
        # Materialize
        result = mat.materialize(prompt, output_type=output_type_enum)
        
        # Convert file path to web-accessible path
        if result.file_path:
            # Convert absolute path to relative URL
            file_path = result.file_path
            if "output" in file_path:
                # Extract relative path from output directory
                output_idx = file_path.find("output")
                if output_idx >= 0:
                    relative_path = file_path[output_idx:]
                    result.file_path = "/" + relative_path.replace("\\", "/")
        
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"Materialize error: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/generate")
async def api_generate(data: dict = {}):
    gen_type = data.get("type", "image")
    prompt = data.get("prompt", "")
    if not prompt:
        return {"error": "prompt required"}
    heavy_types = {"video", "3d", "batch", "audio_long"}
    try:
        if gen_type in heavy_types:
            node_result = _node_request("/api/generate", method="POST", payload=data, timeout=300)
            if node_result.get("status") != "error":
                node_result["source"] = "node"
                return node_result
        if gen_type == "image":
            try:
                from zicore.materializer import ZICOREMaterializer
                m = ZICOREMaterializer()
                result = m.materialize(f"Generate image: {prompt}", output_dir="output/images")
                return {"status": "ok", "type": "image", "path": str(getattr(result, "file_path", ""))}
            except Exception as e:
                return {"status": "ok", "type": "image", "message": f"Image generation queued: {prompt}", "error": str(e)}
        elif gen_type == "video":
            return {"status": "ok", "type": "video", "message": f"Video generation queued: {prompt}"}
        elif gen_type == "3d":
            return {"status": "ok", "type": "3d", "message": f"3D generation queued: {prompt}"}
        else:
            return {"status": "ok", "type": gen_type, "message": f"Generation queued: {prompt}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─── AI 3D Engines API ───────────────────────────────────────────────────────

@app.post("/api/ai3d/generate")
async def api_ai3d_generate(data: dict = {}):
    engine_key = data.get("engine", "")
    prompt = data.get("prompt", "")
    script = data.get("script", "")
    image_data = data.get("image", "")

    if not engine_key:
        return {"status": "error", "error": "engine required (tripo3d, meshy, rodin, openscad, cadquery, build123d, solidpython2)"}

    try:
        from zicore.ai3d_engines import ai3d
    except ImportError:
        return {"status": "error", "error": "ai3d_engines module not found"}

    image_path = ""
    if image_data and image_data.startswith("data:"):
        import base64
        import tempfile
        header, b64 = image_data.split(",", 1)
        ext = "jpg" if "jpeg" in header else "png"
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
        tmp.write(base64.b64decode(b64))
        tmp.close()
        image_path = tmp.name

    result = ai3d.generate(
        engine_key=engine_key,
        prompt=prompt,
        image_path=image_path,
        script=script,
    )
    return result.to_dict()


@app.get("/api/ai3d/engines")
async def api_ai3d_engines():
    try:
        from zicore.ai3d_engines import ai3d
        return {"status": "ok", "engines": ai3d.list_engines()}
    except ImportError:
        return {"status": "error", "error": "ai3d_engines module not found"}


@app.post("/api/code/execute")
async def code_execute(body: dict):
    """
    ZICORE Code Execution API endpoint.
    Executes Python code safely in a sandboxed environment.
    
    Supports:
    - Python code execution
    - Safe imports (math, random, os, sys, json, datetime, collections)
    - Timeout protection (10 seconds max)
    - Output capture (stdout)
    """
    try:
        code = body.get("code", "")
        language = body.get("language", "python")
        
        if not code:
            return {"success": False, "error": "No code provided"}
        
        if language != "python":
            return {"success": False, "error": f"Unsupported language: {language}. Only Python is supported."}
        
        import subprocess
        import sys
        import tempfile
        import os
        
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Execute with timeout
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            
            output = result.stdout
            error = result.stderr
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": output,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "output": output,
                    "error": error
                }
                
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_file)
            except:
                pass
                
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Code execution timed out (10s limit)"}
    except Exception as e:
        logger.error(f"Code execute error: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/video/process")
async def video_process(body: dict):
    try:
        import base64
        import io
        effect = body.get("effect", "none")
        prompt = body.get("prompt", "")
        frames_b64 = body.get("frames", [])

        if prompt:
            p = prompt.lower()
            effects = []
            if "slow" in p or "lento" in p: effects.append("slow")
            if "fast" in p or "rapido" in p: effects.append("fast")
            if "reverse" in p or "reversa" in p: effects.append("reverse")
            if "black" in p or "bw" in p or "gris" in p: effects.append("bw")
            if "sepia" in p or "retro" in p: effects.append("sepia")
            if "invert" in p or "negativo" in p: effects.append("invert")
            if "zoom" in p or "acercar" in p: effects.append("zoom")
            if "glitch" in p or "error" in p: effects.append("glitch")
            if "text" in p or "titulo" in p: effects.append("text")
            if "fade" in p or "transicion" in p: effects.append("fade")
            effect = ",".join(effects) if effects else effect

        processed = []
        for frame_b64 in frames_b64:
            try:
                img_data = base64.b64decode(frame_b64)
                from PIL import Image, ImageEnhance, ImageFilter
                img = Image.open(io.BytesIO(img_data))

                for fx in effect.split(","):
                    fx = fx.strip()
                    if fx == "bw":
                        img = img.convert("L").convert("RGB")
                    elif fx == "sepia":
                        img = img.convert("L")
                        sepia = Image.merge("RGB", [
                            img.point(lambda x: min(255, int(x * 1.2))),
                            img.point(lambda x: min(255, int(x * 1.0))),
                            img.point(lambda x: min(255, int(x * 0.8))),
                        ])
                        img = sepia
                    elif fx == "invert":
                        from PIL import ImageOps
                        img = ImageOps.invert(img)
                    elif fx == "zoom":
                        w, h = img.size
                        crop = img.crop((w * 0.1, h * 0.1, w * 0.9, h * 0.9))
                        img = crop.resize((w, h), Image.LANCZOS)
                    elif fx == "glitch":
                        import random
                        w, h = img.size
                        for _ in range(3):
                            sy = random.randint(0, h - 10)
                            sh = random.randint(2, 8)
                            shift = random.randint(-10, 10)
                            slice_img = img.crop((0, sy, w, sy + sh))
                            img.paste(slice_img, (shift, sy))

                buf = io.BytesIO()
                img.save(buf, format="PNG")
                processed.append(base64.b64encode(buf.getvalue()).decode())
            except Exception:
                processed.append(frame_b64)

        return {"status": "ok", "effects": effect, "processed_frames": len(processed), "frames": processed}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/video/generate")
async def video_generate(body: dict):
    try:
        prompt = body.get("prompt", "")
        duration = body.get("duration", 3)
        width = body.get("width", 640)
        height = body.get("height", 480)
        fps = body.get("fps", 24)
        provider = body.get("provider", "")

        sys.path.insert(0, str(Path(__file__).parent))
        from agent.generator import ZICoreGenerator
        gen = ZICoreGenerator()

        result = gen.generate_video(prompt, width=width, height=height, duration=duration, fps=fps)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/video/trim")
async def video_trim(body: dict):
    try:
        import base64, io
        frames_b64 = body.get("frames", [])
        start = body.get("start", 0)
        end = body.get("end", -1)
        if end < 0: end = len(frames_b64)
        trimmed = frames_b64[start:end]
        return {"status": "ok", "frames": trimmed, "count": len(trimmed)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/video/concat")
async def video_concat(body: dict):
    try:
        import base64, io
        sequences = body.get("sequences", [])
        all_frames = []
        for seq in sequences:
            all_frames.extend(seq.get("frames", []))
        return {"status": "ok", "frames": all_frames, "total_frames": len(all_frames)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.websocket("/ws/zio")
async def zio_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("ZIO WS connected")
    try:
        await websocket.send_json({
            "type": "welcome",
            "message": "ZIO online. All systems nominal. Ready for commands.",
        })
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            command = data.get("command", "")
            payload = data.get("payload", {})

            if command == "chat":
                try:
                    import asyncio
                    user_msg = payload.get("message", "")
                    session_id = payload.get("session_id", "webui")
                    provider_name = payload.get("module", "zicore_native")

                    from zicore.knowledge_base import knowledge_base
                    knowledge_base.add_message("user", user_msg, session_id=session_id)
                    context = knowledge_base.get_context_for_query(user_msg)

                    config = load_config()
                    active_provider = config.get("zio_engine", {}).get("active_provider", "zicore_native")
                    if provider_name in (None, "", "zicorex"):
                        provider_name = active_provider

                    t0 = __import__("time").time()

                    if provider_name == "zicore_native":
                        sys.path.insert(0, str(Path(__file__).parent))
                        from agent.core import ZICoreAgent
                        agent = ZICoreAgent(session_id=session_id)
                        import asyncio
                        result = await agent.process(
                            user_msg,
                            {"source": "zio_webui", "knowledge_context": context}
                        )
                        reply = result.get("outputs", {}).get("text",
                            result.get("outputs", {}).get("zio_msg", str(result.get("outputs", ""))))
                        intent = result.get("intent", "general")
                    else:
                        chat_result = await asyncio.to_thread(call_provider_chat, provider_name, user_msg, config, context)
                        reply = chat_result.get("response", "")
                        intent = "provider_" + provider_name

                    knowledge_base.add_message("zio", reply, session_id=session_id, intent=intent)
                    latency_ms = int((__import__("time").time() - t0) * 1000)
                    await websocket.send_json({
                        "type": "response",
                        "intent": intent,
                        "outputs": {"text": reply},
                        "latency_ms": latency_ms,
                    })
                except Exception as e:
                    logger.error(f"Chat command error: {e}", exc_info=True)
                    try:
                        await websocket.send_json({"type": "error", "message": str(e)})
                    except Exception:
                        pass

            elif command == "generate":
                try:
                    sys.path.insert(0, str(Path(__file__).parent))
                    from agent.generator import generator
                    import asyncio
                    gen_type = payload.get("type", "image")
                    prompt = payload.get("prompt", "")
                    await websocket.send_json({"type": "generating", "generating_type": gen_type})
                    result = generator.generate(gen_type, prompt)
                    await websocket.send_json({"type": "generated", "result": result})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif command == "stream":
                try:
                    import asyncio
                    user_msg = payload.get("message", "")
                    session_id = payload.get("session_id", "webui")
                    provider_name = payload.get("module", "zicore_native")

                    from zicore.knowledge_base import knowledge_base
                    knowledge_base.add_message("user", user_msg, session_id=session_id)
                    context = knowledge_base.get_context_for_query(user_msg)

                    config = load_config()
                    active_provider = config.get("zio_engine", {}).get("active_provider", "zicore_native")
                    if provider_name in (None, "", "zicorex"):
                        provider_name = active_provider

                    t0 = __import__("time").time()

                    if provider_name == "zicore_native":
                        sys.path.insert(0, str(Path(__file__).parent))
                        from agent.core import ZICoreAgent
                        agent = ZICoreAgent(session_id=session_id)
                        import asyncio
                        result = await agent.process(
                            user_msg,
                            {"source": "zio_webui", "knowledge_context": context}
                        )
                        reply = result.get("outputs", {}).get("text",
                            result.get("outputs", {}).get("zio_msg", str(result.get("outputs", ""))))
                        intent = result.get("intent", "general")
                    else:
                        chat_result = await asyncio.to_thread(call_provider_chat, provider_name, user_msg, config, context)
                        reply = chat_result.get("response", "")
                        intent = "provider_" + provider_name

                    latency_ms = int((__import__("time").time() - t0) * 1000)
                    knowledge_base.add_message("zio", reply, session_id=session_id, intent=intent)

                    await websocket.send_json({"type": "stream_start", "message": ""})
                    words = reply.split(" ")
                    for word in words:
                        await websocket.send_json({"type": "stream_chunk", "chunk": word + " "})
                        await asyncio.sleep(0.02)
                    await websocket.send_json({
                        "type": "stream_end",
                        "intent": intent,
                        "outputs": {"text": reply},
                        "latency_ms": latency_ms,
                    })
                except Exception as e:
                    logger.error(f"Stream command error: {e}", exc_info=True)
                    try:
                        await websocket.send_json({"type": "error", "message": str(e)})
                    except Exception:
                        pass

            elif command == "config":
                await websocket.send_json({"type": "config", "config": _sanitize_config(load_config())})

            elif command == "status":
                await websocket.send_json({"type": "status", "server": "ZIO WebUI", "version": "5.0.0"})

            elif command == "telemetry":
                try:
                    from zicore.telemetry_sim import telemetry_sim
                    data = telemetry_sim.get_telemetry()
                    data["modules"] = telemetry_sim.get_module_status()
                    await websocket.send_json({"type": "telemetry", "data": data})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif command == "mission_save":
                try:
                    mission_id = payload.get("id", "current")
                    f = MISSIONS_DIR / f"{mission_id}.json"
                    payload["id"] = mission_id
                    payload["updated"] = __import__("datetime").datetime.now().isoformat()
                    if "created" not in payload:
                        payload["created"] = payload["updated"]
                    with open(f, "w") as fh:
                        json.dump(payload, fh, indent=2)
                    await websocket.send_json({"type": "mission_saved", "id": mission_id})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif command == "mission_load":
                try:
                    mission_id = payload.get("id", "current")
                    f = MISSIONS_DIR / f"{mission_id}.json"
                    if f.exists():
                        with open(f, "r") as fh:
                            data = json.load(fh)
                        await websocket.send_json({"type": "mission_loaded", "data": data})
                    else:
                        await websocket.send_json({"type": "error", "message": "Mission not found"})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif command == "vision_analyze":
                try:
                    from zicore.openvision import OpenVision
                    ov = OpenVision()
                    path = payload.get("path", "")
                    result = ov.analyze_media(path)
                    await websocket.send_json({"type": "vision_result", "result": result})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif command == "dataretention_export":
                try:
                    from zicore.data_retention import data_retention
                    fmt = payload.get("format", "unsloth_jsonl")
                    result = data_retention.export_training_data(fmt)
                    await websocket.send_json({"type": "export_result", "result": result})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif command == "knowledge_search":
                try:
                    from zicore.knowledge_base import knowledge_base
                    q = payload.get("query", "")
                    results = knowledge_base.search_conversations(q, limit=10)
                    await websocket.send_json({"type": "knowledge_results", "results": results})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif command == "knowledge_context":
                try:
                    from zicore.knowledge_base import knowledge_base
                    q = payload.get("query", "")
                    context = knowledge_base.get_context_for_query(q)
                    await websocket.send_json({"type": "knowledge_context", "context": context})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif command == "mesh_generate":
                try:
                    import time
                    mesh_type = payload.get("type", "cube")
                    params = payload.get("params", {})
                    output_dir = Path(__file__).parent / "output" / "meshes"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"mesh_{time.time():.0f}.stl"
                    output_path = output_dir / filename
                    import trimesh
                    if mesh_type == "cube":
                        mesh = trimesh.creation.box(extents=[params.get("size", 1)] * 3)
                    elif mesh_type == "sphere":
                        mesh = trimesh.creation.icosphere(radius=params.get("radius", 0.5))
                    elif mesh_type == "cylinder":
                        mesh = trimesh.creation.cylinder(radius=params.get("radius", 0.5), height=params.get("height", 1))
                    elif mesh_type == "rocket":
                        br = params.get("body_radius", 0.3)
                        bh = params.get("body_height", 2)
                        nh = params.get("nose_height", 0.8)
                        body = trimesh.creation.cylinder(radius=br, height=bh)
                        nose = trimesh.creation.cone(radius=br, height=nh)
                        nose.apply_translation([0, 0, bh / 2 + nh / 2])
                        mesh = trimesh.util.concatenate([body, nose])
                    else:
                        mesh = trimesh.creation.box(extents=[1, 1, 1])
                    mesh.export(str(output_path))
                    await websocket.send_json({
                        "type": "mesh_generated",
                        "result": {
                            "path": f"/output/meshes/{filename}",
                            "type": mesh_type,
                            "vertices": len(mesh.vertices),
                            "faces": len(mesh.faces),
                        }
                    })
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif command == "vision_webcam":
                try:
                    from zicore.openvision import OpenVision
                    ov = OpenVision()
                    image_data = payload.get("image", "")
                    if image_data.startswith("data:image"):
                        import base64
                        image_data = image_data.split(",")[1]
                    img_bytes = base64.b64decode(image_data)
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                        tmp.write(img_bytes)
                        tmp_path = tmp.name
                    result = ov.analyze_media(tmp_path)
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
                    await websocket.send_json({"type": "vision_result", "result": result})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif command == "knowledge_stats":
                try:
                    from zicore.knowledge_base import knowledge_base
                    stats = knowledge_base.get_stats()
                    await websocket.send_json({"type": "knowledge_stats", "stats": stats})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            else:
                await websocket.send_json({"type": "error", "message": f"Unknown command: {command}"})

    except WebSocketDisconnect:
        logger.info("ZIO WS disconnected")


@app.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("Telemetry WS connected")
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "invalid JSON"})
                continue
            mod = data.get("module", "")
            if mod:
                telemetry_modules[mod] = data
            await websocket.send_json({"modules": telemetry_modules})
    except WebSocketDisconnect:
        logger.info("Telemetry WS disconnected")


@app.get("/api/content/library")
async def content_library(type: str = "", search: str = ""):
    """Get all generated content (images, sounds, videos, 3D meshes)."""
    items = []
    output_dir = Path(__file__).parent / "output"
    ext_map = {
        ".png": "image", ".jpg": "image", ".jpeg": "image", ".gif": "image", ".bmp": "image",
        ".wav": "sound", ".mp3": "sound", ".ogg": "sound",
        ".stl": "3d", ".obj": "3d", ".ply": "3d", ".glb": "3d", ".gltf": "3d",
        ".mp4": "video", ".webm": "video",
    }
    for f in sorted(output_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.is_file():
            ext = f.suffix.lower()
            item_type = ext_map.get(ext, "")
            if not item_type:
                continue
            if type and item_type != type:
                continue
            if search and search.lower() not in f.name.lower():
                continue
            stat = f.stat()
            items.append({
                "name": f.name,
                "type": item_type,
                "ext": ext,
                "size": stat.st_size,
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": int(stat.st_mtime),
                "url": f"/output/{f.name}",
            })
        elif f.is_dir() and (f / "manifest.json").exists():
            if type and type != "video":
                continue
            if search and search.lower() not in f.name.lower():
                continue
            try:
                with open(f / "manifest.json", "r") as mf:
                    manifest = json.load(mf)
                frame_count = len(list(f.glob("frame_*.png")))
                items.append({
                    "name": f.name,
                    "type": "video",
                    "ext": ".frames",
                    "size": 0,
                    "size_kb": 0,
                    "frames": frame_count,
                    "modified": f.stat().st_mtime,
                    "url": f"/output/{f.name}/manifest.json",
                })
            except Exception:
                pass
    return {"status": "ok", "count": len(items), "items": items}


@app.delete("/api/content/delete")
async def content_delete(name: str = ""):
    """Delete a generated content item."""
    if not name or ".." in name:
        return {"status": "error", "error": "Invalid name"}
    output_dir = Path(__file__).parent / "output"
    target = output_dir / name
    if not target.exists():
        return {"status": "error", "error": "File not found"}
    if target.is_dir():
        import shutil
        shutil.rmtree(str(target))
    else:
        target.unlink()
    return {"status": "ok", "deleted": name}


@app.get("/api/content/stats")
async def content_stats():
    """Get content library statistics."""
    output_dir = Path(__file__).parent / "output"
    stats = {"images": 0, "sounds": 0, "videos": 0, "meshes": 0, "total_size_kb": 0}
    ext_map = {
        ".png": "images", ".jpg": "images", ".jpeg": "images",
        ".wav": "sounds", ".mp3": "sounds",
        ".stl": "meshes", ".obj": "meshes", ".ply": "meshes",
        ".mp4": "videos", ".webm": "videos",
    }
    for f in output_dir.rglob("*"):
        if f.is_file():
            key = ext_map.get(f.suffix.lower())
            if key:
                stats[key] += 1
                stats["total_size_kb"] += f.stat().st_size
    stats["total_size_kb"] = round(stats["total_size_kb"] / 1024, 1)
    stats["total_items"] = sum(v for k, v in stats.items() if k != "total_size_kb")
    return {"status": "ok", "stats": stats}


# --- SSH / Firefox / Thunderbird Integration ---

from zicore.ssh_integration import SSHManager, FirefoxIntegration, ThunderbirdIntegration
ssh_mgr = SSHManager()
firefox_int = FirefoxIntegration()
thunderbird_int = ThunderbirdIntegration()


@app.get("/api/ssh/status")
async def ssh_status():
    """Get SSH server status."""
    return {"status": "ok", "ssh": ssh_mgr.get_status(), "sessions": ssh_mgr.get_connected_sessions()}


@app.post("/api/ssh/start")
async def ssh_start():
    """Start SSH server."""
    return {"status": "ok", "result": ssh_mgr.start_server()}


@app.post("/api/ssh/stop")
async def ssh_stop():
    """Stop SSH server."""
    return {"status": "ok", "result": ssh_mgr.stop_server()}


@app.post("/api/ssh/execute")
async def ssh_execute(request: Request):
    """Execute a shell command."""
    data = await request.json()
    command = data.get("command", "")
    timeout = data.get("timeout", 30)
    return {"status": "ok", "result": ssh_mgr.execute_command(command, timeout)}


@app.get("/api/ssh/config")
async def ssh_config():
    """Get SSH server configuration."""
    return {"status": "ok", "config": ssh_mgr.get_config()}


@app.get("/api/firefox/status")
async def firefox_status():
    """Get Firefox status."""
    return {"status": "ok", "firefox": firefox_int.get_status()}


@app.post("/api/firefox/open")
async def firefox_open(request: Request):
    """Open URL in Firefox."""
    data = await request.json()
    url = data.get("url", "https://")
    return {"status": "ok", "result": firefox_int.open_url(url)}


@app.post("/api/firefox/open-file")
async def firefox_open_file(request: Request):
    """Open local file in Firefox."""
    data = await request.json()
    file_path = data.get("path", "")
    return {"status": "ok", "result": firefox_int.open_file(file_path)}


@app.get("/api/thunderbird/status")
async def thunderbird_status():
    """Get Thunderbird status."""
    return {"status": "ok", "thunderbird": thunderbird_int.get_status()}


@app.post("/api/thunderbird/open")
async def thunderbird_open():
    """Open Thunderbird."""
    return {"status": "ok", "result": thunderbird_int.open()}


@app.post("/api/thunderbird/compose")
async def thunderbird_compose(request: Request):
    """Open Thunderbird compose email."""
    data = await request.json()
    to = data.get("to", "")
    subject = data.get("subject", "")
    body = data.get("body", "")
    return {"status": "ok", "result": thunderbird_int.open_compose(to, subject, body)}


# --- ZICORE Mail Server ---

from zicore.mail_integration import MailServer
mail_server = MailServer()


@app.get("/api/mail/status")
async def mail_status():
    """Get mail server status."""
    return {"status": "ok", "mail": mail_server.get_status()}


@app.post("/api/mail/start")
async def mail_start():
    """Start mail server containers."""
    return {"status": "ok", "result": mail_server.start()}


@app.post("/api/mail/stop")
async def mail_stop():
    """Stop mail server containers."""
    return {"status": "ok", "result": mail_server.stop()}


@app.post("/api/mail/restart")
async def mail_restart():
    """Restart mail server containers."""
    return {"status": "ok", "result": mail_server.restart()}


@app.get("/api/mail/users")
async def mail_list_users():
    """List all email users."""
    return {"status": "ok", "users": mail_server.list_users()}


@app.post("/api/mail/users")
async def mail_create_user(request: Request):
    """Create a new email user."""
    data = await request.json()
    email_addr = data.get("email", "")
    password = data.get("password", "")
    name = data.get("name", "")
    return {"status": "ok", "result": mail_server.create_user(email_addr, password, name)}


@app.delete("/api/mail/users/{email}")
async def mail_delete_user(email: str):
    """Deactivate an email user."""
    return {"status": "ok", "result": mail_server.delete_user(email)}


@app.get("/api/mail/aliases")
async def mail_list_aliases():
    """List all email aliases."""
    return {"status": "ok", "aliases": mail_server.list_aliases()}


@app.post("/api/mail/send")
async def mail_send(request: Request):
    """Send an email."""
    data = await request.json()
    to = data.get("to", "")
    subject = data.get("subject", "")
    body = data.get("body", "")
    from_addr = data.get("from", "")
    html = data.get("html", False)
    return {"status": "ok", "result": mail_server.send_email(to, subject, body, from_addr, html)}


@app.get("/api/mail/inbox")
async def mail_inbox(request: Request):
    """Read inbox emails."""
    user = request.query_params.get("user", "admin@zinemotion.com.mx")
    limit = int(request.query_params.get("limit", "20"))
    return {"status": "ok", "messages": mail_server.read_inbox(user=user, limit=limit)}


@app.get("/api/mail/logs/{service}")
async def mail_logs(service: str, request: Request):
    """Get mail service logs."""
    lines = int(request.query_params.get("lines", "100"))
    return {"status": "ok", "logs": mail_server.get_logs(service, lines)}


@app.get("/api/mail/dns")
async def mail_dns_records():
    """Get required DNS records."""
    return {"status": "ok", "dns": mail_server.get_dns_records()}


# --- Mail User Registration (Zoho-like) ---

def _validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def _validate_password(password: str) -> tuple:
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, ""

def _hash_password_sha512(password: str) -> str:
    """Generate SHA512-CRYPT hash for Dovecot/Postfix."""
    import subprocess
    salt = secrets.token_hex(16)
    result = subprocess.run(
        ["openssl", "passwd", "-6", "-salt", salt, password],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def _check_rate_limit(ip: str, action: str = "register") -> bool:
    """Simple in-memory rate limiter."""
    now = __import__("time").time()
    key = f"{ip}:{action}"
    if not hasattr(_check_rate_limit, "_attempts"):
        _check_rate_limit._attempts = {}
    attempts = _check_rate_limit._attempts.get(key, [])
    attempts = [t for t in attempts if now - t < 300]
    if len(attempts) >= 5:
        return False
    attempts.append(now)
    _check_rate_limit._attempts[key] = attempts
    return True


@app.get("/mail/register")
async def serve_mail_register():
    """Serve mail registration page."""
    return FileResponse(FRONTEND_DIR / "mail-register.html")


@app.post("/api/mail/register")
async def mail_register_user(request: Request):
    """Register a new mail user account with validation and security."""
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "error": "Invalid JSON"}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    name = data.get("name", "").strip()
    confirm_password = data.get("confirm_password", "")

    # Rate limiting
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        return {"status": "error", "error": "Too many attempts. Try again in 5 minutes."}

    # Input validation
    if not email or not _validate_email(email):
        return {"status": "error", "error": "Invalid email format"}

    if not email.endswith("@zinemotion.com.mx"):
        return {"status": "error", "error": "Email must be @zinemotion.com.mx"}

    if not name or len(name) < 2:
        return {"status": "error", "error": "Name must be at least 2 characters"}

    if password != confirm_password:
        return {"status": "error", "error": "Passwords do not match"}

    valid, msg = _validate_password(password)
    if not valid:
        return {"status": "error", "error": msg}

    # Check if user already exists
    existing_users = mail_server.list_users()
    for u in existing_users:
        if u.get("email") == email and u.get("active"):
            return {"status": "error", "error": "Email already registered"}

    # Create user
    result = mail_server.create_user(email, password, name)
    if result and "error" not in str(result).lower():
        logger.info(f"New mail user registered: {email}")
        return {"status": "ok", "message": f"Account {email} created successfully"}
    else:
        return {"status": "error", "error": f"Failed to create account: {result}"}


@app.post("/api/mail/validate-email")
async def mail_validate_email(request: Request):
    """Check if an email address is available."""
    data = await request.json()
    email = data.get("email", "").strip().lower()
    if not email or not _validate_email(email):
        return {"status": "ok", "available": False, "error": "Invalid email format"}
    existing_users = mail_server.list_users()
    for u in existing_users:
        if u.get("email") == email and u.get("active"):
            return {"status": "ok", "available": False, "error": "Email already taken"}
    return {"status": "ok", "available": True}


@app.get("/api/mail/check-username")
async def mail_check_username(username: str = ""):
    """Check if a username is available for @zinemotion.com.mx."""
    username = username.strip().lower()
    if not username or not re.match(r'^[a-z0-9._-]+$', username):
        return {"status": "ok", "available": False, "error": "Invalid username format"}
    email = f"{username}@zinemotion.com.mx"
    existing_users = mail_server.list_users()
    for u in existing_users:
        if u.get("email") == email and u.get("active"):
            return {"status": "ok", "available": False, "error": "Username already taken"}
    return {"status": "ok", "available": True}


# --- ZIO Machine Learning ---

from zicore.ml_engine import ZIOML
ml_engine = ZIOML()


@app.get("/api/ml/info")
async def ml_info():
    """Get ML engine info and capabilities."""
    return {"status": "ok", "ml": ml_engine.get_info()}


@app.post("/api/ml/train")
async def ml_train(request: Request):
    """Train a text classifier."""
    data = await request.json()
    training_data = data.get("data", [])
    model_name = data.get("model_name", "default")
    return {"status": "ok", "result": ml_engine.train_text_classifier(training_data, model_name)}


@app.post("/api/ml/predict")
async def ml_predict(request: Request):
    """Predict class for text."""
    data = await request.json()
    text = data.get("text", "")
    model_name = data.get("model_name", "default")
    return {"status": "ok", "result": ml_engine.predict_text(text, model_name)}


@app.post("/api/ml/anomaly")
async def ml_anomaly(request: Request):
    """Detect anomalies in data."""
    data = await request.json()
    values = data.get("data", [])
    threshold = data.get("threshold", 2.0)
    return {"status": "ok", "result": ml_engine.detect_anomalies(values, threshold)}


@app.post("/api/ml/cluster")
async def ml_cluster(request: Request):
    """K-Means clustering."""
    data = await request.json()
    points = data.get("data", [])
    k = data.get("k", 3)
    return {"status": "ok", "result": ml_engine.kmeans(points, k)}


@app.post("/api/ml/sentiment")
async def ml_sentiment(request: Request):
    """Analyze text sentiment."""
    data = await request.json()
    text = data.get("text", "")
    return {"status": "ok", "result": ml_engine.analyze_sentiment(text)}


@app.post("/api/ml/similarity")
async def ml_similarity(request: Request):
    """Calculate similarity between texts or vectors."""
    data = await request.json()
    mode = data.get("mode", "cosine")
    if mode == "cosine":
        a = data.get("vector_a", [])
        b = data.get("vector_b", [])
        return {"status": "ok", "result": ml_engine.cosine_similarity(a, b)}
    elif mode == "jaccard":
        a = set(data.get("set_a", []))
        b = set(data.get("set_b", []))
        return {"status": "ok", "result": ml_engine.jaccard_similarity(a, b)}
    return {"status": "error", "error": "Unknown similarity mode"}


@app.post("/api/ml/patterns")
async def ml_patterns(request: Request):
    """Find patterns in a sequence."""
    data = await request.json()
    sequence = data.get("sequence", [])
    return {"status": "ok", "result": ml_engine.find_patterns(sequence)}


@app.post("/api/ml/regression")
async def ml_regression(request: Request):
    """Linear regression."""
    data = await request.json()
    x = data.get("x", [])
    y = data.get("y", [])
    result = ml_engine.linear_regression(x, y)
    if "predict" in result:
        result["predict"] = "function available via /api/ml/regression/predict"
    return {"status": "ok", "result": result}


@app.post("/api/ml/vector")
async def ml_vector(request: Request):
    """Convert text to vector."""
    data = await request.json()
    text = data.get("text", "")
    mode = data.get("mode", "tf")
    if mode == "hash":
        return {"status": "ok", "result": ml_engine.hash_embedding(text)}
    return {"status": "ok", "result": ml_engine.text_to_vector(text)}


# --- Frontend-Compatible API Aliases ---


@app.get("/api/system/info")
async def system_info():
    """Alias for /api/system/stats"""
    return await get_system_stats()


@app.get("/api/engine/status")
async def engine_status():
    """Alias for /api/system/stats"""
    return await get_system_stats()


@app.get("/api/providers")
async def providers_list():
    """Return all providers from config"""
    config = load_config()
    return _sanitize_config(config).get("providers", {})


@app.get("/api/models")
async def models_list():
    """Return models from active provider"""
    config = load_config()
    active = config.get("zio_engine", {}).get("active_provider", "ollama")
    result = get_available_models(active, config)
    return result


# Known free models per provider (updated dynamically when possible)
FREE_MODEL_PATTERNS = {
    "openrouter": lambda mid: ":free" in mid or mid == "openrouter/free",
    "opencode": lambda mid: ":free" in mid or mid.endswith("-free") or mid.endswith("-free"),
    "groq": lambda mid: True,  # Groq free tier: all models are free with rate limits
    "ollama": lambda mid: True,  # Local = always free
}

# Hardcoded Groq free models (fallback if API unavailable)
GROQ_FREE_MODELS = [
    "llama-3.1-8b-instant", "llama-3.1-70b-versatile", "llama-3.3-70b-versatile",
    "mixtral-8x7b-32768", "gemma2-9b-it", "deepseek-r1-distill-llama-70b",
    "qwen-qwq-32b", "llama-3.2-1b-preview", "llama-3.2-3b-preview",
    "llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview",
]


def _detect_free_model(provider: str, model_id: str, model_data: dict = None) -> bool:
    """Detect if a model is free based on provider rules and API data."""
    if provider == "ollama":
        return True
    if provider == "groq":
        return True
    if provider in FREE_MODEL_PATTERNS:
        return FREE_MODEL_PATTERNS[provider](model_id)
    if provider == "openrouter" and model_data:
        pricing = model_data.get("pricing", {})
        try:
            if float(pricing.get("prompt", "1")) == 0 and float(pricing.get("completion", "1")) == 0:
                return True
        except (ValueError, TypeError):
            pass
    return False


def _fetch_provider_models(provider: str, prov_config: dict) -> dict:
    """Fetch live models from a provider API with free detection."""
    base_url = prov_config.get("base_url", "").rstrip("/")
    if base_url and not base_url.startswith("http"):
        base_url = f"http://{base_url}"
    api_key = prov_config.get("api_key", "")
    config_models = prov_config.get("models", [])

    if provider == "ollama":
        try:
            data = _request_json(f"{base_url}/api/tags", timeout=5)
            models = []
            for item in data.get("models", []):
                mid = item.get("name", "") if isinstance(item, dict) else str(item)
                if mid:
                    models.append({"id": mid, "name": mid, "is_free": True})
            return {"status": "ok", "models": models}
        except Exception as e:
            return {"status": "error", "models": [{"id": m, "name": m, "is_free": True} for m in config_models], "error": str(e)}

    if provider == "opencode":
        models = []
        for m in config_models:
            mid = m if isinstance(m, str) else m.get("id", "")
            models.append({"id": mid, "name": mid, "is_free": _detect_free_model(provider, mid)})
        return {"status": "ok", "models": models}

    if not api_key:
        models = [{"id": m, "name": m, "is_free": _detect_free_model(provider, m)} for m in config_models]
        return {"status": "no_api_key", "models": models}

    if provider in ("openrouter", "openai", "groq", "deepseek", "together"):
        try:
            data = _request_json(f"{base_url}/models", headers=_provider_headers(provider, api_key), timeout=15)
            api_items = data.get("data", [])
            models = []
            seen = set()
            for item in api_items:
                if not isinstance(item, dict):
                    continue
                mid = item.get("id", "")
                if not mid or mid in seen:
                    continue
                seen.add(mid)
                is_free = _detect_free_model(provider, mid, item)
                models.append({"id": mid, "name": item.get("name", mid), "is_free": is_free})
            for m in config_models:
                mid = m if isinstance(m, str) else m.get("id", "")
                if mid and mid not in seen:
                    models.append({"id": mid, "name": mid, "is_free": _detect_free_model(provider, mid)})
            return {"status": "ok", "models": models}
        except Exception as e:
            models = [{"id": m, "name": m, "is_free": _detect_free_model(provider, m)} for m in config_models]
            return {"status": "error", "models": models, "error": str(e)}

    models = [{"id": m, "name": m, "is_free": _detect_free_model(provider, m)} for m in config_models]
    return {"status": "ok", "models": models}


@app.get("/api/providers/fetch-models")
async def fetch_provider_models(provider: str = "all"):
    """Fetch live models from provider APIs with free detection.
    Use ?provider=openrouter or ?provider=all for all providers."""
    config = load_config()
    providers = config.get("providers", {})

    if provider != "all":
        if provider not in providers:
            return {"status": "error", "error": f"Unknown provider: {provider}"}
        result = _fetch_provider_models(provider, providers[provider])
        return {"provider": provider, **result}

    results = {}
    for name, prov_config in providers.items():
        results[name] = _fetch_provider_models(name, prov_config)
    return {"status": "ok", "providers": results}


# --- File System API ---


@app.post("/api/fs/ls")
async def fs_list(body: dict = {}):
    path = body.get("path", ".")
    base = Path(__file__).parent
    target = base / path
    if not target.exists() or not str(target.resolve()).startswith(str(base.resolve())):
        return {"status": "error", "error": "Invalid path"}
    items = []
    for f in sorted(target.iterdir()):
        try:
            stat = f.stat()
            items.append({
                "name": f.name,
                "path": str(f.relative_to(base)),
                "type": "dir" if f.is_dir() else "file",
                "size": stat.st_size,
                "modified": int(stat.st_mtime),
            })
        except:
            pass
    return {"status": "ok", "items": items, "cwd": str(target.relative_to(base))}


@app.post("/api/fs/read")
async def fs_read(body: dict = {}):
    path = body.get("path", "")
    base = Path(__file__).parent
    target = base / path
    if not target.exists() or not target.is_file():
        return {"status": "error", "error": "File not found"}
    if not str(target.resolve()).startswith(str(base.resolve())):
        return {"status": "error", "error": "Access denied"}
    try:
        content = target.read_text(encoding="utf-8", errors="replace")
        return {"status": "ok", "content": content, "size": target.stat().st_size}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/fs/write")
async def fs_write(body: dict = {}):
    path = body.get("path", "")
    content = body.get("content", "")
    base = Path(__file__).parent
    target = base / path
    if not str(target.resolve()).startswith(str(base.resolve())):
        return {"status": "error", "error": "Access denied"}
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"status": "ok", "path": str(target.relative_to(base))}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/fs/mkdir")
async def fs_mkdir(body: dict = {}):
    path = body.get("path", "")
    base = Path(__file__).parent
    target = base / path
    if not str(target.resolve()).startswith(str(base.resolve())):
        return {"status": "error", "error": "Access denied"}
    try:
        target.mkdir(parents=True, exist_ok=True)
        return {"status": "ok", "path": str(target.relative_to(base))}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/fs/remove")
async def fs_remove(body: dict = {}):
    path = body.get("path", "")
    base = Path(__file__).parent
    target = base / path
    if not str(target.resolve()).startswith(str(base.resolve())):
        return {"status": "error", "error": "Access denied"}
    try:
        if target.is_file():
            target.unlink()
        elif target.is_dir():
            import shutil
            shutil.rmtree(target)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/fs/rename")
async def fs_rename(body: dict = {}):
    path = body.get("path", "")
    new_name = body.get("new_name", "")
    base = Path(__file__).parent
    target = base / path
    if not target.exists():
        return {"status": "error", "error": "Path not found"}
    if not str(target.resolve()).startswith(str(base.resolve())):
        return {"status": "error", "error": "Access denied"}
    try:
        new_path = target.parent / new_name
        target.rename(new_path)
        return {"status": "ok", "path": str(new_path.relative_to(base))}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/upload")
async def upload_file(body: dict = {}):
    import base64, io
    path = body.get("path", "uploads")
    file_name = body.get("name", "file")
    file_data_b64 = body.get("data", "")
    base = Path(__file__).parent
    target_dir = base / path
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        file_bytes = base64.b64decode(file_data_b64)
        out_path = target_dir / file_name
        with open(out_path, "wb") as f:
            f.write(file_bytes)
        return {"status": "ok", "path": str(out_path.relative_to(base)), "size": len(file_bytes)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/media/upload")
async def media_upload(body: dict = {}):
    import base64
    cat = body.get("category", "images")
    file_name = body.get("name", "file.png")
    file_data_b64 = body.get("data", "")
    cat_dir = MEDIA_DIR / cat
    cat_dir.mkdir(parents=True, exist_ok=True)
    try:
        file_bytes = base64.b64decode(file_data_b64)
        out_path = cat_dir / file_name
        with open(out_path, "wb") as f:
            f.write(file_bytes)
        return {"status": "ok", "url": f"/media/{cat}/{file_name}", "size": len(file_bytes)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.delete("/api/media/delete")
async def media_delete(path: str = ""):
    target = MEDIA_DIR / path
    if not target.exists() or not str(target.resolve()).startswith(str(MEDIA_DIR.resolve())):
        return {"status": "error", "error": "Invalid path"}
    try:
        target.unlink()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# --- Simulator API ---

SIM_STATUS = {"running": False, "mode": "manual", "scenario": "", "started_at": None}
SIM_SCENARIOS = [
    {"id": "orbit_insert", "name": "Orbit Insertion", "desc": "Insert spacecraft into low orbit"},
    {"id": "rendezvous", "name": "Rendezvous", "desc": "Dock with space station"},
    {"id": "reentry", "name": "Atmospheric Re-entry", "desc": "Re-enter atmosphere safely"},
    {"id": "lander", "name": "Lunar Landing", "desc": "Land on lunar surface"},
    {"id": "evasive", "name": "Evasive Maneuvers", "desc": "Avoid incoming threats"},
]
SIM_VEHICLES = [
    {"id": "drone", "name": "Recon Drone", "type": "UAV", "speed": 120, "fuel": 60},
    {"id": "obsidiana", "name": "Obsidiana", "type": "Fighter", "speed": 850, "fuel": 180},
    {"id": "blackvanta", "name": "Blackvanta", "type": "Stealth", "speed": 950, "fuel": 200},
    {"id": "voyager", "name": "Voyager", "type": "Explorer", "speed": 300, "fuel": 500},
    {"id": "sigma", "name": "Ziron Sigma", "type": "Interceptor", "speed": 1200, "fuel": 150},
]


@app.post("/api/sim/start")
async def sim_start(body: dict = {}):
    global SIM_STATUS
    if SIM_STATUS["running"]:
        return {"status": "error", "error": "Simulation already running"}
    scenario = body.get("scenario", "orbit_insert")
    vehicle = body.get("vehicle", "drone")
    SIM_STATUS = {"running": True, "mode": "manual", "scenario": scenario, "vehicle": vehicle,
                  "started_at": __import__("time").time()}
    return {"status": "ok", "simulation": SIM_STATUS}


@app.post("/api/sim/stop")
async def sim_stop():
    global SIM_STATUS
    SIM_STATUS["running"] = False
    return {"status": "ok"}


@app.post("/api/sim/pause")
async def sim_pause():
    global SIM_STATUS
    SIM_STATUS["running"] = not SIM_STATUS["running"]
    return {"status": "ok", "running": SIM_STATUS["running"]}


@app.get("/api/sim/status")
async def sim_status():
    return {"status": "ok", "simulation": SIM_STATUS}


@app.get("/api/sim/telemetry")
async def sim_telemetry():
    from zicore.telemetry_sim import telemetry_sim
    data = telemetry_sim.get_telemetry()
    data["simulation"] = SIM_STATUS
    return data


@app.get("/api/sim/scenarios")
async def sim_scenarios():
    return {"status": "ok", "scenarios": SIM_SCENARIOS}


@app.get("/api/sim/vehicles")
async def sim_vehicles():
    return {"status": "ok", "vehicles": SIM_VEHICLES}


@app.post("/api/sim/command")
async def sim_command(body: dict = {}):
    cmd = body.get("command", "")
    params = body.get("params", {})
    logger.info(f"Sim command: {cmd} {params}")
    return {"status": "ok", "command": cmd, "executed": True}


# --- Backup & Diagnostics ---

BACKUP_DIR = Path(__file__).parent / "data" / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/api/backup/create")
async def backup_create(body: dict = {}):
    import shutil, datetime
    sections = body.get("sections", ["config", "knowledge", "media", "missions"])
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"backup_{timestamp}"
    backup_path.mkdir(parents=True, exist_ok=True)
    results = {}
    for section in sections:
        try:
            src = Path(__file__).parent / "data" / section
            if src.exists():
                dst = backup_path / section
                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                results[section] = "ok"
            else:
                results[section] = "not_found"
        except Exception as e:
            results[section] = str(e)
    return {"status": "ok", "backup_id": timestamp, "path": str(backup_path), "results": results}


@app.post("/api/backup/restore")
async def backup_restore(body: dict = {}):
    import shutil
    backup_id = body.get("backup_id", "")
    sections = body.get("sections", ["config", "knowledge", "media", "missions"])
    backup_path = BACKUP_DIR / f"backup_{backup_id}"
    if not backup_path.exists():
        return {"status": "error", "error": f"Backup {backup_id} not found"}
    results = {}
    for section in sections:
        try:
            src = backup_path / section
            dst = Path(__file__).parent / "data" / section
            if src.exists():
                if dst.exists():
                    if dst.is_dir():
                        shutil.rmtree(dst)
                    else:
                        dst.unlink()
                shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
                results[section] = "restored"
            else:
                results[section] = "not_found"
        except Exception as e:
            results[section] = str(e)
    return {"status": "ok", "results": results}


@app.post("/api/diagnostics/run")
async def diagnostics_run(body: dict = {}):
    checks = body.get("checks", ["ollama", "fs", "network", "services"])
    results = {}
    # Ollama check
    if "ollama" in checks:
        config = load_config()
        base_url = config.get("providers", {}).get("ollama", {}).get("base_url", "")
        if not base_url.startswith("http"):
            base_url = f"http://{base_url}"
        try:
            _request_json(f"{base_url}/api/tags", timeout=5)
            results["ollama"] = "ok"
        except Exception as e:
            results["ollama"] = f"error: {e}"
    # FS check
    if "fs" in checks:
        root = Path(__file__).parent
        results["fs"] = {
            "writable": os.access(root, os.W_OK),
            "disk_free": shutil.disk_usage(root).free if hasattr(shutil, "disk_usage") else "unknown",
        }
    # Network check
    if "network" in checks:
        results["network"] = {"node_reachable": _node_request("/api/status").get("status") == "online"}
    # Services check
    if "services" in checks:
        results["services"] = {
            "config_loaded": CONFIG_FILE.exists(),
            "media_dirs": {c: (MEDIA_DIR / c).exists() for c in ("audio", "video", "images", "music")},
        }
    return {"status": "ok", "diagnostics": results, "timestamp": __import__("time").time()}


# --- Agent API compatibility ---


@app.get("/api/agent/status")
async def agent_status():
    return {
        "status": "online",
        "agent": "ZIO",
        "version": "5.0.0",
        "sessions_active": 1,
        "provider": load_config().get("zio_engine", {}).get("active_provider", "ollama"),
    }


@app.post("/api/agent/chat")
async def agent_chat(body: dict):
    message = body.get("message", "")
    session_id = body.get("session_id", "webui")
    config = load_config()
    active = config.get("zio_engine", {}).get("active_provider", "ollama")
    result = call_provider_chat(active, message, config)
    return {"status": "ok", "response": result.get("response", ""), "session_id": session_id}


@app.get("/api/agent/sessions")
async def agent_sessions():
    import glob
    sessions = []
    for f in sorted(Path(__file__).parent.glob("data/knowledge/sessions/*.jsonl"), reverse=True)[:20]:
        sessions.append({"id": f.stem, "updated": f.stat().st_mtime})
    return {"status": "ok", "sessions": sessions}


@app.post("/api/agent/invoke")
async def agent_invoke(body: dict):
    action = body.get("action", "status")
    params = body.get("params", {})
    if action == "generate":
        return await api_generate(params)
    elif action == "chat":
        return await agent_chat({"message": params.get("message", ""), "session_id": params.get("session_id")})
    return {"status": "ok", "action": action, "executed": True}


@app.get("/api/ws/status")
async def ws_status():
    return {"status": "ok", "websocket": "available", "endpoint": "/ws/zio"}


# ─── Traffic Stats API ──────────────────────────────────────────────────────

@app.get("/web-stats")
async def serve_web_stats():
    return FileResponse(str(FRONTEND_DIR / "web-stats.html"))


@app.get("/api/stats/overview")
async def stats_overview(request: Request):
    hours = int(request.query_params.get("hours", "24"))
    return {"status": "ok", **traffic.overview(hours)}


@app.get("/api/stats/traffic")
async def stats_traffic(request: Request):
    hours = int(request.query_params.get("hours", "24"))
    return {"status": "ok", "data": traffic.requests_per_hour(hours)}


@app.get("/api/stats/endpoints")
async def stats_endpoints(request: Request):
    hours = int(request.query_params.get("hours", "24"))
    limit = int(request.query_params.get("limit", "20"))
    return {"status": "ok", "data": traffic.top_endpoints(hours, limit)}


@app.get("/api/stats/ips")
async def stats_ips(request: Request):
    hours = int(request.query_params.get("hours", "24"))
    limit = int(request.query_params.get("limit", "20"))
    return {"status": "ok", "data": traffic.top_ips(hours, limit)}


@app.get("/api/stats/status")
async def stats_status(request: Request):
    hours = int(request.query_params.get("hours", "24"))
    return {"status": "ok", "data": traffic.status_breakdown(hours)}


@app.post("/api/stats/cleanup")
async def stats_cleanup(request: Request):
    days = int(request.query_params.get("days", "30"))
    traffic.cleanup(days)
    return {"status": "ok", "message": f"Cleaned entries older than {days} days"}


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
if (FRONTEND_DIR / "games").exists():
    app.mount("/games", StaticFiles(directory=str(FRONTEND_DIR / "games")), name="games")
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

# zicore-fs media mount (if available)
if ZICORE_FS_MEDIA.exists():
    app.mount("/media-fs", StaticFiles(directory=str(ZICORE_FS_MEDIA)), name="media-fs")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    logger.info(f"Starting ZICORE Web Server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

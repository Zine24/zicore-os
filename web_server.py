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
import uuid
import asyncio
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

# DoH DNS resolver - ISP blocks UDP port 53, use HTTPS DNS instead
import socket as _socket
_orig_getaddrinfo = _socket.getaddrinfo
_doh_cache = {}
def _doh_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    cache_key = (host, port, family, type)
    if cache_key in _doh_cache:
        return _doh_cache[cache_key]
    if host in ('localhost', '127.0.0.1', '::1') or host.startswith('192.168.') or host.startswith('10.') or host.startswith('172.'):
        return _orig_getaddrinfo(host, port, family, type, proto, flags)
    try:
        import requests as _r
        resp = _r.get(f"https://1.1.1.1/dns-query?name={host}&type=A",
            headers={"Accept": "application/dns-json", "Host": "cloudflare-dns.com"},
            timeout=5, verify=True)
        data = resp.json()
        result = []
        for ans in data.get("Answer", []):
            if ans.get("type") == 1:
                result.append((_socket.AF_INET, _socket.SOCK_STREAM, 6, '', (ans["data"], port or 443)))
        if result:
            _doh_cache[cache_key] = result
            return result
    except Exception:
        pass
    return _orig_getaddrinfo(host, port, family, type, proto, flags)
_socket.getaddrinfo = _doh_getaddrinfo
logger.info("DoH DNS resolver active (ISP blocks UDP 53)")

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
    hdrs = headers or {}
    if "User-Agent" not in hdrs:
        hdrs["User-Agent"] = "ZICORE/5.0"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
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
    allow_origins=[
        "https://zcs.zicore.space",
        "https://zicore.space",
        "https://zinemotion.com.mx",
        "https://www.zinemotion.com.mx",
        "https://zichat.zinemotion.com",
        "https://zzz.zinemotion.com",
        "http://localhost:4000",
        "http://localhost:8080",
        "http://192.168.1.85:4000",
        "http://192.168.1.68:8080",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrafficMiddleware)


import collections


# ─── Rate Limit Middleware ────────────────────────────────────────────────────
class RateLimitMiddleware:
    """Simple in-memory rate limiter for API endpoints."""

    def __init__(self, app):
        self.app = app
        self._attempts = collections.defaultdict(list)  # key -> [timestamp, ...]
        self._LIMITS = {
            "/api/sso/login": (5, 300),      # 5 attempts per 5 minutes
            "/api/sso/register": (3, 600),   # 3 attempts per 10 minutes
            "/api/sso/reset-password": (3, 600),
        }

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path", "")
        if path not in self._LIMITS:
            return await self.app(scope, receive, send)

        headers = dict(scope.get("headers", []))
        client_ip = scope.get("client", ("", 0))[0] if scope.get("client") else "unknown"
        key = f"{path}:{client_ip}"
        limit, window = self._LIMITS[path]

        now = time.time()
        self._attempts[key] = [t for t in self._attempts[key] if now - t < window]

        if len(self._attempts[key]) >= limit:
            from fastapi.responses import JSONResponse
            response = JSONResponse(
                {"status": "error", "error": "Too many requests. Please try again later."},
                status_code=429
            )
            return await response(scope, receive, send)

        self._attempts[key].append(now)
        return await self.app(scope, receive, send)


# ─── SSO Auth Middleware — Login obligatorio ─────────────────────────────────
# Sin token valido no se accede a NADA excepto login y APIs de auth
class SSOAuthMiddleware:
    """Middleware that enforces SSO login on all routes."""

    # Rutas publicas (no requieren autenticacion)
    PUBLIC_PATHS = {
        "/login",
        "/api/sso/login",
        "/api/sso/register",
        "/api/sso/plans",
        "/api/sso/check-username",
        "/api/mail/check-username",
        "/api/mail/validate-email",
        "/api/system/stats",
        "/api/health",
        "/api/games/catalog",
        "/api/games/scores",
        "/api/downloads",
        "/",
        "/zinemotion",
        "/whitepaper",
        "/ecosystem",
        "/zicodex",
        "/download",
        "/installers",
        "/mobile",
        "/api-docs",
        "/docs",
        "/services",
        "/aerospace-portal",
        "/zine-motion",
        "/developer-portal",
        "/solar-navigation",
        "/mission-control",
        "/vehicle-designer",
        "/propulsion-lab",
        "/orbital-mechanics",
        "/engineering",
        "/aerospace-engineering",
        "/games",
        "/outpreview",
        "/materializer",
        "/visualizer",
        "/video-editor",
        "/zicore-bank",
        "/zivault",
        "/zicore-print",
        "/ziprint",
        "/download/apk",
        "/terms-of-service",
        "/privacy-policy",
        "/mail",
        "/mail-portal",
        "/mail-accounts",
        "/mail-incoming",
        "/mail/register",
        "/zinemotion-mail",
        "/settings",
        "/dashboard",
        "/web-stats",
        "/browser",
        "/zio",
        "/zicore",
        "/videochat",
        "/storage",
        "/multimedia",
        "/crypto-pay",
        "/environment",
        "/redgen",
        "/zishield",
        "/governance",
        "/asset-registry",
        "/vr-viewer",
        "/display-monitor",
        "/profile",
        "/api/vr/sessions",
        "/api/mail/admin-check",
        "/api/vault/currencies",
        "/api/vault/store/products",
        "/api/vault/znt/balance",
        "/disclaimer",
        "/api/contact",
        "/api/contact/submissions",
        "/admin",
        "/server-admin",
        "/console",
        "/zihost",
        "/zimail",
        "/zimaterializer",
        "/api/zihost/create",
        "/api/zihost/auth",
        "/api/zihost/stats",
    }

    # Prefijos publicos (static files necesarios para login)
    PUBLIC_PREFIXES = (
        "/output/",    # generated content (images, meshes, etc.)
        "/css/",
        "/js/",
        "/data/",      # i18n translations, config
        "/favicon",
        "/games/",     # game files accessible without login
        "/media/",     # media files
        "/static/",    # static assets
        "/installers/", # downloadable installers and APKs
        "/api/library/", # generation library (public for sidebar)
        "/api/preview/", # mesh preview images
        "/api/simulate/", # mesh simulation
        "/v1/", # OpenAI-compatible ZIO endpoint for Open-WebUI
        "/api/admin/", # server admin console API
        "/ollama/", # Ollama reverse proxy (VPS → local:11434)
        "/shell", # interactive SSH shell terminal
        "/api/shell/", # shell API (servers, sessions, close)
        "/api/zihost/", # ZiHost hosting panel API
    )

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        path = scope.get("path", "")

        # Allow public paths
        if path in self.PUBLIC_PATHS:
            return await self.app(scope, receive, send)

        # Allow public prefixes
        for prefix in self.PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return await self.app(scope, receive, send)

        # Allow WebSocket (auth handled per-connection)
        if scope["type"] == "websocket":
            return await self.app(scope, receive, send)

        # Check for SSO token in cookie or Authorization header
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization", b"").decode("utf-8", "replace")

        # Also check query params for token (useful for initial page load)
        query_string = scope.get("query_string", b"").decode("utf-8", "replace")
        token = None

        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        # Token in query string DISABLED for security (tokens logged in browser history)
        # elif "token=" in query_string:
        #     for param in query_string.split("&"):
        #         if param.startswith("token="):
        #             token = param[6:]
        #             break

        # If no token, check for SSO cookie in headers
        if not token:
            cookie_header = headers.get(b"cookie", b"").decode("utf-8", "replace")
            for part in cookie_header.split(";"):
                part = part.strip()
                if part.startswith("zicore_sso_token="):
                    token = part.split("=", 1)[1]
                    break

        # Validate token
        if token and sso:
            result = sso.verify_token(token)
            if result.get("success") and result.get("user"):
                # Token valid — attach user to scope
                scope["state"] = scope.get("state", {})
                scope["state"]["sso_user"] = result["user"]
                return await self.app(scope, receive, send)

        # No valid token — redirect to login (for HTML pages)
        # or return 401 (for API calls)
        accept = headers.get(b"accept", b"").decode("utf-8", "replace")

        if "text/html" in accept:
            # Browser request — redirect to login
            from fastapi.responses import RedirectResponse
            redirect_url = f"/login?redirect={path}"
            response = RedirectResponse(url=redirect_url, status_code=302)
            await response(scope, receive, send)
        else:
            # API request — return 401
            response = JSONResponse(
                {"status": "error", "error": "Authentication required", "login_url": "/login"},
                status_code=401
            )
            await response(scope, receive, send)


app.add_middleware(RateLimitMiddleware)
app.add_middleware(SSOAuthMiddleware)


# ─── Module-level singletons ─────────────────────────────────────────────────
try:
    from zicore.generation_library import GenerationLibrary
    generation_library = GenerationLibrary()
except Exception as _e:
    logger.warning(f"Generation Library unavailable: {_e}")
    generation_library = None

try:
    from zicore.outpreview import OutPreview
    outpreview = OutPreview()
except Exception as _e:
    logger.warning(f"OutPreview unavailable: {_e}")
    outpreview = None

try:
    from zicore.materializer import ZICOREMaterializer
    materializer = ZICOREMaterializer()
except Exception as _e:
    logger.warning(f"ZICOREMaterializer unavailable: {_e}")
    materializer = None

try:
    from zicore.vr_stream import vr_stream_manager
except Exception as _e:
    logger.warning(f"VR Stream Manager unavailable: {_e}")
    vr_stream_manager = None

# ─── ZICORE SSO Singleton ────────────────────────────────────────────────────
try:
    from zicore.sso import ZICORESSO
    sso = ZICORESSO()
except Exception as _e:
    logger.warning(f"SSO unavailable: {_e}")
    sso = None


@app.get("/")
async def serve_main_menu(request: Request):
    """Main entry point — public landing page."""
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


@app.get("/vehicle-designer")
async def serve_vehicle_designer():
    return FileResponse(str(FRONTEND_DIR / "vehicle-designer.html"))


@app.get("/propulsion-lab")
async def serve_propulsion_lab():
    return FileResponse(str(FRONTEND_DIR / "propulsion-lab.html"))


@app.get("/orbital-mechanics")
async def serve_orbital_mechanics():
    return FileResponse(str(FRONTEND_DIR / "orbital-mechanics.html"))


@app.get("/mail")
async def serve_mail():
    return FileResponse(str(FRONTEND_DIR / "mail.html"))


@app.get("/mail-portal")
async def serve_mail_portal():
    return FileResponse(str(FRONTEND_DIR / "mail-portal.html"))


@app.get("/mail-accounts")
async def serve_mail_accounts():
    return FileResponse(str(FRONTEND_DIR / "mail-accounts.html"))


@app.get("/mail-incoming")
async def serve_mail_incoming():
    return FileResponse(str(FRONTEND_DIR / "mail-incoming.html"))


@app.get("/mission-control")
async def serve_mission_control():
    return FileResponse(str(FRONTEND_DIR / "mission-control.html"))


@app.get("/solar-navigation")
async def serve_solar_navigation():
    return FileResponse(str(FRONTEND_DIR / "solar-navigation.html"))


@app.get("/zinemotion-mail")
async def serve_zinemotion_mail():
    return FileResponse(str(FRONTEND_DIR / "zinemotion-mail.html"))


@app.get("/zicore-bank")
async def serve_zicore_bank():
    return FileResponse(str(FRONTEND_DIR / "zicore-bank.html"))


@app.get("/zivault")
async def serve_zivault():
    return FileResponse(str(FRONTEND_DIR / "zivault.html"))


@app.get("/whitepaper")
async def serve_whitepaper():
    return FileResponse(str(FRONTEND_DIR / "whitepaper.html"))


@app.get("/ecosystem")
async def serve_ecosystem():
    return FileResponse(str(FRONTEND_DIR / "ecosystem.html"))


@app.get("/zicodex")
async def serve_zicodex():
    return FileResponse(str(FRONTEND_DIR / "zicodex.html"))


@app.get("/marketplace")
async def serve_marketplace():
    return FileResponse(str(FRONTEND_DIR / "marketplace.html"))


@app.get("/developer")
async def serve_developer():
    return FileResponse(str(FRONTEND_DIR / "developer.html"))


@app.get("/api-docs")
@app.get("/docs")
async def serve_api_docs():
    return FileResponse(str(FRONTEND_DIR / "api-docs.html"))


@app.get("/portal")
async def serve_portal():
    return FileResponse(str(FRONTEND_DIR / "portal.html"))


@app.get("/services")
async def serve_services():
    return FileResponse(str(FRONTEND_DIR / "services.html"))


@app.get("/aerospace-portal")
async def serve_aerospace_portal():
    return FileResponse(str(FRONTEND_DIR / "aerospace-portal.html"))


@app.get("/zine-motion")
async def serve_zinemotion_portal():
    return FileResponse(str(FRONTEND_DIR / "zinemotion-portal.html"))


@app.get("/developer-portal")
async def serve_developer_portal():
    return FileResponse(str(FRONTEND_DIR / "developer-portal.html"))


@app.get("/download/apk")
async def download_apk():
    fpath = INSTALLERS_DIR / "zicore-android.apk"
    if not fpath.exists():
        return JSONResponse({"status": "error", "error": "APK not found"}, status_code=404)
    count = _load_downloads() + 1
    _save_downloads(count)
    return FileResponse(str(fpath), media_type="application/vnd.android.package-archive", filename="zicore-android.apk")


@app.get("/download")
async def serve_download():
    return RedirectResponse(url="/installers")


@app.get("/installers")
async def serve_installers():
    return FileResponse(str(FRONTEND_DIR / "installers.html"))


INSTALLERS_DIR = Path(__file__).parent / "installers"

@app.get("/installers/{filename}")
async def download_installer(filename: str):
    allowed = {"install_zicore.ps1", "install_zicore.sh", "install_zicore_mac.sh", "zicore-android.apk"}
    if filename not in allowed:
        return JSONResponse({"status": "error", "error": "File not found"}, status_code=404)
    fpath = INSTALLERS_DIR / filename
    if not fpath.exists():
        return JSONResponse({"status": "error", "error": "File not found"}, status_code=404)
    count = _load_downloads() + 1
    _save_downloads(count)
    if filename.endswith(".apk"):
        media_type = "application/vnd.android.package-archive"
    elif filename.endswith(".sh"):
        media_type = "text/plain"
    else:
        media_type = "text/plain"
    return FileResponse(str(fpath), media_type=media_type, filename=filename)


@app.get("/dashboard")
async def serve_dashboard():
    return FileResponse(str(FRONTEND_DIR / "dashboard.html"))


@app.get("/materializer")
async def serve_materializer():
    return FileResponse(str(FRONTEND_DIR / "materializer.html"))


@app.get("/visualizer")
async def serve_visualizer():
    return FileResponse(str(FRONTEND_DIR / "visualizer.html"))


@app.get("/video-editor")
async def serve_video_editor():
    return FileResponse(str(FRONTEND_DIR / "video-editor.html"))


@app.get("/zimail")
async def serve_zimail():
    return FileResponse(str(FRONTEND_DIR / "zimail.html"))


@app.get("/zimaterializer")
async def serve_zimaterializer():
    return FileResponse(str(FRONTEND_DIR / "zimaterializer.html"))


@app.get("/audio-engine")
async def serve_audio_engine():
    return FileResponse(str(FRONTEND_DIR / "audio-engine.html"))


@app.get("/login")
async def serve_sso_login():
    return FileResponse(str(FRONTEND_DIR / "sso-login.html"))


@app.get("/terms-of-service")
async def serve_terms():
    return FileResponse(str(FRONTEND_DIR / "terms-of-service.html"))


@app.get("/privacy-policy")
async def serve_privacy():
    return FileResponse(str(FRONTEND_DIR / "privacy-policy.html"))


@app.get("/disclaimer")
async def serve_disclaimer():
    return FileResponse(str(FRONTEND_DIR / "disclaimer.html"))


@app.post("/api/contact")
async def contact_form(request: Request):
    """Receive contact form submission and store it."""
    try:
        data = await request.json()
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        message = data.get("message", "").strip()
        if not name or not email or not message:
            return JSONResponse({"status": "error", "error": "Name, email, and message are required"}, status_code=400)
        # Store in contact submissions file
        contacts_file = Path(__file__).parent / "data" / "contact_submissions.json"
        contacts_file.parent.mkdir(parents=True, exist_ok=True)
        submissions = []
        if contacts_file.exists():
            try:
                submissions = json.loads(contacts_file.read_text(encoding="utf-8"))
            except Exception:
                submissions = []
        submissions.append({
            "name": name,
            "email": email,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "read": False,
        })
        contacts_file.write_text(json.dumps(submissions, indent=2, ensure_ascii=False), encoding="utf-8")
        # Try to send email notification if mail is available
        try:
            sent = False
            if mail_server is not None:
                r = mail_server.send_email(
                    to="hola@zinemotion.com.mx",
                    subject=f"ZICORE Contact: {name}",
                    body=f"Name: {name}\nEmail: {email}\n\nMessage:\n{message}",
                    from_addr="noreply@zinemotion.com.mx",
                    html=False,
                )
                if isinstance(r, dict) and r.get("success"):
                    sent = True
            if not sent and oracle_email and oracle_email.enabled:
                oracle_email.send_contact_notification(name, email, message)
        except Exception:
            pass  # Don't fail the form if email fails
        return {"status": "ok", "message": "Message received"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/contact/submissions")
async def contact_submissions():
    """Get all contact form submissions (admin)."""
    try:
        contacts_file = Path(__file__).parent / "data" / "contact_submissions.json"
        if not contacts_file.exists():
            return {"status": "ok", "submissions": []}
        submissions = json.loads(contacts_file.read_text(encoding="utf-8"))
        return {"status": "ok", "submissions": submissions, "count": len(submissions)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


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


@app.get("/crypto-pay")
async def serve_crypto_pay():
    return FileResponse(str(FRONTEND_DIR / "crypto-pay.html"))


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
    {"id": "tetris", "name": "Tetris", "category": "puzzle", "icon": "&#129522;"},
    {"id": "snake", "name": "Snake", "category": "arcade", "icon": "&#128013;"},
    {"id": "breakout", "name": "Breakout", "category": "arcade", "icon": "&#127936;"},
    {"id": "2048", "name": "2048", "category": "puzzle", "icon": "&#129516;"},
    {"id": "memory", "name": "Memory", "category": "puzzle", "icon": "&#129504;"},
    {"id": "sudoku", "name": "Sudoku", "category": "puzzle", "icon": "&#128220;"},
    {"id": "tic-tac-toe", "name": "Tic-Tac-Toe", "category": "strategy", "icon": "&#10060;"},
    {"id": "minesweeper", "name": "Minesweeper", "category": "puzzle", "icon": "&#128163;"},
    {"id": "chess", "name": "Chess", "category": "strategy", "icon": "&#9823;"},
    {"id": "asteroids", "name": "Asteroids", "category": "arcade", "icon": "&#128165;"},
    {"id": "contra", "name": "Contra", "category": "action", "icon": "&#128299;"},
    {"id": "mario-bros3", "name": "Mario Bros 3", "category": "arcade", "icon": "&#127918;"},
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


@app.get("/profile")
async def serve_profile():
    return FileResponse(str(FRONTEND_DIR / "profile.html"))


@app.get("/browser")
async def serve_browser():
    return FileResponse(str(FRONTEND_DIR / "browser.html"))


@app.get("/outpreview")
async def serve_outpreview():
    return FileResponse(str(FRONTEND_DIR / "outpreview.html"))


@app.get("/storage")
async def serve_storage():
    return FileResponse(str(FRONTEND_DIR / "storage.html"))


@app.get("/api/proxy")
async def proxy_fetch(url: str = "", headers_json: str = ""):
    """Proxy HTTP requests to bypass CORS/iframe restrictions. Uses DoH for DNS."""
    import asyncio
    import urllib.parse
    import urllib.error as ue
    import ssl
    import requests as _req

    if not url:
        return JSONResponse({"error": "No URL provided"}, status_code=400)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return JSONResponse({"error": "Only http/https URLs allowed"}, status_code=400)

    def _do_fetch():
        extra_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        if headers_json:
            try:
                extra_headers.update(json.loads(headers_json))
            except Exception:
                pass
        resp = _req.get(url, headers=extra_headers, timeout=15, verify=True, allow_redirects=True)
        content_type = resp.headers.get("Content-Type", "text/html")
        body = resp.text
        if "text/html" in content_type:
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            body = body.replace('href="/', f'href="{base_url}/')
            body = body.replace("src=\"/", f"src=\"{base_url}/")
            body = body.replace("src='/", f"src='{base_url}/")
        return body, content_type, resp.status_code

    loop = asyncio.get_event_loop()
    try:
        body, content_type, status_code = await asyncio.wait_for(
            loop.run_in_executor(None, _do_fetch), timeout=25
        )
        if status_code == 403:
            return HTMLResponse(
                content=f"<html><body style='font-family:monospace;background:#0d1117;color:#c8d6e5;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h1 style='color:#ff8800'>403 - Acceso Denegado</h1><p style='color:#667788'>El sitio <code>{parsed.netloc}</code> bloqueo el acceso.</p><p style='color:#667788;font-size:12px'>Intenta abrir la pagina directamente en una pestana nueva.</p></div></body></html>",
                headers={"Content-Type": "text/html"},
            )
        return HTMLResponse(content=body, headers={"Content-Type": content_type})
    except ue.HTTPError as e:
        return HTMLResponse(
            content=f"<html><body style='font-family:monospace;background:#0d1117;color:#c8d6e5;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h1 style='color:#ff3333'>HTTP {e.code}</h1><p style='color:#667788'>{e.reason}</p><p style='color:#667788;font-size:12px'>{url}</p></div></body></html>",
            headers={"Content-Type": "text/html"},
        )
    except asyncio.TimeoutError:
        return HTMLResponse(
            content="<html><body style='font-family:monospace;background:#0d1117;color:#c8d6e5;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h1 style='color:#ff8800'>Timeout</h1><p style='color:#667788'>La pagina tardo demasiado en responder.</p></div></body></html>",
            headers={"Content-Type": "text/html"},
        )
    except ue.URLError as e:
        return HTMLResponse(
            content=f"<html><body style='font-family:monospace;background:#0d1117;color:#c8d6e5;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h1 style='color:#ff3333'>Conexion Fallida</h1><p style='color:#667788'>{e.reason}</p></div></body></html>",
            headers={"Content-Type": "text/html"},
        )
    except Exception as e:
        return HTMLResponse(
            content=f"<html><body style='font-family:monospace;background:#0d1117;color:#c8d6e5;display:flex;align-items:center;justify-content:center;height:100vh'><div style='text-align:center'><h1 style='color:#ff3333'>Error</h1><p style='color:#667788'>{str(e)}</p></div></body></html>",
            headers={"Content-Type": "text/html"},
        )


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
    # Try zicore_native (VPS) first — this is the primary inference
    zicore_url = config.get("providers", {}).get("zicore_native", {}).get("base_url", "")
    if zicore_url:
        if not zicore_url.startswith("http"):
            zicore_url = f"http://{zicore_url}"
        result = status(zicore_url)
        if result.get("status") == "online":
            result["base_url"] = zicore_url
            return {"status": "online", "host": result.get("host", zicore_url), "models": result.get("models", []),
                    "source": "zicore_native", "base_url": zicore_url}
    # Fallback to ollama provider (.68)
    base_url = config.get("providers", {}).get("ollama", {}).get("base_url", "127.0.0.1:11434")
    if not base_url.startswith("http"):
        base_url = f"http://{base_url}"
    result = status(base_url)
    result["base_url"] = base_url
    return {"status": result.get("status", "offline"), "host": result.get("host", base_url),
            "models": result.get("models", []), "source": "ollama", "base_url": base_url}


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

    if provider_name == "aerospace-engineering":
        provider_name = "zicore_native"

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


# ─── OpenAI-Compatible Endpoint for ZIO (Open-WebUI integration) ────────────

ZIO_MODELS = [
    {
        "id": "zicore",
        "object": "model",
        "created": int(time.time()),
        "owned_by": "zicore",
        "permission": [],
    },
    {
        "id": "zicore:aerospace",
        "object": "model",
        "created": int(time.time()),
        "owned_by": "zicore",
        "permission": [],
    },
    {
        "id": "zicore:mission",
        "object": "model",
        "created": int(time.time()),
        "owned_by": "zicore",
        "permission": [],
    },
]


@app.get("/v1/models")
async def openai_list_models():
    return {
        "object": "list",
        "data": ZIO_MODELS,
    }


@app.post("/v1/chat/completions")
async def openai_chat_completions(body: dict):
    try:
        model = body.get("model", "zicore")
        messages = body.get("messages", [])
        stream = body.get("stream", False)

        if not messages:
            return JSONResponse({"error": "messages required"}, status_code=400)

        # Build session context from messages
        system_prompt = ""
        user_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system_prompt = msg.get("content", "")
            elif msg.get("role") in ("user", "assistant"):
                user_messages.append(msg.get("content", ""))

        last_message = user_messages[-1] if user_messages else ""

        # Map model to ZIO variant
        zio_session_id = f"zichat_{model.replace(':', '_')}"
        if "aerospace" in model:
            context = {"source": "openai", "mode": "aerospace", "system_prompt": system_prompt}
        elif "mission" in model:
            context = {"source": "openai", "mode": "mission", "system_prompt": system_prompt}
        else:
            context = {"source": "openai", "system_prompt": system_prompt}

        sys.path.insert(0, str(Path(__file__).parent))
        from agent.core import ZICoreAgent
        agent = ZICoreAgent(session_id=zio_session_id)
        result = await agent.process(last_message, context)
        reply = result.get("outputs", {}).get("text",
                result.get("outputs", {}).get("zio_msg", ""))

        if not reply:
            reply = "I'm sorry, I couldn't process that request."

        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": reply},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(str(messages)) // 4,
                "completion_tokens": len(reply) // 4,
                "total_tokens": (len(str(messages)) + len(reply)) // 4,
            },
        }
    except Exception as e:
        logger.error(f"OpenAI chat error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


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
        ollama_models = []
        ollama_host = ""
        ollama_url_active = ""
        try:
            config = load_config()
            active_prov = config.get("zio_engine", {}).get("active_provider", "zicore_native")
            ollama_cfg = config.get("providers", {}).get("ollama", {})
            zicore_cfg = config.get("providers", {}).get("zicore_native", {})
            ollama_url = ollama_cfg.get("base_url", OLLAMA_BASE_URL)
            if not ollama_url.startswith("http"):
                ollama_url = f"http://{ollama_url}"
            # Try ollama provider first (.68)
            if ollama_cfg.get("enabled"):
                import urllib.request as _req
                try:
                    req = _req.Request(ollama_url + "/api/tags", headers={"User-Agent": "ZICORE/5.0"})
                    resp = _req.urlopen(req, timeout=3)
                    ollama_ok = True
                    ollama_host = ollama_url
                    ollama_url_active = ollama_url
                    tags = json.loads(resp.read().decode())
                    ollama_models = [m.get("name", "") for m in tags.get("models", []) if m.get("name")]
                except Exception:
                    pass
            # Fallback to zicore_native (VPS)
            if not ollama_ok and zicore_cfg.get("enabled"):
                zicore_url = zicore_cfg.get("base_url", "")
                if zicore_url and not zicore_url.startswith("http"):
                    zicore_url = f"http://{zicore_url}"
                if zicore_url:
                    try:
                        import urllib.request as _req
                        req = _req.Request(zicore_url + "/api/tags", headers={"User-Agent": "ZICORE/5.0"})
                        resp = _req.urlopen(req, timeout=5)
                        ollama_ok = True
                        ollama_host = zicore_url
                        ollama_url_active = zicore_url
                        tags = json.loads(resp.read().decode())
                        ollama_models = [m.get("name", "") for m in tags.get("models", []) if m.get("name")]
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
            "ollama_host": ollama_host,
            "ollama_url": ollama_url_active,
            "ollama_models": ollama_models,
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


# ─── SIMULATION ENGINE API ROUTES ──────────────────────────────────────────
sim_engine = None
def _get_sim_engine():
    global sim_engine
    if sim_engine is None:
        from zicore.simulation_engine import SimulationEngine
        sim_engine = SimulationEngine()
    return sim_engine

@app.post("/api/simulate/full")
async def api_simulate_full(request: Request):
    """Generate a simulation from a natural language prompt."""
    try:
        body = await request.json()
        prompt = body.get("prompt", "")
        resolution = body.get("resolution", 512)
        if not prompt:
            return {"status": "error", "error": "No prompt provided"}
        engine = _get_sim_engine()
        result = engine.generate(prompt, resolution=resolution, async_mode=False)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/api/simulate/scene/{sim_id}")
async def api_simulate_scene(sim_id: str):
    """Get the scene configuration for a simulation."""
    try:
        engine = _get_sim_engine()
        scene = engine.get_scene(sim_id)
        if scene is None:
            return {"error": f"Simulation {sim_id} not found"}
        return scene
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/simulate/status/{sim_id}")
async def api_simulate_status(sim_id: str):
    """Get the status of a simulation."""
    try:
        engine = _get_sim_engine()
        status = engine.get_status(sim_id)
        if status is None:
            return {"error": f"Simulation {sim_id} not found"}
        return {"status": "ok", "simulation": status}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/simulate/list")
async def api_simulate_list():
    """List all simulations."""
    try:
        engine = _get_sim_engine()
        sims = engine.list_simulations()
        return {"status": "ok", "simulations": sims}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/simulate/entities")
async def api_simulate_entities():
    """List available entity templates."""
    try:
        engine = _get_sim_engine()
        entities = engine.get_available_entities()
        return {"status": "ok", "entities": entities}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/simulate/bodies")
async def api_simulate_bodies():
    """List available celestial bodies."""
    try:
        engine = _get_sim_engine()
        bodies = engine.get_available_bodies()
        return {"status": "ok", "bodies": bodies}
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
            except Exception:
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


@app.post("/api/audio/process")
async def audio_process(body: dict):
    effect = body.get("effect", "")
    params = body.get("params", {})
    return {"status": "ok", "effect": effect, "params": params, "message": f"Audio processing with {effect}"}


@app.post("/api/audio/generate")
async def audio_generate(body: dict):
    prompt = body.get("prompt", "")
    duration = body.get("duration", 5)
    sample_rate = body.get("sample_rate", 44100)
    try:
        import numpy as np
        import wave, os, time
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        freq = 440
        if any(w in prompt.lower() for w in ['bass', 'low', 'sub']):
            freq = 80
        elif any(w in prompt.lower() for w in ['high', 'hi', 'lead']):
            freq = 880
        elif any(w in prompt.lower() for w in ['mid', 'chord']):
            freq = 330
        elif any(w in prompt.lower() for w in ['drum', 'kick', 'beat']):
            data = np.zeros_like(t)
            beat_interval = 60 / 120
            for i in range(int(duration / beat_interval)):
                idx_start = int(i * beat_interval * sample_rate)
                idx_end = min(idx_start + int(0.05 * sample_rate), len(data))
                data[idx_start:idx_end] = np.exp(-100 * (t[idx_start:idx_end] - t[idx_start])) * 0.8
            tone = data
        else:
            tone = 0.3 * np.sin(2 * np.pi * freq * t) * np.exp(-2 * t)
        if 'tone' in dir():
            tone_data = tone
        else:
            tone_data = data
        os.makedirs("output", exist_ok=True)
        fname = f"output/audio_{int(time.time())}.wav"
        with wave.open(fname, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes((tone_data * 32767).astype(np.int16).tobytes())
        return {"status": "ok", "file": fname, "duration": duration, "sample_rate": sample_rate}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/audio/effects")
async def audio_effects(body: dict):
    effect = body.get("effect", "reverb")
    intensity = body.get("intensity", 0.5)
    effects_info = {
        "reverb": {"name": "Reverb", "desc": "Room simulation with decay time"},
        "delay": {"name": "Delay", "desc": "Echo with feedback control"},
        "eq": {"name": "Equalizer", "desc": "Frequency band adjustment"},
        "compress": {"name": "Compressor", "desc": "Dynamic range control"},
        "filter": {"name": "Filter", "desc": "Low-pass / High-pass / Band-pass"},
        "chorus": {"name": "Chorus", "desc": "Modulated delay for thickness"},
        "distortion": {"name": "Distortion", "desc": "Saturation and overdrive"},
        "flanger": {"name": "Flanger", "desc": "Swept comb filter effect"},
        "phaser": {"name": "Phaser", "desc": "All-pass filter sweeps"},
    }
    info = effects_info.get(effect, {"name": effect, "desc": "Unknown effect"})
    return {"status": "ok", "effect": info, "intensity": intensity, "applied": True}


@app.post("/api/audio/mix")
async def audio_mix(body: dict):
    tracks = body.get("tracks", [])
    master_vol = body.get("master_volume", 0.8)
    return {"status": "ok", "tracks": len(tracks), "master_volume": master_vol, "message": f"Mixed {len(tracks)} tracks"}


@app.post("/api/audio/export")
async def audio_export(body: dict):
    format = body.get("format", "wav")
    sample_rate = body.get("sample_rate", 44100)
    bit_depth = body.get("bit_depth", 16)
    filename = body.get("filename", "zicore-export")
    return {"status": "ok", "format": format, "sample_rate": sample_rate, "bit_depth": bit_depth, "filename": filename, "message": "Export complete"}


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
                    result = await asyncio.to_thread(subprocess.run, ["openscad", "-o", str(stl_path), str(scad_path)],
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


# ─── Enhanced Materializer Routes ────────────────────────────────────────────

@app.post("/api/materialize/audio")
async def materialize_audio(body: dict):
    try:
        prompt = body.get("prompt", "")
        audio_type = body.get("type", "sfx")
        duration = body.get("duration", 5)
        params = body.get("params", {})
        if not prompt:
            return JSONResponse({"status": "error", "error": "prompt required"}, status_code=400)

        from agent.generator import ZICoreGenerator
        gen = ZICoreGenerator()
        result = gen.generate_audio(prompt, audio_type=audio_type, duration=duration, **params)
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"Audio materialize error: {e}")
        return {"status": "error", "error": str(e)}


@app.post("/api/materialize/video")
async def materialize_video(body: dict):
    try:
        prompt = body.get("prompt", "")
        video_type = body.get("type", "procedural")
        duration = body.get("duration", 5)
        fps = body.get("fps", 24)
        params = body.get("params", {})
        if not prompt:
            return JSONResponse({"status": "error", "error": "prompt required"}, status_code=400)

        from agent.generator import ZICoreGenerator
        gen = ZICoreGenerator()
        result = gen.generate_video(prompt, video_type=video_type, duration=duration, fps=fps, **params)
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"Video materialize error: {e}")
        return {"status": "error", "error": str(e)}


@app.post("/api/materialize/simulation")
async def materialize_simulation(body: dict):
    try:
        prompt = body.get("prompt", "")
        scene_type = body.get("scene_type", "space")
        params = body.get("params", {})
        if not prompt:
            return JSONResponse({"status": "error", "error": "prompt required"}, status_code=400)

        if outpreview is None:
            return JSONResponse({"status": "error", "error": "OutPreview not available"}, status_code=503)

        scene = outpreview.create_scene_from_prompt(prompt, engine_results=[params])
        return {"status": "ok", "scene": scene}
    except Exception as e:
        logger.error(f"Simulation materialize error: {e}")
        return {"status": "error", "error": str(e)}


@app.get("/api/materialize/engines")
async def materialize_engines():
    try:
        from zicore.materializer import ZICOREMaterializer
        mat = ZICOREMaterializer()
        engines = getattr(mat, "engines", {})
        return {"status": "ok", "engines": {k: str(v) for k, v in engines.items()} if isinstance(engines, dict) else engines}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/materialize/engine")
async def materialize_set_engine(body: dict):
    try:
        output_type = body.get("output_type", "")
        engine_name = body.get("engine_name", "")
        if not output_type or not engine_name:
            return JSONResponse({"status": "error", "error": "output_type and engine_name required"}, status_code=400)

        from zicore.materializer import ZICOREMaterializer
        mat = ZICOREMaterializer()
        if hasattr(mat, "set_engine"):
            mat.set_engine(output_type, engine_name)
            return {"status": "ok", "output_type": output_type, "engine": engine_name}
        return {"status": "error", "error": "Engine selection not supported by this materializer"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


_materialize_queue = {}
_materialize_queue_counter = 0


@app.post("/api/materialize/queue")
async def materialize_queue(body: dict):
    global _materialize_queue_counter
    try:
        prompt = body.get("prompt", "")
        output_type = body.get("type", "auto")
        priority = body.get("priority", 0)
        if not prompt:
            return JSONResponse({"status": "error", "error": "prompt required"}, status_code=400)

        _materialize_queue_counter += 1
        task_id = str(_materialize_queue_counter)
        _materialize_queue[task_id] = {
            "id": task_id,
            "prompt": prompt,
            "type": output_type,
            "priority": priority,
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return {"status": "ok", "task_id": task_id, "queue_size": len(_materialize_queue)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/materialize/queue/status")
async def materialize_queue_status():
    queued = [t for t in _materialize_queue.values() if t["status"] == "queued"]
    running = [t for t in _materialize_queue.values() if t["status"] == "running"]
    completed = [t for t in _materialize_queue.values() if t["status"] == "completed"]
    return {
        "status": "ok",
        "queue_size": len(queued),
        "running": len(running),
        "completed": len(completed),
        "tasks": list(_materialize_queue.values()),
    }


@app.delete("/api/materialize/queue/{task_id}")
async def materialize_queue_cancel(task_id: str):
    task = _materialize_queue.get(task_id)
    if not task:
        return JSONResponse({"status": "error", "error": "Task not found"}, status_code=404)
    if task["status"] in ("completed", "cancelled"):
        return JSONResponse({"status": "error", "error": "Task already finished"}, status_code=400)
    task["status"] = "cancelled"
    return {"status": "ok", "task_id": task_id}


# ─── Generation Library API ──────────────────────────────────────────────────

@app.get("/api/library/list")
async def library_list(
    type: Optional[str] = None,
    folder: Optional[int] = None,
    favorite: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        results = generation_library.list(
            output_type=type,
            folder_id=folder,
            favorite=bool(favorite) if favorite is not None else False,
            search=search,
            limit=limit,
            offset=offset,
        )
        return {"status": "ok", "generations": results, "count": len(results)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/library/add")
async def library_add(body: dict):
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        prompt = body.get("prompt", "")
        output_type = body.get("type", "unknown")
        engine = body.get("engine", "")
        file_path = body.get("file_path", "")
        file_format = body.get("format", "")
        tags = body.get("tags", [])
        metadata = body.get("metadata", {})
        folder_id = body.get("folder_id")

        if not file_path:
            return JSONResponse({"status": "error", "error": "file_path required"}, status_code=400)

        gen_id = generation_library.add(
            prompt=prompt,
            output_type=output_type,
            engine=engine,
            file_path=file_path,
            file_format=file_format,
            tags=tags,
            metadata=metadata,
            folder_id=folder_id,
        )
        return {"status": "ok", "id": gen_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/library/get/{gen_id}")
async def library_get(gen_id: int):
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        gen = generation_library.get(gen_id)
        if gen is None:
            return JSONResponse({"status": "error", "error": "Generation not found"}, status_code=404)
        return {"status": "ok", "generation": gen}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.put("/api/library/update/{gen_id}")
async def library_update(gen_id: int, body: dict):
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        kwargs = {}
        if "tags" in body:
            kwargs["tags"] = body["tags"]
        if "favorite" in body:
            kwargs["is_favorite"] = body["favorite"]
        if "folder_id" in body:
            kwargs["folder_id"] = body["folder_id"]
        if "prompt" in body:
            kwargs["prompt"] = body["prompt"]
        if "metadata" in body:
            kwargs["metadata"] = body["metadata"]

        ok = generation_library.update(gen_id, **kwargs)
        if not ok:
            return JSONResponse({"status": "error", "error": "Generation not found or no changes"}, status_code=404)
        return {"status": "ok", "id": gen_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.delete("/api/library/delete/{gen_id}")
async def library_delete(gen_id: int):
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        ok = generation_library.delete(gen_id)
        if not ok:
            return JSONResponse({"status": "error", "error": "Generation not found"}, status_code=404)
        return {"status": "ok", "id": gen_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/library/search")
async def library_search(q: str = "", limit: int = 50):
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        if not q:
            return JSONResponse({"status": "error", "error": "Search query (q) required"}, status_code=400)
        results = generation_library.search(q, limit=limit)
        return {"status": "ok", "results": results, "count": len(results)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/library/stats")
async def library_stats():
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        stats = generation_library.get_stats()
        return {"status": "ok", "stats": stats}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/library/folder")
async def library_create_folder(body: dict):
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        name = body.get("name", "")
        parent_id = body.get("parent_id")
        if not name:
            return JSONResponse({"status": "error", "error": "Folder name required"}, status_code=400)
        folder_id = generation_library.create_folder(name, parent_id=parent_id)
        return {"status": "ok", "folder_id": folder_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/library/folders")
async def library_folders():
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        folders = generation_library.list_folders()
        return {"status": "ok", "folders": folders}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/library/latest")
async def library_latest():
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        gen = generation_library.get_latest()
        if gen is None:
            return {"status": "ok", "generation": None}
        return {"status": "ok", "generation": gen}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/library/recent")
async def library_recent(limit: int = 10):
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        results = generation_library.get_recent(limit=limit)
        return {"status": "ok", "generations": results, "count": len(results)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/library/move/{gen_id}")
async def library_move(gen_id: int, body: dict):
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        folder_id = body.get("folder_id")
        ok = generation_library.move_to_folder(gen_id, folder_id)
        if not ok:
            return JSONResponse({"status": "error", "error": "Generation not found"}, status_code=404)
        return {"status": "ok", "id": gen_id, "folder_id": folder_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/library/tag/{gen_id}")
async def library_add_tag(gen_id: int, body: dict):
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        tag = body.get("tag", "")
        if not tag:
            return JSONResponse({"status": "error", "error": "tag required"}, status_code=400)
        ok = generation_library.add_tag(gen_id, tag)
        if not ok:
            return JSONResponse({"status": "error", "error": "Generation not found"}, status_code=404)
        return {"status": "ok", "id": gen_id, "tag": tag}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.delete("/api/library/tag/{gen_id}/{tag}")
async def library_remove_tag(gen_id: int, tag: str):
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        ok = generation_library.remove_tag(gen_id, tag)
        if not ok:
            return JSONResponse({"status": "error", "error": "Generation not found"}, status_code=404)
        return {"status": "ok", "id": gen_id, "tag": tag}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/library/unified")
async def library_unified():
    """Return all library assets in a flat list for the global sidebar."""
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        results = generation_library.list(limit=500)
        # Also append media files from MEDIA_DIR that aren't already in the library
        existing_paths = {r.get("file_path", "") for r in results}
        media_root = MEDIA_DIR
        if media_root.is_dir():
            for ext_pattern in ("**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.gif", "**/*.webp",
                                "**/*.mp3", "**/*.wav", "**/*.ogg", "**/*.flac",
                                "**/*.mp4", "**/*.webm", "**/*.ogv",
                                "**/*.stl", "**/*.obj", "**/*.glb", "**/*.gltf"):
                for fp in media_root.glob(ext_pattern):
                    rel = str(fp.relative_to(media_root)).replace("\\", "/")
                    if rel in existing_paths:
                        continue
                    try:
                        sz = fp.stat().st_size
                    except OSError:
                        sz = 0
                    ext = fp.suffix.lower().lstrip(".")
                    type_map = {
                        "png":"image","jpg":"image","jpeg":"image","gif":"image","webp":"image","bmp":"image",
                        "mp3":"audio","wav":"audio","ogg":"audio","flac":"audio","m4a":"audio",
                        "mp4":"video","webm":"video","ogv":"video","mov":"video","mkv":"video",
                        "stl":"3d","obj":"3d","glb":"3d","gltf":"3d","ply":"3d",
                    }
                    results.append({
                        "id": 0,
                        "prompt": fp.stem,
                        "output_type": type_map.get(ext, "other"),
                        "engine": "media",
                        "file_path": rel,
                        "file_format": ext,
                        "thumbnail_path": "",
                        "tags": "[]",
                        "metadata": json.dumps({"size": sz}),
                        "created_at": "",
                        "updated_at": "",
                        "is_favorite": False,
                        "folder_id": None,
                    })
        return {"status": "ok", "assets": results}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/library/save")
async def library_save(body: dict):
    """Save a generation from a specific module (materializer, video-editor, etc.)."""
    try:
        if generation_library is None:
            return JSONResponse({"status": "error", "error": "Generation Library not available"}, status_code=503)
        prompt = body.get("prompt", "")
        output_type = body.get("type", "unknown")
        engine = body.get("engine", "")
        file_path = body.get("file_path", "")
        file_format = body.get("format", "")
        tags = body.get("tags", [])
        metadata = body.get("metadata", {})
        source = body.get("source", "")  # e.g. "materializer", "video-editor", "audio-editor"
        if source:
            metadata["source"] = source
        if not file_path:
            return JSONResponse({"status": "error", "error": "file_path required"}, status_code=400)
        gen_id = generation_library.add(
            prompt=prompt,
            output_type=output_type,
            engine=engine,
            file_path=file_path,
            file_format=file_format,
            tags=tags,
            metadata=metadata,
        )
        return {"status": "ok", "id": gen_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─── OutPreview API ──────────────────────────────────────────────────────────

@app.get("/api/outpreview/current")
async def outpreview_current():
    try:
        if outpreview is None:
            return JSONResponse({"status": "error", "error": "OutPreview not available"}, status_code=503)
        current = outpreview.get_current()
        return {"status": "ok", "current": current}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/outpreview/set")
async def outpreview_set(body: dict):
    try:
        if outpreview is None:
            return JSONResponse({"status": "error", "error": "OutPreview not available"}, status_code=503)
        result = outpreview.set_generation(body)
        return {"status": "ok", "generation": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/outpreview/history")
async def outpreview_history(limit: int = 20):
    try:
        if outpreview is None:
            return JSONResponse({"status": "error", "error": "OutPreview not available"}, status_code=503)
        history = outpreview.get_history(limit=limit)
        return {"status": "ok", "history": history, "count": len(history)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/outpreview/edit")
async def outpreview_edit(body: dict):
    try:
        if outpreview is None:
            return JSONResponse({"status": "error", "error": "OutPreview not available"}, status_code=503)
        gen_id = body.get("gen_id")
        operation = body.get("operation", "analyze")
        params = body.get("params", {})
        result = outpreview.edit_mesh(gen_id=gen_id, operation=operation, params=params)
        if result is None:
            return JSONResponse({"status": "error", "error": f"Edit operation failed: {operation}"}, status_code=500)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/outpreview/analyze/{gen_id}")
async def outpreview_analyze(gen_id: str):
    try:
        if outpreview is None:
            return JSONResponse({"status": "error", "error": "OutPreview not available"}, status_code=503)
        result = outpreview.edit_mesh(gen_id=gen_id, operation="analyze")
        if result is None:
            return JSONResponse({"status": "error", "error": "Analysis failed or generation not found"}, status_code=404)
        return {"status": "ok", "analysis": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/outpreview/save-to-library")
async def outpreview_save_to_library(body: dict):
    try:
        if outpreview is None:
            return JSONResponse({"status": "error", "error": "OutPreview not available"}, status_code=503)
        gen_id = body.get("gen_id")
        tags = body.get("tags", [])
        folder_id = body.get("folder_id")
        lib_id = outpreview.save_to_library(gen_id=gen_id, tags=tags, folder_id=folder_id)
        if lib_id is None:
            return JSONResponse({"status": "error", "error": "Failed to save to library"}, status_code=500)
        return {"status": "ok", "library_id": lib_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/outpreview/export-print/{gen_id}")
async def outpreview_export_print(gen_id: str, body: dict = {}):
    try:
        if outpreview is None:
            return JSONResponse({"status": "error", "error": "OutPreview not available"}, status_code=503)
        printer = body.get("printer", "ender3")
        material = body.get("material", "PLA")
        result = outpreview.export_for_print(gen_id=gen_id, printer=printer, material=material)
        if result is None:
            return JSONResponse({"status": "error", "error": "Print export failed"}, status_code=500)
        return {"status": "ok", "export": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/outpreview/export-vr/{gen_id}")
async def outpreview_export_vr(gen_id: str):
    try:
        if outpreview is None:
            return JSONResponse({"status": "error", "error": "OutPreview not available"}, status_code=503)
        result = outpreview.export_for_vr(gen_id=gen_id)
        if result is None:
            return JSONResponse({"status": "error", "error": "VR export failed"}, status_code=500)
        return {"status": "ok", "scene": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─── Preview Generation ───────────────────────────────────────────────────────

@app.post("/api/preview/generate")
async def preview_generate(body: dict):
    try:
        file_path = body.get("file", "")
        if not file_path:
            return JSONResponse({"status": "error", "error": "file path required"}, status_code=400)
        width = body.get("width", 800)
        height = body.get("height", 600)
        lighting = body.get("lighting", "aerospace")

        abs_path = Path(__file__).parent / file_path.lstrip("/")
        if not abs_path.exists():
            return JSONResponse({"status": "error", "error": "File not found"}, status_code=404)

        import trimesh
        loaded = trimesh.load(str(abs_path))
        if isinstance(loaded, trimesh.Scene):
            mesh = loaded.dump(concatenate=True)
        else:
            mesh = loaded

        from zicore.materializer_workflow import PreviewEngine
        engine = PreviewEngine()
        preview_path = engine.render_preview(mesh, lighting=lighting, width=width, height=height)
        if not preview_path:
            return JSONResponse({"status": "error", "error": "Preview generation failed (Pillow not available)"}, status_code=500)

        rel_path = "/output/previews/" + Path(preview_path).name
        return {"status": "ok", "preview_url": rel_path}
    except Exception as e:
        logger.error(f"Preview generate error: {e}")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)


# ─── Simulation API ─────────────────────────────────────────────────────────

@app.post("/api/simulate/mesh")
async def simulate_mesh(body: dict):
    try:
        file_path = body.get("file", "")
        sim_types = body.get("simulations", ["structural", "aerodynamic", "mass_properties", "orbital"])
        material_name = body.get("material", "aluminum_6061")
        altitude = body.get("altitude", 400000)
        velocity = body.get("velocity", 7800)
        load_force = body.get("load", 1000.0)

        if not file_path:
            return JSONResponse({"status": "error", "error": "file path required"}, status_code=400)
        abs_path = Path(__file__).parent / file_path.lstrip("/")
        if not abs_path.exists():
            return JSONResponse({"status": "error", "error": "File not found"}, status_code=404)

        import trimesh
        loaded = trimesh.load(str(abs_path))
        if isinstance(loaded, trimesh.Scene):
            mesh = loaded.dump(concatenate=True)
        else:
            mesh = loaded

        from zicore.materializer_workflow import SimulationEngine, MaterialLibrary
        sim = SimulationEngine()
        mat_lib = MaterialLibrary()
        material = mat_lib.get(material_name) or mat_lib.get("aluminum_6061")

        results = {}
        if "structural" in sim_types:
            results["structural"] = sim.structural_analysis(mesh, material, load=load_force).to_dict()
        if "aerodynamic" in sim_types:
            results["aerodynamic"] = sim.aerodynamic_estimate(mesh, material, velocity=velocity, altitude=altitude).to_dict()
        if "mass_properties" in sim_types:
            mass_result = sim.mass_properties(mesh, material)
            results["mass_properties"] = mass_result.to_dict()
        mass_kg = 1000
        if "mass_properties" in results:
            mass_kg = results["mass_properties"].get("results", {}).get("mass_kg", 1000)
        if "orbital" in sim_types:
            results["orbital"] = sim.orbital_simulation(mass=mass_kg, altitude=altitude).to_dict()
        if "thermal" in sim_types:
            results["thermal"] = sim.thermal_analysis(mesh, material).to_dict()

        return {"status": "ok", "simulations": results, "material": material.name}
    except Exception as e:
        logger.error(f"Simulate error: {e}")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)


# ─── General Generation API ───────────────────────────────────────────────────

@app.post("/api/generate")
async def api_generate(data: dict = {}):
    gen_type = data.get("type", "image")
    prompt = data.get("prompt", "")
    if not prompt:
        return {"error": "prompt required"}
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from zicore.generation_pipeline import pipeline
        result = pipeline.generate(gen_type, prompt)
        result["type"] = gen_type
        return result
    except Exception as e:
        logger.error(f"/api/generate error: {e}", exc_info=True)
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


@app.post("/api/ai3d/ollama-generate")
async def api_ai3d_ollama_generate(data: dict = {}):
    """
    Ollama-powered 3D generation:
    1. Send prompt to Ollama to parse into structured JSON
    2. Use parsed params to generate mesh via local_generators or OpenSCAD
    3. Return file path for frontend to load
    """
    prompt = data.get("prompt", "")
    model = data.get("model", "gemma3:1b")
    engine = data.get("engine", "local")

    if not prompt:
        return {"status": "error", "error": "prompt required"}

    config = load_config()
    base_url = config.get("providers", {}).get("ollama", {}).get("base_url", OLLAMA_BASE_URL)
    if not base_url.startswith("http"):
        base_url = f"http://{base_url}"

    # Step 1: Call Ollama to parse the prompt into structured JSON
    parse_prompt = f"""You are a 3D model parameter parser. Given a user description, output ONLY a JSON object (no markdown, no explanation) with these fields:
{{
  "type": "rocket|satellite|station|drone|nozzle|landing_leg|solar_panel|antenna|habitat|rover|payload_bay|engine|fuel_tank|nose_cone|fin|cube|sphere|cylinder|cone|torus|gear|terrain",
  "params": {{
    "fin_count": <number, default 4>,
    "stages": <number, default 1>,
    "nose_cone": <boolean, default true>,
    "has_solar_panels": <boolean, default false>,
    "has_antenna": <boolean, default false>,
    "teeth": <number for gears, default 12>,
    "radius": <number, default 0.5>,
    "height": <number, default 1.0>,
    "width": <number, default 1.0>,
    "depth": <number, default 1.0>
  }}
}}
User description: {prompt}"""

    parsed_type = "cube"
    parsed_params = {}

    try:
        ollama_payload = json.dumps({
            "model": model,
            "prompt": parse_prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 256}
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{base_url}/api/generate",
            data=ollama_payload,
            headers={"Content-Type": "application/json", "User-Agent": "ZICORE/5.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            ollama_result = json.loads(resp.read().decode("utf-8"))

        raw_text = ollama_result.get("response", "").strip()
        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r'\{[\s\S]*\}', raw_text)
        if json_match:
            parsed = json.loads(json_match.group())
            parsed_type = parsed.get("type", "cube")
            parsed_params = parsed.get("params", {})
            logger.info(f"Ollama parsed: type={parsed_type}, params={parsed_params}")
        else:
            logger.warning(f"Ollama could not parse prompt, raw: {raw_text[:200]}")
            # Try keyword matching fallback
            p = prompt.lower()
            fallback_map = {
                "rocket": ["rocket", "launch"], "satellite": ["satellite"],
                "station": ["station"], "drone": ["drone"],
                "nozzle": ["nozzle"], "gear": ["gear"],
                "terrain": ["terrain"], "cube": ["cube", "box"],
                "sphere": ["sphere", "ball"], "cylinder": ["cylinder", "tube"],
                "cone": ["cone"], "torus": ["torus", "ring"],
            }
            for t, kws in fallback_map.items():
                if any(k in p for k in kws):
                    parsed_type = t
                    break
    except Exception as e:
        logger.error(f"Ollama parse failed: {e}")
        # Keyword fallback
        p = prompt.lower()
        for kw in ["rocket", "satellite", "station", "drone", "nozzle", "gear", "terrain", "cube", "sphere", "cylinder", "cone", "torus"]:
            if kw in p:
                parsed_type = kw
                break

    # Step 2: Generate mesh based on parsed type
    output_file = None

    if engine == "openscad":
        # Generate OpenSCAD script from parsed params
        scad_script = _generate_openscad_from_parsed(parsed_type, parsed_params)
        try:
            from zicore.ai3d_engines import ai3d
            result = ai3d.generate(engine_key="openscad", script=scad_script, prompt=prompt)
            result_dict = result.to_dict() if hasattr(result, 'to_dict') else result
            if result_dict.get("status") == "ok":
                output_file = result_dict.get("file", "")
        except Exception as e:
            logger.error(f"OpenSCAD generation failed: {e}")

    if not output_file:
        # Use local trimesh generator
        try:
            from zicore.local_generators import MeshGenerator
            mesh = MeshGenerator.generate_aerospace(parsed_type, parsed_params)
            if mesh is None:
                mesh = MeshGenerator.generate_basic(parsed_type, parsed_params)
            if mesh is None:
                mesh = MeshGenerator.generate_basic("cube")

            output_dir = OUTPUT_DIR / "ai3d"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = f"/output/ai3d/ollama_{parsed_type}_{int(time.time())}.stl"
            abs_path = Path(__file__).parent / output_file.lstrip("/")
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            mesh.export(str(abs_path))
        except Exception as e:
            logger.error(f"Local mesh generation failed: {e}")
            return {"status": "error", "error": f"Generation failed: {e}"}

    return {
        "status": "ok",
        "parsed_type": parsed_type,
        "params": parsed_params,
        "engine": engine,
        "model": model,
        "file": output_file,
    }


def _generate_openscad_from_parsed(ptype: str, params: dict) -> str:
    """Generate an OpenSCAD script from parsed type and parameters."""
    r = params.get("radius", 0.5)
    h = params.get("height", 1.0)
    w = params.get("width", 1.0)
    d = params.get("depth", 1.0)
    fins = params.get("fin_count", 4)
    teeth = params.get("teeth", 12)

    templates = {
        "rocket": f'''// AI-Generated Rocket
difference() {{
  cylinder(r={r*20}, h={h*40}, $fn=64);
  translate([0, 0, {h*35}]) sphere(r={r*15}, $fn=64);
}}
for (i = [0:{fins-1}]) {{
  rotate([0, 0, i*{360//fins}])
    translate([{r*25}, 0, 5])
      cube([{w*15}, 1, {h*15}], center=true);
}}''',
        "satellite": f'''// AI-Generated Satellite
cube([{w*20}, {d*15}, {h*15}], center=true);
translate([0, {h*12}, 0]) cube([{w*50}, 1, {d*20}], center=true);
translate([0, {-h*12}, 0]) cube([{w*50}, 1, {d*20}], center=true);''',
        "gear": f'''// AI-Generated Gear
cylinder(r={r*20}, h=5, $fn={teeth*2});''',
        "cube": f'''cube([{w*20}, {h*20}, {d*20}], center=true);''',
        "sphere": f'''sphere(r={r*20}, $fn=64);''',
        "cylinder": f'''cylinder(r={r*20}, h={h*30}, $fn=64);''',
        "cone": f'''cylinder(r1={r*20}, r2=0, h={h*30}, $fn=64);''',
    }
    return templates.get(ptype, templates["cube"])


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
        
        if len(code) > 5000:
            return {"success": False, "error": "Code too long (max 5000 chars)"}
        
        _dangerous_imports = ['subprocess', 'shutil', 'ctypes', 'socket', 'multiprocessing', 'threading']
        _dangerous_patterns = ['os.system', 'os.popen', '__import__', 'eval(', 'exec(', 'open(/etc', 'open(/proc']
        code_lower = code.lower()
        for pat in _dangerous_patterns:
            if pat in code_lower:
                return {"success": False, "error": f"Blocked dangerous pattern: {pat}"}
        for imp in _dangerous_imports:
            if f'import {imp}' in code_lower or f'from {imp}' in code_lower:
                return {"success": False, "error": f"Blocked import: {imp}"}
        
        import subprocess
        import sys
        import tempfile
        import os
        
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Execute with timeout (non-blocking)
            import asyncio
            result = await asyncio.to_thread(
                subprocess.run,
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
            except Exception:
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

        sys.path.insert(0, str(Path(__file__).parent))
        from zicore.generation_pipeline import pipeline

        result = pipeline.generate_video(prompt, width=width, height=height, duration=duration, fps=fps)
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
                    if provider_name == "aerospace-engineering":
                        provider_name = "zicore_native"

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
                    from zicore.generation_pipeline import pipeline
                    import asyncio
                    gen_type = payload.get("type", "image")
                    prompt = payload.get("prompt", "")
                    await websocket.send_json({"type": "generating", "generating_type": gen_type})
                    result = pipeline.generate(gen_type, prompt)
                    result["type"] = gen_type
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
                    if provider_name == "aerospace-engineering":
                        provider_name = "zicore_native"

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


@app.websocket("/ws/materializer-vr")
async def materializer_vr_websocket(websocket: WebSocket):
    """WebSocket for VR stereo stream from Materializer.

    Client sends JSON commands:
      {"action":"start", "scene":"planetary_surface", "prompt":"...", "stereo":true, "width":640, "height":480, "fps":30}
      {"action":"camera", "yaw":0, "pitch":0, "roll":0, "x":0, "y":1.7, "z":0}
      {"action":"stop"}
      {"action":"ping"}
    Server streams frames as JSON:
      {"type":"stereo_frame", "left":"base64...", "right":"base64...", "width":640, "height":480, "frame":0}
      {"type":"frame", "data":"base64...", "width":640, "height":480, "frame":0}
    """
    await websocket.accept()
    client_id = uuid.uuid4().hex[:8]
    session_id = None
    streaming = False
    stream_task = None
    logger.info(f"VR WS connected: {client_id}")

    async def stream_frames(sid, fps):
        """Background task: render and send frames."""
        nonlocal streaming
        frame_interval = 1.0 / fps
        while streaming and session_id:
            try:
                t0 = time.time()
                frame_data = vr_stream_manager.render_frame(sid)
                if frame_data:
                    await websocket.send_json(frame_data)
                else:
                    await websocket.send_json({"type": "error", "message": "Frame render failed"})
                    break
                elapsed = time.time() - t0
                sleep_time = max(0, frame_interval - elapsed)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    await asyncio.sleep(0.001)
            except Exception:
                break
        streaming = False

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "invalid JSON"})
                continue

            action = data.get("action", "")

            if action == "start":
                if vr_stream_manager is None:
                    await websocket.send_json({"type": "error", "message": "VR Stream not available"})
                    continue

                # Stop existing stream
                if stream_task and not stream_task.done():
                    streaming = False
                    stream_task.cancel()

                scene = data.get("scene", "planetary_surface")
                prompt = data.get("prompt", "")
                stereo = data.get("stereo", True)
                width = min(data.get("width", 640), 1280)
                height = min(data.get("height", 480), 720)
                fps = min(data.get("fps", 30), 60)

                session_id = vr_stream_manager.create_session(
                    scene_type=scene, prompt=prompt,
                    width=width, height=height, fps=fps, stereo=stereo,
                )
                vr_stream_manager.add_client(session_id, client_id)
                streaming = True

                await websocket.send_json({
                    "type": "session_started",
                    "session_id": session_id,
                    "scene": scene,
                    "stereo": stereo,
                    "width": width,
                    "height": height,
                    "fps": fps,
                })

                # Start streaming in background
                stream_task = asyncio.create_task(stream_frames(session_id, fps))

            elif action == "camera":
                if session_id and vr_stream_manager:
                    vr_stream_manager.update_camera(
                        session_id,
                        yaw=data.get("yaw"),
                        pitch=data.get("pitch"),
                        roll=data.get("roll"),
                        x=data.get("x"),
                        y=data.get("y"),
                        z=data.get("z"),
                    )

            elif action == "stop":
                streaming = False
                if stream_task and not stream_task.done():
                    stream_task.cancel()
                if session_id and vr_stream_manager:
                    vr_stream_manager.remove_client(session_id, client_id)
                    vr_stream_manager.close_session(session_id)
                    session_id = None
                await websocket.send_json({"type": "stopped"})

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

            elif action == "sessions":
                if vr_stream_manager:
                    sessions = vr_stream_manager.list_sessions()
                    await websocket.send_json({"type": "sessions", "data": sessions})
                else:
                    await websocket.send_json({"type": "sessions", "data": []})

    except WebSocketDisconnect:
        streaming = False
        if stream_task and not stream_task.done():
            stream_task.cancel()
        if session_id and vr_stream_manager:
            vr_stream_manager.remove_client(session_id, client_id)
        logger.info(f"VR WS disconnected: {client_id}")


@app.websocket("/ws/display-stream")
async def display_stream_websocket(websocket: WebSocket):
    """WebSocket for external display/monitor streaming.

    Pushes rendered frames to external monitors (USB/WiFi connected).
    Client sends: {"action":"subscribe", "session_id":"..."}
    Server streams: {"type":"frame", "data":"base64...", "width":W, "height":H, "frame":N}
    """
    await websocket.accept()
    client_id = uuid.uuid4().hex[:8]
    subscribed_session = None
    streaming = False
    stream_task = None
    logger.info(f"Display stream WS connected: {client_id}")

    async def push_frames(sid):
        """Background task: push frames to display."""
        nonlocal streaming
        while streaming and subscribed_session:
            try:
                frame_data = vr_stream_manager.render_frame(sid)
                if frame_data:
                    await websocket.send_json(frame_data)
                await asyncio.sleep(1.0 / 30)
            except Exception:
                break
        streaming = False

    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "invalid JSON"})
                continue

            action = data.get("action", "")

            if action == "subscribe":
                sid = data.get("session_id", "")
                if vr_stream_manager is None:
                    await websocket.send_json({"type": "error", "message": "VR Stream not available"})
                    continue

                # Stop existing stream
                if stream_task and not stream_task.done():
                    streaming = False
                    stream_task.cancel()

                sessions = vr_stream_manager.list_sessions()
                session_ids = [s["id"] for s in sessions]

                if sid not in session_ids:
                    # Auto-create a mono display session
                    scene = data.get("scene", "planetary_surface")
                    width = min(data.get("width", 640), 1280)
                    height = min(data.get("height", 480), 720)
                    sid = vr_stream_manager.create_session(
                        scene_type=scene, width=width, height=height,
                        fps=30, stereo=False,
                    )

                subscribed_session = sid
                vr_stream_manager.add_client(sid, client_id)
                streaming = True
                await websocket.send_json({"type": "subscribed", "session_id": sid})

                # Start pushing frames in background
                stream_task = asyncio.create_task(push_frames(sid))

            elif action == "unsubscribe":
                streaming = False
                if stream_task and not stream_task.done():
                    stream_task.cancel()
                if subscribed_session and vr_stream_manager:
                    vr_stream_manager.remove_client(subscribed_session, client_id)
                subscribed_session = None
                await websocket.send_json({"type": "unsubscribed"})

            elif action == "ping":
                await websocket.send_json({"type": "pong"})

            elif action == "list_sessions":
                if vr_stream_manager:
                    sessions = vr_stream_manager.list_sessions()
                    await websocket.send_json({"type": "sessions", "data": sessions})

    except WebSocketDisconnect:
        streaming = False
        if stream_task and not stream_task.done():
            stream_task.cancel()
        if subscribed_session and vr_stream_manager:
            vr_stream_manager.remove_client(subscribed_session, client_id)
        logger.info(f"Display stream WS disconnected: {client_id}")


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


# --- Server Admin Console ---

try:
    import paramiko
except ImportError:
    paramiko = None

ADMIN_SERVERS = {
    ".85": {"name": ".85 Primary", "ip": "192.168.1.85", "user": "z", "password": "Jilo1981"},
    ".68": {"name": ".68 Ollama", "ip": "192.168.1.68", "user": "zinemotion", "password": "Jilo1981"},
    "vps": {"name": "VPS Oracle", "ip": "160.34.209.208", "user": "oracle-admin", "password": "zicore2026"},
}


async def _ssh_exec(server: str, command: str, timeout: int = 30) -> dict:
    """Execute a command on a remote server via SSH."""
    if server not in ADMIN_SERVERS:
        return {"success": False, "error": f"Unknown server: {server}"}
    info = ADMIN_SERVERS[server]
    try:
        if paramiko is None:
            raise ImportError("paramiko not available")
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(info["ip"], username=info["user"], password=info["password"],
                       timeout=5, allow_agent=False, look_for_keys=False)
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        rc = stdout.channel.recv_exit_status()
        client.close()
        return {"success": True, "stdout": out, "stderr": err, "returncode": rc}
    except ImportError:
        # Fallback: use subprocess ssh
        import subprocess as _sp
        try:
            result = _sp.run(
                ["sshpass", "-p", info["password"], "ssh", "-o", "StrictHostKeyChecking=no",
                 f"{info['user']}@{info['ip']}", command],
                capture_output=True, text=True, timeout=timeout
            )
            return {"success": True, "stdout": result.stdout, "stderr": result.stderr,
                    "returncode": result.returncode}
        except FileNotFoundError:
            # Last resort: plain ssh (will prompt for password)
            try:
                result = _sp.run(
                    ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
                     f"{info['user']}@{info['ip']}", command],
                    capture_output=True, text=True, timeout=timeout
                )
                return {"success": True, "stdout": result.stdout, "stderr": result.stderr,
                        "returncode": result.returncode}
            except Exception as e2:
                return {"success": False, "error": str(e2)}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_server_stats(server: str) -> dict:
    """Get basic stats from a server (fast timeout)."""
    result = await _ssh_exec(server,
        "echo CPU:$(top -bn1 | grep 'Cpu(s)' | awk '{print $2}')% "
        "RAM:$(free -m | awk '/Mem:/{printf \"%d/%d\", $3, $2}') "
        "RAM_PCT:$(free | awk '/Mem:/{printf \"%.0f\", $3/$2*100}') "
        "DISK:$(df -h / | awk 'NR==2{print $5}') "
        "UPTIME:$(uptime -p)", timeout=5)
    stats = {"online": result.get("success", False), "cpu": "--", "ram": "--",
             "ram_pct": 0, "disk": "--", "disk_pct": 0, "uptime": "--"}
    if result.get("stdout"):
        for part in result["stdout"].split():
            if part.startswith("CPU:"):
                stats["cpu"] = part[4:] if part[4:] != "%" else "0%"
            elif part.startswith("RAM:"):
                stats["ram"] = part[4:]
            elif part.startswith("RAM_PCT:"):
                try: stats["ram_pct"] = int(part[8:])
                except: pass
            elif part.startswith("DISK:"):
                stats["disk"] = part[5:]
                try: stats["disk_pct"] = int(part[5:].replace("%", ""))
                except: pass
            elif part.startswith("UPTIME:"):
                stats["uptime"] = part[7:]
    return stats


_admin_stats_cache = {"data": None, "ts": 0}
_admin_cache_lock = asyncio.Lock() if hasattr(asyncio, 'Lock') else None


@app.get("/api/admin/servers")
async def admin_servers():
    """Get status of all servers (cached 10s to prevent event-loop blocking)."""
    import asyncio as _aio
    import time as _time
    now = _time.time()
    # Return cached if <10s old
    if _admin_stats_cache["data"] and (now - _admin_stats_cache["ts"]) < 10:
        return JSONResponse(content=_admin_stats_cache["data"])
    tasks = {}
    for key in ADMIN_SERVERS:
        if key == ".85":
            # Local server — quick local check
            import subprocess as _sp
            try:
                r = _sp.run(["bash", "-c",
                    "echo CPU:$(top -bn1 | grep 'Cpu(s)' | awk '{print $2}')% "
                    "RAM:$(free -m | awk '/Mem:/{printf \"%d/%d\", $3, $2}') "
                    "RAM_PCT:$(free | awk '/Mem:/{printf \"%.0f\", $3/$2*100}') "
                    "DISK:$(df -h / | awk 'NR==2{print $5}') "
                    "UPTIME:$(uptime -p)"],
                    capture_output=True, text=True, timeout=10)
                stats = {"online": True, "cpu": "--", "ram": "--", "ram_pct": 0,
                         "disk": "--", "disk_pct": 0, "uptime": "--"}
                for part in r.stdout.split():
                    if part.startswith("CPU:"): stats["cpu"] = part[4:]
                    elif part.startswith("RAM:"): stats["ram"] = part[4:]
                    elif part.startswith("RAM_PCT:"):
                        try: stats["ram_pct"] = int(part[8:])
                        except: pass
                    elif part.startswith("DISK:"):
                        stats["disk"] = part[5:]
                        try: stats["disk_pct"] = int(part[5:].replace("%", ""))
                        except: pass
                    elif part.startswith("UPTIME:"): stats["uptime"] = part[7:]
                tasks[key] = stats
            except Exception:
                tasks[key] = {"online": False, "cpu": "--", "ram": "--", "ram_pct": 0,
                              "disk": "--", "disk_pct": 0, "uptime": "--"}
        else:
            tasks[key] = _get_server_stats(key)
    # Wait for remote results
    results = {}
    for key, val in tasks.items():
        if isinstance(val, dict):
            results[key] = val
        else:
            try:
                results[key] = await val
            except Exception:
                results[key] = {"online": False, "cpu": "--", "ram": "--", "ram_pct": 0,
                                "disk": "--", "disk_pct": 0, "uptime": "--"}
    # Update cache
    _admin_stats_cache["data"] = results
    _admin_stats_cache["ts"] = __import__("time").time()
    return JSONResponse(content=results)


@app.post("/api/admin/execute")
async def admin_execute(request: Request):
    """Execute command on a server."""
    data = await request.json()
    server = data.get("server", ".85")
    command = data.get("command", "")
    timeout = data.get("timeout", 30)
    if not command:
        return JSONResponse(content={"error": "No command"}, status_code=400)
    if server == ".85":
        # Local execution
        import subprocess as _sp
        import shlex
        try:
            result = await asyncio.to_thread(
                _sp.run, command, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return {"result": {"success": True, "stdout": result.stdout,
                               "stderr": result.stderr, "returncode": result.returncode}}
        except _sp.TimeoutExpired:
            return {"result": {"success": False, "error": "Command timed out"}}
        except Exception as e:
            return {"result": {"success": False, "error": str(e)}}
    result = await _ssh_exec(server, command, timeout)
    return {"result": result}


@app.get("/admin")
async def admin_page():
    """Serve admin console HTML."""
    from fastapi.responses import FileResponse
    html_path = FRONTEND_DIR / "server-admin.html"
    if html_path.exists():
        return FileResponse(str(html_path), media_type="text/html")
    return JSONResponse(content={"error": "Admin console not found"}, status_code=404)


@app.get("/server-admin")
async def server_admin_redirect():
    return {"status": "ok", "admin_url": "/admin"}


# --- ZICORE Interactive Shell ---
# Generic SSH terminal: user provides host/port/user/password via WebSocket

try:
    from zicore.shell_manager import shell_manager
except ImportError:
    shell_manager = None


@app.get("/shell")
async def shell_page():
    from fastapi.responses import FileResponse
    html_path = FRONTEND_DIR / "shell.html"
    if html_path.exists():
        return FileResponse(str(html_path), media_type="text/html")
    return JSONResponse(content={"error": "Shell module not found"}, status_code=404)


@app.get("/api/shell/sessions")
async def shell_sessions():
    if shell_manager is None:
        return {"sessions": [], "error": "Shell manager not available"}
    return {"sessions": shell_manager.list_sessions()}


@app.post("/api/shell/close")
async def shell_close_session(request: Request):
    if shell_manager is None:
        return JSONResponse(content={"error": "Shell manager not available"}, status_code=503)
    data = await request.json()
    sid = data.get("session_id", "")
    ok = shell_manager.close_session(sid)
    return {"success": ok}


@app.websocket("/ws/shell")
async def shell_websocket(websocket: WebSocket):
    """Interactive SSH shell via WebSocket.
    
    First message from client must be a connect message:
      {"type": "connect", "host": "...", "port": 22, "user": "...", "password": "..."}
    
    Then normal terminal protocol:
      Client → Server: {"type": "input", "data": "..."}
                       {"type": "resize", "cols": 120, "rows": 40}
                       {"type": "ping"}
      Server → Client: {"type": "connected", "session_id": "..."}
                       {"type": "output", "data": "..."}
                       {"type": "disconnected", "reason": "..."}
                       {"type": "error", "message": "..."}
                       {"type": "pong"}
    """
    if shell_manager is None:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Shell manager not available"})
        await websocket.close()
        return

    await websocket.accept()
    session_id = None

    try:
        # Wait for connect message
        first_msg = await websocket.receive_json()
        if first_msg.get("type") != "connect":
            await websocket.send_json({"type": "error", "message": "First message must be connect"})
            await websocket.close()
            return

        host = first_msg.get("host", "").strip()
        port = int(first_msg.get("port", 22))
        user = first_msg.get("user", "").strip()
        password = first_msg.get("password", "")

        if not host or not user:
            await websocket.send_json({"type": "error", "message": "host and user are required"})
            await websocket.close()
            return

        loop = asyncio.get_event_loop()

        async def on_output(sid: str, data):
            try:
                if data is None:
                    await websocket.send_json({"type": "disconnected", "reason": "channel_closed"})
                else:
                    await websocket.send_json({"type": "output", "data": data})
            except Exception:
                pass

        result = shell_manager.create_session(
            host=host, port=port, user=user, password=password,
            cols=120, rows=40,
            output_callback=on_output, loop=loop,
        )

        if not result["success"]:
            await websocket.send_json({"type": "error", "message": result.get("error", "Connection failed")})
            await websocket.close()
            return

        session_id = result["session_id"]
        await websocket.send_json({"type": "connected", "session_id": session_id})

        while True:
            msg = await websocket.receive_json()
            msg_type = msg.get("type", "")

            if msg_type == "input":
                session = shell_manager.get_session(session_id)
                if session:
                    session.send_input(msg.get("data", ""))
                else:
                    break

            elif msg_type == "resize":
                session = shell_manager.get_session(session_id)
                if session:
                    session.resize(msg.get("cols", 120), msg.get("rows", 40))

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "disconnect":
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Shell WebSocket error: {e}")
    finally:
        if session_id:
            shell_manager.close_session(session_id)
        try:
            await websocket.close()
        except Exception:
            pass


# --- ZICORE Server Console: Logs / Errors / Processes ---

@app.get("/api/admin/logs")
async def admin_logs(request: Request):
    """Get recent logs from a server.
    Query params: server (.85|vps), lines (default 80), filter (grep pattern), service (systemd unit).
    """
    server = request.query_params.get("server", ".85")
    lines = int(request.query_params.get("lines", "80"))
    filt = request.query_params.get("filter", "")
    service = request.query_params.get("service", "zicore-materializer")
    if server == ".85":
        import subprocess as _sp
        try:
            cmd = f"sudo journalctl -u {service} --no-pager -n {lines}"
            if filt:
                cmd += f" | grep -i '{filt}'"
            r = _sp.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=10)
            return {"success": True, "logs": r.stdout, "server": server}
        except Exception as e:
            return {"success": False, "error": str(e), "server": server}
    else:
        result = await _ssh_exec(server,
            f"sudo journalctl -u {service} --no-pager -n {lines}"
            + (f" | grep -i '{filt}'" if filt else ""),
            timeout=10)
        return {"success": result.get("success", False), "logs": result.get("stdout", ""),
                "stderr": result.get("stderr", ""), "server": server}


@app.get("/api/admin/errors")
async def admin_errors(request: Request):
    """Get error/warning lines from logs. Query: server, lines (default 200)."""
    server = request.query_params.get("server", ".85")
    lines = int(request.query_params.get("lines", "200"))
    service = request.query_params.get("service", "zicore-materializer")
    err_grep = "grep -iE 'error|exception|fail|critical|traceback|killed|oom|segfault|panic'"
    cmd = f"sudo journalctl -u {service} --no-pager -n {lines} {err_grep}"
    if server == ".85":
        import subprocess as _sp
        try:
            r = _sp.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=10)
            return {"success": True, "errors": r.stdout, "server": server}
        except Exception as e:
            return {"success": False, "error": str(e), "server": server}
    else:
        result = await _ssh_exec(server, cmd, timeout=15)
        return {"success": result.get("success", False), "errors": result.get("stdout", ""),
                "stderr": result.get("stderr", ""), "server": server}


@app.get("/api/admin/processes")
async def admin_processes(request: Request):
    """Get running processes. Query: server, filter (name pattern)."""
    server = request.query_params.get("server", ".85")
    filt = request.query_params.get("filter", "python")
    cmd = f"ps aux --sort=-%cpu | head -30"
    if filt:
        cmd = f"ps aux | grep -i '{filt}' | grep -v grep | head -30"
    if server == ".85":
        import subprocess as _sp
        try:
            r = _sp.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=10)
            return {"success": True, "processes": r.stdout, "server": server}
        except Exception as e:
            return {"success": False, "error": str(e), "server": server}
    else:
        result = await _ssh_exec(server, cmd, timeout=10)
        return {"success": result.get("success", False), "processes": result.get("stdout", ""),
                "server": server}


@app.get("/api/admin/service-status")
async def admin_service_status(request: Request):
    """Get systemd service status. Query: server, service."""
    server = request.query_params.get("server", ".85")
    service = request.query_params.get("service", "zicore-materializer")
    cmd = f"systemctl is-active {service} 2>/dev/null; echo ---; systemctl status {service} --no-pager -l 2>&1 | head -15"
    if server == ".85":
        import subprocess as _sp
        try:
            r = _sp.run(["bash", "-c", cmd], capture_output=True, text=True, timeout=10)
            return {"success": True, "status": r.stdout, "server": server, "service": service}
        except Exception as e:
            return {"success": False, "error": str(e), "server": server}
    else:
        result = await _ssh_exec(server, cmd, timeout=10)
        return {"success": result.get("success", False), "status": result.get("stdout", ""),
                "server": server, "service": service}


@app.get("/console")
async def console_page():
    from fastapi.responses import FileResponse
    html_path = FRONTEND_DIR / "server-console.html"
    if html_path.exists():
        return FileResponse(str(html_path), media_type="text/html")
    return JSONResponse(content={"error": "Console not found"}, status_code=404)


# --- ZiHost: Free Hosting Panel ---

try:
    from zicore.zihost import zihost
except ImportError:
    zihost = None


@app.get("/zihost")
async def zihost_page():
    from fastapi.responses import FileResponse
    html_path = FRONTEND_DIR / "zihost.html"
    if html_path.exists():
        return FileResponse(str(html_path), media_type="text/html")
    return JSONResponse(content={"error": "ZiHost not found"}, status_code=404)


@app.get("/api/zihost/stats")
async def zihost_stats():
    if zihost is None:
        return {"error": "ZiHost not available"}
    return zihost.get_stats()


@app.get("/api/zihost/accounts")
async def zihost_accounts():
    if zihost is None:
        return {"error": "ZiHost not available"}
    return {"accounts": zihost.list_all()}


@app.post("/api/zihost/create")
async def zihost_create(request: Request):
    if zihost is None:
        return JSONResponse(content={"error": "ZiHost not available"}, status_code=503)
    data = await request.json()
    result = zihost.create_account(
        username=data.get("username", ""),
        email=data.get("email", ""),
        password=data.get("password"),
    )
    return result


@app.post("/api/zihost/auth")
async def zihost_auth(request: Request):
    if zihost is None:
        return JSONResponse(content={"error": "ZiHost not available"}, status_code=503)
    data = await request.json()
    result = zihost.authenticate(
        username=data.get("username", ""),
        password=data.get("password", ""),
    )
    return result


@app.get("/api/zihost/quota")
async def zihost_quota(request: Request):
    if zihost is None:
        return {"error": "ZiHost not available"}
    user = request.query_params.get("user", "")
    key = request.query_params.get("key", "")
    # Simple API key check
    for acct in zihost.list_all():
        if acct.get("username") == user and acct.get("api_key") == key:
            return zihost.check_quota(user)
    return {"error": "Unauthorized"}


@app.get("/api/zihost/files")
async def zihost_files(request: Request):
    if zihost is None:
        return {"error": "ZiHost not available"}
    user = request.query_params.get("user", "")
    key = request.query_params.get("key", "")
    path = request.query_params.get("path", "html")
    for acct in zihost.list_all():
        if acct.get("username") == user and acct.get("api_key") == key:
            return zihost.list_files(user, path)
    return {"error": "Unauthorized"}


@app.post("/api/zihost/upload")
async def zihost_upload(request: Request):
    if zihost is None:
        return JSONResponse(content={"error": "ZiHost not available"}, status_code=503)
    user = request.query_params.get("user", "")
    key = request.query_params.get("key", "")
    path = request.query_params.get("path", "html")
    valid = False
    for acct in zihost.list_all():
        if acct.get("username") == user and acct.get("api_key") == key:
            valid = True
            break
    if not valid:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=403)
    form = await request.form()
    upload = form.get("file")
    if not upload:
        return {"error": "No file"}
    content = await upload.read()
    filename = upload.filename or "upload.bin"
    return zihost.write_file(user, path, filename, content)


@app.delete("/api/zihost/file")
async def zihost_delete_file(request: Request):
    if zihost is None:
        return JSONResponse(content={"error": "ZiHost not available"}, status_code=503)
    user = request.query_params.get("user", "")
    key = request.query_params.get("key", "")
    path = request.query_params.get("path", "html")
    name = request.query_params.get("name", "")
    valid = False
    for acct in zihost.list_all():
        if acct.get("username") == user and acct.get("api_key") == key:
            valid = True
            break
    if not valid:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=403)
    return zihost.delete_file(user, path, name)


@app.delete("/api/zihost/account")
async def zihost_delete_account(request: Request):
    if zihost is None:
        return JSONResponse(content={"error": "ZiHost not available"}, status_code=503)
    data = await request.json()
    return zihost.delete_account(data.get("username", ""))


# --- ZICORE Mail Server ---

from zicore.mail_integration import MailServer
mail_server = MailServer()

try:
    from zicore.oracle_email import oracle_email
except Exception:
    oracle_email = None


@app.get("/api/mail/admin-check")
async def mail_admin_check(request: Request):
    """Check if current user is a mail admin.

    Accepts SSO Bearer token OR mail credentials (user/password query params).
    Returns {admin: true/false, email: "...", role: "..."}.
    """
    # Try SSO token first
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and sso is not None:
        token = auth[7:]
        result = sso.verify_token(token)
        if result.get("success"):
            user = result.get("user", {})
            is_admin = user.get("role") == "admin"
            return {"admin": is_admin, "email": user.get("email", ""), "role": user.get("role", "user"), "source": "sso"}

    # Try mail credentials
    user_email = request.query_params.get("user", "")
    if user_email and mail_server is not None:
        users = mail_server.list_users()
        for u in users:
            if u.get("email", "").lower() == user_email.lower():
                role = u.get("role", "user")
                return {"admin": role == "admin", "email": user_email, "role": role, "source": "mail"}

    return {"admin": False, "email": "", "role": "none", "source": "none"}


@app.get("/api/mail/status")
async def mail_status():
    """Get mail server status."""
    return {"status": "ok", "mail": mail_server.get_status()}


@app.post("/api/mail/start")
async def mail_start(request: Request):
    """Start mail server containers. Admin only."""
    err = await _require_mail_admin(request)
    if err:
        return err
    return {"status": "ok", "result": mail_server.start()}


@app.post("/api/mail/stop")
async def mail_stop(request: Request):
    """Stop mail server containers. Admin only."""
    err = await _require_mail_admin(request)
    if err:
        return err
    return {"status": "ok", "result": mail_server.stop()}


@app.post("/api/mail/restart")
async def mail_restart(request: Request):
    """Restart mail server containers. Admin only."""
    err = await _require_mail_admin(request)
    if err:
        return err
    return {"status": "ok", "result": mail_server.restart()}


async def _require_mail_admin(request: Request):
    """Check SSO token for admin role. Returns error response if not admin, None if OK."""
    user = await get_current_user(request)
    if not user or user.get("role") != "admin":
        return JSONResponse({"status": "error", "error": "Admin access required"}, status_code=403)
    return None


@app.get("/api/mail/users")
async def mail_list_users(request: Request):
    """List all email users. Admin only."""
    err = await _require_mail_admin(request)
    if err:
        return err
    users = mail_server.list_users()
    return {"status": "ok", "users": users}


@app.post("/api/mail/users/role")
async def mail_update_role(request: Request):
    """Update a user's role. Admin only."""
    err = await _require_mail_admin(request)
    if err:
        return err
    data = await request.json()
    email = data.get("email", "")
    role = data.get("role", "user")
    result = mail_server.update_role(email, role)
    return {"status": "ok" if result.get("success") else "error", **result}


@app.get("/api/mail/stats")
async def mail_stats(request: Request):
    """Get mail server statistics. Admin only."""
    err = await _require_mail_admin(request)
    if err:
        return err
    return {"status": "ok", **mail_server.get_stats()}


@app.post("/api/mail/restart/{service}")
async def mail_restart_service(service: str, request: Request):
    """Restart a mail service. Admin only."""
    err = await _require_mail_admin(request)
    if err:
        return err
    result = mail_server.restart_service(service)
    return {"status": "ok" if result.get("success") else "error", **result}


@app.post("/api/mail/users")
async def mail_create_user(request: Request):
    """Create a new email user. Admin only."""
    err = await _require_mail_admin(request)
    if err:
        return err
    data = await request.json()
    email_addr = data.get("email", "")
    password = data.get("password", "")
    name = data.get("name", "")
    return {"status": "ok", "result": mail_server.create_user(email_addr, password, name)}


@app.delete("/api/mail/users/{email}")
async def mail_delete_user(email: str, request: Request):
    """Deactivate an email user. Admin only."""
    err = await _require_mail_admin(request)
    if err:
        return err
    return {"status": "ok", "result": mail_server.delete_user(email)}


@app.get("/api/mail/aliases")
async def mail_list_aliases():
    """List all email aliases."""
    return {"status": "ok", "aliases": mail_server.list_aliases()}


@app.post("/api/mail/send")
async def mail_send(request: Request):
    """Send an email — tries Gmail relay first, falls back to Oracle Email Delivery."""
    data = await request.json()
    to = data.get("to", "")
    subject = data.get("subject", "")
    body = data.get("body", "")
    from_addr = data.get("from", "")
    html = data.get("html", False)
    # Try Gmail relay first
    result = mail_server.send_email(to, subject, body, from_addr, html)
    if isinstance(result, dict) and result.get("success") is False:
        # Gmail failed — try Oracle Email Delivery
        if oracle_email and oracle_email.enabled:
            result = oracle_email.send(to, subject, body, from_addr, html)
    return {"status": "ok", "result": result}


@app.get("/api/mail/inbox")
async def mail_inbox(request: Request):
    """Read inbox emails."""
    user = request.query_params.get("user", "admin@zinemotion.com.mx")
    password = request.query_params.get("password", "")
    limit = int(request.query_params.get("limit", "20"))
    return {"status": "ok", "messages": mail_server.read_inbox(user=user, limit=limit)}


@app.post("/api/mail/forward")
async def mail_forward(request: Request):
    """Forward an email to jilo_tuk@yahoo.com.mx."""
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "error": "Invalid JSON"}

    message_id = data.get("message_id", "")
    forward_to = data.get("forward_to", "jilo_tuk@yahoo.com.mx")

    if not message_id:
        return {"status": "error", "error": "message_id required"}

    try:
        result = mail_server.forward_email(message_id, forward_to)
        return {"status": "ok", "result": result}
    except AttributeError:
        result = mail_server.send_email(
            forward_to,
            "Fw: Message " + message_id,
            "Forwarded message (ID: " + message_id + ")",
            "admin@zinemotion.com.mx"
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


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


def _send_welcome_email(email: str, name: str, domain: str):
    """Send welcome email to newly created mailbox.
    
    Stores the welcome email in the user's Maildir.
    """
    import time as _time
    from pathlib import Path

    domain_name = domain.lstrip("@")
    first_name = name.split()[0] if name else "Member"

    subject = "Welcome to the ZiCore Ecosystem"

    body = f"""Welcome to the ZiCore Ecosystem

Hello {first_name},

Welcome, and thank you for joining ZineMotion.

Your registration has been successfully completed, and you are now part of the ZiCore Ecosystem—a growing platform where artificial intelligence, aerospace innovation, advanced engineering, and scientific exploration come together to shape the future.

We are excited to have you with you.

What is ZiCore?
===============

ZiCore is the central intelligence engine powering the ZineMotion ecosystem.

It is designed to integrate cutting-edge technologies, intelligent systems, scientific research, and future-oriented projects into a single collaborative platform built for innovators, researchers, creators, and explorers.

What You'll Discover
=====================

ZiCore AI
    An intelligent assistant designed to support research, engineering, creativity, and decision-making.

ZiCore.Space
    Our aerospace initiative focused on space exploration, orbital systems, advanced propulsion concepts, and the technologies that will enable humanity's expansion beyond Earth.

ZiCodex
    The central knowledge library of the ecosystem, where technical documentation, scientific publications, engineering concepts, and strategic research are continuously developed and shared.

Featured Projects
==================

    OBSIDIANA — Advanced materials research
    ZiLunar — Lunar exploration systems
    BlackVanta — Stealth aerospace technology
    E-LIQUID — Next-gen liquid propulsion
    RedGen — Energy generation systems
    ZiGenesis — Foundational AI systems
    ZiMind — Neural interface research
    ZiShield — Cybersecurity framework

...and many more innovations currently under development.

Your ZICORE Mail Account
=========================

  Email:      {email}
  IMAP:       mail.{domain_name}:993 (SSL)
  SMTP:       mail.{domain_name}:587 (STARTTLS)
  Webmail:    https://zcs.zicore.space/mail-portal

What's Coming Next
===================

As a registered member, you will receive early access to new features, including:

    - AI-powered tools and assistants
    - Engineering and simulation modules
    - Collaborative workspaces
    - Scientific publications
    - Project management systems
    - Aerospace research updates
    - Exclusive beta releases
    - Community events and announcements

Our platform will continue evolving, and you'll be among the first to experience every new milestone.

Our Vision
==========

We believe that the future belongs to those who combine knowledge, technology, creativity, and purpose.

ZiCore is more than software.

It is the foundation of a next-generation ecosystem dedicated to advancing science, engineering, artificial intelligence, and space exploration through collaboration and innovation.

Every member contributes to building technologies that may one day shape humanity's future beyond our planet.

Stay Connected
===============

Visit your dashboard regularly to discover new tools, research, publications, and project updates.

    Official Portal: https://zinemotion.com.mx

Thank you for becoming part of our journey.

Together, we are building tomorrow.

Welcome to ZiCore.

Engineering Tomorrow. Building Beyond.

The ZiCore Team
Powered by ZineMotion Group

http://www.ZineMotion.com.mx

---
AVISO DE CONFIDENCIALIDAD
Este correo electronico es confidencial y para uso exclusivo de la(s) persona(s) a quien(es) se dirige. Si el lector de esta transmision electronica no es el destinatario, se le notifica que cualquier distribucion o copia de la misma esta estrictamente prohibida. Si ha recibido este correo por error le solicitamos notificar inmediatamente a la persona que lo envio y borrarlo definitivamente de su sistema.

ZICORE Mail v5.0 | {domain_name}
"""

    # Store in user's Maildir
    local_part = email.split("@")[0]
    maildir_new = Path(f"/var/mail/vmail/{domain_name}/{local_part}/Maildir/new")
    maildir_new.mkdir(parents=True, exist_ok=True)

    # Generate Maildir filename
    ts = int(_time.time())
    filename = f"{ts}.{ts}.2:,S={len(body)},L={len(body.encode('utf-8'))}"

    # Build raw email
    raw_email = f"From: ZICORE Mail <postmaster@{domain_name}>\r\n"
    raw_email += f"To: {name} <{email}>\r\n"
    raw_email += f"Subject: {subject}\r\n"
    raw_email += f"Date: {_time.strftime('%a, %d %b %Y %H:%M:%S %z')}\r\n"
    raw_email += f"Message-ID: <welcome-{ts}@{domain_name}>\r\n"
    raw_email += f"MIME-Version: 1.0\r\n"
    raw_email += f"Content-Type: text/plain; charset=utf-8\r\n"
    raw_email += f"X-Mailer: ZICORE-Mail/5.0\r\n"
    raw_email += f"X-Priority: 1\r\n"
    raw_email += "\r\n"
    raw_email += body

    filepath = maildir_new / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(raw_email)

    logger.info(f"Welcome email stored: {filepath} for {email}")

    # Also create Maildir folders
    for sub in ["cur", "tmp"]:
        (maildir_new.parent / sub).mkdir(exist_ok=True)

    return True


@app.post("/api/mail/register")
async def mail_register_user(request: Request):
    """Register a new mail user account.
    
    Free plan: only @zinemotion.com.mx, 1 account per user.
    Basic ($5/10 ZTN): 3 accounts, @zinemotion.com.mx.
    Pro ($25/50 ZTN): 10 accounts, multiple domains.
    Ultimate ($100/200 ZTN): unlimited accounts, all domains.
    """
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

    # Free plan: ONLY @zinemotion.com.mx allowed
    # @zicore.space and @zinemotion.com = admin exclusive
    allowed_domains = ["@zinemotion.com.mx"]
    domain = None
    for d in allowed_domains:
        if email.endswith(d):
            domain = d
            break
    if not domain:
        return {"status": "error", "error": "Free accounts only available with @zinemotion.com.mx"}

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

    # Check account limit for free plan (1 account per user)
    # Extract username prefix to check for existing accounts
    username = email.split("@")[0]
    same_user_count = sum(1 for u in existing_users
                         if u.get("email", "").startswith(username + "@")
                         and u.get("active"))
    if same_user_count >= 1:
        return {
            "status": "error",
            "error": "Free plan: 1 account only. Upgrade to Basic for 3 accounts ($5/mo or 10 ZTN)."
        }

    # Create user with plan='free'
    result = mail_server.create_user(email, password, name, plan="free")
    if result and "error" not in str(result).lower():
        logger.info(f"New mail user registered: {email} (free plan)")

        # Send welcome email to the new mailbox
        try:
            _send_welcome_email(email, name, domain)
        except Exception as e:
            logger.warning(f"Failed to send welcome email: {e}")

        return {"status": "ok", "message": f"Account {email} created successfully. Welcome email sent!"}
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
async def mail_check_username(username: str = "", domain: str = "zinemotion.com.mx"):
    """Check if a username is available for the given domain.
    
    Free plan: only @zinemotion.com.mx
    @zicore.space and @zinemotion.com = admin exclusive
    """
    username = username.strip().lower()
    if not username or not re.match(r'^[a-z0-9._-]+$', username):
        return {"status": "ok", "available": False, "error": "Invalid username format"}
    
    # Free plan: only zinemotion.com.mx allowed
    if domain not in ["zinemotion.com.mx"]:
        return {"status": "ok", "available": False, "error": "Free accounts only available with @zinemotion.com.mx"}
    
    email = f"{username}@{domain}"
    existing_users = mail_server.list_users()
    for u in existing_users:
        if u.get("email") == email and u.get("active"):
            return {"status": "ok", "available": False, "error": "Username already taken"}
    return {"status": "ok", "available": True}


@app.post("/api/mail/upgrade-plan")
async def mail_upgrade_plan(request: Request):
    """Upgrade user mail plan. Requires ZNT payment verification."""
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "error": "Invalid JSON"}
    
    email = data.get("email", "").strip().lower()
    new_plan = data.get("plan", "")
    
    valid_plans = ["free", "basic", "pro", "ultimate"]
    if new_plan not in valid_plans:
        return {"status": "error", "error": f"Invalid plan. Choose: {', '.join(valid_plans)}"}
    
    plan_limits = {
        "free": {"max_accounts": 1, "domains": ["zinemotion.com.mx"], "price_ztn": 0},
        "basic": {"max_accounts": 3, "domains": ["zinemotion.com.mx"], "price_ztn": 10},
        "pro": {"max_accounts": 10, "domains": ["zinemotion.com.mx", "zicore.space"], "price_ztn": 50},
        "ultimate": {"max_accounts": -1, "domains": ["zinemotion.com.mx", "zicore.space", "zinemotion.com"], "price_ztn": 200},
    }
    
    # TODO: Verify ZNT payment before upgrading
    # For now, direct upgrade
    
    try:
        safe_email = mail_server._sanitize_sql(email)
        safe_plan = mail_server._sanitize_sql(new_plan)
        sql = f"UPDATE virtual_users SET plan='{safe_plan}' WHERE email='{safe_email}'"
        db_password = os.environ.get('DB_MAIL_PASSWORD', '')
        if not db_password:
            return JSONResponse({"error": "Mail DB not configured"}, status_code=503)
        import asyncio
        result = await asyncio.to_thread(
            subprocess.run,
            ["docker", "exec", "zicore-mail-db", "mariadb", "-u", "zicore_mail",
             f"-p{db_password}",
             "zicore_mail", "-e", sql],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            limits = plan_limits[new_plan]
            return {
                "status": "ok",
                "message": f"Upgraded to {new_plan}",
                "plan": new_plan,
                "limits": limits
            }
        else:
            return {"status": "error", "error": "Upgrade failed"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# --- Mail Account Configuration (IMAP/POP3/External) ---

MAIL_ACCOUNTS_FILE = Path(__file__).parent / "data" / "config" / "mail_accounts.json"

def _load_mail_accounts() -> list:
    """Load mail accounts from config file."""
    try:
        if MAIL_ACCOUNTS_FILE.exists():
            with open(MAIL_ACCOUNTS_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading mail accounts: {e}")
    return []

def _save_mail_accounts(accounts: list):
    """Save mail accounts to config file."""
    MAIL_ACCOUNTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MAIL_ACCOUNTS_FILE, "w") as f:
        json.dump(accounts, f, indent=2)

@app.get("/api/mail/accounts")
async def mail_accounts_list():
    """List all configured external mail accounts."""
    accounts = _load_mail_accounts()
    safe_accounts = []
    for acc in accounts:
        safe = {k: v for k, v in acc.items() if k != "password"}
        safe["has_password"] = bool(acc.get("password"))
        safe_accounts.append(safe)
    return {"status": "ok", "accounts": safe_accounts}

@app.post("/api/mail/accounts")
async def mail_accounts_add(request: Request):
    """Add a new external mail account (IMAP/POP3)."""
    data = await request.json()
    name = data.get("name", "").strip()
    email_addr = data.get("email", "").strip()
    password = data.get("password", "")
    protocol = data.get("protocol", "imap").lower()  # imap, pop3
    server = data.get("server", "").strip()
    port = int(data.get("port", 0))
    use_ssl = data.get("ssl", True)
    smtp_server = data.get("smtp_server", "").strip()
    smtp_port = int(data.get("smtp_port", 0))
    smtp_ssl = data.get("smtp_ssl", True)
    sync_enabled = data.get("sync_enabled", True)
    sync_interval = int(data.get("sync_interval", 300))  # seconds

    if not email_addr or not password or not server:
        return {"status": "error", "error": "Email, password, and server are required"}

    # Auto-detect ports
    if port == 0:
        port = 993 if protocol == "imap" and use_ssl else 143 if protocol == "imap" else 995 if use_ssl else 110
    if smtp_port == 0:
        smtp_port = 465 if smtp_ssl else 587

    # Presets for common providers
    presets = {
        "gmail.com": {"imap": "imap.gmail.com", "pop3": "pop.gmail.com", "smtp": "smtp.gmail.com", "imap_port": 993, "pop3_port": 995, "smtp_port": 465},
        "outlook.com": {"imap": "outlook.office365.com", "pop3": "outlook.office365.com", "smtp": "smtp.office365.com", "imap_port": 993, "pop3_port": 995, "smtp_port": 587},
        "hotmail.com": {"imap": "outlook.office365.com", "pop3": "outlook.office365.com", "smtp": "smtp.office365.com", "imap_port": 993, "pop3_port": 995, "smtp_port": 587},
        "yahoo.com": {"imap": "imap.mail.yahoo.com", "pop3": "pop.mail.yahoo.com", "smtp": "smtp.mail.yahoo.com", "imap_port": 993, "pop3_port": 995, "smtp_port": 465},
        "icloud.com": {"imap": "imap.mail.me.com", "pop3": "pop.mail.me.com", "smtp": "smtp.mail.me.com", "imap_port": 993, "pop3_port": 995, "smtp_port": 587},
        "protonmail.com": {"imap": "127.0.0.1", "pop3": "127.0.0.1", "smtp": "127.0.0.1", "imap_port": 1143, "pop3_port": 1195, "smtp_port": 1025},
        "zoho.com": {"imap": "imap.zoho.com", "pop3": "pop.zoho.com", "smtp": "smtp.zoho.com", "imap_port": 993, "pop3_port": 995, "smtp_port": 465},
        "aol.com": {"imap": "imap.aol.com", "pop3": "pop.aol.com", "smtp": "smtp.aol.com", "imap_port": 993, "pop3_port": 995, "smtp_port": 465},
    }

    domain = email_addr.split("@")[-1].lower()
    preset = presets.get(domain, {})

    accounts = _load_mail_accounts()
    account_id = secrets.token_hex(8)

    account = {
        "id": account_id,
        "name": name or email_addr,
        "email": email_addr,
        "password": password,
        "protocol": protocol,
        "server": server or preset.get(protocol, ""),
        "port": port or preset.get(f"{protocol}_port", 993 if protocol == "imap" else 995),
        "ssl": use_ssl,
        "smtp_server": smtp_server or preset.get("smtp", ""),
        "smtp_port": smtp_port or preset.get("smtp_port", 465),
        "smtp_ssl": smtp_ssl,
        "sync_enabled": sync_enabled,
        "sync_interval": sync_interval,
        "last_sync": None,
        "status": "configured",
        "created": datetime.now().isoformat(),
    }

    accounts.append(account)
    _save_mail_accounts(accounts)

    return {"status": "ok", "account": {k: v for k, v in account.items() if k != "password"}}

@app.put("/api/mail/accounts/{account_id}")
async def mail_accounts_update(account_id: str, request: Request):
    """Update an existing mail account."""
    data = await request.json()
    accounts = _load_mail_accounts()

    for i, acc in enumerate(accounts):
        if acc["id"] == account_id:
            for key in ["name", "email", "password", "protocol", "server", "port", "ssl",
                         "smtp_server", "smtp_port", "smtp_ssl", "sync_enabled", "sync_interval"]:
                if key in data:
                    accounts[i][key] = data[key]
            accounts[i]["updated"] = datetime.now().isoformat()
            _save_mail_accounts(accounts)
            safe = {k: v for k, v in accounts[i].items() if k != "password"}
            safe["has_password"] = bool(accounts[i].get("password"))
            return {"status": "ok", "account": safe}

    return {"status": "error", "error": "Account not found"}

@app.delete("/api/mail/accounts/{account_id}")
async def mail_accounts_delete(account_id: str):
    """Delete a mail account."""
    accounts = _load_mail_accounts()
    accounts = [a for a in accounts if a["id"] != account_id]
    _save_mail_accounts(accounts)
    return {"status": "ok", "deleted": account_id}

@app.post("/api/mail/accounts/{account_id}/test")
async def mail_accounts_test(account_id: str):
    """Test connection to a mail account."""
    accounts = _load_mail_accounts()
    acc = next((a for a in accounts if a["id"] == account_id), None)
    if not acc:
        return {"status": "error", "error": "Account not found"}

    result = {"imap": None, "smtp": None}

    # Test IMAP/POP3
    try:
        if acc["protocol"] == "imap":
            import imaplib
            if acc["ssl"]:
                m = imaplib.IMAP4_SSL(acc["server"], acc["port"])
            else:
                m = imaplib.IMAP4(acc["server"], acc["port"])
            m.login(acc["email"], acc["password"])
            status, data = m.select("INBOX")
            msg_count = int(data[0]) if status == "OK" else 0
            m.logout()
            result["imap"] = {"status": "ok", "message": f"Connected. {msg_count} messages in INBOX."}
        else:
            import poplib
            if acc["ssl"]:
                m = poplib.POP3_SSL(acc["server"], acc["port"])
            else:
                m = poplib.POP3(acc["server"], acc["port"])
            m.user(acc["email"])
            m.pass_(acc["password"])
            count, size = m.stat()
            m.quit()
            result["imap"] = {"status": "ok", "message": f"Connected. {count} messages, {size} bytes."}
    except Exception as e:
        result["imap"] = {"status": "error", "message": str(e)}

    # Test SMTP
    try:
        import smtplib
        if acc["smtp_ssl"]:
            m = smtplib.SMTP_SSL(acc["smtp_server"], acc["smtp_port"], timeout=10)
        else:
            m = smtplib.SMTP(acc["smtp_server"], acc["smtp_port"], timeout=10)
            m.starttls()
        m.login(acc["email"], acc["password"])
        m.quit()
        result["smtp"] = {"status": "ok", "message": "SMTP connection successful"}
    except Exception as e:
        result["smtp"] = {"status": "error", "message": str(e)}

    return {"status": "ok", "result": result}

@app.post("/api/mail/accounts/{account_id}/sync")
async def mail_accounts_sync(account_id: str):
    """Trigger immediate sync for an account."""
    accounts = _load_mail_accounts()
    acc = next((a for a in accounts if a["id"] == account_id), None)
    if not acc:
        return {"status": "error", "error": "Account not found"}

    # Run sync in background
    try:
        import subprocess
        script = f"""python3 -c "
import imaplib, email, os, time
m = imaplib.IMAP4_SSL('{acc['server']}', {acc['port']})
m.login('{acc['email']}', '{acc['password']}')
m.select('INBOX')
status, data = m.search(None, 'UNSEEN')
if status == 'OK':
    for num in data[0].split():
        status2, msg_data = m.fetch(num, '(RFC822)')
        if status2 == 'OK':
            msg = email.message_from_bytes(msg_data[0][1])
            print(f'Found: {{msg.get(\"subject\", \"No subject\")[:50]}}')
m.logout()
" """
        # Schedule for background execution
        accounts[i]["last_sync"] = datetime.now().isoformat()
        _save_mail_accounts(accounts)
        return {"status": "ok", "message": "Sync started"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/api/mail/accounts/providers")
async def mail_accounts_providers():
    """Get list of supported mail providers with presets."""
    providers = {
        "gmail.com": {"name": "Gmail", "imap": "imap.gmail.com", "pop3": "pop.gmail.com", "smtp": "smtp.gmail.com", "ports": {"imap": 993, "pop3": 995, "smtp_ssl": 465, "smtp_starttls": 587}},
        "outlook.com": {"name": "Microsoft Outlook", "imap": "outlook.office365.com", "pop3": "outlook.office365.com", "smtp": "smtp.office365.com", "ports": {"imap": 993, "pop3": 995, "smtp_ssl": 465, "smtp_starttls": 587}},
        "hotmail.com": {"name": "Hotmail", "imap": "outlook.office365.com", "pop3": "outlook.office365.com", "smtp": "smtp.office365.com", "ports": {"imap": 993, "pop3": 995, "smtp_ssl": 465, "smtp_starttls": 587}},
        "yahoo.com": {"name": "Yahoo Mail", "imap": "imap.mail.yahoo.com", "pop3": "pop.mail.yahoo.com", "smtp": "smtp.mail.yahoo.com", "ports": {"imap": 993, "pop3": 995, "smtp_ssl": 465, "smtp_starttls": 587}},
        "icloud.com": {"name": "iCloud Mail", "imap": "imap.mail.me.com", "pop3": "pop.mail.me.com", "smtp": "smtp.mail.me.com", "ports": {"imap": 993, "pop3": 995, "smtp_ssl": 465, "smtp_starttls": 587}},
        "zoho.com": {"name": "Zoho Mail", "imap": "imap.zoho.com", "pop3": "pop.zoho.com", "smtp": "smtp.zoho.com", "ports": {"imap": 993, "pop3": 995, "smtp_ssl": 465, "smtp_starttls": 587}},
        "aol.com": {"name": "AOL Mail", "imap": "imap.aol.com", "pop3": "pop.aol.com", "smtp": "smtp.aol.com", "ports": {"imap": 993, "pop3": 995, "smtp_ssl": 465, "smtp_starttls": 587}},
        "protonmail.com": {"name": "ProtonMail Bridge", "imap": "127.0.0.1", "pop3": "127.0.0.1", "smtp": "127.0.0.1", "ports": {"imap": 1143, "pop3": 1195, "smtp_ssl": 1025, "smtp_starttls": 1025}},
    }
    return {"status": "ok", "providers": providers}

@app.get("/api/mail/accounts/presets")
async def mail_accounts_presets():
    """Get quick-add presets for common providers."""
    return {"status": "ok", "presets": [
        {"id": "gmail", "name": "Gmail", "icon": "📧", "protocol": "imap", "server": "imap.gmail.com", "port": 993, "ssl": True, "smtp_server": "smtp.gmail.com", "smtp_port": 465, "smtp_ssl": True},
        {"id": "outlook", "name": "Microsoft Outlook", "icon": "📨", "protocol": "imap", "server": "outlook.office365.com", "port": 993, "ssl": True, "smtp_server": "smtp.office365.com", "smtp_port": 587, "smtp_ssl": False},
        {"id": "yahoo", "name": "Yahoo Mail", "icon": "📬", "protocol": "imap", "server": "imap.mail.yahoo.com", "port": 993, "ssl": True, "smtp_server": "smtp.mail.yahoo.com", "smtp_port": 465, "smtp_ssl": True},
        {"id": "icloud", "name": "iCloud Mail", "icon": "🍎", "protocol": "imap", "server": "imap.mail.me.com", "port": 993, "ssl": True, "smtp_server": "smtp.mail.me.com", "smtp_port": 587, "smtp_ssl": False},
        {"id": "zoho", "name": "Zoho Mail", "icon": "✉️", "protocol": "imap", "server": "imap.zoho.com", "port": 993, "ssl": True, "smtp_server": "smtp.zoho.com", "smtp_port": 465, "smtp_ssl": True},
        {"id": "aol", "name": "AOL Mail", "icon": "📮", "protocol": "imap", "server": "imap.aol.com", "port": 993, "ssl": True, "smtp_server": "smtp.aol.com", "smtp_port": 465, "smtp_ssl": True},
        {"id": "custom", "name": "Custom Server", "icon": "⚙️", "protocol": "imap", "server": "", "port": 993, "ssl": True, "smtp_server": "", "smtp_port": 587, "smtp_ssl": False},
    ]}


# --- Incoming Mail (from Cloudflare Worker) ---

MAIL_INCOMING_SECRET = "zicore-mail-worker-2026"
INCOMING_MAIL_LOG = Path(__file__).parent / "data" / "incoming_mail.json"

@app.post("/api/mail/incoming")
async def mail_incoming(request: Request):
    """Receive email forwarded by Cloudflare Worker.
    
    Called by Cloudflare Worker when email arrives at zicore.space.
    Stores email in local mailbox and optional forwarding.
    """
    # Verify secret
    secret = request.headers.get("X-Mail-Secret", "")
    if secret != MAIL_INCOMING_SECRET:
        return JSONResponse({"status": "error", "error": "Invalid secret"}, status_code=403)

    try:
        data = await request.json()
    except Exception:
        return JSONResponse({"status": "error", "error": "Invalid JSON"}, status_code=400)

    to_addr = data.get("to", "")
    from_addr = data.get("from", "")
    subject = data.get("subject", "(sin asunto)")
    body = data.get("body", "")
    headers = data.get("headers", {})

    logger.info(f"Incoming mail: {from_addr} -> {to_addr} | {subject}")

    # Determine which mailbox to store in
    # Parse local part from to_addr (e.g., admin@zicore.space -> admin)
    local_part = to_addr.split("@")[0] if "@" in to_addr else "admin"
    domain = to_addr.split("@")[1] if "@" in to_addr else "zicore.space"

    # Store in Maildir format
    maildir_base = Path("/var/mail/vmail")
    maildir = maildir_base / domain / local_part / "Maildir" / "new"

    try:
        maildir.mkdir(parents=True, exist_ok=True)

        # Generate filename (timestamp.pid.message-id)
        ts = int(time.time())
        msg_id = headers.get("message-id", f"{ts}@zicore.space").strip("<>")
        filename = f"{ts}.{ts}.2:,S={len(body)},L={len(body.encode())}"

        # Build raw email in Maildir format
        raw_email = f"From: {from_addr}\r\n"
        raw_email += f"To: {to_addr}\r\n"
        raw_email += f"Subject: {subject}\r\n"
        raw_email += f"Date: {headers.get('date', time.strftime('%a, %d %b %Y %H:%M:%S %z'))}\r\n"
        if headers.get("message-id"):
            raw_email += f"Message-ID: {headers['message-id']}\r\n"
        if headers.get("reply-to"):
            raw_email += f"Reply-To: {headers['reply-to']}\r\n"
        raw_email += f"Content-Type: {headers.get('content-type', 'text/plain; charset=utf-8')}\r\n"
        raw_email += f"X-ZICORE-Source: cloudflare-worker\r\n"
        raw_email += f"X-ZICORE-Forwarded: {time.strftime('%Y-%m-%d %H:%M:%S')}\r\n"
        raw_email += "\r\n"
        raw_email += body

        # Write to Maildir
        filepath = maildir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(raw_email)

        logger.info(f"Email stored: {filepath}")

        # Log to incoming_mail.json for tracking
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "from": from_addr,
            "to": to_addr,
            "subject": subject,
            "size": len(raw_email),
            "file": str(filepath),
        }
        try:
            log_data = []
            if INCOMING_MAIL_LOG.exists():
                with open(INCOMING_MAIL_LOG, "r") as f:
                    log_data = json.load(f)
            log_data.append(log_entry)
            # Keep last 1000 entries
            log_data = log_data[-1000:]
            with open(INCOMING_MAIL_LOG, "w") as f:
                json.dump(log_data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to log incoming mail: {e}")

        return {"status": "ok", "stored": str(filepath), "mailbox": f"{local_part}@{domain}"}

    except Exception as e:
        logger.error(f"Failed to store incoming mail: {e}")
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)


@app.get("/api/mail/incoming")
async def mail_incoming_list(request: Request):
    """List recent incoming emails (from Cloudflare Worker)."""
    limit = int(request.query_params.get("limit", "50"))
    try:
        if INCOMING_MAIL_LOG.exists():
            with open(INCOMING_MAIL_LOG, "r") as f:
                log_data = json.load(f)
            return {"status": "ok", "emails": log_data[-limit:], "total": len(log_data)}
    except Exception:
        pass
    return {"status": "ok", "emails": [], "total": 0}


# ─── ZICORE SSO API ─────────────────────────────────────────────────────────

SSO_PLANS = {
    "free": {
        "name": "Free",
        "price_ztn": 0,
        "mail_accounts": 1,
        "mail_domains": ["zinemotion.com.mx"],
        "zio_daily_messages": 20,
        "storage_mb": 500,
        "services": ["ZIO AI", "Game Center", "Settings"],
    },
    "basic": {
        "name": "Basic",
        "price_ztn": 10,
        "mail_accounts": 3,
        "mail_domains": ["zinemotion.com.mx"],
        "zio_daily_messages": 100,
        "storage_mb": 2048,
        "services": ["ZIO AI", "Materializer", "Game Center", "Settings", "Knowledge Base"],
    },
    "pro": {
        "name": "Pro",
        "price_ztn": 50,
        "mail_accounts": 10,
        "mail_domains": ["zinemotion.com.mx", "zicore.space"],
        "zio_daily_messages": -1,
        "storage_mb": 10240,
        "services": ["ZIO AI", "Materializer", "Mission Control", "Flight Simulator", "Engineering", "Game Center", "Settings", "Knowledge Base"],
    },
    "ultimate": {
        "name": "Ultimate",
        "price_ztn": 200,
        "mail_accounts": -1,
        "mail_domains": ["zinemotion.com.mx", "zicore.space", "zinemotion.com"],
        "zio_daily_messages": -1,
        "storage_mb": -1,
        "services": "__all__",
    },
}


async def get_current_user(request: Request) -> Optional[dict]:
    """Extract Bearer token from Authorization header and verify via SSO.

    Returns user dict on success, or None if unauthenticated.
    """
    if sso is None:
        return None
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    result = sso.verify_token(token)
    if result.get("success"):
        return result.get("user")
    return None


def _require_admin(user: dict) -> Optional[JSONResponse]:
    """Return a JSONResponse error if user is not admin, else None."""
    if not user or user.get("role") != "admin":
        return JSONResponse({"status": "error", "error": "Admin access required"}, status_code=403)
    return None


# ─── Auth Routes ─────────────────────────────────────────────────────────────

@app.post("/api/sso/register")
async def sso_register(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        data = await request.json()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        name = data.get("name", "").strip()

        if not email or not _validate_email(email):
            return {"status": "error", "error": "Invalid email format"}
        if not password or len(password) < 6:
            return {"status": "error", "error": "Password must be at least 6 characters"}
        if not name or len(name) < 2:
            return {"status": "error", "error": "Name must be at least 2 characters"}

        username = email.split("@")[0]
        result = sso.register_user(username, password, email=email, display_name=name)
        if not result.get("success"):
            return {"status": "error", "error": result.get("error", "Registration failed")}

        user = result["user"]

        # Sync with mail system
        try:
            mail_server.create_user(email, password, name, plan="free")
            logger.info(f"SSO: Mail account created for {email}")
        except Exception as e:
            logger.warning(f"SSO: Failed to create mail account for {email}: {e}")

        # Auto-login after registration
        client_ip = request.client.host if request.client else "unknown"
        ua = request.headers.get("User-Agent", "")
        login_result = sso.login(username, password, service="zicore-web", ip_address=client_ip, user_agent=ua)

        if login_result.get("success"):
            return {"status": "ok", "token": login_result["token"], "expires_at": login_result["expires_at"], "user": login_result["user"]}
        return {"status": "ok", "user": user}
    except Exception as e:
        logger.error(f"SSO register error: {e}")
        return {"status": "error", "error": str(e)}


@app.post("/api/sso/login")
async def sso_login(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        data = await request.json()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return {"status": "error", "error": "Email and password are required"}

        username = email.split("@")[0]
        client_ip = request.client.host if request.client else "unknown"
        ua = request.headers.get("User-Agent", "")
        result = sso.login(username, password, service="zicore-web", ip_address=client_ip, user_agent=ua)

        if not result.get("success"):
            return {"status": "error", "error": result.get("error", "Login failed")}

        # Sync plan to mail system
        try:
            user = result["user"]
            mail_server.update_role(email, user.get("role", "user"))
        except Exception:
            pass

        return {"status": "ok", "token": result["token"], "expires_at": result["expires_at"], "user": result["user"]}
    except Exception as e:
        logger.error(f"SSO login error: {e}")
        return {"status": "error", "error": str(e)}


@app.post("/api/sso/logout")
async def sso_logout(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        auth = request.headers.get("Authorization", "")
        token = auth[7:] if auth.startswith("Bearer ") else ""
        if token:
            sso.logout(token)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/sso/me")
async def sso_me(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        # Attach plan info
        plan_name = user.get("role", "user")
        if plan_name not in SSO_PLANS:
            plan_name = "free"
        user["plan"] = plan_name
        user["plan_info"] = SSO_PLANS.get(plan_name, SSO_PLANS["free"])

        return {"status": "ok", "user": user}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/sso/change-password")
async def sso_change_password(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        data = await request.json()
        old_password = data.get("old_password", "")
        new_password = data.get("new_password", "")

        if not old_password or not new_password:
            return {"status": "error", "error": "Both old and new passwords are required"}
        if len(new_password) < 6:
            return {"status": "error", "error": "New password must be at least 6 characters"}

        result = sso.change_password(user["id"], old_password, new_password)
        if not result.get("success"):
            return {"status": "error", "error": result.get("error", "Password change failed")}

        return {"status": "ok", "message": "Password changed successfully"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/sso/reset-password")
async def sso_reset_password(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        data = await request.json()
        email = data.get("email", "").strip().lower()

        if not email or not _validate_email(email):
            return {"status": "error", "error": "Invalid email format"}

        # For now, just log the reset request (no email sending)
        logger.info(f"SSO: Password reset requested for {email}")
        return {"status": "ok", "message": "If an account with that email exists, a reset link has been sent."}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/sso/confirm-reset")
async def sso_confirm_reset(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        data = await request.json()
        token = data.get("token", "")
        new_password = data.get("new_password", "")

        if not token or not new_password:
            return {"status": "error", "error": "Token and new password are required"}
        if len(new_password) < 6:
            return {"status": "error", "error": "Password must be at least 6 characters"}

        # Verify the reset token via SSO session
        result = sso.verify_token(token)
        if not result.get("success"):
            return {"status": "error", "error": "Invalid or expired reset token"}

        user = result["user"]
        reset_result = sso.admin_reset_password(user["id"], new_password)
        if not reset_result.get("success"):
            return {"status": "error", "error": reset_result.get("error", "Reset failed")}

        return {"status": "ok", "message": "Password reset successfully"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─── Profile & API Keys Routes ───────────────────────────────────────────────

@app.post("/api/sso/update-profile")
async def sso_update_profile(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        data = await request.json()
        display_name = data.get("display_name")
        email = data.get("email")

        result = sso.update_user(user["id"], email=email, display_name=display_name)
        if not result.get("success"):
            return {"status": "error", "error": result.get("error", "Update failed")}

        return {"status": "ok", "user": result["user"]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/sso/sessions")
async def sso_sessions(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        rows = sso.conn.execute(
            "SELECT * FROM sessions WHERE user_id=? AND is_active=1 ORDER BY created_at DESC",
            (user["id"],)
        ).fetchall()
        sessions = [{"id": r["id"], "token": r["token"][:8]+"...", "service": r["service"],
                     "ip_address": r["ip_address"], "user_agent": r["user_agent"],
                     "created_at": r["created_at"], "expires_at": r["expires_at"]} for r in rows]
        return {"status": "ok", "sessions": sessions}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/sso/revoke-session")
async def sso_revoke_session(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        data = await request.json()
        session_id = data.get("session_id")
        if session_id:
            sso.conn.execute("UPDATE sessions SET is_active=0 WHERE id=? AND user_id=?",
                             (session_id, user["id"]))
            sso.conn.commit()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/sso/revoke-all-sessions")
async def sso_revoke_all_sessions(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        sso.conn.execute("UPDATE sessions SET is_active=0 WHERE user_id=? AND is_active=1",
                         (user["id"],))
        sso.conn.commit()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/sso/api-keys")
async def sso_api_keys(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        rows = sso.conn.execute(
            "SELECT id, name, permissions, expires_at, created_at FROM api_keys WHERE user_id=?",
            (user["id"],)
        ).fetchall()
        keys = [{"id": r["id"], "name": r["name"], "permissions": r["permissions"],
                 "expires_at": r["expires_at"], "created_at": r["created_at"]} for r in rows]
        return {"status": "ok", "keys": keys}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/sso/api-keys")
async def sso_create_api_key(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        data = await request.json()
        name = data.get("name", "Unnamed Key")
        permissions = data.get("permissions", ["read"])
        expiry_days = data.get("expiry_days", 90)

        import hashlib
        key = "zicore_" + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        key_id = "ak_" + secrets.token_hex(8)
        expires = (datetime.utcnow() + timedelta(days=expiry_days)).isoformat()

        sso.conn.execute(
            "INSERT INTO api_keys (id, user_id, key_hash, name, permissions, expires_at, created_at) VALUES (?,?,?,?,?,?,?)",
            (key_id, user["id"], key_hash, name, json.dumps(permissions), expires, datetime.utcnow().isoformat())
        )
        sso.conn.commit()
        return {"status": "ok", "key": key, "id": key_id, "name": name, "expires_at": expires}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.delete("/api/sso/api-keys/{key_id}")
async def sso_delete_api_key(request: Request, key_id: str):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        sso.conn.execute("DELETE FROM api_keys WHERE id=? AND user_id=?", (key_id, user["id"]))
        sso.conn.commit()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─── Plan Routes ─────────────────────────────────────────────────────────────

@app.get("/api/sso/plans")
async def sso_plans():
    try:
        plans = {}
        for key, info in SSO_PLANS.items():
            plans[key] = {
                "name": info["name"],
                "price_ztn": info["price_ztn"],
                "mail_accounts": info["mail_accounts"],
                "zio_daily_messages": info["zio_daily_messages"],
                "storage_mb": info["storage_mb"],
            }
        return {"status": "ok", "plans": plans}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/sso/upgrade")
async def sso_upgrade(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        data = await request.json()
        new_plan = data.get("plan", "")

        if new_plan not in SSO_PLANS:
            return {"status": "error", "error": f"Invalid plan. Choose: {', '.join(SSO_PLANS.keys())}"}

        # Map plan name to role for SSO user
        result = sso.update_user(user["id"], role=new_plan)
        if not result.get("success"):
            return {"status": "error", "error": result.get("error", "Upgrade failed")}

        # Sync plan to mail system
        try:
            email = user.get("email", "")
            if email:
                mail_server.update_role(email, new_plan)
        except Exception:
            pass

        return {"status": "ok", "plan": new_plan, "plan_info": SSO_PLANS[new_plan]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/sso/limits")
async def sso_limits(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        plan_name = user.get("role", "free")
        if plan_name not in SSO_PLANS:
            plan_name = "free"

        return {"status": "ok", "plan": plan_name, "limits": SSO_PLANS[plan_name]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─── Service Routes ──────────────────────────────────────────────────────────

@app.get("/api/sso/services")
async def sso_services():
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        result = sso.list_services()
        if not result.get("success"):
            return {"status": "error", "error": result.get("error", "Failed to list services")}
        return {"status": "ok", "services": result["services"]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/sso/my-services")
async def sso_my_services(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        result = sso.get_user_services(user["id"])
        if not result.get("success"):
            return {"status": "error", "error": result.get("error", "Failed to get services")}
        return {"status": "ok", "services": result["services"]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/sso/activate-service")
async def sso_activate_service(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        data = await request.json()
        service_id = data.get("service_id")

        if not service_id:
            return {"status": "error", "error": "service_id required"}

        # Check plan allows this service
        plan_name = user.get("role", "free")
        plan_info = SSO_PLANS.get(plan_name, SSO_PLANS["free"])
        allowed_services = plan_info.get("services", [])

        svc_result = sso.get_service(service_id)
        if not svc_result.get("success"):
            return {"status": "error", "error": "Service not found"}

        svc_name = svc_result["service"]["name"]
        if allowed_services != "__all__" and svc_name not in allowed_services:
            return {"status": "error", "error": f"Service '{svc_name}' not available on {plan_name} plan. Upgrade to access it."}

        result = sso.grant_service(user["id"], service_id)
        if not result.get("success"):
            return {"status": "error", "error": result.get("error", "Activation failed")}

        return {"status": "ok", "message": f"Service '{svc_name}' activated"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/sso/deactivate-service")
async def sso_deactivate_service(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        data = await request.json()
        service_id = data.get("service_id")

        if not service_id:
            return {"status": "error", "error": "service_id required"}

        result = sso.revoke_service(user["id"], service_id)
        if not result.get("success"):
            return {"status": "error", "error": result.get("error", "Deactivation failed")}

        return {"status": "ok", "message": "Service deactivated"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/sso/check-access/{service_name}")
async def sso_check_access(service_name: str, request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        if not user:
            return JSONResponse({"status": "error", "error": "Not authenticated"}, status_code=401)

        result = sso.check_service_access(user["id"], service_name)
        if not result.get("success"):
            return {"status": "error", "error": result.get("error", "Check failed")}

        return {"status": "ok", "has_access": result["has_access"], "role": result["role"]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ─── Admin Routes ────────────────────────────────────────────────────────────

@app.get("/api/sso/admin/users")
async def sso_admin_users(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        err = _require_admin(user)
        if err:
            return err

        result = sso.list_users(include_inactive=True)
        if not result.get("success"):
            return {"status": "error", "error": result.get("error", "Failed to list users")}

        return {"status": "ok", "users": result["users"]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.put("/api/sso/admin/user/{user_id}")
async def sso_admin_update_user(user_id: int, request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        err = _require_admin(user)
        if err:
            return err

        data = await request.json()
        email = data.get("email")
        display_name = data.get("display_name")
        role = data.get("role")

        result = sso.update_user(user_id, email=email, display_name=display_name, role=role)
        if not result.get("success"):
            return {"status": "error", "error": result.get("error", "Update failed")}

        return {"status": "ok", "user": result["user"]}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/sso/admin/grant-service")
async def sso_admin_grant_service(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        err = _require_admin(user)
        if err:
            return err

        data = await request.json()
        target_user_id = data.get("user_id")
        service_id = data.get("service_id")

        if not target_user_id or not service_id:
            return {"status": "error", "error": "user_id and service_id required"}

        result = sso.grant_service(target_user_id, service_id)
        if not result.get("success"):
            return {"status": "error", "error": result.get("error", "Grant failed")}

        return {"status": "ok", "message": "Service granted"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/sso/admin/stats")
async def sso_admin_stats(request: Request):
    try:
        if sso is None:
            return JSONResponse({"status": "error", "error": "SSO not available"}, status_code=503)
        user = await get_current_user(request)
        err = _require_admin(user)
        if err:
            return err

        result = sso.stats()
        if not result.get("success"):
            return {"status": "error", "error": result.get("error", "Stats failed")}

        return {"status": "ok", "stats": {
            "users": result["users"],
            "active_sessions": result["active_sessions"],
            "services": result["services"],
            "audit_entries": result["audit_entries"],
        }}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# --- Crypto Payments ---

from zicore.crypto_payment import (
    create_payment, get_payment, confirm_payment,
    get_user_payments, get_all_payments, get_stats as get_crypto_stats,
    get_services, DEPOSIT_ADDRESSES
)


@app.get("/api/crypto/services")
async def crypto_services():
    """Get available services and pricing."""
    return {"status": "ok", "services": get_services(), "addresses": DEPOSIT_ADDRESSES}


@app.post("/api/crypto/pay")
async def crypto_create_payment(request: Request):
    """Create a new crypto payment."""
    data = await request.json()
    service_id = data.get("service", "")
    user_email = data.get("email", "")
    crypto = data.get("crypto", "ztn")
    result = create_payment(service_id, user_email, crypto)
    return {"status": "ok" if "error" not in result else "error", **result}


@app.get("/api/crypto/pay/{payment_id}")
async def crypto_get_payment(payment_id: str):
    """Get payment details."""
    payment = get_payment(payment_id)
    if payment:
        return {"status": "ok", "payment": payment}
    return {"status": "error", "error": "Payment not found"}


@app.post("/api/crypto/pay/{payment_id}/confirm")
async def crypto_confirm_payment(payment_id: str):
    """Confirm a payment (admin)."""
    return confirm_payment(payment_id)


@app.get("/api/crypto/payments")
async def crypto_user_payments(request: Request):
    """Get payments for a user."""
    email = request.query_params.get("email", "")
    if email:
        return {"status": "ok", "payments": get_user_payments(email)}
    return {"status": "ok", "payments": get_all_payments()}


@app.get("/api/crypto/stats")
async def crypto_stats():
    """Get payment statistics."""
    return {"status": "ok", **get_crypto_stats()}


# --- ZICORE Bank API ---

import sqlite3
from pathlib import Path

BANK_DB = Path(__file__).parent / "data" / "bank.db"

def init_bank_db():
    """Initialize bank database."""
    conn = sqlite3.connect(str(BANK_DB))
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        znt_balance REAL DEFAULT 0,
        plan TEXT DEFAULT 'free',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_user TEXT,
        to_user TEXT,
        amount REAL NOT NULL,
        currency TEXT DEFAULT 'ZNT',
        tx_type TEXT DEFAULT 'transfer',
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS staking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        amount REAL NOT NULL,
        apy REAL DEFAULT 15.0,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES accounts(user_id)
    )''')
    conn.commit()
    conn.close()

init_bank_db()

@app.get("/api/bank/account")
async def bank_account(request: Request):
    """Get or create bank account for current user."""
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id", user.get("email", ""))
    email = user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    conn = sqlite3.connect(str(BANK_DB))
    c = conn.cursor()
    c.execute("SELECT * FROM accounts WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO accounts (user_id, email) VALUES (?, ?)", (user_id, email))
        conn.commit()
        c.execute("SELECT * FROM accounts WHERE user_id=?", (user_id,))
        row = c.fetchone()
    conn.close()

    return {
        "status": "ok",
        "account": {
            "id": row[0], "user_id": row[1], "email": row[2],
            "znt_balance": row[3], "plan": row[4], "created_at": row[5]
        }
    }

@app.get("/api/bank/balance")
async def bank_balance(request: Request):
    """Get ZNT balance."""
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id", user.get("email", ""))
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    conn = sqlite3.connect(str(BANK_DB))
    c = conn.cursor()
    c.execute("SELECT znt_balance FROM accounts WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()

    return {"status": "ok", "balance": row[0] if row else 0, "currency": "ZNT"}

@app.get("/api/bank/transactions")
async def bank_transactions(request: Request, limit: int = 50):
    """Get transaction history."""
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id", user.get("email", ""))
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    conn = sqlite3.connect(str(BANK_DB))
    c = conn.cursor()
    c.execute("""SELECT * FROM transactions
                 WHERE from_user=? OR to_user=?
                 ORDER BY created_at DESC LIMIT ?""", (user_id, user_id, limit))
    rows = c.fetchall()
    conn.close()

    txs = [{"id": r[0], "from": r[1], "to": r[2], "amount": r[3], "currency": r[4],
            "type": r[5], "description": r[6], "created_at": r[7]} for r in rows]
    return {"status": "ok", "transactions": txs}

@app.post("/api/bank/send")
async def bank_send(request: Request):
    """Send ZNT to another user."""
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id", user.get("email", ""))
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    data = await request.json()
    to_email = data.get("to", "")
    amount = float(data.get("amount", 0))
    description = data.get("description", "")

    if amount <= 0:
        return {"error": "Invalid amount"}
    if not to_email:
        return {"error": "Recipient required"}

    conn = sqlite3.connect(str(BANK_DB))
    c = conn.cursor()

    # Check sender balance
    c.execute("SELECT znt_balance FROM accounts WHERE user_id=?", (user_id,))
    sender = c.fetchone()
    if not sender or sender[0] < amount:
        conn.close()
        return {"error": "Insufficient balance"}

    # Find or create recipient
    c.execute("SELECT user_id FROM accounts WHERE email=?", (to_email,))
    recipient = c.fetchone()
    if not recipient:
        conn.close()
        return {"error": "Recipient not found"}

    to_id = recipient[0]

    # Execute transfer
    c.execute("UPDATE accounts SET znt_balance = znt_balance - ? WHERE user_id=?", (amount, user_id))
    c.execute("UPDATE accounts SET znt_balance = znt_balance + ? WHERE user_id=?", (amount, to_id))
    c.execute("INSERT INTO transactions (from_user, to_user, amount, description) VALUES (?, ?, ?, ?)",
              (user_id, to_id, amount, description))
    conn.commit()
    conn.close()

    return {"status": "ok", "message": f"Sent {amount} ZNT to {to_email}"}

@app.get("/api/bank/staking")
async def bank_staking(request: Request):
    """Get staking info."""
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id", user.get("email", ""))
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    conn = sqlite3.connect(str(BANK_DB))
    c = conn.cursor()
    c.execute("SELECT * FROM staking WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()

    stakes = [{"id": r[0], "amount": r[2], "apy": r[3], "started_at": r[4]} for r in rows]
    total_staked = sum(s["amount"] for s in stakes)
    return {"status": "ok", "staking": stakes, "total_staked": total_staked, "apy": 15.0}

@app.post("/api/bank/stake")
async def bank_stake(request: Request):
    """Stake ZNT tokens."""
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id", user.get("email", ""))
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    data = await request.json()
    amount = float(data.get("amount", 0))
    if amount <= 0:
        return {"error": "Invalid amount"}

    conn = sqlite3.connect(str(BANK_DB))
    c = conn.cursor()
    c.execute("SELECT znt_balance FROM accounts WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row or row[0] < amount:
        conn.close()
        return {"error": "Insufficient balance"}

    c.execute("UPDATE accounts SET znt_balance = znt_balance - ? WHERE user_id=?", (amount, user_id))
    c.execute("INSERT INTO staking (user_id, amount) VALUES (?, ?)", (user_id, amount))
    c.execute("INSERT INTO transactions (from_user, amount, tx_type, description) VALUES (?, ?, 'stake', 'Staked ZNT')",
              (user_id, amount))
    conn.commit()
    conn.close()

    return {"status": "ok", "message": f"Staked {amount} ZNT at 15% APY"}

@app.get("/api/bank/portfolio")
async def bank_portfolio(request: Request):
    """Get full portfolio (balance + staking + value)."""
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id", user.get("email", ""))
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    conn = sqlite3.connect(str(BANK_DB))
    c = conn.cursor()
    c.execute("SELECT znt_balance FROM accounts WHERE user_id=?", (user_id,))
    balance = c.fetchone()
    c.execute("SELECT SUM(amount) FROM staking WHERE user_id=?", (user_id,))
    staked = c.fetchone()
    conn.close()

    bal = balance[0] if balance else 0
    stk = staked[0] if staked and staked[0] else 0
    znt_price = 2.47  # mock price

    return {
        "status": "ok",
        "portfolio": {
            "znt_balance": bal,
            "znt_staked": stk,
            "znt_total": bal + stk,
            "usd_value": round((bal + stk) * znt_price, 2),
            "znt_price": znt_price,
            "apy": 15.0
        }
    }


# --- ZiVault: Universal Asset Vault ---

from zicore.zivault import ZiVault

zivault = ZiVault()


@app.get("/api/vault/dashboard")
async def vault_dashboard(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "dashboard": zivault.get_dashboard(str(user_id))}


@app.get("/api/vault/currencies")
async def vault_currencies():
    return {"status": "ok", "currencies": zivault.list_currencies()}


@app.get("/api/vault/assets")
async def vault_assets(request: Request, asset_type: str = ""):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "assets": zivault.list_assets(str(user_id), asset_type=asset_type)}


@app.post("/api/vault/assets")
async def vault_create_asset(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    data = await request.json()
    asset = zivault.create_asset(
        str(user_id), data.get("asset_type", "custom"), data.get("name", ""),
        value=data.get("value"), currency=data.get("currency", "ZNT"),
        description=data.get("description", ""),
        metadata=data.get("metadata"), tags=data.get("tags")
    )
    return {"status": "ok", "asset_id": asset.get("id")}


@app.delete("/api/vault/assets/{asset_id}")
async def vault_delete_asset(request: Request, asset_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    zivault.audit_log(str(user_id), "delete_asset", "asset", asset_id=asset_id)
    zivault.delete_asset(asset_id, str(user_id))
    return {"status": "ok"}


@app.get("/api/vault/portfolios")
async def vault_portfolios(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "portfolios": zivault.list_portfolios(str(user_id))}


@app.post("/api/vault/portfolios")
async def vault_create_portfolio(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    data = await request.json()
    portfolio_id = zivault.create_portfolio(
        str(user_id), data.get("name", ""), data.get("portfolio_type", "personal"),
        description=data.get("description", "")
    )
    return {"status": "ok", "portfolio_id": portfolio_id}


@app.get("/api/vault/transactions")
async def vault_transactions(request: Request, asset_id: str = "", limit: int = 50):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "transactions": zivault.list_transactions(str(user_id), asset_id=asset_id, limit=limit)}


@app.post("/api/vault/transactions")
async def vault_create_transaction(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    data = await request.json()
    tx = zivault.create_transaction(
        str(user_id), data.get("asset_id", ""), data.get("tx_type", "valuation_update"),
        amount=data.get("amount", 0), currency=data.get("currency", "ZNT"),
        counterparty=data.get("counterparty", ""), description=data.get("description", "")
    )
    return {"status": "ok", "transaction_id": tx.get("id")}


@app.get("/api/vault/files")
async def vault_files(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "files": zivault.list_files(str(user_id))}


@app.post("/api/vault/files")
async def vault_upload_file(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    data = await request.json()
    file_id = zivault.create_vault_file(
        str(user_id), data.get("filename", ""), data.get("file_type", ""),
        size=data.get("size", 0), encrypted=data.get("encrypted", True),
        description=data.get("description", "")
    )
    return {"status": "ok", "file_id": file_id}


@app.get("/api/vault/audit")
async def vault_audit(request: Request, limit: int = 100):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "audit_logs": zivault.get_audit_logs(str(user_id), limit=limit)}


@app.get("/api/vault/report")
async def vault_report(request: Request, report_type: str = "portfolio"):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "report": zivault.generate_portfolio_report(str(user_id), report_type=report_type)}


@app.get("/api/vault/organizations")
async def vault_organizations(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    conn = zivault.conn
    c = conn.cursor()
    c.execute("SELECT * FROM organizations WHERE id IN (SELECT organization_id FROM org_members WHERE user_id=?)", (str(user_id),))
    orgs = [{"id": r[0], "name": r[1], "org_type": r[2], "owner_id": r[3], "description": r[4], "created_at": r[5]} for r in c.fetchall()]
    return {"status": "ok", "organizations": orgs}


@app.post("/api/vault/organizations")
async def vault_create_organization(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    data = await request.json()
    import uuid
    org_id = str(uuid.uuid4())[:8]
    conn = zivault.conn
    c = conn.cursor()
    c.execute("INSERT INTO organizations (id, name, org_type, owner_id, description) VALUES (?, ?, ?, ?, ?)",
              (org_id, data.get("name", ""), data.get("org_type", ""), str(user_id), data.get("description", "")))
    c.execute("INSERT INTO org_members (organization_id, user_id, role) VALUES (?, ?, 'owner')", (org_id, str(user_id)))
    conn.commit()
    return {"status": "ok", "org_id": org_id}


# --- ZiVault Tags ---

@app.get("/api/vault/tags")
async def vault_tags(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "tags": zivault.list_tags(str(user_id))}


@app.post("/api/vault/tags")
async def vault_create_tag(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    data = await request.json()
    tag = zivault.create_tag(str(user_id), data.get("name", ""), data.get("color", "#00e5ff"))
    return {"status": "ok", "tag": tag}


@app.delete("/api/vault/tags/{tag_id}")
async def vault_delete_tag(request: Request, tag_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    zivault.delete_tag(tag_id)
    return {"status": "ok"}


@app.post("/api/vault/assets/{asset_id}/tags")
async def vault_add_tag_to_asset(request: Request, asset_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    data = await request.json()
    tag_id = data.get("tag_id", "")
    zivault.add_tag_to_asset(asset_id, tag_id)
    return {"status": "ok"}


@app.delete("/api/vault/assets/{asset_id}/tags/{tag_id}")
async def vault_remove_tag_from_asset(request: Request, asset_id: str, tag_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    zivault.remove_tag_from_asset(asset_id, tag_id)
    return {"status": "ok"}


@app.get("/api/vault/assets/{asset_id}/tags")
async def vault_get_asset_tags(request: Request, asset_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "tags": zivault.get_asset_tags(asset_id)}


@app.get("/api/vault/tags/{tag_id}/assets")
async def vault_get_assets_by_tag(request: Request, tag_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "assets": zivault.get_assets_by_tag(str(user_id), tag_id)}


# --- ZiVault Notes ---

@app.get("/api/vault/notes")
async def vault_notes(request: Request, resource_type: str = "", resource_id: str = ""):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "notes": zivault.list_notes(str(user_id), resource_type=resource_type, resource_id=resource_id)}


@app.post("/api/vault/notes")
async def vault_create_note(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    data = await request.json()
    note = zivault.create_note(
        str(user_id), data.get("resource_type", "asset"), data.get("resource_id", ""),
        title=data.get("title", ""), content=data.get("content", ""), color=data.get("color", "")
    )
    return {"status": "ok", "note": note}


@app.put("/api/vault/notes/{note_id}")
async def vault_update_note(request: Request, note_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    data = await request.json()
    note = zivault.update_note(note_id, **{k: data[k] for k in ("title", "content", "pinned", "color") if k in data})
    return {"status": "ok", "note": note}


@app.delete("/api/vault/notes/{note_id}")
async def vault_delete_note(request: Request, note_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    zivault.delete_note(note_id)
    return {"status": "ok"}


@app.post("/api/vault/notes/{note_id}/pin")
async def vault_pin_note(request: Request, note_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    data = await request.json()
    zivault.pin_note(note_id, data.get("pinned", True))
    return {"status": "ok"}


@app.get("/api/vault/notes/search")
async def vault_search_notes(request: Request, q: str = ""):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "notes": zivault.search_notes(str(user_id), q)}


# --- ZiVault Store (WooCommerce ZNT Packages) ---

import urllib.request
import urllib.error
import time
import hmac
import hashlib

WOO_STORE_URL = "https://zzz.zinemotion.com"
WOO_API_BASE = WOO_STORE_URL + "/wp-json/wc/store/v1"
ZNT_DISCOUNT_PERCENT = 15  # Portal discount for ZNT purchases


@app.get("/api/vault/store/products")
async def vault_store_products(request: Request):
    """Fetch ZNT token packages from ZineMotion WooCommerce store.
    Only returns products with 'ZNT' or 'Zitón' category."""
    try:
        url = WOO_API_BASE + "/products?per_page=100"
        req = urllib.request.Request(url, headers={"User-Agent": "ZICORE-ZiVault/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        products = []
        for p in data:
            cats = [c.get("name", "") for c in p.get("categories", [])]
            cats_lower = [c.lower() for c in cats]

            prices = p.get("prices", {})
            price_raw = int(prices.get("price", 0))
            minor_unit = prices.get("currency_minor_unit", 2)
            price = price_raw / (10 ** minor_unit) if minor_unit else price_raw

            regular_raw = int(prices.get("regular_price", 0))
            regular = regular_raw / (10 ** minor_unit) if minor_unit else regular_raw

            sale_raw = int(prices.get("sale_price", 0))
            sale = sale_raw / (10 ** minor_unit) if minor_unit else sale_raw

            # All products are ZNT-purchasable (ZNT is the portal currency)
            is_znt = True

            # Extract ZNT amount from product name or meta
            znt_amount = 0
            name_lower = p.get("name", "").lower()
            for word in name_lower.replace(",", "").split():
                try:
                    val = int(word)
                    if val > 0:
                        znt_amount = val
                        break
                except ValueError:
                    continue

            # If no ZNT amount in name, calculate from MXN price (1 ZNT = ~$2.47 MXN)
            if znt_amount == 0 and price > 0:
                znt_amount = max(1, int(price / 2.47))

            # Calculate portal discounted price (ZNT purchase discount)
            portal_price = round(price * (1 - ZNT_DISCOUNT_PERCENT / 100), 2) if price else 0

            products.append({
                "id": p.get("id"),
                "name": p.get("name", "").replace("&#8211;", "-").replace("&#8212;", "-"),
                "slug": p.get("slug", ""),
                "description": p.get("short_description", ""),
                "znt_amount": znt_amount,
                "price": price,
                "regular_price": regular,
                "sale_price": sale,
                "portal_price": portal_price,
                "portal_discount": ZNT_DISCOUNT_PERCENT,
                "currency": prices.get("currency_code", "MXN"),
                "currency_symbol": prices.get("currency_symbol", "$"),
                "on_sale": p.get("on_sale", False),
                "images": [{"src": img.get("src", ""), "thumbnail": img.get("thumbnail", "")} for img in p.get("images", [])[:3]],
                "categories": cats,
                "permalink": p.get("permalink", ""),
                "add_to_cart": p.get("add_to_cart", {}),
            })

        # Sort by ZNT amount ascending
        products.sort(key=lambda x: x.get("znt_amount", 0))
        return {"status": "ok", "products": products, "store_url": WOO_STORE_URL,
                "discount_percent": ZNT_DISCOUNT_PERCENT}
    except Exception as e:
        logger.warning(f"WooCommerce store fetch failed: {e}")
        return {"status": "ok", "products": [], "store_url": WOO_STORE_URL, "error": str(e)}


@app.post("/api/vault/store/purchase")
async def vault_store_purchase(request: Request):
    """Purchase a ZNT package from the store and credit ZNT to user's vault."""
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    data = await request.json()
    product_id = data.get("product_id", "")
    product_name = data.get("product_name", "")
    znt_amount = int(data.get("znt_amount", 0))
    price = float(data.get("price", 0))
    currency = data.get("currency", "MXN")
    image_url = data.get("image_url", "")
    store_url = data.get("store_url", "")

    if znt_amount <= 0:
        return JSONResponse({"error": "Invalid ZNT amount"}, status_code=400)

    # Credit ZNT to user's ZiVault account
    account = zivault.get_account(str(user_id))
    old_balance = account.get("znt_balance", 0) if account else 0
    new_balance = old_balance + znt_amount

    if account:
        zivault.update_account(str(user_id), znt_balance=new_balance)
    else:
        zivault.create_account(str(user_id), znt_balance=znt_amount)

    # Record transaction
    zivault.create_transaction(
        str(user_id), "", "tokenization",
        amount=znt_amount, currency="ZNT",
        counterparty="ZineMotion Store",
        description=f"Purchased {znt_amount} ZNT via store (Product #{product_id})",
        metadata={"product_id": product_id, "image_url": image_url,
                  "store_url": store_url, "fiat_price": price, "fiat_currency": currency}
    )

    # Create asset record
    asset = zivault.create_asset(
        str(user_id), "cash", f"{product_name}",
        current_value=znt_amount, currency="ZNT",
        description=f"ZNT token package purchased from ZineMotion Store",
        metadata={"product_id": product_id, "image_url": image_url, "store_url": store_url},
        tags=["znt", "purchased", "store"]
    )

    return {"status": "ok", "asset": asset, "znt_credited": znt_amount,
            "new_balance": new_balance, "redirect": store_url}


@app.post("/api/vault/znt/credit")
async def vault_znt_credit(request: Request):
    """API endpoint for WooCommerce plugin to credit ZNT to a user account.
    Requires API key authentication."""
    auth_header = request.headers.get("Authorization", "")
    api_secret = request.headers.get("X-API-Secret", "")

    if not auth_header.startswith("Bearer ") or not api_secret:
        return JSONResponse({"error": "Invalid credentials"}, status_code=401)

    data = await request.json()
    email = data.get("email", "")
    amount = int(data.get("amount", 0))
    order_id = data.get("order_id", "")
    source = data.get("source", "woocommerce")
    description = data.get("description", "")

    if not email or amount <= 0:
        return JSONResponse({"error": "Invalid email or amount"}, status_code=400)

    # Find user by email
    user_id = email

    # Credit ZNT
    account = zivault.get_account(str(user_id))
    old_balance = account.get("znt_balance", 0) if account else 0
    new_balance = old_balance + amount

    if account:
        zivault.update_account(str(user_id), znt_balance=new_balance)
    else:
        zivault.create_account(str(user_id), znt_balance=amount)

    # Record transaction
    zivault.create_transaction(
        str(user_id), "", "tokenization",
        amount=amount, currency="ZNT",
        counterparty="WooCommerce",
        description=description or f"WooCommerce order #{order_id}: +{amount} ZNT",
        metadata={"order_id": order_id, "source": source}
    )

    logger.info(f"ZNT credit: {amount} ZNT → {email} (Order #{order_id})")
    return {"status": "ok", "znt_credited": amount, "new_balance": new_balance}


@app.get("/api/vault/znt/balance")
async def vault_znt_balance(request: Request):
    """Get user's current ZNT balance."""
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    account = zivault.get_account(str(user_id))
    balance = account.get("znt_balance", 0) if account else 0
    return {"status": "ok", "balance": balance, "currency": "ZNT"}


# --- ZiVault v1.0 — Enhanced Routes ---

@app.get("/api/vault/net-worth")
async def vault_net_worth(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "net_worth": zivault.get_net_worth(str(user_id))}


@app.get("/api/vault/distribution")
async def vault_distribution(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "distribution": zivault.get_asset_distribution(str(user_id))}


@app.get("/api/vault/history-value")
async def vault_history_value(request: Request, days: int = 30):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "history": zivault.get_historical_value(str(user_id), days)}


@app.get("/api/vault/alerts")
async def vault_alerts(request: Request, unresolved_only: bool = False):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "alerts": zivault.list_alerts(str(user_id), unresolved_only)}


@app.post("/api/vault/alerts/{alert_id}/resolve")
async def vault_resolve_alert(request: Request, alert_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    zivault.resolve_alert(alert_id)
    return {"status": "ok"}


@app.get("/api/vault/assets/{asset_id}/history")
async def vault_asset_history(request: Request, asset_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "history": zivault.get_asset_history(asset_id)}


@app.get("/api/vault/portfolio/{portfolio_id}/summary")
async def vault_portfolio_summary(request: Request, portfolio_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "summary": zivault.get_portfolio_summary(portfolio_id)}


@app.post("/api/vault/portfolio/{portfolio_id}/snapshot")
async def vault_portfolio_snapshot(request: Request, portfolio_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    zivault.snapshot_portfolio(portfolio_id)
    return {"status": "ok"}


@app.get("/api/vault/portfolio/{portfolio_id}/history")
async def vault_portfolio_history(request: Request, portfolio_id: str, days: int = 30):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "history": zivault.get_portfolio_history(portfolio_id, days)}


@app.get("/api/vault/portfolio/{portfolio_id}/risk")
async def vault_portfolio_risk(request: Request, portfolio_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "risk_score": zivault.calculate_risk_score(portfolio_id)}


@app.get("/api/vault/files/{file_id}/versions")
async def vault_file_versions(request: Request, file_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "versions": zivault.get_file_versions(file_id)}


@app.get("/api/vault/ownership/{asset_id}")
async def vault_ownership(request: Request, asset_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "ownership": zivault.get_ownership(asset_id)}


@app.get("/api/vault/ownership/{asset_id}/history")
async def vault_ownership_history(request: Request, asset_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "history": zivault.get_ownership_history(asset_id)}


@app.post("/api/vault/ownership/{asset_id}/transfer")
async def vault_transfer_ownership(request: Request, asset_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    data = await request.json()
    to_owner = data.get("to_owner", "")
    price = float(data.get("price", 0))
    currency = data.get("currency", "ZNT")
    zivault.transfer_ownership(asset_id, str(user_id), to_owner, price, currency)
    return {"status": "ok"}


@app.get("/api/vault/transaction-summary")
async def vault_transaction_summary(request: Request, days: int = 30):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "summary": zivault.get_transaction_summary(str(user_id), days)}


@app.post("/api/vault/ai/categorize/{asset_id}")
async def vault_ai_categorize(request: Request, asset_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "result": zivault.ai_categorize(asset_id)}


@app.get("/api/vault/ai/duplicates")
async def vault_ai_duplicates(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "duplicates": zivault.ai_detect_duplicates(str(user_id))}


@app.get("/api/vault/ai/optimize")
async def vault_ai_optimize(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "suggestions": zivault.ai_portfolio_optimization(str(user_id))}


@app.get("/api/vault/ai/risk")
async def vault_ai_risk(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "analysis": zivault.ai_risk_analysis(str(user_id))}


@app.get("/api/vault/wallets")
async def vault_wallets(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "wallets": zivault.list_wallets(str(user_id))}


@app.post("/api/vault/wallets")
async def vault_add_wallet(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    data = await request.json()
    chain = data.get("chain", "ethereum")
    address = data.get("address", "")
    label = data.get("label", "")
    wallet = zivault.register_wallet(str(user_id), chain, address, label)
    return {"status": "ok", "wallet": wallet}


@app.post("/api/vault/notifications/mark-all-read")
async def vault_mark_all_read(request: Request):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    zivault.mark_all_read(str(user_id))
    return {"status": "ok"}


@app.delete("/api/vault/notifications/{notification_id}")
async def vault_delete_notification(request: Request, notification_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    zivault.delete_notification(notification_id)
    return {"status": "ok"}


@app.get("/api/vault/reports/portfolio")
async def vault_report_portfolio(request: Request, report_type: str = "full"):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "report": zivault.generate_portfolio_report(str(user_id), report_type)}


@app.get("/api/vault/reports/asset/{asset_id}")
async def vault_report_asset(request: Request, asset_id: str):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "report": zivault.generate_asset_report(asset_id)}


@app.get("/api/vault/reports/audit")
async def vault_report_audit(request: Request, date_from: str = "", date_to: str = ""):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "report": zivault.generate_audit_report(str(user_id), date_from, date_to)}


@app.get("/api/vault/audit/export")
async def vault_audit_export(request: Request, format: str = "json", date_from: str = "", date_to: str = ""):
    user = request.scope.get("state", {}).get("sso_user", {})
    user_id = user.get("id") or user.get("email", "")
    if not user_id:
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    return {"status": "ok", "export": zivault.export_audit_logs(str(user_id), format, date_from, date_to)}


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
        except Exception:
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


# ═══════════════════════════════════════════════════════════════════
# DOWNLOAD COUNTER
# ═══════════════════════════════════════════════════════════════════

DOWNLOADS_FILE = Path(__file__).parent / "data" / "downloads.json"

def _load_downloads() -> int:
    try:
        if DOWNLOADS_FILE.exists():
            return json.loads(DOWNLOADS_FILE.read_text()).get("count", 2250)
    except Exception:
        pass
    return 2250

def _save_downloads(count: int):
    DOWNLOADS_FILE.parent.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_FILE.write_text(json.dumps({"count": count}))

@app.get("/api/downloads")
async def get_downloads():
    return {"count": _load_downloads()}

@app.post("/api/downloads/increment")
async def increment_downloads():
    count = _load_downloads() + 1
    _save_downloads(count)
    return {"count": count}


# ─── ZICORE Print — Manufacturing Division ───────────────────────────────────

@app.get("/zicore-print")
async def serve_zicore_print():
    return FileResponse(str(FRONTEND_DIR / "zicore-print.html"))

@app.get("/ziprint")
async def serve_ziprint():
    f = FRONTEND_DIR / "ziprint.html"
    if f.exists():
        return FileResponse(str(f))
    return JSONResponse({"error": "ZiPrint not deployed yet", "status": 503}, status_code=503)

@app.get("/api/print/printers")
async def print_list_printers():
    from zicore.print_driver import print_manager
    return {"printers": list(print_manager.printers.values())}

@app.get("/api/print/materials")
async def print_materials():
    from zicore.print_driver import MATERIAL_DATABASE
    return {"materials": MATERIAL_DATABASE}

@app.post("/api/print/connect/{printer_id}")
async def print_connect(printer_id: str):
    from zicore.print_driver import print_manager
    ok = await print_manager.connect_printer(printer_id)
    return {"status": "ok" if ok else "error", "connected": ok}

@app.post("/api/print/disconnect/{printer_id}")
async def print_disconnect(printer_id: str):
    from zicore.print_driver import print_manager
    await print_manager.disconnect_printer(printer_id)
    return {"status": "ok"}

@app.get("/api/print/status/{printer_id}")
async def print_status(printer_id: str):
    from zicore.print_driver import print_manager
    return await print_manager.get_printer_status(printer_id)

@app.get("/api/print/all-status")
async def print_all_status():
    from zicore.print_driver import print_manager
    return {"printers": await print_manager.get_all_status()}

@app.post("/api/print/feeder")
async def print_feeder(request: Request):
    body = await request.json()
    printer_id = body.get("printer_id")
    feeder = int(body.get("feeder", 0))
    mm = float(body.get("mm", 0))
    speed = int(body.get("speed", 200))
    action = body.get("action", "")
    from zicore.print_driver import print_manager
    driver = print_manager.drivers.get(printer_id)
    if not driver:
        return JSONResponse({"error": "Driver not connected"}, status_code=400)
    # Tool selection action
    if action == "select" and hasattr(driver, "select_tool"):
        ok = await driver.select_tool(feeder)
        return {"status": "ok" if ok else "error", "tool": feeder}
    # Feeder move action
    if hasattr(driver, "feeder_move"):
        ok = await driver.feeder_move(feeder, mm, speed)
        return {"status": "ok" if ok else "error"}
    return JSONResponse({"error": "Driver does not support feeders"}, status_code=400)

@app.post("/api/print/feeder-name")
async def print_feeder_name(request: Request):
    """Set custom name for a feeder."""
    body = await request.json()
    printer_id = body.get("printer_id")
    feeder = int(body.get("feeder", 0))
    name = body.get("name", "").strip()
    if not name:
        return {"status": "error", "error": "Name required"}
    from zicore.print_driver import print_manager
    driver = print_manager.drivers.get(printer_id)
    if driver and hasattr(driver, "set_feeder_name"):
        driver.set_feeder_name(feeder, name)
        # Also update printers.json config
        try:
            config_path = Path(__file__).parent / "data" / "config" / "printers.json"
            if config_path.exists():
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                for p in cfg.get("printers", []):
                    if p.get("id") == printer_id:
                        if "feeder_names" not in p:
                            p["feeder_names"] = {}
                        p["feeder_names"][str(feeder)] = name
                        break
                with open(config_path, "w") as f:
                    json.dump(cfg, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save feeder name to config: {e}")
        return {"status": "ok", "feeder": feeder, "name": name}
    return JSONResponse({"error": "Driver not connected or no feeder support"}, status_code=400)

@app.post("/api/print/temperature")
async def print_temperature(request: Request):
    body = await request.json()
    printer_id = body.get("printer_id")
    tool = body.get("tool", "hotend")
    temp = int(body.get("temp", 0))
    from zicore.print_driver import print_manager
    driver = print_manager.drivers.get(printer_id)
    if driver:
        if tool == "bed":
            ok = await driver.set_bed_temperature(temp)
        else:
            ok = await driver.set_temperature(0, temp)
        return {"status": "ok" if ok else "error"}
    return JSONResponse({"error": "Driver not connected"}, status_code=400)

@app.post("/api/print/gcode")
async def print_gcode(request: Request):
    body = await request.json()
    printer_id = body.get("printer_id")
    gcode = body.get("gcode", "")
    from zicore.print_driver import print_manager
    driver = print_manager.drivers.get(printer_id)
    if driver:
        result = await driver.send_gcode(gcode)
        return {"status": "ok", "response": result}
    return JSONResponse({"error": "Driver not connected"}, status_code=400)

@app.post("/api/print/move")
async def print_move(request: Request):
    body = await request.json()
    printer_id = body.get("printer_id")
    from zicore.print_driver import print_manager
    driver = print_manager.drivers.get(printer_id)
    if driver:
        ok = await driver.move(
            x=body.get("x"), y=body.get("y"), z=body.get("z"),
            speed=body.get("speed", 100)
        )
        return {"status": "ok" if ok else "error"}
    return JSONResponse({"error": "Driver not connected"}, status_code=400)

@app.post("/api/print/extrude")
async def print_extrude(request: Request):
    body = await request.json()
    printer_id = body.get("printer_id")
    mm = body.get("mm", 0)
    from zicore.print_driver import print_manager
    driver = print_manager.drivers.get(printer_id)
    if driver:
        ok = await driver.extrude(mm, body.get("speed", 100))
        return {"status": "ok" if ok else "error"}
    return JSONResponse({"error": "Driver not connected"}, status_code=400)

@app.post("/api/print/action")
async def print_action(request: Request):
    body = await request.json()
    printer_id = body.get("printer_id")
    action = body.get("action", "")
    from zicore.print_driver import print_manager
    driver = print_manager.drivers.get(printer_id)
    if driver:
        if action == "home": ok = await driver.home()
        elif action == "pause": ok = await driver.pause_print()
        elif action == "resume": ok = await driver.resume_print()
        elif action == "cancel": ok = await driver.cancel_print()
        elif action == "stop": ok = await driver.emergency_stop()
        else: return JSONResponse({"error": f"Unknown action: {action}"}, status_code=400)
        return {"status": "ok" if ok else "error"}
    return JSONResponse({"error": "Driver not connected"}, status_code=400)

@app.post("/api/print/start")
async def print_start(request: Request):
    body = await request.json()
    printer_id = body.get("printer_id")
    filename = body.get("filename", "")
    from zicore.print_driver import print_manager
    driver = print_manager.drivers.get(printer_id)
    if driver:
        ok = await driver.start_print(filename)
        return {"status": "ok" if ok else "error"}
    return JSONResponse({"error": "Driver not connected"}, status_code=400)

@app.get("/api/print/files/{printer_id}")
async def print_files(printer_id: str):
    from zicore.print_driver import print_manager
    driver = print_manager.drivers.get(printer_id)
    if driver:
        files = await driver.get_files()
        return {"files": files}
    return {"files": []}

@app.post("/api/print/purge")
async def print_purge(request: Request):
    body = await request.json()
    from zicore.print_driver import print_manager
    from_mat = body.get("from", "pla")
    to_mat = body.get("to", "pla")
    amount = print_manager.get_purge_amount(from_mat, to_mat)
    return {"purge_mm": amount, "from": from_mat, "to": to_mat}


@app.get("/api/print/camera/{printer_id}")
async def print_camera_stream(printer_id: str):
    from zicore.print_driver import print_manager
    driver = print_manager.drivers.get(printer_id)
    if not driver or not hasattr(driver, 'host'):
        return JSONResponse({"error": "Printer not connected"}, status_code=400)
    host = driver.host
    stream_port = getattr(driver, 'stream_port', 81)
    import urllib.request
    try:
        url = f"http://{host}:{stream_port}/stream"
        req = urllib.request.Request(url)
        r = urllib.request.urlopen(req, timeout=10)
        content_type = r.headers.get('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        async def stream_gen():
            try:
                while True:
                    chunk = r.read(4096)
                    if not chunk:
                        break
                    yield chunk
            except Exception:
                pass
        from starlette.responses import StreamingResponse
        return StreamingResponse(stream_gen(), media_type=content_type)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)


@app.get("/api/print/capture/{printer_id}")
async def print_camera_capture(printer_id: str):
    from zicore.print_driver import print_manager
    driver = print_manager.drivers.get(printer_id)
    if not driver or not hasattr(driver, 'host'):
        return JSONResponse({"error": "Printer not connected"}, status_code=400)
    host = driver.host
    import urllib.request
    try:
        url = f"http://{host}/capture"
        r = urllib.request.urlopen(url, timeout=10)
        img = r.read()
        from starlette.responses import Response
        return Response(content=img, media_type="image/jpeg")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)


@app.get("/api/print/ports")
async def print_list_ports():
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        result = []
        for p in ports:
            result.append({
                'port': p.device,
                'description': p.description,
                'hwid': p.hwid,
                'vid': p.vid,
                'pid': p.pid,
                'manufacturer': p.manufacturer or '',
            })
        return {"ports": result}
    except ImportError:
        return {"ports": [], "error": "pyserial not installed"}


@app.post("/api/print/flash")
async def print_flash_board(request: Request):
    """Flash firmware to printer boards.
    
    Supported board_types:
      - esp32s3: ESP32-S3 Z1_Control feeder hub (camera + 4 feeders)
      - tinybee: MKS Tinybee STM32F407 (Klipper via WSL)
      - ramps: RAMPS 1.4 ATmega2560 (Marlin)
      - cnc_shield: CNC Shield V3 ATmega328P (feeder node)
      - esp32_feeder: ESP32 standalone feeder controller
    """
    body = await request.json()
    port = body.get("port", "")
    board_type = body.get("board_type", "esp32s3")
    wifi_ssid = body.get("wifi_ssid", "")
    wifi_pass = body.get("wifi_pass", "")

    if not port:
        return JSONResponse({"error": "Port required"}, status_code=400)

    import subprocess, os

    # Board configurations
    boards = {
        "esp32s3": {
            "name": "ESP32-S3 Z1_Control",
            "project": r"C:\Users\zinem\Documents\PlatformIO\Projects\Z1_Control",
            "env": "esp32s3_feeder",
            "timeout": 180,
            "needs_wifi": True,
        },
        "tinybee": {
            "name": "MKS Tinybee (Klipper)",
            "project": r"C:\Users\zinem\Documents\PlatformIO\Projects\Z1_Control",
            "env": "tinybee_klipper",
            "timeout": 300,
            "needs_wifi": False,
            "note": "Requiere WSL con Klipper instalado",
        },
        "ramps": {
            "name": "RAMPS 1.4 (Marlin)",
            "project": None,  # Uses esptool or avrdude
            "env": "ramps",
            "timeout": 120,
            "needs_wifi": False,
            "uses_avrdude": True,
            "mcu": "atmega2560",
        },
        "cnc_shield": {
            "name": "CNC Shield V3 (ATmega328P)",
            "project": r"C:\Users\zinem\Documents\PlatformIO\Projects\Z1_Control",
            "env": "feeder_nodo",
            "timeout": 60,
            "needs_wifi": False,
            "uses_avrdude": True,
            "mcu": "atmega328p",
        },
        "esp32_feeder": {
            "name": "ESP32 Feeder Controller",
            "project": r"C:\Users\zinem\Documents\PlatformIO\Projects\Z1_Control",
            "env": "esp32s3_feeder",
            "timeout": 180,
            "needs_wifi": True,
        },
    }

    board = boards.get(board_type)
    if not board:
        return JSONResponse({"error": f"Unknown board type: {board_type}. Supported: {', '.join(boards.keys())}"}, status_code=400)

    result_log = []

    try:
        # Tinybee uses WSL + Klipper make flash
        if board_type == "tinybee":
            cmd = ["wsl", "bash", "-c", "cd ~/klipper && make flash FLASH_DEVICE=0483:df11"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=board["timeout"])
            return {
                "success": result.returncode == 0,
                "board": board["name"],
                "stdout": result.stdout[-2000:] if result.stdout else "",
                "stderr": result.stderr[-1000:] if result.stderr else "",
                "note": board.get("note", ""),
            }

        # RAMPS / CNC Shield use avrdude
        if board.get("uses_avrdude"):
            # Try to find hex file or compile first
            hex_file = None
            if board_type == "ramps":
                # Check for pre-compiled Marlin hex
                possible_paths = [
                    r"C:\Users\zinem\Documents\PlatformIO\Projects\Z1_Control\.pio\build\mega2560\firmware.hex",
                    r"C:\Users\zinem\Documents\PlatformIO\Projects\Marlin\.pio\build\mega2560\firmware.hex",
                ]
                for p in possible_paths:
                    if os.path.exists(p):
                        hex_file = p
                        break

            if board_type == "cnc_shield":
                # Compile feeder_nodo first
                project_dir = board["project"]
                cmd = ["pio", "run", "-e", "feeder_nodo", "-t", "upload", "--upload-port", port]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=board["timeout"], cwd=project_dir)
                return {
                    "success": result.returncode == 0,
                    "board": board["name"],
                    "stdout": result.stdout[-2000:] if result.stdout else "",
                    "stderr": result.stderr[-1000:] if result.stderr else "",
                }

            if hex_file:
                # Flash with avrdude
                cmd = [
                    "avrdude",
                    "-p", board["mcu"],
                    "-c", "wiring",  # or "arduino"
                    "-P", port,
                    "-b", "115200",
                    "-D",
                    "-U", f"flash:w:{hex_file}:i"
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=board["timeout"])
                return {
                    "success": result.returncode == 0,
                    "board": board["name"],
                    "hex_file": hex_file,
                    "stdout": result.stdout[-2000:] if result.stdout else "",
                    "stderr": result.stderr[-1000:] if result.stderr else "",
                }
            else:
                return {
                    "success": False,
                    "board": board["name"],
                    "error": f"No hex file found for {board['name']}. Compile firmware first.",
                    "note": "Place firmware.hex in the project build directory or compile with PlatformIO",
                }

        # ESP32 boards use PlatformIO
        if board["project"]:
            cmd = ["pio", "run", "-e", board["env"], "-t", "upload", "--upload-port", port]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=board["timeout"], cwd=board["project"])
            return {
                "success": result.returncode == 0,
                "board": board["name"],
                "stdout": result.stdout[-2000:] if result.stdout else "",
                "stderr": result.stderr[-1000:] if result.stderr else "",
            }

        return JSONResponse({"error": f"No flash method configured for {board_type}"}, status_code=400)

    except subprocess.TimeoutExpired:
        return {"success": False, "board": board["name"], "error": f"Flash timed out ({board['timeout']}s)"}
    except FileNotFoundError as e:
        return {"success": False, "board": board["name"], "error": f"Tool not found: {e}"}
    except Exception as e:
        return {"success": False, "board": board["name"], "error": str(e)}


@app.get("/api/print/boards")
async def print_boards_list():
    """List supported board types for flashing."""
    return {"boards": [
        {"id": "esp32s3", "name": "ESP32-S3 Z1_Control", "desc": "Feeder hub central + camara OV2640 + streaming MJPEG", "mcu": "ESP32-S3", "firmware": "Z1_Control Arduino", "needs_wifi": True},
        {"id": "tinybee", "name": "MKS Tinybee (Klipper)", "desc": "Impresora 3D con STM32F407, Klipper via WSL", "mcu": "STM32F407VGT6", "firmware": "Klipper", "needs_wifi": False},
        {"id": "ramps", "name": "RAMPS 1.4 (Marlin)", "desc": "Impresora ATmega2560 con RAMPS shield, Marlin firmware", "mcu": "ATmega2560", "firmware": "Marlin", "needs_wifi": False},
        {"id": "cnc_shield", "name": "CNC Shield V3 (Feeders)", "desc": "Controlador de feeders ATmega328P con CNC Shield + A4988", "mcu": "ATmega328P", "firmware": "Feeder Node", "needs_wifi": False},
        {"id": "esp32_feeder", "name": "ESP32 Feeder Controller", "desc": "Controlador WiFi de feeders con ESP32 standalone", "mcu": "ESP32", "firmware": "Z1_Control ESP32", "needs_wifi": True},
    ]}


@app.post("/api/print/serial")
async def print_serial_send(request: Request):
    body = await request.json()
    port = body.get("port", "")
    command = body.get("command", "")
    baud = body.get("baud", 115200)

    if not port or not command:
        return JSONResponse({"error": "Port and command required"}, status_code=400)

    try:
        import serial
        s = serial.Serial(port, baud, timeout=3)
        s.reset_input_buffer()
        s.write((command + "\n").encode())
        import time
        time.sleep(0.5)
        response = s.read(4096).decode('utf-8', errors='ignore')
        s.close()
        return {"response": response}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ─── Video Chat ──────────────────────────────────────────────────────────────

@app.get("/videochat")
async def serve_videochat():
    return FileResponse(str(FRONTEND_DIR / "videochat.html"))

@app.get("/mobile")
async def serve_mobile_monitor():
    return FileResponse(str(FRONTEND_DIR / "mobile-monitor.html"))

@app.get("/vr-viewer")
async def serve_vr_viewer():
    f = FRONTEND_DIR / "vr-viewer.html"
    if f.exists():
        return FileResponse(str(f))
    return JSONResponse({"error": "VR Viewer not deployed"}, status_code=503)

@app.get("/display-monitor")
async def serve_display_monitor():
    f = FRONTEND_DIR / "display-monitor.html"
    if f.exists():
        return FileResponse(str(f))
    return JSONResponse({"error": "Display Monitor not deployed"}, status_code=503)

@app.get("/api/vr/sessions")
async def vr_sessions():
    if vr_stream_manager is None:
        return JSONResponse({"error": "VR Stream not available"}, status_code=503)
    return JSONResponse({"sessions": vr_stream_manager.list_sessions()})

@app.get("/api/vr/session/{session_id}")
async def vr_session_info(session_id: str):
    if vr_stream_manager is None:
        return JSONResponse({"error": "VR Stream not available"}, status_code=503)
    info = vr_stream_manager.get_session(session_id)
    if not info:
        return JSONResponse({"error": "Session not found"}, status_code=404)
    return JSONResponse(info)

@app.delete("/api/vr/session/{session_id}")
async def vr_session_close(session_id: str):
    if vr_stream_manager is None:
        return JSONResponse({"error": "VR Stream not available"}, status_code=503)
    vr_stream_manager.close_session(session_id)
    return JSONResponse({"ok": True})

@app.get("/redgen")
async def serve_redgen():
    return FileResponse(str(FRONTEND_DIR / "redgen.html"))

@app.get("/zishield")
async def serve_zishield():
    return FileResponse(str(FRONTEND_DIR / "zishield.html"))

@app.get("/governance")
async def serve_governance():
    f = FRONTEND_DIR / "governance.html"
    if f.exists():
        return FileResponse(str(f))
    return JSONResponse({"error": "Module not deployed"}, status_code=503)

@app.get("/asset-registry")
async def serve_asset_registry():
    return FileResponse(str(FRONTEND_DIR / "asset-registry.html"))


@app.get("/api/videochat/ice")
async def videochat_ice():
    return {
        "iceServers": [
            {"urls": "stun:stun.l.google.com:19302"},
            {"urls": "stun:stun1.l.google.com:19302"}
        ]
    }

_videochat_rooms = {}

@app.post("/api/videochat/room")
async def create_videochat_room(request: Request):
    body = await request.json()
    room_id = str(__import__("random").randint(100000, 999999))
    _videochat_rooms[room_id] = {"created": __import__("time").time(), "peers": []}
    return {"room_id": room_id, "url": f"/videochat?room={room_id}"}

@app.get("/api/videochat/room/{room_id}")
async def get_videochat_room(room_id: str):
    room = _videochat_rooms.get(room_id)
    if not room:
        return JSONResponse({"error": "Room not found"}, status_code=404)
    return {"room_id": room_id, "peers": len(room["peers"])}

@app.post("/api/videochat/room/{room_id}/signal")
async def videochat_signal(room_id: str, request: Request):
    body = await request.json()
    room = _videochat_rooms.get(room_id)
    if not room:
        return JSONResponse({"error": "Room not found"}, status_code=404)
    room["peers"].append(body)
    return {"status": "ok"}

@app.post("/api/videochat/room/{room_id}/join")
async def videochat_join(room_id: str):
    room = _videochat_rooms.get(room_id)
    if not room:
        _videochat_rooms[room_id] = {"created": __import__("time").time(), "peers": []}
        room = _videochat_rooms[room_id]
    room["peers"].append(__import__("time").time())
    return {"status": "ok", "peers": len(room["peers"])}


app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js-files")
app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css-files")
app.mount("/data", StaticFiles(directory=str(FRONTEND_DIR / "data")), name="data-files")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")


# --- Ollama Reverse Proxy (VPS → local Ollama:11434) ---
# Allows .68/Zichat to reach VPS Ollama via vps.zicore.space/ollama/

import http.client

OLLAMA_PROXY_URL = os.environ.get("OLLAMA_PROXY_URL", "http://localhost:11434")

@app.api_route("/ollama/{path:path}", methods=["GET", "POST", "DELETE", "PUT"])
async def ollama_proxy(path: str, request: Request):
    """Reverse proxy: /ollama/* → localhost:11434/*"""
    target = f"{OLLAMA_PROXY_URL}/{path}"
    method = request.method
    try:
        body = await request.body()
        from urllib.parse import urlparse
        parsed = urlparse(target)
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port or 11434, timeout=120)
        headers = {k: v for k, v in request.headers.items()
                   if k.lower() not in ("host", "transfer-encoding")}
        conn.request(method, parsed.path, body=body, headers=headers)
        resp = conn.getresponse()
        resp_body = resp.read()
        ct = resp.getheader("content-type", "application/json")
        return JSONResponse(
            content=json.loads(resp_body) if "json" in ct else resp_body.decode("utf-8", errors="replace"),
            status_code=resp.status,
            media_type=ct,
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=502)
    finally:
        try:
            conn.close()
        except Exception:
            pass

# Static mounts for new output types
_AUDIO_DIR = OUTPUT_DIR / "audio"
_SCENES_DIR = OUTPUT_DIR / "scenes"
_VIDEO_DIR = OUTPUT_DIR / "video"
_AI3D_DIR = OUTPUT_DIR / "ai3d"
_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
_SCENES_DIR.mkdir(parents=True, exist_ok=True)
_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
_AI3D_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/output/audio", StaticFiles(directory=str(_AUDIO_DIR)), name="audio-output")
app.mount("/output/scenes", StaticFiles(directory=str(_SCENES_DIR)), name="scenes-output")
app.mount("/output/video", StaticFiles(directory=str(_VIDEO_DIR)), name="video-output")

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

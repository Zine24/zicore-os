"""
ZICORE Web Server - Frontend + Backend unified
Serves dashboard, ZIO agent, and API on configurable port.
"""
import os
import sys
import json
import logging
import uvicorn
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("zicore.web")

FRONTEND_DIR = Path(__file__).parent / "frontend"
OUTPUT_DIR = Path(__file__).parent / "output"
CONFIG_DIR = Path(__file__).parent / "data" / "config"
MISSIONS_DIR = Path(__file__).parent / "data" / "missions"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
MISSIONS_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "zio_config.json"

DEFAULT_CONFIG = {
    "providers": {
        "openrouter": {
            "name": "OpenRouter",
            "enabled": False,
            "api_key": "",
            "base_url": "https://openrouter.ai/api/v1",
            "default_model": "meta-llama/llama-3.1-8b-instruct",
            "models": [
                "meta-llama/llama-3.1-8b-instruct",
                "meta-llama/llama-3.1-70b-instruct",
                "mistralai/mistral-7b-instruct",
                "google/gemma-2-9b-it",
                "anthropic/claude-3-haiku",
                "openai/gpt-4o-mini",
            ],
        },
        "ollama": {
            "name": "Ollama (Local)",
            "enabled": False,
            "base_url": "http://localhost:11434",
            "default_model": "llama3.1:8b",
            "models": [
                "llama3.1:8b",
                "llama3.1:70b",
                "mistral:7b",
                "codellama:13b",
                "gemma2:9b",
                "phi3:14b",
            ],
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
                "mixtral-8x7b-32768",
                "gemma2-9b-it",
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
                "mistralai/Mixtral-8x7B-Instruct-v0.1",
                "google/gemma-2-9b-it",
            ],
        },
        "opencode": {
            "name": "OpenCode",
            "enabled": False,
            "api_key": "",
            "base_url": "https://api.opencode.ai/v1",
            "default_model": "opencode/mimo-v2-free",
            "models": [
                "opencode/mimo-v2-free",
                "opencode/mimo-v2-pro",
                "opencode/codestral-2407",
                "opencode/deepseek-v3",
                "opencode/llama-3.1-8b",
                "opencode/mistral-7b",
            ],
        },
    },
    "zio_engine": {
        "active_provider": "zicore_native",
        "temperature": 0.7,
        "max_tokens": 4096,
        "top_p": 0.9,
        "stream": True,
    },
    "theme": "midnight",
    "server": {
        "host": "0.0.0.0",
        "port": 3000,
        "api_port": 8080,
    },
}


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Config saved to {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Failed to save config: {e}")


app = FastAPI(title="ZICORE Web Server", version="3.7.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def serve_main_menu():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/dashboard")
async def serve_dashboard():
    return FileResponse(str(FRONTEND_DIR / "dashboard.html"))


@app.get("/zio")
async def serve_zio():
    return FileResponse(str(FRONTEND_DIR / "zio.html"))


@app.get("/sim")
async def serve_simulator():
    return FileResponse(str(FRONTEND_DIR / "simulator.html"))


@app.get("/api/config")
async def get_config():
    return load_config()


@app.post("/api/config")
async def update_config(config: dict):
    current = load_config()
    current.update(config)
    save_config(current)
    return {"status": "ok", "config": current}


@app.post("/api/config/provider/{provider}")
async def update_provider(provider: str, settings: dict):
    config = load_config()
    if provider in config.get("providers", {}):
        config["providers"][provider].update(settings)
        save_config(config)
        return {"status": "ok", "provider": config["providers"][provider]}
    return {"error": f"Unknown provider: {provider}"}


@app.get("/api/config/provider/{provider}")
async def get_provider(provider: str):
    config = load_config()
    prov = config.get("providers", {}).get(provider)
    if prov:
        return prov
    return {"error": f"Unknown provider: {provider}"}


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
            import urllib.request
            req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            models = [m.get("name", "") for m in data.get("models", [])]
            chat_payload = json.dumps({"model": model, "prompt": "hello", "stream": False}).encode()
            chat_req = urllib.request.Request(f"{base_url}/api/generate", data=chat_payload, headers={"Content-Type": "application/json"}, method="POST")
            chat_resp = urllib.request.urlopen(chat_req, timeout=10)
            chat_data = json.loads(chat_resp.read())
            return {
                "status": "connected",
                "provider": provider,
                "model": model,
                "available_models": models,
                "base_url": base_url,
                "chat_ok": True,
                "response_preview": chat_data.get("response", "")[:80],
            }
        except Exception as e:
            return {"status": "error", "provider": provider, "error": str(e)}

    elif provider in ("openrouter", "openai", "anthropic", "groq", "deepseek", "together", "opencode"):
        if not api_key:
            return {"status": "no_api_key", "provider": provider, "available_models": []}
        return {
            "status": "configured",
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "has_key": True,
            "available_models": prov.get("models", []),
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

    api_key = prov_config.get("api_key", "")
    base_url = prov_config.get("base_url", "")
    model = prov_config.get("default_model", "")

    if not api_key:
        return {"status": "error", "error": "No API key configured"}

    try:
        import urllib.request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        if provider_name == "anthropic":
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": config.get("zio_engine", {}).get("max_tokens", 4096),
            "temperature": config.get("zio_engine", {}).get("temperature", 0.7),
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/chat/completions", data=data, headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read())

        response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {
            "status": "ok",
            "provider": provider_name,
            "model": model,
            "response": response_text,
        }
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

    api_key = prov_config.get("api_key", "")
    base_url = prov_config.get("base_url", "")
    model = prov_config.get("default_model", "")

    if not api_key:
        return {"status": "error", "error": "No API key configured"}

    try:
        import urllib.request
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        system_msg = "You are ZIO, the ZICORE Intelligence Operator. You are an aerospace AI assistant."
        if context:
            system_msg += f"\n\nRelevant knowledge context:\n{context[:1500]}"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": message},
            ],
            "max_tokens": config.get("zio_engine", {}).get("max_tokens", 4096),
            "temperature": config.get("zio_engine", {}).get("temperature", 0.7),
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(f"{base_url}/chat/completions", data=data, headers=headers, method="POST")
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        try:
            from zicore.knowledge_base import knowledge_base
            knowledge_base.add_message("zio", response_text, session_id=session_id)
        except Exception:
            pass
        return {"status": "ok", "response": response_text, "provider": provider, "model": model}
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
            if mesh_type == "cube":
                mesh = trimesh.creation.box(extents=[params.get("size", 1)] * 3)
            elif mesh_type == "sphere":
                mesh = trimesh.creation.icosphere(radius=params.get("radius", 0.5))
            elif mesh_type == "cylinder":
                mesh = trimesh.creation.cylinder(radius=params.get("radius", 0.5), height=params.get("height", 1))
            elif mesh_type == "cone":
                mesh = trimesh.creation.cone(radius=params.get("radius", 0.5), height=params.get("height", 1))
            elif mesh_type == "rocket":
                body_r = params.get("body_radius", 0.3)
                body_h = params.get("body_height", 2)
                nose_r = params.get("nose_radius", body_r)
                nose_h = params.get("nose_height", 0.8)
                body = trimesh.creation.cylinder(radius=body_r, height=body_h)
                nose = trimesh.creation.cone(radius=nose_r, height=nose_h)
                nose.apply_translation([0, 0, body_h / 2 + nose_h / 2])
                mesh = trimesh.util.concatenate([body, nose])
            else:
                mesh = trimesh.creation.box(extents=[1, 1, 1])
            mesh.export(str(output_path))
            return {
                "status": "ok",
                "path": f"/output/meshes/{filename}",
                "type": mesh_type,
                "vertices": len(mesh.vertices),
                "faces": len(mesh.faces),
            }
        except ImportError:
            return {"status": "error", "error": "trimesh not available"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


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
                    user_msg = payload.get("message", "")
                    session_id = payload.get("session_id", "webui")

                    from zicore.knowledge_base import knowledge_base
                    knowledge_base.add_message("user", user_msg, session_id=session_id)

                    context = knowledge_base.get_context_for_query(user_msg)

                    sys.path.insert(0, str(Path(__file__).parent))
                    from agent.core import ZICoreAgent
                    agent = ZICoreAgent(session_id=session_id)
                    import asyncio
                    result = await agent.process(
                        user_msg,
                        {"source": "zio_webui", "module": payload.get("module", "zicorex"),
                         "knowledge_context": context}
                    )

                    reply = result.get("outputs", {}).get("text",
                        result.get("outputs", {}).get("zio_msg", str(result.get("outputs", ""))))
                    knowledge_base.add_message("zio", reply, session_id=session_id,
                                              intent=result.get("intent", ""))

                    await websocket.send_json({
                        "type": "response",
                        "intent": result.get("intent", "general"),
                        "outputs": result.get("outputs", {}),
                        "latency_ms": 0,
                    })
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

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
                    user_msg = payload.get("message", "")
                    session_id = payload.get("session_id", "webui")

                    from zicore.knowledge_base import knowledge_base
                    knowledge_base.add_message("user", user_msg, session_id=session_id)

                    context = knowledge_base.get_context_for_query(user_msg)

                    sys.path.insert(0, str(Path(__file__).parent))
                    from agent.core import ZICoreAgent
                    agent = ZICoreAgent(session_id=session_id)
                    import asyncio
                    result = await agent.process(
                        user_msg,
                        {"source": "zio_webui", "module": payload.get("module", "zicorex"),
                         "knowledge_context": context}
                    )

                    reply = result.get("outputs", {}).get("text",
                        result.get("outputs", {}).get("zio_msg", str(result.get("outputs", ""))))
                    knowledge_base.add_message("zio", reply, session_id=session_id,
                                              intent=result.get("intent", ""))

                    await websocket.send_json({"type": "stream_start", "message": ""})
                    words = reply.split(" ")
                    for word in words:
                        await websocket.send_json({"type": "stream_chunk", "chunk": word + " "})
                        await asyncio.sleep(0.02)
                    await websocket.send_json({
                        "type": "stream_end",
                        "intent": result.get("intent", "general"),
                        "outputs": result.get("outputs", {}),
                        "latency_ms": 0,
                    })
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif command == "config":
                await websocket.send_json({"type": "config", "config": load_config()})

            elif command == "status":
                await websocket.send_json({"type": "status", "server": "ZIO WebUI", "version": "3.7.0"})

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


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    logger.info(f"Starting ZICORE Web Server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)

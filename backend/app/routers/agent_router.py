"""
ZIO Agent API Router - REST + WebSocket endpoints for the agent
"""
import json
import time
import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

logger = logging.getLogger("zicore.agent.api")

router = APIRouter(prefix="/api/agent", tags=["agent"])

OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class AgentRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = "default"


class AgentResponse(BaseModel):
    session_id: str
    intent: str
    input: str
    outputs: Dict[str, Any]
    timestamp: float
    latency_ms: float


class GenerateRequest(BaseModel):
    type: str
    prompt: str
    params: Optional[Dict[str, Any]] = None


class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "default"
    save: Optional[bool] = True


class STTRequest(BaseModel):
    audio_path: Optional[str] = None
    duration: Optional[int] = 5


class InferenceRequest(BaseModel):
    module: str = "zicorex"
    instruction: str = ""
    input_data: str = "{}"
    engine: Optional[str] = "both"


# ── In-memory session store ──────────────────────────────────────────
sessions: Dict[str, Dict[str, Any]] = {}
connected_clients: list = []


def get_or_create_session(session_id: str) -> Dict[str, Any]:
    if session_id not in sessions:
        sessions[session_id] = {
            "id": session_id,
            "history": [],
            "context": {},
            "created": time.time(),
            "last_active": time.time(),
        }
    sessions[session_id]["last_active"] = time.time()
    return sessions[session_id]


# ── REST Endpoints ───────────────────────────────────────────────────

@router.get("/status")
async def agent_status():
    return {
        "status": "online",
        "sessions": len(sessions),
        "connected_clients": len(connected_clients),
        "capabilities": [
            "text_inference",
            "multimedia_generation",
            "voice_recognition",
            "text_to_speech",
            "trajectory_calculation",
            "aircraft_design",
            "telemetry_analysis",
            "3d_mesh_generation",
            "image_generation",
            "video_generation",
            "sound_synthesis",
            "openvision_image_analysis",
            "openvision_video_analysis",
            "openvision_object_detection",
            "data_retention_training",
            "data_retention_export",
        ],
    }


@router.post("/chat")
async def agent_chat(body: AgentRequest):
    t0 = time.time()
    session = get_or_create_session(body.session_id)

    intent = _classify_intent(body.message)
    outputs = {}

    if intent == "inference":
        from ..piplines.orchestrator import PipelineOrchestrator
        orch = PipelineOrchestrator()
        result = await orch.infer("zicorex", body.message, json.dumps(body.context or {}))
        outputs["inference"] = result

    elif intent == "trajectory":
        outputs["trajectory"] = _calc_trajectory(body.message)

    elif intent == "aircraft":
        outputs["aircraft"] = _design_aircraft(body.message)

    elif intent == "telemetry":
        outputs["telemetry"] = _analyze_telemetry(body.message, body.context)

    elif intent == "generate_3d":
        outputs["3d"] = {"status": "queued", "prompt": body.message[:100]}

    elif intent == "generate_image":
        outputs["image"] = {"status": "queued", "prompt": body.message[:100]}

    elif intent == "generate_video":
        outputs["video"] = {"status": "queued", "prompt": body.message[:100]}

    elif intent == "generate_sound":
        outputs["sound"] = {"status": "queued", "prompt": body.message[:100]}

    else:
        outputs["text"] = _general_response(body.message, body.context)

    session["history"].append({
        "role": "user",
        "content": body.message,
        "timestamp": time.time(),
    })
    session["history"].append({
        "role": "assistant",
        "content": outputs,
        "intent": intent,
        "timestamp": time.time(),
    })

    latency = (time.time() - t0) * 1000

    return AgentResponse(
        session_id=body.session_id,
        intent=intent,
        input=body.message,
        outputs=outputs,
        timestamp=time.time(),
        latency_ms=round(latency, 2),
    )


@router.get("/sessions")
async def list_sessions():
    return {
        "sessions": [
            {
                "id": s["id"],
                "messages": len(s["history"]),
                "created": s["created"],
                "last_active": s["last_active"],
            }
            for s in sessions.values()
        ]
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "id": session["id"],
        "history": session["history"][-50:],
        "context": session["context"],
    }


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
    return {"status": "deleted"}


@router.post("/generate")
async def generate_media(body: GenerateRequest):
    result = {"type": body.type, "prompt": body.prompt, "status": "processing"}

    if body.type == "image":
        try:
            from agent.media import MediaEngine
            media = MediaEngine()
            r = media.generate_image(body.prompt)
            result.update(r)
        except Exception as e:
            result["error"] = str(e)

    elif body.type == "video":
        try:
            from agent.media import MediaEngine
            media = MediaEngine()
            r = media.generate_video(body.prompt, duration=body.params.get("duration", 3) if body.params else 3)
            result.update(r)
        except Exception as e:
            result["error"] = str(e)

    elif body.type == "sound":
        try:
            from agent.media import MediaEngine
            media = MediaEngine()
            r = media.generate_sound(body.prompt, duration=body.params.get("duration", 3) if body.params else 3)
            result.update(r)
        except Exception as e:
            result["error"] = str(e)

    elif body.type == "3d":
        try:
            from agent.content3d import Engine3D
            engine = Engine3D()
            r = engine.generate_from_prompt(body.prompt)
            result.update(r)
        except Exception as e:
            result["error"] = str(e)

    return result


@router.post("/tts")
async def text_to_speech(body: TTSRequest):
    try:
        from agent.voice import VoiceEngine
        voice = VoiceEngine()
        r = voice.text_to_speech(body.text)
        return r
    except Exception as e:
        return {"error": str(e), "status": "error"}


@router.post("/stt")
async def speech_to_text(body: STTRequest):
    try:
        from agent.voice import VoiceEngine
        voice = VoiceEngine()
        r = voice.speech_to_text(body.audio_path)
        return r
    except Exception as e:
        return {"error": str(e), "status": "error"}


@router.post("/inference")
async def run_inference(body: InferenceRequest):
    try:
        from ..piplines.orchestrator import PipelineOrchestrator
        orch = PipelineOrchestrator()
        result = await orch.infer(body.module, body.instruction, body.input_data)
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/capabilities")
async def get_capabilities():
    caps = {
        "engines": {
            "engine_a": {"type": "deterministic", "confidence": 0.94, "latency_ms": 0.2},
            "engine_b": {"type": "ml_llm", "confidence": "0.70-0.90", "latency_ms": "variable"},
        },
        "modules": [
            "zinav", "zihab", "zipower", "ziship", "zidrone", "zicomm",
            "zieco", "zimed", "zicorex", "zilink", "zivr", "zisec",
            "zicriogen", "zimaury", "zirobot", "zty",
        ],
        "multimedia": {
            "3d": ["STL", "OBJ"],
            "image": ["PNG", "blueprints", "diagrams"],
            "video": ["frame sequences", "ffmpeg encoding"],
            "sound": ["WAV", "alarms", "engine", "wind", "radio"],
        },
        "voice": {
            "stt": "OpenAI Whisper (base)",
            "tts": "pyttsx3",
        },
        "calculations": ["Hohmann transfer", "lunar transfer", "Mars transfer", "GPD"],
    }
    # Add advanced capabilities
    try:
        from ..engines.engine_b import MLEngine
        eng = MLEngine()
        adv = eng.get_advanced_capabilities()
        caps["advanced"] = {
            "rust_bridge": adv.get("rust_bridge", False),
            "cfd_simulation": adv.get("cfd_simulation", False),
            "unsloth_training": adv.get("unsloth_training", False),
        }
    except Exception:
        caps["advanced"] = {"rust_bridge": False, "cfd_simulation": False, "unsloth_training": False}
    return caps


@router.post("/trajectory")
async def calculate_trajectory(body: AgentRequest):
    """Calculate trajectory using Rust bridge (safety-critical)."""
    try:
        from ..engines.engine_b import MLEngine
        eng = MLEngine()
        params = body.context or {}
        result = eng.calculate_trajectory(
            mission_type=params.get("type", "hohmann"),
            r1=params.get("r1", 6771000),
            r2=params.get("r2", 42164000),
        )
        return result
    except Exception as e:
        return {"error": str(e)}


@router.post("/aerodynamics")
async def analyze_aerodynamics(body: AgentRequest):
    """Full aerodynamic analysis using CFD engine."""
    try:
        from ..engines.engine_b import MLEngine
        eng = MLEngine()
        params = body.context or {}
        result = eng.analyze_aerodynamics(
            velocity=params.get("velocity", 100),
            altitude=params.get("altitude", 0),
            wing_area=params.get("wing_area", 50),
            ar=params.get("aspect_ratio", 8),
        )
        return result
    except Exception as e:
        return {"error": str(e)}


@router.post("/safety-check")
async def safety_check(body: AgentRequest):
    """Safety-critical proximity check."""
    try:
        from ..engines.engine_b import MLEngine
        eng = MLEngine()
        params = body.context or {}
        pos_a = tuple(params.get("pos_a", [0, 0, 0]))
        pos_b = tuple(params.get("pos_b", [1000, 0, 0]))
        radius = params.get("radius", 100)
        result = eng.check_safety(pos_a, pos_b, radius)
        return result
    except Exception as e:
        return {"error": str(e)}


@router.post("/training/start")
async def start_training(body: AgentRequest):
    """Start Unsloth fine-tuning for Motor B."""
    try:
        from ..engines.engine_b import MLEngine
        eng = MLEngine()
        result = eng.start_training(body.context)
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/training/status")
async def training_status():
    """Get training status."""
    try:
        from ..engines.engine_b import MLEngine
        eng = MLEngine()
        return eng.get_training_status()
    except Exception as e:
        return {"error": str(e)}


@router.get("/advanced/status")
async def advanced_status():
    """Get advanced module status (Rust, CFD, Unsloth)."""
    try:
        from ..engines.engine_b import MLEngine
        eng = MLEngine()
        return eng.get_advanced_capabilities()
    except Exception as e:
        return {"error": str(e)}


# ── WebSocket for real-time agent interaction ────────────────────────

@router.websocket("/ws")
async def agent_ws(websocket: WebSocket):
    await websocket.accept()
    session_id = f"ws_{int(time.time())}"
    session = get_or_create_session(session_id)
    connected_clients.append(websocket)
    logger.info(f"Agent WS connected: {session_id}")

    try:
        await websocket.send_json({
            "type": "welcome",
            "session_id": session_id,
            "message": "ZIO Agent online. Ready for commands.",
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
                t0 = time.time()
                text = payload.get("message", "")
                intent = _classify_intent(text)
                outputs = {}

                if intent == "inference":
                    from ..piplines.orchestrator import PipelineOrchestrator
                    orch = PipelineOrchestrator()
                    result = await orch.infer(
                        payload.get("module", "zicorex"),
                        text,
                        json.dumps(payload.get("context", {}))
                    )
                    outputs["inference"] = result
                elif intent == "trajectory":
                    outputs["trajectory"] = _calc_trajectory(text)
                elif intent == "aircraft":
                    outputs["aircraft"] = _design_aircraft(text)
                else:
                    outputs["text"] = _general_response(text, payload.get("context"))

                latency = (time.time() - t0) * 1000
                session["history"].append({"role": "user", "content": text, "ts": time.time()})
                session["history"].append({"role": "assistant", "content": outputs, "intent": intent, "ts": time.time()})

                await websocket.send_json({
                    "type": "response",
                    "intent": intent,
                    "outputs": outputs,
                    "latency_ms": round(latency, 2),
                })

            elif command == "inference":
                from ..piplines.orchestrator import PipelineOrchestrator
                orch = PipelineOrchestrator()
                result = await orch.infer(
                    payload.get("module", "zinav"),
                    payload.get("instruction", "status"),
                    json.dumps(payload.get("data", {}))
                )
                await websocket.send_json({"type": "inference_result", "result": result})

            elif command == "generate":
                gen_type = payload.get("type", "image")
                prompt = payload.get("prompt", "")
                await websocket.send_json({"type": "generating", "generating_type": gen_type})
                result = await _generate_media(gen_type, prompt, payload.get("params", {}))
                await websocket.send_json({"type": "generated", "result": result})

            elif command == "tts":
                text = payload.get("text", "")
                try:
                    from agent.voice import VoiceEngine
                    voice = VoiceEngine()
                    r = voice.text_to_speech(text)
                    await websocket.send_json({"type": "tts_result", "result": r})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif command == "status":
                await websocket.send_json({
                    "type": "status",
                    "session": session_id,
                    "history_len": len(session["history"]),
                    "uptime": time.time() - session["created"],
                })

            elif command == "stream":
                # Streaming response - sends multiple chunks
                t0 = time.time()
                text = payload.get("message", "")
                intent = _classify_intent(text)

                await websocket.send_json({"type": "stream_start", "intent": intent})

                # Simulate streaming by sending chunks
                if intent == "inference":
                    await websocket.send_json({"type": "stream_chunk", "content": "Running inference..."})
                    await asyncio.sleep(0.1)
                    from ..piplines.orchestrator import PipelineOrchestrator
                    orch = PipelineOrchestrator()
                    result = await orch.infer(
                        payload.get("module", "zicorex"),
                        text,
                        json.dumps(payload.get("context", {}))
                    )
                    await websocket.send_json({"type": "stream_chunk", "content": json.dumps(result)})
                elif intent == "trajectory":
                    await websocket.send_json({"type": "stream_chunk", "content": "Calculating trajectory..."})
                    await asyncio.sleep(0.1)
                    tr = _calc_trajectory(text)
                    await websocket.send_json({"type": "stream_chunk", "content": json.dumps(tr)})
                else:
                    # Stream text response word by word
                    response = _general_response(text, payload.get("context"))
                    words = response.split()
                    for i, word in enumerate(words):
                        await websocket.send_json({"type": "stream_chunk", "content": word + " "})
                        if i % 5 == 0:
                            await asyncio.sleep(0.02)

                latency = (time.time() - t0) * 1000
                await websocket.send_json({
                    "type": "stream_end",
                    "intent": intent,
                    "latency_ms": round(latency, 2),
                })

            elif command == "tool":
                # Execute a tool
                tool_name = payload.get("name", "")
                tool_args = payload.get("args", {})
                try:
                    result = session.tools.call(tool_name, **tool_args)
                    await websocket.send_json({"type": "tool_result", "tool": tool_name, "result": result})
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": f"Tool error: {str(e)}"})

            elif command == "tools":
                # List available tools
                tools = session.tools.list_tools()
                await websocket.send_json({"type": "tools_list", "tools": tools})

            else:
                await websocket.send_json({"type": "error", "message": f"Unknown command: {command}"})

    except WebSocketDisconnect:
        logger.info(f"Agent WS disconnected: {session_id}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)


async def _generate_media(gen_type: str, prompt: str, params: dict) -> dict:
    try:
        if gen_type == "image":
            from agent.media import MediaEngine
            return MediaEngine().generate_image(prompt)
        elif gen_type == "video":
            from agent.media import MediaEngine
            return MediaEngine().generate_video(prompt, duration=params.get("duration", 3))
        elif gen_type == "sound":
            from agent.media import MediaEngine
            return MediaEngine().generate_sound(prompt, duration=params.get("duration", 3))
        elif gen_type == "3d":
            from agent.content3d import Engine3D
            return Engine3D().generate_from_prompt(prompt)
        return {"error": f"Unknown type: {gen_type}"}
    except Exception as e:
        return {"error": str(e)}


# ── Intent classification ────────────────────────────────────────────

def _classify_intent(text: str) -> str:
    t = text.lower()
    keywords = {
        "inference": ["infer", "analyze", "evaluate", "assess", "check", "diagnose", "status", "report"],
        "trajectory": ["trajectory", "orbit", "delta-v", "hohmann", "transfer", "insertion", "deorbit", "lunar", "mars"],
        "aircraft": ["design", "aircraft", "rocket", "ship", "vehicle", "airframe", "payload", "build"],
        "telemetry": ["telemetry", "monitor", "watch", "observe", "track"],
        "generate_3d": ["3d", "model", "mesh", "stl", "obj", "render", "sculpt"],
        "generate_image": ["image", "picture", "photo", "draw", "paint", "blueprint", "diagram", "sketch"],
        "generate_video": ["video", "animation", "animate", "simulate", "film", "motion"],
        "generate_sound": ["sound", "audio", "sfx", "alarm", "tone", "noise", "music"],
    }
    for intent, words in keywords.items():
        if any(w in t for w in words):
            return intent
    return "general"


def _calc_trajectory(prompt: str) -> dict:
    import math
    t = prompt.lower()
    mu = 3.986e14
    if "lunar" in t or "moon" in t:
        r1 = (400 + 6371) * 1000
        rm = 384400000
        v1 = math.sqrt(mu / r1)
        vt = math.sqrt(mu * (2 / r1 - 1 / ((r1 + rm) / 2)))
        dv = abs(vt - v1)
        T = math.pi * math.sqrt(((r1 + rm) / 2) ** 3 / mu)
        return {"type": "lunar", "delta_v_ms": round(dv), "time_days": round(T / 86400, 1)}
    elif "mars" in t:
        return {"type": "mars", "delta_v_ms": 5600, "time_days": 259}
    else:
        r1 = (400 + 6371) * 1000
        r2 = (35786 + 6371) * 1000
        at = (r1 + r2) / 2
        v1 = math.sqrt(mu / r1)
        vt = math.sqrt(mu * (2 / r1 - 1 / at))
        dv = abs(vt - v1)
        T = math.pi * math.sqrt(at ** 3 / mu)
        return {"type": "hohmann", "delta_v_ms": round(dv), "time_hours": round(T / 3600, 1)}


def _design_aircraft(prompt: str) -> dict:
    return {
        "name": "ZIO Custom Vehicle",
        "type": "reusable_spacecraft",
        "stages": [
            {"name": "booster", "dry_mass_kg": 15000, "fuel_mass_kg": 85000},
            {"name": "upper", "dry_mass_kg": 3000, "fuel_mass_kg": 17000},
        ],
        "propulsion": {"engine_count": 9, "thrust_kn": 7600, "isp_s": 280},
        "payload_kg": 22800,
        "dimensions": {"length_m": 70, "diameter_m": 12},
    }


def _analyze_telemetry(prompt: str, context: dict = None) -> dict:
    return {
        "analysis": f"Analysis: {prompt[:80]}",
        "health": "nominal",
        "alerts": [],
        "confidence": 0.92,
    }


def _general_response(prompt: str, context: dict = None) -> str:
    return (
        f"ZIO received: '{prompt[:100]}'. "
        "I can help with: inference, trajectory planning, aircraft design, "
        "multimedia generation (3D/image/video/sound), voice commands, "
        "and telemetry analysis. Try a specific command."
    )

"""ZICORE Agent Core — Handles chat, code execution, and AI inference via Ollama."""
import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any, Dict, Optional


CONFIG_DIR = Path(__file__).parent.parent / "data" / "config"
CONFIG_FILE = CONFIG_DIR / "zio_config.json"
DEFAULT_OLLAMA_BASE = os.environ.get("ZICORE_OLLAMA_BASE_URL", "http://localhost:11434")
SYSTEM_PROMPT = (
    "You are ZIO, the ZICORE Intelligence Operator. You control and assist the "
    "ZICORE system with aerospace operations, generation tools, code navigation, "
    "safe workspace edits, and diagnostics. You are running on ZICORE Native "
    "using local inference. Respond concisely and precisely."
)


def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _get_ollama_config() -> tuple:
    config = _load_config()
    zicore_cfg = config.get("providers", {}).get("zicore_native", {})
    ollama_cfg = config.get("providers", {}).get("ollama", {})
    base_url = zicore_cfg.get("base_url") or ollama_cfg.get("base_url") or DEFAULT_OLLAMA_BASE
    model = zicore_cfg.get("default_model") or ollama_cfg.get("default_model") or "gemma3:1b"
    if base_url and not base_url.startswith("http"):
        base_url = f"http://{base_url}"
    return base_url.rstrip("/"), model


class ZICoreAgent:
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.history: list = []

    def _ollama_chat(self, message: str, model: str = None) -> str:
        base_url, default_model = _get_ollama_config()
        if model is None:
            model = default_model
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 2048},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())
                return result.get("message", {}).get("content", "")
        except Exception as e:
            return f"[ZIO Error] {e}"

    def _detect_intent(self, message: str) -> str:
        msg = message.lower()
        if any(w in msg for w in ["generate image", "generate an image", "draw an image", "create an image", "picture of"]):
            return "generate_image"
        if any(w in msg for w in ["generate 3d", "generate a 3d", "make a 3d", "create a 3d", "mesh of", "stl file"]):
            return "generate_3d"
        if any(w in msg for w in ["run code", "execute code", "run python", "execute python", "run script"]):
            return "code"
        if any(w in msg for w in ["write code", "create function", "write function", "generate code", "code for", "write a script", "create a script", "write a program"]):
            return "code_write"
        if any(w in msg for w in ["debug", "find bug", "fix code", "error in", "what's wrong with this code", "review code"]):
            return "code_debug"
        if any(w in msg for w in ["explain code", "what does this code do", "how does this work", "describe this function"]):
            return "code_explain"
        if any(w in msg for w in ["simulate", "simulation", "sim", "run simulation"]):
            return "simulate"
        if any(w in msg for w in ["edit video", "cut video", "trim video", "video editor"]):
            return "video"
        if any(w in msg for w in ["system status", "health check", "system health", "show stats"]):
            return "status"
        if any(w in msg for w in [
            "aerospace", "vehicle design", "propulsion", "orbital", "trajectory",
            "launch", "spacecraft", "rocket", "payload", "delta-v", "thrust",
            "fuel", "engine", "satellite", "orbit", "lunar", "mars", "lander",
            "booster", "stage", "nozzle", "turbopump", "avionics",
            "structural analysis", "stress", "buckling", "fatigue", "safety factor",
            "aerodynamics", "lift", "drag", "mach", "heat shield", "thermal",
            "life support", "eclss", "habitat", "rover", "isru",
            "create improvement", "design improvement", "enhance design",
            "bracket", "mount", "flange", "fitting", "manifold",
        ]):
            return "aerospace_design"
        return "chat"

    async def process(self, message: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        intent = self._detect_intent(message)

        if intent == "status":
            return {
                "intent": "status",
                "outputs": {
                    "text": "All ZICORE systems operational. ZIO agent active.",
                },
            }

        if intent in ("generate_image", "generate_3d", "video"):
            return {
                "intent": intent,
                "outputs": {
                    "text": f"Request received: {intent}. Use the Materializer workspace to process this request.",
                },
            }

        if intent == "code_write":
            reply = self._ollama_chat(
                "You are a coding assistant. Write clean, well-commented code based on this request. "
                "Return ONLY the code inside ```python blocks. No explanation needed.\n\n" + message
            )
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": reply})
            return {"intent": intent, "outputs": {"text": reply, "zio_msg": reply}}

        if intent == "code_debug":
            reply = self._ollama_chat(
                "You are a code debugger. Analyze this code, find bugs, and suggest fixes. "
                "Be specific about line numbers and issues.\n\n" + message
            )
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": reply})
            return {"intent": intent, "outputs": {"text": reply, "zio_msg": reply}}

        if intent == "code_explain":
            reply = self._ollama_chat(
                "You are a code explainer. Explain what this code does step by step. "
                "Be clear and concise.\n\n" + message
            )
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": reply})
            return {"intent": intent, "outputs": {"text": reply, "zio_msg": reply}}

        if intent == "simulate":
            reply = self._ollama_chat(
                "You are a simulation expert for aerospace systems. "
                "Describe the simulation setup, parameters, and expected results. "
                "Use ZICORE simulation modules when available.\n\n" + message
            )
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": reply})
            return {"intent": intent, "outputs": {"text": reply, "zio_msg": reply}}

        if intent == "aerospace_design":
            aerospace_system = (
                "You are ZIO Aerospace Engineering Copilot — an expert aerospace design assistant. "
                "You specialize in: vehicle design (rockets, landers, orbiters, probes), "
                "propulsion systems (chemical, electric, nuclear, fusion), "
                "orbital mechanics (Hohmann transfers, gravity assists, delta-v budgeting), "
                "structural analysis (stress, buckling, fatigue, safety factors), "
                "aerodynamics (lift, drag, Mach number, heating), "
                "thermal control, life support (ECLSS), power systems, "
                "payload integration, and mission planning. "
                "Provide SPECIFIC technical answers with numbers, equations, and actionable recommendations. "
                "Include mass estimates, performance metrics, and trade analyses when relevant. "
                "Reference ZICORE modules (Materializer, Propulsion Lab, Orbital Mechanics, Vehicle Designer) "
                "for procedural generation when appropriate. "
                "If the user asks to create/improve a design, provide a detailed specification "
                "with dimensions, materials, mass properties, and performance characteristics."
            )
            reply = self._ollama_chat(aerospace_system + "\n\n" + message)
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": reply})
            return {"intent": intent, "outputs": {"text": reply, "zio_msg": reply}}

        reply = self._ollama_chat(message)
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": reply})

        return {
            "intent": intent,
            "outputs": {
                "text": reply,
                "zio_msg": reply,
            },
        }

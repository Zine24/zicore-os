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

PROJECTS_DIR = Path(__file__).parent.parent / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)
PROJECT_FILE = PROJECTS_DIR / ".project_active"

SYSTEM_PROMPT = (
    "You are ZIO, the ZICORE Intelligence Operator. You control and assist the "
    "ZICORE system with aerospace operations, generation tools, code navigation, "
    "safe workspace edits, and diagnostics. You are running on ZICORE Native "
    "using local inference. Respond concisely and precisely."
)


def _get_active_project() -> str:
    if PROJECT_FILE.exists():
        return PROJECT_FILE.read_text().strip()
    return ""


def _set_active_project(name: str):
    PROJECTS_DIR.mkdir(exist_ok=True)
    PROJECT_FILE.write_text(name.strip())


def _list_projects() -> list:
    PROJECTS_DIR.mkdir(exist_ok=True)
    return sorted(
        d.name for d in PROJECTS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def _ensure_project(name: str) -> Path:
    p = PROJECTS_DIR / name
    p.mkdir(parents=True, exist_ok=True)
    for sub in ["generations", "exports", "notes", "data"]:
        (p / sub).mkdir(exist_ok=True)
    return p


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
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ZICORE/5.0",
            },
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
        if any(w in msg for w in ["generate sound", "generate audio", "make a sound", "create a sound", "play sound", "sfx"]):
            return "generate_sound"
        if any(w in msg for w in ["edit video", "cut video", "trim video", "video editor"]):
            return "video"
        if any(w in msg for w in ["project", "projects"]):
            if any(w in msg for w in ["create project", "new project", "add project", "make project"]):
                return "project_create"
            if any(w in msg for w in ["switch project", "select project", "change project", "open project", "use project"]):
                return "project_switch"
            if any(w in msg for w in ["list projects", "show projects", "my projects"]):
                return "project_list"
            return "project_info"
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
            active = _get_active_project()
            proj = f" | Active project: {active}" if active else ""
            return {
                "intent": "status",
                "outputs": {
                    "text": f"All ZICORE systems operational. ZIO agent active.{proj}",
                },
            }

        if intent == "project_create":
            name = message.lower().replace("create project", "").replace("new project", "").strip()
            if not name:
                name = f"project_{int(__import__('time').time())}"
            path = _ensure_project(name)
            _set_active_project(name)
            return {"intent": "project_create", "outputs": {"text": f"Project '{name}' created at {path}. Now active."}}

        if intent == "project_switch":
            parts = message.lower().split()
            for w in parts:
                p = PROJECTS_DIR / w
                if p.is_dir() and not w.startswith("."):
                    _set_active_project(w)
                    return {"intent": "project_switch", "outputs": {"text": f"Switched to project '{w}'."}}
            projects = _list_projects()
            if not projects:
                return {"intent": "project_switch", "outputs": {"text": "No projects found. Create one first."}}
            return {"intent": "project_switch", "outputs": {"text": f"Projects: {', '.join(projects)}. Specify one to switch."}}

        if intent == "project_list":
            projects = _list_projects()
            active = _get_active_project()
            if not projects:
                return {"intent": "project_list", "outputs": {"text": "No projects yet. Say 'create project <name>'."}}
            lines = [f"{'* ' if p == active else '  '}{p}" for p in projects]
            return {"intent": "project_list", "outputs": {"text": "Projects:\n" + "\n".join(lines)}}

        if intent == "project_info":
            active = _get_active_project()
            if active:
                p = PROJECTS_DIR / active
                items = [str(f.relative_to(p)) for f in p.rglob("*") if f.is_file()]
                return {"intent": "project_info", "outputs": {"text": f"Project: {active}\nPath: {p}\nFiles: {len(items)}"}}
            return {"intent": "project_info", "outputs": {"text": "No active project. Create or switch to one."}}

        if intent in ("generate_image", "generate_3d", "generate_sound", "video"):
            try:
                from agent.generator import generator as gen
                active = _get_active_project()
                if intent == "generate_image":
                    result = gen.generate_image(message, output_dir=str(PROJECTS_DIR / active / "generations") if active else None)
                elif intent == "generate_3d":
                    result = gen.generate_3d(message, output_dir=str(PROJECTS_DIR / active / "generations") if active else None)
                elif intent == "generate_sound":
                    result = gen.generate_sound(message, output_dir=str(PROJECTS_DIR / active / "generations") if active else None)
                elif intent == "video":
                    result = gen.generate_video(message, output_dir=str(PROJECTS_DIR / active / "generations") if active else None)
                text = f"[{intent.upper()}] Generated: {result.get('file', result.get('path', result.get('message', 'done')))}"
                return {"intent": intent, "outputs": {"text": text, "generation": result}}
            except Exception as e:
                return {"intent": intent, "outputs": {"text": f"Generation failed: {e}"}}

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
            try:
                from zicore.simulation_engine import SimulationEngine
                engine = SimulationEngine()
                result = engine.generate(message, resolution=512)
                sim_id = result.get("simulation_id", "")
                scene_url = f"/visualizer?sim={sim_id}"
                entity_count = len(result.get("config", {}).get("entities", []))
                body_name = result.get("config", {}).get("body", {}).get("name", "unknown")
                terrain_name = result.get("config", {}).get("terrain", {}).get("preset", "unknown")
                text = (
                    f"[SIMULATION GENERATED] ID: {sim_id}\n"
                    f"Body: {body_name} | Terrain: {terrain_name}\n"
                    f"Entities: {entity_count}\n"
                    f"Open Viewer: {scene_url}\n"
                    f"Status: {result.get('status', 'unknown')}"
                )
                self.history.append({"role": "user", "content": message})
                self.history.append({"role": "assistant", "content": text})
                return {
                    "intent": intent,
                    "outputs": {
                        "text": text,
                        "zio_msg": text,
                        "simulation": result,
                    },
                }
            except Exception as e:
                error_text = f"[SIMULATION ERROR] Failed to generate simulation: {e}"
                return {"intent": intent, "outputs": {"text": error_text, "zio_msg": error_text}}

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

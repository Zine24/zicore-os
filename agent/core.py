"""ZICORE Agent Core — Unified agent with tool access, Ollama inference, and workspace sandbox."""
import json
import os
import re
import time
import urllib.request
import urllib.error
import datetime
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("zio.core")


CONFIG_DIR = Path(__file__).parent.parent / "data" / "config"
CONFIG_FILE = CONFIG_DIR / "zio_config.json"
DEFAULT_OLLAMA_BASE = os.environ.get("ZICORE_OLLAMA_BASE_URL", "http://localhost:11434")

# Models with native tool calling support
TOOL_CAPABLE_MODELS = {"qwen3.5:0.8b", "qwen3:0.6b", "qwen3:4b", "qwen3:8b", "qwen2.5-coder:7b", "qwen2.5:7b", "llama3.1:8b", "llama3.3:70b", "gemma3:1b", "gemma3:270m", "gemma3:4b", "gemma4:12b"}

# Ollama-native tool definitions for models that support tools
ZIO_NATIVE_TOOLS = [
    {"type": "function", "function": {"name": "read_file", "description": "Read file contents", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "File path to read"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write content to a file", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "File path"}, "content": {"type": "string", "description": "Content to write"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "list_files", "description": "List files in a directory", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "Directory path"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "run_command", "description": "Run a shell command", "parameters": {"type": "object", "properties": {"command": {"type": "string", "description": "Shell command to execute"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "calculate", "description": "Evaluate a math expression", "parameters": {"type": "object", "properties": {"expression": {"type": "string", "description": "Math expression to evaluate"}}, "required": ["expression"]}}},
    {"type": "function", "function": {"name": "generate_image", "description": "Generate an image from text prompt", "parameters": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Image description"}, "width": {"type": "integer"}, "height": {"type": "integer"}}, "required": ["prompt"]}}},
    {"type": "function", "function": {"name": "generate_3d", "description": "Generate a 3D model from text", "parameters": {"type": "object", "properties": {"prompt": {"type": "string", "description": "3D model description"}, "format": {"type": "string", "enum": ["stl", "glb", "obj"]}}, "required": ["prompt"]}}},
    {"type": "function", "function": {"name": "generate_sound", "description": "Generate a sound effect", "parameters": {"type": "object", "properties": {"prompt": {"type": "string", "description": "Sound description"}, "duration": {"type": "number"}}, "required": ["prompt"]}}},
    {"type": "function", "function": {"name": "capture_webcam", "description": "Capture and analyze image from webcam", "parameters": {"type": "object", "properties": {"device_index": {"type": "integer"}, "width": {"type": "integer"}, "height": {"type": "integer"}}, "required": []}}},
    {"type": "function", "function": {"name": "web_search", "description": "Search the web", "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "Search query"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "web_fetch", "description": "Fetch and read content from a URL", "parameters": {"type": "object", "properties": {"url": {"type": "string", "description": "URL to fetch"}}, "required": ["url"]}}},
    {"type": "function", "function": {"name": "weather", "description": "Get real-time weather for a city", "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": "City name or 'auto' for current location"}}, "required": ["city"]}}},
    {"type": "function", "function": {"name": "edit_file", "description": "Edit a file by replacing old_string with new_string (targeted surgical edit)", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "File path to edit"}, "old_string": {"type": "string", "description": "Exact string to find and replace"}, "new_string": {"type": "string", "description": "Replacement string"}}, "required": ["path", "old_string", "new_string"]}}},
    {"type": "function", "function": {"name": "grep_code", "description": "Search file contents using regex pattern", "parameters": {"type": "object", "properties": {"pattern": {"type": "string", "description": "Regex pattern to search for"}, "path": {"type": "string", "description": "Directory or file to search in"}, "include": {"type": "string", "description": "File extension filter (e.g. '.py')"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {"name": "glob_files", "description": "Find files matching a glob pattern (e.g. **/*.py)", "parameters": {"type": "object", "properties": {"pattern": {"type": "string", "description": "Glob pattern (e.g. **/*.py)"}, "path": {"type": "string", "description": "Root directory to search from"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {"name": "git_operation", "description": "Run git operations (status, diff, log, commit, branch, checkout, stash)", "parameters": {"type": "object", "properties": {"operation": {"type": "string", "enum": ["status", "diff", "log", "show", "branch", "checkout", "commit", "stash"], "description": "Git operation to run"}, "args": {"type": "string", "description": "Additional arguments (e.g. commit message, branch name)"}}, "required": ["operation"]}}},
    {"type": "function", "function": {"name": "plan_task", "description": "Create or manage a task plan with tracked steps", "parameters": {"type": "object", "properties": {"action": {"type": "string", "enum": ["create", "add_step", "complete_step", "list", "get"], "description": "Action to perform"}, "goal": {"type": "string", "description": "Overall goal (for create)"}, "step": {"type": "string", "description": "Step description (for add_step)"}, "step_num": {"type": "integer", "description": "Step number (for complete_step)"}}, "required": ["action"]}}},
    {"type": "function", "function": {"name": "ocr_image", "description": "Extract text from an image using Tesseract OCR", "parameters": {"type": "object", "properties": {"image_path": {"type": "string", "description": "Path to image file"}, "lang": {"type": "string", "description": "OCR language (e.g. spa+eng)"}}, "required": ["image_path"]}}},
    {"type": "function", "function": {"name": "read_pdf", "description": "Extract text and metadata from a PDF file", "parameters": {"type": "object", "properties": {"pdf_path": {"type": "string", "description": "Path to PDF file"}, "pages": {"type": "string", "description": "Page range (e.g. 1-5, 3,7)"}}, "required": ["pdf_path"]}}},
    {"type": "function", "function": {"name": "read_document", "description": "Read any text file (txt, md, csv, json, code, etc.)", "parameters": {"type": "object", "properties": {"path": {"type": "string", "description": "File path to read"}, "max_chars": {"type": "integer", "description": "Max characters to read"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "analyze_document", "description": "Analyze any file: OCR images, read PDFs, extract text from documents", "parameters": {"type": "object", "properties": {"file_path": {"type": "string", "description": "Path to any file"}, "instruction": {"type": "string", "description": "What to analyze"}}, "required": ["file_path"]}}},
]

PROJECTS_DIR = Path(__file__).parent.parent / "projects"
PROJECTS_DIR.mkdir(exist_ok=True)
PROJECT_FILE = PROJECTS_DIR / ".project_active"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VISION_DIR = PROJECT_ROOT / "data" / "vision"

SYSTEM_PROMPT = (
    "You are ZIO, AI copilot of ZICORE SYSTEM v6.0.0 (2027) — an aerospace OS "
    "(Mission Control, Master Creator, Engineering, Aerospace, Materializer, Games, Knowledge). "
    "Use tools when available, never fabricate data, respond concisely. Aerospace precision."
)


def _persona_prompt(persona: Optional[str] = None, knowledge_ctx: str = "") -> str:
    """Resolve the system prompt for a ZIO persona (extension hook).

    Currently supports the CAPCOM mission-control persona provided by the
    zicore.capcom extension. Falls back to the base ZIO prompt otherwise.
    """
    if persona == "capcom":
        try:
            from zicore.capcom import CAPCOM_SYSTEM_PROMPT
            system = CAPCOM_SYSTEM_PROMPT
        except Exception:
            system = (
                "You are CAPCOM — ZIO's mission control voice for ZICORE. "
                "Speak concise, mission-grade flight-controller language. "
                "Never fabricate telemetry. Prefix important announcements with 'CAPCOM:'."
            )
    else:
        system = SYSTEM_PROMPT
    if knowledge_ctx:
        system += f"\n\nKnowledge context:\n{knowledge_ctx[:1500]}"
    return system


def _build_context_prompt(sensor_data: dict = None) -> str:
    """Build context string with current time, server info, and device sensors."""
    now = datetime.datetime.now()
    ctx_lines = [
        f"[CONTEXT] Current time: {now.strftime('%H:%M:%S')}, Date: {now.strftime('%Y-%m-%d')} ({now.strftime('%A')})",
        f"[CONTEXT] Timezone: {now.astimezone().tzname()}",
    ]
    if sensor_data:
        if "battery_level" in sensor_data:
            bat = sensor_data["battery_level"]
            ctx_lines.append(f"[CONTEXT] User device battery: {bat}%")
        if "battery_state" in sensor_data:
            ctx_lines.append(f"[CONTEXT] Battery state: {sensor_data['battery_state']}")
        if "ambient_light" in sensor_data:
            ctx_lines.append(f"[CONTEXT] Ambient light: {sensor_data['ambient_light']} lux")
        if "device_name" in sensor_data:
            ctx_lines.append(f"[CONTEXT] Device: {sensor_data['device_name']}")
        if "os_version" in sensor_data:
            ctx_lines.append(f"[CONTEXT] OS: {sensor_data['os_version']}")
        if "accelerometer" in sensor_data:
            acc = sensor_data["accelerometer"]
            ctx_lines.append(f"[CONTEXT] Accelerometer: x={acc.get('x',0):.2f}, y={acc.get('y',0):.2f}, z={acc.get('z',0):.2f}")
        if "gyroscope" in sensor_data:
            gyro = sensor_data["gyroscope"]
            ctx_lines.append(f"[CONTEXT] Gyroscope: x={gyro.get('x',0):.2f}, y={gyro.get('y',0):.2f}, z={gyro.get('z',0):.2f}")
    return "\n".join(ctx_lines)


# ─── Project helpers ──────────────────────────────────────────────────────────

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


# ─── Config ───────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def time_str_or_now() -> str:
    """Return current time as HH:MM string for alarm fallback."""
    now = datetime.datetime.now()
    return now.strftime("%H:%M")


def _get_ollama_config() -> tuple:
    config = _load_config()
    zicore_cfg = config.get("providers", {}).get("zicore_native", {})
    ollama_cfg = config.get("providers", {}).get("ollama", {})
    base_url = zicore_cfg.get("base_url") or ollama_cfg.get("base_url") or DEFAULT_OLLAMA_BASE
    model = zicore_cfg.get("default_model") or ollama_cfg.get("default_model") or "qwen3.5:0.8b"
    if base_url and not base_url.startswith("http"):
        base_url = f"http://{base_url}"
    return base_url.rstrip("/"), model


def _check_model_loaded(base_url: str, model: str) -> bool:
    """Check if a model is loaded on the Ollama server."""
    try:
        req = urllib.request.Request(
            f"{base_url}/api/tags",
            headers={"User-Agent": "ZICORE/5.0"},
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            for m in data.get("models", []):
                name = m.get("name", "")
                if name == model or name.startswith(model + ":"):
                    return True
            return False
    except Exception:
        return True  # If can't check, assume loaded to avoid blocking


def _pull_model(base_url: str, model: str) -> bool:
    """Attempt to pull a model on the Ollama server. Returns True on success."""
    try:
        logger.info(f"Pulling model '{model}' on {base_url}...")
        payload = json.dumps({"model": model, "stream": False}).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/pull",
            data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "ZICORE/5.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read())
            status = result.get("status", "")
            if "success" in status.lower() or status == "":
                logger.info(f"Model '{model}' pulled successfully")
                return True
            logger.warning(f"Pull status: {status}")
            return True  # Ollama pull returns partial results; assume ok
    except Exception as e:
        logger.error(f"Pull failed for '{model}': {e}")
        return False

TOOL_PATTERNS = {
    "read_file": [
        r"\b(read|open|show|cat|view|look at|contents? of)\b.*\b(file|script|code)\b",
        r"\bwhat('s| is| are) (in|inside) .+\.(py|js|html|json|yaml|yml|txt|md|sh|css)\b",
    ],
    "write_file": [
        r"\b(write|create|save|make) (a )?(file|script|module)\b",
        r"\b(guarda|crea|escribe|genera) (un )?(archivo|script)\b",
    ],
    "list_files": [
        r"\b(list|show|ls|dir|what('s| is| are)) .*\b(file|folder|director)\b",
        r"\b(que) (archivos|carpetas|folders) .*\b(hay|tienes|existen)\b",
    ],
    "run_command": [
        r"\b(run|execute|exec|shell|terminal|bash)\b.*\b(command|cmd|comando)\b",
        r"\b(install|pip|npm|apt|apt-get|yum|brew)\b",
    ],
    "calculate": [
        r"\b(calc|calculate|math|compute|eval|what('s| is| are))\b.*\b(\d+|equation|formula)\b",
        r"\b(berapa|cuanto|resultado de)\b.*[\d\+\-\*\/]",
    ],
    "web_search": [
        r"\b(search|google|lookup|find online|look up|web search)\b",
        r"\b(busca|buscar|investiga|que es|what is|who is|cuando|when did)\b",
    ],
    "web_fetch": [
        r"\b(open|fetch|read|get|scrape|load|access)\s+(https?://\S+)",
        r"\b(open|fetch|read|get|scrape|load|access)\s+(?:the\s+)?(?:url|page|website|link|webpage)\s+(\S+)",
        r"\b(abre|carga|lee|obten|scrape|accede)\s+(https?://\S+)",
        r"\b(what('s| is| are))\s+(on|in|at)\s+(https?://\S+)",
    ],
    "generate_image": [
        r"\b(generate|create|make|draw|paint|render) .*\b(image|picture|photo|img|imagen|foto)\b",
        r"\b(dibuja|genera|crea) .*\b(imagen|foto|ilustracion)\b",
    ],
    "generate_3d": [
        r"\b(generate|create|make|build) .*\b(3d|3d model|mesh|stl|obj|tridimensional)\b",
        r"\b(genera|crea|construye) .*\b(modelo 3d|malla)\b",
    ],
    "generate_sound": [
        r"\b(generate|create|make|play) .*\b(sound|audio|sfx|tone|beep|alarm|sonido)\b",
        r"\b(genera|crea|reproduce) .*\b(sonido|audio)\b",
    ],
    "generate_video": [
        r"\b(generate|create|make|render) .*\b(video|animation|clip|animacion)\b",
        r"\b(genera|crea) .*\b(video|animacion)\b",
    ],
    "analyze_image": [
        r"\b(analyze|analyse|scan|inspect|examine|look at|what do you see|detect objects|ocr|read text)\b.*\b(image|photo|picture|camera|webcam|frame|capture)\b",
        r"\b(analiza|escanea|inspecciona|que ves|detecta|lee texto|captura)\b.*\b(imagen|foto|camara|pantalla)\b",
        r"\b(camera|webcam|cam)\b.*\b(capture|snapshot|take|grab|screenshot)\b",
        r"\b(captura|toma foto|sacar foto)\b",
    ],
    "capture_webcam": [
        r"\b(capture|take|grab|screenshot|snap)\b.*\b(webcam|camera|cam|photo|picture)\b",
        r"\b(captura|toma foto|sacar foto|foto con camara)\b",
    ],
    "device_control": [
        r"\b(vibrate|vibration|shake|haptic|buzz)\b",
        r"\bflashlight|torch|led|linterna|foco|luz.*celular|luz.*telefono",
        r"\b(brightness|brillo|dim|bright|oscurecer|aclarar)\b",
        r"\b(clipboard|copy|copiar|pegar|paste)\b",
        r"\b(notify|notification|notificacion|alerta|aviso)\b",
        r"\b(open|abrir|launch|iniciar)\b.*\b(app|url|link|navegador|browser)\b",
    ],
    "camera_control": [
        r"\b(open|turn on|start|abre|enciende|inicia)\b.*\b(camera|camara|cam|lente|lens)\b",
        r"\b(capture|take|sacar|tomar)\b.*\b(photo|foto|picture|imagen)\b",
        r"\b(look|see|que|que hay)\b.*\b(at|en|veo|ves)\b.*\b(this|esto|eso|here|aqui)\b",
        r"\b(scan|escanea|analiza|describe|what.*see|what.*look)\b",
        r"\b(close|cierra|apaga|stop)\b.*\b(camera|camara|cam)\b",
        r"\b(switch|cambia|voltea)\b.*\b(camera|camara|front|trasera|delantera|frente)\b",
        r"\b(what|que|describe|descr|how|como)\b.*\b(look|color|colores|shape|forma|size|tamaño)\b.*\b(this|this|esto|eso|object|objeto)\b",
        r"\b(read|lee|ocr|text|texto)\b.*\b(this|esto|documento|document|paper|papel)\b",
        r"\b(detect|detecta|identify|identifica|find|encuentra)\b.*\b(object|objeto|person|persona|face|cara|caras)\b",
        r"\b(photo|foto) (of|de) (this|esto|eso|here|aqui)\b",
    ],
    "calculate_trajectory": [
        r"\b(trajectory|orbit|hohmann|transfer|delta.?v|delta.?vee|launch)\b",
        r"\b(trayectoria|orbita|hohmann|transferencia|lanzamiento)\b",
    ],
    "status": [
        r"\b(status|health|how are you|system|report|stats|diagnostics?)\b",
        r"\b(estado|salud|sistemas?|reporte|diagnostico)\b",
    ],
    "timestamp": [
        r"\b(what('s| is) (the )?(time|date|day)|current time|now|hora|fecha)\b",
    ],
    "random": [
        r"\b(random|rand|pick|choose|sort|aleatorio|azar)\b",
    ],
    "weather": [
        r"\b(weather|clima|temperature|temperatura|rain|lluvia|snow|nieve|wind|viento)\b",
        r"\b(cómo|como)\b.*\b(está|esta|esta el|el clima|afuera|outside)\b",
    ],
    "music": [
        r"\b(play|reproduce|pon|poner|escuchar|listen)\b.*\b(music|música|musica|song|cancion|canción|album|artista|artist)\b",
        r"\b(stop music|para la música|pausa|pause)\b",
    ],
    "edit_file": [
        r"\b(edit|modify|change|update|replace|fix|patch|corregir|modificar|cambiar|actualizar|edita|cambia|modifica)\b.*\b(file|code|script|archivo)\b",
        r"\b(in|en|file|archivo)\b.*\b(replace|cambiar|cambia)\b.*\b(with|con|por)\b",
        r"\b(edita|modifica|cambia|actualiza)\s+(el\s+|un\s+)?\S+\.\w+\b",
        r"\b(cambia|replace)\s+(la\s+)?(palabra|word)\s+\S+\s+(por|with)\s+\S+\b",
    ],
    "grep_code": [
        r"\b(search|find|grep|look for|busca|encuentra)\b.*\b(code|funcion|function|class|variable|import)\b.*\b(in|en|files?)?\b",
        r"\b(grep|search)\b.*\b(for|por|regex|pattern)\b",
    ],
    "glob_files": [
        r"\b(find|list|show|glob|match|busca|encuentra)\b.*\b(all )?\b(files?|archivos?)\b.*\b(with|con|matching|like|pattern|\.py|\.js|\.ts|\.html|\.json)\b",
        r"\b(\*\*\/*\.|\*\.\w+)\b",
    ],
    "git_operation": [
        r"\b(git)\b.*\b(status|diff|log|commit|branch|checkout|stash|push|pull|merge|rebase)\b",
        r"\b(commit|guarda cambios|subir cambios|push|ramas?|branches?)\b",
    ],
    "plan_task": [
        r"\b(plan|planea|organize|organiza|steps?|pasos?|tasks?|tareas?|todo|checklist)\b",
        r"\b(break down|desglosa|divide|split|divide into)\b.*\b(steps?|pasos?|parts?|partes?)\b",
    ],
    "ocr_image": [
        r"\b(ocr|extract text|read text|lee texto|extraer texto|scan text)\b.*\b(from|de|from image|de imagen)\b",
        r"\b(what does.*say|que dice|read.*image|lee.*imagen|text in|texto en)\b",
    ],
    "read_pdf": [
        r"\b(read|open|lee|abre|extract|extraer|parse|parsea)\s+(pdf|document|documento)\b",
        r"\b(pdf|document|documento)\s+(content|contenido|text|texto|summary|resumen)\b",
    ],
    "read_document": [
        r"\b(read|open|lee|abre|show|muestra|cat|type)\s+\S+\.(txt|md|csv|json|py|js|ts|html|css|xml|yaml|yml|toml|cfg|ini|conf|log)\b",
    ],
    "analyze_document": [
        r"\b(analyze|analyse|analiza|inspect|inspecciona|review|revisa)\s+(file|archivo|document|documento|image|imagen|pdf)\b",
    ],
    "store_memory": [
        r"\b(remember|recuerda|guarda|store|save|memorize)\s+(that|que|esto|this|lo siguiente)\b",
        r"\b(remember|recuerda|store|guarda)\s+(key|clave|variable)\s*[:=]?\s*\S+",
    ],
    "recall_memory": [
        r"\b(remember|recall|recuerda|que|what)\b.*\b(did|was|is|about|regarding|concerning)\b.*\b(i|we|you|we say|you said|I said)\b",
        r"\b(recall|consulta|lookup|check)\s+(memory|memoria|key|clave)\b",
    ],
    "conversation_summary": [
        r"\b(summary|resumen|recap|summarize|resume|what (have|did) (we|i) (been )?(talking|discussing|chatting))\b",
    ],
    "send_notification": [
        r"\b(send|manda|envia|push|trigger)\s+(a\s+)?notification\b",
        r"\b(notify|notifica|avisa|alert)\s+(me|user|usuario)\b",
    ],
    "create_reminder": [
        r"\b(set|create|crea|agrega|pon)\s+(a\s+)?reminder\b",
        r"\b(remind|recuerda|avísame|avisame)\s+(me|a mi)\s+(in|en|at|para|about|que)\s+\d+\s*(min|minute|minuto|hour|hora|seg|second|segundo)",
    ],
    "set_alarm": [
        r"\b(set|pon|crea|agrega|activa)\s+(a\s+)?alarm\b",
        r"\b(alarm|alarma|temporizador|timer)\s+(for|para|at|en|to|de)\s+\d+",
        r"\b(wake me|despierta|alerta)\s+(at|en|para|a las)\s+\d+",
    ],
    "system_command": [
        r"\b(system status|estado del sistema|estado del server|system health|report|stats of the system)\b",
        r"\b(run diagnostics|diagnostico|corre diagnostico)\b",
        r"\b(list (the )?(volumes|volumenes)|list (the )?(drives|discos|unidades))\b",
        r"\b(media rescan|rescanea|rescan media|actualiza (el )?catalogo)\b",
        r"\b(convert (the )?model|convierte (el )?modelo)\b",
        r"\b(backup|respaldo|respaldar|haz backup)\b",
        r"\b(start the music|play music|play a song|pon musica|pon música|reproduce musica|reproduce música|play (the )?(movie|film|video|pelicula|película))\b",
        r"\b(search for (this )?(movie|film|video|pelicula|película)|busca (una )?(pelicula|película|movie|film)|find (a|this) (movie|film|video|song))\b",
        r"\b(stop music|stop the music|para la musica|para la música|pausa la musica|pause music)\b",
    ],
}


def _resolve_tools(message: str, session) -> List[Dict[str, Any]]:
    """Check if any tools match the message and return their results."""
    msg_lower = message.lower()
    results = []

    for tool_name, patterns in TOOL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                if session.tools.exists(tool_name):
                    try:
                        # Extract parameters from message
                        kwargs = _extract_tool_params(tool_name, message)
                        result = session.tools.call(tool_name, **kwargs)
                        results.append({
                            "tool": tool_name,
                            "result": result,
                            "success": "error" not in result if isinstance(result, dict) else True,
                        })
                    except Exception as e:
                        results.append({
                            "tool": tool_name,
                            "result": {"error": str(e)},
                            "success": False,
                        })
                break  # first matching pattern per tool

    return results


def _extract_tool_params(tool_name: str, message: str) -> dict:
    """Extract tool parameters from the user message."""
    if tool_name == "calculate":
        # Extract math expression
        math_patterns = [
            r"(?:calculate|compute|eval|math|what(?:'s| is| are))\s+(.+?)(?:\?|$)",
            r"(\d[\d\+\-\*\/\(\)\.\s]+)",
        ]
        for p in math_patterns:
            m = re.search(p, message, re.IGNORECASE)
            if m:
                return {"expression": m.group(1).strip()}
        return {"expression": message}

    if tool_name == "read_file":
        # Extract file path
        m = re.search(r"(?:read|open|show|cat|view|contents?\s+of)\s+([^\s]+\.\w+)", message, re.IGNORECASE)
        if not m:
            m = re.search(r"([^\s]+\.(?:py|js|html|json|yaml|yml|txt|md|sh|css))", message, re.IGNORECASE)
        if m:
            return {"path": m.group(1)}
        return {"path": "."}

    if tool_name == "write_file":
        m = re.search(r"(?:write|create|save|make)\s+(?:a\s+)?(?:file|script)\s+(\S+)", message, re.IGNORECASE)
        path = m.group(1) if m else "output.txt"
        content = message
        return {"path": path, "content": content}

    if tool_name == "list_files":
        m = re.search(r"(?:list|show|ls|dir)\s+(.+?)(?:\?|$)", message, re.IGNORECASE)
        path = m.group(1).strip() if m else "."
        return {"path": path}

    if tool_name == "run_command":
        m = re.search(r"(?:run|execute|exec)\s+(.+?)(?:\?|$)", message, re.IGNORECASE)
        if m:
            return {"command": m.group(1).strip()}
        # Direct package managers
        m = re.search(r"(pip\s+install\s+\S+|npm\s+\S+\s+\S+)", message, re.IGNORECASE)
        if m:
            return {"command": m.group(1)}
        return {"command": "echo 'no command specified'"}

    if tool_name == "web_search":
        return {"query": message}

    if tool_name == "web_fetch":
        m = re.search(r'(https?://[^\s]+)', message, re.IGNORECASE)
        if m:
            return {"url": m.group(1)}
        return {"url": ""}

    if tool_name == "weather":
        m = re.search(r'(?:weather|clima|temperature|temperatura)\s+(?:in|en|for|de|para|at)\s+([a-zA-Z\s,]+?)(?:\s*\?|\s*$|\s+and|\s+y|\s+but|\s+pero)', message, re.IGNORECASE)
        if m:
            return {"city": m.group(1).strip()}
        m = re.search(r'(?:in|en|for|de|para|at)\s+([a-zA-Z\s]+?)(?:\s*\?|\s*$)', message, re.IGNORECASE)
        if m:
            return {"city": m.group(1).strip()}
        return {"city": "auto"}

    if tool_name == "generate_image":
        return {"prompt": message}

    if tool_name == "generate_3d":
        return {"prompt": message}

    if tool_name == "analyze_image":
        m = re.search(r"(?:read|open|show|analyze|scan|inspect|view)\s+(?:the\s+)?(?:image|photo|picture|file)\s+(\S+)", message, re.IGNORECASE)
        if m:
            return {"image_path": m.group(1)}
        return {"image_path": ""}

    if tool_name == "capture_webcam":
        return {"device_index": 0}

    if tool_name == "generate_sound":
        return {"prompt": message}

    if tool_name == "generate_video":
        return {"prompt": message}

    if tool_name == "calculate_trajectory":
        return {"type": "hohmann"}

    if tool_name == "random":
        m = re.search(r'(\d+)\s*(?:to|-)\s*(\d+)', message)
        if m:
            return {"min_val": float(m.group(1)), "max_val": float(m.group(2))}
        return {"min_val": 0, "max_val": 100}

    if tool_name == "edit_file":
        # Path: "(edit|...)(in|el|un)? (file|archivo) <path>" or bare path token with extension
        m = re.search(r"(?:edit|modify|change|update|replace|fix|patch|edita|modifica|cambia|actualiza)\b[^.]*?(?:(?:in|el|un)\s+)?(?:file|archivo\s+)?((?:[^\s]+/)*[^\s]+\.\w+)", message, re.IGNORECASE)
        path = m.group(1).strip() if m else ""
        # Replace: "cambia(replace) (la) (palabra) X (por|with|con) (la) (palabra) Y"
        m2 = re.search(r"(?:replace|cambia|cambiar)\s+(?:la\s+)?(?:palabra|word|texto|text\s+)?\s*['\"]?([^'\"]+?)['\"]?\s+(?:por|with|con)\s+(?:la\s+)?(?:palabra|word|texto|text\s+)?\s*['\"]?([^'\"]+?)['\"]?$", message, re.IGNORECASE)
        if not m2:
            m2 = re.search(r"(?:replace|cambia|cambiar)\s+(?:la\s+)?(?:palabra|word|texto|text\s+)?\s*['\"]?([^'\"]+?)['\"]?\s+(?:por|with|con)\s+(?:la\s+)?(?:palabra|word|texto|text\s+)?\s*['\"]?([^'\"]+?)['\"]?", message, re.IGNORECASE)
        if m2:
            return {"path": path, "old_string": m2.group(1).strip(), "new_string": m2.group(2).strip()}
        return {"path": path, "old_string": "", "new_string": ""}

    if tool_name == "grep_code":
        m = re.search(r"(?:search|find|grep|look for|busca|encuentra)\s+(?:for\s+)?['\"]?(.+?)['\"]?\s+(?:in|en)\s+(\S+)", message, re.IGNORECASE)
        if m:
            return {"pattern": m.group(1), "path": m.group(2)}
        m = re.search(r"(?:grep|search)\s+['\"](.+?)['\"]", message, re.IGNORECASE)
        if m:
            return {"pattern": m.group(1), "path": "."}
        return {"pattern": message, "path": "."}

    if tool_name == "glob_files":
        m = re.search(r"(\*\*?\.\w+|\*\*/\*\.\w+)", message)
        if m:
            return {"pattern": m.group(1), "path": "."}
        m = re.search(r"(?:find|list|show|glob)\s+(?:all\s+)?(?:files?\s+)?(?:with|con|matching|like|pattern)\s+(\S+)", message, re.IGNORECASE)
        if m:
            return {"pattern": f"**/*{m.group(1)}", "path": "."}
        return {"pattern": "**/*", "path": "."}

    if tool_name == "system_command":
        msg_lower = message.lower()
        if any(w in msg_lower for w in ["system status", "estado del sistema", "estado del server", "system health", "report", "stats of the system", "system stats"]):
            return {"name": "system_status"}
        if any(w in msg_lower for w in ["diagnostics", "diagnostico", "corre diagnostico", "run diagnostics"]):
            return {"name": "diagnostics"}
        if any(w in msg_lower for w in ["list the volumes", "list volumes", "volumenes", "list the drives", "list drives", "discos", "unidades"]):
            if any(w in msg_lower for w in ["volume", "volumenes", "vol"]):
                return {"name": "list_volumes"}
            return {"name": "list_drives"}
        if any(w in msg_lower for w in ["media rescan", "rescanea", "rescan media", "actualiza el catalogo", "actualiza catalogo", "refresh catalog"]):
            return {"name": "media_rescan"}
        if any(w in msg_lower for w in ["convert the model", "convert model", "convierte el modelo", "convierte modelo", "convert 3d"]):
            m = re.search(r"(?:convert|convierte)\s+(?:the\s+)?(?:model\s+)?(.+?)(?:\?|$)", message, re.IGNORECASE)
            path = m.group(1).strip() if m else ""
            return {"name": "convert_model", "params": {"path": path}}
        if any(w in msg_lower for w in ["backup", "respaldo", "respaldar", "haz backup", "make a backup", "create backup"]):
            return {"name": "backup"}
        if any(w in msg_lower for w in ["stop music", "stop the music", "para la musica", "para la música", "pausa la musica", "pause music"]):
            return {"name": "media_stop"}
        if any(w in msg_lower for w in ["start the music", "play music", "play a song", "pon musica", "pon música", "reproduce musica", "reproduce música"]) or re.search(r"\bplay (the )?(movie|film|video|pelicula|película)\b", msg_lower):
            m = re.search(r"(?:start|play|reproduce|pon|poner)\s+(?:the\s+|some\s+|a\s+)?(.+)", message, re.IGNORECASE)
            query = m.group(1).strip() if m else ""
            if re.fullmatch(r"(music|musica|música|song|la musica|la música|the music)", query.lower()):
                query = ""
            category = "video" if any(w in query.lower() for w in ("movie", "film", "video", "pelicula", "película")) else "music"
            return {"name": "media_play", "params": {"query": query, "category": category}}
        if any(w in msg_lower for w in ["search for this movie", "search for a movie", "search for the movie", "find this movie", "find a movie", "busca una pelicula", "busca una película", "busca esta pelicula", "busca esta película", "search for this film", "find a song"]):
            m = re.search(r"(?:search|find|busca|buscar)\s+(?:for\s+|this\s+|a\s+|una\s+)?(.+)", message, re.IGNORECASE)
            query = m.group(1).strip() if m else ""
            query = re.sub(r"\b(this movie|this film|esta pelicula|esta película|a movie|una pelicula|una película)\b", "", query).strip(" .,;:!?")
            category = "video" if any(w in msg_lower for w in ("movie", "film", "pelicula", "película")) else ""
            return {"name": "media_search", "params": {"query": query, "category": category}}
        return {"name": ""}

    if tool_name == "git_operation":
        m = re.search(r"\b(git)\s+(status|diff|log|show|branch|checkout|commit|stash|merge|rebase|add|reset)\b", message, re.IGNORECASE)
        if m:
            op = m.group(2)
            args_str = re.sub(r"^.*\b(git\s+)?\b(status|diff|log|show|branch|checkout|commit|stash|merge|rebase|add|reset)\b\s*", "", message, flags=re.IGNORECASE).strip()
            return {"operation": op, "args": args_str}
        if any(w in message.lower() for w in ["commit", "guarda cambios", "save changes"]):
            m = re.search(r"(?:commit|guarda)\s+(.+)", message, re.IGNORECASE)
            msg_text = m.group(1).strip() if m else "Update from ZIO"
            return {"operation": "commit", "args": f'-m "{msg_text}"'}
        if any(w in message.lower() for w in ["git status", "repository status", "repo status", "estado del repo"]):
            return {"operation": "status", "args": ""}
        if any(w in message.lower() for w in ["git log", "commit history", "historial de cambios"]):
            return {"operation": "log", "args": "--oneline -10"}
        return {"operation": "status", "args": ""}

    if tool_name == "plan_task":
        if any(w in message.lower() for w in ["create plan", "create task", "new plan", "nuevo plan", "crea plan", "organize"]):
            m = re.search(r"(?:create|new|nuevo|crea|organize)\s+(?:plan|task|tarea)\s+(.+)", message, re.IGNORECASE)
            goal = m.group(1).strip() if m else message
            return {"action": "create", "goal": goal}
        if any(w in message.lower() for w in ["add step", "add task", "next step", "siguiente paso", "agrega paso"]):
            m = re.search(r"(?:add|next|siguiente|agrega)\s+(?:step|paso|task|tarea)\s+(.+)", message, re.IGNORECASE)
            step = m.group(1).strip() if m else "New step"
            return {"action": "add_step", "step": step, "goal": ""}
        if any(w in message.lower() for w in ["complete step", "done step", "finish step", "paso completado", "marca paso"]):
            m = re.search(r"(\d+)", message)
            num = int(m.group(1)) if m else 1
            return {"action": "complete_step", "step_num": num, "goal": ""}
        if any(w in message.lower() for w in ["list plans", "show plans", "my plans", "mis planes", "ver planes"]):
            return {"action": "list", "goal": ""}
        return {"action": "list", "goal": ""}

    if tool_name == "timestamp":
        return {}

    if tool_name == "ocr_image":
        m = re.search(r"(?:ocr|read text|lee texto|extract text|extraer texto|scan)\s+(?:from\s+)?(\S+\.(?:png|jpg|jpeg|gif|bmp|webp|tiff))", message, re.IGNORECASE)
        if m:
            return {"image_path": m.group(1)}
        m = re.search(r"(?:text in|texto en|que dice|what does)\s+(\S+\.(?:png|jpg|jpeg|gif|bmp|webp))", message, re.IGNORECASE)
        if m:
            return {"image_path": m.group(1)}
        return {"image_path": "", "lang": "spa+eng"}

    if tool_name == "read_pdf":
        m = re.search(r"(?:read|open|lee|abre|extract|extraer|parse)\s+(?:from\s+)?(\S+\.pdf)", message, re.IGNORECASE)
        if m:
            return {"pdf_path": m.group(1)}
        m = re.search(r"(\S+\.pdf)", message, re.IGNORECASE)
        if m:
            return {"pdf_path": m.group(1)}
        return {"pdf_path": ""}

    if tool_name == "read_document":
        m = re.search(r"(?:read|open|lee|abre|show|muestra|cat|type)\s+(\S+\.(?:txt|md|csv|json|py|js|ts|html|css|xml|yaml|yml|toml|cfg|ini|conf|log))", message, re.IGNORECASE)
        if m:
            return {"path": m.group(1)}
        m = re.search(r"(\S+\.(?:txt|md|csv|json|py|js|ts|html|css|xml|yaml|yml|toml))", message, re.IGNORECASE)
        if m:
            return {"path": m.group(1)}
        return {"path": ""}

    if tool_name == "analyze_document":
        m = re.search(r"(?:analyze|analiza|inspect|review|revisa)\s+(?:the\s+)?(?:file|archivo|document|documento|image|imagen|pdf)?\s*(\S+)", message, re.IGNORECASE)
        if m:
            return {"file_path": m.group(1), "instruction": message}
        m = re.search(r"(\S+\.(?:png|jpg|jpeg|pdf|txt|md|csv|json|py|js|ts|html))", message, re.IGNORECASE)
        if m:
            return {"file_path": m.group(1), "instruction": message}
        return {"file_path": "", "instruction": message}

    if tool_name == "store_memory":
        m = re.search(r"(?:remember|recuerda|store|guarda|memorize)\s+(?:that|que|esto|this)?\s*(.+)", message, re.IGNORECASE)
        if m:
            content = m.group(1).strip()
            parts = content.split("=", 1) if "=" in content else content.split(":", 1)
            if len(parts) == 2:
                return {"key": parts[0].strip(), "value": parts[1].strip()}
            words = content.split()
            key = words[0] if words else "note"
            return {"key": key, "value": content}
        return {"key": "note", "value": message}

    if tool_name == "recall_memory":
        m = re.search(r"(?:remember|recall|recuerda|que|what)\b.*\b(did|was|is|about|regarding)\b.*\b(i|we|you)\b.*\b(say|said|talk|discuss|mean|mention)\b\s*(.+)?", message, re.IGNORECASE)
        if m and m.group(2):
            return {"key": m.group(2).strip()}
        m = re.search(r"(?:recall|lookup|check|consulta)\s+(?:memory|memoria|key|clave)\s+(\S+)", message, re.IGNORECASE)
        if m:
            return {"key": m.group(1)}
        return {"key": message}

    if tool_name == "conversation_summary":
        return {}

    if tool_name == "send_notification":
        m = re.search(r"(?:send|manda|envia|push|trigger)\s+(?:a\s+)?notification\s*(?:about|de|que|saying|:)?\s*(.+)", message, re.IGNORECASE)
        if m:
            return {"title": "ZIO Notification", "body": m.group(1).strip()}
        m = re.search(r"(?:notify|notifica|avisa|alert)\s+(?:me|user|usuario)\s+(?:about|de|que|saying|:)?\s*(.+)", message, re.IGNORECASE)
        if m:
            return {"title": "ZIO Alert", "body": m.group(1).strip()}
        return {"title": "ZIO Alert", "body": message}

    if tool_name == "create_reminder":
        m = re.search(r"(?:remind|recuerda|avísame|avisame)\s+(?:me|a mi)\s+(?:in|en|at|para)\s+(\d+)\s*(min(?:ute)?s?|minuto?s?|hour?s?|hora?s?|seg(?:ond)?s?|second?s?)", message, re.IGNORECASE)
        if m:
            num = int(m.group(1))
            unit = m.group(2).lower()
            if "hour" in unit or "hora" in unit:
                num *= 60
            elif "seg" in unit or "second" in unit:
                num = max(1, num // 60)
            rest = re.sub(r".*(?:in|en|at|para)\s+\d+\s*\w+\s*", "", message, flags=re.IGNORECASE).strip()
            return {"message": rest or "Reminder from ZIO", "minutes": num}
        m = re.search(r"\d+\s*(min|minute|minuto)", message, re.IGNORECASE)
        if m:
            num = int(re.search(r"\d+", m.group(0)).group())
            return {"message": message, "minutes": num}
        return {"message": message, "minutes": 5}

    if tool_name == "set_alarm":
        m = re.search(r"(\d{1,2}[:\.]\d{2}\s*(?:am|pm|a\.?m\.?|p\.?m\.?)?)", message, re.IGNORECASE)
        if m:
            return {"time_str": m.group(1), "label": f"Alarm at {m.group(1)}"}
        m = re.search(r"(?:in|en)\s+(\d+)\s*(min|minute|minuto|hour|hora)", message, re.IGNORECASE)
        if m:
            return {"time_str": f"in {m.group(1)} {m.group(2)}", "label": f"Alarm in {m.group(1)} {m.group(2)}"}
        return {"time_str": time_str_or_now(), "label": "ZIO Alarm"}

    return {}


# ─── ZICoreAgent ──────────────────────────────────────────────────────────────

class ZICoreAgent:
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.history: list = []

        # Import and create AgentSession with tools
        from agent.state import AgentSession
        self.session = AgentSession(session_id)

    def _ollama_chat(self, message: str, model: str = None,
                     system_override: str = None, tool_context: str = "",
                     sensor_data: dict = None) -> str:
        base_url, default_model = _get_ollama_config()
        if model is None:
            model = default_model

        # ── Model-load gate: verify model is loaded before inference ──
        if not _check_model_loaded(base_url, model):
            logger.warning(f"Model '{model}' not loaded at {base_url}, attempting pull...")
            pull_ok = _pull_model(base_url, model)
            if not pull_ok:
                return f"[ZIO Error] Model '{model}' is not available on {base_url}. Use ollama list to check loaded models."

        system_msg = system_override or SYSTEM_PROMPT
        ctx = _build_context_prompt(sensor_data)
        if ctx:
            system_msg = ctx + "\n" + system_msg
        if tool_context:
            system_msg += f"\n\n--- TOOL RESULTS ---\n{tool_context}\n--- END TOOLS ---\nUse these results to answer the user's question accurately."

        messages = [{"role": "system", "content": system_msg}]
        # Add recent history for context
        for h in self.history[-6:]:
            messages.append(h)
        messages.append({"role": "user", "content": message})

        # Read parameters from config
        try:
            _cfg = _load_config()
            _zio = _cfg.get("zio_engine", {})
            _temperature = _zio.get("temperature", 0.7)
            _top_p = _zio.get("top_p", 0.9)
            _max_tokens = _zio.get("max_tokens", 2048)
            _repeat_penalty = _zio.get("repeat_penalty", 1.1)
        except Exception:
            _temperature, _top_p, _max_tokens, _repeat_penalty = 0.7, 0.9, 2048, 1.1

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,
                "options": {
                "temperature": _temperature,
                "top_p": _top_p,
                "num_predict": _max_tokens,
                "repeat_penalty": _repeat_penalty,
                "num_ctx": 16384,
            },
        }

        use_tools = model in TOOL_CAPABLE_MODELS or any(model.startswith(m) for m in ["qwen2.5-coder:", "llama3.", "deepseek-r1:", "qwen3.5:"])
        if use_tools:
            payload["tools"] = ZIO_NATIVE_TOOLS

        stream_cb = getattr(self, "_stream_callback", None)
        streaming = bool(stream_cb) and not use_tools
        if streaming:
            payload["stream"] = True

        req = urllib.request.Request(
            f"{base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "ZICORE/5.0",
            },
            method="POST",
        )
        try:
            if streaming:
                collected = []
                with urllib.request.urlopen(req, timeout=120) as resp:
                    for raw_line in resp:
                        line = raw_line.decode("utf-8", errors="replace").strip()
                        if not line.startswith("{"):
                            continue
                        try:
                            obj = json.loads(line)
                        except Exception:
                            continue
                        frag = obj.get("message", {}).get("content") or ""
                        if frag:
                            collected.append(frag)
                            stream_cb(frag)
                        if obj.get("done"):
                            break
                return "".join(collected)
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    result = json.loads(resp.read())
            except urllib.error.HTTPError as _he:
                if use_tools and _he.code == 400:
                    payload.pop("tools", None)
                    req = urllib.request.Request(
                        f"{base_url}/api/chat",
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json", "User-Agent": "ZICORE/5.0"},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        result = json.loads(resp.read())
                else:
                    raise
            msg = result.get("message", {})
            # ── Recursive tool-call loop: keep calling LLM with tool results
            #    until the model stops requesting tools or max iterations hit ──
            _max_tool_rounds = 5
            _round = 0
            while use_tools and msg.get("tool_calls") and _round < _max_tool_rounds:
                _round += 1
                tool_context_parts = []
                for tc in msg["tool_calls"]:
                    fn = tc.get("function", {})
                    fname = fn.get("name", "")
                    fargs = fn.get("arguments", {})
                    logger.info(f"Recursive tool call round {_round}: {fname}({fargs})")
                    try:
                        if self.session.tools.exists(fname):
                            tool_result = self.session.tools.call(fname, **fargs)
                            tool_context_parts.append(f"[{fname}] {json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)}")
                        else:
                            tool_context_parts.append(f"[{fname}] Error: tool not found")
                    except Exception as e:
                        tool_context_parts.append(f"[{fname}] Error: {e}")
                if not tool_context_parts:
                    break
                tool_ctx = "\n".join(tool_context_parts)
                messages.append({"role": "assistant", "content": msg.get("content", ""), "tool_calls": msg.get("tool_calls")})
                messages.append({"role": "tool", "content": tool_ctx})
                followup_payload = json.dumps({
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": _temperature, "top_p": _top_p, "num_predict": _max_tokens, "repeat_penalty": _repeat_penalty},
                }).encode("utf-8")
                req2 = urllib.request.Request(
                    f"{base_url}/api/chat",
                    data=followup_payload,
                    headers={"Content-Type": "application/json", "User-Agent": "ZICORE/5.0"},
                    method="POST",
                )
                with urllib.request.urlopen(req2, timeout=300) as resp2:
                    result2 = json.loads(resp2.read())
                    msg = result2.get("message", {})
                    if not msg.get("tool_calls"):
                        return msg.get("content", "")
            return msg.get("content", "")
        except Exception as e:
            return f"[ZIO Error] {e}"

    def _detect_intent(self, message: str) -> str:
        msg = message.lower()
        if any(w in msg for w in ["generate image", "generate an image", "draw an image", "create an image", "picture of",
                                    "genera imagen", "crea imagen", "dibuja",
                                    "genera un logo", "create a logo", "draw a logo", "diseña un logo",
                                    "genera un icono", "create an icon", "design a logo",
                                    "logo for", "logo para", "icon for", "icon para"]):
            return "generate_image"
        if any(w in msg for w in ["generate 3d", "generate a 3d", "make a 3d", "create a 3d", "mesh of", "stl file",
                                   "genera 3d", "crea modelo 3d"]):
            return "generate_3d"
        if any(w in msg for w in ["run code", "execute code", "run python", "execute python", "run script"]):
            return "code"
        if any(w in msg for w in ["write code", "create function", "write function", "generate code", "code for",
                                   "write a script", "create a script", "write a program",
                                   "escribe código", "crea función"]):
            return "code_write"
        if any(w in msg for w in ["debug", "find bug", "fix code", "error in", "what's wrong with this code", "review code"]):
            return "code_debug"
        if any(w in msg for w in ["explain code", "what does this code do", "how does this work", "describe this function"]):
            return "code_explain"
        # "sim" is a whole word only — bare substring catches "simple",
        # "asimismo", etc. and hijacks normal chat into the simulation engine.
        if any(w in msg for w in ["simulate", "simulation", "run simulation"]) or re.search(r'\bsim\b', msg):
            return "simulate"
        if any(w in msg for w in ["capture webcam", "take photo", "take picture", "camera capture", "snap photo",
                                    "captura foto", "toma foto", "sacar foto"]):
            return "capture_webcam"
        if any(w in msg for w in ["analyze image", "analyze photo", "what do you see", "detect objects",
                                    "scan image", "inspect image",
                                    "analiza imagen", "que ves", "detecta objetos"]):
            return "analyze_image"
        if any(w in msg for w in ["vibrate", "vibration", "shake", "buzz", "haptic",
                                    "vibra", "vibracion", "sacude"]):
            return "device_vibrate"
        if any(w in msg for w in ["flashlight", "torch", "led", "linterna", "foco",
                                    "turn on light", "encender luz", "apagar luz"]):
            return "device_flashlight"
        # Brightness must be an explicit request to change it. The bare words
        # are too common in normal speech ("dime" contains "dim", "brillo"
        # means both "brightness" and "shine"), so require a change verb +
        # a brightness word, matched as whole words (NOT substrings).
        if (re.search(r'\b(brightness|brillo|brillante|dim|oscurecer|aclarar|encender|bajar|luz)\b', msg) and
                re.search(r'\b(adjust|change|set|increase|decrease|lower|raise|subir|bajar|ajustar|cambiar|mas|menos|al)\b', msg)):
            return "device_brightness"
        if any(w in msg for w in ["clipboard", "copy", "copiar", "pegar", "paste"]):
            return "device_clipboard"
        if any(w in msg for w in ["notify", "notification", "notificacion", "alerta", "aviso"]):
            return "device_notify"
        if any(w in msg for w in ["open camera", "turn on camera", "start camera", "abre camara", "enciende camara",
                                    "take photo", "take picture", "capture photo", "sacar foto", "tomar foto",
                                    "open cam", "turn on cam"]):
            return "camera_open"
        if any(w in msg for w in ["what do you see", "que ves", "que hay aqui", "describe", "look at this",
                                    "scan", "analyze what", "what is this", "que es esto",
                                    "look around", "que hay por ahi"]):
            return "camera_analyze"
        if any(w in msg for w in ["generate sound", "generate audio", "make a sound", "create a sound", "play sound", "sfx"]):
            return "generate_sound"
        if re.search(r'\b(generat\w*|mak\w*|creat\w*|play)\b.*\b(sound|audio|sfx|ruido|sonido)\b', msg):
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

        # ── Coding/DevOps intents (before file-based docs to avoid .py/.js conflicts) ──
        if re.search(r'\b(read|open|cat|type|lee|abre)\s+(file\s+)?\S+\.(py|js|ts|jsx|tsx|c|cpp|h|rs|go|java|rb|php|sh)\b', msg):
            return "read_document"
        if any(w in msg for w in ["edit file", "modify file", "change file", "replace in", "fix file",
                                    "edit code", "modify code", "change code", "update code",
                                    "edita archivo", "edita el archivo", "edita un archivo",
                                    "modifica archivo", "modifica el archivo", "cambia archivo",
                                    "cambia el archivo", "actualiza archivo", "actualiza el archivo",
                                    "corrige archivo", "corrige el archivo"]):
            return "edit_file"
        if any(w in msg for w in ["search code", "find function", "grep", "search for", "find class",
                                    "where is", "where's defined", "busca funcion", "encuentra funcion",
                                    "busca codigo", "buscar codigo", "busca en los archivos",
                                    "donde esta", "donde está", "donde se define"]):
            return "grep_code"
        if any(w in msg for w in ["find files", "list files matching", "glob", "all files with",
                                    "find all *.py", "find all *.js", "encuentra archivos",
                                    "list *.py", "show *.html", "find all .py", "find all .js",
                                    "list all .py", "show all .py", "list all .js", "show all .js",
                                    "todos los archivos", "archivos con", "lista archivos",
                                    "listar archivos", "encuentra los archivos"]):
            return "glob_files"

        # ── File-based document intents (must come before camera) ──
        if re.search(r'\.(pdf)\b', msg):
            if any(w in msg for w in ["read", "open", "lee", "abre", "extract", "extraer", "parse", "summary", "resumen", "content", "contenido"]):
                return "read_pdf"
            if any(w in msg for w in ["analyze", "analiza", "inspect", "review", "revisa"]):
                return "analyze_document"
            return "read_pdf"
        if re.search(r'\.(png|jpg|jpeg|gif|bmp|webp|tiff|tif)\b', msg):
            if any(w in msg for w in ["ocr", "read text", "lee texto", "extract text", "extraer texto"]):
                return "ocr_image"
            if any(w in msg for w in ["analyze", "analiza", "inspect", "review", "revisa"]):
                return "analyze_document"
            return "analyze_document"
        if re.search(r'\.(txt|md|csv|json|html|css|xml|yaml|yml|toml|cfg|ini|conf|log)\b', msg):
            if any(w in msg for w in ["read", "open", "lee", "abre", "show", "muestra", "cat", "type"]):
                return "read_document"
            if any(w in msg for w in ["analyze", "analiza", "inspect", "review", "revisa"]):
                return "analyze_document"
            return "read_document"

        # ── Camera-specific intents ──
        if any(w in msg for w in ["close camera", "cierra camara", "apaga camara", "stop camera", "turn off camera"]):
            return "camera_close"
        if any(w in msg for w in ["switch camera", "cambia camara", "front camera", "back camera", "camara frontal", "camara trasera",
                                    "voltea camara", "switch to front", "switch to back"]):
            return "camera_switch"
        if any(w in msg for w in ["read text", "lee texto", "ocr", "scan document", "escanea documento",
                                    "read this", "lee esto", "what does this say", "que dice esto"]):
            return "camera_ocr"
        if any(w in msg for w in ["detect objects", "detecta objetos", "detect person", "detecta persona",
                                    "what objects", "que objetos", "identify", "identifica", "find objects"]):
            return "camera_detect"
        if any(w in msg for w in ["what color", "que color", "colors", "colores", "color of", "color de"]):
            return "camera_color"
        if any(w in msg for w in ["describe what you see", "describe this", "describe aqui", "what is in front",
                                    "que hay enfrente", "what's around", "que hay alrededor"]):
            return "camera_describe"

        # ── Alexa-style intents ──
        if any(w in msg for w in ["set alarm", "pon alarma", "create alarm", "alarma para", "alarm for",
                                    "temporizador", "timer for", "timer para", "countdown", "cuenta regresiva"]):
            return "alarm"
        if any(w in msg for w in ["reminder", "recuerda", "avísame", "avisame", "no olvides", "recordatorio"]):
            return "reminder"
        if any(w in msg for w in ["weather", "clima", "temperatura", "temperature", "afuera", "outside",
                                    "como esta el clima", "que tiempo hace"]):
            return "weather"
        if any(w in msg for w in ["play music", "reproduce musica", "pon musica", "escuchar", "listen to",
                                    "play song", "play album", "stop music", "pausa musica"]):
            return "music"

        # ── Web fetch intent ──
        if re.search(r'\b(open|fetch|read|get|scrape|load|access|abre|carga|lee|obten|accede)\s+(https?://\S+)', msg):
            return "web_fetch"
        if re.search(r'\b(what(\'s| is| are))\s+(on|in|at)\s+(https?://\S+)', msg):
            return "web_fetch"
        if re.search(r'\b(que hay|que tiene|ver contenido|show content)\s+(en |on |de )?(https?://\S+)', msg):
            return "web_fetch"

        # ── Git/Plan intents ──
        if any(w in msg for w in ["git status", "git diff", "git log", "git commit", "git branch",
                                    "commit changes", "save to git", "repository",
                                    "commit", "ramas", "branches", "push changes", "guarda cambios"]):
            return "git_operation"
        if any(w in msg for w in ["plan task", "create plan", "break down", "task list", "todo list",
                                    "organize steps", "plan steps", "desglosa", "organiza pasos",
                                    "create a plan", "new plan", "checklist"]):
            return "plan_task"

        return "chat"

    def _build_tool_summary(self, tool_results: List[Dict]) -> str:
        """Build a human-readable summary of tool results for Ollama."""
        if not tool_results:
            return ""
        lines = []
        for tr in tool_results:
            tool = tr["tool"]
            result = tr["result"]
            if isinstance(result, dict):
                # Format nicely
                if "content" in result:
                    lines.append(f"[{tool}] File {result.get('path', '?')}:\n{result['content'][:2000]}")
                elif "entries" in result:
                    entries = result["entries"]
                    names = [e["name"] for e in entries[:20]]
                    lines.append(f"[{tool}] {result.get('path', '.')}: {', '.join(names)}")
                elif "result" in result:
                    lines.append(f"[{tool}] {result.get('expression', '?')} = {result['result']}")
                elif "file" in result:
                    lines.append(f"[{tool}] Generated: {result['file']}")
                elif "error" in result:
                    lines.append(f"[{tool}] Error: {result['error']}")
                elif "stdout" in result:
                    out = result["stdout"][:500]
                    lines.append(f"[{tool}] Command output:\n{out}")
                elif "results" in result:
                    for r in result["results"][:3]:
                        lines.append(f"[{tool}] {r.get('title', '')}: {r.get('text', '')[:200]}")
                else:
                    lines.append(f"[{tool}] {json.dumps(result)[:300]}")
            else:
                lines.append(f"[{tool}] {str(result)[:300]}")
        return "\n".join(lines)

    async def process(self, message: str, context: Optional[Dict] = None,
                      stream_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        self._stream_callback = stream_callback
        intent = self._detect_intent(message)
        msg = message.lower()
        context = context or {}
        sensor_data = context.get("sensor_data", None)

        # ── Non-LLM intents (no Ollama needed) ──────────────────────────
        if intent == "status":
            active = _get_active_project()
            proj = f" | Active project: {active}" if active else ""
            # Also get system status via tool
            try:
                status_result = self.session.tools.call("status")
                status_str = json.dumps(status_result)
            except Exception:
                status_str = "tools unavailable"
            return {
                "intent": "status",
                "outputs": {
                    "text": f"All ZICORE systems operational. ZIO agent active.{proj}\nTools: {status_str}",
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

        # ── Vision intents (OpenVision analysis) ────────────────────────
        if intent == "capture_webcam":
            try:
                from zicore.openvision import openvision as ov
                result = ov.capture_webcam(device_index=0)
                if "error" in result:
                    text = f"[CAMERA ERROR] {result['error']}"
                else:
                    labels = ", ".join(result.get("labels", []))
                    objects = len(result.get("objects", []))
                    text = (
                        f"[CAMERA CAPTURE]\n"
                        f"Resolution: {result.get('frame_size', '?')}\n"
                        f"Analysis: {labels}\n"
                        f"Regions detected: {objects}\n"
                        f"Saved: {result.get('capture_path', '?')}"
                    )
                self.history.append({"role": "user", "content": message})
                self.history.append({"role": "assistant", "content": text})
                return {"intent": intent, "outputs": {"text": text, "vision": result}}
            except Exception as e:
                return {"intent": intent, "outputs": {"text": f"[CAMERA ERROR] {e}"}}

        if intent == "analyze_image":
            try:
                from zicore.openvision import openvision as ov
                image_path = ""
                for w in message.split():
                    if "." in w and any(w.lower().endswith(e) for e in [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"]):
                        image_path = w
                        break
                if not image_path:
                    captures = sorted((Path(VISION_DIR) / "captures").glob("*.jpg"), reverse=True) if (Path(VISION_DIR) / "captures").exists() else []
                    if captures:
                        image_path = str(captures[0])
                    else:
                        return {"intent": intent, "outputs": {"text": "[VISION] No image to analyze. Capture one first with 'capture webcam'."}}
                result = ov.analyze_media(image_path)
                if "error" in result:
                    text = f"[VISION ERROR] {result['error']}"
                else:
                    labels = ", ".join(result.get("labels", []))
                    objects = result.get("objects", [])
                    text = (
                        f"[VISION ANALYSIS] {result.get('analysis_type', 'image')}\n"
                        f"File: {result.get('input_path', '?')}\n"
                        f"Labels: {labels}\n"
                        f"Confidence: {result.get('confidence', 0):.0%}\n"
                        f"Regions: {len(objects)}\n"
                    )
                    for obj in objects[:4]:
                        text += f"  - {obj.get('region', '?')}: {obj.get('color_dominant', '?')} (brightness {obj.get('brightness', 0):.0f})\n"
                self.history.append({"role": "user", "content": message})
                self.history.append({"role": "assistant", "content": text})
                return {"intent": intent, "outputs": {"text": text, "vision": result}}
            except Exception as e:
                return {"intent": intent, "outputs": {"text": f"[VISION ERROR] {e}"}}

        # ── Device control (returns command tags for mobile app) ────────
        if intent == "device_vibrate":
            cmd_tag = "[VIBRATE]"
            if any(w in msg for w in ["pattern", "patron", "multiple"]):
                cmd_tag = "[VIBRATE_PATTERN:200,100,200,100,200]"
            text = f"Vibrating your device now. {cmd_tag}"
            return {"intent": intent, "outputs": {"text": text, "device_command": cmd_tag}}

        if intent == "device_flashlight":
            cmd_tag = "[BRIGHTNESS:100]"
            if any(w in msg for w in ["off", "apagar", "turn off"]):
                cmd_tag = "[BRIGHTNESS:30]"
                text = "Turning flashlight off. Setting brightness to 30%."
            else:
                text = "Turning flashlight on! Setting max brightness. [BRIGHTNESS:100]"
            return {"intent": intent, "outputs": {"text": text, "device_command": cmd_tag}}

        if intent == "device_brightness":
            import re as _re
            m = _re.search(r'(\d{1,3})\s*%?', msg)
            level = int(m.group(1)) if m else 50
            level = max(0, min(100, level))
            text = f"Setting brightness to {level}%. [BRIGHTNESS:{level}]"
            return {"intent": intent, "outputs": {"text": text, "device_command": f"[BRIGHTNESS:{level}]" }}

        if intent == "device_clipboard":
            import re as _re
            m = _re.search(r'(?:copy|copiar)\s+(.+)', msg)
            content = m.group(1) if m else "ZICORE"
            text = f"Copied to clipboard: {content}. [CLIPBOARD:{content}]"
            return {"intent": intent, "outputs": {"text": text, "device_command": f"[CLIPBOARD:{content}]"}}

        if intent == "device_notify":
            import re as _re
            m = _re.search(r'(?:notify|notificar|aviso|alerta)\s+(.+)', msg)
            msg_text = m.group(1) if m else "ZIO Notification"
            text = f"Sending notification: {msg_text}. [NOTIFY:{msg_text}] [NOTIFICATION]"
            return {"intent": intent, "outputs": {"text": text, "device_command": f"[NOTIFICATION]" }}

        # ── Camera control (returns camera command tags) ────────────────
        if intent == "camera_open":
            text = "Opening your camera now. I'll analyze what I see. [CAMERA_CAPTURE]"
            return {"intent": intent, "outputs": {"text": text, "device_command": "[CAMERA_CAPTURE]"}}

        if intent == "camera_analyze":
            text = "Let me capture and analyze what's in front of you. [CAMERA_CAPTURE] [VISION_ANALYZE]"
            return {"intent": intent, "outputs": {"text": text, "device_command": "[CAMERA_CAPTURE] [VISION_ANALYZE]"}}

        if intent == "camera_close":
            text = "Camera closed. [CAMERA_CLOSE]"
            return {"intent": intent, "outputs": {"text": text, "device_command": "[CAMERA_CLOSE]"}}

        if intent == "camera_switch":
            cmd = "[CAMERA_FRONT]" if any(w in msg for w in ["front", "frontal", "delantera", "selfie"]) else "[CAMERA_BACK]"
            text = f"Switching camera. {cmd}"
            return {"intent": intent, "outputs": {"text": text, "device_command": cmd}}

        if intent == "camera_ocr":
            text = "Scanning for text... [CAMERA_CAPTURE] [VISION_ANALYZE:ocr]"
            return {"intent": intent, "outputs": {"text": text, "device_command": "[CAMERA_CAPTURE] [VISION_ANALYZE:ocr]"}}

        if intent == "camera_detect":
            text = "Detecting objects... [CAMERA_CAPTURE] [VISION_ANALYZE:detect]"
            return {"intent": intent, "outputs": {"text": text, "device_command": "[CAMERA_CAPTURE] [VISION_ANALYZE:detect]"}}

        if intent == "camera_color":
            text = "Analyzing colors... [CAMERA_CAPTURE] [VISION_ANALYZE:color]"
            return {"intent": intent, "outputs": {"text": text, "device_command": "[CAMERA_CAPTURE] [VISION_ANALYZE:color]"}}

        if intent == "camera_describe":
            text = "Describing what I see... [CAMERA_CAPTURE] [VISION_ANALYZE:describe]"
            return {"intent": intent, "outputs": {"text": text, "device_command": "[CAMERA_CAPTURE] [VISION_ANALYZE:describe]"}}

        # ── Alexa-style handlers ──
        if intent == "alarm":
            import re as _re
            m = _re.search(r'(\d+)\s*(min|minutes?|hora|hours?|seg|seconds?)', msg)
            if m:
                val = int(m.group(1))
                unit = m.group(2)
                if 'min' in unit:
                    secs = val * 60
                    time_str = f"{val} minutes"
                elif 'hora' in unit or 'hour' in unit:
                    secs = val * 3600
                    time_str = f"{val} hours"
                else:
                    secs = val
                    time_str = f"{val} seconds"
                text = f"Alarm set for {time_str}. I'll notify you when it's time. [ALERT:Alarm in {time_str}]"
                return {"intent": intent, "outputs": {"text": text, "device_command": f"[ALERT:Alarm in {time_str}]"}}
            text = "When should I set the alarm? Say something like 'alarm for 5 minutes'."
            return {"intent": intent, "outputs": {"text": text}}

        if intent == "reminder":
            import re as _re
            m = _re.search(r'(?:remind|recuerda|avísame|avisame|no olvides)\s+(?:me\s+)?(?:to\s+|que\s+|de\s+)?(.+?)(?:\s+(?:at|en|for|para)\s+(.+))?$', msg)
            task = m.group(1).strip() if m else "something"
            when = m.group(2).strip() if m and m.group(2) else "soon"
            text = f"Reminder set: '{task}' {when}. [ALERT:Reminder: {task}]"
            return {"intent": intent, "outputs": {"text": text, "device_command": f"[ALERT:Reminder: {task}]"}}

        if intent == "weather":
            city = "auto"
            import re as _re
            import urllib.parse as _up
            cm = _re.search(r'(?:in|en|para|for|of|de|at)\s+([a-zA-Z\s]+?)(?:\s*\?|\s*$|\s+and|\s+y|\s+but|\s+pero)', message)
            if cm:
                city = cm.group(1).strip()
            try:
                import urllib.request, json
                wttr_url = f"https://wttr.in/{_up.quote(city)}?format=j1"
                req = urllib.request.Request(wttr_url, headers={'User-Agent': 'ZICORE/5.0 Weather'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                    cur = data.get('current_condition', [{}])[0]
                    area = data.get('nearest_area', [{}])[0]
                    loc = area.get('areaName', [{}])[0].get('value', city)
                    country = area.get('country', [{}])[0].get('value', '')
                    temp_c = cur.get('temp_C', '?')
                    temp_f = cur.get('temp_F', '?')
                    feels = cur.get('FeelsLikeC', '?')
                    desc = cur.get('weatherDesc', [{}])[0].get('value', 'Unknown')
                    humidity = cur.get('humidity', '?')
                    wind_kph = cur.get('windspeedKmph', '?')
                    wind_dir = cur.get('winddir16Point', '')
                    uv = cur.get('uvIndex', '?')
                    visibility = cur.get('visibility', '?')
                    text = (f"Weather for {loc}, {country}: {desc}, "
                            f"Temperature: {temp_c}°C ({temp_f}°F), Feels like: {feels}°C, "
                            f"Humidity: {humidity}%, Wind: {wind_kph} km/h {wind_dir}, "
                            f"UV Index: {uv}, Visibility: {visibility} km")
            except Exception as e:
                text = f"Could not fetch weather: {str(e)}. Please check your connection."
            return {"intent": intent, "outputs": {"text": text}}

        if intent == "web_fetch":
            import re as _re
            import urllib.parse as _up
            url_match = _re.search(r'(https?://\S+)', message)
            if not url_match:
                return {"intent": intent, "outputs": {"text": "No URL found in your message. Please provide a URL to fetch."}}
            url = url_match.group(1)
            try:
                from agent.state import AgentSession
                tmp_session = AgentSession("web_fetch")
                result = tmp_session.tools.call("web_fetch", url=url)
                if "error" in result:
                    text = f"Error fetching URL: {result['error']}"
                else:
                    content = result.get("text", "")
                    title = result.get("title", "")
                    text = f"**{title}**\n\n{content}" if title else content
            except Exception as e:
                text = f"Could not fetch URL: {str(e)}"
            return {"intent": intent, "outputs": {"text": text}}

        if intent == "music":
            if any(w in msg for w in ["stop", "pausa", "pause", "para"]):
                text = "Stopping music. [MEDIA_STOP]"
                return {"intent": intent, "outputs": {"text": text, "device_command": "[MEDIA_STOP]"}}
            import re as _re
            m = _re.search(r'(?:play|reproduce|pon|escuchar|listen to)\s+(.+)', msg)
            query = m.group(1).strip() if m else "music"
            text = f"Playing: {query}. [MEDIA_PLAY:{query}]"
            return {"intent": intent, "outputs": {"text": text, "device_command": f"[MEDIA_PLAY:{query}]"}}

        # ── Coding/DevOps intents (tools + Ollama) ────────────────────
        if intent in ("edit_file", "grep_code", "glob_files", "git_operation", "plan_task"):
            tool_results = _resolve_tools(message, self.session)
            tool_ctx = self._build_tool_summary(tool_results)
            tool_names = [tr["tool"] for tr in tool_results]
            tool_errors = [tr["result"].get("error", "") for tr in tool_results if isinstance(tr.get("result"), dict) and tr["result"].get("error")]
            if tool_errors:
                text = f"Tool errors: {'; '.join(tool_errors)}"
            elif tool_ctx:
                text = tool_ctx
            else:
                text = f"No tool matched for {intent}. Try a more specific command."
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": text})
            return {"intent": intent, "outputs": {"text": text, "zio_msg": text, "tools_used": tool_names}}

        # ── Document intents (tools) ────────────────────
        if intent in ("ocr_image", "read_pdf", "read_document", "analyze_document"):
            tool_results = _resolve_tools(message, self.session)
            tool_ctx = self._build_tool_summary(tool_results)
            tool_names = [tr["tool"] for tr in tool_results]
            tool_errors = [tr["result"].get("error", "") for tr in tool_results if isinstance(tr.get("result"), dict) and tr["result"].get("error")]
            if tool_errors:
                text = f"Document error: {'; '.join(tool_errors)}"
            elif tool_ctx:
                text = tool_ctx
            else:
                text = f"Could not process document. Try: 'read the file /path/to/file.pdf' or 'OCR this image /path/to/image.png'"
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": text})
            return {"intent": intent, "outputs": {"text": text, "zio_msg": text, "tools_used": tool_names}}

        # ── Generation intents (use generator + tool) ────────────────────
        if intent in ("generate_image", "generate_3d", "generate_sound", "video"):
            try:
                from agent.generator import generator as gen
                active = _get_active_project()
                output_dir = str(PROJECTS_DIR / active / "generations") if active else None
                if intent == "generate_image":
                    result = gen.generate_image(message, output_dir=output_dir)
                elif intent == "generate_3d":
                    result = gen.generate_3d(message, output_dir=output_dir)
                elif intent == "generate_sound":
                    result = gen.generate_sound(message, output_dir=output_dir)
                elif intent == "video":
                    result = gen.generate_video(message, output_dir=output_dir)
                # Normalize: use media_url/media_type from generator if available
                file_path = result.get("file") or result.get("path") or ""
                media_url = result.get("media_url", "")
                media_type = result.get("media_type", intent.replace("generate_", ""))
                # Fallback: construct media_url from file path
                if not media_url and file_path:
                    import os as _os
                    fname = _os.path.basename(file_path)
                    if "images" in file_path or "img_" in fname:
                        media_url = f"/media/images/{fname}"
                        media_type = "image"
                    elif "audio" in file_path or "sound_" in fname:
                        media_url = f"/media/audio/{fname}"
                        media_type = "audio"
                    elif "3d" in file_path or "mesh" in fname or ".stl" in fname:
                        media_url = f"/media/3d/{fname}"
                        media_type = "3d"
                    elif "video" in file_path:
                        media_url = f"/media/video/{fname}"
                        media_type = "video"
                    else:
                        media_url = f"/output/{fname}"
                result["file"] = file_path
                result["media_url"] = media_url
                result["media_type"] = media_type
                text = f"[GENERATED:{media_type.upper()}:{media_url or file_path}]"
                return {"intent": intent, "outputs": {"text": text, "generation": result, "media_url": media_url, "media_type": media_type}}
            except Exception as e:
                return {"intent": intent, "outputs": {"text": f"Generation failed: {e}"}}

        # ── Code intents (Ollama with specialized prompt) ────────────────
        if intent == "code_write":
            # Try tools first (read existing files for context)
            tool_results = _resolve_tools(message, self.session)
            tool_ctx = self._build_tool_summary(tool_results)

            reply = self._ollama_chat(
                "You are a coding assistant. Write clean, well-commented code based on this request. "
                "Return ONLY the code inside ```python blocks. No explanation needed.\n\n" + message,
                tool_context=tool_ctx,
                sensor_data=sensor_data,
            )
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": reply})
            return {"intent": intent, "outputs": {"text": reply, "zio_msg": reply}}

        if intent == "code_debug":
            tool_results = _resolve_tools(message, self.session)
            tool_ctx = self._build_tool_summary(tool_results)

            reply = self._ollama_chat(
                "You are a code debugger. Analyze this code, find bugs, and suggest fixes. "
                "Be specific about line numbers and issues.\n\n" + message,
                tool_context=tool_ctx,
                sensor_data=sensor_data,
            )
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": reply})
            return {"intent": intent, "outputs": {"text": reply, "zio_msg": reply}}

        if intent == "code_explain":
            tool_results = _resolve_tools(message, self.session)
            tool_ctx = self._build_tool_summary(tool_results)

            reply = self._ollama_chat(
                "You are a code explainer. Explain what this code does step by step. "
                "Be clear and concise.\n\n" + message,
                tool_context=tool_ctx,
                sensor_data=sensor_data,
            )
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": reply})
            return {"intent": intent, "outputs": {"text": reply, "zio_msg": reply}}

        # ── Simulation ───────────────────────────────────────────────────
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
                    "outputs": {"text": text, "zio_msg": text, "simulation": result},
                }
            except Exception as e:
                error_text = f"[SIMULATION ERROR] Failed to generate simulation: {e}"
                return {"intent": intent, "outputs": {"text": error_text, "zio_msg": error_text}}

        # ── Aerospace design (Ollama with domain knowledge) ──────────────
        if intent == "aerospace_design":
            tool_results = _resolve_tools(message, self.session)
            tool_ctx = self._build_tool_summary(tool_results)

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
            reply = self._ollama_chat(aerospace_system + "\n\n" + message, tool_context=tool_ctx, sensor_data=sensor_data)
            self.history.append({"role": "user", "content": message})
            self.history.append({"role": "assistant", "content": reply})
            return {"intent": intent, "outputs": {"text": reply, "zio_msg": reply}}

        # ── General chat (Ollama with tool context) ──────────────────────
        # Always resolve tools — the agent has full access
        tool_results = _resolve_tools(message, self.session)
        tool_ctx = self._build_tool_summary(tool_results)

        # Get knowledge context from web_server if available
        knowledge_ctx = context.get("knowledge_context", "")

        # Persona hook (CAPCOM extension, etc.)
        system = _persona_prompt(context.get("persona"), knowledge_ctx)

        reply = self._ollama_chat(message, system_override=system, tool_context=tool_ctx, sensor_data=sensor_data)
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": reply})

        tool_names = [tr["tool"] for tr in tool_results] if tool_results else []
        return {
            "intent": intent,
            "outputs": {
                "text": reply,
                "zio_msg": reply,
                "tools_used": tool_names,
            },
        }

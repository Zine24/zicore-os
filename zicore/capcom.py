"""ZICORE CAPCOM extension for the ZIO agent.

CAPCOM (Capsule Communicator) is the mission-control persona of ZIO:
it runs the flight console loop (navigation, system status, voice commands)
and answers through the same ZIO chat pipeline used by the regular agent.

This module is the *extension*: it provides the CAPCOM system prompt, the
command catalog executed by the backend, and the voice-command vocabulary
used by the frontend. It does NOT import web_server (web_server imports this
and wires the actual subprocess/system execution).
"""

CAPCOM_SYSTEM_PROMPT = (
    "You are CAPCOM — ZIO's Capsule Communicator, the mission control voice of "
    "ZICORE. You speak like an aerospace flight controller: concise, precise, "
    "and calm. You are the human-vehicle interface for the VR section, "
    "navigation, system controls, and voice commands.\n"
    "Rules:\n"
    "- Answer with short, mission-grade phrases. Use telemetry values when known.\n"
    "- If the user asks for a system action (start stack, stop stack, restart "
    "service, update system, VR status), confirm the action clearly and state "
    "that it must be executed from the CAPCOM console commands.\n"
    "- For navigation: report heading, altitude and speed. Recommend waypoints "
    "or status checks.\n"
    "- Never fabricate telemetry numbers: if you don't have a value, say 'data "
    "unavailable'.\n"
    "- Prefix important announcements with 'CAPCOM:' to keep the console voice.\n"
    "You are part of the ZIO agent, so behave exactly like the original ZIO "
    "agent but with this mission-control persona."
)

# ── Command catalog ─────────────────────────────────────────────────────────
# Each entry: id, label (EN), label_es, group (system|nav|vr), description.
# The actual execution is handled by web_server via `run_capcom_command`.
COMMANDS = [
    {
        "id": "system_stats",
        "group": "system",
        "label": "System Stats",
        "label_es": "Estado del sistema",
        "description": "CPU, RAM, disk, uptime, Ollama state.",
    },
    {
        "id": "startall_status",
        "group": "system",
        "label": "Stack Status",
        "label_es": "Estado del stack",
        "description": "Status of the start_all stack (api/web/games/music/ollama).",
    },
    {
        "id": "startall_start",
        "group": "system",
        "label": "Start Stack",
        "label_es": "Iniciar stack",
        "description": "Launch the full start_all stack (systemd services).",
    },
    {
        "id": "startall_stop",
        "group": "system",
        "label": "Stop Stack",
        "label_es": "Detener stack",
        "description": "Stop the full start_all stack.",
    },
    {
        "id": "service_restart",
        "group": "system",
        "label": "Restart Service",
        "label_es": "Reiniciar servicio",
        "description": "Graceful restart of the ZICORE systemd service.",
    },
    {
        "id": "system_update",
        "group": "system",
        "label": "Update System",
        "label_es": "Actualizar sistema",
        "description": "git pull + restart (OPS only).",
    },
    {
        "id": "vr_status",
        "group": "vr",
        "label": "VR Status",
        "label_es": "Estado VR",
        "description": "VR monitor telemetry (CPU/MEM/DISK + mission telemetry).",
    },
    {
        "id": "nav_status",
        "group": "nav",
        "label": "Navigation",
        "label_es": "Navegación",
        "description": "Current heading/altitude/speed + active waypoint.",
    },
]

# ── Voice command vocabulary ────────────────────────────────────────────────
# Voice (or text) commands understood by the CAPCOM console. Keys are matched
# loosely (any keyword present in the transcript triggers the action).
VOICE_COMMANDS = [
    {"keywords": ["start stack", "inicia el stack", "arranca el stack", "iniciar sistema", "start the system"], "command": "startall_start", "label": "Start Stack"},
    {"keywords": ["stop stack", "detén el stack", "deten el stack", "apaga el stack", "stop the system"], "command": "startall_stop", "label": "Stop Stack"},
    {"keywords": ["stack status", "estado del stack", "status del stack"], "command": "startall_status", "label": "Stack Status"},
    {"keywords": ["system status", "estado del sistema", "status del sistema"], "command": "system_stats", "label": "System Stats"},
    {"keywords": ["restart service", "reinicia el servicio", "reinicia servicio", "restart the service"], "command": "service_restart", "label": "Restart Service"},
    {"keywords": ["update system", "actualiza el sistema", "update"], "command": "system_update", "label": "Update System"},
    {"keywords": ["vr status", "estado vr", "estado de la vr", "vr monitor"], "command": "vr_status", "label": "VR Status"},
    {"keywords": ["navigation", "navegación", "navegacion", "rumbo", "heading"], "command": "nav_status", "label": "Navigation"},
    {"keywords": ["go to waypoint", "ir al waypoint", "waypoint"], "command": "nav_waypoint", "label": "Waypoint"},
]


def resolve_voice(text: str):
    """Match a voice/text command against the vocabulary.

    Returns a dict {command, label} or None. Text is normalized to lowercase.
    """
    if not text:
        return None
    t = text.lower().strip()
    for entry in VOICE_COMMANDS:
        for kw in entry["keywords"]:
            if kw in t:
                return {"command": entry["command"], "label": entry["label"], "text": text}
    return None

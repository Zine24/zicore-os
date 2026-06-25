from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Optional
import logging
import json

from .piplines.orchestrator import PipelineOrchestrator
from .modules import (ZIHabState, ZiNavState, ZiPowerState, ZiShipState,
                      ZIDroneState, ZIRobotState, ZICommState, ZIEcoState,
                      ZIMedState, ZiCoreXState, ZILinkState, ZIVRState,
                      ZISecState, ZiCRIOGENState, ZiMAURYState, GPDEngine)
from zty.factory import ZTYFactory
from .routers.agent_router import router as agent_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("zicore")

# ── Module instances ────────────────────────────────────────────────────────
modules = {
    "zihab": ZIHabState(),
    "zinav": ZiNavState(),
    "zipower": ZiPowerState(),
    "ziship": ZiShipState(),
    "zidrone": ZIDroneState(),
    "zirobot": ZIRobotState(),
    "zicomm": ZICommState(),
    "zieco": ZIEcoState(),
    "zimed": ZIMedState(),
    "zicorex": ZiCoreXState(),
    "zilink": ZILinkState(),
    "zivr": ZIVRState(),
    "zisec": ZISecState(),
    "zicriogen": ZiCRIOGENState(),
    "zimaury": ZiMAURYState(),
}

orchestrator = PipelineOrchestrator()
gpd = GPDEngine()
zty_factory = ZTYFactory()

MODULE_DESCRIPTIONS = {
    "zinav": "Sistema de navegacion principal - SOFTWARE que planifica trayectorias",
    "zihab": "Sistema de control de habitat",
    "zipower": "Sistema de gestion energetica",
    "ziship": "Gestion de naves y propulsion",
    "zidrone": "Control de enjambre de drones",
    "zirobot": "Sistema robotico de mantenimiento",
    "zicomm": "Red de comunicaciones y enlace",
    "zieco": "Sistema ecologico de soporte vital",
    "zimed": "Monitoreo medico de la tripulacion",
    "zicorex": "Nucleo de computacion e IA",
    "zilink": "Enlace de datos optico/RF",
    "zivr": "Entorno de realidad virtual",
    "zisec": "Ciberseguridad y proteccion",
    "zicriogen": "Gestion criogenica de propelente",
    "zimaury": "Sistema de defensa ZIMAUR",
    "zty": "Z-TY Fabrica de aeronaves",
}

# ── App ─────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ZiCore system starting...")
    yield
    logger.info("ZiCore system stopped.")

app = FastAPI(title="ZiCore API", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(agent_router)

# ── Helpers ─────────────────────────────────────────────────────────────────
def _update_module(name: str, data: dict) -> bool:
    mod = modules.get(name)
    if mod is None:
        return False
    mod.update(data)
    return True

def _get_all_modules() -> dict:
    return {name: mod.model_dump() for name, mod in modules.items()}

# ── REST API ────────────────────────────────────────────────────────────────
@app.get("/api/status")
async def get_status():
    return {
        "status": "online",
        "version": "0.2.0",
        "modules": _get_all_modules(),
    }

class InferRequest(BaseModel):
    module: str = "zisys"
    instruction: str = ""
    input_data: str = ""

@app.post("/api/infer")
async def run_inference(body: InferRequest):
    result = await orchestrator.infer(body.module, body.instruction, body.input_data)
    return result

@app.post("/api/telemetry/{module}")
async def update_telemetry(module: str, data: dict):
    if not _update_module(module, data):
        raise HTTPException(status_code=400, detail=f"Unknown module: {module}")
    return {"status": "ok", "module": module}

@app.get("/api/hierarchy")
async def get_hierarchy():
    zinav_mod = modules["zinav"]
    return {
        "zinav": {
            "description": MODULE_DESCRIPTIONS["zinav"],
            "modes": ["zinav-ascent", "zinav-transition", "zinav-orbit", "zinav-descent", "zinav-interplanetary"],
            "current_mode": zinav_mod.mode,
            "current_phase": zinav_mod.phase,
            "subsystem": {
                "ziaxis": {
                    "description": "Sistema estructural de eje gravitacional - HARDWARE que ejecuta GPD",
                    "status": zinav_mod.ziaxis.status,
                    "gpd": {
                        "description": "Tecnica de descenso por camino gravitacional - METODO",
                        "active": zinav_mod.ziaxis.gpd_active,
                        "phase": zinav_mod.ziaxis.descent_phase,
                    }
                }
            }
        },
        **{k: {"description": v} for k, v in MODULE_DESCRIPTIONS.items() if k != "zinav"},
    }

@app.get("/api/gpd/calculate")
async def calculate_gpd(altitude_km: float = 400, velocity_kms: float = 7.68, mass_kg: float = 50000):
    grad = gpd.gravitational_gradient(5.97e24, altitude_km * 1000)
    tidal = gpd.tidal_force(mass_kg, 82, grad)
    energy = gpd.energy_distribution(altitude_km, velocity_kms, mass_kg)
    zinav_mod = modules["zinav"]
    stability = gpd.path_stability(zinav_mod.ziaxis.axial_alignment_deg, zinav_mod.ziaxis.mass_distribution_pct)
    return {
        "gradient": grad,
        "tidal_force_n": tidal,
        "energy": energy,
        "path_stability_pct": stability,
        "ziaxis_status": zinav_mod.ziaxis.model_dump(),
    }

@app.get("/api/zty/templates")
async def list_zty_templates():
    return {"templates": zty_factory.list_vehicles()}

@app.get("/api/zty/report/{name}")
async def get_zty_report(name: str):
    report = zty_factory.generate_report(name)
    if not report:
        raise HTTPException(status_code=404, detail=f"Template '{name}' not found")
    return report

class CustomAircraftRequest(BaseModel):
    name: str = "custom"
    type: str = "custom"
    stages: list = []
    propulsion: dict = {}
    payload: float = 5000
    crew: int = 0

@app.post("/api/zty/custom")
async def create_custom_aircraft(body: CustomAircraftRequest):
    from zty import AircraftConfig, StageConfig, PropulsionConfig
    try:
        stages = [StageConfig(**s) for s in body.stages]
        propulsion = PropulsionConfig(**body.propulsion)
        config = AircraftConfig(name=body.name, vehicle_type=body.type,
                                stages=stages, propulsion=propulsion,
                                payload_kg=body.payload, crew=body.crew)
        return zty_factory.analyze(config)
    except (TypeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

# ── WebSocket ───────────────────────────────────────────────────────────────
@app.websocket("/ws/telemetry")
async def telemetry_ws(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected")
    try:
        while True:
            msg = await websocket.receive_text()
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "invalid JSON"})
                continue
            mod = data.get("module", "")
            _update_module(mod, data)
            await websocket.send_json(_get_all_modules())
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")

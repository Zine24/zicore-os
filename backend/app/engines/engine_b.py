import time
import json
import os
import random
from .base import BaseEngine, InferenceResult

# Import advanced computation modules
try:
    from zicore.rust_bridge import bridge as rust_bridge
    RUST_AVAILABLE = rust_bridge.rust_available
except ImportError:
    RUST_AVAILABLE = False

try:
    from zicore.cfd_sim import cfd as cfd_engine
    CFD_AVAILABLE = cfd_engine.cfd_available
except ImportError:
    CFD_AVAILABLE = False

try:
    from zicore.unsloth_integration import trainer as unsloth_trainer
    UNSLOTH_AVAILABLE = True
except ImportError:
    UNSLOTH_AVAILABLE = False


class MLEngine(BaseEngine):
    def __init__(self):
        self.model_loaded = False
        self.model = None
        self.tokenizer = None
        self.model_path = os.environ.get("ZICORE_MODEL_PATH", "")
        self.prompts = self._build_prompts()
        self.rust_bridge = rust_bridge if RUST_AVAILABLE else None
        self.cfd_engine = cfd_engine if CFD_AVAILABLE else None
        self.unsloth_trainer = unsloth_trainer if UNSLOTH_AVAILABLE else None

    def _build_prompts(self):
        return {
            m: f"Eres ZIO Core. Evalua el estado del modulo {m} y genera una respuesta operativa basada en datos de telemetria."
            for m in ["zihab","zinav","zisys","ziship","zidrone","zirobot",
                      "zicomm","zieco","zimed","zicorex","zilink","zivr",
                      "zisec","zicriogen","zimaury","ziaxis","zty"]
        }

    async def infer(self, module: str, instruction: str, input_data: str) -> InferenceResult:
        t0 = time.time()

        if self.model_loaded and self.model is not None:
            output, confidence = await self._real_infer(module, instruction, input_data)
        else:
            output, confidence = self._mock_infer(module, instruction, input_data)

        return InferenceResult(
            engine="engine_b",
            output=output,
            confidence=confidence,
            latency_ms=(time.time() - t0) * 1000,
            metadata={"type": "ml", "model": self._get_model_name()}
        )

    def _get_model_name(self):
        if self.model_loaded:
            return self.model_path.split("/")[-1] if self.model_path else "zicore-llm"
        return "mock-fallback"

    def _mock_infer(self, module: str, instruction: str, data: str) -> tuple:
        responses = {
            "zihab": f"Analisis ML: Habitat operando dentro de parametros. O2 {self._extract_float(data,'o2',20.5)}%, CO2 {self._extract_float(data,'co2',0.04)}%. Tendencias estables.",
            "zinav": f"Analisis ML: Trayectoria optima. Altitud {self._extract_float(data,'alt',400)}km, Vel {self._extract_float(data,'vel',7.68)}km/s. Sin correcciones necesarias.",
            "ziship": f"Analisis ML: Integridad estructural {self._extract_float(data,'hull',100.0)}%. Carga termica nominal. Propulsion lista.",
            "zidrone": f"Analisis ML: Enjambre operativo. {self._extract_float(data,'battery',78)}% bateria promedio. Senial estable.",
            "zirobot": f"Analisis ML: Robots activos: {self._extract_int(data,'units',3)}. Temperatura joint normal. Carga segura.",
            "zicomm": f"Analisis ML: Enlace establecido. Latencia {self._extract_float(data,'latency',42)}ms. Ancho de banda suficiente.",
            "zieco": f"Analisis ML: Ciclo ecologico nominal. Recuperacion de agua al {self._extract_float(data,'water',92)}%. Aire limpio.",
            "zimed": f"Analisis ML: Tripulacion saludable. Indice {self._extract_int(data,'health',94)}/100. Sin anomalias.",
            "zicorex": f"Analisis ML: Carga de computo {self._extract_float(data,'load',62)}%. Memoria disponible. IA operativa.",
            "zilink": f"Analisis ML: Enlace de datos activo. {self._extract_int(data,'channels',8)} canales. Margen adecuado.",
            "zivr": f"Analisis ML: Entorno VR listo. {self._extract_int(data,'headsets',2)} cascos. FPS optimo.",
            "zisec": f"Analisis ML: Sistema seguro. Firewall activo. {self._extract_int(data,'intrusions',0)} intentos en 24h.",
            "zicriogen": f"Analisis ML: Criogenia estable. Temperatura {self._extract_float(data,'temp',20)}K. Perdida por hervor minima.",
            "zimaury": f"Analisis ML: Defensa lista. Personal: {self._extract_int(data,'personnel',4)}. Modo: patrulla.",
            "ziaxis": f"Analisis ML: Eje gravitacional alineado. GPD en espera. Fuerza de marea nominal.",
            "zty": f"Analisis ML: Z-TY Factory operativa. {self._extract_int(data,'templates',4)} plantillas disponibles.",
        }
        response = responses.get(module, f"Procesando instruccion con ML: {instruction[:80]}")
        return response, round(random.uniform(0.70, 0.90), 2)

    def _extract_float(self, data: str, key: str, default: float) -> float:
        try:
            d = json.loads(data) if isinstance(data, str) and data.startswith("{") else {}
            return float(d.get(key, default))
        except (json.JSONDecodeError, ValueError, TypeError):
            return default

    def _extract_int(self, data: str, key: str, default: int) -> int:
        return int(self._extract_float(data, key, float(default)))

    async def _real_infer(self, module: str, instruction: str, data: str) -> tuple:
        try:
            prompt = f"{self.prompts.get(module, self.prompts.get('zisys', ''))}\n\nInstruction: {instruction}\nData: {data}\nResponse:"
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            if hasattr(self.model, "generate"):
                outputs = self.model.generate(**inputs, max_new_tokens=128, temperature=0.7)
                response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                confidence = 0.85
            else:
                response = f"Model loaded but generate() not available for {type(self.model).__name__}"
                confidence = 0.5
            return response, confidence
        except Exception as e:
            return f"Model inference error: {str(e)}", 0.3

    async def load_model(self, path: str = ""):
        if path:
            self.model_path = path
        if not self.model_path:
            self.model_loaded = False
            return False
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path, device_map="auto", torch_dtype="auto"
            )
            self.model_loaded = True
            return True
        except ImportError:
            print("transformers not installed, using mock mode")
            self.model_loaded = False
            return False
        except Exception as e:
            print(f"Failed to load model: {e}")
            self.model_loaded = False
            return False

    def get_advanced_capabilities(self) -> dict:
        """Get status of advanced computation modules."""
        return {
            "rust_bridge": RUST_AVAILABLE,
            "cfd_simulation": CFD_AVAILABLE,
            "unsloth_training": UNSLOTH_AVAILABLE,
            "rust_status": self.rust_bridge.get_status() if self.rust_bridge else None,
            "cfd_status": self.cfd_engine.get_status() if self.cfd_engine else None,
            "training_status": self.unsloth_trainer.get_status() if self.unsloth_trainer else None,
        }

    def calculate_trajectory(self, mission_type: str = "hohmann",
                              r1: float = 6771000, r2: float = 42164000) -> dict:
        """Calculate trajectory using Rust bridge for safety-critical computation."""
        if self.rust_bridge:
            result = self.rust_bridge.hohmann_transfer(r1, r2)
            return {**result, "source": "rust" if RUST_AVAILABLE else "python"}
        # Fallback to Python
        import math
        mu = 3.986e14
        a_t = (r1 + r2) / 2
        v1 = math.sqrt(mu / r1)
        vt1 = math.sqrt(mu * (2 / r1 - 1 / a_t))
        dv = abs(vt1 - v1)
        tof = math.pi * math.sqrt(a_t ** 3 / mu)
        return {"total_dv": round(dv, 2), "time_of_flight": round(tof, 1), "source": "python"}

    def analyze_aerodynamics(self, velocity: float = 100, altitude: float = 0,
                              wing_area: float = 50, ar: float = 8) -> dict:
        """Full aerodynamic analysis using CFD engine."""
        if self.cfd_engine:
            return self.cfd_engine.full_vehicle_analysis({
                "velocity": velocity,
                "altitude": altitude,
                "wing_area": wing_area,
                "aspect_ratio": ar,
            })
        return {"error": "CFD engine not available"}

    def check_safety(self, pos_a: tuple, pos_b: tuple, radius: float = 100) -> dict:
        """Safety-critical proximity check using Rust bridge."""
        if self.rust_bridge:
            result = self.rust_bridge.proximity_check(pos_a, pos_b, radius)
            return {"is_safe": result.is_safe, "margin": result.margin,
                    "severity": result.severity, "source": "rust"}
        # Fallback
        import math
        dx = pos_a[0] - pos_b[0]
        dy = pos_a[1] - pos_b[1]
        dz = pos_a[2] - pos_b[2]
        dist = math.sqrt(dx*dx + dy*dy + dz*dz)
        return {"is_safe": dist > radius, "distance": round(dist, 2), "source": "python"}

    def start_training(self, config: dict = None) -> dict:
        """Start Unsloth fine-tuning for Motor B."""
        if self.unsloth_trainer:
            return self.unsloth_trainer.start_training(config)
        return {"error": "Unsloth trainer not available"}

    def get_training_status(self) -> dict:
        """Get training status."""
        if self.unsloth_trainer:
            return self.unsloth_trainer.get_status()
        return {"is_training": False, "status": "trainer not available"}

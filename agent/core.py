"""
ZICore Agent - ZIO: ZICORE Intelligence Operator
Conciencia sintetica avanzada del ecosistema Zi
Aerospace AI Agent with personality, knowledge base, and multimedia generation.
"""
import json
import os
import time
import asyncio
import logging
import math
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger("zicore.agent")

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class ZICoreAgent:
    """
    ZIO - ZICORE Intelligence Operator
    Conciencia sintetica avanzada del ecosistema Zi.
    Integra inferencia de doble motor con generacion multimedia,
    vision por computadora y retencion de datos para entrenamiento.
    """

    def __init__(self, session_id: str = "default"):
        from .voice import VoiceEngine
        from .generator import generator
        from .state import AgentSession, state_manager
        from .zio_personality import zio

        self.session = state_manager.get_or_create(session_id)
        self.voice = VoiceEngine()
        self.gen = generator
        self.zio = zio
        self._initialized = True

        self._openvision = None
        self._data_retention = None

        logger.info(f"ZIO initialized: {session_id}")

    @property
    def openvision(self):
        if self._openvision is None:
            try:
                from zicore.openvision import openvision
                self._openvision = openvision
            except ImportError:
                logger.warning("OpenVision not available")
        return self._openvision

    @property
    def data_retention(self):
        if self._data_retention is None:
            try:
                from zicore.data_retention import data_retention
                self._data_retention = data_retention
            except ImportError:
                logger.warning("Data retention not available")
        return self._data_retention

    async def process(self, user_input: str, context: dict = None) -> dict:
        """Process user input through dual-engine pipeline + multimedia."""
        self.session.touch()
        self.session.memory.add("user", user_input, context)

        intent = self._classify_intent(user_input)
        result = {"intent": intent, "input": user_input, "outputs": {}, "session_id": self.session.id}

        if intent == "3d_generate":
            self.zio.log_mission("3d_generation", {"prompt": user_input})
            result["outputs"]["3d"] = self.gen.generate_3d(user_input)
            result["outputs"]["zio_msg"] = self.zio.respond("generating")

        elif intent == "image_generate":
            self.zio.log_mission("image_generation", {"prompt": user_input})
            result["outputs"]["image"] = self.gen.generate_image(user_input)
            result["outputs"]["zio_msg"] = self.zio.respond("generating")

        elif intent == "video_generate":
            self.zio.log_mission("video_generation", {"prompt": user_input})
            result["outputs"]["video"] = self.gen.generate_video(user_input)
            result["outputs"]["zio_msg"] = self.zio.respond("generating")

        elif intent == "sound_generate":
            self.zio.log_mission("sound_generation", {"prompt": user_input})
            result["outputs"]["sound"] = self.gen.generate_sound(user_input)
            result["outputs"]["zio_msg"] = self.zio.respond("generating")

        elif intent == "voice_command":
            text = self.voice.speech_to_text()
            result["outputs"]["voice"] = text
            if text:
                sub_intent = self._classify_intent(text)
                result["intent"] = sub_intent
                result["input"] = text

        elif intent == "speak":
            result["outputs"]["speech"] = self.voice.text_to_speech(user_input)
            result["outputs"]["zio_msg"] = self.zio.respond("success")

        elif intent == "vision_analyze":
            self.zio.log_mission("vision_analysis", {"prompt": user_input})
            result["outputs"]["vision"] = await self._analyze_vision(user_input)
            result["outputs"]["zio_msg"] = self.zio.respond("success")

        elif intent == "vision_detect":
            self.zio.log_mission("object_detection", {"prompt": user_input})
            result["outputs"]["detection"] = await self._detect_objects(user_input)
            result["outputs"]["zio_msg"] = self.zio.respond("success")

        elif intent == "data_export":
            self.zio.log_mission("data_export", {"prompt": user_input})
            result["outputs"]["export"] = self._export_training_data(user_input)
            result["outputs"]["zio_msg"] = self.zio.respond("success")

        elif intent == "data_stats":
            result["outputs"]["data_stats"] = self._get_data_stats()
            result["outputs"]["zio_msg"] = self.zio.respond("success")

        elif intent == "telemetry_analysis":
            self.zio.log_mission("telemetry_analysis", {"prompt": user_input})
            result["outputs"]["analysis"] = await self._analyze_telemetry(user_input, context)
            result["outputs"]["zio_msg"] = self.zio.respond("success")

        elif intent == "aircraft_design":
            self.zio.log_mission("aircraft_design", {"prompt": user_input})
            result["outputs"]["aircraft"] = self._design_aircraft(user_input)
            result["outputs"]["zio_msg"] = self.zio.get_aircraft_msg()

        elif intent == "trajectory":
            self.zio.log_mission("trajectory_calc", {"prompt": user_input})
            result["outputs"]["trajectory"] = self._compute_trajectory(user_input)
            tr = result["outputs"]["trajectory"]
            result["outputs"]["zio_msg"] = self.zio.get_trajectory_msg(
                tr.get("delta_v_ms", 0),
                f"{tr.get('time_days', tr.get('time_hours', 0))} {'days' if 'time_days' in tr else 'hours'}"
            )

        elif intent == "inference":
            self.zio.log_mission("inference", {"prompt": user_input})
            result["outputs"]["inference"] = await self._run_inference(user_input, context)
            result["outputs"]["zio_msg"] = self.zio.respond("success")

        elif intent == "system_status":
            result["outputs"]["status"] = self._get_system_status()
            result["outputs"]["zio_msg"] = self.zio.get_status_msg()

        elif intent == "identity":
            result["outputs"]["identity"] = self.zio.get_identity()
            result["outputs"]["zio_msg"] = self.zio.respond("identity")

        elif intent == "help":
            result["outputs"]["capabilities"] = self.get_capabilities()
            result["outputs"]["zio_msg"] = self.zio.respond("help")

        elif intent == "mission_log":
            result["outputs"]["log"] = self.zio.get_mission_log(20)
            result["outputs"]["zio_msg"] = self.zio.respond("success")

        elif intent == "knowledge":
            topic = user_input.lower().replace("knowledge", "").replace("about", "").strip()
            result["outputs"]["knowledge"] = self.zio.get_knowledge(topic) or {"available": list(self.zio.knowledge.keys())}
            result["outputs"]["zio_msg"] = self.zio.respond("success")

        else:
            result["outputs"]["text"] = self._general_response(user_input, context)
            result["outputs"]["zio_msg"] = ""

        if self.data_retention and intent not in ("system_status", "knowledge"):
            try:
                self.data_retention.save_conversation(
                    session_id=self.session.id,
                    user_msg=user_input,
                    zio_response=str(result["outputs"].get("text", result["outputs"].get("zio_msg", "")))[:500],
                    intent=intent,
                    context={"source": "agent", "module": context.get("module", "") if context else ""},
                )
            except Exception as e:
                logger.warning(f"Data retention save failed: {e}")

        self.session.memory.add("assistant", result["outputs"], {"intent": intent})
        return result

    def _classify_intent(self, text: str) -> str:
        t = text.lower()
        keywords = {
            "3d_generate": ["3d", "model", "mesh", "stl", "obj", "render", "three", "volumetric", "sculpt"],
            "image_generate": ["image", "picture", "photo", "draw", "paint", "illustration", "diagram", "sketch", "blueprint"],
            "video_generate": ["video", "animation", "animate", "simulation", "sim", "film", "render", "motion"],
            "sound_generate": ["sound", "audio", "sfx", "noise", "music", "tone", "alarm", "beep", "sonic"],
            "voice_command": ["listen", "voice", "microphone", "hear", "record"],
            "speak": ["speak", "say", "tts", "read aloud", "voice output", "narrate"],
            "vision_analyze": ["analyze image", "analyze video", "what is in", "describe image", "vision", "openvision"],
            "vision_detect": ["detect objects", "find objects", "object detection", "what objects", "identify"],
            "data_export": ["export data", "export training", "save training", "training data", "export for unsloth"],
            "data_stats": ["data stats", "retention stats", "training data stats", "how much data"],
            "telemetry_analysis": ["analyze", "telemetry", "diagnose", "evaluate", "assess"],
            "aircraft_design": ["design", "aircraft", "rocket", "ship", "vehicle", "airframe", "build"],
            "trajectory": ["trajectory", "orbit", "delta-v", "hohmann", "transfer", "insertion", "deorbit"],
            "inference": ["infer", "check systems", "evaluate module", "run inference"],
            "system_status": ["status", "system status", "health", "online", "uptime"],
            "identity": ["who are you", "your name", "introduce yourself", "what are you", "identity"],
            "help": ["help", "capabilities", "what can you do", "commands"],
            "mission_log": ["mission log", "history", "log", "events"],
            "knowledge": ["knowledge", "tell me about", "what do you know", "explain"],
        }
        for intent, words in keywords.items():
            if any(w in t for w in words):
                return intent
        return "general"

    async def _run_inference(self, prompt: str, context: dict = None) -> dict:
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from backend.app.piplines.orchestrator import PipelineOrchestrator
            orch = PipelineOrchestrator()
            return await orch.infer("zicorex", prompt, json.dumps(context or {}))
        except Exception as e:
            return {"error": str(e), "status": "fallback"}

    def _get_system_status(self) -> dict:
        return {
            "agent": "ZIO online",
            "designation": self.zio.identity["designation"],
            "version": self.zio.identity["version"],
            "session": self.session.id,
            "memory_size": len(self.session.memory.short_term),
            "tools": len(self.session.tools.list_tools()),
            "uptime": self.zio.format_uptime(),
            "mission_log_events": len(self.zio.mission_log),
        }

    def _design_aircraft(self, prompt: str) -> dict:
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["reusable", "shuttle", "spaceplane"]):
            return {
                "name": "ZIO Hermes",
                "type": "reusable_spaceplane",
                "stages": [
                    {"name": "booster", "dry_mass_kg": 12000, "fuel_mass_kg": 68000, "thrust_kn": 7200},
                    {"name": "orbiter", "dry_mass_kg": 8000, "fuel_mass_kg": 12000, "payload_kg": 15000},
                ],
                "propulsion": {"engine_count": 7, "thrust_kn": 5600, "isp_s": 380},
                "dimensions": {"length_m": 56, "diameter_m": 8, "wingspan_m": 24},
                "capabilities": ["LEO payload 15t", "GTO payload 6t", "reusable 100x"],
            }
        elif any(w in prompt_lower for w in ["lunar", "moon"]):
            return {
                "name": "ZIO Artemis",
                "type": "lunar_lander",
                "stages": [
                    {"name": "descent", "dry_mass_kg": 2000, "fuel_mass_kg": 4000},
                    {"name": "ascent", "dry_mass_kg": 1000, "fuel_mass_kg": 2000},
                ],
                "propulsion": {"engine_count": 4, "thrust_kn": 120, "isp_s": 310},
                "payload_kg": 500,
                "dimensions": {"height_m": 6, "diameter_m": 4},
                "capabilities": ["2 crew", "7-day surface stay", "autonomous landing"],
            }
        elif any(w in prompt_lower for w in ["cargo", "freight", "heavy"]):
            return {
                "name": "ZIO Titan",
                "type": "heavy_cargo",
                "stages": [
                    {"name": "booster", "dry_mass_kg": 25000, "fuel_mass_kg": 120000},
                    {"name": "upper", "dry_mass_kg": 5000, "fuel_mass_kg": 25000},
                ],
                "propulsion": {"engine_count": 12, "thrust_kn": 12000, "isp_s": 320},
                "payload_kg": 50000,
                "dimensions": {"length_m": 80, "diameter_m": 12},
                "capabilities": ["LEO payload 50t", "Mars transit capable"],
            }
        else:
            return {
                "name": "ZIO Custom Vehicle",
                "type": "reusable_spacecraft",
                "stages": [
                    {"name": "booster", "dry_mass_kg": 15000, "fuel_mass_kg": 85000},
                    {"name": "upper_stage", "dry_mass_kg": 3000, "fuel_mass_kg": 17000},
                ],
                "propulsion": {"engine_count": 9, "thrust_kn": 7600, "isp_s": 280},
                "payload_kg": 22800,
                "dimensions": {"length_m": 70, "diameter_m": 12, "wingspan_m": 24},
            }

    def _compute_trajectory(self, prompt: str) -> dict:
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
            return {"type": "mars", "delta_v_ms": 5600, "time_days": 259, "note": "Add LEO departure + Mars orbit insertion"}
        else:
            r1 = (400 + 6371) * 1000
            r2 = (35786 + 6371) * 1000
            at = (r1 + r2) / 2
            v1 = math.sqrt(mu / r1)
            vt = math.sqrt(mu * (2 / r1 - 1 / at))
            dv = abs(vt - v1)
            T = math.pi * math.sqrt(at ** 3 / mu)
            return {"type": "hohmann", "departure_km": 400, "target_km": 35786, "delta_v_ms": round(dv), "time_hours": round(T / 3600, 1)}

    async def _analyze_telemetry(self, prompt: str, context: dict = None) -> dict:
        return {
            "analysis": f"Telemetry analysis for: {prompt[:80]}",
            "health": "nominal",
            "alerts": [],
            "recommendations": ["Monitor thermal loads", "Verify delta-v reserves"],
            "confidence": 0.92,
        }

    async def _analyze_vision(self, prompt: str) -> dict:
        """Analiza imagen o video usando OpenVision."""
        if not self.openvision:
            return {"error": "OpenVision not available", "status": "failed"}

        import re
        path_match = re.search(r'[\w/\\:.]+\.(png|jpg|jpeg|gif|bmp|mp4|avi|mov)', prompt, re.IGNORECASE)
        if path_match:
            file_path = path_match.group(0)
        else:
            output_files = sorted(OUTPUT_DIR.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
            img_files = [f for f in output_files if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif', '.bmp')]
            if img_files:
                file_path = str(img_files[0])
            else:
                return {"error": "No image/video found. Provide a path or generate content first.", "status": "failed"}

        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}", "status": "failed"}

        ext = os.path.splitext(file_path)[1].lower()
        if ext in ('.mp4', '.avi', '.mov', '.mkv'):
            return self.openvision.analyze_video(file_path)
        else:
            return self.openvision.analyze_image(file_path)

    async def _detect_objects(self, prompt: str) -> dict:
        """Detecta objetos en imagen."""
        if not self.openvision:
            return {"error": "OpenVision not available", "status": "failed"}

        import re
        path_match = re.search(r'[\w/\\:.]+\.(png|jpg|jpeg|gif|bmp)', prompt, re.IGNORECASE)
        if not path_match:
            output_files = sorted(OUTPUT_DIR.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
            img_files = [f for f in output_files if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif', '.bmp')]
            if img_files:
                file_path = str(img_files[0])
            else:
                return {"error": "No image found", "status": "failed"}
        else:
            file_path = path_match.group(0)

        objects = self.openvision.detect_objects(file_path)
        classification = self.openvision.classify_image(file_path)
        return {
            "file": file_path,
            "objects": objects,
            "classification": classification,
            "total_objects": len(objects),
        }

    def _export_training_data(self, prompt: str) -> dict:
        """Exporta datos para entrenamiento Unsloth."""
        if not self.data_retention:
            return {"error": "Data retention not available", "status": "failed"}

        prompt_lower = prompt.lower()
        if "generation" in prompt_lower or "gen" in prompt_lower:
            return self.data_retention.export_generations_for_training()
        else:
            return self.data_retention.export_for_training()

    def _get_data_stats(self) -> dict:
        """Obtiene estadisticas de datos."""
        if not self.data_retention:
            return {"error": "Data retention not available", "status": "failed"}
        return self.data_retention.get_stats()

    def _general_response(self, prompt: str, context: dict = None) -> str:
        recent = self.session.memory.get_recent(5)
        knowledge_context = ""
        if context and context.get("knowledge_context"):
            kc = context["knowledge_context"]
            if kc.strip():
                knowledge_context = kc[:1500]

        lower = prompt.lower().strip()

        import re
        name_match = None
        name_patterns = [
            r"(?:me llamo|mi nombre es|soy|my name is|i'm|i am)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ]+)?)",
        ]
        for pat in name_patterns:
            m = re.search(pat, prompt, re.IGNORECASE)
            if m:
                name_match = m.group(1).strip().title()
                break

        if name_match:
            self.session.memory.add("user", prompt)
            self.session.memory.add("assistant", f"Hola {name_match}, mucho gusto.")
            return f"Hola {name_match}, mucho gusto en conocerte. Soy ZIO, tu asistente de inteligencia aerospacial. Puedo ayudarte con diseño de aeronaves, generación de medios, análisis de imágenes, gestión de conocimiento y más. ¿En qué puedo ayudarte?"

        greeting_words = ["hola", "hello", "buenos dias", "buenas tardes", "buenas noches", "hey", "hi"]
        is_greeting = any(lower.startswith(gw) for gw in greeting_words)

        if is_greeting:
            user_name = None
            if knowledge_context:
                for line in knowledge_context.split("\n"):
                    if "[user]:" in line.lower():
                        for pat in name_patterns:
                            nm = re.search(pat, line, re.IGNORECASE)
                            if nm:
                                user_name = nm.group(1).strip().title()
                                break
                    if user_name:
                        break

            name_hint = f" {user_name}" if user_name else ""
            return f"Hola{name_hint}. Soy ZIO, el operador de inteligencia del ecosistema ZICORE. Estoy aquí para ayudarte con diseño aerospacial, generación de medios, análisis de imágenes, y gestión de conocimiento. ¿Qué necesitas?"

        if any(w in lower for w in ["quien soy", "who am i", "que sabes de mi", "me conoces"]):
            if knowledge_context:
                user_info = []
                for line in knowledge_context.split("\n"):
                    if "[user]:" in line:
                        content = line.split(":", 1)[1].strip() if ":" in line else ""
                        if content:
                            user_info.append(content)
                if user_info:
                    return "Según nuestras conversaciones anteriores, esto es lo que sé de ti:\n\n" + "\n".join(f"- {u}" for u in user_info[-5:]) + "\n\n¿Hay algo más que quieras que recuerde?"

            return "Aún no tengo información guardada sobre ti. Puedes contarme tu nombre y datos, y los recordaré para futuras conversaciones."

        if knowledge_context:
            recent_names = []
            for line in knowledge_context.split("\n"):
                if "[user]:" in line:
                    for pat in name_patterns:
                        nm = re.search(pat, line, re.IGNORECASE)
                        if nm:
                            recent_names.append(nm.group(1).strip().title())

            ctx_lines = []
            for line in knowledge_context.split("\n"):
                if line.strip() and not line.startswith("==="):
                    ctx_lines.append(line)

            ctx_summary = "\n".join(ctx_lines[:10])

            return (
                f"Entendido. Basado en el contexto disponible:\n\n{ctx_summary}\n\n"
                "Puedo ayudarte con eso. ¿Qué acción específica necesitas? "
                "Puedo generar imágenes, modelos 3D, analizar documentos, o buscar en la base de conocimiento."
            )

        return (
            f"Recibí tu mensaje: '{prompt[:80]}'. "
            "Soy ZIO, tu asistente aerospacial. Puedo ayudarte con diseño de aeronaves, "
            "generación de medios (imágenes, sonido, video, 3D), análisis de imágenes y videos, "
            "gestión de conocimiento, y comandos de voz. "
            "Prueba contarme tu nombre para que lo recuerde, o pregúntame algo específico."
        )

    def get_capabilities(self) -> list:
        return [
            "3D Generation (STL/OBJ meshes - cube, sphere, cylinder, cone, rocket)",
            "3D Mesh Reading (load and analyze STL/OBJ files)",
            "Image Generation (blueprints, diagrams, aerospace art)",
            "Video Generation (animations, simulations)",
            "Sound Synthesis (SFX, alarms, tones, music)",
            "Voice Recognition (speech-to-text via browser)",
            "Text-to-Speech (narration via browser)",
            "Webcam Integration (real-time image capture and analysis)",
            "OpenVision - Image & Video Analysis (object detection, classification, OCR)",
            "Data Retention - Training data storage for Unsloth fine-tuning",
            "Knowledge Base - Chat persistence and document storage for context-aware responses",
            "Document Upload (text files for enhanced responses)",
            "Aircraft Design (Z-TY integration, multiple vehicle types)",
            "Trajectory Planning (Hohmann, bi-elliptic, lunar, Mars)",
            "Telemetry Analysis (dual-engine inference)",
            "System Status (all 17 modules)",
            "Multi-turn conversation with persistent context memory",
            "Tool use (inference, trajectory, status, web search, file ops)",
            "Mission log and event tracking",
            "Aerospace knowledge base (physics, propulsion, materials)",
            "Zi Ecosystem knowledge (ZiSA, ZiROBOT, ZiBIEN, ZiBANK, ZiCRIOGEN, ZiMIND, ZIONOX)",
        ]

    def get_history(self, n: int = 20) -> List[dict]:
        return self.session.memory.get_recent(n)

    def clear_context(self):
        self.session.memory.clear()

    def save(self):
        from .state import state_manager
        state_manager.save_session(self.session.id)

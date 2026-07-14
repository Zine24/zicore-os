"""
ZICORE Auto-Loader
Initializes all generators, engines, and services on system start.
Single entry point for everything.
"""
import time
import logging
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("zicore.loader")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class SystemLoader:
    """Loads all ZICORE components automatically."""

    def __init__(self):
        self.engines = {}
        self.status = {}
        self._start_time = time.time()

    def load_all(self) -> Dict[str, Any]:
        """Load all components and return status report."""
        results = {}

        results["3d_engine"] = self._load_3d_engine()
        results["media_engine"] = self._load_media_engine()
        results["voice_engine"] = self._load_voice_engine()
        results["hunyuan3d"] = self._load_hunyuan3d()
        results["ollama"] = self._load_ollama()
        results["knowledge_base"] = self._load_knowledge_base()
        results["openvision"] = self._load_openvision()

        self.status = results
        return results

    def _load_3d_engine(self) -> dict:
        try:
            from agent.content3d import Engine3D
            engine = Engine3D()
            self.engines["3d"] = engine
            return {"status": "ok", "engine": "trimesh" if engine.trimesh else "fallback", "capabilities": ["stl", "obj"]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _load_media_engine(self) -> dict:
        try:
            from agent.media import MediaEngine
            engine = MediaEngine()
            self.engines["media"] = engine
            return {"status": "ok", "pillow": engine.PIL, "capabilities": ["image", "video", "sound"]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _load_voice_engine(self) -> dict:
        try:
            from agent.voice import VoiceEngine
            engine = VoiceEngine()
            self.engines["voice"] = engine
            return {"status": "ok", "tts": engine.tts_engine is not None, "capabilities": ["tts", "stt"]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _load_hunyuan3d(self) -> dict:
        try:
            from zicore.hunyuan3d_engine import Hunyuan3DEngine
            engine = Hunyuan3DEngine()
            self.engines["hunyuan3d"] = engine
            return {"status": "ok", "capabilities": ["text_to_mesh", "mesh_refine"]}
        except ImportError:
            return {"status": "not_installed", "hint": "pip install hunyuan3d"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _load_ollama(self) -> dict:
        try:
            from zicore.ollama_service import status
            s = status()
            return s
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _load_knowledge_base(self) -> dict:
        try:
            from zicore.knowledge_base import knowledge_base
            self.engines["knowledge"] = knowledge_base
            stats = knowledge_base.get_stats() if hasattr(knowledge_base, "get_stats") else {}
            return {"status": "ok", "stats": stats}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _load_openvision(self) -> dict:
        try:
            from zicore.openvision import openvision
            self.engines["openvision"] = openvision
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_engine(self, name: str):
        return self.engines.get(name)

    def print_report(self):
        total = len(self.status)
        ok = sum(1 for s in self.status.values() if s.get("status") == "ok")
        print(f"\n{'='*60}")
        print(f"  ZICORE System Loader - {ok}/{total} engines ready")
        print(f"{'='*60}")
        for name, s in self.status.items():
            icon = "+" if s.get("status") == "ok" else "~" if s.get("status") == "not_installed" else "-"
            extra = ""
            if "engine" in s:
                extra = f" ({s['engine']})"
            elif "models" in s:
                extra = f" ({len(s.get('models', []))} models)"
            elif "pillow" in s:
                extra = " (pillow)" if s["pillow"] else ""
            elif "tts" in s:
                extra = " (tts)" if s["tts"] else " (browser-only)"
            print(f"  [{icon}] {name}{extra}")
        print(f"{'='*60}\n")


loader = SystemLoader()

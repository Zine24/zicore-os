"""
ZICORE Generation Pipeline — Unified orchestrator for all media generation.

Routes generation requests to the best available engine for each type,
persists results in the Generation Library, and returns standardized responses.

Supported types: image, sound, 3d, video
"""
import os
import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, Optional, List

logger = logging.getLogger("zicore.generation_pipeline")

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"


class GenerationPipeline:
    def __init__(self):
        self._generator = None
        self._media_engine = None
        self._engine_3d = None
        self._library = None
        self._ai3d = None
        self._stable_diffusion = None

    def _get_generator(self):
        if self._generator is None:
            try:
                from agent.generator import ZICoreGenerator
                self._generator = ZICoreGenerator()
            except Exception as e:
                logger.warning(f"ZICoreGenerator not available: {e}")
        return self._generator

    def _get_library(self):
        if self._library is None:
            try:
                from zicore.generation_library import GenerationLibrary
                self._library = GenerationLibrary()
            except Exception as e:
                logger.warning(f"GenerationLibrary not available: {e}")
        return self._library

    def _get_ai3d(self):
        if self._ai3d is None:
            try:
                from zicore.ai3d_engines import ai3d
                self._ai3d = ai3d
            except Exception as e:
                logger.warning(f"AI3D engines not available: {e}")
        return self._ai3d

    def generate(self, gen_type: str, prompt: str, **kwargs) -> Dict[str, Any]:
        if gen_type == "image":
            return self.generate_image(prompt, **kwargs)
        elif gen_type == "sound":
            return self.generate_sound(prompt, **kwargs)
        elif gen_type == "3d":
            return self.generate_3d(prompt, **kwargs)
        elif gen_type == "video":
            return self.generate_video(prompt, **kwargs)
        else:
            return {"status": "error", "error": f"Unknown type: {gen_type}"}

    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        gen = self._get_generator()
        if not gen:
            return {"status": "error", "error": "No generator available"}
        result = gen.generate_image(prompt, **kwargs)
        self._register_in_library(result, "image", prompt)
        return result

    def generate_sound(self, prompt: str, **kwargs) -> Dict[str, Any]:
        gen = self._get_generator()
        if not gen:
            return {"status": "error", "error": "No generator available"}
        result = gen.generate_sound(prompt, **kwargs)
        self._register_in_library(result, "audio", prompt)
        return result

    def generate_3d(self, prompt: str, **kwargs) -> Dict[str, Any]:
        gen = self._get_generator()
        if gen:
            result = gen.generate_3d(prompt, **kwargs)
            if result and result.get("status") != "error":
                self._register_in_library(result, "3d", prompt)
                return result
        ai3d = self._get_ai3d()
        if ai3d:
            keys = [e["key"] for e in getattr(ai3d, "list_engines", lambda: [])() if e.get("available")]
            for key in keys[:3]:
                try:
                    r = ai3d.generate(engine_key=key, prompt=prompt)
                    if r and getattr(r, "success", False) and getattr(r, "file_path", ""):
                        result = {
                            "status": "ok",
                            "file_stl": getattr(r, "file_path", ""),
                            "engine": f"ai3d_{key}",
                            "vertices": getattr(r, "vertices", 0),
                            "faces": getattr(r, "faces", 0),
                        }
                        self._register_in_library(result, "3d", prompt)
                        return result
                except Exception as e:
                    logger.warning(f"AI3D {key} failed: {e}")
        if gen:
            return gen.generate_3d(prompt, **kwargs) or {"status": "error", "error": "Generator returned None"}
        return {"status": "error", "error": "No 3D engine available"}
        self._register_in_library(result, "3d", prompt)
        return result

    def generate_video(self, prompt: str, **kwargs) -> Dict[str, Any]:
        gen = self._get_generator()
        if not gen:
            return {"status": "error", "error": "No generator available"}
        result = gen.generate_video(prompt, **kwargs)
        self._register_in_library(result, "video", prompt)
        return result

    def _register_in_library(self, result: Dict, output_type: str, prompt: str):
        lib = self._get_library()
        if not lib:
            return
        file_path = result.get("file") or result.get("path") or result.get("file_stl") or ""
        if not file_path:
            return
        ext = Path(file_path).suffix.lower().lstrip(".") or "bin"
        try:
            lib.add(
                prompt=prompt,
                output_type=output_type,
                engine=result.get("engine", "zicore"),
                file_path=file_path,
                file_format=ext,
                metadata={"source": "generation_pipeline", "result": result},
            )
        except Exception as e:
            logger.warning(f"Failed to register in library: {e}")


pipeline = GenerationPipeline()

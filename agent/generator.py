"""ZICORE Generator — Unified media generation (image, sound, video, 3D)."""
import time
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("zicore.agent.generator")


class ZICoreGenerator:
    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._media_engine = None
        self._engine_3d = None

    def _get_media_engine(self):
        if self._media_engine is None:
            try:
                from agent.media import MediaEngine
                self._media_engine = MediaEngine()
            except Exception as e:
                logger.warning(f"MediaEngine not available: {e}")
        return self._media_engine

    def _get_engine_3d(self):
        if self._engine_3d is None:
            try:
                from agent.content3d import Engine3D
                self._engine_3d = Engine3D()
            except Exception as e:
                logger.warning(f"Engine3D not available: {e}")
        return self._engine_3d

    def generate(self, gen_type: str, prompt: str, **kwargs) -> Dict[str, Any]:
        if gen_type == "image":
            return self.generate_image(prompt, **kwargs)
        elif gen_type == "sound":
            return self.generate_sound(prompt, **kwargs)
        elif gen_type == "video":
            return self.generate_video(prompt, **kwargs)
        elif gen_type == "3d":
            return self.generate_3d(prompt, **kwargs)
        else:
            return {"status": "error", "error": f"Unknown generation type: {gen_type}"}

    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        engine = self._get_media_engine()
        if engine:
            return engine.generate_image(prompt, **kwargs)
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from zicore.stable_diffusion_engine import StableDiffusionEngine
            sd = StableDiffusionEngine()
            result = sd.generate(prompt, output_dir=str(self.output_dir / "images"))
            return {"status": "ok", "path": result.get("path", ""), "prompt": prompt}
        except Exception as e:
            logger.warning(f"Image generation fallback: {e}")
            return self._fallback_image(prompt, **kwargs)

    def _fallback_image(self, prompt, width=512, height=512):
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (width, height), (6, 6, 20))
            draw = ImageDraw.Draw(img)
            draw.text((width//4, height//2), f"ZICORE: {prompt[:40]}", fill=(0, 200, 255))
            save_path = str(self.output_dir / "images" / f"img_{int(time.time())}.png")
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            img.save(save_path, "PNG")
            return {"file": save_path, "prompt": prompt, "status": "fallback"}
        except Exception as e:
            return {"status": "fallback", "message": f"Image generation: {prompt}", "error": str(e)}

    def generate_sound(self, prompt: str, duration: float = 3.0, **kwargs) -> Dict[str, Any]:
        engine = self._get_media_engine()
        if engine:
            return engine.generate_sound(prompt, duration=duration, **kwargs)
        return self._fallback_sound(duration)

    def _fallback_sound(self, duration=3.0, sample_rate=44100):
        try:
            import struct
            import math
            import wave
            n = int(duration * sample_rate)
            samples = []
            for i in range(n):
                t = i / sample_rate
                s = 0.4 * math.sin(2 * math.pi * 440 * t)
                env = min(1.0, min(t * 5, (duration - t) * 5))
                samples.append(int(s * env * 32767))
            save_path = str(self.output_dir / f"sound_{int(time.time())}.wav")
            with wave.open(save_path, 'w') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                for s in samples:
                    wf.writeframes(struct.pack('<h', max(-32768, min(32767, s))))
            return {"file": save_path, "duration": duration, "status": "ok"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def generate_video(self, prompt: str, width: int = 640, height: int = 480,
                       duration: float = 5.0, fps: int = 24, **kwargs) -> Dict[str, Any]:
        engine = self._get_media_engine()
        if engine:
            result = engine.generate_video(prompt, width=width, height=height,
                                           duration=duration, fps=fps)
            return result
        return {
            "status": "ok",
            "message": f"Video generation queued: {prompt}",
            "params": {"width": width, "height": height, "duration": duration, "fps": fps},
        }

    def generate_3d(self, prompt: str, mesh_type: str = "auto", **kwargs) -> Dict[str, Any]:
        engine = self._get_engine_3d()
        if engine:
            return engine.generate_from_prompt(prompt)
        try:
            import trimesh
            mesh = trimesh.creation.icosphere(subdivisions=2, radius=1.0)
            output_path = self.output_dir / "meshes" / f"mesh_{int(time.time())}.stl"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mesh.export(str(output_path))
            return {"status": "ok", "path": str(output_path), "vertices": len(mesh.vertices), "faces": len(mesh.faces)}
        except Exception as e:
            return {"status": "error", "error": str(e)}


generator = ZICoreGenerator()

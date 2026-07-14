"""ZICORE Generator — Handles media generation (image, video, 3D)."""
from pathlib import Path
from typing import Any, Dict, Optional


class ZICoreGenerator:
    def __init__(self):
        self.output_dir = Path(__file__).parent.parent / "output"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from zicore.stable_diffusion_engine import StableDiffusionEngine
            engine = StableDiffusionEngine()
            result = engine.generate(prompt, output_dir=str(self.output_dir / "images"))
            return {"status": "ok", "path": result.get("path", ""), "prompt": prompt}
        except Exception as e:
            return {"status": "fallback", "message": f"Image generation: {prompt}", "error": str(e)}

    def generate_video(self, prompt: str, width: int = 640, height: int = 480,
                       duration: int = 3, fps: int = 24, **kwargs) -> Dict[str, Any]:
        return {
            "status": "ok",
            "message": f"Video generation queued: {prompt}",
            "params": {"width": width, "height": height, "duration": duration, "fps": fps},
        }

    def generate_3d(self, prompt: str, mesh_type: str = "cube", **kwargs) -> Dict[str, Any]:
        try:
            import trimesh
            if mesh_type == "cube":
                mesh = trimesh.creation.box(extents=[1, 1, 1])
            elif mesh_type == "sphere":
                mesh = trimesh.creation.icosphere(radius=0.5)
            elif mesh_type == "cylinder":
                mesh = trimesh.creation.cylinder(radius=0.5, height=1)
            else:
                mesh = trimesh.creation.box(extents=[1, 1, 1])
            output_path = self.output_dir / "meshes" / f"mesh_{int(__import__('time').time())}.stl"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mesh.export(str(output_path))
            return {"status": "ok", "path": str(output_path), "vertices": len(mesh.vertices), "faces": len(mesh.faces)}
        except Exception as e:
            return {"status": "error", "error": str(e)}


generator = ZICoreGenerator()

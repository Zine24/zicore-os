"""
ZICORE Hunyuan3D Engine - AI Mesh Generation.
Supports Hunyuan3D Docker service, GPU detection, and trimesh fallback.
"""
import json
import re
import subprocess
import time
import logging
import urllib.request
from pathlib import Path

logger = logging.getLogger("zicore.hunyuan3d")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

HUNYUAN_URL = "http://localhost:8082"


class Hunyuan3DEngine:
    """Mesh generation engine with Hunyuan3D backend and trimesh fallback."""

    def __init__(self):
        self._hunyuan_available = False
        self._trimesh_available = False
        self._gpu_available = False
        self._gpu_info = None
        self._gpu_vram = 0
        self._check_backends()

    def _check_backends(self):
        self._detect_gpu()

        try:
            req = urllib.request.Request(f"{HUNYUAN_URL}/health", method="GET")
            urllib.request.urlopen(req, timeout=2)
            self._hunyuan_available = True
            logger.info("[ZICORE] Hunyuan3D Docker service available")
        except Exception:
            if self._gpu_available and self._gpu_vram >= 4096:
                logger.info(f"[ZICORE] GPU detected: {self._gpu_info} ({self._gpu_vram}MB VRAM)")
                logger.info("[ZICORE] Hunyuan3D Docker not running. Start with: docker-compose up hunyuan3d")
            else:
                logger.info("[ZICORE] No compatible GPU detected. Using trimesh fallback for basic shapes.")

        try:
            import trimesh
            self._trimesh = trimesh
            self._trimesh_available = True
            logger.info("[ZICORE] trimesh available for fallback mesh generation")
        except ImportError:
            logger.warning("[ZICORE] trimesh not installed. Run: pip install trimesh")

    def _detect_gpu(self):
        """Detect NVIDIA GPU and VRAM."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                self._gpu_info = result.stdout.strip()
                match = re.search(r'(\d+)\s*MiB', result.stdout)
                if match:
                    self._gpu_vram = int(match.group(1))
                    self._gpu_available = self._gpu_vram >= 4096
        except Exception:
            pass

    def get_status(self):
        """Get engine status for UI display."""
        return {
            "hunyuan3d": self._hunyuan_available,
            "gpu": self._gpu_available,
            "gpu_info": self._gpu_info,
            "gpu_vram": self._gpu_vram,
            "trimesh": self._trimesh_available,
            "mode": "hunyuan3d" if self._hunyuan_available else "trimesh"
        }

    def generate_from_text(self, prompt: str, seed: int = 42) -> dict:
        if self._hunyuan_available:
            return self._generate_hunyuan(prompt, seed)

        if self._gpu_available and self._gpu_vram >= 4096:
            return {
                "status": "warning",
                "message": f"GPU detected ({self._gpu_info}, {self._gpu_vram}MB) but Hunyuan3D Docker not running.",
                "hint": "Start with: docker-compose up hunyuan3d",
                "fallback": "trimesh"
            }

        return self._generate_trimesh(prompt)

    def generate_from_image(self, image_path: str, seed: int = 42) -> dict:
        if self._hunyuan_available:
            return self._generate_hunyuan_from_image(image_path, seed)
        return {
            "status": "error",
            "error": "Hunyuan3D Docker service required for image-to-3D",
            "hint": "Start with: docker-compose up hunyuan3d"
        }

    def _generate_hunyuan(self, prompt: str, seed: int) -> dict:
        try:
            payload = json.dumps({
                "prompt": prompt,
                "num_inference_steps": 30,
                "guidance_scale": 7.5,
                "seed": seed,
            }).encode()
            req = urllib.request.Request(
                f"{HUNYUAN_URL}/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=300)
            data = json.loads(resp.read())
            mesh_path = data.get("mesh_path", "")
            return {
                "status": "ok",
                "file": mesh_path,
                "engine": "hunyuan3d",
                "prompt": prompt,
                "vertices": data.get("vertices", 0),
                "faces": data.get("faces", 0),
            }
        except Exception as e:
            logger.warning(f"[ZICORE] Hunyuan3D generation failed: {e}, falling back to trimesh")
            return self._generate_trimesh(prompt)

    def _generate_hunyuan_from_image(self, image_path: str, seed: int) -> dict:
        try:
            import base64
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            payload = json.dumps({
                "image": img_b64,
                "num_inference_steps": 30,
                "seed": seed,
            }).encode()
            req = urllib.request.Request(
                f"{HUNYUAN_URL}/generate/image",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=300)
            data = json.loads(resp.read())
            return {"status": "ok", "file": data.get("mesh_path", ""), "engine": "hunyuan3d"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _generate_trimesh(self, prompt: str) -> dict:
        if not self._trimesh_available:
            return self._generate_fallback(prompt)

        tm = self._trimesh
        t_lower = prompt.lower()

        try:
            import numpy as np

            if any(w in t_lower for w in ["rocket", "ship", "vehicle", "nave"]):
                mesh = self._mesh_rocket(tm, np)
            elif any(w in t_lower for w in ["satellite", "sattelite"]):
                mesh = self._mesh_satellite(tm, np)
            elif any(w in t_lower for w in ["station", "habitat", "base"]):
                mesh = self._mesh_station(tm, np)
            elif any(w in t_lower for w in ["drone", "uav"]):
                mesh = self._mesh_drone(tm, np)
            elif any(w in t_lower for w in ["sword", "blade", "knife"]):
                mesh = self._mesh_sword(tm, np)
            elif any(w in t_lower for w in ["helmet", "head"]):
                mesh = self._mesh_helmet(tm, np)
            elif any(w in t_lower for w in ["car", "vehicle"]):
                mesh = self._mesh_car(tm, np)
            elif any(w in t_lower for w in ["sphere", "planet", "ball"]):
                mesh = tm.creation.uv_sphere(radius=1.0, count=[32, 32])
            elif any(w in t_lower for w in ["cube", "box", "block"]):
                mesh = tm.creation.box(extents=[1, 1, 1])
            elif any(w in t_lower for w in ["cylinder", "tube", "pipe"]):
                mesh = tm.creation.cylinder(radius=0.5, height=2.0, sections=32)
            elif any(w in t_lower for w in ["cone", "pyramid"]):
                mesh = tm.creation.cone(radius=0.5, height=1.5, sections=32)
            elif any(w in t_lower for w in ["torus", "ring", "wheel"]):
                mesh = tm.creation.annulus(r_min=0.5, r_max=1.0, height=0.3, sections=48)
            else:
                mesh = tm.creation.icosphere(subdivisions=2, radius=1.0)

            ts = int(time.time())
            stl_path = str(OUTPUT_DIR / f"mesh_{ts}.stl")
            obj_path = str(OUTPUT_DIR / f"mesh_{ts}.obj")
            mesh.export(stl_path)
            try:
                tm.exchange.export.export_mesh(mesh, obj_path)
            except Exception:
                obj_path = ""

            return {
                "status": "ok",
                "file": stl_path,
                "file_obj": obj_path,
                "engine": "trimesh",
                "prompt": prompt,
                "vertices": len(mesh.vertices),
                "faces": len(mesh.faces),
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _mesh_rocket(self, tm, np):
        body = tm.creation.cylinder(radius=0.5, height=4.0, sections=32)
        nose = tm.creation.cone(radius=0.5, height=1.5, sections=32)
        nose.apply_translation([0, 0, 4.75])
        fin1 = tm.creation.box(extents=[1.2, 0.05, 0.8])
        fin1.apply_translation([0, 0, 0.4])
        fin2 = tm.creation.box(extents=[0.05, 1.2, 0.8])
        fin2.apply_translation([0, 0, 0.4])
        return tm.util.concatenate([body, nose, fin1, fin2])

    def _mesh_satellite(self, tm, np):
        body = tm.creation.box(extents=[1, 0.6, 0.6])
        panel1 = tm.creation.box(extents=[2, 0.05, 1])
        panel1.apply_translation([0, 0, 0.8])
        panel2 = tm.creation.box(extents=[2, 0.05, 1])
        panel2.apply_translation([0, 0, -0.8])
        dish = tm.creation.cylinder(radius=0.2, height=0.1, sections=24)
        dish.apply_translation([0.6, 0, 0])
        return tm.util.concatenate([body, panel1, panel2, dish])

    def _mesh_station(self, tm, np):
        ring = tm.creation.annulus(r_min=3, r_max=3.5, height=1, sections=48)
        hub = tm.creation.cylinder(radius=0.8, height=2, sections=32)
        spokes = []
        for i in range(6):
            theta = 2 * np.pi * i / 6
            spoke = tm.creation.box(extents=[3, 0.15, 0.15])
            spoke.apply_translation([1.5 * np.cos(theta), 1.5 * np.sin(theta), 0])
            spoke.apply_transform(tm.transformations.rotation_matrix(theta, [0, 0, 1]))
            spokes.append(spoke)
        return tm.util.concatenate([ring, hub] + spokes)

    def _mesh_drone(self, tm, np):
        body = tm.creation.box(extents=[0.8, 0.8, 0.2])
        parts = [body]
        for i in range(4):
            theta = np.pi / 4 + np.pi * i / 2
            arm = tm.creation.box(extents=[0.6, 0.06, 0.06])
            arm.apply_translation([0.4 * np.cos(theta), 0.4 * np.sin(theta), 0])
            parts.append(arm)
            rotor = tm.creation.cylinder(radius=0.2, height=0.02, sections=24)
            rotor.apply_translation([0.6 * np.cos(theta), 0.6 * np.sin(theta), 0.1])
            parts.append(rotor)
        return tm.util.concatenate(parts)

    def _mesh_sword(self, tm, np):
        blade = tm.creation.box(extents=[0.05, 0.15, 3.0])
        blade.apply_translation([0, 0, 2.0])
        guard = tm.creation.box(extents=[0.5, 0.08, 0.1])
        guard.apply_translation([0, 0, 0.4])
        handle = tm.creation.cylinder(radius=0.04, height=0.6, sections=16)
        handle.apply_translation([0, 0, 0.0])
        pommel = tm.creation.uv_sphere(radius=0.08, count=[16, 16])
        pommel.apply_translation([0, 0, -0.35])
        return tm.util.concatenate([blade, guard, handle, pommel])

    def _mesh_helmet(self, tm, np):
        dome = tm.creation.uv_sphere(radius=1.0, count=[32, 32])
        visor = tm.creation.box(extents=[0.9, 0.1, 0.4])
        visor.apply_translation([0, 0.85, -0.1])
        return tm.util.concatenate([dome, visor])

    def _mesh_car(self, tm, np):
        body = tm.creation.box(extents=[2.0, 0.8, 0.5])
        body.apply_translation([0, 0, 0.4])
        cabin = tm.creation.box(extents=[1.0, 0.7, 0.4])
        cabin.apply_translation([-0.2, 0, 0.85])
        parts = [body, cabin]
        for x, y in [(-0.7, 0.45), (-0.7, -0.45), (0.7, 0.45), (0.7, -0.45)]:
            wheel = tm.creation.cylinder(radius=0.2, height=0.1, sections=16)
            wheel.apply_transform(tm.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
            wheel.apply_translation([x, y, 0.2])
            parts.append(wheel)
        return tm.util.concatenate(parts)

    def _generate_fallback(self, prompt: str) -> dict:
        verts = [[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]]
        faces = [[0,1,2,3],[4,5,6,7],[0,1,5,4],[2,3,7,6],[0,3,7,4],[1,2,6,5]]
        ts = int(time.time())
        path = str(OUTPUT_DIR / f"mesh_{ts}.obj")
        with open(path, 'w') as f:
            f.write(f"# ZICORE mesh: {prompt}\n")
            for v in verts:
                f.write(f"v {v[0]} {v[1]} {v[2]}\n")
            for face in faces:
                f.write("f " + " ".join(str(fi + 1) for fi in face) + "\n")
        return {"status": "ok", "file": path, "engine": "fallback", "prompt": prompt, "vertices": 8, "faces": 6}


hunyuan3d = Hunyuan3DEngine()

"""
3D Engine - Mesh Generation, STL/OBJ Export
Uses: trimesh (if available), pure Python fallback with numpy
"""
import os
import math
import json
import time
import logging
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger("zicore.agent.content3d")

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class Engine3D:
    def __init__(self):
        self._init_trimesh()

    def _init_trimesh(self):
        try:
            import trimesh
            self.trimesh = trimesh
            logger.info("trimesh available for 3D generation")
        except ImportError:
            self.trimesh = None
            logger.warning("trimesh not available, using fallback 3D generator")

    def generate_from_prompt(self, prompt: str) -> dict:
        t = prompt.lower()
        if any(w in t for w in ["rocket", "ship", "vehicle", "nave", "cohete"]):
            return self.generate_rocket(prompt)
        elif any(w in t for w in ["satellite", "sattelite"]):
            return self.generate_satellite(prompt)
        elif any(w in t for w in ["station", "habitat", "base"]):
            return self.generate_station(prompt)
        elif any(w in t for w in ["drone", "uav"]):
            return self.generate_drone(prompt)
        elif any(w in t for w in ["wheel", "gear", "ring"]):
            return self.generate_ring(prompt)
        elif any(w in t for w in ["cube", "box", "block"]):
            return self.generate_box(prompt)
        elif any(w in t for w in ["sphere", "planet", "ball"]):
            return self.generate_sphere(prompt)
        elif any(w in t for w in ["cylinder", "tube", "pipe"]):
            return self.generate_cylinder(prompt)
        else:
            return self.generate_custom(prompt)

    def generate_rocket(self, prompt: str = "") -> dict:
        if self.trimesh:
            return self._trimesh_rocket(prompt)
        return self._fallback_rocket(prompt)

    def _trimesh_rocket(self, prompt: str) -> dict:
        tm = self.trimesh
        import numpy as np

        radius_body = 0.5
        height_body = 4.0
        radius_nose = 0.5
        height_nose = 1.5

        n_segments = 32
        theta = np.linspace(0, 2 * np.pi, n_segments, endpoint=False)

        body_verts = []
        for h in [0, height_body]:
            for t in theta:
                body_verts.append([radius_body * math.cos(t), radius_body * math.sin(t), h])
        body_faces = []
        for i in range(n_segments):
            j = (i + 1) % n_segments
            body_faces.append([i, j, j + n_segments])
            body_faces.append([i, j + n_segments, i + n_segments])

        nose_verts = []
        for t in theta:
            nose_verts.append([radius_nose * math.cos(t), radius_nose * math.sin(t), height_body])
        nose_verts.append([0, 0, height_body + height_nose])
        nose_faces = []
        nose_tip = len(nose_verts) - 1
        for i in range(n_segments):
            j = (i + 1) % n_segments
            nose_faces.append([i, j, nose_tip])

        offset = len(body_verts)
        nose_verts_shifted = nose_verts
        nose_faces_shifted = [[f[0] + offset, f[1] + offset, f[2] + offset] for f in nose_faces]

        all_verts = body_verts + nose_verts_shifted
        all_faces = body_faces + nose_faces_shifted

        mesh = tm.Trimesh(vertices=np.array(all_verts), faces=np.array(all_faces))
        stl_path = str(OUTPUT_DIR / f"rocket_{int(time.time())}.stl")
        mesh.export(stl_path)

        obj_path = str(OUTPUT_DIR / f"rocket_{int(time.time())}.obj")
        tm.exchange.export.export_mesh(mesh, obj_path)

        return {
            "file_stl": stl_path,
            "file_obj": obj_path,
            "vertices": len(all_verts),
            "faces": len(all_faces),
            "prompt": prompt,
            "status": "ok",
            "engine": "trimesh",
        }

    def _fallback_rocket(self, prompt: str) -> dict:
        verts = []
        faces = []
        n = 16

        for i in range(n):
            theta = 2 * math.pi * i / n
            x = 0.5 * math.cos(theta)
            y = 0.5 * math.sin(theta)
            verts.append([x, y, 0])
            verts.append([x, y, 4.0])
            if i < n - 1:
                base = i * 2
                faces.append([base, base + 1, base + 3])
                faces.append([base, base + 3, base + 2])
            else:
                faces.append([i * 2, i * 2 + 1, 1])
                faces.append([i * 2, 1, 0])

        nose_idx = len(verts)
        verts.append([0, 0, 5.5])
        for i in range(n):
            theta1 = 2 * math.pi * i / n
            theta2 = 2 * math.pi * ((i + 1) % n) / n
            v1 = i * 2 + 1
            v2 = ((i + 1) % n) * 2 + 1
            faces.append([v1, v2, nose_idx])

        save_path = str(OUTPUT_DIR / f"rocket_{int(time.time())}.obj")
        with open(save_path, 'w') as f:
            f.write("# ZICore Rocket Model\n")
            for v in verts:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            for face in faces:
                f.write(f"f {face[0]+1} {face[1]+1} {face[2]+1}\n")

        return {
            "file_obj": save_path,
            "vertices": len(verts),
            "faces": len(faces),
            "prompt": prompt,
            "status": "ok",
            "engine": "fallback",
        }

    def generate_satellite(self, prompt: str = "") -> dict:
        if self.trimesh:
            return self._trimesh_satellite(prompt)
        return self._fallback_box(prompt, "satellite")

    def _trimesh_satellite(self, prompt: str) -> dict:
        tm = self.trimesh
        import numpy as np

        body = tm.creation.box(extents=[1, 1, 0.6])
        panel1 = tm.creation.box(extents=[2, 0.05, 1])
        panel1.apply_translation([0, 0, 1.5])
        panel2 = tm.creation.box(extents=[2, 0.05, 1])
        panel2.apply_translation([0, 0, -1.5])

        dish = tm.creation.cylinder(radius=0.3, height=0.1, sections=32)
        dish.apply_translation([0.6, 0, 0])

        mesh = tm.util.concatenate([body, panel1, panel2, dish])

        stl_path = str(OUTPUT_DIR / f"satellite_{int(time.time())}.stl")
        mesh.export(stl_path)

        return {
            "file_stl": stl_path,
            "vertices": len(mesh.vertices),
            "faces": len(mesh.faces),
            "prompt": prompt,
            "status": "ok",
            "engine": "trimesh",
        }

    def generate_station(self, prompt: str = "") -> dict:
        if self.trimesh:
            tm = self.trimesh
            import numpy as np

            ring = tm.creation.annulus(r_min=3, r_max=3.5, height=1.5, sections=48)
            hub = tm.creation.cylinder(radius=0.8, height=3, sections=32)

            spokes = []
            for i in range(6):
                theta = 2 * math.pi * i / 6
                spoke = tm.creation.box(extents=[3, 0.2, 0.2])
                spoke.apply_translation([1.5 * math.cos(theta), 1.5 * math.sin(theta), 0])
                spoke.apply_transform(tm.transformations.rotation_matrix(theta, [0, 0, 1]))
                spokes.append(spoke)

            mesh = tm.util.concatenate([ring, hub] + spokes)

            stl_path = str(OUTPUT_DIR / f"station_{int(time.time())}.stl")
            mesh.export(stl_path)
            return {"file_stl": stl_path, "vertices": len(mesh.vertices), "faces": len(mesh.faces), "status": "ok"}
        return self._fallback_box(prompt, "station")

    def generate_drone(self, prompt: str = "") -> dict:
        if self.trimesh:
            tm = self.trimesh
            import numpy as np

            body = tm.creation.box(extents=[0.8, 0.8, 0.2])
            arms = []
            rotors = []
            for i in range(4):
                theta = math.pi / 4 + math.pi * i / 2
                arm = tm.creation.box(extents=[0.6, 0.08, 0.08])
                arm.apply_translation([0.4 * math.cos(theta), 0.4 * math.sin(theta), 0])
                arms.append(arm)
                rotor = tm.creation.cylinder(radius=0.25, height=0.02, sections=24)
                rotor.apply_translation([0.6 * math.cos(theta), 0.6 * math.sin(theta), 0.1])
                rotors.append(rotor)

            mesh = tm.util.concatenate([body] + arms + rotors)
            stl_path = str(OUTPUT_DIR / f"drone_{int(time.time())}.stl")
            mesh.export(stl_path)
            return {"file_stl": stl_path, "vertices": len(mesh.vertices), "faces": len(mesh.faces), "status": "ok"}
        return self._fallback_box(prompt, "drone")

    def generate_ring(self, prompt: str = "") -> dict:
        if self.trimesh:
            tm = self.trimesh
            mesh = tm.creation.annulus(r_min=0.8, r_max=1.0, height=0.3, sections=48)
            stl_path = str(OUTPUT_DIR / f"ring_{int(time.time())}.stl")
            mesh.export(stl_path)
            return {"file_stl": stl_path, "vertices": len(mesh.vertices), "faces": len(mesh.faces), "status": "ok"}
        return self._fallback_box(prompt, "ring")

    def generate_box(self, prompt: str = "") -> dict:
        return self._fallback_box(prompt, "box")

    def generate_sphere(self, prompt: str = "") -> dict:
        if self.trimesh:
            tm = self.trimesh
            mesh = tm.creation.uv_sphere(radius=1.0, count=[32, 32])
            stl_path = str(OUTPUT_DIR / f"sphere_{int(time.time())}.stl")
            mesh.export(stl_path)
            return {"file_stl": stl_path, "vertices": len(mesh.vertices), "faces": len(mesh.faces), "status": "ok"}
        return self._fallback_box(prompt, "sphere")

    def generate_cylinder(self, prompt: str = "") -> dict:
        if self.trimesh:
            tm = self.trimesh
            mesh = tm.creation.cylinder(radius=0.5, height=2.0, sections=32)
            stl_path = str(OUTPUT_DIR / f"cylinder_{int(time.time())}.stl")
            mesh.export(stl_path)
            return {"file_stl": stl_path, "vertices": len(mesh.vertices), "faces": len(mesh.faces), "status": "ok"}
        return self._fallback_box(prompt, "cylinder")

    def generate_custom(self, prompt: str = "") -> dict:
        if self.trimesh:
            tm = self.trimesh
            mesh = tm.creation.icosphere(subdivisions=2, radius=1.0)
            stl_path = str(OUTPUT_DIR / f"custom_{int(time.time())}.stl")
            mesh.export(stl_path)
            return {"file_stl": stl_path, "vertices": len(mesh.vertices), "faces": len(mesh.faces), "status": "ok"}
        return self._fallback_box(prompt, "custom")

    def _fallback_box(self, prompt: str, shape: str) -> dict:
        verts = [
            [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
            [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1],
        ]
        faces = [
            [0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4],
            [2, 3, 7, 6], [0, 3, 7, 4], [1, 2, 6, 5],
        ]
        save_path = str(OUTPUT_DIR / f"{shape}_{int(time.time())}.obj")
        with open(save_path, 'w') as f:
            f.write(f"# ZICore {shape} model\n")
            for v in verts:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            for face in faces:
                f.write("f " + " ".join(str(fi + 1) for fi in face) + "\n")
        return {"file_obj": save_path, "vertices": len(verts), "faces": len(faces), "status": "ok", "engine": "fallback"}

"""
ZICORE AI 3D Engines — Multi-provider text/image-to-3D generation.
Supports: Tripo3D, Meshy AI, Rodin Gen-1, Shap-E (local), OpenSCAD, CadQuery, Build123d
All providers use REST APIs (no local GPU required) or CPU-based fallback.
"""
import json
import os
import time
import logging
import subprocess
import tempfile
import urllib.request
import urllib.error
import urllib.parse
import pathlib
from pathlib import Path
from typing import Optional

logger = logging.getLogger("zicore.ai3d")

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output" / "3d"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class AI3DEngineResult:
    def __init__(self, success=False, file_path="", engine="", error="",
                 vertices=0, faces=0, metadata=None):
        self.success = success
        self.file_path = file_path
        self.engine = engine
        self.error = error
        self.vertices = vertices
        self.faces = faces
        self.metadata = metadata or {}

    def to_dict(self):
        return {
            "status": "ok" if self.success else "error",
            "file": self.file_path,
            "engine": self.engine,
            "error": self.error,
            "vertices": self.vertices,
            "faces": self.faces,
            "metadata": self.metadata,
        }


class Tripo3DEngine:
    """Tripo3D API — text/image-to-3D (free tier: 300 credits/month)."""

    BASE_URL = "https://api.tripo3d.ai/v2/openapi"

    def __init__(self):
        self.api_key = os.environ.get("TRIPO_API_KEY", "")
        self._available = bool(self.api_key)

    @property
    def name(self):
        return "Tripo3D"

    @property
    def available(self):
        return self._available

    @property
    def capabilities(self):
        return ["text_to_3d", "image_to_3d"]

    @property
    def requires(self):
        return "API Key (free tier: 300 credits/mo)"

    def _request(self, endpoint, data=None, method="POST"):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = json.dumps(data).encode() if data else None
        req = urllib.request.Request(
            f"{self.BASE_URL}/{endpoint}",
            data=payload, headers=headers, method=method,
        )
        resp = urllib.request.urlopen(req, timeout=120)
        return json.loads(resp.read())

    def generate_from_text(self, prompt: str) -> AI3DEngineResult:
        if not self._available:
            return AI3DEngineResult(error="Tripo3D API key not configured")
        try:
            task = self._request("task", {
                "type": "text_to_model",
                "prompt": prompt,
            })
            task_id = task.get("data", {}).get("task_id", "")
            if not task_id:
                return AI3DEngineResult(error="No task_id returned")

            for _ in range(60):
                time.sleep(5)
                status = self._request(f"task/{task_id}", method="GET")
                state = status.get("data", {}).get("status", "")
                if state == "success":
                    output = status.get("data", {}).get("output", {})
                    model_url = output.get("model", "")
                    if model_url:
                        return self._download_model(model_url, prompt)
                    return AI3DEngineResult(error="No model URL in output")
                elif state in ("failed", "cancelled"):
                    return AI3DEngineResult(error=f"Task {state}: {status}")

            return AI3DEngineResult(error="Task timed out after 5 minutes")
        except Exception as e:
            return AI3DEngineResult(error=str(e))

    def generate_from_image(self, image_path: str) -> AI3DEngineResult:
        if not self._available:
            return AI3DEngineResult(error="Tripo3D API key not configured")
        try:
            import base64
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            task = self._request("task", {
                "type": "image_to_model",
                "file": {"type": "jpg", "data": img_b64},
            })
            task_id = task.get("data", {}).get("task_id", "")
            for _ in range(60):
                time.sleep(5)
                status = self._request(f"task/{task_id}", method="GET")
                state = status.get("data", {}).get("status", "")
                if state == "success":
                    output = status.get("data", {}).get("output", {})
                    model_url = output.get("model", "")
                    if model_url:
                        return self._download_model(model_url, "image_to_3d")
                    return AI3DEngineResult(error="No model URL")
                elif state in ("failed", "cancelled"):
                    return AI3DEngineResult(error=f"Task {state}")
            return AI3DEngineResult(error="Task timed out")
        except Exception as e:
            return AI3DEngineResult(error=str(e))

    def _download_model(self, url: str, prompt: str) -> AI3DEngineResult:
        try:
            ts = int(time.time())
            ext = ".glb" if ".glb" in url else ".obj"
            out_path = OUTPUT_DIR / f"tripo_{ts}{ext}"
            urllib.request.urlretrieve(url, str(out_path))
            return AI3DEngineResult(
                success=True, file_path=str(out_path),
                engine="tripo3d", metadata={"prompt": prompt, "source_url": url},
            )
        except Exception as e:
            return AI3DEngineResult(error=f"Download failed: {e}")


class MeshyEngine:
    """Meshy AI API — text/image-to-3D."""

    BASE_URL = "https://api.meshy.ai/openapi/v2"

    def __init__(self):
        self.api_key = os.environ.get("MESHY_API_KEY", "")
        self._available = bool(self.api_key)

    @property
    def name(self):
        return "Meshy AI"

    @property
    def available(self):
        return self._available

    @property
    def capabilities(self):
        return ["text_to_3d", "image_to_3d"]

    @property
    def requires(self):
        return "API Key (free tier available)"

    def _request(self, endpoint, data=None, method="POST"):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = json.dumps(data).encode() if data else None
        req = urllib.request.Request(
            f"{self.BASE_URL}/{endpoint}",
            data=payload, headers=headers, method=method,
        )
        resp = urllib.request.urlopen(req, timeout=120)
        return json.loads(resp.read())

    def generate_from_text(self, prompt: str) -> AI3DEngineResult:
        if not self._available:
            return AI3DEngineResult(error="Meshy API key not configured")
        try:
            task = self._request("text-to-3d", {
                "prompt": prompt,
                "art_style": "realistic",
                "negative_prompt": "low quality, blurry",
            })
            task_id = task.get("result", "")
            if not task_id:
                return AI3DEngineResult(error="No task ID returned")

            for _ in range(60):
                time.sleep(5)
                status = self._request(f"text-to-3d/{task_id}", method="GET")
                state = status.get("status", "")
                if state == "SUCCEEDED":
                    model_url = status.get("model_urls", {}).get("glb", "")
                    if model_url:
                        return self._download_model(model_url, prompt)
                    return AI3DEngineResult(error="No model URL in result")
                elif state in ("FAILED", "EXPIRED"):
                    return AI3DEngineResult(error=f"Task {state}")

            return AI3DEngineResult(error="Task timed out")
        except Exception as e:
            return AI3DEngineResult(error=str(e))

    def generate_from_image(self, image_path: str) -> AI3DEngineResult:
        if not self._available:
            return AI3DEngineResult(error="Meshy API key not configured")
        try:
            import base64
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()
            task = self._request("image-to-3d", {
                "image_url": f"data:image/jpeg;base64,{img_b64}",
            })
            task_id = task.get("result", "")
            for _ in range(60):
                time.sleep(5)
                status = self._request(f"image-to-3d/{task_id}", method="GET")
                state = status.get("status", "")
                if state == "SUCCEEDED":
                    model_url = status.get("model_urls", {}).get("glb", "")
                    if model_url:
                        return self._download_model(model_url, "image_to_3d")
                elif state in ("FAILED", "EXPIRED"):
                    return AI3DEngineResult(error=f"Task {state}")
            return AI3DEngineResult(error="Task timed out")
        except Exception as e:
            return AI3DEngineResult(error=str(e))

    def _download_model(self, url: str, prompt: str) -> AI3DEngineResult:
        try:
            ts = int(time.time())
            out_path = OUTPUT_DIR / f"meshy_{ts}.glb"
            urllib.request.urlretrieve(url, str(out_path))
            return AI3DEngineResult(
                success=True, file_path=str(out_path),
                engine="meshy", metadata={"prompt": prompt},
            )
        except Exception as e:
            return AI3DEngineResult(error=f"Download failed: {e}")


class RodinEngine:
    """Rodin Gen-1 (Deemos) — image-to-3D."""

    BASE_URL = "https://hyper3d.rodin.hyper.com/api/v1"

    def __init__(self):
        self.api_key = os.environ.get("RODIN_API_KEY", "")
        self._available = bool(self.api_key)

    @property
    def name(self):
        return "Rodin Gen-1"

    @property
    def available(self):
        return self._available

    @property
    def capabilities(self):
        return ["image_to_3d"]

    @property
    def requires(self):
        return "API Key (free tier available)"

    def generate_from_image(self, image_path: str) -> AI3DEngineResult:
        if not self._available:
            return AI3DEngineResult(error="Rodin API key not configured")
        try:
            import base64
            with open(image_path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode()

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = json.dumps({
                "image": f"data:image/jpeg;base64,{img_b64}",
            }).encode()
            req = urllib.request.Request(
                f"{self.BASE_URL}/rodin",
                data=payload, headers=headers, method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=120)
            data = json.loads(resp.read())
            task_id = data.get("uuid", "")

            for _ in range(60):
                time.sleep(5)
                status_req = urllib.request.Request(
                    f"{self.BASE_URL}/task/{task_id}",
                    headers=headers, method="GET",
                )
                status_resp = urllib.request.urlopen(status_req, timeout=30)
                status = json.loads(status_resp.read())
                if status.get("status") == "Succeeded":
                    model_url = status.get("model_urls", {}).get("glb", "")
                    if model_url:
                        ts = int(time.time())
                        out_path = OUTPUT_DIR / f"rodin_{ts}.glb"
                        urllib.request.urlretrieve(model_url, str(out_path))
                        return AI3DEngineResult(
                            success=True, file_path=str(out_path),
                            engine="rodin", metadata={"task_id": task_id},
                        )
                elif status.get("status") in ("Failed", "Cancelled"):
                    return AI3DEngineResult(error=f"Task {status['status']}")

            return AI3DEngineResult(error="Task timed out")
        except Exception as e:
            return AI3DEngineResult(error=str(e))

    def generate_from_text(self, prompt: str) -> AI3DEngineResult:
        return AI3DEngineResult(error="Rodin Gen-1 requires an image input (image-to-3d only)")


class OpenSCADEngine:
    """OpenSCAD CLI — parametric CSG modeling."""

    def __init__(self):
        self._available = False
        self._check()

    def _check(self):
        try:
            result = subprocess.run(
                ["openscad", "--version"],
                capture_output=True, text=True, timeout=5,
            )
            self._available = result.returncode == 0
        except Exception:
            self._available = False

    @property
    def name(self):
        return "OpenSCAD"

    @property
    def available(self):
        return self._available

    @property
    def capabilities(self):
        return ["csg_modeling", "parametric", "export_stl"]

    @property
    def requires(self):
        return "OpenSCAD binary on PATH"

    def render(self, script: str, output_format: str = "stl") -> AI3DEngineResult:
        if not self._available:
            return AI3DEngineResult(error="OpenSCAD not installed")
        try:
            ts = int(time.time())
            ext = f".{output_format}"
            scad_path = OUTPUT_DIR / f"openscad_{ts}.scad"
            out_path = OUTPUT_DIR / f"openscad_{ts}{ext}"

            with open(scad_path, "w") as f:
                f.write(script)

            result = subprocess.run(
                ["openscad", "-o", str(out_path), str(scad_path)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return AI3DEngineResult(
                    error=f"OpenSCAD error: {result.stderr[:500]}",
                    metadata={"scad_file": str(scad_path)},
                )

            try:
                import trimesh
                mesh = trimesh.load(str(out_path))
                verts = len(mesh.vertices) if hasattr(mesh, 'vertices') else 0
                faces = len(mesh.faces) if hasattr(mesh, 'faces') else 0
            except Exception:
                verts, faces = 0, 0

            return AI3DEngineResult(
                success=True, file_path=str(out_path),
                engine="openscad", vertices=verts, faces=faces,
                metadata={"scad_file": str(scad_path)},
            )
        except subprocess.TimeoutExpired:
            return AI3DEngineResult(error="OpenSCAD render timed out (30s)")
        except Exception as e:
            return AI3DEngineResult(error=str(e))


class CadQueryEngine:
    """CadQuery — parametric CAD with Python (OpenCASCADE kernel)."""

    def __init__(self):
        self._available = False
        try:
            import cadquery
            self._cadquery = cadquery
            self._available = True
        except ImportError:
            pass

    @property
    def name(self):
        return "CadQuery"

    @property
    def available(self):
        return self._available

    @property
    def capabilities(self):
        return ["parametric_cad", "export_stl", "export_step"]

    @property
    def requires(self):
        return "pip install cadquery"

    def render(self, script: str) -> AI3DEngineResult:
        if not self._available:
            return AI3DEngineResult(error="CadQuery not installed. Run: pip install cadquery")
        try:
            ts = int(time.time())
            stl_path = OUTPUT_DIR / f"cadquery_{ts}.stl"
            step_path = OUTPUT_DIR / f"cadquery_{ts}.step"

            namespace = {"cq": self._cadquery}
            exec(script, namespace)

            result_obj = namespace.get("result")
            if result_obj is None:
                return AI3DEngineResult(error="Script must assign a 'result' variable (e.g., result = cq.Workplane(...))")

            try:
                self._cadquery.exporters.export(result_obj, str(stl_path))
            except Exception:
                stl_path = None

            try:
                self._cadquery.exporters.export(result_obj, str(step_path))
            except Exception:
                step_path = None

            try:
                import trimesh
                mesh = trimesh.load(str(stl_path)) if stl_path and stl_path.exists() else None
                verts = len(mesh.vertices) if mesh else 0
                faces = len(mesh.faces) if mesh else 0
            except Exception:
                verts, faces = 0, 0

            final_path = str(stl_path) if stl_path and stl_path.exists() else (
                str(step_path) if step_path and step_path.exists() else ""
            )

            return AI3DEngineResult(
                success=bool(final_path), file_path=final_path,
                engine="cadquery", vertices=verts, faces=faces,
                metadata={"step": str(step_path) if step_path and step_path.exists() else ""},
            )
        except Exception as e:
            return AI3DEngineResult(error=f"CadQuery error: {e}")


class Build123dEngine:
    """Build123d — modern parametric CAD (successor to CadQuery)."""

    def __init__(self):
        self._available = False
        try:
            import build123d
            self._build123d = build123d
            self._available = True
        except ImportError:
            pass

    @property
    def name(self):
        return "Build123d"

    @property
    def available(self):
        return self._available

    @property
    def capabilities(self):
        return ["parametric_cad", "export_stl", "export_step"]

    @property
    def requires(self):
        return "pip install build123d"

    def render(self, script: str) -> AI3DEngineResult:
        if not self._available:
            return AI3DEngineResult(error="Build123d not installed. Run: pip install build123d")
        try:
            ts = int(time.time())
            stl_path = OUTPUT_DIR / f"build123d_{ts}.stl"

            namespace = {"b123d": self._build123d}
            exec(script, namespace)

            result_obj = namespace.get("result")
            if result_obj is None:
                return AI3DEngineResult(error="Script must assign a 'result' variable")

            try:
                from build123d import export_stl
                export_stl(result_obj, str(stl_path))
            except Exception:
                try:
                    from build123d import exporters
                    exporters.export(result_obj, str(stl_path))
                except Exception as e:
                    return AI3DEngineResult(error=f"Export failed: {e}")

            try:
                import trimesh
                mesh = trimesh.load(str(stl_path))
                verts = len(mesh.vertices)
                faces = len(mesh.faces)
            except Exception:
                verts, faces = 0, 0

            return AI3DEngineResult(
                success=True, file_path=str(stl_path),
                engine="build123d", vertices=verts, faces=faces,
            )
        except Exception as e:
            return AI3DEngineResult(error=f"Build123d error: {e}")


class SolidPython2Engine:
    """SolidPython2 — Python bindings for OpenSCAD."""

    def __init__(self):
        self._available = False
        try:
            import solid2 as solid
            self._solid = solid
            self._available = True
        except ImportError:
            pass

    @property
    def name(self):
        return "SolidPython2"

    @property
    def available(self):
        return self._available

    @property
    def capabilities(self):
        return ["python_to_openscad", "csg_modeling"]

    @property
    def requires(self):
        return "pip install solidpython2 + openscad"

    def render(self, script: str) -> AI3DEngineResult:
        if not self._available:
            return AI3DEngineResult(error="SolidPython2 not installed. Run: pip install solidpython2")
        try:
            ts = int(time.time())
            scad_path = OUTPUT_DIR / f"solidpython_{ts}.scad"
            stl_path = OUTPUT_DIR / f"solidpython_{ts}.stl"

            namespace = {"solid": self._solid}
            exec(script, namespace)

            scad_code = str(namespace.get("scad_code", ""))
            if not scad_code:
                return AI3DEngineResult(error="Script must produce a 'scad_code' variable")

            with open(scad_path, "w") as f:
                f.write(scad_code)

            result = subprocess.run(
                ["openscad", "-o", str(stl_path), str(scad_path)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                return AI3DEngineResult(error=f"OpenSCAD render failed: {result.stderr[:300]}")

            return AI3DEngineResult(
                success=True, file_path=str(stl_path),
                engine="solidpython2",
            )
        except Exception as e:
            return AI3DEngineResult(error=str(e))


class ShapEEngine:
    """Shap-E — text-to-3D. Uses the real OpenAI Shap-E model when torch is
    available (zicore-68 node), otherwise falls back to procedural trimesh."""

    def __init__(self):
        self._trimesh_available = False
        self._shap_e_available = False
        self._shap_e_models = None
        self._try_import_trimesh()
        self._try_import_shap_e()

    def _try_import_trimesh(self):
        try:
            import trimesh
            self._trimesh = trimesh
            self._trimesh_available = True
        except ImportError:
            pass

    def _try_import_shap_e(self):
        try:
            import torch
            import shap_e  # noqa: F401
            self._torch = torch
            self._shap_e_available = True
        except Exception:
            pass

    @property
    def name(self):
        return "Shap-E"

    @property
    def available(self):
        return self._shap_e_available or self._trimesh_available

    @property
    def capabilities(self):
        return ["text_to_3d"]

    @property
    def requires(self):
        return "torch + shap-e (full model); trimesh (procedural fallback)"

    def generate_from_text(self, prompt: str) -> AI3DEngineResult:
        if self._shap_e_available:
            result = self._generate_real_shap_e(prompt)
            if result.success:
                return result
        if not self._trimesh_available:
            return AI3DEngineResult(error="Shap-E requires torch+shap-e or trimesh")
        try:
            ts = int(time.time())
            mesh = self._shape_from_prompt(prompt)
            stl_path = OUTPUT_DIR / f"shap_e_{ts}.stl"
            obj_path = OUTPUT_DIR / f"shap_e_{ts}.obj"
            stl_path.parent.mkdir(parents=True, exist_ok=True)
            mesh.export(str(stl_path))
            mesh.export(str(obj_path))
            return AI3DEngineResult(
                success=True, file_path=str(stl_path),
                engine="shap_e", vertices=len(mesh.vertices),
                faces=len(mesh.faces),
                metadata={"prompt": prompt, "obj_path": str(obj_path)},
            )
        except Exception as e:
            return AI3DEngineResult(error=str(e))

    def _generate_real_shap_e(self, prompt: str) -> AI3DEngineResult:
        try:
            ts = int(time.time())
            if self._shap_e_models is None:
                from shap_e.models.download import load_model
                from shap_e.diffusion.sample import sample_latents
                from shap_e.diffusion.gaussian_diffusion import diffusion_from_config
                device = "cuda" if self._torch.cuda.is_available() else "cpu"
                xm = load_model("text300M", device=device)
                diffusion = diffusion_from_config(xm.config, device=device)
                self._shap_e_models = (xm, diffusion, sample_latents, device)
            xm, diffusion, sample_latents, device = self._shap_e_models
            latents = sample_latents(
                batch_size=1,
                model=xm,
                diffusion=diffusion,
                guidance_scale=3.0,
                model_kwargs={"texts": [prompt]},
                progress=False,
                clip_denoised=True,
                use_fp16=False,
                use_karras=True,
                karras_steps=64,
                sigma_min=1e-3,
                sigma_max=160,
                s_churn=0,
            )
            from shap_e.util.notebooks import decode_latent_mesh
            from shap_e.util import trimesh_utils
            mesh_obj = decode_latent_mesh(xm, latents[0])
            with mesh_obj.tri_mesh() as tri:
                tri.export(f"/tmp/shap_e_{ts}.ply")
            stl_path = OUTPUT_DIR / f"shap_e_{ts}.stl"
            obj_path = OUTPUT_DIR / f"shap_e_{ts}.obj"
            stl_path.parent.mkdir(parents=True, exist_ok=True)
            tm = self._trimesh
            m = tm.load(f"/tmp/shap_e_{ts}.ply")
            m.export(str(stl_path))
            m.export(str(obj_path))
            return AI3DEngineResult(
                success=True, file_path=str(stl_path),
                engine="shap_e_model", vertices=len(m.vertices),
                faces=len(m.faces),
                metadata={"prompt": prompt, "obj_path": str(obj_path), "model": "text300M"},
            )
        except Exception as e:
            return AI3DEngineResult(error=f"shap-e model: {e}")

    def _shape_from_prompt(self, prompt: str):
        """Match prompt keywords to a high-quality procedural shape with smoothing."""
        p = prompt.lower()
        tm = self._trimesh
        if any(w in p for w in ["cube", "box", "block"]):
            mesh = tm.creation.box(extents=(1, 1, 1))
            mesh = mesh.subdivide()
            tm.smoothing.filter_laplacian(mesh, iterations=3)
            return mesh
        elif any(w in p for w in ["sphere", "ball", "round"]):
            mesh = tm.creation.icosphere(subdivisions=4, radius=1)
            tm.smoothing.filter_laplacian(mesh, iterations=2)
            return mesh
        elif any(w in p for w in ["cylinder", "tube", "pipe"]):
            mesh = tm.creation.cylinder(radius=0.5, height=2, sections=48)
            tm.smoothing.filter_laplacian(mesh, iterations=2)
            return mesh
        elif any(w in p for w in ["cone", "nose", "tip"]):
            mesh = tm.creation.cone(radius=0.5, height=2, sections=48)
            tm.smoothing.filter_laplacian(mesh, iterations=2)
            return mesh
        elif any(w in p for w in ["capsule", "fuselage"]):
            mesh = tm.creation.capsule(radius=0.4, height=1.5, sections=48)
            tm.smoothing.filter_laplacian(mesh, iterations=3)
            return mesh
        elif any(w in p for w in ["rocket", "spaceship", "ship"]):
            body = tm.creation.cylinder(radius=0.5, height=2, sections=48)
            nose = tm.creation.cone(radius=0.5, height=0.8, sections=48)
            nose.apply_translation([0, 0, 1.4])
            mesh = tm.util.concatenate([body, nose])
            tm.smoothing.filter_laplacian(mesh, iterations=2)
            return mesh
        elif any(w in p for w in ["satellite", "antenna", "solar"]):
            body = tm.creation.box(extents=(0.4, 0.4, 0.6))
            panel = tm.creation.box(extents=(1.5, 0.05, 0.3))
            panel.apply_translation([0.95, 0, 0.15])
            mesh = tm.util.concatenate([body, panel])
            mesh = mesh.subdivide()
            return mesh
        elif any(w in p for w in ["toroidal", "torus", "ring"]):
            mesh = tm.creation.torus(radius=0.8, tube=0.3, sections=48)
            return mesh
        mesh = tm.creation.icosphere(subdivisions=3, radius=1)
        tm.smoothing.filter_laplacian(mesh, iterations=2)
        return mesh

class Hunyuan3DAI3DEngine:
    """Hunyuan3D — Local AI 3D generation (Docker service or trimesh fallback)."""

    def __init__(self):
        self._engine = None
        self._try_import()

    def _try_import(self):
        try:
            from zicore.hunyuan3d_engine import Hunyuan3DEngine
            self._engine = Hunyuan3DEngine()
        except Exception:
            pass

    @property
    def name(self):
        return "Hunyuan3D"

    @property
    def available(self):
        return True  # Always available via trimesh fallback

    @property
    def capabilities(self):
        return ["text_to_3d", "image_to_3d"]

    @property
    def requires(self):
        return "Docker for full Hunyuan3D; trimesh always available as fallback"

    def generate_from_text(self, prompt: str) -> AI3DEngineResult:
        if self._engine:
            result = self._engine.generate_from_text(prompt)
            file_path = result.get("file_stl") or result.get("path", "")
            if file_path:
                return AI3DEngineResult(
                    success=True, file_path=file_path, engine="hunyuan3d",
                    metadata={"prompt": prompt},
                )
        return self._trimesh_fallback(prompt)

    def generate_from_image(self, image_path: str) -> AI3DEngineResult:
        if self._engine:
            result = self._engine.generate_from_image(image_path)
            file_path = result.get("file_stl") or result.get("path", "")
            if file_path:
                return AI3DEngineResult(
                    success=True, file_path=file_path, engine="hunyuan3d",
                )
        return AI3DEngineResult(error="Hunyuan3D image-to-3D requires Docker service")

    def _trimesh_fallback(self, prompt: str) -> AI3DEngineResult:
        try:
            import trimesh
            ts = int(time.time())
            mesh = trimesh.creation.icosphere(subdivisions=2, radius=1)
            stl_path = OUTPUT_DIR / f"hunyuan_{ts}.stl"
            stl_path.parent.mkdir(parents=True, exist_ok=True)
            mesh.export(str(stl_path))
            return AI3DEngineResult(
                success=True, file_path=str(stl_path),
                engine="hunyuan3d_fallback", vertices=len(mesh.vertices),
                faces=len(mesh.faces), metadata={"prompt": prompt},
            )
        except Exception as e:
            return AI3DEngineResult(error=str(e))


class RemoteAI3DEngine:
    """Shap-E delegated to the zicore-68 worker (real torch/text-to-3D),
    with the local trimesh procedural fallback if the worker is unreachable."""

    WORKER_URL = os.environ.get("ZICORE_AI3D_WORKER", "http://192.168.1.68:8200")

    def __init__(self):
        self._fallback = ShapEEngine()
        self._remote_ok = None

    def _check_remote(self):
        if self._remote_ok is not None:
            return self._remote_ok
        try:
            req = urllib.request.Request(f"{self.WORKER_URL}/api/ai3d/health", method="GET")
            with urllib.request.urlopen(req, timeout=4) as r:
                data = json.loads(r.read().decode())
            self._remote_ok = data.get("status") == "ok"
        except Exception:
            self._remote_ok = False
        return self._remote_ok

    @property
    def name(self):
        return "Shap-E (zicore-68)"

    @property
    def available(self):
        return self._check_remote() or self._fallback.available

    @property
    def capabilities(self):
        return ["text_to_3d", "image_to_3d"]

    @property
    def requires(self):
        return "Worker on zicore-68 (torch + shap-e) or local trimesh fallback"

    def _fetch_remote_file(self, remote_path, res):
        try:
            url = f"{self.WORKER_URL}/api/ai3d/file?path={urllib.parse.quote(remote_path)}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=700) as r:
                content = r.read()
            ts = int(time.time())
            suffix = pathlib.Path(remote_path).suffix or ".stl"
            local_path = OUTPUT_DIR / f"shap_e_remote_{ts}{suffix}"
            local_path.write_bytes(content)
            return AI3DEngineResult(
                success=True, file_path=str(local_path),
                engine="shap_e_remote", vertices=res.get("vertices", 0),
                faces=res.get("faces", 0),
                metadata=dict(res.get("metadata", {}), remote="zicore-68"),
            )
        except Exception as e:
            return AI3DEngineResult(error=f"fetch remote file: {e}")

    def generate_from_text(self, prompt: str) -> AI3DEngineResult:
        if self._check_remote():
            try:
                payload = json.dumps({"engine": "shap_e", "prompt": prompt}).encode()
                req = urllib.request.Request(
                    f"{self.WORKER_URL}/api/ai3d/generate", data=payload,
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with urllib.request.urlopen(req, timeout=700) as r:
                    res = json.loads(r.read().decode())
                if res.get("status") == "ok":
                    return self._fetch_remote_file(res.get("file", ""), res)
                if res.get("error"):
                    return self._fallback.generate_from_text(prompt)
            except Exception:
                self._remote_ok = None
                pass
        return self._fallback.generate_from_text(prompt)

    def generate_from_image(self, image_path: str) -> AI3DEngineResult:
        if self._check_remote():
            try:
                with open(image_path, "rb") as fp:
                    b64 = base64.b64encode(fp.read()).decode()
                header = "data:image/jpeg;base64," if str(image_path).lower().endswith((".jpg", ".jpeg")) else "data:image/png;base64,"
                payload = json.dumps({"engine": "shap_e", "image": header + b64}).encode()
                req = urllib.request.Request(
                    f"{self.WORKER_URL}/api/ai3d/generate", data=payload,
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with urllib.request.urlopen(req, timeout=700) as r:
                    res = json.loads(r.read().decode())
                if res.get("status") == "ok":
                    return self._fetch_remote_file(res.get("file", ""), res)
            except Exception:
                pass
        return AI3DEngineResult(error="Shap-E image-to-3D requires the zicore-68 worker")


class AI3DEngineManager:
    """Unified manager for all AI 3D engines."""

    def __init__(self):
        self.engines = {}
        self._register("tripo3d", Tripo3DEngine())
        self._register("meshy", MeshyEngine())
        self._register("rodin", RodinEngine())
        self._register("openscad", OpenSCADEngine())
        self._register("cadquery", CadQueryEngine())
        self._register("build123d", Build123dEngine())
        self._register("solidpython2", SolidPython2Engine())
        self._register("shap_e", RemoteAI3DEngine())
        self._register("hunyuan3d", Hunyuan3DAI3DEngine())
        logger.info(f"[AI3D] Registered {len(self.engines)} engines: {list(self.engines.keys())}")

    def _register(self, key: str, engine):
        self.engines[key] = engine

    def get_engine(self, key: str):
        return self.engines.get(key)

    def list_engines(self) -> list:
        result = []
        for key, engine in self.engines.items():
            result.append({
                "key": key,
                "name": engine.name,
                "available": engine.available,
                "capabilities": engine.capabilities,
                "requires": engine.requires,
            })
        return result

    def list_available(self) -> list:
        return [e for e in self.list_engines() if e["available"]]

    def generate(self, engine_key: str, prompt: str = "", image_path: str = "",
                 script: str = "", **kwargs) -> AI3DEngineResult:
        engine = self.engines.get(engine_key)
        if not engine:
            return AI3DEngineResult(error=f"Unknown engine: {engine_key}")

        if engine_key in ("openscad", "cadquery", "build123d", "solidpython2"):
            return engine.render(script)

        if image_path and hasattr(engine, "generate_from_image"):
            return engine.generate_from_image(image_path)

        if prompt and hasattr(engine, "generate_from_text"):
            return engine.generate_from_text(prompt)

        return AI3DEngineResult(
            error=f"Engine {engine_key} requires {'image_path' if image_path else 'prompt'}"
        )


ai3d = AI3DEngineManager()

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
            import solid
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

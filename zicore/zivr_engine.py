"""
ZICORE ZiVR Engine — Real-world + Generated 3D world backend.
Google Maps 3D, Tripo3D, Stability AI, Polyhaven HDRI, OpenTopography.
"""
import json
import os
import time
import logging
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger("zicore.zivr")

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "data" / "config" / "zio_config.json"
OUTPUT_DIR = ROOT / "output" / "zivr"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = OUTPUT_DIR / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def _load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f).get("zivr", {})
    except Exception:
        return {}


class ZiVRConfig:
    def __init__(self):
        cfg = _load_config()
        self.google_maps_key = cfg.get("google_maps_key", "")
        self.tripo_key = cfg.get("tripo_key", "")
        self.stability_key = cfg.get("stability_key", "")
        self.polyhaven_base = cfg.get("polyhaven_base", "https://api.polyhaven.com")
        self.opentopography_key = cfg.get("opentopography_key", "")
        self.default_location = cfg.get("default_location", {
            "lat": 19.4326, "lng": -99.1332, "name": "Zocalo, CDMX, Mexico"
        })
        self.world_presets = cfg.get("world_presets", {})

    def to_dict(self):
        return {
            "google_maps_key": self.google_maps_key,
            "default_location": self.default_location,
            "world_presets": self.world_presets,
            "has_tripo": bool(self.tripo_key),
            "has_stability": bool(self.stability_key),
            "has_opentopography": bool(self.opentopography_key),
        }


class TripoAssetGenerator:
    """Generate 3D assets via Tripo3D API."""

    BASE_URL = "https://api.tripo3d.ai/v2/openapi"

    def __init__(self, api_key: str):
        self.api_key = api_key

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

    def generate_from_text(self, prompt: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "Tripo3D API key not configured"}
        try:
            task = self._request("task", {"type": "text_to_model", "prompt": prompt})
            task_id = task.get("data", {}).get("task_id", "")
            if not task_id:
                return {"error": "No task_id returned"}

            for _ in range(60):
                time.sleep(5)
                status = self._request(f"task/{task_id}", method="GET")
                state = status.get("data", {}).get("status", "")
                if state == "success":
                    output = status.get("data", {}).get("output", {})
                    model_url = output.get("model", "")
                    if model_url:
                        return self._download(model_url, prompt)
                    return {"error": "No model URL in output"}
                elif state in ("failed", "cancelled"):
                    return {"error": f"Task {state}"}
            return {"error": "Task timed out (5 min)"}
        except Exception as e:
            return {"error": str(e)}

    def generate_from_image(self, image_data_b64: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "Tripo3D API key not configured"}
        try:
            task = self._request("task", {
                "type": "image_to_model",
                "file": {"type": "jpg", "data": image_data_b64},
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
                        return self._download(model_url, "image_to_3d")
                    return {"error": "No model URL"}
                elif state in ("failed", "cancelled"):
                    return {"error": f"Task {state}"}
            return {"error": "Task timed out"}
        except Exception as e:
            return {"error": str(e)}

    def _download(self, url: str, label: str) -> Dict[str, Any]:
        try:
            ts = int(time.time())
            ext = ".glb" if ".glb" in url else ".obj"
            out_path = ASSETS_DIR / f"tripo_{ts}{ext}"
            urllib.request.urlretrieve(url, str(out_path))
            return {
                "status": "ok",
                "file": f"/output/zivr/assets/tripo_{ts}{ext}",
                "engine": "tripo3d",
                "prompt": label,
            }
        except Exception as e:
            return {"error": f"Download failed: {e}"}


class StabilityTextureGenerator:
    """Generate textures/skyboxes via Stability AI."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate_texture(self, prompt: str, style: str = "photographic") -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "Stability AI API key not configured"}
        try:
            import base64
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "image/*",
            }
            data = urllib.parse.urlencode({
                "text_prompts[0][text]": prompt,
                "text_prompts[0][weight]": 1,
                "cfg_scale": 7,
                "height": 1024,
                "width": 1024,
                "samples": 1,
                "style_preset": style,
            }).encode()
            req = urllib.request.Request(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                data=data, headers=headers, method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=60)
            result = json.loads(resp.read())
            artifacts = result.get("artifacts", [])
            if artifacts:
                img_b64 = artifacts[0].get("base64", "")
                if img_b64:
                    ts = int(time.time())
                    out_path = ASSETS_DIR / f"texture_{ts}.png"
                    with open(out_path, "wb") as f:
                        f.write(base64.b64decode(img_b64))
                    return {
                        "status": "ok",
                        "file": f"/output/zivr/assets/texture_{ts}.png",
                        "engine": "stability",
                    }
            return {"error": "No artifacts returned"}
        except Exception as e:
            return {"error": str(e)}


class PolyhavenHDRI:
    """Fetch HDRI environment maps from Polyhaven (free, CC0)."""

    def __init__(self, base_url: str = "https://api.polyhaven.com"):
        self.base_url = base_url

    def list_hdris(self, category: str = "sky") -> List[Dict]:
        try:
            req = urllib.request.Request(
                f"{self.base_url}/hdris?t={category}",
                headers={"Accept": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read())
            results = []
            for name, info in list(data.items())[:20]:
                results.append({
                    "name": name,
                    "category": info.get("category", ""),
                    "colors": info.get("colours", []),
                })
            return results
        except Exception:
            return []

    def get_hdri_url(self, name: str, resolution: int = 2048) -> str:
        return f"https://dl.polyhaven.org/file/ph-assets/HDRIs/hdr/{resolution}/{name}_{resolution}.hdr"

    def get_terrain_url(self, name: str) -> Dict[str, str]:
        return {
            "diffuse": f"https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/{name}_2k.jpg",
            "normal": f"https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/{name}_2k_normal.jpg",
            "roughness": f"https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/{name}_2k_roughness.jpg",
        }


class OpenTopographyTerrain:
    """Fetch real terrain DEM data from OpenTopography."""

    BASE_URL = "https://portal.opentopography.org/API/globaldem"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_terrain(self, lat: float, lng: float, radius_km: float = 5) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "OpenTopography API key not configured"}
        try:
            half = radius_km / 111.0
            params = {
                "demtype": "SRTMGL1",
                "south": str(lat - half),
                "north": str(lat + half),
                "west": str(lng - half),
                "east": str(lng + half),
                "outputFormat": "GTiff",
                "API_Key": self.api_key,
            }
            url = f"{self.BASE_URL}?{urllib.parse.urlencode(params)}"
            ts = int(time.time())
            out_path = ASSETS_DIR / f"terrain_{ts}.tif"
            urllib.request.urlretrieve(url, str(out_path))
            return {
                "status": "ok",
                "file": f"/output/zivr/assets/terrain_{ts}.tif",
                "bounds": {
                    "south": lat - half, "north": lat + half,
                    "west": lng - half, "east": lng + half,
                },
            }
        except Exception as e:
            return {"error": str(e)}


class WorldBuilder:
    """Build world configs from natural language prompts."""

    WORLD_KEYWORDS = {
        "space_station": ["space station", "orbital station", "airlock", "space module"],
        "underwater": ["underwater", "abyss", "deep sea", "submarine", "trench", "jellyfish", "hydrothermal"],
        "lunar": ["moon", "lunar", "crater", "mars", "rover", "colony"],
        "medieval": ["medieval", "castle", "kingdom", "knight", "fortress", "sword"],
        "cyberpunk": ["cyberpunk", "neon", "hologram", "dystopia", "synth"],
        "fantasy": ["fantasy", "magic", "floating island", "crystal", "portal", "wizard"],
        "forest": ["forest", "tree", "woods", "jungle", "nature", "glade", "oak", "pine"],
        "ocean": ["ocean", "sea", "water", "beach", "coral", "marine"],
        "city": ["city", "urban", "building", "street", "downtown", "metropolis", "skyscraper"],
    }

    def parse_prompt(self, prompt: str) -> Dict[str, Any]:
        prompt_lower = prompt.lower()
        detected_world = "city"
        found = False
        for world_type, keywords in self.WORLD_KEYWORDS.items():
            for kw in keywords:
                if kw in prompt_lower:
                    detected_world = world_type
                    found = True
                    break
            if found:
                break

        objects = []
        object_keywords = {
            "building": "building", "skyscraper": "building", "house": "building",
            "tree": "tree", "pine": "tree", "oak": "tree",
            "car": "vehicle", "vehicle": "vehicle", "truck": "vehicle",
            "robot": "robot", "drone": "drone",
            "character": "character", "person": "character", "npc": "character",
            "light": "light", "lamp": "light", "neon": "light",
            "crystal": "crystal", "portal": "portal",
        }
        for kw, obj_type in object_keywords.items():
            if kw in prompt_lower and obj_type not in objects:
                objects.append(obj_type)

        return {
            "world_type": detected_world,
            "prompt": prompt,
            "objects": objects,
            "lighting": self._detect_lighting(prompt_lower),
            "audio": self._detect_audio(prompt_lower),
        }

    def _detect_lighting(self, text: str) -> str:
        if any(w in text for w in ["night", "dark", "neon", "cyber"]):
            return "night"
        if any(w in text for w in ["sunset", "dawn", "golden", "orange"]):
            return "sunset"
        if any(w in text for w in ["underwater", "deep", "abyss"]):
            return "underwater"
        if any(w in text for w in ["space", "star", "void"]):
            return "space"
        return "day"

    def _detect_audio(self, text: str) -> str:
        audio_map = {
            "city": "urban", "forest": "nature", "ocean": "waves",
            "space_station": "mechanical", "medieval": "period",
            "cyberpunk": "electronic", "underwater": "muffled",
            "lunar": "silence", "fantasy": "magical",
        }
        for world_type, audio in audio_map.items():
            if any(w in text for w in [world_type.replace("_", " ")]):
                return audio
        return "ambient"


class ZiVREngine:
    """Main ZiVR engine — orchestrates all subsystems."""

    def __init__(self):
        self.config = ZiVRConfig()
        self.tripo = TripoAssetGenerator(self.config.tripo_key)
        self.stability = StabilityTextureGenerator(self.config.stability_key)
        self.hdri = PolyhavenHDRI(self.config.polyhaven_base)
        self.terrain = OpenTopographyTerrain(self.config.opentopography_key)
        self.world_builder = WorldBuilder()

    def get_config(self) -> Dict:
        return self.config.to_dict()

    def generate_asset(self, prompt: str, engine: str = "tripo") -> Dict:
        if engine == "tripo":
            return self.tripo.generate_from_text(prompt)
        elif engine == "stability":
            return self.stability.generate_texture(prompt)
        return {"error": f"Unknown engine: {engine}"}

    def generate_from_image(self, image_b64: str) -> Dict:
        return self.tripo.generate_from_image(image_b64)

    def get_hdri_list(self, category: str = "sky") -> List[Dict]:
        return self.hdri.list_hdris(category)

    def get_hdri_url(self, name: str, resolution: int = 2048) -> str:
        return self.hdri.get_hdri_url(name, resolution)

    def get_terrain_data(self, lat: float, lng: float) -> Dict:
        return self.terrain.get_terrain(lat, lng)

    def build_world(self, prompt: str) -> Dict:
        return self.world_builder.parse_prompt(prompt)

    def list_assets(self) -> List[Dict]:
        assets = []
        for f in sorted(ASSETS_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.suffix in (".glb", ".obj", ".stl", ".png", ".jpg", ".tif"):
                assets.append({
                    "name": f.name,
                    "path": f"/output/zivr/assets/{f.name}",
                    "size": f.stat().st_size,
                    "modified": f.stat().st_mtime,
                })
        return assets[:50]

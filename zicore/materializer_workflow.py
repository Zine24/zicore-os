"""
ZICORE Materializer Workflow System
PROMPT → Intent → Generate → Preview → Materialize → Simulate → Export

The STAR PRODUCT workflow for ZICORE's materialization pipeline.
Transforms natural language prompts into fully simulated, exportable 3D assets.

Author: ZineMotion Foundation — Aerospace Division
Version: 5.0.0
"""

import os
import re
import json
import math
import time
import uuid
import struct
import hashlib
import zipfile
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False

logger = logging.getLogger("zicore.materializer_workflow")

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMP_DIR = PROJECT_ROOT / "data" / "temp"
PREVIEW_DIR = OUTPUT_DIR / "previews"
SIM_DIR = OUTPUT_DIR / "simulations"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
SIM_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class ObjectType(Enum):
    ROCKET = "rocket"
    SATELLITE = "satellite"
    SPACECRAFT = "spacecraft"
    SPACE_STATION = "space_station"
    LANDER = "lander"
    ROVER = "rover"
    DRONE = "drone"
    BRACKET = "bracket"
    GEAR = "gear"
    PIPE = "pipe"
    HABITAT = "habitat"
    ANTENNA = "antenna"
    SOLAR_PANEL = "solar_panel"
    ENGINE_NOZZLE = "engine_nozzle"
    LANDING_LEG = "landing_leg"
    PAYLOAD = "payload"
    TERRAIN = "terrain"
    PROSTHETIC = "prosthetic"
    TOOL = "tool"
    CONTAINER = "container"
    GENERIC = "generic"
    ASSEMBLY = "assembly"


class QualityLevel(Enum):
    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"
    PRODUCTION = "production"
    ULTRA = "ultra"


class ExportFormat(Enum):
    STL = "stl"
    OBJ = "obj"
    GLB = "glb"
    GLTF = "gltf"
    PLY = "ply"
    STEP = "step"
    IGES = "iges"


class SimulationType(Enum):
    STRUCTURAL = "structural"
    THERMAL = "thermal"
    AERODYNAMIC = "aerodynamic"
    MASS_PROPERTIES = "mass_properties"
    ORBITAL = "orbital"
    TRAJECTORY = "trajectory"


class MaterialCategory(Enum):
    METAL = "metal"
    COMPOSITE = "composite"
    POLYMER = "polymer"
    CERAMIC = "ceramic"
    ELASTOMER = "elastomer"


@dataclass
class MaterialProps:
    name: str
    category: MaterialCategory
    density: float  # kg/m³
    yield_strength: float  # MPa
    tensile_strength: float  # MPa
    elastic_modulus: float  # GPa
    thermal_conductivity: float  # W/(m·K)
    specific_heat: float  # J/(kg·K)
    thermal_expansion: float  # µm/(m·K)
    color: Tuple[int, int, int]  # RGB 0-255
    cost_per_kg: float  # USD
    is_conductive: bool = True
    max_temp: float = 500.0  # °C
    poisson_ratio: float = 0.33

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category.value,
            "density": self.density,
            "yield_strength": self.yield_strength,
            "tensile_strength": self.tensile_strength,
            "elastic_modulus": self.elastic_modulus,
            "thermal_conductivity": self.thermal_conductivity,
            "specific_heat": self.specific_heat,
            "thermal_expansion": self.thermal_expansion,
            "color": list(self.color),
            "cost_per_kg": self.cost_per_kg,
            "is_conductive": self.is_conductive,
            "max_temp": self.max_temp,
            "poisson_ratio": self.poisson_ratio,
        }


@dataclass
class GenerationRequest:
    object_type: ObjectType = ObjectType.GENERIC
    subtype: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    material: str = "aluminum_6061"
    scale: float = 1.0
    quality: QualityLevel = QualityLevel.STANDARD
    dimensions: Dict[str, float] = field(default_factory=dict)
    color: Optional[Tuple[int, int, int]] = None
    tags: List[str] = field(default_factory=list)
    export_formats: List[ExportFormat] = field(default_factory=lambda: [ExportFormat.STL, ExportFormat.OBJ])
    run_simulation: bool = True
    preview_frames: int = 0
    raw_prompt: str = ""

    def to_dict(self) -> dict:
        return {
            "object_type": self.object_type.value,
            "subtype": self.subtype,
            "params": self.params,
            "material": self.material,
            "scale": self.scale,
            "quality": self.quality.value,
            "dimensions": self.dimensions,
            "color": list(self.color) if self.color else None,
            "tags": self.tags,
            "export_formats": [f.value for f in self.export_formats],
            "run_simulation": self.run_simulation,
            "preview_frames": self.preview_frames,
            "raw_prompt": self.raw_prompt,
        }


@dataclass
class PipelineResult:
    step: str
    success: bool
    data: Any = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "success": self.success,
            "duration": self.duration,
            "metadata": self.metadata,
            "error": self.error,
        }


@dataclass
class SimulationResult:
    sim_type: SimulationType
    success: bool
    results: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    safety_factor: float = 1.0
    duration: float = 0.0

    def to_dict(self) -> dict:
        return {
            "sim_type": self.sim_type.value,
            "success": self.success,
            "results": self.results,
            "warnings": self.warnings,
            "safety_factor": self.safety_factor,
            "duration": self.duration,
        }


@dataclass
class WorkflowOutput:
    request: GenerationRequest = field(default_factory=GenerationRequest)
    mesh: Any = None  # trimesh.Trimesh
    mesh_files: Dict[str, str] = field(default_factory=dict)
    preview_images: List[str] = field(default_factory=list)
    simulation_results: List[SimulationResult] = field(default_factory=list)
    mass_properties: Dict[str, Any] = field(default_factory=dict)
    pipeline_log: List[PipelineResult] = field(default_factory=list)
    package_path: Optional[str] = None
    job_id: str = ""
    total_duration: float = 0.0

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "request": self.request.to_dict(),
            "mesh_files": self.mesh_files,
            "preview_images": self.preview_images,
            "simulation_results": [s.to_dict() for s in self.simulation_results],
            "mass_properties": self.mass_properties,
            "pipeline_log": [p.to_dict() for p in self.pipeline_log],
            "package_path": self.package_path,
            "total_duration": self.total_duration,
        }


# =============================================================================
# MATERIAL LIBRARY
# =============================================================================

class MaterialLibrary:
    """Pre-defined aerospace and engineering materials database."""

    def __init__(self):
        self._materials: Dict[str, MaterialProps] = {}
        self._init_defaults()

    def _init_defaults(self):
        metals = [
            MaterialProps(
                name="aluminum_6061", category=MaterialCategory.METAL,
                density=2700, yield_strength=276, tensile_strength=310,
                elastic_modulus=68.9, thermal_conductivity=167, specific_heat=896,
                thermal_expansion=23.6, color=(190, 195, 200), cost_per_kg=2.5,
                is_conductive=True, max_temp=300, poisson_ratio=0.33,
            ),
            MaterialProps(
                name="aluminum_7075", category=MaterialCategory.METAL,
                density=2810, yield_strength=503, tensile_strength=572,
                elastic_modulus=71.7, thermal_conductivity=130, specific_heat=960,
                thermal_expansion=23.6, color=(180, 185, 190), cost_per_kg=4.0,
                is_conductive=True, max_temp=250, poisson_ratio=0.33,
            ),
            MaterialProps(
                name="titanium_6al4v", category=MaterialCategory.METAL,
                density=4430, yield_strength=880, tensile_strength=950,
                elastic_modulus=113.8, thermal_conductivity=6.7, specific_heat=526,
                thermal_expansion=8.6, color=(165, 160, 155), cost_per_kg=35.0,
                is_conductive=True, max_temp=400, poisson_ratio=0.34,
            ),
            MaterialProps(
                name="steel_4130", category=MaterialCategory.METAL,
                density=7850, yield_strength=460, tensile_strength=560,
                elastic_modulus=205, thermal_conductivity=42.7, specific_heat=475,
                thermal_expansion=11.2, color=(140, 140, 145), cost_per_kg=1.5,
                is_conductive=True, max_temp=600, poisson_ratio=0.29,
            ),
            MaterialProps(
                name="stainless_steel_304", category=MaterialCategory.METAL,
                density=8000, yield_strength=215, tensile_strength=505,
                elastic_modulus=193, thermal_conductivity=16.2, specific_heat=500,
                thermal_expansion=17.3, color=(175, 175, 180), cost_per_kg=2.0,
                is_conductive=True, max_temp=870, poisson_ratio=0.29,
            ),
            MaterialProps(
                name="copper", category=MaterialCategory.METAL,
                density=8960, yield_strength=70, tensile_strength=220,
                elastic_modulus=117, thermal_conductivity=401, specific_heat=385,
                thermal_expansion=16.5, color=(185, 115, 65), cost_per_kg=8.0,
                is_conductive=True, max_temp=200, poisson_ratio=0.34,
            ),
            MaterialProps(
                name="brass", category=MaterialCategory.METAL,
                density=8500, yield_strength=120, tensile_strength=340,
                elastic_modulus=100, thermal_conductivity=109, specific_heat=380,
                thermal_expansion=18.7, color=(180, 150, 60), cost_per_kg=5.0,
                is_conductive=True, max_temp=200, poisson_ratio=0.34,
            ),
            MaterialProps(
                name="inconel_718", category=MaterialCategory.METAL,
                density=8190, yield_strength=1035, tensile_strength=1240,
                elastic_modulus=205, thermal_conductivity=11.4, specific_heat=435,
                thermal_expansion=13.0, color=(150, 148, 145), cost_per_kg=60.0,
                is_conductive=True, max_temp=700, poisson_ratio=0.29,
            ),
        ]

        composites = [
            MaterialProps(
                name="carbon_fiber_epoxy", category=MaterialCategory.COMPOSITE,
                density=1600, yield_strength=0, tensile_strength=600,
                elastic_modulus=70, thermal_conductivity=5, specific_heat=800,
                thermal_expansion=2.0, color=(30, 30, 35), cost_per_kg=25.0,
                is_conductive=False, max_temp=180, poisson_ratio=0.30,
            ),
            MaterialProps(
                name="fiberglass", category=MaterialCategory.COMPOSITE,
                density=1800, yield_strength=0, tensile_strength=200,
                elastic_modulus=15, thermal_conductivity=0.3, specific_heat=800,
                thermal_expansion=14.0, color=(200, 200, 180), cost_per_kg=5.0,
                is_conductive=False, max_temp=150, poisson_ratio=0.30,
            ),
            MaterialProps(
                name="kevlar", category=MaterialCategory.COMPOSITE,
                density=1440, yield_strength=0, tensile_strength=3600,
                elastic_modulus=131, thermal_conductivity=0.04, specific_heat=1420,
                thermal_expansion=-2.0, color=(210, 190, 50), cost_per_kg=30.0,
                is_conductive=False, max_temp=250, poisson_ratio=0.36,
            ),
        ]

        polymers = [
            MaterialProps(
                name="PLA", category=MaterialCategory.POLYMER,
                density=1240, yield_strength=60, tensile_strength=50,
                elastic_modulus=3.5, thermal_conductivity=0.13, specific_heat=1200,
                thermal_expansion=70.0, color=(220, 220, 220), cost_per_kg=20.0,
                is_conductive=False, max_temp=60, poisson_ratio=0.36,
            ),
            MaterialProps(
                name="PETG", category=MaterialCategory.POLYMER,
                density=1270, yield_strength=50, tensile_strength=53,
                elastic_modulus=2.2, thermal_conductivity=0.22, specific_heat=1000,
                thermal_expansion=65.0, color=(200, 210, 220), cost_per_kg=25.0,
                is_conductive=False, max_temp=70, poisson_ratio=0.38,
            ),
            MaterialProps(
                name="ABS", category=MaterialCategory.POLYMER,
                density=1050, yield_strength=40, tensile_strength=44,
                elastic_modulus=2.3, thermal_conductivity=0.22, specific_heat=1400,
                thermal_expansion=90.0, color=(230, 230, 230), cost_per_kg=18.0,
                is_conductive=False, max_temp=80, poisson_ratio=0.39,
            ),
            MaterialProps(
                name="nylon_PA12", category=MaterialCategory.POLYMER,
                density=1010, yield_strength=45, tensile_strength=48,
                elastic_modulus=1.7, thermal_conductivity=0.25, specific_heat=1700,
                thermal_expansion=80.0, color=(210, 210, 215), cost_per_kg=50.0,
                is_conductive=False, max_temp=90, poisson_ratio=0.40,
            ),
            MaterialProps(
                name="TPU", category=MaterialCategory.ELASTOMER,
                density=1200, yield_strength=25, tensile_strength=35,
                elastic_modulus=0.05, thermal_conductivity=0.20, specific_heat=1500,
                thermal_expansion=120.0, color=(50, 50, 55), cost_per_kg=40.0,
                is_conductive=False, max_temp=80, poisson_ratio=0.48,
            ),
            MaterialProps(
                name="polycarbonate", category=MaterialCategory.POLYMER,
                density=1200, yield_strength=62, tensile_strength=65,
                elastic_modulus=2.4, thermal_conductivity=0.20, specific_heat=1170,
                thermal_expansion=65.0, color=(200, 210, 220), cost_per_kg=30.0,
                is_conductive=False, max_temp=130, poisson_ratio=0.37,
            ),
        ]

        ceramics = [
            MaterialProps(
                name="alumina_Al2O3", category=MaterialCategory.CERAMIC,
                density=3950, yield_strength=2000, tensile_strength=2000,
                elastic_modulus=370, thermal_conductivity=30, specific_heat=880,
                thermal_expansion=7.1, color=(230, 230, 230), cost_per_kg=15.0,
                is_conductive=False, max_temp=1700, poisson_ratio=0.22,
            ),
            MaterialProps(
                name="silicon_carbide", category=MaterialCategory.CERAMIC,
                density=3210, yield_strength=3500, tensile_strength=3500,
                elastic_modulus=450, thermal_conductivity=120, specific_heat=750,
                thermal_expansion=4.0, color=(80, 85, 80), cost_per_kg=50.0,
                is_conductive=False, max_temp=2000, poisson_ratio=0.17,
            ),
        ]

        for mat in metals + composites + polymers + ceramics:
            self._materials[mat.name] = mat

    def get(self, name: str) -> Optional[MaterialProps]:
        return self._materials.get(name)

    def list_names(self) -> List[str]:
        return sorted(self._materials.keys())

    def list_by_category(self, cat: MaterialCategory) -> List[MaterialProps]:
        return [m for m in self._materials.values() if m.category == cat]

    def search(self, query: str) -> List[MaterialProps]:
        q = query.lower().replace(" ", "_")
        return [m for m in self._materials.values() if q in m.name.lower()]

    def recommend(self, purpose: str, min_yield: float = 0,
                  max_density: float = 999999,
                  max_temp: float = 999999) -> List[MaterialProps]:
        p = purpose.lower()
        candidates = list(self._materials.values())
        if min_yield > 0:
            candidates = [m for m in candidates if m.yield_strength >= min_yield]
        if max_density < 999999:
            candidates = [m for m in candidates if m.density <= max_density]
        if max_temp < 999999:
            candidates = [m for m in candidates if m.max_temp >= max_temp]

        if "space" in p or "rocket" in p or "aerospace" in p:
            high_perform = [m for m in candidates
                           if m.category in (MaterialCategory.METAL, MaterialCategory.COMPOSITE)]
            return high_perform or candidates
        if "print" in p or "pla" in p or "3d print" in p:
            return [m for m in candidates if m.category in (MaterialCategory.POLYMER, MaterialCategory.ELASTOMER)] or candidates
        if "ceramic" in p or "heat" in p or "thermal" in p:
            return [m for m in candidates if m.category == MaterialCategory.CERAMIC] or candidates
        return candidates

    def add_custom(self, mat: MaterialProps):
        self._materials[mat.name] = mat

    def all(self) -> Dict[str, MaterialProps]:
        return dict(self._materials)


# =============================================================================
# PROMPT PARSER
# =============================================================================

class PromptParser:
    """Parse natural language prompts into structured GenerationRequest."""

    _OBJECT_KEYWORDS: Dict[ObjectType, List[str]] = {
        ObjectType.ROCKET: [
            "rocket", "missile", "launch vehicle", "lv", "upper stage",
            "first stage", "booster", "fairing", "nose cone", "payload adapter",
        ],
        ObjectType.SATELLITE: [
            "satellite", "sat", "probe", "orbiter", "spacecraft bus",
            "microsat", "nanosat", "cubesat",
        ],
        ObjectType.SPACE_STATION: [
            "space station", "station", "habitat module", "hab module",
            "laboratory module", "connecting node",
        ],
        ObjectType.LANDER: [
            "lander", "moon lander", "mars lander", "touchdown", "descent stage",
            "ascent stage",
        ],
        ObjectType.ROVER: [
            "rover", "surface vehicle", "moon buggy", "mars rover",
            "exploration vehicle",
        ],
        ObjectType.DRONE: [
            "drone", "uav", "unmanned", "quadcopter", "multirotor",
            "autonomous vehicle",
        ],
        ObjectType.BRACKET: [
            "bracket", "mount", "support", "holder", "clamp",
            "fixture", "adapter plate",
        ],
        ObjectType.GEAR: [
            "gear", "cog", "sprocket", "toothed wheel", "transmission",
            "planetary gear",
        ],
        ObjectType.PIPE: [
            "pipe", "tube", "conduit", "duct", "hose", "manifold",
            "exhaust", "nozzle pipe",
        ],
        ObjectType.HABITAT: [
            "habitat", "base", "shelter", "dome", "bunker",
            "outpost", "lunar base", "mars habitat",
        ],
        ObjectType.ANTENNA: [
            "antenna", "dish", "transmitter", "receiver", "radar",
            "communication array",
        ],
        ObjectType.SOLAR_PANEL: [
            "solar panel", "solar array", "photovoltaic", "solar wing",
        ],
        ObjectType.ENGINE_NOZZLE: [
            "nozzle", "engine nozzle", "bell nozzle", "convergent",
            "divergent", "thruster nozzle",
        ],
        ObjectType.LANDING_LEG: [
            "landing leg", "landing gear", "foot pad", "shock absorber",
        ],
        ObjectType.PAYLOAD: [
            "payload", "cargo", "bay", "capsule", "module",
        ],
        ObjectType.TERRAIN: [
            "terrain", "heightmap", "landscape", "mountain", "hills",
            "crater", "mars terrain", "lunar surface",
        ],
        ObjectType.PROSTHETIC: [
            "prosthetic", "implant", "orthotic", "joint", "bone plate",
        ],
        ObjectType.TOOL: [
            "tool", "wrench", "socket", "spanner", "gripper",
            "manipulator", "end effector",
        ],
        ObjectType.CONTAINER: [
            "container", "box", "case", "housing", "enclosure",
            "tank", "fuel tank", "pressure vessel",
        ],
    }

    _MATERIAL_MAP = {
        "aluminum": "aluminum_6061",
        "aluminium": "aluminum_6061",
        "al6061": "aluminum_6061",
        "al 6061": "aluminum_6061",
        "al7075": "aluminum_7075",
        "al 7075": "aluminum_7075",
        "titanium": "titanium_6al4v",
        "ti-6al-4v": "titanium_6al4v",
        "steel": "steel_4130",
        "4130": "steel_4130",
        "stainless": "stainless_steel_304",
        "stainless steel": "stainless_steel_304",
        "304": "stainless_steel_304",
        "copper": "copper",
        "brass": "brass",
        "inconel": "inconel_718",
        "inconel 718": "inconel_718",
        "carbon fiber": "carbon_fiber_epoxy",
        "carbon": "carbon_fiber_epoxy",
        "cf": "carbon_fiber_epoxy",
        "fiberglass": "fiberglass",
        "kevlar": "kevlar",
        "pla": "PLA",
        "petg": "PETG",
        "abs": "ABS",
        "nylon": "nylon_PA12",
        "tpu": "TPU",
        "polycarbonate": "polycarbonate",
        "pc": "polycarbonate",
        "alumina": "alumina_Al2O3",
        "al2o3": "alumina_Al2O3",
        "silicon carbide": "silicon_carbide",
        "sic": "silicon_carbide",
    }

    _UNIT_CONVERT = {
        "mm": 0.001,
        "cm": 0.01,
        "m": 1.0,
        "in": 0.0254,
        "inch": 0.0254,
        "inches": 0.0254,
        "ft": 0.3048,
        "foot": 0.3048,
        "feet": 0.3048,
        "yd": 0.9144,
        "yard": 0.9144,
    }

    _QUALITY_MAP = {
        "draft": QualityLevel.DRAFT,
        "quick": QualityLevel.DRAFT,
        "fast": QualityLevel.DRAFT,
        "low": QualityLevel.DRAFT,
        "standard": QualityLevel.STANDARD,
        "normal": QualityLevel.STANDARD,
        "medium": QualityLevel.STANDARD,
        "high": QualityLevel.HIGH,
        "good": QualityLevel.HIGH,
        "detailed": QualityLevel.HIGH,
        "production": QualityLevel.PRODUCTION,
        "production ready": QualityLevel.PRODUCTION,
        "final": QualityLevel.PRODUCTION,
        "ultra": QualityLevel.ULTRA,
        "maximum": QualityLevel.ULTRA,
        "best": QualityLevel.ULTRA,
    }

    def __init__(self, material_library: Optional[MaterialLibrary] = None):
        self.library = material_library or MaterialLibrary()

    def parse(self, prompt: str) -> GenerationRequest:
        p = prompt.lower().strip()
        req = GenerationRequest(raw_prompt=prompt)

        req.object_type = self._detect_object(p)
        req.subtype = self._extract_subtype(p, req.object_type)
        req.dimensions = self._extract_dimensions(p)
        req.material = self._extract_material(p)
        req.scale = self._extract_scale(p)
        req.quality = self._extract_quality(p)
        req.color = self._extract_color(p)
        req.tags = self._extract_tags(p)
        req.params = self._extract_params(p, req.object_type)

        return req

    def _detect_object(self, p: str) -> ObjectType:
        best = ObjectType.GENERIC
        best_score = 0
        for otype, keywords in self._OBJECT_KEYWORDS.items():
            for kw in keywords:
                if kw in p:
                    score = len(kw)
                    if score > best_score:
                        best_score = score
                        best = otype
        return best

    def _extract_subtype(self, p: str, otype: ObjectType) -> str:
        subs = {
            ObjectType.ROCKET: ["heavy", "light", "reusable", "expendable", "solid", "liquid", "hybrid"],
            ObjectType.SATELLITE: ["communication", "weather", "reconnaissance", "navigation", "science"],
            ObjectType.SPACE_STATION: ["modular", "single", "rotating"],
            ObjectType.LANDER: ["moon", "mars", "europa", "titan", "asteroid"],
            ObjectType.ROVER: ["exploration", "mining", "construction", "science"],
            ObjectType.DRONE: ["recon", "delivery", "agriculture", "swarm"],
            ObjectType.BRACKET: ["structural", "mounting", "pipe", "sensor"],
            ObjectType.GEAR: ["spur", "helical", "bevel", "worm", "planetary"],
            ObjectType.PIPE: ["exhaust", "intake", "coolant", "fuel", "hydraulic"],
            ObjectType.TERRAIN: ["lunar", "mars", "earth", "asteroid", "procedural"],
        }
        for sub in subs.get(otype, []):
            if sub in p:
                return sub
        return ""

    def _extract_dimensions(self, p: str) -> Dict[str, float]:
        dims = {}
        h_patterns = [
            r"(?:height|tall|high|length|long)\s*[:=]?\s*([\d.]+)\s*(mm|cm|m|in|inch|inches|ft|foot|feet)",
            r"([\d.]+)\s*(mm|cm|m|in|inch|inches|ft|foot|feet)\s*(?:tall|high|long)",
            r"(?:size|dimension)\s*[:=]?\s*([\d.]+)\s*(mm|cm|m|in|inch|inches|ft|foot|feet)",
        ]
        for pat in h_patterns:
            m = re.search(pat, p)
            if m:
                val = float(m.group(1))
                unit = m.group(2)
                if unit in self._UNIT_CONVERT:
                    dims["height"] = val * self._UNIT_CONVERT[unit]
                break

        r_patterns = [
            r"(?:radius|r)\s*[:=]?\s*([\d.]+)\s*(mm|cm|m|in|inch|inches|ft)",
            r"(?:diameter|d)\s*[:=]?\s*([\d.]+)\s*(mm|cm|m|in|inch|inches|ft)",
            r"([\d.]+)\s*(mm|cm|m|in|inch|inches|ft)\s*(?:radius|diameter|wide|thick)",
        ]
        for pat in r_patterns:
            m = re.search(pat, p)
            if m:
                val = float(m.group(1))
                unit = m.group(2)
                if unit in self._UNIT_CONVERT:
                    dims["radius"] = val * self._UNIT_CONVERT[unit]
                break

        w_patterns = [
            r"(?:width|wide)\s*[:=]?\s*([\d.]+)\s*(mm|cm|m|in|inch|inches|ft)",
            r"([\d.]+)\s*(mm|cm|m|in|inch|inches|ft)\s*(?:wide)",
        ]
        for pat in w_patterns:
            m = re.search(pat, p)
            if m:
                val = float(m.group(1))
                unit = m.group(2)
                if unit in self._UNIT_CONVERT:
                    dims["width"] = val * self._UNIT_CONVERT[unit]
                break

        if "radius" in dims and "diameter" not in dims:
            dims["diameter"] = dims["radius"] * 2

        if not dims:
            dims["height"] = 1.0
            dims["radius"] = 0.15

        return dims

    def _extract_material(self, p: str) -> str:
        for key, mat_name in sorted(self._MATERIAL_MAP.items(), key=lambda x: -len(x[0])):
            if key in p:
                return mat_name
        return "aluminum_6061"

    def _extract_scale(self, p: str) -> float:
        m = re.search(r"scale\s*[:=]?\s*1\s*:\s*([\d.]+)", p)
        if m:
            return 1.0 / float(m.group(1))
        m = re.search(r"scale\s*[:=]?\s*([\d.]+)", p)
        if m:
            return float(m.group(1))
        if "full scale" in p or "full-size" in p or "real size" in p:
            return 1.0
        if "miniature" in p or "small" in p:
            return 0.1
        if "large" in p or "big" in p:
            return 2.0
        return 1.0

    def _extract_quality(self, p: str) -> QualityLevel:
        for key, level in self._QUALITY_MAP.items():
            if key in p:
                return level
        return QualityLevel.STANDARD

    def _extract_color(self, p: str) -> Optional[Tuple[int, int, int]]:
        color_map = {
            "red": (220, 40, 40),
            "blue": (40, 80, 200),
            "green": (40, 180, 60),
            "yellow": (230, 210, 40),
            "orange": (230, 130, 30),
            "purple": (140, 50, 200),
            "pink": (220, 120, 160),
            "white": (240, 240, 240),
            "black": (30, 30, 30),
            "gray": (140, 140, 140),
            "grey": (140, 140, 140),
            "silver": (192, 192, 192),
            "gold": (220, 180, 50),
            "copper": (185, 115, 65),
            "chrome": (200, 200, 210),
            "matte black": (40, 40, 40),
            "nasa white": (245, 245, 245),
            "space x black": (25, 25, 25),
        }
        for name, rgb in color_map.items():
            if name in p:
                return rgb
        return None

    def _extract_tags(self, p: str) -> List[str]:
        tags = []
        tag_words = [
            "aerospace", "space", "nasa", "spacex", "mars", "moon", "lunar",
            "flight", "launch", "orbital", "deep space", "exploration",
            "military", "defense", "recon", "satellite", "communication",
            "reusable", "experimental", "prototype", "production", "stealth",
            "supersonic", "hypersonic", "subsonic", "vtol", "stol",
        ]
        for t in tag_words:
            if t in p:
                tags.append(t)
        return tags

    def _extract_params(self, p: str, otype: ObjectType) -> Dict[str, Any]:
        params: Dict[str, Any] = {}

        if otype == ObjectType.ROCKET:
            params["stages"] = 1
            for st in ["two-stage", "2-stage", "three-stage", "3-stage"]:
                if st in p:
                    params["stages"] = int(st[0])
                    break
            params["recoverable"] = "recoverable" in p or "reusable" in p
            params["payload_fairing"] = "fairing" in p

        elif otype == ObjectType.SATELLITE:
            params["solar_panels"] = "solar" in p
            params["antenna_type"] = "dish" if "dish" in p else "array" if "array" in p else "patch"
            for size in ["microsat", "nanosat", "cubesat"]:
                if size in p:
                    params["bus_type"] = size
                    break

        elif otype == ObjectType.LANDER:
            params["legs"] = 4
            for n in ["three leg", "3 leg", "tripod"]:
                if n in p:
                    params["legs"] = 3
                    break
            params["descent_stage"] = True
            params["ascent_stage"] = "ascent" in p

        elif otype == ObjectType.ROVER:
            params["wheels"] = 6
            for n in ["four wheel", "4 wheel"]:
                if n in p:
                    params["wheels"] = 4
                    break
            params["arm"] = "arm" in p or "manipulator" in p

        elif otype == ObjectType.BRACKET:
            params["mounting_holes"] = 4
            params["through_holes"] = "through" in p

        elif otype == ObjectType.GEAR:
            m = re.search(r"(\d+)\s*teeth", p)
            params["teeth"] = int(m.group(1)) if m else 24
            params["module"] = 2.0

        elif otype == ObjectType.PIPE:
            params["wall_thickness"] = 0.003
            params["length"] = params.get("length", 0.5)

        elif otype == ObjectType.TERRAIN:
            m = re.search(r"(\d+)\s*x\s*(\d+)", p)
            params["resolution"] = (int(m.group(1)), int(m.group(2))) if m else (256, 256)
            params["octaves"] = 6
            params["persistence"] = 0.5
            params["seed"] = int(time.time()) % 10000

        elif otype == ObjectType.ANTENNA:
            params["gain"] = 30.0
            params["frequency"] = "Ku"

        elif otype == ObjectType.SOLAR_PANEL:
            params["cells"] = 36
            params["efficiency"] = 0.22

        return params


# =============================================================================
# MESH GENERATOR
# =============================================================================

class MeshGenerator:
    """Generate trimesh objects for various aerospace components."""

    def generate(self, req: GenerationRequest) -> Any:
        if not TRIMESH_AVAILABLE:
            return self._fallback_box(req)

        generators = {
            ObjectType.ROCKET: self._rocket,
            ObjectType.SATELLITE: self._satellite,
            ObjectType.SPACE_STATION: self._space_station,
            ObjectType.LANDER: self._lander,
            ObjectType.ROVER: self._rover,
            ObjectType.DRONE: self._drone,
            ObjectType.BRACKET: self._bracket,
            ObjectType.GEAR: self._gear,
            ObjectType.PIPE: self._pipe,
            ObjectType.HABITAT: self._habitat,
            ObjectType.ANTENNA: self._antenna,
            ObjectType.SOLAR_PANEL: self._solar_panel,
            ObjectType.ENGINE_NOZZLE: self._engine_nozzle,
            ObjectType.LANDING_LEG: self._landing_leg,
            ObjectType.PAYLOAD: self._payload,
            ObjectType.TERRAIN: self._terrain,
            ObjectType.CONTAINER: self._container,
            ObjectType.PROSTHETIC: self._prosthetic,
            ObjectType.TOOL: self._tool,
            ObjectType.ASSEMBLY: self._assembly,
        }
        gen = generators.get(req.object_type, self._fallback_box)
        try:
            mesh = gen(req)
            mesh.apply_scale(req.scale)
            return mesh
        except Exception as e:
            logger.warning(f"Generation failed for {req.object_type.value}: {e}")
            return self._fallback_box(req)

    def _fallback_box(self, req: GenerationRequest) -> Any:
        h = req.dimensions.get("height", 1.0)
        r = req.dimensions.get("radius", 0.15)
        w = req.dimensions.get("width", r * 2)
        return trimesh.creation.box(extents=[w, h, w])

    def _rocket(self, req: GenerationRequest) -> Any:
        h = req.dimensions.get("height", 2.0)
        r = req.dimensions.get("radius", 0.15)
        stages = req.params.get("stages", 1)

        hull = trimesh.creation.cylinder(radius=r, height=h * 0.7, sections=32)
        nose_cone = trimesh.creation.cone(radius=r, height=h * 0.2, sections=32)
        nose_cone.apply_translation([0, h * 0.45, 0])

        skirt = trimesh.creation.cylinder(radius=r * 1.08, height=h * 0.1, sections=32)
        skirt.apply_translation([0, -h * 0.35, 0])

        nozzle = trimesh.creation.cone(radius=r * 0.6, height=h * 0.08, sections=24)
        nozzle.apply_translation([0, -h * 0.44, 0])

        fins = []
        for angle in [0, 90, 180, 270]:
            fin = trimesh.creation.box(extents=[r * 0.8, h * 0.12, 0.01])
            t = np.radians(angle)
            fin.apply_translation([np.cos(t) * r * 0.8, -h * 0.35, np.sin(t) * r * 0.8])
            fins.append(fin)

        parts = [hull, nose_cone, skirt, nozzle] + fins
        try:
            mesh = trimesh.util.concatenate(parts)
        except Exception:
            mesh = hull
        return mesh

    def _satellite(self, req: GenerationRequest) -> Any:
        s = req.dimensions.get("radius", 0.3)
        bus = trimesh.creation.box(extents=[s, s * 0.6, s])
        panel_l = trimesh.creation.box(extents=[s * 2.5, 0.02, s * 0.8])
        panel_l.apply_translation([-s * 1.75, 0, 0])
        panel_r = trimesh.creation.box(extents=[s * 2.5, 0.02, s * 0.8])
        panel_r.apply_translation([s * 1.75, 0, 0])
        dish = trimesh.creation.cylinder(radius=s * 0.25, height=0.02, sections=20)
        dish.apply_translation([0, s * 0.4, 0])
        try:
            return trimesh.util.concatenate([bus, panel_l, panel_r, dish])
        except Exception:
            return bus

    def _space_station(self, req: GenerationRequest) -> Any:
        hub_r = req.dimensions.get("radius", 0.5)
        hub = trimesh.creation.cylinder(radius=hub_r, height=hub_r * 3, sections=20)
        modules = []
        for i in range(4):
            mod = trimesh.creation.cylinder(radius=hub_r * 0.4, height=hub_r * 2, sections=12)
            angle = np.radians(90 * i)
            mod.apply_translation([np.cos(angle) * hub_r * 2, 0, np.sin(angle) * hub_r * 2])
            modules.append(mod)
            conn = trimesh.creation.cylinder(radius=hub_r * 0.12, height=hub_r * 2, sections=8)
            conn.apply_translation([np.cos(angle) * hub_r, 0, np.sin(angle) * hub_r])
            modules.append(conn)
        try:
            return trimesh.util.concatenate([hub] + modules)
        except Exception:
            return hub

    def _lander(self, req: GenerationRequest) -> Any:
        s = req.dimensions.get("radius", 0.4)
        body = trimesh.creation.cylinder(radius=s, height=s * 1.5, sections=20)
        top = trimesh.creation.cone(radius=s * 0.6, height=s * 0.4, sections=16)
        top.apply_translation([0, s * 0.95, 0])
        legs = []
        n = req.params.get("legs", 4)
        for i in range(n):
            angle = np.radians(360 * i / n)
            leg = trimesh.creation.cylinder(radius=0.005, height=s * 1.8, sections=6)
            leg.apply_translation([np.cos(angle) * s * 1.2, -s * 0.5, np.sin(angle) * s * 1.2])
            pad = trimesh.creation.cylinder(radius=0.05, height=0.005, sections=8)
            pad.apply_translation([np.cos(angle) * s * 1.2, -s * 1.4, np.sin(angle) * s * 1.2])
            legs.extend([leg, pad])
        try:
            return trimesh.util.concatenate([body, top] + legs)
        except Exception:
            return body

    def _rover(self, req: GenerationRequest) -> Any:
        s = req.dimensions.get("radius", 0.3)
        body = trimesh.creation.box(extents=[s * 1.5, s * 0.5, s])
        wheels = []
        nw = req.params.get("wheels", 6)
        for i in range(nw):
            w = trimesh.creation.cylinder(radius=s * 0.2, height=0.04, sections=12)
            side = -1 if i % 2 == 0 else 1
            fwd = (i // 2 - 0.5) * s * 0.8
            w.apply_translation([fwd, -s * 0.35, side * s * 0.55])
            w.apply_rotation(np.radians(90), axis=[1, 0, 0])
            wheels.append(w)
        if req.params.get("arm"):
            arm = trimesh.creation.cylinder(radius=0.008, height=s * 1.5, sections=6)
            arm.apply_translation([s * 0.3, s * 0.5, 0])
            wheels.append(arm)
        try:
            return trimesh.util.concatenate([body] + wheels)
        except Exception:
            return body

    def _drone(self, req: GenerationRequest) -> Any:
        s = req.dimensions.get("radius", 0.15)
        body = trimesh.creation.cylinder(radius=s * 0.5, height=s * 0.15, sections=16)
        arms = []
        props = []
        for i in range(4):
            angle = np.radians(45 + 90 * i)
            arm = trimesh.creation.cylinder(radius=0.004, height=s, sections=6)
            arm.apply_rotation(np.radians(90), axis=[0, 0, 1])
            arm.apply_translation([np.cos(angle) * s * 0.5, 0.02, np.sin(angle) * s * 0.5])
            prop = trimesh.creation.cylinder(radius=s * 0.35, height=0.003, sections=20)
            prop.apply_translation([np.cos(angle) * s, 0.03, np.sin(angle) * s])
            arms.append(arm)
            props.append(prop)
        try:
            return trimesh.util.concatenate([body] + arms + props)
        except Exception:
            return body

    def _bracket(self, req: GenerationRequest) -> Any:
        h = req.dimensions.get("height", 0.1)
        r = req.dimensions.get("radius", 0.05)
        w = req.dimensions.get("width", r * 2)
        plate = trimesh.creation.box(extents=[w, h, 0.008])
        gusset = trimesh.creation.box(extents=[0.005, h * 0.7, r])
        gusset.apply_translation([w * 0.35, -h * 0.15, r * 0.5])
        gusset2 = trimesh.creation.box(extents=[0.005, h * 0.7, r])
        gusset2.apply_translation([-w * 0.35, -h * 0.15, r * 0.5])
        try:
            return trimesh.util.concatenate([plate, gusset, gusset2])
        except Exception:
            return plate

    def _gear(self, req: GenerationRequest) -> Any:
        r = req.dimensions.get("radius", 0.05)
        teeth = req.params.get("teeth", 24)
        thickness = 0.01
        body = trimesh.creation.cylinder(radius=r * 0.85, height=thickness, sections=24)
        tooth_parts = []
        for i in range(teeth):
            angle = 2 * np.pi * i / teeth
            tooth = trimesh.creation.box(extents=[r * 0.15, thickness * 0.9, 0.008])
            tooth.apply_translation([np.cos(angle) * r, 0, np.sin(angle) * r])
            tooth_parts.append(tooth)
        try:
            return trimesh.util.concatenate([body] + tooth_parts)
        except Exception:
            return body

    def _pipe(self, req: GenerationRequest) -> Any:
        length = req.dimensions.get("height", 0.5)
        r = req.dimensions.get("radius", 0.025)
        wall = req.params.get("wall_thickness", 0.003)
        outer = trimesh.creation.cylinder(radius=r, height=length, sections=16)
        return outer

    def _habitat(self, req: GenerationRequest) -> Any:
        s = req.dimensions.get("radius", 2.0)
        dome = trimesh.creation.Sphere(radius=s, count=[20, 20])
        floor = trimesh.creation.cylinder(radius=s, height=0.1, sections=20)
        floor.apply_translation([0, -s * 0.7, 0])
        entry = trimesh.creation.cylinder(radius=s * 0.2, height=s * 0.5, sections=12)
        entry.apply_rotation(np.radians(90), axis=[0, 0, 1])
        entry.apply_translation([s * 1.1, -s * 0.3, 0])
        try:
            return trimesh.util.concatenate([dome, floor, entry])
        except Exception:
            return dome

    def _antenna(self, req: GenerationRequest) -> Any:
        r = req.dimensions.get("radius", 0.3)
        dish = trimesh.creation.Sphere(radius=r, count=[16, 16])
        m = dish.vertices[:, 1] < 0
        dish.vertices[m, 1] = 0
        feed = trimesh.creation.cylinder(radius=0.005, height=r * 1.2, sections=8)
        feed.apply_translation([0, r * 0.6, 0])
        try:
            return trimesh.util.concatenate([dish, feed])
        except Exception:
            return dish

    def _solar_panel(self, req: GenerationRequest) -> Any:
        w = req.dimensions.get("height", 1.5)
        h = req.dimensions.get("radius", 1.0)
        panel = trimesh.creation.box(extents=[w, 0.015, h])
        cells = []
        for ix in range(4):
            for iz in range(3):
                cell = trimesh.creation.box(extents=[w * 0.22, 0.016, h * 0.28])
                cell.apply_translation([w * (ix - 1.5) * 0.25, 0, h * (iz - 1) * 0.33])
                cells.append(cell)
        try:
            return trimesh.util.concatenate([panel] + cells)
        except Exception:
            return panel

    def _engine_nozzle(self, req: GenerationRequest) -> Any:
        r = req.dimensions.get("radius", 0.15)
        h = req.dimensions.get("height", 0.4)
        bell = trimesh.creation.cone(radius=r, height=h * 0.7, sections=24)
        throat = trimesh.creation.cylinder(radius=r * 0.3, height=h * 0.15, sections=16)
        throat.apply_translation([0, h * 0.42, 0])
        chamber = trimesh.creation.cylinder(radius=r * 0.35, height=h * 0.2, sections=16)
        chamber.apply_translation([0, h * 0.57, 0])
        try:
            return trimesh.util.concatenate([bell, throat, chamber])
        except Exception:
            return bell

    def _landing_leg(self, req: GenerationRequest) -> Any:
        h = req.dimensions.get("height", 0.8)
        leg = trimesh.creation.cylinder(radius=0.015, height=h, sections=8)
        foot = trimesh.creation.cylinder(radius=0.06, height=0.01, sections=12)
        foot.apply_translation([0, -h * 0.5, 0])
        shock = trimesh.creation.cylinder(radius=0.025, height=h * 0.3, sections=8)
        shock.apply_translation([0, h * 0.2, 0])
        try:
            return trimesh.util.concatenate([leg, foot, shock])
        except Exception:
            return leg

    def _payload(self, req: GenerationRequest) -> Any:
        r = req.dimensions.get("radius", 0.5)
        h = req.dimensions.get("height", 1.0)
        body = trimesh.creation.cylinder(radius=r, height=h, sections=20)
        return body

    def _terrain(self, req: GenerationRequest) -> Any:
        res = req.params.get("resolution", (128, 128))
        octaves = req.params.get("octaves", 6)
        persistence = req.params.get("persistence", 0.5)
        seed = req.params.get("seed", 42)

        w, d = res
        hmap = self._perlin_2d(w, d, octaves, persistence, seed)
        x = np.linspace(0, 1, w)
        z = np.linspace(0, 1, d)
        xv, zv = np.meshgrid(x, z, indexing="ij")
        yv = hmap * 0.3
        verts = np.stack([xv.ravel(), yv.ravel(), zv.ravel()], axis=-1)
        faces = []
        for i in range(w - 1):
            for j in range(d - 1):
                idx = i * d + j
                faces.append([idx, idx + 1, idx + d])
                faces.append([idx + 1, idx + d + 1, idx + d])
        return trimesh.Trimesh(vertices=verts, faces=np.array(faces))

    def _perlin_2d(self, w: int, h: int, octaves: int, persistence: float, seed: int) -> np.ndarray:
        rng = np.random.RandomState(seed)
        result = np.zeros((w, h), dtype=np.float64)
        amp = 1.0
        freq = 1.0
        for _ in range(octaves):
            grid_w = max(2, int(w / freq) + 1)
            grid_h = max(2, int(h / freq) + 1)
            grads = rng.randn(grid_w, grid_h)
            ix = np.linspace(0, grid_w - 1, w)
            iy = np.linspace(0, grid_h - 1, h)
            ix_i = ix.astype(int).clip(0, grid_w - 2)
            iy_i = iy.astype(int).clip(0, grid_h - 2)
            ix_f = ix - ix_i
            iy_f = iy - iy_i
            ix_f2 = ix_f * ix_f * (3 - 2 * ix_f)
            iy_f2 = iy_f * iy_f * (3 - 2 * iy_f)
            ix_f2_2d, iy_f2_2d = np.meshgrid(ix_f2, iy_f2, indexing="ij")
            ix_i_2d, iy_i_2d = np.meshgrid(ix_i, iy_i, indexing="ij")
            ix_i1_2d = (ix_i_2d + 1).clip(0, grid_w - 2)
            iy_i1_2d = (iy_i_2d + 1).clip(0, grid_h - 2)
            v00 = grads[ix_i_2d, iy_i_2d]
            v10 = grads[ix_i1_2d, iy_i_2d]
            v01 = grads[ix_i_2d, iy_i1_2d]
            v11 = grads[ix_i1_2d, iy_i1_2d]
            top = v00 + ix_f2_2d * (v10 - v00)
            bot = v01 + ix_f2_2d * (v11 - v01)
            result += amp * (top + iy_f2_2d * (bot - top))
            amp *= persistence
            freq *= 2.0
        mn, mx = result.min(), result.max()
        if mx - mn > 0:
            result = (result - mn) / (mx - mn)
        return result

    def _container(self, req: GenerationRequest) -> Any:
        r = req.dimensions.get("radius", 0.3)
        h = req.dimensions.get("height", 0.5)
        body = trimesh.creation.cylinder(radius=r, height=h, sections=20)
        lid = trimesh.creation.cylinder(radius=r * 1.02, height=h * 0.05, sections=20)
        lid.apply_translation([0, h * 0.525, 0])
        try:
            return trimesh.util.concatenate([body, lid])
        except Exception:
            return body

    def _prosthetic(self, req: GenerationRequest) -> Any:
        s = req.dimensions.get("radius", 0.05)
        h = req.dimensions.get("height", 0.3)
        shaft = trimesh.creation.cylinder(radius=s, height=h, sections=12)
        joint = trimesh.creation.Sphere(radius=s * 1.5, count=[12, 12])
        joint.apply_translation([0, h * 0.5, 0])
        try:
            return trimesh.util.concatenate([shaft, joint])
        except Exception:
            return shaft

    def _tool(self, req: GenerationRequest) -> Any:
        h = req.dimensions.get("height", 0.2)
        r = req.dimensions.get("radius", 0.03)
        handle = trimesh.creation.cylinder(radius=r, height=h, sections=10)
        head = trimesh.creation.box(extents=[h * 0.3, r * 4, r * 4])
        head.apply_translation([0, h * 0.55, 0])
        try:
            return trimesh.util.concatenate([handle, head])
        except Exception:
            return handle

    def _assembly(self, req: GenerationRequest) -> Any:
        parts = []
        for i in range(3):
            part = trimesh.creation.box(extents=[0.1, 0.1, 0.1])
            part.apply_translation([i * 0.12, 0, 0])
            parts.append(part)
        try:
            return trimesh.util.concatenate(parts)
        except Exception:
            return parts[0] if parts else trimesh.creation.box(extents=[1, 1, 1])


# =============================================================================
# PREVIEW ENGINE
# =============================================================================

class PreviewEngine:
    """Generate 2D preview renders of 3D meshes using Pillow."""

    LIGHTING_PRESETS = {
        "studio": {"ambient": 0.3, "diffuse": 0.7, "specular": 0.4, "bg": (240, 240, 245)},
        "outdoor": {"ambient": 0.5, "diffuse": 0.6, "specular": 0.2, "bg": (180, 210, 240)},
        "dramatic": {"ambient": 0.1, "diffuse": 0.9, "specular": 0.6, "bg": (20, 20, 30)},
        "aerospace": {"ambient": 0.2, "diffuse": 0.8, "specular": 0.5, "bg": (10, 12, 20)},
    }

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or PREVIEW_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render_preview(self, mesh: Any, material_name: str = "aluminum_6061",
                       lighting: str = "aerospace",
                       width: int = 800, height: int = 600) -> Optional[str]:
        if not PILLOW_AVAILABLE:
            return None

        preset = self.LIGHTING_PRESETS.get(lighting, self.LIGHTING_PRESETS["aerospace"])
        lib = MaterialLibrary()
        mat = lib.get(material_name)
        base_color = mat.color if mat else (180, 180, 180)

        img = Image.new("RGB", (width, height), preset["bg"])
        draw = ImageDraw.Draw(img)

        try:
            verts, faces = mesh.vertices, mesh.faces
            normals = mesh.face_normals if hasattr(mesh, "face_normals") else None
            if normals is None:
                try:
                    normals = mesh.face_normal
                except Exception:
                    normals = np.zeros((len(faces), 3))
                    normals[:, 1] = 1.0
        except Exception:
            return None

        centroid = verts.mean(axis=0)
        verts = verts - centroid
        scale_f = max(np.ptp(verts, axis=0)) or 1.0
        verts = verts / scale_f

        angle = time.time() % (2 * np.pi)
        cos_a, sin_a = np.cos(angle), np.sin(angle)
        rx = verts[:, 0] * cos_a - verts[:, 2] * sin_a
        ry = verts[:, 1]
        rz = verts[:, 0] * sin_a + verts[:, 2] * cos_a

        cos_b, sin_b = np.cos(0.3), np.sin(0.3)
        ry2 = ry * cos_b - rz * sin_b
        rz2 = ry * sin_b + rz * cos_b

        light_dir = np.array([0.4, 0.8, 0.3])
        light_dir = light_dir / np.linalg.norm(light_dir)

        proj_x = (rx * width * 0.35 + width * 0.5).astype(np.float64)
        proj_y = (-ry2 * height * 0.35 + height * 0.5).astype(np.float64)
        depth = rz2

        face_data = []
        for fi in range(len(faces)):
            face = faces[fi]
            z_avg = depth[face].mean()
            n = normals[fi] if fi < len(normals) else np.array([0, 1, 0])
            n_norm = np.linalg.norm(n)
            if n_norm > 0:
                n = n / n_norm
            dot = max(0, np.dot(n, light_dir))
            brightness = preset["ambient"] + preset["diffuse"] * dot
            brightness = min(1.0, max(0.05, brightness))

            r_c = int(min(255, base_color[0] * brightness))
            g_c = int(min(255, base_color[1] * brightness))
            b_c = int(min(255, base_color[2] * brightness))

            pts = [(int(proj_x[face[i]]), int(proj_y[face[i]])) for i in range(3)]
            if all(0 <= p[0] < width and 0 <= p[1] < height for p in pts):
                face_data.append((z_avg, pts, (r_c, g_c, b_c)))

        face_data.sort(key=lambda x: x[0])

        for _, pts, color in face_data:
            draw.polygon(pts, fill=color, outline=None)

        if self._try_draw_text(draw, width, height, material_name, lighting):
            pass

        path = str(self.output_dir / f"preview_{uuid.uuid4().hex[:8]}.png")
        img.save(path, "PNG")
        return path

    def _try_draw_text(self, draw: ImageDraw.Draw, w: int, h: int,
                       material: str, lighting: str) -> bool:
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except Exception:
            try:
                font = ImageFont.load_default()
            except Exception:
                return False
        draw.text((10, h - 30), f"Material: {material} | Lighting: {lighting}", fill=(200, 200, 200), font=font)
        return True

    def create_turntable(self, mesh: Any, frames: int = 36,
                         material_name: str = "aluminum_6061",
                         width: int = 640, height: int = 480) -> List[str]:
        if not PILLOW_AVAILABLE:
            return []
        paths = []
        lib = MaterialLibrary()
        mat = lib.get(material_name)
        base_color = mat.color if mat else (180, 180, 180)

        try:
            verts, faces = mesh.vertices, mesh.faces
            normals = mesh.face_normals if hasattr(mesh, "face_normals") else None
            if normals is None:
                try:
                    normals = mesh.face_normal
                except Exception:
                    normals = np.zeros((len(faces), 3))
                    normals[:, 1] = 1.0
        except Exception:
            return []

        centroid = verts.mean(axis=0)
        verts = verts - centroid
        scale_f = max(np.ptp(verts, axis=0)) or 1.0
        verts = verts / scale_f

        light_dir = np.array([0.4, 0.8, 0.3])
        light_dir = light_dir / np.linalg.norm(light_dir)

        for fi_frame in range(frames):
            angle = 2 * np.pi * fi_frame / frames
            cos_a, sin_a = np.cos(angle), np.sin(angle)
            rx = verts[:, 0] * cos_a - verts[:, 2] * sin_a
            ry = verts[:, 1]
            rz = verts[:, 0] * sin_a + verts[:, 2] * cos_a

            cos_b, sin_b = np.cos(0.3), np.sin(0.3)
            ry2 = ry * cos_b - rz * sin_b
            rz2 = ry * sin_b + rz * cos_b

            proj_x = (rx * width * 0.35 + width * 0.5)
            proj_y = (-ry2 * height * 0.35 + height * 0.5)
            depth = rz2

            img = Image.new("RGB", (width, height), (10, 12, 20))
            draw = ImageDraw.Draw(img)

            face_data = []
            for fi in range(len(faces)):
                face = faces[fi]
                z_avg = depth[face].mean()
                n = normals[fi] if fi < len(normals) else np.array([0, 1, 0])
                n_norm = np.linalg.norm(n)
                if n_norm > 0:
                    n = n / n_norm
                dot = max(0, np.dot(n, light_dir))
                brightness = 0.2 + 0.8 * dot
                brightness = min(1.0, max(0.05, brightness))
                r_c = int(min(255, base_color[0] * brightness))
                g_c = int(min(255, base_color[1] * brightness))
                b_c = int(min(255, base_color[2] * brightness))
                pts = [(int(proj_x[face[i]]), int(proj_y[face[i]])) for i in range(3)]
                if all(0 <= p[0] < width and 0 <= p[1] < height for p in pts):
                    face_data.append((z_avg, pts, (r_c, g_c, b_c)))

            face_data.sort(key=lambda x: x[0])
            for _, pts, color in face_data:
                draw.polygon(pts, fill=color)

            try:
                font = ImageFont.truetype("arial.ttf", 14)
            except Exception:
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None
            if font:
                draw.text((10, 10), f"Frame {fi_frame + 1}/{frames}", fill=(100, 200, 255), font=font)

            path = str(self.output_dir / f"turntable_{uuid.uuid4().hex[:8]}_{fi_frame:03d}.png")
            img.save(path, "PNG")
            paths.append(path)

        return paths

    def create_cross_section(self, mesh: Any, plane: str = "xz",
                             material_name: str = "aluminum_6061",
                             width: int = 800, height: int = 600) -> Optional[str]:
        if not PILLOW_AVAILABLE:
            return None

        lib = MaterialLibrary()
        mat = lib.get(material_name)
        base_color = mat.color if mat else (180, 180, 180)

        try:
            verts, faces = mesh.vertices, mesh.faces
            centroid = verts.mean(axis=0)
            verts_c = verts - centroid
            scale_f = max(np.ptp(verts_c, axis=0)) or 1.0
            verts_c = verts_c / scale_f

            img = Image.new("RGB", (width, height), (15, 18, 25))
            draw = ImageDraw.Draw(img)

            if plane == "xz":
                proj = verts_c[:, [0, 2]]
                y_vals = verts_c[:, 1]
            elif plane == "xy":
                proj = verts_c[:, [0, 1]]
                y_vals = verts_c[:, 2]
            else:
                proj = verts_c[:, [1, 2]]
                y_vals = verts_c[:, 0]

            px = (proj[:, 0] * width * 0.4 + width * 0.5).astype(np.float64)
            py = (-proj[:, 1] * height * 0.4 + height * 0.5).astype(np.float64)

            for face in faces:
                y_avg = y_vals[face].mean()
                brightness = 0.4 + 0.6 * max(0, min(1, (y_avg + 1) / 2))
                r_c = int(min(255, base_color[0] * brightness))
                g_c = int(min(255, base_color[1] * brightness))
                b_c = int(min(255, base_color[2] * brightness))
                pts = [(int(px[face[i]]), int(py[face[i]])) for i in range(3)]
                if all(0 <= p[0] < width and 0 <= p[1] < height for p in pts):
                    draw.polygon(pts, fill=(r_c, g_c, b_c), outline=(100, 200, 255))

            try:
                font = ImageFont.truetype("arial.ttf", 14)
            except Exception:
                font = None
            if font:
                draw.text((10, 10), f"Cross Section: {plane.upper()}", fill=(100, 200, 255), font=font)

            path = str(self.output_dir / f"crosssection_{uuid.uuid4().hex[:8]}.png")
            img.save(path, "PNG")
            return path
        except Exception as e:
            logger.warning(f"Cross-section failed: {e}")
            return None

    def create_wireframe_overlay(self, mesh: Any, material_name: str = "aluminum_6061",
                                 width: int = 800, height: int = 600) -> Optional[str]:
        if not PILLOW_AVAILABLE:
            return None

        lib = MaterialLibrary()
        mat = lib.get(material_name)
        base_color = mat.color if mat else (180, 180, 180)

        try:
            verts, faces = mesh.vertices, mesh.faces
            centroid = verts.mean(axis=0)
            verts_c = verts - centroid
            scale_f = max(np.ptp(verts_c, axis=0)) or 1.0
            verts_c = verts_c / scale_f

            angle = 0.4
            cos_a, sin_a = np.cos(angle), np.sin(angle)
            rx = verts_c[:, 0] * cos_a - verts_c[:, 2] * sin_a
            ry = verts_c[:, 1]
            rz = verts_c[:, 0] * sin_a + verts_c[:, 2] * cos_a

            proj_x = (rx * width * 0.35 + width * 0.5)
            proj_y = (-ry * height * 0.35 + height * 0.5)

            img = Image.new("RGB", (width, height), (10, 12, 20))
            draw = ImageDraw.Draw(img)

            r_c = int(min(255, base_color[0] * 0.3))
            g_c = int(min(255, base_color[1] * 0.3))
            b_c = int(min(255, base_color[2] * 0.3))
            for face in faces:
                pts = [(int(proj_x[face[i]]), int(proj_y[face[i]])) for i in range(3)]
                if all(0 <= p[0] < width and 0 <= p[1] < height for p in pts):
                    draw.polygon(pts, fill=(r_c, g_c, b_c))

            edges = set()
            for face in faces:
                for i in range(3):
                    e = tuple(sorted((int(face[i]), int(face[(i + 1) % 3]))))
                    edges.add(e)

            for e in edges:
                x1, y1 = int(proj_x[e[0]]), int(proj_y[e[0]])
                x2, y2 = int(proj_x[e[1]]), int(proj_y[e[1]])
                draw.line([(x1, y1), (x2, y2)], fill=(100, 200, 255), width=1)

            path = str(self.output_dir / f"wireframe_{uuid.uuid4().hex[:8]}.png")
            img.save(path, "PNG")
            return path
        except Exception as e:
            logger.warning(f"Wireframe failed: {e}")
            return None

    def create_annotated(self, mesh: Any, material_name: str = "aluminum_6061",
                         width: int = 800, height: int = 600) -> Optional[str]:
        if not PILLOW_AVAILABLE:
            return None

        lib = MaterialLibrary()
        mat = lib.get(material_name)
        base_color = mat.color if mat else (180, 180, 180)

        try:
            verts = mesh.vertices
            extents = verts.max(axis=0) - verts.min(axis=0)
            bbox_min = verts.min(axis=0)

            img = Image.new("RGB", (width, height), (10, 12, 20))
            draw = ImageDraw.Draw(img)

            centroid = verts.mean(axis=0)
            verts_c = verts - centroid
            scale_f = max(np.ptp(verts_c, axis=0)) or 1.0
            verts_c = verts_c / scale_f

            angle = 0.3
            cos_a, sin_a = np.cos(angle), np.sin(angle)
            rx = verts_c[:, 0] * cos_a - verts_c[:, 2] * sin_a
            ry = verts_c[:, 1]
            rz = verts_c[:, 0] * sin_a + verts_c[:, 2] * cos_a

            proj_x = (rx * width * 0.3 + width * 0.5)
            proj_y = (-ry * height * 0.3 + height * 0.5)

            r_c = int(min(255, base_color[0] * 0.6))
            g_c = int(min(255, base_color[1] * 0.6))
            b_c = int(min(255, base_color[2] * 0.6))

            for face in mesh.faces:
                pts = [(int(proj_x[face[i]]), int(proj_y[face[i]])) for i in range(3)]
                if all(0 <= p[0] < width and 0 <= p[1] < height for p in pts):
                    draw.polygon(pts, fill=(r_c, g_c, b_c))

            try:
                font = ImageFont.truetype("arial.ttf", 14)
                font_sm = ImageFont.truetype("arial.ttf", 11)
            except Exception:
                font = None
                font_sm = None

            dims_m = extents
            units = []
            for i, axis in enumerate(["W", "H", "D"]):
                v = dims_m[i]
                if v < 0.01:
                    s = f"{v * 1000:.1f} mm"
                elif v < 1.0:
                    s = f"{v * 100:.1f} cm"
                else:
                    s = f"{v:.2f} m"
                units.append(f"{axis}: {s}")

            cx, cy = int(proj_x.mean()), int(proj_y.mean())
            draw.line([(cx, cy - 20), (cx, cy + 20)], fill=(255, 80, 80), width=2)
            draw.line([(cx - 20, cy), (cx + 20, cy)], fill=(80, 255, 80), width=2)

            if font:
                y_off = 15
                for txt in units:
                    draw.text((width - 150, y_off), txt, fill=(200, 200, 200), font=font)
                    y_off += 20

            path = str(self.output_dir / f"annotated_{uuid.uuid4().hex[:8]}.png")
            img.save(path, "PNG")
            return path
        except Exception as e:
            logger.warning(f"Annotation failed: {e}")
            return None


# =============================================================================
# SIMULATION ENGINE
# =============================================================================

class SimulationEngine:
    """Run physics simulation estimates on meshes and materials."""

    EARTH_MASS = 5.972e24
    EARTH_RADIUS = 6371000
    EARTH_GM = 3.986e14
    MOON_MASS = 7.342e22
    MOON_RADIUS = 1737400
    MOON_GM = 4.9048695e12
    MARS_MASS = 6.417e23
    MARS_RADIUS = 3389500
    MARS_GM = 4.282837e13
    SUN_GM = 1.32712440018e20
    G = 6.674e-11

    def structural_analysis(self, mesh: Any, material: MaterialProps,
                            load: float = 1000.0,
                            load_dir: str = "y") -> SimulationResult:
        t0 = time.time()
        result = SimulationResult(sim_type=SimulationType.STRUCTURAL, success=True)

        try:
            verts = mesh.vertices
            extents = verts.max(axis=0) - verts.min(axis=0)
        except Exception:
            result.success = False
            result.warnings.append("Cannot access mesh geometry")
            return result

        h = float(extents[1]) if load_dir == "y" else float(extents[0])
        w = float(extents[0]) if load_dir == "y" else float(extents[1])
        t = float(extents[2]) if len(extents) > 2 else w * 0.1
        if t < 1e-6:
            t = 0.001

        volume = float(np.prod(extents))
        mass = volume * material.density
        area = w * t
        if area < 1e-12:
            area = 1e-6

        if h < 1e-6:
            h = 0.01

        stress = load / area
        deflection = (load * h ** 3) / (3 * material.elastic_modulus * 1e9 * area * t) if t > 0 else 0
        safety_factor = material.yield_strength / (stress / 1e6) if stress > 0 else 100.0

        if safety_factor < 1.0:
            result.warnings.append(f"YIELD FAILURE PREDICTED — Safety factor: {safety_factor:.2f}")
        elif safety_factor < 2.0:
            result.warnings.append(f"Low safety margin — Factor: {safety_factor:.2f}")

        if deflection > h * 0.01:
            result.warnings.append(f"Excessive deflection: {deflection * 1000:.2f} mm ({deflection / h * 100:.2f}%)")

        result.results = {
            "applied_load_N": load,
            "stress_MPa": stress / 1e6,
            "yield_strength_MPa": material.yield_strength,
            "safety_factor": safety_factor,
            "deflection_m": deflection,
            "deflection_mm": deflection * 1000,
            "mass_kg": mass,
            "volume_m3": volume,
            "cross_section_area_m2": area,
            "member_length_m": h,
            "material": material.name,
            "pass_fail": "PASS" if safety_factor >= 1.0 else "FAIL",
        }
        result.safety_factor = safety_factor
        result.duration = time.time() - t0
        return result

    def thermal_analysis(self, mesh: Any, material: MaterialProps,
                         temp_min: float = -150.0,
                         temp_max: float = 150.0,
                         temp_ref: float = 20.0) -> SimulationResult:
        t0 = time.time()
        result = SimulationResult(sim_type=SimulationType.THERMAL, success=True)

        try:
            extents = mesh.vertices.max(axis=0) - mesh.vertices.min(axis=0)
            volume = float(np.prod(extents))
        except Exception:
            result.success = False
            result.warnings.append("Cannot access mesh geometry")
            return result

        mass = volume * material.density
        delta_t_max = max(abs(temp_max - temp_ref), abs(temp_min - temp_ref))
        thermal_expansion = material.thermal_expansion * 1e-6
        strain = thermal_expansion * delta_t_max
        thermal_stress = strain * material.elastic_modulus * 1e9

        heat_energy = mass * material.specific_heat * delta_t_max
        thermal_time_constant = (mass * material.specific_heat) / (material.thermal_conductivity * max(np.prod(extents[:2]), 1e-6))

        max_safe_delta_t = material.yield_strength / (material.thermal_expansion * 1e-6 * material.elastic_modulus * 1e9) if material.thermal_expansion > 0 else 9999

        warnings = []
        if delta_t_max > max_safe_delta_t:
            warnings.append(f"Thermal stress exceeds yield — delta_T={delta_t_max:.0f}°C vs limit {max_safe_delta_t:.0f}°C")
        if temp_max > material.max_temp:
            warnings.append(f"Temperature {temp_max:.0f}°C exceeds material max {material.max_temp:.0f}°C")
        if temp_min < -200:
            warnings.append(f"Cryogenic temperature {temp_min:.0f}°C — check embrittlement")

        result.results = {
            "temp_min_C": temp_min,
            "temp_max_C": temp_max,
            "temp_ref_C": temp_ref,
            "delta_T_max_C": delta_t_max,
            "thermal_strain": strain,
            "thermal_expansion_um_m": thermal_expansion * 1e6,
            "thermal_stress_MPa": thermal_stress / 1e6,
            "heat_energy_J": heat_energy,
            "thermal_time_constant_s": thermal_time_constant,
            "max_safe_delta_T_C": max_safe_delta_t,
            "thermal_expansion_m": strain * max(float(extents[0]), 0.01),
            "mass_kg": mass,
            "material": material.name,
        }
        result.warnings = warnings
        result.duration = time.time() - t0
        return result

    def aerodynamic_estimate(self, mesh: Any, material: MaterialProps,
                             velocity: float = 300.0,
                             altitude: float = 0.0,
                             frontal_area: Optional[float] = None) -> SimulationResult:
        t0 = time.time()
        result = SimulationResult(sim_type=SimulationType.AERODYNAMIC, success=True)

        try:
            extents = mesh.vertices.max(axis=0) - mesh.vertices.min(axis=0)
            volume = float(np.prod(extents))
        except Exception:
            result.success = False
            result.warnings.append("Cannot access mesh geometry")
            return result

        if frontal_area is None:
            frontal_area = float(extents[0] * extents[2]) if len(extents) > 2 else float(extents[0] ** 2)
        if frontal_area < 1e-8:
            frontal_area = 0.01

        temp = 288.15 - 0.0065 * altitude
        temp = max(temp, 180)
        pressure = 101325 * (temp / 288.15) ** 5.256
        rho = pressure / (287.05 * temp)

        speed_of_sound = 331.3 * math.sqrt(temp / 273.15)
        mach = velocity / speed_of_sound if speed_of_sound > 0 else 0

        if mach < 0.3:
            cd = 0.5
        elif mach < 0.8:
            cd = 0.5 + 0.3 * (mach - 0.3) / 0.5
        elif mach < 1.2:
            cd = 0.8 + 0.5 * (1 - abs(mach - 1.0) / 0.2)
        elif mach < 5.0:
            cd = 0.4 + 0.2 / mach
        else:
            cd = 0.3

        drag = 0.5 * rho * velocity ** 2 * cd * frontal_area
        lift = drag * 0.3
        q = 0.5 * rho * velocity ** 2

        heating_rate = 1.83e-4 * math.sqrt(rho) * velocity ** 3

        mass = volume * material.density
        dyn_pressure = q

        warnings = []
        if mach > 1.0:
            warnings.append(f"Supersonic regime — Mach {mach:.2f}")
        if heating_rate > 100:
            warnings.append(f"High aerodynamic heating: {heating_rate:.0f} W/m²")
        if dyn_pressure > 50000:
            warnings.append(f"High dynamic pressure: {dyn_pressure / 1000:.0f} kPa")

        result.results = {
            "velocity_ms": velocity,
            "altitude_m": altitude,
            "mach_number": mach,
            "air_density_kgm3": rho,
            "temperature_K": temp,
            "pressure_Pa": pressure,
            "drag_coefficient": cd,
            "drag_force_N": drag,
            "lift_force_N": lift,
            "dynamic_pressure_Pa": dyn_pressure,
            "heating_rate_Wm2": heating_rate,
            "frontal_area_m2": frontal_area,
            "mass_kg": mass,
            "material": material.name,
        }
        result.warnings = warnings
        result.duration = time.time() - t0
        return result

    def mass_properties(self, mesh: Any, material: MaterialProps) -> SimulationResult:
        t0 = time.time()
        result = SimulationResult(sim_type=SimulationType.MASS_PROPERTIES, success=True)

        try:
            verts = mesh.vertices
            faces = mesh.faces
        except Exception:
            result.success = False
            result.warnings.append("Cannot access mesh geometry")
            return result

        try:
            volume = float(abs(mesh.volume)) if hasattr(mesh, "volume") else 0
        except Exception:
            volume = 0

        if volume < 1e-12:
            try:
                extents = verts.max(axis=0) - verts.min(axis=0)
                volume = float(np.prod(extents)) * 0.6
            except Exception:
                volume = 0.001

        mass = volume * material.density

        try:
            centroid = verts.mean(axis=0)
        except Exception:
            centroid = np.zeros(3)

        try:
            extents = verts.max(axis=0) - verts.min(axis=0)
        except Exception:
            extents = np.ones(3) * 0.1

        ixx = mass * (float(extents[1]) ** 2 + float(extents[2]) ** 2) / 12
        iyy = mass * (float(extents[0]) ** 2 + float(extents[2]) ** 2) / 12
        izz = mass * (float(extents[0]) ** 2 + float(extents[1]) ** 2) / 12

        cost = mass * material.cost_per_kg

        result.results = {
            "mass_kg": mass,
            "mass_g": mass * 1000,
            "mass_lb": mass * 2.20462,
            "volume_m3": volume,
            "volume_cm3": volume * 1e6,
            "density_kgm3": material.density,
            "centroid_m": centroid.tolist(),
            "moment_of_inertia_kgm2": {"ixx": ixx, "iyy": iyy, "izz": izz},
            "bounding_box_m": extents.tolist(),
            "material": material.name,
            "estimated_cost_usd": cost,
        }
        result.duration = time.time() - t0
        return result

    def orbital_simulation(self, mass: float, altitude: float,
                           inclination: float = 0.0,
                           planet: str = "earth") -> SimulationResult:
        t0 = time.time()
        result = SimulationResult(sim_type=SimulationType.ORBITAL, success=True)

        planet_data = {
            "earth": {"mass": self.EARTH_MASS, "radius": self.EARTH_RADIUS, "gm": self.EARTH_GM},
            "moon": {"mass": self.MOON_MASS, "radius": self.MOON_RADIUS, "gm": self.MOON_GM},
            "mars": {"mass": self.MARS_MASS, "radius": self.MARS_RADIUS, "gm": self.MARS_GM},
        }
        pd = planet_data.get(planet, planet_data["earth"])
        r = pd["radius"] + altitude
        mu = pd["gm"]

        v_circ = math.sqrt(mu / r) if r > 0 else 0
        t_period = 2 * math.pi * r / v_circ if v_circ > 0 else 0
        t_period_min = t_period / 60

        energy = -mu / (2 * r) if r > 0 else 0
        h_ang = math.sqrt(mu * r) if r > 0 else 0

        v_esc = math.sqrt(2 * mu / r) if r > 0 else 0
        v_circ_km = v_circ / 1000
        v_esc_km = v_esc / 1000

        ground_track_speed = v_circ * math.cos(math.radians(inclination)) if r > 0 else 0

        warnings = []
        if altitude < 160000:
            warnings.append(f"Very low altitude ({altitude / 1000:.0f} km) — significant drag, orbit decays rapidly")
        elif altitude < 400000:
            warnings.append(f"LEO altitude ({altitude / 1000:.0f} km) — periodic reboost needed")

        result.results = {
            "planet": planet,
            "altitude_m": altitude,
            "orbit_radius_m": r,
            "inclination_deg": inclination,
            "circular_velocity_ms": v_circ,
            "circular_velocity_kms": v_circ_km,
            "escape_velocity_ms": v_esc,
            "escape_velocity_kms": v_esc_km,
            "orbital_period_s": t_period,
            "orbital_period_min": t_period_min,
            "specific_orbital_energy": energy,
            "specific_angular_momentum": h_ang,
            "ground_track_velocity_ms": ground_track_speed,
            "satellite_mass_kg": mass,
        }
        result.warnings = warnings
        result.duration = time.time() - t0
        return result

    def trajectory(self, origin: str, destination: str,
                   depart_time: Optional[float] = None) -> SimulationResult:
        t0 = time.time()
        result = SimulationResult(sim_type=SimulationType.TRAJECTORY, success=True)

        bodies = {
            "earth": {"orbit_radius_au": 1.0, "period_yr": 1.0, "mu": self.EARTH_GM, "radius": self.EARTH_RADIUS},
            "mars": {"orbit_radius_au": 1.524, "period_yr": 1.881, "mu": self.MARS_GM, "radius": self.MARS_RADIUS},
            "moon": {"orbit_radius_au": 0.00257, "period_yr": 0.0748, "mu": self.MOON_GM, "radius": self.MOON_RADIUS, "parent": "earth"},
            "venus": {"orbit_radius_au": 0.723, "period_yr": 0.615, "mu": 3.249e14, "radius": 6051800},
            "jupiter": {"orbit_radius_au": 5.203, "period_yr": 11.86, "mu": 1.267e17, "radius": 69911000},
        }

        o = bodies.get(origin, bodies["earth"])
        d = bodies.get(destination, bodies["mars"])

        AU = 1.496e11
        r1 = o["orbit_radius_au"] * AU
        r2 = d["orbit_radius_au"] * AU

        if r1 < 1e6 or r2 < 1e6:
            result.success = False
            result.warnings.append(f"Cannot compute heliocentric transfer between {origin} and {destination}")
            result.duration = time.time() - t0
            return result

        a_transfer = (r1 + r2) / 2

        v1_helio = math.sqrt(self.SUN_GM / r1) if r1 > 0 else 0
        v2_helio = math.sqrt(self.SUN_GM / r2) if r2 > 0 else 0

        dv1 = abs(math.sqrt(self.SUN_GM * (2 / r1 - 1 / a_transfer)) - v1_helio)
        dv2 = abs(math.sqrt(self.SUN_GM * (2 / r2 - 1 / a_transfer)) - v2_helio)
        dv_total = dv1 + dv2

        t_transfer = math.pi * math.sqrt(a_transfer ** 3 / self.SUN_GM) if self.SUN_GM > 0 and a_transfer > 0 else 0

        if r1 > 0 and r2 > 0:
            cos_arg = (r1 ** 2 + r2 ** 2 - (2 * r1 * r2 * math.cos(math.pi * (1 - (r1 / r2) ** 1.5) / 2))) / (r1 ** 2 + r2 ** 2)
            cos_arg = max(-1.0, min(1.0, cos_arg))
            phase_angle = 180 - math.degrees(math.acos(cos_arg))
        else:
            phase_angle = 0.0
        phase_angle = max(0, min(180, phase_angle))

        mu_o = o.get("mu", self.EARTH_GM)
        r_o = o.get("radius", self.EARTH_RADIUS)
        v_esc_o = math.sqrt(2 * mu_o / (r_o + 200000))
        v_circ_o = math.sqrt(mu_o / (r_o + 200000))
        dv_to_escape = v_esc_o - v_circ_o

        warnings = []
        if dv_total > 20000:
            warnings.append(f"Very high delta-V: {dv_total / 1000:.1f} km/s")
        if t_transfer > 365 * 24 * 3600:
            warnings.append(f"Transfer time exceeds 1 year: {t_transfer / (86400):.0f} days")

        result.results = {
            "origin": origin,
            "destination": destination,
            "heliocentric_transfer": {
                "semi_major_axis_m": a_transfer,
                "delta_v1_ms": dv1,
                "delta_v2_ms": dv2,
                "delta_v_total_ms": dv_total,
                "delta_v_total_kms": dv_total / 1000,
                "transfer_time_s": t_transfer,
                "transfer_time_days": t_transfer / 86400,
                "transfer_time_months": t_transfer / (86400 * 30.44),
            },
            "phase_angle_deg": phase_angle,
            "departure_orbit": {
                "circular_velocity_ms": v_circ_o,
                "escape_velocity_ms": v_esc_o,
                "delta_v_to_escape_ms": dv_to_escape,
            },
            "total_mission_delta_v_ms": dv_total + dv_to_escape,
        }
        result.warnings = warnings
        result.duration = time.time() - t0
        return result


# =============================================================================
# GENERATION PIPELINE
# =============================================================================

class GenerationPipeline:
    """Main workflow engine — PROMPT → Intent → Generate → Preview → Materialize → Simulate → Export."""

    def __init__(self, material_library: Optional[MaterialLibrary] = None):
        self.library = material_library or MaterialLibrary()
        self.parser = PromptParser(self.library)
        self.generator = MeshGenerator()
        self.preview_engine = PreviewEngine()
        self.sim_engine = SimulationEngine()

    def run(self, prompt: str, options: Optional[Dict[str, Any]] = None,
            progress_callback: Optional[Callable[[str, float, str], None]] = None) -> WorkflowOutput:
        opts = options or {}
        job_id = uuid.uuid4().hex[:12]
        output = WorkflowOutput(job_id=job_id)
        t_start = time.time()

        def emit(step: str, pct: float, msg: str = ""):
            if progress_callback:
                progress_callback(step, pct, msg)
            logger.info(f"[{step}] {pct * 100:.0f}% — {msg}")

        # STEP 1: Parse
        emit("parse", 0.0, "Parsing prompt...")
        t0 = time.time()
        try:
            req = self.parser.parse(prompt)
            output.request = req
            output.pipeline_log.append(PipelineResult(
                step="parse", success=True,
                data=req.to_dict(), duration=time.time() - t0,
            ))
        except Exception as e:
            output.pipeline_log.append(PipelineResult(
                step="parse", success=False, error=str(e), duration=time.time() - t0,
            ))
            output.total_duration = time.time() - t_start
            return output
        emit("parse", 1.0, f"Detected: {req.object_type.value}")

        # STEP 2: Validate
        emit("validate", 0.0, "Validating request...")
        t0 = time.time()
        mat = self.library.get(req.material)
        if mat is None:
            mat = self.library.get("aluminum_6061")
            req.material = "aluminum_6061"
        output.pipeline_log.append(PipelineResult(
            step="validate", success=True,
            data={"material": mat.name, "dimensions": req.dimensions},
            duration=time.time() - t0,
        ))
        emit("validate", 1.0, f"Material: {mat.name}")

        # STEP 3: Generate
        emit("generate", 0.0, f"Generating {req.object_type.value}...")
        t0 = time.time()
        try:
            mesh = self.generator.generate(req)
            output.mesh = mesh
            n_verts = len(mesh.vertices) if hasattr(mesh, "vertices") else 0
            n_faces = len(mesh.faces) if hasattr(mesh, "faces") else 0
            output.pipeline_log.append(PipelineResult(
                step="generate", success=True,
                data={"vertices": n_verts, "faces": n_faces},
                duration=time.time() - t0,
            ))
        except Exception as e:
            output.pipeline_log.append(PipelineResult(
                step="generate", success=False, error=str(e), duration=time.time() - t0,
            ))
            output.total_duration = time.time() - t_start
            return output
        emit("generate", 1.0, f"Mesh: {n_verts} verts, {n_faces} faces")

        # STEP 4: Analyze
        emit("analyze", 0.0, "Computing mass properties...")
        t0 = time.time()
        try:
            mp = self.sim_engine.mass_properties(mesh, mat)
            output.mass_properties = mp.results
            output.pipeline_log.append(PipelineResult(
                step="analyze", success=True,
                data=mp.results, duration=time.time() - t0,
            ))
        except Exception as e:
            output.pipeline_log.append(PipelineResult(
                step="analyze", success=False, error=str(e), duration=time.time() - t0,
            ))
        emit("analyze", 1.0, f"Mass: {output.mass_properties.get('mass_kg', 0):.3f} kg")

        # STEP 5: Preview
        emit("preview", 0.0, "Rendering preview...")
        t0 = time.time()
        try:
            preview = self.preview_engine.render_preview(mesh, req.material, "aerospace")
            if preview:
                output.preview_images.append(preview)
            wireframe = self.preview_engine.create_wireframe_overlay(mesh, req.material)
            if wireframe:
                output.preview_images.append(wireframe)
            cross = self.preview_engine.create_cross_section(mesh, "xz", req.material)
            if cross:
                output.preview_images.append(cross)
            annotated = self.preview_engine.create_annotated(mesh, req.material)
            if annotated:
                output.preview_images.append(annotated)
            output.pipeline_log.append(PipelineResult(
                step="preview", success=True,
                data={"images": output.preview_images},
                duration=time.time() - t0,
            ))
        except Exception as e:
            output.pipeline_log.append(PipelineResult(
                step="preview", success=False, error=str(e), duration=time.time() - t0,
            ))
        emit("preview", 1.0, f"Generated {len(output.preview_images)} preview images")

        # STEP 6: Simulate
        if req.run_simulation:
            emit("simulate", 0.0, "Running simulations...")
            t0 = time.time()
            try:
                structural = self.sim_engine.structural_analysis(mesh, mat)
                output.simulation_results.append(structural)
                thermal = self.sim_engine.thermal_analysis(mesh, mat)
                output.simulation_results.append(thermal)
                orbital = self.sim_engine.orbital_simulation(
                    output.mass_properties.get("mass_kg", 100),
                    400000,
                )
                output.simulation_results.append(orbital)
                output.pipeline_log.append(PipelineResult(
                    step="simulate", success=True,
                    data={"simulations_run": len(output.simulation_results)},
                    duration=time.time() - t0,
                ))
            except Exception as e:
                output.pipeline_log.append(PipelineResult(
                    step="simulate", success=False, error=str(e), duration=time.time() - t0,
                ))
            emit("simulate", 1.0, f"Completed {len(output.simulation_results)} simulations")

        # STEP 7: Export
        emit("export", 0.0, "Exporting files...")
        t0 = time.time()
        try:
            out_dir = OUTPUT_DIR / job_id
            out_dir.mkdir(parents=True, exist_ok=True)

            for fmt in req.export_formats:
                try:
                    if fmt == ExportFormat.STL:
                        fp = out_dir / f"{req.object_type.value}.stl"
                        mesh.export(str(fp), file_type="stl")
                        output.mesh_files["stl"] = str(fp)
                    elif fmt == ExportFormat.OBJ:
                        fp = out_dir / f"{req.object_type.value}.obj"
                        mesh.export(str(fp), file_type="obj")
                        output.mesh_files["obj"] = str(fp)
                    elif fmt == ExportFormat.GLB:
                        fp = out_dir / f"{req.object_type.value}.glb"
                        mesh.export(str(fp), file_type="glb")
                        output.mesh_files["glb"] = str(fp)
                    elif fmt == ExportFormat.PLY:
                        fp = out_dir / f"{req.object_type.value}.ply"
                        mesh.export(str(fp), file_type="ply")
                        output.mesh_files["ply"] = str(fp)
                except Exception as e:
                    logger.warning(f"Export {fmt.value} failed: {e}")

            meta_path = out_dir / "metadata.json"
            meta = {
                "job_id": job_id,
                "prompt": prompt,
                "request": req.to_dict(),
                "mass_properties": output.mass_properties,
                "simulation_results": [s.to_dict() for s in output.simulation_results],
                "timestamp": datetime.utcnow().isoformat(),
                "pipeline_log": [p.to_dict() for p in output.pipeline_log],
            }
            meta_path.write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
            output.mesh_files["metadata"] = str(meta_path)

            output.pipeline_log.append(PipelineResult(
                step="export", success=True,
                data=output.mesh_files, duration=time.time() - t0,
            ))
        except Exception as e:
            output.pipeline_log.append(PipelineResult(
                step="export", success=False, error=str(e), duration=time.time() - t0,
            ))
        emit("export", 1.0, f"Exported to {out_dir}")

        output.total_duration = time.time() - t_start
        emit("complete", 1.0, f"Done in {output.total_duration:.2f}s")
        return output


# =============================================================================
# OUTPUT PACKAGE
# =============================================================================

class OutputPackage:
    """Bundle mesh files, previews, simulations, and metadata into a ZIP."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or OUTPUT_DIR

    def create_package(self, workflow_output: WorkflowOutput,
                       package_name: Optional[str] = None) -> Optional[str]:
        if package_name is None:
            package_name = f"zicore_{workflow_output.job_id}"

        pkg_dir = self.output_dir / package_name
        pkg_dir.mkdir(parents=True, exist_ok=True)

        zip_path = self.output_dir / f"{package_name}.zip"

        try:
            with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
                for fmt, fp in workflow_output.mesh_files.items():
                    if fp and fmt != "metadata":
                        try:
                            zf.write(fp, f"mesh/{Path(fp).name}")
                        except Exception:
                            pass

                for i, pp in enumerate(workflow_output.preview_images):
                    try:
                        zf.write(pp, f"previews/preview_{i:02d}.png")
                    except Exception:
                        pass

                sim_data = [s.to_dict() for s in workflow_output.simulation_results]
                if sim_data:
                    zf.writestr("simulations/results.json", json.dumps(sim_data, indent=2, default=str))

                zf.writestr("metadata.json", json.dumps({
                    "job_id": workflow_output.job_id,
                    "request": workflow_output.request.to_dict(),
                    "mass_properties": workflow_output.mass_properties,
                    "total_duration": workflow_output.total_duration,
                    "timestamp": datetime.utcnow().isoformat(),
                }, indent=2, default=str))

                zf.writestr("manifest.json", json.dumps({
                    "package": package_name,
                    "files": {
                        "mesh": list(workflow_output.mesh_files.keys()),
                        "previews": [f"previews/preview_{i:02d}.png" for i in range(len(workflow_output.preview_images))],
                        "simulations": ["simulations/results.json"],
                        "metadata": ["metadata.json"],
                    },
                    "job_id": workflow_output.job_id,
                }, indent=2))

            workflow_output.package_path = str(zip_path)
            return str(zip_path)
        except Exception as e:
            logger.error(f"Package creation failed: {e}")
            return None

    def extract_package(self, zip_path: str, extract_to: Optional[str] = None) -> Optional[str]:
        dest = extract_to or str(self.output_dir / Path(zip_path).stem)
        Path(dest).mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(dest)
            return dest
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return None


# =============================================================================
# MAIN WORKFLOW FACADE
# =============================================================================

class MaterializerWorkflow:
    """Complete materialization workflow — the STAR PRODUCT interface.

    Usage:
        wf = MaterializerWorkflow()
        result = wf.run("create a reusable rocket, 2 meters tall, aluminum 6061")
        package = wf.package(result)
    """

    def __init__(self):
        self.library = MaterialLibrary()
        self.parser = PromptParser(self.library)
        self.pipeline = GenerationPipeline(self.library)
        self.preview = PreviewEngine()
        self.simulation = SimulationEngine()
        self.packager = OutputPackage()

    def run(self, prompt: str, **kwargs) -> WorkflowOutput:
        return self.pipeline.run(prompt, options=kwargs)

    def parse(self, prompt: str) -> GenerationRequest:
        return self.parser.parse(prompt)

    def preview_mesh(self, mesh: Any, material: str = "aluminum_6061",
                     lighting: str = "aerospace") -> Optional[str]:
        return self.preview.render_preview(mesh, material, lighting)

    def simulate(self, mesh: Any, material_name: str = "aluminum_6061") -> List[SimulationResult]:
        mat = self.library.get(material_name) or self.library.get("aluminum_6061")
        results = []
        results.append(self.simulation.structural_analysis(mesh, mat))
        results.append(self.simulation.thermal_analysis(mesh, mat))
        results.append(self.simulation.aerodynamic_estimate(mesh, mat))
        results.append(self.simulation.mass_properties(mesh, mat))
        return results

    def package(self, workflow_output: WorkflowOutput) -> Optional[str]:
        return self.packager.create_package(workflow_output)

    def materials(self) -> Dict[str, MaterialProps]:
        return self.library.all()

    def recommend_material(self, purpose: str, **kwargs) -> List[MaterialProps]:
        return self.library.recommend(purpose, **kwargs)

    def orbital(self, mass: float, altitude: float, **kwargs) -> SimulationResult:
        return self.simulation.orbital_simulation(mass, altitude, **kwargs)

    def trajectory(self, origin: str, destination: str, **kwargs) -> SimulationResult:
        return self.simulation.trajectory(origin, destination, **kwargs)

    def quick_mesh(self, prompt: str) -> Any:
        req = self.parser.parse(prompt)
        return self.pipeline.generator.generate(req)


# =============================================================================
# CLI / DIRECT EXECUTION
# =============================================================================

def _cli():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python materializer_workflow.py <prompt>")
        print('Example: python materializer_workflow.py "create a rocket, 2m tall, aluminum"')
        sys.exit(1)

    prompt = " ".join(sys.argv[1:])
    wf = MaterializerWorkflow()

    def progress(step, pct, msg):
        bar_len = 30
        filled = int(bar_len * pct)
        bar = "=" * filled + "-" * (bar_len - filled)
        print(f"\r[{bar}] {step}: {msg}", end="", flush=True)
    print()

    result = wf.run(prompt, progress_callback=progress)
    print(f"\n\n{'=' * 60}")
    print(f"Job: {result.job_id}")
    print(f"Duration: {result.total_duration:.2f}s")
    print(f"Object: {result.request.object_type.value}")
    print(f"Material: {result.request.material}")
    print(f"Mass: {result.mass_properties.get('mass_kg', 0):.4f} kg")

    if result.mesh_files:
        print(f"\nExported files:")
        for k, v in result.mesh_files.items():
            print(f"  {k}: {v}")

    if result.preview_images:
        print(f"\nPreviews:")
        for p in result.preview_images:
            print(f"  {p}")

    if result.simulation_results:
        print(f"\nSimulation Results:")
        for s in result.simulation_results:
            print(f"  {s.sim_type.value}: safety_factor={s.safety_factor:.2f}")
            if s.warnings:
                for w in s.warnings:
                    print(f"    WARNING: {w}")

    pkg = wf.package(result)
    if pkg:
        print(f"\nPackage: {pkg}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    _cli()

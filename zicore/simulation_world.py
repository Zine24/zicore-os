"""
ZICORE Simulation World — Celestial bodies, terrain, and environment.

Provides:
- CelestialBody catalog (Earth, Moon, Mars, etc.)
- Terrain generation (heightmaps, texture maps)
- Environment presets (atmosphere, gravity, lighting)
- Scene configuration for the Simulation Engine

Author: ZineMotion Foundation — Aerospace Division
Version: 5.0.0
License: CC BY-NC-SA 4.0
"""
import math
import random
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

logger = None
try:
    import logging
    logger = logging.getLogger("zicore.simulation_world")
except Exception:
    pass


class BodyType(Enum):
    PLANET = "planet"
    MOON = "moon"
    ASTEROID = "asteroid"
    STATION = "station"
    CUSTOM = "custom"


@dataclass
class CelestialBody:
    """A celestial body or artificial structure with physical properties."""
    name: str
    body_type: BodyType
    radius_km: float
    gravity_ms2: float
    mass_kg: float
    escape_velocity_kms: float
    surface_pressure_kpa: float
    atmosphere_composition: Dict[str, float]
    surface_temp_k: float
    albedo: float
    has_atmosphere: bool
    has_magnetic_field: bool
    orbital_period_days: float
    parent_body: Optional[str]
    description: str = ""
    texture_url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["body_type"] = self.body_type.value
        return d


CELESTIAL_BODIES: Dict[str, CelestialBody] = {
    "earth": CelestialBody(
        name="Earth", body_type=BodyType.PLANET, radius_km=6371.0, gravity_ms2=9.807,
        mass_kg=5.972e24, escape_velocity_kms=11.186, surface_pressure_kpa=101.325,
        atmosphere_composition={"N2": 78.0, "O2": 21.0, "Ar": 0.93, "CO2": 0.04},
        surface_temp_k=288.0, albedo=0.306, has_atmosphere=True, has_magnetic_field=True,
        orbital_period_days=365.25, parent_body=None,
        description="Third planet from the Sun, home to humanity.",
        texture_url="/data/textures/earth_daymap.jpg",
    ),
    "moon": CelestialBody(
        name="Moon", body_type=BodyType.MOON, radius_km=1737.4, gravity_ms2=1.625,
        mass_kg=7.342e22, escape_velocity_kms=2.38, surface_pressure_kpa=3e-15,
        atmosphere_composition={"He": 95.0, "Ne": 4.0, "Ar": 0.6, "H2": 0.2},
        surface_temp_k=220.0, albedo=0.12, has_atmosphere=False, has_magnetic_field=False,
        orbital_period_days=27.32, parent_body="earth",
        description="Earth's only natural satellite, site of extensive human activity.",
        texture_url="/data/textures/moon_daymap.jpg",
    ),
    "mars": CelestialBody(
        name="Mars", body_type=BodyType.PLANET, radius_km=3389.5, gravity_ms2=3.721,
        mass_kg=6.417e23, escape_velocity_kms=5.03, surface_pressure_kpa=0.610,
        atmosphere_composition={"CO2": 95.3, "N2": 2.7, "Ar": 1.6, "O2": 0.13},
        surface_temp_k=210.0, albedo=0.250, has_atmosphere=True, has_magnetic_field=False,
        orbital_period_days=687.0, parent_body=None,
        description="The Red Planet, target of extensive robotic and future human exploration.",
        texture_url="/data/textures/mars_daymap.jpg",
    ),
    "mars_moon_phobos": CelestialBody(
        name="Phobos", body_type=BodyType.MOON, radius_km=11.1, gravity_ms2=0.0057,
        mass_kg=1.08e16, escape_velocity_kms=0.011, surface_pressure_kpa=0.0,
        atmosphere_composition={}, surface_temp_k=200.0, albedo=0.07,
        has_atmosphere=False, has_magnetic_field=False, orbital_period_days=0.319,
        parent_body="mars", description="Inner moon of Mars, irregularly shaped.",
    ),
    "mars_moon_deimos": CelestialBody(
        name="Deimos", body_type=BodyType.MOON, radius_km=6.2, gravity_ms2=0.003,
        mass_kg=2.48e15, escape_velocity_kms=0.006, surface_pressure_kpa=0.0,
        atmosphere_composition={}, surface_temp_k=190.0, albedo=0.08,
        has_atmosphere=False, has_magnetic_field=False, orbital_period_days=1.263,
        parent_body="mars", description="Outer moon of Mars, irregularly shaped.",
    ),
    "europa": CelestialBody(
        name="Europa", body_type=BodyType.MOON, radius_km=1560.8, gravity_ms2=1.315,
        mass_kg=4.80e22, escape_velocity_kms=2.025, surface_pressure_kpa=1e-12,
        atmosphere_composition={"O2": 99.0, "H2O": 0.1},
        surface_temp_k=102.0, albedo=0.68, has_atmosphere=False, has_magnetic_field=False,
        orbital_period_days=3.55, parent_body="jupiter",
        description="Jupiter's moon with subsurface ocean beneath ice crust.",
    ),
    "titan": CelestialBody(
        name="Titan", body_type=BodyType.MOON, radius_km=2574.73, gravity_ms2=1.352,
        mass_kg=1.345e23, escape_velocity_kms=2.64, surface_pressure_kpa=146.0,
        atmosphere_composition={"N2": 98.4, "CH4": 1.4, "H2": 0.01},
        surface_temp_k=94.0, albedo=0.22, has_atmosphere=True, has_magnetic_field=False,
        orbital_period_days=15.95, parent_body="saturn",
        description="Saturn's largest moon, with dense atmosphere and liquid methane lakes.",
    ),
    "asteroid_bennu": CelestialBody(
        name="Bennu", body_type=BodyType.ASTEROID, radius_km=0.245, gravity_ms2=0.00003,
        mass_kg=7.329e10, escape_velocity_kms=0.0002, surface_pressure_kpa=0.0,
        atmosphere_composition={}, surface_temp_k=250.0, albedo=0.045,
        has_atmosphere=False, has_magnetic_field=False, orbital_period_days=436.0,
        parent_body=None, description="Carbon-rich near-Earth asteroid.",
    ),
}


@dataclass
class TerrainConfig:
    """Configuration for procedural terrain generation."""
    seed: int
    size: int  # grid resolution (e.g., 256, 512)
    scale: float  # vertical scale factor
    octaves: int
    frequency: float
    lacunarity: float
    persistence: float
    height_range: Tuple[float, float]
    color_map: List[Tuple[float, Tuple[int, int, int]]]
    material: str
    features: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["height_range"] = list(self.height_range)
        d["color_map"] = [{"threshold": t, "color": list(c)} for t, c in self.color_map]
        return d


TERRAIN_PRESETS: Dict[str, TerrainConfig] = {
    "lunar_mare": TerrainConfig(
        seed=42, size=512, scale=2.0, octaves=5, frequency=0.01,
        lacunarity=2.0, persistence=0.5, height_range=(-1.0, 0.0),
        color_map=[
            (-1.0, (30, 30, 40)),
            (-0.8, (50, 50, 55)),
            (-0.5, (70, 70, 75)),
            (-0.3, (90, 90, 95)),
            (-0.1, (110, 110, 115)),
            (0.0, (130, 130, 135)),
        ],
        material="regolith",
        features=["craters", "lava_tubes", "ridges"],
    ),
    "lunar_highlands": TerrainConfig(
        seed=137, size=512, scale=3.0, octaves=6, frequency=0.008,
        lacunarity=2.2, persistence=0.45, height_range=(0.0, 5.0),
        color_map=[
            (0.0, (120, 120, 125)),
            (1.0, (140, 140, 145)),
            (2.5, (160, 160, 165)),
            (4.0, (180, 180, 185)),
            (5.0, (200, 200, 205)),
        ],
        material="anorthosite",
        features=["mountains", "craters", "scarps"],
    ),
    "mars_terrain": TerrainConfig(
        seed=256, size=512, scale=4.0, octaves=5, frequency=0.006,
        lacunarity=2.0, persistence=0.5, height_range=(-5.0, 10.0),
        color_map=[
            (-5.0, (100, 80, 60)),
            (-2.0, (130, 100, 75)),
            (0.0, (160, 120, 90)),
            (3.0, (180, 140, 100)),
            (6.0, (200, 160, 120)),
            (10.0, (220, 180, 140)),
        ],
        material="regolith",
        features=["canyons", "volcanoes", "dunes", "craters"],
    ),
    "mars_valles_marineris": TerrainConfig(
        seed=512, size=512, scale=8.0, octaves=4, frequency=0.004,
        lacunarity=2.5, persistence=0.4, height_range=(-10.0, 5.0),
        color_map=[
            (-10.0, (80, 60, 40)),
            (-5.0, (110, 85, 60)),
            (-2.0, (140, 110, 80)),
            (0.0, (170, 135, 100)),
            (3.0, (190, 155, 120)),
            (5.0, (210, 175, 140)),
        ],
        material="canyon_wall",
        features=["canyon", "cliff_faces", "layered_rock"],
    ),
    "mars_olympus_mons": TerrainConfig(
        seed=1024, size=512, scale=12.0, octaves=3, frequency=0.003,
        lacunarity=3.0, persistence=0.3, height_range=(0.0, 25.0),
        color_map=[
            (0.0, (120, 100, 80)),
            (5.0, (140, 120, 100)),
            (10.0, (160, 140, 120)),
            (15.0, (180, 160, 140)),
            (20.0, (200, 180, 160)),
            (25.0, (220, 200, 180)),
        ],
        material="volcanic_basalt",
        features=["volcano", "crater", "lava_flow"],
    ),
    "earth_terrain": TerrainConfig(
        seed=777, size=512, scale=2.0, octaves=6, frequency=0.01,
        lacunarity=2.0, persistence=0.5, height_range=(0.0, 3.0),
        color_map=[
            (0.0, (30, 80, 150)),
            (0.5, (240, 220, 150)),
            (1.0, (40, 140, 50)),
            (1.5, (60, 120, 50)),
            (2.0, (80, 100, 60)),
            (3.0, (100, 90, 70)),
        ],
        material="mixed",
        features=["rivers", "mountains", "forests", "plains"],
    ),
    "asteroid_surface": TerrainConfig(
        seed=999, size=256, scale=0.5, octaves=4, frequency=0.02,
        lacunarity=2.0, persistence=0.6, height_range=(-0.5, 0.5),
        color_map=[
            (-0.5, (40, 40, 45)),
            (-0.2, (55, 55, 60)),
            (0.0, (70, 70, 75)),
            (0.2, (85, 85, 90)),
            (0.5, (100, 100, 105)),
        ],
        material="regolith",
        features=["boulders", "craters", "dust_deposits"],
    ),
}


@dataclass
class EnvironmentConfig:
    """Environment settings for a simulation scene."""
    gravity: float  # m/s^2
    atmospheric_pressure: float  # kPa
    atmospheric_density: float  # kg/m^3
    temperature: float  # K
    wind_speed: float  # m/s
    wind_direction: float  # degrees
    visibility: float  # km
    magnetic_field_strength: float  # microtesla
    radiation_level: float  # mSv/day
    sky_color: Tuple[float, float, float]
    sun_intensity: float
    sun_color: Tuple[float, float, float]
    ambient_light: float
    fog_density: float
    fog_color: Tuple[float, float, float]

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["sky_color"] = list(self.sky_color)
        d["sun_color"] = list(self.sun_color)
        d["fog_color"] = list(self.fog_color)
        return d


def get_environment_for_body(body: CelestialBody) -> EnvironmentConfig:
    """Generate environment config from a celestial body."""
    if body.body_type == BodyType.MOON and body.name == "Moon":
        return EnvironmentConfig(
            gravity=1.625, atmospheric_pressure=0.0, atmospheric_density=0.0,
            temperature=220.0, wind_speed=0.0, wind_direction=0.0,
            visibility=1000.0, magnetic_field_strength=0.0, radiation_level=2.0,
            sky_color=(0.0, 0.0, 0.05), sun_intensity=1.0,
            sun_color=(1.0, 0.98, 0.9), ambient_light=0.15,
            fog_density=0.0, fog_color=(0.0, 0.0, 0.05),
        )
    elif body.name == "Mars":
        return EnvironmentConfig(
            gravity=3.721, atmospheric_pressure=0.610, atmospheric_density=0.02,
            temperature=210.0, wind_speed=10.0, wind_direction=45.0,
            visibility=10.0, magnetic_field_strength=0.0, radiation_level=0.7,
            sky_color=(0.6, 0.4, 0.25), sun_intensity=0.5,
            sun_color=(1.0, 0.85, 0.7), ambient_light=0.25,
            fog_density=0.05, fog_color=(0.6, 0.4, 0.25),
        )
    elif body.name == "Earth":
        return EnvironmentConfig(
            gravity=9.807, atmospheric_pressure=101.325, atmospheric_density=1.225,
            temperature=288.0, wind_speed=5.0, wind_direction=180.0,
            visibility=20.0, magnetic_field_strength=50.0, radiation_level=0.01,
            sky_color=(0.4, 0.6, 0.9), sun_intensity=1.0,
            sun_color=(1.0, 0.98, 0.9), ambient_light=0.4,
            fog_density=0.01, fog_color=(0.4, 0.6, 0.9),
        )
    else:
        return EnvironmentConfig(
            gravity=body.gravity_ms2, atmospheric_pressure=body.surface_pressure_kpa,
            atmospheric_density=0.0, temperature=body.surface_temp_k,
            wind_speed=0.0, wind_direction=0.0, visibility=100.0,
            magnetic_field_strength=0.0, radiation_level=0.0,
            sky_color=(0.0, 0.0, 0.05), sun_intensity=1.0,
            sun_color=(1.0, 0.98, 0.9), ambient_light=0.1,
            fog_density=0.0, fog_color=(0.0, 0.0, 0.05),
        )


def generate_heightmap(
    config: TerrainConfig,
    output_path: Optional[Path] = None,
) -> Optional[Any]:
    """Generate a heightmap image from terrain config."""
    if not HAS_NUMPY:
        if logger:
            logger.warning("numpy not available, cannot generate heightmap")
        return None

    size = config.size
    heightmap = np.zeros((size, size), dtype=np.float32)

    if HAS_NUMPY:
        def fbm(x, y, octaves, frequency, lacunarity, persistence):
            value = 0.0
            amplitude = 1.0
            for _ in range(octaves):
                value += amplitude * np.sin(x * frequency) * np.cos(y * frequency)
                x *= lacunarity
                y *= lacunarity
                amplitude *= persistence
            return value

        for i in range(size):
            for j in range(size):
                x = i / size * 10.0
                y = j / size * 10.0
                heightmap[i, j] = fbm(x, y, config.octaves, config.frequency,
                                     config.lacunarity, config.persistence)

    h_min, h_max = config.height_range
    heightmap = h_min + (heightmap - heightmap.min()) / (heightmap.max() - heightmap.min() + 1e-8) * (h_max - h_min)

    if HAS_PIL and output_path:
        normalized = ((heightmap - h_min) / (h_max - h_min + 1e-8) * 255).astype(np.uint8)
        img = Image.fromarray(normalized, mode="L")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)

    return heightmap


def generate_terrain_texture(
    config: TerrainConfig,
    output_path: Optional[Path] = None,
) -> Optional[Any]:
    """Generate a color texture map from terrain config."""
    if not HAS_NUMPY or not HAS_PIL:
        if logger:
            logger.warning("numpy or PIL not available, cannot generate texture")
        return None

    size = config.size
    texture = np.zeros((size, size, 3), dtype=np.uint8)

    if HAS_NUMPY:
        def fbm(x, y, octaves, frequency, lacunarity, persistence):
            value = 0.0
            amplitude = 1.0
            for _ in range(octaves):
                value += amplitude * np.sin(x * frequency) * np.cos(y * frequency)
                x *= lacunarity
                y *= lacunarity
                amplitude *= persistence
            return value

        for i in range(size):
            for j in range(size):
                x = i / size * 10.0
                y = j / size * 10.0
                elevation = fbm(x, y, config.octaves, config.frequency,
                               config.lacunarity, config.persistence)
                elevation = (elevation + 1.0) / 2.0

                for threshold, color in config.color_map:
                    if elevation <= threshold:
                        texture[i, j] = color
                        break
                else:
                    texture[i, j] = config.color_map[-1][1]

    if output_path:
        img = Image.fromarray(texture, mode="RGB")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)

    return texture


def get_body(name: str) -> Optional[CelestialBody]:
    """Get a celestial body by name (case-insensitive)."""
    for key, body in CELESTIAL_BODIES.items():
        if key.lower() == name.lower() or body.name.lower() == name.lower():
            return body
    return None


def list_bodies() -> List[str]:
    """List all available celestial body names."""
    return [body.name for body in CELESTIAL_BODIES.values()]


def get_terrain_presets() -> List[str]:
    """List all available terrain presets."""
    return list(TERRAIN_PRESETS.keys())


def get_terrain_preset(name: str) -> Optional[TerrainConfig]:
    """Get a terrain preset by name."""
    return TERRAIN_PRESETS.get(name)


def create_custom_body(
    name: str,
    radius_km: float,
    gravity_ms2: float,
    mass_kg: float,
    **kwargs,
) -> CelestialBody:
    """Create a custom celestial body."""
    escape_v = math.sqrt(2 * 6.674e-11 * mass_kg / (radius_km * 1000)) / 1000
    return CelestialBody(
        name=name, body_type=BodyType.CUSTOM, radius_km=radius_km,
        gravity_ms2=gravity_ms2, mass_kg=mass_kg, escape_velocity_kms=escape_v,
        surface_pressure_kpa=kwargs.get("surface_pressure_kpa", 0.0),
        atmosphere_composition=kwargs.get("atmosphere_composition", {}),
        surface_temp_k=kwargs.get("surface_temp_k", 250.0),
        albedo=kwargs.get("albedo", 0.3),
        has_atmosphere=kwargs.get("has_atmosphere", False),
        has_magnetic_field=kwargs.get("has_magnetic_field", False),
        orbital_period_days=kwargs.get("orbital_period_days", 365.0),
        parent_body=kwargs.get("parent_body"),
        description=kwargs.get("description", ""),
        texture_url=kwargs.get("texture_url"),
    )
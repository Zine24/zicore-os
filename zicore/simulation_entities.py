"""
ZICORE Simulation Entities — Entity templates for simulation scenes.

Provides:
- EntityTemplate base class and registry
- Pre-built templates: habitat domes, rovers, solar arrays, ISRU units,
  spacecraft, space stations, surface infrastructure
- Entity placement and behavior definitions
- Integration with local_generators for mesh creation

Author: ZineMotion Foundation — Aerospace Division
Version: 5.0.0
License: CC BY-NC-SA 4.0
"""
import math
import random
import json
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

logger = None
try:
    import logging
    logger = logging.getLogger("zicore.simulation_entities")
except Exception:
    pass


class EntityCategory(Enum):
    HABITAT = "habitat"
    ROVER = "rover"
    POWER = "power"
    PROPULSION = "propulsion"
    SCIENCE = "science"
    STORAGE = "storage"
    TRANSPORT = "transport"
    UTILITY = "utility"
    STRUCTURE = "structure"
    VEHICLE = "vehicle"
    STATION = "station"
    LANDING = "landing"
    MANUFACTURING = "manufacturing"
    COMMUNICATION = "communication"
    DEFENSE = "defense"


@dataclass
class EntityBehavior:
    """Defines autonomous behavior for an entity."""
    behavior_type: str  # "patrol", "orbit", "rotate", "idle", "dock", "mine", "track_sun"
    parameters: Dict[str, Any] = field(default_factory=dict)
    update_interval: float = 1.0  # seconds between behavior updates

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EntityTemplate:
    """A template for creating simulation entities."""
    name: str
    category: EntityCategory
    description: str
    mesh_type: str  # "primitive", "generated", "loaded", "procedural"
    mesh_params: Dict[str, Any]
    scale: Tuple[float, float, float]
    mass_kg: float
    power_consumption_kw: float
    power_generation_kw: float
    behaviors: List[EntityBehavior]
    properties: Dict[str, Any]
    tags: List[str]
    requires_terrain: bool = False
    requires_power: bool = False
    requires_crew: bool = False
    default_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["scale"] = list(self.scale)
        return d


ENTITY_TEMPLATES: Dict[str, EntityTemplate] = {}


def register_entity(template: EntityTemplate):
    """Register an entity template."""
    ENTITY_TEMPLATES[template.name] = template


# =============================================================================
# HABITAT ENTITIES
# =============================================================================

register_entity(EntityTemplate(
    name="habitat_dome",
    category=EntityCategory.HABITAT,
    description="Pressurized inflatable habitat dome with life support systems",
    mesh_type="generated",
    mesh_params={"shape": "capsule", "radius": 5.0, "height": 8.0, "segments": 32},
    scale=(1.0, 1.0, 1.0),
    mass_kg=12000.0,
    power_consumption_kw=15.0,
    power_generation_kw=0.0,
    behaviors=[EntityBehavior("idle", {})],
    properties={
        "interior_volume_m3": 400.0,
        "crew_capacity": 4,
        "pressure_kpa": 101.3,
        "o2_level_pct": 21.0,
        "co2_level_pct": 0.04,
        "temperature_c": 22.0,
        "has_airlock": True,
        "has_life_support": True,
    },
    tags=["pressurized", "life_support", "crew_habitat", "inflatable"],
    requires_power=True,
    requires_crew=True,
))

register_entity(EntityTemplate(
    name="habitat_module",
    category=EntityCategory.HABITAT,
    description="Modular cylindrical habitat section for space stations",
    mesh_type="generated",
    mesh_params={"shape": "cylinder", "radius": 2.0, "height": 6.0, "segments": 24},
    scale=(1.0, 1.0, 1.0),
    mass_kg=8000.0,
    power_consumption_kw=8.0,
    power_generation_kw=0.0,
    behaviors=[EntityBehavior("idle", {})],
    properties={
        "interior_volume_m3": 75.0,
        "crew_capacity": 2,
        "pressure_kpa": 101.3,
        "has_docking_port": True,
    },
    tags=["pressurized", "modular", "space_station", "docking"],
    requires_power=True,
    requires_crew=True,
))

register_entity(EntityTemplate(
    name="underground_habitat",
    category=EntityCategory.HABITAT,
    description="Underground habitat carved into terrain for radiation protection",
    mesh_type="generated",
    mesh_params={"shape": "box", "x": 10.0, "y": 5.0, "z": 15.0},
    scale=(1.0, 0.5, 1.0),
    mass_kg=50000.0,
    power_consumption_kw=20.0,
    power_generation_kw=0.0,
    behaviors=[EntityBehavior("idle", {})],
    properties={
        "interior_volume_m3": 600.0,
        "crew_capacity": 6,
        "radiation_shielding": "regolith",
        "shielding_thickness_m": 3.0,
        "has_greenhouse": True,
    },
    tags=["underground", "radiation_shielded", "crew_habitat", "greenhouse"],
    requires_terrain=True,
    requires_power=True,
    requires_crew=True,
))

# =============================================================================
# ROVER ENTITIES
# =============================================================================

register_entity(EntityTemplate(
    name="cargo_rover",
    category=EntityCategory.ROVER,
    description="Heavy-duty cargo transport rover with articulated suspension",
    mesh_type="generated",
    mesh_params={"shape": "custom", "type": "rover_chassis"},
    scale=(2.5, 2.0, 4.0),
    mass_kg=2500.0,
    power_consumption_kw=5.0,
    power_generation_kw=2.0,
    behaviors=[
        EntityBehavior("patrol", {"waypoints": [], "speed_ms": 3.0, "loop": True}),
        EntityBehavior("track_sun", {"axis": "y"}),
    ],
    properties={
        "cargo_capacity_kg": 1000.0,
        "cargo_volume_m3": 8.0,
        "max_speed_kmh": 25.0,
        "has_drill": False,
        "has_manipulator": True,
        "wheel_count": 6,
        "solar_panel_area_m2": 4.0,
    },
    tags=["wheeled", "cargo", "surface", "autonomous"],
    requires_power=True,
))

register_entity(EntityTemplate(
    name="exploration_rover",
    category=EntityCategory.ROVER,
    description="Scientific exploration rover with instruments and sampling tools",
    mesh_type="generated",
    mesh_params={"shape": "custom", "type": "rover_exploration"},
    scale=(2.0, 2.0, 3.5),
    mass_kg=1800.0,
    power_consumption_kw=3.0,
    power_generation_kw=1.5,
    behaviors=[
        EntityBehavior("patrol", {"waypoints": [], "speed_ms": 2.0, "loop": True}),
        EntityBehavior("track_sun", {"axis": "y"}),
    ],
    properties={
        "max_speed_kmh": 15.0,
        "has_drill": True,
        "has_spectrometer": True,
        "has_camera": True,
        "has_sample_container": True,
        "sample_capacity_kg": 5.0,
        "solar_panel_area_m2": 3.0,
    },
    tags=["wheeled", "scientific", "surface", "autonomous", "drill"],
    requires_power=True,
))

register_entity(EntityTemplate(
    name="drone_rover",
    category=EntityCategory.ROVER,
    description="Aerial drone for reconnaissance and atmospheric sampling",
    mesh_type="generated",
    mesh_params={"shape": "custom", "type": "quadcopter"},
    scale=(1.5, 1.5, 0.5),
    mass_kg=15.0,
    power_consumption_kw=2.0,
    power_generation_kw=0.0,
    behaviors=[
        EntityBehavior("orbit", {"target": "habitat_dome", "radius": 50.0, "speed": 5.0}),
        EntityBehavior("track_sun", {"axis": "z"}),
    ],
    properties={
        "max_speed_kmh": 60.0,
        "flight_time_min": 45.0,
        "has_camera": True,
        "has_lidar": True,
        "has_atmospheric_sensor": True,
        "rotor_count": 4,
    },
    tags=["aerial", "reconnaissance", "autonomous", "quadcopter"],
    requires_power=True,
))

# =============================================================================
# POWER ENTITIES
# =============================================================================

register_entity(EntityTemplate(
    name="solar_array",
    category=EntityCategory.POWER,
    description="Solar panel array with sun-tracking capability",
    mesh_type="generated",
    mesh_params={"shape": "box", "x": 0.1, "y": 4.0, "z": 8.0},
    scale=(1.0, 1.0, 1.0),
    mass_kg=800.0,
    power_consumption_kw=0.0,
    power_generation_kw=8.0,
    behaviors=[
        EntityBehavior("track_sun", {"axis": "z", "smooth": True}),
    ],
    properties={
        "panel_area_m2": 32.0,
        "efficiency_pct": 22.0,
        "peak_output_kw": 8.0,
        "has_battery": True,
        "battery_capacity_kwh": 16.0,
    },
    tags=["solar", "power_generation", "tracking", "renewable"],
    requires_power=True,
))

register_entity(EntityTemplate(
    name="nuclear_reactor",
    category=EntityCategory.POWER,
    description="Radioisotope thermoelectric generator (RTG) or small fission reactor",
    mesh_type="generated",
    mesh_params={"shape": "cylinder", "radius": 1.5, "height": 3.0, "segments": 24},
    scale=(1.0, 1.0, 1.0),
    mass_kg=1500.0,
    power_consumption_kw=0.0,
    power_generation_kw=5.0,
    behaviors=[EntityBehavior("idle", {})],
    properties={
        "thermal_output_kw": 50.0,
        "electrical_output_kw": 5.0,
        "fuel_type": "plutonium-238",
        "fuel_mass_kg": 4.8,
        "half_life_years": 87.7,
        "has_radiation_shielding": True,
    },
    tags=["nuclear", "power_generation", "rtg", "long_term"],
    requires_power=True,
))

register_entity(EntityTemplate(
    name="wind_turbine",
    category=EntityCategory.POWER,
    description="Vertical-axis wind turbine for atmospheric power generation",
    mesh_type="generated",
    mesh_params={"shape": "cylinder", "radius": 2.0, "height": 8.0, "segments": 16},
    scale=(1.0, 1.0, 1.0),
    mass_kg=1200.0,
    power_consumption_kw=0.0,
    power_generation_kw=3.0,
    behaviors=[
        EntityBehavior("rotate", {"axis": "y", "speed": 30.0}),
    ],
    properties={
        "blade_count": 0,
        "rated_power_kw": 3.0,
        "cut_in_speed_ms": 3.0,
        "rated_speed_ms": 15.0,
        "has_battery": True,
        "battery_capacity_kwh": 10.0,
    },
    tags=["wind", "power_generation", "atmospheric", "renewable"],
    requires_power=True,
))

# =============================================================================
# PROPULSION / TRANSPORT ENTITIES
# =============================================================================

register_entity(EntityTemplate(
    name="fuel_depot",
    category=EntityCategory.PROPULSION,
    description="Cryogenic fuel storage depot for propellant transfer",
    mesh_type="generated",
    mesh_params={"shape": "cylinder", "radius": 2.0, "height": 6.0, "segments": 24},
    scale=(1.0, 1.0, 1.0),
    mass_kg=5000.0,
    power_consumption_kw=2.0,
    power_generation_kw=0.0,
    behaviors=[EntityBehavior("idle", {})],
    properties={
        "fuel_type": "methalox",
        "fuel_capacity_kg": 50000.0,
        "fuel_stored_kg": 25000.0,
        "has_cryocooler": True,
        "temperature_k": 110.0,
        "has_docking_port": True,
    },
    tags=["fuel", "storage", "cryogenic", "docking"],
    requires_power=True,
))

register_entity(EntityTemplate(
    name="landing_pad",
    category=EntityCategory.LANDING,
    description="Reinforced landing pad with guidance markers",
    mesh_type="generated",
    mesh_params={"shape": "box", "x": 20.0, "y": 0.5, "z": 20.0},
    scale=(1.0, 1.0, 1.0),
    mass_kg=50000.0,
    power_consumption_kw=0.0,
    power_generation_kw=0.0,
    behaviors=[EntityBehavior("idle", {})],
    properties={
        "surface_material": "concrete",
        "has_guidance_lights": True,
        "has_survey_beacon": True,
        "max_touchdown_mass_kg": 50000.0,
    },
    tags=["landing", "infrastructure", "concrete"],
    requires_terrain=True,
))

register_entity(EntityTemplate(
    name="launch_clamp",
    category=EntityCategory.STRUCTURE,
    description="Hold-down clamp for launch vehicle restraint",
    mesh_type="generated",
    mesh_params={"shape": "custom", "type": "launch_clamp"},
    scale=(1.0, 1.0, 1.0),
    mass_kg=10000.0,
    power_consumption_kw=0.0,
    power_generation_kw=0.0,
    behaviors=[EntityBehavior("idle", {})],
    properties={
        "max_load_kg": 500000.0,
        "release_force_kn": 500.0,
        "has_tower": True,
        "tower_height_m": 20.0,
    },
    tags=["launch", "structure", "clamp", "restraint"],
    requires_terrain=True,
))

# =============================================================================
# SCIENCE / UTILITY ENTITIES
# =============================================================================

register_entity(EntityTemplate(
    name="isru_unit",
    category=EntityCategory.MANUFACTURING,
    description="In-Situ Resource Utilization unit for extracting water and oxygen from regolith",
    mesh_type="generated",
    mesh_params={"shape": "box", "x": 3.0, "y": 3.0, "z": 4.0},
    scale=(1.0, 1.0, 1.0),
    mass_kg=4000.0,
    power_consumption_kw=25.0,
    power_generation_kw=0.0,
    behaviors=[EntityBehavior("idle", {})],
    properties={
        "process_type": "electrolysis",
        "input_material": "regolith",
        "output_material": "oxygen",
        "production_rate_kg_per_hour": 10.0,
        "has_heating_element": True,
        "operating_temp_c": 800.0,
    },
    tags=["isru", "manufacturing", "oxygen_production", "resource_extraction"],
    requires_power=True,
    requires_terrain=True,
))

register_entity(EntityTemplate(
    name="science_lab",
    category=EntityCategory.SCIENCE,
    description="Mobile science laboratory with sample analysis equipment",
    mesh_type="generated",
    mesh_params={"shape": "box", "x": 4.0, "y": 3.0, "z": 5.0},
    scale=(1.0, 1.0, 1.0),
    mass_kg=6000.0,
    power_consumption_kw=10.0,
    power_generation_kw=0.0,
    behaviors=[EntityBehavior("idle", {})],
    properties={
        "has_microscope": True,
        "has_spectrometer": True,
        "has_mass_spectrometer": True,
        "sample_capacity_kg": 50.0,
        "analysis_rate_per_hour": 5.0,
        "has_3d_printer": True,
    },
    tags=["science", "laboratory", "analysis", "manufacturing"],
    requires_power=True,
    requires_crew=True,
))

register_entity(EntityTemplate(
    name="communication_array",
    category=EntityCategory.COMMUNICATION,
    description="High-gain communication dish for deep space communication",
    mesh_type="generated",
    mesh_params={"shape": "custom", "type": "dish_antenna"},
    scale=(1.0, 1.0, 1.0),
    mass_kg=3000.0,
    power_consumption_kw=5.0,
    power_generation_kw=0.0,
    behaviors=[
        EntityBehavior("track_sun", {"axis": "y", "smooth": True}),
    ],
    properties={
        "dish_diameter_m": 3.0,
        "frequency_ghz": 8.4,
        "data_rate_mbps": 100.0,
        "has_star_tracker": True,
        "pointing_accuracy_deg": 0.01,
    },
    tags=["communication", "dish", "deep_space", "tracking"],
    requires_power=True,
))

register_entity(EntityTemplate(
    name="weather_station",
    category=EntityCategory.SCIENCE,
    description="Meteorological station for atmospheric monitoring",
    mesh_type="generated",
    mesh_params={"shape": "custom", "type": "weather_station"},
    scale=(1.0, 1.0, 1.0),
    mass_kg=500.0,
    power_consumption_kw=1.0,
    power_generation_kw=2.0,
    behaviors=[EntityBehavior("idle", {})],
    properties={
        "has_barometer": True,
        "has_thermometer": True,
        "has_anemometer": True,
        "has_hygrometer": True,
        "has_wind_vane": True,
        "solar_panel_area_m2": 2.0,
    },
    tags=["science", "weather", "atmospheric", "monitoring"],
    requires_power=True,
))

register_entity(EntityTemplate(
    name="greenhouse",
    category=EntityCategory.HABITAT,
    description="Pressurized greenhouse for food production",
    mesh_type="generated",
    mesh_params={"shape": "box", "x": 6.0, "y": 4.0, "z": 10.0},
    scale=(1.0, 1.0, 1.0),
    mass_kg=8000.0,
    power_consumption_kw=12.0,
    power_generation_kw=0.0,
    behaviors=[EntityBehavior("idle", {})],
    properties={
        "growing_area_m2": 40.0,
        "food_production_kg_per_day": 15.0,
        "has_led_lights": True,
        "has_irrigation": True,
        "has_climate_control": True,
        "crop_types": ["lettuce", "tomato", "potato", "wheat"],
    },
    tags=["agriculture", "food_production", "pressurized", "life_support"],
    requires_power=True,
    requires_crew=True,
))

# =============================================================================
# SPACE VEHICLES
# =============================================================================

register_entity(EntityTemplate(
    name="cargo_ship",
    category=EntityCategory.VEHICLE,
    description="Interplanetary cargo transport spacecraft",
    mesh_type="generated",
    mesh_params={"shape": "custom", "type": "cargo_ship"},
    scale=(3.0, 3.0, 12.0),
    mass_kg=50000.0,
    power_consumption_kw=20.0,
    power_generation_kw=15.0,
    behaviors=[
        EntityBehavior("orbit", {"target": "planet", "radius": 500.0, "speed": 1.0}),
    ],
    properties={
        "cargo_capacity_kg": 20000.0,
        "cargo_volume_m3": 100.0,
        "has_docking_port": True,
        "has_heat_shield": True,
        "propulsion_type": "chemical",
        "isp_s": 350.0,
        "delta_v_ms": 4000.0,
    },
    tags=["spacecraft", "cargo", "interplanetary", "propulsion"],
    requires_power=True,
))

register_entity(EntityTemplate(
    name="shuttle",
    category=EntityCategory.VEHICLE,
    description="Reusable spaceplane for crew and cargo transport",
    mesh_type="generated",
    mesh_params={"shape": "custom", "type": "spaceplane"},
    scale=(8.0, 4.0, 15.0),
    mass_kg=75000.0,
    power_consumption_kw=30.0,
    power_generation_kw=20.0,
    behaviors=[
        EntityBehavior("orbit", {"target": "planet", "radius": 400.0, "speed": 2.0}),
    ],
    properties={
        "crew_capacity": 7,
        "cargo_capacity_kg": 25000.0,
        "has_landing_gear": True,
        "has_wings": True,
        "has_heat_shield": True,
        "propulsion_type": "combined",
        "isp_s": 450.0,
    },
    tags=["spacecraft", "crew", "reusable", "spaceplane", "propulsion"],
    requires_power=True,
))

# =============================================================================
# STORAGE / UTILITY
# =============================================================================

register_entity(EntityTemplate(
    name="cargo_container",
    category=EntityCategory.STORAGE,
    description="Standard cargo container for material storage",
    mesh_type="generated",
    mesh_params={"shape": "box", "x": 2.0, "y": 2.0, "z": 4.0},
    scale=(1.0, 1.0, 1.0),
    mass_kg=2000.0,
    power_consumption_kw=0.0,
    power_generation_kw=0.0,
    behaviors=[EntityBehavior("idle", {})],
    properties={
        "cargo_capacity_kg": 20000.0,
        "cargo_volume_m3": 16.0,
        "has_crane_mount": True,
        "material": "aluminum",
    },
    tags=["storage", "cargo", "container"],
    requires_terrain=True,
))

register_entity(EntityTemplate(
    name="antenna_array",
    category=EntityCategory.COMMUNICATION,
    description="Ground-based antenna array for satellite communication",
    mesh_type="generated",
    mesh_params={"shape": "custom", "type": "antenna_array"},
    scale=(1.0, 1.0, 1.0),
    mass_kg=5000.0,
    power_consumption_kw=10.0,
    power_generation_kw=0.0,
    behaviors=[
        EntityBehavior("track_sun", {"axis": "y", "smooth": True}),
    ],
    properties={
        "antenna_count": 4,
        "frequency_ghz": 2.3,
        "data_rate_gbps": 10.0,
        "beam_width_deg": 2.0,
        "has_star_tracker": True,
    },
    tags=["communication", "ground_station", "antenna", "tracking"],
    requires_power=True,
    requires_terrain=True,
))

register_entity(EntityTemplate(
    name="fuel_tank",
    category=EntityCategory.STORAGE,
    description="Cryogenic fuel storage tank",
    mesh_type="generated",
    mesh_params={"shape": "cylinder", "radius": 1.5, "height": 5.0, "segments": 24},
    scale=(1.0, 1.0, 1.0),
    mass_kg=3000.0,
    power_consumption_kw=1.0,
    power_generation_kw=0.0,
    behaviors=[EntityBehavior("idle", {})],
    properties={
        "fuel_type": "methalox",
        "capacity_kg": 20000.0,
        "has_cryocooler": True,
        "insulation_type": "multilayer",
        "temperature_k": 110.0,
    },
    tags=["fuel", "storage", "cryogenic", "tank"],
    requires_power=True,
))

register_entity(EntityTemplate(
    name="space_station",
    category=EntityCategory.STATION,
    description="Modular space station with multiple docking ports",
    mesh_type="generated",
    mesh_params={"shape": "custom", "type": "space_station_core"},
    scale=(20.0, 20.0, 5.0),
    mass_kg=400000.0,
    power_consumption_kw=50.0,
    power_generation_kw=40.0,
    behaviors=[
        EntityBehavior("rotate", {"axis": "y", "speed": 0.5}),
    ],
    properties={
        "habitable_volume_m3": 1000.0,
        "crew_capacity": 12,
        "docking_ports": 8,
        "solar_array_area_m2": 500.0,
        "has_central_core": True,
        "has_radar": True,
        "has_medbay": True,
    },
    tags=["station", "space_station", "modular", "docking", "crew"],
    requires_power=True,
    requires_crew=True,
))


def get_entity_template(name: str) -> Optional[EntityTemplate]:
    """Get an entity template by name."""
    return ENTITY_TEMPLATES.get(name)


def list_entities() -> List[str]:
    """List all available entity template names."""
    return sorted(ENTITY_TEMPLATES.keys())


def list_entities_by_category(category: EntityCategory) -> List[str]:
    """List entities in a specific category."""
    return sorted(
        name for name, template in ENTITY_TEMPLATES.items()
        if template.category == category
    )


def list_categories() -> List[str]:
    """List all entity categories."""
    return sorted(set(t.category.value for t in ENTITY_TEMPLATES.values()))


@dataclass
class EntityInstance:
    """An instance of an entity placed in a simulation scene."""
    template_name: str
    position: Tuple[float, float, float]
    rotation: Tuple[float, float, float]
    scale: Tuple[float, float, float]
    instance_id: str
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    behavior_state: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["position"] = list(self.position)
        d["rotation"] = list(self.rotation)
        d["scale"] = list(self.scale)
        return d


def create_entity_instance(
    template_name: str,
    position: Tuple[float, float, float],
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    scale: Optional[Tuple[float, float, float]] = None,
    instance_id: Optional[str] = None,
    **custom_properties,
) -> Optional[EntityInstance]:
    """Create an entity instance from a template."""
    template = get_entity_template(template_name)
    if template is None:
        if logger:
            logger.error(f"Unknown entity template: {template_name}")
        return None

    if scale is None:
        scale = template.scale

    if instance_id is None:
        instance_id = f"{template_name}_{random.randint(1000, 9999)}"

    return EntityInstance(
        template_name=template_name,
        position=position,
        rotation=rotation,
        scale=scale,
        instance_id=instance_id,
        custom_properties=custom_properties,
    )


def get_entity_mesh_spec(template_name: str) -> Optional[Dict[str, Any]]:
    """Get the mesh specification for an entity template."""
    template = get_entity_template(template_name)
    if template is None:
        return None
    return {
        "mesh_type": template.mesh_type,
        "mesh_params": template.mesh_params,
        "scale": list(template.scale),
        "mass_kg": template.mass_kg,
        "tags": template.tags,
    }
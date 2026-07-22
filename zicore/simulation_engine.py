"""
ZICORE Simulation Engine — Prompt-to-simulation pipeline.

Orchestrates:
- Natural language prompt parsing (keyword-based, no LLM required)
- World and celestial body selection
- Terrain generation (heightmaps + textures)
- Entity placement and scene composition
- Physics configuration
- Asset export (STL, GLB, JSON config)
- Client-side scene streaming

Author: ZineMotion Foundation — Aerospace Division
Version: 5.0.0
License: CC BY-NC-SA 4.0
"""
import os
import sys
import math
import json
import time
import uuid
import random
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

logger = None
try:
    import logging
    logger = logging.getLogger("zicore.simulation_engine")
except Exception:
    pass

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "simulations"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

from zicore.simulation_world import (
    CelestialBody, BodyType, CELESTIAL_BODIES, get_body, list_bodies,
    TerrainConfig, TERRAIN_PRESETS, get_terrain_presets, get_terrain_preset,
    EnvironmentConfig, get_environment_for_body,
    generate_heightmap, generate_terrain_texture,
)
from zicore.simulation_entities import (
    EntityTemplate, EntityCategory, ENTITY_TEMPLATES,
    get_entity_template, list_entities, list_entities_by_category,
    list_categories, EntityInstance, create_entity_instance,
    get_entity_mesh_spec,
)


class SimulationStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    ASSETS_GENERATING = "assets_generating"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class SimulationConfig:
    """Configuration for a simulation run."""
    simulation_id: str
    prompt: str
    body_name: str
    terrain_preset: str
    entities: List[Dict[str, Any]]
    environment: Optional[Dict[str, Any]]
    physics: Dict[str, Any]
    seed: int
    resolution: int
    created_at: float
    status: str = SimulationStatus.PENDING.value
    progress: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class SimulationResult:
    """Result of a simulation generation."""
    simulation_id: str
    config: Dict[str, Any]
    assets: Dict[str, str]  # name -> file path
    scene_file: str
    glb_file: Optional[str]
    status: str
    created_at: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


class PromptParser:
    """Parses natural language prompts into simulation parameters."""

    BODY_KEYWORDS: Dict[str, List[str]] = {
        "moon": ["moon", "lunar", "luna", "moonbase", "munar"],
        "mars": ["mars", "martian", "red planet"],
        "earth": ["earth", "terran", "planet earth"],
        "europa": ["europa", "europan", "jupiter moon"],
        "titan": ["titan", "titanian", "saturn moon"],
        "asteroid_bennu": ["asteroid", "bennu", "asteroid belt"],
    }

    TERRAIN_KEYWORDS: Dict[str, List[str]] = {
        "mars_valles_marineris": ["valles marineris", "grand canyon"],
        "mars_olympus_mons": ["olympus mons", "shield volcano"],
        "lunar_highlands": ["highland", "highlands", "anorthosite"],
        "lunar_mare": ["mare", "lunar plain", "smooth", "basalt"],
        "mars_terrain": ["mars", "martian", "red", "dust", "canyon"],
        "earth_terrain": ["earth", "terran", "forest", "grass", "ocean"],
        "asteroid_surface": ["asteroid", "rocky", "boulder", "cratered"],
    }

    ENTITY_KEYWORDS: Dict[str, List[str]] = {
        "habitat_dome": ["habitat", "dome", "base", "hab", "living"],
        "underground_habitat": ["underground", "bunker", "below ground", "subsurface"],
        "cargo_rover": ["cargo rover", "transport rover", "truck"],
        "exploration_rover": ["exploration rover", "rover", "exploration"],
        "drone_rover": ["drone", "quadcopter", "uav", "aerial"],
        "solar_array": ["solar", "panel", "array", "power"],
        "nuclear_reactor": ["nuclear", "rtg", "reactor", "fission"],
        "wind_turbine": ["wind", "turbine", "turbine"],
        "fuel_depot": ["fuel depot", "propellant", "fuel storage"],
        "landing_pad": ["landing pad", "landing zone", "lz", "pad"],
        "launch_clamp": ["launch clamp", "hold down", "clamp"],
        "isru_unit": ["isru", "in-situ", "resource", "oxygen", "water extraction"],
        "science_lab": ["lab", "laboratory", "science", "research"],
        "communication_array": ["communication", "antenna", "dish", "satcom"],
        "weather_station": ["weather", "meteorology", "atmosphere"],
        "greenhouse": ["greenhouse", "farm", "agriculture", "food"],
        "cargo_ship": ["cargo ship", "freighter", "transport ship"],
        "shuttle": ["shuttle", "spaceplane", "orbiter"],
        "cargo_container": ["container", "storage container", "crate"],
        "antenna_array": ["antenna array", "ground station", "tracking"],
        "fuel_tank": ["fuel tank", "tank", "propellant tank"],
        "space_station": ["station", "space station", "orbital"],
    }

    PHYSICS_KEYWORDS: Dict[str, List[str]] = {
        "realistic": ["realistic", "real", "accurate", "precise"],
        "fast": ["fast", "quick", "real-time", "interactive"],
        "n_body": ["n-body", "n body", "gravity", "orbit"],
    }

    def __init__(self):
        self._body_keywords = {k: set(v) for k, v in self.BODY_KEYWORDS.items()}
        self._terrain_keywords = {k: set(v) for k, v in self.TERRAIN_KEYWORDS.items()}
        self._entity_keywords = {k: set(v) for k, v in self.ENTITY_KEYWORDS.items()}
        self._physics_keywords = {k: set(v) for k, v in self.PHYSICS_KEYWORDS.items()}

    def parse(self, prompt: str) -> Dict[str, Any]:
        """Parse a natural language prompt into simulation parameters."""
        msg = prompt.lower().strip()
        tokens = set(msg.split())

        body = self._detect_body(msg, tokens)
        terrain = self._detect_terrain(msg, tokens, body)
        entities = self._detect_entities(msg, tokens)
        physics = self._detect_physics(msg, tokens)
        seed = self._generate_seed(msg)

        return {
            "body": body,
            "terrain": terrain,
            "entities": entities,
            "physics": physics,
            "seed": seed,
        }

    def _detect_body(self, msg: str, tokens: Set[str]) -> str:
        """Detect celestial body from prompt."""
        for body_name, keywords in self._body_keywords.items():
            if any(kw in msg for kw in keywords):
                return body_name
        return "moon"

    def _detect_terrain(self, msg: str, tokens: Set[str], body: str) -> str:
        """Detect terrain preset from prompt."""
        for terrain_name, keywords in self._terrain_keywords.items():
            if any(kw in msg for kw in keywords):
                return terrain_name

        if body == "mars":
            return "mars_terrain"
        elif body == "moon":
            return "lunar_mare"
        elif body == "earth":
            return "earth_terrain"
        elif body == "asteroid_bennu":
            return "asteroid_surface"
        return "lunar_mare"

    def _detect_entities(self, msg: str, tokens: Set[str]) -> List[str]:
        """Detect entity templates from prompt."""
        entities = []
        for entity_name, keywords in self._entity_keywords.items():
            if any(kw in msg for kw in keywords):
                if entity_name not in entities:
                    entities.append(entity_name)

        if not entities:
            if "base" in msg or "habitat" in msg:
                entities = ["habitat_dome", "solar_array", "cargo_rover"]
            elif "station" in msg:
                entities = ["space_station", "communication_array"]
            elif "landing" in msg:
                entities = ["landing_pad", "launch_clamp", "cargo_ship"]
            elif "mining" in msg:
                entities = ["isru_unit", "cargo_rover", "cargo_container"]
            elif "exploration" in msg:
                entities = ["exploration_rover", "science_lab", "weather_station"]
            else:
                entities = ["habitat_dome", "solar_array"]

        return entities

    def _detect_physics(self, msg: str, tokens: Set[str]) -> Dict[str, Any]:
        """Detect physics settings from prompt."""
        physics = {
            "engine": "basic",
            "gravity": True,
            "atmosphere": True,
            "collision": True,
            "timestep": 0.016,
        }
        for phys_key, keywords in self._physics_keywords.items():
            if any(kw in msg for kw in keywords):
                if phys_key == "realistic":
                    physics["engine"] = "advanced"
                    physics["timestep"] = 0.008
                elif phys_key == "fast":
                    physics["engine"] = "basic"
                    physics["timestep"] = 0.033
                elif phys_key == "n_body":
                    physics["engine"] = "n_body"
                    physics["timestep"] = 0.016
        return physics

    def _generate_seed(self, msg: str) -> int:
        """Generate a deterministic seed from the prompt."""
        h = hashlib.md5(msg.encode("utf-8")).hexdigest()
        return int(h[:8], 16) % (2**31)


class SimulationComposer:
    """Composes simulation scenes from parsed parameters."""

    def __init__(self):
        self.parser = PromptParser()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="sim")

    def generate(self, prompt: str, resolution: int = 512, async_mode: bool = False) -> Dict[str, Any]:
        """Generate a complete simulation from a prompt."""
        sim_id = f"sim_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        parsed = self.parser.parse(prompt)

        config = SimulationConfig(
            simulation_id=sim_id,
            prompt=prompt,
            body_name=parsed["body"],
            terrain_preset=parsed["terrain"],
            entities=[{"template": e, "count": 1} for e in parsed["entities"]],
            environment=None,
            physics=parsed["physics"],
            seed=parsed["seed"],
            resolution=resolution,
            created_at=time.time(),
        )

        config_path = OUTPUT_DIR / sim_id / "config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config.to_dict(), f, indent=2)

        if async_mode:
            future = self._executor.submit(self._generate_async, config)
            return {
                "simulation_id": sim_id,
                "status": SimulationStatus.PROCESSING.value,
                "config": config.to_dict(),
                "async": True,
            }
        else:
            result = self._generate_sync(config)
            return result.to_dict()

    def _generate_sync(self, config: SimulationConfig) -> SimulationResult:
        """Synchronous simulation generation."""
        sim_dir = OUTPUT_DIR / config.simulation_id
        sim_dir.mkdir(parents=True, exist_ok=True)
        config_path = sim_dir / "config.json"

        try:
            config.status = SimulationStatus.ASSETS_GENERATING.value
            config.progress = 0.1

            body = get_body(config.body_name) or get_body("moon")
            terrain_preset = get_terrain_preset(config.terrain_preset) or get_terrain_preset("lunar_mare")
            environment = get_environment_for_body(body)

            config.environment = environment.to_dict()

            terrain_dir = sim_dir / "terrain"
            terrain_dir.mkdir(parents=True, exist_ok=True)

            heightmap_path = terrain_dir / "heightmap.png"
            texture_path = terrain_dir / "texture.png"

            if HAS_NUMPY:
                generate_heightmap(terrain_preset, heightmap_path)
                generate_terrain_texture(terrain_preset, texture_path)
            else:
                heightmap_path = None
                texture_path = None

            config.progress = 0.3

            entity_instances: List[EntityInstance] = []
            entity_assets: Dict[str, str] = {}

            for i, entity_spec in enumerate(config.entities):
                template_name = entity_spec["template"]
                count = entity_spec.get("count", 1)
                template = get_entity_template(template_name)

                if template is None:
                    continue

                for j in range(count):
                    if template.requires_terrain:
                        pos = self._place_on_terrain(i, j, count)
                    else:
                        pos = self._place_entity(i, j, count, template)

                    rotation = (0.0, random.uniform(0, 360), 0.0) if template.category == EntityCategory.ROVER else (0.0, 0.0, 0.0)

                    instance = create_entity_instance(
                        template_name=template_name,
                        position=pos,
                        rotation=rotation,
                        instance_id=f"{template_name}_{i}_{j}",
                    )
                    if instance:
                        entity_instances.append(instance)

                    mesh_spec = get_entity_mesh_spec(template_name)
                    if mesh_spec:
                        entity_assets[f"{template_name}_{i}_{j}"] = json.dumps(mesh_spec)

                config.progress = 0.3 + (i + 1) / len(config.entities) * 0.4

            scene_config = {
                "simulation_id": config.simulation_id,
                "body": body.to_dict(),
                "terrain": {
                    "preset": config.terrain_preset,
                    "config": terrain_preset.to_dict(),
                    "heightmap_url": f"/output/simulations/{config.simulation_id}/terrain/heightmap.png" if heightmap_path else None,
                    "texture_url": f"/output/simulations/{config.simulation_id}/terrain/texture.png" if texture_path else None,
                },
                "environment": environment.to_dict(),
                "physics": config.physics,
                "entities": [inst.to_dict() for inst in entity_instances],
                "entity_assets": entity_assets,
                "seed": config.seed,
                "created_at": config.created_at,
            }

            scene_path = sim_dir / "scene.json"
            with open(scene_path, "w") as f:
                json.dump(scene_config, f, indent=2)

            config.progress = 0.8

            glb_path = self._export_glb(sim_dir, scene_config)

            config.status = SimulationStatus.COMPLETE.value
            config.progress = 1.0

            with open(config_path, "w") as f:
                json.dump(config.to_dict(), f, indent=2)

            return SimulationResult(
                simulation_id=config.simulation_id,
                config=scene_config,
                assets={
                    "scene": str(scene_path),
                    "heightmap": str(heightmap_path) if heightmap_path else None,
                    "texture": str(texture_path) if texture_path else None,
                    "glb": glb_path,
                },
                scene_file=str(scene_path),
                glb_file=glb_path,
                status=SimulationStatus.COMPLETE.value,
                created_at=time.time(),
            )

        except Exception as e:
            if logger:
                logger.error(f"Simulation generation failed: {e}")
            config.status = SimulationStatus.ERROR.value
            config.error = str(e)
            with open(config_path, "w") as f:
                json.dump(config.to_dict(), f, indent=2)
            return SimulationResult(
                simulation_id=config.simulation_id,
                config=config.to_dict(),
                assets={},
                scene_file="",
                glb_file=None,
                status=SimulationStatus.ERROR.value,
                created_at=time.time(),
                error=str(e),
            )

    def _generate_async(self, config: SimulationConfig) -> SimulationResult:
        """Async simulation generation (runs in thread pool)."""
        return self._generate_sync(config)

    def _place_entity(self, index: int, sub_index: int, count: int, template: EntityTemplate) -> Tuple[float, float, float]:
        """Place an entity in the scene."""
        base_radius = 30.0 + index * 15.0
        angle = (sub_index / max(count, 1)) * 2 * math.pi
        x = base_radius * math.cos(angle)
        z = base_radius * math.sin(angle)
        y = 0.0

        if template.requires_terrain:
            y = 0.5

        if template.category == EntityCategory.ROVER:
            y = 0.3
        elif template.category == EntityCategory.VEHICLE:
            y = 1.0

        return (x, y, z)

    def _place_on_terrain(self, index: int, sub_index: int, count: int) -> Tuple[float, float, float]:
        """Place an entity on the terrain surface."""
        base_radius = 40.0 + index * 20.0
        angle = (sub_index / max(count, 1)) * 2 * math.pi
        x = base_radius * math.cos(angle)
        z = base_radius * math.sin(angle)
        y = 0.2
        return (x, y, z)

    def _export_glb(self, sim_dir: Path, scene_config: Dict[str, Any]) -> Optional[str]:
        """Export scene as GLB file. Non-blocking — returns None on failure."""
        try:
            import trimesh
        except ImportError:
            return None
        except Exception:
            return None

        try:
            scene = trimesh.Scene()

            for entity in scene_config.get("entities", []):
                template_name = entity["template_name"]
                pos = entity["position"]
                rot = entity["rotation"]
                scale_vec = entity["scale"]

                mesh_spec = None
                for key, val in scene_config.get("entity_assets", {}).items():
                    if key.startswith(template_name):
                        try:
                            mesh_spec = json.loads(val) if isinstance(val, str) else val
                        except Exception:
                            pass
                        break

                if mesh_spec:
                    mesh = self._create_entity_mesh(mesh_spec)
                    if mesh:
                        mesh.apply_translation(pos)
                        if scale_vec:
                            try:
                                mesh.apply_scale(scale_vec)
                            except Exception:
                                pass
                        scene.add_geometry(mesh)

            glb_path = sim_dir / "scene.glb"
            scene.export(str(glb_path))
            return str(glb_path)

        except Exception as e:
            if logger:
                logger.warning(f"GLB export failed (non-critical): {e}")
            return None

    def _create_entity_mesh(self, spec: Dict[str, Any]) -> Optional[Any]:
        """Create a mesh from entity spec."""
        try:
            import trimesh
            import trimesh.creation as creation

            mesh_type = spec.get("mesh_type", "primitive")
            params = spec.get("mesh_params", {})

            if mesh_type == "generated":
                shape = params.get("shape", "cube")
                if shape == "capsule":
                    return creation.capsule(radius=params.get("radius", 1.0), height=params.get("height", 2.0))
                elif shape == "cylinder":
                    return creation.cylinder(radius=params.get("radius", 1.0), height=params.get("height", 2.0))
                elif shape == "cone":
                    return creation.cone(radius=params.get("radius", 1.0), height=params.get("height", 2.0))
                elif shape == "box":
                    return creation.box(extents=[params.get("x", 1.0), params.get("y", 1.0), params.get("z", 1.0)])
                elif shape == "sphere":
                    return creation.icosphere(radius=params.get("radius", 1.0))
                elif shape == "custom":
                    entity_type = params.get("type", "cube")
                    if entity_type == "rover_chassis":
                        body = creation.box(extents=[2.5, 1.0, 4.0])
                        body.apply_translation([0, 1.5, 0])
                        wheels = []
                        for sx in [-1.2, 1.2]:
                            for sz in [-1.5, 1.5]:
                                w = creation.cylinder(radius=0.4, height=0.3)
                                w.apply_translation([sx, 0.4, sz])
                                wheels.append(w)
                        return trimesh.util.concatenate([body] + wheels)
                    elif entity_type == "quadcopter":
                        body = creation.box(extents=[1.5, 0.3, 1.5])
                        body.apply_translation([0, 0.15, 0])
                        motors = []
                        for sx in [-0.7, 0.7]:
                            for sz in [-0.7, 0.7]:
                                m = creation.cylinder(radius=0.1, height=0.05)
                                m.apply_translation([sx, 0.3, sz])
                                motors.append(m)
                        return trimesh.util.concatenate([body] + motors)
                    elif entity_type == "dish_antenna":
                        dish = creation.cone(radius=1.5, height=0.3)
                        dish.apply_translation([0, 0.8, 0])
                        pole = creation.cylinder(radius=0.05, height=0.8)
                        pole.apply_translation([0, 0.4, 0])
                        return trimesh.util.concatenate([dish, pole])
                    elif entity_type == "antenna_array":
                        elements = []
                        for i in range(4):
                            angle = i * math.pi / 2
                            x = math.cos(angle) * 2.0
                            z = math.sin(angle) * 2.0
                            pole = creation.cylinder(radius=0.05, height=3.0)
                            pole.apply_translation([x, 1.5, z])
                            dish = creation.cone(radius=0.5, height=0.2)
                            dish.apply_translation([x, 3.0, z])
                            elements.extend([pole, dish])
                        base = creation.box(extents=[6, 0.2, 6])
                        elements.append(base)
                        return trimesh.util.concatenate(elements)
                    elif entity_type == "space_station_core":
                        core = creation.box(extents=[8, 2, 8])
                        core.apply_translation([0, 1, 0])
                        modules = []
                        for i in range(4):
                            angle = i * math.pi / 2
                            x = math.cos(angle) * 6
                            z = math.sin(angle) * 6
                            m = creation.cylinder(radius=2, height=6)
                            m.apply_translation([x, 0, z])
                            modules.append(m)
                        return trimesh.util.concatenate([core] + modules)
                    elif entity_type == "cargo_ship":
                        body = creation.box(extents=[3, 3, 12])
                        body.apply_translation([0, 6, 0])
                        engine = creation.cone(radius=1.5, height=2)
                        engine.apply_translation([0, 1.5, -6])
                        return trimesh.util.concatenate([body, engine])
                    elif entity_type == "spaceplane":
                        body = creation.box(extents=[4, 2, 15])
                        body.apply_translation([0, 1, 0])
                        wing_l = creation.box(extents=[0.5, 0.2, 8])
                        wing_l.apply_translation([-4, 0.5, 0])
                        wing_r = creation.box(extents=[0.5, 0.2, 8])
                        wing_r.apply_translation([4, 0.5, 0])
                        return trimesh.util.concatenate([body, wing_l, wing_r])
                    else:
                        return creation.box(extents=[1, 1, 1])
                else:
                    return creation.box(extents=[1, 1, 1])
            else:
                return creation.box(extents=[1, 1, 1])

        except Exception as e:
            if logger:
                logger.warning(f"Mesh creation failed for spec {spec}: {e}")
            return None

    def get_status(self, sim_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a simulation."""
        config_path = OUTPUT_DIR / sim_id / "config.json"
        if not config_path.exists():
            return None
        with open(config_path, "r") as f:
            return json.load(f)

    def get_scene(self, sim_id: str) -> Optional[Dict[str, Any]]:
        """Get the scene configuration for a simulation."""
        scene_path = OUTPUT_DIR / sim_id / "scene.json"
        if not scene_path.exists():
            return None
        with open(scene_path, "r") as f:
            return json.load(f)

    def list_simulations(self) -> List[Dict[str, Any]]:
        """List all simulations."""
        simulations = []
        for sim_dir in sorted(OUTPUT_DIR.iterdir(), key=lambda p: p.name, reverse=True):
            if sim_dir.is_dir() and (sim_dir / "config.json").exists():
                with open(sim_dir / "config.json", "r") as f:
                    config = json.load(f)
                simulations.append(config)
        return simulations


class SimulationEngine:
    """Main entry point for the Simulation Engine."""

    _instance: Optional["SimulationEngine"] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.composer = SimulationComposer()
        self._active_simulations: Dict[str, Future] = {}

    def generate(self, prompt: str, resolution: int = 512, async_mode: bool = False) -> Dict[str, Any]:
        """Generate a simulation from a natural language prompt."""
        return self.composer.generate(prompt, resolution=resolution, async_mode=async_mode)

    def get_status(self, sim_id: str) -> Optional[Dict[str, Any]]:
        """Get simulation status."""
        return self.composer.get_status(sim_id)

    def get_scene(self, sim_id: str) -> Optional[Dict[str, Any]]:
        """Get simulation scene configuration."""
        return self.composer.get_scene(sim_id)

    def list_simulations(self) -> List[Dict[str, Any]]:
        """List all simulations."""
        return self.composer.list_simulations()

    def get_available_entities(self) -> List[str]:
        """List all available entity templates."""
        return list_entities()

    def get_available_bodies(self) -> List[str]:
        """List all available celestial bodies."""
        return list_bodies()

    def get_available_terrains(self) -> List[str]:
        """List all available terrain presets."""
        return get_terrain_presets()


simulation_engine = SimulationEngine()


if __name__ == "__main__":
    engine = SimulationEngine()

    test_prompts = [
        "Create a simulation of a lunar mining base with habitat dome, cargo rover, and ISRU unit",
        "Simulate a Mars exploration mission with rovers, solar arrays, and a science lab",
        "Build a space station orbiting Earth with communication arrays and docking ports",
    ]

    for prompt in test_prompts:
        print(f"\n{'='*60}")
        print(f"Prompt: {prompt}")
        print(f"{'='*60}")
        result = engine.generate(prompt, resolution=256)
        print(f"Simulation ID: {result.get('simulation_id')}")
        print(f"Status: {result.get('status')}")
        if result.get("config"):
            config = result["config"]
            print(f"Body: {config.get('body', {}).get('name', 'unknown')}")
            print(f"Terrain: {config.get('terrain', {}).get('preset', 'unknown')}")
            print(f"Entities: {len(config.get('entities', []))}")
            print(f"Physics: {config.get('physics', {}).get('engine', 'unknown')}")
        print()
"""
ZICORE Local 3D Generation Engine
Full local mesh generation, analysis, and export using trimesh + pymeshlab.

Replaces cloud API dependency for common 3D tasks.
No GPU required — CPU-only generation.

Author: ZineMotion Foundation — Aerospace Division
Version: 5.0.0
"""

import os
import math
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

try:
    import trimesh
    from trimesh.creation import (
        box, cylinder, cone, torus, capsule, icosphere, icosahedron,
        annulus, extrude_polygon
    )
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False

try:
    import pymeshlab
    HAS_PYMESHLAB = True
except ImportError:
    HAS_PYMESHLAB = False

logger = logging.getLogger("zicore.local_generators")

OUTPUT_DIR = Path(__file__).parent.parent / "output"


def _ensure_output_dir(subdir: str = "") -> Path:
    path = OUTPUT_DIR / subdir if subdir else OUTPUT_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_execute(func, *args, **kwargs):
    """Run a function with graceful error handling."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        return None


# =============================================================================
# MESH GENERATOR — Create 3D meshes from shapes, prompts, and aerospace parts
# =============================================================================

class MeshGenerator:
    """
    Generate 3D meshes from basic shapes, aerospace components,
    composite part lists, or natural language prompts.
    """

    BASIC_SHAPES = [
        "cube", "sphere", "cylinder", "cone", "torus", "capsule",
        "icosahedron", "octahedron", "dodecahedron", "plane"
    ]

    AEROSPACE_COMPONENTS = [
        "rocket", "satellite", "station", "drone", "nozzle", "fin",
        "landing_leg", "solar_panel", "antenna", "habitat", "rover",
        "payload_bay", "engine", "fuel_tank", "nose_cone"
    ]

    # -----------------------------------------------------------------
    # Basic Shape Generation
    # -----------------------------------------------------------------

    @staticmethod
    def generate_basic(shape: str, params: Optional[Dict[str, Any]] = None) -> Optional["trimesh.Trimesh"]:
        """
        Generate a basic geometric shape.

        Supported shapes: cube, sphere, cylinder, cone, torus, capsule,
        icosahedron, octahedron, dodecahedron, plane
        """
        if not HAS_TRIMESH:
            logger.error("trimesh not installed")
            return None

        params = params or {}
        shape = shape.lower().strip()

        generators = {
            "cube": lambda p: box(
                extents=[p.get("width", 1), p.get("height", 1), p.get("depth", 1)]
            ),
            "sphere": lambda p: icosphere(subdivisions=p.get("subdivisions", 3),
                                           radius=p.get("radius", 0.5)),
            "cylinder": lambda p: cylinder(
                radius=p.get("radius", 0.5),
                height=p.get("height", 1),
                sections=p.get("sections", 64)
            ),
            "cone": lambda p: cone(
                radius=p.get("radius", 0.5),
                height=p.get("height", 1),
                sections=p.get("sections", 64)
            ),
            "torus": lambda p: torus(
                major_radius=p.get("major_radius", 0.5),
                minor_radius=p.get("minor_radius", 0.15),
                major_sections=p.get("major_sections", 64),
                minor_sections=p.get("minor_sections", 32)
            ),
            "capsule": lambda p: capsule(
                radius=p.get("radius", 0.25),
                height=p.get("height", 1)
            ),
            "icosahedron": lambda p: trimesh.creation.icosahedron().scale(
                p.get("radius", 0.5)
            ) if hasattr(trimesh.creation, 'icosahedron') else trimesh.creation.icosphere(
                subdivisions=0, radius=p.get("radius", 0.5)
            ),
            "octahedron": lambda p: _make_octahedron(p.get("radius", 0.5)),
            "dodecahedron": lambda p: _make_dodecahedron(p.get("radius", 0.5)),
            "plane": lambda p: _make_plane(
                p.get("width", 1), p.get("height", 1),
                p.get("width_sections", 10), p.get("height_sections", 10)
            ),
        }

        if shape not in generators:
            logger.warning(f"Unknown shape '{shape}'. Available: {MeshGenerator.BASIC_SHAPES}")
            return None

        try:
            mesh = generators[shape](params)
            if mesh is not None and not isinstance(mesh, trimesh.Trimesh):
                mesh = trimesh.util.concatenate(mesh) if isinstance(mesh, trimesh.Scene) else mesh
            return mesh
        except Exception as e:
            logger.error(f"Failed to generate '{shape}': {e}")
            return None

    # -----------------------------------------------------------------
    # Aerospace Component Generation
    # -----------------------------------------------------------------

    @staticmethod
    def generate_aerospace(component: str, params: Optional[Dict[str, Any]] = None) -> Optional["trimesh.Trimesh"]:
        """
        Generate an aerospace component mesh.

        Supported: rocket, satellite, station, drone, nozzle, fin, landing_leg,
        solar_panel, antenna, habitat, rover, payload_bay, engine, fuel_tank, nose_cone
        """
        if not HAS_TRIMESH:
            logger.error("trimesh not installed")
            return None

        params = params or {}
        component = component.lower().strip()

        try:
            ac = AerospaceComponents
            dispatch = {
                "rocket": lambda p: ac.rocket(
                    p.get("height", 10), p.get("radius", 1), p.get("stages", 3)),
                "satellite": lambda p: ac.satellite(
                    p.get("body_size", 1), p.get("solar_panel_size", 3), p.get("antenna_count", 2)),
                "station": lambda p: ac.space_station(
                    p.get("ring_radius", 5), p.get("hub_size", 1.5), p.get("spoke_count", 6)),
                "drone": lambda p: ac.drone(
                    p.get("body_size", 0.5), p.get("arm_length", 1), p.get("rotor_size", 0.3)),
                "nozzle": lambda p: ac.nozzle(
                    p.get("throat_radius", 0.1), p.get("exit_radius", 0.3),
                    p.get("length", 1), p.get("bell_ratio", 0.8)),
                "fin": lambda p: ac.fin(
                    p.get("height", 1), p.get("chord", 0.5), p.get("sweep", 30)),
                "landing_leg": lambda p: ac.landing_leg(
                    p.get("length", 2), p.get("spread_angle", 20)),
                "solar_panel": lambda p: ac.solar_panel(
                    p.get("width", 2), p.get("height", 1), p.get("cell_count", 6)),
                "antenna": lambda p: ac.antenna(
                    p.get("dish_radius", 0.5), p.get("mast_height", 1)),
                "habitat": lambda p: ac.habitat(
                    p.get("diameter", 4), p.get("height", 3), p.get("levels", 2)),
                "rover": lambda p: ac.rover(
                    p.get("wheel_base", 2), p.get("width", 1.5), p.get("height", 1)),
                "payload_bay": lambda p: ac.payload_bay(
                    p.get("width", 2), p.get("height", 1.5), p.get("depth", 3)),
                "engine": lambda p: ac.engine(
                    p.get("radius", 0.5), p.get("length", 1.5), p.get("engine_type", "bell")),
                "fuel_tank": lambda p: ac.fuel_tank(
                    p.get("radius", 0.5), p.get("height", 2), p.get("tank_type", "cylindrical")),
                "nose_cone": lambda p: ac.nose_cone(
                    p.get("radius", 0.5), p.get("height", 1.5), p.get("cone_type", "ogive")),
            }

            if component not in dispatch:
                logger.warning(f"Unknown component '{component}'. Available: {MeshGenerator.AEROSPACE_COMPONENTS}")
                return None

            return dispatch[component](params)
        except Exception as e:
            logger.error(f"Failed to generate aerospace component '{component}': {e}")
            return None

    # -----------------------------------------------------------------
    # Composite Generation — combine multiple parts
    # -----------------------------------------------------------------

    @staticmethod
    def generate_composite(parts_list: List[Dict[str, Any]]) -> Optional["trimesh.Trimesh"]:
        """
        Combine multiple parts into one mesh.

        Each part dict: {"type": "basic"|"aerospace", "shape": str,
                         "params": dict, "translate": [x,y,z],
                         "rotate": {"axis": [x,y,z], "angle": float},
                         "scale": float|list}
        """
        if not HAS_TRIMESH:
            logger.error("trimesh not installed")
            return None

        meshes = []
        for part in parts_list:
            ptype = part.get("type", "basic")
            shape = part.get("shape", "cube")
            params = part.get("params", {})

            if ptype == "aerospace":
                mesh = MeshGenerator.generate_aerospace(shape, params)
            else:
                mesh = MeshGenerator.generate_basic(shape, params)

            if mesh is None:
                logger.warning(f"Skipping failed part: {shape}")
                continue

            tx = part.get("translate", [0, 0, 0])
            if tx:
                mesh.apply_translation(tx)

            rot = part.get("rotate")
            if rot:
                axis = rot.get("axis", [0, 1, 0])
                angle = math.radians(rot.get("angle", 0))
                R = trimesh.transformations.rotation_matrix(angle, axis)
                mesh.apply_transform(R)

            sc = part.get("scale")
            if sc is not None:
                if isinstance(sc, (list, tuple)):
                    mesh.apply_scale(sc[0])
                else:
                    mesh.apply_scale(sc)

            meshes.append(mesh)

        if not meshes:
            logger.error("No valid meshes in composite parts list")
            return None

        if len(meshes) == 1:
            return meshes[0]

        try:
            return trimesh.util.concatenate(meshes)
        except Exception as e:
            logger.error(f"Failed to concatenate meshes: {e}")
            return None

    # -----------------------------------------------------------------
    # Prompt-based Generation — AI-like intent detection
    # -----------------------------------------------------------------

    @staticmethod
    def generate_from_prompt(prompt: str) -> Optional["trimesh.Trimesh"]:
        """
        Parse a natural language prompt and route to appropriate generator.
        Uses keyword matching for intent detection.
        """
        if not HAS_TRIMESH:
            logger.error("trimesh not installed")
            return None

        p = prompt.lower().strip()

        aerospace_keywords = {
            "rocket": ["rocket", "launch vehicle", "missile", "booster"],
            "satellite": ["satellite", "satsat", "orbiter"],
            "station": ["space station", "orbital station", "habitat ring"],
            "drone": ["drone", "uav", "quadcopter", "unmanned"],
            "nozzle": ["nozzle", "bell nozzle", "engine nozzle"],
            "landing_leg": ["landing leg", "landing gear", "strut"],
            "solar_panel": ["solar panel", "solar array", "photovoltaic"],
            "antenna": ["antenna", "dish", "radio dish", "comm dish"],
            "habitat": ["habitat", "hab module", "living quarters"],
            "rover": ["rover", "surface vehicle", "moon buggy", "mars rover"],
            "payload_bay": ["payload bay", "cargo bay", "cargo hold"],
            "engine": ["engine", "thruster", "propulsion"],
            "fuel_tank": ["fuel tank", "propellant tank", "tank"],
            "nose_cone": ["nose cone", "fairing", "aerodynamic nose"],
            "fin": ["fin", "stabilizer", "tail fin", "aero fin"],
        }

        shape_keywords = {
            "cube": ["cube", "block", "box", "rectangular"],
            "sphere": ["sphere", "ball", "orb", "globe"],
            "cylinder": ["cylinder", "tube", "pipe", "column"],
            "cone": ["cone", "pyramid", "pointed"],
            "torus": ["torus", "donut", "ring", "doughnut"],
            "capsule": ["capsule", "pill", "rounded cylinder"],
        }

        for comp, keywords in aerospace_keywords.items():
            for kw in keywords:
                if kw in p:
                    logger.info(f"Prompt matched aerospace component: {comp}")
                    return MeshGenerator.generate_aerospace(comp)

        for shape, keywords in shape_keywords.items():
            for kw in keywords:
                if kw in p:
                    logger.info(f"Prompt matched basic shape: {shape}")
                    return MeshGenerator.generate_basic(shape)

        logger.info("No specific match — generating default cube")
        return MeshGenerator.generate_basic("cube")


# =============================================================================
# MESH OPERATIONS — Modify existing meshes
# =============================================================================

class MeshOperations:
    """Boolean, transform, smoothing, and mesh modification operations."""

    @staticmethod
    def boolean_union(mesh_a: "trimesh.Trimesh",
                      mesh_b: "trimesh.Trimesh") -> Optional["trimesh.Trimesh"]:
        """Combine two meshes (union)."""
        if not HAS_TRIMESH:
            return None
        try:
            return mesh_a.union(mesh_b)
        except Exception as e:
            logger.error(f"Boolean union failed: {e}")
            return _fallback_concatenate(mesh_a, mesh_b)

    @staticmethod
    def boolean_difference(mesh_a: "trimesh.Trimesh",
                           mesh_b: "trimesh.Trimesh") -> Optional["trimesh.Trimesh"]:
        """Subtract mesh_b from mesh_a."""
        if not HAS_TRIMESH:
            return None
        try:
            return mesh_a.difference(mesh_b)
        except Exception as e:
            logger.error(f"Boolean difference failed: {e}")
            return None

    @staticmethod
    def boolean_intersection(mesh_a: "trimesh.Trimesh",
                             mesh_b: "trimesh.Trimesh") -> Optional["trimesh.Trimesh"]:
        """Keep only the overlapping volume."""
        if not HAS_TRIMESH:
            return None
        try:
            return mesh_a.intersection(mesh_b)
        except Exception as e:
            logger.error(f"Boolean intersection failed: {e}")
            return None

    @staticmethod
    def scale(mesh: "trimesh.Trimesh",
              factor: Union[float, List[float]]) -> Optional["trimesh.Trimesh"]:
        """Scale mesh uniformly or per-axis."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            m = mesh.copy()
            if isinstance(factor, (list, tuple)):
                sx, sy, sz = factor
                m.vertices *= np.array([sx, sy, sz])
            else:
                m.apply_scale(factor)
            return m
        except Exception as e:
            logger.error(f"Scale failed: {e}")
            return None

    @staticmethod
    def rotate(mesh: "trimesh.Trimesh", axis: List[float],
               angle_degrees: float) -> Optional["trimesh.Trimesh"]:
        """Rotate mesh around an axis by angle_degrees."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            m = mesh.copy()
            angle_rad = math.radians(angle_degrees)
            R = trimesh.transformations.rotation_matrix(angle_rad, axis)
            m.apply_transform(R)
            return m
        except Exception as e:
            logger.error(f"Rotate failed: {e}")
            return None

    @staticmethod
    def translate(mesh: "trimesh.Trimesh",
                  x: float = 0, y: float = 0, z: float = 0) -> Optional["trimesh.Trimesh"]:
        """Translate mesh by (x, y, z)."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            m = mesh.copy()
            m.apply_translation([x, y, z])
            return m
        except Exception as e:
            logger.error(f"Translate failed: {e}")
            return None

    @staticmethod
    def mirror(mesh: "trimesh.Trimesh", axis: str = "x") -> Optional["trimesh.Trimesh"]:
        """Mirror mesh across an axis ('x', 'y', or 'z')."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            m = mesh.copy()
            axis_map = {"x": 0, "y": 1, "z": 2}
            idx = axis_map.get(axis.lower(), 0)
            m.vertices[:, idx] *= -1
            m.faces = m.faces[:, ::-1]
            m.fix_normals()
            return m
        except Exception as e:
            logger.error(f"Mirror failed: {e}")
            return None

    @staticmethod
    def smooth(mesh: "trimesh.Trimesh",
               iterations: int = 3) -> Optional["trimesh.Trimesh"]:
        """Laplacian mesh smoothing via pymeshlab or manual Laplacian."""
        if not HAS_TRIMESH or mesh is None:
            return None

        if HAS_PYMESHLAB:
            return _pymeshlab_smooth(mesh, iterations)

        try:
            m = mesh.copy()
            for _ in range(iterations):
                m = _laplacian_smooth_step(m)
            m.fix_normals()
            return m
        except Exception as e:
            logger.error(f"Smooth failed: {e}")
            return None

    @staticmethod
    def decimate(mesh: "trimesh.Trimesh",
                 target_faces: int = 1000) -> Optional["trimesh.Trimesh"]:
        """Reduce polygon count to target_faces using pymeshlab or trimesh simplification."""
        if mesh is None:
            return None

        if HAS_PYMESHLAB:
            return _pymeshlab_decimate(mesh, target_faces)

        if HAS_TRIMESH:
            try:
                current = len(mesh.faces)
                if current <= target_faces:
                    return mesh.copy()
                ratio = target_faces / current
                simplified = mesh.simplify_quadric_decimation(face_count=target_faces)
                return simplified
            except Exception as e:
                logger.warning(f"trimesh decimate failed, returning original: {e}")
                return mesh.copy()

        return None

    @staticmethod
    def subdivide(mesh: "trimesh.Trimesh",
                  level: int = 1) -> Optional["trimesh.Trimesh"]:
        """Catmull-Clark subdivision."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            m = mesh.copy()
            for _ in range(level):
                m = m.subdivide()
            return m
        except Exception as e:
            logger.error(f"Subdivide failed: {e}")
            return None

    @staticmethod
    def extrude(mesh: "trimesh.Trimesh",
                distance: float = 0.1) -> Optional["trimesh.Trimesh"]:
        """Extrude all faces outward along their normals."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            verts = mesh.vertices.copy()
            faces = mesh.faces.copy()
            normals = mesh.face_normals
            n_original = len(verts)

            face_verts = verts[faces]
            extruded = face_verts + normals[:, np.newaxis, :] * distance
            extruded_flat = extruded.reshape(-1, 3)
            new_verts = np.vstack([verts, extruded_flat])

            new_faces = []
            for i, face in enumerate(faces):
                o0, o1, o2 = int(face[0]), int(face[1]), int(face[2])
                n0 = o0 + n_original
                n1 = o1 + n_original
                n2 = o2 + n_original
                new_faces.append([o0, o1, n1])
                new_faces.append([o0, n1, n0])
                new_faces.append([o1, o2, n2])
                new_faces.append([o1, n2, n1])
                new_faces.append([o2, o0, n0])
                new_faces.append([o2, n0, n2])
                new_faces.append([o0, o1, o2])
                new_faces.append([n0, n1, n2])

            result = trimesh.Trimesh(
                vertices=new_verts,
                faces=np.array(new_faces, dtype=np.int64)
            )
            result.fix_normals()
            return result
        except Exception as e:
            logger.error(f"Extrude failed: {e}")
            return None

    @staticmethod
    def hollow(mesh: "trimesh.Trimesh",
               thickness: float = 0.05) -> Optional["trimesh.Trimesh"]:
        """Hollow out a solid mesh by shrinking inward."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            outer = mesh.copy()
            inner = mesh.copy()
            normals = inner.vertex_normals
            avg_normal = np.mean(normals, axis=0)
            avg_normal = avg_normal / (np.linalg.norm(avg_normal) + 1e-10)
            inner.vertices -= avg_normal * thickness
            inner.faces = inner.faces[:, ::-1]
            inner.fix_normals()
            return trimesh.util.concatenate([outer, inner])
        except Exception as e:
            logger.error(f"Hollow failed: {e}")
            return None

    @staticmethod
    def chamfer(mesh: "trimesh.Trimesh",
                radius: float = 0.02) -> Optional["trimesh.Trimesh"]:
        """Approximate chamfer/bevel. Uses pymeshlab if available."""
        if mesh is None:
            return None

        if HAS_PYMESHLAB:
            return _pymeshlab_chamfer(mesh, radius)

        logger.info("Chamfer approximated via subdivision + smoothing (pymeshlab not available)")
        return MeshOperations.smooth(mesh, iterations=max(1, int(radius * 20)))


# =============================================================================
# MESH ANALYSIS — Compute physical and structural properties
# =============================================================================

class MeshAnalysis:
    """Analyze mesh geometry, physics, and structural properties."""

    @staticmethod
    def volume(mesh: "trimesh.Trimesh") -> Optional[float]:
        """Calculate signed volume."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            return float(mesh.volume)
        except Exception as e:
            logger.error(f"Volume calc failed: {e}")
            return None

    @staticmethod
    def surface_area(mesh: "trimesh.Trimesh") -> Optional[float]:
        """Calculate total surface area."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            return float(mesh.area)
        except Exception as e:
            logger.error(f"Surface area calc failed: {e}")
            return None

    @staticmethod
    def bounding_box(mesh: "trimesh.Trimesh") -> Optional[Dict[str, Any]]:
        """Return bounding box extents."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            bb = mesh.bounding_box.extents
            return {
                "width": float(bb[0]),
                "height": float(bb[1]),
                "depth": float(bb[2]),
                "min": mesh.bounds[0].tolist(),
                "max": mesh.bounds[1].tolist(),
            }
        except Exception as e:
            logger.error(f"Bounding box calc failed: {e}")
            return None

    @staticmethod
    def center_of_mass(mesh: "trimesh.Trimesh") -> Optional[List[float]]:
        """Calculate centroid (uniform density)."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            return mesh.centroid.tolist()
        except Exception as e:
            logger.error(f"Center of mass calc failed: {e}")
            return None

    @staticmethod
    def is_watertight(mesh: "trimesh.Trimesh") -> Optional[bool]:
        """Check if mesh is manifold/watertight."""
        if not HAS_TRIMESH or mesh is None:
            return None
        return bool(mesh.is_watertight)

    @staticmethod
    def face_count(mesh: "trimesh.Trimesh") -> Optional[int]:
        """Number of faces."""
        if mesh is None:
            return None
        return len(mesh.faces)

    @staticmethod
    def vertex_count(mesh: "trimesh.Trimesh") -> Optional[int]:
        """Number of vertices."""
        if mesh is None:
            return None
        return len(mesh.vertices)

    @staticmethod
    def moment_of_inertia(mesh: "trimesh.Trimesh") -> Optional[Dict[str, Any]]:
        """Calculate moment of inertia tensor and principal moments."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            inertia, com = mesh.volume_inertia_frame
            principal = mesh.volume_inertia_frame(principal=True)
            return {
                "inertia_tensor": inertia.tolist(),
                "center_of_mass": com.tolist() if com is not None else None,
                "principal_moments": principal.tolist() if isinstance(principal, np.ndarray) else None,
            }
        except Exception as e:
            logger.error(f"Moment of inertia calc failed: {e}")
            return None

    @staticmethod
    def center_of_gravity(mesh: "trimesh.Trimesh") -> Optional[List[float]]:
        """Center of gravity (same as center_of_mass for uniform density)."""
        return MeshAnalysis.center_of_mass(mesh)

    @staticmethod
    def estimate_mass(mesh: "trimesh.Trimesh",
                      density_kg_m3: float = 2700.0) -> Optional[float]:
        """Estimate mass from volume × density (default: aluminum)."""
        vol = MeshAnalysis.volume(mesh)
        if vol is None:
            return None
        return float(abs(vol) * density_kg_m3)

    @staticmethod
    def structural_estimate(mesh: "trimesh.Trimesh",
                            material: str = "aluminum") -> Optional[Dict[str, Any]]:
        """
        Rough structural estimate: max dimension, area, estimated mass,
        approximate stress under self-weight.
        """
        if not HAS_TRIMESH or mesh is None:
            return None

        materials_db = {
            "aluminum": {"density": 2700, "yield_strength": 276e6, "young_modulus": 69e9},
            "steel": {"density": 7850, "yield_strength": 250e6, "young_modulus": 200e9},
            "titanium": {"density": 4500, "yield_strength": 880e6, "young_modulus": 116e9},
            "carbon_fiber": {"density": 1600, "yield_strength": 600e6, "young_modulus": 150e9},
            "plastic": {"density": 1200, "yield_strength": 40e6, "young_modulus": 2e9},
        }

        mat = materials_db.get(material, materials_db["aluminum"])
        try:
            vol = abs(float(mesh.volume))
            area = float(mesh.area)
            mass = vol * mat["density"]
            extents = mesh.bounding_box.extents
            max_dim = float(max(extents))

            force = mass * 9.81
            stress = force / (area + 1e-10) if area > 0 else 0
            safety_factor = mat["yield_strength"] / (stress + 1e-10)

            return {
                "material": material,
                "volume_m3": vol,
                "surface_area_m2": area,
                "max_dimension_m": max_dim,
                "estimated_mass_kg": mass,
                "self_weight_N": force,
                "approx_stress_Pa": stress,
                "yield_strength_Pa": mat["yield_strength"],
                "safety_factor": min(safety_factor, 9999),
                "youngs_modulus_Pa": mat["young_modulus"],
            }
        except Exception as e:
            logger.error(f"Structural estimate failed: {e}")
            return None


# =============================================================================
# EXPORT UTILITIES — File I/O and scene management
# =============================================================================

class ExportUtils:
    """Import, export, merge, and scene management utilities."""

    @staticmethod
    def to_stl(mesh: "trimesh.Trimesh", path: str,
               subdir: str = "stl") -> Optional[str]:
        """Export mesh to STL file."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            out = _ensure_output_dir(subdir) / path
            mesh.export(str(out))
            logger.info(f"Exported STL: {out}")
            return str(out)
        except Exception as e:
            logger.error(f"STL export failed: {e}")
            return None

    @staticmethod
    def to_obj(mesh: "trimesh.Trimesh", path: str,
               subdir: str = "obj") -> Optional[str]:
        """Export mesh to OBJ file."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            out = _ensure_output_dir(subdir) / path
            mesh.export(str(out))
            logger.info(f"Exported OBJ: {out}")
            return str(out)
        except Exception as e:
            logger.error(f"OBJ export failed: {e}")
            return None

    @staticmethod
    def to_glb(mesh: "trimesh.Trimesh", path: str,
               subdir: str = "glb") -> Optional[str]:
        """Export mesh to GLB (binary glTF) file."""
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            out = _ensure_output_dir(subdir) / path
            mesh.export(str(out))
            logger.info(f"Exported GLB: {out}")
            return str(out)
        except Exception as e:
            logger.error(f"GLB export failed: {e}")
            return None

    @staticmethod
    def to_scad(mesh: "trimesh.Trimesh", path: str,
                subdir: str = "scad") -> Optional[str]:
        """
        Export mesh to OpenSCAD format (approximate — polyhedron definition).
        """
        if not HAS_TRIMESH or mesh is None:
            return None
        try:
            out = _ensure_output_dir(subdir) / path
            verts = mesh.vertices.tolist()
            faces = [f.tolist() for f in mesh.faces]
            lines = ["// Auto-generated OpenSCAD polyhedron from ZICORE", "polyhedron("]
            lines.append(f"  points = {verts},")
            lines.append(f"  faces = {faces},")
            lines.append("  convexity = 10")
            lines.append(");")
            out.write_text("\n".join(lines), encoding="utf-8")
            logger.info(f"Exported SCAD: {out}")
            return str(out)
        except Exception as e:
            logger.error(f"SCAD export failed: {e}")
            return None

    @staticmethod
    def from_stl(path: str) -> Optional["trimesh.Trimesh"]:
        """Load mesh from STL file."""
        if not HAS_TRIMESH:
            return None
        try:
            return trimesh.load(path, force="mesh")
        except Exception as e:
            logger.error(f"STL load failed: {e}")
            return None

    @staticmethod
    def from_obj(path: str) -> Optional["trimesh.Trimesh"]:
        """Load mesh from OBJ file."""
        if not HAS_TRIMESH:
            return None
        try:
            return trimesh.load(path, force="mesh")
        except Exception as e:
            logger.error(f"OBJ load failed: {e}")
            return None

    @staticmethod
    def from_glb(path: str) -> Optional["trimesh.Trimesh"]:
        """Load mesh from GLB file."""
        if not HAS_TRIMESH:
            return None
        try:
            result = trimesh.load(path)
            if isinstance(result, trimesh.Scene):
                return trimesh.util.concatenate(result.dump())
            return result
        except Exception as e:
            logger.error(f"GLB load failed: {e}")
            return None

    @staticmethod
    def merge_meshes(meshes: List["trimesh.Trimesh"]) -> Optional["trimesh.Trimesh"]:
        """Combine multiple meshes into one."""
        if not HAS_TRIMESH or not meshes:
            return None
        try:
            valid = [m for m in meshes if m is not None]
            if len(valid) == 1:
                return valid[0]
            return trimesh.util.concatenate(valid)
        except Exception as e:
            logger.error(f"Merge failed: {e}")
            return None

    @staticmethod
    def create_scene(objects_list: List[Dict[str, Any]]) -> Optional["trimesh.Scene"]:
        """
        Create a trimesh Scene from a list of objects.
        Each dict: {"mesh": Trimesh, "name": str, "transform": np.array}
        """
        if not HAS_TRIMESH:
            return None
        try:
            scene = trimesh.Scene()
            for i, obj in enumerate(objects_list):
                mesh = obj.get("mesh")
                name = obj.get("name", f"object_{i}")
                transform = obj.get("transform")
                if mesh is not None:
                    if transform is not None:
                        scene.add_geometry(mesh, node_name=name, transform=transform)
                    else:
                        scene.add_geometry(mesh, node_name=name)
            return scene
        except Exception as e:
            logger.error(f"Scene creation failed: {e}")
            return None


# =============================================================================
# AEROSPACE COMPONENTS — Pre-built parametric aerospace parts
# =============================================================================

class AerospaceComponents:
    """Pre-built aerospace component generators with parametric inputs."""

    @staticmethod
    def rocket(height: float = 10, radius: float = 1,
               stages: int = 3) -> Optional["trimesh.Trimesh"]:
        """Multi-stage launch vehicle."""
        if not HAS_TRIMESH:
            return None
        try:
            stage_h = height / stages
            parts = []
            for i in range(stages):
                s_radius = radius * (1 - 0.15 * i)
                s_h = stage_h * (1 + 0.1 * i)
                stage = cylinder(radius=s_radius, height=s_h, sections=32)
                stage.apply_translation([0, 0, (i + 0.5) * s_h])
                parts.append(stage)

            nose = AerospaceComponents.nose_cone(
                radius=radius * 0.85, height=height * 0.15, cone_type="ogive")
            nose.apply_translation([0, 0, height + height * 0.075])
            parts.append(nose)

            for i in range(stages):
                if i < stages - 1:
                    ring_r = radius * (1 - 0.15 * i)
                    ring = torus(major_radius=ring_r + 0.02, minor_radius=0.03,
                                 major_sections=32, minor_sections=8)
                    ring.apply_translation([0, 0, (i + 1) * stage_h])
                    parts.append(ring)

            return trimesh.util.concatenate(parts)
        except Exception as e:
            logger.error(f"Rocket generation failed: {e}")
            return None

    @staticmethod
    def satellite(body_size: float = 1, solar_panel_size: float = 3,
                  antenna_count: int = 2) -> Optional["trimesh.Trimesh"]:
        """Satellite with body, solar panels, and antennas."""
        if not HAS_TRIMESH:
            return None
        try:
            body = box(extents=[body_size, body_size, body_size * 0.8])
            parts = [body]

            panel_w = solar_panel_size
            panel_h = solar_panel_size * 0.6
            for side in [-1, 1]:
                panel = box(extents=[panel_w, 0.05, panel_h])
                panel.apply_translation([side * (body_size / 2 + panel_w / 2), 0, 0])
                parts.append(panel)

            for i in range(antenna_count):
                angle = (2 * math.pi * i) / antenna_count
                mast = cylinder(radius=0.03, height=0.5, sections=8)
                mast.apply_translation([
                    math.cos(angle) * (body_size * 0.4),
                    math.sin(angle) * (body_size * 0.4),
                    body_size * 0.4 + 0.25
                ])
                parts.append(mast)

            return trimesh.util.concatenate(parts)
        except Exception as e:
            logger.error(f"Satellite generation failed: {e}")
            return None

    @staticmethod
    def space_station(ring_radius: float = 5, hub_size: float = 1.5,
                      spoke_count: int = 6) -> Optional["trimesh.Trimesh"]:
        """Rotating space station with ring, hub, and spokes."""
        if not HAS_TRIMESH:
            return None
        try:
            ring = torus(major_radius=ring_radius, minor_radius=0.4,
                         major_sections=64, minor_sections=16)
            parts = [ring]

            hub = cylinder(radius=hub_size, height=hub_size * 2, sections=32)
            hub.apply_translation([0, 0, 0])
            parts.append(hub)

            for i in range(spoke_count):
                angle = (2 * math.pi * i) / spoke_count
                spoke = cylinder(radius=0.1, height=ring_radius * 0.9, sections=8)
                R = trimesh.transformations.rotation_matrix(angle, [0, 0, 1])
                spoke.apply_transform(R)
                spoke.apply_translation([
                    math.cos(angle) * ring_radius / 2,
                    math.sin(angle) * ring_radius / 2,
                    0
                ])
                parts.append(spoke)

            return trimesh.util.concatenate(parts)
        except Exception as e:
            logger.error(f"Space station generation failed: {e}")
            return None

    @staticmethod
    def drone(body_size: float = 0.5, arm_length: float = 1,
              rotor_size: float = 0.3) -> Optional["trimesh.Trimesh"]:
        """Quadcopter drone."""
        if not HAS_TRIMESH:
            return None
        try:
            body = cylinder(radius=body_size, height=0.15, sections=32)
            parts = [body]

            for i in range(4):
                angle = math.pi / 4 + (math.pi / 2) * i
                arm = cylinder(radius=0.05, height=arm_length, sections=8)
                arm.apply_transform(
                    trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
                arm.apply_translation([
                    math.cos(angle) * arm_length / 2,
                    math.sin(angle) * arm_length / 2,
                    0.1
                ])
                parts.append(arm)

                disc = cylinder(radius=rotor_size, height=0.02, sections=16)
                disc.apply_translation([
                    math.cos(angle) * arm_length,
                    math.sin(angle) * arm_length,
                    0.15
                ])
                parts.append(disc)

            return trimesh.util.concatenate(parts)
        except Exception as e:
            logger.error(f"Drone generation failed: {e}")
            return None

    @staticmethod
    def nozzle(throat_radius: float = 0.1, exit_radius: float = 0.3,
               length: float = 1, bell_ratio: float = 0.8) -> Optional["trimesh.Trimesh"]:
        """Rocket engine nozzle (bell shape)."""
        if not HAS_TRIMESH:
            return None
        try:
            segments = 32
            angles = np.linspace(0, math.pi / 2 * bell_ratio, segments)
            radii = np.linspace(throat_radius, exit_radius, segments)
            heights = np.sin(angles) * length

            verts = []
            for r, h in zip(radii, heights):
                ring_pts = []
                for j in range(24):
                    theta = 2 * math.pi * j / 24
                    ring_pts.append([r * math.cos(theta), r * math.sin(theta), h])
                verts.append(ring_pts)

            verts_flat = [pt for ring in verts for pt in ring]
            faces = []
            n = 24
            for i in range(segments - 1):
                for j in range(n):
                    v0 = i * n + j
                    v1 = i * n + (j + 1) % n
                    v2 = (i + 1) * n + j
                    v3 = (i + 1) * n + (j + 1) % n
                    faces.append([v0, v1, v3])
                    faces.append([v0, v3, v2])

            mesh = trimesh.Trimesh(vertices=np.array(verts_flat),
                                    faces=np.array(faces, dtype=np.int64))
            mesh.fix_normals()
            return mesh
        except Exception as e:
            logger.error(f"Nozzle generation failed: {e}")
            return None

    @staticmethod
    def fin(height: float = 1, chord: float = 0.5,
            sweep: float = 30) -> Optional["trimesh.Trimesh"]:
        """Aerodynamic fin/triangular plate."""
        if not HAS_TRIMESH:
            return None
        try:
            sweep_rad = math.radians(sweep)
            tip_offset = math.tan(sweep_rad) * height

            verts = np.array([
                [0, 0, 0],
                [chord, 0, 0],
                [chord - tip_offset, 0, height],
                [0, 0, height * 0.1],
                [0, 0.03, 0],
                [chord, 0.03, 0],
                [chord - tip_offset, 0.03, height],
                [0, 0.03, height * 0.1],
            ])
            faces = np.array([
                [0, 1, 2], [0, 2, 3],
                [4, 6, 5], [4, 7, 6],
                [0, 4, 5], [0, 5, 1],
                [1, 5, 6], [1, 6, 2],
                [2, 6, 7], [2, 7, 3],
                [3, 7, 4], [3, 4, 0],
            ], dtype=np.int64)
            return trimesh.Trimesh(vertices=verts, faces=faces)
        except Exception as e:
            logger.error(f"Fin generation failed: {e}")
            return None

    @staticmethod
    def landing_leg(length: float = 2,
                    spread_angle: float = 20) -> Optional["trimesh.Trimesh"]:
        """Landing gear leg with foot pad."""
        if not HAS_TRIMESH:
            return None
        try:
            parts = []
            for side in [-1, 1]:
                leg = cylinder(radius=0.04, height=length, sections=8)
                R = trimesh.transformations.rotation_matrix(
                    math.radians(spread_angle * side), [0, 1, 0])
                leg.apply_transform(R)
                foot = cylinder(radius=0.15, height=0.03, sections=16)
                foot.apply_translation([side * length * 0.3, -length * 0.9, 0])
                parts.extend([leg, foot])
            return trimesh.util.concatenate(parts)
        except Exception as e:
            logger.error(f"Landing leg generation failed: {e}")
            return None

    @staticmethod
    def solar_panel(width: float = 2, height: float = 1,
                    cell_count: int = 6) -> Optional["trimesh.Trimesh"]:
        """Solar panel array with cell grid lines."""
        if not HAS_TRIMESH:
            return None
        try:
            base = box(extents=[width, 0.04, height])
            parts = [base]

            cols = max(1, int(math.sqrt(cell_count)))
            rows = max(1, cell_count // cols)
            cell_w = (width * 0.9) / cols
            cell_h = (height * 0.9) / rows

            for r in range(rows):
                for c in range(cols):
                    x = -width / 2 + width * 0.05 + c * cell_w + cell_w / 2
                    z = -height / 2 + height * 0.05 + r * cell_h + cell_h / 2
                    cell = box(extents=[cell_w * 0.9, 0.005, cell_h * 0.9])
                    cell.apply_translation([x, 0.025, z])
                    parts.append(cell)

            strut = cylinder(radius=0.03, height=0.3, sections=8)
            strut.apply_transform(
                trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
            parts.append(strut)

            return trimesh.util.concatenate(parts)
        except Exception as e:
            logger.error(f"Solar panel generation failed: {e}")
            return None

    @staticmethod
    def antenna(dish_radius: float = 0.5,
                mast_height: float = 1) -> Optional["trimesh.Trimesh"]:
        """Parabolic dish antenna."""
        if not HAS_TRIMESH:
            return None
        try:
            dish = cylinder(radius=dish_radius, height=0.1, sections=32)
            dish.apply_translation([0, 0, mast_height])
            inner = cone(radius=dish_radius * 0.9, height=0.08, sections=32)
            inner.apply_translation([0, 0, mast_height + 0.01])
            mast = cylinder(radius=0.04, height=mast_height, sections=8)
            feed = cylinder(radius=0.02, height=0.2, sections=8)
            feed.apply_translation([0, 0, mast_height + 0.15])
            return trimesh.util.concatenate([dish, inner, mast, feed])
        except Exception as e:
            logger.error(f"Antenna generation failed: {e}")
            return None

    @staticmethod
    def habitat(diameter: float = 4, height: float = 3,
                levels: int = 2) -> Optional["trimesh.Trimesh"]:
        """Habitat module (cylindrical with dome)."""
        if not HAS_TRIMESH:
            return None
        try:
            parts = []
            for i in range(levels):
                level = cylinder(radius=diameter / 2, height=height / levels, sections=32)
                level.apply_translation([0, 0, i * (height / levels) + height / levels / 2])
                parts.append(level)

            dome = icosphere(subdivisions=2, radius=diameter / 2)
            dome.vertices[:, 2] = np.abs(dome.vertices[:, 2]) * 0.4
            dome.apply_translation([0, 0, height])
            parts.append(dome)

            window = cylinder(radius=0.3, height=0.1, sections=16)
            window.apply_transform(
                trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
            window.apply_translation([diameter / 2, 0, height * 0.6])
            parts.append(window)

            return trimesh.util.concatenate(parts)
        except Exception as e:
            logger.error(f"Habitat generation failed: {e}")
            return None

    @staticmethod
    def rover(wheel_base: float = 2, width: float = 1.5,
              height: float = 1) -> Optional["trimesh.Trimesh"]:
        """Surface exploration rover."""
        if not HAS_TRIMESH:
            return None
        try:
            body = box(extents=[wheel_base * 0.6, width * 0.8, height * 0.4])
            body.apply_translation([0, 0, height * 0.5])
            parts = [body]

            mast = cylinder(radius=0.03, height=height * 0.6, sections=8)
            mast.apply_translation([wheel_base * 0.2, 0, height * 0.7 + height * 0.3])
            parts.append(mast)

            cam = box(extents=[0.15, 0.1, 0.1])
            cam.apply_translation([wheel_base * 0.2, 0, height + height * 0.3])
            parts.append(cam)

            wheel_r = height * 0.15
            positions = [
                [wheel_base * 0.25, width * 0.45, wheel_r],
                [wheel_base * 0.25, -width * 0.45, wheel_r],
                [-wheel_base * 0.25, width * 0.45, wheel_r],
                [-wheel_base * 0.25, -width * 0.45, wheel_r],
            ]
            for pos in positions:
                wheel = cylinder(radius=wheel_r, height=0.15, sections=16)
                wheel.apply_transform(
                    trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
                wheel.apply_translation(pos)
                parts.append(wheel)

            return trimesh.util.concatenate(parts)
        except Exception as e:
            logger.error(f"Rover generation failed: {e}")
            return None

    @staticmethod
    def fuel_tank(radius: float = 0.5, height: float = 2,
                  tank_type: str = "cylindrical") -> Optional["trimesh.Trimesh"]:
        """Fuel tank — cylindrical or spherical."""
        if not HAS_TRIMESH:
            return None
        try:
            if tank_type == "spherical":
                return icosphere(subdivisions=3, radius=radius)

            body = cylinder(radius=radius, height=height, sections=32)
            cap_top = hemisphere(radius=radius, sections=32)
            cap_top.apply_translation([0, 0, height / 2])
            cap_bot = hemisphere(radius=radius, sections=32)
            cap_bot.apply_transform(
                trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
            cap_bot.apply_translation([0, 0, -height / 2])

            return trimesh.util.concatenate([body, cap_top, cap_bot])
        except Exception as e:
            logger.error(f"Fuel tank generation failed: {e}")
            return None

    @staticmethod
    def payload_bay(width: float = 2, height: float = 1.5,
                    depth: float = 3) -> Optional["trimesh.Trimesh"]:
        """Payload bay / cargo hold."""
        if not HAS_TRIMESH:
            return None
        try:
            outer = box(extents=[width, depth, height])
            inner = box(extents=[width * 0.9, depth * 0.9, height * 0.95])
            result = outer.difference(inner)
            if result is None:
                return outer
            return result
        except Exception as e:
            logger.error(f"Payload bay generation failed: {e}")
            return None

    @staticmethod
    def engine(radius: float = 0.5, length: float = 1.5,
               engine_type: str = "bell") -> Optional["trimesh.Trimesh"]:
        """Rocket engine (bell, aerospike, or ion)."""
        if not HAS_TRIMESH:
            return None
        try:
            chamber = cylinder(radius=radius, height=length * 0.6, sections=32)
            chamber.apply_translation([0, 0, length * 0.2])

            nozzle = AerospaceComponents.nozzle(
                throat_radius=radius * 0.4,
                exit_radius=radius * 1.2,
                length=length * 0.4,
                bell_ratio=0.8
            )
            nozzle.apply_translation([0, 0, -length * 0.1])

            injector = cylinder(radius=radius * 0.8, height=0.1, sections=32)
            injector.apply_translation([0, 0, length * 0.55])

            return trimesh.util.concatenate([chamber, nozzle, injector])
        except Exception as e:
            logger.error(f"Engine generation failed: {e}")
            return None

    @staticmethod
    def nose_cone(radius: float = 0.5, height: float = 1.5,
                  cone_type: str = "ogive", **kwargs) -> Optional["trimesh.Trimesh"]:
        """Nose cone — ogive, conical, or parabolic."""
        if not HAS_TRIMESH:
            return None
        try:
            if cone_type == "conical":
                return cone(radius=radius, height=height, sections=32)

            segments = 32
            if cone_type == "ogive":
                t = np.linspace(0, 1, segments)
                r_profile = radius * np.sin(np.pi * t / 2)
            else:
                t = np.linspace(0, 1, segments)
                r_profile = radius * np.sqrt(t)

            verts = []
            for i, (r, z) in enumerate(zip(r_profile, np.linspace(0, height, segments))):
                for j in range(24):
                    theta = 2 * math.pi * j / 24
                    verts.append([r * math.cos(theta), r * math.sin(theta), z])

            faces = []
            n = 24
            for i in range(segments - 1):
                for j in range(n):
                    v0 = i * n + j
                    v1 = i * n + (j + 1) % n
                    v2 = (i + 1) * n + j
                    v3 = (i + 1) * n + (j + 1) % n
                    faces.append([v0, v1, v3])
                    faces.append([v0, v3, v2])

            return trimesh.Trimesh(
                vertices=np.array(verts),
                faces=np.array(faces, dtype=np.int64)
            )
        except Exception as e:
            logger.error(f"Nose cone generation failed: {e}")
            return None


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _make_octahedron(radius: float = 0.5) -> Optional["trimesh.Trimesh"]:
    """Create a regular octahedron."""
    r = radius
    verts = np.array([
        [r, 0, 0], [-r, 0, 0],
        [0, r, 0], [0, -r, 0],
        [0, 0, r], [0, 0, -r],
    ])
    faces = np.array([
        [0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4],
        [0, 3, 5], [3, 1, 5], [1, 2, 5], [2, 0, 5],
    ], dtype=np.int64)
    return trimesh.Trimesh(vertices=verts, faces=faces)


def _make_dodecahedron(radius: float = 0.5) -> Optional["trimesh.Trimesh"]:
    """Create a regular dodecahedron."""
    phi = (1 + math.sqrt(5)) / 2
    a = radius / math.sqrt(3)
    b = a / phi
    c = a * (2 - phi)

    verts = []
    for x, y, z in [
        (1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1),
        (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1),
    ]:
        verts.append([x * a, y * a, z * a])

    for x, y, z in [
        (0, phi, 1/phi), (0, phi, -1/phi), (0, -phi, 1/phi), (0, -phi, -1/phi),
        (1/phi, 0, phi), (1/phi, 0, -phi), (-1/phi, 0, phi), (-1/phi, 0, -phi),
        (phi, 1/phi, 0), (phi, -1/phi, 0), (-phi, 1/phi, 0), (-phi, -1/phi, 0),
    ]:
        verts.append([x * b, y * b, z * b])

    verts_arr = np.array(verts)
    try:
        hull = trimesh.convex.hull(verts_arr)
        return hull
    except Exception:
        return _make_octahedron(radius)


def _make_plane(width: float = 1, height: float = 1,
                w_sections: int = 10, h_sections: int = 10) -> Optional["trimesh.Trimesh"]:
    """Create a subdivided plane."""
    verts = []
    faces = []
    for i in range(h_sections + 1):
        for j in range(w_sections + 1):
            x = (j / w_sections - 0.5) * width
            y = (i / h_sections - 0.5) * height
            verts.append([x, y, 0])

    n = w_sections + 1
    for i in range(h_sections):
        for j in range(w_sections):
            v0 = i * n + j
            v1 = v0 + 1
            v2 = (i + 1) * n + j
            v3 = v2 + 1
            faces.append([v0, v1, v3])
            faces.append([v0, v3, v2])

    return trimesh.Trimesh(
        vertices=np.array(verts),
        faces=np.array(faces, dtype=np.int64)
    )


def hemisphere(radius: float = 0.5, sections: int = 32) -> Optional["trimesh.Trimesh"]:
    """Create a hemisphere (half sphere)."""
    if not HAS_TRIMESH:
        return None
    sphere = icosphere(subdivisions=3, radius=radius)
    sphere.vertices[:, 2] = np.abs(sphere.vertices[:, 2])
    return sphere


def _fallback_concatenate(mesh_a, mesh_b):
    """Fallback: concatenate meshes when boolean ops fail."""
    try:
        return trimesh.util.concatenate([mesh_a, mesh_b])
    except Exception:
        return mesh_a


def _laplacian_smooth_step(mesh: "trimesh.Trimesh") -> "trimesh.Trimesh":
    """Single step of Laplacian smoothing."""
    verts = mesh.vertices.copy()
    neighbors = mesh.vertex_neighbors
    n_verts = len(verts)
    new_verts = verts.copy()
    for i in range(n_verts):
        nbrs = neighbors[i]
        if len(nbrs) > 0:
            avg = np.mean(verts[nbrs], axis=0)
            new_verts[i] = (verts[i] + avg) / 2
    result = mesh.copy()
    result.vertices = new_verts
    return result


def _pymeshlab_smooth(mesh: "trimesh.Trimesh", iterations: int) -> "trimesh.Trimesh":
    """Smooth using pymeshlab Laplacian."""
    if not HAS_PYMESHLAB:
        return mesh.copy()
    try:
        ms = pymeshlab.MeshSet()
        ms.add_new_mesh(
            np.array(mesh.vertices, dtype=np.float64),
            np.array(mesh.faces, dtype=np.int32)
        )
        ms.apply_coord_laplacian_smoothing(
            stepsmoothnum=iterations,
            weight=0.5,
            cottangentsweighting=True
        )
        m = ms.current_mesh()
        return trimesh.Trimesh(
            vertices=m.vertex_matrix(),
            faces=m.face_matrix()
        )
    except Exception as e:
        logger.warning(f"pymeshlab smooth failed: {e}")
        return mesh.copy()


def _pymeshlab_decimate(mesh: "trimesh.Trimesh",
                        target_faces: int) -> Optional["trimesh.Trimesh"]:
    """Decimate using pymeshlab."""
    if not HAS_PYMESHLAB:
        return mesh.copy()
    try:
        ms = pymeshlab.MeshSet()
        ms.add_new_mesh(
            np.array(mesh.vertices, dtype=np.float64),
            np.array(mesh.faces, dtype=np.int32)
        )
        ms.meshing_decimation_quadric_edge_collapse(targetfacenum=target_faces)
        m = ms.current_mesh()
        return trimesh.Trimesh(
            vertices=m.vertex_matrix(),
            faces=m.face_matrix()
        )
    except Exception as e:
        logger.warning(f"pymeshlab decimate failed: {e}")
        return mesh.copy()


def _pymeshlab_chamfer(mesh: "trimesh.Trimesh",
                       radius: float) -> Optional["trimesh.Trimesh"]:
    """Approximate chamfer using pymeshlab smoothing."""
    if not HAS_PYMESHLAB:
        return mesh.copy()
    try:
        ms = pymeshlab.MeshSet()
        ms.add_new_mesh(
            np.array(mesh.vertices, dtype=np.float64),
            np.array(mesh.faces, dtype=np.int32)
        )
        ms.apply_coord_laplacian_smoothing(
            stepsmoothnum=1,
            weight=0.5,
            cottangentsweighting=True
        )
        m = ms.current_mesh()
        return trimesh.Trimesh(
            vertices=m.vertex_matrix(),
            faces=m.face_matrix()
        )
    except Exception as e:
        logger.warning(f"pymeshlab chamfer failed: {e}")
        return mesh.copy()


# =============================================================================
# MODULE-LEVEL CONVENIENCE FUNCTIONS
# =============================================================================

def quick_generate(prompt: str, save: bool = False) -> Optional["trimesh.Trimesh"]:
    """Generate mesh from prompt, optionally save to output/."""
    mesh = MeshGenerator.generate_from_prompt(prompt)
    if mesh is not None and save:
        name = prompt.replace(" ", "_")[:40]
        ExportUtils.to_stl(mesh, f"{name}.stl")
    return mesh


def quick_export(mesh: "trimesh.Trimesh", filename: str,
                 formats: List[str] = None) -> Dict[str, str]:
    """Export mesh to multiple formats. Returns dict of format → path."""
    if formats is None:
        formats = ["stl", "obj", "glb"]
    results = {}
    exporters = {"stl": ExportUtils.to_stl, "obj": ExportUtils.to_obj,
                 "glb": ExportUtils.to_glb, "scad": ExportUtils.to_scad}
    for fmt in formats:
        if fmt in exporters and mesh is not None:
            path = exporters[fmt](mesh, f"{filename}.{fmt}")
            if path:
                results[fmt] = path
    return results

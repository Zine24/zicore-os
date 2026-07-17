"""
ZICORE OutPreview — Central Output/Preview Panel

Manages the latest generated content for viewing, editing,
saving to library, and sending to 3D printing or VR simulation.

This module provides:
- Current generation tracking with history
- Mesh editing operations (scale, rotate, boolean, smooth, etc.)
- 3D print export with validation and cost estimation
- VR simulation scene export

Author: ZineMotion Foundation — Aerospace Division
Version: 5.0.0
"""

import json
import logging
import time
import uuid
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union
from datetime import datetime

logger = logging.getLogger("zicore.outpreview")

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
EXPORT_DIR = PROJECT_ROOT / "data" / "exports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# Try importing trimesh for mesh operations
try:
    import trimesh
    import numpy as np
    HAS_TRIMESH = True
except ImportError:
    HAS_TRIMESH = False
    logger.warning("trimesh not available — mesh editing operations disabled")


# =============================================================================
# MESH EDITING OPERATIONS
# =============================================================================

class MeshEditor:
    """Collection of mesh editing operations using trimesh."""

    @staticmethod
    def _load_mesh(mesh_path: str) -> Optional[Any]:
        """Load a mesh from file path."""
        if not HAS_TRIMESH:
            logger.error("trimesh not available")
            return None

        path = Path(mesh_path)
        if not path.is_file():
            logger.error(f"Mesh file not found: {mesh_path}")
            return None

        try:
            mesh = trimesh.load(str(path), force="mesh")
            return mesh
        except Exception as e:
            logger.error(f"Failed to load mesh: {e}")
            return None

    @staticmethod
    def _save_mesh(mesh: Any, output_path: str) -> bool:
        """Save a mesh to file."""
        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            mesh.export(str(path))
            logger.info(f"Mesh saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save mesh: {e}")
            return False

    @classmethod
    def scale(cls, mesh_path: str, factor: Union[float, List[float]],
              output_path: Optional[str] = None) -> Optional[Dict]:
        """Uniform or non-uniform scale a mesh.

        Args:
            mesh_path: Path to input mesh
            factor: Scale factor (float for uniform, [x,y,z] for non-uniform)
            output_path: Optional output path (generates one if None)

        Returns:
            Dict with output_path and metadata, or None on failure
        """
        mesh = cls._load_mesh(mesh_path)
        if mesh is None:
            return None

        if isinstance(factor, (int, float)):
            scale_factor = [factor, factor, factor]
        else:
            scale_factor = list(factor)

        try:
            mesh.apply_scale(scale_factor)

            if output_path is None:
                output_path = str(OUTPUT_DIR / f"scaled_{uuid.uuid4().hex[:8]}.stl")

            cls._save_mesh(mesh, output_path)
            return {
                "output_path": output_path,
                "operation": "scale",
                "parameters": {"factor": scale_factor},
                "vertices": len(mesh.vertices),
                "faces": len(mesh.faces),
                "bounds": mesh.bounds.tolist() if hasattr(mesh, 'bounds') else None,
            }
        except Exception as e:
            logger.error(f"Scale operation failed: {e}")
            return None

    @classmethod
    def rotate(cls, mesh_path: str, axis: str, angle: float,
               output_path: Optional[str] = None) -> Optional[Dict]:
        """Rotate a mesh around an axis.

        Args:
            mesh_path: Path to input mesh
            axis: Rotation axis ('x', 'y', or 'z')
            angle: Rotation angle in degrees
            output_path: Optional output path

        Returns:
            Dict with output_path and metadata
        """
        mesh = cls._load_mesh(mesh_path)
        if mesh is None:
            return None

        axis_map = {
            'x': [1, 0, 0],
            'y': [0, 1, 0],
            'z': [0, 0, 1],
        }

        if axis.lower() not in axis_map:
            logger.error(f"Invalid axis: {axis}")
            return None

        try:
            rotation_matrix = trimesh.transformations.rotation_matrix(
                np.radians(angle), axis_map[axis.lower()]
            )
            mesh.apply_transform(rotation_matrix)

            if output_path is None:
                output_path = str(OUTPUT_DIR / f"rotated_{uuid.uuid4().hex[:8]}.stl")

            cls._save_mesh(mesh, output_path)
            return {
                "output_path": output_path,
                "operation": "rotate",
                "parameters": {"axis": axis, "angle": angle},
                "vertices": len(mesh.vertices),
                "faces": len(mesh.faces),
            }
        except Exception as e:
            logger.error(f"Rotate operation failed: {e}")
            return None

    @classmethod
    def translate(cls, mesh_path: str, offset: List[float],
                  output_path: Optional[str] = None) -> Optional[Dict]:
        """Translate a mesh in space.

        Args:
            mesh_path: Path to input mesh
            offset: Translation offset [x, y, z]
            output_path: Optional output path

        Returns:
            Dict with output_path and metadata
        """
        mesh = cls._load_mesh(mesh_path)
        if mesh is None:
            return None

        try:
            mesh.apply_translation(offset)

            if output_path is None:
                output_path = str(OUTPUT_DIR / f"translated_{uuid.uuid4().hex[:8]}.stl")

            cls._save_mesh(mesh, output_path)
            return {
                "output_path": output_path,
                "operation": "translate",
                "parameters": {"offset": offset},
                "vertices": len(mesh.vertices),
                "faces": len(mesh.faces),
            }
        except Exception as e:
            logger.error(f"Translate operation failed: {e}")
            return None

    @classmethod
    def mirror(cls, mesh_path: str, axis: str,
               output_path: Optional[str] = None) -> Optional[Dict]:
        """Mirror a mesh across an axis.

        Args:
            mesh_path: Path to input mesh
            axis: Mirror axis ('x', 'y', or 'z')
            output_path: Optional output path

        Returns:
            Dict with output_path and metadata
        """
        mesh = cls._load_mesh(mesh_path)
        if mesh is None:
            return None

        axis_map = {'x': 0, 'y': 1, 'z': 2}
        if axis.lower() not in axis_map:
            logger.error(f"Invalid axis: {axis}")
            return None

        try:
            vertices = mesh.vertices.copy()
            axis_idx = axis_map[axis.lower()]
            vertices[:, axis_idx] *= -1

            if mesh.faces is not None and len(mesh.faces) > 0:
                faces = mesh.faces.copy()
                faces = faces[:, ::-1]
            else:
                faces = None

            mirrored = trimesh.Trimesh(vertices=vertices, faces=faces)

            if output_path is None:
                output_path = str(OUTPUT_DIR / f"mirrored_{uuid.uuid4().hex[:8]}.stl")

            cls._save_mesh(mirrored, output_path)
            return {
                "output_path": output_path,
                "operation": "mirror",
                "parameters": {"axis": axis},
                "vertices": len(mirrored.vertices),
                "faces": len(mirrored.faces) if mirrored.faces is not None else 0,
            }
        except Exception as e:
            logger.error(f"Mirror operation failed: {e}")
            return None

    @classmethod
    def union(cls, mesh_path_a: str, mesh_path_b: str,
              output_path: Optional[str] = None) -> Optional[Dict]:
        """Boolean union of two meshes.

        Args:
            mesh_path_a: Path to first mesh
            mesh_path_b: Path to second mesh
            output_path: Optional output path

        Returns:
            Dict with output_path and metadata
        """
        if not HAS_TRIMESH:
            return None

        mesh_a = cls._load_mesh(mesh_path_a)
        mesh_b = cls._load_mesh(mesh_path_b)
        if mesh_a is None or mesh_b is None:
            return None

        try:
            result = mesh_a.union(mesh_b)

            if output_path is None:
                output_path = str(OUTPUT_DIR / f"union_{uuid.uuid4().hex[:8]}.stl")

            cls._save_mesh(result, output_path)
            return {
                "output_path": output_path,
                "operation": "union",
                "parameters": {"mesh_a": mesh_path_a, "mesh_b": mesh_path_b},
                "vertices": len(result.vertices),
                "faces": len(result.faces) if result.faces is not None else 0,
            }
        except Exception as e:
            logger.error(f"Boolean union failed: {e}")
            return None

    @classmethod
    def difference(cls, mesh_path_a: str, mesh_path_b: str,
                   output_path: Optional[str] = None) -> Optional[Dict]:
        """Boolean difference (A - B).

        Args:
            mesh_path_a: Path to first mesh
            mesh_path_b: Path to second mesh (subtracted from A)
            output_path: Optional output path

        Returns:
            Dict with output_path and metadata
        """
        mesh_a = cls._load_mesh(mesh_path_a)
        mesh_b = cls._load_mesh(mesh_path_b)
        if mesh_a is None or mesh_b is None:
            return None

        try:
            result = mesh_a.difference(mesh_b)

            if output_path is None:
                output_path = str(OUTPUT_DIR / f"difference_{uuid.uuid4().hex[:8]}.stl")

            cls._save_mesh(result, output_path)
            return {
                "output_path": output_path,
                "operation": "difference",
                "parameters": {"mesh_a": mesh_path_a, "mesh_b": mesh_path_b},
                "vertices": len(result.vertices),
                "faces": len(result.faces) if result.faces is not None else 0,
            }
        except Exception as e:
            logger.error(f"Boolean difference failed: {e}")
            return None

    @classmethod
    def intersection(cls, mesh_path_a: str, mesh_path_b: str,
                     output_path: Optional[str] = None) -> Optional[Dict]:
        """Boolean intersection (common volume).

        Args:
            mesh_path_a: Path to first mesh
            mesh_path_b: Path to second mesh
            output_path: Optional output path

        Returns:
            Dict with output_path and metadata
        """
        mesh_a = cls._load_mesh(mesh_path_a)
        mesh_b = cls._load_mesh(mesh_path_b)
        if mesh_a is None or mesh_b is None:
            return None

        try:
            result = mesh_a.intersection(mesh_b)

            if output_path is None:
                output_path = str(OUTPUT_DIR / f"intersection_{uuid.uuid4().hex[:8]}.stl")

            cls._save_mesh(result, output_path)
            return {
                "output_path": output_path,
                "operation": "intersection",
                "parameters": {"mesh_a": mesh_path_a, "mesh_b": mesh_path_b},
                "vertices": len(result.vertices),
                "faces": len(result.faces) if result.faces is not None else 0,
            }
        except Exception as e:
            logger.error(f"Boolean intersection failed: {e}")
            return None

    @classmethod
    def smooth(cls, mesh_path: str, iterations: int = 5,
               output_path: Optional[str] = None) -> Optional[Dict]:
        """Laplacian smoothing.

        Args:
            mesh_path: Path to input mesh
            iterations: Number of smoothing iterations (1-50)
            output_path: Optional output path

        Returns:
            Dict with output_path and metadata
        """
        mesh = cls._load_mesh(mesh_path)
        if mesh is None:
            return None

        try:
            iterations = max(1, min(50, iterations))
            mesh = trimesh.smoothing.filter_humphrey(mesh, iterations=iterations)

            if output_path is None:
                output_path = str(OUTPUT_DIR / f"smooth_{uuid.uuid4().hex[:8]}.stl")

            cls._save_mesh(mesh, output_path)
            return {
                "output_path": output_path,
                "operation": "smooth",
                "parameters": {"iterations": iterations},
                "vertices": len(mesh.vertices),
                "faces": len(mesh.faces) if mesh.faces is not None else 0,
            }
        except Exception as e:
            logger.error(f"Smooth operation failed: {e}")
            return None

    @classmethod
    def decimate(cls, mesh_path: str, target_faces: int = 1000,
                 output_path: Optional[str] = None) -> Optional[Dict]:
        """Reduce polygon count (decimation).

        Args:
            mesh_path: Path to input mesh
            target_faces: Target number of faces
            output_path: Optional output path

        Returns:
            Dict with output_path and metadata
        """
        mesh = cls._load_mesh(mesh_path)
        if mesh is None:
            return None

        original_faces = len(mesh.faces) if mesh.faces is not None else 0

        try:
            if HAS_TRIMESH and hasattr(trimesh, 'simplify'):
                mesh = mesh.simplify_quadric_decimation(target_faces)

            if output_path is None:
                output_path = str(OUTPUT_DIR / f"decimated_{uuid.uuid4().hex[:8]}.stl")

            cls._save_mesh(mesh, output_path)
            new_faces = len(mesh.faces) if mesh.faces is not None else 0
            return {
                "output_path": output_path,
                "operation": "decimate",
                "parameters": {"target_faces": target_faces},
                "original_faces": original_faces,
                "new_faces": new_faces,
                "reduction_pct": round((1 - new_faces / original_faces) * 100, 1) if original_faces > 0 else 0,
                "vertices": len(mesh.vertices),
            }
        except Exception as e:
            logger.error(f"Decimate operation failed: {e}")
            return None

    @classmethod
    def analyze(cls, mesh_path: str) -> Optional[Dict]:
        """Analyze mesh properties.

        Args:
            mesh_path: Path to input mesh

        Returns:
            Dict with analysis results
        """
        mesh = cls._load_mesh(mesh_path)
        if mesh is None:
            return None

        try:
            bounds = mesh.bounds
            extents = bounds[1] - bounds[0]
            center = mesh.centroid

            result = {
                "vertices": len(mesh.vertices),
                "faces": len(mesh.faces) if mesh.faces is not None else 0,
                "volume": float(mesh.volume) if mesh.is_volume else None,
                "surface_area": float(mesh.area),
                "is_watertight": bool(mesh.is_watertight),
                "is_volume": bool(mesh.is_volume),
                "bounds_min": bounds[0].tolist(),
                "bounds_max": bounds[1].tolist(),
                "extents": extents.tolist(),
                "center": center.tolist(),
                "diameter": float(np.max(extents)),
            }

            if mesh.is_watertight and mesh.is_volume:
                result["inertia"] = mesh.moment_inertia.tolist() if hasattr(mesh, 'moment_inertia') else None
                result["center_of_mass"] = mesh.center_mass.tolist() if hasattr(mesh, 'center_of_mass') else None

            return result
        except Exception as e:
            logger.error(f"Mesh analysis failed: {e}")
            return None


# =============================================================================
# PRINT EXPORT
# =============================================================================

class PrintExporter:
    """Handles export of meshes for 3D printing."""

    # Minimum wall thickness recommendations per material (mm)
    MIN_WALL_THICKNESS = {
        "PLA": 0.8,
        "PETG": 0.8,
        "ABS": 0.8,
        "TPU": 0.6,
        "Nylon": 0.6,
        "Resin": 0.5,
    }

    # Default slicer settings per printer profile
    SLICER_PRESETS = {
        "ender3": {
            "printer": "Ender 3",
            "nozzle": 0.4,
            "layer_height": 0.2,
            "first_layer_height": 0.28,
            "infill": 20,
            "infill_pattern": "grid",
            "wall_thickness": 1.2,
            "top_layers": 4,
            "bottom_layers": 4,
            "print_speed": 50,
            "travel_speed": 150,
            "retraction_distance": 5,
            "retraction_speed": 45,
            "bed_temp": 60,
            "nozzle_temp": 200,
            "fan_speed": 100,
            "support_enabled": False,
            "support_angle": 50,
        },
        "voron24": {
            "printer": "Voron 2.4",
            "nozzle": 0.4,
            "layer_height": 0.2,
            "first_layer_height": 0.28,
            "infill": 15,
            "infill_pattern": "gyroid",
            "wall_thickness": 1.2,
            "top_layers": 5,
            "bottom_layers": 4,
            "print_speed": 120,
            "travel_speed": 300,
            "retraction_distance": 0.8,
            "retraction_speed": 35,
            "bed_temp": 110,
            "nozzle_temp": 250,
            "fan_speed": 100,
            "support_enabled": False,
            "support_angle": 50,
        },
        "prusa_mk4": {
            "printer": "Prusa MK4",
            "nozzle": 0.4,
            "layer_height": 0.2,
            "first_layer_height": 0.2,
            "infill": 15,
            "infill_pattern": "gyroid",
            "wall_thickness": 1.2,
            "top_layers": 5,
            "bottom_layers": 5,
            "print_speed": 80,
            "travel_speed": 150,
            "retraction_distance": 0.8,
            "retraction_speed": 35,
            "bed_temp": 60,
            "nozzle_temp": 215,
            "fan_speed": 100,
            "support_enabled": False,
            "support_angle": 50,
        },
        "z1_corexy": {
            "printer": "Z1 CoreXY",
            "nozzle": 0.4,
            "layer_height": 0.2,
            "first_layer_height": 0.28,
            "infill": 20,
            "infill_pattern": "grid",
            "wall_thickness": 1.2,
            "top_layers": 4,
            "bottom_layers": 4,
            "print_speed": 80,
            "travel_speed": 200,
            "retraction_distance": 1.2,
            "retraction_speed": 40,
            "bed_temp": 60,
            "nozzle_temp": 200,
            "fan_speed": 100,
            "support_enabled": False,
            "support_angle": 50,
        },
    }

    @classmethod
    def validate_for_print(cls, mesh_path: str, material: str = "PLA") -> Optional[Dict]:
        """Validate a mesh for 3D printing.

        Checks manifoldness, minimum wall thickness, overhangs,
        and general printability.

        Args:
            mesh_path: Path to the mesh file
            material: Material to validate against

        Returns:
            Dict with validation results
        """
        if not HAS_TRIMESH:
            return {"valid": False, "error": "trimesh not available"}

        path = Path(mesh_path)
        if not path.is_file():
            return {"valid": False, "error": f"File not found: {mesh_path}"}

        try:
            mesh = trimesh.load(str(path), force="mesh")

            issues = []
            warnings = []

            # Check watertight (manifold)
            is_watertight = bool(mesh.is_watertight)
            if not is_watertight:
                issues.append("Mesh is not watertight (non-manifold)")

            # Check face normals
            if not mesh.is_winding_consistent:
                warnings.append("Inconsistent face winding detected")

            # Check degenerate faces
            if mesh.faces is not None and len(mesh.faces) > 0:
                areas = trimesh.triangles.area(mesh.vertices[mesh.faces])
                degenerate = np.sum(areas < 1e-10)
                if degenerate > 0:
                    issues.append(f"{degenerate} degenerate faces found")

            # Check minimum wall thickness estimate
            min_wall = cls.MIN_WALL_THICKNESS.get(material, 0.8)
            extents = mesh.extents
            min_extent = min(extents)
            if min_extent < min_wall:
                warnings.append(
                    f"Minimum extent ({min_extent:.2f}mm) may be below "
                    f"recommended wall thickness ({min_wall}mm) for {material}"
                )

            # Check overhangs (approximate)
            overhang_issues = cls._check_overhangs(mesh)
            if overhang_issues:
                warnings.extend(overhang_issues)

            # Check scale (if too large or too small)
            bbox_volume = np.prod(extents)
            if bbox_volume > 1e6:
                warnings.append(f"Model is very large ({bbox_volume:.0f}mm³)")
            elif bbox_volume < 0.001:
                warnings.append("Model appears very small — check units (expected mm)")

            # Analysis data
            analysis = MeshEditor.analyze(mesh_path) or {}

            return {
                "valid": len(issues) == 0,
                "watertight": is_watertight,
                "winding_consistent": bool(mesh.is_winding_consistent),
                "issues": issues,
                "warnings": warnings,
                "material": material,
                "recommended_min_wall": min_wall,
                "volume_cm3": round(float(mesh.volume) / 1000, 2) if mesh.is_volume else None,
                "surface_area_cm2": round(float(mesh.area) / 100, 2) if hasattr(mesh, 'area') else None,
                "dimensions_mm": extents.tolist(),
                "analysis": analysis,
            }

        except Exception as e:
            logger.error(f"Print validation failed: {e}")
            return {"valid": False, "error": str(e)}

    @classmethod
    def _check_overhangs(cls, mesh: Any, threshold_angle: float = 45.0) -> List[str]:
        """Check for unsupported overhangs."""
        issues = []
        try:
            face_normals = mesh.face_normals
            gravity = np.array([0, 0, -1])

            dot_products = np.dot(face_normals, gravity)
            overhang_angles = np.degrees(np.arccos(np.clip(-dot_products, -1, 1)))

            overhanging = np.sum(overhang_angles > threshold_angle)
            if overhanging > 0:
                pct = overhanging / len(face_normals) * 100
                issues.append(
                    f"{overhanging} faces ({pct:.1f}%) exceed {threshold_angle}° overhang"
                )
        except Exception:
            pass
        return issues

    @classmethod
    def estimate_print_cost(cls, mesh_path: str, material: str = "PLA",
                            infill: int = 20) -> Optional[Dict]:
        """Estimate the cost of 3D printing a mesh.

        Args:
            mesh_path: Path to the mesh file
            material: Material name
            infill: Infill percentage (0-100)

        Returns:
            Dict with cost breakdown
        """
        if not HAS_TRIMESH:
            return None

        path = Path(mesh_path)
        if not path.is_file():
            return None

        try:
            mesh = trimesh.load(str(path), force="mesh")

            if not mesh.is_volume:
                logger.warning("Mesh is not a closed volume — estimate may be inaccurate")

            # Material properties ($/kg)
            material_costs = {
                "PLA": 20, "PETG": 25, "ABS": 22, "TPU": 35,
                "Nylon": 40, "PC": 50, "ASA": 28, "Resin": 30,
            }

            material_density = {
                "PLA": 1.24, "PETG": 1.27, "ABS": 1.04, "TPU": 1.21,
                "Nylon": 1.14, "PC": 1.20, "ASA": 1.07, "Resin": 1.10,
            }

            cost_per_kg = material_costs.get(material, 20)
            density = material_density.get(material, 1.24)

            # Calculate volume in cm³
            volume_mm3 = float(mesh.volume) if mesh.is_volume else float(mesh.area) * 0.5
            volume_cm3 = volume_mm3 / 1000

            # Apply infill
            solid_volume = volume_cm3 * (infill / 100)

            # Add walls (rough estimate: 15% overhead)
            effective_volume = solid_volume * 1.15

            # Weight in grams
            weight_g = effective_volume * density

            # Cost
            material_cost = (weight_g / 1000) * cost_per_kg

            # Time estimate (rough: 10mm³/s typical)
            time_seconds = volume_mm3 / 10
            time_hours = time_seconds / 3600

            # Electricity cost (rough: 0.2kWh * $0.12/kWh per hour)
            electricity = time_hours * 0.024

            total = material_cost + electricity

            return {
                "material": material,
                "infill_pct": infill,
                "volume_cm3": round(volume_cm3, 2),
                "weight_g": round(weight_g, 1),
                "material_cost_usd": round(material_cost, 2),
                "electricity_cost_usd": round(electricity, 2),
                "total_cost_usd": round(total, 2),
                "estimated_time_hours": round(time_hours, 1),
                "cost_per_kg": cost_per_kg,
                "density": density,
            }

        except Exception as e:
            logger.error(f"Cost estimation failed: {e}")
            return None

    @classmethod
    def get_slicer_settings(cls, mesh_path: str, printer: str = "ender3",
                            material: str = "PLA") -> Optional[Dict]:
        """Get default slicer settings for a printer.

        Args:
            mesh_path: Path to mesh (for dimension checks)
            printer: Printer profile key
            material: Material name

        Returns:
            Dict with slicer settings
        """
        preset = cls.SLICER_PRESETS.get(printer, cls.SLICER_PRESETS["ender3"]).copy()

        # Adjust for material
        material_temps = {
            "PLA": {"nozzle": 200, "bed": 60},
            "PETG": {"nozzle": 235, "bed": 80},
            "ABS": {"nozzle": 240, "bed": 100},
            "TPU": {"nozzle": 220, "bed": 50},
            "Nylon": {"nozzle": 255, "bed": 80},
        }

        temps = material_temps.get(material, {"nozzle": 200, "bed": 60})
        preset["nozzle_temp"] = temps["nozzle"]
        preset["bed_temp"] = temps["bed"]
        preset["material"] = material

        # Check if support might be needed
        analysis = MeshEditor.analyze(mesh_path) if mesh_path else None
        if analysis:
            extents = analysis.get("extents", [0, 0, 0])
            max_overhang_pct = analysis.get("analysis", {}).get("overhang_pct", 0)
            if max_overhang_pct > 10:
                preset["support_enabled"] = True
                preset["support_angle"] = 45

        return preset

    @classmethod
    def export_for_print(cls, mesh_path: str, printer: str = "ender3",
                         material: str = "PLA") -> Optional[Dict]:
        """Full print export package: validation, cost, slicer settings.

        Args:
            mesh_path: Path to mesh file
            printer: Printer profile key
            material: Material name

        Returns:
            Dict with all print export data
        """
        validation = cls.validate_for_print(mesh_path, material)
        cost = cls.estimate_print_cost(mesh_path, material)
        slicer = cls.get_slicer_settings(mesh_path, printer, material)

        # Copy to export directory with print suffix
        export_path = EXPORT_DIR / f"print_{Path(mesh_path).stem}_{material}.stl"
        try:
            shutil.copy2(mesh_path, str(export_path))
        except Exception:
            export_path = mesh_path

        return {
            "source": mesh_path,
            "export_path": str(export_path),
            "printer": printer,
            "material": material,
            "validation": validation,
            "cost_estimate": cost,
            "slicer_settings": slicer,
            "ready_to_print": validation.get("valid", False) if validation else False,
            "timestamp": datetime.utcnow().isoformat(),
        }


# =============================================================================
# VR SCENE EXPORT
# =============================================================================

class VRExporter:
    """Handles export of meshes for VR simulation."""

    # Default material appearances
    MATERIAL_PRESETS = {
        "metal": {"color": "#888888", "metalness": 0.9, "roughness": 0.3},
        "plastic": {"color": "#cccccc", "metalness": 0.0, "roughness": 0.5},
        "glass": {"color": "#aaddff", "metalness": 0.1, "roughness": 0.1, "alpha": 0.5},
        "wood": {"color": "#8B4513", "metalness": 0.0, "roughness": 0.8},
        "carbon": {"color": "#333333", "metalness": 0.5, "roughness": 0.4},
        "spacecraft": {"color": "#e0e0e0", "metalness": 0.7, "roughness": 0.2},
    }

    # Default lighting
    DEFAULT_LIGHTING = {
        "ambient": {"color": "#404060", "intensity": 0.4},
        "directional": [
            {"color": "#ffffff", "intensity": 0.8, "direction": [1, 1, 1]},
            {"color": "#8888ff", "intensity": 0.3, "direction": [-1, 0.5, -0.5]},
        ],
        "environment": "space",  # space, studio, outdoor
    }

    # Default camera
    DEFAULT_CAMERA = {
        "position": [0, 0, 5],
        "target": [0, 0, 0],
        "up": [0, 1, 0],
        "fov": 60,
        "near": 0.1,
        "far": 1000,
    }

    @classmethod
    def prepare_scene(cls, generations: List[Dict],
                      lighting: Optional[Dict] = None,
                      camera: Optional[Dict] = None) -> Optional[Dict]:
        """Create a VR-ready scene from a list of generations.

        Args:
            generations: List of generation dicts with file_path, position, etc.
            lighting: Optional lighting override
            camera: Optional camera override

        Returns:
            Scene description dict
        """
        objects = []

        for i, gen in enumerate(generations):
            mesh_path = gen.get("file_path", "")
            if not mesh_path or not Path(mesh_path).is_file():
                continue

            # Analyze mesh for bounds
            analysis = MeshEditor.analyze(mesh_path) or {}
            extents = analysis.get("extents", [1, 1, 1])
            center = analysis.get("center", [0, 0, 0])

            obj = {
                "id": gen.get("id", f"obj_{i}"),
                "name": gen.get("prompt", f"Object {i+1}"),
                "mesh_path": mesh_path,
                "position": gen.get("position", [0, 0, 0]),
                "rotation": gen.get("rotation", [0, 0, 0]),
                "scale": gen.get("scale", [1, 1, 1]),
                "material": gen.get("material", "spacecraft"),
                "material_properties": cls.MATERIAL_PRESETS.get(
                    gen.get("material", "spacecraft"),
                    cls.MATERIAL_PRESETS["spacecraft"]
                ),
                "dimensions": extents,
                "metadata": {
                    "vertices": analysis.get("vertices", 0),
                    "faces": analysis.get("faces", 0),
                    "source_prompt": gen.get("prompt", ""),
                    "engine": gen.get("engine", "unknown"),
                },
            }
            objects.append(obj)

        scene = {
            "version": "1.0",
            "name": "ZICORE VR Scene",
            "created_at": datetime.utcnow().isoformat(),
            "objects": objects,
            "lighting": lighting or cls.DEFAULT_LIGHTING.copy(),
            "camera": camera or cls.DEFAULT_CAMERA.copy(),
            "skybox": {
                "type": "stars",
                "color": "#000010",
                "stars_enabled": True,
                "nebula_enabled": True,
            },
            "physics": {
                "gravity": [0, -9.81, 0],
                "collision_enabled": True,
            },
        }

        return scene

    @classmethod
    def create_scene_from_prompt(cls, prompt: str,
                                  engine_results: Optional[List[Dict]] = None) -> Optional[Dict]:
        """Build a VR scene from a materializer prompt and results.

        Args:
            prompt: Original materializer prompt
            engine_results: List of engine result dicts (file_path, metadata, etc.)

        Returns:
            Scene description dict
        """
        # Determine scene type from prompt
        scene_type = "general"
        prompt_lower = prompt.lower()

        if any(kw in prompt_lower for kw in ["space", "orbital", "station", "satellite"]):
            scene_type = "space"
        elif any(kw in prompt_lower for kw in ["lunar", "moon", "mars", "planet"]):
            scene_type = "planetary"
        elif any(kw in prompt_lower for kw in ["base", "habitat", "facility"]):
            scene_type = "facility"
        elif any(kw in prompt_lower for kw in ["vehicle", "rocket", "ship"]):
            scene_type = "vehicle"

        # Build lighting based on scene type
        lighting = cls.DEFAULT_LIGHTING.copy()
        if scene_type == "space":
            lighting["environment"] = "space"
            lighting["ambient"]["intensity"] = 0.2
        elif scene_type == "planetary":
            lighting["environment"] = "outdoor"
            lighting["ambient"]["intensity"] = 0.5
            lighting["directional"].append({
                "color": "#ffaa44",
                "intensity": 0.6,
                "direction": [0, -1, 0],
            })

        # Process engine results
        objects = []
        if engine_results:
            for i, result in enumerate(engine_results):
                if not result.get("success", False):
                    continue
                if not result.get("file_path"):
                    continue

                objects.append({
                    "id": f"gen_{i}",
                    "name": prompt,
                    "file_path": result["file_path"],
                    "position": [0, 0, 0],
                    "rotation": [0, 0, 0],
                    "scale": [1, 1, 1],
                    "material": "spacecraft",
                    "engine": result.get("engine", "unknown"),
                    "output_type": result.get("output_type", "unknown"),
                })

        scene = cls.prepare_scene(objects, lighting=lighting)
        scene["name"] = f"ZICORE Scene: {prompt[:50]}"
        scene["prompt"] = prompt
        scene["scene_type"] = scene_type

        return scene

    @classmethod
    def export_scene(cls, scene: Dict, output_path: Optional[str] = None) -> Optional[str]:
        """Export a scene to JSON file.

        Args:
            scene: Scene description dict
            output_path: Optional output path

        Returns:
            Path to exported scene file
        """
        if output_path is None:
            output_path = str(EXPORT_DIR / f"scene_{uuid.uuid4().hex[:8]}.json")

        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(scene, f, indent=2, default=str)
            logger.info(f"Scene exported to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Scene export failed: {e}")
            return None


# =============================================================================
# OUTPREVIEW — MAIN CLASS
# =============================================================================

class OutPreview:
    """Central output/preview panel for the Materializer cockpit.

    Tracks the latest generation, maintains history, and provides
    editing, print export, and VR simulation capabilities.

    Usage:
        preview = OutPreview()
        preview.set_generation({
            "prompt": "lunar base concept",
            "type": "3d",
            "file_path": "output/lunar_base.stl",
            "metadata": {"vertices": 1234, "faces": 5678},
        })
        current = preview.get_current()
        history = preview.get_history()
    """

    MAX_HISTORY = 20

    def __init__(self, max_history: int = 20):
        """Initialize the OutPreview panel.

        Args:
            max_history: Maximum number of generations to keep in history
        """
        self.MAX_HISTORY = max_history
        self.current: Optional[Dict] = None
        self.history: List[Dict] = []
        self._editors = MeshEditor
        self._print_exporter = PrintExporter
        self._vr_exporter = VRExporter

        logger.info("OutPreview initialized")

    def set_generation(self, gen_data: Dict) -> Dict:
        """Set the current generation and push previous to history.

        Args:
            gen_data: Generation dict with prompt, type, file_path, metadata, etc.

        Returns:
            The generation data with added id and timestamp
        """
        gen = {
            "id": gen_data.get("id", uuid.uuid4().hex[:12]),
            "prompt": gen_data.get("prompt", ""),
            "type": gen_data.get("type", "unknown"),
            "file_path": gen_data.get("file_path", ""),
            "metadata": gen_data.get("metadata", {}),
            "thumbnail": gen_data.get("thumbnail", None),
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Push current to history
        if self.current is not None:
            self.history.insert(0, self.current)
            if len(self.history) > self.MAX_HISTORY:
                self.history = self.history[:self.MAX_HISTORY]

        self.current = gen
        logger.info(f"Generation set: {gen['id']} type={gen['type']}")

        return gen

    def get_current(self) -> Optional[Dict]:
        """Get the current generation.

        Returns:
            Current generation dict, or None if nothing set
        """
        return self.current

    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get generation history.

        Args:
            limit: Maximum number of history entries to return

        Returns:
            List of generation dicts (most recent first)
        """
        return self.history[:limit]

    def clear(self) -> None:
        """Clear the current generation (does not affect history)."""
        self.current = None
        logger.info("OutPreview cleared")

    def clear_history(self) -> None:
        """Clear the generation history."""
        self.history.clear()
        logger.info("OutPreview history cleared")

    # ------------------------------------------------------------------
    # MESH EDITING
    # ------------------------------------------------------------------

    def edit_mesh(self, gen_id: Optional[str] = None, operation: str = "analyze",
                  params: Optional[Dict] = None) -> Optional[Dict]:
        """Edit the mesh of a generation or current.

        Args:
            gen_id: Generation ID to edit (None for current)
            operation: Operation name (see get_edit_operations())
            params: Operation parameters

        Returns:
            Operation result dict, or None on failure
        """
        gen = self._resolve_generation(gen_id)
        if gen is None:
            logger.error("No generation to edit")
            return None

        mesh_path = gen.get("file_path", "")
        if not mesh_path:
            logger.error("Generation has no file_path")
            return None

        params = params or {}

        op_map = {
            "scale": lambda: self._editors.scale(mesh_path, **params),
            "rotate": lambda: self._editors.rotate(mesh_path, **params),
            "translate": lambda: self._editors.translate(mesh_path, **params),
            "mirror": lambda: self._editors.mirror(mesh_path, **params),
            "smooth": lambda: self._editors.smooth(mesh_path, **params),
            "decimate": lambda: self._editors.decimate(mesh_path, **params),
            "analyze": lambda: self._editors.analyze(mesh_path),
        }

        # Boolean operations require two mesh paths
        boolean_ops = {
            "union": lambda: self._editors.union(
                mesh_path, params.get("mesh_path_b", ""), **{k: v for k, v in params.items() if k != "mesh_path_b"}
            ),
            "difference": lambda: self._editors.difference(
                mesh_path, params.get("mesh_path_b", ""), **{k: v for k, v in params.items() if k != "mesh_path_b"}
            ),
            "intersection": lambda: self._editors.intersection(
                mesh_path, params.get("mesh_path_b", ""), **{k: v for k, v in params.items() if k != "mesh_path_b"}
            ),
        }

        all_ops = {**op_map, **boolean_ops}

        if operation not in all_ops:
            logger.error(f"Unknown operation: {operation}")
            return {"error": f"Unknown operation: {operation}"}

        try:
            result = all_ops[operation]()
            if result is None:
                return {"error": f"Operation {operation} failed"}

            # Update generation file_path if output was created
            if "output_path" in result and result.get("output_path"):
                gen["file_path"] = result["output_path"]
                gen["edited"] = True
                gen["edit_operation"] = operation

            return result
        except Exception as e:
            logger.error(f"Edit operation failed: {e}")
            return {"error": str(e)}

    def get_edit_operations(self) -> List[Dict]:
        """List available edit operations.

        Returns:
            List of operation dicts with name, description, and parameters
        """
        operations = [
            {
                "name": "scale",
                "description": "Uniform or non-uniform scale",
                "category": "transform",
                "parameters": {
                    "factor": {"type": "float|list", "required": True, "description": "Scale factor (float or [x,y,z])"},
                },
            },
            {
                "name": "rotate",
                "description": "Rotate around an axis",
                "category": "transform",
                "parameters": {
                    "axis": {"type": "str", "required": True, "description": "Axis: 'x', 'y', or 'z'"},
                    "angle": {"type": "float", "required": True, "description": "Angle in degrees"},
                },
            },
            {
                "name": "translate",
                "description": "Move in 3D space",
                "category": "transform",
                "parameters": {
                    "offset": {"type": "list", "required": True, "description": "[x, y, z] offset in mm"},
                },
            },
            {
                "name": "mirror",
                "description": "Mirror across an axis",
                "category": "transform",
                "parameters": {
                    "axis": {"type": "str", "required": True, "description": "Axis: 'x', 'y', or 'z'"},
                },
            },
            {
                "name": "union",
                "description": "Boolean union (combine two meshes)",
                "category": "boolean",
                "parameters": {
                    "mesh_path_b": {"type": "str", "required": True, "description": "Path to second mesh"},
                },
            },
            {
                "name": "difference",
                "description": "Boolean difference (subtract B from A)",
                "category": "boolean",
                "parameters": {
                    "mesh_path_b": {"type": "str", "required": True, "description": "Path to second mesh"},
                },
            },
            {
                "name": "intersection",
                "description": "Boolean intersection (common volume)",
                "category": "boolean",
                "parameters": {
                    "mesh_path_b": {"type": "str", "required": True, "description": "Path to second mesh"},
                },
            },
            {
                "name": "smooth",
                "description": "Laplacian smoothing",
                "category": "modify",
                "parameters": {
                    "iterations": {"type": "int", "required": False, "description": "Smoothing iterations (1-50, default: 5)"},
                },
            },
            {
                "name": "decimate",
                "description": "Reduce polygon count",
                "category": "modify",
                "parameters": {
                    "target_faces": {"type": "int", "required": False, "description": "Target face count (default: 1000)"},
                },
            },
            {
                "name": "analyze",
                "description": "Analyze mesh properties",
                "category": "analysis",
                "parameters": {},
            },
        ]

        return operations

    # ------------------------------------------------------------------
    # PRINT EXPORT
    # ------------------------------------------------------------------

    def export_for_print(self, gen_id: Optional[str] = None,
                         printer: str = "ender3",
                         material: str = "PLA") -> Optional[Dict]:
        """Export current or specific generation for 3D printing.

        Args:
            gen_id: Generation ID (None for current)
            printer: Printer profile key
            material: Material name

        Returns:
            Print export package dict
        """
        gen = self._resolve_generation(gen_id)
        if gen is None:
            logger.error("No generation to export for print")
            return None

        mesh_path = gen.get("file_path", "")
        if not mesh_path:
            logger.error("Generation has no file_path")
            return None

        result = self._print_exporter.export_for_print(mesh_path, printer, material)

        if result:
            result["generation_id"] = gen.get("id")
            result["prompt"] = gen.get("prompt", "")

        return result

    # ------------------------------------------------------------------
    # VR EXPORT
    # ------------------------------------------------------------------

    def export_for_vr(self, gen_id: Optional[str] = None) -> Optional[Dict]:
        """Export current or specific generation for VR simulation.

        Args:
            gen_id: Generation ID (None for current)

        Returns:
            VR scene description dict
        """
        gen = self._resolve_generation(gen_id)
        if gen is None:
            logger.error("No generation to export for VR")
            return None

        scene = self._vr_exporter.prepare_scene([gen])

        if scene:
            scene["source_generation"] = gen.get("id")
            scene["prompt"] = gen.get("prompt", "")

            # Export to file
            export_path = self._vr_exporter.export_scene(scene)
            if export_path:
                scene["export_path"] = export_path

        return scene

    def prepare_vr_scene(self, generations: List[Dict],
                         lighting: Optional[Dict] = None,
                         camera: Optional[Dict] = None) -> Optional[Dict]:
        """Prepare a VR scene from multiple generations.

        Args:
            generations: List of generation dicts
            lighting: Optional lighting config
            camera: Optional camera config

        Returns:
            Scene description dict
        """
        return self._vr_exporter.prepare_scene(generations, lighting, camera)

    def create_scene_from_prompt(self, prompt: str,
                                  engine_results: Optional[List[Dict]] = None) -> Optional[Dict]:
        """Create a VR scene from a materializer prompt.

        Args:
            prompt: Original prompt
            engine_results: Engine result dicts

        Returns:
            Scene description dict
        """
        return self._vr_exporter.create_scene_from_prompt(prompt, engine_results)

    # ------------------------------------------------------------------
    # SAVE TO LIBRARY
    # ------------------------------------------------------------------

    def save_to_library(self, gen_id: Optional[str] = None,
                        tags: Optional[List[str]] = None,
                        folder_id: Optional[int] = None) -> Optional[int]:
        """Save current or specific generation to the Generation Library.

        Args:
            gen_id: Generation ID (None for current)
            tags: Optional tags to apply
            folder_id: Optional folder to place in

        Returns:
            Library generation ID, or None on failure
        """
        gen = self._resolve_generation(gen_id)
        if gen is None:
            logger.error("No generation to save")
            return None

        try:
            from zicore.generation_library import generation_library

            lib_id = generation_library.add(
                prompt=gen.get("prompt", ""),
                output_type=gen.get("type", "unknown"),
                engine=gen.get("metadata", {}).get("engine", "materializer"),
                file_path=gen.get("file_path", ""),
                file_format=Path(gen.get("file_path", "")).suffix.lstrip(".") or "unknown",
                metadata=gen.get("metadata", {}),
                tags=tags or [],
                folder_id=folder_id,
            )

            logger.info(f"Generation saved to library: id={lib_id}")
            return lib_id

        except ImportError:
            logger.error("Generation Library not available")
            return None
        except Exception as e:
            logger.error(f"Failed to save to library: {e}")
            return None

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    def _resolve_generation(self, gen_id: Optional[str]) -> Optional[Dict]:
        """Resolve a generation by ID or return current."""
        if gen_id is None:
            return self.current

        # Search in history
        for gen in self.history:
            if gen.get("id") == gen_id:
                return gen

        # Check current
        if self.current and self.current.get("id") == gen_id:
            return self.current

        return None

    def to_dict(self) -> Dict:
        """Serialize the OutPreview state."""
        return {
            "current": self.current,
            "history": self.history,
            "history_count": len(self.history),
        }

    def get_summary(self) -> Dict:
        """Get a summary of the OutPreview state."""
        current_summary = None
        if self.current:
            current_summary = {
                "id": self.current.get("id"),
                "prompt": self.current.get("prompt", "")[:80],
                "type": self.current.get("type"),
                "file_path": self.current.get("file_path"),
            }

        return {
            "has_current": self.current is not None,
            "current": current_summary,
            "history_count": len(self.history),
            "history_types": list(set(g.get("type", "unknown") for g in self.history)),
            "max_history": self.MAX_HISTORY,
        }


# =============================================================================
# MODULE-LEVEL CONVENIENCE INSTANCE
# =============================================================================

outpreview = OutPreview()


# =============================================================================
# CLI / TESTING
# =============================================================================

if __name__ == "__main__":
    preview = OutPreview()

    print("=== ZICORE OutPreview ===")
    print(f"Edit operations: {[op['name'] for op in preview.get_edit_operations()]}")

    # Test with a sample generation
    sample = preview.set_generation({
        "prompt": "Lunar base habitat module",
        "type": "3d",
        "file_path": "output/lunar_habitat.stl",
        "metadata": {"vertices": 5000, "faces": 10000, "engine": "trimesh"},
    })
    print(f"Set generation: {sample['id']}")

    current = preview.get_current()
    print(f"Current: {current['prompt']}")

    history = preview.get_history()
    print(f"History entries: {len(history)}")

    summary = preview.get_summary()
    print(f"Summary: {json.dumps(summary, indent=2)}")

    print("OutPreview ready.")

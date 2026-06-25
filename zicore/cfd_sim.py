"""
ZICORE CFD Simulation Module - Computational Fluid Dynamics
Provides aerodynamic analysis, drag/lift calculations, and flow simulation.
Pure Python fallback when C++ pybind11 module is not compiled.
"""
import math
import os
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("zicore.cfd")

# Try to load compiled C++ module
CFD_MODULE = None
CFD_AVAILABLE = False

try:
    import zicore_cfd
    CFD_MODULE = zicore_cfd
    CFD_AVAILABLE = True
    logger.info("Loaded C++ CFD module")
except ImportError:
    logger.info("C++ CFD module not found — using pure Python fallback")


# ── Constants ─────────────────────────────────────────────────────────

AIR_DENSITY_SEA_LEVEL = 1.225  # kg/m^3
SPEED_OF_SOUND = 343.0  # m/s at 20C
GAMMA_AIR = 1.4  # ratio of specific heats
GAS_CONSTANT_AIR = 287.058  # J/(kg*K)

# Airfoil polar coefficients (approximate for common profiles)
AIRFOIL_DATA = {
    "naca0012": {"cl_alpha": 0.11, "cd0": 0.006, "cd_k": 0.004, "cl_max": 1.5, "cm0": -0.02},
    "naca2412": {"cl_alpha": 0.11, "cd0": 0.007, "cd_k": 0.004, "cl_max": 1.6, "cm0": -0.04},
    "naca4412": {"cl_alpha": 0.11, "cd0": 0.008, "cd_k": 0.005, "cl_max": 1.7, "cm0": -0.07},
    "naca6412": {"cl_alpha": 0.10, "cd0": 0.009, "cd_k": 0.005, "cl_max": 1.6, "cm0": -0.09},
    "flat_plate": {"cl_alpha": 0.09, "cd0": 0.010, "cd_k": 0.006, "cl_max": 1.2, "cm0": 0.0},
}


# ── Data Classes ─────────────────────────────────────────────────────

@dataclass
class AerodynamicState:
    mach: float
    reynolds: float
    cl: float  # lift coefficient
    cd: float  # drag coefficient
    cm: float  # moment coefficient
    ld_ratio: float  # L/D ratio
    dynamic_pressure: float  # Pa
    lift_force: float  # N
    drag_force: float  # N


@dataclass
class FlowField:
    nx: int  # grid points x
    ny: int  # grid points y
    u: List[List[float]]  # x-velocity field
    v: List[List[float]]  # y-velocity field
    p: List[List[float]]  # pressure field
    magnitude: List[List[float]]  # velocity magnitude


@dataclass
class BoundaryLayer:
    thickness: float  # meters
    displacement_thickness: float
    momentum_thickness: float
    friction_coefficient: float
    transition_reynolds: float
    is_turbulent: bool


@dataclass
class ShockWave:
    mach_upstream: float
    mach_downstream: float
    pressure_ratio: float
    deflection_angle: float  # degrees
    wave_angle: float  # degrees


# ── Pure Python CFD Implementations ──────────────────────────────────

def _py_compressible_flow(mach: float, gamma: float = GAMMA_AIR) -> Dict[str, float]:
    """Compressible flow relations."""
    if mach < 0:
        raise ValueError("Mach number must be non-negative")
    m2 = mach ** 2
    p_ratio = (1 + 0.5 * (gamma - 1) * m2) ** (gamma / (gamma - 1))
    t_ratio = 1 + 0.5 * (gamma - 1) * m2
    rho_ratio = p_ratio / t_ratio if t_ratio > 0 else 0
    return {
        "mach": round(mach, 4),
        "total_pressure_ratio": round(p_ratio, 6),
        "total_temperature_ratio": round(t_ratio, 6),
        "density_ratio": round(rho_ratio, 6),
        "is_subsonic": mach < 1.0,
        "is_supersonic": mach > 1.0,
        "is_transonic": 0.8 <= mach <= 1.2,
    }


def _py_naca_airfoil(cl_alpha: float, cd0: float, cd_k: float,
                      alpha: float, s: float, q: float) -> AerodynamicState:
    """Thin airfoil theory with drag polar."""
    alpha_rad = math.radians(alpha)
    cl = cl_alpha * alpha_rad * 2 * math.pi  # thin airfoil
    cd = cd0 + cd_k * cl ** 2
    cm = -0.1 * cl  # approximate
    ld = cl / cd if cd > 0 else 0
    lift = cl * q * s
    drag = cd * q * s
    return AerodynamicState(
        mach=0, reynolds=0, cl=round(cl, 4), cd=round(cd, 6),
        cm=round(cm, 4), ld_ratio=round(ld, 2),
        dynamic_pressure=round(q, 2),
        lift_force=round(lift, 2), drag_force=round(drag, 2),
    )


def _py_reynolds_number(velocity: float, length: float,
                         kinematic_viscosity: float = 1.516e-5) -> float:
    """Calculate Reynolds number."""
    return abs(velocity * length / kinematic_viscosity) if kinematic_viscosity > 0 else 0


def _py_boundary_layer(velocity: float, x: float,
                        rho: float = AIR_DENSITY_SEA_LEVEL,
                        mu: float = 1.81e-5) -> BoundaryLayer:
    """Boundary layer properties at position x."""
    re_x = rho * velocity * x / mu if mu > 0 else 0
    transition_re = 5e5
    is_turbulent = re_x > transition_re

    if is_turbulent:
        # Turbulent flat plate (1/7th power law)
        delta = 0.37 * x / (re_x ** 0.2) if re_x > 0 else 0
        delta_star = delta / 8.0
        theta = delta * 7.0 / 72.0
        cf = 0.0592 / (re_x ** 0.2) if re_x > 0 else 0
    else:
        # Laminar Blasius solution
        delta = 5.0 * x / math.sqrt(re_x) if re_x > 0 else 0
        delta_star = delta / 3.0
        theta = delta * 2.0 / 15.0
        cf = 0.664 / math.sqrt(re_x) if re_x > 0 else 0

    return BoundaryLayer(
        thickness=round(delta, 6),
        displacement_thickness=round(delta_star, 6),
        momentum_thickness=round(theta, 6),
        friction_coefficient=round(cf, 6),
        transition_reynolds=transition_re,
        is_turbulent=is_turbulent,
    )


def _py_shock_wave(mach: float, deflection: float,
                    gamma: float = GAMMA_AIR) -> Optional[ShockWave]:
    """Normal/oblique shock relations."""
    if mach <= 1.0 or deflection <= 0:
        return None
    # Simplified oblique shock (weak shock solution)
    deflection_rad = math.radians(deflection)
    beta = math.asin(1.0 / mach) + deflection_rad * 0.5
    beta = min(beta, math.pi / 2 - 0.01)

    mn = mach * math.sin(beta)  # normal component
    mn2 = mn ** 2
    p_ratio = 1 + 2 * gamma / (gamma + 1) * (mn2 - 1)
    t_ratio = (1 + 2 * gamma / (gamma + 1) * (mn2 - 1)) * \
              ((2 + (gamma - 1) * mn2) / ((gamma + 1) * mn2))
    mn_down = math.sqrt((1 + 0.5 * (gamma - 1) * mn2) / (gamma * mn2 - 0.5 * (gamma - 1)))
    mach_down = mn_down / math.sin(beta - deflection_rad) if math.sin(beta - deflection_rad) > 0 else mn_down

    return ShockWave(
        mach_upstream=round(mach, 4),
        mach_downstream=round(mach_down, 4),
        pressure_ratio=round(p_ratio, 4),
        deflection_angle=round(deflection, 2),
        wave_angle=round(math.degrees(beta), 2),
    )


def _py_wave_drag(mach: float, thickness_ratio: float,
                   cl: float = 0.0) -> float:
    """Supersonic wave drag coefficient."""
    if mach <= 1.0:
        return 0.0
    m2 = mach ** 2
    # Ackeret's linear theory
    cd_wave = 4 * thickness_ratio ** 2 / math.sqrt(m2 - 1)
    cd_wave += 2 * cl ** 2 / math.sqrt(m2 - 1)  # lift-dependent wave drag
    return round(cd_wave, 6)


def _py_induced_drag(cl: float, ar: float, e: float = 0.85) -> float:
    """Induced drag coefficient."""
    if ar <= 0:
        return 0.0
    cd_i = cl ** 2 / (math.pi * ar * e)
    return round(cd_i, 6)


def _py_oswald_efficiency(ar: float, sweep: float = 0.0) -> float:
    """Estimate Oswald efficiency factor."""
    sweep_rad = math.radians(sweep)
    # Raymer's approximation
    e = 1.78 * (1 - 0.045 * ar ** 0.68) - 0.64
    e *= math.cos(sweep_rad) ** 0.15
    return round(max(0.5, min(0.95, e)), 3)


def _py_pressure_distribution(x_chord: List[float], mach: float,
                               cl: float) -> List[float]:
    """Simple pressure coefficient distribution over airfoil."""
    cp_list = []
    for x in x_chord:
        if x <= 0:
            cp = -cl * 2 / (1 + 0.2 * mach ** 2)  # leading edge
        elif x >= 1:
            cp = 0.02  # trailing edge
        else:
            # Parabolic distribution
            cp = -cl * (1 - 2 * x) / (1 + 0.2 * mach ** 2) + 0.01
        cp_list.append(round(cp, 4))
    return cp_list


def _py_heat_flux(mach: float, rho: float, velocity: float,
                   nose_radius: float) -> float:
    """Stagnation point heat flux (Sutton-Graves approximation)."""
    if velocity <= 0 or nose_radius <= 0:
        return 0.0
    # k = 1.83e-4 for air
    q = 1.83e-4 * math.sqrt(rho / nose_radius) * velocity ** 3
    return round(q, 2)  # W/m^2


def _py_thermal_equilibrium(heat_flux: float, emissivity: float = 0.85,
                             area: float = 1.0) -> float:
    """Equilibrium temperature from heat flux (Stefan-Boltzmann)."""
    sigma = 5.67e-8
    if heat_flux <= 0 or emissivity <= 0 or area <= 0:
        return 300.0  # ambient
    T = (heat_flux / (emissivity * sigma)) ** 0.25
    return round(T, 1)


# ── Public API ───────────────────────────────────────────────────────

class CFDSimulation:
    """Computational Fluid Dynamics simulation engine.
    Falls back to pure Python when C++ module is unavailable."""

    def __init__(self):
        self.cfd_available = CFD_AVAILABLE
        self.module = CFD_MODULE

    def compressible_flow(self, mach: float) -> Dict[str, float]:
        """Compressible flow relations."""
        if self.cfd_available and self.module:
            try:
                return self.module.compressible_flow(mach)
            except Exception:
                pass
        return _py_compressible_flow(mach)

    def airfoil_analysis(self, airfoil: str, alpha: float,
                          s: float, velocity: float,
                          rho: float = AIR_DENSITY_SEA_LEVEL) -> AerodynamicState:
        """Analyze airfoil performance."""
        data = AIRFOIL_DATA.get(airfoil.lower(), AIRFOIL_DATA["naca0012"])
        q = 0.5 * rho * velocity ** 2
        return _py_naca_airfoil(data["cl_alpha"], data["cd0"], data["cd_k"],
                                alpha, s, q)

    def reynolds_number(self, velocity: float, length: float,
                         kinematic_viscosity: float = 1.516e-5) -> float:
        """Calculate Reynolds number."""
        return _py_reynolds_number(velocity, length, kinematic_viscosity)

    def boundary_layer(self, velocity: float, x: float) -> BoundaryLayer:
        """Boundary layer properties."""
        return _py_boundary_layer(velocity, x)

    def shock_wave(self, mach: float, deflection: float) -> Optional[ShockWave]:
        """Oblique shock wave analysis."""
        return _py_shock_wave(mach, deflection)

    def wave_drag(self, mach: float, thickness_ratio: float,
                  cl: float = 0.0) -> float:
        """Supersonic wave drag."""
        return _py_wave_drag(mach, thickness_ratio, cl)

    def induced_drag(self, cl: float, ar: float, e: float = 0.85) -> float:
        """Induced drag coefficient."""
        return _py_induced_drag(cl, ar, e)

    def oswald_efficiency(self, ar: float, sweep: float = 0.0) -> float:
        """Oswald efficiency factor."""
        return _py_oswald_efficiency(ar, sweep)

    def pressure_distribution(self, mach: float, cl: float,
                               n_points: int = 20) -> List[float]:
        """Pressure coefficient distribution."""
        x = [i / (n_points - 1) for i in range(n_points)]
        return _py_pressure_distribution(x, mach, cl)

    def heat_flux(self, mach: float, rho: float, velocity: float,
                   nose_radius: float) -> float:
        """Stagnation point heat flux."""
        return _py_heat_flux(mach, rho, velocity, nose_radius)

    def thermal_equilibrium(self, heat_flux: float,
                             emissivity: float = 0.85) -> float:
        """Equilibrium temperature."""
        return _py_thermal_equilibrium(heat_flux, emissivity)

    def full_vehicle_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Full aerodynamic vehicle analysis."""
        velocity = params.get("velocity", 100)
        altitude = params.get("altitude", 0)
        mach = params.get("mach", velocity / SPEED_OF_SOUND)
        wing_area = params.get("wing_area", 50)
        ar = params.get("aspect_ratio", 8)
        sweep = params.get("sweep_angle", 30)
        cl = params.get("cl", 0.5)
        thickness = params.get("thickness_ratio", 0.12)

        rho = AIR_DENSITY_SEA_LEVEL * math.exp(-altitude / 8500) if altitude < 80000 else 0.001
        q = 0.5 * rho * velocity ** 2

        cd_wave = self.wave_drag(mach, thickness, cl) if mach > 1 else 0
        cd_induced = self.induced_drag(cl, ar, self.oswald_efficiency(ar, sweep))
        cd_friction = 0.003  # typical skin friction
        cd_total = cd_friction + cd_induced + cd_wave

        ld = cl / cd_total if cd_total > 0 else 0
        lift = cl * q * wing_area
        drag = cd_total * q * wing_area

        bl = self.boundary_layer(velocity, 1.0)
        re = self.reynolds_number(velocity, 1.0)

        return {
            "mach": round(mach, 3),
            "reynolds": round(re, 0),
            "dynamic_pressure": round(q, 1),
            "cl": round(cl, 4),
            "cd_total": round(cd_total, 6),
            "cd_friction": round(cd_friction, 6),
            "cd_induced": round(cd_induced, 6),
            "cd_wave": round(cd_wave, 6),
            "ld_ratio": round(ld, 2),
            "lift_force": round(lift, 1),
            "drag_force": round(drag, 1),
            "boundary_layer_mm": round(bl.thickness * 1000, 2),
            "friction_coefficient": round(bl.friction_coefficient, 6),
            "is_turbulent": bl.is_turbulent,
            "source": "rust" if self.cfd_available else "python",
        }

    def get_status(self) -> Dict[str, Any]:
        """Get simulation engine status."""
        return {
            "cfd_available": self.cfd_available,
            "module_loaded": self.module is not None,
            "fallback_mode": not self.cfd_available,
            "airfoils": list(AIRFOIL_DATA.keys()),
            "capabilities": [
                "compressible_flow", "airfoil_analysis", "reynolds_number",
                "boundary_layer", "shock_wave", "wave_drag",
                "induced_drag", "pressure_distribution",
                "heat_flux", "thermal_equilibrium",
                "full_vehicle_analysis",
            ],
        }


# Fix the typo in oswald_efficiency
def _py_oswald_efficiency(ar: float, sweep: float = 0.0) -> float:
    sweep_rad = math.radians(sweep)
    e = 1.78 * (1 - 0.045 * ar ** 0.68) - 0.64
    e *= math.cos(sweep_rad) ** 0.15
    return round(max(0.5, min(0.95, e)), 3)


# Singleton
cfd = CFDSimulation()

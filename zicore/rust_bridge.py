"""
ZICORE Rust FFI Bridge - Safety-critical avionics calculations
Provides deterministic, memory-safe computation for flight-critical systems.
Pure Python fallback when Rust library is not compiled.
"""
import math
import ctypes
import os
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("zicore.rust_bridge")

# Try to load compiled Rust library
RUST_LIB = None
RUST_AVAILABLE = False

_lib_paths = [
    os.path.join(os.path.dirname(__file__), "..", "native", "libzicore_avionics.dll"),
    os.path.join(os.path.dirname(__file__), "..", "native", "libzicore_avionics.so"),
    os.path.join(os.path.dirname(__file__), "..", "native", "zicore_avionics.dll"),
]

for _path in _lib_paths:
    if os.path.exists(_path):
        try:
            RUST_LIB = ctypes.CDLL(_path)
            RUST_AVAILABLE = True
            logger.info(f"Loaded Rust avionics library: {_path}")
            break
        except OSError as e:
            logger.warning(f"Failed to load {_path}: {e}")

if not RUST_AVAILABLE:
    logger.info("Rust library not found — using pure Python fallback")


# ── Data Classes ─────────────────────────────────────────────────────

@dataclass
class TrajectoryState:
    position: Tuple[float, float, float]  # x, y, z in meters
    velocity: Tuple[float, float, float]  # vx, vy, vz in m/s
    acceleration: Tuple[float, float, float]
    mass: float  # kg
    fuel_remaining: float  # kg
    timestamp: float


@dataclass
class AttitudeState:
    pitch: float  # radians
    yaw: float    # radians
    roll: float   # radians
    angular_rate: Tuple[float, float, float]  # p, q, r in rad/s
    quaternion: Tuple[float, float, float, float]  # w, x, y, z


@dataclass
class NavigationSolution:
    position_lla: Tuple[float, float, float]  # lat, lon, alt
    velocity_ned: Tuple[float, float, float]  # north, east, down
    heading: float
    uncertainty: float  # meters


@dataclass
class SafetyCheck:
    is_safe: bool
    violations: list
    margin: float  # safety margin percentage
    severity: str  # "nominal", "caution", "warning", "critical"


# ── Pure Python Fallback Implementations ──────────────────────────────

def _py_hohmann_transfer(r1: float, r2: float, mu: float = 3.986e14) -> Dict[str, float]:
    """Calculate Hohmann transfer orbit parameters."""
    a_t = (r1 + r2) / 2.0
    v1 = math.sqrt(mu / r1)
    v2 = math.sqrt(mu / r2)
    vt1 = math.sqrt(mu * (2.0 / r1 - 1.0 / a_t))
    vt2 = math.sqrt(mu * (2.0 / r2 - 1.0 / a_t))
    dv1 = abs(vt1 - v1)
    dv2 = abs(v2 - vt2)
    tof = math.pi * math.sqrt(a_t ** 3 / mu)
    return {
        "delta_v1": round(dv1, 2),
        "delta_v2": round(dv2, 2),
        "total_dv": round(dv1 + dv2, 2),
        "time_of_flight": round(tof, 2),
        "semi_major_axis": round(a_t, 2),
    }


def _py_lambert_solve(r1_vec: Tuple[float, float, float],
                       r2_vec: Tuple[float, float, float],
                       tof: float,
                       mu: float = 3.986e14) -> Dict[str, float]:
    """Simplified Lambert problem solver."""
    r1 = math.sqrt(sum(x**2 for x in r1_vec))
    r2 = math.sqrt(sum(x**2 for x in r2_vec))
    cos_dnu = sum(a*b for a,b in zip(r1_vec, r2_vec)) / (r1 * r2)
    dnu = math.acos(max(-1, min(1, cos_dnu)))
    a = 1.0 / (2.0 / r1 - (1.0 / mu) * (math.sqrt(mu / r1) * math.sin(dnu))**2 / r1)
    return {
        "semi_major_axis": round(a, 2),
        "true_anomaly": round(math.degrees(dnu), 4),
        "r1_magnitude": round(r1, 2),
        "r2_magnitude": round(r2, 2),
    }


def _py_rk4_step(state: Tuple[float, ...], dt: float,
                  derivatives_fn) -> Tuple[float, ...]:
    """4th-order Runge-Kutta integration step."""
    n = len(state)
    k1 = derivatives_fn(state)
    s2 = tuple(state[i] + 0.5 * dt * k1[i] for i in range(n))
    k2 = derivatives_fn(s2)
    s3 = tuple(state[i] + 0.5 * dt * k2[i] for i in range(n))
    k3 = derivatives_fn(s3)
    s4 = tuple(state[i] + dt * k3[i] for i in range(n))
    k4 = derivatives_fn(s4)
    return tuple(
        state[i] + (dt / 6.0) * (k1[i] + 2*k2[i] + 2*k3[i] + k4[i])
        for i in range(n)
    )


def _py_attitude_quaternion_multiply(q1: Tuple[float, ...],
                                      q2: Tuple[float, ...]) -> Tuple[float, float, float, float]:
    """Hamilton product of two quaternions."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return (
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    )


def _py_attitude_to_euler(q: Tuple[float, float, float, float]) -> Tuple[float, float, float]:
    """Convert quaternion to Euler angles (pitch, yaw, roll)."""
    w, x, y, z = q
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)
    sinp = 2.0 * (w * y - z * x)
    sinp = max(-1, min(1, sinp))
    pitch = math.asin(sinp)
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return (pitch, yaw, roll)


def _py_proximity_check(pos_a: Tuple[float, float, float],
                         pos_b: Tuple[float, float, float],
                         safety_radius: float = 100.0) -> SafetyCheck:
    """Check proximity safety between two objects."""
    dx = pos_a[0] - pos_b[0]
    dy = pos_a[1] - pos_b[1]
    dz = pos_a[2] - pos_b[2]
    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
    violations = []
    if dist < safety_radius:
        violations.append(f"Proximity violation: {dist:.1f}m < {safety_radius:.1f}m")
    margin = ((dist - safety_radius) / safety_radius * 100) if safety_radius > 0 else 100.0
    severity = "nominal" if margin > 50 else "caution" if margin > 0 else "warning" if margin > -50 else "critical"
    return SafetyCheck(
        is_safe=len(violations) == 0,
        violations=violations,
        margin=round(margin, 2),
        severity=severity,
    )


def _py_deorbit_burn(altitude: float, velocity: float,
                      target_alt: float = 0.0,
                      mu: float = 3.986e14,
                      r_earth: float = 6371000.0) -> Dict[str, float]:
    """Calculate deorbit burn parameters."""
    r = r_earth + altitude
    v_circ = math.sqrt(mu / r)
    r_target = r_earth + target_alt
    a_transfer = (r + r_target) / 2.0
    v_perigee = math.sqrt(mu * (2.0 / r - 1.0 / a_transfer))
    dv = abs(v_perigee - v_circ)
    tof = math.pi * math.sqrt(a_transfer ** 3 / mu)
    return {
        "burn_delta_v": round(dv, 2),
        "burn_duration": round(dv / 0.003, 1),  # assuming 3 mm/s^2 deceleration
        "time_to_impact": round(tof, 1),
        "new_perigee_alt": round(target_alt, 1),
    }


def _py_structural_stress(load: float, area: float,
                           yield_strength: float = 250e6) -> Dict[str, float]:
    """Calculate structural stress and safety factor."""
    stress = load / area if area > 0 else float('inf')
    safety_factor = yield_strength / stress if stress > 0 else float('inf')
    utilization = stress / yield_strength * 100 if yield_strength > 0 else 0
    return {
        "stress_pascals": round(stress, 2),
        "safety_factor": round(safety_factor, 2),
        "utilization_pct": round(utilization, 2),
        "is_structural_safe": safety_factor > 1.5,
    }


def _py_collision_risk(pos_a: Tuple[float, float, float],
                        vel_a: Tuple[float, float, float],
                        pos_b: Tuple[float, float, float],
                        vel_b: Tuple[float, float, float],
                        radius_a: float = 1.0,
                        radius_b: float = 1.0) -> Dict[str, float]:
    """Calculate collision risk between two objects."""
    dx = pos_b[0] - pos_a[0]
    dy = pos_b[1] - pos_a[1]
    dz = pos_b[2] - pos_a[2]
    dvx = vel_b[0] - vel_a[0]
    dvy = vel_b[1] - vel_a[1]
    dvz = vel_b[2] - vel_a[2]
    dist = math.sqrt(dx*dx + dy*dy + dz*dz)
    rel_speed = math.sqrt(dvx*dvx + dvy*dvy + dvz*dvz)
    closing_speed = -(dx*dvx + dy*dvy + dz*dvz) / dist if dist > 0 else 0
    combined_radius = radius_a + radius_b
    tca = dist / closing_speed if closing_speed > 0 else float('inf')
    dot = dx*dvx + dy*dvy + dz*dvz
    cos_angle = dot / (dist * rel_speed) if rel_speed > 0 else 0
    cos_angle = max(-1, min(1, cos_angle))
    miss_distance = dist * math.sin(math.acos(cos_angle)) if rel_speed > 0 else dist
    risk_score = max(0, min(100, (1 - miss_distance / (combined_radius * 10)) * 100))
    return {
        "distance": round(dist, 2),
        "closing_speed": round(closing_speed, 2),
        "miss_distance": round(miss_distance, 2),
        "time_to_closest": round(tca, 2),
        "risk_score": round(risk_score, 2),
        "collision_predicted": miss_distance < combined_radius,
    }


# ── Public API ───────────────────────────────────────────────────────

class RustAvionicsBridge:
    """Bridge to Rust-based safety-critical avionics calculations.
    Falls back to pure Python when Rust library is unavailable."""

    def __init__(self):
        self.rust_available = RUST_AVAILABLE
        self.lib = RUST_LIB
        if self.rust_available:
            self._setup_rust_functions()

    def _setup_rust_functions(self):
        """Configure ctypes argument/return types for Rust functions."""
        if not self.lib:
            return
        try:
            # Example function signatures (adjust when actual Rust lib is compiled)
            self.lib.hohmann_transfer.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double]
            self.lib.hohmann_transfer.restype = ctypes.c_double
        except Exception as e:
            logger.warning(f"Could not setup Rust function signatures: {e}")

    def hohmann_transfer(self, r1: float, r2: float, mu: float = 3.986e14) -> Dict[str, float]:
        """Calculate Hohmann transfer orbit."""
        if self.rust_available and self.lib:
            try:
                # Call Rust implementation
                dv1 = self.lib.hohmann_transfer(r1, r2, mu)
                return {"total_dv": dv1, "source": "rust"}
            except Exception as e:
                logger.warning(f"Rust call failed, falling back: {e}")
        return {**_py_hohmann_transfer(r1, r2, mu), "source": "python"}

    def lambert_solve(self, r1_vec, r2_vec, tof, mu=3.986e14) -> Dict[str, float]:
        """Solve Lambert's problem."""
        return {**_py_lambert_solve(r1_vec, r2_vec, tof, mu), "source": "python"}

    def rk4_integrate(self, state, dt, derivatives_fn, steps=1) -> Tuple[float, ...]:
        """Runge-Kutta 4th order integration."""
        current = state
        for _ in range(steps):
            current = _py_rk4_step(current, dt, derivatives_fn)
        return current

    def quaternion_multiply(self, q1, q2) -> Tuple[float, float, float, float]:
        """Quaternion Hamilton product."""
        return _py_attitude_quaternion_multiply(q1, q2)

    def quaternion_to_euler(self, q) -> Tuple[float, float, float]:
        """Quaternion to Euler angles."""
        return _py_attitude_to_euler(q)

    def proximity_check(self, pos_a, pos_b, safety_radius=100.0) -> SafetyCheck:
        """Check proximity safety."""
        return _py_proximity_check(pos_a, pos_b, safety_radius)

    def deorbit_burn(self, altitude, velocity, target_alt=0.0) -> Dict[str, float]:
        """Calculate deorbit burn."""
        return _py_deorbit_burn(altitude, velocity, target_alt)

    def structural_stress(self, load, area, yield_strength=250e6) -> Dict[str, float]:
        """Calculate structural stress."""
        return _py_structural_stress(load, area, yield_strength)

    def collision_risk(self, pos_a, vel_a, pos_b, vel_b, radius_a=1.0, radius_b=1.0) -> Dict[str, float]:
        """Calculate collision risk."""
        return _py_collision_risk(pos_a, vel_a, pos_b, vel_b, radius_a, radius_b)

    def get_status(self) -> Dict[str, Any]:
        """Get bridge status."""
        return {
            "rust_available": self.rust_available,
            "library_loaded": self.lib is not None,
            "fallback_mode": not self.rust_available,
            "capabilities": [
                "hohmann_transfer", "lambert_solve", "rk4_integrate",
                "quaternion_multiply", "quaternion_to_euler",
                "proximity_check", "deorbit_burn",
                "structural_stress", "collision_risk",
            ],
        }


# Singleton
bridge = RustAvionicsBridge()

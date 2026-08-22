"""
ZICORE Telemetry Simulation - Real-time cockpit data
Provides simulated flight data for the cockpit dashboard.
"""
import math
import time
import random
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class MissionState:
    """Current mission state."""
    mission_type: str = "lunar"
    mission_name: str = "ZIO-ALPHA LUNAR TRANSFER"
    start_time: float = 0.0
    phase: str = "coast"
    total_duration_days: float = 3.0
    elapsed_days: float = 0.0


class TelemetrySimulator:
    """Generates realistic telemetry data for cockpit display."""

    def __init__(self):
        self.mission = MissionState(start_time=time.time())
        self.start_time = time.time()
        self._update_mission()

    def _update_mission(self):
        elapsed = time.time() - self.mission.start_time
        self.mission.elapsed_days = elapsed / 86400.0
        progress = self.mission.elapsed_days / self.mission.total_duration_days

        if progress < 0.05:
            self.mission.phase = "launch"
        elif progress < 0.15:
            self.mission.phase = "leo_insertion"
        elif progress < 0.25:
            self.mission.phase = "trans_lunar_injection"
        elif progress < 0.9:
            self.mission.phase = "coast"
        elif progress < 0.95:
            self.mission.phase = "lunar_orbit_insertion"
        else:
            self.mission.phase = "approach"

    def get_telemetry(self) -> Dict[str, Any]:
        """Get current telemetry data."""
        self._update_mission()
        t = time.time() - self.start_time
        progress = min(1.0, self.mission.elapsed_days / self.mission.total_duration_days)

        altitude = 400 + 380000 * progress * math.sin(progress * math.pi * 0.8)
        velocity = 7.68 - 4.0 * progress + 2.0 * math.sin(progress * math.pi)
        fuel = max(0, 98 - progress * 45)

        return {
            "timestamp": t,
            "mission": {
                "name": self.mission.mission_name,
                "type": self.mission.mission_type,
                "phase": self.mission.phase,
                "elapsed_days": round(self.mission.elapsed_days, 2),
                "total_days": self.mission.total_duration_days,
                "progress_pct": round(progress * 100, 1),
            },
            "navigation": {
                "altitude_km": round(altitude, 1),
                "velocity_kms": round(velocity, 2),
                "heading_deg": round((275.4 + t * 0.5) % 360, 1),
                "latitude": round(math.sin(t * 0.01) * 28.5, 4),
                "longitude": round(math.cos(t * 0.008) * 45.2, 4),
            },
            "propulsion": {
                "thrust_kn": round(7600 * (0.1 + 0.9 * (1 - progress)), 0),
                "isp_s": 380,
                "fuel_pct": round(fuel, 1),
                "engine_status": "nominal" if fuel > 10 else "low_fuel",
            },
            "power": {
                "solar_gen_kw": round(12.5 + math.sin(t * 0.1) * 2, 1),
                "battery_pct": round(92 + math.sin(t * 0.05) * 3, 1),
                "load_kw": round(8.2 + math.sin(t * 0.2) * 1, 1),
            },
            "thermal": {
                "hull_temp_c": round(-170 + 50 * progress + math.sin(t * 0.3) * 5, 1),
                "engine_temp_c": round(850 + math.sin(t * 0.5) * 50, 0),
                "cryo_temp_k": round(20 + math.sin(t * 0.1) * 2, 1),
            },
            "communications": {
                "signal_strength_pct": round(87 + math.sin(t * 0.2) * 8, 1),
                "latency_ms": round(120 + 200 * progress + math.sin(t * 0.3) * 30, 0),
                "data_rate_kbps": round(1024 - 500 * progress, 0),
            },
            "modules": {
                "zinav": {"status": "active", "mode": self.mission.phase},
                "zihab": {"status": "active", "pressure_kpa": 101.3, "o2_pct": 21.0},
                "zipower": {"status": "active", "output_kw": round(12.5 + math.sin(t * 0.1) * 2, 1)},
                "ziship": {"status": "active", "structural_integrity": 99.8},
                "zidrone": {"status": "standby", "active_units": 0},
                "zirobot": {"status": "standby"},
                "zicomm": {"status": "active", "bandwidth_mbps": round(10 - 5 * progress, 1)},
                "zieco": {"status": "active", "o2_generation": "nominal"},
                "zimed": {"status": "active", "crew_health": "nominal"},
                "zicorex": {"status": "active", "cpu_load": round(45 + math.sin(t * 0.2) * 15, 0)},
                "zilink": {"status": "active"},
                "zivr": {"status": "standby"},
                "zisec": {"status": "active", "threat_level": "nominal"},
                "zicriogen": {"status": "active", "temp_k": round(20 + math.sin(t * 0.1) * 2, 1)},
                "zimaury": {"status": "standby"},
            },
            "trajectory": {
                "delta_v_remaining_ms": round(3100 * (1 - progress), 0),
                "time_to_go": f"{max(0, 3-progress*3):.1f}d {max(0, (24-progress*24)%24):.0f}h",
                "transfer_angle_deg": round(progress * 180, 1),
            },
            "attitude": {
                "pitch_deg": round(math.sin(t * 0.1) * 5, 1),
                "roll_deg": round(math.sin(t * 0.15) * 3, 1),
                "yaw_deg": round((275.4 + t * 0.5) % 360, 1),
            },
        }

    def get_module_status(self) -> Dict[str, Any]:
        """Get status of all Zi modules."""
        t = time.time() - self.start_time
        return {
            "zinav": {"status": "active", "health": 99.9},
            "zihab": {"status": "active", "health": 99.7},
            "zipower": {"status": "active", "health": 99.8},
            "ziship": {"status": "active", "health": 99.9},
            "zidrone": {"status": "standby", "health": 100},
            "zirobot": {"status": "standby", "health": 100},
            "zicomm": {"status": "active", "health": 99.5},
            "zieco": {"status": "active", "health": 99.8},
            "zimed": {"status": "active", "health": 100},
            "zicorex": {"status": "active", "health": 99.9},
            "zilink": {"status": "active", "health": 99.7},
            "zivr": {"status": "standby", "health": 100},
            "zisec": {"status": "active", "health": 100},
            "zicriogen": {"status": "active", "health": 99.6},
            "zimaury": {"status": "standby", "health": 100},
        }


telemetry_sim = TelemetrySimulator()

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.modules import (
    ZIHabState, ZiNavState, ZiPowerState, ZiShipState, ZIDroneState,
    ZIRobotState, ZICommState, ZIEcoState, ZIMedState, ZiCoreXState,
    ZILinkState, ZIVRState, ZISecState, ZiCRIOGENState, ZiMAURYState,
    GPDEngine,
)

class TestModuleStates:
    def test_zihab_defaults(self):
        s = ZIHabState()
        assert s.o2 == 20.5
        assert s.status == "nominal"

    def test_zinav_contains_ziaxis(self):
        s = ZiNavState()
        assert hasattr(s, "ziaxis")
        assert s.ziaxis.name == "ziaxis"
        assert s.hierarchy["zinav"]["status"] == "nominal"
        assert s.hierarchy["ziaxis"]["status"] == "standby"

    def test_zinav_update(self):
        s = ZiNavState()
        s.update({"alt_km": 500, "vel_kms": 8.0})
        assert s.alt_km == 500.0
        assert s.vel_kms == 8.0

    def test_zinav_update_ziaxis(self):
        s = ZiNavState()
        s.update({"ziaxis": {"axial_alignment_deg": 5.0, "gpd_active": True}})
        assert s.ziaxis.axial_alignment_deg == 5.0
        assert s.ziaxis.gpd_active == True

    def test_zihab_update(self):
        s = ZIHabState()
        s.update({"o2": 19.5, "temp": 24.0})
        assert s.o2 == 19.5
        assert s.temp == 24.0

    def test_zipower_defaults(self):
        s = ZiPowerState()
        assert s.solar_w == 1200.0
        assert s.battery_pct == 85.0

    def test_ziship_defaults(self):
        s = ZiShipState()
        assert s.hull_integrity_pct == 100.0
        assert s.propulsion_mode == "ion"

    def test_zidrone_defaults(self):
        s = ZIDroneState()
        assert s.swarm_size == 12
        assert s.mission_phase == "survey"

    def test_zirobot_defaults(self):
        s = ZIRobotState()
        assert s.units_active == 3
        assert s.autonomy_level == "semi"

    def test_zicomm_defaults(self):
        s = ZICommState()
        assert s.link_status == "established"
        assert s.bandwidth_mbps == 150.0

    def test_zieco_defaults(self):
        s = ZIEcoState()
        assert s.water_recovery_pct == 92.0
        assert s.air_quality_index == 12

    def test_zimed_defaults(self):
        s = ZIMedState()
        assert s.crew_health_index == 94
        assert s.heart_rate_bpm == 72

    def test_zicorex_defaults(self):
        s = ZiCoreXState()
        assert s.compute_load_pct == 62.0
        assert s.memory_total_gb == 512.0

    def test_zilink_defaults(self):
        s = ZILinkState()
        assert s.data_rate_gbps == 10.0
        assert s.optical_links == 2

    def test_zivr_defaults(self):
        s = ZIVRState()
        assert s.headsets_active == 2
        assert s.fps == 90

    def test_zisec_defaults(self):
        s = ZISecState()
        assert s.firewall == "active"
        assert s.auth_level == 3

    def test_zicriogen_defaults(self):
        s = ZiCRIOGENState()
        assert s.propellant_temp_k == 20.0
        assert s.fuel_level_pct == 72.0

    def test_zimaury_defaults(self):
        s = ZiMAURYState()
        assert s.personnel == 4
        assert s.readiness_level == 2

    def test_all_modules_serialize(self):
        for cls in [ZIHabState, ZiNavState, ZiPowerState, ZiShipState,
                     ZIDroneState, ZIRobotState, ZICommState, ZIEcoState,
                     ZIMedState, ZiCoreXState, ZILinkState, ZIVRState,
                     ZISecState, ZiCRIOGENState, ZiMAURYState]:
            s = cls()
            d = s.model_dump()
            assert isinstance(d, dict)
            assert "name" in d
            assert "status" in d

class TestGPDEngine:
    def test_gravitational_gradient(self):
        g = GPDEngine.gravitational_gradient(5.97e24, 400000)
        assert g < 0

    def test_tidal_force(self):
        grad = GPDEngine.gravitational_gradient(5.97e24, 400000)
        tf = GPDEngine.tidal_force(50000, 82, grad)
        assert tf != 0

    def test_energy_distribution(self):
        e = GPDEngine.energy_distribution(400, 7.68, 50000)
        assert e["total_j"] > 0
        assert e["distributed"] == True
        assert e["potential_j"] < e["kinetic_j"]

    def test_path_stability(self):
        s = GPDEngine.path_stability(0, 50)
        assert s == 100.0
        s2 = GPDEngine.path_stability(10, 30)
        assert s2 < 100

    def test_descent_angle(self):
        a = GPDEngine.descent_angle(5, -1.28e-6)
        assert isinstance(a, float)

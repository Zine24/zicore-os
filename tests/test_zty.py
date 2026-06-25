import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from zty import AircraftConfig, StageConfig, PropulsionConfig
from zty.factory import ZTYFactory

class TestAircraftConfig:
    def test_blackvanta_config(self):
        factory = ZTYFactory()
        config = factory.get_template("blackvanta")
        assert config is not None
        assert config.name.startswith("BlackVanta")
        assert config.total_mass_kg() > 0
        assert config.mass_ratio() > 1

    def test_ziron_sigma_config(self):
        factory = ZTYFactory()
        config = factory.get_template("ziron_sigma")
        assert config is not None
        assert config.total_mass_kg() > 0

    def test_zi_voyager_config(self):
        factory = ZTYFactory()
        config = factory.get_template("zi_voyager")
        assert config is not None
        assert config.payload_kg == 1500

    def test_obsidiana_config(self):
        factory = ZTYFactory()
        config = factory.get_template("obsidiana")
        assert config is not None
        assert config.total_mass_kg() > 0

    def test_list_vehicles(self):
        factory = ZTYFactory()
        v = factory.list_vehicles()
        assert len(v) == 4
        assert "blackvanta" in v

    def test_analyze_all(self):
        factory = ZTYFactory()
        for name in factory.list_vehicles():
            report = factory.generate_report(name)
            assert report is not None
            assert report["total_mass_kg"] > 0
            assert report["delta_v_m_s"] > 0

class TestAeroEngine:
    def test_wing_area(self):
        from zty.engines.aerodynamics import AeroEngine
        a = AeroEngine.wing_area(50000, 300)
        assert a > 0

    def test_drag_force(self):
        from zty.engines.aerodynamics import AeroEngine
        d = AeroEngine.drag_force(1.2, 100, 500, 0.5)
        assert d > 0

class TestStructuralEngine:
    def test_beam_stress(self):
        from zty.engines.structures import StructuralEngine
        s = StructuralEngine.beam_stress(500000, 5, 0.1)
        assert s > 0

    def test_safety_factor(self):
        from zty.engines.structures import StructuralEngine
        sf = StructuralEngine.safety_factor(500e6, 250e6)
        assert sf == 2.0

class TestPropulsionEngine:
    def test_thrust_chamber_pressure(self):
        from zty.engines.propulsion import PropulsionEngine
        p = PropulsionEngine.thrust_chamber_pressure(5.0, 3000)
        assert p > 0

    def test_delta_v(self):
        from zty.engines.propulsion import PropulsionEngine
        dv = PropulsionEngine.delta_v(450, 9.81, 3.0)
        assert dv > 0
        assert dv == pytest.approx(450 * 9.81 * 1.0986, rel=0.01)

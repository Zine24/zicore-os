import json
from typing import Optional
from .engines.aerodynamics import AeroEngine
from .engines.structures import StructuralEngine
from .engines.propulsion import PropulsionEngine
from .generators.aircraft_factory import AircraftFactory
from . import AircraftConfig

class ZTYFactory:
    """Z-TY: Fábrica Inteligente de Aeronaves"""
    
    def __init__(self):
        self.aero = AeroEngine()
        self.struct = StructuralEngine()
        self.prop = PropulsionEngine()
        self.factory = AircraftFactory()
        self._cache = {}
    
    def get_template(self, name: str) -> Optional[AircraftConfig]:
        templates = {
            "blackvanta": self.factory.blackvanta(),
            "ziron_sigma": self.factory.ziron_sigma(),
            "zi_voyager": self.factory.zi_voyager(),
            "obsidiana": self.factory.obsidiana(),
        }
        return templates.get(name)
    
    def analyze(self, config: AircraftConfig) -> dict:
        return {
            "name": config.name,
            "type": config.vehicle_type,
            "total_mass_kg": round(config.total_mass_kg(), 1),
            "dry_mass_kg": round(sum(s.dry_mass_kg for s in config.stages), 1),
            "propellant_mass_kg": round(sum(s.propellant_mass_kg for s in config.stages), 1),
            "payload_kg": config.payload_kg,
            "mass_ratio": round(config.mass_ratio(), 3),
            "delta_v_m_s": round(config.delta_v(), 1),
            "crew": config.crew,
            "t/w": round(sum(s.engines * config.propulsion.thrust_kN * 1000 for s in config.stages) / (config.total_mass_kg() * 9.81), 2) if config.total_mass_kg() > 0 else 0,
        }
    
    def generate_report(self, name: str) -> Optional[dict]:
        config = self.get_template(name)
        if not config:
            return None
        return self.analyze(config)
    
    def list_vehicles(self) -> list:
        return ["blackvanta", "ziron_sigma", "zi_voyager", "obsidiana"]

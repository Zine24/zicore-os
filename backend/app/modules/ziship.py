from .base import BaseModuleState

class ZiShipState(BaseModuleState):
    name: str = "ziship"
    hull_integrity_pct: float = 100.0
    propulsion_mode: str = "ion"
    thermal_load_kw: float = 450.0
    radiation_shield_pct: float = 95.0
    docking_status: str = "undocked"
    pressure_hull_kpa: float = 101.3

    def _eval(self):
        if self.hull_integrity_pct < 70:
            self.status = "critical"
        elif self.hull_integrity_pct < 90 or self.thermal_load_kw > 800:
            self.status = "warning"
        else:
            self.status = "nominal"

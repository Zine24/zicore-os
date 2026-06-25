from .base import BaseModuleState

class ZiCRIOGENState(BaseModuleState):
    name: str = "zicriogen"
    propellant_temp_k: float = 20.0
    tank_pressure_kpa: float = 250.0
    fuel_level_pct: float = 72.0
    oxidizer_level_pct: float = 68.0
    boiloff_rate_gh: float = 0.5
    insulation_integrity: str = "nominal"

    def _eval(self):
        if self.fuel_level_pct < 10 or self.tank_pressure_kpa > 400:
            self.status = "critical"
        elif self.fuel_level_pct < 30 or self.boiloff_rate_gh > 2.0:
            self.status = "warning"
        else:
            self.status = "nominal"

from .base import BaseModuleState

class ZIEcoState(BaseModuleState):
    name: str = "zieco"
    co2_scrub_rate_gph: float = 2.5
    water_recovery_pct: float = 92.0
    waste_recycled_kg: float = 1.8
    air_quality_index: int = 12
    plant_health_pct: float = 88.0
    o2_generation_gh: float = 45.0

    def _eval(self):
        if self.water_recovery_pct < 60 or self.air_quality_index > 80:
            self.status = "critical"
        elif self.water_recovery_pct < 80 or self.air_quality_index > 50:
            self.status = "warning"
        else:
            self.status = "nominal"

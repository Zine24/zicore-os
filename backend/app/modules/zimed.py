from .base import BaseModuleState

class ZIMedState(BaseModuleState):
    name: str = "zimed"
    crew_health_index: int = 94
    heart_rate_bpm: int = 72
    bp_systolic: int = 120
    bp_diastolic: int = 80
    radiation_exposure_msv: float = 0.8
    medical_supplies_pct: float = 85.0

    def _eval(self):
        if self.crew_health_index < 60 or self.radiation_exposure_msv > 100:
            self.status = "critical"
        elif self.crew_health_index < 80 or self.medical_supplies_pct < 40:
            self.status = "warning"
        else:
            self.status = "nominal"

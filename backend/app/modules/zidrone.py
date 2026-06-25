from .base import BaseModuleState

class ZIDroneState(BaseModuleState):
    name: str = "zidrone"
    swarm_size: int = 12
    deployed: int = 4
    avg_battery_pct: float = 78.0
    range_km: float = 15.0
    signal_strength_dbm: float = -65.0
    mission_phase: str = "survey"

    def _eval(self):
        if self.avg_battery_pct < 15:
            self.status = "critical"
        elif self.avg_battery_pct < 30 or self.signal_strength_dbm < -80:
            self.status = "warning"
        else:
            self.status = "nominal"

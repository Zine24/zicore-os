from .base import BaseModuleState

class ZiMAURYState(BaseModuleState):
    name: str = "zimaury"
    personnel: int = 4
    readiness_level: int = 2
    drones_armed: int = 3
    tactical_mode: str = "patrol"
    shield_status: str = "active"
    weapon_safety: str = "safe"

    def _eval(self):
        if self.shield_status == "offline" or self.weapon_safety == "armed":
            self.status = "critical"
        elif self.shield_status == "standby" or self.readiness_level < 2:
            self.status = "warning"
        else:
            self.status = "nominal"

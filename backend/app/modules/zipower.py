from .base import BaseModuleState

class ZiPowerState(BaseModuleState):
    name: str = "zipower"
    solar_w: float = 1200.0
    battery_pct: float = 85.0
    load_w: float = 980.0
    grid_v: float = 28.5

    def _eval(self):
        net = self.solar_w - self.load_w
        if self.battery_pct < 20:
            self.status = "critical"
        elif net < -200 or self.battery_pct < 40:
            self.status = "warning"
        else:
            self.status = "nominal"

    @property
    def net_w(self) -> float:
        return self.solar_w - self.load_w

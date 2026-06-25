from .base import BaseModuleState

class ZIHabState(BaseModuleState):
    name: str = "zihab"
    o2: float = 20.5
    co2: float = 0.04
    temp: float = 22.0
    humidity: float = 45.0
    pressure: float = 101.3
    power_w: float = 320.0

    def _eval(self):
        issues = []
        if self.o2 < 19.5:
            issues.append("o2")
        if self.co2 > 0.5:
            issues.append("co2")
        if self.temp > 30 or self.temp < 15:
            issues.append("temp")
        if self.pressure < 90.0 or self.pressure > 110.0:
            issues.append("pressure")
        if len(issues) > 1:
            self.status = "critical"
        elif len(issues) > 0:
            self.status = "warning"
        else:
            self.status = "nominal"

from .base import BaseModuleState

class ZIVRState(BaseModuleState):
    name: str = "zivr"
    headsets_active: int = 2
    environment: str = "command"
    fps: int = 90
    latency_ms: float = 12.0
    resolution: str = "4k"
    haptic_feedback: bool = True

    def _eval(self):
        if self.fps < 30 or self.latency_ms > 50:
            self.status = "critical"
        elif self.fps < 60 or self.latency_ms > 20:
            self.status = "warning"
        else:
            self.status = "nominal"

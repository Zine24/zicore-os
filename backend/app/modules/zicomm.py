from .base import BaseModuleState

class ZICommState(BaseModuleState):
    name: str = "zicomm"
    link_status: str = "established"
    bandwidth_mbps: float = 150.0
    latency_ms: float = 42.0
    packet_loss_pct: float = 0.02
    encryption: str = "aes-256"
    antennas_active: int = 3

    def _eval(self):
        if self.link_status == "offline":
            self.status = "critical"
        elif self.latency_ms > 200 or self.packet_loss_pct > 1.0:
            self.status = "warning"
        else:
            self.status = "nominal"

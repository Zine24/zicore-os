from .base import BaseModuleState

class ZILinkState(BaseModuleState):
    name: str = "zilink"
    up_channels: int = 8
    down_channels: int = 8
    data_rate_gbps: float = 10.0
    optical_links: int = 2
    rf_links: int = 4
    link_margin_db: float = 3.5

    def _eval(self):
        if self.link_margin_db < 1.0:
            self.status = "critical"
        elif self.link_margin_db < 2.0:
            self.status = "warning"
        else:
            self.status = "nominal"

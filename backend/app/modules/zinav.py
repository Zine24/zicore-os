from pydantic import BaseModel
from .base import BaseModuleState

class ZiAXISState(BaseModuleState):
    name: str = "ziaxis"
    axial_alignment_deg: float = 0.0
    mass_distribution_pct: float = 50.0
    gradient_lock: bool = False
    gpd_active: bool = False
    descent_phase: str = "idle"
    tidal_force_n: float = 0.0
    status: str = "standby"

class ZiNavState(BaseModuleState):
    name: str = "zinav"
    alt_km: float = 400.0
    vel_kms: float = 7.68
    inclination_deg: float = 51.6
    dv_remaining: float = 1200.0
    fuel_pct: float = 65.0
    phase: str = "orbital"
    mode: str = "zinav-orbit"
    ziaxis: ZiAXISState = ZiAXISState()

    def update(self, data: dict):
        for k, v in data.items():
            if k == "ziaxis" and isinstance(v, dict):
                self.ziaxis.update(v)
            elif hasattr(self, k):
                current = getattr(self, k)
                if isinstance(current, float):
                    try:
                        v = float(v)
                    except (ValueError, TypeError):
                        continue
                elif isinstance(current, int):
                    try:
                        v = int(v)
                    except (ValueError, TypeError):
                        continue
                setattr(self, k, v)
        self._eval()

    def _eval(self):
        if self.fuel_pct < 10:
            self.status = "critical"
        elif self.fuel_pct < 30:
            self.status = "warning"
        else:
            self.status = "nominal"

    @property
    def hierarchy(self) -> dict:
        return {
            "zinav": {"mode": self.mode, "phase": self.phase, "status": self.status},
            "ziaxis": self.ziaxis.model_dump(),
            "gpd": {"active": self.ziaxis.gpd_active, "phase": self.ziaxis.descent_phase},
        }

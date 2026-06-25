from .base import BaseModuleState

class ZiCoreXState(BaseModuleState):
    name: str = "zicorex"
    compute_load_pct: float = 62.0
    memory_used_gb: float = 128.0
    memory_total_gb: float = 512.0
    inference_queue: int = 3
    cluster_nodes: int = 4
    ai_model: str = "mistral-7b-zicore"

    def _eval(self):
        if self.compute_load_pct > 95 or self.memory_used_gb > self.memory_total_gb * 0.95:
            self.status = "critical"
        elif self.compute_load_pct > 80:
            self.status = "warning"
        else:
            self.status = "nominal"

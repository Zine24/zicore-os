from pydantic import BaseModel
from typing import Any

class BaseModuleState(BaseModel):
    """Estado base para todos los modulos ZIO."""
    name: str
    status: str = "nominal"

    def update(self, data: dict):
        for k, v in data.items():
            if not hasattr(self, k):
                continue
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
        pass

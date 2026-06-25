from abc import ABC, abstractmethod
from pydantic import BaseModel

class InferenceResult(BaseModel):
    engine: str
    output: str
    confidence: float
    latency_ms: float
    metadata: dict = {}

class BaseEngine(ABC):
    @abstractmethod
    async def infer(self, module: str, instruction: str, input_data: str) -> InferenceResult:
        pass

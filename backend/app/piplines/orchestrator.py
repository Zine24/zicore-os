import asyncio
import logging
from typing import Optional
from ..engines.base import InferenceResult
from ..engines.engine_a import DeterministicEngine
from ..engines.engine_b import MLEngine
from ..config import CONFIDENCE_THRESHOLD

logger = logging.getLogger("zicore.orchestrator")

class PipelineOrchestrator:
    """Orquestador de pipeline de inferencia dual"""
    
    def __init__(self):
        self.engine_a = DeterministicEngine()
        self.engine_b = MLEngine()
    
    async def infer(self, module: str, instruction: str, input_data: str) -> dict:
        tasks = [
            self.engine_a.infer(module, instruction, input_data),
            self.engine_b.infer(module, instruction, input_data),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                results[i] = InferenceResult(
                    engine=f"engine_{['a','b'][i]}",
                    output=f"ERROR: {str(r)}",
                    confidence=0.0,
                    latency_ms=0,
                    metadata={"error": str(r)}
                )
        
        result_a: InferenceResult = results[0]
        result_b: InferenceResult = results[1]
        
        merged = self._merge(results)
        return {
            "engine_a": result_a.model_dump(),
            "engine_b": result_b.model_dump(),
            "merged": merged,
            "consensus": merged["confidence"] >= CONFIDENCE_THRESHOLD,
        }
    
    def _merge(self, results: list) -> dict:
        a, b = results
        conf = (a.confidence * 0.6 + b.confidence * 0.4)
        
        if a.confidence >= b.confidence:
            output = a.output
        else:
            output = b.output
        
        if abs(a.confidence - b.confidence) < 0.15:
            output = f"[CROSS-VALIDATED] {a.output} | ML añade: {b.output[:100]}..."
        
        return {
            "output": output,
            "confidence": round(conf, 3),
            "engine_used": "a" if a.confidence > b.confidence else "b",
        }

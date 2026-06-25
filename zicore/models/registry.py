MODEL_REGISTRY = {
    "engine_a": {
        "name": "Deterministic Solver",
        "type": "rules",
        "version": "0.1.0",
        "status": "ready",
        "languages": ["python"],
        "description": "Motor basado en reglas determinísticas y solvers numéricos",
    },
    "engine_b": {
        "name": "ZiCore LLM",
        "type": "llm",
        "version": "0.1.0",
        "status": "mock",
        "languages": ["python"],
        "base_model": "Meta-Llama-3.1-8B",
        "fine_tuned": False,
        "description": "Motor ML basado en Unsloth + Llama-3.1-8B fine-tuneado",
    },
}

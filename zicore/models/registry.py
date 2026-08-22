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
    "ollama": {
        "name": "llama3.1:8b",
        "type": "llm",
        "version": "1.0.2",
        "status": "not_loaded",
        "languages": ["python", "multilingual"],
        "base_model": "llama3.1:8b",
        "description": "Modern coding model from Ollama, 8B parameters with 8k context window",
        "capabilities": ["code_generation", "reasoning", "text_completion"],
        "parameters": {
            "model": "llama3.1:8b",
            "temperature": 0.1,
            "max_tokens": 2048,
            "num_ctx": 8192,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0
        }
    },
}

"""
Local LLM Inference - Uses HuggingFace transformers with small models.
Fallback for zicore_native when no external provider is available.
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger("zicore.local_llm")

_local_model = None
_tokenizer = None
_model_name = None

MODELS_DIR = Path(__file__).parent.parent / "data" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

FALLBACK_MODELS = [
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "microsoft/phi-1_5",
    "Qwen/Qwen2-0.5B-Instruct",
    "HuggingFaceTB/SmolLM-1.7B-Instruct",
]


def _get_device():
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def load_model(model_name: str = None):
    global _local_model, _tokenizer, _model_name
    if _local_model is not None:
        return True

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError:
        logger.warning("transformers not installed. Install with: pip install transformers torch")
        return False

    device = _get_device()
    if model_name is None:
        model_name = os.environ.get("ZICORE_LOCAL_MODEL", FALLBACK_MODELS[0])

    logger.info(f"Loading local model: {model_name} on {device}")
    try:
        _tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=str(MODELS_DIR),
            trust_remote_code=True,
        )
        _local_model = AutoModelForCausalLM.from_pretrained(
            model_name,
            cache_dir=str(MODELS_DIR),
            torch_dtype="auto" if device == "cuda" else "float32",
            device_map="auto" if device == "cuda" else None,
            trust_remote_code=True,
        )
        if device == "cpu":
            _local_model = _local_model.to("cpu")
        _model_name = model_name
        logger.info(f"Model loaded: {model_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to load model {model_name}: {e}")
        _local_model = None
        _tokenizer = None
        return False


def generate(prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
    global _local_model, _tokenizer

    if _local_model is None:
        if not load_model():
            return ""

    try:
        import torch
        messages = [
            {"role": "system", "content": "You are ZIO, a helpful aerospace AI assistant. Respond concisely and helpfully."},
            {"role": "user", "content": prompt},
        ]

        if hasattr(_tokenizer, "apply_chat_template"):
            text = _tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            text = f"System: You are ZIO, a helpful aerospace AI assistant.\nUser: {prompt}\nAssistant:"

        inputs = _tokenizer(text, return_tensors="pt")
        if _local_model.device.type != "cpu":
            inputs = {k: v.to(_local_model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = _local_model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature if temperature > 0 else 0.01,
                do_sample=temperature > 0,
                top_p=0.9,
                repetition_penalty=1.1,
            )

        generated = outputs[0][inputs["input_ids"].shape[1]:]
        response = _tokenizer.decode(generated, skip_special_tokens=True).strip()
        return response
    except Exception as e:
        logger.error(f"Generation error: {e}")
        return ""


def is_available() -> bool:
    try:
        import transformers
        import torch
        return True
    except ImportError:
        return False


def get_status() -> dict:
    return {
        "available": is_available(),
        "model_loaded": _local_model is not None,
        "model_name": _model_name,
        "device": _get_device() if is_available() else "none",
    }

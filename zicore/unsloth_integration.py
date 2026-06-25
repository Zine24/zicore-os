"""
ZICORE Unsloth Training Integration - Motor B ML Fine-tuning
Manages LoRA fine-tuning of Llama-3.1-8B / Mistral-7B via Unsloth on Colab.
"""
import json
import os
import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger("zicore.unsloth")

TRAINING_DIR = Path(__file__).parent.parent / "data" / "training"
TRAINING_DIR.mkdir(parents=True, exist_ok=True)

TRAINING_DATA_FILE = Path(__file__).parent.parent / "zicore_training.jsonl"
CHECKPOINT_DIR = TRAINING_DIR / "checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)


@dataclass
class TrainingConfig:
    model_name: str = "unsloth/Meta-Llama-3.1-8B"
    max_seq_length: int = 2048
    lora_r: int = 16
    lora_alpha: int = 16
    lora_dropout: float = 0.0
    batch_size: int = 2
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    num_epochs: int = 3
    warmup_steps: int = 5
    max_steps: int = -1
    output_dir: str = str(CHECKPOINT_DIR / "latest")
    save_steps: int = 100
    logging_steps: int = 10
    fp16: bool = False
    bf16: bool = True
    optim: str = "adamw_8bit"
    weight_decay: float = 0.01
    lr_scheduler_type: str = "linear"
    seed: int = 42

    def to_dict(self) -> dict:
        return {
            "model_name": self.model_name,
            "max_seq_length": self.max_seq_length,
            "lora_r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "batch_size": self.batch_size,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "learning_rate": self.learning_rate,
            "num_epochs": self.num_epochs,
            "warmup_steps": self.warmup_steps,
            "max_steps": self.max_steps,
            "output_dir": self.output_dir,
            "save_steps": self.save_steps,
            "logging_steps": self.logging_steps,
            "fp16": self.fp16,
            "bf16": self.bf16,
            "optim": self.optim,
            "weight_decay": self.weight_decay,
            "lr_scheduler_type": self.lr_scheduler_type,
            "seed": self.seed,
        }


@dataclass
class TrainingStatus:
    is_training: bool = False
    current_step: int = 0
    total_steps: int = 0
    loss: float = 0.0
    learning_rate: float = 0.0
    epoch: float = 0.0
    elapsed_seconds: float = 0.0
    model_path: str = ""
    status: str = "idle"


class UnslothTrainer:
    """Manages Unsloth fine-tuning for ZICORE Motor B."""

    def __init__(self):
        self.config = TrainingConfig()
        self.status = TrainingStatus()
        self.training_history: List[Dict[str, Any]] = []
        self._load_training_data()

    def _load_training_data(self):
        """Load training data from JSONL file."""
        self.training_data = []
        if TRAINING_DATA_FILE.exists():
            with open(TRAINING_DATA_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            self.training_data.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        logger.info(f"Loaded {len(self.training_data)} training examples")

    def generate_training_script(self, config: Optional[Dict[str, Any]] = None) -> str:
        """Generate Unsloth training script for Colab."""
        if config:
            for k, v in config.items():
                if hasattr(self.config, k):
                    setattr(self.config, k, v)

        c = self.config
        script = f'''# ZICORE Motor B Fine-tuning with Unsloth
# Run on Google Colab (Free T4 GPU)
# Runtime > Change runtime type > T4 GPU

!pip install unsloth
!pip install --force-reinstall --no-cache-dir --no-deps unsloth

from unsloth import FastLanguageModel
import torch
from datasets import Dataset
from trl import SFTTrainer
from transformers import TrainingArguments

# ── Model Configuration ──────────────────────────────────────────
model_name = "{c.model_name}"
max_seq_length = {c.max_seq_length}
lora_r = {c.lora_r}
lora_alpha = {c.lora_alpha}
lora_dropout = {c.lora_dropout}

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=model_name,
    max_seq_length=max_seq_length,
    dtype=None,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=lora_r,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                     "gate_proj", "up_proj", "down_proj"],
    lora_alpha=lora_alpha,
    lora_dropout=lora_dropout,
    bias="none",
    use_gradient_checkpointing="unsloth",
    random_state=42,
)

# ── Training Data ────────────────────────────────────────────────
# Upload zicore_training.jsonl to Colab, then load:
# from google.colab import files
# uploaded = files.upload()

import json
training_examples = []
with open("zicore_training.jsonl", "r") as f:
    for line in f:
        if line.strip():
            training_examples.append(json.loads(line.strip()))

alpaca_prompt = """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
{{}}

### Input:
{{}}

### Response:
{{}}"""

def format_dataset(examples):
    texts = []
    for ex in examples:
        instruction = ex.get("instruction", "")
        inp = ex.get("input", "")
        output = ex.get("output", "")
        text = alpaca_prompt.format(instruction, inp, output) + tokenizer.eos_token
        texts.append(text)
    return {"text": texts}

dataset = Dataset.from_list(training_examples)
dataset = dataset.map(format_dataset, batched=True)

# ── Trainer ──────────────────────────────────────────────────────
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=dataset,
    dataset_text_field="text",
    max_seq_length=max_seq_length,
    args=TrainingArguments(
        output_dir="{c.output_dir}",
        per_device_train_batch_size={c.batch_size},
        gradient_accumulation_steps={c.gradient_accumulation_steps},
        learning_rate={c.learning_rate},
        num_train_epochs={c.num_epochs},
        warmup_steps={c.warmup_steps},
        max_steps={c.max_steps},
        fp16={c.fp16},
        bf16={c.bf16},
        optim="{c.optim}",
        weight_decay={c.weight_decay},
        lr_scheduler_type="{c.lr_scheduler_type}",
        logging_steps={c.logging_steps},
        save_steps={c.save_steps},
        seed={c.seed},
        report_to="none",
    ),
)

# ── Train ────────────────────────────────────────────────────────
print("Starting ZICORE Motor B training...")
trainer_stats = trainer.train()
print(f"Training complete! Loss: {{trainer_stats.training_loss:.4f}}")

# ── Save Model ───────────────────────────────────────────────────
model.save_pretrained("{c.output_dir}/lora_model")
tokenizer.save_pretrained("{c.output_dir}/lora_model")
print(f"Model saved to {c.output_dir}/lora_model")

# ── Export to GGUF (for Ollama/llama.cpp) ────────────────────────
model.save_pretrained_gguf("{c.output_dir}/gguf", tokenizer, quantization_method="q4_k_m")
print("GGUF exported for Ollama/llama.cpp")
'''
        return script

    def start_training(self, config: Optional[Dict[str, Any]] = None,
                        data_path: Optional[str] = None) -> Dict[str, Any]:
        """Start training (simulated for local, generates script for Colab)."""
        if self.status.is_training:
            return {"error": "Training already in progress"}

        if config:
            for k, v in config.items():
                if hasattr(self.config, k):
                    setattr(self.config, k, v)

        if data_path and os.path.exists(data_path):
            self.training_data = []
            with open(data_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            self.training_data.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

        self.status = TrainingStatus(
            is_training=True,
            current_step=0,
            total_steps=max(1, len(self.training_data) * self.config.num_epochs),
            status="preparing",
        )

        script = self.generate_training_script()
        script_path = TRAINING_DIR / "train_unsloth.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script)

        self.training_history.append({
            "timestamp": time.time(),
            "action": "started",
            "config": self.config.to_dict(),
            "data_size": len(self.training_data),
        })

        return {
            "status": "started",
            "script_path": str(script_path),
            "config": self.config.to_dict(),
            "data_size": len(self.training_data),
            "estimated_time_minutes": len(self.training_data) * self.config.num_epochs * 0.5,
            "instructions": [
                "1. Open Google Colab (colab.research.google.com)",
                "2. Upload zicore_training.jsonl",
                "3. Copy the generated script",
                "4. Runtime > Change runtime type > T4 GPU",
                "5. Run all cells",
                f"6. Model will be saved to {self.config.output_dir}",
            ],
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current training status."""
        return {
            "is_training": self.status.is_training,
            "current_step": self.status.current_step,
            "total_steps": self.status.total_steps,
            "loss": self.status.loss,
            "learning_rate": self.status.learning_rate,
            "epoch": self.status.epoch,
            "status": self.status.status,
            "config": self.config.to_dict(),
            "data_size": len(self.training_data),
            "history": self.training_history[-5:],
        }

    def generate_colab_notebook(self) -> Dict[str, Any]:
        """Generate a Colab-compatible notebook structure."""
        script = self.generate_training_script()
        cells = []

        # Cell 1: Install
        cells.append({
            "cell_type": "code",
            "source": "!pip install unsloth\n!pip install --force-reinstall --no-cache-dir --no-deps unsloth",
            "metadata": {},
        })

        # Cell 2: Imports and model
        cells.append({
            "cell_type": "code",
            "source": script.split("# ── Training Data")[0],
            "metadata": {},
        })

        # Cell 3: Training data
        cells.append({
            "cell_type": "code",
            "source": "# Upload your training data:\n# from google.colab import files\n# uploaded = files.upload()\n\n" + script.split("# ── Training Data")[1].split("# ── Trainer")[0],
            "metadata": {},
        })

        # Cell 4: Training
        cells.append({
            "cell_type": "code",
            "source": script.split("# ── Trainer")[1].split("# ── Save Model")[0],
            "metadata": {},
        })

        # Cell 5: Save
        cells.append({
            "cell_type": "code",
            "source": script.split("# ── Save Model")[1],
            "metadata": {},
        })

        return {
            "cells": cells,
            "metadata": {
                "colab": {"provenance": []},
                "kernelspec": {"display_name": "Python 3", "name": "python3"},
                "language_info": {"name": "python"},
            },
            "nbformat": 4,
            "nbformat_minor": 0,
        }

    def get_training_examples(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get sample training examples."""
        return self.training_data[:n]

    def add_training_example(self, instruction: str, inp: str, output: str):
        """Add a training example."""
        example = {"instruction": instruction, "input": inp, "output": output}
        self.training_data.append(example)
        with open(TRAINING_DATA_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
        return {"status": "added", "total": len(self.training_data)}


# Singleton
trainer = UnslothTrainer()

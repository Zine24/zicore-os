"""
ZICORE Data Retention - Almacenamiento para Entrenamiento
Retiene conversaciones, generaciones y telemetria para fine-tuning de Unsloth.
"""
import os
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

logger = logging.getLogger("zicore.data_retention")

DATA_DIR = Path(__file__).parent.parent / "data" / "retention"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONVERSATIONS_DIR = DATA_DIR / "conversations"
GENERATIONS_DIR = DATA_DIR / "generations"
TELEMETRY_DIR = DATA_DIR / "telemetry"
TRAINING_EXPORT_DIR = DATA_DIR / "training_export"

for d in [CONVERSATIONS_DIR, GENERATIONS_DIR, TELEMETRY_DIR, TRAINING_EXPORT_DIR]:
    d.mkdir(exist_ok=True)

MAX_CONVERSATIONS = 10000
MAX_GENERATIONS = 50000
RETENTION_DAYS = 365


@dataclass
class ConversationEntry:
    """Entrada de conversacion para retencion."""
    session_id: str
    user_message: str
    zio_response: str
    intent: str
    context: Dict[str, Any]
    timestamp: float = 0.0
    entry_id: str = ""

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if not self.entry_id:
            raw = f"{self.session_id}:{self.user_message}:{self.timestamp}"
            self.entry_id = hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GenerationEntry:
    """Entrada de generacion multimedia para retencion."""
    gen_type: str
    prompt: str
    output_path: str
    parameters: Dict[str, Any]
    session_id: str = ""
    timestamp: float = 0.0
    entry_id: str = ""

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if not self.entry_id:
            raw = f"{self.gen_type}:{self.prompt}:{self.timestamp}"
            self.entry_id = hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TelemetryEntry:
    """Entrada de telemetria para analisis."""
    module: str
    data: Dict[str, Any]
    timestamp: float = 0.0
    entry_id: str = ""

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if not self.entry_id:
            raw = f"{self.module}:{self.timestamp}"
            self.entry_id = hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return asdict(self)


class DataRetention:
    """
    Sistema de retencion de datos para entrenamiento de Motor B.
    Almacena conversaciones, generaciones y telemetria.
    """

    def __init__(self):
        self.conversations: List[Dict[str, Any]] = []
        self.generations: List[Dict[str, Any]] = []
        self.telemetry: List[Dict[str, Any]] = []
        self._load_all()

    def _load_all(self):
        """Carga datos existentes desde archivos."""
        self.conversations = self._load_jsonl(CONVERSATIONS_DIR / "conversations.jsonl")
        self.generations = self._load_jsonl(GENERATIONS_DIR / "generations.jsonl")
        self.telemetry = self._load_jsonl(TELEMETRY_DIR / "telemetry.jsonl")
        logger.info(
            f"Loaded: {len(self.conversations)} conversations, "
            f"{len(self.generations)} generations, "
            f"{len(self.telemetry)} telemetry entries"
        )

    def _load_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        """Carga archivo JSONL."""
        entries = []
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        return entries

    def _append_jsonl(self, path: Path, entry: dict):
        """Append a JSONL file."""
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ── CONVERSATIONS ──────────────────────────────────────────────

    def save_conversation(self, session_id: str, user_msg: str, zio_response: str,
                           intent: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Guarda una entrada de conversacion."""
        entry = ConversationEntry(
            session_id=session_id,
            user_message=user_msg,
            zio_response=zio_response,
            intent=intent,
            context=context or {},
        )
        entry_dict = entry.to_dict()
        self.conversations.append(entry_dict)
        self._append_jsonl(CONVERSATIONS_DIR / "conversations.jsonl", entry_dict)

        if len(self.conversations) > MAX_CONVERSATIONS:
            self.conversations = self.conversations[-MAX_CONVERSATIONS:]

        return {"status": "saved", "entry_id": entry.entry_id}

    def get_conversations(self, n: int = 100, intent_filter: str = None) -> List[Dict[str, Any]]:
        """Obtiene las ultimas N conversaciones."""
        data = self.conversations
        if intent_filter:
            data = [c for c in data if c.get("intent") == intent_filter]
        return data[-n:]

    # ── GENERATIONS ────────────────────────────────────────────────

    def save_generation(self, gen_type: str, prompt: str, output_path: str,
                         parameters: Dict[str, Any] = None,
                         session_id: str = "") -> Dict[str, Any]:
        """Guarda una entrada de generacion."""
        entry = GenerationEntry(
            gen_type=gen_type,
            prompt=prompt,
            output_path=output_path,
            parameters=parameters or {},
            session_id=session_id,
        )
        entry_dict = entry.to_dict()
        self.generations.append(entry_dict)
        self._append_jsonl(GENERATIONS_DIR / "generations.jsonl", entry_dict)

        if len(self.generations) > MAX_GENERATIONS:
            self.generations = self.generations[-MAX_GENERATIONS:]

        return {"status": "saved", "entry_id": entry.entry_id}

    def get_generations(self, n: int = 100, gen_type_filter: str = None) -> List[Dict[str, Any]]:
        """Obtiene las ultimas N generaciones."""
        data = self.generations
        if gen_type_filter:
            data = [g for g in data if g.get("gen_type") == gen_type_filter]
        return data[-n:]

    # ── TELEMETRY ──────────────────────────────────────────────────

    def save_telemetry(self, module: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Guarda entrada de telemetria."""
        entry = TelemetryEntry(module=module, data=data)
        entry_dict = entry.to_dict()
        self.telemetry.append(entry_dict)
        self._append_jsonl(TELEMETRY_DIR / "telemetry.jsonl", entry_dict)
        return {"status": "saved", "entry_id": entry.entry_id}

    def get_telemetry(self, module: str = None, n: int = 100) -> List[Dict[str, Any]]:
        """Obtiene telemetria."""
        data = self.telemetry
        if module:
            data = [t for t in data if t.get("module") == module]
        return data[-n:]

    # ── TRAINING EXPORT ────────────────────────────────────────────

    def export_for_training(self, output_path: str = None,
                             max_examples: int = 5000) -> Dict[str, Any]:
        """Exporta datos en formato JSONL para Unsloth fine-tuning."""
        if output_path is None:
            output_path = str(TRAINING_EXPORT_DIR / f"training_{int(time.time())}.jsonl")

        exported = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for conv in self.conversations[-max_examples:]:
                training_example = {
                    "instruction": conv.get("user_message", ""),
                    "input": "",
                    "output": conv.get("zio_response", ""),
                    "metadata": {
                        "intent": conv.get("intent", ""),
                        "session_id": conv.get("session_id", ""),
                        "timestamp": conv.get("timestamp", 0),
                    },
                }
                f.write(json.dumps(training_example, ensure_ascii=False) + "\n")
                exported += 1

        return {
            "status": "exported",
            "output_path": output_path,
            "examples_exported": exported,
            "total_conversations": len(self.conversations),
        }

    def export_generations_for_training(self, output_path: str = None,
                                         max_examples: int = 5000) -> Dict[str, Any]:
        """Exporta generaciones para training multimodal."""
        if output_path is None:
            output_path = str(TRAINING_EXPORT_DIR / f"gen_training_{int(time.time())}.jsonl")

        exported = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for gen in self.generations[-max_examples:]:
                training_example = {
                    "instruction": f"Generate {gen.get('gen_type', 'content')}",
                    "input": gen.get("prompt", ""),
                    "output": json.dumps({
                        "type": gen.get("gen_type"),
                        "path": gen.get("output_path"),
                        "parameters": gen.get("parameters", {}),
                    }),
                }
                f.write(json.dumps(training_example, ensure_ascii=False) + "\n")
                exported += 1

        return {
            "status": "exported",
            "output_path": output_path,
            "examples_exported": exported,
            "total_generations": len(self.generations),
        }

    # ── CLEANUP ────────────────────────────────────────────────────

    def cleanup_old_data(self, days: int = RETENTION_DAYS) -> Dict[str, Any]:
        """Elimina datos antiguos para liberar espacio."""
        cutoff = time.time() - (days * 86400)

        before_conv = len(self.conversations)
        self.conversations = [c for c in self.conversations if c.get("timestamp", 0) > cutoff]
        removed_conv = before_conv - len(self.conversations)

        before_gen = len(self.generations)
        self.generations = [g for g in self.generations if g.get("timestamp", 0) > cutoff]
        removed_gen = before_gen - len(self.generations)

        before_tel = len(self.telemetry)
        self.telemetry = [t for t in self.telemetry if t.get("timestamp", 0) > cutoff]
        removed_tel = before_tel - len(self.telemetry)

        return {
            "conversations_removed": removed_conv,
            "generations_removed": removed_gen,
            "telemetry_removed": removed_tel,
            "cutoff_days": days,
        }

    # ── STATS ──────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        """Estadisticas del sistema de retencion."""
        conv_size = os.path.getsize(CONVERSATIONS_DIR / "conversations.jsonl") if (CONVERSATIONS_DIR / "conversations.jsonl").exists() else 0
        gen_size = os.path.getsize(GENERATIONS_DIR / "generations.jsonl") if (GENERATIONS_DIR / "generations.jsonl").exists() else 0
        tel_size = os.path.getsize(TELEMETRY_DIR / "telemetry.jsonl") if (TELEMETRY_DIR / "telemetry.jsonl").exists() else 0

        intents = {}
        for c in self.conversations:
            intent = c.get("intent", "unknown")
            intents[intent] = intents.get(intent, 0) + 1

        gen_types = {}
        for g in self.generations:
            gt = g.get("gen_type", "unknown")
            gen_types[gt] = gen_types.get(gt, 0) + 1

        return {
            "conversations": len(self.conversations),
            "generations": len(self.generations),
            "telemetry_entries": len(self.telemetry),
            "storage_bytes": conv_size + gen_size + tel_size,
            "storage_mb": round((conv_size + gen_size + tel_size) / 1024 / 1024, 2),
            "intent_distribution": intents,
            "generation_type_distribution": gen_types,
            "retention_days": RETENTION_DAYS,
        }


# Singleton
data_retention = DataRetention()

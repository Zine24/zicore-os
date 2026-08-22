"""
ZICORE RAG Training System
Captures Q&A pairs, generates embeddings via Tailscale .68,
provides context retrieval for improved responses.
"""
import json
import sqlite3
import os
import time
import urllib.request
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

DATA_DIR = Path(__file__).parent.parent / "data" / "knowledge"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RAG_DB = DATA_DIR / "rag_training.db"
EMBEDDING_URL = os.environ.get("ZICORE_EMBEDDING_URL", "http://100.94.98.59:11434")
EMBEDDING_MODEL = "granite-embedding:latest"
EMBEDDING_DIM = 384


class RAGTrainingSystem:
    def __init__(self):
        self.db = sqlite3.connect(str(RAG_DB), check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self._init_tables()

    def _init_tables(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS qa_pairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                user_message TEXT NOT NULL,
                zio_response TEXT NOT NULL,
                intent TEXT DEFAULT '',
                model TEXT DEFAULT '',
                quality_score REAL DEFAULT 0.5,
                embedding BLOB,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                used_in_training INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_qa_session ON qa_pairs(session_id);
            CREATE INDEX IF NOT EXISTS idx_qa_intent ON qa_pairs(intent);
            CREATE INDEX IF NOT EXISTS idx_qa_quality ON qa_pairs(quality_score);

            CREATE TABLE IF NOT EXISTS training_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_type TEXT NOT NULL,
                qa_count INTEGER,
                model_name TEXT,
                status TEXT DEFAULT 'pending',
                metrics TEXT DEFAULT '{}',
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS qa_fts USING fts5(
                user_message, zio_response, intent,
                content='qa_pairs',
                content_rowid='id'
            );
        """)
        self.db.commit()

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from .68 granite-embedding via Tailscale"""
        try:
            payload = json.dumps({
                "model": EMBEDDING_MODEL,
                "input": text
            }).encode()
            req = urllib.request.Request(
                f"{EMBEDDING_URL}/api/embed",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                embeddings = data.get("embeddings", [])
                if embeddings:
                    return embeddings[0]
        except Exception as e:
            print(f"[RAG] Embedding error: {e}")
        return None

    def get_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Get embeddings for multiple texts"""
        try:
            payload = json.dumps({
                "model": EMBEDDING_MODEL,
                "input": texts
            }).encode()
            req = urllib.request.Request(
                f"{EMBEDDING_URL}/api/embed",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data.get("embeddings", [None] * len(texts))
        except Exception as e:
            print(f"[RAG] Batch embedding error: {e}")
            return [None] * len(texts)

    def save_qa(self, user_message: str, zio_response: str,
                session_id: str = "web", intent: str = "",
                model: str = "", quality_score: float = 0.5) -> int:
        """Save a Q&A pair with embedding"""
        embedding = self.get_embedding(user_message)
        embedding_blob = json.dumps(embedding).encode() if embedding else None

        cursor = self.db.execute("""
            INSERT INTO qa_pairs (session_id, user_message, zio_response, intent, model, quality_score, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, user_message, zio_response, intent, model, quality_score, embedding_blob))
        self.db.commit()

        # Also add to FTS for text search
        rowid = cursor.lastrowid
        self.db.execute("""
            INSERT INTO qa_fts (rowid, user_message, zio_response, intent)
            VALUES (?, ?, ?, ?)
        """, (rowid, user_message, zio_response, intent))
        self.db.commit()

        return rowid

    def search_similar(self, query: str, limit: int = 5, min_score: float = 0.0) -> List[Dict]:
        """Find similar Q&A pairs using embedding similarity"""
        query_embedding = self.get_embedding(query)
        if not query_embedding:
            # Fallback to FTS text search
            return self._fts_search(query, limit)

        rows = self.db.execute("""
            SELECT id, session_id, user_message, zio_response, intent,
                   model, quality_score, embedding, created_at
            FROM qa_pairs
            WHERE embedding IS NOT NULL
        """).fetchall()

        results = []
        for row in rows:
            try:
                stored_embedding = json.loads(row[7])
                similarity = self._cosine_similarity(query_embedding, stored_embedding)
                if similarity >= min_score:
                    results.append({
                        "id": row[0],
                        "session_id": row[1],
                        "user_message": row[2],
                        "zio_response": row[3],
                        "intent": row[4],
                        "model": row[5],
                        "quality_score": row[6],
                        "similarity": similarity,
                        "created_at": row[8]
                    })
            except (json.JSONDecodeError, IndexError):
                continue

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]

    def _fts_search(self, query: str, limit: int = 5) -> List[Dict]:
        """Fallback text search using FTS5"""
        try:
            rows = self.db.execute("""
                SELECT qa_pairs.id, session_id, user_message, zio_response,
                       intent, model, quality_score, created_at
                FROM qa_fts
                JOIN qa_pairs ON qa_fts.rowid = qa_pairs.id
                WHERE qa_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (query, limit)).fetchall()

            return [{
                "id": r[0], "session_id": r[1], "user_message": r[2],
                "zio_response": r[3], "intent": r[4], "model": r[5],
                "quality_score": r[6], "similarity": 0.5, "created_at": r[7]
            } for r in rows]
        except Exception:
            return []

    def get_rag_context(self, query: str, max_chars: int = 2000) -> str:
        """Get relevant context for a query from stored Q&A pairs"""
        similar = self.search_similar(query, limit=5, min_score=0.3)
        if not similar:
            return ""

        context_parts = []
        total = 0
        for item in similar:
            entry = f"Q: {item['user_message']}\nA: {item['zio_response']}"
            if total + len(entry) > max_chars:
                break
            context_parts.append(entry)
            total += len(entry)

        if context_parts:
            return "Relevant past conversations:\n" + "\n---\n".join(context_parts)
        return ""

    def get_training_dataset(self, min_quality: float = 0.6,
                             unused_only: bool = True) -> List[Dict]:
        """Get Q&A pairs suitable for training"""
        query = """
            SELECT id, session_id, user_message, zio_response, intent, model, quality_score
            FROM qa_pairs
            WHERE quality_score >= ?
        """
        params = [min_quality]
        if unused_only:
            query += " AND used_in_training = 0"
        query += " ORDER BY quality_score DESC, created_at DESC"

        rows = self.db.execute(query, params).fetchall()
        return [{
            "id": r[0], "session_id": r[1], "user_message": r[2],
            "zio_response": r[3], "intent": r[4], "model": r[5],
            "quality_score": r[6]
        } for r in rows]

    def export_training_jsonl(self, output_path: str = None, min_quality: float = 0.6) -> str:
        """Export training data as JSONL for fine-tuning"""
        if not output_path:
            output_path = str(DATA_DIR / "training_dataset.jsonl")

        dataset = self.get_training_dataset(min_quality=min_quality)
        with open(output_path, "w", encoding="utf-8") as f:
            for item in dataset:
                # Format for instruction fine-tuning
                training_entry = {
                    "instruction": item["user_message"],
                    "response": item["zio_response"],
                    "intent": item.get("intent", ""),
                    "quality": item["quality_score"]
                }
                f.write(json.dumps(training_entry, ensure_ascii=False) + "\n")

        # Mark as used
        ids = [item["id"] for item in dataset]
        if ids:
            placeholders = ",".join("?" * len(ids))
            self.db.execute(f"""
                UPDATE qa_pairs SET used_in_training = 1
                WHERE id IN ({placeholders})
            """, ids)
            self.db.commit()

        return output_path

    def get_stats(self) -> Dict:
        """Get RAG system statistics"""
        total = self.db.execute("SELECT COUNT(*) FROM qa_pairs").fetchone()[0]
        with_embedding = self.db.execute("SELECT COUNT(*) FROM qa_pairs WHERE embedding IS NOT NULL").fetchone()[0]
        high_quality = self.db.execute("SELECT COUNT(*) FROM qa_pairs WHERE quality_score >= 0.7").fetchone()[0]
        used_in_training = self.db.execute("SELECT COUNT(*) FROM qa_pairs WHERE used_in_training = 1").fetchone()[0]
        intents = self.db.execute("SELECT intent, COUNT(*) FROM qa_pairs WHERE intent != '' GROUP BY intent ORDER BY COUNT(*) DESC LIMIT 10").fetchall()

        return {
            "total_qa": total,
            "with_embeddings": with_embedding,
            "high_quality": high_quality,
            "used_in_training": used_in_training,
            "ready_for_training": high_quality - used_in_training,
            "top_intents": {i[0]: i[1] for i in intents},
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dim": EMBEDDING_DIM
        }

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


# Singleton
rag_system = None

def get_rag_system():
    global rag_system
    if rag_system is None:
        rag_system = RAGTrainingSystem()
    return rag_system

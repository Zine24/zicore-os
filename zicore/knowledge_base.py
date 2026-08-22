"""
ZICORE Knowledge Base - Chat persistence + Document storage for ZIO agent
All conversations become knowledge. Documents/texts enhance responses.
"""
import json
import hashlib
import os
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

DATA_DIR = Path(__file__).parent.parent / "data" / "knowledge"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CONVERSATIONS_FILE = DATA_DIR / "conversations.jsonl"
DOCUMENTS_DIR = DATA_DIR / "documents"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
INDEX_FILE = DATA_DIR / "document_index.json"


class KnowledgeBase:
    def __init__(self):
        self.conversations: List[Dict] = []
        self.documents: Dict[str, Dict] = {}
        self._load_conversations()
        self._load_documents()

    def _load_conversations(self):
        if CONVERSATIONS_FILE.exists():
            try:
                with open(CONVERSATIONS_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self.conversations.append(json.loads(line))
            except Exception:
                pass

    def _save_conversation(self, entry: Dict):
        try:
            with open(CONVERSATIONS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[KB] Error saving conversation: {e}")

    def _load_documents(self):
        if INDEX_FILE.exists():
            try:
                with open(INDEX_FILE, "r", encoding="utf-8") as f:
                    self.documents = json.load(f)
            except Exception:
                pass

    def _save_documents_index(self):
        try:
            with open(INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(self.documents, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[KB] Error saving document index: {e}")

    def add_message(self, role: str, content: str, session_id: str = "default",
                    intent: str = "", metadata: Dict = None) -> str:
        entry_id = hashlib.sha256(
            f"{session_id}:{datetime.now().isoformat()}:{content[:100]}".encode()
        ).hexdigest()[:16]

        entry = {
            "id": entry_id,
            "role": role,
            "content": content,
            "session_id": session_id,
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.conversations.append(entry)
        self._save_conversation(entry)
        return entry_id

    def search_conversations(self, query: str, limit: int = 10) -> List[Dict]:
        query_lower = query.lower()
        results = []
        for conv in reversed(self.conversations):
            content = conv.get("content", "").lower()
            if query_lower in content:
                results.append(conv)
                if len(results) >= limit:
                    break
        return results

    def get_recent(self, limit: int = 20, session_id: str = None) -> List[Dict]:
        filtered = self.conversations
        if session_id:
            filtered = [c for c in filtered if c.get("session_id") == session_id]
        return filtered[-limit:]

    def add_document(self, name: str, content: str, doc_type: str = "text",
                     metadata: Dict = None) -> str:
        doc_id = hashlib.sha256(name.encode()).hexdigest()[:12]

        doc_path = DOCUMENTS_DIR / f"{doc_id}.txt"
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(content)

        self.documents[doc_id] = {
            "id": doc_id,
            "name": name,
            "type": doc_type,
            "path": str(doc_path),
            "length": len(content),
            "words": len(content.split()),
            "added": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self._save_documents_index()
        return doc_id

    def search_documents(self, query: str, limit: int = 5) -> List[Dict]:
        query_lower = query.lower()
        results = []
        for doc_id, doc in self.documents.items():
            try:
                with open(doc["path"], "r", encoding="utf-8") as f:
                    content = f.read()
                if query_lower in content.lower():
                    idx = content.lower().find(query_lower)
                    snippet = content[max(0, idx - 100):idx + 200]
                    results.append({
                        "id": doc_id,
                        "name": doc["name"],
                        "snippet": snippet,
                        "score": content.lower().count(query_lower),
                    })
            except Exception:
                pass
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def get_document(self, doc_id: str) -> Optional[Dict]:
        doc = self.documents.get(doc_id)
        if doc and os.path.exists(doc["path"]):
            with open(doc["path"], "r", encoding="utf-8") as f:
                doc["content"] = f.read()
            return doc
        return None

    def delete_document(self, doc_id: str) -> bool:
        doc = self.documents.pop(doc_id, None)
        if doc:
            try:
                os.remove(doc["path"])
            except Exception:
                pass
            self._save_documents_index()
            return True
        return False

    def get_context_for_query(self, query: str, max_tokens: int = 2000) -> str:
        context_parts = []

        doc_results = self.search_documents(query, limit=3)
        if doc_results:
            context_parts.append("=== DOCUMENT KNOWLEDGE ===")
            for dr in doc_results:
                context_parts.append(f"[{dr['name']}]: {dr['snippet']}")

        conv_results = self.search_conversations(query, limit=5)
        if conv_results:
            context_parts.append("=== PAST CONVERSATIONS ===")
            for cr in conv_results:
                role = cr.get("role", "unknown")
                content = cr.get("content", "")[:200]
                context_parts.append(f"[{role}]: {content}")

        context = "\n\n".join(context_parts)
        if len(context) > max_tokens:
            context = context[:max_tokens]
        return context

    def get_stats(self) -> Dict:
        total_words = sum(d.get("words", 0) for d in self.documents.values())
        return {
            "conversations": len(self.conversations),
            "documents": len(self.documents),
            "total_words": total_words,
            "total_conversation_words": sum(
                len(c.get("content", "").split()) for c in self.conversations
            ),
        }


knowledge_base = KnowledgeBase()

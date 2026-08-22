"""
ZICORE ZIO Machine Learning Module
Provides ML capabilities: classification, anomaly detection, pattern recognition,
sentiment analysis, clustering, and predictive analytics.
Signed by ZineMotion
"""
from __future__ import annotations
import json
import math
import random
import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


class ZIOML:
    """ZIO Machine Learning engine - lightweight, no external dependencies."""

    def __init__(self):
        self.models_dir = Path(__file__).parent.parent / "data" / "ml_models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._models = {}

    # --- TEXT CLASSIFICATION ---

    def train_text_classifier(self, training_data: list[dict], model_name: str = "default") -> dict:
        """
        Train a Naive Bayes text classifier.
        training_data: [{"text": "...", "label": "..."}]
        """
        vocab = set()
        class_counts = Counter()
        word_counts = defaultdict(Counter)

        for item in training_data:
            label = item["label"]
            words = self._tokenize(item["text"])
            class_counts[label] += 1
            for word in words:
                word_counts[label][word] += 1
                vocab.add(word)

        total_docs = sum(class_counts.values())
        class_priors = {c: count / total_docs for c, count in class_counts.items()}

        model = {
            "type": "naive_bayes",
            "class_priors": class_priors,
            "class_counts": dict(class_counts),
            "word_counts": {c: dict(wc) for c, wc in word_counts.items()},
            "vocab_size": len(vocab),
            "total_docs": total_docs,
        }
        self._models[model_name] = model
        self._save_model(model_name, model)
        return {"status": "ok", "model": model_name, "classes": list(class_counts.keys()), "vocab_size": len(vocab)}

    def predict_text(self, text: str, model_name: str = "default") -> dict:
        """Predict class for text using trained classifier."""
        model = self._models.get(model_name) or self._load_model(model_name)
        if not model:
            return {"error": f"Model '{model_name}' not found"}

        words = self._tokenize(text)
        scores = {}

        for label, prior in model["class_priors"].items():
            log_prob = math.log(prior)
            wc = model["word_counts"].get(label, {})
            total_words_in_class = sum(wc.values()) or 1
            for word in words:
                word_count = wc.get(word, 0)
                log_prob += math.log((word_count + 1) / (total_words_in_class + model["vocab_size"]))
            scores[label] = log_prob

        best = max(scores, key=scores.get)
        confidence = math.exp(scores[best]) / sum(math.exp(v) for v in scores.values())
        return {"prediction": best, "confidence": round(confidence, 4), "scores": scores}

    # --- ANOMALY DETECTION ---

    def detect_anomalies(self, data: list[float], threshold: float = 2.0) -> dict:
        """Detect anomalies using Z-score method."""
        if len(data) < 3:
            return {"anomalies": [], "stats": {}}

        mean = sum(data) / len(data)
        variance = sum((x - mean) ** 2 for x in data) / len(data)
        std = math.sqrt(variance) if variance > 0 else 1

        anomalies = []
        for i, x in enumerate(data):
            z_score = abs(x - mean) / std
            if z_score > threshold:
                anomalies.append({"index": i, "value": x, "z_score": round(z_score, 4)})

        return {
            "anomalies": anomalies,
            "stats": {"mean": round(mean, 4), "std": round(std, 4), "count": len(data)},
            "threshold": threshold,
        }

    # --- CLUSTERING (K-Means) ---

    def kmeans(self, data: list[list[float]], k: int = 3, iterations: int = 50) -> dict:
        """Simple K-Means clustering."""
        if not data or k >= len(data):
            return {"error": "Invalid data or k"}

        # Initialize centroids randomly
        centroids = random.sample(data, k)

        for _ in range(iterations):
            # Assign points to nearest centroid
            clusters = [[] for _ in range(k)]
            for point in data:
                distances = [self._euclidean(point, c) for c in centroids]
                nearest = distances.index(min(distances))
                clusters[nearest].append(point)

            # Update centroids
            new_centroids = []
            for cluster in clusters:
                if cluster:
                    new_centroids.append([sum(col) / len(cluster) for col in zip(*cluster)])
                else:
                    new_centroids.append(random.choice(data))

            if new_centroids == centroids:
                break
            centroids = new_centroids

        # Calculate inertia
        inertia = 0
        assignments = []
        for point in data:
            distances = [self._euclidean(point, c) for c in centroids]
            nearest = distances.index(min(distances))
            inertia += distances[nearest] ** 2
            assignments.append(nearest)

        return {
            "centroids": [[round(c, 4) for c in cent] for cent in centroids],
            "assignments": assignments,
            "inertia": round(inertia, 4),
            "k": k,
            "n_points": len(data),
        }

    # --- SIMILARITY ---

    def cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def jaccard_similarity(self, set_a: set, set_b: set) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set_a and not set_b:
            return 1.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    # --- PATTERN RECOGNITION ---

    def find_patterns(self, sequence: list, min_length: int = 2, max_occurrences: int = 1) -> list:
        """Find repeating patterns in a sequence."""
        patterns = []
        for length in range(min_length, len(sequence) // 2 + 1):
            seen = {}
            for i in range(len(sequence) - length + 1):
                sub = tuple(sequence[i:i + length])
                if sub in seen:
                    seen[sub] += 1
                else:
                    seen[sub] = 1
            for pattern, count in seen.items():
                if count >= 2:
                    patterns.append({
                        "pattern": list(pattern),
                        "length": length,
                        "occurrences": count,
                    })
        return sorted(patterns, key=lambda x: (-x["occurrences"], -x["length"]))

    # --- SENTIMENT ANALYSIS ---

    def analyze_sentiment(self, text: str) -> dict:
        """Simple rule-based sentiment analysis."""
        positive_words = {
            "good", "great", "excellent", "amazing", "awesome", "love", "like",
            "happy", "best", "fantastic", "wonderful", "perfect", "beautiful",
            "brilliant", "superb", "outstanding", "nice", "cool", "thanks",
            "yes", "right", "agree", "correct", "true", "positive", "win",
        }
        negative_words = {
            "bad", "terrible", "horrible", "hate", "worst", "awful", "ugly",
            "angry", "sad", "wrong", "error", "fail", "broken", "crash",
            "bug", "issue", "problem", "danger", "risk", "loss", "negative",
            "no", "not", "never", "don't", "can't", "won't", "impossible",
        }

        words = self._tokenize(text.lower())
        pos_count = sum(1 for w in words if w in positive_words)
        neg_count = sum(1 for w in words if w in negative_words)
        total = pos_count + neg_count

        if total == 0:
            return {"sentiment": "neutral", "score": 0.0, "confidence": 0.5}

        score = (pos_count - neg_count) / total
        if score > 0.1:
            sentiment = "positive"
        elif score < -0.1:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "score": round(score, 4),
            "confidence": round(total / len(words), 4) if words else 0.5,
            "positive_words": pos_count,
            "negative_words": neg_count,
        }

    # --- PREDICTIVE ANALYTICS ---

    def linear_regression(self, x_data: list[float], y_data: list[float]) -> dict:
        """Simple linear regression."""
        n = len(x_data)
        if n < 2:
            return {"error": "Need at least 2 data points"}

        sum_x = sum(x_data)
        sum_y = sum(y_data)
        sum_xy = sum(x * y for x, y in zip(x_data, y_data))
        sum_x2 = sum(x * x for x in x_data)

        denom = n * sum_x2 - sum_x ** 2
        if denom == 0:
            return {"error": "Cannot compute (zero denominator)"}

        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n

        # R-squared
        mean_y = sum_y / n
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in zip(x_data, y_data))
        ss_tot = sum((y - mean_y) ** 2 for y in y_data)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        return {
            "slope": round(slope, 6),
            "intercept": round(intercept, 6),
            "r_squared": round(r_squared, 6),
            "predict": lambda x: round(slope * x + intercept, 4),
        }

    def moving_average(self, data: list[float], window: int = 5) -> list[float]:
        """Calculate moving average."""
        result = []
        for i in range(len(data)):
            start = max(0, i - window + 1)
            result.append(round(sum(data[start:i + 1]) / (i - start + 1), 4))
        return result

    # --- EMBEDDING / VECTOR ---

    def text_to_vector(self, text: str, vocab: list[str] = None) -> list[float]:
        """Convert text to TF vector."""
        words = self._tokenize(text.lower())
        if not vocab:
            vocab = sorted(set(words))
        counts = Counter(words)
        return [counts.get(w, 0) for w in vocab]

    def hash_embedding(self, text: str, dim: int = 64) -> list[float]:
        """Generate a deterministic hash-based embedding."""
        h = hashlib.sha256(text.encode()).digest()
        vec = []
        for i in range(0, min(len(h), dim), 1):
            vec.append(h[i] / 255.0)
        while len(vec) < dim:
            vec.append(0.0)
        return vec

    # --- HELPERS ---

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization."""
        return re.findall(r'\b\w+\b', text.lower())

    def _euclidean(self, a: list[float], b: list[float]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def _save_model(self, name: str, model: dict):
        path = self.models_dir / f"{name}.json"
        try:
            with open(path, "w") as f:
                json.dump(model, f, indent=2, default=str)
        except Exception:
            pass

    def _load_model(self, name: str) -> dict | None:
        path = self.models_dir / f"{name}.json"
        try:
            with open(path) as f:
                model = json.load(f)
            self._models[name] = model
            return model
        except Exception:
            return None

    def list_models(self) -> list:
        models = []
        for f in self.models_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)
                models.append({
                    "name": f.stem,
                    "type": data.get("type", "unknown"),
                    "classes": list(data.get("class_counts", {}).keys()),
                })
            except Exception:
                pass
        return models

    def get_info(self) -> dict:
        return {
            "engine": "ZIO-ML",
            "version": "1.0.0",
            "capabilities": [
                "text_classification",
                "anomaly_detection",
                "clustering",
                "similarity",
                "pattern_recognition",
                "sentiment_analysis",
                "linear_regression",
                "moving_average",
                "text_vectorization",
                "hash_embedding",
            ],
            "models": self.list_models(),
        }

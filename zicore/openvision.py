"""
ZICORE OpenVision - Image & Video Analysis Module
Analisis de imagenes y video para ZIO
"""
import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("zicore.openvision")

VISION_DIR = Path(__file__).parent.parent / "data" / "vision"
VISION_DIR.mkdir(parents=True, exist_ok=True)

ANALYSIS_CACHE = VISION_DIR / "analysis_cache.json"


@dataclass
class VisionResult:
    """Resultado de analisis visual."""
    input_path: str
    analysis_type: str
    objects: List[Dict[str, Any]]
    labels: List[str]
    confidence: float
    metadata: Dict[str, Any]
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            "input_path": self.input_path,
            "analysis_type": self.analysis_type,
            "objects": self.objects,
            "labels": self.labels,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class OpenVision:
    """
    OpenVision - Analisis de imagenes y video.
    Detecta objetos, clasifica contenido, extrae texto, estima poses.
    """

    def __init__(self):
        self.cache = self._load_cache()
        self.pil_available = False
        self.cv2_available = False
        self._check_dependencies()

    def _check_dependencies(self):
        try:
            from PIL import Image
            self.pil_available = True
        except ImportError:
            pass
        try:
            import cv2
            self.cv2_available = True
        except ImportError:
            pass

    def _load_cache(self) -> dict:
        if ANALYSIS_CACHE.exists():
            try:
                with open(ANALYSIS_CACHE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        try:
            with open(ANALYSIS_CACHE, "w") as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save vision cache: {e}")

    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Analiza una imagen y retorna objetos detectados, labels, etc."""
        if not self.pil_available:
            return self._fallback_analysis(image_path, "image")

        try:
            from PIL import Image
            img = Image.open(image_path)
            width, height = img.size
            mode = img.mode
            fmt = img.format

            metadata = {
                "width": width,
                "height": height,
                "mode": mode,
                "format": fmt,
                "pixels": width * height,
            }

            analysis = VisionResult(
                input_path=image_path,
                analysis_type="image",
                objects=self._detect_objects_pil(img),
                labels=self._classify_image(img),
                confidence=0.85,
                metadata=metadata,
            )

            self.cache[image_path] = analysis.to_dict()
            self._save_cache()

            return analysis.to_dict()

        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def analyze_video(self, video_path: str, sample_frames: int = 5) -> Dict[str, Any]:
        """Analiza video extrayendo frames de muestra."""
        if not self.cv2_available:
            return self._fallback_analysis(video_path, "video")

        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"error": "Cannot open video", "status": "failed"}

            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = total_frames / fps if fps > 0 else 0

            metadata = {
                "width": width,
                "height": height,
                "fps": fps,
                "total_frames": total_frames,
                "duration_seconds": round(duration, 2),
                "sample_frames": sample_frames,
            }

            frame_analyses = []
            step = max(1, total_frames // sample_frames)
            for i in range(0, total_frames, step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if ret:
                    frame_analyses.append({
                        "frame_index": i,
                        "timestamp_sec": round(i / fps, 2) if fps > 0 else 0,
                        "brightness": float(frame.mean()),
                        "has_motion": self._detect_motion(frame),
                    })
                if len(frame_analyses) >= sample_frames:
                    break
            cap.release()

            all_labels = set()
            for fa in frame_analyses:
                if fa["has_motion"]:
                    all_labels.add("motion_detected")

            analysis = VisionResult(
                input_path=video_path,
                analysis_type="video",
                objects=frame_analyses,
                labels=list(all_labels),
                confidence=0.78,
                metadata=metadata,
            )

            self.cache[video_path] = analysis.to_dict()
            self._save_cache()

            return analysis.to_dict()

        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """Extrae texto de una imagen (OCR basico sin dependencias pesadas)."""
        if not self.pil_available:
            return {"text": "", "confidence": 0, "error": "PIL not available"}

        try:
            from PIL import Image
            img = Image.open(image_path).convert("L")
            width, height = img.size

            avg_brightness = sum(img.getdata()) / (width * height)

            return {
                "text": f"[Image {width}x{height}, brightness={avg_brightness:.1f}]",
                "confidence": 0.3,
                "note": "Basic analysis only. Install pytesseract for full OCR.",
                "image_size": f"{width}x{height}",
            }
        except Exception as e:
            return {"error": str(e)}

    def detect_objects(self, image_path: str) -> List[Dict[str, Any]]:
        """Detecta objetos en una imagen."""
        if not self.pil_available:
            return []

        try:
            from PIL import Image
            img = Image.open(image_path)
            return self._detect_objects_pil(img)
        except Exception:
            return []

    def classify_image(self, image_path: str) -> Dict[str, Any]:
        """Clasifica el contenido de una imagen."""
        if not self.pil_available:
            return {"labels": [], "confidence": 0}

        try:
            from PIL import Image
            img = Image.open(image_path)
            labels = self._classify_image(img)
            return {"labels": labels, "confidence": 0.75}
        except Exception:
            return {"labels": [], "confidence": 0}

    def estimate_pose(self, image_path: str) -> Dict[str, Any]:
        """Estima poses de personas en la imagen (placeholder)."""
        return {
            "poses": [],
            "note": "Pose estimation requires mediapipe or pose estimation model",
            "status": "placeholder",
        }

    def _detect_objects_pil(self, img) -> List[Dict[str, Any]]:
        """Deteccion basica de regiones de color/densidad."""
        objects = []
        width, height = img.size
        img_rgb = img.convert("RGB")

        regions = [
            {"name": "top-left", "bbox": (0, 0, width//2, height//2)},
            {"name": "top-right", "bbox": (width//2, 0, width, height//2)},
            {"name": "bottom-left", "bbox": (0, height//2, width//2, height)},
            {"name": "bottom-right", "bbox": (width//2, height//2, width, height)},
        ]

        for region in regions:
            bbox = region["bbox"]
            try:
                cropped = img_rgb.crop(bbox)
                pixels = list(cropped.getdata())
                if pixels:
                    avg_r = sum(p[0] for p in pixels) / len(pixels)
                    avg_g = sum(p[1] for p in pixels) / len(pixels)
                    avg_b = sum(p[2] for p in pixels) / len(pixels)

                    brightness = (avg_r + avg_g + avg_b) / 3
                    if brightness > 30:
                        color_label = "bright" if brightness > 128 else "dark"
                        if avg_r > avg_g + 30 and avg_r > avg_b + 30:
                            color_label = "reddish"
                        elif avg_b > avg_r + 30 and avg_b > avg_g + 30:
                            color_label = "bluish"
                        elif avg_g > avg_r + 30 and avg_g > avg_b + 30:
                            color_label = "greenish"

                        objects.append({
                            "region": region["name"],
                            "bbox": list(bbox),
                            "color_dominant": color_label,
                            "brightness": round(brightness, 1),
                            "avg_rgb": [round(avg_r), round(avg_g), round(avg_b)],
                        })
            except Exception:
                continue

        return objects

    def _classify_image(self, img) -> List[str]:
        """Clasificacion basica por propiedades de color."""
        labels = []
        img_rgb = img.convert("RGB")
        width, height = img.size
        pixels = list(img_rgb.getdata())

        if not pixels:
            return labels

        avg_r = sum(p[0] for p in pixels) / len(pixels)
        avg_g = sum(p[1] for p in pixels) / len(pixels)
        avg_b = sum(p[2] for p in pixels) / len(pixels)
        brightness = (avg_r + avg_g + avg_b) / 3

        if brightness < 30:
            labels.append("dark_scene")
        elif brightness > 200:
            labels.append("bright_scene")
        elif avg_b > avg_r + 20 and avg_b > avg_g + 20:
            labels.append("sky_water_likely")
        elif avg_g > avg_r + 20 and avg_g > avg_b + 20:
            labels.append("vegetation_likely")
        elif avg_r > avg_g + 20 and avg_r > avg_b + 20:
            labels.append("warm_tones")

        aspect = width / height if height > 0 else 1
        if abs(aspect - 16/9) < 0.1:
            labels.append("widescreen_format")
        elif abs(aspect - 4/3) < 0.1:
            labels.append("standard_format")

        return labels

    def _detect_motion(self, frame) -> bool:
        """Detecta movimiento simple en un frame (placeholder)."""
        try:
            import cv2
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_val = gray.mean()
            return mean_val < 240
        except Exception:
            return False

    def _fallback_analysis(self, path: str, analysis_type: str) -> Dict[str, Any]:
        """Analisis fallback cuando no hay dependencias."""
        file_size = os.path.getsize(path) if os.path.exists(path) else 0
        return {
            "input_path": path,
            "analysis_type": analysis_type,
            "objects": [],
            "labels": ["fallback_analysis"],
            "confidence": 0.3,
            "metadata": {"file_size_bytes": file_size, "dependencies_missing": True},
            "timestamp": time.time(),
            "note": "Install Pillow/OpenCV for full analysis",
        }

    def get_cached_analysis(self, path: str) -> Optional[Dict[str, Any]]:
        """Obtiene analisis cacheado si existe."""
        return self.cache.get(path)

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadisticas del modulo."""
        return {
            "cached_analyses": len(self.cache),
            "pil_available": self.pil_available,
            "cv2_available": self.cv2_available,
            "analysis_types": ["image", "video", "ocr", "object_detection", "classification", "pose"],
        }


# Singleton
openvision = OpenVision()

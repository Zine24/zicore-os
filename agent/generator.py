"""
ZICORE Unified Generation Engine
All generators in one file. Test each before adding next.
Command: generate <type> <prompt> [options]
"""
import os
import sys
import math
import json
import time
import struct
import wave
import random
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("zicore.generator")

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Pillow availability
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# numpy availability
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# trimesh availability
try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False


class ZICoreGenerator:
    """Unified generation engine for image, video, 3D, sound."""

    def __init__(self):
        self.output_dir = OUTPUT_DIR
        self.pil = PIL_AVAILABLE
        self.numpy = NUMPY_AVAILABLE
        self.tm_available = TRIMESH_AVAILABLE
        self.tm = trimesh if TRIMESH_AVAILABLE else None
        self._load_config()

    def _load_config(self):
        """Load provider config for API keys."""
        config_path = Path(__file__).parent.parent / "data" / "config" / "zio_config.json"
        self.config = {}
        if config_path.exists():
            try:
                with open(config_path) as f:
                    self.config = json.load(f)
            except Exception:
                pass

    def status(self) -> Dict[str, Any]:
        return {
            "image": self.pil,
            "video": self.pil and self.numpy,
            "3d": self.tm is not None or True,  # fallback always available
            "sound": True,  # pure python
            "output_dir": str(self.output_dir),
        }

    def _call_image_api(self, prompt: str, provider: str = None, params: dict = None) -> Dict[str, Any]:
        """Call external image generation API (DALL-E, Stability, etc.)."""
        import urllib.request
        import urllib.error

        providers = self.config.get("providers", {})
        zio_engine = self.config.get("zio_engine", {})
        active = provider or zio_engine.get("active_provider", "openai")

        provider_config = providers.get(active, {})
        if not provider_config.get("enabled", False):
            return {"error": f"Provider {active} not enabled", "status": "failed"}

        api_key = provider_config.get("api_key", "")
        if not api_key:
            return {"error": f"No API key for {active}", "status": "failed"}

        base_url = provider_config.get("base_url", "")

        if active == "openai":
            return self._call_openai_image(prompt, api_key, base_url, params or {})
        elif active == "stability":
            return self._call_stability_image(prompt, api_key, base_url, params or {})
        else:
            return {"error": f"Image generation not supported for {active}", "status": "failed"}

    def _call_openai_image(self, prompt: str, api_key: str, base_url: str, params: dict) -> Dict[str, Any]:
        """Call OpenAI DALL-E API."""
        import urllib.request
        import urllib.error

        url = (base_url or "https://api.openai.com/v1") + "/images/generations"
        data = json.dumps({
            "model": params.get("model", "dall-e-3"),
            "prompt": prompt,
            "n": 1,
            "size": params.get("size", "1024x1024"),
        }).encode()

        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        })

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                img_url = result["data"][0]["url"]
                img_data = urllib.request.urlopen(img_url).read()
                filename = f"img_openai_{int(time.time())}.png"
                save_path = str(self.output_dir / filename)
                with open(save_path, "wb") as f:
                    f.write(img_data)
                return {
                    "file": save_path,
                    "filename": filename,
                    "prompt": prompt,
                    "engine": "dall-e-3",
                    "status": "ok",
                }
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    def _call_stability_image(self, prompt: str, api_key: str, base_url: str, params: dict) -> Dict[str, Any]:
        """Call Stability AI API."""
        import urllib.request

        url = (base_url or "https://api.stability.ai") + "/v1/generation/stable-diffusion-xl/text-to-image"
        data = json.dumps({
            "text_prompts": [{"text": prompt}],
            "cfg_scale": 7,
            "height": params.get("height", 1024),
            "width": params.get("width", 1024),
        }).encode()

        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        })

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                import base64
                img_b64 = result["artifacts"][0]["base64"]
                img_data = base64.b64decode(img_b64)
                filename = f"img_stability_{int(time.time())}.png"
                save_path = str(self.output_dir / filename)
                with open(save_path, "wb") as f:
                    f.write(img_data)
                return {
                    "file": save_path,
                    "filename": filename,
                    "prompt": prompt,
                    "engine": "stability",
                    "status": "ok",
                }
        except Exception as e:
            return {"error": str(e), "status": "failed"}

    # ──────────────────────────────────────────────────────────────
    # IMAGE GENERATOR
    # ──────────────────────────────────────────────────────────────

    def generate_image(self, prompt: str, width: int = 1024, height: int = 768, provider: str = None) -> Dict[str, Any]:
        """Generate image from prompt. Tries API first, falls back to local."""
        t0 = time.time()

        api_result = self._call_image_api(prompt, provider)
        if api_result.get("status") == "ok":
            api_result["latency_ms"] = round((time.time() - t0) * 1000, 1)
            return api_result

        if not self.pil:
            return {"error": "Pillow not installed and API unavailable", "status": "failed"}

        prompt_lower = prompt.lower()

        img = Image.new("RGB", (width, height), (6, 6, 20))
        draw = ImageDraw.Draw(img)

        # Route to specific generator based on prompt
        if any(w in prompt_lower for w in ["rocket", "ship", "vehicle", "nave", "cohete", "falcon"]):
            self._img_rocket(draw, width, height)
        elif any(w in prompt_lower for w in ["orbit", "planet", "earth", "space", "orbita"]):
            self._img_orbit(draw, width, height)
        elif any(w in prompt_lower for w in ["star", "stars", "starfield", "constellation"]):
            self._img_starfield(draw, width, height)
        elif any(w in prompt_lower for w in ["blueprint", "schematic", "diagram", "engineering"]):
            self._img_blueprint(draw, width, height, prompt)
        elif any(w in prompt_lower for w in ["circuit", "pcb", "board", "electronic"]):
            self._img_circuit(draw, width, height)
        elif any(w in prompt_lower for w in ["mars", "moon", "saturn", "jupiter", "planet"]):
            self._img_planet(draw, width, height, prompt_lower)
        elif any(w in prompt_lower for w in ["drone", "uav", "quad"]):
            self._img_drone(draw, width, height)
        elif any(w in prompt_lower for w in ["station", "habitat", "base", "ISS"]):
            self._img_station(draw, width, height)
        elif any(w in prompt_lower for w in ["wave", "ocean", "water"]):
            self._img_wave(draw, width, height)
        elif any(w in prompt_lower for w in ["nebula", "galaxy", "cosmos"]):
            self._img_nebula(draw, width, height)
        else:
            self._img_aerospace_grid(draw, width, height)

        # Add watermark
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except Exception:
            font = ImageFont.load_default()
        draw.text((10, height - 25), f"ZICORE | {prompt[:50]}", fill=(0, 180, 255), font=font)

        filename = f"img_{prompt[:20].replace(' ', '_')}_{int(time.time())}.png"
        save_path = str(self.output_dir / filename)
        img.save(save_path, "PNG")

        elapsed = (time.time() - t0) * 1000
        return {
            "file": save_path,
            "filename": filename,
            "prompt": prompt,
            "width": width,
            "height": height,
            "engine": "pillow",
            "latency_ms": round(elapsed, 1),
            "status": "ok",
        }

    def _img_rocket(self, draw, w, h):
        cx, cy = w // 2, h // 2
        # Nose cone
        draw.polygon([(cx, cy - 200), (cx - 30, cy - 100), (cx + 30, cy - 100)], fill=(0, 200, 255))
        # Body
        draw.rectangle([cx - 30, cy - 100, cx + 30, cy + 120], fill=(0, 200, 255))
        # Fins
        draw.polygon([(cx - 30, cy + 80), (cx - 80, cy + 150), (cx - 30, cy + 120)], fill=(0, 150, 200))
        draw.polygon([(cx + 30, cy + 80), (cx + 80, cy + 150), (cx + 30, cy + 120)], fill=(0, 150, 200))
        # Flame
        draw.polygon([(cx - 25, cy + 120), (cx, cy + 220), (cx + 25, cy + 120)], fill=(255, 120, 0))
        draw.polygon([(cx - 15, cy + 140), (cx, cy + 200), (cx + 15, cy + 140)], fill=(255, 200, 50))
        # Window
        draw.ellipse([cx - 12, cy - 60, cx + 12, cy - 30], fill=(100, 220, 255))
        # Stars
        random.seed(42)
        for _ in range(300):
            x, y = random.randint(0, w), random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))

    def _img_orbit(self, draw, w, h):
        cx, cy = w // 2, h // 2
        # Stars
        random.seed(7)
        for _ in range(400):
            x, y = random.randint(0, w), random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))
        # Earth
        r = 80
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(30, 100, 200))
        draw.ellipse([cx - r + 25, cy - r + 15, cx + r - 15, cy + r - 25], fill=(40, 140, 220))
        draw.ellipse([cx - 30, cy - 40, cx + 10, cy - 10], fill=(50, 180, 80))
        # Orbits
        for orbit_r in [140, 200, 260]:
            draw.ellipse([cx - orbit_r, cy - orbit_r, cx + orbit_r, cy + orbit_r], outline=(0, 200, 255), width=1)
            angle = random.random() * 2 * math.pi
            sx = int(cx + orbit_r * math.cos(angle))
            sy = int(cy + orbit_r * math.sin(angle))
            draw.rectangle([sx - 4, sy - 2, sx + 4, sy + 2], fill=(255, 200, 0))

    def _img_starfield(self, draw, w, h):
        random.seed(42)
        for _ in range(600):
            x, y = random.randint(0, w), random.randint(0, h)
            b = random.randint(100, 255)
            draw.point((x, y), fill=(b, b, b))
            if random.random() > 0.92:
                draw.line([(x - 3, y), (x + 3, y)], fill=(b, b, b))
                draw.line([(x, y - 3), (x, y + 3)], fill=(b, b, b))

    def _img_blueprint(self, draw, w, h, prompt):
        draw.rectangle([20, 20, w - 20, h - 20], outline=(0, 100, 200), width=2)
        for i in range(20, w - 20, 40):
            draw.line([(i, 20), (i, h - 20)], fill=(0, 30, 60))
        for i in range(20, h - 20, 40):
            draw.line([(20, i), (w - 20, i)], fill=(0, 30, 60))
        cx, cy = w // 2, h // 2
        # Main shape
        draw.rectangle([cx - 120, cy - 60, cx + 120, cy + 60], outline=(0, 200, 255), width=2)
        # Dimensions
        draw.line([(cx - 120, cy - 80), (cx + 120, cy - 80)], fill=(255, 200, 0), width=1)
        draw.line([(cx - 140, cy - 60), (cx - 140, cy + 60)], fill=(255, 200, 0), width=1)
        # Labels
        try:
            font = ImageFont.truetype("arial.ttf", 12)
        except Exception:
            font = ImageFont.load_default()
        draw.text((cx - 50, cy + 70), "ZICORE AEROSPACE", fill=(0, 200, 255), font=font)
        draw.text((cx - 30, cy - 90), "240mm", fill=(255, 200, 0), font=font)

    def _img_circuit(self, draw, w, h):
        random.seed(42)
        for _ in range(60):
            x1 = random.randint(40, w - 40)
            y1 = random.randint(40, h - 40)
            x2 = x1 + random.choice([-80, -40, 0, 40, 80])
            y2 = y1 + random.choice([-40, 0, 40])
            draw.line([(x1, y1), (x2, y2)], fill=(0, 180, 80), width=2)
            draw.rectangle([x2 - 4, y2 - 4, x2 + 4, y2 + 4], fill=(0, 255, 100))
        # IC chip
        cx, cy = w // 2, h // 2
        draw.rectangle([cx - 30, cy - 20, cx + 30, cy + 20], fill=(20, 20, 20), outline=(0, 200, 100))
        draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=(0, 255, 100))

    def _img_planet(self, draw, w, h, prompt):
        cx, cy = w // 2, h // 2
        if "mars" in prompt:
            colors = [(180, 80, 40), (200, 100, 50), (160, 70, 30)]
        elif "moon" in prompt:
            colors = [(180, 180, 180), (160, 160, 160), (140, 140, 140)]
        elif "saturn" in prompt:
            colors = [(200, 180, 120), (180, 160, 100), (160, 140, 80)]
        else:
            colors = [(30, 100, 200), (40, 130, 220), (20, 80, 180)]

        r = 100
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=colors[0])
        draw.ellipse([cx - r + 20, cy - r + 15, cx + r - 30, cy + r - 20], fill=colors[1])

        if "saturn" in prompt:
            draw.ellipse([cx - r - 60, cy - 10, cx + r + 60, cy + 10], outline=colors[2], width=8)

        random.seed(42)
        for _ in range(300):
            x, y = random.randint(0, w), random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))

    def _img_drone(self, draw, w, h):
        cx, cy = w // 2, h // 2
        # Body
        draw.rectangle([cx - 30, cy - 15, cx + 30, cy + 15], fill=(60, 60, 80))
        # Arms
        for angle in [45, 135, 225, 315]:
            rad = math.radians(angle)
            ex = int(cx + 60 * math.cos(rad))
            ey = int(cy + 60 * math.sin(rad))
            draw.line([(cx, cy), (ex, ey)], fill=(80, 80, 100), width=4)
            draw.ellipse([ex - 20, ey - 20, ex + 20, ey + 20], outline=(0, 200, 255), width=2)
            draw.ellipse([ex - 8, ey - 8, ex + 8, ey + 8], fill=(0, 200, 255))
        # Camera
        draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(255, 50, 50))
        # Stars
        random.seed(42)
        for _ in range(200):
            x, y = random.randint(0, w), random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))

    def _img_station(self, draw, w, h):
        cx, cy = w // 2, h // 2
        # Central hub
        draw.ellipse([cx - 25, cy - 25, cx + 25, cy + 25], fill=(100, 100, 120))
        # Solar panels
        draw.rectangle([cx - 150, cy - 8, cx - 30, cy + 8], fill=(50, 80, 150))
        draw.rectangle([cx + 30, cy - 8, cx + 150, cy + 8], fill=(50, 80, 150))
        # Modules
        draw.rectangle([cx - 60, cy - 15, cx - 30, cy + 15], fill=(80, 80, 100))
        draw.rectangle([cx + 30, cy - 15, cx + 60, cy + 15], fill=(80, 80, 100))
        # Docking port
        draw.rectangle([cx - 8, cy + 25, cx + 8, cy + 50], fill=(120, 120, 140))
        # Stars
        random.seed(42)
        for _ in range(300):
            x, y = random.randint(0, w), random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))

    def _img_wave(self, draw, w, h):
        for y in range(h):
            for x in range(w):
                wave_val = math.sin(x * 0.02 + y * 0.01) * 0.5 + 0.5
                r = int(10 + wave_val * 30)
                g = int(50 + wave_val * 100)
                b = int(150 + wave_val * 100)
                draw.point((x, y), fill=(r, g, b))

    def _img_nebula(self, draw, w, h):
        random.seed(42)
        for _ in range(2000):
            x, y = random.randint(0, w), random.randint(0, h)
            r = random.randint(0, 255)
            g = random.randint(0, 100)
            b = random.randint(100, 255)
            a = random.randint(1, 5)
            draw.ellipse([x - a, y - a, x + a, y + a], fill=(r, g, b))
        # Bright stars
        for _ in range(20):
            x, y = random.randint(0, w), random.randint(0, h)
            draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(255, 255, 255))

    def _img_aerospace_grid(self, draw, w, h):
        for i in range(0, w, 30):
            draw.line([(i, 0), (i, h)], fill=(0, 30, 50))
        for i in range(0, h, 30):
            draw.line([(0, i), (w, i)], fill=(0, 30, 50))
        random.seed(42)
        for _ in range(200):
            x, y = random.randint(0, w), random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))

    # ──────────────────────────────────────────────────────────────
    # SOUND GENERATOR
    # ──────────────────────────────────────────────────────────────

    def generate_sound(self, prompt: str, duration: float = 3.0,
                       sample_rate: int = 44100) -> Dict[str, Any]:
        """Generate WAV sound from prompt."""
        t0 = time.time()
        prompt_lower = prompt.lower()

        if any(w in prompt_lower for w in ["alarm", "alert", "warning", "siren"]):
            samples = self._snd_alarm(duration, sample_rate)
        elif any(w in prompt_lower for w in ["engine", "thrust", "rocket", "roar"]):
            samples = self._snd_engine(duration, sample_rate)
        elif any(w in prompt_lower for w in ["beep", "sonar", "ping", "radar"]):
            samples = self._snd_beep(duration, sample_rate)
        elif any(w in prompt_lower for w in ["wind", "atmosphere", "air"]):
            samples = self._snd_wind(duration, sample_rate)
        elif any(w in prompt_lower for w in ["radio", "transmission", "static", "comms"]):
            samples = self._snd_radio(duration, sample_rate)
        elif any(w in prompt_lower for w in ["music", "melody", "theme"]):
            samples = self._snd_melody(duration, sample_rate)
        elif any(w in prompt_lower for w in ["heartbeat", "pulse", "vital"]):
            samples = self._snd_heartbeat(duration, sample_rate)
        elif any(w in prompt_lower for w in ["laser", "blaster", "weapon"]):
            samples = self._snd_laser(duration, sample_rate)
        else:
            samples = self._snd_tone(duration, sample_rate)

        filename = f"snd_{prompt[:20].replace(' ', '_')}_{int(time.time())}.wav"
        save_path = str(self.output_dir / filename)

        with wave.open(save_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            for s in samples:
                val = max(-32768, min(32767, int(s * 32767)))
                wf.writeframes(struct.pack('<h', val))

        elapsed = (time.time() - t0) * 1000
        return {
            "file": save_path,
            "filename": filename,
            "prompt": prompt,
            "duration": duration,
            "sample_rate": sample_rate,
            "samples": len(samples),
            "latency_ms": round(elapsed, 1),
            "status": "ok",
        }

    def _snd_alarm(self, dur, sr):
        samples = []
        for i in range(int(dur * sr)):
            t = i / sr
            freq = 800 if int(t * 4) % 2 == 0 else 600
            s = 0.5 * math.sin(2 * math.pi * freq * t)
            env = min(1.0, min(t * 10, (dur - t) * 10))
            samples.append(s * env)
        return samples

    def _snd_engine(self, dur, sr):
        random.seed(42)
        samples = []
        for i in range(int(dur * sr)):
            t = i / sr
            base = 0.3 * math.sin(2 * math.pi * 60 * t)
            noise = 0.5 * (random.random() * 2 - 1)
            rumble = 0.2 * math.sin(2 * math.pi * 30 * t)
            env = min(1.0, t * 2) * max(0, 1 - t / dur * 0.3)
            samples.append((base + noise * 0.6 + rumble) * env)
        return samples

    def _snd_beep(self, dur, sr):
        samples = []
        for i in range(int(dur * sr)):
            t = i / sr
            s = 0.4 * math.sin(2 * math.pi * 1200 * t)
            env = max(0, 1 - (t % 0.5) * 4)
            samples.append(s * env)
        return samples

    def _snd_wind(self, dur, sr):
        random.seed(123)
        samples = []
        for i in range(int(dur * sr)):
            t = i / sr
            noise = 0.6 * (random.random() * 2 - 1)
            s = 0.3 * math.sin(2 * math.pi * 200 * t + noise * 5)
            env = 0.5 + 0.5 * math.sin(2 * math.pi * 0.5 * t)
            samples.append((s + noise * 0.4) * env)
        return samples

    def _snd_radio(self, dur, sr):
        random.seed(999)
        samples = []
        for i in range(int(dur * sr)):
            t = i / sr
            static = 0.3 * (random.random() * 2 - 1)
            tone = 0.2 * math.sin(2 * math.pi * 1000 * t)
            env = 0.5 + 0.5 * math.sin(2 * math.pi * 3 * t)
            samples.append((static + tone * 0.3) * env)
        return samples

    def _snd_melody(self, dur, sr):
        notes = [440, 494, 523, 587, 659, 587, 523, 494]
        samples = []
        note_dur = dur / len(notes)
        for i in range(int(dur * sr)):
            t = i / sr
            note_idx = min(int(t / note_dur), len(notes) - 1)
            freq = notes[note_idx]
            s = 0.4 * math.sin(2 * math.pi * freq * t)
            note_t = t % note_dur
            env = min(1.0, note_t * 10) * max(0, 1 - (note_t - note_dur + 0.1) * 10)
            samples.append(s * max(0, env))
        return samples

    def _snd_heartbeat(self, dur, sr):
        samples = []
        bpm = 72
        beat_period = 60.0 / bpm
        for i in range(int(dur * sr)):
            t = i / sr
            beat_t = t % beat_period
            s = 0.0
            if beat_t < 0.1:
                s = 0.8 * math.sin(2 * math.pi * 40 * t) * (1 - beat_t / 0.1)
            elif 0.15 < beat_t < 0.25:
                s = 0.5 * math.sin(2 * math.pi * 50 * t) * (1 - (beat_t - 0.15) / 0.1)
            samples.append(s)
        return samples

    def _snd_laser(self, dur, sr):
        samples = []
        for i in range(int(dur * sr)):
            t = i / sr
            freq = 2000 - t * 2000 / dur
            s = 0.5 * math.sin(2 * math.pi * max(100, freq) * t)
            env = max(0, 1 - t / dur)
            samples.append(s * env)
        return samples

    def _snd_tone(self, dur, sr):
        samples = []
        for i in range(int(dur * sr)):
            t = i / sr
            s = 0.4 * math.sin(2 * math.pi * 440 * t)
            env = min(1.0, min(t * 5, (dur - t) * 5))
            samples.append(s * env)
        return samples

    # ──────────────────────────────────────────────────────────────
    # VIDEO GENERATOR (Frame sequence)
    # ──────────────────────────────────────────────────────────────

    def generate_video(self, prompt: str, width: int = 640, height: int = 480,
                       duration: float = 3.0, fps: int = 24) -> Dict[str, Any]:
        """Generate video frame sequence."""
        if not self.pil:
            return {"error": "Pillow not installed", "status": "failed"}
        if not self.numpy:
            return {"error": "numpy not installed", "status": "failed"}

        t0 = time.time()
        prompt_lower = prompt.lower()
        n_frames = int(duration * fps)

        frames_dir = self.output_dir / f"vid_{int(time.time())}"
        frames_dir.mkdir(exist_ok=True)

        for frame_idx in range(n_frames):
            t = frame_idx / fps
            progress = frame_idx / n_frames

            img = Image.new("RGB", (width, height), (6, 6, 20))
            draw = ImageDraw.Draw(img)

            if any(w in prompt_lower for w in ["launch", "rocket", "lift"]):
                self._vid_launch(draw, width, height, t, progress)
            elif any(w in prompt_lower for w in ["orbit", "satellite"]):
                self._vid_orbit(draw, width, height, t, progress)
            elif any(w in prompt_lower for w in ["warp", "star", "hyperspace"]):
                self._vid_warp(draw, width, height, t, progress)
            elif any(w in prompt_lower for w in ["wave", "ocean"]):
                self._vid_wave(draw, width, height, t, progress)
            elif any(w in prompt_lower for w in ["pulse", "energy"]):
                self._vid_pulse(draw, width, height, t, progress)
            else:
                self._vid_default(draw, width, height, t, progress)

            frame_path = str(frames_dir / f"frame_{frame_idx:05d}.png")
            img.save(frame_path, "PNG")

        elapsed = (time.time() - t0) * 1000
        return {
            "frames_dir": str(frames_dir),
            "frame_count": n_frames,
            "fps": fps,
            "duration": duration,
            "width": width,
            "height": height,
            "prompt": prompt,
            "latency_ms": round(elapsed, 1),
            "encode_cmd": f"ffmpeg -framerate {fps} -i {frames_dir}/frame_%05d.png -c:v libx264 -pix_fmt yuv420p output.mp4",
            "status": "ok",
        }

    def _vid_launch(self, draw, w, h, t, p):
        cx = w // 2
        rocket_y = int(h - 50 - p * (h - 100))
        flame_h = 40 + random.randint(-10, 20)
        draw.rectangle([cx - 25, rocket_y - 80, cx + 25, rocket_y + 40], fill=(0, 200, 255))
        draw.polygon([(cx, rocket_y - 110), (cx - 25, rocket_y - 80), (cx + 25, rocket_y - 80)], fill=(0, 200, 255))
        draw.polygon([(cx - 20, rocket_y + 40), (cx, rocket_y + 40 + flame_h), (cx + 20, rocket_y + 40)], fill=(255, 120, 0))
        random.seed(int(t * 100))
        for _ in range(150):
            x, y = random.randint(0, w), random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))

    def _vid_orbit(self, draw, w, h, t, p):
        cx, cy = w // 2, h // 2
        draw.ellipse([cx - 80, cy - 80, cx + 80, cy + 80], fill=(30, 100, 200))
        orbit_r = 160
        draw.ellipse([cx - orbit_r, cy - orbit_r, cx + orbit_r, cy + orbit_r], outline=(0, 200, 255), width=1)
        angle = t * 0.5
        sat_x = int(cx + orbit_r * math.cos(angle))
        sat_y = int(cy + orbit_r * math.sin(angle))
        draw.rectangle([sat_x - 4, sat_y - 2, sat_x + 4, sat_y + 2], fill=(255, 200, 0))
        random.seed(42)
        for _ in range(200):
            x, y = random.randint(0, w), random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))

    def _vid_warp(self, draw, w, h, t, p):
        cx, cy = w // 2, h // 2
        random.seed(int(t * 100))
        for _ in range(250):
            x = random.randint(0, w)
            y = random.randint(0, h)
            dx = x - cx
            dy = y - cy
            stretch = 1 + p * 4
            sx = int(cx + dx * stretch)
            sy = int(cy + dy * stretch)
            if 0 <= sx < w and 0 <= sy < h:
                draw.line([(x, y), (sx, sy)], fill=(200, 200, 255), width=1)

    def _vid_wave(self, draw, w, h, t, p):
        for x in range(0, w, 2):
            y_val = int(h / 2 + 50 * math.sin(x * 0.02 + t * 2))
            draw.line([(x, y_val), (x, h)], fill=(0, 50 + int(p * 100), 150 + int(p * 100)))

    def _vid_pulse(self, draw, w, h, t, p):
        cx, cy = w // 2, h // 2
        r = int(20 + 80 * (0.5 + 0.5 * math.sin(t * 3)))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(0, int(200 * p), 255))

    def _vid_default(self, draw, w, h, t, p):
        random.seed(int(t * 10))
        for _ in range(100):
            x, y = random.randint(0, w), random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))
        cx = int(w * 0.5 + 100 * math.sin(t))
        cy = int(h * 0.5 + 100 * math.cos(t))
        draw.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=(0, 200, 255))

    # ──────────────────────────────────────────────────────────────
    # 3D MESH GENERATOR
    # ──────────────────────────────────────────────────────────────

    def generate_3d(self, prompt: str) -> Dict[str, Any]:
        """Generate 3D mesh from prompt."""
        t0 = time.time()
        prompt_lower = prompt.lower()

        if self.tm:
            if any(w in prompt_lower for w in ["rocket", "ship", "vehicle"]):
                result = self._3d_rocket(prompt)
            elif any(w in prompt_lower for w in ["satellite"]):
                result = self._3d_satellite(prompt)
            elif any(w in prompt_lower for w in ["station", "habitat"]):
                result = self._3d_station(prompt)
            elif any(w in prompt_lower for w in ["drone", "uav"]):
                result = self._3d_drone(prompt)
            elif any(w in prompt_lower for w in ["gear", "ring", "wheel"]):
                result = self._3d_ring(prompt)
            elif any(w in prompt_lower for w in ["sphere", "planet"]):
                result = self._3d_sphere(prompt)
            elif any(w in prompt_lower for w in ["cube", "box"]):
                result = self._3d_box(prompt)
            elif any(w in prompt_lower for w in ["cylinder", "tube"]):
                result = self._3d_cylinder(prompt)
            else:
                result = self._3d_custom(prompt)
        else:
            result = self._3d_fallback(prompt)

        result["latency_ms"] = round((time.time() - t0) * 1000, 1)
        result["prompt"] = prompt
        return result

    def _3d_rocket(self, prompt):
        tm = self.tm
        n = 32
        theta = [2 * math.pi * i / n for i in range(n)]

        verts = []
        for h in [0, 4.0]:
            for t in theta:
                verts.append([0.5 * math.cos(t), 0.5 * math.sin(t), h])
        faces = []
        for i in range(n):
            j = (i + 1) % n
            faces.append([i, j, j + n])
            faces.append([i, j + n, i + n])

        nose_offset = len(verts)
        for t in theta:
            verts.append([0.5 * math.cos(t), 0.5 * math.sin(t), 4.0])
        verts.append([0, 0, 5.5])
        nose_tip = len(verts) - 1
        for i in range(n):
            j = (i + 1) % n
            faces.append([nose_offset + i, nose_offset + j, nose_tip])

        mesh = tm.Trimesh(vertices=np.array(verts), faces=np.array(faces))
        stl_path = str(OUTPUT_DIR / f"rocket_{int(time.time())}.stl")
        mesh.export(stl_path)
        return {"file": stl_path, "format": "stl", "vertices": len(verts), "faces": len(faces), "engine": "trimesh"}

    def _3d_satellite(self, prompt):
        tm = self.tm
        body = tm.creation.box(extents=[1, 1, 0.6])
        panel1 = tm.creation.box(extents=[2, 0.05, 1])
        panel1.apply_translation([0, 0, 1.5])
        panel2 = tm.creation.box(extents=[2, 0.05, 1])
        panel2.apply_translation([0, 0, -1.5])
        dish = tm.creation.cylinder(radius=0.3, height=0.1, sections=32)
        dish.apply_translation([0.6, 0, 0])
        mesh = tm.util.concatenate([body, panel1, panel2, dish])
        stl_path = str(OUTPUT_DIR / f"satellite_{int(time.time())}.stl")
        mesh.export(stl_path)
        return {"file": stl_path, "format": "stl", "vertices": len(mesh.vertices), "faces": len(mesh.faces), "engine": "trimesh"}

    def _3d_station(self, prompt):
        tm = self.tm
        ring = tm.creation.annulus(r_min=3, r_max=3.5, height=1.5, sections=48)
        hub = tm.creation.cylinder(radius=0.8, height=3, sections=32)
        spokes = []
        for i in range(6):
            theta = 2 * math.pi * i / 6
            spoke = tm.creation.box(extents=[3, 0.2, 0.2])
            spoke.apply_translation([1.5 * math.cos(theta), 1.5 * math.sin(theta), 0])
            spoke.apply_transform(tm.transformations.rotation_matrix(theta, [0, 0, 1]))
            spokes.append(spoke)
        mesh = tm.util.concatenate([ring, hub] + spokes)
        stl_path = str(OUTPUT_DIR / f"station_{int(time.time())}.stl")
        mesh.export(stl_path)
        return {"file": stl_path, "format": "stl", "vertices": len(mesh.vertices), "faces": len(mesh.faces), "engine": "trimesh"}

    def _3d_drone(self, prompt):
        tm = self.tm
        body = tm.creation.box(extents=[0.8, 0.8, 0.2])
        parts = [body]
        for i in range(4):
            theta = math.pi / 4 + math.pi * i / 2
            arm = tm.creation.box(extents=[0.6, 0.08, 0.08])
            arm.apply_translation([0.4 * math.cos(theta), 0.4 * math.sin(theta), 0])
            parts.append(arm)
            rotor = tm.creation.cylinder(radius=0.25, height=0.02, sections=24)
            rotor.apply_translation([0.6 * math.cos(theta), 0.6 * math.sin(theta), 0.1])
            parts.append(rotor)
        mesh = tm.util.concatenate(parts)
        stl_path = str(OUTPUT_DIR / f"drone_{int(time.time())}.stl")
        mesh.export(stl_path)
        return {"file": stl_path, "format": "stl", "vertices": len(mesh.vertices), "faces": len(mesh.faces), "engine": "trimesh"}

    def _3d_ring(self, prompt):
        tm = self.tm
        mesh = tm.creation.annulus(r_min=0.8, r_max=1.0, height=0.3, sections=48)
        stl_path = str(OUTPUT_DIR / f"ring_{int(time.time())}.stl")
        mesh.export(stl_path)
        return {"file": stl_path, "format": "stl", "vertices": len(mesh.vertices), "faces": len(mesh.faces), "engine": "trimesh"}

    def _3d_sphere(self, prompt):
        tm = self.tm
        mesh = tm.creation.uv_sphere(radius=1.0, count=[32, 32])
        stl_path = str(OUTPUT_DIR / f"sphere_{int(time.time())}.stl")
        mesh.export(stl_path)
        return {"file": stl_path, "format": "stl", "vertices": len(mesh.vertices), "faces": len(mesh.faces), "engine": "trimesh"}

    def _3d_box(self, prompt):
        tm = self.tm
        mesh = tm.creation.box(extents=[2, 2, 2])
        stl_path = str(OUTPUT_DIR / f"box_{int(time.time())}.stl")
        mesh.export(stl_path)
        return {"file": stl_path, "format": "stl", "vertices": len(mesh.vertices), "faces": len(mesh.faces), "engine": "trimesh"}

    def _3d_cylinder(self, prompt):
        tm = self.tm
        mesh = tm.creation.cylinder(radius=0.5, height=2.0, sections=32)
        stl_path = str(OUTPUT_DIR / f"cylinder_{int(time.time())}.stl")
        mesh.export(stl_path)
        return {"file": stl_path, "format": "stl", "vertices": len(mesh.vertices), "faces": len(mesh.faces), "engine": "trimesh"}

    def _3d_custom(self, prompt):
        tm = self.tm
        mesh = tm.creation.icosphere(subdivisions=2, radius=1.0)
        stl_path = str(OUTPUT_DIR / f"custom_{int(time.time())}.stl")
        mesh.export(stl_path)
        return {"file": stl_path, "format": "stl", "vertices": len(mesh.vertices), "faces": len(mesh.faces), "engine": "trimesh"}

    def _3d_fallback(self, prompt):
        verts = [
            [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
            [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1],
        ]
        faces = [
            [0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4],
            [2, 3, 7, 6], [0, 3, 7, 4], [1, 2, 6, 5],
        ]
        obj_path = str(OUTPUT_DIR / f"model_{int(time.time())}.obj")
        with open(obj_path, 'w') as f:
            f.write(f"# ZICore 3D Model: {prompt}\n")
            for v in verts:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            for face in faces:
                f.write("f " + " ".join(str(fi + 1) for fi in face) + "\n")
        return {"file": obj_path, "format": "obj", "vertices": len(verts), "faces": len(faces), "engine": "fallback"}

    # ──────────────────────────────────────────────────────────────
    # UNIFIED COMMAND INTERFACE
    # ──────────────────────────────────────────────────────────────

    def generate(self, gen_type: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """Unified generate command. Routes to specific generator."""
        gen_type = gen_type.lower()

        if gen_type in ("image", "img", "picture", "draw"):
            return self.generate_image(prompt, **kwargs)
        elif gen_type in ("sound", "snd", "audio", "sfx"):
            return self.generate_sound(prompt, **kwargs)
        elif gen_type in ("video", "vid", "animation"):
            return self.generate_video(prompt, **kwargs)
        elif gen_type in ("3d", "mesh", "stl", "obj"):
            return self.generate_3d(prompt)
        else:
            return {"error": f"Unknown generation type: {gen_type}", "available": ["image", "sound", "video", "3d"]}


# Singleton
generator = ZICoreGenerator()

"""
Media Engine - Image, Video, Sound Generation
Uses: Pillow (images), numpy (audio/video), wave (sound)
"""
import os
import math
import json
import struct
import time
import wave
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("zicore.agent.media")

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


class MediaEngine:
    def __init__(self):
        self._init_pillow()

    def _init_pillow(self):
        try:
            from PIL import Image, ImageDraw, ImageFont
            self.PIL = True
            logger.info("Pillow available for image generation")
        except ImportError:
            self.PIL = False
            logger.warning("Pillow not available")

    def generate_image(self, prompt: str, width: int = 1024, height: int = 768) -> dict:
        if not self.PIL:
            return {"error": "Pillow not installed", "hint": "pip install Pillow"}

        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            return {"error": "Pillow not importable"}

        img = Image.new("RGB", (width, height), (6, 6, 20))
        draw = ImageDraw.Draw(img)

        t_lower = prompt.lower()

        if any(w in t_lower for w in ["rocket", "ship", "vehicle", "craft", "nave", "cohete"]):
            self._draw_rocket(draw, width, height)
        elif any(w in t_lower for w in ["orbit", "planet", "earth", "space", "orbita"]):
            self._draw_orbit(draw, width, height)
        elif any(w in t_lower for w in ["star", "constellation", "starfield", "stars"]):
            self._draw_starfield(draw, width, height)
        elif any(w in t_lower for w in ["blueprint", "schematic", "diagram", "engineering"]):
            self._draw_blueprint(draw, width, height, prompt)
        elif any(w in t_lower for w in ["circuit", "pcb", "board"]):
            self._draw_circuit(draw, width, height)
        elif any(w in t_lower for w in ["planet", "mars", "moon", "saturn"]):
            self._draw_planet(draw, width, height)
        else:
            self._draw_aerospace_grid(draw, width, height)

        try:
            try:
                from PIL import ImageFont
                font = ImageFont.truetype("arial.ttf", 18)
            except Exception:
                font = ImageFont.load_default()

            draw.text((10, height - 30), f"ZICore | {prompt[:60]}", fill=(0, 200, 255), font=font)
        except Exception:
            pass

        save_path = str(OUTPUT_DIR / f"image_{int(time.time())}.png")
        img.save(save_path, "PNG")
        return {"file": save_path, "prompt": prompt, "dimensions": f"{width}x{height}", "status": "ok"}

    def _draw_rocket(self, draw, w, h):
        cx, cy = w // 2, h // 2
        body_color = (0, 200, 255)
        flame_color = (255, 120, 0)

        points_nose = [(cx, cy - 200), (cx - 30, cy - 100), (cx + 30, cy - 100)]
        draw.polygon(points_nose, fill=body_color)

        draw.rectangle([cx - 30, cy - 100, cx + 30, cy + 120], fill=body_color)

        fin_pts_left = [(cx - 30, cy + 80), (cx - 80, cy + 150), (cx - 30, cy + 120)]
        fin_pts_right = [(cx + 30, cy + 80), (cx + 80, cy + 150), (cx + 30, cy + 120)]
        draw.polygon(fin_pts_left, fill=(0, 150, 200))
        draw.polygon(fin_pts_right, fill=(0, 150, 200))

        flame_pts = [(cx - 25, cy + 120), (cx, cy + 220), (cx + 25, cy + 120)]
        draw.polygon(flame_pts, fill=flame_color)

        draw.ellipse([cx - 15, cy - 50, cx + 15, cy - 20], fill=(100, 220, 255))

        for i in range(200):
            import random
            x = random.randint(0, w)
            y = random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))

    def _draw_orbit(self, draw, w, h):
        cx, cy = w // 2, h // 2

        for i in range(300):
            import random
            x, y = random.randint(0, w), random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))

        r_earth = 80
        draw.ellipse([cx - r_earth, cy - r_earth, cx + r_earth, cy + r_earth],
                     fill=(30, 100, 200))
        draw.ellipse([cx - r_earth + 20, cy - r_earth - 10, cx + r_earth - 10, cy + r_earth + 20],
                     fill=(40, 130, 220))

        for orbit_r in [140, 200, 260]:
            draw.ellipse([cx - orbit_r, cy - orbit_r, cx + orbit_r, cy + orbit_r],
                        outline=(0, 200, 255, 100), width=1)
            sat_x = cx + orbit_r - 20
            sat_y = cy
            draw.rectangle([sat_x - 5, sat_y - 3, sat_x + 5, sat_y + 3], fill=(255, 200, 0))

    def _draw_starfield(self, draw, w, h):
        import random
        random.seed(42)
        for _ in range(500):
            x, y = random.randint(0, w), random.randint(0, h)
            brightness = random.randint(100, 255)
            draw.point((x, y), fill=(brightness, brightness, brightness))
            if random.random() > 0.9:
                draw.line([(x - 2, y), (x + 2, y)], fill=(brightness, brightness, brightness))

    def _draw_blueprint(self, draw, w, h, prompt):
        draw.rectangle([20, 20, w - 20, h - 20], outline=(0, 100, 200), width=2)
        for i in range(20, w - 20, 50):
            draw.line([(i, 20), (i, h - 20)], fill=(0, 40, 80), width=1)
        for i in range(20, h - 20, 50):
            draw.line([(20, i), (w - 20, i)], fill=(0, 40, 80), width=1)
        cx, cy = w // 2, h // 2
        draw.rectangle([cx - 100, cy - 50, cx + 100, cy + 50], outline=(0, 200, 255), width=2)
        draw.line([(cx - 100, cy), (cx - 140, cy)], fill=(255, 200, 0), width=2)
        draw.line([(cx + 100, cy), (cx + 140, cy)], fill=(255, 200, 0), width=2)
        try:
            from PIL import ImageFont
            font = ImageFont.truetype("arial.ttf", 14)
        except Exception:
            font = None
        draw.text((cx - 80, cy + 60), "ZICORE AEROSPACE", fill=(0, 200, 255), font=font)

    def _draw_circuit(self, draw, w, h):
        import random
        for _ in range(50):
            x1 = random.randint(50, w - 50)
            y1 = random.randint(50, h - 50)
            x2 = x1 + random.choice([-80, -40, 0, 40, 80])
            y2 = y1 + random.choice([-40, 0, 40])
            draw.line([(x1, y1), (x2, y2)], fill=(0, 180, 80), width=2)
            draw.rectangle([x2 - 4, y2 - 4, x2 + 4, y2 + 4], fill=(0, 255, 100))

    def _draw_planet(self, draw, w, h):
        cx, cy = w // 2, h // 2
        r = 120
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(180, 80, 40))
        draw.ellipse([cx - r + 30, cy - r + 20, cx + r - 40, cy + r - 10],
                     fill=(200, 100, 50))
        draw.ellipse([cx + 40, cy - r - 5, cx + r + 80, cy - r + 15], fill=(200, 200, 100), outline=(220, 220, 120))
        import random
        for _ in range(300):
            x, y = random.randint(0, w), random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))

    def _draw_aerospace_grid(self, draw, w, h):
        for i in range(0, w, 30):
            draw.line([(i, 0), (i, h)], fill=(0, 40, 60), width=1)
        for i in range(0, h, 30):
            draw.line([(0, i), (w, i)], fill=(0, 40, 60), width=1)
        import random
        for _ in range(200):
            x, y = random.randint(0, w), random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))

    def generate_sound(self, prompt: str, duration: float = 3.0, sample_rate: int = 44100) -> dict:
        t_lower = prompt.lower()
        if any(w in t_lower for w in ["alarm", "alert", "warning"]):
            samples = self._gen_alarm(duration, sample_rate)
        elif any(w in t_lower for w in ["engine", "thrust", "rocket"]):
            samples = self._gen_roar(duration, sample_rate)
        elif any(w in t_lower for w in ["beep", "sonar", "ping"]):
            samples = self._gen_beep(duration, sample_rate)
        elif any(w in t_lower for w in ["wind", "atmosphere"]):
            samples = self._gen_wind(duration, sample_rate)
        elif any(w in t_lower for w in ["radio", "transmission", "static"]):
            samples = self._gen_radio(duration, sample_rate)
        else:
            samples = self._gen_tone(duration, sample_rate)

        save_path = str(OUTPUT_DIR / f"sound_{int(time.time())}.wav")
        with wave.open(save_path, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            for s in samples:
                wf.writeframes(struct.pack('<h', max(-32768, min(32767, int(s * 32767)))))

        return {"file": save_path, "prompt": prompt, "duration": duration, "status": "ok"}

    def _gen_alarm(self, dur, sr):
        samples = []
        n = int(dur * sr)
        for i in range(n):
            t = i / sr
            freq = 800 if int(t * 4) % 2 == 0 else 600
            s = 0.5 * math.sin(2 * math.pi * freq * t)
            env = min(1.0, min(t * 10, (dur - t) * 10))
            samples.append(s * env)
        return samples

    def _gen_roar(self, dur, sr):
        import random
        samples = []
        n = int(dur * sr)
        random.seed(42)
        for i in range(n):
            t = i / sr
            base = 0.3 * math.sin(2 * math.pi * 60 * t)
            noise = 0.5 * (random.random() * 2 - 1)
            rumble = 0.2 * math.sin(2 * math.pi * 30 * t)
            env = min(1.0, t * 2) * max(0, 1 - t / dur * 0.5)
            samples.append((base + noise * 0.6 + rumble) * env)
        return samples

    def _gen_beep(self, dur, sr):
        samples = []
        n = int(dur * sr)
        for i in range(n):
            t = i / sr
            s = 0.4 * math.sin(2 * math.pi * 1200 * t)
            env = max(0, 1 - (t % 0.5) * 4)
            samples.append(s * env)
        return samples

    def _gen_wind(self, dur, sr):
        import random
        samples = []
        n = int(dur * sr)
        random.seed(123)
        for i in range(n):
            t = i / sr
            noise = 0.6 * (random.random() * 2 - 1)
            s = 0.3 * math.sin(2 * math.pi * 200 * t + noise * 5)
            env = 0.5 + 0.5 * math.sin(2 * math.pi * 0.5 * t)
            samples.append((s + noise * 0.4) * env)
        return samples

    def _gen_radio(self, dur, sr):
        import random
        samples = []
        n = int(dur * sr)
        random.seed(999)
        for i in range(n):
            t = i / sr
            static = 0.3 * (random.random() * 2 - 1)
            tone = 0.2 * math.sin(2 * math.pi * 1000 * t)
            env = 0.5 + 0.5 * math.sin(2 * math.pi * 3 * t)
            samples.append((static + tone * 0.3) * env)
        return samples

    def _gen_tone(self, dur, sr):
        samples = []
        n = int(dur * sr)
        for i in range(n):
            t = i / sr
            s = 0.4 * math.sin(2 * math.pi * 440 * t)
            env = min(1.0, min(t * 5, (dur - t) * 5))
            samples.append(s * env)
        return samples

    def generate_video(self, prompt: str, width: int = 640, height: int = 480,
                       duration: float = 5.0, fps: int = 24) -> dict:
        try:
            import numpy as np
        except ImportError:
            return {"error": "numpy not installed", "hint": "pip install numpy"}

        try:
            from PIL import Image
        except ImportError:
            return {"error": "Pillow not installed", "hint": "pip install Pillow"}

        import random
        random.seed(42)

        frames_dir = OUTPUT_DIR / f"video_{int(time.time())}"
        frames_dir.mkdir(exist_ok=True)

        t_lower = prompt.lower()
        n_frames = int(duration * fps)

        for frame_idx in range(n_frames):
            t = frame_idx / fps
            progress = frame_idx / n_frames

            img = Image.new("RGB", (width, height), (6, 6, 20))

            try:
                from PIL import ImageDraw
                draw = ImageDraw.Draw(img)
            except ImportError:
                continue

            if any(w in t_lower for w in ["launch", "rocket", "lift"]):
                self._frame_launch(draw, width, height, t, progress)
            elif any(w in t_lower for w in ["orbit", "satellite"]):
                self._frame_orbit(draw, width, height, t, progress)
            elif any(w in t_lower for w in ["star", "warp"]):
                self._frame_warp(draw, width, height, t, progress)
            else:
                self._frame_default(draw, width, height, t, progress)

            frame_path = str(frames_dir / f"frame_{frame_idx:05d}.png")
            img.save(frame_path, "PNG")

        save_path = str(OUTPUT_DIR / f"video_{int(time.time())}.json")
        info = {
            "status": "frames_generated",
            "frames_dir": str(frames_dir),
            "frame_count": n_frames,
            "fps": fps,
            "duration": duration,
            "dimensions": f"{width}x{height}",
            "prompt": prompt,
            "note": "Frames saved. Use ffmpeg to encode: ffmpeg -framerate {fps} -i {frames_dir}/frame_%05d.png output.mp4"
        }
        with open(save_path, 'w') as f:
            json.dump(info, f, indent=2)

        return info

    def _frame_launch(self, draw, w, h, t, p):
        import random
        cx = w // 2
        rocket_y = int(h - 50 - p * (h - 100))
        flame_h = 40 + random.randint(-10, 20)
        draw.rectangle([cx - 25, rocket_y - 80, cx + 25, rocket_y + 40], fill=(0, 200, 255))
        draw.polygon([(cx, rocket_y - 110), (cx - 25, rocket_y - 80), (cx + 25, rocket_y - 80)], fill=(0, 200, 255))
        draw.polygon([(cx - 20, rocket_y + 40), (cx, rocket_y + 40 + flame_h), (cx + 20, rocket_y + 40)], fill=(255, 120, 0))
        for _ in range(100):
            x = random.randint(0, w)
            y = random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))

    def _frame_orbit(self, draw, w, h, t, p):
        import random
        cx, cy = w // 2, h // 2
        r = 100
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(30, 100, 200))
        orbit_r = 160
        draw.ellipse([cx - orbit_r, cy - orbit_r, cx + orbit_r, cy + orbit_r], outline=(0, 200, 255), width=1)
        angle = t * 0.5
        sat_x = int(cx + orbit_r * math.cos(angle))
        sat_y = int(cy + orbit_r * math.sin(angle))
        draw.rectangle([sat_x - 4, sat_y - 2, sat_x + 4, sat_y + 2], fill=(255, 200, 0))
        for _ in range(150):
            x, y = random.randint(0, w), random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))

    def _frame_warp(self, draw, w, h, t, p):
        import random
        random.seed(int(t * 100))
        cx, cy = w // 2, h // 2
        for _ in range(200):
            x = random.randint(0, w)
            y = random.randint(0, h)
            dx = x - cx
            dy = y - cy
            dist = max(1, (dx ** 2 + dy ** 2) ** 0.5)
            stretch = 1 + p * 3
            sx = int(cx + dx * stretch)
            sy = int(cy + dy * stretch)
            if 0 <= sx < w and 0 <= sy < h:
                draw.line([(x, y), (sx, sy)], fill=(200, 200, 255), width=1)

    def _frame_default(self, draw, w, h, t, p):
        import random
        random.seed(int(t * 10))
        for _ in range(100):
            x, y = random.randint(0, w), random.randint(0, h)
            draw.point((x, y), fill=(255, 255, 255))
        cx = int(w * 0.5 + 100 * math.sin(t))
        cy = int(h * 0.5 + 100 * math.cos(t))
        draw.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=(0, 200, 255))

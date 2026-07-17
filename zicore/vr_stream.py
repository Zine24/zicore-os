"""
ZICORE VR Stream Renderer — Real-time VR frame generation and streaming.

Generates stereo frames from materialized meshes for VR headsets,
external displays, and monitor output. CPU-only rendering via Pillow.

Author: ZineMotion Foundation — Aerospace Division
Version: 5.0.0
"""

import io
import time
import json
import uuid
import base64
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Callable
from dataclasses import dataclass, field

logger = logging.getLogger("zicore.vr_stream")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


# =============================================================================
# CONSTANTS
# =============================================================================

DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480
DEFAULT_FPS = 30
DEFAULT_IPD = 0.063  # Interpupillary distance in meters (63mm)
STERO_MARGIN = 4     # Pixels between left/right eye

SCENE_PRESETS = {
    "planetary_surface": {
        "bg": (8, 12, 24),
        "ground_color": (40, 50, 70),
        "sky_color": (15, 20, 40),
        "horizon_y": 0.55,
        "objects": [
            {"type": "crater", "x": 0.3, "y": 0.58, "w": 0.15, "h": 0.04, "color": (30, 35, 50)},
            {"type": "crater", "x": 0.65, "y": 0.62, "w": 0.08, "h": 0.02, "color": (25, 30, 45)},
            {"type": "rock", "x": 0.8, "y": 0.54, "w": 0.03, "h": 0.05, "color": (60, 65, 80)},
            {"type": "rock", "x": 0.15, "y": 0.56, "w": 0.02, "h": 0.03, "color": (55, 60, 75)},
        ],
        "stars": True,
        "nebula": True,
    },
    "space_station": {
        "bg": (5, 5, 15),
        "ground_color": None,
        "sky_color": (5, 5, 15),
        "horizon_y": 1.0,
        "objects": [
            {"type": "module", "x": 0.5, "y": 0.5, "w": 0.25, "h": 0.08, "color": (120, 130, 150)},
            {"type": "solar_panel", "x": 0.3, "y": 0.48, "w": 0.12, "h": 0.04, "color": (40, 60, 120)},
            {"type": "solar_panel", "x": 0.7, "y": 0.48, "w": 0.12, "h": 0.04, "color": (40, 60, 120)},
            {"type": "truss", "x": 0.5, "y": 0.5, "w": 0.35, "h": 0.01, "color": (100, 105, 120)},
        ],
        "stars": True,
        "nebula": False,
    },
    "lunar_base": {
        "bg": (10, 10, 18),
        "ground_color": (50, 48, 55),
        "sky_color": (10, 10, 18),
        "horizon_y": 0.6,
        "objects": [
            {"type": "habitat", "x": 0.5, "y": 0.55, "w": 0.15, "h": 0.1, "color": (140, 135, 120)},
            {"type": "antenna", "x": 0.65, "y": 0.45, "w": 0.01, "h": 0.12, "color": (180, 180, 190)},
            {"type": "rover", "x": 0.3, "y": 0.58, "w": 0.06, "h": 0.03, "color": (160, 155, 140)},
            {"type": "earth", "x": 0.8, "y": 0.15, "w": 0.08, "h": 0.08, "color": (60, 100, 180)},
        ],
        "stars": True,
        "nebula": False,
    },
    "launch_pad": {
        "bg": (20, 30, 60),
        "ground_color": (60, 60, 65),
        "sky_color": (20, 30, 60),
        "horizon_y": 0.65,
        "objects": [
            {"type": "rocket", "x": 0.5, "y": 0.35, "w": 0.06, "h": 0.3, "color": (200, 200, 210)},
            {"type": "tower", "x": 0.42, "y": 0.4, "w": 0.02, "h": 0.22, "color": (100, 100, 110)},
            {"type": "flame", "x": 0.5, "y": 0.65, "w": 0.08, "h": 0.06, "color": (255, 160, 40)},
        ],
        "stars": True,
        "nebula": False,
    },
    "cockpit": {
        "bg": (10, 14, 22),
        "ground_color": None,
        "sky_color": (10, 14, 22),
        "horizon_y": 1.0,
        "objects": [
            {"type": "hud_frame", "x": 0.5, "y": 0.5, "w": 0.9, "h": 0.8, "color": (30, 40, 60)},
            {"type": "display", "x": 0.5, "y": 0.35, "w": 0.3, "h": 0.2, "color": (0, 80, 60)},
            {"type": "display", "x": 0.25, "y": 0.55, "w": 0.2, "h": 0.15, "color": (60, 20, 20)},
            {"type": "display", "x": 0.75, "y": 0.55, "w": 0.2, "h": 0.15, "color": (20, 20, 60)},
        ],
        "stars": True,
        "nebula": False,
    },
    "landscape": {
        "bg": (15, 25, 45),
        "ground_color": (30, 60, 40),
        "sky_color": (15, 25, 45),
        "horizon_y": 0.55,
        "objects": [
            {"type": "mountain", "x": 0.2, "y": 0.48, "w": 0.25, "h": 0.15, "color": (40, 70, 50)},
            {"type": "mountain", "x": 0.7, "y": 0.5, "w": 0.3, "h": 0.12, "color": (35, 65, 45)},
            {"type": "tree", "x": 0.4, "y": 0.52, "w": 0.02, "h": 0.06, "color": (25, 80, 35)},
            {"type": "tree", "x": 0.6, "y": 0.54, "w": 0.015, "h": 0.04, "color": (30, 75, 40)},
        ],
        "stars": True,
        "nebula": True,
    },
}


# =============================================================================
# VR FRAME RENDERER
# =============================================================================

@dataclass
class CameraState:
    """VR camera state for stereo rendering."""
    x: float = 0.0
    y: float = 1.7
    z: float = 0.0
    yaw: float = 0.0    # Horizontal rotation (degrees)
    pitch: float = 0.0  # Vertical rotation (degrees)
    roll: float = 0.0   # Head tilt (degrees)
    fov: float = 75.0


@dataclass
class VRFrame:
    """A single rendered VR frame."""
    left_eye: bytes       # PNG bytes for left eye
    right_eye: bytes      # PNG bytes for right eye
    width: int
    height: int
    timestamp: float
    frame_num: int
    camera: CameraState


class VRStreamRenderer:
    """CPU-based stereo VR frame renderer.

    Generates left/right eye PNG frames from scene descriptions.
    Uses Pillow for software rasterization — no GPU required.
    """

    def __init__(self):
        self.width = DEFAULT_WIDTH
        self.height = DEFAULT_HEIGHT
        self.half_w = DEFAULT_WIDTH // 2
        self.stars_cache: Dict[str, List[Tuple[float, float, float]]] = {}
        self._star_seed = 42

    def render_stereo_frame(
        self,
        scene_type: str,
        camera: CameraState,
        frame_num: int = 0,
        mesh_data: Optional[Any] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Optional[VRFrame]:
        """Render a stereo pair (left + right eye) for the given scene."""
        if not PILLOW_AVAILABLE or not NUMPY_AVAILABLE:
            return None

        w = width or self.width
        h = height or self.height
        hw = w // 2
        ipd_offset = DEFAULT_IPD * 0.5  # Half IPD for each eye

        left_camera = CameraState(
            x=camera.x - ipd_offset, y=camera.y, z=camera.z,
            yaw=camera.yaw, pitch=camera.pitch, roll=camera.roll, fov=camera.fov,
        )
        right_camera = CameraState(
            x=camera.x + ipd_offset, y=camera.y, z=camera.z,
            yaw=camera.yaw, pitch=camera.pitch, roll=camera.roll, fov=camera.fov,
        )

        left_img = self._render_eye(scene_type, left_camera, frame_num, hw, h, mesh_data)
        right_img = self._render_eye(scene_type, right_camera, frame_num, hw, h, mesh_data)

        if left_img is None or right_img is None:
            return None

        left_bytes = io.BytesIO()
        right_bytes = io.BytesIO()
        left_img.save(left_bytes, format="PNG", optimize=False)
        right_img.save(right_bytes, format="PNG", optimize=False)

        return VRFrame(
            left_eye=left_bytes.getvalue(),
            right_eye=right_bytes.getvalue(),
            width=w,
            height=h,
            timestamp=time.time(),
            frame_num=frame_num,
            camera=camera,
        )

    def render_single_frame(
        self,
        scene_type: str,
        camera: CameraState,
        frame_num: int = 0,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> Optional[bytes]:
        """Render a single eye view (for non-stereo displays)."""
        if not PILLOW_AVAILABLE or not NUMPY_AVAILABLE:
            return None

        w = width or self.width
        h = height or self.height
        img = self._render_eye(scene_type, camera, frame_num, w, h, None)
        if img is None:
            return None

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=False)
        return buf.getvalue()

    def _render_eye(
        self,
        scene_type: str,
        camera: CameraState,
        frame_num: int,
        w: int,
        h: int,
        mesh_data: Optional[Any],
    ) -> Optional[Image.Image]:
        """Render a single eye view."""
        preset = SCENE_PRESETS.get(scene_type, SCENE_PRESETS["planetary_surface"])
        img = Image.new("RGB", (w, h), preset["bg"])
        draw = ImageDraw.Draw(img)

        # Sky gradient
        self._draw_sky(draw, w, h, preset, camera)

        # Stars
        if preset.get("stars"):
            self._draw_stars(draw, w, h, scene_type, frame_num, camera)

        # Nebula
        if preset.get("nebula"):
            self._draw_nebula(img, w, h, scene_type, frame_num)

        # Ground/terrain
        if preset.get("ground_color"):
            self._draw_ground(draw, w, h, preset, camera, frame_num)

        # Objects
        self._draw_objects(draw, w, h, preset, camera, frame_num)

        # HUD overlay for cockpit
        if scene_type == "cockpit":
            self._draw_hud(draw, w, h, camera, frame_num)

        # Scanline effect (aerospace aesthetic)
        self._draw_scanlines(draw, w, h)

        # Vignette
        self._draw_vignette(img, w, h)

        return img

    def _draw_sky(self, draw, w, h, preset, camera):
        """Draw gradient sky."""
        sky = preset.get("sky_color", (10, 15, 30))
        horizon_y = int(h * preset.get("horizon_y", 0.5))
        for y in range(horizon_y):
            t = y / max(horizon_y, 1)
            r = int(sky[0] + t * 10)
            g = int(sky[1] + t * 12)
            b = int(sky[2] + t * 20)
            draw.line([(0, y), (w, y)], fill=(min(r, 255), min(g, 255), min(b, 255)))

    def _draw_stars(self, draw, w, h, scene_type, frame_num, camera):
        """Draw procedural starfield."""
        key = f"{scene_type}_{w}_{h}"
        if key not in self.stars_cache:
            rng = np.random.RandomState(self._star_seed)
            stars = []
            for _ in range(120):
                sx = rng.random() * w
                sy = rng.random() * h * 0.6
                brightness = rng.random() * 0.7 + 0.3
                size = rng.random() < 0.1 and 1.5 or 0.8
                stars.append((sx, sy, brightness, size))
            self.stars_cache[key] = stars

        t = frame_num * 0.02
        for sx, sy, brightness, size in self.stars:
            # Parallax: stars shift slightly with camera yaw
            px = (sx - camera.yaw * 0.5) % w
            flicker = brightness * (0.85 + 0.15 * np.sin(t + sx * 0.1))
            c = int(flicker * 200)
            if size > 1:
                draw.ellipse([px - 1, sy - 1, px + 1, sy + 1], fill=(c, c, min(c + 30, 255)))
            else:
                draw.point((px, sy), fill=(c, c, min(c + 20, 255)))

    @property
    def stars(self):
        """Lazy star access."""
        key = "default"
        if key not in self.stars_cache:
            rng = np.random.RandomState(self._star_seed)
            stars = []
            for _ in range(120):
                sx = rng.random()
                sy = rng.random() * 0.6
                brightness = rng.random() * 0.7 + 0.3
                size = 1.5 if rng.random() < 0.1 else 0.8
                stars.append((sx, sy, brightness, size))
            self.stars_cache[key] = stars
        return self.stars_cache[key]

    def _draw_nebula(self, img, w, h, scene_type, frame_num):
        """Draw subtle nebula glow."""
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        cx = w * (0.5 + 0.2 * np.sin(frame_num * 0.01))
        cy = h * 0.25
        for r in range(80, 0, -2):
            alpha = max(0, int(8 * (1 - r / 80)))
            color = (80, 40, 120, alpha) if scene_type != "landscape" else (40, 80, 60, alpha)
            od.ellipse([cx - r, cy - r * 0.6, cx + r, cy + r * 0.6], fill=color)
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

    def _draw_ground(self, draw, w, h, preset, camera, frame_num):
        """Draw ground plane with perspective."""
        gc = preset["ground_color"]
        horizon_y = int(h * preset.get("horizon_y", 0.5))
        for y in range(horizon_y, h):
            t = (y - horizon_y) / max(h - horizon_y, 1)
            r = int(gc[0] * (0.3 + 0.7 * t))
            g = int(gc[1] * (0.3 + 0.7 * t))
            b = int(gc[2] * (0.3 + 0.7 * t))
            draw.line([(0, y), (w, y)], fill=(min(r, 255), min(g, 255), min(b, 255)))

        # Grid lines for depth
        grid_color = (gc[0] // 2, gc[1] // 2, gc[2] // 2)
        for i in range(8):
            gy = horizon_y + int((h - horizon_y) * (i / 8) ** 1.5)
            if gy < h:
                draw.line([(0, gy), (w, gy)], fill=grid_color, width=1)
        for i in range(12):
            gx = int(w * ((i - 6) / 6) * 0.5 + w * 0.5 + camera.yaw * 0.3)
            if 0 <= gx <= w:
                draw.line([(gx, horizon_y), (gx + int(camera.yaw), h)], fill=grid_color, width=1)

    def _draw_objects(self, draw, w, h, preset, camera, frame_num):
        """Draw scene objects with parallax and animation."""
        horizon_y = int(h * preset.get("horizon_y", 0.5))
        t = frame_num * 0.03

        for obj in preset.get("objects", []):
            ox = int(obj["x"] * w - camera.yaw * 0.5)
            oy = int(obj["y"] * h)
            ow = int(obj["w"] * w)
            oh = int(obj["h"] * h)
            color = obj["color"]
            otype = obj["type"]

            if otype == "rocket":
                # Rocket body
                draw.polygon([
                    (ox, oy - oh // 2),
                    (ox - ow // 3, oy + oh // 2),
                    (ox + ow // 3, oy + oh // 2),
                ], fill=color)
                # Nose cone
                draw.polygon([
                    (ox, oy - oh // 2 - oh // 4),
                    (ox - ow // 4, oy - oh // 3),
                    (ox + ow // 4, oy - oh // 3),
                ], fill=(200, 60, 60))
                # Fins
                draw.polygon([
                    (ox - ow // 3, oy + oh // 3),
                    (ox - ow // 2, oy + oh // 2),
                    (ox - ow // 3, oy + oh // 2),
                ], fill=(150, 150, 160))
                draw.polygon([
                    (ox + ow // 3, oy + oh // 3),
                    (ox + ow // 2, oy + oh // 2),
                    (ox + ow // 3, oy + oh // 2),
                ], fill=(150, 150, 160))

            elif otype == "flame":
                # Animated flame
                flicker = 0.7 + 0.3 * np.sin(t * 5 + ox)
                fr = min(255, int(color[0] * flicker))
                fg = min(255, int(color[1] * flicker))
                fb = min(255, int(color[2] * flicker * 0.5))
                for i in range(3):
                    foff = int(oh * 0.3 * np.sin(t * 8 + i))
                    draw.ellipse([
                        ox - ow // 2 + foff, oy - oh // 4,
                        ox + ow // 2 + foff, oy + oh // 4
                    ], fill=(fr, fg, fb))

            elif otype == "habitat":
                # Dome habitat
                draw.ellipse([ox - ow // 2, oy - oh // 2, ox + ow // 2, oy + oh // 4], fill=color)
                draw.rectangle([ox - ow // 2, oy, ox + ow // 2, oy + oh // 3], fill=color)
                # Window
                draw.ellipse([ox - ow // 8, oy - oh // 6, ox + ow // 8, oy + oh // 12], fill=(100, 160, 200))

            elif otype == "module":
                # Space station module
                draw.rounded_rectangle([ox - ow // 2, oy - oh // 2, ox + ow // 2, oy + oh // 2],
                                       radius=4, fill=color)
                # Windows
                for wx in range(-2, 3):
                    draw.ellipse([ox + wx * ow // 6 - 3, oy - 3, ox + wx * ow // 6 + 3, oy + 3],
                                 fill=(100, 180, 220))

            elif otype == "solar_panel":
                draw.rectangle([ox - ow // 2, oy - oh // 2, ox + ow // 2, oy + oh // 2], fill=color)
                # Grid lines
                for i in range(4):
                    lx = ox - ow // 2 + i * ow // 4
                    draw.line([(lx, oy - oh // 2), (lx, oy + oh // 2)], fill=(30, 50, 100), width=1)

            elif otype == "antenna":
                draw.line([(ox, oy + oh // 2), (ox, oy - oh // 2)], fill=color, width=2)
                draw.ellipse([ox - 4, oy - oh // 2 - 4, ox + 4, oy - oh // 2 + 4], fill=(200, 60, 60))

            elif otype == "earth":
                draw.ellipse([ox - ow // 2, oy - oh // 2, ox + ow // 2, oy + oh // 2], fill=color)
                # Clouds
                cloud_x = int(ow * 0.2 * np.sin(t * 0.5))
                draw.ellipse([ox - ow // 3 + cloud_x, oy - oh // 4,
                              ox + ow // 6 + cloud_x, oy + oh // 8], fill=(200, 210, 230))

            elif otype == "mountain":
                draw.polygon([
                    (ox, oy - oh),
                    (ox - ow // 2, oy),
                    (ox + ow // 2, oy),
                ], fill=color)
                # Snow cap
                snow = (min(255, color[0] + 80), min(255, color[1] + 80), min(255, color[2] + 80))
                draw.polygon([
                    (ox, oy - oh),
                    (ox - ow // 6, oy - oh // 2),
                    (ox + ow // 6, oy - oh // 2),
                ], fill=snow)

            elif otype == "tree":
                draw.rectangle([ox - 2, oy, ox + 2, oy + oh // 3], fill=(80, 60, 40))
                draw.polygon([
                    (ox, oy - oh // 2),
                    (ox - ow // 2, oy + oh // 4),
                    (ox + ow // 2, oy + oh // 4),
                ], fill=color)

            elif otype == "rock":
                draw.ellipse([ox - ow // 2, oy - oh // 2, ox + ow // 2, oy + oh // 2], fill=color)

            elif otype == "crater":
                draw.ellipse([ox - ow // 2, oy - oh // 2, ox + ow // 2, oy + oh // 2], fill=color)
                rim = (min(255, color[0] + 15), min(255, color[1] + 15), min(255, color[2] + 15))
                draw.ellipse([ox - ow // 2 - 2, oy - oh // 2 - 1, ox + ow // 2 + 2, oy + oh // 2 + 1],
                             outline=rim, width=1)

            elif otype == "rover":
                draw.rectangle([ox - ow // 2, oy - oh // 4, ox + ow // 2, oy + oh // 4], fill=color)
                # Wheels
                draw.ellipse([ox - ow // 2 - 3, oy + oh // 6, ox - ow // 2 + 5, oy + oh // 3], fill=(60, 60, 60))
                draw.ellipse([ox + ow // 2 - 5, oy + oh // 6, ox + ow // 2 + 3, oy + oh // 3], fill=(60, 60, 60))
                # Mast
                draw.line([(ox, oy - oh // 4), (ox, oy - oh)], fill=(140, 140, 150), width=1)

            elif otype == "tower":
                draw.rectangle([ox - ow // 2, oy - oh // 2, ox + ow // 2, oy + oh // 2], fill=color)
                for i in range(3):
                    ty = oy - oh // 2 + i * oh // 3
                    draw.line([(ox - ow // 2, ty), (ox + ow // 2, ty)], fill=(80, 80, 90), width=1)

            elif otype == "hud_frame":
                # Cockpit frame
                draw.rounded_rectangle([ox - ow // 2, oy - oh // 2, ox + ow // 2, oy + oh // 2],
                                       radius=8, outline=(40, 60, 90), width=2)
                # Cross-hair
                draw.line([(ox - ow // 4, oy), (ox + ow // 4, oy)], fill=(0, 180, 120), width=1)
                draw.line([(ox, oy - oh // 4), (ox, oy + oh // 4)], fill=(0, 180, 120), width=1)

            elif otype == "display":
                draw.rectangle([ox - ow // 2, oy - oh // 2, ox + ow // 2, oy + oh // 2],
                               fill=(5, 10, 15), outline=color, width=1)
                # Fake data lines
                for i in range(4):
                    ly = oy - oh // 3 + i * oh // 5
                    lw = int(ow * 0.6 * (0.5 + 0.5 * np.sin(t + i)))
                    draw.line([(ox - lw // 2, ly), (ox + lw // 2, ly)],
                              fill=(color[0] // 2, color[1] // 2, color[2] // 2), width=1)

            else:
                draw.rectangle([ox - ow // 2, oy - oh // 2, ox + ow // 2, oy + oh // 2], fill=color)

    def _draw_hud(self, draw, w, h, camera, frame_num):
        """Draw cockpit HUD overlay."""
        t = frame_num * 0.05
        green = (0, 200, 140)

        # Altitude
        alt = 100 + 50 * np.sin(t * 0.1)
        draw.text((10, 10), f"ALT {alt:.0f}m", fill=green)
        # Speed
        spd = 250 + 30 * np.sin(t * 0.15)
        draw.text((10, 25), f"SPD {spd:.0f}m/s", fill=green)
        # Heading
        hdg = (camera.yaw * 10) % 360
        draw.text((10, 40), f"HDG {hdg:.0f}", fill=green)

        # Artificial horizon
        cx, cy = w // 2, h // 2 + 30
        draw.ellipse([cx - 50, cy - 50, cx + 50, cy + 50], outline=green, width=1)
        pitch_offset = int(camera.pitch * 0.5)
        draw.line([(cx - 40, cy + pitch_offset), (cx + 40, cy + pitch_offset)], fill=green, width=1)

        # Fuel bar
        fuel = max(0, 100 - (frame_num % 300) * 0.3)
        bar_w = 80
        draw.rectangle([w - bar_w - 10, 10, w - 10, 22], outline=green, width=1)
        fill_w = int(bar_w * fuel / 100)
        draw.rectangle([w - bar_w - 10, 10, w - bar_w - 10 + fill_w, 22], fill=green)
        draw.text((w - bar_w - 10, 24), f"FUEL {fuel:.0f}%", fill=green)

    def _draw_scanlines(self, draw, w, h):
        """Draw subtle scanline effect."""
        for y in range(0, h, 3):
            draw.line([(0, y), (w, y)], fill=(0, 0, 0), width=1)

    def _draw_vignette(self, img, w, h):
        """Draw vignette darkening at edges."""
        vignette = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vignette)
        cx, cy = w // 2, h // 2
        max_r = np.sqrt(cx ** 2 + cy ** 2)
        for i in range(20):
            r = max_r * (1 - i * 0.04)
            alpha = int(i * 3)
            vd.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 0, 0, alpha), width=int(max_r * 0.04))
        img.paste(Image.alpha_composite(img.convert("RGBA"), vignette).convert("RGB"))


# =============================================================================
# VR STREAM MANAGER — manages multiple client streams
# =============================================================================

class VRStreamManager:
    """Manages VR streaming sessions for multiple clients.

    Each client gets its own stream with independent camera state.
    Supports: VR headset (stereo), external display (mono), monitor (mono).
    """

    def __init__(self):
        self.renderer = VRStreamRenderer()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create_session(
        self,
        session_id: Optional[str] = None,
        scene_type: str = "planetary_surface",
        prompt: str = "",
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        fps: int = DEFAULT_FPS,
        stereo: bool = True,
    ) -> str:
        """Create a new streaming session. Returns session ID."""
        sid = session_id or uuid.uuid4().hex[:12]
        with self._lock:
            self.sessions[sid] = {
                "id": sid,
                "scene_type": scene_type,
                "prompt": prompt,
                "camera": CameraState(),
                "width": width,
                "height": height,
                "fps": fps,
                "stereo": stereo,
                "frame_num": 0,
                "created": time.time(),
                "clients": set(),
                "active": True,
            }
        logger.info(f"VR session created: {sid} ({scene_type}, {'stereo' if stereo else 'mono'})")
        return sid

    def update_camera(self, session_id: str, **kwargs) -> bool:
        """Update camera state for a session."""
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
            cam = session["camera"]
            for key, val in kwargs.items():
                if hasattr(cam, key):
                    setattr(cam, key, val)
            return True

    def render_frame(self, session_id: str) -> Optional[Dict]:
        """Render the next frame for a session. Returns base64 encoded frame(s)."""
        with self._lock:
            session = self.sessions.get(session_id)
            if not session or not session["active"]:
                return None

        cam = session["camera"]
        frame_num = session["frame_num"]
        scene = session["scene_type"]

        # Auto-rotate camera for orbit scenes
        preset = SCENE_PRESETS.get(scene, {})
        if frame_num > 0:
            cam.yaw += 0.5  # Slow auto-rotate

        if session["stereo"]:
            frame = self.renderer.render_stereo_frame(
                scene, cam, frame_num,
                width=session["width"], height=session["height"],
            )
            if frame is None:
                return None
            with self._lock:
                session["frame_num"] += 1
            return {
                "type": "stereo_frame",
                "left": base64.b64encode(frame.left_eye).decode(),
                "right": base64.b64encode(frame.right_eye).decode(),
                "width": frame.width,
                "height": frame.height,
                "frame": frame_num,
                "timestamp": frame.timestamp,
            }
        else:
            frame_bytes = self.renderer.render_single_frame(
                scene, cam, frame_num,
                width=session["width"], height=session["height"],
            )
            if frame_bytes is None:
                return None
            with self._lock:
                session["frame_num"] += 1
            return {
                "type": "frame",
                "data": base64.b64encode(frame_bytes).decode(),
                "width": session["width"],
                "height": session["height"],
                "frame": frame_num,
                "timestamp": time.time(),
            }

    def add_client(self, session_id: str, client_id: str) -> bool:
        """Register a client to a session."""
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session["clients"].add(client_id)
                return True
            return False

    def remove_client(self, session_id: str, client_id: str):
        """Remove a client from a session."""
        with self._lock:
            session = self.sessions.get(session_id)
            if session:
                session["clients"].discard(client_id)

    def close_session(self, session_id: str):
        """Close and clean up a session."""
        with self._lock:
            if session_id in self.sessions:
                self.sessions[session_id]["active"] = False
                del self.sessions[session_id]
                logger.info(f"VR session closed: {session_id}")

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session info."""
        with self._lock:
            s = self.sessions.get(session_id)
            if s:
                return {
                    "id": s["id"],
                    "scene_type": s["scene_type"],
                    "prompt": s["prompt"],
                    "width": s["width"],
                    "height": s["height"],
                    "fps": s["fps"],
                    "stereo": s["stereo"],
                    "frame_num": s["frame_num"],
                    "clients": len(s["clients"]),
                    "active": s["active"],
                }
            return None

    def list_sessions(self) -> List[Dict]:
        """List all active sessions."""
        with self._lock:
            return [
                {
                    "id": s["id"],
                    "scene_type": s["scene_type"],
                    "stereo": s["stereo"],
                    "frame_num": s["frame_num"],
                    "clients": len(s["clients"]),
                }
                for s in self.sessions.values() if s["active"]
            ]


# =============================================================================
# MODULE-LEVEL INSTANCE
# =============================================================================

vr_stream_manager = VRStreamManager()

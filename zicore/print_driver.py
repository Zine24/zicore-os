"""
ZICORE Print — Universal Printer Driver System

Provides abstraction over multiple printer protocols:
- Klipper (via Moonraker API)
- Marlin (via HTTP/Serial)
- OctoPrint (via REST API)
- Z1_Control (ESP32-S3 REST API for multi-filament)
- Generic HTTP printer
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger("zicore.print")

# ─── Printer Profile Database ────────────────────────────────────────────────

DEFAULT_PRINTERS = [
    {
        "id": "z1_corexy",
        "name": "Z1 CoreXY (Z1_Control)",
        "type": "z1_control",
        "driver": "z1_control",
        "icon": "&#128736;",
        "connection": {"host": "192.168.1.90", "port": 80, "stream_port": 81},
        "specs": {
            "build_volume": [235, 235, 250],
            "nozzle_diameter": 0.4,
            "filament_diameter": 1.75,
            "max_temp_hotend": 280,
            "max_temp_bed": 120,
            "max_speed": 300,
            "max_accel": 3000,
            "kinematics": "corexy",
            "firmware": "Klipper",
            "mcu": "MKS Tinybee (STM32F407)",
            "extruders": 1,
            "feeders": 4,
            "materials": ["PLA", "PETG", "ABS", "TPU"]
        },
        "status": "offline"
    },
    {
        "id": "ender3_klipper",
        "name": "Ender 3 (Klipper)",
        "type": "klipper",
        "driver": "klipper",
        "icon": "&#128736;",
        "connection": {"moonraker_url": "http://localhost:7125"},
        "specs": {
            "build_volume": [220, 220, 250],
            "nozzle_diameter": 0.4,
            "filament_diameter": 1.75,
            "max_temp_hotend": 260,
            "max_temp_bed": 110,
            "max_speed": 200,
            "max_accel": 2000,
            "kinematics": "bed_slinger",
            "firmware": "Klipper",
            "extruders": 1
        },
        "status": "offline"
    },
    {
        "id": "prusa_mk4",
        "name": "Prusa MK4 (OctoPrint)",
        "type": "octoprint",
        "driver": "octoprint",
        "icon": "&#128736;",
        "connection": {"host": "octopi.local", "port": 5000, "api_key": ""},
        "specs": {
            "build_volume": [250, 210, 220],
            "nozzle_diameter": 0.4,
            "filament_diameter": 1.75,
            "max_temp_hotend": 290,
            "max_temp_bed": 120,
            "max_speed": 200,
            "max_accel": 3000,
            "kinematics": "bed_slinger",
            "firmware": "Prusa firmware",
            "extruders": 1
        },
        "status": "offline"
    },
    {
        "id": "marlin_generic",
        "name": "Marlin Generic (HTTP)",
        "type": "marlin",
        "driver": "marlin",
        "icon": "&#128736;",
        "connection": {"host": "192.168.1.100", "port": 80},
        "specs": {
            "build_volume": [200, 200, 200],
            "nozzle_diameter": 0.4,
            "filament_diameter": 1.75,
            "max_temp_hotend": 250,
            "max_temp_bed": 100,
            "max_speed": 150,
            "max_accel": 1000,
            "firmware": "Marlin",
            "extruders": 1
        },
        "status": "offline"
    },
    {
        "id": "ender5_plus",
        "name": "Ender 5 Plus (Marlin)",
        "type": "marlin",
        "driver": "marlin",
        "icon": "&#128736;",
        "connection": {"host": "192.168.1.101", "port": 80},
        "specs": {
            "build_volume": [350, 350, 400],
            "nozzle_diameter": 0.4,
            "filament_diameter": 1.75,
            "max_temp_hotend": 260,
            "max_temp_bed": 110,
            "max_speed": 150,
            "max_accel": 1000,
            "firmware": "Marlin",
            "extruders": 1
        },
        "status": "offline"
    },
    {
        "id": "voron_24",
        "name": "Voron 2.4 (Klipper)",
        "type": "klipper",
        "driver": "klipper",
        "icon": "&#128736;",
        "connection": {"moonraker_url": "http://voron.local:7125"},
        "specs": {
            "build_volume": [350, 350, 340],
            "nozzle_diameter": 0.4,
            "filament_diameter": 1.75,
            "max_temp_hotend": 300,
            "max_temp_bed": 120,
            "max_speed": 400,
            "max_accel": 5000,
            "kinematics": "corexy",
            "firmware": "Klipper",
            "extruders": 1
        },
        "status": "offline"
    },
    {
        "id": "z2_ramps",
        "name": "Z2 REST (RAMPS + CNC Shield)",
        "type": "z2_rest",
        "driver": "z2_rest",
        "icon": "&#9881;",
        "connection": {"host": "192.168.1.100", "port": 80},
        "specs": {
            "build_volume": [220, 220, 250],
            "nozzle_diameter": 0.4,
            "filament_diameter": 1.75,
            "max_temp_hotend": 260,
            "max_temp_bed": 110,
            "max_speed": 200,
            "max_accel": 2000,
            "kinematics": "bed_slinger",
            "firmware": "Marlin (RAMPS)",
            "mcu": "ATmega2560 + RAMPS 1.4",
            "extruders": 1,
            "feeders": 4,
            "feeder_controller": "CNC Shield V3 (A4988 x4)",
            "materials": ["PLA", "PETG", "ABS", "TPU"]
        },
        "feeder_names": {
            "0": "PLA Blanco",
            "1": "PETG Negro",
            "2": "ABS Rojo",
            "3": "TPU Flexible"
        },
        "status": "offline"
    }
]

MATERIAL_DATABASE = [
    {"id": "pla", "name": "PLA", "color": "#00ff00", "temp_range": [180, 220], "bed_temp": [50, 60], "speed_mult": 1.0, "density": 1.24, "cost_kg": 20},
    {"id": "petg", "name": "PETG", "color": "#00aaff", "temp_range": [220, 250], "bed_temp": [70, 85], "speed_mult": 0.85, "density": 1.27, "cost_kg": 25},
    {"id": "abs", "name": "ABS", "color": "#ff6600", "temp_range": [220, 260], "bed_temp": [90, 110], "speed_mult": 0.9, "density": 1.04, "cost_kg": 22},
    {"id": "tpu", "name": "TPU", "color": "#ff00ff", "temp_range": [210, 230], "bed_temp": [40, 60], "speed_mult": 0.5, "density": 1.21, "cost_kg": 35},
    {"id": "nylon", "name": "Nylon (PA)", "color": "#ffff00", "temp_range": [240, 270], "bed_temp": [70, 90], "speed_mult": 0.7, "density": 1.14, "cost_kg": 40},
    {"id": "pc", "name": "Polycarbonate", "color": "#ffffff", "temp_range": [270, 310], "bed_temp": [100, 120], "speed_mult": 0.6, "density": 1.20, "cost_kg": 50},
    {"id": "asa", "name": "ASA", "color": "#cccccc", "temp_range": [235, 255], "bed_temp": [90, 110], "speed_mult": 0.85, "density": 1.07, "cost_kg": 28},
    {"id": "pva", "name": "PVA (Soluble)", "color": "#00ff88", "temp_range": [180, 210], "bed_temp": [45, 60], "speed_mult": 0.6, "density": 1.30, "cost_kg": 60},
]

# Purge matrix: mm of filament to purge when switching between materials
PURGE_MATRIX = {
    "pla":  {"pla": 8,  "petg": 22, "abs": 15, "tpu": 28, "nylon": 20, "pc": 25, "asa": 18, "pva": 10},
    "petg": {"pla": 22, "petg": 8,  "abs": 15, "tpu": 28, "nylon": 22, "pc": 28, "asa": 20, "pva": 12},
    "abs":  {"pla": 15, "petg": 15, "abs": 8,  "tpu": 22, "nylon": 18, "pc": 22, "asa": 15, "pva": 10},
    "tpu":  {"pla": 28, "petg": 28, "abs": 22, "tpu": 8,  "nylon": 25, "pc": 30, "asa": 24, "pva": 15},
    "nylon": {"pla": 20, "petg": 22, "abs": 18, "tpu": 25, "nylon": 10, "pc": 20, "asa": 18, "pva": 12},
    "pc":   {"pla": 25, "petg": 28, "abs": 22, "tpu": 30, "nylon": 20, "pc": 10, "asa": 22, "pva": 15},
    "asa":  {"pla": 18, "petg": 20, "abs": 15, "tpu": 24, "nylon": 18, "pc": 22, "asa": 8,  "pva": 12},
    "pva":  {"pla": 10, "petg": 12, "abs": 10, "tpu": 15, "nylon": 12, "pc": 15, "asa": 12, "pva": 5},
}


# ─── Base Driver ─────────────────────────────────────────────────────────────

class PrinterDriver:
    """Base class for printer drivers."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connected = False
        self.last_status = {}
        self.last_error = None

    async def connect(self) -> bool:
        raise NotImplementedError

    async def disconnect(self):
        self.connected = False

    async def get_status(self) -> Dict[str, Any]:
        raise NotImplementedError

    async def home(self, axes: str = "xyz") -> bool:
        raise NotImplementedError

    async def set_temperature(self, tool: int, temp: int) -> bool:
        raise NotImplementedError

    async def set_bed_temperature(self, temp: int) -> bool:
        raise NotImplementedError

    async def extrude(self, mm: int, speed: int = 100) -> bool:
        raise NotImplementedError

    async def retract(self, mm: int, speed: int = 100) -> bool:
        return await self.extrude(-mm, speed)

    async def move(self, x: float = None, y: float = None, z: float = None, speed: int = 100) -> bool:
        raise NotImplementedError

    async def fan_speed(self, speed: int) -> bool:
        raise NotImplementedError

    async def emergency_stop(self) -> bool:
        raise NotImplementedError

    async def start_print(self, filename: str) -> bool:
        raise NotImplementedError

    async def cancel_print(self) -> bool:
        raise NotImplementedError

    async def pause_print(self) -> bool:
        raise NotImplementedError

    async def resume_print(self) -> bool:
        raise NotImplementedError

    async def send_gcode(self, gcode: str) -> str:
        raise NotImplementedError

    async def get_files(self) -> List[Dict]:
        return []

    async def get_camera_url(self) -> Optional[str]:
        return None


# ─── Z1_Control Driver ──────────────────────────────────────────────────────

class Z1ControlDriver(PrinterDriver):
    """Driver for Z1_Control ESP32-S3 multi-filament system."""

    def __init__(self, config):
        super().__init__(config)
        self.host = config.get("connection", {}).get("host", "192.168.4.1")
        self.port = config.get("connection", {}).get("port", 80)
        self.stream_port = config.get("connection", {}).get("stream_port", 81)
        self.feeders = [{"position": 0, "active": False, "material": None} for _ in range(4)]

    async def _request(self, path: str, method: str = "GET", data: dict = None) -> Optional[dict]:
        try:
            import aiohttp
            url = f"http://{self.host}:{self.port}{path}"
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if method == "POST":
                    async with session.post(url, data=data) as resp:
                        text = await resp.text()
                        if resp.status == 200:
                            try:
                                return await resp.json()
                            except Exception:
                                logger.warning(f"Z1_Control JSON parse failed: {text[:200]}")
                        else:
                            logger.warning(f"Z1_Control HTTP {resp.status}: {text[:200]}")
                else:
                    async with session.get(url) as resp:
                        text = await resp.text()
                        if resp.status == 200:
                            try:
                                return await resp.json()
                            except Exception:
                                logger.warning(f"Z1_Control JSON parse failed: {text[:200]}")
                        else:
                            logger.warning(f"Z1_Control HTTP {resp.status}: {text[:200]}")
        except Exception as e:
            logger.warning(f"Z1_Control request failed: {type(e).__name__}: {e}")
            self.last_error = f"{type(e).__name__}: {e}"
        return None

    async def connect(self) -> bool:
        status = await self._request("/status")
        if status:
            self.connected = True
            self.last_status = status
            logger.info(f"Connected to Z1_Control at {self.host}")
            return True
        return False

    async def get_status(self) -> Dict[str, Any]:
        status = await self._request("/status")
        if status:
            self.last_status = status
            self.connected = True
            return {
                "connected": True,
                "printer": self.config.get("name", "Z1_Control"),
                "mode": "Z%d" % (status.get("mode", 0) + 1),
                "active_feeder": status.get("active", -1),
                "camera": status.get("camera", False),
                "moving": status.get("moving", False),
                "sta_ip": status.get("sta_ip", ""),
                "feeders": status.get("feeders", []),
            }
        return {"connected": False, "printer": self.config.get("name", "Z1_Control")}

    async def get_feeder_status(self) -> Dict[str, Any]:
        result = await self._request("/feeder/status")
        return result or {"moving": False}

    async def feeder_move(self, feeder: int, mm: float, speed: int = 400) -> bool:
        result = await self._request("/feeder", "POST", {"n": str(feeder), "mm": str(mm), "vel": str(speed)})
        if result and result.get("ok"):
            logger.info(f"Feeder {feeder}: moved {mm}mm at {speed}mm/s")
            return True
        return False

    async def set_mode(self, mode: int) -> bool:
        result = await self._request("/mode", "POST", {"mode": str(mode)})
        return result and result.get("ok")

    async def reset(self) -> bool:
        result = await self._request("/reset", "POST")
        return result and result.get("ok")

    async def get_camera_url(self) -> Optional[str]:
        return f"http://{self.host}:{self.stream_port}/stream"

    async def load_material(self, feeder: int, amount: float = 200) -> bool:
        return await self.feeder_move(feeder, amount, 200)

    async def unload_material(self, feeder: int, amount: float = -150) -> bool:
        return await self.feeder_move(feeder, amount, 200)

    async def emergency_stop(self) -> bool:
        result = await self._request("/stop", "POST")
        return result and result.get("ok")


# ─── Z2 REST Driver (RAMPS + CNC Shield) ───────────────────────────────────

class Z2RestDriver(PrinterDriver):
    """Driver for Z2 REST: RAMPS 1.4 + CNC Shield for multi-filament feeders.
    
    RAMPS handles: heaters, steppers X/Y/Z/E0, fans, bed
    CNC Shield handles: up to 4 feeder steppers (E1, E2, E3, E4 via A4988)
    
    Communication: REST API on ESP32/Arduino that bridges HTTP to GCode serial.
    """

    def __init__(self, config):
        super().__init__(config)
        self.host = config.get("connection", {}).get("host", "192.168.1.100")
        self.port = config.get("connection", {}).get("port", 80)
        self.feeders = [{"position": 0, "active": False, "material": None, "name": f"Feeder {i}"} for i in range(4)]
        self.active_feeder = -1
        self._feeder_names = config.get("feeder_names", {})

    async def _request(self, path: str, method: str = "GET", data: dict = None) -> Optional[dict]:
        try:
            import aiohttp
            url = f"http://{self.host}:{self.port}{path}"
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if method == "POST":
                    async with session.post(url, data=data) as resp:
                        text = await resp.text()
                        if resp.status == 200:
                            try:
                                return await resp.json()
                            except Exception:
                                return {"raw": text}
                        else:
                            logger.warning(f"Z2 REST HTTP {resp.status}: {text[:200]}")
                else:
                    async with session.get(url) as resp:
                        text = await resp.text()
                        if resp.status == 200:
                            try:
                                return await resp.json()
                            except Exception:
                                return {"raw": text}
        except Exception as e:
            logger.warning(f"Z2 REST request failed: {type(e).__name__}: {e}")
            self.last_error = f"{type(e).__name__}: {e}"
        return None

    async def connect(self) -> bool:
        status = await self._request("/status")
        if status:
            self.connected = True
            self.last_status = status
            logger.info(f"Connected to Z2 REST at {self.host}")
            return True
        return False

    async def get_status(self) -> Dict[str, Any]:
        status = await self._request("/status")
        if status:
            self.connected = True
            self.last_status = status
            return {
                "connected": True,
                "printer": self.config.get("name", "Z2 REST"),
                "mode": "Z2",
                "temperatures": {
                    "hotend": {"actual": status.get("hotend_temp", 0), "target": status.get("hotend_target", 0)},
                    "bed": {"actual": status.get("bed_temp", 0), "target": status.get("bed_target", 0)},
                },
                "active_feeder": status.get("active_feeder", self.active_feeder),
                "moving": status.get("moving", False),
                "feeders": self.feeders,
                "printing": status.get("printing", False),
                "state": status.get("state", "idle"),
            }
        return {"connected": False, "printer": self.config.get("name", "Z2 REST")}

    async def home(self, axes="xyz") -> bool:
        result = await self._request("/gcode", "POST", {"gcode": f"G28 {axes}"})
        return result is not None

    async def set_temperature(self, tool, temp) -> bool:
        gcode = f"M104 S{temp} T{tool}" if temp > 0 else "M104 S0"
        result = await self._request("/gcode", "POST", {"gcode": gcode})
        return result is not None

    async def set_bed_temperature(self, temp) -> bool:
        gcode = f"M140 S{temp}" if temp > 0 else "M140 S0"
        result = await self._request("/gcode", "POST", {"gcode": gcode})
        return result is not None

    async def extrude(self, mm=10, speed=100) -> bool:
        gcode = f"G1 E{mm} F{speed * 60}"
        result = await self._request("/gcode", "POST", {"gcode": gcode})
        return result is not None

    async def move(self, x=None, y=None, z=None, speed=100) -> bool:
        parts = ["G1"]
        if x is not None: parts.append(f"X{x}")
        if y is not None: parts.append(f"Y{y}")
        if z is not None: parts.append(f"Z{z}")
        parts.append(f"F{speed * 60}")
        result = await self._request("/gcode", "POST", {"gcode": " ".join(parts)})
        return result is not None

    async def fan_speed(self, speed) -> bool:
        val = max(0, min(255, int(speed * 2.55)))
        result = await self._request("/gcode", "POST", {"gcode": f"M106 S{val}"})
        return result is not None

    async def emergency_stop(self) -> bool:
        result = await self._request("/gcode", "POST", {"gcode": "M112"})
        return result is not None

    async def send_gcode(self, gcode) -> str:
        result = await self._request("/gcode", "POST", {"gcode": gcode})
        return result.get("response", "") if result else ""

    async def select_tool(self, tool: int) -> bool:
        """Select tool T0-T3. Sends GCode T{n} and activates corresponding feeder."""
        if tool < 0 or tool > 3:
            return False
        result = await self._request("/gcode", "POST", {"gcode": f"T{tool}"})
        if result:
            self.active_feeder = tool
            for i, f in enumerate(self.feeders):
                f["active"] = (i == tool)
            return True
        return False

    async def feeder_move(self, feeder: int, mm: float, speed: int = 200) -> bool:
        """Move feeder stepper via CNC Shield. Uses E1-E4 axis commands."""
        if feeder < 0 or feeder > 3:
            return False
        # CNC Shield: E1=Feeder0, E2=Feeder1, E3=Feeder2, E4=Feeder3
        # Map to GCode: use T{n} to select, then G1 E{mm}
        await self.select_tool(feeder)
        gcode = f"G1 E{mm} F{speed * 60}"
        result = await self._request("/gcode", "POST", {"gcode": gcode})
        if result:
            self.feeders[feeder]["position"] = self.feeders[feeder].get("position", 0) + mm
            return True
        return False

    def get_feeder_name(self, index: int) -> str:
        """Get custom name for a feeder."""
        return self._feeder_names.get(str(index), self.feeders[index].get("name", f"Feeder {index}"))

    def set_feeder_name(self, index: int, name: str):
        """Set custom name for a feeder."""
        self._feeder_names[str(index)] = name
        if index < len(self.feeders):
            self.feeders[index]["name"] = name


# ─── Klipper Driver (via Moonraker) ────────────────────────────────────────

class KlipperDriver(PrinterDriver):
    """Driver for Klipper printers via Moonraker API."""

    def __init__(self, config):
        super().__init__(config)
        self.moonraker_url = config.get("connection", {}).get("moonraker_url", "http://localhost:7125")
        self.websocket = None
        self._printer_state = {}

    async def _request(self, path: str, method: str = "GET", data: dict = None) -> Optional[dict]:
        try:
            import aiohttp
            url = f"{self.moonraker_url}{path}"
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if method == "POST":
                    async with session.post(url, json=data) as resp:
                        return await resp.json() if resp.status == 200 else None
                else:
                    async with session.get(url) as resp:
                        return await resp.json() if resp.status == 200 else None
        except Exception as e:
            logger.warning(f"Moonraker request failed: {e}")
            self.last_error = str(e)
        return None

    async def connect(self) -> bool:
        info = await self._request("/server/info")
        if info:
            self.connected = True
            logger.info(f"Connected to Moonraker at {self.moonraker_url}")
            return True
        return False

    async def get_status(self) -> Dict[str, Any]:
        printer = await self._request("/printer/objects/query?heater_bed&extruder&print_stats&motion_report")
        if not printer:
            return {"connected": False}

        status = printer.get("status", {})
        extruder = status.get("extruder", {})
        bed = status.get("heater_bed", {})
        print_stats = status.get("print_stats", {})
        motion = status.get("motion_report", {})

        return {
            "connected": True,
            "printer": self.config.get("name", "Klipper"),
            "temperatures": {
                "hotend": {"actual": extruder.get("temperature", 0), "target": extruder.get("target", 0)},
                "bed": {"actual": bed.get("temperature", 0), "target": bed.get("target", 0)},
            },
            "printing": print_stats.get("state", "") in ("printing", "paused"),
            "state": print_stats.get("state", "standby"),
            "progress": print_stats.get("progress", 0) * 100,
            "filename": print_stats.get("filename", ""),
            "position": motion.get("live_position", [0, 0, 0]),
            "print_time": print_stats.get("print_duration", 0),
            "total_duration": print_stats.get("total_duration", 0),
            "filament_used": print_stats.get("filament_used", 0),
        }

    async def home(self, axes="xyz") -> bool:
        return bool(await self._request("/printer/gcode/script", "POST", {"script": f"G28 {axes}"}))

    async def set_temperature(self, tool, temp) -> bool:
        cmd = f"M104 S{temp} T{tool}" if temp > 0 else "M104 S0"
        return bool(await self._request("/printer/gcode/script", "POST", {"script": cmd}))

    async def set_bed_temperature(self, temp) -> bool:
        cmd = f"M140 S{temp}" if temp > 0 else "M140 S0"
        return bool(await self._request("/printer/gcode/script", "POST", {"script": cmd}))

    async def extrude(self, mm, speed=100) -> bool:
        return bool(await self._request("/printer/gcode/script", "POST", {"script": f"G1 E{mm} F{speed * 60}"}))

    async def move(self, x=None, y=None, z=None, speed=100) -> bool:
        parts = ["G1"]
        if x is not None: parts.append(f"X{x}")
        if y is not None: parts.append(f"Y{y}")
        if z is not None: parts.append(f"Z{z}")
        parts.append(f"F{speed * 60}")
        return bool(await self._request("/printer/gcode/script", "POST", {"script": " ".join(parts)}))

    async def fan_speed(self, speed) -> bool:
        return bool(await self._request("/printer/gcode/script", "POST", {"script": f"M106 S{int(speed * 255)}"}))

    async def emergency_stop(self) -> bool:
        return bool(await self._request("/printer/emergency_stop", "POST"))

    async def start_print(self, filename) -> bool:
        return bool(await self._request("/printer/print/start", "POST", {"filename": filename}))

    async def cancel_print(self) -> bool:
        return bool(await self._request("/printer/print/cancel", "POST"))

    async def pause_print(self) -> bool:
        return bool(await self._request("/printer/print/pause", "POST"))

    async def resume_print(self) -> bool:
        return bool(await self._request("/printer/print/resume", "POST"))

    async def send_gcode(self, gcode) -> str:
        result = await self._request("/printer/gcode/script", "POST", {"script": gcode})
        return str(result) if result else ""

    async def get_files(self) -> List[Dict]:
        result = await self._request("/server/files/list")
        return result.get("files", []) if result else []


# ─── OctoPrint Driver ──────────────────────────────────────────────────────

class OctoPrintDriver(PrinterDriver):
    """Driver for OctoPrint API."""

    def __init__(self, config):
        super().__init__(config)
        self.host = config.get("connection", {}).get("host", "octopi.local")
        self.port = config.get("connection", {}).get("port", 5000)
        self.api_key = config.get("connection", {}).get("api_key", "")
        self.base_url = f"http://{self.host}:{self.port}/api"

    async def _request(self, path: str, method: str = "GET", data: dict = None) -> Optional[dict]:
        try:
            import aiohttp
            url = f"{self.base_url}{path}"
            headers = {"X-Api-Key": self.api_key}
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                if method == "POST":
                    async with session.post(url, json=data) as resp:
                        return await resp.json() if resp.status == 200 else None
                else:
                    async with session.get(url) as resp:
                        return await resp.json() if resp.status in (200, 409) else None
        except Exception as e:
            logger.warning(f"OctoPrint request failed: {e}")
            self.last_error = str(e)
        return None

    async def connect(self) -> bool:
        info = await self._request("/version")
        if info:
            self.connected = True
            logger.info(f"Connected to OctoPrint at {self.host}")
            return True
        return False

    async def get_status(self) -> Dict[str, Any]:
        printer = await self._request("/printer")
        job = await self._request("/job")
        if not printer:
            return {"connected": False}

        temps = printer.get("temperature", {})
        return {
            "connected": True,
            "printer": self.config.get("name", "OctoPrint"),
            "temperatures": {
                "hotend": {"actual": temps.get("tool0", {}).get("actual", 0), "target": temps.get("tool0", {}).get("target", 0)},
                "bed": {"actual": temps.get("bed", {}).get("actual", 0), "target": temps.get("bed", {}).get("target", 0)},
            },
            "printing": job.get("state") == "Printing",
            "state": job.get("state", "Unknown"),
            "progress": job.get("progress", {}).get("completion", 0) or 0,
            "filename": job.get("job", {}).get("file", {}).get("name", ""),
        }

    async def home(self, axes="xyz") -> bool:
        axis_map = {"x": "x", "y": "y", "z": "z", "xyz": "xyz"}
        return bool(await self._request("/printer/printhead", "POST", {"command": "home", "axes": list(axes)}))

    async def set_temperature(self, tool, temp) -> bool:
        return bool(await self._request("/printer/tool", "POST", {"command": "target", "targets": {f"tool{tool}": temp}}))

    async def set_bed_temperature(self, temp) -> bool:
        return bool(await self._request("/printer/bed", "POST", {"command": "target", "target": temp}))

    async def extrude(self, mm, speed=100) -> bool:
        return bool(await self._request("/printer/tool", "POST", {"command": "extrude", "amount": mm, "speed": speed}))

    async def emergency_stop(self) -> bool:
        return bool(await self._request("/connection", "POST", {"command": "disconnect"}))

    async def start_print(self, filename) -> bool:
        return bool(await self._request("/files/local/" + filename, "POST", {"command": "select", "print": True}))

    async def cancel_print(self) -> bool:
        return bool(await self._request("/job", "POST", {"command": "cancel"}))

    async def pause_print(self) -> bool:
        return bool(await self._request("/job", "POST", {"command": "pause", "action": "toggle"}))

    async def get_files(self) -> List[Dict]:
        result = await self._request("/files")
        files = []
        for item in result.get("files", []):
            files.append({"name": item.get("name"), "size": item.get("size"), "date": item.get("date")})
        return files

    async def get_camera_url(self) -> Optional[str]:
        return f"http://{self.host}:{self.port}/webcam/?action=stream"


# ─── Marlin Driver ──────────────────────────────────────────────────────────

class MarlinDriver(PrinterDriver):
    """Driver for Marlin printers with HTTP API (e.g., ESP3D, OctoESP)."""

    def __init__(self, config):
        super().__init__(config)
        self.host = config.get("connection", {}).get("host", "192.168.1.100")
        self.port = config.get("connection", {}).get("port", 80)
        self.base_url = f"http://{self.host}:{self.port}"

    async def _request(self, path: str) -> Optional[dict]:
        try:
            import aiohttp
            url = f"{self.base_url}{path}"
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        ct = resp.headers.get("Content-Type", "")
                        if "json" in ct:
                            return await resp.json()
                        return {"text": await resp.text()}
        except Exception as e:
            logger.warning(f"Marlin request failed: {e}")
            self.last_error = str(e)
        return None

    async def connect(self) -> bool:
        result = await self._request("/M115")
        if result:
            self.connected = True
            logger.info(f"Connected to Marlin at {self.host}")
            return True
        return False

    async def get_status(self) -> Dict[str, Any]:
        temp = await self._request("/M105")
        progress = await self._request("/M27")
        return {
            "connected": self.connected,
            "printer": self.config.get("name", "Marlin"),
            "temperatures": self._parse_temps(temp),
            "progress": self._parse_progress(progress),
        }

    def _parse_temps(self, data) -> dict:
        if not data:
            return {}
        text = data.get("text", "")
        result = {}
        if "T:" in text:
            parts = text.split("T:")[1].split(" ")
            try:
                result["hotend"] = {"actual": float(parts[0]), "target": float(parts[1].replace("B:", ""))}
            except (ValueError, IndexError):
                pass
        if "B:" in text:
            parts = text.split("B:")[1].split(" ")
            try:
                result["bed"] = {"actual": float(parts[0]), "target": float(parts[1]) if len(parts) > 1 else 0}
            except (ValueError, IndexError):
                pass
        return result

    def _parse_progress(self, data) -> float:
        if not data:
            return 0
        text = data.get("text", "")
        if "SD printing byte" in text:
            parts = text.split("/")
            if len(parts) == 2:
                try:
                    current = int(parts[0].split()[-1])
                    total = int(parts[1].strip().replace("\n", ""))
                    return (current / total * 100) if total > 0 else 0
                except (ValueError, IndexError):
                    pass
        return 0

    async def emergency_stop(self) -> bool:
        return bool(await self._request("/M112"))

    async def get_camera_url(self) -> Optional[str]:
        return f"http://{self.host}:8080/?action=stream"


# ─── Driver Factory ─────────────────────────────────────────────────────────

DRIVER_MAP = {
    "z1_control": Z1ControlDriver,
    "klipper": KlipperDriver,
    "octoprint": OctoPrintDriver,
    "marlin": MarlinDriver,
}


def create_driver(printer_config: Dict[str, Any]) -> PrinterDriver:
    driver_type = printer_config.get("driver", "klipper")
    cls = DRIVER_MAP.get(driver_type, PrinterDriver)
    return cls(printer_config)


class PrintManager:
    """Manages all connected printers and driver instances."""

    def __init__(self):
        self.printers: Dict[str, Dict] = {}
        self.drivers: Dict[str, PrinterDriver] = {}
        self.print_history: List[Dict] = []
        self._load_config()

    def _load_config(self):
        config_file = Path(__file__).parent.parent / "data" / "config" / "printers.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    data = json.load(f)
                    self.printers = {p["id"]: p for p in data.get("printers", DEFAULT_PRINTERS)}
            except Exception:
                pass
        if not self.printers:
            self.printers = {p["id"]: p for p in DEFAULT_PRINTERS}
        self._save_config()

    def _save_config(self):
        config_file = Path(__file__).parent.parent / "data" / "config" / "printers.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w") as f:
            json.dump({"printers": list(self.printers.values())}, f, indent=2)

    async def connect_printer(self, printer_id: str) -> bool:
        config = self.printers.get(printer_id)
        if not config:
            return False
        driver = create_driver(config)
        if await driver.connect():
            self.drivers[printer_id] = driver
            config["status"] = "online"
            self._save_config()
            return True
        config["status"] = "error"
        return False

    async def disconnect_printer(self, printer_id: str):
        driver = self.drivers.get(printer_id)
        if driver:
            await driver.disconnect()
            del self.drivers[printer_id]
        if printer_id in self.printers:
            self.printers[printer_id]["status"] = "offline"

    async def get_printer_status(self, printer_id: str) -> Dict[str, Any]:
        driver = self.drivers.get(printer_id)
        if driver:
            return await driver.get_status()
        config = self.printers.get(printer_id, {})
        return {"connected": False, "printer": config.get("name", "Unknown"), "status": config.get("status", "offline")}

    async def get_all_status(self) -> List[Dict]:
        results = []
        for pid, config in self.printers.items():
            status = await self.get_printer_status(pid)
            status["id"] = pid
            status["config"] = config
            results.append(status)
        return results

    def get_materials(self) -> List[Dict]:
        return MATERIAL_DATABASE

    def get_purge_amount(self, from_mat: str, to_mat: str) -> int:
        return PURGE_MATRIX.get(from_mat, {}).get(to_mat, 15)


print_manager = PrintManager()

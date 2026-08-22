"""
ZICORE System - SSH Integration Module (Cross-platform)
Provides SSH server management and remote shell access via web API.
Signed by ZineMotion
"""
from __future__ import annotations
import subprocess
import os
import sys
import json
import shutil
from pathlib import Path


def _get_platform():
    return sys.platform


class SSHManager:
    """Manages OpenSSH server and remote shell sessions (cross-platform)."""

    def __init__(self):
        self.ssh_port = 22
        self.ssh_host = "127.0.0.1"
        self._server_running = False
        self._check_server_status()

    def _check_server_status(self):
        platform = _get_platform()
        try:
            if platform == "win32":
                result = subprocess.run(
                    ["sc", "query", "sshd"],
                    capture_output=True, text=True, timeout=5
                )
                self._server_running = "RUNNING" in result.stdout
            else:
                result = subprocess.run(
                    ["systemctl", "is-active", "sshd"],
                    capture_output=True, text=True, timeout=5
                )
                self._server_running = result.stdout.strip() == "active"
        except Exception:
            self._server_running = False

    def get_status(self) -> dict:
        self._check_server_status()
        platform = _get_platform()
        if platform == "win32":
            config_path = r"C:\ProgramData\ssh\sshd_config"
        elif platform == "darwin":
            config_path = "/etc/ssh/sshd_config"
        else:
            config_path = "/etc/ssh/sshd_config"
        return {
            "running": self._server_running,
            "port": self.ssh_port,
            "host": self.ssh_host,
            "service": "sshd",
            "config_path": config_path,
            "platform": platform,
        }

    def start_server(self) -> dict:
        platform = _get_platform()
        try:
            if platform == "win32":
                result = subprocess.run(
                    ["net", "start", "sshd"],
                    capture_output=True, text=True, timeout=10
                )
            else:
                result = subprocess.run(
                    ["sudo", "systemctl", "start", "sshd"],
                    capture_output=True, text=True, timeout=10
                )
            self._server_running = result.returncode == 0
            return {"success": result.returncode == 0, "message": "SSH server started", "output": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_server(self) -> dict:
        platform = _get_platform()
        try:
            if platform == "win32":
                result = subprocess.run(
                    ["net", "stop", "sshd"],
                    capture_output=True, text=True, timeout=10
                )
            else:
                result = subprocess.run(
                    ["sudo", "systemctl", "stop", "sshd"],
                    capture_output=True, text=True, timeout=10
                )
            self._server_running = False
            return {"success": True, "message": "SSH server stopped", "output": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_connected_sessions(self) -> list:
        sessions = []
        try:
            if _get_platform() == "win32":
                result = subprocess.run(
                    ["netstat", "-an"],
                    capture_output=True, text=True, timeout=5
                )
            else:
                result = subprocess.run(
                    ["ss", "-tn"],
                    capture_output=True, text=True, timeout=5
                )
            for line in result.stdout.splitlines():
                if f":{self.ssh_port}" in line and "ESTABLISHED" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        remote = parts[2] if _get_platform() == "win32" else parts[4]
                        sessions.append({"remote": remote, "status": "ESTABLISHED"})
        except Exception:
            pass
        return sessions

    def execute_command(self, command: str, timeout: int = 30) -> dict:
        try:
            import shlex
            platform = _get_platform()
            if platform == "win32":
                result = subprocess.run(
                    command, capture_output=True, text=True,
                    timeout=timeout, shell=True
                )
            else:
                result = subprocess.run(
                    shlex.split(command), capture_output=True, text=True,
                    timeout=timeout
                )
            return {
                "success": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_config(self) -> dict:
        config = {}
        platform = _get_platform()
        if platform == "win32":
            config_path = r"C:\ProgramData\ssh\sshd_config"
        else:
            config_path = "/etc/ssh/sshd_config"
        try:
            with open(config_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split(None, 1)
                        if len(parts) == 2:
                            config[parts[0]] = parts[1]
        except FileNotFoundError:
            config["error"] = "sshd_config not found"
        except PermissionError:
            config["error"] = "Permission denied - run as admin/root"
        return config


class FirefoxIntegration:
    """Launch and manage Firefox browser instances (cross-platform)."""

    def __init__(self):
        self.firefox_path = self._find_firefox()

    def _find_firefox(self) -> str | None:
        # Check PATH first
        in_path = shutil.which("firefox") or shutil.which("firefox.exe")
        if in_path:
            return in_path

        # Platform-specific paths
        platform = _get_platform()
        candidates = []
        if platform == "darwin":
            candidates = [
                "/Applications/Firefox.app/Contents/MacOS/firefox",
                str(Path.home() / "Applications" / "Firefox.app" / "Contents" / "MacOS" / "firefox"),
            ]
        elif platform.startswith("linux"):
            candidates = [
                "/usr/bin/firefox",
                "/usr/local/bin/firefox",
                "/snap/bin/firefox",
                "/usr/bin/firefox-esr",
            ]
        elif platform == "win32":
            candidates = [
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
            ]

        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def get_status(self) -> dict:
        return {
            "installed": self.firefox_path is not None,
            "path": self.firefox_path,
            "version": self._get_version(),
            "platform": _get_platform(),
        }

    def _get_version(self) -> str:
        if not self.firefox_path:
            return "not installed"
        try:
            result = subprocess.run(
                [self.firefox_path, "--version"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def open_url(self, url: str) -> dict:
        if not self.firefox_path:
            return {"success": False, "error": "Firefox not installed"}
        try:
            subprocess.Popen([self.firefox_path, url])
            return {"success": True, "message": f"Opened {url} in Firefox"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_file(self, file_path: str) -> dict:
        if not self.firefox_path:
            return {"success": False, "error": "Firefox not installed"}
        try:
            subprocess.Popen([self.firefox_path, file_path])
            return {"success": True, "message": f"Opened {file_path} in Firefox"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class ThunderbirdIntegration:
    """Launch and manage Thunderbird email client (cross-platform)."""

    def __init__(self):
        self.thunderbird_path = self._find_thunderbird()

    def _find_thunderbird(self) -> str | None:
        in_path = shutil.which("thunderbird") or shutil.which("thunderbird.exe")
        if in_path:
            return in_path

        platform = _get_platform()
        candidates = []
        if platform == "darwin":
            candidates = [
                "/Applications/Thunderbird.app/Contents/MacOS/thunderbird",
            ]
        elif platform.startswith("linux"):
            candidates = [
                "/usr/bin/thunderbird",
                "/usr/local/bin/thunderbird",
                "/snap/bin/thunderbird",
            ]
        elif platform == "win32":
            candidates = [
                r"C:\Program Files\Mozilla Thunderbird\thunderbird.exe",
                r"C:\Program Files (x86)\Mozilla Thunderbird\thunderbird.exe",
            ]

        for path in candidates:
            if os.path.exists(path):
                return path
        return None

    def get_status(self) -> dict:
        return {
            "installed": self.thunderbird_path is not None,
            "path": self.thunderbird_path,
            "version": self._get_version(),
            "platform": _get_platform(),
        }

    def _get_version(self) -> str:
        if not self.thunderbird_path:
            return "not installed"
        try:
            result = subprocess.run(
                [self.thunderbird_path, "--version"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"

    def open(self) -> dict:
        if not self.thunderbird_path:
            return {"success": False, "error": "Thunderbird not installed"}
        try:
            subprocess.Popen([self.thunderbird_path])
            return {"success": True, "message": "Thunderbird opened"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def open_compose(self, to: str = "", subject: str = "", body: str = "") -> dict:
        if not self.thunderbird_path:
            return {"success": False, "error": "Thunderbird not installed"}
        try:
            args = [self.thunderbird_path]
            if to:
                args.append(f"mailto:{to}")
                if subject:
                    args[-1] += f"?subject={subject}"
                    if body:
                        args[-1] += f"&body={body}"
            subprocess.Popen(args)
            return {"success": True, "message": f"Compose email to {to}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

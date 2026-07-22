"""
ZICORE Ollama Service - Cross-platform.
Runs via Docker container by default. Falls back to native binary.
Signed by ZineMotion
"""
import os
import sys
import json
import shutil
import subprocess
import urllib.request
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools" / "ollama"
DATA_DIR = ROOT / "data" / "ollama" / "models"
DEFAULT_HOST = "127.0.0.1:11434"
DOCKER_CONTAINER = "zicore-ollama"


def _get_platform():
    """Detect platform: 'linux', 'darwin', 'windows'."""
    return sys.platform


def _find_ollama_binary():
    """Find native ollama binary: tools/ > PATH > default installs."""
    # Check tools dir (cross-platform)
    bin_names = ["ollama.exe", "ollama"]
    for name in bin_names:
        p = TOOLS_DIR / name
        if p.exists():
            return str(p)

    # Check PATH
    in_path = shutil.which("ollama")
    if in_path:
        return in_path

    # Check common install locations
    platform = _get_platform()
    candidates = []
    if platform == "darwin":
        candidates = [
            Path.home() / "bin" / "ollama",
            Path("/usr/local/bin/ollama"),
            Path("/opt/homebrew/bin/ollama"),
        ]
    elif platform.startswith("linux"):
        candidates = [
            Path("/usr/local/bin/ollama"),
            Path("/usr/bin/ollama"),
            Path.home() / "bin" / "ollama",
        ]
    elif platform == "win32":
        local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
        candidates = [local]

    for c in candidates:
        if c.exists():
            return str(c)

    return None


def _get_env():
    """Get environment with OLLAMA_MODELS set."""
    env = os.environ.copy()
    env["OLLAMA_MODELS"] = str(DATA_DIR)
    env["OLLAMA_HOST"] = DEFAULT_HOST
    env["OLLAMA_KEEP_ALIVE"] = "5m"
    return env


def _has_docker():
    """Check if Docker is available."""
    return shutil.which("docker") is not None


def _docker_compose_cmd(args):
    """Run docker compose command."""
    compose_file = ROOT / "docker-compose.yml"
    cmd = ["docker", "compose", "-f", str(compose_file)] + args
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        # Try docker-compose standalone
        cmd = ["docker-compose"] + args
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except Exception as e:
            return subprocess.CompletedProcess(args, 1, stderr=str(e))


def status(base_url=None):
    """Check if Ollama is running (Docker or native)."""
    raw = base_url or DEFAULT_HOST
    scheme = "http"
    host = raw
    if raw.startswith("https://"):
        scheme = "https"
        host = raw[8:]
    elif raw.startswith("http://"):
        scheme = "http"
        host = raw[7:]
    try:
        url = f"{scheme}://{host}/api/tags"
        req = urllib.request.Request(url, method="GET", headers={"User-Agent": "ZICORE/5.0"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        models = [m.get("name", "unknown") for m in data.get("models", [])]
        mode = "docker" if _is_docker_running() else "native"
        return {"status": "online", "host": host, "models": models, "mode": mode}
    except Exception:
        return {"status": "offline", "host": host}


def _is_docker_running():
    """Check if Ollama Docker container is running."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", DOCKER_CONTAINER],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() == "true"
    except Exception:
        return False


def start():
    """Start Ollama - prefer Docker container, fallback to native."""
    current = status()
    if current["status"] == "online":
        return current

    # Try Docker first (cross-platform)
    if _has_docker():
        r = _docker_compose_cmd(["up", "-d", "ollama"])
        if r.returncode == 0:
            for _ in range(20):
                time.sleep(1)
                if status()["status"] == "online":
                    return {"status": "started", "mode": "docker", "host": DEFAULT_HOST}

    # Fallback to native binary
    binary = _find_ollama_binary()
    if not binary:
        return {
            "status": "error",
            "error": "Ollama not found. Install Docker or download binary.",
            "hint": "https://ollama.com/download"
        }

    try:
        platform = _get_platform()
        kwargs = {"env": _get_env(), "stdout": subprocess.PIPE, "stderr": subprocess.PIPE}
        if platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        proc = subprocess.Popen([binary, "serve"], **kwargs)

        for _ in range(15):
            time.sleep(1)
            if status()["status"] == "online":
                return {"status": "started", "pid": proc.pid, "mode": "native", "host": DEFAULT_HOST}

        return {"status": "error", "error": "Ollama failed to start within 15 seconds"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def stop():
    """Stop Ollama - both Docker and native."""
    # Stop Docker container
    if _has_docker() and _is_docker_running():
        _docker_compose_cmd(["stop", "ollama"])

    # Kill native process
    platform = _get_platform()
    try:
        if platform == "win32":
            subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], capture_output=True)
        else:
            subprocess.run(["pkill", "-f", "ollama serve"], capture_output=True)
        return {"status": "stopped"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def pull_model(model="tinyllama"):
    """Pull a model."""
    # Try Docker first
    if _has_docker() and _is_docker_running():
        r = _docker_compose_cmd(["exec", "ollama", "ollama", "pull", model])
        return {"status": "ok" if r.returncode == 0 else "error", "output": r.stdout, "error": r.stderr}

    # Native fallback
    binary = _find_ollama_binary()
    if not binary:
        return {"status": "error", "error": "Ollama not found"}

    result = subprocess.run(
        [binary, "pull", model],
        env=_get_env(),
        capture_output=True,
        text=True,
        timeout=600,
    )
    return {"status": "ok" if result.returncode == 0 else "error", "output": result.stdout, "error": result.stderr}


def list_models():
    """List downloaded models."""
    s = status()
    return s.get("models", [])


def chat(model, prompt, base_url=None):
    """Send chat request."""
    host = base_url or DEFAULT_HOST
    try:
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }).encode()
        req = urllib.request.Request(
            f"http://{host}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=120)
        data = json.loads(resp.read())
        return {"status": "ok", "response": data.get("message", {}).get("content", "")}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def setup():
    """Ensure Ollama is available - prefer Docker."""
    if status()["status"] == "online":
        return {"status": "ok", "mode": "running"}

    if _has_docker():
        return start()

    binary = _find_ollama_binary()
    if binary:
        return {"status": "ok", "binary": binary, "mode": "native"}

    return {
        "status": "error",
        "error": "Neither Docker nor Ollama found",
        "hint": "Install Docker Desktop or download ollama from https://ollama.com/download"
    }

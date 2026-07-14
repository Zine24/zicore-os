"""
ZICORE System Launcher v5.0
ZineMotion Foundation - Aerospace Division
Starts API, Web, Ollama (native/Docker), and auto-loads all generators.
"""
import sys
import os
import subprocess
import time
import webbrowser
import urllib.request
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
API_PORT = 4080
WEB_PORT = 4000

MISSION_MODULES = [
    "zihab", "zinav", "zipower", "ziship", "zidrone", "zirobot",
    "zicomm", "zieco", "zimed", "zicorex", "zilink", "zivr", "zisec",
    "zicriogen", "zimaury", "zty", "gpdengine"
]


def progress(value, max_val, width=25):
    filled = int(width * value / max_val)
    bar = "=" * filled + "-" * (width - filled)
    pct = int(value * 100 / max_val)
    return f"[{bar}] {pct}%"


def check_url(name, url):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            if 200 <= resp.status < 300:
                print(f"  [OK] {name}: {url}")
                return True
    except Exception:
        pass
    print(f"  [--] {name}: starting...")
    return False


def has_docker():
    return shutil.which("docker") is not None


def has_docker_compose():
    if shutil.which("docker-compose"):
        return True
    try:
        r = subprocess.run(["docker", "compose", "version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


def docker_compose_cmd(args):
    try:
        r = subprocess.run(["docker-compose"] + args, cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        return r
    except FileNotFoundError:
        try:
            r = subprocess.run(["docker", "compose"] + args, cwd=str(ROOT), capture_output=True, text=True, timeout=120)
            return r
        except Exception as e:
            return subprocess.CompletedProcess(args, 1, stderr=str(e))


def start_native_ollama():
    """Start Ollama server natively with correct environment."""
    sys.path.insert(0, str(ROOT))
    from zicore import ollama_service

    current = ollama_service.status()
    if current["status"] == "online":
        print(f"  [OK] Ollama already running ({len(current['models'])} models)")
        return True

    print("  Starting Ollama server...")
    result = ollama_service.start()
    if result["status"] == "started":
        print(f"  [OK] Ollama started (PID: {result.get('pid')})")
        return True
    else:
        print(f"  [--] Ollama not available: {result.get('error', 'not installed')}")
        print("       System works without AI — install Docker or Ollama for AI features")
        return False


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    use_docker = "--docker" in sys.argv or mode == "docker"

    print()
    print("=" * 60)
    print("  ZICORE SYSTEM v5.0 - ZineMotion Foundation")
    print("  Aerospace Division - Inference Platform")
    print("=" * 60)

    procs = []

    # ── OLLAMA SERVER ─────────────────────────────────────────────────
    print()
    print("[1/5] Ollama Server")

    # Always prefer Docker container (cross-platform, no OS dependency)
    if has_docker() and has_docker_compose():
        print("  Starting Ollama via Docker container...")
        r = docker_compose_cmd(["up", "-d", "ollama"])
        if r.returncode == 0:
            print("  [OK] Ollama Docker container started")
            print("       URL: http://localhost:11434")
        else:
            print(f"  [--] Docker Ollama failed, using native Ollama")
            start_native_ollama()
    else:
        # Check if Ollama is already running
        sys.path.insert(0, str(ROOT))
        from zicore import ollama_service
        current = ollama_service.status()
        if current["status"] == "online":
            print(f"  [OK] Ollama already running ({len(current['models'])} models)")
        else:
            print("  Starting native Ollama...")
            start_native_ollama()

    # ── AUTO-LOAD GENERATORS ──────────────────────────────────────────
    print()
    print("[2/5] Loading generators...")
    try:
        sys.path.insert(0, str(ROOT))
        from agent.loader import loader
        results = loader.load_all()
        total = len(results)
        ok = sum(1 for r in results.values() if r.get("status") == "ok")
        warn = sum(1 for r in results.values() if r.get("status") == "not_installed")
        print(f"  Engines: {ok}/{total} ready, {warn} optional")
        for name, s in results.items():
            icon = "+" if s.get("status") == "ok" else "~" if s.get("status") == "not_installed" else "-"
            extra = ""
            if "engine" in s:
                extra = f" ({s['engine']})"
            elif "models" in s:
                models = s.get("models", [])
                extra = f" ({len(models)} models)" if models else " (no models)"
            elif "pillow" in s:
                extra = " (pillow)" if s["pillow"] else ""
            elif "tts" in s:
                extra = " (tts)" if s["tts"] else " (browser-only)"
            print(f"    [{icon}] {name}{extra}")
    except Exception as e:
        print(f"  [WARN] Loader failed: {e}")

    # ── MISSION MODULES ──────────────────────────────────────────────
    print()
    print(f"[3/5] Mission modules ({len(MISSION_MODULES)})")
    try:
        from backend.app.main import modules
        for i, mod_name in enumerate(MISSION_MODULES, 1):
            print(f"  {progress(i, len(MISSION_MODULES))} {mod_name}")
    except Exception:
        for i, mod_name in enumerate(MISSION_MODULES, 1):
            print(f"  {progress(i, len(MISSION_MODULES))} {mod_name}")

    # ── START API ─────────────────────────────────────────────────────
    log_dir = ROOT / "output"
    log_dir.mkdir(exist_ok=True)
    api_log = open(log_dir / "api.log", "w", encoding="utf-8", errors="replace")
    web_log = open(log_dir / "web.log", "w", encoding="utf-8", errors="replace")

    def kill_port(port):
        """Kill only the LISTENING process on a port (cross-platform)."""
        import subprocess as _sp
        import signal as _sig
        try:
            if sys.platform == "win32":
                r = _sp.run(['netstat', '-ano'], capture_output=True, text=True, timeout=5)
                for line in r.stdout.splitlines():
                    if f':{port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        if parts:
                            pid = int(parts[-1])
                            print(f"  Killing PID {pid} on port {port}")
                            try:
                                _sp.run(['taskkill', '/PID', str(pid), '/F'],
                                       capture_output=True, timeout=5)
                            except Exception:
                                pass
                            time.sleep(1)
                            return True
            else:
                r = _sp.run(['ss', '-tlnp'], capture_output=True, text=True, timeout=5)
                for line in r.stdout.splitlines():
                    if f':{port}' in line and 'LISTEN' in line:
                        import re
                        m = re.search(r'pid=(\d+)', line)
                        if m:
                            pid = int(m.group(1))
                            print(f"  Killing PID {pid} on port {port}")
                            try:
                                os.kill(pid, _sig.SIGKILL)
                            except Exception:
                                pass
                            time.sleep(1)
                            return True
        except Exception:
            pass
        return False

    if mode in ("api", "all") and not use_docker:
        if kill_port(API_PORT):
            print(f"  [OK] Port {API_PORT} cleared")

        print()
        print(f"[4/5] API backend on port {API_PORT}")
        api_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.app.main:app",
             "--host", "0.0.0.0", "--port", str(API_PORT), "--reload"],
            cwd=str(ROOT),
            stdout=api_log,
            stderr=api_log,
        )
        procs.append(("API", api_proc))

    # ── START WEB ─────────────────────────────────────────────────────
    if mode in ("web", "all") and not use_docker:
        if kill_port(WEB_PORT):
            print(f"  [OK] Port {WEB_PORT} cleared")

        print(f"[4/5] Web server on port {WEB_PORT}")
        web_proc = subprocess.Popen(
            [sys.executable, "web_server.py", str(WEB_PORT)],
            cwd=str(ROOT),
            stdout=web_log,
            stderr=web_log,
        )
        procs.append(("WEB", web_proc))

        # ── START EMULATORJS (GAMES) ──────────────────────────────────
        GAMES_PORT = 4001
        games_server = ROOT / "tools" / "emulatorjs" / "server.js"
        if games_server.exists() and shutil.which("node"):
            if kill_port(GAMES_PORT):
                print(f"  [OK] Port {GAMES_PORT} cleared")
            print(f"      Games server on port {GAMES_PORT}")
            games_proc = subprocess.Popen(
                ["node", str(games_server)],
                cwd=str(ROOT / "tools" / "emulatorjs"),
                stdout=web_log,
                stderr=web_log,
            )
            procs.append(("GAMES", games_proc))
        else:
            print(f"      [WARN] Games server skipped (node not found or server.js missing)")

        # ── START WEBAMP (MUSIC) ─────────────────────────────────────
        MUSIC_PORT = 4002
        music_server = ROOT / "tools" / "webamp" / "server.js"
        if music_server.exists() and shutil.which("node"):
            if kill_port(MUSIC_PORT):
                print(f"  [OK] Port {MUSIC_PORT} cleared")
            print(f"      Music server on port {MUSIC_PORT}")
            music_proc = subprocess.Popen(
                ["node", str(music_server)],
                cwd=str(ROOT / "tools" / "webamp"),
                stdout=web_log,
                stderr=web_log,
            )
            procs.append(("MUSIC", music_proc))

    if use_docker:
        print("[4/5] Services managed by Docker Compose")

    # ── STATUS ────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  ZICORE System Ready")
    print("")
    print("  Dashboard:  http://localhost:4000")
    print("  ZIO Agent:  http://localhost:4000/zio")
    print("  Portal:     http://localhost:4000/portal")
    print("  API:        http://localhost:4080/api/status")
    if any(name == "GAMES" for name, _ in procs):
        print("  Games:      http://localhost:4001")
    if any(name == "MUSIC" for name, _ in procs):
        print("  Music:      http://localhost:4002")
    print("=" * 60)
    print()
    print("[5/5] System online")
    print("  Press Ctrl+C to stop")
    print()

    # ── HEALTH CHECK ──────────────────────────────────────────────────
    time.sleep(2)
    if procs:
        check_url("API", f"http://localhost:{API_PORT}/api/status")
        check_url("WEB", f"http://localhost:{WEB_PORT}/")
        for name, _ in procs:
            if name == "GAMES":
                check_url("GAMES", f"http://localhost:4001/")
            elif name == "MUSIC":
                check_url("MUSIC", f"http://localhost:4002/")
        try:
            webbrowser.open(f"http://localhost:{WEB_PORT}")
        except Exception:
            pass

    # ── KEEP ALIVE ────────────────────────────────────────────────────
    try:
        while True:
            time.sleep(1)
            for name, proc in procs:
                if proc.poll() is not None:
                    print(f"  [WARN] {name} exited (code {proc.returncode})")
    except KeyboardInterrupt:
        print("\n  Shutting down...")
        for name, proc in procs:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        print("  All services stopped.")


if __name__ == "__main__":
    raise SystemExit(main())

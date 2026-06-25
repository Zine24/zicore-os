"""
ZICORE System Launcher
Starts both API backend (8080) and Web Server (3000).
"""
import sys
import os
import subprocess
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).parent
API_PORT = 8080
WEB_PORT = 3000

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"

    print("=" * 60)
    print("  ZICORE SYSTEM v3.7")
    print("  ZineMotion Foundation")
    print("=" * 60)

    procs = []

    if mode in ("api", "all"):
        print(f"\n[API] Starting backend on port {API_PORT}...")
        api_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.app.main:app",
             "--host", "0.0.0.0", "--port", str(API_PORT), "--reload"],
            cwd=str(ROOT),
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        procs.append(("API", api_proc))

    if mode in ("web", "all"):
        print(f"\n[WEB] Starting web server on port {WEB_PORT}...")
        web_proc = subprocess.Popen(
            [sys.executable, "web_server.py", str(WEB_PORT)],
            cwd=str(ROOT),
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        procs.append(("WEB", web_proc))

    print("\n" + "=" * 60)
    print(f"  Dashboard:  http://localhost:{WEB_PORT}")
    print(f"  ZIO Server: http://localhost:{WEB_PORT}/zio")
    print(f"  API:        http://localhost:{API_PORT}/api/status")
    print("=" * 60)
    print("\nPress Ctrl+C to stop all services.\n")

    try:
        time.sleep(2)
        if mode == "all":
            try:
                webbrowser.open(f"http://localhost:{WEB_PORT}")
            except Exception:
                pass

        while True:
            time.sleep(1)
            for name, proc in procs:
                if proc.poll() is not None:
                    print(f"[WARN] {name} process exited with code {proc.returncode}")
    except KeyboardInterrupt:
        print("\n[STOP] Shutting down...")
        for name, proc in procs:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"[STOP] {name} stopped")
            except Exception:
                proc.kill()
                print(f"[STOP] {name} killed")
        print("[STOP] All services stopped.")


if __name__ == "__main__":
    main()

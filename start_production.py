"""
ZICORE Production Launcher — Local + SSL + Cloudflare
Starts all services locally with SSL.

Usage:
    python start_production.py
"""
import sys
import subprocess
import time
import os
from pathlib import Path

ROOT = Path(__file__).parent
TUNNEL_NAME = "zicore"
CLOUDFLARED = ROOT / "cloudflared.exe"

def check_prerequisites():
    """Check all prerequisites."""
    print("[1/4] Checking prerequisites...")

    # Check Python
    print(f"  [OK] Python {sys.version.split()[0]}")

    # Check cloudflared
    if CLOUDFLARED.exists():
        print(f"  [OK] cloudflared found")
    else:
        print("  [WARN] cloudflared.exe not found")
        print("  Download: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        return False

    # Check SSL
    cert_file = ROOT / "nginx" / "ssl" / "cert.pem"
    key_file = ROOT / "nginx" / "ssl" / "key.pem"
    if cert_file.exists() and key_file.exists():
        print("  [OK] SSL certificates found")
    else:
        print("  [INFO] Generating SSL certificates...")
        subprocess.run([sys.executable, "ssl_setup.py"], cwd=str(ROOT))

    return True

def start_services():
    """Start API + Web servers."""
    procs = []

    # Start API backend
    print("\n[2/4] Starting API backend (port 8080)...")
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app",
         "--host", "0.0.0.0", "--port", "8080"],
        cwd=str(ROOT),
    )
    procs.append(("API", api_proc))
    print(f"  [OK] PID: {api_proc.pid}")

    # Start Web server
    print("\n[3/4] Starting Web server (port 3000)...")
    web_proc = subprocess.Popen(
        [sys.executable, "web_server.py", "3000"],
        cwd=str(ROOT),
    )
    procs.append(("WEB", web_proc))
    print(f"  [OK] PID: {web_proc.pid}")

    return procs

def start_tunnel():
    """Start Cloudflare tunnel."""
    print("\n[4/4] Starting Cloudflare tunnel...")

    # Check if authenticated
    cred_file = Path.home() / ".cloudflared" / "credentials.json"
    if not cred_file.exists():
        print("  [INFO] Not authenticated with Cloudflare")
        print("  Run: .\\cloudflared.exe tunnel login")
        print("  Then: .\\cloudflared.exe tunnel create zicore")
        print("  Then: .\\cloudflared.exe tunnel route dns zicore app.zicore.space")
        print()
        print("  [FALLBACK] Using quick tunnel (temporary URL)...")

        tunnel_proc = subprocess.Popen(
            [str(CLOUDFLARED), "tunnel", "--url", "http://localhost:3000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        # Wait for URL
        import re
        public_url = None
        start_time = time.time()
        while time.time() - start_time < 30:
            line = tunnel_proc.stdout.readline()
            if not line:
                break
            match = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
            if match:
                public_url = match.group(1)
                break

        if public_url:
            print(f"  [OK] Quick tunnel: {public_url}")
            return tunnel_proc, public_url
        else:
            print("  [WARN] Tunnel timeout")
            return tunnel_proc, None
    else:
        print("  [OK] Using named tunnel: zicore")
        tunnel_proc = subprocess.Popen(
            [str(CLOUDFLARED), "tunnel", "run", TUNNEL_NAME],
            cwd=str(ROOT),
        )
        return tunnel_proc, "https://app.zicore.space"

def show_urls(public_url):
    """Show all access URLs."""
    print()
    print("=" * 60)
    print("  ZICORE SYSTEM ONLINE!")
    print("")
    if public_url and "trycloudflare" in public_url:
        print("  Temporary URL (Cloudflare Quick Tunnel):")
        print(f"    {public_url}")
        print(f"    {public_url}/dashboard")
        print(f"    {public_url}/zio")
        print(f"    {public_url}/sim")
        print()
        print("  For production (zicore.space), run:")
        print("    .\\cloudflared.exe tunnel login")
        print("    .\\cloudflared.exe tunnel create zicore")
        print("    .\\cloudflared.exe tunnel route dns zicore app.zicore.space")
    else:
        print("  Production URLs:")
        print("    https://app.zicore.space")
        print("    https://app.zicore.space/dashboard")
        print("    https://app.zicore.space/zio")
        print("    https://app.zicore.space/sim")
        print("    https://api.zicore.space")
    print("")
    print("  Local URLs:")
    print("    http://localhost:3000")
    print("    http://localhost:3000/dashboard")
    print("    http://localhost:3000/zio")
    print("    http://localhost:3000/sim")
    print("=" * 60)

def main():
    print("=" * 60)
    print("  ZICORE SYSTEM v4.0 — PRODUCTION")
    print("  ZineMotion Foundation — Aerospace Division")
    print("=" * 60)

    if not check_prerequisites():
        print("\n[ERROR] Prerequisites not met")
        sys.exit(1)

    procs = start_services()
    tunnel_proc, public_url = start_tunnel()

    time.sleep(3)
    show_urls(public_url)

    print("\n  Press Ctrl+C to stop all services.\n")

    try:
        while True:
            time.sleep(1)
            for name, proc in procs:
                if proc.poll() is not None:
                    print(f"[WARN] {name} exited with code {proc.returncode}")
    except KeyboardInterrupt:
        print("\n[STOP] Shutting down...")
        for name, proc in procs:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"[STOP] {name} stopped")
            except:
                proc.kill()
                print(f"[STOP] {name} killed")

        if tunnel_proc:
            try:
                tunnel_proc.terminate()
                print("[STOP] Tunnel stopped")
            except:
                tunnel_proc.kill()

        print("[STOP] All services stopped.")

if __name__ == "__main__":
    main()

"""
ZICORE Production Launcher — SSL + Docker Compose
Starts all services with SSL and Docker.

Usage:
    python docker_start.py
"""
import subprocess
import sys
import os
import time
from pathlib import Path

ROOT = Path(__file__).parent

def check_docker():
    """Check if Docker is installed."""
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        print(f"[OK] Docker: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("[ERROR] Docker not installed")
        print("Install: https://docs.docker.com/get-docker/")
        return False

def check_docker_compose():
    """Check if Docker Compose is installed."""
    try:
        result = subprocess.run(["docker-compose", "--version"], capture_output=True, text=True)
        print(f"[OK] Docker Compose: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        # Try docker compose (v2)
        try:
            result = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
            print(f"[OK] Docker Compose: {result.stdout.strip()}")
            return True
        except FileNotFoundError:
            print("[ERROR] Docker Compose not installed")
            return False

def generate_ssl():
    """Generate SSL certificates if not exists."""
    cert_file = ROOT / "nginx" / "ssl" / "cert.pem"
    key_file = ROOT / "nginx" / "ssl" / "key.pem"

    if not cert_file.exists() or not key_file.exists():
        print("\n[SSL] Generating certificates...")
        subprocess.run([sys.executable, "ssl_setup.py"], cwd=str(ROOT))
    else:
        print("[OK] SSL certificates exist")

def setup_cloudflared():
    """Setup cloudflared credentials."""
    cred_dir = ROOT / "cloudflared"
    cred_file = cred_dir / "credentials.json"

    if not cred_file.exists():
        print("\n[Cloudflare] Setting up tunnel...")
        print("  Run this command to authenticate:")
        print("    cloudflared tunnel login")
        print()
        print("  Then create the tunnel:")
        print("    cloudflared tunnel create zicore")
        print()
        print("  Route DNS:")
        print("    cloudflared tunnel route dns zicore app.zicore.space")
        print("    cloudflared tunnel route dns zicore api.zicore.space")
        return False
    else:
        print("[OK] Cloudflared credentials found")
        return True

def start_docker():
    """Start services with Docker Compose."""
    print("\n[Docker] Starting services...")

    # Build and start
    subprocess.run(
        ["docker-compose", "up", "-d", "--build"],
        cwd=str(ROOT),
        check=True,
    )

    print("[OK] Services started")

def show_status():
    """Show running services."""
    print("\n[Docker] Running services:")
    subprocess.run(["docker-compose", "ps"], cwd=str(ROOT))

def show_urls():
    """Show access URLs."""
    print()
    print("=" * 60)
    print("  ZICORE SYSTEM ONLINE")
    print("")
    print("  Cloudflare Tunnel (SSL):")
    print("    https://app.zicore.space")
    print("    https://app.zicore.space/dashboard")
    print("    https://app.zicore.space/zio")
    print("    https://app.zicore.space/sim")
    print("")
    print("  Direct (with SSL):")
    print("    https://localhost/dashboard")
    print("    https://localhost/zio")
    print("    https://localhost/sim")
    print("")
    print("  API:")
    print("    https://api.zicore.space")
    print("    https://localhost:4080/api/status")
    print("=" * 60)

def main():
    print("=" * 60)
    print("  ZICORE — Docker + SSL Production")
    print("=" * 60)

    # Check prerequisites
    print("\n[1/5] Checking prerequisites...")
    if not check_docker():
        sys.exit(1)
    if not check_docker_compose():
        sys.exit(1)

    # Generate SSL
    print("\n[2/5] SSL setup...")
    generate_ssl()

    # Setup Cloudflare
    print("\n[3/5] Cloudflare setup...")
    cloudflare_ready = setup_cloudflared()

    # Start Docker
    print("\n[4/5] Starting Docker services...")
    start_docker()

    # Show status
    print("\n[5/5] Status...")
    time.sleep(5)
    show_status()
    show_urls()

    if not cloudflare_ready:
        print()
        print("[WARN] Cloudflare tunnel not configured")
        print("  Complete the setup above, then restart")

    print()
    print("[ZICORE] All systems online")
    print("[ZICORE] Press Ctrl+C to stop")
    print()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[STOP] Shutting down...")
        subprocess.run(["docker-compose", "down"], cwd=str(ROOT))
        print("[STOP] All services stopped")

if __name__ == "__main__":
    main()

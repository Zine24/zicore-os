"""
ZICORE Cloudflare Tunnel — Custom Domain Setup
For production deployment with your own domain.

Requirements:
1. Cloudflare account (free)
2. Domain added to Cloudflare
3. cloudflared installed

Usage:
    python cloudflare_setup.py --domain zicore.zinemotion.com
"""
import subprocess
import sys
import os
import argparse
from pathlib import Path

def check_cloudflared():
    """Check if cloudflared is installed."""
    try:
        result = subprocess.run(["cloudflared", "--version"], capture_output=True, text=True)
        print(f"[OK] cloudflared: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("[ERROR] cloudflared not installed")
        print("Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        return False

def authenticate():
    """Authenticate with Cloudflare."""
    print("\n[1/4] Authenticating with Cloudflare...")
    print("  A browser window will open. Log in and authorize.")
    subprocess.run(["cloudflared", "tunnel", "login"])

def create_tunnel(name="zicore"):
    """Create a named tunnel."""
    print(f"\n[2/4] Creating tunnel: {name}")
    result = subprocess.run(
        ["cloudflared", "tunnel", "create", name],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  [OK] Tunnel created: {name}")
        # Extract tunnel ID
        for line in result.stdout.split("\n"):
            if "Created tunnel" in line:
                tunnel_id = line.split()[-1]
                print(f"  [OK] Tunnel ID: {tunnel_id}")
                return tunnel_id
    else:
        print(f"  [ERROR] {result.stderr}")
        return None

def configure_dns(tunnel_id, domain):
    """Route DNS to tunnel."""
    print(f"\n[3/4] Configuring DNS: {domain}")
    subprocess.run(["cloudflared", "tunnel", "route", "dns", tunnel_id, domain])

def run_tunnel(tunnel_name, port=3000):
    """Run the tunnel."""
    print(f"\n[4/4] Starting tunnel on port {port}...")
    print(f"  URL: https://{tunnel_name}")
    subprocess.run(["cloudflared", "tunnel", "run", tunnel_name])

def main():
    parser = argparse.ArgumentParser(description="ZICORE Cloudflare Tunnel Setup")
    parser.add_argument("--domain", help="Custom domain (e.g., zicore.zinemotion.com)")
    parser.add_argument("--tunnel", default="zicore", help="Tunnel name (default: zicore)")
    parser.add_argument("--port", type=int, default=3000, help="Port to expose (default: 3000)")
    parser.add_argument("--skip-auth", action="store_true", help="Skip authentication (if already done)")
    args = parser.parse_args()

    print("=" * 60)
    print("  ZICORE — Cloudflare Tunnel Setup")
    print("  Custom Domain Deployment")
    print("=" * 60)

    if not check_cloudflared():
        sys.exit(1)

    if not args.skip_auth:
        authenticate()

    tunnel_id = create_tunnel(args.tunnel)
    if not tunnel_id:
        sys.exit(1)

    if args.domain:
        configure_dns(tunnel_id, args.domain)

    print()
    print("=" * 60)
    print("  SETUP COMPLETE")
    print("")
    if args.domain:
        print(f"  Dashboard:     https://{args.domain}")
        print(f"  ZIO Agent:     https://{args.domain}/zio")
        print(f"  Flight Sim:    https://{args.domain}/sim")
        print(f"  API:           https://api.{args.domain}")
    else:
        print(f"  Dashboard:     https://{args.tunnel}")
    print("")
    print("  Start ZICORE:")
    print(f"    python start_all.py")
    print("")
    print("  Then run tunnel:")
    print(f"    cloudflared tunnel run {args.tunnel}")
    print("=" * 60)

if __name__ == "__main__":
    main()

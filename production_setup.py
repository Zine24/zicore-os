"""
ZICORE Production Setup — zicore.space via Cloudflare Tunnel
Run this once on your server to configure the tunnel.

Requirements:
1. cloudflared installed
2. cloudflared tunnel login (run once to authenticate)
3. This script

Usage:
    python production_setup.py
"""
import subprocess
import sys
import os
from pathlib import Path

DOMAIN = "zicore.space"
TUNNEL_NAME = "zicore"
PORT_WEB = 4000
PORT_API = 4080

def run(cmd, check=True):
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=True, text=True)

def main():
    print("=" * 60)
    print("  ZICORE — Production Setup for zicore.space")
    print("=" * 60)

    # Check cloudflared
    print("\n[1/5] Checking cloudflared...")
    try:
        r = run(["cloudflared", "--version"], check=False)
        print(f"  [OK] {r.stdout.strip()}")
    except FileNotFoundError:
        print("  [ERROR] cloudflared not installed")
        print("  Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        sys.exit(1)

    # Check authentication
    print("\n[2/5] Checking authentication...")
    cred_file = Path.home() / ".cloudflared" / "credentials.json"
    if not cred_file.exists():
        print("  [INFO] Not authenticated. Opening browser...")
        run(["cloudflared", "tunnel", "login"], check=False)
        print("  [OK] Authenticated")
    else:
        print("  [OK] Authenticated")

    # Create tunnel
    print(f"\n[3/5] Creating tunnel: {TUNNEL_NAME}")
    r = run(["cloudflared", "tunnel", "create", TUNNEL_NAME], check=False)
    if "already exists" in r.stderr:
        print(f"  [OK] Tunnel '{TUNNEL_NAME}' already exists")
    elif r.returncode == 0:
        print(f"  [OK] Tunnel created")
    else:
        print(f"  [WARN] {r.stderr}")

    # Get tunnel ID
    r = run(["cloudflared", "tunnel", "list"], check=False)
    tunnel_id = None
    for line in r.stdout.split("\n"):
        if TUNNEL_NAME in line:
            tunnel_id = line.split()[0]
            break

    if tunnel_id:
        print(f"  [OK] Tunnel ID: {tunnel_id}")

    # Configure DNS
    print(f"\n[4/5] Configuring DNS for {DOMAIN}...")
    subdomains = ["app", "api"]
    for sub in subdomains:
        host = f"{sub}.{DOMAIN}"
        if sub == "app":
            service = f"http://localhost:{PORT_WEB}"
        else:
            service = f"http://localhost:{PORT_API}"

        print(f"  {host} → {service}")
        if tunnel_id:
            run(["cloudflared", "tunnel", "route", "dns", TUNNEL_NAME, host], check=False)

    # Create config file
    print("\n[5/5] Creating config file...")
    config = {
        "tunnel": TUNNEL_NAME,
        "credentials-file": str(cred_file),
        "ingress": [
            {"hostname": f"app.{DOMAIN}", "service": f"http://localhost:{PORT_WEB}"},
            {"hostname": f"api.{DOMAIN}", "service": f"http://localhost:{PORT_API}"},
            {"service": "http_status:404"},
        ],
    }

    config_path = Path("cloudflare_config.json")
    import json
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  [OK] Config: {config_path}")

    # Summary
    print()
    print("=" * 60)
    print("  SETUP COMPLETE!")
    print("")
    print("  DNS Configuration (in Cloudflare):")
    print(f"    app.{DOMAIN}  → CNAME  {TUNNEL_NAME}.cfargotunnel.com")
    print(f"    api.{DOMAIN}  → CNAME  {TUNNEL_NAME}.cfargotunnel.com")
    print("")
    print("  Start ZICORE:")
    print("    python start_all.py")
    print("")
    print("  Start tunnel:")
    print(f"    cloudflared tunnel run {TUNNEL_NAME}")
    print("")
    print("  URLs:")
    print(f"    Main Menu:     https://app.{DOMAIN}")
    print(f"    Dashboard:     https://app.{DOMAIN}/dashboard")
    print(f"    ZIO Agent:     https://app.{DOMAIN}/zio")
    print(f"    Flight Sim:    https://app.{DOMAIN}/sim")
    print(f"    API:           https://api.{DOMAIN}")
    print("=" * 60)

if __name__ == "__main__":
    main()

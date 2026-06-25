"""
ZICORE Google Colab Setup — CPU Only + Groq AI
Run this in a SINGLE Colab cell after uploading zicore-system.zip.
No GPU required. No Unsloth. Just Groq API for real AI.
"""
import subprocess
import sys
import os
import time
import re
from pathlib import Path
from IPython.display import display, HTML

print("=" * 60)
print("  ZICORE SYSTEM v4.0 — Colab CPU")
print("  ZineMotion Foundation — Aerospace Division")
print("=" * 60)

# Install dependencies
print("\n[1/4] Installing dependencies...")
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q",
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "websockets>=12.0",
    "pydantic>=2.0",
    "Pillow>=10.0",
    "numpy>=1.24",
    "trimesh>=3.20",
    "httpx>=0.25",
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("  [OK] Installed")

# Install cloudflared
print("\n[2/4] Installing cloudflared...")
subprocess.run(
    ["wget", "-q", "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
     "-O", "/usr/local/bin/cloudflared"],
    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
subprocess.run(["chmod", "+x", "/usr/local/bin/cloudflared"], check=True)
print("  [OK] Installed")

# Check for zicore-system
ZICORE_DIR = Path("/content/zicore-system")

if not ZICORE_DIR.exists():
    print("\n[!] zicore-system not found")
    print("  Run UPLOAD cell first, then re-run this cell")
else:
    print("\n[3/4] [OK] Found ZICORE")

    # Start API
    print("\n[4/4] Starting API (port 8080)...")
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.app.main:app",
         "--host", "0.0.0.0", "--port", "8080"],
        cwd=str(ZICORE_DIR),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"  [OK] API PID: {api_proc.pid}")

    # Start Web
    print("  Starting Web (port 3000)...")
    web_proc = subprocess.Popen(
        [sys.executable, "web_server.py", "3000"],
        cwd=str(ZICORE_DIR),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    print(f"  [OK] Web PID: {web_proc.pid}")

    time.sleep(5)

    # Create tunnel
    print("\n[TUNNEL] Creating Cloudflare tunnel...")
    try:
        tunnel_proc = subprocess.Popen(
            ["/usr/local/bin/cloudflared", "tunnel", "--url", "http://localhost:3000"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )

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
            print()
            print("=" * 60)
            print("  ZICORE IS LIVE!")
            print("")
            print(f"  Temporary:  {public_url}")
            print(f"  Production: https://app.zicore.space")
            print("")
            print("  Pages:")
            print(f"    {public_url}")
            print(f"    {public_url}/dashboard")
            print(f"    {public_url}/zio")
            print(f"    {public_url}/sim")
            print("")
            print("  AI: Groq (free) — run CONNECT_GROQ cell next")
            print("=" * 60)

            display(HTML(f'''
            <div style="padding:20px;background:#0a0e18;border:1px solid #00e5ff;border-radius:8px;margin:16px 0;font-family:monospace">
                <h3 style="color:#00e5ff;margin:0 0 12px 0">ZICORE SYSTEM ONLINE — CPU</h3>
                <p><a href="{public_url}" target="_blank" style="color:#00e5ff">{public_url}</a></p>
                <p><a href="{public_url}/dashboard" target="_blank" style="color:#7c4dff">Dashboard</a> | 
                   <a href="{public_url}/zio" target="_blank" style="color:#0f6">ZIO Agent</a> | 
                   <a href="{public_url}/sim" target="_blank" style="color:#fa0">Flight Sim</a></p>
            </div>
            '''))
        else:
            print("  [WARN] Tunnel timeout. Use Colab port forwarding.")

    except Exception as e:
        print(f"  [WARN] {e}")

    print()
    print("[ZICORE] All systems online")

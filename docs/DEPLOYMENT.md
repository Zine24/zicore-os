# Deployment Guide

## Local Development

### Prerequisites

- Python 3.10+
- pip

### Steps

```bash
git clone https://github.com/Zine24/zicore-system.git
cd zicore-system
pip install -r requirements.txt
python start_all.py
```

### URLs

- Web: `http://localhost:3000`
- API: `http://localhost:8080`
- Dashboard: `http://localhost:3000/dashboard`
- ZIO Agent: `http://localhost:3000/zio`
- Flight Sim: `http://localhost:3000/sim`

---

## Google Colab (Free GPU T4)

### Prerequisites

- Google account
- `zicore-system.zip` (2.8 MB)
- (Optional) Groq API key for real AI: https://console.groq.com

### Steps

#### 1. Open Colab

Go to https://colab.research.google.com and create a new notebook.

#### 2. Change Runtime to GPU T4

```
Runtime → Change runtime type → GPU T4 → Save
```

#### 3. Cell 1 — Upload

```python
from google.colab import files
import zipfile, os

print("Select zicore-system.zip:")
uploaded = files.upload()
fname = list(uploaded.keys())[0]

with zipfile.ZipFile(fname, 'r') as z:
    z.extractall('/content/')

print(f"[OK] Extracted to /content/zicore-system")
```

#### 4. Cell 2 — Install + Start

```python
import subprocess, time, urllib.request, json

ZICORE_DIR = '/content/zicore-system'

# Install
!cd /content/zicore-system && pip install -q -r requirements.txt

# Start API
api = subprocess.Popen(
    ['python', '-m', 'uvicorn', 'backend.app.main:app',
     '--host', '0.0.0.0', '--port', '8080'],
    cwd=ZICORE_DIR
)

# Start Web
web = subprocess.Popen(
    ['python', 'web_server.py', '3000'],
    cwd=ZICORE_DIR
)

time.sleep(5)

# Test
try:
    r = urllib.request.urlopen('http://localhost:3000/api/status', timeout=5)
    print("[OK] Web + API online")
except:
    print("[WARN] Servers starting...")
```

#### 5. Cell 3 — Cloudflare Tunnel

```python
import subprocess, re

!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared
!chmod +x /usr/local/bin/cloudflared

tunnel = subprocess.Popen(
    ['/usr/local/bin/cloudflared', 'tunnel', '--url', 'http://localhost:3000'],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)

url = None
for _ in range(30):
    line = tunnel.stdout.readline()
    m = re.search(r'(https://[a-zA-Z0-9-]+\.trycloudflare\.com)', line)
    if m:
        url = m.group(1)
        break

if url:
    print(f"Main Menu: {url}")
    print(f"Dashboard: {url}/dashboard")
    print(f"ZIO Agent: {url}/zio")
    print(f"Flight Sim: {url}/sim")
```

#### 6. Cell 4 — Connect Groq (Optional)

```python
import json

GROQ_API_KEY = "gsk_..."  # Get free key from console.groq.com

config_path = '/content/zicore-system/data/config/zio_config.json'
with open(config_path, 'r') as f:
    config = json.load(f)

config['providers']['groq']['enabled'] = True
config['providers']['groq']['api_key'] = GROQ_API_KEY
config['zio_engine']['active_provider'] = 'groq'

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)

print("[OK] Groq connected — real AI enabled")
```

#### 7. Cell 5 — Google Drive (Optional)

```python
from google.colab import drive
drive.mount('/content/drive')

!mkdir -p /content/drive/MyDrive/zicore-data
!cp -r /content/zicore-system/data/knowledge/* /content/drive/MyDrive/zicore-data/ 2>/dev/null || true

print("[OK] Knowledge base synced to Drive")
```

---

## Docker

### Prerequisites

- Docker
- Docker Compose

### Steps

```bash
git clone https://github.com/Zine24/zicore-system.git
cd zicore-system
docker-compose up -d
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| api | 8080 | FastAPI backend |
| web | 3000 | Web server |
| nginx | 443 | SSL reverse proxy |
| cloudflare | - | Tunnel to zicore.space |

### URLs

- Local: `http://localhost:3000`
- Production: `https://app.zicore.space`

---

## Production (zicore.space)

### Prerequisites

- Cloudflare account
- Domain `zicore.space` on Cloudflare
- cloudflared installed

### Steps

#### 1. Authenticate with Cloudflare

```bash
.\cloudflared.exe tunnel login
```

#### 2. Create Named Tunnel

```bash
.\cloudflared.exe tunnel create zicore
```

#### 3. Configure DNS

```bash
.\cloudflared.exe tunnel route dns zicore app.zicore.space
.\cloudflared.exe tunnel route dns zicore api.zicore.space
```

#### 4. Start Services

```bash
python start_production.py
```

### DNS Configuration

| Domain | Port | Service |
|--------|------|---------|
| app.zicore.space | 3000 | Web (Dashboard, ZIO, Sim) |
| api.zicore.space | 8080 | API (REST, WebSocket) |

---

## Troubleshooting

### "Address already in use"

```bash
# Windows
taskkill /F /IM python.exe

# Linux/Mac
pkill -f uvicorn
pkill -f web_server
```

### "Module not found"

```bash
pip install -r requirements.txt
```

### "Cloudflare tunnel timeout"

- Check internet connection
- Try restarting the tunnel
- Use Colab port forwarding as fallback

### Colab disconnects

- Re-run all cells
- Use Google Drive for persistence

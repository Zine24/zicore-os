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
python install.py  # Installs Ollama and sets up environment
python start_all.py
```

### URLs

- Web: `http://localhost:4000`
- API: `http://localhost:4080`
- Dashboard: `http://localhost:4000/dashboard`
- ZIO Agent: `http://localhost:4000/zio`
- Flight Sim: `http://localhost:4000/sim`

---

## Docker Deployment

### Prerequisites

- Docker
- Docker Compose

### Steps

```bash
# Build and run with Cloudflare tunnel
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

- Local: `http://localhost:4000`
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

## Ollama Integration

### Prerequisites

- Ollama installed (local or in Docker)

### Steps

```bash
python -m zicore.ollama_service start
```

This will start an Ollama server locally with pre-loaded models.

### Available Models

- llama3.1:8b
- mistral:7b
- codellama:7b
- qwen2.5:7b

### Integration with ZIO

ZIO automatically detects and uses Ollama models when available. You can switch to Ollama provider:

```python
# Set ZIO to use Ollama
from backend.app.config import update_config
update_config({"zio_engine": {"active_provider": "ollama"}})
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

- Local: `http://localhost:4000`
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

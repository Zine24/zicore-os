# ZICORE System v5.0

> **Z**ine **I**ntelligence **Core** — Materializer Engine

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![License: CC-BY-SA-4.0](https://img.shields.io/badge/License-CC--BY--SA--4.0-00e5ff.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

ZICORE is a full-stack aerospace AI system — a Materializer that turns ideas into reality through AI generation, procedural generation, and content creation tools. Features 100 API endpoints, 10 dashboard workspaces, 7 HTML5 games, mail server, ML engine, and cross-platform deployment.

---

## Features

| Category | Feature | Detail |
|----------|---------|--------|
| **AI Engine** | Materializer | IntentClassifier + ZICOREMaterializer — dispatches to image/3d/code/video/audio/procedural engines |
| **AI Engine** | 9 Providers | ZICORE Native, OpenRouter, Ollama, OpenAI, Anthropic, Groq, DeepSeek, Together AI, OpenCode |
| **ML Engine** | 9 Functions | Text classification, anomaly detection, K-Means, sentiment, linear regression, patterns, cosine similarity, hash embedding, text vectorization |
| **Dashboard** | 10 Workspaces | System, ZIO AI, 3D, Video, Audio, Image, Code, Text, Vision, Library |
| **Dashboard** | Floating Panels | Video NLE editor, Materializer panel |
| **Dashboard** | ZIO Mirror | Real-time engine status, command dispatch, task queue |
| **Flight Sim** | 7 Vehicles | Drone, Obsidiana, BlackVanta, ZIron Sigma, ZI Voyager, X-Wing, GT Begasus |
| **Flight Sim** | Aircraft Config | Propulsion type, mass, thrust, speed, ceiling, destination selector |
| **Games** | 7 HTML5 Games | Snake, Tetris, Breakout, 2048, Pong, X-Wing Alliance, FreeSpace 2 |
| **Games** | EmulatorJS | Retro ROM emulator + HTML5 game server (port 3001) |
| **Music** | Webamp | Winamp 2 clone audio player (port 3002) |
| **Mail** | Postfix + Dovecot | Full mail server with Rspamd spam filter, Roundcube webmail |
| **3D** | Mesh Generation | Cube, sphere, cylinder, cone, rocket — STL/OBJ/GLB export |
| **Audio** | Sound Synthesis | 8 sound types + TTS/STT via browser Speech API |
| **Vision** | Camera Input | getUserMedia webcam capture with frame analysis + OCR |
| **Data** | Knowledge Base | Persistent chat history + document ingestion + full-text search |
| **Deploy** | Cross-Platform | Windows, Linux, macOS — Docker-first, no OS dependency |
| **Deploy** | Install Scripts | `install.sh` (Linux), `zicore_v5.0.bat` (Windows), `zicore_v5.0.sh` (Linux) |

---

## Quick Start

### Option 1: Windows Launcher

```bat
zicore_v5.0.bat
```

### Option 2: Linux Installer

```bash
curl -sL https://raw.githubusercontent.com/zinemotion/zicore-system/main/install.sh | sudo bash
```

### Option 3: Docker Compose

```bash
docker-compose up -d
```

### Option 4: Manual

```bash
git clone https://github.com/zinemotion/zicore-system.git
cd zicore-system
pip install -r requirements.txt
python start_all.py
```

Open: `http://localhost:4000`

---

## Ports

| Port | Service |
|------|---------|
| 3000 | Web UI (ZICORE Dashboard) |
| 3001 | EmulatorJS (Games) |
| 3002 | Webamp (Music) |
| 8080 | API Server + Webmail |
| 8081 | FileBrowser |
| 11434 | Ollama (Docker) |
| 25/465/587 | SMTP (Mail) |
| 143/993/110/995 | IMAP/POP3 (Mail) |

---

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │        ZICORE System v5.0            │
                    │        Materializer Engine           │
                    └─────────────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
     ┌────────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐
     │   Frontend       │    │   Web Server     │    │   API Backend    │
     │   (Port 3000)    │    │   (Port 3000)    │    │   (Port 8080)    │
     │                  │    │                  │    │                  │
     │ • index.html     │    │ • 100 Routes     │    │ • 16 Modules     │
     │ • dashboard.html │    │ • WebSocket      │    │ • Materializer   │
     │ • flight-sim.html│    │ • Static Files   │    │ • ML Engine      │
     │ • zio.html       │    │ • Config API     │    │ • Procedural     │
     └──────────────────┘    └──────────────────┘    └──────────────────┘
              │                       │                       │
              │              ┌────────▼────────┐             │
              │              │  Docker Services │             │
              └──────────────│  • Ollama        │◄────────────┘
                             │  • Mail Stack    │
                             │  • EmulatorJS    │
                             │  • Webamp        │
                             │  • FileBrowser   │
                             └─────────────────┘
```

### Materializer Pipeline

```
User Input ("Generate a picture of a sunset")
    │
    ▼
┌───────────────────────────────────────────┐
│            IntentClassifier               │
│  Classifies: image/3d/code/video/audio/   │
│              procedural/text/vision        │
└───────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────┐
│          ZICOREMaterializer               │
│  Dispatches to appropriate engine:        │
│  • StableDiffusionEngine (CPU)            │
│  • Hunyuan3DEngine (trimesh fallback)     │
│  • ProceduralEngine (10 techniques)       │
│  • Code execution (sandboxed Python)      │
│  • Audio synthesis (Web Audio API)        │
└───────────────────────────────────────────┘
    │
    ▼
Output (image/mesh/terrain/code/audio)
```

---

## Zicore Modules (16)

| Module | Function |
|--------|----------|
| materializer | IntentClassifier + ZICOREMaterializer — dispatches to generation engines |
| ml_engine | ZIOML — 9 ML functions (classification, anomaly, clustering, sentiment, regression, patterns, similarity, embedding, vectorization) |
| procedural | ProceduralEngine — 10 techniques (terrain, cave, dungeon, fractal, L-system, Voronoi, WFC, Perlin, Worley, cellular) |
| knowledge_base | KnowledgeBase — persistent chat, document ingestion, full-text search |
| hunyuan3d_engine | 3D mesh generation with GPU detection and trimesh fallback |
| stable_diffusion_engine | CPU image generation via diffusers library |
| ollama_service | Cross-platform Ollama management (Docker-first) |
| ssh_integration | Cross-platform SSH, Firefox, Thunderbird management |
| mail_integration | Mail server management (users, aliases, send, inbox, IMAP, SMTP, DNS) |
| openvision | Image/video analysis, OCR, object detection |
| data_retention | Training data export (JSONL, Unsloth format) |
| local_llm | Local LLM inference wrapper |
| inference | Inference pipeline orchestrator |
| cfd_sim | CFD simulation engine |
| telemetry_sim | Telemetry simulation |
| rust_bridge | Rust FFI bridge for performance-critical ops |

---

## Supported Providers

| Provider | Type | Free Tier | Models |
|----------|------|-----------|--------|
| ZICORE Native | Local | Yes | Rule-based + procedural |
| Groq | Cloud | Yes (30 req/min) | llama-3.1-8b-instant, mixtral-8x7b |
| OpenRouter | Cloud | Some free | meta-llama, mistral, google, anthropic |
| OpenAI | Cloud | Paid | gpt-4o, gpt-4o-mini, o1-mini |
| Anthropic | Cloud | Paid | claude-3.5-sonnet, claude-3-haiku |
| DeepSeek | Cloud | Paid | deepseek-chat, deepseek-coder |
| Together AI | Cloud | Free tier | Meta-Llama-3.1-8B/70B, Mixtral |
| Ollama | Local | Yes | llama3.1:8b, mistral:7b, codellama |
| OpenCode | Cloud | Free | mimo-v2-free, codestral, deepseek-v3 |

---

## API Endpoints

### REST

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | System status + all 17 modules |
| GET | `/api/config` | Get configuration |
| POST | `/api/config` | Update configuration |
| POST | `/api/chat` | Chat with ZIO (knowledge-aware) |
| POST | `/api/provider/chat` | Chat via specific provider |
| POST | `/api/config/test-provider/{id}` | Test provider connection |
| GET | `/api/telemetry` | Real-time telemetry data |
| GET | `/api/knowledge/stats` | Knowledge base statistics |
| GET | `/api/knowledge/search?q=` | Search conversations |
| POST | `/api/knowledge/document` | Upload document |
| POST | `/api/mesh/generate` | Generate 3D mesh |
| POST | `/api/video/process` | Process video frames |
| GET | `/api/missions` | List saved missions |

### WebSocket

| Command | Description |
|---------|-------------|
| `chat` | Send message, get full response |
| `stream` | Send message, get word-by-word streaming |
| `generate` | Generate image/video/3d/sound |
| `telemetry` | Subscribe to real-time telemetry |
| `mission_save` | Save current mission |
| `mission_load` | Load mission by ID |
| `vision_analyze` | Analyze image |
| `vision_webcam` | Analyze webcam frame |
| `knowledge_search` | Search knowledge base |
| `knowledge_stats` | Get knowledge stats |
| `mesh_generate` | Generate 3D mesh |

---

## Configuration

Config file: `data/config/zio_config.json`

```json
{
  "providers": {
    "groq": {
      "enabled": true,
      "api_key": "gsk_...",
      "default_model": "llama-3.1-8b-instant"
    }
  },
  "zio_engine": {
    "active_provider": "groq",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "theme": "midnight"
}
```

---

## Project Structure

```
zicore-system/
├── backend/              # FastAPI API server
│   ├── app/
│   │   ├── main.py       # App entry point
│   │   ├── engines/      # Motor A + Motor B
│   │   ├── pipelines/    # Orchestrator
│   │   ├── modules/      # 17 module state machines
│   │   └── routers/      # Agent router
│   └── requirements.txt
├── frontend/             # Static HTML/JS/CSS
│   ├── index.html        # Main menu (3D animated)
│   ├── dashboard.html    # Flight deck (8 workspaces)
│   ├── zio.html          # ZIO agent WebUI
│   └── simulator.html    # Flight simulator
├── agent/                # AI agent core
│   ├── core.py           # ZICoreAgent main class
│   ├── generator.py      # Unified generation engine
│   ├── voice.py          # TTS/STT
│   └── zio_personality.py # ZIO personality + responses
├── zicore/               # Core modules
│   ├── knowledge_base.py # Chat persistence + docs
│   ├── openvision.py     # Image/video analysis
│   ├── telemetry_sim.py  # Telemetry simulation
│   ├── data_retention.py # Training data export
│   └── unsloth_integration.py # Fine-tuning scripts
├── zty/                  # Z-TY Factory (aircraft design)
├── native/               # Rust/C++ modules
├── tests/                # 93 tests
├── data/                 # Config, knowledge, missions
├── docs/                 # Documentation
├── web_server.py         # Web server (port 3000)
├── start_all.py          # Local launcher
├── start_production.py   # Production launcher
├── colab_setup.py        # Colab deployment
├── docker-compose.yaml   # Docker Compose
├── requirements.txt      # Python dependencies
└── LICENSE               # MIT License
```

---

## Deployment

| Method | Command | URL |
|--------|---------|-----|
| Local | `python start_all.py` | `http://localhost:4000` |
| Production | `python start_production.py` | `https://app.zicore.space` |
| Docker | `docker-compose up -d` | `https://app.zicore.space` |
| Colab | Run cells in notebook | Cloudflare tunnel URL |

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Development setup
git clone https://github.com/Zine24/zicore-system.git
cd zicore-system
pip install -r requirements.txt
pip install pytest pytest-asyncio
python -m pytest tests/ -v
```

---

## License

MIT License — Copyright (c) 2024 ZineMotion Foundation

See [LICENSE](LICENSE) for full text.

---

## Acknowledgments

- **ZineMotion Foundation** — Aerospace Division
- **Unsloth** — Efficient LLM fine-tuning
- **FastAPI** — High-performance Python API framework
- **Three.js** — 3D graphics in the browser
- **Cloudflare** — Tunnel and edge network

---

<p align="center">
  <b>ZICORE System v0.4.0</b><br>
  ZineMotion Foundation — Aerospace Division<br>
  <i>Nucleo de Control Inteligente del Ecosistema Zi</i>
</p>

# ZICORE System

> **Z**ine **I**ntelligence **Core** — Aerospace AI Operating System

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-00e5ff.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Issues](https://img.shields.io/github/issues/Zine24/zicore-system)](https://github.com/Zine24/zicore-system/issues)
[![Stars](https://img.shields.io/github/stars/Zine24/zicore-system)](https://github.com/Zine24/zicore-system)

ZICORE is a full-stack aerospace AI system featuring dual-engine inference (deterministic + ML), 17 mission modules, holographic cockpit-style dashboard, NLE video editor, 3D mesh viewer, and real-time telemetry — deployable locally, via Docker, or on Google Colab with free GPU.

---

## Features

| Category | Feature | Detail |
|----------|---------|--------|
| **AI Engine** | Dual-Engine Pipeline | Motor A (deterministic rules) + Motor B (ML inference via Unsloth/transformers) |
| **AI Engine** | 9 Providers | ZICORE Native, OpenRouter, Ollama, OpenAI, Anthropic, Groq, DeepSeek, Together AI, OpenCode |
| **AI Engine** | Confidence-Weighted Merge | Both engines vote; output weighted by confidence score |
| **Dashboard** | 8 Workspaces | System, ZIO AI, 3D, Video, Audio, Post, Vision, Data |
| **Dashboard** | Cockpit-Style UI | Dark aerospace theme, real-time telemetry bars, WebSocket streaming |
| **Dashboard** | 8 Themes | Midnight, Cyber Neon, Matrix, Solar Flare, Arctic, Blood Moon, Deep Forest, Void |
| **Modules** | 17 Mission Modules | ZiNav, ZiHab, ZiPower, ZiShip, ZIDrone, ZIRobot, ZIComm, ZIEco, ZIMed, ZiCoreX, ZILink, ZIVR, ZISec, ZiCRIOGEN, ZiMAURY, GPDEngine, Z-TY Factory |
| **Video** | NLE Editor | Multi-track timeline (V1/V2/A1/A2), 12 effects, 8 transitions, drag reorder |
| **Video** | Video Generation | Frame-by-frame procedural + API-based (DALL-E, Stability) |
| **3D** | Mesh Viewer | Three.js WebGL viewport with material editor |
| **3D** | Mesh Generation | Cube, sphere, cylinder, cone, rocket — STL/OBJ/GLB export |
| **Audio** | Waveform Visualizer | Web Audio API real-time visualization |
| **Audio** | Sound Synthesis | 8 sound types: alarm, engine, beep, wind, radio, melody, heartbeat, laser |
| **Audio** | TTS/STT | Browser Speech API + optional Whisper |
| **Vision** | Camera Input | getUserMedia webcam capture with frame analysis |
| **Vision** | OpenVision | Image/video analysis, OCR, object detection |
| **Data** | Knowledge Base | Persistent chat history + document ingestion + full-text search |
| **Data** | Data Retention | Training data export (JSONL, Unsloth format) |
| **Data** | Mission Save/Load | JSON-based mission persistence |
| **Sim** | Flight Simulator | 4 vehicles with physics, HUD, keyboard controls |
| **Deploy** | Cloudflare Tunnel | One-command public deployment |
| **Deploy** | Docker | Dockerfile + docker-compose with Nginx SSL |

---

## Quick Start

### Option 1: Local

```bash
git clone https://github.com/Zine24/zicore-system.git
cd zicore-system
pip install -r requirements.txt
python start_all.py
```

Open: `http://localhost:3000`

### Option 2: Google Colab (Free GPU T4)

```python
# Cell 1 — Upload
from google.colab import files
import zipfile
uploaded = files.upload()
with zipfile.ZipFile(list(uploaded.keys())[0], 'r') as z:
    z.extractall('/content/')

# Cell 2 — Setup + Start
!cd /content/zicore-system && pip install -q -r requirements.txt
!cd /content/zicore-system && python colab_setup.py
```

### Option 3: Docker

```bash
docker-compose up -d
```

Open: `https://app.zicore.space`

---

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │         ZICORE System v0.4.0         │
                    └─────────────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
     ┌────────▼────────┐    ┌────────▼────────┐    ┌────────▼────────┐
     │   Frontend       │    │   Web Server     │    │   API Backend    │
     │   (Port 3000)    │    │   (Port 3000)    │    │   (Port 8080)    │
     │                  │    │                  │    │                  │
     │ • index.html     │    │ • 45 Routes      │    │ • 17 Modules     │
     │ • dashboard.html │    │ • WebSocket      │    │ • Dual Engine    │
     │ • zio.html       │    │ • Static Files   │    │ • Pipeline       │
     │ • simulator.html │    │ • Config API     │    │ • Orchestrator   │
     └──────────────────┘    └──────────────────┘    └──────────────────┘
              │                       │                       │
              │              ┌────────▼────────┐             │
              │              │  Cloudflare      │             │
              └──────────────│  Tunnel          │◄────────────┘
                             │  (Public URL)    │
                             └─────────────────┘
```

### Dual-Engine Pipeline

```
User Input
    │
    ▼
┌───────────────────────────────────────────┐
│            Intent Classifier               │
└───────────────────────────────────────────┘
    │                         │
    ▼                         ▼
┌─────────────┐    ┌─────────────────────┐
│  Motor A     │    │  Motor B             │
│  (Rules)     │    │  (ML Inference)      │
│              │    │                      │
│  Deterministic│    │  • Groq (free)       │
│  Fast (<1ms) │    │  • OpenAI            │
│  100% uptime │    │  • Anthropic         │
└──────┬──────┘    │  • Unsloth (local)   │
       │           └──────────┬──────────┘
       │                      │
       ▼                      ▼
┌───────────────────────────────────────────┐
│       Confidence-Weighted Merge            │
│                                            │
│  output = (conf_A × out_A + conf_B × out_B)│
│            / (conf_A + conf_B)             │
└───────────────────────────────────────────┘
    │
    ▼
Response
```

---

## 17 Mission Modules

| Module | Name | Function |
|--------|------|----------|
| ZiNav | Navigation | Trajectory planning, orbital mechanics |
| ZiHab | Habitat | Life support, environment control |
| ZiPower | Power | Solar, battery, grid management |
| ZiShip | Ship | Hull integrity, propulsion, thermal |
| ZIDrone | Drone | Swarm control, autonomous survey |
| ZIRobot | Robot | Manipulator control, maintenance |
| ZIComm | Comms | RF/optical links, encryption |
| ZIEco | Ecology | CO2 scrubbing, water recovery, plants |
| ZIMed | Medical | Crew health, vitals monitoring |
| ZiCoreX | Compute | AI inference, cluster management |
| ZILink | Link | Data rates, link margin |
| ZIVR | VR | Headset control, environment rendering |
| ZISec | Security | Firewall, intrusion detection |
| ZiCRIOGEN | Cryogenic | Propellant management, tank pressure |
| ZiMAURY | Defense | Tactical systems, shield control |
| GPDEngine | GPD | Guidance, proximity, docking |
| Z-TY Factory | Manufacturing | Parametric aircraft design |

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
| Local | `python start_all.py` | `http://localhost:3000` |
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

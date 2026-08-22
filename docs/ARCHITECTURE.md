# ZICORE Architecture

## System Overview

ZICORE is a full-stack aerospace AI system with three main layers:

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │Main Menu │  │Dashboard │  │ZIO Agent │  │Flight Sim│       │
│  │index.html│  │dashboard │  │zio.html  │  │simulator │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│       │              │              │              │              │
│       └──────────────┴──────────────┴──────────────┘              │
│                          │ HTTP + WebSocket                       │
├──────────────────────────┼──────────────────────────────────────┤
│                     SERVER LAYER                                 │
│                          │                                       │
│  ┌───────────────────────▼───────────────────────┐              │
│  │              Web Server (port 3000)             │              │
│  │  • 45 routes                                    │              │
│  │  • Static file serving                          │              │
│  │  • WebSocket handler                            │              │
│  │  • Config management                            │              │
│  └───────────────────────┬───────────────────────┘              │
│                          │                                       │
│  ┌───────────────────────▼───────────────────────┐              │
│  │              API Backend (port 8080)            │              │
│  │  • FastAPI + uvicorn                            │              │
│  │  • 17 module state machines                     │              │
│  │  • Dual-engine pipeline                         │              │
│  │  • Pipeline orchestrator                        │              │
│  └───────────────────────┬───────────────────────┘              │
│                          │                                       │
├──────────────────────────┼──────────────────────────────────────┤
│                    ENGINE LAYER                                  │
│                          │                                       │
│  ┌───────────────────────▼───────────────────────┐              │
│  │         Confidence-Weighted Merge              │              │
│  │  output = (conf_A * A + conf_B * B) / (A + B)  │              │
│  └──────────┬────────────────────┬───────────────┘              │
│             │                    │                                │
│  ┌──────────▼──────┐  ┌────────▼────────────┐                  │
│  │   Motor A        │  │   Motor B            │                  │
│  │   (Deterministic)│  │   (ML Inference)     │                  │
│  │                  │  │                      │                  │
│  │  • Rule engine   │  │  • Groq (free)       │                  │
│  │  • Math formulas │  │  • OpenAI            │                  │
│  │  • Always works  │  │  • Unsloth (local)   │                  │
│  │  • Fast (<1ms)   │  │  • 9 providers       │                  │
│  └──────────────────┘  └──────────────────────┘                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Module Architecture

Each of the 17 modules follows the same pattern:

```python
class ModuleState:
    """Base state machine for a ZICORE module."""
    
    def __init__(self):
        self.status = "nominal"
        self.last_update = time.time()
        self.parameters = {...}
    
    def update(self, data: dict):
        """Update module state from inference output."""
        self.parameters.update(data)
        self.last_update = time.time()
    
    def model_dump(self) -> dict:
        """Export state as dictionary."""
        return {
            "name": self.name,
            "status": self.status,
            **self.parameters
        }
```

### Module Categories

| Category | Modules | Purpose |
|----------|---------|---------|
| Navigation | ZiNav, GPDEngine | Trajectory, orbital mechanics, docking |
| Life Support | ZiHab, ZIEco, ZIMed | Habitat, ecology, medical |
| Power & Propulsion | ZiPower, ZiShip, ZiCRIOGEN | Energy, hull, cryogenic |
| Robotics | ZIDrone, ZIRobot | Drones, manipulators |
| Communications | ZIComm, ZILink | RF, optical, data links |
| Computing | ZiCoreX, ZIVR | AI inference, VR |
| Security | ZISec, ZiMAURY | Cybersecurity, defense |
| Manufacturing | Z-TY Factory | Parametric aircraft design |

---

## Data Flow

```
1. User Input
   │
2. Intent Classification (keyword matching)
   │
3. Module Selection (based on intent)
   │
4. Dual-Engine Inference
   │
   ├── Motor A: Deterministic rules → confidence: 0.95
   │
   └── Motor B: ML inference → confidence: 0.80
   │
5. Confidence-Weighted Merge
   │
6. Output Generation
   │
7. Knowledge Base Update
   │
8. WebSocket Streaming (word-by-word)
   │
9. Frontend Display
```

---

## WebSocket Protocol

```
Client → Server:
{
  "command": "stream",
  "payload": {
    "message": "Analyze trajectory",
    "module": "zinav",
    "session_id": "webui"
  }
}

Server → Client:
{"type": "stream_start", "message": ""}
{"type": "stream_chunk", "chunk": "Computing "}
{"type": "stream_chunk", "chunk": "Hohmann "}
{"type": "stream_chunk", "chunk": "transfer..."}
{"type": "stream_end", "intent": "trajectory", "outputs": {...}}
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Vanilla JS | No frameworks, direct DOM manipulation |
| 3D Graphics | Three.js r128 | WebGL viewport, mesh rendering |
| Audio | Web Audio API | Real-time waveform visualization |
| Camera | getUserMedia | Webcam capture |
| Backend | FastAPI + uvicorn | Async Python API |
| WebSocket | websockets | Real-time streaming |
| Database | JSON files | Knowledge base, config, missions |
| ML Engine | Unsloth + transformers | LLM fine-tuning and inference |
| Deployment | Cloudflare Tunnel | Public URL without port forwarding |
| Container | Docker + Nginx | Production deployment with SSL |

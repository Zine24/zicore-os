# ZICORE SYSTEM v5.0 — Master Context

> **Any AI working on this project MUST read this file first.**
> This is the single source of truth for ZICORE's architecture, philosophy, and scope.

---

## PROJECT IDENTITY

**ZICORE SYSTEM** (ZICORE Command System) is a **digital aerospace operating system**, not a chatbot.

It is the neural core of **ZiAerospace** — an ecosystem capable of controlling simulations, engineering modules, autonomous spacecraft, lunar infrastructure, AI assistants, robotics, digital twins, manufacturing systems, mission planning, and future aerospace vehicles.

**ZIO** is the AI copilot — one subsystem among many, not the center of the system.

---

## ORGANIZATION

### Zi Group — Divisions

| Division | Purpose |
|----------|---------|
| **ZiCore** | Central OS, core architecture |
| **ZiAerospace** | Aerospace vehicles, missions, infrastructure |
| **ZiLaunch** | Launch operations, countdown, Go/No-Go |
| **ZiDefense** | Military aerospace, recon, tactical |
| **ZiLab** | Research, experiments, scientific computing |
| **ZiEnergy** | Power systems, reactors, solar, RTG |
| **ZiRobotics** | Autonomous robots, rovers, manipulators |
| **ZiSimulation** | Flight sims, orbital mechanics, physics |
| **ZiCodex** | Knowledge base, space database, docs |
| **ZiEngineering** | Structural analysis, CAD, manufacturing |
| **ZiMission Control** | Mission planning, telemetry, ground ops |

---

## SOFTWARE ARCHITECTURE

```
┌─────────────────────────────────────────────────────────┐
│                    ZICORE CORE                          │
│          (REST API + WebSocket + State Engine)          │
├──────────┬──────────┬──────────┬──────────┬─────────────┤
│   ZIO    │ Material │ Mission  │  Flight  │ Engineering │
│    AI    │  izer    │ Control  │   Sim    │   Modules   │
├──────────┼──────────┼──────────┼──────────┼─────────────┤
│ Telemetry│  Space   │   3D     │  Games   │  Settings   │
│  Engine  │ Database │  Engine  │  Center  │   & Config  │
└──────────┴──────────┴──────────┴──────────┴─────────────┘
         ↕                ↕                ↕
   ┌──────────┐    ┌──────────┐    ┌──────────┐
   │  .85     │    │  .68     │    │  Future  │
   │ Primary  │    │ Ollama   │    │  Nodes   │
   │ Server   │    │ Server   │    │          │
   └──────────┘    └──────────┘    └──────────┘
```

Every module communicates through ZICORE Core. Modules can operate independently.

---

## CORE MODULES (Complete List)

### AI & Intelligence
- **ZIO** — Conversational AI (OpenRouter + Ollama fallback)
- **ZIO Copilot** — Mission AI, flight engineer, scientist by context
- **Computer Vision** — Image/video analysis, OCR
- **Knowledge Base** — Persistent docs, search, ZiCodex

### 3D & Manufacturing
- **Materializer** — Procedural 3D generation engine (14+ types)
- **OpenSCAD Generator** — Programmatic CAD (SolidPython2 bindings)
- **Mesh Generator** — STL/OBJ/GLB export (trimesh[easy])
- **CAD Generator** — Parametric design (CadQuery + Build123d)
- **3D Printing** — Direct manufacturing integration
- **PicoGK Engine** — Voxel/level-set modeling (PicoPie), lattices, TPMS, implicit surfaces
- **Mesh Processing** — Open3D + PyMeshLab (repair, simplify, reconstruct)
- **Voronoi Engine** — 3D Voronoi tessellation for lattice/lightweight structures
- **AI 3D Generation** — Tripo3D/Meshy cloud APIs for concept generation (Hunyuan3D when GPU available)

### Engineering
- **Structural Analysis** — Stress, buckling, fatigue, safety factors
- **Aerodynamics** — Lift, drag, Mach, heating, CFD placeholders
- **Propulsion Lab** — All propulsion systems (chemical to fusion)
- **Vehicle Designer** — Unlimited vehicle templates
- **Rocket Designer** — Full launch vehicle design
- **Payload Bay Manager** — Mass, volume, deployment
- **Drone Designer** — Autonomous UAV systems
- **Robot Designer** — Robotic manipulators

### Mission Control
- **Mission Planner** — Sequence planning, timelines
- **Launch Operations Console** — Countdown, Go/No-Go, checklists
- **Ground Station Control** — Antennas, telemetry, tracking
- **Constellation Manager** — Multi-satellite control
- **Mission Replay** — Full mission reconstruction
- **Flight Recorder** — Digital black box

### Space Operations
- **Orbital Mechanics** — Hohmann, bi-elliptic, gravity assists
- **Trajectory Optimizer** — Delta-V, transfers, escape
- **Navigation** — Celestial nav, star tracking
- **Autonomous Docking** — Station rendezvous
- **Life Support Simulator** — O₂, CO₂, water, pressure, temp
- **Cryogenics** — Cryogenic preservation systems

### Environment
- **Physics Engine** — Gravity, atmosphere, vacuum, collisions
- **Weather Engine** — Atmospheric conditions
- **Space Weather Center** — Solar wind, geomagnetic storms, radiation
- **Terrain Generator** — Procedural planetary surfaces
- **Real Star Map** — Stellar catalogs, constellations
- **Orbital Debris Tracking** — Collision alerts

### Power & Resources
- **Power Management** — Solar panels, batteries, RTG, reactors
- **ISRU** — In-Situ Resource Utilization (Lunar/Mars production)

### Surface Operations
- **Lunar Surface Operations** — Base, mining, construction
- **Mars Surface Operations** — Habitat, terraforming prep
- **Rover Control** — Surface exploration

### Communications
- **Signal Processing** — Data encoding, compression
- **Satellite Control** — Orbit, attitude, payloads
- **Communications** — Deep space network

### Data & Research
- **Space Database** — Launch vehicles, engines, satellites, missions
- **Research Database** — Scientific papers, experiments
- **Telemetry** — Real-time data streams
- **Digital Twin** — Real-time synchronized simulation

### Training & Games
- **Training Simulator** — Pilot/astronaut training
- **Game Center** — 14+ HTML5 games with leaderboards

---

## SPACE VEHICLES

### Supported Types (Unlimited Templates)

| Category | Examples |
|----------|----------|
| **Launch** | Reusable rockets, heavy lift, small sat |
| **Crew** | Capsules, spaceplanes, crew transfer |
| **Cargo** | Resupply, deep space probes |
| **Lunar** | Moon landers, lunar orbiters, rovers |
| **Mars** | Mars landers, surface habitats |
| **Orbital** | Tugs, stations, platforms |
| **Deep Space** | Interplanetary ships, generation ships |
| **Recon** | Surveillance satellites, EO/IR |
| **VTOL** | Hypersonic vehicles, spaceplanes |
| **Autonomous** | Drone swarms, robotic craft |
| **Experimental** | Fusion ships, antimatter, photon sail |

### Vehicle Properties

Every vehicle must support:
- Mass, Dimensions, Center of Gravity
- Propulsion type & configuration
- Fuel type & capacity
- Payload mass & volume
- Crew capacity & life support
- Landing gear configuration
- Navigation & avionics
- Power system (solar, battery, RTG, reactor)
- Thermal control system
- Material composition
- Simulation parameters

---

## PROPULSION SYSTEMS

| Category | Types |
|----------|-------|
| **Chemical** | LOX/RP1, LOX/LH2, Methalox, Hypergolic, Solid, Hybrid |
| **Electric** | Ion, Hall Effect, VASIMR, MPD |
| **Nuclear** | Nuclear Thermal, Nuclear Electric |
| **Advanced** | Fusion, Antimatter, Photon, Solar Sail, Beamed |
| **Experimental** | Alcubierre, EM Drive (placeholders) |

---

## ENGINEERING CALCULATIONS

- Mass, Volume, Density, Pressure, Temperature
- Heat Transfer, Specific Impulse, Delta-V, TWR
- Orbital Energy, Escape Velocity, Orbital Transfer
- Rocket Equation (Tsiolkovsky)
- Stress, Buckling, Fatigue, Structural Safety
- Center of Pressure, Aerodynamic Coefficients
- Lift, Drag, Mach Number, Heating Rate
- CFD placeholders, Finite Element placeholders

---

## SIMULATION ENVIRONMENTS

### Celestial Bodies
Earth, Moon, Mars, Europa, Titan, Venus, Mercury, Asteroids, Kuiper Belt

### Orbital Regimes
LEO, MEO, GEO, Lagrange Points (L1-L5), Deep Space, Cislunar, Interplanetary

### Physics
Gravity (N-body), Atmosphere (varied), Vacuum, Wind, Temperature
Solar Radiation, Orbital Mechanics, Collisions, Fuel Consumption, Structural Failure

---

## 3D MATERIALIZER — Generator Types

Cube, Sphere, Cylinder, Cone, Capsule, Rocket, Terrain, Pipe, Gear, Star
Parametric Surface, OpenSCAD, Mesh, Heightmap
Spacecraft Hull, Engine Nozzle, Landing Legs, Solar Panels
Satellite Bus, Space Station Modules, Procedural Rockets

---

## ZIO AI — Provider Stack

| Priority | Provider | Default Model | Notes |
|----------|----------|---------------|-------|
| 1 | OpenRouter | `nvidia/nemotron-3-super-120b-a12b:free` | Primary, free tier |
| 2 | Ollama (.68) | `gemma3:1b` | Local fallback |
| 3 | Ollama (.85) | `gemma3:1b` | Secondary fallback |
| 4 | Future | — | Additional providers |

### ZIO Capabilities
- Conversation history & memory
- Chat Import/Export (ChatGPT, Grok, Claude, Gemini, DeepSeek)
- Session Manager
- Knowledge Search
- Engineering Assistant
- Scientific Assistant
- Mission Planner
- Programming Assistant
- Dual Engine (Deterministic + ML inference)

---

## SETTINGS — 11 Tabs

General | Providers | ZIO | Materializer | Network | Ollama | Engineering | Theme | System | **MODELS** | **CHATS**

- **MODELS tab**: Friendly names, provider, speed, memory, capabilities, context window. Free models highlighted green.
- **CHATS tab**: Import files, chat history, sessions grouped by session_id.

---

## NETWORK TOPOLOGY

```
┌─────────────────────────────────────────┐
│          Cloudflare Tunnel              │
│    zcs.zicore.space  (Mission Control)  │
│    zicore.space                         │
│    zinemotion.com.mx  (Portal)          │
│    mail.zinemotion.com.mx (Mail)        │
└────────────┬────────────────────────────┘
             │
    ┌────────┴────────┐
    │                 │
┌───▼────┐     ┌─────▼───┐
│  .85   │────▶│  .68    │
│Primary │     │ Ollama  │
│Server  │     │ Server  │
│        │     │         │
│:4000   │     │:11434   │
│Web UI  │     │13 models│
│Material│     │         │
│Games   │     │Heartbeat│
│Settings│     │Fallback │
└────────┘     └─────────┘
```

### Primary Server (.85)
- **IP**: 192.168.1.85
- **OS**: Ubuntu x86_64
- **CPU**: Xeon E5345 (4C no HT)
- **RAM**: 8GB
- **GPU**: GT 230 OEM (CC 1.1, no compute)
- **Disk**: 93% (16GB free)
- **Services**: zicore-materializer (port 4000), Ollama (6 models), cloudflared

### Secondary Server (.68)
- **IP**: 192.168.1.68
- **OS**: Ubuntu x86_64
- **CPU**: i3-550 (2C/4T)
- **RAM**: 13GB
- **GPU**: Intel integrated (no compute)
- **Disk**: 59GB free
- **Services**: Ollama primary (13 models)
- **SSH**: zinemotion / Jilo1981

---

## MISSION CONTROL — Dashboard Elements

Vehicle status | Telemetry | Mission timer
Altitude | Velocity | Acceleration | G-force
Fuel | Battery | Power | Communications
Weather | Orbital parameters | Trajectory | Target
Mission logs | Warnings | AI status | Subsystem health
CPU | RAM | Network | Connected nodes

---

## VISUAL IDENTITY

- **Inspired by**: NASA, SpaceX, Blue Origin mission control
- **Style**: Dark aerospace cockpit, glass HUD, blue holograms
- **Colors**: `#00e5ff` (primary), `#7c4dff` (purple), `#00ff88` (green), `#04060c` (background)
- **Fonts**: System UI, monospace for telemetry
- **Animations**: Particles, scanlines, 3D rotating hex logo, pulse effects
- **HUD Elements**: Status bar, module indicators, real-time clock

---

## 3D TOOLS STACK — CPU-Compatible Libraries

> **All tools below run on CPU (no GPU required) unless noted.**

### Core Mesh Library
| Tool | Purpose | Install |
|------|---------|---------|
| **trimesh[easy]** | Mesh I/O, primitives, booleans, voxels | `pip install trimesh[easy]` |

### Parametric CAD (OpenCASCADE kernel)
| Tool | Purpose | Install |
|------|---------|---------|
| **CadQuery** | Parametric CAD scripting (method chaining) | `pip install cadquery` |
| **Build123d** | Modern parametric CAD (context managers) | `pip install build123d` |
| **SolidPython2** | OpenSCAD bindings (CSG via Python) | `pip install solidpython2` |

### Voxel/Implicit Modeling
| Tool | Purpose | Install |
|------|---------|---------|
| **PicoGK/PicoPie** | Voxel/level-set, lattices, TPMS, implicit SDF | `pip install picopie` |

### Mesh Processing
| Tool | Purpose | Install |
|------|---------|---------|
| **Open3D** | Point clouds, mesh reconstruction, ICP | `pip install open3d-cpu` |
| **PyMeshLab** | 400+ mesh filters (repair, simplify, remesh) | `pip install pymeshlab` |

### Lattice/Voronoi
| Tool | Purpose | Install |
|------|---------|---------|
| **lattice300** | Voronoi/Delaunay lattice generation | `pip install gmsh` |
| **mesh-voronoi** | 3D Voronoi cell partitioning | Script (GitHub) |

### Cloud AI 3D (API, no local GPU needed)
| Tool | Purpose | Install |
|------|---------|---------|
| **Tripo3D** | Text/image-to-3D (free tier: 300 credits/mo) | `pip install tripo3d` |
| **Meshy AI** | Text/image-to-3D (REST API) | `requests` |
| **Rodin Gen-1** | Image-to-3D (REST API) | `curl`/`requests` |

### GPU-Required (future GPU server only)
| Tool | Purpose | Status |
|------|---------|--------|
| **Hunyuan3D 2.1** | Image-to-3D + texture (Tencent) | In codebase, trimesh fallback |
| **TRELLIS** | Text/image-to-3D (Microsoft, 2B params) | Needs 16GB+ VRAM |
| **InstantMesh** | Image-to-3D (TencentARC) | Needs CUDA 12.1+ |
| **Shap-E** | Text-to-3D (OpenAI) | Slow on CPU, viable |

---

## ADVANCED MODULES (Future)

| Module | Description |
|--------|-------------|
| **Mission Timeline** | Sequence planner, event scheduling |
| **Launch Operations Console** | Countdown, Go/No-Go, checklists |
| **Ground Station Control** | Antenna tracking, telemetry downlink |
| **Constellation Manager** | Multi-satellite fleet control |
| **Orbital Debris Tracking** | conjunction assessment, collision avoidance |
| **Space Weather Center** | Solar wind, GCR, SPE alerts |
| **Trajectory Optimizer** | Hohmann, bi-elliptic, gravity assist |
| **Life Support Simulator** | ECLSS modeling |
| **Power Management** | Solar arrays, batteries, RTG, reactors |
| **FDIR** | Fault Detection, Isolation, Recovery |
| **Autonomous Docking** | Rendezvous, proximity operations |
| **Payload Bay Manager** | Mass budget, deployment sequences |
| **Crew Health Monitor** | Biometrics, radiation dose |
| **Digital Twin** | Real-time vehicle/system sync |
| **Mission Replay** | Full reconstruction from flight data |
| **Flight Recorder** | Digital black box, post-incident analysis |
| **Real Star Map** | Stellar catalogs, navigation stars |
| **Celestial Navigation** | Star tracker simulation |
| **Lunar Surface Ops** | Base construction, mining, ISRU |
| **Mars Surface Ops** | Habitat, resource extraction |
| **ISRU** | In-Situ Resource Utilization |
| **Rocket Engine Test Stand** | Engine simulation & analysis |
| **Mission AI Copilot** | Context-aware ZIO (pilot/engineer/scientist) |

---

## DESIGN PRINCIPLES

1. **Modularity** — Every module is independent, communicates via Core
2. **Scalability** — Add new modules without redesign
3. **Future Deployment** — Architecture supports real spacecraft control
4. **Professional Standards** — NASA/ESA-grade engineering practices
5. **No Hard Limits** — Everything configurable and extensible
6. **REST + WebSocket** — Every module exposes API endpoints
7. **Maintainable Code** — Document APIs, never break existing functionality
8. **Future Compatibility** > Short-term implementation

---

## CURRENT STATE (v5.0.0)

### Deployed & Working
- **Mission Control dashboard** (zcs.zicore.space) — real-time telemetry, system status, missions, nodes, modules, alerts
- **ZineMotion portal** (zinemotion.com.mx) — cinematic landing page with module cards
- **ZICORE main menu** (/zicore) — legacy 6-card launcher
- ZIO AI chat (OpenRouter free models, Ollama fallback)
- Chat import (ChatGPT, Grok, Claude, Gemini, DeepSeek formats)
- 14 HTML5 games with leaderboard
- 11-tab settings (General, Providers, ZIO, Materializer, Network, Ollama, Engineering, Theme, System, Models, Chats)
- 14 parametric 3D generators
- Materializer web server (port 4000)
- Cloudflare tunnel (zcs.zicore.space, zinemotion.com.mx)
- Aerospace module (/aerospace) — 5 tabs: Vehicles, Propulsion, Orbital, Engineering, Missions
- Mail portal (/mail) — inbox, compose, user management

### In Progress
- mail.zinemotion.com.mx (DNS configured, needs Cloudflare ingress hostname)
- zinemotion.com.mx template refinement
- OpenCode API key renewal (current key 403)

### Not Started
- Most advanced aerospace modules (Mission Control calculations, Orbital Mechanics live, etc.)
- Heartbeat between .85 and .68
- Distributed compute

---

## FILE STRUCTURE

```
zicore-system/
├── AGENTS.md              ← THIS FILE (master context)
├── web_server.py          ← Main backend (~3000 lines, all API routes)
├── frontend/
│   ├── mission-control.html ← Mission Control dashboard (main hub)
│   ├── index.html         ← Main menu (6 cards)
│   ├── dashboard.html     ← Cockpit hub
│   ├── zio.html           ← AI chat + import
│   ├── flight-sim.html    ← Flight simulator
│   ├── simulator.html     ← Generic simulator
│   ├── games.html         ← 14 games + leaderboard
│   ├── multimedia.html    ← Audio/video/image library
│   ├── settings.html      ← 11 tabs
│   └── ...
├── data/
│   ├── config/
│   │   └── zio_config.json
│   └── games_scores.json
├── agent/                 ← ZIO agent modules
│   ├── core.py
│   ├── zio_personality.py
│   ├── content3d.py
│   ├── generator.py
│   ├── media.py
│   ├── voice.py
│   └── state.py
└── ...
```

---

## DEPLOYMENT

### Server .85
- Service: `zicore-materializer.service` (root, port 4000)
- Config: `/opt/zicore-materializer/data/config/zio_config.json`
- Frontend: `/opt/zicore-materializer/frontend/`

### Cloudflare
- Tunnel: `88ba5f49-87f1-4f33-9b14-23a074a798a1` (zmmx-core)
- Hostnames: zicore.space, api.zicore.space, zzz.zicore.space, zcs.zicore.space, zinemotion.com.mx

---

## MEDIA STORAGE

Media files (audio, video, images, music) are served from `MEDIA_DIR`, configurable via:

| Method | Mechanism |
|--------|-----------|
| **Environment variable** | `ZICORE_MEDIA_DIR=/path/to/media` |
| **Default** | `<project_root>/data/media/` |

### Current Setup (Local Dev)
- Location: `C:\Users\zinem\Documents\zicore-system\data\media\`
- Categories: `audio/`, `video/`, `images/`, `music/`
- Content: Generated sounds, ZIO vision outputs, procedural images

### Server Setup (.85) — zicore-fs
- Location: `/mnt/zicore-fs/ZiCoreFS/media/`
- Configured via: `ZICORE_MEDIA_DIR` env var in systemd override
- Benefits: Separates storage from app code, avoids filling system disk (93% full)
- Setup: Run `C:\Users\zinem\AppData\Local\Temp\opencode\setup_zicorefs_media.py`

### SSH
- `.85`: `z@192.168.1.85` (alias `zicore`)
- `.68`: `zinemotion@192.168.1.68` (alias `zicore2`, pw `Jilo1981`)

---

*This file defines the complete ZICORE vision. Any AI or developer reading it should understand that ZICORE is a full aerospace operating system, not just a web app with chat.*

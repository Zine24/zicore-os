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
- **Launch pad** (/zicore-os) — Deploy Console embebida para el stack `start_all.py` (polling `/api/system/startall/status`)
- **Master Creator** (https://mc.zicore.space/master-creator, público) — Creator Art Studio estilo NightCafe: lienzo central + sidebar de estudios (Nano Banana, Rodin, NightCafe, Engineering→Blender), 14 presets de estilo visuales de Nano Banana, galería `localStorage` (`zc_mc_gallery`), visor 3D `model-viewer`, capas de lienzo, telemetría, deploy start_all y 17 módulos de misión en vivo
- ZIO AI chat (OpenRouter free models, Ollama fallback)
- Chat import (ChatGPT, Grok, Claude, Gemini, DeepSeek formats)
- 14 HTML5 games with leaderboard
- 11-tab settings (General, Providers, ZIO, Materializer, Network, Ollama, Engineering, Theme, System, Models, Chats)
- 14 parametric 3D generators
- Materializer web server (port 4000)
- Cloudflare tunnel (zcs.zicore.space, mc.zicore.space, zinemotion.com.mx)
- Aerospace module (/aerospace) — 5 tabs: Vehicles, Propulsion, Orbital, Engineering, Missions
- Mail portal (/mail) — inbox, compose, user management
- Portal de descargas (/installers + /downloads) — installers, APK, ZioUnified, docker-compose, OEM setup
- **Heartbeat 2-nodos** — `_node_heartbeat()` cacheado (15s) sobre `ZICORE_NODE_BASE_URL` (default `http://192.168.1.68:4000`); expuesto en `/api/node/heartbeat` (público), `/api/system/stats` (clave `node`) y `/api/diagnostics/run` (check `network`)
- **Portales por subdominio `*.zicore.space`** — routing por `Host` en `serve_main_menu` (`web_server.py`): `zio`, `aerospace`, `materializer`, `engineering`, `games`, `zmmx`, `mail`, `zicodex`, `zivault`, `mc`, `zcs` → cada subdominio sirve SOLO su módulo; catch-all `*zicore.space` → `frontpage.html`. Todos verificados 200 público vía túnel `zicore-kernel` (wildcard `*.zicore.space → localhost:8000` en `/etc/cloudflared/config.yml`). `zmmx.zicore.space` y `zivault.zicore.space` añadidos a DNS del túnel el 2026-08-07.
- **SSO login + token universal por usuario** — `/api/sso/login` (usuario actual `admin`/`12345678`, rol admin, sin 2FA; el API deriva username del local part del email). Token por usuario `zc_`+`secrets.token_urlsafe(32)` (`zicore/sso.py`: migración columna `api_token`, métodos `generate/get/revoke/verify_api_token`; nunca se expone el token plano, solo `has_api_token`/`api_token_created_at`). `SSOAuthMiddleware` acepta `Authorization: Bearer` o `X-API-Key`. Endpoints: `GET /api/sso/token`, `POST /api/sso/token/generate`, `POST /api/sso/token/revoke`. Protegido por token: `GET /api/media/library` (catálogo unificado local+zicore-fs+jilocomotion, `limit` max 200, `share_url` absoluto). Los serve públicos: `/api/media/serve`, `/media/`, `/media-fs/`, `/api/jilocomotion/serve`.
- **Share en ZMMX** — botón 🔗 en lista/cuadrícula (`frontend/zmmx.html`): usa `navigator.share` si existe, si no copia el enlace absoluto al portapapeles con toast `zmmx-toast`.
- **ZMMX v2 — Volúmenes, streaming con transcode y share cifrado (desplegado VPS, 2026-08-08)** — volúmenes: `_detect_volumes()` (scan `/proc/mounts` + `/media`,`/run/media`,`/mnt`; excluye raíces integradas y `/run/user`; caché 10s), `/api/zmmx/volumes`, drives `volume:true` integrados a `/api/zmmx/drives` y `/api/zmmx/dir` (ids `vol_<name>`), sección "Volúmenes" en el árbol (`renderTree`, dot `.dot-vol`). Streaming: `/api/zmmx/stream` con `_stream_resolved()`; nativos (mp3/wav/m4a/aac/ogg, mp4/webm/ogv) → Range directo (`_serve_file_with_range`); no nativos (audio flac/aiff/wma/opus/amr/ape/alac/mid; video mkv/avi/mov/m4v/ts/m2ts/mpg/wmv/flv/3gp/ogm/vob) → ffmpeg pipe a stdout (`libmp3lame -b:a 192k` audio→MP3, `libx264 veryfast zerolatency +frag_keyframe+empty_moov+default_base_moof` video→fMP4 + `aac 128k`); `transcode=1` fuerza; `_transcode_ffmpeg(command, media_type=...)` fija Content-Type correcto (`audio/mpeg`/`video/mp4`). Share cifrado: secreto HMAC-SHA256 persistido en `data/config/zmmx_share_key`, token `_sign_share` con payload `source|path|exp` (TTL 1–90 días, default 30), `_verify_share` con `hmac.compare_digest`; `GET /api/zmmx/share/link` → `{url, share_url, expires}`; `GET /api/zmmx/share/{token}` sirve SOLO ese archivo (403 inválido/expirado), `?stream=1` reutiliza `_stream_resolved`. Frontend: `ZMMX.utils.transcodable`/`streamUrl` (listas ext = backend), playerbar/video usan `streamUrl` (transcode=1 para no nativos), archivos transcodables playables con badge `↻` (`.codec-badge.tx`), `shareFile` abre panel con token firmado, fallback a URL directa si falla. Verificado: drives 200, volumes 200, share válido 200 / token malo 403, share+stream 200 `video/mp4` con `ftyp`, harness jsdom sin errores. `.85` sigue offline en Tailscale → su disco no montable desde VPS hasta que vuelva.
- **Puertos configurables vía env** — `start_all.py` y `web_server.py` leen `ZICORE_API_PORT/WEB_PORT/GAMES_PORT/MUSIC_PORT`. Defaults embebidos: 9080/9090/9091/9092. En `.85` el override systemd (`/etc/systemd/system/zicore-materializer.service.d/ports.conf`) fija 4080/4000/4001/4002 (producción).
- **Node.js Engineering System (Node platform pre-aerospace)** — `/opt/zicore-os` (copia desplegada; maestro en `/mnt/zicore-fs/ZiCore/ZIO/ZiCore`). Stack Next.js + REST API `ZiRestServer` con **Noyron** (6 plantillas: heat_exchanger, bracket, lattice_block, mechanical_part, vase, freeform), **EngineeringPipeline** (noyron→picogk→slice→print), **PicoGKBridge** (dotnet opcional, fallback JS GeometryEngine), más ZiMail/ZiVPS/ZiBank/ZiCrypto/Obsidiana portales (4100-4105) y ZiGateway (4109). **Público en `https://zicore-os.zicore.space/`** (túnel Cloudflare `aa7670b0` → `localhost:3000`, config `/etc/cloudflared/zicore-os.yml` + systemd `cloudflared-zicore-os.service`). Servicio persistente: **`zicore-engineering.service`** (systemd, `ENG_PORT=3000`, WorkingDirectory `/opt/zicore-os`). Arranque manual (cmd en `.85`): `cd /opt/zicore-os && node scripts/start-engineering.js` (puerto 3000, `ENG_PORT` para cambiar). API: `POST /api/engineering/generate`, `GET /api/engineering/status/:taskId`, `GET /api/engineering/download/:taskId/:type`, `/api/engineering/noyron/templates`. **WebSocket bridge** montado sobre el mismo `:3000` en `/ws` (túnel Cloudflare proxea upgrade): `wss://zicore-os.zicore.space/ws`; mensajes `ping`, `status`, `generate`, `task.status`, `templates`; reenvía eventos `engineering:start/progress/complete/error` en tiempo real. Outputs en `/opt/zicore-os/data/picogk/`. No toca el stack Python.
- **Engineering daemon VPS (desplegado, reescrito en Node puro)** — `/opt/zicore-os` en el VPS (reconstruido desde cero porque `.85` quedó inaccesible; misma API que el original). **Cero dependencias** (`server.js` + `lib/mesh.js` + `lib/noyron.js` + `package.json`), sirve los mismos 4 endpoints (`templates`/`generate`/`status/:id`/`download/:id/:type`), **6 plantillas Noyron** (heat_exchanger, bracket, lattice_block TPMS gyroid por marching tetrahedra, mechanical_part engranaje, vase lathe, freeform blobs), exporta **STL binario + GLB (glTF2)** reales, y WebSocket bridge `/ws` (RFC6455 mínimo, mensajes ping/templates/status/generate/task.status). Servicio systemd **`zicore-engineering.service`** (port 3000, user oracle-admin, WorkingDirectory `/opt/zicore-os`, outputs en `/opt/zicore-os/data/picogk/`). Verificado: `https://mc.zicore.space/api/creator/status` → `engineering_online: true`, y el flujo público completo generate→status→download STL 200. El túnel `zicore-kernel` mapea `mc.zicore.space → localhost:8000` (backend Python), por lo que `/ws` público NO pasa por el túnel (el frontend usa polling HTTP, no WS). El proxy Python sigue en `ENGINEERING_BASE=http://127.0.0.1:3000`.
- **CAPCOM Console (desplegado VPS, 2026-08-13)** — consola mission-control integrada en `frontend/videochat.html` (el dashboard WebRTC existente). Extensión del agente ZIO: `zicore/capcom.py` (system prompt CAPCOM Capsule Communicator, catálogo `COMMANDS`: system_stats, startall_status/start/stop, system_update, service_restart, vr_status, nav_status + `VOICE_COMMANDS`/`resolve_voice`); `agent/core.py` `_persona_prompt(persona, knowledge_ctx)` con fallback al prompt base, aplicado en `process()` vía `context['persona']`. Endpoints en `web_server.py`: `GET /api/capcom/status` [público: telemetría sim + `_system_stats_sync` + `vr_monitor_stats` + nav/waypoints], `POST /api/capcom/nav` [auth: add/remove/reset + heading/altitude/speed/target], `POST /api/capcom/command` [admin, whitelist `COMMANDS`, ejecución real (systemctl/subprocess) y registro en knowledge_base session `capcom`]. `persona` aceptado en WS `/ws/zio` (stream y chat) y `POST /api/chat`; `/api/capcom/` añadido a `SSOAuthMiddleware.PUBLIC_PREFIXES`. UI: slider/slider de la sidebar izquierda (collapse overlay), panel CAPCOM con tabs Consola (gauges CPU/RAM/DISK, telemetría misión, navegación waypoints) / Sistema (Start All / Stop All / Restart / Update / VR Status con confirm) / Voz (Web Speech API → `/api/capcom/command` o chat, TTS opcional) / Chat (WS `/ws/zio` persona capcom, streaming, burbujas estilo ZIO), overlay VR `/vr-monitor`. Verificado producción: status 200 público, nav 401 sin auth / 200 con auth (add/remove/reset), command 200 admin con reply mission-grade (Ollama ON) / 400 comando desconocido / 401 sin token, `/videochat` y `/vr-monitor` 200.
- **GeoTrack device layer — Z-Device-Key (desplegado VPS, 2026-08-13)** — tabla `geo_devices` en `data/geo.db` (`zicore/geo.py`): `name, type, token_hash UNIQUE (sha256), owner_id, owner_name, active, meta, created_at, last_seen`. Registro vía `POST /api/geo/devices` [auth, cuota por plan: free=5, pro=20, admin=0=ilimitado], devuelve token `zc_dev_`+`secrets.token_urlsafe(24)` UNA sola vez. Trackers sin cuenta reportan a `POST /api/geo/device/report` y `GET /api/geo/device/latest` (públicos, prefijo `/api/geo/device/` en `SSOAuthMiddleware.PUBLIC_PREFIXES`) con header `Z-Device-Key`; puntos con `user_id=0`, `source/app='device'`, excluidos de `latest_all()`/`stats()`. `GET /api/geo/devices` [auth] lista con `lat/lon/last_seen` del último punto; `DELETE /api/geo/devices/{id}` [auth, owner o admin]. Dashboard `/geo`: card "Dispositivos rastreados" (form nombre+tipo, modal con token, copiar, revocar) y marcadores ámbar en Leaflet. Verificado producción: create 200, report 200 (GeoIP Mexico City), latest 200, list con pos, 401 sin token.
- **ZIO Agent V2 — Multimodal Agentic System (desplegado .68, 2026-08-17)** — `/home/zinemotion/zio-agent-v2/`, FastAPI en puerto 8201, servicio systemd `zio-agent-v2.service`. Pipeline completo: perceive→interpret→reason→decide→execute→observe→correct. AgentRouter clasifica 6 intents (vision/chat, vision/detect, 3d/generate, memory/*, web/*, media/*). LLMPipeline vía Ollama gemma3:1b (~35-65s en i3-550). EmbeddingPipeline con SentenceTransformer all-MiniLM-L6-v2 (384-dim, local). QdrantMemory (Docker :6333, collection `zio_knowledge`). PostgresMemory (Docker :5432, tables sessions/messages/tool_history). 6 tools ejecutables: vision_analyze, vision_detect, speech_transcribe, tts_speak, memory_search, web_search. JobManager con ResourceMonitor (14GB RAM cap, max 2 heavy concurrent). Chat API (`POST /api/agent/v2/chat`), WebSocket (`/api/agent/v2/ws`), Vision API (`POST /api/agent/v2/vision/analyze`). Frontend chat UI dark-theme aerospace en `/`. Verificado: E2E chat→LLM→embedding→Qdrant store 200 OK, memory_search con scores 0.67-0.70, tool execution via job manager. Pendiente: Cloudflare tunnel `agent.zicore.space` (DNS routed, necesita ingress en CF Zero Trust dashboard).

### In Progress
- mail.zinemotion.com.mx (DNS configured, needs Cloudflare ingress hostname)
- zinemotion.com.mx template refinement
- Fallback/Heartbeat en frontends (indicator en settings → Network; replicar en mission-control/ecosystem)
- Rediseño futurista de `aerospace.html` (temática, eficiencia, funcionalidad)
- Fix VR monitor bugs (mirror portrait, sensor cube rotation, dead code cleanup)
- Apollo 11 program en solar navigation (`/solar-navigation`)

### Done (2026-08-13 → 2026-08-17)
- **OpenCode API key renewal** — key renovada `sk-Kj...` validada HTTP 200 (412 models). Config `opencode.jsonc` corregido con modelos VPS reales (`qwen2.5:1.5b`, `gemma3:1b`, `tinyllama:latest`, `deepseek-coder:1.3b`).
- **APK `com.zicore.system` rebuild** — RESUELTO: fix `expo-font@13.0.4`, build OK (15m39s), `app-release.apk` 87.6MB vCode 500, instalado en Huawei MAR-LX3A. Clave: detener `zicore-ai3d-worker` durante build.
- **VR monitor v5.2** — horizonte por gravedad (`gravityAttitude()`), consola transparente con PROCESSES top-10, sys-list con avail %. Desplegado VPS.
- **Sesiones ZIO persistentes** — `sessionId` en `expo-secure-store`, `loadHistory()` desde servidor. Build vCode 500 regenerado.
- **ZIO guard anti-degeneración v2** — streaming en vivo: `_feed_chunk` detecta bucle durante stream, corta feed, envía `degenerate: true`. Verificado 9/9 test cases, `conversations.jsonl` limpio.
- **ZIO: sesiones en slider** — PROJECTS/SESSIONS tabs, servidor como fuente de verdad.
- **ZIO pipeline inferencia arreglado** — causa raíz: `"dim" in msg` (substring) capturaba "dime hola" → `device_brightness` hardcodeado. Fix: `\b...\b` + verbo de cambio en `agent/core.py`. Verificado 8 mensajes con respuestas coherentes.
- **Slider sidebar en aerospace** — sidebar rail colapsable (estilo videochat) con menú principal, persistido en `localStorage`.

### Not Started
- Most advanced aerospace modules (Mission Control calculations, Orbital Mechanics live, etc.)
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
- Tunnel VPS `zicore-kernel` (config `/etc/cloudflared/config.yml`, servicio `cloudflared-zicore-kernel`): ingress wildcard `*.zicore.space → localhost:8000` + hostnames explícitos para `zio`, `aerospace`, `materializer`, `engineering`, `games`, `zmmx`, `mail`, `zicodex`, `zivault`, `mc`, `zcs`, `zicore.space`, `zinemotion.com(.mx)`. DNS: `cloudflared tunnel route dns --overwrite-dns zicore-kernel <host>.zicore.space` (CNAME al túnel) — necesaria por hostname además del wildcard del ingress. Todos los portales verificados 200 público el 2026-08-07.

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

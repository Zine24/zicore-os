# Changelog

All notable changes to ZICORE System.

## [0.4.0] — 2026-06-25

### Added
- 8 workspace tabs in dashboard right panel (System, AI, 3D, Video, Audio, Post, Vision, Data)
- Multi-track NLE video editor with drag reordering (V1/V2/A1/A2)
- 12 video effects, 8 transitions, clip properties (speed/volume/opacity)
- Three.js 3D mesh viewer with material editor (color, opacity, wireframe, grid)
- Mesh export (STL, OBJ, GLB)
- Web Audio API waveform visualization
- 8 sound synthesis types (alarm, engine, beep, wind, radio, melody, heartbeat, laser)
- Image editor with adjustments (brightness, contrast, saturation, hue)
- 8 image filters (B&W, sepia, invert, blur, sharpen, emboss, edge, vintage)
- Camera input via getUserMedia
- OpenVision image/video analysis + OCR
- Knowledge base document upload and full-text search
- Data retention export (JSONL, Unsloth format)
- Mission save/load system
- 9 AI providers (ZICORE Native, OpenRouter, Ollama, OpenAI, Anthropic, Groq, DeepSeek, Together AI, OpenCode)
- Provider testing with available_models response
- Model selection only from enabled/connected providers
- WebSocket streaming (stream_start/chunk/end protocol)
- Main menu with 3D animated particle background
- Flight simulator with 4 vehicles and physics engine
- Cloudflare tunnel deployment (quick + named tunnels)
- Docker Compose with Nginx SSL
- Google Colab deployment with GPU T4 support
- 93 tests all passing

### Changed
- Dashboard redesigned with workspace tabs replacing floating panels
- Agent general_response with personalized identity handling
- Generator with API integration (DALL-E 3, Stability AI) + local fallback
- Chat endpoint with knowledge base context injection

## [0.3.0] — 2026-06-20

### Added
- 17 mission module state machines
- Dual-engine pipeline (Motor A deterministic + Motor B ML)
- Confidence-weighted merge algorithm
- Pipeline orchestrator
- Agent REST + WebSocket API
- Knowledge base with persistent chat
- Data retention with training data export
- OpenVision image analysis
- Telemetry simulation
- Z-TY Factory parametric aircraft design

### Changed
- FastAPI backend on port 8080
- Web server on port 3000

## [0.2.0] — 2026-06-15

### Added
- Initial dashboard with cockpit-style UI
- ZIO agent with personality
- Basic chat functionality
- Theme system (8 themes)
- Provider configuration system

## [0.1.0] — 2026-06-10

### Added
- Project initialization
- Backend engine architecture
- Module state machine framework
- Frontend scaffolding
- Basic test suite

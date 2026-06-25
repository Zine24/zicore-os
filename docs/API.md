# ZICORE API Reference

Base URL: `http://localhost:8080` (local) or `https://api.zicore.space` (production)

---

## REST Endpoints

### System

#### GET /api/status

Returns system status and all 17 module states.

**Response:**
```json
{
  "status": "online",
  "version": "0.4.0",
  "modules": {
    "zihab": {"name": "zihab", "status": "nominal", "o2": 20.5, ...},
    "zinav": {"name": "zinav", "status": "nominal", "alt_km": 400.0, ...},
    ...
  }
}
```

---

### Configuration

#### GET /api/config

Returns full configuration including providers.

**Response:**
```json
{
  "providers": {
    "groq": {"name": "Groq", "enabled": true, "api_key": "..."},
    "openai": {"name": "OpenAI", "enabled": false, ...}
  },
  "zio_engine": {"active_provider": "groq", "temperature": 0.7},
  "theme": "midnight"
}
```

#### POST /api/config

Updates configuration.

**Request:**
```json
{
  "providers": {
    "groq": {"enabled": true, "api_key": "gsk_..."}
  }
}
```

**Response:**
```json
{"status": "ok", "config": {...}}
```

---

### Providers

#### POST /api/config/test-provider/{provider_id}

Tests provider connection and returns available models.

**Response (success):**
```json
{
  "status": "connected",
  "provider": "groq",
  "model": "llama-3.1-8b-instant",
  "available_models": ["llama-3.1-8b-instant", "llama-3.1-70b-versatile", ...]
}
```

**Response (disabled):**
```json
{"status": "disabled", "provider": "groq"}
```

#### POST /api/provider/chat

Send chat to a specific provider.

**Request:**
```json
{
  "provider": "groq",
  "message": "What is the status of ZiNav?"
}
```

**Response:**
```json
{
  "status": "ok",
  "provider": "groq",
  "model": "llama-3.1-8b-instant",
  "response": "ZiNav is currently in orbital phase..."
}
```

---

### Chat

#### POST /api/chat

Chat with ZIO using knowledge base context.

**Request:**
```json
{
  "message": "Hola, soy Carlos",
  "session_id": "webchat",
  "provider": "groq"
}
```

**Response:**
```json
{
  "status": "ok",
  "response": "Hola Carlos. Soy ZIO, el operador de inteligencia del ecosistema ZICORE.",
  "intent": "identity"
}
```

---

### Telemetry

#### GET /api/telemetry

Returns real-time telemetry data.

**Response:**
```json
{
  "altitude_km": 400.0,
  "velocity_kms": 7.68,
  "battery_pct": 85.0,
  "signal_strength": -65.0
}
```

#### GET /api/telemetry/modules

Returns module status.

**Response:**
```json
{
  "modules": {
    "zinav": {"status": "nominal", "phase": "orbital"},
    "zipower": {"status": "nominal", "solar_w": 1200.0}
  }
}
```

---

### Knowledge Base

#### GET /api/knowledge/stats

**Response:**
```json
{
  "status": "ok",
  "stats": {
    "conversations": 8,
    "documents": 3,
    "total_words": 15420,
    "storage_mb": 0.5
  }
}
```

#### GET /api/knowledge/search?q={query}

**Response:**
```json
{
  "status": "ok",
  "results": [
    {"role": "user", "content": "Analyze trajectory", "timestamp": "..."},
    {"role": "zio", "content": "Computing Hohmann transfer...", "intent": "trajectory"}
  ]
}
```

#### POST /api/knowledge/document

Upload a document to the knowledge base.

**Request:** `multipart/form-data`
- `file`: Text file
- `name`: Document name (optional)

**Response:**
```json
{"status": "ok", "doc_id": "...", "name": "readme.txt", "words": 500}
```

#### POST /api/knowledge/document/text

Add text content directly.

**Request:**
```json
{
  "name": "Flight Manual",
  "content": "Chapter 1: Pre-flight checklist..."
}
```

**Response:**
```json
{"status": "ok", "doc_id": "...", "name": "Flight Manual", "words": 150}
```

---

### Missions

#### GET /api/missions

List all saved missions.

**Response:**
```json
{
  "missions": [
    {"id": "mission_001", "name": "Alpha Test", "phase": "orbital", "created": "..."}
  ]
}
```

#### GET /api/missions/{mission_id}

Get mission details.

#### POST /api/missions/{mission_id}

Save mission data.

**Request:**
```json
{
  "name": "Alpha Test",
  "phase": "orbital",
  "modules": {"zinav": {...}, "zipower": {...}}
}
```

#### DELETE /api/missions/{mission_id}

Delete a mission.

---

### 3D Mesh

#### POST /api/mesh/generate

Generate a 3D mesh.

**Request:**
```json
{
  "type": "rocket",
  "params": {"body_radius": 0.3, "body_height": 2, "nose_height": 0.8}
}
```

**Response:**
```json
{
  "status": "ok",
  "path": "/output/meshes/mesh_1719312000.stl",
  "type": "rocket",
  "vertices": 256,
  "faces": 512
}
```

---

### Video

#### POST /api/video/process

Process video frames with effects.

**Request:**
```json
{
  "effect": "sepia",
  "frames": ["base64_frame_1", "base64_frame_2"]
}
```

#### POST /api/video/trim

Trim frame sequence.

**Request:**
```json
{
  "frames": ["f1", "f2", "f3", "f4", "f5"],
  "start": 1,
  "end": 4
}
```

#### POST /api/video/concat

Concatenate video sequences.

**Request:**
```json
{
  "sequences": [
    {"frames": ["f1", "f2"]},
    {"frames": ["f3", "f4"]}
  ]
}
```

---

### Themes

#### GET /api/themes

**Response:**
```json
{
  "themes": [
    {"id": "midnight", "name": "Midnight", "colors": {"bg": "#0a0a0f", "primary": "#00ffff"}},
    {"id": "cyber", "name": "Cyber Neon", "colors": {...}},
    ...
  ]
}
```

#### POST /api/config/theme/{theme_id}

Set active theme.

---

## WebSocket

Connect: `ws://localhost:8080/ws/zio`

### Commands

#### chat

Full response (non-streaming).

**Send:**
```json
{"command": "chat", "payload": {"message": "Status report", "module": "zicorex"}}
```

**Receive:**
```json
{"type": "response", "intent": "system_status", "outputs": {...}}
```

#### stream

Word-by-word streaming response.

**Send:**
```json
{"command": "stream", "payload": {"message": "Analyze trajectory", "module": "zinav"}}
```

**Receive:**
```json
{"type": "stream_start", "message": ""}
{"type": "stream_chunk", "chunk": "Computing "}
{"type": "stream_chunk", "chunk": "Hohmann "}
{"type": "stream_chunk", "chunk": "transfer..."}
{"type": "stream_end", "intent": "trajectory", "outputs": {...}}
```

#### generate

Generate image/video/3d/sound.

**Send:**
```json
{"command": "generate", "payload": {"type": "image", "prompt": "rocket launch"}}
```

**Receive:**
```json
{"type": "generating", "generating_type": "image"}
{"type": "generated", "result": {...}}
```

#### telemetry

Subscribe to real-time telemetry.

**Send:**
```json
{"command": "telemetry"}
```

**Receive:**
```json
{"type": "telemetry", "data": {"altitude_km": 400.0, "velocity_kms": 7.68, ...}}
```

#### mission_save

Save current mission.

**Send:**
```json
{"command": "mission_save", "payload": {"id": "mission_001", "name": "Alpha"}}
```

#### mission_load

Load mission by ID.

**Send:**
```json
{"command": "mission_load", "payload": {"id": "mission_001"}}
```

#### vision_analyze

Analyze an image.

**Send:**
```json
{"command": "vision_analyze", "payload": {"path": "/path/to/image.png"}}
```

#### vision_webcam

Analyze webcam frame.

**Send:**
```json
{"command": "vision_webcam", "payload": {"image": "data:image/png;base64,..."}}
```

#### knowledge_search

Search knowledge base.

**Send:**
```json
{"command": "knowledge_search", "payload": {"query": "trajectory"}}
```

#### knowledge_stats

Get knowledge base stats.

**Send:**
```json
{"command": "knowledge_stats"}
```

#### mesh_generate

Generate 3D mesh.

**Send:**
```json
{"command": "mesh_generate", "payload": {"type": "rocket", "params": {"body_radius": 0.3}}}
```

---

## Error Responses

All endpoints return errors in this format:

```json
{"status": "error", "error": "Description of the error"}
```

WebSocket errors:

```json
{"type": "error", "message": "Description of the error"}
```

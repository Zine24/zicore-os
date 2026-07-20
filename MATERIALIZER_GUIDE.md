# Materializer + Visualizer — Guía de Uso

## Pipeline Completo: Prompt → Generación → Simulación

```
             ┌─────────────┐
  Prompt ──▶ │ Materializer │ ──▶ archivo (PNG/WAV/STL/MP4)
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │  Visualizer  │ ──▶ vista previa + workspace
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │  Simulation  │ ──▶ escena 3D interactiva
             └─────────────┘
```

---

## 1. Materializer — Generación por Prompt

### Endpoints API

| Tipo | Método | Endpoint | Body |
|------|--------|----------|------|
| **Imagen** | POST | `/api/generate` | `{"type":"image","prompt":"..."}` |
| **Sonido** | POST | `/api/generate` | `{"type":"sound","prompt":"..."}` |
| **3D** | POST | `/api/generate` | `{"type":"3d","prompt":"..."}` |
| **Video** | POST | `/api/generate` | `{"type":"video","prompt":"..."}` |
| **Video** | POST | `/api/video/generate` | `{"prompt":"...","duration":3,"width":640,"height":480,"fps":24}` |
| **AI 3D** | POST | `/api/ai3d/generate` | `{"engine":"cadquery|build123d|solidpython2|openscad|tripo3d|meshy|rodin","prompt":"...","script":"..."}` |

### Ejemplos con curl

```bash
# Imagen
curl -X POST /api/generate -H "Content-Type: application/json" \
  -d '{"type":"image","prompt":"lunar base concept art"}'

# Sonido
curl -X POST /api/generate -H "Content-Type: application/json" \
  -d '{"type":"sound","prompt":"engine ignition sound"}'

# 3D
curl -X POST /api/generate -H "Content-Type: application/json" \
  -d '{"type":"3d","prompt":"spacecraft hull"}'

# Video
curl -X POST /api/video/generate -H "Content-Type: application/json" \
  -d '{"prompt":"satellite orbit animation","duration":5,"fps":24}'
```

### Pipelines de Generación (por tipo)

**Imagen** → 3 motores en cascada:
1. Stable Diffusion (`zicore/stable_diffusion_engine.py`) — CPU diffusers
2. Pillow procedural (`agent/media.py`) — dibuja formas, texto, colores
3. Fallback puro Python — imagen de color sólido con texto

**Sonido** → 2 niveles:
1. Generación procedural (`agent/media.py`) — ondas seno, ruido, envolventes
2. Fallback puro Python — tono 440Hz simple

**3D** → 3 motores en cascada:
1. AI3D cloud APIs (`zicore/ai3d_engines.py`) — Tripo3D, Meshy, Rodin
2. Trimesh procedural (`agent/content3d.py`) — icospheres, text, extrusión
3. Fallback trimesh directo — icosphere básica

**Video** → 2 niveles:
1. Frame-by-frame procedural (`agent/media.py`) — PNG sequence
2. Placeholder — mensaje de cola (requiere ffmpeg para encoding real)

---

## 2. Visualizer — Visualización y Workspace

### Tabs del Visualizer

| Tab | Función |
|-----|---------|
| **Scenes** | Escenas 3D precargadas (lunar, orbital, Mars) |
| **Workspace** | Panel de trabajo — sube/arrastra archivos generados |
| **Generations** | Historial de todo lo generado (desde Generation Library) |
| **Simulation** | Escena 3D interactiva con Three.js (pendiente de implementar canvas) |
| **Telemetry** | Datos en vivo si hay simulación activa |
| **Export** | Exportar escena como STL/OBJ/GLB |

### Flujo de Trabajo

```
1. Escribe un prompt en ZIO o llama a /api/generate
       │
       ▼
2. El archivo se guarda en /output/
       │
       ▼
3. Se registra automáticamente en Generation Library (SQLite)
       │
       ▼
4. Abre Visualizer → tab "Generations" → busca tu archivo
       │
       ▼
5. Tab "Workspace" → arrastra el archivo a la escena
       │
       ▼
6. Tab "Simulation" → la escena 3D carga el modelo
       │
       ▼
7. Tab "Telemetry" → datos de la simulación en vivo
```

---

## 3. Ciclo Iterativo: Prompt → Revisión → Mejora

Para llegar a una simulación completa:

```
Iteración 1: Prompt básico
  "generate a spacecraft hull" → 3D básico (icosphere + texto)
  
Iteración 2: Refinar
  "generate an orbital satellite with solar panels" → 3D mejorado
  
Iteración 3: Escena
  Usa Visualizer → Workspace para posicionar el modelo en escena
  
Iteración 4: Simulación
  Visualizer → Simulation para vista 3D interactiva
```

---

## 4. Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| "No generator available" | MediaEngine no importa | `pip install Pillow numpy` |
| "Sound generation failed" | Faltan imports de audio | Usa fallback (tono puro) |
| "3D engine not available" | No trimesh | `pip install trimesh[easy]` |
| 301 redirect en WordPress | URL HTTPS configurada | Cloudflare maneja SSL |
| Cloudflare tunnel wrong port | Tunnel apunta a :4000 | Cambiar a :80 en Cloudflare Dashboard |
| "Not connected to server" | Provider desconectado | Ir a Settings → Providers → reconectar |

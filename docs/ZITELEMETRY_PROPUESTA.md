# ZITELEMETRY — Mission Control System (Propuesta)

> Estado: **PROPUESTA** — pendiente de implementación
> Sistema: Misión Control de ZICORE
> Subdominio: `zitelemetry.zicore.space`
> Portal actual: `zcs.zicore.space` (misión control en exhibidor)
> Fecha: 2026-08-05

---

## Contexto

ZICORE necesita un sistema de **Mission Control** completo. Actualmente `zcs.zicore.space`
sirve `mission-control.html` como consola estática. La propuesta es construir **Zitelemetry**,
el sistema operativo de telemetría y control de misión del ecosistema, conectado al Kernel Hub.

## Alcance

Zitelemetry será un subsistema independiente en `zitelemetry.zicore.space`, conectado al
backend por el Kernel Hub (REST + WebSocket + State Engine), igual que el resto de subsistemas.

### Núcleo de telemetría
- Streams en tiempo real por WebSocket (data de vehículos, subsistemas, nodos)
- Rest API para datos históricos y config
- Fallback REST cuando WS no está disponible

### Módulos de misión
- **Mission Planner**: secuencias, timelines, eventos
- **Launch Operations Console**: countdown, Go/No-Go, checklists
- **Ground Station Control**: antenas, tracking, telemetría downlink
- **Constellation Manager**: flota de satélites
- **Mission Replay**: reconstrucción de misión desde flight data
- **Flight Recorder**: caja negra digital, análisis post-incidente

### Monitoreo
- Vehicle status, telemetry, mission timer
- Altitude, velocity, acceleration, G-force
- Fuel, battery, power, communications
- Weather, orbital params, trajectory, target
- Mission logs, warnings, AI status, subsystem health

## Arquitectura

```
zitelemetry.zicore.space
        │  REST :8000 (kernel hub)  +  WS /ws
        ▼
   KERNEL HUB  (VPS — motores de creación)
        │
        ▼
   backends: telemetría, vehículos, ingeniería, ZIO
```

- Frontend: `frontend/zitelemetry.html` (nuevo, estilo misión control)
- Enrutado por host ya activo en `web_server.py` (`zitelemetry.zicore.space` → `telemetry.html` temporal)
- Conectar vía WS al kernel hub como MC (`mc.*` commands), con reintento + fallback REST

## Pasos de implementación

1. Crear `frontend/zitelemetry.html` — consola de misión completa (reutilizar `mission-control.html`)
2. Extender el bridge WS del kernel hub con comandos `zt.*` (status, stream, replay)
3. Endpoints REST en `web_server.py`: `/api/zt/status`, `/api/zt/history`, `/api/zt/mission`
4. Enrutar `zitelemetry.zicore.space` → `zitelemetry.html` en `serve_main_menu`
5. Crear CNAME `zitelemetry.zicore.space` → túnel `d2881059` (VPS)
6. Integrar con Aerospace (`aerospace.zicore.space`) y Telemetry (`telemetry.zicore.space`)

## Dependencias

- Kernel Hub VPS activo (`/opt/zicore-system`, puerto 8000)
- Túnel Cloudflare `d2881059-86c9-4230-8531-ac4dceb60d84` (config.yml local con `zitelemetry.zicore.space`)
- Frontend base: `mission-control.html`, `telemetry.html`

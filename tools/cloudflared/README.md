# ZICORE Cloudflare Tunnel

Production tunnel deployment for ZICORE System.

## Quick Start (Testing)

No authentication required - creates temporary URL:

```batch
cloudflared.exe tunnel --url http://localhost:4000
```

## Production Setup

### 1. Download cloudflared

```powershell
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile "cloudflared.exe"
```

### 2. Authenticate with Cloudflare

```batch
cloudflared.exe tunnel login
```

Opens browser - select your domain (zicore.space).

### 3. Create Named Tunnel

```batch
cloudflared.exe tunnel create zicore
```

Save the tunnel ID from output.

### 4. Update config.yml

Replace `TUNNEL_ID.json` with your actual tunnel credentials file.

### 5. Route DNS

```batch
cloudflared.exe tunnel route dns zicore app.zicore.space
cloudflared.exe tunnel route dns zicore api.zicore.space
```

### 6. Start Tunnel

```batch
cloudflared.exe --config=config.yml tunnel run
```

## ZICORE System Integration

The ZICORE System auto-starts the tunnel when running `start_production.py`.

Configure in `data/config/zio_config.json`:
```json
{
  "tunnel": {
    "enabled": true,
    "name": "zicore",
    "domain": "zicore.space"
  }
}
```

## URLs

| Service | Local | Production |
|---------|-------|------------|
| Dashboard | http://localhost:4000 | https://app.zicore.space |
| API | http://localhost:4080 | https://api.zicore.space |
| ZIO Agent | http://localhost:4000/zio | https://app.zicore.space/zio |

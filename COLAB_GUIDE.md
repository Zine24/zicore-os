# ZICORE — Google Colab Deployment Guide

## Quick Start (2 cells)

### Cell 1: Upload Files
```python
# Run this first to upload your zicore-system.zip
exec(open('colab_upload.py').read())
```

### Cell 2: Start System
```python
# Run this after uploading
exec(open('colab_setup.py').read())
```

---

## Alternative: Manual Upload

### Step 1: Upload zip to Colab
```python
from google.colab import files
uploaded = files.upload()  # Select zicore-system.zip

import zipfile
with zipfile.ZipFile('zicore-system.zip', 'r') as z:
    z.extractall('/content/')
```

### Step 2: Start system
```python
!cd /content/zicore-system && python colab_setup.py
```

---

## Alternative: Mount Google Drive
```python
from google.colab import drive
drive.mount('/content/drive')

!cp -r /content/drive/MyDrive/zicore-system /content/
!cd /content/zicore-system && python colab_setup.py
```

---

## What You Get

After running, you'll get a public URL:

| URL | Page |
|-----|------|
| `{url}` | Main Menu (3D animated) |
| `{url}/dashboard` | Flight Deck (8 workspaces) |
| `{url}/zio` | ZIO Agent (streaming chat) |
| `{url}/sim` | Flight Simulator |

---

## System Requirements

- **Colab Free Tier** (T4 GPU) works fine
- **RAM**: ~2GB
- **Disk**: ~500MB
- **No GPU required** for core system (only for ML training)

---

## Troubleshooting

### "ZICORE not found"
→ Run the upload cell first, then re-run setup

### "ngrok failed"
→ Use Colab's built-in port forwarding:
1. Click Resources tab (top right)
2. Click Connect → Port Forwarding
3. Add port 3000

### "Address already in use"
→ Runtime → Disconnect and delete runtime, then re-run

---

## Providers Setup

After system starts, open Dashboard → CONFIG:

1. Select provider (OpenAI, Anthropic, Groq, OpenCode, etc.)
2. Toggle ON
3. Enter API Key
4. Click SAVE

### ZICORE Native (no API key needed)
- Built-in deterministic + ML inference
- Works offline
- No external API required

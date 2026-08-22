# ZICORE Ollama Deployment

Native Ollama server for ZICORE System.

## Setup

1. Download Ollama from: https://ollama.com/download
2. Extract `ollama.exe` to this folder
3. Run `start.bat` or execute:

```batch
set OLLAMA_MODELS=C:\Users\zinem\Documents\zicore-system\data\ollama\models
set OLLAMA_HOST=127.0.0.1:11434
.\ollama.exe serve
```

## Pull Models

```bash
.\ollama.exe pull tinyllama      # 637MB - fast, basic
.\ollama.exe pull llama3.1:8b    # 4.7GB - recommended
.\ollama.exe pull mistral        # 4.1GB - alternative
```

## ZICORE Integration

The ZICORE System auto-detects Ollama at `http://127.0.0.1:11434`.

Set as default provider in `data/config/zio_config.json`:
```json
{
  "zio_engine": {
    "active_provider": "ollama",
    "active_model": "llama3.1:8b"
  }
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| OLLAMA_MODELS | ~/.ollama/models | Model storage path |
| OLLAMA_HOST | 127.0.0.1:11434 | Server bind address |
| OLLAMA_KEEP_ALIVE | 5m | Model unload timeout |

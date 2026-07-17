#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# ZICORE SYSTEM — Termux Setup for Android
# Installs ZICORE backend on your phone via Termux
# ═══════════════════════════════════════════════════════════════

set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

ZICORE_DIR="$HOME/zicore-system"
PORT=4000

echo -e "${CYAN}"
echo "  ╔══════════════════════════════════════╗"
echo "  ║     ZICORE SYSTEM — Android Setup    ║"
echo "  ║     Aerospace OS on your phone       ║"
echo "  ╚══════════════════════════════════════╝"
echo -e "${NC}"

# ── Step 1: Update Termux ────────────────────────────────────
echo -e "${YELLOW}[1/8] Actualizando Termux...${NC}"
pkg update -y && pkg upgrade -y

# ── Step 2: Install dependencies ─────────────────────────────
echo -e "${YELLOW}[2/8] Instalando dependencias...${NC}"
pkg install -y python git curl wget build-essential libffi openssl

# ── Step 3: Install Python packages ──────────────────────────
echo -e "${YELLOW}[3/8] Instalando paquetes Python...${NC}"
pip install --upgrade pip
pip install fastapi uvicorn[standard] httpx requests aiohttp bcrypt
pip install trimesh numpy Pillow

# Optional: heavier packages (skip on low-end phones)
echo -e "${YELLOW}[3b/8] Paquetes pesados ( opcionales )...${NC}"
echo "  Instalando pymeshlab (puede tardar)..."
pip install pymeshlab 2>/dev/null || echo "  pymeshlab no disponible — funcionara sin mesh processing avanzado"

# ── Step 4: Clone or copy ZICORE ─────────────────────────────
echo -e "${YELLOW}[4/8] Configurando ZICORE...${NC}"
if [ -d "$ZICORE_DIR" ]; then
  echo "  Directorio existe, actualizando..."
  cd "$ZICORE_DIR" && git pull 2>/dev/null || true
else
  echo "  Clonando repositorio..."
  git clone https://github.com/Zine24/zicore-os.git "$ZICORE_DIR" 2>/dev/null || {
    echo "  No se pudo clonar. Copia manualmente zicore-system a $ZICORE_DIR"
    echo "  O usa: scp -r zicore-system/ phone:~/zicore-system/"
  }
fi

cd "$ZICORE_DIR"

# ── Step 5: Create data directories ──────────────────────────
echo -e "${YELLOW}[5/8] Creando directorios de datos...${NC}"
mkdir -p data/config data/media/audio data/media/video data/media/images data/media/music

# ── Step 6: Create minimal config ────────────────────────────
echo -e "${YELLOW}[6/8] Generando configuracion...${NC}"
if [ ! -f data/config/zio_config.json ]; then
  cat > data/config/zio_config.json << 'ZIOCONFIG'
{
  "active_provider": "zicore_native",
  "active_model": "gemma3:1b",
  "providers": {
    "zicore_native": {
      "name": "ZICORE Native (Ollama)",
      "type": "ollama",
      "base_url": "http://127.0.0.1:11434",
      "models": ["gemma3:1b", "tinyllama:latest", "qwen3:0.6b"],
      "requires_api_key": false
    },
    "openrouter": {
      "name": "OpenRouter",
      "type": "openrouter",
      "base_url": "https://openrouter.ai/api/v1",
      "api_key": "",
      "models": ["nvidia/nemotron-3-super-120b-a12b:free"],
      "requires_api_key": true
    }
  },
  "features": {
    "voice_input": false,
    "voice_output": false,
    "aerospace_mode": true
  }
}
ZIOCONFIG
  echo "  Config creada."
fi

# ── Step 7: Create launcher script ───────────────────────────
echo -e "${YELLOW}[7/8] Creando launcher...${NC}"
cat > "$HOME/start-zicore.sh" << LAUNCHER
#!/bin/bash
cd $ZICORE_DIR
echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║     ZICORE SYSTEM v5.0               ║"
echo "  ║     http://localhost:$PORT            ║"
echo "  ╚══════════════════════════════════════╝"
echo ""
echo "  Abre tu navegador en: http://localhost:$PORT"
echo "  O desde otro dispositivo: http://$(ip route get 1 2>/dev/null | awk '{print $7; exit}'):$PORT"
echo ""
echo "  Presiona Ctrl+C para detener"
echo ""
python -m uvicorn web_server:app --host 0.0.0.0 --port $PORT --reload
LAUNCHER
chmod +x "$HOME/start-zicore.sh"

# ── Step 8: Create Termux boot script ────────────────────────
echo -e "${YELLOW}[8/8] Configurando auto-start...${NC}"
mkdir -p "$HOME/.termux/boot" 2>/dev/null
cat > "$HOME/.termux/boot/zicore-start.sh" << BOOT
#!/bin/bash
termux-wake-lock
cd $ZICORE_DIR
python -m uvicorn web_server:app --host 0.0.0.0 --port $PORT
BOOT
chmod +x "$HOME/.termux/boot/zicore-start.sh" 2>/dev/null || true

echo ""
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ZICORE instalado correctamente!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
echo ""
echo "  Para iniciar:"
echo -e "    ${CYAN}bash ~/start-zicore.sh${NC}"
echo ""
echo "  Luego abre en tu navegador:"
echo -e "    ${CYAN}http://localhost:$PORT${NC}"
echo ""
echo "  Auto-start en boot (requiere termux-boot):"
echo "    pkg install termux-services"
echo "    sv-enable zicore"
echo ""
echo "  Desde otro dispositivo en tu red:"
LOCAL_IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}')
echo -e "    ${CYAN}http://${LOCAL_IP:-<ip-del-telefono>}:${PORT}${NC}"
echo ""
echo "  O conecta el APK de ZICORE:"
echo "    El APK buscara automaticamente localhost:4000"
echo ""

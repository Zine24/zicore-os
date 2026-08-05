#!/bin/bash
# ╔══════════════════════════════════════════════════╗
# ║     ZIO UNIFIED (ZiCAM)                          ║
# ║     ESP32-S3 CAM + Desktop Control               ║
# ║     Installer — zicore.space                     ║
# ╚══════════════════════════════════════════════════╝
#
# Usage:
#   curl -sL https://zcs.zicore.space/installers/ziounified_setup.sh | bash
#   or download and run:
#   chmod +x ziounified_setup.sh && ./ziounified_setup.sh
#
# Installs: git, esptool (firmware flashing), python deps for the
# desktop visualizer. Clones https://github.com/Zine24/ZioUnified

set -euo pipefail

VERSION="5.0.0"
ZIO_DIR="${ZIO_DIR:-$HOME/ZioUnified}"
REPO="https://github.com/Zine24/ZioUnified.git"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'
YELLOW='\033[1;33m'; PURPLE='\033[0;35m'; NC='\033[0m'

banner() {
    echo -e "${CYAN}"
    echo "  ╔══════════════════════════════════════════════════╗"
    echo "  ║     ZIO UNIFIED (ZiCAM)  v${VERSION}               ║"
    echo "  ║     ESP32-S3 CAM + Desktop Control               ║"
    echo "  ║     Installer — zicore.space                     ║"
    echo "  ╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

step() { echo -e "${YELLOW}[$1/4] $2${NC}"; }
ok()   { echo -e "  ${GREEN}✓ $1${NC}"; }
warn() { echo -e "  ${YELLOW}⚠ $1${NC}"; }
err()  { echo -e "  ${RED}✗ $1${NC}"; }

banner

step 1 "Verificando git..."
if ! command -v git &>/dev/null; then
    warn "git no instalado. Instalando..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update -qq && sudo apt-get install -y -qq git
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y -q git
    elif command -v brew &>/dev/null; then
        brew install git
    else
        err "Instala git manualmente y vuelve a ejecutar."
        exit 1
    fi
fi
ok "git listo"

step 2 "Clonando ZioUnified..."
if [ -d "$ZIO_DIR/.git" ]; then
    warn "$ZIO_DIR ya existe. Actualizando..."
    (cd "$ZIO_DIR" && git pull --ff-only)
else
    git clone "$REPO" "$ZIO_DIR"
fi
ok "repositorio en $ZIO_DIR"

step 3 "Preparando entorno Python (visualizador + esptool)..."
PY="python3"
if ! command -v "$PY" &>/dev/null; then
    PY="python"
fi
if command -v "$PY" &>/dev/null; then
    "$PY" -m pip install --quiet --upgrade pip
    "$PY" -m pip install --quiet esptool || warn "esptool opcional (requiere pip)"
else
    warn "Python no encontrado. Solo el firmware ESP32 esta disponible."
fi
ok "entorno listo"

step 4 "Verificando instalacion..."
if [ -f "$ZIO_DIR/firmware/ZiCAM_ESP32-S3/ZiCAM_ESP32-S3.ino" ]; then
    ok "Firmware: $ZIO_DIR/firmware/ZiCAM_ESP32-S3/"
else
    warn "Estructura del firmware no encontrada (revisa el repositorio)."
fi

echo -e "${CYAN}"
echo "  ┌────────────────────────────────────────────────────┐"
echo "  │  ZIO UNIFIED instalado                              │"
echo "  │                                                    │"
echo "  │  Firmware ESP32-S3:  firmware/ZiCAM_ESP32-S3/      │"
echo "  │    - Abrir el .ino en Arduino IDE (board S3)       │"
echo "  │    - Editar zicam_config.h (WiFi / AP por defecto) │"
echo "  │    - AP: ZIOCONTROL / 12345678 / 192.168.4.1      │"
echo "  │                                                    │"
echo "  │  Control desktop:  desktop/Desktop_Visualizer/     │"
echo "  │    cd '$ZIO_DIR' && python3 -m http.server 8000   │"
echo "  │    abrir http://localhost:8000/desktop/...         │"
echo "  │                                                    │"
echo "  │  Stream: http://<ESP_IP>:81/stream                 │"
echo "  └────────────────────────────────────────────────────┘"
echo -e "${NC}"

echo -e "${GREEN}ZioUnified listo. ¡Vuela!${NC}"

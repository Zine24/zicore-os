#!/bin/bash
# ╔══════════════════════════════════════════════════╗
# ║     ZICORE SYSTEM v5.0                          ║
# ║     Digital Aerospace Operating System          ║
# ║     Linux Installer — zicore.space              ║
# ╚══════════════════════════════════════════════════╝
#
# Usage:
#   curl -sL https://zcs.zicore.space/installers/install_zicore.sh | bash
#   or download and run:
#   chmod +x install_zicore.sh && ./install_zicore.sh
#
# Tested on: Ubuntu 22+, Debian 12+, Fedora 38+, Arch, Linux Mint

set -euo pipefail

VERSION="5.0.0"
ZICORE_DIR="${ZICORE_DIR:-$HOME/zicore-system}"
PORT="${PORT:-4000}"
REPO="https://github.com/zinemotion/ZiCore-OS.git"

# ─── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'
YELLOW='\033[1;33m'; PURPLE='\033[0;35m'; NC='\033[0m'

banner() {
    echo -e "${CYAN}"
    echo "  ╔══════════════════════════════════════════════════╗"
    echo "  ║     ZICORE SYSTEM v${VERSION}                     ║"
    echo "  ║     Digital Aerospace Operating System          ║"
    echo "  ║     Linux Installer — zicore.space              ║"
    echo "  ╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

step()  { echo -e "${YELLOW}[$1/$TOTAL] $2${NC}"; }
ok()    { echo -e "  ${GREEN}✓ $1${NC}"; }
warn()  { echo -e "  ${YELLOW}⚠ $1${NC}"; }
err()   { echo -e "  ${RED}✗ $1${NC}"; }

# ─── Detect distro ─────────────────────────────────────────────────────────────
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_LIKE=${ID_LIKE:-$ID}
    elif command -v lsb_release &>/dev/null; then
        DISTRO=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
    else
        DISTRO="unknown"
    fi
    echo -e "  Detected: ${PURPLE}$DISTRO${NC}"
}

pkg_install() {
    case $DISTRO in
        ubuntu|debian|linuxmint|pop)
            sudo apt-get update -qq && sudo apt-get install -y -qq "$@" ;;
        fedora|rhel|centos|rocky)
            sudo dnf install -y -q "$@" ;;
        arch|manjaro)
            sudo pacman -Sy --noconfirm "$@" ;;
        opensuse*|sles)
            sudo zypper install -y -q "$@" ;;
        *)
            warn "Unknown distro. Install manually: $*"
            return 1 ;;
    esac
}

TOTAL=8
banner

# ─── 1. Prerequisites ────────────────────────────────────────────────────────
step 1 "Checking prerequisites..."
detect_distro

# Build essentials
pkg_install build-essential curl wget git 2>/dev/null || true
ok "Build tools ready"

# ─── 2. Python 3.10+ ─────────────────────────────────────────────────────────
step 2 "Checking Python..."

if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo $PY_VER | cut -d. -f1)
    PY_MINOR=$(echo $PY_VER | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
        ok "Python $PY_VER found"
    else
        warn "Python $PY_VER too old, installing 3.12..."
        pkg_install python3.12 python3.12-venv python3-pip 2>/dev/null
    fi
else
    warn "Python3 not found, installing..."
    pkg_install python3 python3-pip python3-venv 2>/dev/null
fi

PYTHON=$(command -v python3 || command -v python)
ok "Python ready: $($PYTHON --version)"

# ─── 3. Node.js 20+ ──────────────────────────────────────────────────────────
step 3 "Checking Node.js..."

if command -v node &>/dev/null; then
    NODE_VER=$(node --version | sed 's/v//' | cut -d. -f1)
    if [ "$NODE_VER" -ge 20 ]; then
        ok "Node.js $(node --version) found"
    else
        warn "Node.js too old, installing 20..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - 2>/dev/null
        pkg_install nodejs 2>/dev/null
    fi
else
    warn "Node.js not found, installing 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - 2>/dev/null
    pkg_install nodejs 2>/dev/null
fi
ok "Node.js ready: $(node --version)"

# ─── 4. Clone / Update ───────────────────────────────────────────────────────
step 4 "Setting up ZICORE repository..."

if [ -d "$ZICORE_DIR/.git" ]; then
    cd "$ZICORE_DIR"
    git pull origin main --quiet 2>/dev/null || warn "Pull failed, using existing"
    ok "Updated existing installation"
else
    if [ -d "$ZICORE_DIR" ]; then
        warn "Directory exists but not a git repo. Backing up..."
        mv "$ZICORE_DIR" "${ZICORE_DIR}.bak.$(date +%s)"
    fi
    git clone --quiet "$REPO" "$ZICORE_DIR" 2>/dev/null || {
        warn "Git clone failed. Downloading ZIP..."
        curl -sL "https://github.com/zinemotion/ZiCore-OS/archive/refs/heads/main.zip" -o /tmp/zicore.zip
        unzip -q /tmp/zicore.zip -d /tmp
        mv /tmp/zicore-system-main "$ZICORE_DIR"
        rm -f /tmp/zicore.zip
    }
    ok "Repository cloned to $ZICORE_DIR"
fi
cd "$ZICORE_DIR"

# ─── 5. Python Dependencies ──────────────────────────────────────────────────
step 5 "Installing Python dependencies..."

$PYTHON -m pip install --upgrade pip --quiet 2>/dev/null
$PYTHON -m pip install --quiet \
    fastapi "uvicorn[standard]" websockets pydantic \
    Pillow numpy httpx trimesh scipy 2>/dev/null
ok "Core Python packages installed"

# Optional ML
read -p "  Install ML/AI dependencies? (torch, diffusers) ~2GB [y/N]: " INSTALL_ML
if [ "$INSTALL_ML" = "y" ] || [ "$INSTALL_ML" = "Y" ]; then
    $PYTHON -m pip install --quiet torch --index-url https://download.pytorch.org/whl/cpu 2>/dev/null
    $PYTHON -m pip --quiet install "diffusers[torch]" transformers accelerate safetensors 2>/dev/null
    ok "ML dependencies installed"
else
    warn "Skipping ML dependencies (3D generation uses fallback)"
fi

# ─── 6. Node.js Dependencies ─────────────────────────────────────────────────
step 6 "Installing Node.js dependencies..."

KERNEL_DIR="$ZICORE_DIR/New project/ZiCore"
if [ -f "$KERNEL_DIR/package.json" ]; then
    cd "$KERNEL_DIR"
    npm install --silent 2>/dev/null
    ok "Node.js kernel dependencies installed"
else
    warn "Node.js kernel not found, skipping"
fi

# ─── 7. Configuration ────────────────────────────────────────────────────────
step 7 "Configuring ZICORE..."

CONFIG_DIR="$ZICORE_DIR/data/config"
CONFIG_FILE="$CONFIG_DIR/zio_config.json"

mkdir -p "$CONFIG_DIR"

if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" <<'CONF'
{
  "providers": {
    "openrouter": {
      "name": "OpenRouter",
      "enabled": true,
      "api_key": "",
      "base_url": "https://openrouter.ai/api/v1",
      "default_model": "nvidia/nemotron-3-super-120b-a12b:free"
    },
    "ollama": {
      "name": "Ollama",
      "enabled": false,
      "base_url": "localhost:11434",
      "default_model": "gemma3:1b"
    }
  },
  "zio": {
    "name": "ZIO",
    "personality": "copilot",
    "active_provider": "openrouter",
    "active_model": "nvidia/nemotron-3-super-120b-a12b:free"
  }
}
CONF
    ok "Default config created"
    echo -e "  → Edit ${CYAN}$CONFIG_FILE${NC} to add your API keys"
else
    ok "Config already exists"
fi

# ─── 8. Done ─────────────────────────────────────────────────────────────────
step 8 "Installation complete!"

echo ""
echo -e "${GREEN}  ╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}  ║  ZICORE installed successfully!                 ║${NC}"
echo -e "${GREEN}  ╠══════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}  ║  Portal:  http://localhost:${PORT}                  ║${NC}"
echo -e "${GREEN}  ║  Config:  ${CONFIG_DIR}  ║${NC}"
echo -e "${GREEN}  ║  Start:   cd ${ZICORE_DIR}     ║${NC}"
echo -e "${GREEN}  ║           python3 web_server.py                 ║${NC}"
echo -e "${GREEN}  ╚══════════════════════════════════════════════════╝${NC}"
echo ""

read -p "  Start ZICORE now? [Y/n]: " START_NOW
if [ "$START_NOW" != "n" ] && [ "$START_NOW" != "N" ]; then
    cd "$ZICORE_DIR"
    echo -e "${CYAN}  Starting web server on port $PORT...${NC}"
    $PYTHON web_server.py $PORT &
    sleep 2
    echo -e "${GREEN}  Open http://localhost:${PORT} in your browser${NC}"
fi

echo ""

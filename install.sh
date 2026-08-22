#!/bin/bash
# ============================================
#  ZICORE System - Linux Server Installer
#  Materializer Engine v5.0
#  Signed by ZineMotion
#
#  Usage:
#    curl -sL https://raw.githubusercontent.com/zinemotion/zicore-system/main/install.sh | bash
#    wget -qO- https://raw.githubusercontent.com/zinemotion/zicore-system/main/install.sh | bash
#
#  Or download and run:
#    curl -sLO https://raw.githubusercontent.com/zinemotion/zicore-system/main/install.sh
#    chmod +x install.sh
#    sudo ./install.sh
#
#  Prerequisites:
#    - Docker Engine installed and running
#    - Root or sudo access
#    - Internet connection
# ============================================

set -e

# --- Configuration ---
ZICORE_VERSION="5.0.0"
ZICORE_USER="${ZICORE_USER:-zicore}"
ZICORE_DIR="${ZICORE_DIR:-/opt/zicore-system}"
ZICORE_DATA="${ZICORE_DATA:-/var/lib/zicore}"
ZICORE_PORT="${ZICORE_PORT:-4000}"
ZICORE_API_PORT="${ZICORE_API_PORT:-4080}"
ZICORE_MAIL_DOMAIN="${ZICORE_MAIL_DOMAIN:-zinemotion.com}"
ZICORE_ADMIN_EMAIL="${ZICORE_ADMIN_EMAIL:-admin@zinemotion.com}"
ZICORE_ADMIN_PASS="${ZICORE_ADMIN_PASS:-ZineMotion2026!}"
INSTALL_MODE="${1:-server}"  # server or workstation

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()    { echo -e "${CYAN}[ZICORE]${NC} $1"; }
ok()     { echo -e "${GREEN}[  OK ]${NC} $1"; }
warn()   { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()  { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }

# --- Banner ---
show_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════╗"
    echo "║  ZICORE SYSTEM - Materializer Engine v${ZICORE_VERSION}    ║"
    echo "║  ZineMotion Foundation - Aerospace Division      ║"
    echo "║  License: CC-BY-SA-4.0                           ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo "  Install Mode: ${INSTALL_MODE}"
    echo "  Install Path:  ${ZICORE_DIR}"
    echo "  Data Path:     ${ZICORE_DATA}"
    echo "  Domain:        ${ZICORE_MAIL_DOMAIN}"
    echo ""
}

# --- Check Root ---
check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "Please run as root: sudo ./install.sh"
    fi
}

# --- Check Docker ---
check_docker() {
    log "Checking Docker..."
    if ! command -v docker &> /dev/null; then
        error "Docker not found! Install Docker Engine first:
  curl -fsSL https://get.docker.com | sh
  sudo systemctl enable --now docker"
    fi

    if ! docker info &> /dev/null; then
        error "Docker daemon not running! Start it:
  sudo systemctl enable --now docker"
    fi

    if ! command -v docker compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        error "Docker Compose not found! Install it:
  sudo apt install docker-compose-plugin"
    fi

    ok "Docker $(docker --version | awk '{print $3}' | tr -d ',')"
}

# --- Check System ---
check_system() {
    log "Checking system requirements..."

    # OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        log "OS: ${PRETTY_NAME:-$ID $VERSION_ID}"
    else
        warn "Cannot detect OS - continuing anyway"
    fi

    # Architecture
    ARCH=$(uname -m)
    log "Architecture: ${ARCH}"

    # Memory
    MEM=$(free -m | awk '/^Mem:/{print $2}')
    if [ "$MEM" -lt 2048 ]; then
        warn "Only ${MEM}MB RAM - recommended 4GB+"
    else
        ok "RAM: ${MEM}MB"
    fi

    # Disk
    DISK=$(df -BG / | awk 'NR==2{print $4}' | tr -d 'G')
    if [ "$DISK" -lt 10 ]; then
        warn "Only ${DISK}GB free disk - recommended 20GB+"
    else
        ok "Free disk: ${DISK}GB"
    fi

    # Ports
    for port in 25 143 465 587 993 3000 3001 3002 8080 8081 11434; do
        if ss -tlnp | grep -q ":${port} "; then
            warn "Port ${port} already in use"
        fi
    done
}

# --- Create User ---
create_user() {
    log "Creating ZICORE user..."
    if ! id "$ZICORE_USER" &>/dev/null; then
        useradd -r -m -d "${ZICORE_DIR}" -s /bin/bash "$ZICORE_USER"
        ok "User ${ZICORE_USER} created"
    else
        ok "User ${ZICORE_USER} exists"
    fi
}

# --- Install System Packages ---
install_packages() {
    log "Installing system packages..."

    if command -v apt &> /dev/null; then
        apt-get update -qq
        apt-get install -y -qq curl wget git unzip python3 python3-pip python3-venv \
            net-tools dnsutils mailutils mutt \
            build-essential libffi-dev libssl-dev
    elif command -v dnf &> /dev/null; then
        dnf install -y curl wget git unzip python3 python3-pip \
            net-tools bind-utils mailx mutt \
            gcc gcc-c++ libffi-devel openssl-devel
    elif command -v yum &> /dev/null; then
        yum install -y curl wget git unzip python3 python3-pip \
            net-tools bind-utils mailx mutt \
            gcc gcc-c++ libffi-devel openssl-devel
    elif command -v pacman &> /dev/null; then
        pacman -Sy --noconfirm curl wget git unzip python python-pip \
            net-tools bind-tools mutt \
            base-devel libffi openssl
    else
        warn "Unknown package manager - install packages manually"
    fi

    ok "System packages installed"
}

# --- Clone ZICORE ---
clone_zicore() {
    log "Installing ZICORE System..."

    if [ -d "${ZICORE_DIR}/.git" ]; then
        log "Updating existing installation..."
        cd "${ZICORE_DIR}"
        git pull origin main
    else
        if [ -d "${ZICORE_DIR}" ]; then
            warn "Directory exists, backing up..."
            mv "${ZICORE_DIR}" "${ZICORE_DIR}.bak.$(date +%s)"
        fi
        git clone https://github.com/zinemotion/zicore-system.git "${ZICORE_DIR}"
    fi

    cd "${ZICORE_DIR}"
    ok "ZICORE installed at ${ZICORE_DIR}"
}

# --- Setup Python Environment ---
setup_python() {
    log "Setting up Python virtual environment..."
    cd "${ZICORE_DIR}"

    python3 -m venv venv
    source venv/bin/activate

    pip install --upgrade pip -q
    pip install -r requirements.txt -q

    ok "Python environment ready"
}

# --- Setup Data Directories ---
setup_data() {
    log "Setting up data directories..."

    mkdir -p "${ZICORE_DATA}"/{ollama,mail,ml_models,conversations,uploads}
    mkdir -p "${ZICORE_DATA}/mail"/{vmail,postfix,dovecot,rspamd}
    mkdir -p "${ZICORE_DATA}/ollama"/models
    mkdir -p "${ZICORE_DIR}/output"
    mkdir -p "${ZICORE_DIR}/logs"

    # Symlink data dir
    ln -sf "${ZICORE_DATA}" "${ZICORE_DIR}/data/persistent"

    chown -R "${ZICORE_USER}:${ZICORE_USER}" "${ZICORE_DIR}" "${ZICORE_DATA}"

    ok "Data directories created"
}

# --- Generate SSL Certificates ---
generate_ssl() {
    log "Generating SSL certificates..."

    SSL_DIR="${ZICORE_DATA}/ssl"
    mkdir -p "${SSL_DIR}"

    if [ ! -f "${SSL_DIR}/cert.pem" ]; then
        openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
            -keyout "${SSL_DIR}/key.pem" \
            -out "${SSL_DIR}/cert.pem" \
            -subj "/C=MX/ST=CDMX/L=CDMX/O=ZineMotion/CN=mail.${ZICORE_MAIL_DOMAIN}"
        ok "SSL certificate generated"
    else
        ok "SSL certificate exists"
    fi

    chown -R "${ZICORE_USER}:${ZICORE_USER}" "${SSL_DIR}"
}

# --- Configure Docker ---
configure_docker() {
    log "Configuring Docker containers..."

    cd "${ZICORE_DIR}"

    # Create .env for Docker
    cat > .env << ENVEOF
# ZICORE System Configuration
# Generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Database
DB_ROOT_PASSWORD=$(openssl rand -hex 16)
DB_MAIL_PASSWORD=$(openssl rand -hex 16)

# Domain
MAIL_DOMAIN=${ZICORE_MAIL_DOMAIN}
MAIL_HOSTNAME=mail.${ZICORE_MAIL_DOMAIN}
MAIL_ADMIN_EMAIL=${ZICORE_ADMIN_EMAIL}
MAIL_ADMIN_PASSWORD=${ZICORE_ADMIN_PASS}

# SSL
SSL_CERT_PATH=/etc/ssl/mail/cert.pem
SSL_KEY_PATH=/etc/ssl/mail/key.pem

# Ports
WEB_PORT=${ZICORE_PORT}
API_PORT=${ZICORE_API_PORT}
ENVEOF

    chown "${ZICORE_USER}:${ZICORE_USER}" .env
    chmod 600 .env

    ok "Docker configuration ready"
}

# --- Build and Start Containers ---
start_containers() {
    log "Building and starting containers..."

    cd "${ZICORE_DIR}"

    # Build custom images
    docker compose build --no-cache

    # Start all services
    docker compose up -d

    # Wait for services
    log "Waiting for services to start..."
    sleep 30

    # Check status
    docker compose ps

    ok "All containers started"
}

# --- Initialize Database ---
init_database() {
    log "Initializing mail database..."

    cd "${ZICORE_DIR}"

    # Wait for MariaDB
    for i in $(seq 1 30); do
        if docker exec zicore-mail-db mysql -u root -e "SELECT 1" &>/dev/null; then
            break
        fi
        sleep 2
    done

    # Import schema
    docker exec -i zicore-mail-db mysql -u root zicore_mail < containers/mail/data/init.sql 2>/dev/null || true

    # Create admin user
    HASH=$(docker exec zicore-mail-db mysql -u root zicore_mail -N -e \
        "SELECT SHA2('${ZICORE_ADMIN_PASS}', 512)" 2>/dev/null || echo "")
    if [ -n "$HASH" ]; then
        docker exec zicore-mail-db mysql -u root zicore_mail -e \
            "INSERT INTO virtual_users (domain_id, email, password, name) VALUES (1, '${ZICORE_ADMIN_EMAIL}', CONCAT('\$6\$rounds=5000\$salt\$', '${HASH}'), 'Admin') ON DUPLICATE KEY UPDATE password=CONCAT('\$6\$rounds=5000\$salt\$', '${HASH}')" 2>/dev/null || true
    fi

    ok "Mail database initialized"
}

# --- Pull Ollama Models ---
pull_models() {
    log "Pulling Ollama models..."

    # Wait for Ollama
    for i in $(seq 1 30); do
        if curl -s http://localhost:11434/api/tags &>/dev/null; then
            break
        fi
        sleep 2
    done

    docker exec zicore-ollama ollama pull tinyllama &
    docker exec zicore-ollama ollama pull llama3.1:8b &
    wait

    ok "Ollama models pulled"
}

# --- Setup Systemd Service ---
setup_service() {
    log "Setting up systemd service..."

    cat > /etc/systemd/system/zicore.service << SVCEOF
[Unit]
Description=ZICORE System - Materializer Engine
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${ZICORE_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
SVCEOF

    systemctl daemon-reload
    systemctl enable zicore.service

    ok "Systemd service created"
}

# --- Setup Firewall ---
setup_firewall() {
    log "Configuring firewall..."

    if command -v ufw &> /dev/null; then
        ufw allow 22/tcp    # SSH
        ufw allow 25/tcp    # SMTP
        ufw allow 143/tcp   # IMAP
        ufw allow 465/tcp   # SMTPS
        ufw allow 587/tcp   # Submission
        ufw allow 993/tcp   # IMAPS
        ufw allow 995/tcp   # POP3S
        ufw allow ${ZICORE_PORT}/tcp   # Web UI
        ufw allow ${ZICORE_API_PORT}/tcp  # API
        ufw allow 3001/tcp  # EmulatorJS
        ufw allow 3002/tcp  # Webamp
        ufw allow 8080/tcp  # Webmail
        ufw allow 8081/tcp  # FileBrowser
        ufw allow 11434/tcp # Ollama
        ufw --force enable
        ok "UFW firewall configured"
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=22/tcp
        firewall-cmd --permanent --add-port=25/tcp
        firewall-cmd --permanent --add-port=143/tcp
        firewall-cmd --permanent --add-port=465/tcp
        firewall-cmd --permanent --add-port=587/tcp
        firewall-cmd --permanent --add-port=993/tcp
        firewall-cmd --permanent --add-port=995/tcp
        firewall-cmd --permanent --add-port=${ZICORE_PORT}/tcp
        firewall-cmd --permanent --add-port=${ZICORE_API_PORT}/tcp
        firewall-cmd --permanent --add-port=3001/tcp
        firewall-cmd --permanent --add-port=3002/tcp
        firewall-cmd --permanent --add-port=8080/tcp
        firewall-cmd --permanent --add-port=8081/tcp
        firewall-cmd --permanent --add-port=11434/tcp
        firewall-cmd --reload
        ok "Firewalld configured"
    else
        warn "No firewall manager found - configure manually"
    fi
}

# --- Print Summary ---
print_summary() {
    SERVER_IP=$(hostname -I | awk '{print $1}')

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ZICORE SYSTEM INSTALLED SUCCESSFULLY!          ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Services:"
    echo "    - Web UI:        http://${SERVER_IP}:${ZICORE_PORT}"
    echo "    - API:           http://${SERVER_IP}:${ZICORE_API_PORT}"
    echo "    - Webmail:       http://${SERVER_IP}:4080"
    echo "    - EmulatorJS:    http://${SERVER_IP}:4001"
    echo "    - Webamp:        http://${SERVER_IP}:4002"
    echo "    - Ollama:        http://${SERVER_IP}:11434"
    echo ""
    echo "  Mail Server:"
    echo "    - SMTP:          ${SERVER_IP}:25"
    echo "    - IMAP:          ${SERVER_IP}:993"
    echo "    - Admin Email:   ${ZICORE_ADMIN_EMAIL}"
    echo ""
    echo "  Management:"
    echo "    - Status:        sudo systemctl status zicore"
    echo "    - Logs:          cd ${ZICORE_DIR} && docker compose logs"
    echo "    - Restart:       sudo systemctl restart zicore"
    echo "    - Update:        cd ${ZICORE_DIR} && git pull && docker compose up -d --build"
    echo ""
    echo "  DNS Records needed for ${ZICORE_MAIL_DOMAIN}:"
    echo "    MX   @                  mail.${ZICORE_MAIL_DOMAIN} (priority 10)"
    echo "    A    mail               ${SERVER_IP}"
    echo "    TXT  @                  v=spf1 mx a ip4:${SERVER_IP} -all"
    echo "    TXT  _dmarc             v=DMARC1; p=reject; rua=mailto:${ZICORE_ADMIN_EMAIL}"
    echo ""
    echo "  Signed by ZineMotion | CC-BY-SA-4.0"
    echo ""
}

# --- Main ---
main() {
    show_banner
    check_root
    check_system
    check_docker
    create_user
    install_packages
    clone_zicore
    setup_python
    setup_data
    generate_ssl
    configure_docker
    start_containers
    init_database
    pull_models
    setup_service
    setup_firewall
    print_summary
}

main "$@"

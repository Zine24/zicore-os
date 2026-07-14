@echo off
REM ============================================
REM  ZICORE System - WSL Build Environment
REM  Creates Linux build environment inside WSL
REM  Signed by ZineMotion
REM ============================================
echo.
echo  ZICORE System - WSL Build Environment
echo  =====================================
echo.

REM Check WSL is available
wsl --list --verbose 2>nul
if %errorLevel% neq 0 (
    echo [ERROR] WSL not installed!
    echo Install WSL: wsl --install
    pause
    exit /b 1
)

echo [1/4] Creating ZICORE build workspace in WSL...
wsl -e bash -c "mkdir -p /mnt/c/Users/zinem/Documents/zicore-system/wsl/build"

echo [2/4] Creating WSL build Dockerfile...
wsl -e bash -c "cat > /mnt/c/Users/zinem/Documents/zicore-system/wsl/build/Dockerfile << 'DOCKERFILE'
FROM ubuntu:22.04
LABEL maintainer=\"ZineMotion - ZICORE System\"

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV ZICORE_VERSION=5.0.0

RUN apt-get update && apt-get install -y \\
    curl wget git unzip sudo \\
    python3 python3-pip python3-venv \\
    docker.io docker-compose-plugin \\
    net-tools dnsutils \\
    build-essential libffi-dev libssl-dev \\
    && rm -rf /var/lib/apt/lists/*

# Create zicore user
RUN useradd -m -s /bin/bash zicore && echo \"zicore ALL=(ALL) NOPASSWD:ALL\" >> /etc/sudoers

USER zicore
WORKDIR /home/zicore

# Clone ZICORE
RUN git clone https://github.com/zinemotion/zicore-system.git /home/zicore/zicore-system || true

# Setup Python
RUN cd /home/zicore/zicore-system && python3 -m venv venv && . venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt || true

EXPOSE 3000 8080 8081 3001 3002 11434 25 143 465 587 993 995

CMD [\"/bin/bash\"]
DOCKERFILE"

echo [3/4] Creating WSL build script...
wsl -e bash -c "cat > /mnt/c/Users/zinem/Documents/zicore-system/wsl/build/build.sh << 'BUILDSH'
#!/bin/bash
# ZICORE WSL Build Script
set -e

ZICORE_DIR=\"/home/zicore/zicore-system\"
BUILD_DIR=\"/home/zicore/build\"

echo \"[ZICORE] Starting WSL build...\"

# Build Docker image
cd \"\$ZICORE_DIR\"
docker build -t zicore-system:latest -f wsl/build/Dockerfile .

# Build individual service images
echo \"[ZICORE] Building mail server...\"
docker build -t zicore-mail:latest -f containers/mail/postfix/Dockerfile containers/mail/postfix/
docker build -t zicore-dovecot:latest -f containers/mail/dovecot/Dockerfile containers/mail/dovecot/

echo \"[ZICORE] Building tool containers...\"
docker build -t zicore-emulatorjs:latest -f containers/emulatorjs/Dockerfile .
docker build -t zicore-webamp:latest -f containers/webamp/Dockerfile .

echo \"[ZICORE] Exporting images...\"
mkdir -p \"\$BUILD_DIR\"
docker save zicore-system:latest | gzip > \"\$BUILD_DIR/zicore-system.tar.gz\"
docker save zicore-mail:latest zicore-dovecot:latest | gzip > \"\$BUILD_DIR/zicore-mail.tar.gz\"
docker save zicore-emulatorjs:latest zicore-webamp:latest | gzip > \"\$BUILD_DIR/zicore-tools.tar.gz\"

echo \"[ZICORE] Build complete! Images in \$BUILD_DIR\"
ls -lh \"\$BUILD_DIR\"
BUILDSH
chmod +x /mnt/c/Users/zinem/Documents/zicore-system/wsl/build/build.sh"

echo [4/4] Creating WSL init script...
wsl -e bash -c "cat > /mnt/c/Users/zinem/Documents/zicore-system/wsl/init_wsl.sh << 'INITWSH'
#!/bin/bash
# Initialize WSL environment for ZICORE development
set -e

echo \"[ZICORE] Initializing WSL build environment...\"

# Update system
sudo apt-get update -qq
sudo apt-get install -y -qq curl wget git unzip python3 python3-pip docker.io

# Add user to docker group
sudo usermod -aG docker \$USER

# Create workspace
mkdir -p ~/zicore-build
cd ~/zicore-build

# Clone repo
if [ ! -d \"zicore-system\" ]; then
    git clone https://github.com/zinemotion/zicore-system.git
fi

cd zicore-system
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo \"[ZICORE] WSL environment ready!\"
echo \"  Run: cd ~/zicore-build/zicore-system\"
echo \"  Run: bash wsl/build/build.sh\"
INITWSH
chmod +x /mnt/c/Users/zinem/Documents/zicore-system/wsl/init_wsl.sh"

echo.
echo ============================================
echo  WSL Build Environment Created!
echo.
echo  To initialize WSL:
echo    wsl -e bash -c "bash /mnt/c/Users/zinem/Documents/zicore-system/wsl/init_wsl.sh"
echo.
echo  To build Docker images:
echo    wsl -e bash -c "bash /mnt/c/Users/zinem/Documents/zicore-system/wsl/build/build.sh"
echo.
echo  To deploy to Linux server:
echo    scp install.sh user@server:/tmp/
echo    ssh user@server "sudo bash /tmp/install.sh"
echo.
echo  Signed by ZineMotion
echo ============================================
pause

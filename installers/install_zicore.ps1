<# 
  ZICORE System — Windows Installer v5.0
  Installs: Python 3.12+, Node.js 20+, Ollama, dependencies
  Run in PowerShell as Administrator
  Signed by ZineMotion — zicore.space
#>

$ErrorActionPreference = "Continue"
$ZICORE_VERSION = "5.0.0"
$ZICORE_DIR = "$env:USERPROFILE\zicore-system"
$PORT = 4000

# ─── Banner ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║     ZICORE SYSTEM v$ZICORE_VERSION                      ║" -ForegroundColor Cyan
Write-Host "  ║     Digital Aerospace Operating System          ║" -ForegroundColor Cyan
Write-Host "  ║     Windows Installer — zicore.space            ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$steps = @(
    "Checking prerequisites",
    "Installing Python 3.12+",
    "Installing Node.js 20+",
    "Cloning ZICORE repository",
    "Installing Python dependencies",
    "Installing Node.js dependencies",
    "Configuring ZICORE",
    "Starting services"
)

function Write-Step($i, $msg) {
    Write-Host "[$i/$($steps.Count)] $msg" -ForegroundColor Yellow
}

function Write-Ok($msg) {
    Write-Host "  ✓ $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "  ⚠ $msg" -ForegroundColor DarkYellow
}

function Write-Err($msg) {
    Write-Host "  ✗ $msg" -ForegroundColor Red
}

# ─── 1. Prerequisites ────────────────────────────────────────────────────────
Write-Step 1 "Checking prerequisites..."

# Check winget
$hasWinget = Get-Command winget -ErrorAction SilentlyContinue
if (-not $hasWinget) {
    Write-Warn "winget not found. Install App Installer from Microsoft Store."
    Write-Host "  Opening Microsoft Store..." -ForegroundColor Gray
    Start-Process "ms-windows-store://pdp/?productid=9NBLGGH4NNS1"
    Write-Host "  Press Enter after installing winget..." -ForegroundColor Gray
    Read-Host
}

# Check git
$hasGit = Get-Command git -ErrorAction SilentlyContinue
if (-not $hasGit) {
    Write-Host "  Installing Git..." -ForegroundColor Gray
    winget install Git.Git --silent --accept-package-agreements --accept-source-agreements 2>$null
    $env:PATH = "$env:ProgramFiles\Git\cmd;$env:LOCALAPPDATA\Programs\Git\cmd;$env:PATH"
}
Write-Ok "Git ready"

# ─── 2. Python ────────────────────────────────────────────────────────────────
Write-Step 2 "Checking Python..."

$pythonCmd = $null
foreach ($cmd in @("python3", "python")) {
    $found = Get-Command $cmd -ErrorAction SilentlyContinue
    if ($found) {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python 3\.1[0-9]") {
            $pythonCmd = $cmd
            break
        }
    }
}

if (-not $pythonCmd) {
    Write-Host "  Installing Python 3.12..." -ForegroundColor Gray
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements 2>$null
    $env:PATH = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;$env:PATH"
    $pythonCmd = "python"
}
Write-Ok "Python ready: $pythonCmd"

# ─── 3. Node.js ───────────────────────────────────────────────────────────────
Write-Step 3 "Checking Node.js..."

$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Write-Host "  Installing Node.js 20 LTS..." -ForegroundColor Gray
    winget install OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements 2>$null
    $env:PATH = "$env:ProgramFiles\nodejs;$env:PATH"
}
$nodeVer = & node --version 2>&1
Write-Ok "Node.js ready: $nodeVer"

# ─── 4. Clone / Update ───────────────────────────────────────────────────────
Write-Step 4 "Setting up ZICORE repository..."

if (Test-Path "$ZICORE_DIR\.git") {
    Write-Host "  Updating existing installation..." -ForegroundColor Gray
    Set-Location $ZICORE_DIR
    & git pull origin main 2>$null
} else {
    Write-Host "  Cloning zicore-system..." -ForegroundColor Gray
    & git clone https://github.com/zinemotion/ZiCore-OS.git $ZICORE_DIR 2>$null
    if (-not (Test-Path "$ZICORE_DIR\.git")) {
        Write-Warn "Git clone failed. Downloading ZIP..."
        $zipUrl = "https://github.com/zinemotion/ZiCore-OS/archive/refs/heads/main.zip"
        $zipPath = "$env:TEMP\zicore-main.zip"
        Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing 2>$null
        Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
        Move-Item "$env:TEMP\zicore-system-main" $ZICORE_DIR -Force
        Remove-Item $zipPath -Force
    }
}
Set-Location $ZICORE_DIR
Write-Ok "Repository ready at $ZICORE_DIR"

# ─── 5. Python Dependencies ──────────────────────────────────────────────────
Write-Step 5 "Installing Python dependencies (this may take a few minutes)..."

& $pythonCmd -m pip install --upgrade pip 2>$null | Out-Null
& $pythonCmd -m pip install fastapi "uvicorn[standard]" websockets pydantic Pillow numpy httpx trimesh 2>$null | Out-Null
Write-Ok "Core Python packages installed"

# Optional: ML dependencies (heavy, ~2GB)
$installML = Read-Host "  Install ML/AI dependencies? (torch, diffusers) [y/N]"
if ($installML -eq "y" -or $installML -eq "Y") {
    Write-Host "  Installing ML dependencies (~2GB download)..." -ForegroundColor Gray
    & $pythonCmd -m pip install torch --index-url https://download.pytorch.org/whl/cpu 2>$null | Out-Null
    & $pythonCmd -m pip install "diffusers[torch]" transformers accelerate safetensors scipy 2>$null | Out-Null
    Write-Ok "ML dependencies installed"
} else {
    Write-Warn "Skipping ML dependencies (3D generation will use fallback)"
}

# ─── 6. Node.js Dependencies ─────────────────────────────────────────────────
Write-Step 6 "Installing Node.js dependencies..."

$kernelDir = "$ZICORE_DIR\New project\ZiCore"
if (Test-Path "$kernelDir\package.json") {
    Set-Location $kernelDir
    & npm install --silent 2>$null
    Write-Ok "Node.js kernel dependencies installed"
} else {
    Write-Warn "Node.js kernel not found, skipping"
}

# ─── 7. Configuration ────────────────────────────────────────────────────────
Write-Step 7 "Configuring ZICORE..."

$configDir = "$ZICORE_DIR\data\config"
$configFile = "$configDir\zio_config.json"

if (-not (Test-Path $configFile)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
    
    $config = @"
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
"@
    Set-Content -Path $configFile -Value $config -Encoding UTF8
    Write-Ok "Default config created"
    Write-Host "  → Edit $configFile to add your API keys" -ForegroundColor Gray
} else {
    Write-Ok "Config already exists"
}

# ─── 8. Start Services ──────────────────────────────────────────────────────
Write-Step 8 "Starting ZICORE Web Server..."

$webServer = "$ZICORE_DIR\web_server.py"
if (Test-Path $webServer) {
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "  ║  ZICORE installed successfully!                 ║" -ForegroundColor Green
    Write-Host "  ╠══════════════════════════════════════════════════╣" -ForegroundColor Green
    Write-Host "  ║  Portal:  http://localhost:$PORT                   ║" -ForegroundColor Green
    Write-Host "  ║  Config:  $configDir  ║" -ForegroundColor Green
    Write-Host "  ║  Start:   cd $ZICORE_DIR     ║" -ForegroundColor Green
    Write-Host "  ║           python web_server.py                  ║" -ForegroundColor Green
    Write-Host "  ╚══════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    
    $startNow = Read-Host "  Start ZICORE now? [Y/n]"
    if ($startNow -ne "n" -and $startNow -ne "N") {
        Write-Host "  Starting web server on port $PORT..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ZICORE_DIR'; python web_server.py $PORT"
    }
} else {
    Write-Err "web_server.py not found at $webServer"
}

Write-Host ""
Write-Host "  Installation complete." -ForegroundColor Cyan
Write-Host ""

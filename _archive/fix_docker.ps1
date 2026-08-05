# ============================================
#  ZICORE Docker Fix Script
#  Run as Administrator after PC restart
#  Fixes broken WSL2 and Docker Desktop
# ============================================
#Requires -RunAsAdministrator

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ZICORE Docker Fix Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Shutdown WSL completely
Write-Host "[1/5] Shutting down WSL..." -ForegroundColor Yellow
wsl --shutdown 2>&1
Start-Sleep -Seconds 3

# Step 2: Unregister broken WSL distro
Write-Host "[2/5] Removing broken WSL distro..." -ForegroundColor Yellow
wsl --unregister Ubuntu-22.04 2>&1
Start-Sleep -Seconds 2

# Step 3: Remove broken .wslconfig
Write-Host "[3/5] Cleaning WSL config..." -ForegroundColor Yellow
Remove-Item "$env:USERPROFILE\.wslconfig" -Force -ErrorAction SilentlyContinue

# Clean WSL state directory
$wslDir = "$env:LOCALAPPDATA\Packages\MicrosoftCorporationII.WindowsSubsystemForLinux_8wekyb3d8bbwe\LocalState"
if (Test-Path $wslDir) {
    Remove-Item "$wslDir\*.vhdx" -Force -ErrorAction SilentlyContinue
    Write-Host "  Cleaned WSL state files"
}

# Step 4: Install fresh Ubuntu
Write-Host "[4/5] Installing fresh Ubuntu WSL distro..." -ForegroundColor Yellow
Write-Host "  (This may take a few minutes)"
wsl --install Ubuntu-22.04 2>&1

# Step 5: Wait and verify
Write-Host "[5/5] Verifying WSL..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
$distros = wsl --list --verbose 2>&1
if ($distros -match "Ubuntu-22.04") {
    Write-Host "  [OK] Ubuntu WSL installed" -ForegroundColor Green
} else {
    Write-Host "  [WARN] WSL distro may still be installing" -ForegroundColor Yellow
}

# Step 6: Start Docker Desktop
Write-Host ""
Write-Host "Starting Docker Desktop..." -ForegroundColor Yellow
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -PassThru | Select-Object Id

# Step 7: Wait for Docker daemon
Write-Host "Waiting for Docker daemon (this may take 2-3 minutes)..."
$dockerExe = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 10
    & $dockerExe info 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  Docker is READY!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        & $dockerExe version
        Write-Host ""
        Write-Host "Next: Start ZICORE with:" -ForegroundColor Cyan
        Write-Host "  python start_all.py" -ForegroundColor White
        break
    }
    Write-Host "  [$($i*10)s] waiting..."
}

& $dockerExe info 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Docker daemon did not start. Check Docker Desktop UI for errors." -ForegroundColor Yellow
    Write-Host "You may need to manually open Docker Desktop and wait for initialization." -ForegroundColor Yellow
}

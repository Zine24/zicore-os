@echo off
REM ╔══════════════════════════════════════════════════╗
REM ║     ZIO UNIFIED (ZiCAM)                          ║
REM ║     ESP32-S3 CAM + Desktop Control               ║
REM ║     Installer - zicore.space                     ║
REM ╚══════════════════════════════════════════════════╝
REM
REM Usage:
REM   powershell -ExecutionPolicy Bypass -File ziounified_setup.bat
REM   or double-click (right click -> Run as Administrator)

@setlocal EnableDelayedExpansion
set "VERSION=5.0.0"
set "ZIO_DIR=%USERPROFILE%\ZioUnified"
set "REPO=https://github.com/Zine24/ZioUnified.git"

echo.
echo   ╔══════════════════════════════════════════════════╗
echo   ║     ZIO UNIFIED (ZiCAM)  v%VERSION%               ║
echo   ║     ESP32-S3 CAM + Desktop Control               ║
echo   ║     Installer - zicore.space                     ║
echo   ╚══════════════════════════════════════════════════╝
echo.

REM ── 1/4 git ─────────────────────────────────────────────────────────
echo [1/4] Verificando git...
git --version >nul 2>&1
if errorlevel 1 (
    echo   [!] git no instalado. Instalando via winget...
    winget install --id Git.Git -e --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
    if errorlevel 1 (
        echo   [X] No se pudo instalar git. Instalalo desde https://git-scm.com/
        exit /b 1
    )
)
echo   [OK] git listo

REM ── 2/4 clonar ───────────────────────────────────────────────────────
echo [2/4] Clonando ZioUnified...
if exist "%ZIO_DIR%\.git" (
    echo   [!] Ya existe. Actualizando...
    pushd "%ZIO_DIR%" >nul
    git pull --ff-only
    popd >nul
) else (
    git clone "%REPO%" "%ZIO_DIR%"
    if errorlevel 1 (
        echo   [X] Fallo al clonar.
        exit /b 1
    )
)
echo   [OK] Repositorio en %ZIO_DIR%

REM ── 3/4 python (visualizador + esptool) ─────────────────────────────
echo [3/4] Preparando entorno Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo   [!] Python no encontrado. Instalalo desde https://www.python.org/
    echo       (marca "Add Python to PATH")
) else (
    python -m pip install --quiet --upgrade pip
    python -m pip install --quiet esptool
)
echo   [OK] Entorno listo

REM ── 4/4 verificar ───────────────────────────────────────────────────
echo [4/4] Verificando instalacion...
if exist "%ZIO_DIR%\firmware\ZiCAM_ESP32-S3\ZiCAM_ESP32-S3.ino" (
    echo   [OK] Firmware: %ZIO_DIR%\firmware\ZiCAM_ESP32-S3\
) else (
    echo   [!] Estructura del firmware no encontrada.
)

echo.
echo   ┌────────────────────────────────────────────────────┐
echo   │  ZIO UNIFIED instalado                              │
echo   │                                                    │
echo   │  Firmware ESP32-S3:  firmware\ZiCAM_ESP32-S3\      │
echo   │    - Abrir el .ino en Arduino IDE (board S3)       │
echo   │    - Editar zicam_config.h (WiFi / AP por defecto) │
echo   │    - AP: ZIOCONTROL / 12345678 / 192.168.4.1      │
echo   │                                                    │
echo   │  Control desktop:  desktop\Desktop_Visualizer\     │
echo   │    cd %ZIO_DIR%                                     │
echo   │    python -m http.server 8000                      │
echo   │    abrir http://localhost:8000/desktop/...         │
echo   │                                                    │
echo   │  Stream: http://<ESP_IP>:81/stream                 │
echo   └────────────────────────────────────────────────────┘
echo.
echo   ZioUnified listo. (C) ZineMotion Foundation
pause

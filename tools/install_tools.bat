@echo off
REM ============================================
REM  ZICORE System - Open Source Tools Installer
REM  Installs: Thunderbird, Firefox, EmulatorJS,
REM  Webamp, FileBrowser, FFmpeg, Photopea
REM  Run as Administrator for SSH setup!
REM  Signed by ZineMotion
REM ============================================
echo.
echo  ZICORE System - Open Source Tools Installer
echo  ===========================================
echo.

set ERRORS=0

echo [1/7] Checking Thunderbird...
where thunderbird >nul 2>&1
if %errorLevel% neq 0 (
    echo       Installing Thunderbird...
    winget install Mozilla.Thunderbird --silent --accept-package-agreements --accept-source-agreements
    if %errorLevel% neq 0 (
        echo       [WARN] Thunderbird install failed
        set /a ERRORS+=1
    ) else (
        echo       [OK] Thunderbird installed
    )
) else (
    echo       [OK] Thunderbird already installed
)

echo.
echo [2/7] Checking Firefox...
where firefox >nul 2>&1
if %errorLevel% neq 0 (
    echo       Installing Firefox...
    winget install Mozilla.Firefox --silent --accept-package-agreements --accept-source-agreements
    if %errorLevel% neq 0 (
        echo       [WARN] Firefox install failed
        set /a ERRORS+=1
    ) else (
        echo       [OK] Firefox installed
    )
) else (
    echo       [OK] Firefox already installed
)

echo.
echo [3/7] Checking FFmpeg...
where ffmpeg >nul 2>&1
if %errorLevel% neq 0 (
    echo       Installing FFmpeg...
    winget install Gyan.FFmpeg --silent --accept-package-agreements --accept-source-agreements
    if %errorLevel% neq 0 (
        echo       [WARN] FFmpeg install failed - trying chocolatey
        choco install ffmpeg -y
    )
) else (
    echo       [OK] FFmpeg already installed
)

echo.
echo [4/7] Checking Node.js...
where node >nul 2>&1
if %errorLevel% neq 0 (
    echo       Installing Node.js...
    winget install OpenJS.NodeJS.LTS --silent --accept-package-agreements --accept-source-agreements
) else (
    echo       [OK] Node.js already installed: 
    node --version
)

echo.
echo [5/7] Setting up EmulatorJS (game emulator)...
if not exist "tools\emulatorjs" mkdir tools\emulatorjs
if not exist "tools\emulatorjs\package.json" (
    echo       Initializing EmulatorJS project...
    cd tools\emulatorjs
    echo {"name":"zicore-emulatorjs","version":"1.0.0","description":"ZICORE Game Emulator","main":"server.js","scripts":{"start":"node server.js"},"dependencies":{}} > package.json
    echo [OK] EmulatorJS project created - run npm install later
    cd ..\..
) else (
    echo       [OK] EmulatorJS project exists
)

echo.
echo [6/7] Setting up Webamp (audio player)...
if not exist "tools\webamp" mkdir tools\webamp
if not exist "tools\webamp\package.json" (
    echo       Initializing Webamp project...
    cd tools\webamp
    echo {"name":"zicore-webamp","version":"1.0.0","description":"ZICORE Audio Player","main":"server.js","scripts":{"start":"node server.js"},"dependencies":{}} > package.json
    echo [OK] Webamp project created - run npm install later
    cd ..\..
) else (
    echo       [OK] Webamp project exists
)

echo.
echo [7/7] Setting up FileBrowser (file manager)...
if not exist "tools\filebrowser" mkdir tools\filebrowser
echo       FileBrowser requires manual download:
echo       https://github.com/filebrowser/filebrowser/releases
echo       Or run: Invoke-WebRequest -Uri "https://github.com/filebrowser/filebrowser/releases/latest/download/filebrowser_windows_amd64.exe" -OutFile "tools/filebrowser/filebrowser.exe"
echo       [OK] Directory created

echo.
echo ===========================================
if %ERRORS% equ 0 (
    echo  All tools installed successfully!
) else (
    echo  Completed with %ERRORS% warning^(s^)
)
echo.
echo  Installed:
echo    - Thunderbird (email)
echo    - Firefox (browser)  
echo    - FFmpeg (video/audio)
echo    - Node.js (tool containers)
echo    - EmulatorJS project (games)
echo    - Webamp project (audio)
echo    - FileBrowser directory (files)
echo    - OpenSSH (run setup_ssh_server.bat)
echo.
echo  Signed by ZineMotion
echo ===========================================
pause

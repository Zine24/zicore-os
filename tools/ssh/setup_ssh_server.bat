@echo off
REM ============================================
REM  ZICORE System - OpenSSH Server Setup
REM  Run as Administrator!
REM  Signed by ZineMotion
REM ============================================
echo.
echo  ZICORE System - OpenSSH Server Setup
echo  =====================================
echo.

REM Check admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] This script must be run as Administrator!
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo [1/5] Enabling OpenSSH Server feature...
powershell -Command "Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0" 2>nul
if %errorLevel% neq 0 (
    echo [INFO] Feature may already be enabled, continuing...
)

echo [2/5] Starting sshd service...
net start sshd 2>nul
if %errorLevel% neq 0 (
    echo [INFO] Service may already be running
)

echo [3/5] Setting sshd to start automatically...
sc config sshd start= auto

echo [4/5] Configuring firewall rule...
netsh advfirewall firewall add rule name="ZICORE SSH" dir=in action=allow protocol=TCP localport=22 2>nul

echo [5/5] Verifying SSH server status...
sc query sshd | findstr STATE

echo.
echo ============================================
echo  OpenSSH Server configured successfully!
echo  Port: 22
echo  Connect: ssh zinem@localhost
echo ============================================
echo.
pause

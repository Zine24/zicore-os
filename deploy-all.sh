#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# ZICORE SYSTEM — Deploy Script
# Deploys all changes to .85 server
# Run from Windows: bash deploy-all.sh
# ═══════════════════════════════════════════════════════════════

set -e

SERVER="z@192.168.1.85"
REMOTE="/opt/zicore-materializer"
LOCAL="$(dirname "$0")"

echo "  ╔══════════════════════════════════════╗"
echo "  ║  ZICORE Deploy — Full System Update  ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# Test connection
echo "Testing connection to .85..."
ssh -o ConnectTimeout=5 $SERVER "echo 'Connected OK'" || {
    echo "ERROR: Cannot connect to $SERVER"
    echo "Make sure you're on the same network or use Tailscale"
    exit 1
}

# ── 1. Backend (web_server.py) ──────────────────────────────
echo "[1/6] Deploying web_server.py..."
scp "$LOCAL/web_server.py" $SERVER:$REMOTE/web_server.py

# ── 2. ZICORE modules ──────────────────────────────────────
echo "[2/6] Deploying zicore/ modules..."
scp "$LOCAL/zicore/sso.py" $SERVER:$REMOTE/zicore/sso.py
scp "$LOCAL/zicore/mail_integration.py" $SERVER:$REMOTE/zicore/mail_integration.py
scp "$LOCAL/zicore/crypto_payment.py" $SERVER:$REMOTE/zicore/crypto_payment.py
scp "$LOCAL/zicore/generation_library.py" $SERVER:$REMOTE/zicore/generation_library.py
scp "$LOCAL/zicore/outpreview.py" $SERVER:$REMOTE/zicore/outpreview.py
scp "$LOCAL/zicore/materializer_workflow.py" $SERVER:$REMOTE/zicore/materializer_workflow.py
scp "$LOCAL/zicore/local_generators.py" $SERVER:$REMOTE/zicore/local_generators.py
scp "$LOCAL/zicore/materializer.py" $SERVER:$REMOTE/zicore/materializer.py

# ── 3. Frontend files ──────────────────────────────────────
echo "[3/6] Deploying frontend..."
scp "$LOCAL/frontend/sso-login.html" $SERVER:$REMOTE/frontend/sso-login.html
scp "$LOCAL/frontend/zicore-portal.html" $SERVER:$REMOTE/frontend/zicore-portal.html
scp "$LOCAL/frontend/browser.html" $SERVER:$REMOTE/frontend/browser.html
scp "$LOCAL/frontend/zicore-print.html" $SERVER:$REMOTE/frontend/zicore-print.html
scp "$LOCAL/frontend/materializer.html" $SERVER:$REMOTE/frontend/materializer.html
scp "$LOCAL/frontend/outpreview.html" $SERVER:$REMOTE/frontend/outpreview.html
scp "$LOCAL/frontend/video-editor.html" $SERVER:$REMOTE/frontend/video-editor.html
scp "$LOCAL/frontend/dashboard.html" $SERVER:$REMOTE/frontend/dashboard.html
scp "$LOCAL/frontend/videochat.html" $SERVER:$REMOTE/frontend/videochat.html
scp "$LOCAL/frontend/aerospace-engineering.html" $SERVER:$REMOTE/frontend/aerospace-engineering.html
scp "$LOCAL/frontend/zio.html" $SERVER:$REMOTE/frontend/zio.html
scp "$LOCAL/frontend/games.html" $SERVER:$REMOTE/frontend/games.html
scp "$LOCAL/frontend/settings.html" $SERVER:$REMOTE/frontend/settings.html
scp "$LOCAL/frontend/mail-portal.html" $SERVER:$REMOTE/frontend/mail-portal.html
scp "$LOCAL/frontend/web-stats.html" $SERVER:$REMOTE/frontend/web-stats.html
scp "$LOCAL/frontend/mobile-monitor.html" $SERVER:$REMOTE/frontend/mobile-monitor.html
scp "$LOCAL/frontend/zicore-bank.html" $SERVER:$REMOTE/frontend/zicore-bank.html
scp "$LOCAL/frontend/api-docs.html" $SERVER:$REMOTE/frontend/api-docs.html
scp "$LOCAL/frontend/storage.html" $SERVER:$REMOTE/frontend/storage.html
scp "$LOCAL/frontend/services.html" $SERVER:$REMOTE/frontend/services.html
scp "$LOCAL/frontend/aerospace-portal.html" $SERVER:$REMOTE/frontend/aerospace-portal.html
scp "$LOCAL/frontend/zinemotion-portal.html" $SERVER:$REMOTE/frontend/zinemotion-portal.html
scp "$LOCAL/frontend/developer-portal.html" $SERVER:$REMOTE/frontend/developer-portal.html

# ── 3b. CSS & JS shared assets ─────────────────────────────
echo "[3b/6] Deploying shared CSS/JS..."
ssh $SERVER "mkdir -p $REMOTE/frontend/css $REMOTE/frontend/js"
scp "$LOCAL/frontend/css/zicore-ui.css" $SERVER:$REMOTE/frontend/css/zicore-ui.css
scp "$LOCAL/frontend/js/zicore-topbar.js" $SERVER:$REMOTE/frontend/js/zicore-topbar.js
scp "$LOCAL/frontend/storage.html" $SERVER:$REMOTE/frontend/storage.html

# ── 4. Agent modules ───────────────────────────────────────
echo "[4/6] Deploying agent/..."
scp "$LOCAL/agent/core.py" $SERVER:$REMOTE/agent/core.py

# ── 5. Mail config ────────────────────────────────────────
echo "[5/6] Deploying mail config..."
scp "$LOCAL/containers/mail/.env" $SERVER:$REMOTE/containers/mail/.env
scp "$LOCAL/containers/mail/scripts/gmail_sync.py" $SERVER:$REMOTE/containers/mail/scripts/gmail_sync.py 2>/dev/null || true
scp "$LOCAL/containers/mail/scripts/gmail_sync.sh" $SERVER:$REMOTE/containers/mail/scripts/gmail_sync.sh 2>/dev/null || true

# ── 6. Android setup + distro ──────────────────────────────
echo "[6/6] Deploying Android + distro..."
ssh $SERVER "mkdir -p $REMOTE/android $REMOTE/distro"
scp "$LOCAL/android/termux-setup.sh" $SERVER:$REMOTE/android/termux-setup.sh
scp "$LOCAL/android/app/build/outputs/apk/debug/app-debug.apk" $SERVER:$REMOTE/distro/zicore-android.apk 2>/dev/null || echo "  APK not built yet — skip"

# ── 6. Restart service ─────────────────────────────────────
echo "[6/6] Restarting zicore-materializer..."
ssh $SERVER "sudo systemctl restart zicore-materializer"

echo ""
echo "══════════════════════════════════════════"
echo "  Deploy complete!"
echo "  Server: https://zcs.zicore.space"
echo "══════════════════════════════════════════"

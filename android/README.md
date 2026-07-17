# ZICORE Android

## Quick Start

### Option 1: Build with Android Studio
1. Open `android/` folder in Android Studio
2. Let Gradle sync
3. Connect Android device or start emulator
4. Click Run ▶

### Option 2: Build from command line
```bash
cd android/
./gradlew assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

### Option 3: Install via ADB
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Server Connection

On first launch, ZICORE asks which server to connect to:

| Option | URL | Description |
|--------|-----|-------------|
| ☁ Cloud | `https://zcs.zicore.space` | ZICORE cloud server |
| 📱 Termux | `http://localhost:4000` | Local backend on phone |
| 🌐 Custom | User-defined | Your own server |

## Termux Backend (Offline Mode)

For full offline operation:

1. Install **Termux** from F-Droid (NOT Play Store)
2. Run the setup script:
   ```bash
   bash termux-setup.sh
   ```
3. Start ZICORE:
   ```bash
   bash ~/start-zicore.sh
   ```
4. Open ZICORE Android app → Select "Termux Local"

## Features

- WebView-based interface
- Auto-reconnect on network loss
- SSO token persistence
- Camera & microphone access
- File upload support
- Geolocation support
- Immersive fullscreen mode

## Permissions

| Permission | Use |
|------------|-----|
| INTERNET | Connect to server |
| CAMERA | ZICORE Print camera |
| RECORD_AUDIO | ZIO voice input |
| WAKE_LOCK | Keep alive in background |

## Requirements

- Android 7.0+ (API 24)
- ~5MB storage
- Internet connection (or Termux for offline)

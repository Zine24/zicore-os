# ZICORE Mobile App — React Native + Expo

## Overview
Cross-platform mobile app (Android + iOS) for ZICORE system administration and module control. Built with React Native + Expo, distributed as APK from vps.zicore.space.

---

## Tech Stack

| Component | Choice | Reason |
|-----------|--------|--------|
| Framework | **React Native + Expo SDK 52+** | Single codebase, OTA updates, easy APK build |
| Navigation | **Expo Router v4** (file-based) | Modern, typed, deep linking |
| State | **Zustand** | Lightweight, no boilerplate |
| HTTP | **Axios** + interceptors | Token injection, retry, error handling |
| WebSocket | **Socket.io-client** | ZIO chat, telemetry streaming |
| Storage | **expo-secure-store** | Tokens, credentials (encrypted) |
| UI Kit | **React Native Paper** (Material Design 3) | Dark theme, professional look |
| Charts | **react-native-chart-kit** | System stats, telemetry graphs |
| Icons | **@expo/vector-icons** (MaterialCommunityIcons) | Consistent icon set |
| Auth | **expo-local-authentication** | Biometric lock (fingerprint/face) |

---

## Project Structure

```
mobile/
├── app/                        # Expo Router pages
│   ├── _layout.tsx             # Root layout (auth gate)
│   ├── (auth)/
│   │   ├── login.tsx           # Login screen
│   │   └── register.tsx        # Register screen
│   ├── (tabs)/
│   │   ├── _layout.tsx         # Tab navigator
│   │   ├── dashboard.tsx       # Admin dashboard (home)
│   │   ├── chat.tsx            # ZIO AI chat
│   │   ├── missions.tsx        # Mission control
│   │   └── settings.tsx        # Settings / profile
│   ├── admin/
│   │   ├── users.tsx           # User management
│   │   ├── servers.tsx         # Server stats (.85 + .68)
│   │   └── logs.tsx            # System logs
│   ├── zivr/
│   │   ├── viewer.tsx          # ZiVR 3D viewer
│   │   └── assets.tsx          # Asset browser
│   └── +not-found.tsx
├── components/
│   ├── auth/
│   │   ├── AuthGate.tsx        # Token check + redirect
│   │   └── LoginForm.tsx
│   ├── dashboard/
│   │   ├── StatsCard.tsx       # CPU/RAM/Disk cards
│   │   ├── ServerStatus.tsx    # .85 + .68 status
│   │   └── QuickActions.tsx
│   ├── chat/
│   │   ├── MessageBubble.tsx   # Chat message
│   │   ├── ChatInput.tsx       # Text input + send
│   │   └── SessionList.tsx     # Chat history
│   ├── missions/
│   │   ├── MissionCard.tsx     # Mission summary card
│   │   └── TelemetryGauge.tsx  # Gauge component
│   └── shared/
│       ├── Header.tsx          # Custom header
│       ├── LoadingScreen.tsx   # Splash / loading
│       └── ErrorBoundary.tsx   # Error handler
├── lib/
│   ├── api.ts                  # Axios instance + interceptors
│   ├── ws.ts                   # WebSocket manager
│   ├── auth.ts                 # Token management (secure store)
│   └── config.ts               # API base URL config
├── stores/
│   ├── authStore.ts            # Auth state (token, user)
│   ├── chatStore.ts            # Chat messages, sessions
│   └── systemStore.ts          # System stats, servers
├── theme/
│   ├── colors.ts               # ZICORE color palette
│   ├── typography.ts           # Fonts, sizes
│   └── dark.ts                 # Dark aerospace theme
├── assets/
│   ├── icon.png                # App icon
│   ├── splash.png              # Splash screen
│   └── adaptive-icon.png       # Android adaptive icon
├── app.json                    # Expo config
├── eas.json                    # EAS Build config
├── package.json
└── tsconfig.json
```

---

## Screens & Features

### 1. Auth Screens (`(auth)/`)

**Login Screen**
- Email + password fields
- "Remember me" toggle (stores credentials securely)
- Biometric login (fingerprint/face) if previously enabled
- Link to register
- ZICORE logo + dark aerospace background

**Register Screen**
- Name, email prefix (@zinemotion.com.mx), password
- Password strength meter (matches web: 8+ chars, upper, lower, digit)
- Mandatory checkboxes: Aviso de Privacidad + Condiciones de Uso (opens web view)
- Link to login

### 2. Dashboard Tab (`dashboard.tsx`)

**System Overview Cards**
- CPU usage (animated gauge)
- RAM usage (animated gauge)
- Disk usage (animated gauge)
- Uptime counter

**Server Status**
- .85 Primary Server: status, services, health
- .68 Secondary Server: status, Ollama models
- VPS: status, services
- Green/red indicators

**Quick Actions**
- Restart services
- Clear cache
- View logs
- System info

**Recent Activity**
- Last logins
- Active users
- Recent missions

### 3. ZIO AI Chat Tab (`chat.tsx`)

**Chat Interface**
- Message bubbles (user = right/blue, ZIO = left/purple)
- Real-time streaming via WebSocket
- Typing indicator
- Session selector (dropdown)
- Copy message, export chat
- Provider indicator (which AI is responding)
- Daily message counter (plan-based)

**Features**
- Send text messages
- Voice input (expo-speech)
- Image analysis (camera roll)
- Knowledge base search
- Chat history (persisted)

### 4. Mission Control Tab (`missions.tsx`)

**Mission List**
- Cards with: name, phase (planning/active/complete), date
- Create new mission
- Tap to view details

**Mission Detail**
- Telemetry gauges (altitude, velocity, acceleration)
- Vehicle status
- Orbital parameters
- Timeline/events
- Phase transitions

**Telemetry View**
- Real-time graphs (altitude, velocity, fuel)
- G-force meter
- Orbital visualization (2D)

### 5. Settings Tab (`settings.tsx`)

**Profile**
- Display name, email, role
- Change password
- API keys management
- Active sessions

**Preferences**
- Server URL configuration
- Theme (dark mode always, accent color)
- Notifications toggle
- Biometric lock toggle
- Language (ES/EN)

**About**
- App version
- Server status
- Licenses
- Legal (Aviso de Privacidad, Condiciones de Uso)

### 6. Admin Screens (admin/)

**User Management** (`users.tsx`)
- List all users (search, filter)
- Tap user → edit role, services, status
- User stats (total, active, by plan)

**Server Monitor** (`servers.tsx`)
- Real-time CPU/RAM/Disk graphs
- Service status (green/red dots)
- Ollama models + status
- Network info
- Disk usage breakdown

**System Logs** (`logs.tsx`)
- Live log feed (WebSocket)
- Filter by level (info/warn/error)
- Search
- Export

### 7. ZiVR Screens (zivr/)

**3D Viewer** (`viewer.tsx`)
- WebView loading ZiVR engine (vps.zicore.space/zimaterializer)
- Touch controls for 3D navigation
- Screenshot capture
- Export to device

**Asset Browser** (`assets.tsx`)
- Grid view of generated 3D assets
- Filter by type (mesh, texture, HDRI)
- Download to device
- Share

---

## API Integration

### Base Configuration
```typescript
// lib/config.ts
const CONFIG = {
  // Default to VPS (primary)
  baseUrl: 'https://vps.zicore.space',
  wsUrl: 'wss://vps.zicore.space',
  
  // Fallback to .85
  fallbackUrl: 'http://192.168.1.85:4000',
  
  // Timeouts
  timeout: 15000,
  wsTimeout: 30000,
};
```

### Auth Flow
```typescript
// lib/auth.ts
import * as SecureStore from 'expo-secure-store';

const TOKEN_KEY = 'zicore_token';
const USER_KEY = 'zicore_user';

export const auth = {
  getToken: () => SecureStore.getItemAsync(TOKEN_KEY),
  setToken: (token: string) => SecureStore.setItemAsync(TOKEN_KEY, token),
  removeToken: () => SecureStore.deleteItemAsync(TOKEN_KEY),
  getUser: () => SecureStore.getItemAsync(USER_KEY).then(JSON.parse),
  setUser: (user: object) => SecureStore.setItemAsync(USER_KEY, JSON.stringify(user)),
};
```

### Axios Interceptor
```typescript
// lib/api.ts
import axios from 'axios';
import { auth } from './auth';

const api = axios.create({ baseURL: CONFIG.baseUrl });

api.interceptors.request.use(async (config) => {
  const token = await auth.getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      await auth.removeToken();
      // Redirect to login
    }
    return Promise.reject(error);
  }
);
```

---

## Key API Endpoints by Module

### Authentication
- `POST /api/sso/login` → `{status, token, expires_at, user}`
- `POST /api/sso/register` → `{status, token, user}`
- `GET /api/sso/me` → `{status, user}` (with plan info)
- `POST /api/sso/logout`
- `POST /api/sso/change-password`
- `GET /api/sso/sessions`
- `GET /api/sso/plans`

### Dashboard / System
- `GET /api/system/stats` → `{cpu_percent, memory_percent, disk_percent, uptime, ollama_status, ...}`
- `GET /api/status` → server version, active provider
- `GET /api/node/status` → .68 server status

### ZIO AI Chat
- `POST /api/chat` → `{status, response, intent}`
- `POST /api/provider/chat` → specific provider
- `WS /ws/zio` → real-time streaming

### Missions
- `GET /api/missions` → mission list
- `GET /api/missions/{id}` → mission detail
- `POST /api/missions/{id}` → create/update

### Telemetry
- `GET /api/telemetry` → current telemetry
- `WS /ws/telemetry` → live stream

### ZiVR
- `GET /api/zivr/config`
- `POST /api/zivr/generate` → generate 3D asset
- `GET /api/zivr/assets` → asset list

---

## Theme — Dark Aerospace Cockpit

```typescript
// theme/colors.ts
export const COLORS = {
  // Backgrounds
  background: '#04060c',
  surface: '#0d1117',
  card: '#111827',
  
  // Primary (Cyan)
  primary: '#00e5ff',
  primaryLight: 'rgba(0, 229, 255, 0.15)',
  
  // Accent (Purple)
  accent: '#7c4dff',
  accentLight: 'rgba(124, 77, 255, 0.15)',
  
  // Status
  success: '#00ff88',
  warning: '#ffa500',
  error: '#ff5555',
  
  // Text
  text: '#e0e0e0',
  textSecondary: '#607080',
  textMuted: '#3a4050',
  
  // Borders
  border: '#1a2332',
  borderLight: '#2a3342',
};
```

---

## Build & Distribution

### EAS Build (for APK)
```json
// eas.json
{
  "build": {
    "preview": {
      "distribution": "internal",
      "android": {
        "buildType": "apk"
      }
    },
    "production": {
      "android": {
        "buildType": "apk"
      }
    }
  }
}
```

### Build Commands
```bash
# Install dependencies
cd mobile && npm install

# Build APK locally (requires Android SDK)
npx expo run:android --variant release

# Build with EAS (cloud)
eas build -p android --profile preview
```

### Distribution
1. Build APK → `zicore-mobile.apk`
2. Upload to VPS: `scp zicore-mobile.apk oracle-admin@160.34.209.208:/opt/zicore-system/installers/`
3. Serve from: `GET /download/mobile-apk`
4. Update download page at `/installers`

---

## Implementation Phases

### Phase 1: Foundation (Sessions 1-2)
- [ ] Initialize Expo project
- [ ] Set up navigation (Expo Router)
- [ ] Create theme + design system
- [ ] Auth screens (login, register)
- [ ] API layer (Axios + token management)
- [ ] Secure storage for credentials

### Phase 2: Core Features (Sessions 3-4)
- [ ] Dashboard (system stats, server status)
- [ ] ZIO AI Chat (basic messaging)
- [ ] Settings (profile, server config)

### Phase 3: Advanced Features (Sessions 5-6)
- [ ] Mission Control (missions list, telemetry)
- [ ] Admin screens (user management, server monitor)
- [ ] WebSocket integration (real-time telemetry, chat streaming)

### Phase 4: Polish & Deploy (Sessions 7-8)
- [ ] ZiVR viewer (WebView integration)
- [ ] Biometric authentication
- [ ] Push notifications
- [ ] APK build + distribution
- [ ] OTA update configuration

---

## Dependencies (package.json)

```json
{
  "dependencies": {
    "expo": "~52.0.0",
    "expo-router": "~4.0.0",
    "expo-secure-store": "~14.0.0",
    "expo-local-authentication": "~15.0.0",
    "expo-web-browser": "~14.0.0",
    "expo-status-bar": "~2.0.0",
    "expo-splash-screen": "~0.29.0",
    "expo-linking": "~7.0.0",
    "expo-constants": "~17.0.0",
    "react": "18.3.1",
    "react-native": "0.76.3",
    "react-native-paper": "^5.12.0",
    "react-native-safe-area-context": "4.12.0",
    "react-native-screens": "~4.1.0",
    "react-native-chart-kit": "^6.12.0",
    "react-native-svg": "15.8.0",
    "react-native-gesture-handler": "~2.20.0",
    "react-native-reanimated": "~3.16.0",
    "@expo/vector-icons": "^14.0.0",
    "axios": "^1.7.0",
    "socket.io-client": "^4.7.0",
    "zustand": "^5.0.0"
  }
}
```

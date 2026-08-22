import * as Device from 'expo-device';
import { geoAPI } from './api';

export interface GeoPoint {
  lat: number;
  lon: number;
  accuracy?: number | null;
  altitude?: number | null;
  speed?: number | null;
  heading?: number | null;
}

export interface Bookmark {
  id: number;
  user_id: number;
  name: string;
  lat: number;
  lon: number;
  altitude?: number | null;
  icon: string;
  color: string;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TrackingSession {
  id: number;
  user_id: number;
  started_at: string;
  stopped_at?: string | null;
  interval_s: number;
  points: number;
  status: string;
}

let cachedDeviceId: string | null = null;

function getDeviceId(): string {
  if (cachedDeviceId) return cachedDeviceId;
  const brand = (Device as any)?.brand || 'unknown';
  const model = (Device as any)?.modelName || 'device';
  cachedDeviceId = `${brand}-${model}`;
  return cachedDeviceId;
}

export async function getCurrentPosition(): Promise<GeoPoint> {
  const mod = (await import('expo-location')) as typeof import('expo-location');
  const { status } = await mod.requestForegroundPermissionsAsync();
  if (status !== 'granted') {
    throw new Error('Permiso de ubicación denegado');
  }
  const pos = await mod.getCurrentPositionAsync({ accuracy: mod.Accuracy.Balanced });
  return {
    lat: pos.coords.latitude,
    lon: pos.coords.longitude,
    accuracy: pos.coords.accuracy,
    altitude: pos.coords.altitude,
    speed: pos.coords.speed,
    heading: pos.coords.heading,
  };
}

export async function shareMyLocation(): Promise<any> {
  const point = await getCurrentPosition();
  const res = await geoAPI.report({
    lat: point.lat,
    lon: point.lon,
    accuracy: point.accuracy,
    altitude: point.altitude,
    speed: point.speed,
    heading: point.heading,
    source: 'gps',
    app: 'mobile',
    device_id: getDeviceId(),
  });
  return res.data;
}

// ── Background Location Service ────────────────────────────────────────────

const BACKGROUND_TASK_NAME = 'GEO_BACKGROUND_TRACKING';
let bgTaskRegistered = false;

async function ensureTaskRegistered() {
  if (bgTaskRegistered) return;
  try {
    const TaskManager = await import('expo-task-manager');
    const Location = await import('expo-location');

    if (!TaskManager.isTaskRegistered(BACKGROUND_TASK_NAME)) {
      await TaskManager.defineTask(BACKGROUND_TASK_NAME, async ({ data, error }: any) => {
        if (error) return;
        const locations = data?.locations;
        if (!locations || locations.length === 0) return;
        const loc = locations[0];
        if (!loc?.coords) return;
        try {
          await geoAPI.report({
            lat: loc.coords.latitude,
            lon: loc.coords.longitude,
            accuracy: loc.coords.accuracy,
            altitude: loc.coords.altitude,
            speed: loc.coords.speed,
            heading: loc.coords.heading,
            source: 'gps',
            app: 'mobile-bg',
            device_id: getDeviceId(),
          });
        } catch { }
      });
    }
    bgTaskRegistered = true;
  } catch { }
}

let bgTrackingActive = false;

export async function startBackgroundTracking(intervalS = 60): Promise<boolean> {
  const Location = await import('expo-location');
  const { status: foregroundStatus } = await Location.requestForegroundPermissionsAsync();
  if (foregroundStatus !== 'granted') throw new Error('Permiso de ubicación denegado');

  await ensureTaskRegistered();

  const { status: bgStatus } = await Location.requestBackgroundPermissionsAsync();
  if (bgStatus !== 'granted') {
    throw new Error('Permiso de ubicación en segundo plano denegado. Actívalo en Configuración.');
  }

  const isRunning = await Location.hasStartedLocationUpdatesAsync(BACKGROUND_TASK_NAME).catch(() => false);
  if (isRunning) {
    bgTrackingActive = true;
    return true;
  }

  await Location.startLocationUpdatesAsync(BACKGROUND_TASK_NAME, {
    accuracy: Location.Accuracy.Balanced,
    distanceInterval: 10,
    deferredUpdatesInterval: intervalS * 1000,
    showsBackgroundLocationIndicator: true,
    foregroundService: {
      notificationTitle: 'ZICORE GeoTrack',
      notificationBody: `Reportando ubicación cada ${intervalS}s`,
      notificationColor: '#00e5ff',
    },
  });

  bgTrackingActive = true;
  return true;
}

export async function stopBackgroundTracking(): Promise<void> {
  const Location = await import('expo-location');
  const isRunning = await Location.hasStartedLocationUpdatesAsync(BACKGROUND_TASK_NAME).catch(() => false);
  if (isRunning) {
    await Location.stopLocationUpdatesAsync(BACKGROUND_TASK_NAME);
  }
  bgTrackingActive = false;
}

export async function isBackgroundTrackingActive(): Promise<boolean> {
  try {
    const Location = await import('expo-location');
    const running = await Location.hasStartedLocationUpdatesAsync(BACKGROUND_TASK_NAME).catch(() => false);
    bgTrackingActive = running;
    return running;
  } catch {
    return false;
  }
}

// ── Foreground Watch (when app is open) ────────────────────────────────────

let activeWatchHandle: { stop: () => void } | null = null;
let activeTrackingSession: TrackingSession | null = null;

export function startLocationWatch(
  onUpdate?: (point: GeoPoint) => void,
  intervalMs = 60000
): { stop: () => void } {
  if (activeWatchHandle) {
    activeWatchHandle.stop();
    activeWatchHandle = null;
  }

  let stopped = false;
  let timer: ReturnType<typeof setTimeout> | null = null;

  async function tick() {
    if (stopped) return;
    try {
      const point = await getCurrentPosition();
      onUpdate?.(point);
      geoAPI.report({
        lat: point.lat,
        lon: point.lon,
        accuracy: point.accuracy,
        altitude: point.altitude,
        speed: point.speed,
        heading: point.heading,
        source: 'gps',
        app: 'mobile',
        device_id: getDeviceId(),
      }).catch(() => {});
      if (activeTrackingSession) {
        geoAPI.activeTracking().catch(() => {});
      }
    } catch { }
  }

  timer = setInterval(tick, intervalMs);
  tick();

  activeWatchHandle = {
    stop: () => {
      stopped = true;
      if (timer) clearInterval(timer);
      activeWatchHandle = null;
    },
  };
  return activeWatchHandle;
}

export function stopLocationWatch(): void {
  if (activeWatchHandle) {
    activeWatchHandle.stop();
    activeWatchHandle = null;
  }
}

export function isTrackingActive(): boolean {
  return activeWatchHandle !== null;
}

// ── Bookmarks ───────────────────────────────────────────────────────────────

export async function fetchBookmarks(): Promise<Bookmark[]> {
  const res = await geoAPI.bookmarks();
  return res.data?.bookmarks || [];
}

export async function createBookmark(
  name: string,
  lat: number,
  lon: number,
  opts?: { altitude?: number; icon?: string; color?: string; notes?: string }
): Promise<Bookmark | null> {
  const res = await geoAPI.createBookmark({
    name,
    lat,
    lon,
    altitude: opts?.altitude,
    icon: opts?.icon || '📍',
    color: opts?.color || '#00e5ff',
    notes: opts?.notes,
  });
  return res.data?.bookmark || null;
}

export async function deleteBookmark(id: number): Promise<boolean> {
  const res = await geoAPI.deleteBookmark(id);
  return res.data?.deleted === true;
}

// ── Tracking Sessions ───────────────────────────────────────────────────────

export async function startTrackingSession(intervalS = 60): Promise<TrackingSession | null> {
  const res = await geoAPI.startTracking(intervalS);
  activeTrackingSession = res.data?.session || null;
  return activeTrackingSession;
}

export async function stopTrackingSession(): Promise<TrackingSession | null> {
  stopLocationWatch();
  await stopBackgroundTracking().catch(() => {});
  const res = await geoAPI.stopTracking();
  activeTrackingSession = null;
  return res.data?.session || null;
}

export async function getActiveTracking(): Promise<TrackingSession | null> {
  const res = await geoAPI.activeTracking();
  activeTrackingSession = res.data?.session || null;
  return activeTrackingSession;
}

export async function getTrackingHistory(limit = 20): Promise<TrackingSession[]> {
  const res = await geoAPI.trackingHistory(limit);
  return res.data?.sessions || [];
}

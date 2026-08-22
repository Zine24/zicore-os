import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, Alert,
  ActivityIndicator, TextInput, Modal, Platform, Switch,
} from 'react-native';
import { WebView } from 'react-native-webview';
import { Ionicons } from '@expo/vector-icons';
import { COLORS, SPACING, RADIUS } from '@/theme/colors';
import {
  getCurrentPosition, shareMyLocation, GeoPoint, Bookmark,
  fetchBookmarks, createBookmark, deleteBookmark,
  startTrackingSession, stopTrackingSession, getActiveTracking,
  getTrackingHistory, startLocationWatch, stopLocationWatch,
  startBackgroundTracking, stopBackgroundTracking, isBackgroundTrackingActive,
  TrackingSession,
} from '@/lib/geo';
import { geoAPI } from '@/lib/api';

type Tab = 'map' | 'bookmarks' | 'tracking';

function haversineDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371000;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) *
    Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function generateMapHTML(centerLat: number, centerLon: number, markers: any[], trail: any[]): string {
  const markersJS = markers.map(m =>
    `L.marker([${m.lat}, ${m.lon}], {icon: L.divIcon({className:'custom-marker',html:'<div style="background:${m.color};width:${m.size||14}px;height:${m.size||14}px;border-radius:50%;border:2px solid #fff;box-shadow:0 0 8px ${m.color}${m.pulse?';animation:pulse 2s infinite':''}"></div>${m.pulse?'<style>@keyframes pulse{0%,100%{box-shadow:0 0 4px '+m.color+'}50%{box-shadow:0 0 16px '+m.color+'}}</style>':''}',iconSize:[m.size||14,m.size||14],iconAnchor:[(m.size||14)/2,(m.size||14)/2]})}).addTo(map).bindPopup('${m.label.replace(/'/g, "\\'")}');`
  ).join('\n');

  const trailCoords = trail.map(p => `[${p.lat}, ${p.lon}]`).join(',');
  const trailLine = trail.length > 1
    ? `L.polyline([${trailCoords}], {color:'#00e5ff',weight:3,opacity:0.7,dashArray:'8,6'}).addTo(map);`
    : '';

  return `<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body{margin:0;padding:0;background:#04060c}
  #map{width:100%;height:100vh;background:#04060c}
  .leaflet-control-zoom{border:none !important}
  .leaflet-control-zoom a{background:#0d1117 !important;color:#00e5ff !important;border:1px solid #1a2332 !important}
  .leaflet-popup-content-wrapper{background:#0d1117;color:#e0e0e0;border:1px solid #1a2332;border-radius:8px}
  .leaflet-popup-tip{background:#0d1117}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:0.6}}
</style>
</head>
<body>
<div id="map"></div>
<script>
var map = L.map('map',{zoomControl:true}).setView([${centerLat},${centerLon}],16);
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{
  attribution:'&copy; OpenStreetMap',maxZoom:19
}).addTo(map);
${markersJS}
${trailLine}
map.invalidateSize();
</script>
</body>
</html>`;
}

export default function GeoScreen() {
  const [tab, setTab] = useState<Tab>('map');
  const [point, setPoint] = useState<GeoPoint | null>(null);
  const [loading, setLoading] = useState(true);
  const [bookmarks, setBookmarks] = useState<Bookmark[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [tracking, setTracking] = useState<TrackingSession | null>(null);
  const [trackingActive, setTrackingActive] = useState(false);
  const [bgTrackingActive, setBgTrackingActive] = useState(false);
  const [trackingInterval, setTrackingInterval] = useState('60');
  const [trackingHistory, setTrackingHistory] = useState<TrackingSession[]>([]);
  const [showBookmarkModal, setShowBookmarkModal] = useState(false);
  const [bmName, setBmName] = useState('');
  const [bmNotes, setBmNotes] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const [totalDistance, setTotalDistance] = useState(0);
  const [pointCount, setPointCount] = useState(0);
  const webViewRef = useRef<WebView>(null);
  const lastPointRef = useRef<GeoPoint | null>(null);

  const loadAll = useCallback(async () => {
    try {
      const pos = await getCurrentPosition();
      setPoint(pos);
      if (lastPointRef.current) {
        const dist = haversineDistance(lastPointRef.current.lat, lastPointRef.current.lon, pos.lat, pos.lon);
        if (dist > 2 && dist < 10000) {
          setTotalDistance(d => d + dist);
          setPointCount(c => c + 1);
        }
      }
      lastPointRef.current = pos;
    } catch { }

    try {
      const bms = await fetchBookmarks();
      setBookmarks(bms);
    } catch { }

    try {
      const hRes = await geoAPI.history(50);
      setHistory(hRes.data?.history || []);
    } catch { }

    try {
      const at = await getActiveTracking();
      setTracking(at);
      setTrackingActive(!!at);
    } catch { }

    try {
      const bgActive = await isBackgroundTrackingActive();
      setBgTrackingActive(bgActive);
    } catch { }

    try {
      const th = await getTrackingHistory();
      setTrackingHistory(th);
    } catch { }

    setLoading(false);
  }, []);

  useEffect(() => { loadAll(); }, []);

  useEffect(() => {
    const interval = setInterval(loadAll, 15000);
    return () => clearInterval(interval);
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadAll();
    setRefreshing(false);
  }, []);

  const handleRefreshLocation = async () => {
    try {
      const pos = await getCurrentPosition();
      setPoint(pos);
      await shareMyLocation();
    } catch (e: any) {
      Alert.alert('Error', e?.message || 'No se pudo obtener ubicación');
    }
  };

  const handleAddBookmark = async () => {
    if (!point) {
      Alert.alert('Error', 'No hay posición disponible');
      return;
    }
    if (!bmName.trim()) {
      Alert.alert('Error', 'Escribe un nombre para el marcador');
      return;
    }
    try {
      await createBookmark(bmName.trim(), point.lat, point.lon, { notes: bmNotes || undefined });
      setShowBookmarkModal(false);
      setBmName('');
      setBmNotes('');
      await loadAll();
    } catch (e: any) {
      Alert.alert('Error', e?.message || 'No se pudo crear el marcador');
    }
  };

  const handleDeleteBookmark = (bm: Bookmark) => {
    Alert.alert('Eliminar marcador', `¿Eliminar "${bm.name}"?`, [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Eliminar', style: 'destructive',
        onPress: async () => {
          try {
            await deleteBookmark(bm.id);
            await loadAll();
          } catch { }
        },
      },
    ]);
  };

  const handleStartTracking = async () => {
    const interval = parseInt(trackingInterval) || 60;
    try {
      const session = await startTrackingSession(interval);
      if (session) {
        setTrackingActive(true);
        setTracking(session);

        try {
          await startBackgroundTracking(interval);
          setBgTrackingActive(true);
        } catch (bgErr: any) {
          console.log('BG tracking unavailable, using foreground only:', bgErr?.message);
        }

        startLocationWatch((p) => {
          setPoint(p);
        }, interval * 1000);
        Alert.alert('Tracking activo', `Reportando cada ${interval}s${bgTrackingActive ? ' (segundo plano)' : ''}`);
      }
    } catch (e: any) {
      Alert.alert('Error', e?.message || 'No se pudo iniciar tracking');
    }
  };

  const handleStopTracking = async () => {
    try {
      await stopLocationWatch();
      await stopBackgroundTracking();
      await stopTrackingSession();
      setTrackingActive(false);
      setBgTrackingActive(false);
      setTracking(null);
      await loadAll();
      Alert.alert('Tracking detenido');
    } catch (e: any) {
      Alert.alert('Error', e?.message || 'No se pudo detener');
    }
  };

  const toggleBgTracking = async () => {
    if (bgTrackingActive) {
      await stopBackgroundTracking();
      setBgTrackingActive(false);
    } else {
      try {
        const interval = parseInt(trackingInterval) || 60;
        await startBackgroundTracking(interval);
        setBgTrackingActive(true);
        Alert.alert('Background activo', 'Tu ubicación se reportará incluso con la app en segundo plano');
      } catch (e: any) {
        Alert.alert('Permiso requerido', e?.message || 'Activa el permiso de ubicación en segundo plano');
      }
    }
  };

  const mapMarkers: any[] = [];
  if (point) {
    mapMarkers.push({
      lat: point.lat, lon: point.lon, color: '#00e5ff',
      label: 'Mi posición actual', size: 16, pulse: trackingActive,
    });
  }
  bookmarks.forEach(bm => {
    mapMarkers.push({ lat: bm.lat, lon: bm.lon, color: bm.color || '#7c4dff', label: `${bm.icon} ${bm.name}` });
  });

  const trailPoints = history
    .filter((h: any) => h.lat && h.lon)
    .reverse()
    .map((h: any) => ({ lat: h.lat, lon: h.lon }));

  const mapCenter = point || { lat: 19.43, lon: -99.13 };

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <Ionicons name="location" size={16} color={COLORS.primary} />
          <Text style={styles.headerTitle}>GEOTRACK</Text>
          {trackingActive && <View style={styles.liveDot} />}
        </View>
        <View style={styles.headerRight}>
          {trackingActive && (
            <View style={styles.distanceBadge}>
              <Ionicons name="walk" size={12} color={COLORS.primary} />
              <Text style={styles.distanceText}>{(totalDistance / 1000).toFixed(2)} km</Text>
            </View>
          )}
          <TouchableOpacity onPress={onRefreshLocation} style={styles.refreshBtn}>
            <Ionicons name="refresh" size={16} color={COLORS.primary} />
          </TouchableOpacity>
        </View>
      </View>

      <View style={styles.tabBar}>
        {(['map', 'bookmarks', 'tracking'] as Tab[]).map(t => (
          <TouchableOpacity
            key={t}
            style={[styles.subTab, tab === t && styles.subTabActive]}
            onPress={() => setTab(t)}
          >
            <Ionicons
              name={t === 'map' ? 'map-outline' : t === 'bookmarks' ? 'bookmark-outline' : 'pulse-outline'}
              size={14}
              color={tab === t ? COLORS.primary : COLORS.textMuted}
            />
            <Text style={[styles.subTabText, tab === t && styles.subTabTextActive]}>
              {t === 'map' ? 'MAPA' : t === 'bookmarks' ? 'MARCAS' : 'TRACKING'}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {tab === 'map' && (
        <View style={styles.mapContainer}>
          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color={COLORS.primary} />
              <Text style={styles.loadingText}>Obteniendo posición...</Text>
            </View>
          ) : (
            <WebView
              ref={webViewRef}
              source={{ html: generateMapHTML(mapCenter.lat, mapCenter.lon, mapMarkers, trailPoints) }}
              style={styles.webview}
              javaScriptEnabled
              domStorageEnabled
            />
          )}

          {point && (
            <View style={styles.locationCard}>
              <View style={styles.locRow}>
                <Text style={styles.locLabel}>LAT</Text>
                <Text style={styles.locValue}>{point.lat.toFixed(6)}</Text>
              </View>
              <View style={styles.locRow}>
                <Text style={styles.locLabel}>LON</Text>
                <Text style={styles.locValue}>{point.lon.toFixed(6)}</Text>
              </View>
              {point.altitude != null && (
                <View style={styles.locRow}>
                  <Text style={styles.locLabel}>ALT</Text>
                  <Text style={styles.locValue}>{Math.round(point.altitude)}m</Text>
                </View>
              )}
              {point.speed != null && point.speed > 0 && (
                <View style={styles.locRow}>
                  <Text style={styles.locLabel}>SPD</Text>
                  <Text style={styles.locValue}>{(point.speed * 3.6).toFixed(1)} km/h</Text>
                </View>
              )}
              {point.accuracy != null && (
                <View style={styles.locRow}>
                  <Text style={styles.locLabel}>GPS</Text>
                  <Text style={styles.locValue}>±{Math.round(point.accuracy)}m</Text>
                </View>
              )}
              <View style={styles.locActions}>
                <TouchableOpacity style={styles.locActionBtn} onPress={handleRefreshLocation}>
                  <Ionicons name="navigate" size={14} color={COLORS.primary} />
                  <Text style={styles.locActionText}>Actualizar</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.locActionBtn} onPress={() => setShowBookmarkModal(true)}>
                  <Ionicons name="bookmark" size={14} color={COLORS.accent} />
                  <Text style={[styles.locActionText, { color: COLORS.accent }]}>Marcar</Text>
                </TouchableOpacity>
                {trackingActive && (
                  <TouchableOpacity
                    style={styles.locActionBtn}
                    onPress={() => { setTotalDistance(0); setPointCount(0); }}
                  >
                    <Ionicons name="refresh-circle" size={14} color={COLORS.textMuted} />
                    <Text style={[styles.locActionText, { color: COLORS.textMuted }]}>Reset km</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          )}
        </View>
      )}

      {tab === 'bookmarks' && (
        <ScrollView style={styles.scrollContent} contentContainerStyle={styles.scrollContentInner}>
          <TouchableOpacity style={styles.addBtn} onPress={() => setShowBookmarkModal(true)}>
            <Ionicons name="add-circle" size={18} color={COLORS.primary} />
            <Text style={styles.addBtnText}>AGREGAR MARCADOR AQUÍ</Text>
          </TouchableOpacity>

          {bookmarks.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="bookmark-outline" size={48} color={COLORS.textMuted} />
              <Text style={styles.emptyText}>Sin marcadores</Text>
              <Text style={styles.emptySubtext}>Guarda ubicaciones importantes para acceso rápido</Text>
            </View>
          ) : (
            bookmarks.map(bm => (
              <TouchableOpacity key={bm.id} style={styles.bookmarkCard} onLongPress={() => handleDeleteBookmark(bm)}>
                <View style={[styles.bmIcon, { backgroundColor: bm.color + '30', borderColor: bm.color }]}>
                  <Text style={styles.bmIconText}>{bm.icon}</Text>
                </View>
                <View style={styles.bmInfo}>
                  <Text style={styles.bmName}>{bm.name}</Text>
                  <Text style={styles.bmCoords}>{bm.lat.toFixed(5)}, {bm.lon.toFixed(5)}</Text>
                  {bm.notes && <Text style={styles.bmNotes}>{bm.notes}</Text>}
                </View>
                <TouchableOpacity onPress={() => handleDeleteBookmark(bm)} style={styles.bmDelete}>
                  <Ionicons name="trash-outline" size={14} color={COLORS.error} />
                </TouchableOpacity>
              </TouchableOpacity>
            ))
          )}
        </ScrollView>
      )}

      {tab === 'tracking' && (
        <ScrollView style={styles.scrollContent} contentContainerStyle={styles.scrollContentInner}>
          <View style={styles.trackingCard}>
            <View style={styles.trackingHeader}>
              <Ionicons name={trackingActive ? 'radio' : 'radio-outline'} size={20} color={trackingActive ? COLORS.success : COLORS.textMuted} />
              <Text style={styles.trackingTitle}>{trackingActive ? 'TRACKING ACTIVO' : 'SIN TRACKING'}</Text>
            </View>

            {trackingActive && tracking && (
              <View style={styles.trackingStats}>
                <View style={styles.tsRow}>
                  <Text style={styles.tsLabel}>Iniciado</Text>
                  <Text style={styles.tsValue}>{new Date(tracking.started_at).toLocaleTimeString()}</Text>
                </View>
                <View style={styles.tsRow}>
                  <Text style={styles.tsLabel}>Intervalo</Text>
                  <Text style={styles.tsValue}>{tracking.interval_s}s</Text>
                </View>
                <View style={styles.tsRow}>
                  <Text style={styles.tsLabel}>Puntos reportados</Text>
                  <Text style={styles.tsValue}>{pointCount}</Text>
                </View>
                <View style={styles.tsRow}>
                  <Text style={styles.tsLabel}>Distancia recorrida</Text>
                  <Text style={styles.tsValue}>{(totalDistance / 1000).toFixed(2)} km</Text>
                </View>
              </View>
            )}

            {trackingActive && (
              <View style={styles.bgRow}>
                <View style={styles.bgInfo}>
                  <Ionicons name={bgTrackingActive ? 'phone-portrait' : 'phone-portrait-outline'} size={16} color={bgTrackingActive ? COLORS.success : COLORS.textMuted} />
                  <View>
                    <Text style={styles.bgLabel}>Segundo Plano</Text>
                    <Text style={styles.bgSub}>{bgTrackingActive ? 'Activo — GPS persistente' : 'Inactivo'}</Text>
                  </View>
                </View>
                <Switch
                  value={bgTrackingActive}
                  onValueChange={toggleBgTracking}
                  trackColor={{ false: '#1a2332', true: COLORS.success + '40' }}
                  thumbColor={bgTrackingActive ? COLORS.success : COLORS.textMuted}
                />
              </View>
            )}

            <View style={styles.trackingControls}>
              {!trackingActive ? (
                <>
                  <Text style={styles.intervalLabel}>INTERVALO DE REPORTE</Text>
                  <View style={styles.intervalPresets}>
                    {['15', '30', '60', '120', '300'].map(v => (
                      <TouchableOpacity
                        key={v}
                        style={[styles.presetBtn, trackingInterval === v && styles.presetBtnActive]}
                        onPress={() => setTrackingInterval(v)}
                      >
                        <Text style={[styles.presetText, trackingInterval === v && styles.presetTextActive]}>
                          {parseInt(v) < 60 ? `${v}s` : `${parseInt(v) / 60}m`}
                        </Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                  <TextInput
                    style={styles.intervalInput}
                    value={trackingInterval}
                    onChangeText={setTrackingInterval}
                    keyboardType="number-pad"
                    placeholder="60"
                    placeholderTextColor={COLORS.textMuted}
                  />
                  <TouchableOpacity style={styles.startBtn} onPress={handleStartTracking}>
                    <Ionicons name="play" size={16} color="#000" />
                    <Text style={styles.startBtnText}>INICIAR TRACKING</Text>
                  </TouchableOpacity>
                </>
              ) : (
                <TouchableOpacity style={styles.stopBtn} onPress={handleStopTracking}>
                  <Ionicons name="stop" size={16} color="#fff" />
                  <Text style={styles.stopBtnText}>DETENER TRACKING</Text>
                </TouchableOpacity>
              )}
            </View>
          </View>

          <Text style={styles.sectionTitle}>HISTORIAL DE SESIONES</Text>
          {trackingHistory.length === 0 ? (
            <View style={styles.emptyState}>
              <Ionicons name="time-outline" size={36} color={COLORS.textMuted} />
              <Text style={styles.emptyText}>Sin sesiones previas</Text>
            </View>
          ) : (
            trackingHistory.map(s => (
              <View key={s.id} style={styles.historyCard}>
                <View style={styles.hcHeader}>
                  <Ionicons
                    name={s.status === 'active' ? 'radio' : 'checkmark-circle-outline'}
                    size={14}
                    color={s.status === 'active' ? COLORS.success : COLORS.textSecondary}
                  />
                  <Text style={styles.hcStatus}>{s.status === 'active' ? 'ACTIVA' : 'DETENIDA'}</Text>
                  <Text style={styles.hcDate}>{new Date(s.started_at).toLocaleDateString()}</Text>
                </View>
                <View style={styles.hcStats}>
                  <Text style={styles.hcStat}>{s.interval_s}s</Text>
                  <Text style={styles.hcStat}>{s.points} pts</Text>
                  {s.stopped_at && (
                    <Text style={styles.hcStat}>
                      {Math.round((new Date(s.stopped_at).getTime() - new Date(s.started_at).getTime()) / 60000)} min
                    </Text>
                  )}
                </View>
              </View>
            ))
          )}
        </ScrollView>
      )}

      <Modal visible={showBookmarkModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>NUEVO MARCADOR</Text>
            {point && (
              <Text style={styles.modalCoords}>{point.lat.toFixed(6)}, {point.lon.toFixed(6)}</Text>
            )}
            <TextInput
              style={styles.modalInput}
              value={bmName}
              onChangeText={setBmName}
              placeholder="Nombre del lugar"
              placeholderTextColor={COLORS.textMuted}
              autoFocus
            />
            <TextInput
              style={[styles.modalInput, { height: 60 }]}
              value={bmNotes}
              onChangeText={setBmNotes}
              placeholder="Notas (opcional)"
              placeholderTextColor={COLORS.textMuted}
              multiline
            />
            <View style={styles.modalActions}>
              <TouchableOpacity style={styles.modalCancel} onPress={() => { setShowBookmarkModal(false); setBmName(''); setBmNotes(''); }}>
                <Text style={styles.modalCancelText}>CANCELAR</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.modalSave} onPress={handleAddBookmark}>
                <Text style={styles.modalSaveText}>GUARDAR</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: SPACING.md, paddingTop: SPACING.sm, paddingBottom: SPACING.xs,
    borderBottomWidth: 1, borderBottomColor: COLORS.border,
  },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  headerRight: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  headerTitle: { fontSize: 13, fontWeight: '700', color: COLORS.primary, letterSpacing: 2 },
  liveDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: COLORS.success, marginLeft: 4 },
  refreshBtn: { padding: 6 },
  distanceBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: COLORS.primary + '15', borderRadius: RADIUS.sm,
    paddingHorizontal: 8, paddingVertical: 3,
  },
  distanceText: { fontSize: 11, color: COLORS.primary, fontFamily: 'monospace', fontWeight: '600' },

  tabBar: {
    flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: COLORS.border,
  },
  subTab: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, paddingVertical: 10, borderBottomWidth: 2, borderBottomColor: 'transparent',
  },
  subTabActive: { borderBottomColor: COLORS.primary },
  subTabText: { fontSize: 10, fontWeight: '600', color: COLORS.textMuted, letterSpacing: 1 },
  subTabTextActive: { color: COLORS.primary },

  mapContainer: { flex: 1, position: 'relative' },
  webview: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { color: COLORS.textMuted, fontSize: 12, marginTop: 12 },

  locationCard: {
    position: 'absolute', bottom: 12, left: 12, right: 12,
    backgroundColor: 'rgba(13,17,23,0.95)', borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.md, padding: 12,
  },
  locRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 3 },
  locLabel: { fontSize: 10, fontWeight: '600', color: COLORS.textMuted, letterSpacing: 1 },
  locValue: { fontSize: 12, color: COLORS.text, fontFamily: 'monospace' },
  locActions: { flexDirection: 'row', gap: 16, marginTop: 8, borderTopWidth: 1, borderTopColor: COLORS.border, paddingTop: 8 },
  locActionBtn: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  locActionText: { fontSize: 11, color: COLORS.primary, fontWeight: '600' },

  scrollContent: { flex: 1 },
  scrollContentInner: { padding: SPACING.md, paddingBottom: 100 },

  addBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    padding: 12, borderRadius: RADIUS.sm, borderWidth: 1, borderColor: COLORS.primary,
    borderStyle: 'dashed', marginBottom: SPACING.md,
  },
  addBtnText: { fontSize: 11, fontWeight: '700', color: COLORS.primary, letterSpacing: 1 },

  emptyState: { alignItems: 'center', paddingVertical: 40 },
  emptyText: { fontSize: 14, color: COLORS.textSecondary, marginTop: 12 },
  emptySubtext: { fontSize: 11, color: COLORS.textMuted, marginTop: 4, textAlign: 'center' },

  bookmarkCard: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.md, padding: 12, marginBottom: 8,
  },
  bmIcon: { width: 36, height: 36, borderRadius: 18, borderWidth: 1, justifyContent: 'center', alignItems: 'center' },
  bmIconText: { fontSize: 16 },
  bmInfo: { flex: 1 },
  bmName: { fontSize: 13, fontWeight: '600', color: COLORS.text },
  bmCoords: { fontSize: 10, color: COLORS.textSecondary, fontFamily: 'monospace', marginTop: 2 },
  bmNotes: { fontSize: 10, color: COLORS.textMuted, marginTop: 2 },
  bmDelete: { padding: 6 },

  trackingCard: {
    backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.md, padding: 16, marginBottom: SPACING.md,
  },
  trackingHeader: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 12 },
  trackingTitle: { fontSize: 13, fontWeight: '700', color: COLORS.text, letterSpacing: 1 },
  trackingStats: { marginBottom: 12 },
  tsRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  tsLabel: { fontSize: 11, color: COLORS.textMuted },
  tsValue: { fontSize: 11, color: COLORS.text, fontFamily: 'monospace' },

  bgRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    backgroundColor: COLORS.background, borderRadius: RADIUS.sm,
    padding: 12, marginBottom: 12, borderWidth: 1, borderColor: COLORS.border,
  },
  bgInfo: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  bgLabel: { fontSize: 12, fontWeight: '600', color: COLORS.text },
  bgSub: { fontSize: 10, color: COLORS.textMuted },

  trackingControls: {},
  intervalLabel: { fontSize: 10, color: COLORS.textMuted, letterSpacing: 1, marginBottom: 6 },
  intervalPresets: { flexDirection: 'row', gap: 6, marginBottom: 10 },
  presetBtn: {
    flex: 1, padding: 8, borderRadius: RADIUS.sm, borderWidth: 1, borderColor: COLORS.border,
    alignItems: 'center',
  },
  presetBtnActive: { borderColor: COLORS.primary, backgroundColor: COLORS.primary + '15' },
  presetText: { fontSize: 11, color: COLORS.textMuted, fontWeight: '600' },
  presetTextActive: { color: COLORS.primary },
  intervalInput: {
    backgroundColor: COLORS.background, borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.sm, padding: 10, color: COLORS.text, fontSize: 14,
    fontFamily: 'monospace', marginBottom: 12,
  },
  startBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    padding: 12, borderRadius: RADIUS.sm, backgroundColor: COLORS.success,
  },
  startBtnText: { fontSize: 12, fontWeight: '700', color: '#000', letterSpacing: 1 },
  stopBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    padding: 12, borderRadius: RADIUS.sm, backgroundColor: COLORS.error,
  },
  stopBtnText: { fontSize: 12, fontWeight: '700', color: '#fff', letterSpacing: 1 },

  sectionTitle: { fontSize: 10, fontWeight: '600', letterSpacing: 2, color: COLORS.textMuted, marginBottom: 8 },

  historyCard: {
    backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.sm, padding: 12, marginBottom: 8,
  },
  hcHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  hcStatus: { fontSize: 10, fontWeight: '700', color: COLORS.text, letterSpacing: 1, flex: 1 },
  hcDate: { fontSize: 10, color: COLORS.textMuted },
  hcStats: { flexDirection: 'row', gap: 16 },
  hcStat: { fontSize: 10, color: COLORS.textSecondary },

  modalOverlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.8)', justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: COLORS.surface, borderTopLeftRadius: RADIUS.lg, borderTopRightRadius: RADIUS.lg,
    padding: SPACING.lg, paddingBottom: 40,
  },
  modalTitle: { fontSize: 14, fontWeight: '700', color: COLORS.primary, letterSpacing: 2, marginBottom: 4 },
  modalCoords: { fontSize: 11, color: COLORS.textSecondary, fontFamily: 'monospace', marginBottom: 16 },
  modalInput: {
    backgroundColor: COLORS.background, borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.sm, padding: 12, color: COLORS.text, fontSize: 14,
    marginBottom: 12,
  },
  modalActions: { flexDirection: 'row', gap: 12, marginTop: 4 },
  modalCancel: { flex: 1, padding: 12, borderRadius: RADIUS.sm, borderWidth: 1, borderColor: COLORS.border, alignItems: 'center' },
  modalCancelText: { fontSize: 12, color: COLORS.textSecondary, fontWeight: '600' },
  modalSave: { flex: 1, padding: 12, borderRadius: RADIUS.sm, backgroundColor: COLORS.primary, alignItems: 'center' },
  modalSaveText: { fontSize: 12, color: '#000', fontWeight: '700' },
});

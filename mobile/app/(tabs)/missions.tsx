import { useState, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, BackHandler } from 'react-native';
import { WebView } from 'react-native-webview';
import { COLORS, SPACING, RADIUS } from '@/theme/colors';
import { Ionicons } from '@expo/vector-icons';

type SubTab = 'control' | 'launches' | 'local';

const MISSION_CONTROL_URL = 'https://aerospace.zicore.space/mission-control';

export default function MissionsScreen() {
  const [activeTab, setActiveTab] = useState<SubTab>('control');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [loadProgress, setLoadProgress] = useState(0);
  const webViewRef = useRef<WebView>(null);

  const onRefresh = () => {
    setLoading(true);
    setError('');
    webViewRef.current?.reload();
  };

  const handleBack = () => {
    if (webViewRef.current) {
      webViewRef.current.goBack();
      return true;
    }
    return false;
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>MISSIONS</Text>
          <Text style={styles.subtitle}>Mission Control & Launch Intelligence</Text>
        </View>
        <TouchableOpacity style={styles.refreshBtn} onPress={onRefresh}>
          <Ionicons name="refresh" size={18} color={COLORS.primary} />
        </TouchableOpacity>
      </View>

      {/* Sub-tabs */}
      <View style={styles.tabBar}>
        {([
          { key: 'control', label: 'Control', icon: 'radio' as const },
          { key: 'launches', label: 'Launches', icon: 'rocket' as const },
          { key: 'local', label: 'Local', icon: 'list' as const },
        ] as const).map((tab) => (
          <TouchableOpacity
            key={tab.key}
            style={[styles.tabBtn, activeTab === tab.key && styles.tabBtnActive]}
            onPress={() => setActiveTab(tab.key)}
          >
            <Ionicons name={tab.icon} size={14} color={activeTab === tab.key ? COLORS.primary : COLORS.textSecondary} />
            <Text style={[styles.tabLabel, activeTab === tab.key && styles.tabLabelActive]}>{tab.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      <View style={styles.content}>
        {activeTab === 'control' && (
          <>
            {loading && (
              <View style={styles.loadingOverlay}>
                <ActivityIndicator size="large" color={COLORS.primary} />
                <Text style={styles.loadingText}>Loading Mission Control...</Text>
                {loadProgress > 0 && loadProgress < 100 && (
                  <View style={styles.progressBar}>
                    <View style={[styles.progressFill, { width: `${loadProgress}%` }]} />
                  </View>
                )}
              </View>
            )}
            {error ? (
              <View style={styles.errorContainer}>
                <Ionicons name="cloud-offline" size={48} color={COLORS.error || '#ff4444'} />
                <Text style={styles.errorText}>{error}</Text>
                <TouchableOpacity style={styles.retryBtn} onPress={onRefresh}>
                  <Text style={styles.retryBtnText}>RETRY</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <WebView
                ref={webViewRef}
                source={{ uri: MISSION_CONTROL_URL }}
                style={styles.webview}
                onLoadStart={() => { setLoading(true); setError(''); }}
                onLoadProgress={({ nativeEvent }) => setLoadProgress(Math.round(nativeEvent.progress * 100))}
                onLoadEnd={() => { setLoading(false); setLoadProgress(0); }}
                onError={(e) => { setLoading(false); setError(e.nativeEvent.description || 'Failed to load'); }}
                onHttpError={(e) => {
                  if (e.nativeEvent.statusCode >= 400) {
                    setLoading(false);
                    setError(`HTTP ${e.nativeEvent.statusCode}`);
                  }
                }}
                javaScriptEnabled
                domStorageEnabled
                allowsInlineMediaPlayback
                allowsBackForwardNavigationGestures
                mixedContentMode="always"
                startInLoadingState
                renderLoading={() => null}
              />
            )}
          </>
        )}

        {activeTab === 'launches' && (
          <WebView
            source={{ uri: 'https://aerospace.zicore.space/aerospace' }}
            style={styles.webview}
            javaScriptEnabled
            domStorageEnabled
            allowsInlineMediaPlayback
            mixedContentMode="always"
          />
        )}

        {activeTab === 'local' && (
          <View style={styles.localContainer}>
            <View style={styles.localHeader}>
              <Ionicons name="rocket-outline" size={40} color={COLORS.primary} />
              <Text style={styles.localTitle}>Launch Intelligence (ZALI)</Text>
              <Text style={styles.localSub}>Real-time launch data from Launch Library 2</Text>
            </View>
            <TouchableOpacity style={styles.openControlBtn} onPress={() => setActiveTab('control')}>
              <Ionicons name="open-outline" size={16} color={COLORS.primary} />
              <Text style={styles.openControlText}>Open Mission Control</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.openControlBtn} onPress={() => {
              setActiveTab('control');
              setTimeout(() => {
                webViewRef.current?.postMessage(JSON.stringify({ type: 'navigate', path: '/api/launches' }));
              }, 1000);
            }}>
              <Ionicons name="list-outline" size={16} color={COLORS.accent || COLORS.primary} />
              <Text style={styles.openControlText}>View Launch Manifest</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: SPACING.md, borderBottomWidth: 1, borderBottomColor: COLORS.border,
    backgroundColor: COLORS.surface,
  },
  title: { fontSize: 16, fontWeight: '800', letterSpacing: 2, color: COLORS.text },
  subtitle: { fontSize: 10, color: COLORS.textSecondary, marginTop: 2 },
  refreshBtn: { padding: 8, borderWidth: 1, borderColor: COLORS.border, borderRadius: RADIUS.sm },
  tabBar: {
    flexDirection: 'row', backgroundColor: COLORS.surface,
    borderBottomWidth: 1, borderBottomColor: COLORS.border,
  },
  tabBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    paddingVertical: 10, gap: 6,
  },
  tabBtnActive: { borderBottomWidth: 2, borderBottomColor: COLORS.primary },
  tabLabel: { fontSize: 11, fontWeight: '600', color: COLORS.textSecondary, letterSpacing: 0.5 },
  tabLabelActive: { color: COLORS.primary },
  content: { flex: 1 },
  webview: { flex: 1 },
  loadingOverlay: {
    ...StyleSheet.absoluteFillObject,
    justifyContent: 'center', alignItems: 'center',
    backgroundColor: COLORS.background, zIndex: 10,
  },
  loadingText: { color: COLORS.textSecondary, fontSize: 12, marginTop: 12 },
  progressBar: {
    width: 200, height: 3, backgroundColor: COLORS.border,
    borderRadius: 2, marginTop: 12, overflow: 'hidden',
  },
  progressFill: { height: '100%', backgroundColor: COLORS.primary, borderRadius: 2 },
  errorContainer: {
    flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12,
  },
  errorText: { color: COLORS.textSecondary, fontSize: 13, textAlign: 'center', paddingHorizontal: 40 },
  retryBtn: {
    paddingHorizontal: 24, paddingVertical: 10, borderWidth: 1,
    borderColor: COLORS.primary, borderRadius: RADIUS.sm, marginTop: 8,
  },
  retryBtnText: { color: COLORS.primary, fontSize: 12, fontWeight: '700', letterSpacing: 1 },
  localContainer: { flex: 1, padding: SPACING.lg, gap: 16 },
  localHeader: { alignItems: 'center', paddingTop: 60, gap: 8 },
  localTitle: { fontSize: 18, fontWeight: '700', color: COLORS.text, textAlign: 'center' },
  localSub: { fontSize: 12, color: COLORS.textSecondary, textAlign: 'center' },
  openControlBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 8, padding: SPACING.md, borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.md, backgroundColor: COLORS.surface,
  },
  openControlText: { fontSize: 13, fontWeight: '600', color: COLORS.primary },
});

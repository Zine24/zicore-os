import { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, StatusBar } from 'react-native';
import { WebView } from 'react-native-webview';
import { useRouter } from 'expo-router';
import { useAuthStore } from '@/stores/authStore';
import { COLORS } from '@/theme/colors';
import { BASE_URL } from '@/lib/api';

export default function VRMonitorScreen() {
  const router = useRouter();
  const token = useAuthStore((s) => s.token);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    StatusBar.setHidden(true, 'none');
    return () => { StatusBar.setHidden(false); };
  }, []);

  const injectedJS = `
    window.ZICORE_API = '${BASE_URL}';
    window.ZICORE_TOKEN = '${token || ''}';
    true;
  `;

  return (
    <View style={styles.container}>
      <WebView
        source={{ uri: `${BASE_URL}/vr-monitor` }}
        style={styles.webview}
        injectedJavaScript={injectedJS}
        javaScriptEnabled
        mediaPlaybackRequiresUserAction={false}
        allowsInlineMediaPlayback
        allowsFullscreenVideo
        originWhitelist={['*']}
        onLoad={() => setConnected(true)}
        onError={() => setConnected(false)}
        mixedContentMode="always"
        androidLayerType="hardware"
        cacheEnabled={false}
        scrollEnabled={false}
        setSupportMultipleWindows={false}
      />
      {!connected && (
        <View style={styles.overlay}>
          <View style={styles.loadingHex}>
            <Text style={styles.loadingZ}>Z</Text>
          </View>
          <Text style={styles.loadingText}>ZICORE VR VIEWPORT</Text>
          <Text style={styles.loadingSub}>INITIALIZING SUBSYSTEMS...</Text>
        </View>
      )}
      <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
        <Text style={styles.backBtnText}>X</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  webview: { flex: 1, backgroundColor: '#000' },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#04060c',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 100,
  },
  loadingHex: {
    width: 80, height: 80, borderRadius: 16,
    backgroundColor: COLORS.primaryDim,
    borderWidth: 1, borderColor: COLORS.primary,
    justifyContent: 'center', alignItems: 'center',
  },
  loadingZ: { fontSize: 36, fontWeight: '900', color: COLORS.primary },
  loadingText: {
    fontSize: 12, letterSpacing: 4, color: COLORS.primary,
    marginTop: 20, fontWeight: '700',
  },
  loadingSub: {
    fontSize: 9, letterSpacing: 2, color: COLORS.textMuted,
    marginTop: 8,
  },
  backBtn: {
    position: 'absolute', top: 12, right: 12,
    width: 32, height: 32, borderRadius: 16,
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderWidth: 1, borderColor: 'rgba(0,229,255,0.3)',
    justifyContent: 'center', alignItems: 'center',
    zIndex: 200,
  },
  backBtnText: { color: COLORS.primary, fontSize: 14, fontWeight: '700' },
});

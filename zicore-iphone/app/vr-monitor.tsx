import { useState, useEffect } from 'react';
import { View, TouchableOpacity, StyleSheet, StatusBar } from 'react-native';
import { WebView } from 'react-native-webview';
import { useRouter } from 'expo-router';
import { useAuthStore } from '@/stores/authStore';
import { COLORS } from '@/theme/colors';
import { BASE_URL } from '@/lib/api';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';

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
    <SafeAreaView style={styles.container} edges={[]}>
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
        cacheEnabled={false}
        scrollEnabled={false}
        setSupportMultipleWindows={false}
        allowsBackForwardNavigationGestures
      />
      {!connected && (
        <View style={styles.overlay}>
          <View style={styles.loadingHex}>
            <View style={styles.loadingHexInner}>
              <Ionicons name="radio-outline" size={32} color={COLORS.primary} />
            </View>
          </View>
        </View>
      )}
      <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
        <Ionicons name="close" size={18} color={COLORS.primary} />
      </TouchableOpacity>
    </SafeAreaView>
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
  loadingHexInner: {},
  backBtn: {
    position: 'absolute', top: 12, right: 12,
    width: 36, height: 36, borderRadius: 18,
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderWidth: 1, borderColor: 'rgba(0,229,255,0.3)',
    justifyContent: 'center', alignItems: 'center',
    zIndex: 200,
  },
});

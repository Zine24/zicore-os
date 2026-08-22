import { useState, useEffect, useRef } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ScrollView, Image, Animated,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuthStore } from '@/stores/authStore';
import { COLORS, SPACING, RADIUS, haptic } from '@/theme/colors';
import { Ionicons } from '@expo/vector-icons';
import { SafeAreaView } from 'react-native-safe-area-context';

function StarField() {
  const stars = useRef(
    Array.from({ length: 40 }, () => ({
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 2 + 0.5,
      opacity: Math.random() * 0.6 + 0.2,
    }))
  ).current;
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const iv = setInterval(() => setTick((t) => t + 1), 3000);
    return () => clearInterval(iv);
  }, []);
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      {stars.map((s, i) => (
        <View
          key={i}
          style={{
            position: 'absolute',
            left: `${s.x}%`,
            top: `${s.y}%`,
            width: s.size,
            height: s.size,
            borderRadius: s.size / 2,
            backgroundColor: COLORS.primary,
            opacity: ((tick + i) % 3 === 0) ? s.opacity * 0.4 : s.opacity,
          }}
        />
      ))}
    </View>
  );
}

export default function LoginScreen() {
  const router = useRouter();
  const login = useAuthStore((s) => s.login);
  const [email, setEmail] = useState('ziton2@zicore.space');
  const [password, setPassword] = useState('ZiTon2026');
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const glowAnim = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(glowAnim, { toValue: 0.8, duration: 2000, useNativeDriver: true }),
        Animated.timing(glowAnim, { toValue: 0.3, duration: 2000, useNativeDriver: true }),
      ])
    ).start();
  }, []);

  const handleLogin = async () => {
    if (!email || !password) { setError('Email and password required'); return; }
    haptic.medium();
    setLoading(true);
    setError('');
    const result = await login(email, password);
    setLoading(false);
    if (result.success) {
      haptic.success();
      router.replace('/(tabs)');
    } else {
      haptic.error();
      setError(result.error || 'Login failed');
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={0}
      >
        <StarField />
        <View style={styles.scanlines} pointerEvents="none" />

        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={styles.topLine} />

          <View style={styles.logoWrap}>
            <Animated.View style={[styles.hexFrame, { opacity: glowAnim }]}>
              <View style={styles.hexInner} />
            </Animated.View>
            <Image source={require('../../assets/icon.png')} style={styles.logoImage} resizeMode="contain" />

            <Text style={styles.title}>ZICORE</Text>
            <View style={styles.subtitleRow}>
              <View style={styles.dot} />
              <Text style={styles.subtitle}>AEROSPACE OPERATING SYSTEM</Text>
              <View style={styles.dot} />
            </View>
            <Text style={styles.slogan}>MATERIALIZING IDEAS INTO REALITY</Text>
          </View>

          <View style={styles.form}>
            <Text style={styles.label}>EMAIL</Text>
            <View style={styles.inputWrap}>
              <Ionicons name="mail-outline" size={16} color={COLORS.textMuted} style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="your@email.com"
                placeholderTextColor={COLORS.textMuted}
                value={email}
                onChangeText={setEmail}
                keyboardType="email-address"
                autoCapitalize="none"
                autoComplete="email"
              />
            </View>

            <Text style={styles.label}>PASSWORD</Text>
            <View style={styles.inputWrap}>
              <Ionicons name="lock-closed-outline" size={16} color={COLORS.textMuted} style={styles.inputIcon} />
              <TextInput
                style={styles.input}
                placeholder="Enter password"
                placeholderTextColor={COLORS.textMuted}
                value={password}
                onChangeText={setPassword}
                secureTextEntry={!showPass}
              />
              <TouchableOpacity onPress={() => { haptic.light(); setShowPass(!showPass); }} style={styles.eyeBtn}>
                <Ionicons name={showPass ? "eye-off-outline" : "eye-outline"} size={16} color={COLORS.textMuted} />
              </TouchableOpacity>
            </View>

            {error ? (
              <View style={styles.errorWrap}>
                <Ionicons name="alert-circle" size={14} color={COLORS.error} />
                <Text style={styles.error}>{error}</Text>
              </View>
            ) : null}

            <TouchableOpacity
              style={[styles.btn, loading && styles.btnDisabled]}
              onPress={handleLogin}
              disabled={loading}
            >
              {loading ? (
                <Ionicons name="sync" size={16} color={COLORS.primary} />
              ) : (
                <Ionicons name="log-in-outline" size={16} color={COLORS.primary} />
              )}
              <Text style={styles.btnText}>{loading ? 'AUTHENTICATING...' : 'LOG IN'}</Text>
            </TouchableOpacity>

            <TouchableOpacity onPress={() => { haptic.light(); router.push('/(auth)/register'); }}>
              <Text style={styles.link}>Don't have an account? <Text style={styles.linkBold}>Register</Text></Text>
            </TouchableOpacity>
          </View>

          <View style={styles.footer}>
            <View style={styles.footerLine} />
            <Text style={styles.footerText}>ZINEMOTION FOUNDATION</Text>
            <Text style={styles.footerVersion}>ZICORE SYSTEM v5.0</Text>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  scanlines: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'transparent',
    opacity: 0.015,
    borderWidth: 0.5,
    borderColor: COLORS.primary,
  },
  topLine: {
    width: 60, height: 2, backgroundColor: COLORS.primary,
    alignSelf: 'center', marginBottom: SPACING.xl, opacity: 0.6,
  },
  scroll: { flexGrow: 1, justifyContent: 'center', padding: SPACING.lg, paddingTop: 40 },
  logoWrap: { alignItems: 'center', marginBottom: SPACING.xl },
  hexFrame: {
    width: 130, height: 130, borderRadius: 26, overflow: 'hidden',
    borderWidth: 1.5, borderColor: COLORS.primary, backgroundColor: 'rgba(0,229,255,0.05)',
    marginBottom: SPACING.md,
  },
  hexInner: {
    ...StyleSheet.absoluteFillObject,
    borderWidth: 1, borderColor: 'rgba(0,229,255,0.15)',
    borderRadius: 24, margin: 4,
  },
  logoImage: { width: 130, height: 130, position: 'absolute', top: 0, left: 0 },
  title: { fontSize: 32, fontWeight: '900', letterSpacing: 8, color: COLORS.primary, marginTop: SPACING.sm },
  subtitleRow: { flexDirection: 'row', alignItems: 'center', gap: 8, marginTop: SPACING.xs },
  dot: { width: 4, height: 1, backgroundColor: COLORS.primary, opacity: 0.4 },
  subtitle: { fontSize: 9, letterSpacing: 2.5, color: COLORS.textSecondary },
  slogan: { fontSize: 7, letterSpacing: 3, color: COLORS.primary, marginTop: SPACING.sm, opacity: 0.5 },
  form: { gap: 4 },
  label: { fontSize: 9, fontWeight: '600', letterSpacing: 1.5, color: COLORS.textSecondary, marginTop: SPACING.sm, marginLeft: 4 },
  inputWrap: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.5)', borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.sm, marginTop: 4,
  },
  inputIcon: { marginLeft: 12 },
  input: {
    flex: 1, padding: 14, color: COLORS.text, fontSize: 14, paddingLeft: 10,
  },
  eyeBtn: { padding: 12 },
  errorWrap: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: SPACING.xs },
  error: { color: COLORS.error, fontSize: 12 },
  btn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    backgroundColor: COLORS.primaryDim, borderWidth: 1, borderColor: COLORS.primary,
    borderRadius: RADIUS.sm, padding: 14, marginTop: SPACING.md,
  },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: COLORS.primary, fontSize: 12, fontWeight: '700', letterSpacing: 2 },
  link: { textAlign: 'center', color: COLORS.textSecondary, fontSize: 12, marginTop: SPACING.md },
  linkBold: { color: COLORS.primary, fontWeight: '600' },
  footer: { marginTop: SPACING.xl * 2, alignItems: 'center' },
  footerLine: { width: 40, height: 1, backgroundColor: COLORS.border, marginBottom: SPACING.md },
  footerText: { fontSize: 8, letterSpacing: 2, color: COLORS.textMuted },
  footerVersion: { fontSize: 7, letterSpacing: 1, color: COLORS.textMuted, marginTop: 4, opacity: 0.5 },
});

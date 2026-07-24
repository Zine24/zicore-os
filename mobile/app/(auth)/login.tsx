import { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuthStore } from '@/stores/authStore';
import { COLORS, SPACING, RADIUS, FONT } from '@/theme/colors';

export default function LoginScreen() {
  const router = useRouter();
  const login = useAuthStore((s) => s.login);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) { setError('Email and password required'); return; }
    setLoading(true);
    setError('');
    const result = await login(email, password);
    setLoading(false);
    if (result.success) {
      router.replace('/(tabs)');
    } else {
      setError(result.error || 'Login failed');
    }
  };

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        {/* Logo */}
        <View style={styles.logoWrap}>
          <View style={styles.hexagon}>
            <Text style={styles.logoText}>Z</Text>
          </View>
          <Text style={styles.title}>ZICORE</Text>
          <Text style={styles.subtitle}>AEROSPACE OPERATING SYSTEM</Text>
        </View>

        {/* Form */}
        <View style={styles.form}>
          <Text style={styles.label}>EMAIL</Text>
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

          <Text style={styles.label}>PASSWORD</Text>
          <TextInput
            style={styles.input}
            placeholder="Enter password"
            placeholderTextColor={COLORS.textMuted}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <TouchableOpacity style={[styles.btn, loading && styles.btnDisabled]} onPress={handleLogin} disabled={loading}>
            <Text style={styles.btnText}>{loading ? 'LOGGING IN...' : 'LOG IN'}</Text>
          </TouchableOpacity>

          <TouchableOpacity onPress={() => router.push('/(auth)/register')}>
            <Text style={styles.link}>Don't have an account? <Text style={styles.linkBold}>Register</Text></Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  scroll: { flexGrow: 1, justifyContent: 'center', padding: SPACING.lg },
  logoWrap: { alignItems: 'center', marginBottom: SPACING.xl },
  hexagon: {
    width: 80, height: 80, borderRadius: 16, backgroundColor: COLORS.primaryDim,
    borderWidth: 1, borderColor: COLORS.primary, justifyContent: 'center', alignItems: 'center',
    transform: [{ rotate: '0deg' }],
  },
  logoText: { fontSize: 32, fontWeight: '800', color: COLORS.primary },
  title: { fontSize: 24, fontWeight: '800', letterSpacing: 4, color: COLORS.primary, marginTop: SPACING.md },
  subtitle: { fontSize: 10, letterSpacing: 2, color: COLORS.textSecondary, marginTop: SPACING.xs },
  form: { gap: SPACING.sm },
  label: { fontSize: 10, fontWeight: '600', letterSpacing: 1, color: COLORS.textSecondary, marginTop: SPACING.sm },
  input: {
    backgroundColor: 'rgba(0,0,0,0.4)', borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.sm, padding: 14, color: COLORS.text, fontSize: 14,
  },
  error: { color: COLORS.error, fontSize: 12, marginTop: SPACING.xs },
  btn: {
    backgroundColor: COLORS.primaryDim, borderWidth: 1, borderColor: COLORS.primary,
    borderRadius: RADIUS.sm, padding: 14, alignItems: 'center', marginTop: SPACING.md,
  },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: COLORS.primary, fontSize: 12, fontWeight: '700', letterSpacing: 2 },
  link: { textAlign: 'center', color: COLORS.textSecondary, fontSize: 12, marginTop: SPACING.md },
  linkBold: { color: COLORS.primary, fontWeight: '600' },
});

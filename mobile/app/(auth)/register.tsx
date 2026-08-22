import { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuthStore } from '@/stores/authStore';
import { COLORS, SPACING, RADIUS } from '@/theme/colors';

export default function RegisterScreen() {
  const router = useRouter();
  const register = useAuthStore((s) => s.register);
  const [name, setName] = useState('');
  const [emailPrefix, setEmailPrefix] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [acceptTerms, setAcceptTerms] = useState(false);
  const [acceptPrivacy, setAcceptPrivacy] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const passwordValid = (pw: string) =>
    pw.length >= 8 && /[A-Z]/.test(pw) && /[a-z]/.test(pw) && /[0-9]/.test(pw);

  const handleRegister = async () => {
    if (!name || name.length < 2) { setError('Name must be at least 2 characters'); return; }
    if (!emailPrefix) { setError('Email prefix required'); return; }
    if (!passwordValid(password)) { setError('Password: 8+ chars, upper, lower, digit'); return; }
    if (password !== confirm) { setError('Passwords do not match'); return; }
    if (!acceptTerms || !acceptPrivacy) { setError('You must accept Terms and Privacy'); return; }

    setLoading(true);
    setError('');
    const email = emailPrefix + '@zinemotion.com.mx';
    const result = await register(name, email, password);
    setLoading(false);
    if (result.success) {
      router.replace('/(tabs)');
    } else {
      setError(result.error || 'Registration failed');
    }
  };

  const Toggle = ({ checked, onToggle }: { checked: boolean; onToggle: () => void }) => (
    <TouchableOpacity onPress={onToggle} style={[styles.checkbox, checked && styles.checkboxChecked]}>
      {checked && <Text style={styles.checkmark}>✓</Text>}
    </TouchableOpacity>
  );

  return (
    <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <Text style={styles.title}>CREATE ACCOUNT</Text>
          <Text style={styles.subtitle}>Join ZICORE Aerospace OS</Text>
        </View>

        <View style={styles.form}>
          <Text style={styles.label}>NAME</Text>
          <TextInput style={styles.input} placeholder="Your name" placeholderTextColor={COLORS.textMuted} value={name} onChangeText={setName} />

          <Text style={styles.label}>EMAIL</Text>
          <View style={styles.emailRow}>
            <TextInput style={[styles.input, styles.emailInput]} placeholder="prefix" placeholderTextColor={COLORS.textMuted} value={emailPrefix} onChangeText={setEmailPrefix} autoCapitalize="none" />
            <View style={styles.domain}><Text style={styles.domainText}>@zinemotion.com.mx</Text></View>
          </View>

          <Text style={styles.label}>PASSWORD</Text>
          <TextInput style={styles.input} placeholder="Min 8 chars, upper, lower, digit" placeholderTextColor={COLORS.textMuted} value={password} onChangeText={setPassword} secureTextEntry />
          <Text style={styles.hint}>Min 8 characters, 1 uppercase, 1 lowercase, 1 number</Text>

          <Text style={styles.label}>CONFIRM PASSWORD</Text>
          <TextInput style={styles.input} placeholder="Repeat password" placeholderTextColor={COLORS.textMuted} value={confirm} onChangeText={setConfirm} secureTextEntry />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <TouchableOpacity style={styles.checkRow} onPress={() => setAcceptTerms(!acceptTerms)}>
            <Toggle checked={acceptTerms} onToggle={() => setAcceptTerms(!acceptTerms)} />
            <Text style={styles.checkText}>I accept the <Text style={styles.checkLink}>Terms of Use</Text></Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.checkRow} onPress={() => setAcceptPrivacy(!acceptPrivacy)}>
            <Toggle checked={acceptPrivacy} onToggle={() => setAcceptPrivacy(!acceptPrivacy)} />
            <Text style={styles.checkText}>I accept the <Text style={styles.checkLink}>Privacy Notice</Text></Text>
          </TouchableOpacity>

          <TouchableOpacity style={[styles.btn, loading && styles.btnDisabled]} onPress={handleRegister} disabled={loading}>
            <Text style={styles.btnText}>{loading ? 'CREATING...' : 'CREATE ACCOUNT'}</Text>
          </TouchableOpacity>

          <TouchableOpacity onPress={() => router.back()}>
            <Text style={styles.link}>Already have an account? <Text style={styles.linkBold}>Log In</Text></Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  scroll: { flexGrow: 1, padding: SPACING.lg, paddingTop: SPACING.xl },
  header: { alignItems: 'center', marginBottom: SPACING.lg },
  title: { fontSize: 20, fontWeight: '800', letterSpacing: 3, color: COLORS.accent },
  subtitle: { fontSize: 10, letterSpacing: 2, color: COLORS.textSecondary, marginTop: 4 },
  form: { gap: 4 },
  label: { fontSize: 10, fontWeight: '600', letterSpacing: 1, color: COLORS.textSecondary, marginTop: SPACING.sm },
  input: {
    backgroundColor: 'rgba(0,0,0,0.4)', borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.sm, padding: 12, color: COLORS.text, fontSize: 13,
  },
  emailRow: { flexDirection: 'row', gap: 0 },
  emailInput: { flex: 1, borderTopRightRadius: 0, borderBottomRightRadius: 0 },
  domain: {
    backgroundColor: 'rgba(0,229,255,0.06)', borderWidth: 1, borderLeftWidth: 0,
    borderColor: COLORS.border, borderRadius: 0, borderTopRightRadius: RADIUS.sm,
    borderBottomRightRadius: RADIUS.sm, padding: 12, justifyContent: 'center',
  },
  domainText: { color: COLORS.primary, fontSize: 10, fontWeight: '600' },
  hint: { fontSize: 9, color: COLORS.textMuted, marginTop: 2 },
  error: { color: COLORS.error, fontSize: 12, marginTop: SPACING.sm },
  checkRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: SPACING.sm },
  checkbox: {
    width: 18, height: 18, borderWidth: 1, borderColor: COLORS.border, borderRadius: 4,
    justifyContent: 'center', alignItems: 'center',
  },
  checkboxChecked: { backgroundColor: COLORS.primary, borderColor: COLORS.primary },
  checkmark: { color: COLORS.background, fontSize: 12, fontWeight: '700' },
  checkText: { fontSize: 11, color: COLORS.textSecondary, flex: 1 },
  checkLink: { color: COLORS.primary, fontWeight: '600' },
  btn: {
    backgroundColor: COLORS.accentDim, borderWidth: 1, borderColor: COLORS.accent,
    borderRadius: RADIUS.sm, padding: 14, alignItems: 'center', marginTop: SPACING.md,
  },
  btnDisabled: { opacity: 0.5 },
  btnText: { color: COLORS.accent, fontSize: 12, fontWeight: '700', letterSpacing: 2 },
  link: { textAlign: 'center', color: COLORS.textSecondary, fontSize: 12, marginTop: SPACING.md },
  linkBold: { color: COLORS.accent, fontWeight: '600' },
});

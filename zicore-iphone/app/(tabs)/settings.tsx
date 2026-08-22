import { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet, Alert, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuthStore } from '@/stores/authStore';
import { Ionicons } from '@expo/vector-icons';
import { COLORS, SPACING, RADIUS, haptic } from '@/theme/colors';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as Device from 'expo-device';

function SettingsRow({ icon, label, value, onPress, color }: { icon: string; label: string; value?: string; onPress?: () => void; color?: string }) {
  return (
    <TouchableOpacity
      style={styles.row}
      onPress={() => { if (onPress) { haptic.light(); onPress(); } }}
      activeOpacity={onPress ? 0.6 : 1}
    >
      <Text style={styles.rowIcon}>{icon}</Text>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={[styles.rowValue, color && { color }]}>{value || '>'}</Text>
    </TouchableOpacity>
  );
}

export default function SettingsScreen() {
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const [deviceInfo, setDeviceInfo] = useState('');

  useEffect(() => {
    const info = `${Device.brand || 'Apple'} ${Device.modelName || 'iPhone'}`;
    setDeviceInfo(info);
  }, []);

  const handleLogout = () => {
    haptic.warning();
    Alert.alert('Logout', 'Are you sure you want to log out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Log Out', style: 'destructive', onPress: () => {
          haptic.heavy();
          logout();
          router.replace('/(auth)/login');
        }
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView contentContainerStyle={styles.content}>
        <View style={styles.profileCard}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{user?.display_name?.charAt(0)?.toUpperCase() || 'U'}</Text>
          </View>
          <View style={styles.profileInfo}>
            <Text style={styles.profileName}>{user?.display_name || 'User'}</Text>
            <Text style={styles.profileEmail}>{user?.email || 'user@zinemotion.com.mx'}</Text>
            <View style={styles.planBadge}>
              <Text style={styles.planText}>{(user?.role || 'user').toUpperCase()}</Text>
            </View>
          </View>
        </View>

        <Text style={styles.sectionTitle}>ACCOUNT</Text>
        <View style={styles.section}>
          <SettingsRow icon="person" label="Edit Profile" value={user?.display_name} onPress={() => {}} />
          <SettingsRow icon="lock-closed" label="Change Password" onPress={() => {}} />
          <SettingsRow icon="key" label="API Keys" onPress={() => {}} />
          <SettingsRow icon="phone-portrait" label="Active Sessions" onPress={() => {}} />
        </View>

        <Text style={styles.sectionTitle}>SYSTEM</Text>
        <View style={styles.section}>
          <SettingsRow icon="server" label="Server" value="192.168.1.85:4000" onPress={() => {}} />
          <SettingsRow icon="hardware-chip" label="AI Provider" value="ZICORE Native" onPress={() => {}} />
          <SettingsRow icon="stats-chart" label="System Status" onPress={() => {}} />
        </View>

        <Text style={styles.sectionTitle}>DEVICE</Text>
        <View style={styles.section}>
          <SettingsRow icon="phone-portrait" label="Device" value={deviceInfo} />
          <SettingsRow icon="information-circle" label="Platform" value={`iOS ${Platform.Version || ''}`} />
          <SettingsRow icon="construct" label="App Version" value="5.0.0 (iPhone)" />
        </View>

        <Text style={styles.sectionTitle}>LEGAL</Text>
        <View style={styles.section}>
          <SettingsRow icon="document-text" label="Terms of Service" onPress={() => {}} />
          <SettingsRow icon="shield-checkmark" label="Privacy Policy" onPress={() => {}} />
          <SettingsRow icon="document-text" label="Aviso de Privacidad" onPress={() => {}} />
        </View>

        <Text style={styles.sectionTitle}>ABOUT</Text>
        <View style={styles.section}>
          <SettingsRow icon="rocket" label="Version" value="5.0.0" />
          <SettingsRow icon="globe" label="Web Portal" value="zcs.zicore.space" onPress={() => {}} />
        </View>

        <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
          <Ionicons name="log-out-outline" size={18} color={COLORS.error} />
          <Text style={styles.logoutText}>LOG OUT</Text>
        </TouchableOpacity>

        <Text style={styles.footer}>ZICORE SYSTEM v5.0 - AEROSPACE OS</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: SPACING.md, paddingBottom: 100 },
  profileCard: {
    flexDirection: 'row', alignItems: 'center', gap: 14,
    backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.md, padding: SPACING.md, marginBottom: SPACING.lg,
  },
  avatar: {
    width: 56, height: 56, borderRadius: 28, backgroundColor: COLORS.primaryDim,
    borderWidth: 1, borderColor: COLORS.primary, justifyContent: 'center', alignItems: 'center',
  },
  avatarText: { fontSize: 22, fontWeight: '800', color: COLORS.primary },
  profileInfo: { flex: 1 },
  profileName: { fontSize: 16, fontWeight: '700', color: COLORS.text },
  profileEmail: { fontSize: 11, color: COLORS.textSecondary, marginTop: 2 },
  planBadge: {
    alignSelf: 'flex-start', marginTop: 6, paddingHorizontal: 8, paddingVertical: 2,
    borderRadius: 8, backgroundColor: COLORS.accentDim, borderWidth: 1, borderColor: COLORS.accent,
  },
  planText: { fontSize: 9, fontWeight: '700', color: COLORS.accent, letterSpacing: 1 },
  sectionTitle: {
    fontSize: 10, fontWeight: '600', letterSpacing: 2, color: COLORS.textMuted,
    marginBottom: 8, marginTop: 8,
  },
  section: {
    backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.md, overflow: 'hidden', marginBottom: 8,
  },
  row: {
    flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14,
    borderBottomWidth: 1, borderBottomColor: COLORS.border,
  },
  rowIcon: { fontSize: 16, width: 22, textAlign: 'center' },
  rowLabel: { flex: 1, fontSize: 13, color: COLORS.text },
  rowValue: { fontSize: 11, color: COLORS.textSecondary },
  logoutBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    marginTop: SPACING.lg, padding: 14, borderRadius: RADIUS.sm,
    backgroundColor: COLORS.errorDim, borderWidth: 1, borderColor: 'rgba(255,85,85,0.3)',
  },
  logoutText: { fontSize: 12, fontWeight: '700', color: COLORS.error, letterSpacing: 1 },
  footer: {
    textAlign: 'center', fontSize: 9, color: COLORS.textMuted,
    marginTop: SPACING.xl, letterSpacing: 1,
  },
});

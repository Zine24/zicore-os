import React, { useState, useEffect } from 'react';
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, RefreshControl, Alert, TextInput } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { COLORS, SPACING, RADIUS, FONT } from '@/theme/colors';
import { BASE_URL } from '@/lib/api';
import { authStorage } from '@/lib/auth';

type Tab = 'users' | 'servers' | '2fa';

interface User {
  id: number; username: string; email: string; display_name: string;
  is_active: number; is_admin: number; two_factor_enabled: number;
  last_login: string; created_at: string;
}
interface ServerStats {
  cpu: number; mem: number; disk: number; uptime: string;
  ollama: boolean; ollama_models: string[];
  net_recv_mb: number; net_sent_mb: number;
}

export default function AdminScreen() {
  const [tab, setTab] = useState<Tab>('users');
  const [users, setUsers] = useState<User[]>([]);
  const [servers, setServers] = useState<ServerStats | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [totpCode, setTotpCode] = useState('');
  const [totpSetup, setTotpSetup] = useState<{secret: string; qr_url: string} | null>(null);

  const getHeaders = () => {
    const token = authStorage.getToken();
    return { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) };
  };

  const fetchUsers = async () => {
    try {
      const r = await fetch(`${BASE_URL}/api/sso/admin/users`, { headers: getHeaders() });
      const d = await r.json();
      if (d.success) setUsers(d.users || []);
    } catch {}
  };

  const fetchServers = async () => {
    try {
      const r = await fetch(`${BASE_URL}/api/capacity`, { headers: getHeaders() });
      const d = await r.json();
      setServers(d);
    } catch {}
  };

  const refresh = async () => {
    setRefreshing(true);
    if (tab === 'users') await fetchUsers();
    else await fetchServers();
    setRefreshing(false);
  };

  useEffect(() => {
    setLoading(true);
    Promise.all([fetchUsers(), fetchServers()]).finally(() => setLoading(false));
  }, []);

  const toggleUser = async (userId: number, active: boolean) => {
    Alert.alert(active ? 'Deactivate User' : 'Activate User',
      `Are you sure?`,
      [{ text: 'Cancel' }, {
        text: active ? 'Deactivate' : 'Activate', style: 'destructive',
        onPress: async () => {
          await fetch(`${BASE_URL}/api/sso/users/${userId}/toggle`, {
            method: 'POST', headers: getHeaders(),
          });
          fetchUsers();
        },
      }]
    );
  };

  const deleteUser = async (userId: number, username: string) => {
    Alert.alert('Delete User', `Delete "${username}"? This cannot be undone.`,
      [{ text: 'Cancel' }, {
        text: 'Delete', style: 'destructive',
        onPress: async () => {
          const r = await fetch(`${BASE_URL}/api/sso/users/${userId}`, {
            method: 'DELETE', headers: getHeaders(),
          });
          const d = await r.json();
          if (!d.success) Alert.alert('Error', d.error || 'Cannot delete');
          fetchUsers();
        },
      }]
    );
  };

  const setup2FA = async () => {
    try {
      const r = await fetch(`${BASE_URL}/api/sso/2fa/setup`, {
        method: 'POST', headers: getHeaders(),
      });
      const d = await r.json();
      if (d.success) setTotpSetup({ secret: d.secret, qr_url: d.otpauth_url });
    } catch {}
  };

  const verify2FA = async () => {
    if (!totpCode || totpCode.length !== 6) return;
    try {
      const r = await fetch(`${BASE_URL}/api/sso/2fa/verify`, {
        method: 'POST', headers: getHeaders(),
        body: JSON.stringify({ code: totpCode }),
      });
      const d = await r.json();
      Alert.alert(d.success ? '2FA Enabled' : 'Verification Failed', d.message || d.error);
      if (d.success) setTotpSetup(null);
    } catch {}
  };

  const disable2FA = async () => {
    Alert.alert('Disable 2FA', 'Remove two-factor authentication?',
      [{ text: 'Cancel' }, {
        text: 'Disable', style: 'destructive',
        onPress: async () => {
          const r = await fetch(`${BASE_URL}/api/sso/2fa/disable`, {
            method: 'POST', headers: getHeaders(),
          });
          const d = await r.json();
          Alert.alert(d.success ? '2FA Disabled' : 'Error', d.message || d.error);
        },
      }]
    );
  };

  const TabBtn = ({ t, icon, label }: { t: Tab; icon: string; label: string }) => (
    <TouchableOpacity
      style={[styles.tabBtn, tab === t && styles.tabBtnActive]}
      onPress={() => setTab(t)}
    >
      <Ionicons name={icon as any} size={16} color={tab === t ? COLORS.primary : COLORS.textMuted} />
      <Text style={[styles.tabLabel, tab === t && styles.tabLabelActive]}>{label}</Text>
    </TouchableOpacity>
  );

  return (
    <ScrollView style={styles.container} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={COLORS.primary} />}>
      <View style={styles.header}>
        <Ionicons name="shield-checkmark-outline" size={28} color={COLORS.primary} />
        <View style={{ marginLeft: 12 }}>
          <Text style={styles.title}>Admin Panel</Text>
          <Text style={styles.subtitle}>System Management</Text>
        </View>
      </View>

      <View style={styles.tabRow}>
        <TabBtn t="users" icon="people-outline" label="Users" />
        <TabBtn t="servers" icon="server-outline" label="Servers" />
        <TabBtn t="2fa" icon="key-outline" label="2FA" />
      </View>

      {tab === 'users' && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Registered Users ({users.length})</Text>
          {users.map(u => (
            <View key={u.id} style={styles.userCard}>
              <View style={styles.userInfo}>
                <Text style={styles.username}>{u.username}</Text>
                <Text style={styles.userEmail}>{u.email || 'No email'}</Text>
                <Text style={styles.userMeta}>
                  {u.is_admin ? 'Admin' : 'User'} | {u.two_factor_enabled ? '2FA ON' : '2FA OFF'} | Last: {u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}
                </Text>
              </View>
              <View style={styles.userActions}>
                <TouchableOpacity style={styles.iconBtn} onPress={() => toggleUser(u.id, !!u.is_active)}>
                  <Ionicons name={u.is_active ? 'pause-outline' : 'play-outline'} size={18} color={u.is_active ? COLORS.warning : COLORS.success} />
                </TouchableOpacity>
                <TouchableOpacity style={styles.iconBtn} onPress={() => deleteUser(u.id, u.username)}>
                  <Ionicons name="trash-outline" size={18} color={COLORS.error} />
                </TouchableOpacity>
              </View>
            </View>
          ))}
          {users.length === 0 && <Text style={styles.empty}>No users found</Text>}
        </View>
      )}

      {tab === 'servers' && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>System Capacity</Text>
          {servers ? (
            <View style={styles.serverCard}>
              <View style={styles.statRow}>
                <StatBox label="CPU" value={`${servers.cpu}%`} warn={servers.cpu > 70} crit={servers.cpu > 90} />
                <StatBox label="Memory" value={`${servers.mem}%`} warn={servers.mem > 70} crit={servers.mem > 90} />
                <StatBox label="Disk" value={`${servers.disk}%`} warn={servers.disk > 70} crit={servers.disk > 90} />
              </View>
              <View style={styles.statRow}>
                <StatBox label="Network" value={`↓${servers.net_recv_mb} ↑${servers.net_sent_mb} MB`} />
                <StatBox label="Uptime" value={servers.uptime || '--'} />
                <StatBox label="Ollama" value={servers.ollama ? `ON (${servers.ollama_models?.length || 0})` : 'OFF'} warn={!servers.ollama} />
              </View>
              {servers.ollama_models && servers.ollama_models.length > 0 && (
                <View style={styles.modelList}>
                  <Text style={styles.modelTitle}>Models</Text>
                  {servers.ollama_models.map(m => (
                    <Text key={m} style={styles.modelItem}>• {m}</Text>
                  ))}
                </View>
              )}
            </View>
          ) : (
            <Text style={styles.empty}>Loading...</Text>
          )}
        </View>
      )}

      {tab === '2fa' && (
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Two-Factor Authentication</Text>
          <View style={styles.totpCard}>
            <Text style={styles.totpInfo}>Add an extra layer of security with TOTP-based 2FA.</Text>
            <Text style={styles.totpInfo}>Compatible with Google Authenticator, Authy, etc.</Text>

            {!totpSetup ? (
              <View style={styles.totpBtns}>
                <TouchableOpacity style={styles.btnPrimary} onPress={setup2FA}>
                  <Ionicons name="shield-outline" size={16} color={COLORS.background} />
                  <Text style={styles.btnPrimaryText}>Enable 2FA</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.btnDanger} onPress={disable2FA}>
                  <Ionicons name="shield-offline-outline" size={16} color={COLORS.error} />
                  <Text style={styles.btnDangerText}>Disable 2FA</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <View style={styles.setupBox}>
                <Text style={styles.setupLabel}>1. Add this secret to your authenticator app:</Text>
                <Text style={styles.secret}>{totpSetup.secret}</Text>
                <Text style={styles.setupLabel}>2. Enter the 6-digit code:</Text>
                <TextInput
                  style={styles.codeInput}
                  placeholder="000000"
                  placeholderTextColor={COLORS.textMuted}
                  keyboardType="number-pad"
                  maxLength={6}
                  value={totpCode}
                  onChangeText={setTotpCode}
                />
                <TouchableOpacity style={[styles.btnPrimary, { marginTop: 8 }]} onPress={verify2FA}>
                  <Text style={styles.btnPrimaryText}>Verify & Enable</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>
        </View>
      )}
    </ScrollView>
  );
}

function StatBox({ label, value, warn, crit }: { label: string; value: string; warn?: boolean; crit?: boolean }) {
  const color = crit ? COLORS.error : warn ? COLORS.warning : COLORS.primary;
  return (
    <View style={styles.statBox}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={[styles.statValue, { color }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  header: { flexDirection: 'row', alignItems: 'center', padding: SPACING.lg, paddingTop: 48 },
  title: { fontSize: FONT.size.xl, fontWeight: FONT.weight.bold, color: COLORS.text },
  subtitle: { fontSize: FONT.size.sm, color: COLORS.textSecondary, marginTop: 2 },
  tabRow: { flexDirection: 'row', paddingHorizontal: SPACING.md, gap: 6 },
  tabBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 10, borderRadius: RADIUS.sm, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border },
  tabBtnActive: { backgroundColor: COLORS.primaryDim, borderColor: COLORS.primary },
  tabLabel: { fontSize: FONT.size.sm, color: COLORS.textMuted, fontWeight: FONT.weight.medium },
  tabLabelActive: { color: COLORS.primary },
  section: { padding: SPACING.md },
  sectionTitle: { fontSize: FONT.size.lg, fontWeight: FONT.weight.bold, color: COLORS.text, marginBottom: 12 },
  userCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: COLORS.card, borderRadius: RADIUS.md, padding: SPACING.md, marginBottom: 8, borderWidth: 1, borderColor: COLORS.border },
  userInfo: { flex: 1 },
  username: { fontSize: FONT.size.md, fontWeight: FONT.weight.bold, color: COLORS.text },
  userEmail: { fontSize: FONT.size.sm, color: COLORS.textSecondary, marginTop: 2 },
  userMeta: { fontSize: FONT.size.xs, color: COLORS.textMuted, marginTop: 4 },
  userActions: { flexDirection: 'row', gap: 8 },
  iconBtn: { width: 36, height: 36, borderRadius: 18, backgroundColor: COLORS.surface, justifyContent: 'center', alignItems: 'center', borderWidth: 1, borderColor: COLORS.border },
  empty: { fontSize: FONT.size.md, color: COLORS.textMuted, textAlign: 'center', padding: SPACING.xl },
  serverCard: { backgroundColor: COLORS.card, borderRadius: RADIUS.md, padding: SPACING.md, borderWidth: 1, borderColor: COLORS.border },
  statRow: { flexDirection: 'row', gap: 8, marginBottom: 8 },
  statBox: { flex: 1, backgroundColor: COLORS.surface, borderRadius: RADIUS.sm, padding: 10, alignItems: 'center', borderWidth: 1, borderColor: COLORS.border },
  statLabel: { fontSize: FONT.size.xs, color: COLORS.textMuted, letterSpacing: 1 },
  statValue: { fontSize: FONT.size.md, fontWeight: FONT.weight.bold, marginTop: 4 },
  modelList: { marginTop: 8, padding: 10, backgroundColor: COLORS.surface, borderRadius: RADIUS.sm, borderWidth: 1, borderColor: COLORS.border },
  modelTitle: { fontSize: FONT.size.xs, color: COLORS.textSecondary, marginBottom: 4, letterSpacing: 1 },
  modelItem: { fontSize: FONT.size.sm, color: COLORS.text, lineHeight: 20 },
  totpCard: { backgroundColor: COLORS.card, borderRadius: RADIUS.md, padding: SPACING.md, borderWidth: 1, borderColor: COLORS.border },
  totpInfo: { fontSize: FONT.size.sm, color: COLORS.textSecondary, marginBottom: 6, lineHeight: 18 },
  totpBtns: { flexDirection: 'row', gap: 10, marginTop: 12 },
  btnPrimary: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: COLORS.primary, paddingHorizontal: 16, paddingVertical: 10, borderRadius: RADIUS.sm },
  btnPrimaryText: { fontSize: FONT.size.sm, fontWeight: FONT.weight.bold, color: COLORS.background },
  btnDanger: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: COLORS.errorDim, paddingHorizontal: 16, paddingVertical: 10, borderRadius: RADIUS.sm, borderWidth: 1, borderColor: COLORS.error },
  btnDangerText: { fontSize: FONT.size.sm, fontWeight: FONT.weight.bold, color: COLORS.error },
  setupBox: { marginTop: 12 },
  setupLabel: { fontSize: FONT.size.sm, color: COLORS.textSecondary, marginBottom: 6 },
  secret: { fontSize: FONT.size.md, fontFamily: 'Courier New', color: COLORS.primary, backgroundColor: COLORS.surface, padding: 10, borderRadius: RADIUS.sm, textAlign: 'center', letterSpacing: 2, marginBottom: 12 },
  codeInput: { fontSize: FONT.size.xl, fontFamily: 'Courier New', color: COLORS.text, backgroundColor: COLORS.surface, padding: 12, borderRadius: RADIUS.sm, textAlign: 'center', letterSpacing: 8, borderWidth: 1, borderColor: COLORS.border },
});

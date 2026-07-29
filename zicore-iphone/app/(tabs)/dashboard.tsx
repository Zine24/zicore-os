import React, { useEffect, useCallback, useState } from 'react';
import {
  View, Text, ScrollView, RefreshControl, StyleSheet,
  TouchableOpacity, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useSystemStore } from '@/stores/systemStore';
import { useAuthStore } from '@/stores/authStore';
import { Ionicons } from '@expo/vector-icons';
import { COLORS, SPACING, RADIUS, haptic } from '@/theme/colors';
import { SafeAreaView } from 'react-native-safe-area-context';

function GaugeCard({ label, value, color, unit, icon }: { label: string; value: number; color: string; unit: string; icon: string }) {
  const pct = Math.min(Math.max(value, 0), 100);
  return (
    <View style={styles.gaugeCard}>
      <View style={styles.gaugeHeader}>
        <Ionicons name={icon as any} size={14} color={color} />
        <Text style={styles.gaugeLabel}>{label}</Text>
      </View>
      <View style={styles.gaugeBarBg}>
        <View style={[styles.gaugeBarFill, { width: `${pct}%`, backgroundColor: color }]} />
      </View>
      <Text style={[styles.gaugeValue, { color }]}>{value.toFixed(1)}{unit}</Text>
    </View>
  );
}

function StatCard({ icon, label, value, color }: { icon: string; label: string; value: string; color: string }) {
  return (
    <View style={styles.statCard}>
      <Ionicons name={icon as any} size={18} color={color} />
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={[styles.statValue, { color }]}>{value}</Text>
    </View>
  );
}

export default function DashboardScreen() {
  const router = useRouter();
  const { stats, isLoading, fetchStats } = useSystemStore();
  const user = useAuthStore((s) => s.user);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => { fetchStats(); }, []);
  useEffect(() => {
    const interval = setInterval(fetchStats, 10000);
    return () => clearInterval(interval);
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchStats();
    setRefreshing(false);
  }, []);

  const cpuColor = (stats?.cpu_percent || 0) > 80 ? COLORS.error : (stats?.cpu_percent || 0) > 50 ? COLORS.warning : COLORS.success;
  const memColor = (stats?.memory_percent || 0) > 80 ? COLORS.error : (stats?.memory_percent || 0) > 50 ? COLORS.warning : COLORS.success;
  const diskColor = (stats?.disk_percent || 0) > 90 ? COLORS.error : (stats?.disk_percent || 0) > 70 ? COLORS.warning : COLORS.success;

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView
        style={styles.scrollContent}
        contentContainerStyle={styles.content}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.primary} />}
      >
        <View style={styles.header}>
          <View style={styles.headerLeft}>
            <View style={styles.headerHex}>
              <Text style={styles.headerHexText}>Z</Text>
            </View>
            <View>
              <Text style={styles.greeting}>Hello, {user?.display_name || 'Commander'}</Text>
              <View style={styles.statusRow}>
                <View style={[styles.statusDot, { backgroundColor: stats ? COLORS.success : COLORS.error }]} />
                <Text style={styles.headerSub}>{stats ? 'Systems Online' : 'Connecting...'}</Text>
              </View>
            </View>
          </View>
        </View>

        <Text style={styles.sectionTitle}>SYSTEM MONITOR</Text>
        <View style={styles.gauges}>
          <GaugeCard label="CPU" value={stats?.cpu_percent || 0} color={cpuColor} unit="%" icon="hardware-chip-outline" />
          <GaugeCard label="MEMORY" value={stats?.memory_percent || 0} color={memColor} unit="%" icon="cube-outline" />
          <GaugeCard label="DISK" value={stats?.disk_percent || 0} color={diskColor} unit="%" icon="server-outline" />
        </View>

        <Text style={styles.sectionTitle}>TELEMETRY</Text>
        <View style={styles.statsGrid}>
          <StatCard icon="time-outline" label="Uptime" value={stats?.uptime || '--'} color={COLORS.primary} />
          <StatCard icon="flash-outline" label="RAM Used" value={`${stats?.memory_used_mb || 0}MB`} color={COLORS.accent} />
          <StatCard icon="archive-outline" label="Disk Used" value={`${stats?.disk_used_gb || 0}GB`} color={COLORS.primary} />
          <StatCard icon="hardware-chip-outline" label="Ollama" value={stats?.ollama_status ? 'Online' : 'Offline'} color={stats?.ollama_status ? COLORS.success : COLORS.error} />
        </View>

        <View style={styles.providerCard}>
          <View style={styles.providerRow}>
            <Ionicons name="radio-outline" size={16} color={COLORS.primary} />
            <Text style={styles.providerLabel}>Active AI Provider</Text>
          </View>
          <Text style={styles.providerValue}>{stats?.active_provider || 'unknown'}</Text>
        </View>

        <TouchableOpacity
          style={styles.vrButton}
          onPress={() => { haptic.medium(); router.push('/vr-monitor'); }}
        >
          <View style={styles.vrHex}>
            <Text style={styles.vrHexText}>Z</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.vrTitle}>VR MONITOR</Text>
            <Text style={styles.vrSub}>Stereoscopic mirror view for headset</Text>
          </View>
          <Ionicons name="chevron-forward" size={18} color={COLORS.primary} />
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  scrollContent: { flex: 1 },
  content: { padding: SPACING.md, paddingBottom: 100 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: SPACING.lg },
  headerLeft: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  headerHex: {
    width: 42, height: 42, borderRadius: 12, backgroundColor: COLORS.primaryDim,
    borderWidth: 1, borderColor: COLORS.primary, justifyContent: 'center', alignItems: 'center',
  },
  headerHexText: { fontSize: 18, fontWeight: '900', color: COLORS.primary },
  greeting: { fontSize: 18, fontWeight: '800', color: COLORS.text },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: 5, marginTop: 2 },
  statusDot: { width: 7, height: 7, borderRadius: 4 },
  headerSub: { fontSize: 10, color: COLORS.textSecondary, letterSpacing: 0.5 },
  sectionTitle: {
    fontSize: 9, fontWeight: '700', letterSpacing: 2, color: COLORS.textMuted,
    marginBottom: SPACING.sm, marginTop: SPACING.sm,
  },
  gauges: { gap: SPACING.sm, marginBottom: SPACING.md },
  gaugeCard: { backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: RADIUS.md, padding: SPACING.md },
  gaugeHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  gaugeLabel: { fontSize: 10, fontWeight: '600', letterSpacing: 1, color: COLORS.textSecondary },
  gaugeBarBg: { height: 6, backgroundColor: COLORS.border, borderRadius: 3, overflow: 'hidden' },
  gaugeBarFill: { height: '100%', borderRadius: 3 },
  gaugeValue: { fontSize: 13, fontWeight: '700', marginTop: 6 },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: SPACING.sm, marginBottom: SPACING.md },
  statCard: {
    width: '48%', flexGrow: 1, backgroundColor: COLORS.surface,
    borderWidth: 1, borderColor: COLORS.border, borderRadius: RADIUS.md, padding: SPACING.md, gap: 4,
  },
  statLabel: { fontSize: 10, color: COLORS.textSecondary, letterSpacing: 0.5 },
  statValue: { fontSize: 13, fontWeight: '700' },
  providerCard: {
    backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.md, padding: SPACING.md,
  },
  providerRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 },
  providerLabel: { fontSize: 10, color: COLORS.textSecondary, letterSpacing: 1 },
  providerValue: { fontSize: 14, fontWeight: '600', color: COLORS.primary },
  vrButton: {
    flexDirection: 'row', alignItems: 'center', gap: SPACING.md,
    backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.primary,
    borderRadius: RADIUS.md, padding: SPACING.md, marginTop: SPACING.md,
  },
  vrHex: {
    width: 44, height: 44, borderRadius: 10,
    backgroundColor: COLORS.primaryDim, borderWidth: 1, borderColor: COLORS.primary,
    justifyContent: 'center', alignItems: 'center',
  },
  vrHexText: { fontSize: 20, fontWeight: '900', color: COLORS.primary },
  vrTitle: { fontSize: 12, fontWeight: '700', letterSpacing: 2, color: COLORS.primary },
  vrSub: { fontSize: 9, color: COLORS.textSecondary, marginTop: 2 },
});

import { useEffect, useCallback } from 'react';
import { View, Text, ScrollView, RefreshControl, StyleSheet } from 'react-native';
import { useSystemStore } from '@/stores/systemStore';
import { useAuthStore } from '@/stores/authStore';
import { COLORS, SPACING, RADIUS } from '@/theme/colors';

function GaugeCard({ label, value, color, unit }: { label: string; value: number; color: string; unit: string }) {
  const pct = Math.min(Math.max(value, 0), 100);
  return (
    <View style={styles.gaugeCard}>
      <Text style={styles.gaugeLabel}>{label}</Text>
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
      <Text style={styles.statIcon}>{icon}</Text>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={[styles.statValue, { color }]}>{value}</Text>
    </View>
  );
}

export default function DashboardScreen() {
  const { stats, isLoading, fetchStats } = useSystemStore();
  const user = useAuthStore((s) => s.user);
  const [refreshing, setRefreshing] = React.useState(false);

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
    <ScrollView style={styles.container} contentContainerStyle={styles.content} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.primary} />}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>Hello, {user?.display_name || 'Commander'}</Text>
          <Text style={styles.headerSub}>System Dashboard</Text>
        </View>
        <View style={[styles.statusDot, { backgroundColor: stats ? COLORS.success : COLORS.error }]} />
      </View>

      {/* Gauges */}
      <View style={styles.gauges}>
        <GaugeCard label="CPU" value={stats?.cpu_percent || 0} color={cpuColor} unit="%" />
        <GaugeCard label="MEMORY" value={stats?.memory_percent || 0} color={memColor} unit="%" />
        <GaugeCard label="DISK" value={stats?.disk_percent || 0} color={diskColor} unit="%" />
      </View>

      {/* Stats Grid */}
      <View style={styles.statsGrid}>
        <StatCard icon="⏱️" label="Uptime" value={stats?.uptime || '--'} color={COLORS.cyan} />
        <StatCard icon="🧠" label="RAM Used" value={`${stats?.memory_used_mb || 0}MB`} color={COLORS.accent} />
        <StatCard icon="💾" label="Disk Used" value={`${stats?.disk_used_gb || 0}GB`} color={COLORS.primary} />
        <StatCard icon="🤖" label="Ollama" value={stats?.ollama_status ? 'Online' : 'Offline'} color={stats?.ollama_status ? COLORS.success : COLORS.error} />
      </View>

      {/* Provider */}
      <View style={styles.providerCard}>
        <Text style={styles.providerLabel}>Active AI Provider</Text>
        <Text style={styles.providerValue}>{stats?.active_provider || 'unknown'}</Text>
      </View>
    </ScrollView>
  );
}

import React from 'react';

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { padding: SPACING.md, paddingBottom: 100 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: SPACING.lg },
  greeting: { fontSize: 20, fontWeight: '800', color: COLORS.text },
  headerSub: { fontSize: 11, color: COLORS.textSecondary, letterSpacing: 1, marginTop: 2 },
  statusDot: { width: 10, height: 10, borderRadius: 5 },
  gauges: { gap: SPACING.sm, marginBottom: SPACING.md },
  gaugeCard: { backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: RADIUS.md, padding: SPACING.md },
  gaugeLabel: { fontSize: 10, fontWeight: '600', letterSpacing: 1, color: COLORS.textSecondary, marginBottom: 6 },
  gaugeBarBg: { height: 6, backgroundColor: COLORS.border, borderRadius: 3, overflow: 'hidden' },
  gaugeBarFill: { height: '100%', borderRadius: 3, transition: 'width 0.5s' },
  gaugeValue: { fontSize: 13, fontWeight: '700', marginTop: 6 },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: SPACING.sm, marginBottom: SPACING.md },
  statCard: { width: '48%', flexGrow: 1, backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: RADIUS.md, padding: SPACING.md },
  statIcon: { fontSize: 20, marginBottom: 6 },
  statLabel: { fontSize: 10, color: COLORS.textSecondary, letterSpacing: 0.5, marginBottom: 4 },
  statValue: { fontSize: 13, fontWeight: '700' },
  providerCard: { backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border, borderRadius: RADIUS.md, padding: SPACING.md },
  providerLabel: { fontSize: 10, color: COLORS.textSecondary, letterSpacing: 1, marginBottom: 4 },
  providerValue: { fontSize: 14, fontWeight: '600', color: COLORS.primary },
});

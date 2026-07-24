import { useState, useEffect } from 'react';
import { View, Text, FlatList, TouchableOpacity, RefreshControl, StyleSheet } from 'react-native';
import { missionsAPI } from '@/lib/api';
import { COLORS, SPACING, RADIUS } from '@/theme/colors';
import { Ionicons } from '@expo/vector-icons';

interface Mission {
  id: string;
  name: string;
  phase: string;
  created: string;
}

const PHASE_COLORS: Record<string, string> = {
  planning: COLORS.warning,
  active: COLORS.success,
  complete: COLORS.primary,
};

const PHASE_ICONS: Record<string, string> = {
  planning: '📋',
  active: '🚀',
  complete: '✅',
};

export default function MissionsScreen() {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchMissions = async () => {
    try {
      const res = await missionsAPI.list();
      setMissions(res.data?.missions || []);
    } catch {
      setMissions([]);
    }
    setLoading(false);
    setRefreshing(false);
  };

  useEffect(() => { fetchMissions(); }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await fetchMissions();
  };

  const renderMission = ({ item }: { item: Mission }) => {
    const phaseColor = PHASE_COLORS[item.phase] || COLORS.textSecondary;
    const phaseIcon = PHASE_ICONS[item.phase] || '📌';

    return (
      <TouchableOpacity style={styles.card} activeOpacity={0.7}>
        <View style={styles.cardHeader}>
          <Text style={styles.cardIcon}>{phaseIcon}</Text>
          <View style={styles.cardInfo}>
            <Text style={styles.cardTitle}>{item.name}</Text>
            <Text style={styles.cardDate}>{item.created?.split('T')[0] || 'Unknown date'}</Text>
          </View>
          <View style={[styles.phaseBadge, { borderColor: phaseColor }]}>
            <Text style={[styles.phaseText, { color: phaseColor }]}>{item.phase?.toUpperCase()}</Text>
          </View>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.title}>MISSIONS</Text>
          <Text style={styles.subtitle}>{missions.length} mission{missions.length !== 1 ? 's' : ''}</Text>
        </View>
        <TouchableOpacity style={styles.addBtn}>
          <Ionicons name="add" size={20} color={COLORS.primary} />
        </TouchableOpacity>
      </View>

      {/* List */}
      <FlatList
        data={missions}
        keyExtractor={(item) => item.id}
        renderItem={renderMission}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={COLORS.primary} />}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>🚀</Text>
            <Text style={styles.emptyText}>No missions yet</Text>
            <Text style={styles.emptySub}>Create your first mission</Text>
          </View>
        }
      />
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
  addBtn: { padding: 8, borderWidth: 1, borderColor: COLORS.border, borderRadius: RADIUS.sm },
  list: { padding: SPACING.md, paddingBottom: 100 },
  card: {
    backgroundColor: COLORS.surface, borderWidth: 1, borderColor: COLORS.border,
    borderRadius: RADIUS.md, padding: SPACING.md, marginBottom: SPACING.sm,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  cardIcon: { fontSize: 24 },
  cardInfo: { flex: 1 },
  cardTitle: { fontSize: 14, fontWeight: '600', color: COLORS.text },
  cardDate: { fontSize: 10, color: COLORS.textSecondary, marginTop: 2 },
  phaseBadge: { borderWidth: 1, borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4 },
  phaseText: { fontSize: 9, fontWeight: '700', letterSpacing: 1 },
  empty: { alignItems: 'center', paddingTop: 100 },
  emptyIcon: { fontSize: 48, marginBottom: 12 },
  emptyText: { fontSize: 16, fontWeight: '600', color: COLORS.textSecondary },
  emptySub: { fontSize: 11, color: COLORS.textMuted, marginTop: 4 },
});

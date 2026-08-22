import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { COLORS, SPACING } from '@/theme/colors';

export default function NotFound() {
  const router = useRouter();
  return (
    <View style={styles.container}>
      <Text style={styles.icon}>🛸</Text>
      <Text style={styles.title}>404</Text>
      <Text style={styles.subtitle}>Page not found</Text>
      <TouchableOpacity style={styles.btn} onPress={() => router.replace('/')}>
        <Text style={styles.btnText}>GO HOME</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background, justifyContent: 'center', alignItems: 'center', padding: SPACING.lg },
  icon: { fontSize: 64, marginBottom: 16 },
  title: { fontSize: 48, fontWeight: '800', color: COLORS.primary },
  subtitle: { fontSize: 14, color: COLORS.textSecondary, marginTop: 4 },
  btn: {
    marginTop: 24, paddingHorizontal: 24, paddingVertical: 10, borderRadius: 8,
    backgroundColor: COLORS.primaryDim, borderWidth: 1, borderColor: COLORS.primary,
  },
  btnText: { color: COLORS.primary, fontSize: 12, fontWeight: '700', letterSpacing: 2 },
});

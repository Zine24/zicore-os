import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { COLORS, SPACING } from '@/theme/colors';
import { SafeAreaView } from 'react-native-safe-area-context';
import { haptic } from '@/theme/colors';

export default function NotFound() {
  const router = useRouter();
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <Text style={styles.icon}>UFO</Text>
        <Text style={styles.title}>404</Text>
        <Text style={styles.subtitle}>Page not found</Text>
        <TouchableOpacity
          style={styles.btn}
          onPress={() => { haptic.medium(); router.replace('/'); }}
        >
          <Text style={styles.btnText}>GO HOME</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.background },
  content: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: SPACING.lg },
  icon: { fontSize: 48, marginBottom: 16, color: COLORS.primary },
  title: { fontSize: 48, fontWeight: '800', color: COLORS.primary },
  subtitle: { fontSize: 14, color: COLORS.textSecondary, marginTop: 4 },
  btn: {
    marginTop: 24, paddingHorizontal: 24, paddingVertical: 10, borderRadius: 8,
    backgroundColor: COLORS.primaryDim, borderWidth: 1, borderColor: COLORS.primary,
  },
  btnText: { color: COLORS.primary, fontSize: 12, fontWeight: '700', letterSpacing: 2 },
});

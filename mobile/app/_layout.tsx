import { useEffect } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { PaperProvider, MD3DarkTheme } from 'react-native-paper';
import { useAuthStore } from '@/stores/authStore';
import { COLORS } from '@/theme/colors';

const theme = {
  ...MD3DarkTheme,
  colors: {
    ...MD3DarkTheme.colors,
    primary: COLORS.primary,
    secondary: COLORS.accent,
    background: COLORS.background,
    surface: COLORS.surface,
    surfaceVariant: COLORS.card,
    error: COLORS.error,
    text: COLORS.text,
    onBackground: COLORS.text,
    onSurface: COLORS.text,
    outline: COLORS.border,
  },
};

export default function RootLayout() {
  const init = useAuthStore((s) => s.init);

  useEffect(() => { init(); }, []);

  return (
    <PaperProvider theme={theme}>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: COLORS.background },
          animation: 'fade',
        }}
      />
    </PaperProvider>
  );
}

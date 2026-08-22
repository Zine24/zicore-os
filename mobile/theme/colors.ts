export const COLORS = {
  background: '#04060c',
  surface: '#0d1117',
  card: '#111827',
  cardHover: '#1a2332',

  primary: '#00e5ff',
  primaryDim: 'rgba(0, 229, 255, 0.15)',
  accent: '#7c4dff',
  accentDim: 'rgba(124, 77, 255, 0.15)',

  success: '#00ff88',
  successDim: 'rgba(0, 255, 136, 0.15)',
  warning: '#ffa500',
  warningDim: 'rgba(255, 165, 0, 0.15)',
  error: '#ff5555',
  errorDim: 'rgba(255, 85, 85, 0.15)',

  text: '#e0e0e0',
  textSecondary: '#607080',
  textMuted: '#3a4050',

  border: '#1a2332',
  borderLight: '#2a3342',

  white: '#ffffff',
  black: '#000000',
};

export const SPACING = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
};

export const RADIUS = {
  sm: 6,
  md: 10,
  lg: 16,
  xl: 24,
};

export const FONT = {
  size: {
    xs: 10,
    sm: 12,
    md: 14,
    lg: 16,
    xl: 20,
    xxl: 28,
  },
  weight: {
    regular: '400' as const,
    medium: '500' as const,
    semibold: '600' as const,
    bold: '700' as const,
  },
};

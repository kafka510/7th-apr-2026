import type { Theme } from '../contexts/ThemeContext';

export interface ThemeColors {
  bgPrimary: string;
  bgSecondary: string;
  bgTertiary: string;
  textPrimary: string;
  textSecondary: string;
  textTertiary: string;
  border: string;
  cardBg: string;
  cardBorder: string;
  accent: string;
  accentSecondary: string;
  hover: string;
  active: string;
}

export function getThemeColors(theme: Theme): ThemeColors {
  if (theme === 'light') {
    return {
      bgPrimary: '#f8fbff',
      bgSecondary: '#ffffff',
      bgTertiary: '#f0f4f8',
      textPrimary: '#1a1a1a',
      textSecondary: '#4a5568',
      textTertiary: '#718096',
      border: '#e2e8f0',
      cardBg: '#ffffff',
      cardBorder: '#e2e8f0',
      accent: '#0072ce',
      accentSecondary: '#00c6ff',
      hover: 'rgba(0, 114, 206, 0.05)',
      active: 'rgba(0, 114, 206, 0.1)',
    };
  } else {
    return {
      bgPrimary: '#0f172a',
      bgSecondary: '#1e293b',
      bgTertiary: '#334155',
      textPrimary: '#f1f5f9',
      textSecondary: '#cbd5e0',
      textTertiary: '#94a3b8',
      border: '#334155',
      cardBg: '#1e293b',
      cardBorder: '#334155',
      accent: '#00c6ff',
      accentSecondary: '#0072ce',
      hover: 'rgba(255, 255, 255, 0.05)',
      active: 'rgba(0, 163, 255, 0.15)',
    };
  }
}

export function getGradientBg(theme: Theme): string {
  return theme === 'dark'
    ? 'linear-gradient(to bottom right, #0f172a, #1e293b, #0f172a)'
    : 'linear-gradient(to bottom right, #f8fbff, #ffffff, #f8fbff)';
}


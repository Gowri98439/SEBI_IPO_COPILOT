/**
 * Design Tokens — IPO Copilot AI Professional Theme
 * Source of truth for all colour, spacing, and typography values.
 * Mirrors the CSS custom properties in index.css.
 */

export const DesignTokens = {
  colors: {
    /* Backgrounds */
    bgPage:     '#F1F5F9',
    bgCard:     '#FFFFFF',
    bgSidebar:  '#0F2040',
    bgElevated: '#F8FAFC',
    bgMuted:    '#EFF3F8',

    /* Text */
    textPrimary:   '#0F172A',
    textSecondary: '#475569',
    textMuted:     '#94A3B8',
    textInverse:   '#FFFFFF',

    /* Brand */
    accent:      '#003087',
    accentLight: '#EFF6FF',
    accentHover: '#00235E',
    accentMid:   '#1A56DB',

    /* Semantic */
    success:       '#15803D',
    successBg:     '#F0FDF4',
    successBorder: '#BBF7D0',
    warning:       '#B45309',
    warningBg:     '#FFFBEB',
    warningBorder: '#FDE68A',
    danger:        '#B91C1C',
    dangerBg:      '#FEF2F2',
    dangerBorder:  '#FECACA',

    /* Borders */
    border:      '#E2E8F0',
    borderFocus: '#003087',
  },

  shadows: {
    sm: '0 1px 3px 0 rgba(0,0,0,0.10), 0 1px 2px -1px rgba(0,0,0,0.06)',
    md: '0 4px 6px -1px rgba(0,0,0,0.10), 0 2px 4px -2px rgba(0,0,0,0.06)',
    lg: '0 10px 15px -3px rgba(0,0,0,0.10), 0 4px 6px -4px rgba(0,0,0,0.05)',
  },

  radius: {
    sm: '6px',
    md: '8px',
    lg: '10px',
    xl: '14px',
    full: '9999px',
  },

  fonts: {
    sans: "'Inter', system-ui, -apple-system, sans-serif",
    mono: "'JetBrains Mono', 'Fira Code', ui-monospace, monospace",
  },

  transitions: {
    fast: '150ms cubic-bezier(0.4,0,0.2,1)',
    normal: '250ms cubic-bezier(0.4,0,0.2,1)',
  },
} as const;

export type DesignTokensType = typeof DesignTokens;

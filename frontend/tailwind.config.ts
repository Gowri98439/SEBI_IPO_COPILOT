import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // --- Core brand (matches CSS var(--accent) = #003087) ---
        'ipo-base':           '#F1F5F9',  // var(--bg-page)
        'ipo-elevated':       '#FFFFFF',  // var(--bg-card)
        'ipo-overlay':        '#F8FAFC',  // var(--bg-elevated)
        'ipo-border':         '#E2E8F0',  // var(--border)
        'ipo-text':           '#0F172A',  // var(--text-primary)
        'ipo-text-secondary': '#475569',  // var(--text-secondary)
        'ipo-muted':          '#64748B',  // WCAG AA on white: 4.6:1 (replaces #94A3B8)
        'ipo-verified':       '#15803D',  // var(--success)
        'ipo-attention':      '#B45309',  // var(--warning)
        'ipo-critical':       '#B91C1C',  // var(--danger)
        'ipo-ai':             '#1A56DB',  // var(--accent-mid)
        'ipo-accent':         '#003087',  // var(--accent) — primary SEBI navy
        'ipo-sidebar':        '#0F2040',  // var(--bg-sidebar)
        'ipo-sidebar-hover':  'rgba(255,255,255,0.07)',
      },
      borderRadius: {
        'sm': '0.375rem',
        'md': '0.5rem',
        'lg': '0.75rem',
      },
      fontFamily: {
        display: ['"Inter"', 'system-ui', 'sans-serif'],
        body: ['"Inter"', 'system-ui', 'sans-serif'],
        data: ['"JetBrains Mono"', 'Menlo', 'monospace'],
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
        serif: ['"Georgia"', 'serif'],
        mono: ['"JetBrains Mono"', 'Menlo', 'monospace'],
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out forwards',
        'slide-up': 'slideUp 0.25s ease-out forwards',
        shimmer: 'shimmer 2s linear infinite',
      },
      boxShadow: {
        'card': '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
        'panel': '0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.025)',
      },
    },
  },
  plugins: [],
}

export default config

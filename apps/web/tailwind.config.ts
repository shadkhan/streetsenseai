import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // ── shadcn/ui CSS variable mappings ────────────────────
        // These let shadcn Button, Card, etc. resolve their utilities.
        // Values come from our :root CSS variables in globals.css.
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        border:  'hsl(var(--border))',
        input:   'hsl(var(--input))',
        ring:    'hsl(var(--ring))',

        // ── Brand ──────────────────────────────────────────────
        brand: {
          DEFAULT: '#1E3A5F',   // Slate blue — primary actions, headings
          light:   '#E8EEF5',   // Brand tint — hover states, selected rows
          muted:   '#4A6FA5',   // Secondary brand — links, icons
        },

        // ── Semantic — Risk Levels ──────────────────────────────
        risk: {
          low:           '#1A9E62',   // deep forest-green (was emerald-600)
          'low-bg':      '#D1FAE5',
          medium:        '#B5680A',   // deep amber-brown (was neon amber)
          'medium-bg':   '#FEF3C7',
          high:          '#CC470D',   // burnt sienna-orange (was bright orange)
          'high-bg':     '#FFF7ED',
          critical:      '#BE2222',   // deep crimson (was bright red)
          'critical-bg': '#FEE2E2',
        },

        // ── Map Canvas ─────────────────────────────────────────
        map: {
          corridor: '#F97316',   // Coral — critical corridor highlight
          works:    '#3B82F6',   // Blue — individual works marker
          nuar:     '#8B5CF6',   // Purple — underground asset overlay
          dtro:     '#0EA5E9',   // Sky — D-TRO overlay
        },

        // ── Surface ─────────────────────────────────────────────
        surface: {
          page:   '#FAFAFA',   // Page background
          panel:  '#F4F4F5',   // Panel / card background
          raised: '#FFFFFF',   // Elevated card (shadow)
          sunken: '#E4E4E7',   // Input backgrounds
        },

        // ── Line / Divider (NOT 'border' — avoids Tailwind utility clash)
        // ADR-006: use `border-line` for divider colour, `border-2` for width
        line: {
          DEFAULT: '#E4E4E7',   // Standard divider — border-line
          strong:  '#D1D1D6',   // Emphasised divider — border-line-strong
          focus:   '#1E3A5F',   // Focus ring — ring-line-focus
        },

        // ── Text ────────────────────────────────────────────────
        ink: {
          DEFAULT: '#18181B',   // Primary text
          muted:   '#52525B',   // Secondary text / labels
          subtle:  '#A1A1AA',   // Placeholder / disabled
          inverse: '#FFFFFF',   // Text on dark backgrounds
        },
      },

      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },

      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}

export default config

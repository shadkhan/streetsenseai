# DESIGN.md — StreetSense AI Design System
> The single source of truth for all visual and interaction decisions.
> Read this before touching any component, layout, or style.
>
> **Version 1.1** — May 2026
> Pair with `CLAUDE.md` (architecture rules) and `.phase` (current phase pointer).

---

## 1. Design Philosophy

StreetSense AI is a **professional intelligence tool for highways officers**,
not a consumer app. Every design decision prioritises:

1. **Trust over delight** — a highways officer must trust the data before
   they find the UI pleasant. Accuracy signals come before aesthetics.
2. **Data density over whitespace** — permit tables have many columns.
   Do not sacrifice density for breathing room.
3. **Map primacy** — the map is the product. Everything else annotates it.
4. **GOV.UK credibility** — users spend their working day in government
   interfaces. Familiar patterns reduce cognitive load.
5. **AI transparency** — every AI statement must cite its source. A copilot
   that cannot be verified will not be trusted.

### What This Is NOT
- Not a consumer dashboard (no rounded hero cards, no gradient backgrounds)
- Not a dark-mode product (highways officers work in bright offices)
- Not a mobile-first product (permit officers work at desktops)
- Not Causeway's design system (distinct identity — we are a peer, not a clone)

---

## 2. Colour System

### 2.1 Tailwind Config — Complete Token Set

Add this to `tailwind.config.ts` under `theme.extend.colors`:

```typescript
colors: {
  // ── Brand ──────────────────────────────────────────────
  brand: {
    DEFAULT:  '#1E3A5F',   // Slate blue — primary actions, headings
    light:    '#E8EEF5',   // Brand tint — hover states, selected rows
    muted:    '#4A6FA5',   // Secondary brand — links, icons
  },

  // ── Semantic — Risk Levels ──────────────────────────────
  risk: {
    low:           '#059669',   // Emerald — compliant, no issues
    'low-bg':      '#D1FAE5',
    medium:        '#D97706',   // Amber — monitor, review
    'medium-bg':   '#FEF3C7',
    high:          '#EA580C',   // Orange — action required
    'high-bg':     '#FFF7ED',
    critical:      '#DC2626',   // Red — immediate action
    'critical-bg': '#FEE2E2',
  },

  // ── Map Canvas ─────────────────────────────────────────
  map: {
    corridor:   '#F97316',   // Coral — critical corridor highlight
    works:      '#3B82F6',   // Blue — individual works marker
    nuar:       '#8B5CF6',   // Purple — underground asset overlay
    dtro:       '#0EA5E9',   // Sky — D-TRO overlay
  },

  // ── Surface ─────────────────────────────────────────────
  surface: {
    page:    '#FAFAFA',   // Page background
    panel:   '#F4F4F5',   // Panel / card background
    raised:  '#FFFFFF',   // Elevated card (shadow)
    sunken:  '#E4E4E7',   // Input backgrounds
  },

  // ── Line / Divider (NOT 'border' — avoids Tailwind utility clash) ──
  line: {
    DEFAULT: '#E4E4E7',   // Standard divider — use as `border-line`
    strong:  '#D1D1D6',   // Emphasised divider — use as `border-line-strong`
    focus:   '#1E3A5F',   // Focus ring — use as `ring-line-focus`
  },

  // ── Text ────────────────────────────────────────────────
  ink: {
    DEFAULT:  '#18181B',   // Primary text
    muted:    '#52525B',   // Secondary text / labels
    subtle:   '#A1A1AA',   // Placeholder / disabled
    inverse:  '#FFFFFF',   // Text on dark backgrounds
  },
},
```

### 2.2 Why `line` Not `border`

In Tailwind, `border-*` is reserved for border-width utilities
(`border-2`, `border-4`, `border-strong` would be ambiguous).
Naming the colour group `line` lets us write `border-line` (colour) and
`border-2` (width) without conflict.

```tsx
// ✅ Combines width + colour cleanly
<hr className="border-t border-line" />
<div className="border-2 border-line-strong" />
<input className="ring-2 ring-line-focus" />
```

### 2.3 Colour Usage Rules

| Element | Token | Never use |
|---------|-------|-----------|
| Primary buttons | `bg-brand text-ink-inverse` | Hardcoded hex |
| Page background | `bg-surface-page` | `bg-white` or `bg-gray-*` |
| Card / panel | `bg-surface-raised` or `bg-surface-panel` | Custom colours |
| Permit ref numbers | `bg-brand-light text-brand font-mono` | Any other bg |
| Risk: Low | `bg-risk-low-bg text-risk-low` | `bg-green-*` |
| Risk: Medium | `bg-risk-medium-bg text-risk-medium` | `bg-yellow-*` |
| Risk: High | `bg-risk-high-bg text-risk-high` | `bg-orange-*` |
| Risk: Critical | `bg-risk-critical-bg text-risk-critical` | `bg-red-*` |
| Map: critical corridor | `map.corridor` (#F97316) — Mapbox paint only | In CSS |
| Section labels | `text-ink-subtle uppercase tracking-wider text-xs` | Bold labels |
| Body text | `text-ink` | `text-black` or `text-gray-*` |
| Dividers | `border-line` (with `border-t` or `border-b`) | `border-gray-*` |

### 2.4 Do Not Use Default Tailwind Colours Directly
```tsx
// ❌ WRONG — breaks when tokens change
<div className="bg-green-100 text-green-700">Low Risk</div>
<p className="text-gray-500">Secondary text</p>

// ✅ CORRECT — semantic and maintainable
<div className="bg-risk-low-bg text-risk-low">Low Risk</div>
<p className="text-ink-muted">Secondary text</p>
```

---

## 3. Typography

### 3.1 Font Setup

```tsx
// app/layout.tsx
import { Inter, JetBrains_Mono } from 'next/font/google'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
})
```

```typescript
// tailwind.config.ts
fontFamily: {
  sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
  mono: ['var(--font-mono)', 'Menlo', 'monospace'],
},
```

### 3.2 Type Scale

| Use case | Class | Size | Weight |
|----------|-------|------|--------|
| Page title | `text-2xl font-semibold text-brand` | 24px | 600 |
| Section heading | `text-lg font-semibold text-ink` | 18px | 600 |
| Card heading | `text-base font-medium text-ink` | 16px | 500 |
| Body | `text-sm text-ink` | 14px | 400 |
| Secondary text | `text-sm text-ink-muted` | 14px | 400 |
| Label / metadata | `text-xs text-ink-subtle uppercase tracking-wider font-medium` | 12px | 500 |
| Permit reference | `text-xs font-mono text-brand bg-brand-light px-1.5 py-0.5 rounded` | 12px | 400 |
| USRN | `text-xs font-mono text-ink-muted` | 12px | 400 |
| Table header | `text-xs font-medium text-ink-subtle uppercase tracking-wider` | 12px | 500 |
| Table cell | `text-sm text-ink` | 14px | 400 |

### 3.3 The Monospace Rule
**Every permit reference number, USRN code, and data identifier must be
rendered in `font-mono`.** This is non-negotiable. It signals technical
precision to professional users and makes scanning tables dramatically faster.

```tsx
// ✅ Permit reference — always this pattern
<code className="font-mono text-xs bg-brand-light text-brand px-1.5 py-0.5 rounded">
  WG7/2025/04001234
</code>

// ✅ USRN — inline, less prominent
<span className="font-mono text-xs text-ink-muted">41507223</span>
```

---

## 4. Layout System

### 4.1 The Map-Primary Layout (Main Experience)

```
┌─────────────────────────────────────────────────────────────┐
│  Header bar (48px fixed)                                    │
├─────────────────────────────────────────────────────────────┤
│                                          │                  │
│                                          │  Corridor Sheet  │
│          Map Canvas                      │  (right, 420px)  │
│          (full remaining viewport)       │  OR              │
│                                          │  Copilot Sheet   │
│  [Layer toggles — top right]             │  (right, 480px)  │
│  [Risk legend — bottom left]             │                  │
│  [Copilot trigger — bottom right]        │  Never both.     │
│                                          │  See 4.2.        │
└──────────────────────────────────────────┴──────────────────┘
```

```tsx
// The exact layout structure — do not deviate
export default function MapPage() {
  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col">
      <Header className="h-12 flex-shrink-0 z-50" />
      <main className="relative flex-1 overflow-hidden">
        {/* Map always fills the container */}
        <MapCanvas className="absolute inset-0" />

        {/* Floating controls — never obscure corridor names */}
        <LayerControls className="absolute top-4 right-4 z-10" />
        <RiskLegend className="absolute bottom-8 left-4 z-10" />
        <CopilotTrigger className="absolute bottom-8 right-4 z-10" />

        {/* Sheets slide over the map — do not resize map */}
        <CorridorSheet />   {/* shadcn Sheet — right, 420px */}
        <CopilotSheet />    {/* shadcn Sheet — right, 480px */}
      </main>
    </div>
  )
}
```

### 4.2 Sheet Conflict Resolution — Mutual Exclusivity

The Corridor Sheet and Copilot Sheet **never coexist on screen**.
Opening one automatically closes the other. This is enforced via a single
panel state machine in `lib/stores/panels.ts`:

```typescript
// lib/stores/panels.ts
import { create } from 'zustand'

type ActivePanel = 'none' | 'corridor' | 'copilot'

interface PanelState {
  active: ActivePanel
  corridorId: string | null
  openCorridor: (id: string) => void
  openCopilot: () => void
  close: () => void
}

export const usePanels = create<PanelState>((set) => ({
  active: 'none',
  corridorId: null,
  // Opening corridor automatically closes copilot
  openCorridor: (id) => set({ active: 'corridor', corridorId: id }),
  // Opening copilot automatically closes corridor
  openCopilot: () => set({ active: 'copilot', corridorId: null }),
  close: () => set({ active: 'none', corridorId: null }),
}))
```

Both Sheet components subscribe to this store. When the user clicks a
corridor on the map while the copilot is open, the copilot closes
automatically and the corridor sheet opens. The transition is instant —
no animation chaining.

### 4.3 The Analytics Layout (Dashboard Pages)

```
┌──────────────────────────────────────────────────────────────┐
│  Header bar (48px fixed)                                     │
├──────────────────────────────────────────────────────────────┤
│  ← Back to map    [Analytics — Non-Compliance]               │
├──────────────────────────────────────────────────────────────┤
│  Stat cards (3 col)                                          │
├──────────────────────────────────────────────────────────────┤
│  Filter bar (authority, region, date range, promoter)        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  DataTable — full width, sticky header, sortable columns     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 4.4 Spacing Scale — Use Tailwind defaults
- Component internal padding: `p-4` (16px)
- Card gap: `gap-4` (16px)
- Section gap: `gap-6` (24px)
- Page padding: `px-6 py-4`
- Table cell padding: `px-3 py-2`

---

## 5. Core Components

### 5.1 RiskBadge

The most-used component in the entire product.
Build this as a custom component — no library install needed.

```tsx
// components/risk/RiskBadge.tsx
import { cn } from '@/lib/utils'
import type { RiskLevel } from '@/types'
import { RISK_CONFIG } from './risk-config'   // see CLAUDE.md §6.4

interface RiskBadgeProps {
  level: RiskLevel
  showDot?: boolean
  className?: string
}

export function RiskBadge({ level, showDot = true, className }: RiskBadgeProps) {
  const { label, dot, bg, text } = RISK_CONFIG[level]
  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium',
      bg, text, className
    )}>
      {showDot && <span className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', dot)} />}
      {label}
    </span>
  )
}
```

### 5.2 PermitReference

```tsx
// components/ui/PermitReference.tsx
import { cn } from '@/lib/utils'

interface PermitReferenceProps {
  reference: string
  className?: string
}

export function PermitReference({ reference, className }: PermitReferenceProps) {
  return (
    <code className={cn(
      'font-mono text-xs bg-brand-light text-brand px-1.5 py-0.5 rounded',
      'whitespace-nowrap',
      className
    )}>
      {reference}
    </code>
  )
}
```

### 5.3 SectionLabel

```tsx
// Inline — use directly as className pattern, no component needed
<p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-2">
  Concurrent Works
</p>
```

### 5.4 StatCard

Used in the analytics dashboard header row.

```tsx
// components/analytics/StatCard.tsx
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string | number
  delta?: string           // e.g. "+12% vs last month"
  deltaDirection?: 'up' | 'down' | 'neutral'
  className?: string
}

export function StatCard({ label, value, delta, deltaDirection, className }: StatCardProps) {
  return (
    <div className={cn(
      'bg-surface-raised rounded-lg border border-line p-4',
      className
    )}>
      <p className="text-xs font-medium text-ink-subtle uppercase tracking-wider mb-1">
        {label}
      </p>
      <p className="text-2xl font-semibold text-ink tabular-nums">
        {value}
      </p>
      {delta && (
        <p className={cn('text-xs mt-1', {
          'text-risk-low': deltaDirection === 'up',
          'text-risk-critical': deltaDirection === 'down',
          'text-ink-muted': deltaDirection === 'neutral',
        })}>
          {delta}
        </p>
      )}
    </div>
  )
}
```

### 5.5 CopilotMessage

The AI response rendering component. This is the most technically
important component in the product — it determines user trust.

```tsx
// components/copilot/CopilotMessage.tsx
'use client'
import { PermitReference } from '@/components/ui/PermitReference'
import type { CopilotMessage as CopilotMessageType } from '@/types'
import { formatDistanceToNow } from 'date-fns'

interface Props {
  message: CopilotMessageType
  isStreaming?: boolean
}

export function CopilotMessage({ message, isStreaming }: Props) {
  // Render inline permit references in monospace chips
  const renderContent = (content: string) => {
    // Pattern: permit refs like WG7/2025/04001234
    const permitPattern = /([A-Z0-9]+\/\d{4}\/\d+)/g
    const parts = content.split(permitPattern)
    return parts.map((part, i) =>
      permitPattern.test(part)
        ? <PermitReference key={i} reference={part} className="mx-0.5" />
        : <span key={i}>{part}</span>
    )
  }

  return (
    <div className="space-y-3">
      {/* Question bubble */}
      <div className="flex justify-end">
        <div className="bg-surface-panel rounded-lg px-3 py-2 max-w-[85%]">
          <p className="text-sm text-ink">{message.content}</p>
        </div>
      </div>

      {/* AI Response */}
      {message.role === 'assistant' && (
        <div className="space-y-2">
          <div className="text-sm text-ink leading-relaxed">
            {renderContent(message.content)}
            {isStreaming && (
              <span className="inline-block w-0.5 h-4 bg-brand ml-0.5 animate-pulse" />
            )}
          </div>

          {/* Citations */}
          {message.citations.length > 0 && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {message.citations.map((citation) => (
                <PermitReference
                  key={citation.permitReference}
                  reference={citation.permitReference}
                />
              ))}
            </div>
          )}

          {/* Suggested questions — only when not streaming */}
          {!isStreaming && message.suggestedQuestions && (
            <div className="flex flex-wrap gap-1.5 pt-2">
              {message.suggestedQuestions.map((q) => (
                <button
                  key={q}
                  className="text-xs text-brand border border-brand/30 bg-brand-light
                             rounded px-2 py-1 hover:bg-brand hover:text-ink-inverse
                             transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {/* Data source footer — always present */}
          <p className="text-xs text-ink-subtle pt-1 border-t border-line">
            Based on Street Manager data · Updated{' '}
            {formatDistanceToNow(new Date(message.dataTimestamp))} ago
          </p>
        </div>
      )}
    </div>
  )
}
```

---

## 6. Map Design

### 6.1 Base Map — Mapbox Standard + OS Vector Tiles

Use **Mapbox Standard** style (`mapbox://styles/mapbox/standard`) as the
base canvas. **Overlay OS Vector Tiles** for UK road labels and street names —
this gives our map the authoritative UK road labelling that highways
officers expect.

Do not use Mapbox Satellite, Dark, or Navigation styles for the MVP.

#### OS Vector Tiles Setup

```typescript
// components/map/MapCanvas.tsx
'use client'
import { useEffect, useRef } from 'react'
import mapboxgl from 'mapbox-gl'

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN!
const OS_API_KEY = process.env.NEXT_PUBLIC_OS_API_KEY!

export function MapCanvas() {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: 'mapbox://styles/mapbox/standard',
      center: [-2.0, 53.0],     // Centre of England
      zoom: 6,
      maxBounds: [[-8.5, 49.5], [2.0, 60.5]],   // UK bounding box
    })

    map.on('load', () => {
      // OS Vector Tiles — UK road labels overlay
      map.addSource('os-vector', {
        type: 'vector',
        tiles: [
          `https://api.os.uk/maps/vector/v1/vts/tile/{z}/{y}/{x}.pbf?key=${OS_API_KEY}`,
        ],
        minzoom: 7,
        maxzoom: 16,
      })
      map.addLayer({
        id: 'os-road-labels',
        type: 'symbol',
        source: 'os-vector',
        'source-layer': 'roadname',
        layout: {
          'text-field': ['get', 'name'],
          'text-font': ['Inter Medium', 'Arial Unicode MS Regular'],
          'text-size': 11,
        },
        paint: {
          'text-color': '#52525B',          // ink-muted
          'text-halo-color': '#FAFAFA',     // surface-page
          'text-halo-width': 1,
        },
      })

      // Then add corridor + works layers (see 6.2 and 6.3)
    })

    mapRef.current = map
    return () => { map.remove(); mapRef.current = null }
  }, [])

  return <div ref={containerRef} className="absolute inset-0" />
}
```

OS attribution is required — add `© Crown copyright and database rights {year} OS`
to the map's attribution control.

### 6.2 Corridor Overlay — Paint Specification

```javascript
// Corridor heat map — colour by risk level
map.addLayer({
  id: 'corridor-risk',
  type: 'line',
  source: 'corridors',
  paint: {
    'line-color': [
      'match', ['get', 'riskLevel'],
      'low',      '#059669',   // risk.low
      'medium',   '#D97706',   // risk.medium
      'high',     '#EA580C',   // risk.high
      'critical', '#F97316',   // map.corridor (coral — maximum visibility)
      '#A1A1AA'                // fallback — ink.subtle
    ],
    'line-width': [
      'match', ['get', 'riskLevel'],
      'critical', 6,
      'high',     4,
      'medium',   3,
      2           // low + fallback
    ],
    'line-opacity': 0.85,
  }
})
```

### 6.3 Works Marker Style
Individual works are points. Use a circle layer, not symbols.

```javascript
map.addLayer({
  id: 'works-points',
  type: 'circle',
  source: 'works',
  paint: {
    'circle-radius': 6,
    'circle-color': '#3B82F6',      // map.works
    'circle-stroke-width': 2,
    'circle-stroke-color': '#FFFFFF',
    'circle-opacity': 0.9,
  }
})
```

### 6.4 Selected State
When a corridor or works is selected, increase opacity and add a glow:

```javascript
// Selected corridor
'line-color': '#1E3A5F',   // brand
'line-width': 8,
'line-opacity': 1,
```

### 6.5 Layer Order (bottom to top)
1. Mapbox Standard base map
2. OS Vector Tiles road labels (Section 6.1)
3. NUAR underground assets (purple, dashed, low opacity) — Phase 4+
4. D-TRO overlay (sky blue) — Phase 6+
5. Street Manager works corridor heat map
6. Individual works markers (circles)
7. Selected state highlight
8. Floating UI controls (rendered as React DOM, not Mapbox layers)

### 6.6 Floating Controls — Layer Toggle Component

```
┌─────────────────────┐
│ Layers              │
├─────────────────────┤
│ ● Street Manager    │  ← Blue dot = active
│ ○ D-TRO             │  ← Empty = inactive
│ ○ NUAR              │
└─────────────────────┘
```

Implemented as a `<Card>` with `<Switch>` components from shadcn/ui.
Width: `180px`. Positioned: `top-4 right-4`. Background: `bg-white/90
backdrop-blur-sm`.

---

## 7. shadcn/ui Components to Install

Run these commands after `npx shadcn@latest init`:

```bash
npx shadcn@latest add badge
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add command
npx shadcn@latest add dialog
npx shadcn@latest add dropdown-menu
npx shadcn@latest add input
npx shadcn@latest add label
npx shadcn@latest add scroll-area
npx shadcn@latest add select
npx shadcn@latest add separator
npx shadcn@latest add sheet
npx shadcn@latest add skeleton
npx shadcn@latest add switch
npx shadcn@latest add table
npx shadcn@latest add tabs
npx shadcn@latest add tooltip
```

**Sheet** is the most important component in the product.
It powers both the Corridor Panel and the Copilot Panel.

---

## 8. Header Component

The header is 48px tall, sticky, with a left-aligned logo and right-aligned
navigation. It must never exceed 48px — the map needs the space.

```tsx
// components/layout/Header.tsx
import Link from 'next/link'
import { MapIcon } from 'lucide-react'

export function Header() {
  return (
    <header className="h-12 bg-brand border-b border-brand/20 flex items-center
                        px-4 gap-4 flex-shrink-0 z-50">
      {/* Logo */}
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 bg-map-corridor rounded-sm flex items-center
                        justify-center flex-shrink-0">
          <MapIcon className="w-3.5 h-3.5 text-white" />
        </div>
        <span className="text-sm font-semibold text-ink-inverse tracking-tight">
          StreetSense
          <span className="text-map-corridor ml-0.5">AI</span>
        </span>
      </div>

      <div className="w-px h-4 bg-white/20" />

      {/* Nav */}
      <nav className="flex items-center gap-1">
        <Link href="/" className="text-xs text-white/70 hover:text-white
                                   px-2 py-1 rounded hover:bg-white/10
                                   transition-colors">
          Map
        </Link>
        <Link href="/analytics" className="text-xs text-white/70 hover:text-white
                                            px-2 py-1 rounded hover:bg-white/10
                                            transition-colors">
          Analytics
        </Link>
      </nav>

      <div className="ml-auto flex items-center gap-2">
        <span className="text-xs text-white/50 font-mono">
          Street Manager · Live
        </span>
        <div className="w-1.5 h-1.5 rounded-full bg-risk-low animate-pulse" />
      </div>
    </header>
  )
}
```

---

## 9. Interaction Principles

### The Three Rules — Every Screen Must Follow These

**Rule 1: The map always has at least 60% of the viewport.**
Sheets slide over the map — they do not shrink it. Use `position: absolute`
and `z-index` for all panels. Never use a CSS grid that reduces the map's
allocated space.

**Rule 2: Every AI response cites a permit reference number.**
If the AI cannot cite a specific permit, it should not make a specific claim.
The copilot system prompt must enforce this at the LLM level.

**Rule 3: No action takes more than one click from the map canvas.**
Corridor detail panel: one click on the corridor.
Copilot: one click on the trigger button.
Layer toggle: one click on the switch.
If it takes two clicks, redesign it.

### Hover States
- Table rows: `hover:bg-surface-panel` (subtle, not coloured)
- Buttons: lighten brand by 10% or darken surface
- Map features: `cursor: pointer` + opacity increase to 1.0
- Permit references: no hover state — they are non-interactive by default

### Loading States
- Map data loading: skeleton pulse on the corridor layer (Mapbox paint opacity 0.3)
- Table loading: shadcn Skeleton rows — 5 rows, same column structure as data
- Copilot generating: blinking cursor `animate-pulse` on last character
- **Never use a spinning loader** — it implies the system is slow
- **Never use skeleton on the map canvas itself** — show an empty map

### Empty States
- No works in a corridor: "No active or planned works in this corridor for the selected period."
- No results in table: "No promoters match the current filters."
- Copilot no data: "No Street Manager data found for that location and period."
- Keep empty state text factual — no illustrations, no emojis

---

## 10. v0.dev Prompt Templates

Use these prompts to generate specific components. Generate, paste into
codebase, then restyle with your Tailwind tokens.

### Corridor Risk Table Row
```
Create a React table row component for a street works data table using
Tailwind CSS. The row contains: a permit reference number in monospace
font (small, slate blue background chip), a street name in regular font,
a promoter company name in muted text, a restriction type as a small
grey outlined chip, start and end dates in tabular numbers, and a risk
badge (dot + label, coloured by level: green/amber/orange-red/red).
The row has a subtle hover background. Columns are left-aligned.
Design is minimal — no card shadows, just a 1px bottom border between rows.
```

### Non-Compliance Stat Row
```
Create a React component for a promoter compliance row in a non-compliance
analytics table. Shows: rank number (1, 2, 3), company name in bold, a
horizontal progress bar showing overrun rate (0-100%), three small metric
chips showing overrun rate %, late start rate %, and missing reinstatement
rate %, and a trend indicator (up/down/flat arrow with colour). The overall
compliance score is shown as a large number on the right. Dense layout —
this sits in a full-width table with many rows. Use Tailwind only.
```

### Copilot Input Bar
```
Create a React command-palette style input component for an AI copilot
using Tailwind. It has a search/chat icon on the left, placeholder text
"Ask about any road or corridor...", a keyboard shortcut badge showing
"/" on the right, and a subtle border. When focused, the border becomes
a slate blue colour. Below the input, show 3 suggested question buttons
as small outlined chips: "What's happening on the A38 this month?",
"Which promoters have the most overruns?", "Show me critical corridors
in Birmingham". The whole component has a white background with a
slight drop shadow.
```

---

## 11. What We Deliberately Did Not Build

These are explicit out-of-scope decisions. Do not add them unless the
current phase spec says to.

| Feature | Reason Not Built |
|---------|-----------------|
| Dark mode | Highways officers work in bright offices; doubles CSS complexity |
| Mobile layout | Desktop-only tool for permit officers; mobile is Phase 3+ |
| Animations on tables | Data density matters more than motion |
| Onboarding flow | No auth in Phase 1–5; public tool needs no onboarding |
| User accounts / login | Phase 6 only |
| Export to PDF in Phase 1 | Phase 5 feature |
| Custom map style | Mapbox Standard is sufficient; custom style = weeks of work |
| Internationalisation | English-only; Welsh language support is a future consideration |
| Accessibility audit | Tailwind + shadcn provides WCAG AA baseline; full audit is Phase 6 |
| `status.*` token group | Risk tokens cover all states; no separate status colours needed |

---

## 12. Reference Products — Visual North Stars

Study these products before building each major component:

| What to study | Where to look | What to take |
|---------------|---------------|--------------|
| Status badges, warning callouts | design-system.service.gov.uk | Colour meaning conventions |
| Map-as-primary-canvas | felt.com | Layout, panel slide-in, layer controls |
| Dense data tables | linear.app/projects | Typography, row density, status dots |
| AI citation pattern | perplexity.ai | Inline source references, streaming |
| Floating map controls | mapbox.com/showcase | Control panel positioning, opacity |
| Stat cards | vercel.com/dashboard | Minimal stat display, delta indicators |

---

## 13. Changelog

**v1.1 — May 2026**
- Renamed `border` token group to `line` to avoid Tailwind utility-class clash
  (use `border-line` for divider colour, `border-2` for width — they no longer collide)
- Removed `status.*` token group (was unused; risk tokens cover all states)
- Added Section 4.2: Sheet Conflict Resolution with full Zustand state machine
- Added Section 6.1: complete OS Vector Tiles setup code with attribution
- Updated all `border-DEFAULT` references in code samples to `border-line`
- Added Section 11 entry documenting `status.*` removal
- Updated RiskBadge sample to import shared `RISK_CONFIG` from CLAUDE.md §6.4

**v1.0 — May 2026** — Initial version

---

*DESIGN.md is a living document. When a visual decision is made that is not
covered here, add it here immediately so the next session inherits it.*
*Last updated: May 2026 | Version: 1.1*

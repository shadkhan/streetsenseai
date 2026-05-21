'use client'

import { useMapStore } from '@/lib/stores/map'
import type { MapStyle } from '@/lib/stores/map'
import { Hint } from '@/components/ui/Hint'
import { cn } from '@/lib/utils'

const STYLES: Array<{ value: MapStyle; label: string; hint: string }> = [
  { value: 'streets',   label: 'Streets',   hint: 'Standard street map with 3D buildings and rich labels' },
  { value: 'dark',      label: 'Dark',      hint: 'Dark basemap — better contrast for risk overlays at night or on external displays' },
  { value: 'satellite', label: 'Satellite', hint: 'Satellite imagery with street labels — useful for ground-level context at high zoom' },
]

export function MapStyleControl() {
  const { mapStyle, setMapStyle, is3D, setIs3D, showDtro, setShowDtro } = useMapStore()

  return (
    <div className="flex flex-col gap-2">
      {/* Style switcher */}
      <div className="bg-white/95 backdrop-blur-sm rounded-lg shadow-md border border-line overflow-hidden">
        {STYLES.map(({ value, label, hint }) => (
          <Hint key={value} text={hint} side="right" delayDuration={400}>
            <button
              onClick={() => setMapStyle(value)}
              aria-pressed={mapStyle === value}
              className={cn(
                'block w-full text-left px-3 py-1.5 text-xs font-medium transition-colors',
                mapStyle === value
                  ? 'bg-brand text-ink-inverse'
                  : 'text-ink-muted hover:bg-surface-panel hover:text-ink',
              )}
            >
              {label}
            </button>
          </Hint>
        ))}
      </div>

      {/* 2D / 3D toggle */}
      <Hint
        text={is3D ? 'Switch to flat 2D view' : 'Switch to 3D perspective view with building extrusions'}
        side="right"
        delayDuration={400}
      >
        <button
          onClick={() => setIs3D(!is3D)}
          aria-pressed={is3D}
          className={cn(
            'bg-white/95 backdrop-blur-sm rounded-lg shadow-md border border-line',
            'px-3 py-1.5 text-xs font-semibold transition-colors',
            is3D
              ? 'bg-brand text-ink-inverse border-brand'
              : 'text-ink-muted hover:text-ink',
          )}
        >
          {is3D ? '3D' : '2D'}
        </button>
      </Hint>

      {/* D-TRO layer toggle (DT-003) */}
      <Hint
        text={showDtro ? 'Hide D-TRO restriction boundaries' : 'Show D-TRO traffic regulation order boundaries (dashed blue lines)'}
        side="right"
        delayDuration={400}
      >
        <button
          onClick={() => setShowDtro(!showDtro)}
          aria-pressed={showDtro}
          className={cn(
            'bg-white/95 backdrop-blur-sm rounded-lg shadow-md border border-line',
            'px-3 py-1.5 text-xs font-semibold transition-colors',
            showDtro
              ? 'bg-[#0EA5E9] text-white border-[#0EA5E9]'
              : 'text-ink-muted hover:text-ink',
          )}
        >
          D-TRO
        </button>
      </Hint>
    </div>
  )
}

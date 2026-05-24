'use client'

import { useState, useEffect, useRef } from 'react'
import { Search, X, MapPin } from 'lucide-react'
import { useMapStore } from '@/lib/stores/map'
import { cn } from '@/lib/utils'

interface GeocodingFeature {
  id: string
  place_name: string
  place_type: string[]
  center: [number, number]
  text: string
}

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState<T>(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return debounced
}

export function MapSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<GeocodingFeature[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  const { setFlyTarget } = useMapStore()
  const debouncedQuery = useDebounce(query.trim(), 300)

  // Fetch geocoding suggestions
  useEffect(() => {
    if (debouncedQuery.length < 2) {
      setResults([])
      setOpen(false)
      return
    }

    const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN
    if (!token) return

    let cancelled = false
    setLoading(true)

    fetch(
      `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(debouncedQuery)}.json` +
      `?access_token=${token}&country=gb&limit=6&types=place,locality,district,postcode,address`,
    )
      .then((r) => r.json())
      .then((data) => {
        if (cancelled) return
        setResults(data.features ?? [])
        setOpen(true)
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [debouncedQuery])

  // Close dropdown on outside click
  useEffect(() => {
    function onMouseDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onMouseDown)
    return () => document.removeEventListener('mousedown', onMouseDown)
  }, [])

  function handleSelect(feature: GeocodingFeature) {
    setFlyTarget(feature.center)
    setQuery(feature.text)
    setOpen(false)
  }

  function clear() {
    setQuery('')
    setResults([])
    setOpen(false)
    inputRef.current?.focus()
  }

  const showDropdown = open && results.length > 0

  return (
    <div ref={containerRef} className="relative w-48 sm:w-64">
      {/* Input row */}
      <div
        className={cn(
          'flex items-center gap-2 bg-white/95 backdrop-blur-sm shadow-lg border border-line px-3 h-9 transition-all',
          showDropdown ? 'rounded-t-lg rounded-b-none border-b-surface-sunken' : 'rounded-lg',
        )}
      >
        {loading ? (
          <span className="w-3.5 h-3.5 rounded-full border border-ink-subtle border-t-transparent animate-spin shrink-0" />
        ) : (
          <Search className="h-3.5 w-3.5 text-ink-subtle shrink-0" />
        )}
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => results.length > 0 && setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') { setOpen(false); inputRef.current?.blur() }
          }}
          placeholder="Search UK locations…"
          aria-label="Search for a location in the UK"
          className="flex-1 min-w-0 bg-transparent text-xs text-ink placeholder:text-ink-subtle outline-none"
        />
        {query && (
          <button
            onClick={clear}
            aria-label="Clear search"
            className="text-ink-subtle hover:text-ink transition-colors shrink-0"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>

      {/* Results dropdown */}
      {showDropdown && (
        <ul
          role="listbox"
          className="absolute top-full left-0 right-0 bg-white/97 backdrop-blur-sm border border-line border-t-0 rounded-b-lg shadow-lg overflow-hidden z-50 max-h-64 overflow-y-auto"
        >
          {results.map((feature) => {
            // Strip the feature name from the full place_name to get context only
            const context = feature.place_name.startsWith(feature.text)
              ? feature.place_name.slice(feature.text.length).replace(/^,\s*/, '')
              : feature.place_name

            return (
              <li key={feature.id} role="option">
                <button
                  onClick={() => handleSelect(feature)}
                  className="w-full flex items-start gap-2.5 px-3 py-2.5 text-left hover:bg-surface-panel transition-colors group"
                >
                  <MapPin className="h-3.5 w-3.5 text-ink-subtle group-hover:text-brand shrink-0 mt-0.5 transition-colors" />
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-ink leading-tight truncate">
                      {feature.text}
                    </p>
                    {context && (
                      <p className="text-[10px] text-ink-subtle truncate mt-0.5">{context}</p>
                    )}
                  </div>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

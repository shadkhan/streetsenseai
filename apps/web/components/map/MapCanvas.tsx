'use client'

import { useEffect, useRef } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import type { FeatureCollection, Feature } from 'geojson'
import { useCorridors } from '@/lib/api'
import { useMapStore } from '@/lib/stores/map'
import { usePanels } from '@/lib/stores/panels'
import type { Corridor } from '@/types'

const SOURCE_ID = 'corridors'
const LAYER_LINES = 'corridor-lines'
const LAYER_LABELS = 'corridor-labels'
const LAYER_HIT = 'corridor-hit'  // wide transparent layer for easier click targeting

const RISK_COLORS: Record<string, string> = {
  low: '#059669', medium: '#D97706', high: '#EA580C', critical: '#DC2626',
}

function buildGeoJSON(corridors: Corridor[]): FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: corridors.map((c): Feature => ({
      type: 'Feature',
      properties: {
        id: c.id,
        name: c.name,
        riskLevel: c.riskLevel,
        riskScore: c.riskScore,
        activeWorksCount: c.activeWorksCount,
      },
      geometry: {
        type: 'LineString',
        coordinates: c.geometry.coordinates as number[][],
      },
    })),
  }
}

export function MapCanvas() {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)

  const { center, zoom, setViewport, timeWindow } = useMapStore()
  const { openCorridor } = usePanels()
  const { data: corridors = [] } = useCorridors(timeWindow)

  // Initialise map once on mount
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN
    if (!token) return  // Map renders placeholder when token is absent

    mapboxgl.accessToken = token

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center,
      zoom,
      attributionControl: false,
    })

    map.addControl(
      new mapboxgl.AttributionControl({ compact: true }),
      'bottom-right',
    )
    map.addControl(
      new mapboxgl.NavigationControl({ showCompass: false }),
      'top-right',
    )

    map.on('moveend', () => {
      const c = map.getCenter()
      setViewport([c.lng, c.lat], map.getZoom())
    })

    map.on('load', () => {
      map.addSource(SOURCE_ID, {
        type: 'geojson',
        data: buildGeoJSON([]),
        promoteId: 'id',
      })

      // Coloured lines — width increases on hover via feature state
      map.addLayer({
        id: LAYER_LINES,
        type: 'line',
        source: SOURCE_ID,
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: {
          'line-color': [
            'match',
            ['get', 'riskLevel'],
            'low',      '#059669',
            'medium',   '#D97706',
            'high',     '#EA580C',
            'critical', '#DC2626',
            '#94A3B8',
          ],
          'line-width': [
            'case',
            ['boolean', ['feature-state', 'hover'], false],
            7,
            4,
          ],
          'line-opacity': 0.88,
        },
      })

      // Wider transparent layer for hit-testing — easier to click thin lines
      map.addLayer({
        id: LAYER_HIT,
        type: 'line',
        source: SOURCE_ID,
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: { 'line-color': 'transparent', 'line-width': 20 },
      })

      // Corridor name labels placed along the line
      map.addLayer({
        id: LAYER_LABELS,
        type: 'symbol',
        source: SOURCE_ID,
        layout: {
          'text-field': ['get', 'name'],
          'text-font': ['DIN Pro Medium', 'Arial Unicode MS Regular'],
          'text-size': 11,
          'symbol-placement': 'line',
          'text-offset': [0, -1],
          'text-allow-overlap': false,
          'text-ignore-placement': false,
        },
        paint: {
          'text-color': '#18181B',
          'text-halo-color': '#FFFFFF',
          'text-halo-width': 2,
          'text-opacity': 0.9,
        },
      })
    })

    // Hover tooltip
    const popup = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
      maxWidth: '240px',
      offset: 8,
    })

    let hoveredId: string | number | null = null

    map.on('mousemove', LAYER_HIT, (e) => {
      if (!e.features?.length) return
      map.getCanvas().style.cursor = 'pointer'

      const feature = e.features[0]
      const id = feature.id

      // Update hover highlight when moving to a new corridor
      if (id !== hoveredId && id != null) {
        if (hoveredId != null) {
          map.setFeatureState({ source: SOURCE_ID, id: hoveredId }, { hover: false })
        }
        hoveredId = id
        map.setFeatureState({ source: SOURCE_ID, id: hoveredId }, { hover: true })
      }

      // Always update popup position and content
      if (id != null) {
        const p = feature.properties as {
          name: string
          riskLevel: string | null
          riskScore: number | null
          activeWorksCount: number
        }
        const color = p.riskLevel ? (RISK_COLORS[p.riskLevel] ?? '#94A3B8') : '#94A3B8'
        const riskLabel = p.riskLevel
          ? p.riskLevel.charAt(0).toUpperCase() + p.riskLevel.slice(1)
          : 'Unscored'
        const scoreStr = p.riskScore != null ? ` · ${Math.round(p.riskScore)}/100` : ''
        const worksStr = p.activeWorksCount > 0
          ? `${p.activeWorksCount} active work${p.activeWorksCount !== 1 ? 's' : ''} nearby`
          : 'No active works'

        popup
          .setLngLat(e.lngLat)
          .setHTML(
            `<span class="ss-popup-name">${p.name}</span>` +
            `<div class="ss-popup-risk">` +
            `<span class="ss-popup-dot" style="background:${color}"></span>` +
            `${riskLabel} risk${scoreStr}` +
            `</div>` +
            `<div class="ss-popup-meta">${worksStr} · click for details</div>`
          )
          .addTo(map)
      }
    })

    map.on('mouseleave', LAYER_HIT, () => {
      map.getCanvas().style.cursor = ''
      if (hoveredId != null) {
        map.setFeatureState({ source: SOURCE_ID, id: hoveredId }, { hover: false })
        hoveredId = null
      }
      popup.remove()
    })

    // Click → open corridor detail Sheet (CR-006 will render the content)
    map.on('click', LAYER_HIT, (e) => {
      const id = e.features?.[0]?.properties?.id
      if (typeof id === 'string') openCorridor(id)
    })

    mapRef.current = map

    return () => {
      popup.remove()
      map.remove()
      mapRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Keep corridor source data in sync with query results
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    const update = () => {
      const source = map.getSource(SOURCE_ID) as mapboxgl.GeoJSONSource | undefined
      source?.setData(buildGeoJSON(corridors))
    }

    if (map.isStyleLoaded()) {
      update()
    } else {
      map.once('load', update)
    }
  }, [corridors])

  const hasToken = Boolean(process.env.NEXT_PUBLIC_MAPBOX_TOKEN)

  return (
    <div className="absolute inset-0">
      <div ref={containerRef} className="w-full h-full" />
      {!hasToken && (
        <div className="absolute inset-0 flex items-center justify-center bg-surface-panel">
          <div className="text-center space-y-2">
            <p className="text-sm font-medium text-ink">Map not configured</p>
            <p className="text-xs text-ink-muted">
              Add{' '}
              <span className="font-mono">NEXT_PUBLIC_MAPBOX_TOKEN</span>
              {' '}to{' '}
              <span className="font-mono">.env.local</span>
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

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
const LAYER_HIT = 'corridor-hit'  // wide transparent layer for easier click targeting

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
    })

    // Hover state tracking
    let hoveredId: string | number | null = null

    map.on('mousemove', LAYER_HIT, (e) => {
      if (!e.features?.length) return
      map.getCanvas().style.cursor = 'pointer'
      const id = e.features[0].id
      if (id === hoveredId || id == null) return
      if (hoveredId != null) {
        map.setFeatureState({ source: SOURCE_ID, id: hoveredId }, { hover: false })
      }
      hoveredId = id
      map.setFeatureState({ source: SOURCE_ID, id: hoveredId }, { hover: true })
    })

    map.on('mouseleave', LAYER_HIT, () => {
      map.getCanvas().style.cursor = ''
      if (hoveredId != null) {
        map.setFeatureState({ source: SOURCE_ID, id: hoveredId }, { hover: false })
        hoveredId = null
      }
    })

    // Click → open corridor detail Sheet (CR-006 will render the content)
    map.on('click', LAYER_HIT, (e) => {
      const id = e.features?.[0]?.properties?.id
      if (typeof id === 'string') openCorridor(id)
    })

    mapRef.current = map

    return () => {
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

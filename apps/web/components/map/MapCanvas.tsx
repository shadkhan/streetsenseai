'use client'

import { useEffect, useRef } from 'react'
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css'
import type { FeatureCollection, Feature } from 'geojson'
import { useCorridors, useDTROsGeoJSON } from '@/lib/api'
import { useMapStore, MAP_STYLE_URLS } from '@/lib/stores/map'
import { usePanels } from '@/lib/stores/panels'
import type { Corridor } from '@/types'

const SOURCE_ID  = 'corridors'
const DTRO_SOURCE_ID = 'dtros'
const DTRO_LINE_LAYER_ID   = 'dtro-line'          // LineString TROs (speed limits, closures, etc.)
const DTRO_FILL_LAYER_ID   = 'dtro-fill'          // Polygon TROs (parking zones, bus lanes, etc.)
const DTRO_BORDER_LAYER_ID = 'dtro-fill-outline'  // Outline for polygon zones
const DTRO_ALL_LAYERS = [DTRO_LINE_LAYER_ID, DTRO_FILL_LAYER_ID, DTRO_BORDER_LAYER_ID] as const
const LAYER_GLOW   = 'corridor-glow'   // outer glow for high/critical
const LAYER_LINES  = 'corridor-lines'
const LAYER_LABELS = 'corridor-labels'
const LAYER_HIT    = 'corridor-hit'    // wide transparent hit target

const TRO_TYPE_LABELS: Record<string, string> = {
  speedLimit:         'Speed Limit',
  parkingRestriction: 'Parking Restriction',
  roadClosure:        'Road Closure',
  busLane:            'Bus Lane',
  cycleLane:          'Cycle Lane',
  weightRestriction:  'Weight Restriction',
  oneWay:             'One Way',
  turningProhibition: 'Turning Prohibition',
  pedestrianZone:     'Pedestrian Zone',
}

const RISK_COLORS: Record<string, string> = {
  low: '#1A9E62', medium: '#B5680A', high: '#CC470D', critical: '#BE2222',
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

function addDTROLayer(map: mapboxgl.Map) {
  if (!map.getSource(DTRO_SOURCE_ID)) {
    map.addSource(DTRO_SOURCE_ID, {
      type: 'geojson',
      data: { type: 'FeatureCollection', features: [] },
    })
  }

  // Dashed lines for linear TROs (speed limits, road closures, weight restrictions, etc.)
  if (!map.getLayer(DTRO_LINE_LAYER_ID)) {
    map.addLayer({
      id: DTRO_LINE_LAYER_ID,
      type: 'line',
      source: DTRO_SOURCE_ID,
      filter: ['==', ['geometry-type'], 'LineString'],
      layout: { 'line-join': 'round', 'line-cap': 'round', 'visibility': 'none' },
      paint: {
        'line-color': [
          'match', ['get', 'troType'],
          'speedLimit',         '#EF4444',
          'roadClosure',        '#B91C1C',
          'weightRestriction',  '#F97316',
          'oneWay',             '#0D9488',
          'turningProhibition', '#CA8A04',
          '#0EA5E9',
        ],
        'line-width': 3.5,
        'line-dasharray': [5, 3],
        'line-opacity': 0.9,
      },
    })
  }

  // Filled zones for area TROs (parking, bus lanes, cycle lanes, pedestrian zones)
  if (!map.getLayer(DTRO_FILL_LAYER_ID)) {
    map.addLayer({
      id: DTRO_FILL_LAYER_ID,
      type: 'fill',
      source: DTRO_SOURCE_ID,
      filter: ['==', ['geometry-type'], 'Polygon'],
      layout: { 'visibility': 'none' },
      paint: {
        'fill-color': [
          'match', ['get', 'troType'],
          'parkingRestriction', '#F59E0B',
          'pedestrianZone',     '#10B981',
          'busLane',            '#8B5CF6',
          'cycleLane',          '#3B82F6',
          '#0EA5E9',
        ],
        'fill-opacity': 0.3,
      },
    })
  }

  // Zone outlines
  if (!map.getLayer(DTRO_BORDER_LAYER_ID)) {
    map.addLayer({
      id: DTRO_BORDER_LAYER_ID,
      type: 'line',
      source: DTRO_SOURCE_ID,
      filter: ['==', ['geometry-type'], 'Polygon'],
      layout: { 'line-join': 'round', 'visibility': 'none' },
      paint: {
        'line-color': [
          'match', ['get', 'troType'],
          'parkingRestriction', '#D97706',
          'pedestrianZone',     '#059669',
          'busLane',            '#7C3AED',
          'cycleLane',          '#2563EB',
          '#0EA5E9',
        ],
        'line-width': 1.5,
        'line-opacity': 0.75,
      },
    })
  }
}

function addCorridorLayers(map: mapboxgl.Map, corridors: Corridor[]) {
  // Fog / atmosphere
  map.setFog({
    color: 'rgb(220, 230, 240)',
    'high-color': 'rgb(180, 200, 230)',
    'horizon-blend': 0.05,
    'space-color': 'rgb(120, 150, 200)',
    'star-intensity': 0.0,
  })

  // 3D buildings — insert behind the flat building layer when available
  if (map.getLayer('building') && !map.getLayer('ss-3d-buildings')) {
    map.addLayer(
      {
        id: 'ss-3d-buildings',
        source: 'composite',
        'source-layer': 'building',
        filter: ['==', 'extrude', 'true'],
        type: 'fill-extrusion',
        minzoom: 13,
        paint: {
          'fill-extrusion-color': '#C8D0DC',
          'fill-extrusion-height': ['interpolate', ['linear'], ['zoom'], 13, 0, 13.5, ['get', 'height']],
          'fill-extrusion-base':   ['interpolate', ['linear'], ['zoom'], 13, 0, 13.5, ['get', 'min_height']],
          'fill-extrusion-opacity': 0.55,
        },
      },
      'building',
    )
  }

  // Corridor source
  if (!map.getSource(SOURCE_ID)) {
    map.addSource(SOURCE_ID, {
      type: 'geojson',
      data: buildGeoJSON(corridors),
      promoteId: 'id',
    })
  } else {
    ;(map.getSource(SOURCE_ID) as mapboxgl.GeoJSONSource).setData(buildGeoJSON(corridors))
  }

  // Glow halo — high/critical only
  if (!map.getLayer(LAYER_GLOW)) {
    map.addLayer({
      id: LAYER_GLOW,
      type: 'line',
      source: SOURCE_ID,
      filter: ['in', ['get', 'riskLevel'], ['literal', ['high', 'critical']]],
      layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: {
        'line-color': ['match', ['get', 'riskLevel'], 'critical', '#BE2222', '#CC470D'],
        'line-width': 18,
        'line-opacity': 0.18,
        'line-blur': 6,
      },
    })
  }

  // Corridor lines — active-work corridors get a bolder stroke
  if (!map.getLayer(LAYER_LINES)) {
    map.addLayer({
      id: LAYER_LINES,
      type: 'line',
      source: SOURCE_ID,
      layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: {
        'line-color': [
          'match', ['get', 'riskLevel'],
          'low',      '#1A9E62',
          'medium',   '#B5680A',
          'high',     '#CC470D',
          'critical', '#BE2222',
          '#94A3B8',
        ],
        'line-width': [
          'case',
          ['boolean', ['feature-state', 'hover'], false], 8,
          ['>', ['get', 'activeWorksCount'], 0], 6,
          4,
        ],
        'line-opacity': 0.95,
      },
    })
  }

  // Hit target
  if (!map.getLayer(LAYER_HIT)) {
    map.addLayer({
      id: LAYER_HIT,
      type: 'line',
      source: SOURCE_ID,
      layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: { 'line-color': 'transparent', 'line-width': 20 },
    })
  }

  // Labels
  if (!map.getLayer(LAYER_LABELS)) {
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
        'text-color': '#FFFFFF',
        'text-halo-color': 'rgba(0,0,0,0.75)',
        'text-halo-width': 1.5,
        'text-opacity': 0.95,
      },
    })
  }
}

export function MapCanvas() {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const currentStyleRef = useRef<string>('')

  const { center, zoom, setViewport, timeWindow, mapStyle, is3D, showDtro, flyTarget } = useMapStore()
  const { openCorridor, openDtro } = usePanels()
  const { data: corridors = [] } = useCorridors(timeWindow)
  // Wide UK bbox — server filters spatially within this window
  const uкBbox: [number, number, number, number] = [-5.5, 49.5, 2.0, 55.5]
  const { data: dtroGeoJSON } = useDTROsGeoJSON(uкBbox, showDtro)

  // Live refs so style.load callback always reads the latest values after a style swap
  const corridorsRef = useRef<Corridor[]>(corridors)
  const showDtroRef = useRef<boolean>(showDtro)
  const dtroGeoJSONRef = useRef<typeof dtroGeoJSON>(dtroGeoJSON)
  useEffect(() => { corridorsRef.current = corridors }, [corridors])
  useEffect(() => { showDtroRef.current = showDtro }, [showDtro])
  useEffect(() => { dtroGeoJSONRef.current = dtroGeoJSON }, [dtroGeoJSON])

  // Initialise map once on mount
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    const token = process.env.NEXT_PUBLIC_MAPBOX_TOKEN
    if (!token) return

    mapboxgl.accessToken = token
    const initialStyle = MAP_STYLE_URLS[mapStyle]
    currentStyleRef.current = initialStyle

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: initialStyle,
      center,
      zoom,
      pitch: is3D ? 45 : 0,
      bearing: -10,
      antialias: true,
      attributionControl: false,
    })

    map.addControl(new mapboxgl.AttributionControl({ compact: true }), 'bottom-right')
    map.addControl(new mapboxgl.NavigationControl({ showCompass: true }), 'top-right')

    map.on('moveend', () => {
      const c = map.getCenter()
      setViewport([c.lng, c.lat], map.getZoom())
    })

    // style.load fires on initial load AND after each setStyle() — single handler for both
    map.on('style.load', () => {
      addCorridorLayers(map, corridorsRef.current)
      addDTROLayer(map)
      // Sync D-TRO visibility and data — critical after a style swap resets all layers
      const vis = showDtroRef.current ? 'visible' : 'none'
      for (const layerId of DTRO_ALL_LAYERS) {
        if (map.getLayer(layerId)) map.setLayoutProperty(layerId, 'visibility', vis)
      }
      const dtroData = dtroGeoJSONRef.current
      if (dtroData) {
        ;(map.getSource(DTRO_SOURCE_ID) as mapboxgl.GeoJSONSource)?.setData(
          dtroData as Parameters<mapboxgl.GeoJSONSource['setData']>[0],
        )
      }
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

      if (id !== hoveredId && id != null) {
        if (hoveredId != null) {
          map.setFeatureState({ source: SOURCE_ID, id: hoveredId }, { hover: false })
        }
        hoveredId = id
        map.setFeatureState({ source: SOURCE_ID, id: hoveredId }, { hover: true })
      }

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
            `<div class="ss-popup-meta">${worksStr} · click for details</div>`,
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

    map.on('click', LAYER_HIT, (e) => {
      const id = e.features?.[0]?.properties?.id
      if (typeof id === 'string') openCorridor(id)
    })

    // D-TRO hover popup
    const dtroPopup = new mapboxgl.Popup({
      closeButton: false,
      closeOnClick: false,
      maxWidth: '260px',
      offset: 8,
    })

    const dtroInteractiveLayers = [DTRO_LINE_LAYER_ID, DTRO_FILL_LAYER_ID] as const

    dtroInteractiveLayers.forEach((layerId) => {
      map.on('mousemove', layerId, (e) => {
        if (!e.features?.length) return
        map.getCanvas().style.cursor = 'pointer'
        const p = e.features[0].properties as {
          troType: string
          authority: string
          referenceNumber: string
          isTemporary: boolean
          validFrom: string | null
          validTo: string | null
        }
        const typeLabel = TRO_TYPE_LABELS[p.troType] ?? p.troType
        const ttroTag = p.isTemporary
          ? ' <span style="background:#FEF3C7;color:#92400E;padding:1px 5px;border-radius:3px;font-size:10px">TTRO</span>'
          : ''
        const validity = p.validTo
          ? `${p.validFrom ?? '—'} → ${p.validTo}`
          : `From ${p.validFrom ?? '—'} · Permanent`

        dtroPopup
          .setLngLat(e.lngLat)
          .setHTML(
            `<span class="ss-popup-name">${typeLabel}${ttroTag}</span>` +
            `<div class="ss-popup-meta">${p.authority}</div>` +
            `<div class="ss-popup-meta" style="font-family:monospace;font-size:10px">${p.referenceNumber}</div>` +
            `<div class="ss-popup-meta">${validity}</div>` +
            `<div class="ss-popup-meta" style="margin-top:4px;opacity:0.7">click for details</div>`,
          )
          .addTo(map)
      })

      map.on('mouseleave', layerId, () => {
        map.getCanvas().style.cursor = ''
        dtroPopup.remove()
      })

      map.on('click', layerId, (e) => {
        const dtroId = e.features?.[0]?.properties?.dtroId
        if (typeof dtroId === 'string') openDtro(dtroId)
      })
    })

    mapRef.current = map

    return () => {
      popup.remove()
      dtroPopup.remove()
      map.remove()
      mapRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Sync corridor data to live source (without style swap)
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return
    const source = map.getSource(SOURCE_ID) as mapboxgl.GeoJSONSource | undefined
    source?.setData(buildGeoJSON(corridors))
  }, [corridors])

  // Sync D-TRO GeoJSON data to map source (DT-003)
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return
    const source = map.getSource(DTRO_SOURCE_ID) as mapboxgl.GeoJSONSource | undefined
    if (!source) return
    if (dtroGeoJSON) {
      source.setData(dtroGeoJSON as Parameters<typeof source.setData>[0])
    }
  }, [dtroGeoJSON])

  // Toggle D-TRO layer visibility (DT-003)
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return
    const vis = showDtro ? 'visible' : 'none'
    for (const layerId of DTRO_ALL_LAYERS) {
      if (map.getLayer(layerId)) map.setLayoutProperty(layerId, 'visibility', vis)
    }
  }, [showDtro])

  // Swap basemap style
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const nextUrl = MAP_STYLE_URLS[mapStyle]
    if (currentStyleRef.current === nextUrl) return
    currentStyleRef.current = nextUrl
    map.setStyle(nextUrl)
    // Layers are re-added by the style.load handler above
  }, [mapStyle])

  // Toggle 3D / 2D pitch
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    map.easeTo({ pitch: is3D ? 45 : 0, duration: 600 })
  }, [is3D])

  // Fly to search result
  useEffect(() => {
    const map = mapRef.current
    if (!map || !flyTarget) return
    map.flyTo({ center: flyTarget, zoom: 13, duration: 1800, essential: true })
  }, [flyTarget])

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

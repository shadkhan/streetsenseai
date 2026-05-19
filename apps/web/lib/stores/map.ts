import { create } from 'zustand'

export interface TimeWindow {
  label: string
  startDate: string   // YYYY-MM-DD
  endDate: string     // YYYY-MM-DD
}

export type MapStyle = 'streets' | 'dark' | 'satellite'

export const MAP_STYLE_URLS: Record<MapStyle, string> = {
  streets:   'mapbox://styles/mapbox/streets-v12',
  dark:      'mapbox://styles/mapbox/dark-v11',
  satellite: 'mapbox://styles/mapbox/satellite-streets-v12',
}

interface MapState {
  center: [number, number]
  zoom: number
  setViewport: (center: [number, number], zoom: number) => void
  timeWindow: TimeWindow | null   // null = "All Active" — no date filter
  setTimeWindow: (window: TimeWindow | null) => void
  mapStyle: MapStyle
  setMapStyle: (style: MapStyle) => void
  is3D: boolean
  setIs3D: (value: boolean) => void
  // Search-driven fly-to — updated by MapSearch, consumed by MapCanvas
  flyTarget: [number, number] | null
  setFlyTarget: (coords: [number, number]) => void
}

// Default to Birmingham city centre — the synthetic fixture data is centred here
export const useMapStore = create<MapState>((set) => ({
  center: [-1.8904, 52.4862],
  zoom: 11,
  setViewport: (center, zoom) => set({ center, zoom }),
  timeWindow: null,
  setTimeWindow: (window) => set({ timeWindow: window }),
  mapStyle: 'satellite',
  setMapStyle: (style) => set({ mapStyle: style }),
  is3D: true,
  setIs3D: (value) => set({ is3D: value }),
  flyTarget: null,
  setFlyTarget: (coords) => set({ flyTarget: coords }),
}))

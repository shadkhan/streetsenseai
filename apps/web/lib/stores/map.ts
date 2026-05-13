import { create } from 'zustand'

export interface TimeWindow {
  label: string
  startDate: string   // YYYY-MM-DD
  endDate: string     // YYYY-MM-DD
}

interface MapState {
  center: [number, number]
  zoom: number
  setViewport: (center: [number, number], zoom: number) => void
  timeWindow: TimeWindow | null   // null = "All Active" — no date filter
  setTimeWindow: (window: TimeWindow | null) => void
}

// Default to Birmingham city centre — the synthetic fixture data is centred here
export const useMapStore = create<MapState>((set) => ({
  center: [-1.8904, 52.4862],
  zoom: 11,
  setViewport: (center, zoom) => set({ center, zoom }),
  timeWindow: null,
  setTimeWindow: (window) => set({ timeWindow: window }),
}))

import { create } from 'zustand'

type ActivePanel = 'none' | 'corridor' | 'copilot' | 'permit'

interface PanelState {
  active: ActivePanel
  corridorId: string | null
  permitRef: string | null
  openCorridor: (id: string) => void
  openCopilot: () => void
  openPermit: (ref: string) => void
  close: () => void
}

// Sheet conflict resolution — all three panels are mutually exclusive.
// Opening any panel closes the others (DESIGN.md §4.2, ADR-003).
export const usePanels = create<PanelState>((set) => ({
  active: 'none',
  corridorId: null,
  permitRef: null,
  openCorridor: (id) => set({ active: 'corridor', corridorId: id, permitRef: null }),
  openCopilot: () => set({ active: 'copilot', corridorId: null, permitRef: null }),
  openPermit: (ref) => set({ active: 'permit', permitRef: ref, corridorId: null }),
  close: () => set({ active: 'none', corridorId: null, permitRef: null }),
}))

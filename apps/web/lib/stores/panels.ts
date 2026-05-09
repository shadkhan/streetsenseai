import { create } from 'zustand'

type ActivePanel = 'none' | 'corridor' | 'copilot'

interface PanelState {
  active: ActivePanel
  corridorId: string | null
  openCorridor: (id: string) => void
  openCopilot: () => void
  close: () => void
}

// Sheet conflict resolution — corridor and copilot panels are mutually exclusive.
// Opening one automatically closes the other (see DESIGN.md §4.2 and ADR-003).
export const usePanels = create<PanelState>((set) => ({
  active: 'none',
  corridorId: null,
  openCorridor: (id) => set({ active: 'corridor', corridorId: id }),
  openCopilot: () => set({ active: 'copilot', corridorId: null }),
  close: () => set({ active: 'none', corridorId: null }),
}))

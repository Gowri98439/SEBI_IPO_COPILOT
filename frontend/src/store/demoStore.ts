import { create } from 'zustand'

interface DemoState {
  isDemoMode: boolean
  enableDemo: () => void
  disableDemo: () => void
  toggleDemo: () => void
}

export const useDemoStore = create<DemoState>((set) => ({
  isDemoMode: typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('demo') === 'true',
  enableDemo: () => set({ isDemoMode: true }),
  disableDemo: () => set({ isDemoMode: false }),
  toggleDemo: () => set((s) => ({ isDemoMode: !s.isDemoMode })),
}))

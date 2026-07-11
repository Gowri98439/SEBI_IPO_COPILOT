import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface WorkspaceState {
  currentWorkspaceId: string | null
  currentWorkspaceName: string | null
  setCurrentWorkspace: (id: string, name?: string) => void
  clearWorkspace: () => void
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      currentWorkspaceId: null,
      currentWorkspaceName: null,

      setCurrentWorkspace: (id, name) =>
        set({ currentWorkspaceId: id, currentWorkspaceName: name ?? null }),

      clearWorkspace: () =>
        set({ currentWorkspaceId: null, currentWorkspaceName: null }),
    }),
    {
      name: 'ipo-copilot-workspace',
      partialize: (state) => ({
        currentWorkspaceId: state.currentWorkspaceId,
        currentWorkspaceName: state.currentWorkspaceName,
      }),
    }
  )
)

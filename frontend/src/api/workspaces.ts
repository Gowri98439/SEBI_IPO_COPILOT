import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { Workspace, CreateWorkspaceRequest } from '@/types'

const WORKSPACES_KEY = ['workspaces'] as const

/* ── List workspaces (optionally by company) ──────────────────────────── */
export const useWorkspaces = (companyId?: string) =>
  useQuery<Workspace[]>({
    queryKey: companyId ? [...WORKSPACES_KEY, { companyId }] : [...WORKSPACES_KEY],
    queryFn: () =>
      apiClient.get('/workspaces', {
        params: companyId ? { company_id: companyId } : undefined,
      }),
  })

/* ── Single workspace ─────────────────────────────────────────────────── */
export const useWorkspace = (id: string) =>
  useQuery<Workspace>({
    queryKey: [...WORKSPACES_KEY, id],
    queryFn: () => apiClient.get(`/workspaces/${id}`),
    enabled: !!id,
  })

/* ── Create workspace ─────────────────────────────────────────────────── */
export const useCreateWorkspace = () => {
  const qc = useQueryClient()

  return useMutation<Workspace, Error, CreateWorkspaceRequest>({
    mutationFn: (data) => apiClient.post('/workspaces', data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: WORKSPACES_KEY })
    },
  })
}

/* ── Create demo workspace ────────────────────────────────────────────── */
export const useCreateDemoWorkspace = () => {
  const qc = useQueryClient()

  return useMutation<Workspace, Error, void>({
    mutationFn: () => apiClient.post('/workspaces/demo/seed'),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: WORKSPACES_KEY })
    },
  })
}

/* ── Update workspace ─────────────────────────────────────────────────── */
export const useUpdateWorkspace = (id: string) => {
  const qc = useQueryClient()

  return useMutation<Workspace, Error, Partial<CreateWorkspaceRequest> & { status?: string }>({
    mutationFn: (data) => apiClient.patch(`/workspaces/${id}`, data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: WORKSPACES_KEY })
    },
  })
}

/* ── Delete workspace ─────────────────────────────────────────────────── */
export const useDeleteWorkspace = () => {
  const qc = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: (id) => apiClient.delete(`/workspaces/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: WORKSPACES_KEY })
    },
  })
}

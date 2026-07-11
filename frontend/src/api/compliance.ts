import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { ComplianceCheck } from '@/types'

/* ── List compliance checks for workspace ─────────────────────────────── */
export const useComplianceChecks = (workspaceId: string) =>
  useQuery<ComplianceCheck[]>({
    queryKey: ['compliance', workspaceId],
    queryFn: () => apiClient.get(`/workspaces/${workspaceId}/compliance`),
    enabled: !!workspaceId,
  })

/* ── Single compliance check ──────────────────────────────────────────── */
export const useComplianceCheck = (checkId: string) =>
  useQuery<ComplianceCheck>({
    queryKey: ['compliance-check', checkId],
    queryFn: () => apiClient.get(`/compliance/${checkId}`),
    enabled: !!checkId,
  })

/* ── Run compliance checks for workspace ─────────────────────────────── */
export const useRunCompliance = (workspaceId: string) => {
  const qc = useQueryClient()

  return useMutation<ComplianceCheck[], Error, void>({
    mutationFn: () => apiClient.post(`/workspaces/${workspaceId}/compliance/run`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['compliance', workspaceId] })
      void qc.invalidateQueries({ queryKey: ['dashboard', workspaceId] })
    },
  })
}

/* ── Override a compliance check (manual review decision) ─────────────── */
export const useOverrideCompliance = (workspaceId: string) => {
  const qc = useQueryClient()

  return useMutation<
    ComplianceCheck,
    Error,
    { checkId: string; status: 'pass' | 'fail'; notes: string }
  >({
    mutationFn: ({ checkId, ...body }) =>
      apiClient.patch(`/compliance/${checkId}/override`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['compliance', workspaceId] })
    },
  })
}

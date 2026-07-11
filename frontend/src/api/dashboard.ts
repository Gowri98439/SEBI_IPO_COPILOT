import { useQuery } from '@tanstack/react-query'
import { apiClient } from './client'
import type { DashboardStats } from '@/types'

/* ── Dashboard stats for workspace ───────────────────────────────────── */
export const useDashboard = (workspaceId: string) =>
  useQuery<DashboardStats>({
    queryKey: ['dashboard', workspaceId],
    queryFn: () => apiClient.get(`/workspaces/${workspaceId}/dashboard`),
    enabled: !!workspaceId,
    refetchInterval: 60_000, // auto-refresh every minute
    staleTime: 30_000,
  })

/* ── Readiness score history ──────────────────────────────────────────── */
export interface ReadinessPoint {
  date: string
  score: number
}

export const useReadinessHistory = (workspaceId: string) =>
  useQuery<ReadinessPoint[]>({
    queryKey: ['readiness-history', workspaceId],
    queryFn: () => apiClient.get(`/workspaces/${workspaceId}/readiness-history`),
    enabled: !!workspaceId,
    staleTime: 120_000,
  })

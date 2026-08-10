import { useQuery } from '@tanstack/react-query'
import { apiClient } from './client'

export function useIPOReadiness(workspaceId: string) {
  return useQuery({
    queryKey: ['readiness', workspaceId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/workspaces/${workspaceId}/intelligence/readiness`)
      return data
    },
    enabled: !!workspaceId
  })
}

export function useRiskProfile(workspaceId: string) {
  return useQuery({
    queryKey: ['risks', workspaceId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/workspaces/${workspaceId}/intelligence/risks`)
      return data
    },
    enabled: !!workspaceId
  })
}

export function useKnowledgeGraph(workspaceId: string) {
  return useQuery({
    queryKey: ['graph', workspaceId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/workspaces/${workspaceId}/intelligence/graph`)
      return data
    },
    enabled: !!workspaceId
  })
}

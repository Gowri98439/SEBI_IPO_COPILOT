import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { DraftReview, ReviewTask, CreateDraftReviewRequest, CreateReviewTaskRequest } from '@/types'

/* ── Draft Reviews ────────────────────────────────────────────────────── */
export const useDraftReviews = (workspaceId: string) =>
  useQuery<DraftReview[]>({
    queryKey: ['draft-reviews', workspaceId],
    queryFn: () => apiClient.get(`/workspaces/${workspaceId}/drafts`),
    enabled: !!workspaceId,
  })

export const useDraftReview = (reviewId: string) =>
  useQuery<DraftReview>({
    queryKey: ['draft-review', reviewId],
    queryFn: () => apiClient.get(`/drafts/${reviewId}`),
    enabled: !!reviewId,
  })

export const useCreateDraftReview = () => {
  const qc = useQueryClient()

  return useMutation<DraftReview, Error, CreateDraftReviewRequest>({
    mutationFn: (data) => apiClient.post(`/workspaces/${data.workspace_id}/drafts`, data),
    onSuccess: (data) => {
      void qc.invalidateQueries({ queryKey: ['draft-reviews', data.workspace_id] })
    },
  })
}

export const useUpdateDraftReview = (reviewId: string) => {
  const qc = useQueryClient()

  return useMutation<DraftReview, Error, Partial<CreateDraftReviewRequest> & { status?: string }>({
    mutationFn: (data) => apiClient.patch(`/drafts/${reviewId}`, data),
    onSuccess: (data) => {
      void qc.invalidateQueries({ queryKey: ['draft-reviews', data.workspace_id] })
      void qc.invalidateQueries({ queryKey: ['draft-review', reviewId] })
    },
  })
}

/* ── Human Review Tasks ───────────────────────────────────────────────── */
export const useReviewTasks = (workspaceId: string) =>
  useQuery<ReviewTask[]>({
    queryKey: ['review-tasks', workspaceId],
    queryFn: () => apiClient.get(`/workspaces/${workspaceId}/reviews`),
    enabled: !!workspaceId,
  })

export const useReviewTask = (taskId: string) =>
  useQuery<ReviewTask>({
    queryKey: ['review-task', taskId],
    queryFn: () => apiClient.get(`/reviews/${taskId}`),
    enabled: !!taskId,
  })

export const useCreateReviewTask = () => {
  const qc = useQueryClient()

  return useMutation<ReviewTask, Error, CreateReviewTaskRequest>({
    mutationFn: (data) => apiClient.post(`/workspaces/${data.workspace_id}/reviews`, data),
    onSuccess: (data) => {
      void qc.invalidateQueries({ queryKey: ['review-tasks', data.workspace_id] })
    },
  })
}

export const useUpdateReviewTask = (taskId: string) => {
  const qc = useQueryClient()

  return useMutation<ReviewTask, Error, Partial<CreateReviewTaskRequest> & { status?: string }>({
    mutationFn: (data) => apiClient.patch(`/reviews/${taskId}`, data),
    onSuccess: (data) => {
      void qc.invalidateQueries({ queryKey: ['review-tasks', data.workspace_id] })
      void qc.invalidateQueries({ queryKey: ['review-task', taskId] })
    },
  })
}

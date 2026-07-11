import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { Document, ValidationResult, DocumentVersion } from '@/types'

/* ── List documents in workspace ──────────────────────────────────────── */
export const useDocuments = (workspaceId: string) =>
  useQuery<Document[]>({
    queryKey: ['documents', workspaceId],
    queryFn: () => apiClient.get(`/workspaces/${workspaceId}/documents`),
    enabled: !!workspaceId,
  })

/* ── Single document ──────────────────────────────────────────────────── */
export const useDocument = (docId: string) =>
  useQuery<Document>({
    queryKey: ['document', docId],
    queryFn: () => apiClient.get(`/documents/${docId}`),
    enabled: !!docId,
  })

/* ── Upload document (multipart FormData) ─────────────────────────────── */
export const useUploadDocument = (workspaceId: string) => {
  const qc = useQueryClient()

  return useMutation<Document, Error, FormData>({
    mutationFn: (formData) =>
      apiClient.post(`/workspaces/${workspaceId}/documents`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['documents', workspaceId] })
    },
  })
}

/* ── Trigger AI validation ────────────────────────────────────────────── */
export const useTriggerValidation = (docId: string) => {
  const qc = useQueryClient()

  return useMutation<ValidationResult, Error, void>({
    mutationFn: () => apiClient.post(`/documents/${docId}/validate`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['validation', docId] })
      void qc.invalidateQueries({ queryKey: ['document', docId] })
    },
  })
}

/* ── Validation result (polls while running) ──────────────────────────── */
export const useValidationResult = (docId: string) =>
  useQuery<ValidationResult>({
    queryKey: ['validation', docId],
    queryFn: () => apiClient.get(`/documents/${docId}/validation-result`),
    enabled: !!docId,
    refetchInterval: (query) => {
      const data = query.state.data as ValidationResult | undefined
      return (data?.status === 'running' || data?.status === 'processing' || data?.status === 'pending') ? 3_000 : false
    },
  })

/* ── Document versions ────────────────────────────────────────────────── */
export const useDocumentVersions = (docId: string) =>
  useQuery<DocumentVersion[]>({
    queryKey: ['document-versions', docId],
    queryFn: () => apiClient.get(`/documents/${docId}/versions`),
    enabled: !!docId,
  })

/* ── Delete document ──────────────────────────────────────────────────── */
export const useDeleteDocument = (workspaceId: string) => {
  const qc = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: (docId) => apiClient.delete(`/documents/${docId}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['documents', workspaceId] })
    },
  })
}

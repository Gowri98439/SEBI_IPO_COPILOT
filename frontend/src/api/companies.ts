import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from './client'
import type { Company, CreateCompanyRequest } from '@/types'

const COMPANIES_KEY = ['companies'] as const

/* ── List all companies ───────────────────────────────────────────────── */
export const useCompanies = () =>
  useQuery<Company[]>({
    queryKey: [...COMPANIES_KEY],
    queryFn: () => apiClient.get('/companies'),
  })

/* ── Single company ───────────────────────────────────────────────────── */
export const useCompany = (id: string) =>
  useQuery<Company>({
    queryKey: [...COMPANIES_KEY, id],
    queryFn: () => apiClient.get(`/companies/${id}`),
    enabled: !!id,
  })

/* ── Create company ───────────────────────────────────────────────────── */
export const useCreateCompany = () => {
  const qc = useQueryClient()

  return useMutation<Company, Error, CreateCompanyRequest>({
    mutationFn: (data) => apiClient.post('/companies', data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: COMPANIES_KEY })
    },
  })
}

/* ── Update company ───────────────────────────────────────────────────── */
export const useUpdateCompany = (id: string) => {
  const qc = useQueryClient()

  return useMutation<Company, Error, Partial<CreateCompanyRequest>>({
    mutationFn: (data) => apiClient.patch(`/companies/${id}`, data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: COMPANIES_KEY })
    },
  })
}

/* ── Delete company ───────────────────────────────────────────────────── */
export const useDeleteCompany = () => {
  const qc = useQueryClient()

  return useMutation<void, Error, string>({
    mutationFn: (id) => apiClient.delete(`/companies/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: COMPANIES_KEY })
    },
  })
}

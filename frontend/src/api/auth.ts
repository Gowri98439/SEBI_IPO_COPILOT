import { useMutation } from '@tanstack/react-query'
import { apiClient } from './client'
import { useAuthStore } from '@/store/authStore'
import type { LoginRequest, RegisterRequest, AuthResponse } from '@/types'

/* ── Login ────────────────────────────────────────────────────────────── */
export const useLogin = () => {
  const setAuth = useAuthStore((s) => s.setAuth)

  return useMutation<AuthResponse, Error, LoginRequest>({
    mutationFn: async (credentials) => {
      const response = await apiClient.post<unknown, AuthResponse>('/auth/login', credentials)
      return response
    },
    onSuccess: (data) => {
      setAuth(data.user, data.access_token)
      localStorage.setItem('ipo_copilot_token', data.access_token)
    },
  })
}

/* ── Register ─────────────────────────────────────────────────────────── */
export const useRegister = () => {
  const setAuth = useAuthStore((s) => s.setAuth)

  return useMutation<AuthResponse, Error, RegisterRequest>({
    mutationFn: async (data) =>
      apiClient.post<unknown, AuthResponse>('/auth/register', data),
    onSuccess: (data) => {
      setAuth(data.user, data.access_token)
      localStorage.setItem('ipo_copilot_token', data.access_token)
    },
  })
}

/* ── Refresh Token ────────────────────────────────────────────────────── */
export const useRefreshToken = () => {
  const setAuth = useAuthStore((s) => s.setAuth)

  return useMutation<AuthResponse, Error, string>({
    mutationFn: async (token) =>
      apiClient.post<unknown, AuthResponse>('/auth/refresh', { token }),
    onSuccess: (data) => {
      setAuth(data.user, data.access_token)
      localStorage.setItem('ipo_copilot_token', data.access_token)
    },
  })
}

/* ── Logout ───────────────────────────────────────────────────────────── */
export const useLogout = () => {
  const clearAuth = useAuthStore((s) => s.clearAuth)

  return useMutation<void, Error, void>({
    mutationFn: async () => {
      await apiClient.post('/auth/logout').catch(() => {
        /* ignore server errors on logout */
      })
    },
    onSettled: () => {
      clearAuth()
      localStorage.removeItem('ipo_copilot_token')
      window.location.href = '/login'
    },
  })
}

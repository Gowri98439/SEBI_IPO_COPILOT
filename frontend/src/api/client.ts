import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios'

const TOKEN_KEY = 'ipo_copilot_token'

export const apiClient: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 60_000,   // 60s to allow large DRHP generation polls
})

/* ── Request interceptor: attach JWT ──────────────────────────────────── */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => Promise.reject(error)
)

/* ── Response interceptor: unwrap data, handle 401 ───────────────────── */
apiClient.interceptors.response.use(
  (response) => {
    // Unwrap the `data.data` envelope if present
    if (response.data && typeof response.data === 'object' && 'data' in response.data) {
      return response.data.data
    }
    return response.data
  },
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      // Redirect to login without importing router (avoid circular deps)
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export { TOKEN_KEY }
export default apiClient

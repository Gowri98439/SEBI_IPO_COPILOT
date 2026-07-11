import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState, useCallback } from 'react'
import { apiClient } from './client'
import type { CopilotSession, CopilotMessage, SendMessageRequest } from '@/types'

/* ── List sessions for workspace ──────────────────────────────────────── */
export const useCopilotSessions = (workspaceId: string) =>
  useQuery<CopilotSession[]>({
    queryKey: ['copilot-sessions', workspaceId],
    queryFn: () => apiClient.get(`/workspaces/${workspaceId}/copilot/sessions`),
    enabled: !!workspaceId,
  })

/* ── Create new session ───────────────────────────────────────────────── */
export const useCreateSession = () => {
  const qc = useQueryClient()

  return useMutation<CopilotSession, Error, { workspace_id: string }>({
    mutationFn: (data) => apiClient.post(`/workspaces/${data.workspace_id}/copilot/sessions`, data),
    onSuccess: (data) => {
      void qc.invalidateQueries({ queryKey: ['copilot-sessions', data.workspace_id] })
    },
  })
}

/* ── Get messages for session ─────────────────────────────────────────── */
export const useCopilotMessages = (sessionId: string) =>
  useQuery<CopilotMessage[]>({
    queryKey: ['copilot-messages', sessionId],
    queryFn: () => apiClient.get(`/copilot/sessions/${sessionId}/messages`),
    enabled: !!sessionId,
  })

/* ── Send a message (non-streaming) ──────────────────────────────────── */
export const useSendMessage = (sessionId: string) => {
  const qc = useQueryClient()

  return useMutation<CopilotMessage, Error, SendMessageRequest>({
    mutationFn: (data) =>
      apiClient.post(`/copilot/sessions/${sessionId}/message`, data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['copilot-messages', sessionId] })
    },
  })
}

/* ── SSE streaming hook ───────────────────────────────────────────────── */
export interface SSEStreamState {
  streamText: string
  isStreaming: boolean
  error: string | null
  startStream: (content: string) => void
  stopStream: () => void
}

export const useSSEStream = (sessionId: string): SSEStreamState => {
  const [streamText, setStreamText] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const eventSourceRef = useRef<EventSource | null>(null)
  const qc = useQueryClient()

  const stopStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setIsStreaming(false)
  }, [])

  const startStream = useCallback(
    (content: string) => {
      stopStream()
      setStreamText('')
      setError(null)
      setIsStreaming(true)

      const token = localStorage.getItem('ipo_copilot_token') ?? ''
      const url = `/api/v1/copilot/sessions/${sessionId}/stream?` + new URLSearchParams({ content, token })

      const es = new EventSource(url)
      eventSourceRef.current = es

      es.addEventListener('message', (e: MessageEvent<string>) => {
        if (e.data === '[DONE]') {
          stopStream()
          void qc.invalidateQueries({ queryKey: ['copilot-messages', sessionId] })
          return
        }
        try {
          const parsed = JSON.parse(e.data) as { delta?: string; text?: string }
          setStreamText((prev) => prev + (parsed.delta ?? parsed.text ?? ''))
        } catch {
          setStreamText((prev) => prev + e.data)
        }
      })

      es.addEventListener('error', () => {
        setError('Stream connection failed. Please try again.')
        stopStream()
      })
    },
    [sessionId, stopStream, qc]
  )

  useEffect(() => () => stopStream(), [stopStream])

  return { streamText, isStreaming, error, startStream, stopStream }
}

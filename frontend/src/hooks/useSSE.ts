import { useEffect, useRef, useCallback } from 'react';

interface SSEOptions {
  onMessage: (data: string) => void;
  onError?: (err: Event) => void;
  onOpen?: () => void;
  withCredentials?: boolean;
}

/**
 * Custom hook for consuming Server-Sent Events (SSE).
 * Auto-reconnects with exponential back-off up to 30 s.
 * Tears down EventSource on unmount or when url becomes null.
 */
export function useSSE(url: string | null, options: SSEOptions): void;
export function useSSE(url: string | null, onMessage: (data: string) => void): void;
export function useSSE(
  url: string | null,
  optionsOrCallback: SSEOptions | ((data: string) => void)
): void {
  const esRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Normalise overloads
  const opts: SSEOptions =
    typeof optionsOrCallback === 'function'
      ? { onMessage: optionsOrCallback }
      : optionsOrCallback;

  const { onMessage, onError, onOpen, withCredentials = false } = opts;

  // Keep callbacks stable without triggering re-connect
  const onMessageRef = useRef(onMessage);
  const onErrorRef = useRef(onError);
  const onOpenRef = useRef(onOpen);
  useEffect(() => { onMessageRef.current = onMessage; }, [onMessage]);
  useEffect(() => { onErrorRef.current = onError; }, [onError]);
  useEffect(() => { onOpenRef.current = onOpen; }, [onOpen]);

  const cleanup = useCallback(() => {
    if (retryTimerRef.current !== null) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!url) return;

    const es = new EventSource(url, { withCredentials });
    esRef.current = es;

    es.onopen = () => {
      retryCountRef.current = 0;
      onOpenRef.current?.();
    };

    es.onmessage = (event: MessageEvent) => {
      onMessageRef.current(event.data);
    };

    es.onerror = (event: Event) => {
      onErrorRef.current?.(event);
      es.close();
      esRef.current = null;

      // Exponential back-off: 1s → 2s → 4s → … capped at 30s
      const delay = Math.min(1000 * 2 ** retryCountRef.current, 30_000);
      retryCountRef.current += 1;

      retryTimerRef.current = setTimeout(() => {
        connect();
      }, delay);
    };
  }, [url, withCredentials]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!url) {
      cleanup();
      return;
    }

    connect();

    return () => {
      cleanup();
    };
  }, [url, connect, cleanup]);
}

export default useSSE;

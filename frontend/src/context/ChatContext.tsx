/**
 * ChatContext — Global persistent SEBI Advisor chat state.
 * Survives page navigation; history stored in localStorage per workspace.
 * Supports multiple conversation threads (like ChatGPT).
 */
import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string; // ISO string — serialisable for localStorage
  ragSources?: number;
}

export interface ChatThread {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
}

interface ChatState {
  threads: Record<string, ChatThread[]>;   // keyed by workspaceId
  activeThreadId: Record<string, string>;  // workspaceId -> threadId
}

type ChatAction =
  | { type: 'INIT'; workspaceId: string; threads: ChatThread[]; activeThreadId?: string }
  | { type: 'NEW_THREAD'; workspaceId: string; thread: ChatThread }
  | { type: 'SET_ACTIVE'; workspaceId: string; threadId: string }
  | { type: 'ADD_MESSAGE'; workspaceId: string; threadId: string; message: ChatMessage }
  | { type: 'DELETE_THREAD'; workspaceId: string; threadId: string };

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'INIT': {
      const threads = action.threads.length > 0 ? action.threads : [createThread()];
      const activeId = action.activeThreadId ?? threads[0].id;
      return {
        threads: { ...state.threads, [action.workspaceId]: threads },
        activeThreadId: { ...state.activeThreadId, [action.workspaceId]: activeId },
      };
    }
    case 'NEW_THREAD':
      return {
        threads: {
          ...state.threads,
          [action.workspaceId]: [action.thread, ...(state.threads[action.workspaceId] ?? [])],
        },
        activeThreadId: { ...state.activeThreadId, [action.workspaceId]: action.thread.id },
      };
    case 'SET_ACTIVE':
      return {
        ...state,
        activeThreadId: { ...state.activeThreadId, [action.workspaceId]: action.threadId },
      };
    case 'ADD_MESSAGE': {
      const wsThreads = state.threads[action.workspaceId] ?? [];
      const updated = wsThreads.map((t) => {
        if (t.id !== action.threadId) return t;
        const newMsgs = [...t.messages, action.message];
        const title = t.title === 'New conversation'
          ? deriveTitle(newMsgs)
          : t.title;
        return { ...t, messages: newMsgs, title, updatedAt: new Date().toISOString() };
      });
      return { ...state, threads: { ...state.threads, [action.workspaceId]: updated } };
    }
    case 'DELETE_THREAD': {
      const remaining = (state.threads[action.workspaceId] ?? []).filter(
        (t) => t.id !== action.threadId
      );
      if (remaining.length === 0) {
        const fresh = createThread();
        return {
          threads: { ...state.threads, [action.workspaceId]: [fresh] },
          activeThreadId: { ...state.activeThreadId, [action.workspaceId]: fresh.id },
        };
      }
      const newActive =
        state.activeThreadId[action.workspaceId] === action.threadId
          ? remaining[0].id
          : state.activeThreadId[action.workspaceId];
      return {
        threads: { ...state.threads, [action.workspaceId]: remaining },
        activeThreadId: { ...state.activeThreadId, [action.workspaceId]: newActive },
      };
    }
    default:
      return state;
  }
}

function createThread(): ChatThread {
  const id = `thread_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  return {
    id,
    title: 'New conversation',
    messages: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}

function deriveTitle(messages: ChatMessage[]): string {
  const first = messages.find((m) => m.role === 'user');
  if (!first) return 'New conversation';
  return first.content.slice(0, 50) + (first.content.length > 50 ? '…' : '');
}

const STORAGE_KEY = 'ipo_chat_state_v2';

function loadFromStorage(): ChatState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as ChatState;
  } catch { /* ignore */ }
  return { threads: {}, activeThreadId: {} };
}

function saveToStorage(state: ChatState) {
  try {
    // Keep only last 50 threads per workspace to avoid storage bloat
    const trimmed: ChatState = { threads: {}, activeThreadId: state.activeThreadId };
    for (const [wsId, threads] of Object.entries(state.threads)) {
      trimmed.threads[wsId] = threads.slice(0, 50);
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
  } catch { /* storage full — ignore */ }
}

interface ChatContextValue {
  getThreads: (workspaceId: string) => ChatThread[];
  getActiveThread: (workspaceId: string) => ChatThread | undefined;
  newThread: (workspaceId: string) => void;
  setActive: (workspaceId: string, threadId: string) => void;
  addMessage: (workspaceId: string, threadId: string, msg: ChatMessage) => void;
  deleteThread: (workspaceId: string, threadId: string) => void;
  initWorkspace: (workspaceId: string) => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, undefined, loadFromStorage);

  // Persist every state change
  useEffect(() => {
    saveToStorage(state);
  }, [state]);

  const initWorkspace = useCallback((workspaceId: string) => {
    if (!state.threads[workspaceId]) {
      const loaded = loadFromStorage();
      const threads = loaded.threads[workspaceId] ?? [];
      const activeId = loaded.activeThreadId[workspaceId];
      dispatch({ type: 'INIT', workspaceId, threads, activeThreadId: activeId });
    }
  }, [state.threads]);

  const getThreads = useCallback(
    (workspaceId: string) => state.threads[workspaceId] ?? [],
    [state.threads]
  );

  const getActiveThread = useCallback(
    (workspaceId: string): ChatThread | undefined => {
      const threads = state.threads[workspaceId] ?? [];
      const activeId = state.activeThreadId[workspaceId];
      return threads.find((t) => t.id === activeId) ?? threads[0];
    },
    [state]
  );

  const newThread = useCallback((workspaceId: string) => {
    dispatch({ type: 'NEW_THREAD', workspaceId, thread: createThread() });
  }, []);

  const setActive = useCallback((workspaceId: string, threadId: string) => {
    dispatch({ type: 'SET_ACTIVE', workspaceId, threadId });
  }, []);

  const addMessage = useCallback(
    (workspaceId: string, threadId: string, msg: ChatMessage) => {
      dispatch({ type: 'ADD_MESSAGE', workspaceId, threadId, message: msg });
    },
    []
  );

  const deleteThread = useCallback((workspaceId: string, threadId: string) => {
    dispatch({ type: 'DELETE_THREAD', workspaceId, threadId });
  }, []);

  return (
    <ChatContext.Provider value={{ getThreads, getActiveThread, newThread, setActive, addMessage, deleteThread, initWorkspace }}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext(): ChatContextValue {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error('useChatContext must be used within <ChatProvider>');
  return ctx;
}

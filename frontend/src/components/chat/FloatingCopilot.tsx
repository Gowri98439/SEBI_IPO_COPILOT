/**
 * FloatingCopilot — Persistent ChatGPT-style chat widget.
 * Mounts once in AppShell, survives page navigation.
 * Chat history is persisted in localStorage via ChatContext.
 */
import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  MessageSquare, X, Send, Plus, ChevronDown, Bot, User,
  Minimize2, Maximize2, Trash2, RotateCcw,
} from 'lucide-react';
import api from '../../api/client';
import { useChatContext, ChatMessage } from '../../context/ChatContext';
import { useWorkspaceStore } from '../../store/workspaceStore';

/* ── Inline style constants ─────────────────────────────────────────── */
const Z = 9999;

const PANEL_W = 420;
const PANEL_H_DEFAULT = 620;
const PANEL_H_EXPANDED = Math.min(window.innerHeight - 80, 800);

const COLORS = {
  bg: '#0F1117',
  surface: '#16191F',
  border: '#1E2330',
  accent: '#1A56DB',
  accentLight: '#2563EB',
  text: '#F1F5F9',
  textSub: '#94A3B8',
  user: '#1A56DB',
  userText: '#FFFFFF',
  bot: '#1A1F2E',
  botText: '#E2E8F0',
  input: '#1A1F2E',
};

/* ── Simple Markdown renderer ───────────────────────────────────────── */
function MdLine({ text }: { text: string }) {
  const bold = (t: string) =>
    t.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
      part.startsWith('**') && part.endsWith('**')
        ? <strong key={i}>{part.slice(2, -2)}</strong>
        : part
    );
  return <span>{bold(text)}</span>;
}

function renderMd(content: string): React.ReactNode {
  const lines = content.split('\n');
  const out: React.ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (/^#{1,3} /.test(line)) {
      const lvl = (line.match(/^#+/)![0]).length;
      const sz = lvl === 1 ? '1rem' : lvl === 2 ? '0.9375rem' : '0.875rem';
      out.push(<div key={i} style={{ fontWeight: 700, fontSize: sz, color: COLORS.text, margin: '0.75rem 0 0.25rem' }}>{line.replace(/^#+\s*/, '')}</div>);
    } else if (/^[-*]\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s/.test(lines[i])) {
        items.push(lines[i].replace(/^[-*]\s/, ''));
        i++;
      }
      out.push(<ul key={i} style={{ margin: '0.375rem 0', paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
        {items.map((item, j) => <li key={j} style={{ fontSize: '0.875rem', color: COLORS.botText, lineHeight: 1.6 }}><MdLine text={item} /></li>)}
      </ul>);
      continue;
    } else if (line.trim() === '') {
      if (out.length > 0) out.push(<div key={i} style={{ height: '0.5rem' }} />);
    } else {
      out.push(<p key={i} style={{ margin: 0, fontSize: '0.875rem', lineHeight: 1.65, color: COLORS.botText }}><MdLine text={line} /></p>);
    }
    i++;
  }
  return <>{out}</>;
}

/* ── Main component ─────────────────────────────────────────────────── */
export default function FloatingCopilot() {
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [streamBuf, setStreamBuf] = useState('');

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const workspaceId = useWorkspaceStore((s) => s.currentWorkspaceId) ?? 'global';
  const { getThreads, getActiveThread, newThread, addMessage, initWorkspace, setActive, deleteThread } = useChatContext();

  // Init workspace threads on mount / workspaceId change
  useEffect(() => {
    initWorkspace(workspaceId);
  }, [workspaceId, initWorkspace]);

  const threads = getThreads(workspaceId);
  const activeThread = getActiveThread(workspaceId);
  const messages = activeThread?.messages ?? [];

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamBuf, open]);

  // Focus input when opened
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  const panelH = expanded ? PANEL_H_EXPANDED : PANEL_H_DEFAULT;

  const sendMessage = useCallback(async () => {
    const text = input.trim();
    if (!text || streaming || !activeThread) return;

    setInput('');
    setStreaming(true);
    setStreamBuf('');

    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    addMessage(workspaceId, activeThread.id, userMsg);

    abortRef.current = new AbortController();

    try {
      // Show a typing animation while waiting
      setStreamBuf('…');

      const token = localStorage.getItem('ipo_copilot_token') ?? '';
      const response = await fetch(`/api/v1/workspaces/${workspaceId}/copilot/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          message: text,
          history: messages.slice(-10).map((m) => ({
            role: m.role,
            content: m.content,
          })),
        }),
        signal: abortRef.current.signal,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({})) as { detail?: string };
        throw new Error(errData.detail ?? `Server error ${response.status}`);
      }

      const data = await response.json() as { response?: string; answer?: string; message?: string };
      const answer = data.response ?? data.answer ?? data.message ?? 'No response received.';

      const botMsg: ChatMessage = {
        id: `msg_${Date.now()}_bot`,
        role: 'assistant',
        content: answer,
        timestamp: new Date().toISOString(),
      };
      addMessage(workspaceId, activeThread.id, botMsg);
    } catch (err: any) {
      if (err?.name !== 'AbortError') {
        const errMsg: ChatMessage = {
          id: `msg_${Date.now()}_err`,
          role: 'assistant',
          content: `⚠️ ${err?.message ?? 'Connection error'}. Please check the backend is running and try again.`,
          timestamp: new Date().toISOString(),
        };
        addMessage(workspaceId, activeThread.id, errMsg);
      }
    } finally {
      setStreaming(false);
      setStreamBuf('');
    }
  }, [input, streaming, activeThread, workspaceId, messages, addMessage]);


  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void sendMessage();
    }
  };

  const handleStop = () => {
    abortRef.current?.abort();
  };

  const panelHeight = panelH;

  /* ── Render ────────────────────────────────────────────────────────── */
  return (
    <>
      {/* Floating toggle button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          title="Open SEBI Advisor"
          style={{
            position: 'fixed',
            bottom: '1.5rem',
            right: '1.5rem',
            zIndex: Z,
            width: '56px',
            height: '56px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #1A56DB, #0E3A9E)',
            border: 'none',
            boxShadow: '0 4px 24px rgba(26,86,219,0.5), 0 2px 8px rgba(0,0,0,0.4)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'transform 180ms ease, box-shadow 180ms ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.08)';
            e.currentTarget.style.boxShadow = '0 6px 32px rgba(26,86,219,0.65), 0 2px 8px rgba(0,0,0,0.4)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1)';
            e.currentTarget.style.boxShadow = '0 4px 24px rgba(26,86,219,0.5), 0 2px 8px rgba(0,0,0,0.4)';
          }}
        >
          <MessageSquare size={24} color="#fff" />
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div
          style={{
            position: 'fixed',
            bottom: '1.5rem',
            right: '1.5rem',
            zIndex: Z,
            width: `${PANEL_W}px`,
            height: `${panelHeight}px`,
            borderRadius: '16px',
            background: COLORS.bg,
            border: `1px solid ${COLORS.border}`,
            boxShadow: '0 24px 64px rgba(0,0,0,0.7), 0 4px 16px rgba(0,0,0,0.4)',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
            transition: 'height 250ms ease',
          }}
        >
          {/* Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.625rem',
            padding: '0.875rem 1rem',
            background: COLORS.surface,
            borderBottom: `1px solid ${COLORS.border}`,
            flexShrink: 0,
          }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '8px',
              background: 'linear-gradient(135deg, #1A56DB, #0E3A9E)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <Bot size={16} color="#fff" />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: '0.875rem', fontWeight: 700, color: COLORS.text }}>SEBI Advisor</div>
              <div style={{ fontSize: '0.6875rem', color: COLORS.textSub }}>
                {streaming ? '● Thinking…' : 'Powered by Groq · SEBI 2026 Regulations'}
              </div>
            </div>
            <button onClick={() => newThread(workspaceId)} title="New chat" style={iconBtn}>
              <Plus size={15} />
            </button>
            <button onClick={() => setExpanded((e) => !e)} title={expanded ? 'Collapse' : 'Expand'} style={iconBtn}>
              {expanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
            </button>
            <button onClick={() => setOpen(false)} title="Close" style={iconBtn}>
              <X size={15} />
            </button>
          </div>

          {/* Thread sidebar + messages in flex row */}
          <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>

            {/* Thread list (mini sidebar) — visible only when expanded */}
            {expanded && threads.length > 1 && (
              <div style={{
                width: '140px', minWidth: '140px',
                borderRight: `1px solid ${COLORS.border}`,
                overflowY: 'auto',
                background: COLORS.surface,
                display: 'flex',
                flexDirection: 'column',
                padding: '0.5rem 0',
                gap: '1px',
              }}>
                {threads.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setActive(workspaceId, t.id)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '0.375rem',
                      padding: '0.5rem 0.625rem',
                      background: t.id === activeThread?.id ? 'rgba(26,86,219,0.25)' : 'transparent',
                      border: 'none', cursor: 'pointer',
                      borderLeft: t.id === activeThread?.id ? '2px solid #1A56DB' : '2px solid transparent',
                      textAlign: 'left', width: '100%',
                    }}
                  >
                    <MessageSquare size={11} color={t.id === activeThread?.id ? '#1A56DB' : COLORS.textSub} />
                    <span style={{
                      fontSize: '0.7rem', color: t.id === activeThread?.id ? COLORS.text : COLORS.textSub,
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1,
                    }}>
                      {t.title}
                    </span>
                    {threads.length > 1 && (
                      <button
                        onClick={(e) => { e.stopPropagation(); deleteThread(workspaceId, t.id); }}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '1px', opacity: 0.5 }}
                      >
                        <Trash2 size={9} color={COLORS.textSub} />
                      </button>
                    )}
                  </button>
                ))}
              </div>
            )}

            {/* Messages area */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.625rem' }}>

              {/* Empty state */}
              {messages.length === 0 && !streaming && (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem 1rem', gap: '0.75rem' }}>
                  <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'rgba(26,86,219,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Bot size={24} color="#1A56DB" />
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: 700, color: COLORS.text, marginBottom: '0.25rem' }}>SEBI IPO Advisor</div>
                    <div style={{ fontSize: '0.75rem', color: COLORS.textSub, lineHeight: 1.6 }}>
                      Ask me anything about SEBI regulations, SME IPO eligibility, DRHP requirements, or compliance checks.
                    </div>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', width: '100%', marginTop: '0.5rem' }}>
                    {['What are 2026 SEBI SME IPO eligibility criteria?', 'Explain lock-in requirements for promoters', 'What is mandatory in a DRHP?'].map((q) => (
                      <button
                        key={q}
                        onClick={() => { setInput(q); setTimeout(() => inputRef.current?.focus(), 50); }}
                        style={{
                          background: COLORS.surface, border: `1px solid ${COLORS.border}`,
                          borderRadius: '8px', padding: '0.5rem 0.75rem',
                          color: COLORS.textSub, fontSize: '0.75rem', textAlign: 'left',
                          cursor: 'pointer', lineHeight: 1.5, transition: 'border-color 150ms',
                        }}
                        onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#1A56DB'; e.currentTarget.style.color = COLORS.text; }}
                        onMouseLeave={(e) => { e.currentTarget.style.borderColor = COLORS.border; e.currentTarget.style.color = COLORS.textSub; }}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Message bubbles */}
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  style={{
                    display: 'flex',
                    flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                    gap: '0.5rem',
                    alignItems: 'flex-start',
                  }}
                >
                  {/* Avatar */}
                  <div style={{
                    width: '26px', height: '26px', borderRadius: '50%', flexShrink: 0,
                    background: msg.role === 'user' ? COLORS.user : 'rgba(26,86,219,0.15)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    marginTop: '2px',
                  }}>
                    {msg.role === 'user'
                      ? <User size={13} color="#fff" />
                      : <Bot size={13} color="#1A56DB" />}
                  </div>

                  {/* Bubble */}
                  <div style={{
                    maxWidth: '80%',
                    background: msg.role === 'user' ? COLORS.user : COLORS.bot,
                    color: msg.role === 'user' ? COLORS.userText : COLORS.botText,
                    borderRadius: msg.role === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
                    padding: '0.625rem 0.875rem',
                    fontSize: '0.875rem',
                    lineHeight: 1.65,
                    boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                  }}>
                    {msg.role === 'user'
                      ? <p style={{ margin: 0 }}>{msg.content}</p>
                      : renderMd(msg.content)}
                  </div>
                </div>
              ))}

              {/* Streaming bubble */}
              {streaming && (
                <div style={{ display: 'flex', flexDirection: 'row', gap: '0.5rem', alignItems: 'flex-start' }}>
                  <div style={{
                    width: '26px', height: '26px', borderRadius: '50%', flexShrink: 0,
                    background: 'rgba(26,86,219,0.15)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: '2px',
                  }}>
                    <Bot size={13} color="#1A56DB" />
                  </div>
                  <div style={{
                    maxWidth: '80%', background: COLORS.bot,
                    borderRadius: '14px 14px 14px 4px',
                    padding: '0.625rem 0.875rem',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.2)',
                  }}>
                    {streamBuf
                      ? renderMd(streamBuf)
                      : <div style={{ display: 'flex', gap: '4px', alignItems: 'center', padding: '2px 0' }}>
                          {[0, 1, 2].map((i) => (
                            <div key={i} style={{
                              width: '6px', height: '6px', borderRadius: '50%', background: '#1A56DB',
                              animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
                            }} />
                          ))}
                        </div>
                    }
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input area */}
          <div style={{
            padding: '0.75rem',
            borderTop: `1px solid ${COLORS.border}`,
            background: COLORS.surface,
            flexShrink: 0,
          }}>
            <div style={{
              display: 'flex',
              gap: '0.5rem',
              alignItems: 'flex-end',
              background: COLORS.input,
              border: `1px solid ${COLORS.border}`,
              borderRadius: '12px',
              padding: '0.5rem 0.5rem 0.5rem 0.875rem',
              transition: 'border-color 150ms',
            }}
              onFocus={() => {}}
            >
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about SEBI regulations, DRHP, IPO compliance…"
                disabled={streaming}
                rows={1}
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: COLORS.text,
                  fontSize: '0.875rem',
                  lineHeight: 1.5,
                  resize: 'none',
                  maxHeight: '120px',
                  overflowY: 'auto',
                  padding: '0.25rem 0',
                  fontFamily: 'inherit',
                  minHeight: '24px',
                }}
                onInput={(e) => {
                  const el = e.currentTarget;
                  el.style.height = 'auto';
                  el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
                }}
              />
              {streaming
                ? (
                  <button onClick={handleStop} title="Stop" style={{
                    ...sendBtnStyle,
                    background: 'rgba(239,68,68,0.15)',
                    border: '1px solid rgba(239,68,68,0.3)',
                  }}>
                    <RotateCcw size={15} color="#F87171" />
                  </button>
                ) : (
                  <button
                    onClick={() => void sendMessage()}
                    disabled={!input.trim()}
                    title="Send (Enter)"
                    style={{
                      ...sendBtnStyle,
                      background: input.trim() ? COLORS.accent : 'rgba(26,86,219,0.15)',
                      cursor: input.trim() ? 'pointer' : 'default',
                    }}
                  >
                    <Send size={15} color={input.trim() ? '#fff' : COLORS.textSub} />
                  </button>
                )}
            </div>
            <div style={{ fontSize: '0.6875rem', color: 'rgba(148,163,184,0.45)', marginTop: '0.375rem', textAlign: 'center' }}>
              Enter to send · Shift+Enter for new line · Groq AI
            </div>
          </div>
        </div>
      )}

      {/* CSS keyframe for typing bounce */}
      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.5; }
          40% { transform: translateY(-4px); opacity: 1; }
        }
      `}</style>
    </>
  );
}

const iconBtn: React.CSSProperties = {
  background: 'transparent',
  border: 'none',
  cursor: 'pointer',
  padding: '4px',
  borderRadius: '6px',
  color: 'rgba(148,163,184,0.7)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'background 150ms, color 150ms',
};

const sendBtnStyle: React.CSSProperties = {
  width: '32px',
  height: '32px',
  borderRadius: '8px',
  border: 'none',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  flexShrink: 0,
  transition: 'background 150ms',
};

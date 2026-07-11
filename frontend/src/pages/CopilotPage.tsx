import React, { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Send, Plus, Trash2, MessageSquare, User, Bot,
  Info, BookOpen, ChevronDown, ChevronUp,
} from 'lucide-react';
import api from '../api/client';
import { useChatContext, ChatMessage } from '../context/ChatContext';

/* ── Suggested starter questions ───────────────────────────────────────── */
const SUGGESTED = [
  'What is the minimum net tangible assets required for SME IPO under SEBI ICDR?',
  'What are the 2024 SEBI amendments to SME IPO eligibility criteria?',
  'Explain the lock-in requirements for promoters in an SME IPO.',
  'What financial disclosures are mandatory in a DRHP?',
  'What is the difference between SME IPO and main board IPO?',
  'How does book building work for SME IPOs?',
  'What are the new ESG disclosure requirements for IPO issuers in 2025?',
  'What is the minimum number of allottees required for an SME IPO?',
];

/* ── Simple markdown-to-JSX renderer ────────────────────────────────────── */
function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split('\n');
  const result: React.ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith('### ')) {
      result.push(<h4 key={i} style={{ margin: '1rem 0 0.375rem', fontWeight: 700, fontSize: '0.9375rem', color: 'var(--text-primary)' }}>{line.slice(4)}</h4>);
    } else if (line.startsWith('## ')) {
      result.push(<h3 key={i} style={{ margin: '1rem 0 0.375rem', fontWeight: 700, fontSize: '1rem', color: 'var(--text-primary)' }}>{line.slice(3)}</h3>);
    } else if (line.startsWith('**') && line.endsWith('**')) {
      result.push(<p key={i} style={{ margin: '0.25rem 0', fontWeight: 700, color: 'var(--text-primary)' }}>{line.slice(2, -2)}</p>);
    } else if (/^(\d+\.|-|\*) /.test(line)) {
      // Collect consecutive list items
      const listItems: string[] = [];
      while (i < lines.length && /^(\d+\.|-|\*) /.test(lines[i])) {
        listItems.push(lines[i].replace(/^(\d+\.|-|\*) /, ''));
        i++;
      }
      result.push(
        <ul key={i} style={{ margin: '0.5rem 0', paddingLeft: '1.5rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          {listItems.map((item, j) => (
            <li key={j} style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.65 }}>{formatInline(item)}</li>
          ))}
        </ul>
      );
      continue;
    } else if (line.trim() === '') {
      result.push(<br key={i} />);
    } else {
      result.push(<p key={i} style={{ margin: '0.2rem 0', lineHeight: 1.7, color: 'var(--text-secondary)', fontSize: '0.9375rem' }}>{formatInline(line)}</p>);
    }
    i++;
  }
  return result;
}

function formatInline(text: string): React.ReactNode {
  // Bold **text**, inline code `code`, citations [ICDR ...]
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[ICDR[^\]]+\]|\[LODR[^\]]+\]|\[Reg[^\]]+\])/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**'))
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('`') && part.endsWith('`'))
      return <code key={i} style={{ background: 'var(--bg-elevated)', padding: '0 4px', borderRadius: '4px', fontSize: '0.85em', fontFamily: 'monospace' }}>{part.slice(1, -1)}</code>;
    if (part.startsWith('[ICDR') || part.startsWith('[LODR') || part.startsWith('[Reg'))
      return <span key={i} style={{ background: 'var(--accent-light)', color: 'var(--accent)', borderRadius: '4px', padding: '0 4px', fontSize: '0.8em', fontWeight: 600 }}>{part}</span>;
    return part;
  });
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}
function formatDate(iso: string) {
  const d = new Date(iso);
  const today = new Date();
  if (d.toDateString() === today.toDateString()) return 'Today';
  const yest = new Date(); yest.setDate(yest.getDate() - 1);
  if (d.toDateString() === yest.toDateString()) return 'Yesterday';
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' });
}

/* ── Main Component ─────────────────────────────────────────────────────── */
const CopilotPage: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const chat = useChatContext();

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const [showSuggested, setShowSuggested] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Init workspace in chat context on mount
  useEffect(() => {
    if (workspaceId) chat.initWorkspace(workspaceId);
  }, [workspaceId, chat.initWorkspace]);

  const threads = workspaceId ? chat.getThreads(workspaceId) : [];
  const activeThread = workspaceId ? chat.getActiveThread(workspaceId) : undefined;
  const messages = activeThread?.messages ?? [];

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, loading]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + 'px';
    }
  }, [input]);

  const sendMessage = async (text?: string) => {
    const content = (text ?? input).trim();
    if (!content || loading || !workspaceId || !activeThread) return;
    setInput('');

    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    chat.addMessage(workspaceId, activeThread.id, userMsg);
    setLoading(true);

    // Build history from all current messages for multi-turn context
    const history = messages.map((m) => ({ role: m.role, content: m.content }));

    try {
      const data = await api.post(`/workspaces/${workspaceId}/copilot/chat`, {
        message: content,
        history,
      });
      const reply = data?.response ?? data?.message ?? 'No response received.';
      const botMsg: ChatMessage = {
        id: `msg_${Date.now() + 1}`,
        role: 'assistant',
        content: reply,
        timestamp: new Date().toISOString(),
        ragSources: data?.rag_sources ?? 0,
      };
      chat.addMessage(workspaceId, activeThread.id, botMsg);
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? err?.message ?? 'Please check your connection and try again.';
      chat.addMessage(workspaceId, activeThread.id, {
        id: `msg_${Date.now() + 2}`,
        role: 'assistant',
        content: `I encountered an issue processing your question. ${detail}`,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const newChat = () => { if (workspaceId) chat.newThread(workspaceId); };

  // Group threads by date for sidebar display
  const threadsByDate: Record<string, typeof threads> = {};
  threads.forEach((t) => {
    const dateKey = formatDate(t.updatedAt);
    if (!threadsByDate[dateKey]) threadsByDate[dateKey] = [];
    threadsByDate[dateKey].push(t);
  });

  return (
    <div style={{
      height: 'calc(100vh - 4rem)', display: 'flex', flexDirection: 'row', overflow: 'hidden',
      background: 'var(--bg-base)', margin: '-1.5rem',
    }}>

      {/* ── Left sidebar: conversation history ──────────────────────────── */}
      {showSidebar && (
        <div style={{
          width: '260px', flexShrink: 0, borderRight: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column', background: 'var(--bg-card)',
          overflow: 'hidden',
        }}>
          {/* Sidebar header */}
          <div style={{ padding: '1rem', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
            <button
              onClick={newChat}
              className="btn btn-primary"
              style={{ width: '100%', justifyContent: 'center', gap: '0.5rem' }}
            >
              <Plus size={16} /> New Chat
            </button>
          </div>

          {/* Thread list */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '0.5rem' }}>
            {Object.entries(threadsByDate).map(([date, dateThreads]) => (
              <div key={date}>
                <p style={{
                  fontSize: '0.6875rem', fontWeight: 700, color: 'var(--text-muted)',
                  textTransform: 'uppercase', letterSpacing: '0.06em',
                  padding: '0.5rem 0.5rem 0.25rem',
                }}>
                  {date}
                </p>
                {dateThreads.map((thread) => {
                  const isActive = thread.id === activeThread?.id;
                  return (
                    <div
                      key={thread.id}
                      style={{
                        display: 'flex', alignItems: 'center', gap: '0.5rem',
                        borderRadius: '8px', marginBottom: '2px',
                        background: isActive ? 'var(--accent-light)' : 'transparent',
                        cursor: 'pointer',
                      }}
                      onClick={() => workspaceId && chat.setActive(workspaceId, thread.id)}
                      onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'var(--bg-elevated)'; }}
                      onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
                    >
                      <MessageSquare size={13} color={isActive ? 'var(--accent)' : 'var(--text-muted)'} style={{ flexShrink: 0, marginLeft: '0.625rem' }} />
                      <span style={{
                        flex: 1, fontSize: '0.8125rem', color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                        padding: '0.5rem 0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                        fontWeight: isActive ? 600 : 400,
                      }}>
                        {thread.title}
                      </span>
                      {thread.messages.length > 0 && (
                        <button
                          onClick={(e) => { e.stopPropagation(); workspaceId && chat.deleteThread(workspaceId, thread.id); }}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0.5rem 0.5rem', flexShrink: 0, opacity: 0 }}
                          className="thread-delete-btn"
                          title="Delete conversation"
                        >
                          <Trash2 size={12} color="var(--text-muted)" />
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            ))}
          </div>

          {/* Disclaimer */}
          <div style={{ padding: '0.75rem', borderTop: '1px solid var(--border)', flexShrink: 0 }}>
            <p style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', lineHeight: 1.5, margin: 0 }}>
              Advisory use only. Verify outputs with a qualified legal professional. Powered by SEBI regulations 2018-2026.
            </p>
          </div>
        </div>
      )}

      {/* ── Right: chat area ─────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Chat header */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '0.75rem',
          padding: '0.75rem 1.25rem', borderBottom: '1px solid var(--border)',
          background: 'var(--bg-card)', flexShrink: 0,
        }}>
          <button
            onClick={() => setShowSidebar((v) => !v)}
            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '0.25rem', display: 'flex' }}
            title={showSidebar ? 'Hide history' : 'Show history'}
          >
            <MessageSquare size={18} color="var(--text-muted)" />
          </button>
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: 0, fontSize: '0.9375rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              SEBI Advisor
            </h2>
            <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              SEBI ICDR 2018 · Amendments 2024-2026 · NSE/BSE SME Guidelines
            </p>
          </div>
          <div className="alert alert-info" style={{ margin: 0, padding: '0.375rem 0.75rem', fontSize: '0.75rem', alignItems: 'center' }}>
            <Info size={13} style={{ flexShrink: 0 }} />
            Advisory use only — verify with legal counsel
          </div>
        </div>

        {/* Messages */}
        <div style={{
          flex: 1, overflowY: 'auto', padding: '1.5rem',
          display: 'flex', flexDirection: 'column', gap: '1.5rem',
        }}>

          {/* Empty state */}
          {messages.length === 0 && (
            <div style={{ maxWidth: '720px', margin: '0 auto', width: '100%' }}>
              <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                <div style={{
                  width: '56px', height: '56px', borderRadius: '50%',
                  background: 'var(--accent-light)', border: '1px solid var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  margin: '0 auto 1rem',
                }}>
                  <BookOpen size={28} color="var(--accent)" />
                </div>
                <h3 style={{ margin: '0 0 0.375rem', fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  SEBI Advisor
                </h3>
                <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.9375rem' }}>
                  Ask anything about SEBI regulations, SME IPO process, and DRHP requirements.
                  Trained on SEBI ICDR 2018, circulars up to 2026, and 500+ DRHP patterns.
                </p>
              </div>

              {/* Suggested questions */}
              <button
                onClick={() => setShowSuggested((v) => !v)}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  background: 'none', border: 'none', cursor: 'pointer', padding: '0.5rem 0',
                  marginBottom: '0.75rem',
                }}
              >
                <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Suggested questions</span>
                {showSuggested ? <ChevronUp size={15} color="var(--text-muted)" /> : <ChevronDown size={15} color="var(--text-muted)" />}
              </button>

              {(showSuggested || true) && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.625rem' }}>
                  {SUGGESTED.map((q) => (
                    <button
                      key={q}
                      onClick={() => sendMessage(q)}
                      style={{
                        textAlign: 'left', padding: '0.875rem 1rem',
                        background: 'var(--bg-card)', border: '1.5px solid var(--border)',
                        borderRadius: '10px', cursor: 'pointer', fontSize: '0.8125rem',
                        color: 'var(--text-secondary)', lineHeight: 1.5, transition: 'all 150ms',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = 'var(--accent)';
                        e.currentTarget.style.background = 'var(--accent-light)';
                        e.currentTarget.style.color = 'var(--accent)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = 'var(--border)';
                        e.currentTarget.style.background = 'var(--bg-card)';
                        e.currentTarget.style.color = 'var(--text-secondary)';
                      }}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Message list */}
          {messages.map((msg) => (
            <div
              key={msg.id}
              style={{
                maxWidth: '760px', width: '100%',
                margin: msg.role === 'user' ? '0 0 0 auto' : '0 auto 0 0',
              }}
            >
              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
                {/* Avatar */}
                <div style={{
                  width: '34px', height: '34px', borderRadius: '50%', flexShrink: 0,
                  background: msg.role === 'user' ? 'var(--accent)' : 'var(--bg-elevated)',
                  border: '1.5px solid',
                  borderColor: msg.role === 'user' ? 'var(--accent)' : 'var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {msg.role === 'user'
                    ? <User size={16} color="white" />
                    : <Bot size={16} color="var(--accent)" />}
                </div>

                {/* Bubble */}
                <div style={{
                  flex: 1,
                  padding: '0.875rem 1.125rem',
                  borderRadius: msg.role === 'user' ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
                  background: msg.role === 'user' ? 'var(--accent)' : 'var(--bg-card)',
                  border: '1px solid',
                  borderColor: msg.role === 'user' ? 'transparent' : 'var(--border)',
                  color: msg.role === 'user' ? 'white' : 'var(--text-primary)',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
                }}>
                  {msg.role === 'user' ? (
                    <p style={{ margin: 0, fontSize: '0.9375rem', lineHeight: 1.65, whiteSpace: 'pre-wrap' }}>
                      {msg.content}
                    </p>
                  ) : (
                    <div style={{ fontSize: '0.9375rem' }}>
                      {renderMarkdown(msg.content)}
                    </div>
                  )}
                </div>
              </div>

              {/* Timestamp + sources */}
              <div style={{
                display: 'flex', gap: '0.75rem', alignItems: 'center',
                justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                marginTop: '0.25rem', paddingLeft: msg.role === 'user' ? 0 : '46px',
                paddingRight: msg.role === 'user' ? '46px' : 0,
              }}>
                <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
                  {formatTime(msg.timestamp)}
                </span>
                {msg.ragSources != null && msg.ragSources > 0 && msg.role === 'assistant' && (
                  <span style={{
                    fontSize: '0.6875rem', color: 'var(--accent)', fontWeight: 600,
                    background: 'var(--accent-light)', padding: '1px 6px', borderRadius: '99px',
                  }}>
                    {msg.ragSources} regulation{msg.ragSources !== 1 ? 's' : ''} cited
                  </span>
                )}
              </div>
            </div>
          ))}

          {/* Typing indicator */}
          {loading && (
            <div style={{ maxWidth: '760px', width: '100%' }}>
              <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                <div style={{
                  width: '34px', height: '34px', borderRadius: '50%',
                  background: 'var(--bg-elevated)', border: '1.5px solid var(--border)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  <Bot size={16} color="var(--accent)" />
                </div>
                <div style={{
                  padding: '0.875rem 1.125rem', background: 'var(--bg-card)',
                  border: '1px solid var(--border)', borderRadius: '4px 16px 16px 16px',
                  display: 'flex', gap: '5px', alignItems: 'center',
                }}>
                  {[0, 1, 2].map((i) => (
                    <span key={i} style={{
                      width: '7px', height: '7px', borderRadius: '50%',
                      background: 'var(--accent)', opacity: 0.7,
                      animation: `typing-dot 1.4s ease-in-out ${i * 0.2}s infinite`,
                    }} />
                  ))}
                </div>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* ── Input bar ────────────────────────────────────────────────── */}
        <div style={{
          borderTop: '1px solid var(--border)', padding: '1rem 1.25rem',
          background: 'var(--bg-card)', flexShrink: 0,
        }}>
          <div style={{
            maxWidth: '760px', margin: '0 auto',
            display: 'flex', gap: '0.75rem', alignItems: 'flex-end',
            background: 'var(--bg-base)', border: '1.5px solid var(--border)',
            borderRadius: '12px', padding: '0.5rem 0.75rem',
            transition: 'border-color 150ms',
          }}
            onFocusCapture={(e) => e.currentTarget.style.borderColor = 'var(--border-focus)'}
            onBlurCapture={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Ask about SEBI regulations, DRHP requirements, SME IPO process..."
              rows={1}
              style={{
                flex: 1, resize: 'none', background: 'transparent', border: 'none',
                outline: 'none', fontFamily: 'var(--font-sans)', fontSize: '0.9375rem',
                color: 'var(--text-primary)', lineHeight: 1.6,
                maxHeight: '160px', overflowY: 'auto', padding: '0.25rem 0',
              }}
            />
            <button
              onClick={() => sendMessage()}
              disabled={!input.trim() || loading}
              style={{
                background: input.trim() && !loading ? 'var(--accent)' : 'var(--bg-elevated)',
                border: 'none', borderRadius: '8px', padding: '0.5rem',
                cursor: input.trim() && !loading ? 'pointer' : 'not-allowed',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0, transition: 'background 150ms',
              }}
            >
              <Send size={17} color={input.trim() && !loading ? 'white' : 'var(--text-muted)'} />
            </button>
          </div>
          <p style={{ textAlign: 'center', fontSize: '0.6875rem', color: 'var(--text-muted)', margin: '0.5rem 0 0' }}>
            Shift+Enter for new line · Enter to send · Covers SEBI regulations up to 2026
          </p>
        </div>
      </div>

      <style>{`
        @keyframes typing-dot {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.7; }
          30% { transform: translateY(-6px); opacity: 1; }
        }
        .thread-delete-btn:hover { opacity: 1 !important; }
        div:hover > div > .thread-delete-btn { opacity: 0.6 !important; }
      `}</style>
    </div>
  );
};

export default CopilotPage;

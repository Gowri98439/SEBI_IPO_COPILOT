import React, { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { BookOpen, Plus, MessagesSquare, Sparkles } from 'lucide-react';
import api from '../api/client';
import { useChatContext, ChatMessage as ChatMessageType } from '../context/ChatContext';

import { ChatLayout } from '../components/chat/ChatLayout';
import { ChatHeader } from '../components/chat/ChatHeader';
import { ConversationList } from '../components/chat/ConversationList';
import { ChatMessage } from '../components/chat/ChatMessage';
import { StreamingStatus } from '../components/chat/StreamingStatus';
import { PromptComposer } from '../components/chat/PromptComposer';

const SUGGESTED = [
  'What is the minimum net tangible assets required for SME IPO?',
  'What are the 2024 SEBI amendments to SME IPO eligibility?',
  'Explain the lock-in requirements for promoters.',
  'What financial disclosures are mandatory in a DRHP?',
];

const CopilotPage: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const chat = useChatContext();

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

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

  const sendMessage = async () => {
    const content = input.trim();
    if (!content || loading || !workspaceId || !activeThread) return;
    setInput('');

    const userMsg: ChatMessageType = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    chat.addMessage(workspaceId, activeThread.id, userMsg);
    setLoading(true);

    const history = messages.map((m) => ({ role: m.role, content: m.content }));

    try {
      const data: any = await api.post(`/workspaces/${workspaceId}/copilot/chat`, {
        message: content,
        history,
      });
      const reply = data?.response ?? data?.message ?? 'No response received.';
      const botMsg: ChatMessageType = {
        id: `msg_${Date.now() + 1}`,
        role: 'assistant',
        content: reply,
        timestamp: new Date().toISOString(),
        ragSources: data?.rag_sources ?? 0,
      };
      chat.addMessage(workspaceId, activeThread.id, botMsg);
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ?? err?.message ?? 'Please check your connection and try again.';
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

  const handleStop = () => setLoading(false);

  const handleRegenerate = () => {
    if (messages.length >= 2) {
      const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
      if (lastUserMsg) setInput(lastUserMsg.content);
    }
  };

  // ── SIDEBAR ──────────────────────────────────────────────────────────────────
  const sidebarContent = (
    <div className="flex flex-col h-full bg-gray-50 border-r border-gray-200">
      {/* New Chat button */}
      <div className="p-3">
        <button
          className="w-full flex items-center justify-between px-3 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-xl font-medium text-[13px] transition-colors shadow-sm"
          onClick={() => { if (workspaceId) chat.newThread(workspaceId); }}
        >
          <span className="flex items-center gap-2">
            <MessagesSquare size={15} />
            New Chat
          </span>
          <Plus size={15} />
        </button>
      </div>

      {/* Thread history */}
      <ConversationList
        threads={threads}
        activeThreadId={activeThread?.id}
        onSelect={(id) => { if (workspaceId) chat.setActive(workspaceId, id); }}
        onDelete={(id) => { if (workspaceId) chat.deleteThread(workspaceId, id); }}
      />

      {/* Disclaimer */}
      <div className="p-3 text-[10px] text-gray-400 text-center border-t border-gray-200">
        SEBI Advisor is an AI tool. Verify all advice with qualified legal counsel.
      </div>
    </div>
  );

  // ── MAIN CHAT ─────────────────────────────────────────────────────────────────
  const mainContent = (
    <div className="flex flex-col h-full bg-white">
      {/* Fixed header */}
      <ChatHeader />

      {/* Scrollable message area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {messages.length === 0 ? (
          /* ── Empty state: welcome screen ─────────────────────────── */
          <div className="flex flex-col items-center justify-center min-h-full px-6 py-16">
            <div className="w-14 h-14 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center mb-5 shadow-sm">
              <BookOpen size={28} className="text-blue-600" />
            </div>
            <h1
              className="text-[26px] font-bold text-gray-900 mb-2 text-center"
              style={{ fontFamily: 'Inter, sans-serif' }}
            >
              SEBI Copilot
            </h1>
            <p
              className="text-gray-500 text-center text-[15px] leading-relaxed max-w-[480px] mb-10"
              style={{ fontFamily: 'Inter, sans-serif' }}
            >
              Ask anything about SEBI regulations, SME IPO processes, and DRHP drafting.
              Trained on ICDR 2018 and the latest 2026 amendments.
            </p>

            {/* Suggested prompts */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-[700px]">
              {SUGGESTED.map((q) => (
                <button
                  key={q}
                  onClick={() => setInput(q)}
                  className="group text-left px-4 py-3.5 rounded-xl border border-gray-200 bg-white hover:border-blue-400 hover:bg-blue-50/50 transition-all shadow-sm hover:shadow-md"
                >
                  <div className="flex items-start gap-2.5">
                    <Sparkles
                      size={14}
                      className="text-blue-400 mt-0.5 flex-shrink-0 group-hover:text-blue-600 transition-colors"
                    />
                    <p
                      className="text-[13px] text-gray-600 group-hover:text-gray-900 leading-relaxed font-medium transition-colors"
                      style={{ fontFamily: 'Inter, sans-serif' }}
                    >
                      {q}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* ── Messages thread ──────────────────────────────────────── */
          <div className="w-full">
            {/* Separator line with session label */}
            <div className="flex items-center gap-3 px-6 py-3">
              <div className="flex-1 h-px bg-gray-100" />
              <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">
                This session
              </span>
              <div className="flex-1 h-px bg-gray-100" />
            </div>

            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} onRegenerate={handleRegenerate} />
            ))}

            {loading && <StreamingStatus onStop={handleStop} />}
            <div ref={bottomRef} className="h-4" />
          </div>
        )}
      </div>

      {/* ── Pinned input at bottom ─────────────────────────────────── */}
      <div className="flex-shrink-0 border-t border-gray-100 bg-white px-4 pt-3 pb-2">
        <PromptComposer
          input={input}
          setInput={setInput}
          onSend={sendMessage}
          loading={loading}
        />
      </div>
    </div>
  );

  return (
    <div style={{ height: 'calc(100vh - 4rem)', margin: '-1.5rem' }}>
      <ChatLayout sidebarContent={sidebarContent} mainContent={mainContent} />
    </div>
  );
};

export default CopilotPage;

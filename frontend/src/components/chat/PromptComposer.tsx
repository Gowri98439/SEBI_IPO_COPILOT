import React, { useRef, useEffect, useState, KeyboardEvent } from 'react';
import { Send, Paperclip, Globe, Command, X } from 'lucide-react';

interface PromptComposerProps {
  input: string;
  setInput: (value: string) => void;
  onSend: () => void;
  loading: boolean;
}

export const PromptComposer: React.FC<PromptComposerProps> = ({
  input,
  setInput,
  onSend,
  loading,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [showSlashMenu, setShowSlashMenu] = useState(false);
  const [attachments, setAttachments] = useState<string[]>([]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
    if (input.endsWith('/')) {
      setShowSlashMenu(true);
    } else if (!input.includes('/')) {
      setShowSlashMenu(false);
    }
  }, [input]);

  const handleKey = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!loading && input.trim()) onSend();
    }
  };

  const handleSlashCommand = (cmd: string) => {
    setInput(input.slice(0, -1) + cmd + ' ');
    setShowSlashMenu(false);
    textareaRef.current?.focus();
  };

  const commands = [
    { cmd: '/compare', desc: 'Compare with previous DRHP' },
    { cmd: '/compliance', desc: 'Run SEBI compliance check' },
    { cmd: '/drhp', desc: 'Draft DRHP section' },
  ];

  return (
    <div className="relative w-full max-w-[760px] mx-auto mb-4">

      {/* Slash Commands Popover */}
      {showSlashMenu && (
        <div className="absolute bottom-full left-0 mb-2 w-64 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden z-10">
          <div className="px-3 py-2 text-[11px] font-semibold text-gray-400 uppercase tracking-wider border-b border-gray-100">
            Slash Commands
          </div>
          {commands.map((c) => (
            <button
              key={c.cmd}
              className="w-full text-left px-3 py-2.5 hover:bg-gray-50 flex items-center gap-2.5 transition-colors"
              onClick={() => handleSlashCommand(c.cmd)}
            >
              <Command size={13} className="text-blue-500" />
              <div>
                <div className="text-[13px] font-semibold text-gray-800">{c.cmd}</div>
                <div className="text-[11px] text-gray-400">{c.desc}</div>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Attachment tray */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2 px-1">
          {attachments.map((file, idx) => (
            <div
              key={idx}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-lg text-[12px] font-medium text-blue-700"
            >
              <Paperclip size={11} />
              {file}
              <button
                className="ml-1 text-blue-400 hover:text-red-500 transition-colors"
                onClick={() => setAttachments(attachments.filter((_, i) => i !== idx))}
              >
                <X size={11} />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input box */}
      <div className="flex flex-col bg-white border border-gray-300 rounded-2xl shadow-sm focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100 transition-all duration-200">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask SEBI Copilot... (Type '/' for commands)"
          rows={1}
          className="w-full bg-transparent border-none outline-none resize-none px-4 pt-4 pb-2 text-[15px] leading-relaxed text-gray-800 placeholder-gray-400 font-inter custom-scrollbar"
          style={{ maxHeight: '200px', fontFamily: 'Inter, sans-serif' }}
        />

        <div className="flex items-center justify-between px-3 pb-3 pt-1">
          {/* Left actions */}
          <div className="flex items-center gap-0.5">
            <button
              className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              title="Attach document"
              onClick={() => setAttachments([...attachments, 'Financials_Q4.pdf'])}
            >
              <Paperclip size={16} />
            </button>
            <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors flex items-center gap-1.5">
              <Globe size={16} />
              <span className="text-[12px] font-medium hidden sm:inline">Search Web</span>
            </button>
          </div>

          {/* Send button */}
          <button
            onClick={() => { if (!loading && input.trim()) onSend(); }}
            disabled={!input.trim() || loading}
            className={`p-2 rounded-xl flex items-center justify-center transition-all duration-200 ${
              input.trim() && !loading
                ? 'bg-blue-600 text-white hover:bg-blue-500 shadow-md hover:shadow-blue-200'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
            }`}
          >
            <Send size={16} />
          </button>
        </div>
      </div>

      {/* Disclaimer */}
      <p className="text-center mt-2 text-[11px] text-gray-400 font-inter">
        Copilot can make mistakes. Check important information.
      </p>
    </div>
  );
};

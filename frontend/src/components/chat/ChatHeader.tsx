import React from 'react';
import { useChatLayout } from './ChatLayout';
import { SidebarToggle } from './SidebarToggle';
import { Share, Settings, Zap, Database, CheckCircle2 } from 'lucide-react';

export const ChatHeader: React.FC = () => {
  const { isOpen, toggleSidebar } = useChatLayout();

  return (
    <header className="flex-shrink-0 h-14 flex items-center justify-between px-4 border-b border-gray-200 bg-white">
      <div className="flex items-center gap-3">
        <SidebarToggle isOpen={isOpen} toggle={toggleSidebar} />

        {/* Model & KB indicator */}
        <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-50 border border-gray-200 cursor-pointer hover:bg-gray-100 transition-colors">
          <span className="text-[13px] font-semibold text-gray-800">Groq LLaMA-3 70B</span>
          <span className="text-gray-300">·</span>
          <Database size={13} className="text-gray-400" />
          <span className="text-[12px] font-medium text-gray-500">SEBI Copilot KB</span>
          <span className="text-gray-300">·</span>
          <CheckCircle2 size={13} className="text-emerald-500" />
          <span className="text-[12px] font-medium text-emerald-600">Connected</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Token badge */}
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full border border-amber-300 bg-amber-50 text-amber-600">
          <Zap size={12} />
          <span className="text-[12px] font-semibold">1,024 tokens</span>
        </div>

        <button
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-700"
          title="Share Chat"
        >
          <Share size={17} />
        </button>
        <button
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-700"
          title="Settings"
        >
          <Settings size={17} />
        </button>
      </div>
    </header>
  );
};

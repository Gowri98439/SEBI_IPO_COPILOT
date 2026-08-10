import React, { useState } from 'react';
import { MessageSquare, MoreHorizontal, Trash2, Edit2, Archive, Pin } from 'lucide-react';
import { ChatThread } from '../../context/ChatContext';

interface ConversationItemProps {
  thread: ChatThread;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

export const ConversationItem: React.FC<ConversationItemProps> = ({
  thread,
  isActive,
  onSelect,
  onDelete,
}) => {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div
      className={`group relative flex items-center gap-2.5 px-3 py-2 my-0.5 rounded-lg cursor-pointer transition-all duration-150 ${
        isActive
          ? 'bg-blue-50 border border-blue-100'
          : 'hover:bg-gray-100 border border-transparent'
      }`}
      onClick={onSelect}
      onMouseLeave={() => setShowMenu(false)}
    >
      <MessageSquare
        size={14}
        className={`flex-shrink-0 ${isActive ? 'text-blue-600' : 'text-gray-400 group-hover:text-gray-500'}`}
      />

      <div className="flex-1 truncate pr-5 relative">
        <span
          className={`text-[13px] font-medium truncate block ${
            isActive ? 'text-blue-700 font-semibold' : 'text-gray-700'
          }`}
          style={{ fontFamily: 'Inter, sans-serif' }}
        >
          {thread.title || 'New Conversation'}
        </span>

        {/* More button — fades in on hover */}
        <div
          className={`absolute right-0 top-0 bottom-0 flex items-center transition-opacity duration-150 ${
            isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
          }`}
        >
          <button
            className={`p-1 rounded-md transition-colors ${
              isActive ? 'text-blue-500 hover:bg-blue-100' : 'text-gray-400 hover:bg-gray-200 hover:text-gray-600'
            }`}
            onClick={(e) => { e.stopPropagation(); setShowMenu(!showMenu); }}
          >
            <MoreHorizontal size={13} />
          </button>
        </div>
      </div>

      {/* Dropdown menu */}
      {showMenu && (
        <div className="absolute right-2 top-9 z-50 w-36 bg-white border border-gray-200 rounded-xl shadow-lg py-1 overflow-hidden">
          <button
            className="w-full text-left px-3 py-2 text-[12px] hover:bg-gray-50 text-gray-700 flex items-center gap-2 transition-colors"
            onClick={(e) => { e.stopPropagation(); setShowMenu(false); }}
          >
            <Pin size={11} className="text-gray-400" /> Pin Chat
          </button>
          <button
            className="w-full text-left px-3 py-2 text-[12px] hover:bg-gray-50 text-gray-700 flex items-center gap-2 transition-colors"
            onClick={(e) => { e.stopPropagation(); setShowMenu(false); }}
          >
            <Edit2 size={11} className="text-gray-400" /> Rename
          </button>
          <button
            className="w-full text-left px-3 py-2 text-[12px] hover:bg-gray-50 text-gray-700 flex items-center gap-2 transition-colors"
            onClick={(e) => { e.stopPropagation(); setShowMenu(false); }}
          >
            <Archive size={11} className="text-gray-400" /> Archive
          </button>
          <div className="border-t border-gray-100 my-0.5" />
          <button
            className="w-full text-left px-3 py-2 text-[12px] hover:bg-red-50 text-red-500 flex items-center gap-2 transition-colors"
            onClick={(e) => { e.stopPropagation(); onDelete(); setShowMenu(false); }}
          >
            <Trash2 size={11} /> Delete
          </button>
        </div>
      )}
    </div>
  );
};

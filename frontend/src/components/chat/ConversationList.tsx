import React, { useMemo } from 'react';
import { ChatThread } from '../../context/ChatContext';
import { ConversationItem } from './ConversationItem';

interface ConversationListProps {
  threads: ChatThread[];
  activeThreadId?: string;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

export const ConversationList: React.FC<ConversationListProps> = ({ threads, activeThreadId, onSelect, onDelete }) => {
  const groupedThreads = useMemo(() => {
    const groups: Record<string, ChatThread[]> = {
      'Today': [],
      'Yesterday': [],
      'Previous 7 Days': [],
      'Older': []
    };

    const now = new Date();
    now.setHours(0, 0, 0, 0);

    threads.forEach(thread => {
      const updated = new Date(thread.updatedAt);
      updated.setHours(0, 0, 0, 0);
      
      const diffTime = Math.abs(now.getTime() - updated.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

      if (diffDays === 0) {
        groups['Today'].push(thread);
      } else if (diffDays === 1) {
        groups['Yesterday'].push(thread);
      } else if (diffDays <= 7) {
        groups['Previous 7 Days'].push(thread);
      } else {
        groups['Older'].push(thread);
      }
    });

    // Remove empty groups
    return Object.entries(groups).filter(([_, groupThreads]) => groupThreads.length > 0);
  }, [threads]);

  return (
    <div className="flex-1 overflow-y-auto overflow-x-hidden p-2 custom-scrollbar">
      {groupedThreads.length === 0 && (
        <div className="text-center p-4 text-xs text-gray-500 mt-4">
          No conversations yet.
        </div>
      )}
      
      {groupedThreads.map(([groupName, groupThreads]) => (
        <div key={groupName} className="mb-6">
          <h3 className="px-3 text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5 sticky top-0 bg-gray-50 py-1 z-10">
            {groupName}
          </h3>
          <div>
            {groupThreads.map(thread => (
              <ConversationItem
                key={thread.id}
                thread={thread}
                isActive={thread.id === activeThreadId}
                onSelect={() => onSelect(thread.id)}
                onDelete={() => onDelete(thread.id)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

import React from 'react';
import { User, Bot } from 'lucide-react';
import { format } from 'date-fns';

export interface ChatMessageData {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

interface ChatMessageProps {
  message: ChatMessageData;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user';

  return (
    <div
      className={`flex gap-3 font-body ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-sm font-bold ${
          isUser
            ? 'bg-ipo-ai text-ipo-base shadow-sm'
            : 'bg-ipo-overlay border border-ipo-border text-ipo-text-secondary'
        }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      {/* Bubble */}
      <div className={`max-w-[75%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div
          className={`rounded-md px-4 py-3 shadow-sm ${
            isUser
              ? 'bg-ipo-ai text-ipo-base'
              : 'bg-ipo-elevated border border-ipo-border text-ipo-text'
          }`}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
            {message.isStreaming && (
              <span
                className="inline-block w-0.5 h-4 bg-current ml-0.5 align-middle animate-pulse"
              />
            )}
          </p>
        </div>
        <span className="text-[10px] uppercase font-bold tracking-wider font-data text-ipo-text-secondary mt-1.5 px-1">
          {format(message.timestamp, 'HH:mm')}
        </span>
      </div>
    </div>
  );
};

export default ChatMessage;

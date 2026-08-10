import React from 'react';
import { User, Bot } from 'lucide-react';
import { ChatMessage as ChatMessageType } from '../../context/ChatContext';
import { MessageActions } from './MessageActions';
import { EvidenceCard } from './EvidenceCard';

interface ChatMessageProps {
  message: ChatMessageType;
  onRegenerate?: () => void;
}

// Markdown renderer for AI responses
function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split('\n');
  const result: React.ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith('### ')) {
      result.push(
        <h4 key={i} className="mt-5 mb-2 font-semibold text-[15px] text-gray-900 font-inter">
          {line.slice(4)}
        </h4>
      );
    } else if (line.startsWith('## ')) {
      result.push(
        <h3 key={i} className="mt-5 mb-2 font-bold text-[16px] text-gray-900 font-inter">
          {line.slice(3)}
        </h3>
      );
    } else if (line.startsWith('# ')) {
      result.push(
        <h2 key={i} className="mt-5 mb-2 font-bold text-[18px] text-gray-900 font-inter">
          {line.slice(2)}
        </h2>
      );
    } else if (/^(\d+\.|-|\*) /.test(line)) {
      const listItems: string[] = [];
      const isOrdered = /^\d+\. /.test(line);
      while (i < lines.length && /^(\d+\.|-|\*) /.test(lines[i])) {
        listItems.push(lines[i].replace(/^(\d+\.|-|\*) /, ''));
        i++;
      }
      const Tag = isOrdered ? 'ol' : 'ul';
      result.push(
        <Tag
          key={i}
          className={`my-3 pl-5 flex flex-col gap-1.5 ${isOrdered ? 'list-decimal' : 'list-disc'}`}
        >
          {listItems.map((item, j) => (
            <li key={j} className="text-[15px] text-gray-700 leading-[1.7] font-inter">
              {formatInline(item)}
            </li>
          ))}
        </Tag>
      );
      continue;
    } else if (line.trim() === '') {
      result.push(<div key={i} className="h-1.5" />);
    } else {
      result.push(
        <p key={i} className="leading-[1.75] text-gray-700 text-[15px] font-inter my-1.5">
          {formatInline(line)}
        </p>
      );
    }
    i++;
  }
  return result;
}

function formatInline(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[ICDR[^\]]+\]|\[LODR[^\]]+\]|\[Reg[^\]]+\])/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**'))
      return (
        <strong key={i} className="text-gray-900 font-semibold">
          {part.slice(2, -2)}
        </strong>
      );
    if (part.startsWith('`') && part.endsWith('`'))
      return (
        <code
          key={i}
          className="bg-gray-100 border border-gray-200 px-1.5 py-0.5 rounded text-[0.83em] font-mono text-gray-800"
        >
          {part.slice(1, -1)}
        </code>
      );
    if (part.startsWith('[ICDR') || part.startsWith('[LODR') || part.startsWith('[Reg'))
      return (
        <span
          key={i}
          className="inline-flex items-center bg-blue-50 text-blue-700 rounded-md px-2 py-0.5 text-[0.78em] font-semibold border border-blue-100 mx-0.5"
        >
          {part}
        </span>
      );
    return part;
  });
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, onRegenerate }) => {
  const isUser = message.role === 'user';

  const mockSources =
    message.ragSources && message.ragSources > 0
      ? Array.from({ length: message.ragSources }).map(
          (_, i) => `SEBI ICDR Regulation 2018, Schedule VI, Part A, Clause ${i + 1}`
        )
      : [];

  return (
    <div className={`w-full flex py-5 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`flex gap-3 w-full max-w-[760px] px-6 ${
          isUser ? 'flex-row-reverse' : 'flex-row'
        }`}
      >
        {/* Avatar */}
        <div
          className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm ${
            isUser
              ? 'bg-blue-600 text-white'
              : 'bg-white text-blue-600 border border-gray-200'
          }`}
        >
          {isUser ? <User size={16} /> : <Bot size={16} />}
        </div>

        {/* Message Content */}
        <div className={`flex flex-col min-w-0 flex-1 ${isUser ? 'items-end' : 'items-start'}`}>
          {/* Role label */}
          <div
            className={`text-[12px] font-semibold mb-1.5 tracking-wide uppercase ${
              isUser ? 'text-gray-400' : 'text-blue-600'
            }`}
          >
            {isUser ? 'You' : 'SEBI Copilot'}
          </div>

          {/* Bubble / Content */}
          {isUser ? (
            <div className="bg-gray-900 text-white px-4 py-3 rounded-2xl rounded-tr-sm inline-block max-w-[90%] text-[15px] leading-[1.7] font-inter whitespace-pre-wrap shadow-sm">
              {message.content}
            </div>
          ) : (
            <div className="w-full">
              <div className="prose-sm text-gray-700">{renderMarkdown(message.content)}</div>

              {/* Evidence card */}
              {mockSources.length > 0 && (
                <EvidenceCard confidence={92} sources={mockSources} />
              )}

              {/* Action row */}
              <MessageActions content={message.content} onRegenerate={onRegenerate} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

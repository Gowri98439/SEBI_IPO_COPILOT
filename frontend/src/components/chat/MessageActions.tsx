import React, { useState } from 'react';
import { Copy, Check, ThumbsUp, ThumbsDown, RotateCcw } from 'lucide-react';

interface MessageActionsProps {
  content: string;
  onRegenerate?: () => void;
}

export const MessageActions: React.FC<MessageActionsProps> = ({ content, onRegenerate }) => {
  const [copied, setCopied] = useState(false);
  const [liked, setLiked] = useState<boolean | null>(null);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex items-center gap-1 mt-2 text-gray-400">
      <button 
        onClick={handleCopy}
        className="p-1.5 rounded-md hover:bg-gray-700/50 hover:text-gray-200 transition-colors"
        title="Copy message"
      >
        {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
      </button>

      {onRegenerate && (
        <button 
          onClick={onRegenerate}
          className="p-1.5 rounded-md hover:bg-gray-700/50 hover:text-gray-200 transition-colors"
          title="Regenerate response"
        >
          <RotateCcw size={14} />
        </button>
      )}

      <button 
        onClick={() => setLiked(true)}
        className={`p-1.5 rounded-md hover:bg-gray-700/50 transition-colors ${liked === true ? 'text-green-500' : 'hover:text-gray-200'}`}
        title="Helpful"
      >
        <ThumbsUp size={14} />
      </button>

      <button 
        onClick={() => setLiked(false)}
        className={`p-1.5 rounded-md hover:bg-gray-700/50 transition-colors ${liked === false ? 'text-red-500' : 'hover:text-gray-200'}`}
        title="Not helpful"
      >
        <ThumbsDown size={14} />
      </button>
    </div>
  );
};

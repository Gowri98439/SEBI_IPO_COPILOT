import React, { useState, useEffect } from 'react';
import { Bot, Square, BrainCircuit } from 'lucide-react';

interface StreamingStatusProps {
  onStop?: () => void;
}

export const StreamingStatus: React.FC<StreamingStatusProps> = ({ onStop }) => {
  const [statusText, setStatusText] = useState('Searching workspace documents...');

  useEffect(() => {
    const statuses = [
      'Searching workspace documents...',
      'Cross-referencing SEBI ICDR 2018...',
      'Synthesizing legal opinion...',
      'Generating response...',
    ];
    let i = 0;
    const interval = setInterval(() => {
      setStatusText(statuses[i]);
      i = (i + 1) % statuses.length;
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full flex py-5 justify-start">
      <div className="flex gap-3 w-full max-w-[760px] px-6">

        {/* Avatar */}
        <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 bg-white text-blue-600 border border-gray-200 shadow-sm">
          <Bot size={16} className="animate-pulse" />
        </div>

        {/* Status Content */}
        <div className="flex flex-col items-start">
          <div
            className="text-[12px] font-semibold mb-2 text-blue-600 uppercase tracking-wide"
            style={{ fontFamily: 'Inter, sans-serif' }}
          >
            SEBI Copilot
          </div>

          <div className="flex items-center gap-2.5 bg-gray-50 border border-gray-200 px-4 py-2.5 rounded-xl text-[13px] text-gray-600">
            <BrainCircuit size={15} className="text-blue-500 animate-pulse flex-shrink-0" />
            <span className="font-medium" style={{ fontFamily: 'Inter, sans-serif' }}>
              {statusText}
            </span>
            <span className="flex gap-1 ml-1">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '300ms' }} />
            </span>
          </div>

          {onStop && (
            <button
              onClick={onStop}
              className="mt-3 flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-gray-50 border border-gray-200 rounded-lg text-[12px] font-medium text-gray-600 transition-colors"
            >
              <Square size={10} fill="currentColor" />
              Stop generating
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

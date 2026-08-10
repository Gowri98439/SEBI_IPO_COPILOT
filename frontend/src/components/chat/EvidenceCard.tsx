import React, { useState } from 'react';
import { BookOpen, ChevronDown, ChevronUp, CheckCircle, AlertTriangle } from 'lucide-react';

interface EvidenceCardProps {
  confidence: number;
  sources: string[];
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({ confidence, sources }) => {
  const [expanded, setExpanded] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 mb-2 max-w-full rounded-lg border border-gray-200 overflow-hidden" style={{ borderColor: 'var(--border)' }}>
      <button 
        className="w-full flex items-center justify-between px-3 py-2 text-xs hover:bg-gray-50 transition-colors"
        style={{ background: 'var(--bg-card)' }}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <BookOpen size={14} className="text-blue-500" />
          <span className="font-semibold text-gray-700">{sources.length} SEBI Citations</span>
          <span className="px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-600 font-medium ml-2">
            {confidence}% Confidence
          </span>
        </div>
        {expanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
      </button>

      {expanded && (
        <div className="bg-gray-50 border-t border-gray-200 p-3 space-y-2" style={{ background: 'var(--bg-elevated)', borderColor: 'var(--border)' }}>
          {sources.map((source, idx) => (
            <div key={idx} className="text-xs text-gray-600 leading-relaxed flex items-start gap-2">
              <CheckCircle size={12} className="text-green-500 mt-0.5 flex-shrink-0" />
              <span>{source}</span>
            </div>
          ))}
          <div className="mt-2 pt-2 border-t border-[#333] flex items-center gap-1 text-[10px] text-yellow-500" style={{ borderColor: 'var(--border)' }}>
            <AlertTriangle size={10} />
            <span>AI-generated interpretations. Always verify with official SEBI gazettes.</span>
          </div>
        </div>
      )}
    </div>
  );
};

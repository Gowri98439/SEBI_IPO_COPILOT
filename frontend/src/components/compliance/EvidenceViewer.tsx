import React from 'react';
import { Brain, FileSearch, BarChart3 } from 'lucide-react';

interface EvidenceViewerProps {
  reasoning?: string;
  evidence?: string;
  source?: string;
  confidence?: number; // 0 – 1
}

const EvidenceViewer: React.FC<EvidenceViewerProps> = ({
  reasoning,
  evidence,
  source,
  confidence,
}) => {
  const confidencePct = confidence !== undefined ? Math.round(confidence * 100) : null;
  const confColor =
    confidencePct !== null
      ? confidencePct >= 80
        ? 'text-ipo-verified'
        : confidencePct >= 50
        ? 'text-ipo-attention'
        : 'text-ipo-critical'
      : 'text-ipo-text-secondary';
      
  const confBg =
    confidencePct !== null
      ? confidencePct >= 80
        ? 'bg-ipo-verified'
        : confidencePct >= 50
        ? 'bg-ipo-attention'
        : 'bg-ipo-critical'
      : 'bg-ipo-text-secondary';

  return (
    <div className="space-y-4 font-body">
      {/* AI Reasoning */}
      {reasoning && (
        <div
          className="bg-ipo-ai/5 border border-ipo-ai/20 rounded-md p-4"
        >
          <div className="flex items-center gap-2 mb-2 font-data">
            <Brain className="w-4 h-4 text-ipo-ai" />
            <span className="text-[10px] font-bold text-ipo-ai uppercase tracking-wider">
              AI Reasoning
            </span>
          </div>
          <p className="text-ipo-text-secondary text-sm leading-relaxed">{reasoning}</p>
        </div>
      )}

      {/* Document Evidence */}
      {evidence && (
        <div
          className="bg-ipo-overlay border border-ipo-border rounded-md p-4"
        >
          <div className="flex items-center gap-2 mb-2 font-data">
            <FileSearch className="w-4 h-4 text-ipo-text-secondary" />
            <span className="text-[10px] font-bold text-ipo-text-secondary uppercase tracking-wider">
              Document Evidence
            </span>
            {source && (
              <span className="ml-auto text-[10px] uppercase font-bold tracking-wider text-ipo-text-secondary bg-ipo-elevated px-2 py-0.5 rounded-sm border border-ipo-border">{source}</span>
            )}
          </div>
          <blockquote className="text-ipo-text-secondary text-sm leading-relaxed italic border-l-2 border-ipo-text-secondary/40 pl-3">
            "{evidence}"
          </blockquote>
        </div>
      )}

      {/* Confidence Score */}
      {confidencePct !== null && (
        <div
          className="flex items-center gap-3 font-data"
        >
          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-ipo-text-secondary" />
            <span className="text-[10px] font-bold uppercase tracking-wider text-ipo-text-secondary">Confidence</span>
          </div>
          <div className="flex-1 h-1.5 bg-ipo-overlay border border-ipo-border rounded-full overflow-hidden">
            <div
              style={{ width: `${confidencePct}%` }}
              className={`h-full rounded-full transition-all duration-300 ${confBg}`}
            />
          </div>
          <span className={`text-[10px] font-bold uppercase tracking-wider ${confColor}`}>{confidencePct}%</span>
        </div>
      )}

      {!reasoning && !evidence && (
        <p className="text-ipo-text-secondary text-xs italic">No detailed evidence available for this check.</p>
      )}
    </div>
  );
};

export default EvidenceViewer;

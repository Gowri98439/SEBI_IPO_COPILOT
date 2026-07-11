import React, { useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  Info,
  ChevronDown,
  ChevronUp,
  BookOpen,
  FileText,
} from 'lucide-react';

export type IssueSeverity = 'high' | 'medium' | 'low';

export interface ValidationIssue {
  id: string;
  severity: IssueSeverity;
  title: string;
  description: string;
  page?: number | string;
  sebi_rule?: string;
  suggestion?: string;
}

interface IssueCardProps {
  issue: ValidationIssue;
}

const SEVERITY_CONFIG: Record<
  IssueSeverity,
  {
    border: string;
    badge: string;
    icon: React.ElementType;
    iconColor: string;
    label: string;
  }
> = {
  high: {
    border: 'border-l-ipo-critical',
    badge: 'bg-ipo-critical/10 text-ipo-critical border-ipo-critical/20',
    icon: AlertCircle,
    iconColor: 'text-ipo-critical',
    label: 'High',
  },
  medium: {
    border: 'border-l-ipo-attention',
    badge: 'bg-ipo-attention/10 text-ipo-attention border-ipo-attention/20',
    icon: AlertTriangle,
    iconColor: 'text-ipo-attention',
    label: 'Medium',
  },
  low: {
    border: 'border-l-ipo-text-secondary',
    badge: 'bg-ipo-text-secondary/10 text-ipo-text-secondary border-ipo-border',
    icon: Info,
    iconColor: 'text-ipo-text-secondary',
    label: 'Low',
  },
};

const IssueCard: React.FC<IssueCardProps> = ({ issue }) => {
  const [expanded, setExpanded] = useState(false);
  const config = SEVERITY_CONFIG[issue.severity];
  const IconComponent = config.icon;

  return (
    <div className={`bg-ipo-elevated border border-ipo-border border-l-[3px] ${config.border} rounded-md shadow-sm overflow-hidden`}>
      <button
        onClick={() => setExpanded((p) => !p)}
        className="w-full flex items-start gap-3 p-4 text-left hover:bg-ipo-overlay transition-colors"
      >
        <div className="mt-0.5 flex-shrink-0">
          <IconComponent className={`w-4 h-4 ${config.iconColor}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1.5 font-data">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-sm text-[10px] uppercase font-bold tracking-wider border ${config.badge}`}
            >
              {config.label}
            </span>
            {issue.sebi_rule && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono bg-ipo-ai/10 text-ipo-ai border border-ipo-ai/20">
                <BookOpen className="w-3 h-3" />
                {issue.sebi_rule}
              </span>
            )}
            {issue.page !== undefined && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] uppercase font-bold tracking-wider bg-ipo-overlay text-ipo-text-secondary border border-ipo-border">
                <FileText className="w-3 h-3" />
                Page {issue.page}
              </span>
            )}
          </div>
          <p className="text-ipo-text text-sm font-semibold font-body">{issue.title}</p>
        </div>
        <div className="flex-shrink-0 text-ipo-text-secondary mt-0.5">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-0 ml-7 space-y-3 border-t border-ipo-border bg-ipo-base/30">
          <p className="text-ipo-text-secondary text-sm leading-relaxed mt-3 font-body">{issue.description}</p>
          {issue.suggestion && (
            <div className="bg-ipo-ai/5 border border-ipo-ai/20 rounded-md p-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-ipo-ai mb-1 font-data flex items-center gap-1">
                <span>💡</span> Suggestion
              </p>
              <p className="text-ipo-text-secondary text-sm leading-relaxed font-body">{issue.suggestion}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default IssueCard;

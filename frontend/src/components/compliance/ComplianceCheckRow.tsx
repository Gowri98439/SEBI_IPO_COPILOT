import React from 'react';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  ChevronDown,
  ChevronUp,
  Shield,
} from 'lucide-react';
import EvidenceViewer from './EvidenceViewer';

export type CheckStatus = 'pass' | 'fail' | 'warning' | 'pending';

export interface ComplianceCheck {
  id: string;
  regulation_code: string;
  regulation_name: string;
  status: CheckStatus;
  confidence?: number;
  reasoning?: string;
  evidence_excerpt?: string;
  evidence_source?: string;
  category?: string;
}

interface ComplianceCheckRowProps {
  check: ComplianceCheck;
}

const STATUS_CONFIG: Record<
  CheckStatus,
  { icon: React.ElementType; color: string; bg: string; label: string }
> = {
  pass: {
    icon: CheckCircle2,
    color: 'text-ipo-verified',
    bg: 'bg-ipo-verified/10 border-ipo-verified/20 text-ipo-verified',
    label: 'Pass',
  },
  fail: {
    icon: XCircle,
    color: 'text-ipo-critical',
    bg: 'bg-ipo-critical/10 border-ipo-critical/20 text-ipo-critical',
    label: 'Fail',
  },
  warning: {
    icon: AlertTriangle,
    color: 'text-ipo-attention',
    bg: 'bg-ipo-attention/10 border-ipo-attention/20 text-ipo-attention',
    label: 'Warning',
  },
  pending: {
    icon: Clock,
    color: 'text-ipo-text-secondary',
    bg: 'bg-ipo-overlay border-ipo-border text-ipo-text-secondary',
    label: 'Pending',
  },
};

const ComplianceCheckRow: React.FC<ComplianceCheckRowProps> = ({ check }) => {
  const [expanded, setExpanded] = React.useState(false);
  const config = STATUS_CONFIG[check.status];
  const StatusIcon = config.icon;

  return (
    <div
      className="bg-ipo-elevated border border-ipo-border rounded-md shadow-sm overflow-hidden font-body"
    >
      <button
        onClick={() => setExpanded((p) => !p)}
        className="w-full flex items-center gap-3 px-4 py-3.5 text-left hover:bg-ipo-overlay transition-colors"
      >
        {/* Status icon */}
        <StatusIcon className={`w-5 h-5 flex-shrink-0 ${config.color}`} />

        {/* Regulation code badge */}
        <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-sm text-[10px] uppercase tracking-wider font-bold font-data bg-ipo-ai/10 text-ipo-ai border border-ipo-ai/20 flex-shrink-0">
          <Shield className="w-3 h-3" />
          {check.regulation_code}
        </span>

        {/* Regulation name */}
        <p className="flex-1 text-ipo-text text-sm font-semibold min-w-0 truncate">
          {check.regulation_name}
        </p>

        {/* Status badge */}
        <span
          className={`px-2.5 py-0.5 rounded-sm text-[10px] uppercase font-bold tracking-wider font-data border flex-shrink-0 ${config.bg}`}
        >
          {config.label}
        </span>

        {/* Expand toggle */}
        <div className="text-ipo-text-secondary flex-shrink-0">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {expanded && (
        <div className="overflow-hidden border-t border-ipo-border bg-ipo-base/30">
          <div className="p-4">
            <EvidenceViewer
              reasoning={check.reasoning}
              evidence={check.evidence_excerpt}
              source={check.evidence_source}
              confidence={check.confidence}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default ComplianceCheckRow;

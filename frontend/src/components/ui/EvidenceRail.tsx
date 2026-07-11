import { useEvidenceRail } from '@/hooks/useEvidenceRail'
import { X, BookOpen, FileText, Shield, HelpCircle } from 'lucide-react'

const CONFIDENCE_BANDS = {
  strong: {
    label: 'Strong match',
    icon: '●',
    color: 'text-ipo-verified',
    bg: 'bg-ipo-verified/10',
    border: 'border-ipo-verified/30',
    description: 'High certainty — regulation directly addresses this disclosure',
  },
  partial: {
    label: 'Partial match — verify',
    icon: '■',
    color: 'text-ipo-attention',
    bg: 'bg-ipo-attention/10',
    border: 'border-ipo-attention/30',
    description: 'Moderate certainty — related regulation found, manual review recommended',
  },
  low: {
    label: 'Low match — likely gap',
    icon: '▲',
    color: 'text-ipo-critical',
    bg: 'bg-ipo-critical/10',
    border: 'border-ipo-critical/30',
    description: 'Low certainty — no clear regulation match, possible compliance gap',
  },
}

export default function EvidenceRail() {
  const { evidence, isOpen, clearEvidence } = useEvidenceRail()

  if (!isOpen || !evidence) {
    return null
  }

  const band = CONFIDENCE_BANDS[evidence.confidenceBand]

  return (
    <aside
      className="w-80 flex-shrink-0 border-l border-ipo-border bg-ipo-elevated overflow-y-auto flex flex-col"
      aria-label="Evidence panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-ipo-border">
        <h2 className="font-display text-sm font-semibold text-ipo-text">Evidence</h2>
        <button
          onClick={clearEvidence}
          className="p-1 rounded text-ipo-text-secondary hover:text-ipo-text transition-colors"
          aria-label="Close evidence panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 p-4 space-y-5">
        {/* Regulation Clause */}
        <section>
          <div className="flex items-center gap-1.5 mb-2">
            <BookOpen className="w-3.5 h-3.5 text-ipo-text-secondary" />
            <span className="text-xs font-semibold uppercase tracking-wider text-ipo-text-secondary font-body">
              Regulation Clause
            </span>
          </div>
          <div className="font-data text-xs text-ipo-ai font-semibold mb-1.5">
            {evidence.regulationId}
          </div>
          <p className="text-sm text-ipo-text leading-relaxed font-body">
            {evidence.regulationText}
          </p>
        </section>

        {/* Source Excerpt */}
        <section>
          <div className="flex items-center gap-1.5 mb-2">
            <FileText className="w-3.5 h-3.5 text-ipo-text-secondary" />
            <span className="text-xs font-semibold uppercase tracking-wider text-ipo-text-secondary font-body">
              Source Excerpt
            </span>
          </div>
          <blockquote className="border-l-2 border-ipo-border pl-3 py-1">
            <p className="text-sm text-ipo-text-secondary italic leading-relaxed font-body">
              "{evidence.sourceExcerpt}"
            </p>
          </blockquote>
          {(evidence.sourceDocument || evidence.sourcePage) && (
            <p className="text-xs text-ipo-text-secondary mt-1.5 font-data">
              {evidence.sourceDocument && <span>{evidence.sourceDocument}</span>}
              {evidence.sourcePage && <span> · Page {evidence.sourcePage}</span>}
            </p>
          )}
        </section>

        {/* Confidence Band */}
        <section>
          <div className="flex items-center gap-1.5 mb-2">
            <Shield className="w-3.5 h-3.5 text-ipo-text-secondary" />
            <span className="text-xs font-semibold uppercase tracking-wider text-ipo-text-secondary font-body">
              Retrieval Confidence
            </span>
          </div>
          <div className={`flex items-center gap-2 px-3 py-2 rounded-md border ${band.bg} ${band.border}`}>
            <span className={`text-base ${band.color}`}>{band.icon}</span>
            <div>
              <p className={`text-sm font-semibold font-body ${band.color}`}>{band.label}</p>
              <p className="text-xs text-ipo-text-secondary font-body mt-0.5">{band.description}</p>
            </div>
          </div>
        </section>

        {/* Why This Matters & Reasoning */}
        <section>
          <div className="flex items-center gap-1.5 mb-2">
            <HelpCircle className="w-3.5 h-3.5 text-ipo-text-secondary" />
            <span className="text-xs font-semibold uppercase tracking-wider text-ipo-text-secondary font-body">
              Analysis
            </span>
          </div>
          <div className="space-y-3">
            <div>
              <p className="text-xs text-ipo-text-secondary font-semibold mb-0.5">Why it matters</p>
              <p className="text-sm text-ipo-text leading-relaxed font-body">
                {evidence.whyItMatters}
              </p>
            </div>
            {evidence.reasoning && (
              <div>
                <p className="text-xs text-ipo-text-secondary font-semibold mb-0.5">AI Reasoning</p>
                <p className="text-sm text-ipo-text leading-relaxed font-body">
                  {evidence.reasoning}
                </p>
              </div>
            )}
            {evidence.citation && (
              <div>
                <p className="text-xs text-ipo-text-secondary font-semibold mb-0.5">Citation</p>
                <p className="text-xs text-ipo-ai font-mono">
                  {evidence.citation}
                </p>
              </div>
            )}
          </div>
        </section>
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-ipo-border">
        <p className="text-[10px] text-ipo-text-secondary font-data uppercase tracking-wider">
          AI-retrieved · Verify before filing
        </p>
      </div>
    </aside>
  )
}

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  AlertTriangle, AlertCircle, Info, CheckCircle2, Clock,
  RefreshCw, Zap, ChevronDown, ChevronRight, BookOpen,
  Lightbulb, FileText, Upload, ShieldAlert
} from 'lucide-react'
import { useDocuments, useValidationResult, useTriggerValidation } from '@/api/documents'
import AIReasoningStream from '@/components/ui/AIReasoningStream'
import { useEvidenceRail, type EvidenceData } from '@/hooks/useEvidenceRail'

/* ── Status config (icon + label + color) ──────────────────────────────── */
const SEVERITY_CFG = {
  high: { shape: '▲', label: 'Critical', color: 'text-ipo-critical', bg: 'bg-ipo-critical/10', border: 'border-ipo-critical/25' },
  medium: { shape: '■', label: 'Needs Review', color: 'text-ipo-attention', bg: 'bg-ipo-attention/10', border: 'border-ipo-attention/25' },
  low: { shape: '●', label: 'Advisory', color: 'text-ipo-ai', bg: 'bg-ipo-ai/10', border: 'border-ipo-ai/25' },
}

/* ── Confidence band from severity ─────────────────────────────────────── */
function getConfidenceBand(severity: string): 'strong' | 'partial' | 'low' {
  if (severity === 'high') return 'low'
  if (severity === 'medium') return 'partial'
  return 'strong'
}

/* ── Recommendation from description ───────────────────────────────────── */
function deriveRecommendation(description: string, rule: string): string {
  if (!description) return 'Review this item against SEBI ICDR requirements.'
  if (description.toLowerCase().includes('missing'))
    return `Add the missing information to satisfy ${rule || 'SEBI requirements'}.`
  if (description.toLowerCase().includes('incomplete'))
    return `Complete the disclosure as required by ${rule || 'SEBI ICDR'}.`
  return `Review and update this disclosure to satisfy ${rule || 'applicable SEBI regulations'}.`
}

/* ── Reasoning steps ───────────────────────────────────────────────────── */
const VALIDATION_STEPS = [
  { id: 's1', label: 'Reading uploaded document', duration: 700 },
  { id: 's2', label: 'Extracting entities', duration: 900 },
  { id: 's3', label: 'Identifying disclosures', duration: 800 },
  { id: 's4', label: 'Searching SEBI regulations', duration: 1100 },
  { id: 's5', label: 'Matching clauses', duration: 950 },
  { id: 's6', label: 'Evaluating compliance', duration: 800 },
  { id: 's7', label: 'Generating recommendations', duration: 700 },
]

/* ── Issue Card ────────────────────────────────────────────────────────── */
function IssueCard({ issue, isExpanded, onToggle, onShowEvidence }: {
  issue: any
  isExpanded: boolean
  onToggle: () => void
  onShowEvidence: () => void
}) {
  const sev = (issue.severity ?? 'low') as keyof typeof SEVERITY_CFG
  const cfg = SEVERITY_CFG[sev] ?? SEVERITY_CFG.low
  const recommendation = deriveRecommendation(issue.description, issue.rule)

  return (
    <div className={`border border-ipo-border rounded-md overflow-hidden ${isExpanded ? 'bg-ipo-overlay' : 'bg-ipo-elevated'}`}>
      <button className="w-full flex items-start gap-3 p-4 text-left" onClick={onToggle}>
        <span className={`text-sm ${cfg.color} mt-0.5`}>{cfg.shape}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-ipo-text font-body leading-snug">{issue.description}</p>
          {issue.rule && (
            <p className="text-xs text-ipo-text-secondary font-body mt-0.5">
              Rule: <span className="font-data text-ipo-ai">{issue.rule}</span>
              {issue.page && <span className="ml-2">· Page {issue.page}</span>}
            </p>
          )}
        </div>
        <span className={`badge-base ${cfg.bg} ${cfg.color} border ${cfg.border} flex-shrink-0`}>
          <span>{cfg.shape}</span> {cfg.label}
        </span>
        {isExpanded ? <ChevronDown className="w-3.5 h-3.5 text-ipo-text-secondary" /> : <ChevronRight className="w-3.5 h-3.5 text-ipo-text-secondary" />}
      </button>

      {isExpanded && (
        <div className="border-t border-ipo-border px-4 pb-4 pt-3 space-y-3">
          {/* Reason */}
          <div className="bg-ipo-base rounded-md p-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Info className="w-3 h-3 text-ipo-text-secondary" />
              <span className="text-xs font-semibold uppercase tracking-wider text-ipo-text-secondary font-body">Reason</span>
            </div>
            <p className="text-sm text-ipo-text leading-relaxed font-body">{issue.description}</p>
          </div>

          {/* Recommendation */}
          <div className="bg-ipo-ai/5 border border-ipo-ai/15 rounded-md p-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <Lightbulb className="w-3 h-3 text-ipo-ai" />
              <span className="text-xs font-semibold uppercase tracking-wider text-ipo-ai font-body">Recommendation</span>
            </div>
            <p className="text-sm text-ipo-text leading-relaxed font-body">{recommendation}</p>
          </div>

          {/* Evidence Rail link */}
          <button
            onClick={onShowEvidence}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-body font-medium text-ipo-ai bg-ipo-ai/10 border border-ipo-ai/25 hover:bg-ipo-ai/20 transition-colors"
          >
            <BookOpen className="w-3 h-3" />
            View in Evidence Rail
          </button>
        </div>
      )}
    </div>
  )
}

/* ── Validation Results ────────────────────────────────────────────────── */
function ValidationResults({ docId }: { docId: string }) {
  const { data: realResult, isLoading } = useValidationResult(docId)
  const triggerValidation = useTriggerValidation(docId)
  const [expanded, setExpanded] = useState<number | null>(null)
  const { setEvidence } = useEvidenceRail()

  const result = realResult

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="w-6 h-6 border-2 border-ipo-ai/30 border-t-ipo-ai rounded-full animate-spin" />
      </div>
    )
  }

  if (!result) {
    return (
      <div className="bg-ipo-elevated border border-ipo-border rounded-lg p-8 text-center">
        <Zap className="w-8 h-8 text-ipo-text-secondary mx-auto mb-3" />
        <p className="text-sm text-ipo-text-secondary font-body mb-4">No validation has been run on this document yet.</p>
        <button
          onClick={() => triggerValidation.mutate(undefined)}
          disabled={triggerValidation.isPending}
          className="mx-auto flex items-center gap-2 bg-ipo-ai hover:bg-ipo-ai/80 text-white text-sm font-body font-semibold px-4 py-2 rounded-md transition-colors"
        >
          <Zap className="w-4 h-4" /> Run AI Validation
        </button>
      </div>
    )
  }

  if (result.status === 'pending' || result.status === 'running') {
    return (
      <div className="bg-ipo-elevated border border-ipo-border rounded-lg">
        <AIReasoningStream
          steps={VALIDATION_STEPS}
          title="Analyzing Document"
          subtitle="Running AI validation against SEBI ICDR Regulations…"
          onComplete={() => {}}
        />
      </div>
    )
  }

  const issues = result.issues ?? []
  const missing = result.missing_info ?? []
  const highCount = issues.filter((i: any) => i.severity === 'high').length
  const medCount = issues.filter((i: any) => i.severity === 'medium').length

  const handleShowEvidence = (issue: any) => {
    const evidence: EvidenceData = {
      regulationId: issue.rule || 'SEBI ICDR',
      regulationText: issue.rule ? `Regulation ${issue.rule} — SEBI ICDR 2018` : 'General SEBI ICDR requirement',
      sourceExcerpt: issue.description,
      confidenceBand: getConfidenceBand(issue.severity),
      whyItMatters: deriveRecommendation(issue.description, issue.rule),
      sourcePage: issue.page,
    }
    setEvidence(evidence)
  }

  return (
    <div className="space-y-5">
      {/* AI Summary */}
      {result.summary && (
        <div className="bg-ipo-elevated border border-ipo-border rounded-lg p-5">
          <div className="flex items-center gap-2 mb-2">
            <div className="border-l-2 border-ipo-ai h-4" />
            <span className="text-xs font-semibold uppercase tracking-wider text-ipo-ai font-body">AI-drafted Summary</span>
          </div>
          <p className="text-sm text-ipo-text leading-relaxed font-body">{result.summary}</p>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Issues', value: issues.length, shape: '▲', color: 'text-ipo-text' },
          { label: 'Critical', value: highCount, shape: '▲', color: 'text-ipo-critical' },
          { label: 'Needs Review', value: medCount, shape: '■', color: 'text-ipo-attention' },
          { label: 'Missing', value: missing.length, shape: '◌', color: 'text-ipo-text-secondary' },
        ].map((s) => (
          <div key={s.label} className="bg-ipo-elevated border border-ipo-border rounded-md p-3 text-center">
            <p className={`font-data text-xl font-bold ${s.color}`}>{s.value}</p>
            <p className="text-xs text-ipo-text-secondary font-body mt-0.5"><span>{s.shape}</span> {s.label}</p>
          </div>
        ))}
      </div>

      {/* Issues list */}
      {issues.length > 0 && (
        <div>
          <h3 className="font-display text-sm font-semibold text-ipo-text mb-2 flex items-center gap-2">
            Issues Found ({issues.length})
            <span className="text-ipo-text-secondary font-body font-normal text-xs">— click to expand</span>
          </h3>
          <div className="space-y-1.5">
            {issues.map((issue: any, i: number) => (
              <IssueCard
                key={i}
                issue={issue}
                isExpanded={expanded === i}
                onToggle={() => setExpanded(expanded === i ? null : i)}
                onShowEvidence={() => handleShowEvidence(issue)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Missing info */}
      {missing.length > 0 && (
        <div>
          <h3 className="font-display text-sm font-semibold text-ipo-text mb-2 flex items-center gap-2">
            <span className="text-ipo-attention">■</span>
            Missing Disclosures ({missing.length})
          </h3>
          <div className="bg-ipo-elevated border border-ipo-border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ipo-border bg-ipo-overlay">
                  <th className="text-left text-xs text-ipo-text-secondary font-body font-semibold px-4 py-2.5 uppercase tracking-wide">Field</th>
                  <th className="text-left text-xs text-ipo-text-secondary font-body font-semibold px-4 py-2.5 uppercase tracking-wide">Section</th>
                  <th className="text-left text-xs text-ipo-text-secondary font-body font-semibold px-4 py-2.5 uppercase tracking-wide">Required By</th>
                </tr>
              </thead>
              <tbody>
                {missing.map((item: any, i: number) => (
                  <tr key={i} className="border-b border-ipo-border hover:bg-ipo-overlay transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-ipo-text font-body font-medium">{item.field}</p>
                      {item.description && <p className="text-ipo-text-secondary text-xs font-body mt-0.5">{item.description}</p>}
                    </td>
                    <td className="px-4 py-3 text-ipo-text-secondary text-xs font-body">{item.section}</td>
                    <td className="px-4 py-3">
                      <span className="font-data text-ipo-ai text-xs">{item.required_by}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {issues.length === 0 && missing.length === 0 && (
        <div className="bg-ipo-elevated border border-ipo-verified/20 rounded-lg p-8 text-center">
          <CheckCircle2 className="w-8 h-8 text-ipo-verified mx-auto mb-3" />
          <p className="text-ipo-text font-display font-semibold">● Verified — Document passed all checks</p>
          <p className="text-sm text-ipo-text-secondary font-body mt-1">No issues or missing disclosures detected.</p>
        </div>
      )}
    </div>
  )
}

/* ── Main Page ─────────────────────────────────────────────────────────── */
export default function ValidationPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const { data: rawDocuments = [] } = useDocuments(workspaceId!)
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null)

  const documents = rawDocuments
  const activeDocId = selectedDoc ?? documents[0]?.id ?? null

  return (
    <div className="p-6 space-y-5 max-w-5xl">
      <div>
        <h1 className="font-display text-xl font-semibold text-ipo-text mb-1">AI Document Validation</h1>
        <p className="text-sm text-ipo-text-secondary font-body">
          Evidence-based validation against SEBI ICDR regulations — every finding traceable to source
        </p>
      </div>

      {documents.length === 0 ? (
        <div className="bg-ipo-elevated border border-ipo-border rounded-lg p-8 text-center">
          <Upload className="w-10 h-10 text-ipo-text-secondary mx-auto mb-3" />
          <p className="text-ipo-text font-display font-semibold mb-1">No documents uploaded yet</p>
          <p className="text-sm text-ipo-text-secondary font-body">Upload documents first to run AI validation.</p>
        </div>
      ) : (
        <>
          {/* Document selector */}
          <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
            {documents.map((doc: any) => (
              <button
                key={doc.id}
                onClick={() => setSelectedDoc(doc.id)}
                className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-body font-medium transition-colors whitespace-nowrap border flex-shrink-0 ${
                  activeDocId === doc.id
                    ? 'bg-ipo-ai/15 border-ipo-ai/30 text-ipo-text'
                    : 'bg-ipo-elevated border-ipo-border text-ipo-text-secondary hover:border-ipo-text-secondary/30'
                }`}
              >
                {doc.status === 'validated' && <><span className="text-ipo-verified">●</span> <CheckCircle2 className="w-3.5 h-3.5 text-ipo-verified" /></>}
                {doc.status === 'processing' && <><span className="text-ipo-attention">■</span> <RefreshCw className="w-3.5 h-3.5 text-ipo-attention animate-spin" /></>}
                {(doc.status === 'uploaded' || doc.status === 'pending') && <><span className="text-ipo-text-secondary">◌</span> <Clock className="w-3.5 h-3.5 text-ipo-text-secondary" /></>}
                <span className="max-w-[160px] truncate">{doc.name}</span>
              </button>
            ))}
          </div>

          {activeDocId && <ValidationResults docId={activeDocId} />}
        </>
      )}
    </div>
  )
}

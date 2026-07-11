import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  PenLine, CheckCircle2, XCircle, MessageSquare,
  ChevronRight, BookOpen, Zap, AlertTriangle, Sparkles
} from 'lucide-react'
import { useForm } from 'react-hook-form'
import { motion, AnimatePresence } from 'framer-motion'
import { useDraftReviews, useCreateDraftReview } from '@/api/reviews'
import { apiClient } from '@/api/client'
import { formatDate } from '@/utils/formatters'
import AIReasoningStream from '@/components/ui/AIReasoningStream'
import { useEvidenceRail, type EvidenceData } from '@/hooks/useEvidenceRail'

const SECTIONS = [
  'Risk Factors', 'Business Description', 'Industry Overview',
  'Financial Information', 'Management Discussion & Analysis',
  'Promoter Background', 'Objects of the Issue', 'Capital Structure',
  'Corporate Governance', 'Legal Disclosures',
]

/* ── Status config ─────────────────────────────────────────────────────── */
const SEVERITY_CFG = {
  high: { shape: '▲', label: 'Critical', color: 'text-ipo-critical', bg: 'bg-ipo-critical/10', border: 'border-ipo-critical/25' },
  medium: { shape: '■', label: 'Needs Review', color: 'text-ipo-attention', bg: 'bg-ipo-attention/10', border: 'border-ipo-attention/25' },
  low: { shape: '●', label: 'Advisory', color: 'text-ipo-ai', bg: 'bg-ipo-ai/10', border: 'border-ipo-ai/25' },
}

const REVIEW_STEPS = [
  { id: 'dr1', label: 'Reading draft section', duration: 700 },
  { id: 'dr2', label: 'Matching SEBI disclosure requirements', duration: 1000 },
  { id: 'dr3', label: 'Identifying compliance gaps', duration: 900 },
  { id: 'dr4', label: 'Generating suggestions', duration: 800 },
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 15 },
  visible: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 24 } }
}

export default function DraftReviewPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const [selectedSection, setSelectedSection] = useState(SECTIONS[0])
  const [activeReviewId, setActiveReviewId] = useState<string | null>(null)
  const [showReasoning, setShowReasoning] = useState(false)
  const { setEvidence } = useEvidenceRail()

  const { data: rawReviews = [], refetch } = useDraftReviews(workspaceId!)
  const createReview = useCreateDraftReview()
  const reviews = rawReviews

  const { register, handleSubmit, reset, formState: { errors } } = useForm<{ draft_content: string }>()

  const onSubmit = async (data: { draft_content: string }) => {
    setShowReasoning(true)
    const review = await createReview.mutateAsync({
      workspace_id: workspaceId!,
      section: selectedSection,
      draft_content: data.draft_content,
    })
    setActiveReviewId(review.id)
    reset()
    setTimeout(() => {
      refetch()
      setShowReasoning(false)
    }, 4000)
  }

  const handleUpdateStatus = async (reviewId: string, status: string) => {
    try {
      await apiClient.patch(`/drafts/${reviewId}`, { status })
      refetch()
    } catch (e) {
      console.error(e)
    }
  }

  const activeReview = activeReviewId
    ? reviews.find((r) => r.id === activeReviewId)
    : reviews[0] ?? null
  const feedbackRaw = activeReview?.ai_feedback
  const feedback = Array.isArray(feedbackRaw)
    ? feedbackRaw
    : (feedbackRaw as any)?.feedback ?? []

  const handleShowEvidence = (fb: any) => {
    const evidence: EvidenceData = {
      regulationId: fb.ref_rule || 'SEBI ICDR',
      regulationText: fb.ref_rule ? `SEBI Regulation ${fb.ref_rule.replace(/_/g, ' ')}` : 'SEBI ICDR Disclosure Requirement',
      sourceExcerpt: fb.suggestion || fb.issue,
      confidenceBand: fb.severity === 'high' ? 'low' : fb.severity === 'medium' ? 'partial' : 'strong',
      whyItMatters: fb.issue,
    }
    setEvidence(evidence)
  }

  return (
    <motion.div 
      initial="hidden" 
      animate="visible" 
      variants={containerVariants} 
      className="p-6 space-y-6 max-w-6xl mx-auto"
    >
      <motion.div variants={itemVariants}>
        <h1 className="font-display text-2xl font-bold text-ipo-text mb-2 bg-gradient-to-r from-ipo-text to-ipo-text-secondary bg-clip-text text-transparent">AI Draft Review</h1>
        <p className="text-sm text-ipo-text-secondary font-body max-w-2xl">
          Submit offer document sections for clause-by-clause AI compliance review. 
          Our models automatically map your draft against SEBI ICDR 2018 requirements.
        </p>
      </motion.div>

      {/* AI Reasoning overlay */}
      <AnimatePresence mode="wait">
        {showReasoning && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-white border shadow-panel border-ipo-ai/20 rounded-xl overflow-hidden"
          >
            <AIReasoningStream
              steps={REVIEW_STEPS}
              title="Analyzing Draft Section"
              subtitle={`Validating ${selectedSection} against current regulatory frameworks…`}
              onComplete={() => setShowReasoning(false)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {!showReasoning && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Submit Form */}
          <div className="space-y-6">
            <motion.div variants={itemVariants} className="bg-white/60 backdrop-blur-md border shadow-sm border-ipo-border rounded-xl p-6 space-y-5">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-ipo-ai" />
                <h2 className="font-display text-base font-semibold text-ipo-text">Submit for Review</h2>
              </div>

              {/* Section selector */}
              <div>
                <label className="block text-[11px] font-body font-bold text-ipo-text-secondary mb-3 uppercase tracking-wider">Target Section</label>
                <div className="flex flex-wrap gap-2">
                  {SECTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => setSelectedSection(s)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-body font-medium transition-all duration-200 border ${
                        selectedSection === s
                          ? 'bg-ipo-ai border-ipo-ai text-white shadow-md shadow-ipo-ai/20 scale-105'
                          : 'bg-white border-ipo-border text-ipo-text-secondary hover:text-ipo-text hover:border-ipo-text-secondary/30 hover:bg-gray-50'
                      }`}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div>
                  <label className="block text-[11px] font-body font-bold text-ipo-text-secondary mb-3 uppercase tracking-wider">Draft Content</label>
                  <textarea
                    {...register('draft_content', { required: "Draft content is required", minLength: { value: 50, message: "Draft content must be at least 50 characters for AI analysis" } })}
                    placeholder={`Paste your draft ${selectedSection} content here for AI review…`}
                    rows={10}
                    className={`w-full bg-white border ${errors.draft_content ? 'border-ipo-critical' : 'border-ipo-border'} rounded-xl px-4 py-3 text-ipo-text placeholder-ipo-text-secondary/40 text-sm font-body focus:outline-none focus:ring-2 focus:ring-ipo-ai/30 focus:border-ipo-ai resize-none transition-all duration-200 shadow-sm`}
                  />
                  <AnimatePresence>
                    {errors.draft_content && (
                      <motion.div 
                        initial={{ opacity: 0, height: 0, y: -10 }} 
                        animate={{ opacity: 1, height: 'auto', y: 0 }} 
                        exit={{ opacity: 0, height: 0, y: -10 }}
                        className="flex items-center gap-1.5 text-ipo-critical mt-2 text-xs font-medium"
                      >
                        <AlertTriangle className="w-3.5 h-3.5" />
                        {errors.draft_content.message}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                <motion.button
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.98 }}
                  type="submit"
                  disabled={createReview.isPending}
                  className="w-full bg-gradient-to-r from-ipo-ai to-indigo-500 hover:from-indigo-600 hover:to-indigo-500 text-white shadow-lg shadow-ipo-ai/25 font-body font-semibold py-3 rounded-xl transition-all flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {createReview.isPending ? (
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <><Zap className="w-4 h-4" /> Run Compliance Review</>
                  )}
                </motion.button>
              </form>
            </motion.div>

            {/* Previous Reviews */}
            {reviews.length > 0 && (
              <motion.div variants={itemVariants} className="bg-white border shadow-sm border-ipo-border rounded-xl p-5 space-y-3">
                <h3 className="font-display text-[11px] font-bold text-ipo-text-secondary uppercase tracking-wider mb-2">Review History</h3>
                <div className="space-y-2">
                  {reviews.map((r) => (
                    <button
                      key={r.id}
                      onClick={() => setActiveReviewId(r.id)}
                      className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-all border group ${
                        activeReviewId === r.id
                          ? 'bg-indigo-50/50 border-ipo-ai/30 shadow-sm'
                          : 'bg-white border-transparent hover:border-ipo-border hover:bg-gray-50'
                      }`}
                    >
                      <div className={`p-2 rounded-md ${activeReviewId === r.id ? 'bg-ipo-ai/10 text-ipo-ai' : 'bg-gray-100 text-gray-500 group-hover:bg-gray-200'}`}>
                        <PenLine className="w-4 h-4 flex-shrink-0" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-body font-medium truncate ${activeReviewId === r.id ? 'text-ipo-ai' : 'text-ipo-text'}`}>{r.section}</p>
                        <p className="text-ipo-text-secondary text-xs font-data mt-0.5">{formatDate(r.created_at)}</p>
                      </div>
                      <ChevronRight className={`w-4 h-4 ${activeReviewId === r.id ? 'text-ipo-ai' : 'text-gray-400 group-hover:text-gray-600'} transition-transform ${activeReviewId === r.id ? 'translate-x-1' : ''}`} />
                    </button>
                  ))}
                </div>
              </motion.div>
            )}
          </div>

          {/* Right: Feedback Panel */}
          <motion.div variants={itemVariants} className="space-y-6 h-full">
            {activeReview ? (
              <div className="bg-white shadow-panel border border-ipo-border rounded-xl p-6 space-y-6 h-full flex flex-col">
                <div className="flex items-center justify-between pb-4 border-b border-gray-100">
                  <div>
                    <h2 className="font-display text-lg font-bold text-ipo-text">
                      Analysis: {activeReview.section}
                    </h2>
                    <p className="text-xs text-gray-500 font-data mt-1">{formatDate(activeReview.created_at)}</p>
                  </div>
                  <span className={`badge-base border font-data text-xs px-3 py-1.5 rounded-full ${
                    activeReview.status === 'reviewed'
                      ? 'bg-indigo-50 text-ipo-ai border-indigo-200'
                      : activeReview.status === 'accepted'
                      ? 'bg-emerald-50 text-ipo-verified border-emerald-200'
                      : 'bg-gray-50 text-ipo-text-secondary border-gray-200'
                  }`}>
                    {activeReview.status === 'reviewed' ? '■ Reviewed' :
                     activeReview.status === 'accepted' ? '● Accepted' : '◌ ' + activeReview.status}
                  </span>
                </div>

                {/* Draft content preview */}
                {activeReview.draft_content && (
                  <div className="bg-gray-50/80 border border-gray-100 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-1.5">
                        <PenLine className="w-3.5 h-3.5 text-gray-500" />
                        <span className="text-[10px] font-body font-bold text-gray-500 uppercase tracking-widest">Source Text</span>
                      </div>
                    </div>
                    <div className="relative">
                      <p className="text-sm text-gray-700 font-body leading-relaxed line-clamp-3 relative z-10">{activeReview.draft_content}</p>
                      <div className="absolute inset-x-0 bottom-0 h-8 bg-gradient-to-t from-gray-50/80 to-transparent z-20"></div>
                    </div>
                  </div>
                )}

                {(activeReview.status === 'pending' || feedback.length === 0) ? (
                  <div className="flex-1 flex flex-col items-center justify-center py-16 gap-4">
                    <div className="relative">
                      <div className="w-12 h-12 border-4 border-indigo-100 rounded-full"></div>
                      <div className="w-12 h-12 border-4 border-ipo-ai border-t-transparent rounded-full animate-spin absolute inset-0"></div>
                    </div>
                    <div className="text-center">
                      <p className="text-ipo-text font-semibold">Running Compliance Checks</p>
                      <p className="text-gray-500 text-sm mt-1">Cross-referencing ICDR 2018...</p>
                    </div>
                  </div>
                ) : (
                  <div className="flex-1 overflow-y-auto pr-2 space-y-4 no-scrollbar">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="h-px bg-gray-200 flex-1"></div>
                      <span className="text-[10px] font-data text-ipo-ai font-medium uppercase tracking-widest px-2 bg-indigo-50 rounded-full py-0.5 border border-indigo-100">AI Feedback Detected</span>
                      <div className="h-px bg-gray-200 flex-1"></div>
                    </div>

                    {(feedback as any[]).map((fb, i) => {
                      const sev = (fb.severity ?? 'low') as keyof typeof SEVERITY_CFG
                      const cfg = SEVERITY_CFG[sev] ?? SEVERITY_CFG.low
                      
                      return (
                        <motion.div
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: i * 0.1 }}
                          key={i}
                          className={`relative overflow-hidden bg-white border ${cfg.border} shadow-sm rounded-xl p-5 space-y-3 group hover:shadow-md transition-shadow`}
                        >
                          {/* Accent left border */}
                          <div className={`absolute left-0 top-0 bottom-0 w-1 ${cfg.bg.replace('/10', '/50')}`}></div>
                          
                          <div className="flex items-start justify-between gap-4">
                            <p className="text-sm text-ipo-text font-body font-semibold leading-snug">{fb.issue}</p>
                            <span className={`badge-base ${cfg.bg} ${cfg.color} rounded-full border-none font-bold tracking-wide flex-shrink-0 px-2.5 py-1 shadow-sm`}>
                              {cfg.label}
                            </span>
                          </div>
                          
                          <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                            <div className="flex gap-2 items-start">
                              <MessageSquare className="w-4 h-4 text-ipo-ai mt-0.5 flex-shrink-0" />
                              <p className="text-sm text-gray-700 font-body leading-relaxed">{fb.suggestion}</p>
                            </div>
                          </div>
                          
                          <div className="flex items-center justify-between pt-2">
                            {fb.ref_rule ? (
                              <button
                                onClick={() => handleShowEvidence(fb)}
                                className="flex items-center gap-1.5 text-xs font-data text-ipo-ai hover:text-indigo-800 transition-colors bg-indigo-50 px-2 py-1 rounded border border-indigo-100 hover:border-indigo-200"
                              >
                                <BookOpen className="w-3.5 h-3.5" />
                                {fb.ref_rule}
                              </button>
                            ) : <div></div>}
                            
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleUpdateStatus(activeReview.id, 'accepted')}
                                className="flex items-center gap-1 text-[11px] font-bold tracking-wide uppercase text-ipo-verified bg-emerald-50 px-3 py-1.5 rounded-md hover:bg-emerald-100 transition-colors border border-emerald-100"
                              >
                                <CheckCircle2 className="w-3.5 h-3.5" /> Accept
                              </button>
                              <button
                                onClick={() => handleUpdateStatus(activeReview.id, 'rejected')}
                                className="flex items-center gap-1 text-[11px] font-bold tracking-wide uppercase text-ipo-critical bg-red-50 px-3 py-1.5 rounded-md hover:bg-red-100 transition-colors border border-red-100"
                              >
                                <XCircle className="w-3.5 h-3.5" /> Reject
                              </button>
                            </div>
                          </div>
                        </motion.div>
                      )
                    })}
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-full min-h-[400px] bg-gradient-to-b from-white to-gray-50 border border-ipo-border rounded-xl shadow-sm relative overflow-hidden">
                {/* Decorative background elements */}
                <div className="absolute top-10 left-10 w-32 h-32 bg-indigo-100 rounded-full mix-blend-multiply filter blur-3xl opacity-50 animate-pulse"></div>
                <div className="absolute bottom-10 right-10 w-32 h-32 bg-emerald-100 rounded-full mix-blend-multiply filter blur-3xl opacity-50 animate-pulse" style={{ animationDelay: '2s' }}></div>
                
                <div className="relative z-10 flex flex-col items-center">
                  <div className="w-16 h-16 bg-white shadow-sm border border-gray-100 rounded-2xl flex items-center justify-center mb-5 transform -rotate-6">
                    <PenLine className="w-8 h-8 text-ipo-ai" />
                  </div>
                  <h3 className="font-display text-lg font-bold text-ipo-text mb-2">No Review Selected</h3>
                  <p className="text-gray-500 text-sm font-body text-center max-w-xs">
                    Select a section and submit your draft content on the left to generate an AI-powered compliance analysis.
                  </p>
                </div>
              </div>
            )}
          </motion.div>
        </div>
      )}
    </motion.div>
  )
}

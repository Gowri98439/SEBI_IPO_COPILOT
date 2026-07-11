import { useEffect, useState } from 'react'
import { CheckCircle2, Circle, Loader2 } from 'lucide-react'

export interface ReasoningStep {
  id: string
  label: string
  duration?: number
}

interface Props {
  steps: ReasoningStep[]
  onComplete?: () => void
  subtitle?: string
  title?: string
}

type StepStatus = 'pending' | 'running' | 'done'

/**
 * AIReasoningStream
 * Renders a numbered, streaming AI reasoning trace.
 * No spring animations. Respects prefers-reduced-motion via CSS.
 */
export default function AIReasoningStream({ steps, onComplete, subtitle, title }: Props) {
  const [statuses, setStatuses] = useState<StepStatus[]>(
    steps.map(() => 'pending')
  )

  useEffect(() => {
    let cancelled = false

    const runStep = async (index: number) => {
      if (cancelled || index >= steps.length) {
        if (!cancelled && onComplete) onComplete()
        return
      }

      setStatuses((prev) => {
        const next = [...prev]
        next[index] = 'running'
        return next
      })

      await new Promise((r) => setTimeout(r, steps[index].duration ?? 900))
      if (cancelled) return

      setStatuses((prev) => {
        const next = [...prev]
        next[index] = 'done'
        return next
      })

      runStep(index + 1)
    }

    runStep(0)
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const allDone = statuses.every((s) => s === 'done')

  return (
    <div className="flex flex-col items-center justify-center py-12 px-6">
      {/* Status indicator */}
      <div className="mb-6">
        <div className="w-14 h-14 rounded-md bg-ipo-overlay border border-ipo-border flex items-center justify-center">
          {allDone ? (
            <CheckCircle2 className="w-6 h-6 text-ipo-verified" />
          ) : (
            <Loader2 className="w-6 h-6 text-ipo-ai animate-spin" />
          )}
        </div>
      </div>

      {/* Title */}
      <h3 className="font-display text-ipo-text font-semibold text-lg mb-1">
        {title ?? 'AI Analysis in Progress'}
      </h3>
      {subtitle && (
        <p className="text-ipo-text-secondary text-sm mb-6 text-center max-w-sm font-body">{subtitle}</p>
      )}

      {/* Numbered steps */}
      <div className="w-full max-w-sm space-y-2">
        {steps.map((step, i) => {
          const status = statuses[i]
          return (
            <div
              key={step.id}
              className={`flex items-center gap-3 transition-opacity ${
                status === 'pending' ? 'opacity-30' : 'opacity-100'
              }`}
            >
              {/* Step number / status icon */}
              <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center">
                {status === 'done' && (
                  <CheckCircle2 className="w-4 h-4 text-ipo-verified" />
                )}
                {status === 'running' && (
                  <Loader2 className="w-4 h-4 text-ipo-ai animate-spin" />
                )}
                {status === 'pending' && (
                  <span className="text-xs font-data text-ipo-text-secondary">{i + 1}</span>
                )}
              </div>

              {/* Label */}
              <span
                className={`text-sm font-body transition-colors ${
                  status === 'done'
                    ? 'text-ipo-text-secondary'
                    : status === 'running'
                    ? 'text-ipo-text font-medium'
                    : 'text-ipo-text-secondary/60'
                }`}
              >
                {step.label}
              </span>

              {/* Running indicator */}
              {status === 'running' && (
                <span className="text-ipo-ai text-xs font-data ml-auto">
                  analyzing…
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

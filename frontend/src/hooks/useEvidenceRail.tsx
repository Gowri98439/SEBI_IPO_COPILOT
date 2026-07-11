import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

export interface EvidenceData {
  /** Regulation clause ID, e.g. ICDR_REG_26 */
  regulationId: string
  /** Full text of the regulation clause */
  regulationText: string
  /** Excerpt from the source document that was matched */
  sourceExcerpt: string
  /** Confidence band: 'strong' | 'partial' | 'low' */
  confidenceBand: 'strong' | 'partial' | 'low'
  /** One-line explanation of why this matters */
  whyItMatters: string
  /** Source document name, if available */
  sourceDocument?: string
  /** Page number, if available */
  sourcePage?: number
  /** AI Reasoning for why this is compliant or not */
  reasoning?: string
  /** Official legal citation */
  citation?: string
}

interface EvidenceRailContextType {
  evidence: EvidenceData | null
  isOpen: boolean
  setEvidence: (data: EvidenceData) => void
  clearEvidence: () => void
  toggleRail: () => void
}

const EvidenceRailContext = createContext<EvidenceRailContextType>({
  evidence: null,
  isOpen: false,
  setEvidence: () => {},
  clearEvidence: () => {},
  toggleRail: () => {},
})

export function EvidenceRailProvider({ children }: { children: ReactNode }) {
  const [evidence, setEvidenceState] = useState<EvidenceData | null>(null)
  const [isOpen, setIsOpen] = useState(false)

  const setEvidence = useCallback((data: EvidenceData) => {
    setEvidenceState(data)
    setIsOpen(true)
  }, [])

  const clearEvidence = useCallback(() => {
    setEvidenceState(null)
    setIsOpen(false)
  }, [])

  const toggleRail = useCallback(() => {
    setIsOpen((prev) => !prev)
  }, [])

  return (
    <EvidenceRailContext.Provider value={{ evidence, isOpen, setEvidence, clearEvidence, toggleRail }}>
      {children}
    </EvidenceRailContext.Provider>
  )
}

export function useEvidenceRail() {
  return useContext(EvidenceRailContext)
}

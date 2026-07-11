import { useState } from 'react'
import { BookOpen, ExternalLink, ShieldAlert, Loader2 } from 'lucide-react'
import api from '@/api/client'
import { useQuery } from '@tanstack/react-query'

interface InteractiveCitationProps {
  rule: string
}

export default function InteractiveCitation({ rule }: InteractiveCitationProps) {
  const [isOpen, setIsOpen] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['ragSearch', rule],
    queryFn: async () => {
      const res = await api.get(`/api/v1/copilot/rag-search?q=${encodeURIComponent(rule)}`)
      return res.data
    },
    enabled: isOpen,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  return (
    <div className="relative inline-block font-body">
      <button
        onClick={(e) => {
          e.stopPropagation()
          setIsOpen(!isOpen)
        }}
        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-sm transition-colors font-data uppercase tracking-wider ${
          isOpen
            ? 'bg-ipo-ai/20 text-ipo-ai border border-ipo-ai/30'
            : 'bg-ipo-overlay hover:bg-ipo-ai/10 text-ipo-text-secondary hover:text-ipo-ai border border-ipo-border hover:border-ipo-ai/20'
        }`}
      >
        <BookOpen className="w-3 h-3" />
        <span className="text-[10px] font-bold">{rule}</span>
      </button>

      {isOpen && (
        <>
          {/* Backdrop to close on click outside */}
          <div
            className="fixed inset-0 z-40"
            onClick={(e) => {
              e.stopPropagation()
              setIsOpen(false)
            }}
          />
          {/* Popover */}
          <div
            onClick={(e) => e.stopPropagation()}
            className="absolute left-0 top-full mt-2 z-50 w-80 bg-ipo-elevated border border-ipo-border rounded-md shadow-panel overflow-hidden"
          >
            <div className="bg-ipo-overlay border-b border-ipo-border px-3 py-2 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-ipo-attention" />
              <span className="text-ipo-text text-xs font-semibold">SEBI Regulation Source</span>
              <a
                href="#"
                className="ml-auto flex items-center gap-1 text-ipo-text-secondary hover:text-ipo-text transition-colors"
              >
                <span className="text-[10px] uppercase font-bold tracking-wider font-data">View</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <div className="p-4 max-h-64 overflow-y-auto custom-scrollbar">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center py-6 gap-2">
                  <Loader2 className="w-5 h-5 text-ipo-ai animate-spin" />
                  <span className="text-ipo-text-secondary text-xs">Retrieving from SEBI Corpus...</span>
                </div>
              ) : isError ? (
                <div className="text-ipo-critical text-xs text-center py-4 font-semibold">
                  Failed to fetch regulation text.
                </div>
              ) : data ? (
                <div className="space-y-3">
                  <div className="inline-block bg-ipo-overlay border border-ipo-border px-2 py-1 rounded-sm text-ipo-text-secondary font-data font-bold text-[10px] uppercase tracking-wider">
                    {data.regulation_id}
                  </div>
                  <p className="text-ipo-text-secondary text-xs leading-relaxed">
                    {data.content}
                  </p>
                </div>
              ) : null}
            </div>
          </div>
        </>
      )}
    </div>
  )
}

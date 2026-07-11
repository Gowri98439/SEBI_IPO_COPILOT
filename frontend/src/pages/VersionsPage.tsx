import React from 'react'
import { useParams } from 'react-router-dom'
import { History, Download, FileText, User, Calendar, GitBranch } from 'lucide-react'
import { useDocuments, useDocumentVersions } from '@/api/documents'
import { formatDate } from '@/utils/formatters'

function VersionTimeline({ docId, docName }: { docId: string; docName: string }) {
  const { data: versions = [] } = useDocumentVersions(docId)

  if (versions.length === 0) return null

  return (
    <div className="space-y-3">
      <p className="text-ipo-text-secondary text-sm font-semibold flex items-center gap-2">
        <FileText className="w-4 h-4" />
        {docName}
      </p>
      <div className="relative pl-6">
        <div className="absolute left-[9px] top-2 bottom-2 w-px bg-ipo-border" />
        {versions.map((v) => (
          <div
            key={v.id}
            className="relative mb-4 last:mb-0"
          >
            <div className="absolute -left-[19px] top-4 w-2.5 h-2.5 rounded-full bg-ipo-base border-[2px] border-ipo-text-secondary" />
            <div className="bg-ipo-elevated border border-ipo-border hover:border-ipo-text-secondary rounded-xl p-4 transition-colors shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="bg-ipo-overlay text-ipo-text-secondary text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-md border border-ipo-border font-data">
                      v{v.version_number}
                    </span>
                    <p className="text-ipo-text text-sm font-semibold">Version {v.version_number}</p>
                  </div>
                  {v.change_summary && (
                    <p className="text-ipo-text-secondary text-sm mt-1">{v.change_summary}</p>
                  )}
                  <div className="flex items-center gap-4 mt-3">
                    <div className="flex items-center gap-1.5 text-ipo-text-secondary text-xs font-data">
                      <Calendar className="w-3.5 h-3.5" />
                      {formatDate(v.created_at)}
                    </div>
                    {v.created_by && (
                      <div className="flex items-center gap-1.5 text-ipo-text-secondary text-xs font-data">
                        <User className="w-3.5 h-3.5" />
                        <span className="font-mono">{v.created_by.slice(0, 8)}...</span>
                      </div>
                    )}
                  </div>
                </div>
                <a
                  href={`/api/v1/documents/${docId}/versions/${v.id}/download`}
                  className="flex items-center gap-1.5 text-xs bg-ipo-overlay hover:bg-ipo-border/50 text-ipo-text px-3 py-1.5 rounded-md transition-colors border border-ipo-border font-semibold flex-shrink-0"
                >
                  <Download className="w-3.5 h-3.5" /> Download
                </a>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function VersionsPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const { data: documents = [] } = useDocuments(workspaceId!)

  const docsWithVersions = documents.filter(d => d.status === 'validated' || d.status === 'processing')

  return (
    <div className="p-6 space-y-6 font-body">
      <div>
        <h1 className="text-2xl font-bold font-display text-ipo-text mb-1">Version & Revision Tracking</h1>
        <p className="text-ipo-text-secondary text-sm">Complete audit trail of all document versions and revisions</p>
      </div>

      {documents.length === 0 ? (
        <div className="text-center py-20 bg-ipo-elevated border border-ipo-border rounded-xl border-dashed">
          <History className="w-10 h-10 text-ipo-text-secondary mx-auto mb-3" />
          <p className="text-ipo-text-secondary text-sm">No documents uploaded yet. Upload documents to track versions.</p>
        </div>
      ) : (
        <div className="bg-ipo-elevated border border-ipo-border rounded-xl p-6 space-y-8 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <GitBranch className="w-5 h-5 text-ipo-text-secondary" />
            <h2 className="text-ipo-text font-semibold font-display">Document Version History</h2>
          </div>
          {documents.map((doc) => (
            <VersionTimeline key={doc.id} docId={doc.id} docName={doc.name} />
          ))}
          {docsWithVersions.length === 0 && (
            <div className="text-center py-8">
              <p className="text-ipo-text-secondary text-sm">No version history available yet. Versions are created when documents are validated and updated.</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

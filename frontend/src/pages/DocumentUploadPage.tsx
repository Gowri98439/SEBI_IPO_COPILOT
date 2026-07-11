import React, { useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { Upload, FileText, CheckCircle2, AlertCircle, Clock, Zap, X } from 'lucide-react'
import { useDocuments, useUploadDocument } from '@/api/documents'
import { apiClient } from '@/api/client'
import { formatFileSize, formatDate } from '@/utils/formatters'

const DOC_TYPES = [
  { value: 'financial_statement', label: 'Financial Statement' },
  { value: 'prospectus_draft', label: 'Prospectus Draft' },
  { value: 'auditor_report', label: 'Auditor Report' },
  { value: 'legal_opinion', label: 'Legal Opinion' },
  { value: 'shareholding_pattern', label: 'Shareholding Pattern' },
  { value: 'other', label: 'Other Document' },
]

export default function DocumentUploadPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>()
  const [dragActive, setDragActive] = useState(false)
  const [selectedType, setSelectedType] = useState('financial_statement')
  const [uploading, setUploading] = useState<string[]>([])

  const { data: documents = [], refetch } = useDocuments(workspaceId!)
  const uploadDoc = useUploadDocument(workspaceId!)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const handleFiles = useCallback(async (files: FileList | null) => {
    if (!files?.length) return
    setErrorMsg(null)
    for (const file of Array.from(files)) {
      setUploading((p) => [...p, file.name])
      try {
        const form = new FormData()
        form.append('file', file)
        form.append('doc_type', selectedType)
        await uploadDoc.mutateAsync(form)
        await refetch()
      } catch (e: any) {
        const msg = e?.response?.data?.detail || e?.message || 'Upload failed'
        setErrorMsg(`Failed to upload "${file.name}": ${msg}`)
        console.error('Upload failed:', e)
      } finally {
        setUploading((p) => p.filter((n) => n !== file.name))
      }
    }
  }, [selectedType, uploadDoc, refetch])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const handleValidate = async (docId: string) => {
    try {
      await apiClient.post(`/documents/${docId}/validate`)
      await refetch()
    } catch (e) {
      console.error('Validation failed:', e)
    }
  }

  const statusIcon = (status: string) => {
    if (status === 'validated') return <CheckCircle2 className="w-3.5 h-3.5" />
    if (status === 'processing') return <Clock className="w-3.5 h-3.5 animate-spin" />
    if (status === 'failed') return <AlertCircle className="w-3.5 h-3.5" />
    return <Clock className="w-3.5 h-3.5" />
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold font-display text-ipo-text mb-1">Document Upload</h1>
        <p className="text-ipo-text-secondary text-sm">Upload IPO-related documents for AI validation and compliance analysis</p>
      </div>

      {/* Doc type selector */}
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-ipo-text-secondary mb-2 font-data">Document Type</label>
        <div className="flex flex-wrap gap-2">
          {DOC_TYPES.map((t) => (
            <button
              key={t.value}
              onClick={() => setSelectedType(t.value)}
              className={`px-4 py-2 rounded-md text-sm font-semibold transition-colors border ${
                selectedType === t.value
                  ? 'bg-ipo-text text-ipo-base border-ipo-text'
                  : 'bg-ipo-overlay border-ipo-border text-ipo-text-secondary hover:text-ipo-text hover:border-ipo-text-secondary'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Drop Zone */}
      <label
        htmlFor="file-input"
        onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        className={`flex flex-col items-center justify-center w-full h-52 border-2 border-dashed rounded-xl cursor-pointer transition-colors bg-ipo-overlay group ${
          dragActive ? 'border-ipo-text bg-ipo-border/50' : 'border-ipo-border hover:border-ipo-text-secondary'
        }`}
      >
        <div className="flex flex-col items-center gap-4">
          <div className={`w-12 h-12 rounded-lg flex items-center justify-center transition-colors border ${
            dragActive ? 'bg-ipo-text text-ipo-base border-ipo-text' : 'bg-ipo-elevated border-ipo-border text-ipo-text-secondary group-hover:text-ipo-text'
          }`}>
            <Upload className="w-5 h-5" />
          </div>
          <div className="text-center">
            <p className={`font-semibold ${dragActive ? 'text-ipo-text' : 'text-ipo-text'}`}>
              {dragActive ? 'Drop files here' : 'Drag & drop files or click to browse'}
            </p>
            <p className="text-ipo-text-secondary text-xs mt-1 font-data">PDF, DOCX up to 50MB each</p>
          </div>
        </div>
        <input
          id="file-input"
          type="file"
          multiple
          accept=".pdf,.docx,.doc"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </label>

      {/* Error Banner */}
      {errorMsg && (
        <div className="flex items-start gap-3 bg-red-50 border border-red-200 text-red-700 rounded-xl p-4">
          <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <p className="text-sm flex-1">{errorMsg}</p>
          <button onClick={() => setErrorMsg(null)} className="flex-shrink-0">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Uploading Progress */}
      {uploading.length > 0 && (
        <div className="space-y-3">
          {uploading.map((name) => (
            <div
              key={name}
              className="bg-ipo-elevated border border-ipo-border rounded-xl p-4 flex items-center gap-4 shadow-sm"
            >
              <div className="w-5 h-5 border-2 border-ipo-border border-t-ipo-text rounded-full animate-spin flex-shrink-0" />
              <div className="flex-1">
                <p className="text-ipo-text text-sm font-semibold">{name}</p>
                <div className="w-full bg-ipo-overlay rounded-full h-1 mt-2 overflow-hidden">
                  <div className="bg-ipo-text h-1 rounded-full animate-pulse w-full" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Documents List */}
      {documents.length > 0 && (
        <div>
          <h2 className="text-base font-semibold font-display text-ipo-text mb-4">Uploaded Documents ({documents.length})</h2>
          <div className="space-y-3">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="bg-ipo-elevated border border-ipo-border rounded-xl p-5 flex items-center gap-4 shadow-sm"
              >
                <div className="w-10 h-10 bg-ipo-overlay border border-ipo-border rounded-md flex items-center justify-center flex-shrink-0">
                  <FileText className="w-5 h-5 text-ipo-text-secondary" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-ipo-text font-semibold truncate text-sm">{doc.name}</p>
                  <p className="text-ipo-text-secondary text-xs mt-0.5 font-data">
                    {DOC_TYPES.find(t => t.value === doc.doc_type)?.label} • {formatFileSize(doc.file_size)} • {formatDate(doc.created_at)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <div className={`flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1.5 rounded-md border uppercase tracking-wider font-data ${
                    doc.status === 'validated' ? 'bg-ipo-verified/10 text-ipo-verified border-ipo-verified/20' :
                    doc.status === 'processing' ? 'bg-ipo-attention/10 text-ipo-attention border-ipo-attention/20' :
                    doc.status === 'failed' ? 'bg-ipo-critical/10 text-ipo-critical border-ipo-critical/20' :
                    'bg-ipo-overlay text-ipo-text-secondary border-ipo-border'
                  }`}>
                    {statusIcon(doc.status)}
                    {doc.status}
                  </div>
                  {(doc.status === 'uploaded' || doc.status === 'failed') && (
                    <button
                      onClick={() => handleValidate(doc.id)}
                      className="flex items-center gap-1.5 bg-ipo-text hover:bg-ipo-text-secondary text-ipo-base text-xs font-semibold px-3 py-1.5 rounded-md transition-colors"
                    >
                      <Zap className="w-3.5 h-3.5" /> Validate
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {documents.length === 0 && uploading.length === 0 && (
        <div className="text-center py-12 bg-ipo-elevated border border-ipo-border rounded-xl border-dashed">
          <FileText className="w-8 h-8 text-ipo-text-secondary mx-auto mb-3" />
          <p className="text-ipo-text-secondary text-sm">No documents uploaded yet. Start by uploading your IPO documents above.</p>
        </div>
      )}
    </div>
  )
}

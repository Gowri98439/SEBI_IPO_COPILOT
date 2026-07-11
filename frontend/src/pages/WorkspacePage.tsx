import React, { useState, useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { UploadCloud, FileText, X, CheckCircle, Clock, XCircle, Trash2 } from 'lucide-react';
import { useWorkspace } from '@/api/workspaces';
import { useDocuments } from '@/api/documents';
import api from '../api/client';

const STATUS_MAP: Record<string, { label: string; badge: string; icon: React.FC<any> }> = {
  pending:   { label: 'Pending',   badge: 'badge-neutral',  icon: Clock },
  validated: { label: 'Validated', badge: 'badge-success',  icon: CheckCircle },
  failed:    { label: 'Failed',    badge: 'badge-danger',   icon: XCircle },
  processing:{ label: 'Processing',badge: 'badge-accent',   icon: Clock },
};

interface UploadItem {
  id: string;
  name: string;
  size: number;
  progress: 'uploading' | 'done' | 'error';
  error?: string;
}

export default function WorkspacePage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data: workspace } = useWorkspace(workspaceId!);
  const { data: documents = [] } = useDocuments(workspaceId!);

  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState<UploadItem[]>([]);

  const handleDragOver = useCallback((e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); }, []);
  const handleDragLeave = useCallback((e: React.DragEvent) => { e.preventDefault(); setIsDragging(false); }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length) await uploadFiles(files);
  }, [workspaceId]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) await uploadFiles(Array.from(e.target.files));
    e.target.value = '';
  };

  const uploadFiles = async (files: File[]) => {
    const items: UploadItem[] = files.map((f) => ({
      id: Math.random().toString(36).slice(2),
      name: f.name,
      size: f.size,
      progress: 'uploading',
    }));
    setUploading((prev) => [...prev, ...items]);

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const item = items[i];
      const formData = new FormData();
      formData.append('file', file);
      try {
        await api.post(`/workspaces/${workspaceId}/documents`, formData);
        setUploading((prev) => prev.map((u) => u.id === item.id ? { ...u, progress: 'done' } : u));
      } catch (err: any) {
        const msg = err.response?.data?.detail || 'Upload failed';
        setUploading((prev) => prev.map((u) => u.id === item.id ? { ...u, progress: 'error', error: msg } : u));
      }
    }
    void qc.invalidateQueries({ queryKey: ['documents', workspaceId] });
  };

  const removeUploadItem = (id: string) => setUploading((prev) => prev.filter((u) => u.id !== id));

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Documents</h1>
          <p className="page-subtitle">
            {workspace?.name ?? 'Loading...'} &mdash; Upload and manage your IPO filing documents
          </p>
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => fileInputRef.current?.click()}>
          <UploadCloud size={15} /> Upload Files
        </button>
      </div>

      {/* Upload Zone */}
      <div
        className={`upload-zone${isDragging ? ' dragging' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{ marginBottom: '1.75rem', cursor: 'pointer' }}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.doc,.xlsx,.xls,.csv"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <UploadCloud size={36} color={isDragging ? 'var(--accent)' : 'var(--text-muted)'} strokeWidth={1.5} style={{ marginBottom: '0.75rem' }} />
        <p style={{ margin: '0 0 0.25rem', fontWeight: 600, color: 'var(--text-primary)', fontSize: '1rem' }}>
          {isDragging ? 'Release to upload' : 'Drag and drop files here'}
        </p>
        <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          Supports PDF, DOCX, XLSX &mdash; or click to browse
        </p>
      </div>

      {/* Upload Progress */}
      {uploading.length > 0 && (
        <div className="card" style={{ marginBottom: '1.75rem' }}>
          <div className="card-header">
            <h3 style={{ margin: 0, fontSize: '0.9375rem', fontWeight: 700 }}>Uploading Files</h3>
          </div>
          <div style={{ padding: '0.75rem 1.5rem' }}>
            {uploading.map((item) => (
              <div key={item.id} style={{
                display: 'flex', alignItems: 'center', gap: '0.875rem',
                padding: '0.625rem 0', borderBottom: '1px solid var(--border)',
              }}>
                <FileText size={18} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ margin: 0, fontSize: '0.875rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.name}</p>
                  <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>{formatSize(item.size)}</p>
                </div>
                {item.progress === 'uploading' && <div className="spinner" />}
                {item.progress === 'done' && <CheckCircle size={18} color="var(--success)" />}
                {item.progress === 'error' && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--danger)', maxWidth: '180px' }}>{item.error}</span>
                )}
                <button
                  onClick={() => removeUploadItem(item.id)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '4px', color: 'var(--text-muted)', display: 'flex' }}
                >
                  <X size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Documents Table */}
      <div className="card">
        <div className="card-header">
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>
            Filed Documents
            <span style={{ marginLeft: '0.625rem', fontSize: '0.8125rem', fontWeight: 500, color: 'var(--text-muted)' }}>
              ({documents.length})
            </span>
          </h2>
        </div>
        {documents.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Document Name</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Uploaded</th>
                  <th style={{ width: '48px' }}></th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc: any) => {
                  const status = STATUS_MAP[doc.status] ?? STATUS_MAP['pending'];
                  return (
                    <tr key={doc.id}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
                          <FileText size={16} color="var(--text-muted)" style={{ flexShrink: 0 }} />
                          <span style={{ fontWeight: 500 }}>{doc.name}</span>
                        </div>
                      </td>
                      <td>
                        <span className="badge badge-neutral">{doc.doc_type ?? 'Document'}</span>
                      </td>
                      <td>
                        <span className={`badge ${status.badge}`}>
                          <status.icon size={11} strokeWidth={2.5} />
                          {status.label}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                        {new Date(doc.created_at).toLocaleDateString('en-IN')}
                      </td>
                      <td>
                        <button
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: '4px', display: 'flex' }}
                          title="Delete document"
                        >
                          <Trash2 size={15} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ padding: '3.5rem 2rem', textAlign: 'center' }}>
            <UploadCloud size={40} color="#CBD5E1" strokeWidth={1.5} style={{ marginBottom: '1rem' }} />
            <p style={{ margin: '0 0 0.375rem', fontWeight: 600, color: 'var(--text-primary)' }}>No documents uploaded yet</p>
            <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              Upload your DRHP, financial statements, and supporting documents above
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

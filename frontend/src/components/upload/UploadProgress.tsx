import React from 'react';
import { CheckCircle2, XCircle, Loader2, FileText, X } from 'lucide-react';

export type UploadStatus = 'uploading' | 'processing' | 'complete' | 'error';

export interface UploadFileItem {
  id: string;
  name: string;
  size: number;
  progress: number; // 0-100
  status: UploadStatus;
  error?: string;
}

interface UploadProgressProps {
  file: UploadFileItem;
  onRemove?: (id: string) => void;
}

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
};

const STATUS_CONFIG: Record<UploadStatus, { label: string; color: string }> = {
  uploading: { label: 'Uploading…', color: 'text-ipo-ai' },
  processing: { label: 'Processing…', color: 'text-ipo-attention' },
  complete: { label: 'Complete', color: 'text-ipo-verified' },
  error: { label: 'Failed', color: 'text-ipo-critical' },
};

const UploadProgress: React.FC<UploadProgressProps> = ({ file, onRemove }) => {
  const config = STATUS_CONFIG[file.status];
  const isActive = file.status === 'uploading' || file.status === 'processing';

  const barColor =
    file.status === 'complete'
      ? 'bg-ipo-verified'
      : file.status === 'error'
      ? 'bg-ipo-critical'
      : file.status === 'processing'
      ? 'bg-ipo-attention'
      : 'bg-ipo-ai';

  return (
    <div className="bg-ipo-elevated border border-ipo-border rounded-md px-4 py-3.5 space-y-3 font-body">
      {/* Top row */}
      <div className="flex items-center gap-3">
        {/* File icon */}
        <div className="w-8 h-8 rounded-sm bg-ipo-overlay border border-ipo-border flex items-center justify-center flex-shrink-0">
          <FileText className="w-4 h-4 text-ipo-text-secondary" />
        </div>

        {/* Name + size */}
        <div className="flex-1 min-w-0">
          <p className="text-ipo-text text-sm font-semibold truncate">{file.name}</p>
          <p className="text-ipo-text-secondary text-[10px] uppercase font-bold tracking-wider font-data">{formatBytes(file.size)}</p>
        </div>

        {/* Status */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {isActive && (
            <Loader2 className={`w-4 h-4 animate-spin ${config.color}`} />
          )}
          {file.status === 'complete' && <CheckCircle2 className="w-4 h-4 text-ipo-verified" />}
          {file.status === 'error' && <XCircle className="w-4 h-4 text-ipo-critical" />}
          <span className={`text-[10px] uppercase font-bold tracking-wider font-data ${config.color}`}>{config.label}</span>
        </div>

        {/* Remove */}
        {onRemove && (
          <button
            onClick={() => onRemove(file.id)}
            className="text-ipo-text-secondary hover:text-ipo-critical transition-colors p-1 rounded-sm hover:bg-ipo-critical/10"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-ipo-overlay border border-ipo-border rounded-full overflow-hidden">
        <div
          style={{ width: `${file.progress}%` }}
          className={`h-full rounded-full transition-all duration-300 ${barColor}`}
        />
      </div>

      {/* Error message */}
      {file.status === 'error' && file.error && (
        <p className="text-ipo-critical text-xs">{file.error}</p>
      )}
    </div>
  );
};

export default UploadProgress;

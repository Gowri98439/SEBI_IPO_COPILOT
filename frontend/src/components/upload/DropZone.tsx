import React, { useCallback, useState } from 'react';
import { useDropzone, type FileRejection } from 'react-dropzone';
import { CloudUpload, FileType, X } from 'lucide-react';
import toast from 'react-hot-toast';

interface DropZoneProps {
  onFilesAccepted: (files: File[]) => void;
  accept?: Record<string, string[]>;
  maxSize?: number; // bytes
  maxFiles?: number;
  disabled?: boolean;
}

const DEFAULT_ACCEPT: Record<string, string[]> = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'text/plain': ['.txt'],
};

const FILE_ICONS: Record<string, string> = {
  pdf: '📄',
  docx: '.docx',
  xlsx: '📊',
  txt: '📝',
};

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
};

const DropZone: React.FC<DropZoneProps> = ({
  onFilesAccepted,
  accept = DEFAULT_ACCEPT,
  maxSize = 50 * 1024 * 1024,
  maxFiles = 10,
  disabled = false,
}) => {
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);

  const onDrop = useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      if (rejected.length > 0) {
        rejected.forEach((r) => {
          const msg = r.errors[0]?.message ?? 'File rejected';
          toast.error(`${r.file.name}: ${msg}`);
        });
      }
      if (accepted.length > 0) {
        setPendingFiles((prev) => [...prev, ...accepted]);
        onFilesAccepted(accepted);
      }
    },
    [onFilesAccepted]
  );

  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept,
    maxSize,
    maxFiles,
    disabled,
  });

  const removeFile = (name: string) => {
    setPendingFiles((prev) => prev.filter((f) => f.name !== name));
  };

  const borderColor = isDragReject
    ? 'border-ipo-critical'
    : isDragAccept
    ? 'border-ipo-ai'
    : isDragActive
    ? 'border-ipo-ai'
    : 'border-ipo-border';

  const bgColor = isDragReject
    ? 'bg-ipo-critical/10'
    : isDragAccept || isDragActive
    ? 'bg-ipo-ai/10'
    : 'bg-ipo-elevated';

  return (
    <div className="space-y-4 font-body">
      {/* Drop Zone */}
      <div
        {...(getRootProps() as any)}
        className={`relative border-2 border-dashed ${borderColor} ${bgColor} rounded-md p-10 cursor-pointer transition-colors duration-200 flex flex-col items-center justify-center gap-4 min-h-[200px] ${
          disabled ? 'opacity-50 cursor-not-allowed' : 'hover:border-ipo-text-secondary hover:bg-ipo-overlay'
        }`}
      >
        <input {...getInputProps()} />

        {/* Icon */}
        <div className={`w-12 h-12 rounded-full border flex items-center justify-center transition-colors ${
          isDragActive ? 'bg-ipo-ai/20 border-ipo-ai' : 'bg-ipo-overlay border-ipo-border'
        }`}>
          <CloudUpload className={`w-6 h-6 ${isDragActive ? 'text-ipo-ai' : 'text-ipo-text-secondary'}`} />
        </div>

        {/* Text */}
        <div className="text-center">
          <p className="text-ipo-text font-semibold text-sm">
            {isDragActive ? 'Release to upload' : 'Drag & drop files here'}
          </p>
          <p className="text-ipo-text-secondary text-sm mt-1">
            or{' '}
            <span className="text-ipo-ai font-semibold hover:underline cursor-pointer">
              browse from your computer
            </span>
          </p>
          <p className="text-ipo-text-secondary text-[10px] uppercase tracking-wider font-bold mt-3 font-data">
            PDF, DOCX, XLSX · Up to {formatBytes(maxSize)} per file
          </p>
        </div>
      </div>

      {/* Pending files list */}
      {pendingFiles.length > 0 && (
        <div className="space-y-2 mt-4">
          {pendingFiles.map((file, idx) => {
            const ext = file.name.split('.').pop() ?? '';
            const emoji = FILE_ICONS[ext] ?? '📁';
            return (
              <div
                key={file.name + idx}
                className="flex items-center gap-3 bg-ipo-elevated border border-ipo-border rounded-md px-4 py-3"
              >
                <span className="text-xl">{emoji}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-ipo-text text-sm font-semibold truncate">{file.name}</p>
                  <p className="text-ipo-text-secondary text-xs font-data">{formatBytes(file.size)}</p>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); removeFile(file.name); }}
                  className="text-ipo-text-secondary hover:text-ipo-critical transition-colors p-1 rounded-sm hover:bg-ipo-critical/10"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default DropZone;

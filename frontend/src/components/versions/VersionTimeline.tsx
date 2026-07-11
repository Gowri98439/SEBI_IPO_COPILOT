import React from 'react';
import { format } from 'date-fns';
import { Download, GitBranch, User2, ChevronRight } from 'lucide-react';

export interface DocumentVersion {
  id: string;
  version: string; // e.g. "v1.0", "v2.1"
  documentName: string;
  changeSummary: string;
  uploadedBy: string;
  uploadedAt: Date;
  fileSize?: number;
  isLatest?: boolean;
  onDownload?: (id: string) => void;
}

interface VersionTimelineProps {
  versions: DocumentVersion[];
}

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
};

const VersionTimeline: React.FC<VersionTimelineProps> = ({ versions }) => {
  if (versions.length === 0) {
    return (
      <div className="text-center py-12 bg-ipo-elevated border-ipo-border border border-dashed rounded-md font-body">
        <GitBranch className="w-10 h-10 text-ipo-text-secondary mx-auto mb-3" />
        <p className="text-ipo-text-secondary text-sm">No versions yet</p>
      </div>
    );
  }

  return (
    <div className="relative font-body">
      {/* Vertical connecting line */}
      <div className="absolute left-[29px] top-8 bottom-8 w-px bg-ipo-border" />

      <div className="space-y-4">
        {versions.map((version) => (
          <div
            key={version.id}
            className="relative flex gap-5"
          >
            {/* Timeline dot */}
            <div className="flex-shrink-0 flex flex-col items-center">
              <div
                className={`w-14 h-14 rounded-full flex items-center justify-center font-bold font-data text-[10px] tracking-wider uppercase border-[3px] z-10 transition-colors ${
                  version.isLatest
                    ? 'bg-ipo-ai text-ipo-base border-ipo-base'
                    : 'bg-ipo-overlay border-ipo-border text-ipo-text-secondary'
                }`}
              >
                {version.version}
              </div>
            </div>

            {/* Card */}
            <div className="flex-1 bg-ipo-elevated border border-ipo-border rounded-md p-4 hover:border-ipo-text-secondary transition-colors group shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1.5">
                    <p className="text-ipo-text font-semibold text-sm truncate">
                      {version.documentName}
                    </p>
                    {version.isLatest && (
                      <span className="px-2 py-0.5 rounded-sm text-[10px] uppercase font-bold tracking-wider font-data bg-ipo-ai/10 text-ipo-ai border border-ipo-ai/20">
                        Latest
                      </span>
                    )}
                  </div>
                  <p className="text-ipo-text-secondary text-sm leading-relaxed">{version.changeSummary}</p>
                  <div className="flex items-center gap-3 mt-3">
                    <span className="flex items-center gap-1.5 text-[10px] uppercase font-bold tracking-wider font-data text-ipo-text-secondary">
                      <User2 className="w-3.5 h-3.5" />
                      {version.uploadedBy}
                    </span>
                    <span className="text-ipo-border text-xs">|</span>
                    <span className="text-[10px] uppercase font-bold tracking-wider font-data text-ipo-text-secondary">
                      {format(version.uploadedAt, 'dd MMM yyyy, HH:mm')}
                    </span>
                    {version.fileSize && (
                      <>
                        <span className="text-ipo-border text-xs">|</span>
                        <span className="text-[10px] uppercase font-bold tracking-wider font-data text-ipo-text-secondary">{formatBytes(version.fileSize)}</span>
                      </>
                    )}
                  </div>
                </div>

                {/* Download button */}
                {version.onDownload && (
                  <button
                    onClick={() => version.onDownload!(version.id)}
                    className="flex-shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-ipo-overlay hover:bg-ipo-border/50 border border-ipo-border text-ipo-text text-xs font-semibold transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download
                  </button>
                )}

                <ChevronRight className="w-4 h-4 text-ipo-text-secondary flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity mt-1.5" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default VersionTimeline;

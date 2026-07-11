import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Download, FileText, ShieldCheck, Loader2, CheckCircle } from 'lucide-react';
import api from '../api/client';

const ExportPage: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const [downloading, setDownloading] = useState<'report' | null>(null);
  const [done, setDone] = useState<string | null>(null);

  const downloadReport = async () => {
    setDownloading('report');
    setDone(null);
    try {
      const response = await api.get(`/workspaces/${workspaceId}/export/report.pdf`, {
        responseType: 'blob',
      });
      const blob = new Blob([response], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `IPO_Compliance_Report.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      setDone('report');
    } catch (err) {
      alert('Failed to generate report. Please ensure compliance checks have been run.');
    } finally {
      setDownloading(null);
    }
  };

  const ExportCard = ({
    title,
    description,
    icon: Icon,
    iconColor,
    iconBg,
    action,
    actionLabel,
    actionKey,
    note,
  }: {
    title: string;
    description: string;
    icon: React.FC<any>;
    iconColor: string;
    iconBg: string;
    action: () => void;
    actionLabel: string;
    actionKey: string;
    note?: string;
  }) => (
    <div className="card" style={{ padding: '2rem' }}>
      <div style={{ display: 'flex', gap: '1.25rem', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
        <div style={{
          width: '52px', height: '52px', borderRadius: '14px',
          background: iconBg, flexShrink: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon size={26} color={iconColor} strokeWidth={1.75} />
        </div>
        <div>
          <h3 style={{ margin: '0 0 0.375rem', fontSize: '1.0625rem', fontWeight: 700 }}>{title}</h3>
          <p style={{ margin: 0, fontSize: '0.9375rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{description}</p>
        </div>
      </div>
      {note && (
        <div className="alert alert-info" style={{ marginBottom: '1.25rem', fontSize: '0.875rem' }}>
          {note}
        </div>
      )}
      <button
        className="btn btn-primary"
        onClick={action}
        disabled={downloading === actionKey}
        style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
      >
        {downloading === actionKey
          ? <><Loader2 size={16} className="animate-spin" /> Generating...</>
          : done === actionKey
          ? <><CheckCircle size={16} /> Downloaded</>
          : <><Download size={16} /> {actionLabel}</>}
      </button>
    </div>
  );

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Export Reports</h1>
        <p className="page-subtitle">Download compliance and filing documents for your records</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.5rem' }}>
        <ExportCard
          title="Compliance Report PDF"
          description="A comprehensive compliance report covering all 20 SEBI ICDR rules, AI-generated findings, evidence references, and an audit trail. Suitable for internal review and regulator submission."
          icon={ShieldCheck}
          iconColor="var(--success)"
          iconBg="var(--success-bg)"
          action={downloadReport}
          actionLabel="Download Compliance Report"
          actionKey="report"
          note="Ensure you have run the Compliance Engine before exporting. The report reflects the latest scan results."
        />

        <ExportCard
          title="DRHP Draft Document"
          description="Download your generated Draft Red Herring Prospectus. Navigate to the DRHP Generator to create or update your draft before downloading."
          icon={FileText}
          iconColor="var(--accent)"
          iconBg="var(--accent-light)"
          action={() => window.location.href = `/app/drhp/${workspaceId}`}
          actionLabel="Go to DRHP Generator"
          actionKey="drhp"
          note="Generate your DRHP first using the DRHP Generator, then download it from there."
        />
      </div>

      <div className="card" style={{ marginTop: '1.75rem', padding: '1.5rem' }}>
        <h3 style={{ margin: '0 0 1rem', fontSize: '0.9375rem', fontWeight: 700 }}>Export Notes</h3>
        <ul style={{ margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          <li>All exports are stamped with the date and time of generation.</li>
          <li>The Compliance Report is confidential and intended for authorised personnel only.</li>
          <li>The DRHP draft is a working document and must be reviewed by a SEBI-registered merchant banker before filing.</li>
          <li>All downloads are logged in the Audit Trail for compliance purposes.</li>
        </ul>
      </div>
    </div>
  );
};

export default ExportPage;

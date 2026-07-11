import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { FileText, ShieldCheck, TrendingUp, AlertTriangle, ArrowRight, UploadCloud } from 'lucide-react';
import api from '../api/client';

interface Workspace {
  id: string;
  name: string;
  status: string;
  executive_summary?: string;
  created_at: string;
}

interface DashboardData {
  readiness_score: number;
  documents_uploaded: number;
  documents_required: number;
  compliance_pass_rate_percent: number;
  compliance_total: number;
  compliance_passing: number;
  compliance_failed: number;
  open_issues: number;
  audit_events: Array<{
    id: string;
    action: string;
    status: string;
    details: string;
    created_at: string;
  }>;
}

const DashboardPage: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [stats, setStats] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!workspaceId) return;
    Promise.all([
      api.get(`/workspaces/${workspaceId}`),
      api.get(`/workspaces/${workspaceId}/dashboard`).catch(() => null),
    ]).then(([ws, s]) => {
      setWorkspace(ws);
      setStats(s);
    }).finally(() => setLoading(false));
  }, [workspaceId]);

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
      <div className="spinner" style={{ width: '36px', height: '36px' }} />
    </div>
  );

  if (!workspace) return (
    <div className="alert alert-danger">Workspace not found.</div>
  );

  let summary: any = null;
  try { summary = workspace.executive_summary ? JSON.parse(workspace.executive_summary) : null; } catch {}

  const kpis = [
    {
      label: 'Filing Readiness',
      value: `${stats?.readiness_score ?? 0}%`,
      icon: TrendingUp,
      color: 'var(--accent)',
      bg: 'var(--accent-light)',
    },
    {
      label: 'Documents Uploaded',
      value: `${stats?.documents_uploaded ?? 0} / ${stats?.documents_required ?? 5}`,
      icon: FileText,
      color: '#0F766E',
      bg: '#F0FDFA',
    },
    {
      label: 'Compliance Score',
      value: `${Math.round(stats?.compliance_pass_rate_percent ?? 0)}%`,
      icon: ShieldCheck,
      color: 'var(--success)',
      bg: 'var(--success-bg)',
    },
    {
      label: 'Open Issues',
      value: stats?.open_issues ?? 0,
      icon: AlertTriangle,
      color: stats?.open_issues ? 'var(--danger)' : 'var(--success)',
      bg: stats?.open_issues ? 'var(--danger-bg)' : 'var(--success-bg)',
    },
  ];

  return (
    <div>
      {/* Page Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 className="page-title">{
            // De-duplicate workspace names (e.g. "Acme...Acme..." → "Acme...")
            (() => {
              const n = workspace.name;
              const half = n.slice(0, Math.floor(n.length / 2));
              if (n.length > 20 && n.slice(Math.floor(n.length / 2)).trim().startsWith(half.split(' ').slice(0, 2).join(' '))) {
                return n.slice(0, Math.floor(n.length / 2)).trim();
              }
              return n;
            })()
          }</h1>
          <p className="page-subtitle">
            Created {new Date(workspace.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' })}
            <span style={{
              marginLeft: '0.75rem',
              display: 'inline-flex', alignItems: 'center', gap: '0.25rem',
              padding: '0.125rem 0.5rem', borderRadius: '9999px',
              fontSize: '0.75rem', fontWeight: 600,
              background: 'var(--accent-light)', color: 'var(--accent)',
              border: '1px solid #BFDBFE',
            }}>
              {workspace.status.toUpperCase()}
            </span>
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <Link to={`/app/workspace/${workspaceId}`} className="btn btn-secondary btn-sm">
            <UploadCloud size={15} /> Upload Documents
          </Link>
          <Link to={`/app/drhp/${workspaceId}`} className="btn btn-primary btn-sm">
            <FileText size={15} /> Generate DRHP
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        {kpis.map((kpi) => (
          <div key={kpi.label} className="card stat-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <p className="stat-label">{kpi.label}</p>
                <p className="stat-value" style={{ color: kpi.color }}>{kpi.value}</p>
              </div>
              <div style={{
                width: '40px', height: '40px', borderRadius: '10px',
                background: kpi.bg, display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
              }}>
                <kpi.icon size={20} color={kpi.color} strokeWidth={2} />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '1.5rem', alignItems: 'start' }}>

        {/* Left: Executive Summary + Activity Feed */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

          {/* AI Executive Summary */}
          <div className="card">
            <div className="card-header">
              <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>IPO Readiness Summary</h2>
            </div>
            <div className="card-body">
              {summary ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                  {summary.executive_overview && (
                    <div>
                      <p className="section-title">Overview</p>
                      <p style={{ margin: 0, color: 'var(--text-secondary)', lineHeight: 1.7 }}>{summary.executive_overview}</p>
                    </div>
                  )}
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <div className="alert alert-info" style={{ margin: 0 }}>
                    Upload financial documents and run the Compliance Engine to generate an automated IPO readiness analysis.
                  </div>
                  {/* Compliance progress bar */}
                  {stats && stats.compliance_total > 0 && (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.375rem' }}>
                        <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Compliance Rules Checked</span>
                        <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                          {stats.compliance_passing} / {stats.compliance_total} passing
                        </span>
                      </div>
                      <div style={{ height: '8px', background: 'var(--bg-elevated)', borderRadius: '99px', overflow: 'hidden' }}>
                        <div style={{
                          height: '100%', borderRadius: '99px', background: 'var(--success)',
                          width: `${stats.compliance_pass_rate_percent}%`, transition: 'width 0.6s ease',
                        }} />
                      </div>
                    </div>
                  )}
                  <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <Link to={`/app/workspace/${workspaceId}`} className="btn btn-primary" style={{ textDecoration: 'none' }}>
                      <UploadCloud size={15} /> Upload Documents
                    </Link>
                    <Link to={`/app/compliance/${workspaceId}`} className="btn btn-secondary" style={{ textDecoration: 'none' }}>
                      <ShieldCheck size={15} /> Run Compliance Check
                    </Link>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Recent Activity */}
          {stats?.audit_events && stats.audit_events.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Recent Activity</h2>
              </div>
              <div style={{ padding: '0' }}>
                {stats.audit_events.slice(0, 6).map((evt, i) => (
                  <div key={evt.id} style={{
                    display: 'flex', alignItems: 'center', gap: '0.875rem',
                    padding: '0.875rem 1.25rem',
                    borderBottom: i < Math.min(stats.audit_events.length - 1, 5) ? '1px solid var(--border)' : 'none',
                  }}>
                    <div style={{
                      width: '8px', height: '8px', borderRadius: '50%', flexShrink: 0,
                      background: evt.status === 'SUCCESS' ? 'var(--success)' : 'var(--danger)',
                    }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {evt.action.replace(/_/g, ' ')}
                      </div>
                      {evt.details && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {evt.details}
                        </div>
                      )}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', flexShrink: 0 }}>
                      {new Date(evt.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: Quick Actions */}
        <div>
          <div className="card">
            <div className="card-header">
              <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>Quick Actions</h2>
            </div>
            <div style={{ padding: '0.5rem' }}>
              {[
                { label: 'Upload Documents',   desc: 'Add financial & legal files',  path: `/app/workspace/${workspaceId}` },
                { label: 'Compliance Check',   desc: 'Run SEBI rule validation',      path: `/app/compliance/${workspaceId}` },
                { label: 'Generate DRHP',      desc: 'Draft IPO prospectus (PDF)',    path: `/app/drhp/${workspaceId}` },
                { label: 'SEBI Advisor',        desc: 'Ask regulatory questions',      path: `/app/copilot/${workspaceId}` },
                { label: 'Export Report',       desc: 'Download compliance PDF',       path: `/app/export/${workspaceId}` },
                { label: 'Audit Trail',         desc: 'View all system events',        path: `/app/audit/${workspaceId}` },
              ].map((action) => (
                <Link
                  key={action.path}
                  to={action.path}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '0.75rem 1rem', borderRadius: '8px', textDecoration: 'none',
                    marginBottom: '2px', transition: 'background 150ms',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-elevated)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <div>
                    <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>{action.label}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{action.desc}</div>
                  </div>
                  <ArrowRight size={16} color="var(--text-muted)" />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;


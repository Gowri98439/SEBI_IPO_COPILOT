import React, { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { ShieldCheck, ShieldAlert, AlertTriangle, ChevronDown, ChevronUp, RefreshCw, BookOpen } from 'lucide-react';
import api from '../api/client';

interface EvidencePayload {
  evidence?: string;
  confidence?: 'strong' | 'medium' | 'low';
  regulation_reference?: string;
  suggestions?: string[];
  category?: string;
  severity?: 'high' | 'medium' | 'low';
  source?: string;
}

interface ComplianceCheck {
  id: string;
  check_type: string;
  regulation: string;
  status: 'pass' | 'warning' | 'fail' | 'pending' | 'not_applicable';
  ai_reasoning: string;
  evidence?: EvidencePayload;
  created_at?: string;
}

const STATUS_CONFIG = {
  pass:           { label: 'Pass',           badge: 'badge-success', icon: ShieldCheck  },
  warning:        { label: 'Warning',        badge: 'badge-warning', icon: AlertTriangle },
  fail:           { label: 'Fail',           badge: 'badge-danger',  icon: ShieldAlert   },
  pending:        { label: 'Pending',        badge: 'badge-neutral', icon: ShieldCheck   },
  not_applicable: { label: 'Not Applicable', badge: 'badge-neutral', icon: ShieldCheck   },
};

const SEVERITY_COLORS: Record<string, string> = {
  high:   'var(--danger)',
  medium: 'var(--warning)',
  low:    'var(--text-muted)',
};

const CONFIDENCE_COLORS: Record<string, string> = {
  strong: 'var(--success)',
  medium: 'var(--warning)',
  low:    'var(--danger)',
};

const CompliancePage: React.FC = () => {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const [checks, setChecks] = useState<ComplianceCheck[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'pass' | 'fail' | 'warning'>('all');

  const fetchChecks = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const data = await api.get(`/workspaces/${workspaceId}/compliance`);
      setChecks(Array.isArray(data) ? data : []);
    } catch { setChecks([]); }
    finally { setLoading(false); }
  }, [workspaceId]);

  useEffect(() => { fetchChecks(); }, [fetchChecks]);

  const runCompliance = async () => {
    setRunning(true);
    try {
      await api.post(`/workspaces/${workspaceId}/compliance/run`);
      // Poll every 3 seconds for up to 90 seconds
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        await fetchChecks();
        if (attempts >= 30) clearInterval(poll);
      }, 3000);
      setTimeout(() => { clearInterval(poll); setRunning(false); }, 95000);
    } catch {
      setRunning(false);
    }
  };

  const passed   = checks.filter((c) => c.status === 'pass').length;
  const failed   = checks.filter((c) => c.status === 'fail').length;
  const warnings = checks.filter((c) => c.status === 'warning').length;
  const na       = checks.filter((c) => c.status === 'not_applicable').length;
  const score    = checks.length > na ? Math.round((passed / (checks.length - na)) * 100) : 0;

  const filtered = filter === 'all' ? checks : checks.filter((c) => c.status === filter);

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}>
      <div className="spinner" style={{ width: '36px', height: '36px' }} />
    </div>
  );

  return (
    <div>
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 className="page-title">Compliance Engine</h1>
          <p className="page-subtitle">SEBI ICDR Regulations 2018 — Automated rule-by-rule evaluation against your documents</p>
        </div>
        <button
          className="btn btn-primary btn-sm"
          onClick={runCompliance}
          disabled={running}
        >
          {running
            ? <span className="spinner" style={{ width: '14px', height: '14px', borderTopColor: 'white', borderColor: 'rgba(255,255,255,0.3)' }} />
            : <RefreshCw size={15} />}
          {running ? 'Running AI Scan...' : 'Run Compliance Scan'}
        </button>
      </div>

      {/* Running Banner */}
      {running && (
        <div className="alert alert-info" style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className="spinner" style={{ width: '18px', height: '18px', flexShrink: 0 }} />
          <span>
            <strong>Compliance scan in progress.</strong> The AI is evaluating all 20 SEBI ICDR rules against your uploaded documents.
            This may take 1-2 minutes. Results will update automatically.
          </span>
        </div>
      )}

      {/* Summary Stats */}
      {checks.length > 0 && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
            {[
              { label: 'Compliance Score', value: `${score}%`,    color: score >= 80 ? 'var(--success)' : score >= 50 ? 'var(--warning)' : 'var(--danger)', bg: 'var(--bg-muted)' },
              { label: 'Total Rules',       value: checks.length, color: 'var(--text-primary)', bg: 'var(--bg-muted)' },
              { label: 'Passed',            value: passed,        color: 'var(--success)',      bg: 'var(--success-bg)' },
              { label: 'Warnings',          value: warnings,      color: 'var(--warning)',      bg: 'var(--warning-bg)' },
              { label: 'Failed',            value: failed,        color: 'var(--danger)',       bg: 'var(--danger-bg)' },
            ].map((s) => (
              <div key={s.label} className="card stat-card">
                <p className="stat-label">{s.label}</p>
                <p className="stat-value" style={{ fontSize: '1.75rem', color: s.color }}>{s.value}</p>
              </div>
            ))}
          </div>

          {/* Score progress bar */}
          <div className="card" style={{ padding: '1rem 1.25rem', marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Overall SEBI Compliance Score</span>
              <span style={{ fontSize: '0.875rem', fontWeight: 700, color: score >= 80 ? 'var(--success)' : score >= 50 ? 'var(--warning)' : 'var(--danger)' }}>{score}%</span>
            </div>
            <div style={{ height: '10px', background: 'var(--bg-elevated)', borderRadius: '99px', overflow: 'hidden' }}>
              <div style={{
                height: '100%', borderRadius: '99px',
                background: score >= 80 ? 'var(--success)' : score >= 50 ? 'var(--warning)' : 'var(--danger)',
                width: `${score}%`, transition: 'width 0.8s ease',
              }} />
            </div>
          </div>
        </>
      )}

      {/* Filter tabs */}
      {checks.length > 0 && (
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          {(['all', 'pass', 'warning', 'fail'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-secondary'}`}
              style={{ textTransform: 'capitalize' }}
            >
              {f === 'all' ? `All (${checks.length})` : f === 'pass' ? `Pass (${passed})` : f === 'warning' ? `Warning (${warnings})` : `Fail (${failed})`}
            </button>
          ))}
        </div>
      )}

      {/* Checks List */}
      <div className="card">
        <div className="card-header">
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700 }}>
            SEBI Regulatory Checks
            {filtered.length !== checks.length && <span style={{ fontWeight: 400, color: 'var(--text-muted)', marginLeft: '0.5rem' }}>({filtered.length} shown)</span>}
          </h2>
        </div>
        {filtered.length > 0 ? (
          <div>
            {filtered.map((check) => {
              const cfg = STATUS_CONFIG[check.status] ?? STATUS_CONFIG['pending'];
              const isExpanded = expandedId === check.id;
              const ev = check.evidence ?? {};
              const severity = ev.severity ?? 'medium';
              const confidence = ev.confidence ?? 'medium';
              return (
                <div key={check.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : check.id)}
                    style={{
                      width: '100%', display: 'flex', alignItems: 'center', gap: '1rem',
                      padding: '1rem 1.5rem', background: 'none', border: 'none',
                      cursor: 'pointer', textAlign: 'left', transition: 'background 150ms',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-elevated)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
                  >
                    <span className={`badge ${cfg.badge}`} style={{ flexShrink: 0, minWidth: '68px', justifyContent: 'center' }}>
                      <cfg.icon size={11} strokeWidth={2.5} />
                      {cfg.label}
                    </span>
                    <span style={{ flex: 1, fontSize: '0.9375rem', fontWeight: 500, color: 'var(--text-primary)' }}>
                      {check.regulation}
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginLeft: '0.5rem', fontWeight: 400 }}>
                        [{check.check_type}]
                      </span>
                    </span>
                    {/* Severity indicator */}
                    <span style={{
                      fontSize: '0.75rem', fontWeight: 600, color: SEVERITY_COLORS[severity],
                      textTransform: 'uppercase', letterSpacing: '0.03em', flexShrink: 0,
                    }}>
                      {severity}
                    </span>
                    {/* Confidence */}
                    {confidence && (
                      <span style={{ fontSize: '0.75rem', color: CONFIDENCE_COLORS[confidence], flexShrink: 0, marginLeft: '0.5rem' }}>
                        {confidence} confidence
                      </span>
                    )}
                    {isExpanded ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
                  </button>

                  {isExpanded && (
                    <div style={{ padding: '0 1.5rem 1.5rem' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>

                        {/* AI Reasoning */}
                        <div style={{ padding: '1rem', background: 'var(--bg-elevated)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                          <p className="section-title" style={{ marginBottom: '0.375rem', display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                            <ShieldCheck size={14} /> AI Analysis
                          </p>
                          <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                            {check.ai_reasoning || 'Analysis not available.'}
                          </p>
                        </div>

                        {/* Evidence */}
                        {ev.evidence && (
                          <div style={{ padding: '1rem', background: 'var(--bg-elevated)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                            <p className="section-title" style={{ marginBottom: '0.375rem', display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                              <BookOpen size={14} /> Document Evidence
                            </p>
                            <p style={{ margin: '0 0 0.375rem', fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.7, fontStyle: 'italic' }}>
                              "{ev.evidence}"
                            </p>
                            {ev.source && (
                              <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-muted)' }}>Source: {ev.source}</p>
                            )}
                            {ev.regulation_reference && (
                              <p style={{ margin: '0.25rem 0 0', fontSize: '0.75rem', color: 'var(--accent)', fontWeight: 600 }}>
                                Regulation: {ev.regulation_reference}
                              </p>
                            )}
                          </div>
                        )}

                        {/* Suggestions */}
                        {ev.suggestions && ev.suggestions.length > 0 && (
                          <div style={{ padding: '1rem', background: 'var(--warning-bg)', borderRadius: '8px', border: '1px solid rgba(180,83,9,0.2)' }}>
                            <p className="section-title" style={{ marginBottom: '0.5rem', color: 'var(--warning)' }}>
                              Recommended Actions
                            </p>
                            <ul style={{ margin: 0, paddingLeft: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                              {ev.suggestions.map((s, i) => (
                                <li key={i} style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{s}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ padding: '4rem 2rem', textAlign: 'center' }}>
            <ShieldCheck size={40} color="#CBD5E1" strokeWidth={1.5} style={{ marginBottom: '1rem' }} />
            <p style={{ margin: '0 0 0.375rem', fontWeight: 600, color: 'var(--text-primary)' }}>No compliance data yet</p>
            <p style={{ margin: '0 0 1.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              Upload your financial documents and run a compliance scan to evaluate against all 20 SEBI ICDR rules.
            </p>
            <button className="btn btn-primary" onClick={runCompliance} disabled={running}>
              {running ? 'Running...' : 'Run First Scan'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CompliancePage;

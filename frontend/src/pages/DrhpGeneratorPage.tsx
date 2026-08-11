import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import {
  Building2, Users, BarChart3, FileText, ChevronRight, ChevronLeft,
  CheckCircle, Download, Loader2, AlertCircle, Plus, Trash2,
  Zap, Shield, TrendingUp, AlertTriangle, BookOpen, Radio,
  FileBarChart, Activity, RefreshCw, Eye, ChevronDown, ChevronUp,
  Circle, CheckSquare, XSquare, Info, Star
} from 'lucide-react';
import api, { API_BASE_URL } from '../api/client';

/* ─── Types ────────────────────────────────────────────────── */
interface Promoter { name: string; designation: string; qualification: string; holding_pct: string; experience_years: string; }
interface FinancialYear { year: string; revenue: string; net_profit: string; total_assets: string; total_equity: string; ebitda: string; total_debt: string; interest_expense: string; }
interface UsageItem { purpose: string; amount_lakhs: string; timeline_months: string; }

interface FormData {
  company_name: string; cin: string; pan: string; incorporation_date: string;
  registered_address: string; sector: string; sub_sector: string; website: string; description: string;
  employee_count: string; key_products: string; geographies: string; certifications: string;
  statutory_auditor: string; company_secretary: string; listing_exchange: string;
  promoters: Promoter[];
  financials: FinancialYear[];
  use_of_proceeds_items: UsageItem[];
  issue_size_cr: string; fresh_issue_cr: string; ofs_cr: string;
  price_band_low: string; price_band_high: string; face_value: string; lot_size: string;
  objects_of_issue: string; use_of_proceeds: string; merchant_banker: string;
  generate_intelligence_report: boolean; generate_charts: boolean; use_llm: boolean;
}

interface JobStatus {
  status: string; progress_pct: number; current_stage?: string; message: string;
  sections_completed: number; sections_total: number; drhp_ready: boolean;
  intelligence_report_ready: boolean; warnings: string[]; errors: string[];
  total_time_seconds?: number;
}

interface ConsistencyCheck { severity: string; check_name: string; description: string; recommended_fix?: string; }

/* ─── Constants ─────────────────────────────────────────────── */
const SECTORS = [
  'Manufacturing', 'Technology & IT', 'Healthcare & Pharma', 'Financial Services',
  'Retail & FMCG', 'Real Estate & Construction', 'Agriculture & Agro-processing',
  'Infrastructure & Logistics', 'Textiles & Apparel', 'Chemicals & Specialty',
  'Media & Entertainment', 'Education & Skilling', 'Tourism & Hospitality', 'Other',
];
const EXCHANGES = ['NSE Emerge', 'BSE SME'];
const DEFAULT_PROMOTER: Promoter = { name: '', designation: '', qualification: '', holding_pct: '', experience_years: '' };
const DEFAULT_FY: FinancialYear = { year: '', revenue: '', net_profit: '', total_assets: '', total_equity: '', ebitda: '', total_debt: '', interest_expense: '' };
const DEFAULT_USAGE: UsageItem = { purpose: '', amount_lakhs: '', timeline_months: '' };

const STEPS = [
  { id: 1, label: 'Company', icon: Building2 },
  { id: 2, label: 'Promoters', icon: Users },
  { id: 3, label: 'Financials', icon: BarChart3 },
  { id: 4, label: 'Issue Details', icon: FileText },
  { id: 5, label: 'Generate', icon: Zap },
];

const DRHP_SECTIONS = [
  'Cover Page', 'Disclaimer', 'Table of Contents', 'Definitions', 'Forward Looking Statements',
  'Issue Summary', 'Risk Factors', 'Business Overview', 'Business Model', 'Competitive Strengths',
  'Strategies', 'Industry Overview', 'Market Opportunity', 'Corporate Structure', 'Promoters',
  'Directors', 'MDA', 'Capital Structure', 'Shareholding Pattern', 'Objects of Issue',
  'Use of Proceeds', 'Basis for Price', 'Dividend Policy', 'Financial Statements',
  'Financial Ratios', 'Related Party', 'Outstanding Litigation', 'Govt Approvals',
  'Material Contracts', 'Employees', 'Corporate Governance', 'Compliance Matrix', 'Declaration',
];

const INITIAL: FormData = {
  company_name: '', cin: '', pan: '', incorporation_date: '', registered_address: '', sector: '',
  sub_sector: '', website: '', description: '', employee_count: '', key_products: '',
  geographies: '', certifications: '', statutory_auditor: '', company_secretary: '', listing_exchange: 'NSE Emerge',
  promoters: [{ ...DEFAULT_PROMOTER }],
  financials: [
    { year: '2021-22', revenue: '', net_profit: '', total_assets: '', total_equity: '', ebitda: '', total_debt: '', interest_expense: '' },
    { year: '2022-23', revenue: '', net_profit: '', total_assets: '', total_equity: '', ebitda: '', total_debt: '', interest_expense: '' },
    { year: '2023-24', revenue: '', net_profit: '', total_assets: '', total_equity: '', ebitda: '', total_debt: '', interest_expense: '' },
  ],
  use_of_proceeds_items: [{ ...DEFAULT_USAGE }],
  issue_size_cr: '', fresh_issue_cr: '', ofs_cr: '', price_band_low: '', price_band_high: '',
  face_value: '10', lot_size: '', objects_of_issue: '', use_of_proceeds: '', merchant_banker: '',
  generate_intelligence_report: true, generate_charts: true, use_llm: true,
};

/* ─── Sub-components ────────────────────────────────────────── */
const Field: React.FC<{ label: string; required?: boolean; hint?: string; children: React.ReactNode; span?: number }> = ({
  label, required, hint, children, span = 1
}) => (
  <div style={{ gridColumn: span > 1 ? `span ${span}` : undefined }}>
    <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '0.375rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
      {label}{required && <span style={{ color: '#EF4444', marginLeft: '3px' }}>*</span>}
    </label>
    {hint && <p style={{ margin: '0 0 0.375rem', fontSize: '0.71875rem', color: 'var(--text-muted)' }}>{hint}</p>}
    {children}
  </div>
);

const inp = {
  width: '100%', padding: '0.5rem 0.75rem', background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.1)', borderRadius: '0.5rem', color: 'var(--text-primary)',
  fontSize: '0.875rem', outline: 'none', boxSizing: 'border-box' as const,
};

const StageIndicator: React.FC<{ stage?: string; pct: number }> = ({ stage, pct }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '0.75rem', background: 'rgba(59,130,246,0.08)', borderRadius: '0.625rem', border: '1px solid rgba(59,130,246,0.2)' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#60A5FA' }}>{stage || 'Processing...'}</span>
      <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#93C5FD' }}>{pct}%</span>
    </div>
    <div style={{ height: '6px', background: 'rgba(255,255,255,0.08)', borderRadius: '999px', overflow: 'hidden' }}>
      <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg,#3B82F6,#8B5CF6)', borderRadius: '999px', transition: 'width 0.5s ease' }} />
    </div>
  </div>
);

/* ─── Main Component ─────────────────────────────────────────── */
export default function DrhpGeneratorPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<FormData>(INITIAL);
  const [generating, setGenerating] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [useV2, setUseV2] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);
  const [showWorkspace, setShowWorkspace] = useState(false);
  const [activeNavSection, setActiveNavSection] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);

  const set = (field: keyof FormData, value: any) => setForm(f => ({ ...f, [field]: value }));
  const setPromoter = (i: number, field: keyof Promoter, value: string) => setForm(f => {
    const p = [...f.promoters]; p[i] = { ...p[i], [field]: value }; return { ...f, promoters: p };
  });
  const setFinancial = (i: number, field: keyof FinancialYear, value: string) => setForm(f => {
    const fy = [...f.financials]; fy[i] = { ...fy[i], [field]: value }; return { ...f, financials: fy };
  });
  const setUsage = (i: number, field: keyof UsageItem, value: string) => setForm(f => {
    const u = [...f.use_of_proceeds_items]; u[i] = { ...u[i], [field]: value }; return { ...f, use_of_proceeds_items: u };
  });

  // Connect SSE for real-time progress
  const connectSSE = useCallback((jid: string) => {
    if (eventSourceRef.current) eventSourceRef.current.close();
    const token = localStorage.getItem('access_token');
    // SSE via polling fallback since auth header can't be sent with EventSource
    const pollInterval = setInterval(async () => {
      try {
        const endpoint = useV2 ? `/workspaces/${workspaceId}/drhp/v2/status/${jid}` : `/workspaces/${workspaceId}/drhp/status/${jid}`;
        const status: any = await api.get(endpoint);
        setJobStatus({
          status: status.status,
          progress_pct: status.progress_pct ?? 0,
          current_stage: status.current_stage,
          message: status.message ?? '',
          sections_completed: status.sections_completed ?? 0,
          sections_total: status.sections_total ?? 0,
          drhp_ready: status.drhp_ready ?? false,
          intelligence_report_ready: status.intelligence_report_ready ?? false,
          warnings: status.warnings ?? [],
          errors: status.errors ?? [],
          total_time_seconds: status.total_time_seconds,
        });
        if (status.status === 'done' || status.status === 'error') {
          clearInterval(pollInterval);
          setGenerating(false);
        }
      } catch (err) {
        // ignore polling errors
      }
    }, 1500);
    return () => clearInterval(pollInterval);
  }, [workspaceId, useV2]);

  useEffect(() => {
    if (jobId && generating) {
      return connectSSE(jobId);
    }
  }, [jobId, generating, connectSSE]);

  /* ── Build v2 payload ── */
  const buildV2Payload = () => ({
    company: {
      name: form.company_name, cin: form.cin, pan: form.pan,
      incorporation_date: form.incorporation_date, registered_address: form.registered_address,
      sector: form.sector, sub_sector: form.sub_sector || null, website: form.website || null,
      description: form.description,
      employee_count: form.employee_count ? parseInt(form.employee_count) : null,
      key_products: form.key_products ? form.key_products.split(',').map(s => ({ name: s.trim() })) : null,
      geographies_served: form.geographies ? form.geographies.split(',').map(s => s.trim()) : null,
      certifications: form.certifications ? form.certifications.split(',').map(s => s.trim()) : null,
      statutory_auditor: form.statutory_auditor || null,
      listing_exchange: form.listing_exchange || null,
    },
    promoters: form.promoters.map(p => ({
      name: p.name, designation: p.designation, qualification: p.qualification || null,
      holding_pct: parseFloat(p.holding_pct) || 0,
      experience_years: p.experience_years ? parseInt(p.experience_years) : null,
    })),
    financials: form.financials.map(fy => ({
      year: fy.year, revenue: parseFloat(fy.revenue) || 0, net_profit: parseFloat(fy.net_profit) || 0,
      total_assets: parseFloat(fy.total_assets) || 0, total_equity: parseFloat(fy.total_equity) || 0,
      ebitda: fy.ebitda ? parseFloat(fy.ebitda) : null,
      total_debt: fy.total_debt ? parseFloat(fy.total_debt) : null,
      interest_expense: fy.interest_expense ? parseFloat(fy.interest_expense) : null,
    })),
    issue: {
      issue_size_cr: parseFloat(form.issue_size_cr) || 0,
      fresh_issue_cr: parseFloat(form.fresh_issue_cr) || 0,
      ofs_cr: parseFloat(form.ofs_cr) || 0,
      price_band_low: parseFloat(form.price_band_low) || 0,
      price_band_high: parseFloat(form.price_band_high) || 0,
      face_value: parseFloat(form.face_value) || 10,
      lot_size: parseInt(form.lot_size) || 0,
      objects_of_issue: form.objects_of_issue, use_of_proceeds: form.use_of_proceeds,
      merchant_banker: form.merchant_banker,
      use_of_proceeds_structured: form.use_of_proceeds_items.filter(u => u.purpose && u.amount_lakhs).map(u => ({
        purpose: u.purpose, amount_lakhs: parseFloat(u.amount_lakhs) || 0,
        timeline_months: u.timeline_months ? parseInt(u.timeline_months) : null,
      })),
    },
    generate_intelligence_report: form.generate_intelligence_report,
    generate_charts: form.generate_charts,
    use_llm_generation: form.use_llm,
    max_peers: 5,
  });

  /* ── Generate ── */
  const generate = async () => {
    setGenerating(true); setError(null);
    setJobStatus({ status: 'pending', progress_pct: 0, message: 'Starting pipeline...', sections_completed: 0, sections_total: 0, drhp_ready: false, intelligence_report_ready: false, warnings: [], errors: [] });
    try {
      const endpoint = useV2 ? `/workspaces/${workspaceId}/drhp/v2/generate` : `/workspaces/${workspaceId}/drhp/generate`;
      const payload = useV2 ? buildV2Payload() : {
        company: { name: form.company_name, cin: form.cin, pan: form.pan, incorporation_date: form.incorporation_date, registered_address: form.registered_address, sector: form.sector, sub_sector: form.sub_sector, website: form.website, description: form.description },
        promoters: form.promoters.map(p => ({ ...p, holding_pct: parseFloat(p.holding_pct) || 0 })),
        financials: form.financials.map(fy => ({ year: fy.year, revenue: parseFloat(fy.revenue)||0, net_profit: parseFloat(fy.net_profit)||0, total_assets: parseFloat(fy.total_assets)||0, total_equity: parseFloat(fy.total_equity)||0, ebitda: parseFloat(fy.ebitda)||0 })),
        issue: { issue_size_cr: parseFloat(form.issue_size_cr)||0, fresh_issue_cr: parseFloat(form.fresh_issue_cr)||0, ofs_cr: parseFloat(form.ofs_cr)||0, price_band_low: parseFloat(form.price_band_low)||0, price_band_high: parseFloat(form.price_band_high)||0, face_value: parseFloat(form.face_value)||10, lot_size: parseInt(form.lot_size)||0, objects_of_issue: form.objects_of_issue, use_of_proceeds: form.use_of_proceeds, merchant_banker: form.merchant_banker },
      };
      const res: any = await api.post(endpoint, payload);
      setJobId(res.job_id);
      setShowWorkspace(true);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Generation failed');
      setGenerating(false);
    }
  };

  const downloadDrhp = async () => {
    if (!jobId) return;
    try {
      const endpoint = useV2 ? `/workspaces/${workspaceId}/drhp/v2/download/${jobId}` : `/workspaces/${workspaceId}/drhp/download/${jobId}`;
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('ipo_copilot_token')}` }
      });
      if (!response.ok) throw new Error(`HTTP error ${response.status}`);
      const blob = await response.blob();
      const pdfBlob = new Blob([blob], { type: 'application/pdf' });
      let filename = `DRHP_${form.company_name.replace(/[\/\\:*?"<>| ]/g, '_')}.pdf`;
      const disp = response.headers.get('Content-Disposition');
      if (disp && disp.includes('filename=')) {
        filename = disp.split('filename=')[1].replace(/['"]/g, '').split(';')[0];
      }
      const url = URL.createObjectURL(pdfBlob);
      const a = document.createElement('a'); a.href = url; a.download = filename.endsWith('.pdf') ? filename : `${filename}.pdf`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) { setError('Download failed: ' + err.message); }
  };

  const downloadIntelligence = async () => {
    if (!jobId) return;
    try {
      const response = await fetch(`${API_BASE_URL}/workspaces/${workspaceId}/drhp/v2/intelligence/${jobId}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('ipo_copilot_token')}` }
      });
      if (!response.ok) throw new Error(`HTTP error ${response.status}`);
      const blob = await response.blob();
      const pdfBlob = new Blob([blob], { type: 'application/pdf' });
      let filename = `IPO_Intelligence_${form.company_name.replace(/[\/\\:*?"<>| ]/g, '_')}.pdf`;
      const disp = response.headers.get('Content-Disposition');
      if (disp && disp.includes('filename=')) {
        filename = disp.split('filename=')[1].replace(/['"]/g, '').split(';')[0];
      }
      const url = URL.createObjectURL(pdfBlob);
      const a = document.createElement('a'); a.href = url; a.download = filename.endsWith('.pdf') ? filename : `${filename}.pdf`;
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) { setError('Download failed: ' + err.message); }
  };

  const isDone = jobStatus?.status === 'done';
  const isError = jobStatus?.status === 'error';
  const pct = jobStatus?.progress_pct ?? 0;

  /* ══════════════ WORKSPACE VIEW (post-generation) ══════════════ */
  if (showWorkspace && jobId) {
    return (
      <div style={{ display: 'flex', height: '100vh', background: 'var(--bg-primary)', fontFamily: 'Inter, sans-serif', overflow: 'hidden' }}>

        {/* ── LEFT: Section Navigator ── */}
        <div style={{ width: '260px', flexShrink: 0, background: 'var(--bg-secondary)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '1rem', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
              <BookOpen size={16} color='#60A5FA' />
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>DRHP Sections</span>
            </div>
            <StageIndicator stage={jobStatus?.current_stage} pct={pct} />
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '0.5rem' }}>
            {DRHP_SECTIONS.map((sec, i) => {
              const done = isDone || (jobStatus?.sections_completed ?? 0) > i;
              const active = i === activeNavSection;
              return (
                <button key={sec} onClick={() => setActiveNavSection(i)}
                  style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 0.75rem', borderRadius: '0.5rem', background: active ? 'rgba(59,130,246,0.12)' : 'transparent', border: active ? '1px solid rgba(59,130,246,0.3)' : '1px solid transparent', cursor: 'pointer', textAlign: 'left', marginBottom: '2px' }}>
                  {done ? <CheckCircle size={13} color='#22C55E' /> : generating ? <Loader2 size={13} color='#60A5FA' style={{ animation: 'spin 1s linear infinite' }} /> : <Circle size={13} color='rgba(255,255,255,0.2)' />}
                  <span style={{ fontSize: '0.8rem', color: active ? '#93C5FD' : 'var(--text-secondary)', fontWeight: active ? 600 : 400 }}>{sec}</span>
                </button>
              );
            })}
          </div>
          {/* Consistency/Warnings panel */}
          {(jobStatus?.warnings?.length || 0) > 0 && (
            <div style={{ padding: '0.75rem', borderTop: '1px solid var(--border)', maxHeight: '160px', overflowY: 'auto' }}>
              <p style={{ fontSize: '0.7rem', fontWeight: 700, color: '#F59E0B', marginBottom: '0.5rem', textTransform: 'uppercase' }}>⚠ Warnings</p>
              {jobStatus!.warnings.slice(0, 5).map((w, i) => (
                <p key={i} style={{ fontSize: '0.69rem', color: '#FCA5A5', marginBottom: '0.25rem', lineHeight: 1.4 }}>{w}</p>
              ))}
            </div>
          )}
        </div>

        {/* ── CENTER: Main Content Area ── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Header bar */}
          <div style={{ padding: '0.875rem 1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--bg-secondary)' }}>
            <div>
              <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
                {form.company_name || 'DRHP'} — Enterprise Authoring Workspace
              </h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '0.125rem 0 0' }}>
                {isDone ? `✓ Generation complete in ${jobStatus?.total_time_seconds?.toFixed(0)}s` : isError ? '✗ Generation failed' : `Stage: ${jobStatus?.current_stage || 'Processing...'}`}
              </p>
            </div>
            <div style={{ display: 'flex', gap: '0.625rem' }}>
              <button onClick={() => setShowWorkspace(false)} style={{ padding: '0.5rem 0.875rem', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem', cursor: 'pointer' }}>
                ← Edit Form
              </button>
              {isDone && (
                <>
                  <button onClick={downloadDrhp} style={{ padding: '0.5rem 1rem', background: 'linear-gradient(135deg,#3B82F6,#2563EB)', border: 'none', borderRadius: '0.5rem', color: '#fff', fontSize: '0.8rem', cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                    <Download size={14} /> DRHP PDF
                  </button>
                  {jobStatus?.intelligence_report_ready && (
                    <button onClick={downloadIntelligence} style={{ padding: '0.5rem 1rem', background: 'linear-gradient(135deg,#8B5CF6,#7C3AED)', border: 'none', borderRadius: '0.5rem', color: '#fff', fontSize: '0.8rem', cursor: 'pointer', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                      <FileBarChart size={14} /> Intelligence Report
                    </button>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Main generation status */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
            {generating && !isDone && (
              <div style={{ marginBottom: '1.5rem', padding: '1.5rem', background: 'rgba(59,130,246,0.06)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: '0.875rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                  <Loader2 size={20} color='#60A5FA' style={{ animation: 'spin 1s linear infinite' }} />
                  <span style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#93C5FD' }}>Enterprise DRHP Pipeline Running</span>
                </div>
                <StageIndicator stage={jobStatus?.current_stage} pct={pct} />
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '0.75rem' }}>{jobStatus?.message}</p>
              </div>
            )}

            {isDone && (
              <div style={{ marginBottom: '1.5rem', padding: '1.5rem', background: 'rgba(34,197,94,0.06)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: '0.875rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <CheckCircle size={20} color='#22C55E' />
                  <span style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#86EFAC' }}>DRHP Generation Complete</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '0.75rem', marginTop: '1rem' }}>
                  {[
                    { label: 'DRHP PDF', icon: FileText, ready: jobStatus?.drhp_ready, color: '#3B82F6' },
                    { label: 'Intelligence Report', icon: FileBarChart, ready: jobStatus?.intelligence_report_ready, color: '#8B5CF6' },
                    { label: 'Time Taken', icon: Activity, ready: true, value: `${jobStatus?.total_time_seconds?.toFixed(0)}s`, color: '#10B981' },
                  ].map(card => (
                    <div key={card.label} style={{ padding: '0.875rem', background: 'rgba(255,255,255,0.04)', borderRadius: '0.625rem', border: '1px solid rgba(255,255,255,0.08)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.375rem' }}>
                        <card.icon size={14} color={card.color} />
                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>{card.label}</span>
                      </div>
                      <span style={{ fontSize: '0.875rem', fontWeight: 700, color: card.ready ? '#86EFAC' : '#FCA5A5' }}>
                        {card.value || (card.ready ? '✓ Ready' : '✗ Not Ready')}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {isError && (
              <div style={{ marginBottom: '1.5rem', padding: '1.25rem', background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: '0.875rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <AlertCircle size={18} color='#EF4444' />
                  <span style={{ fontWeight: 600, color: '#FCA5A5' }}>Pipeline Failed</span>
                </div>
                <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>{jobStatus?.message}</p>
              </div>
            )}

            {/* Section checklist */}
            <div>
              <h3 style={{ fontSize: '0.875rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Section Status</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
                {DRHP_SECTIONS.map((sec, i) => {
                  const done = isDone || (jobStatus?.sections_completed ?? 0) > i;
                  const active = !isDone && generating && Math.floor((pct / 100) * DRHP_SECTIONS.length) === i;
                  return (
                    <div key={sec} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 0.75rem', borderRadius: '0.5rem', background: active ? 'rgba(59,130,246,0.1)' : done ? 'rgba(34,197,94,0.06)' : 'rgba(255,255,255,0.02)', border: `1px solid ${active ? 'rgba(59,130,246,0.25)' : done ? 'rgba(34,197,94,0.15)' : 'rgba(255,255,255,0.05)'}` }}>
                      {done ? <CheckCircle size={13} color='#22C55E' /> : active ? <Loader2 size={13} color='#60A5FA' style={{ animation: 'spin 1s linear infinite' }} /> : <Circle size={13} color='rgba(255,255,255,0.15)' />}
                      <span style={{ fontSize: '0.78rem', color: done ? '#86EFAC' : active ? '#93C5FD' : 'var(--text-muted)' }}>{sec}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* ── RIGHT: Compliance Rail ── */}
        <div style={{ width: '240px', flexShrink: 0, background: 'var(--bg-secondary)', borderLeft: '1px solid var(--border)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '0.875rem 1rem', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Shield size={14} color='#60A5FA' />
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>SEBI Compliance</span>
            </div>
          </div>
          <div style={{ flex: 1, overflowY: 'auto', padding: '0.75rem' }}>
            {[
              { label: 'ICDR Reg 268 — SME IPO', status: 'reviewing' },
              { label: 'Promoter Lock-in', status: isDone ? 'checking' : 'pending' },
              { label: '3yr Audited Financials', status: form.financials.length >= 3 ? 'ok' : 'warn' },
              { label: 'Objects of Issue', status: form.objects_of_issue.length > 50 ? 'ok' : 'warn' },
              { label: 'Merchant Banker', status: form.merchant_banker ? 'ok' : 'warn' },
              { label: 'Face Value SEBI', status: ['1','2','5','10'].includes(form.face_value) ? 'ok' : 'warn' },
              { label: 'Fresh + OFS = Total', status: (() => { const total = (parseFloat(form.fresh_issue_cr)||0) + (parseFloat(form.ofs_cr)||0); const declared = parseFloat(form.issue_size_cr)||0; return declared > 0 && Math.abs(total - declared) < 0.05 ? 'ok' : 'warn'; })() },
              { label: 'Promoter Holdings ≤ 100%', status: (() => { const total = form.promoters.reduce((s, p) => s + (parseFloat(p.holding_pct)||0), 0); return total <= 100 ? 'ok' : 'error'; })() },
            ].map(item => (
              <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem', borderRadius: '0.375rem', marginBottom: '0.25rem', background: 'rgba(255,255,255,0.02)' }}>
                {item.status === 'ok' ? <CheckCircle size={12} color='#22C55E' /> : item.status === 'warn' ? <AlertTriangle size={12} color='#F59E0B' /> : item.status === 'error' ? <AlertCircle size={12} color='#EF4444' /> : <Loader2 size={12} color='#60A5FA' style={{ animation: 'spin 1s linear infinite' }} />}
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.3 }}>{item.label}</span>
              </div>
            ))}
          </div>
          {/* AI confidence summary */}
          <div style={{ padding: '0.75rem', borderTop: '1px solid var(--border)' }}>
            <p style={{ fontSize: '0.7rem', fontWeight: 700, color: '#60A5FA', marginBottom: '0.5rem', textTransform: 'uppercase' }}>AI Confidence</p>
            {[
              { label: 'LLM Sections', val: form.use_llm ? 85 : 0, color: '#8B5CF6' },
              { label: 'Algorithmic', val: 100, color: '#22C55E' },
              { label: 'Financial Data', val: form.financials.filter(f => f.revenue).length / 3 * 100, color: '#3B82F6' },
            ].map(bar => (
              <div key={bar.label} style={{ marginBottom: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                  <span style={{ fontSize: '0.69rem', color: 'var(--text-muted)' }}>{bar.label}</span>
                  <span style={{ fontSize: '0.69rem', fontWeight: 700, color: bar.color }}>{Math.round(bar.val)}%</span>
                </div>
                <div style={{ height: '4px', background: 'rgba(255,255,255,0.06)', borderRadius: '999px' }}>
                  <div style={{ height: '100%', width: `${bar.val}%`, background: bar.color, borderRadius: '999px' }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  /* ══════════════ FORM WIZARD VIEW ══════════════ */
  const renderStep = () => {
    switch (step) {
      /* Step 1: Company Profile */
      case 1: return (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
          <Field label="Company Name" required><input style={inp} value={form.company_name} onChange={e => set('company_name', e.target.value)} placeholder="Full legal name as per MCA records" /></Field>
          <Field label="CIN" required><input style={inp} value={form.cin} onChange={e => set('cin', e.target.value)} placeholder="U12345MH2015PLC123456" /></Field>
          <Field label="PAN" required><input style={inp} value={form.pan} onChange={e => set('pan', e.target.value)} placeholder="AAAPL1234C" /></Field>
          <Field label="Incorporation Date" required><input style={inp} type="date" value={form.incorporation_date} onChange={e => set('incorporation_date', e.target.value)} /></Field>
          <Field label="Sector" required span={1}><select style={inp} value={form.sector} onChange={e => set('sector', e.target.value)}><option value="">Select sector</option>{SECTORS.map(s => <option key={s} value={s}>{s}</option>)}</select></Field>
          <Field label="Sub-Sector"><input style={inp} value={form.sub_sector} onChange={e => set('sub_sector', e.target.value)} placeholder="e.g. Specialty Chemicals" /></Field>
          <Field label="Registered Address" span={2}><textarea style={{ ...inp, minHeight: '70px', resize: 'vertical' }} value={form.registered_address} onChange={e => set('registered_address', e.target.value)} placeholder="Complete registered office address" /></Field>
          <Field label="Website"><input style={inp} value={form.website} onChange={e => set('website', e.target.value)} placeholder="https://company.com" /></Field>
          <Field label="Employee Count"><input style={inp} type="number" value={form.employee_count} onChange={e => set('employee_count', e.target.value)} placeholder="e.g. 250" /></Field>
          <Field label="Listing Exchange"><select style={inp} value={form.listing_exchange} onChange={e => set('listing_exchange', e.target.value)}>{EXCHANGES.map(e => <option key={e} value={e}>{e}</option>)}</select></Field>
          <Field label="Statutory Auditor"><input style={inp} value={form.statutory_auditor} onChange={e => set('statutory_auditor', e.target.value)} placeholder="CA firm name (Peer Review Board certified)" /></Field>
          <Field label="Business Description" required span={2} hint="Minimum 200 words recommended. Describe the business model, products/services, market position."><textarea style={{ ...inp, minHeight: '120px', resize: 'vertical' }} value={form.description} onChange={e => set('description', e.target.value)} /></Field>
          <Field label="Key Products / Services (comma-separated)" span={2}><input style={inp} value={form.key_products} onChange={e => set('key_products', e.target.value)} placeholder="Product A, Product B, Service C" /></Field>
          <Field label="Geographies Served (comma-separated)"><input style={inp} value={form.geographies} onChange={e => set('geographies', e.target.value)} placeholder="Maharashtra, Gujarat, Pan-India" /></Field>
          <Field label="Certifications (comma-separated)"><input style={inp} value={form.certifications} onChange={e => set('certifications', e.target.value)} placeholder="ISO 9001, BIS, FSSAI" /></Field>
        </div>
      );
      /* Step 2: Promoters */
      case 2: return (
        <div>
          {form.promoters.map((p, i) => (
            <div key={i} style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '0.75rem', border: '1px solid var(--border)', marginBottom: '0.875rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.875rem' }}>
                <span style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-primary)' }}>Promoter {i + 1}</span>
                {form.promoters.length > 1 && <button onClick={() => setForm(f => ({ ...f, promoters: f.promoters.filter((_, idx) => idx !== i) }))} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#EF4444' }}><Trash2 size={14} /></button>}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <Field label="Full Name" required><input style={inp} value={p.name} onChange={e => setPromoter(i, 'name', e.target.value)} /></Field>
                <Field label="Designation"><input style={inp} value={p.designation} onChange={e => setPromoter(i, 'designation', e.target.value)} placeholder="Managing Director" /></Field>
                <Field label="Pre-Issue Holding %" required><input style={inp} type="number" step="0.01" max="100" value={p.holding_pct} onChange={e => setPromoter(i, 'holding_pct', e.target.value)} placeholder="e.g. 65.00" /></Field>
                <Field label="Experience (years)"><input style={inp} type="number" value={p.experience_years} onChange={e => setPromoter(i, 'experience_years', e.target.value)} /></Field>
                <Field label="Qualification" span={2}><input style={inp} value={p.qualification} onChange={e => setPromoter(i, 'qualification', e.target.value)} placeholder="B.E. Mechanical, MBA Finance" /></Field>
              </div>
            </div>
          ))}
          <p style={{ fontSize: '0.78rem', color: '#F59E0B', marginBottom: '0.75rem' }}>Total holding: {form.promoters.reduce((s, p) => s + (parseFloat(p.holding_pct) || 0), 0).toFixed(2)}%{form.promoters.reduce((s, p) => s + (parseFloat(p.holding_pct) || 0), 0) > 100 ? ' ⚠ Exceeds 100%' : ''}</p>
          <button onClick={() => setForm(f => ({ ...f, promoters: [...f.promoters, { ...DEFAULT_PROMOTER }] }))} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', background: 'rgba(59,130,246,0.08)', border: '1px dashed rgba(59,130,246,0.4)', borderRadius: '0.5rem', color: '#60A5FA', fontSize: '0.8125rem', cursor: 'pointer' }}><Plus size={14} /> Add Promoter</button>
        </div>
      );
      /* Step 3: Financials */
      case 3: return (
        <div>
          <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>All values in <strong>INR Lakhs</strong>. SEBI requires 3 years of audited financials. Extended fields improve ratio computation quality.</p>
          {form.financials.map((fy, i) => (
            <div key={i} style={{ padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '0.75rem', border: '1px solid var(--border)', marginBottom: '0.875rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <input style={{ ...inp, width: '160px', fontWeight: 700 }} value={fy.year} onChange={e => setFinancial(i, 'year', e.target.value)} placeholder="2023-24" />
                {form.financials.length > 1 && <button onClick={() => setForm(f => ({ ...f, financials: f.financials.filter((_, idx) => idx !== i) }))} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#EF4444' }}><Trash2 size={14} /></button>}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.875rem' }}>
                {[
                  ['Revenue', 'revenue', true, 'Total revenue/turnover'],
                  ['Net Profit (PAT)', 'net_profit', true, 'Can be negative'],
                  ['Total Assets', 'total_assets', true, ''],
                  ['Total Equity', 'total_equity', true, 'Net worth'],
                  ['EBITDA', 'ebitda', false, 'Optional but improves ratios'],
                  ['Total Debt', 'total_debt', false, 'All borrowings'],
                  ['Interest Expense', 'interest_expense', false, 'Finance costs'],
                ].map(([label, field, req, hint]) => (
                  <Field key={field as string} label={label as string} required={req as boolean} hint={hint as string}>
                    <input style={inp} type="number" step="0.01" value={(fy as any)[field as string]} onChange={e => setFinancial(i, field as keyof FinancialYear, e.target.value)} placeholder="0.00" />
                  </Field>
                ))}
              </div>
            </div>
          ))}
          <button onClick={() => setForm(f => ({ ...f, financials: [...f.financials, { ...DEFAULT_FY }] }))} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', background: 'rgba(59,130,246,0.08)', border: '1px dashed rgba(59,130,246,0.4)', borderRadius: '0.5rem', color: '#60A5FA', fontSize: '0.8125rem', cursor: 'pointer' }}><Plus size={14} /> Add Year</button>
        </div>
      );
      /* Step 4: Issue Details */
      case 4: return (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
          <Field label="Total Issue Size (₹ Crore)" required><input style={inp} type="number" step="0.01" value={form.issue_size_cr} onChange={e => set('issue_size_cr', e.target.value)} /></Field>
          <Field label="Fresh Issue (₹ Crore)"><input style={inp} type="number" step="0.01" value={form.fresh_issue_cr} onChange={e => set('fresh_issue_cr', e.target.value)} /></Field>
          <Field label="OFS Component (₹ Crore)"><input style={inp} type="number" step="0.01" value={form.ofs_cr} onChange={e => set('ofs_cr', e.target.value)} /></Field>
          <Field label="Price Band — Floor (₹)"><input style={inp} type="number" step="0.01" value={form.price_band_low} onChange={e => set('price_band_low', e.target.value)} /></Field>
          <Field label="Price Band — Cap (₹)" required><input style={inp} type="number" step="0.01" value={form.price_band_high} onChange={e => set('price_band_high', e.target.value)} /></Field>
          <Field label="Face Value (₹)" hint="SEBI: ₹1, ₹2, ₹5, or ₹10"><select style={inp} value={form.face_value} onChange={e => set('face_value', e.target.value)}>{['1','2','5','10'].map(v => <option key={v} value={v}>₹{v}</option>)}</select></Field>
          <Field label="Lot Size (shares/lot)"><input style={inp} type="number" value={form.lot_size} onChange={e => set('lot_size', e.target.value)} placeholder="e.g. 1200" /></Field>
          <Field label="Lead Manager (Merchant Banker)" required span={2}><input style={inp} value={form.merchant_banker} onChange={e => set('merchant_banker', e.target.value)} placeholder="SEBI-registered merchant banker name" /></Field>
          <Field label="Objects of the Issue" required span={2} hint="Specific, measurable deployment plan — minimum 100 words recommended"><textarea style={{ ...inp, minHeight: '100px', resize: 'vertical' }} value={form.objects_of_issue} onChange={e => set('objects_of_issue', e.target.value)} /></Field>
          <Field label="Use of Proceeds (narrative)" span={2}><textarea style={{ ...inp, minHeight: '80px', resize: 'vertical' }} value={form.use_of_proceeds} onChange={e => set('use_of_proceeds', e.target.value)} /></Field>
          <div style={{ gridColumn: 'span 2' }}>
            <p style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.625rem', textTransform: 'uppercase' }}>Use of Proceeds — Structured Breakdown (improves consistency checks)</p>
            {form.use_of_proceeds_items.map((item, i) => (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: '0.625rem', marginBottom: '0.5rem', alignItems: 'end' }}>
                <input style={inp} placeholder="Purpose (e.g. Capital Expenditure)" value={item.purpose} onChange={e => setUsage(i, 'purpose', e.target.value)} />
                <input style={inp} type="number" placeholder="Amount (₹L)" value={item.amount_lakhs} onChange={e => setUsage(i, 'amount_lakhs', e.target.value)} />
                <input style={inp} type="number" placeholder="Months" value={item.timeline_months} onChange={e => setUsage(i, 'timeline_months', e.target.value)} />
                {form.use_of_proceeds_items.length > 1 && <button onClick={() => setForm(f => ({ ...f, use_of_proceeds_items: f.use_of_proceeds_items.filter((_, idx) => idx !== i) }))} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#EF4444' }}><Trash2 size={14} /></button>}
              </div>
            ))}
            <button onClick={() => setForm(f => ({ ...f, use_of_proceeds_items: [...f.use_of_proceeds_items, { ...DEFAULT_USAGE }] }))} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.375rem 0.875rem', background: 'rgba(59,130,246,0.08)', border: '1px dashed rgba(59,130,246,0.4)', borderRadius: '0.5rem', color: '#60A5FA', fontSize: '0.8rem', cursor: 'pointer', marginTop: '0.375rem' }}><Plus size={13} /> Add Item</button>
          </div>
        </div>
      );
      /* Step 5: Generate */
      case 5: return (
        <div>
          <div style={{ padding: '1.25rem', background: 'rgba(59,130,246,0.06)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: '0.875rem', marginBottom: '1.25rem' }}>
            <h3 style={{ fontSize: '0.9375rem', fontWeight: 700, color: '#93C5FD', marginBottom: '0.875rem' }}>Generation Settings</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.875rem' }}>
              {[
                { key: 'use_llm', label: '🤖 LLM-Assisted Sections', desc: 'AI generates Business Overview, Industry, Risk Factors etc. using RAG + SEBI corpus' },
                { key: 'generate_intelligence_report', label: '📊 IPO Intelligence Report', desc: 'Generates second PDF: SWOT, Red Flags, Financial Analysis, Peer Benchmarking' },
                { key: 'generate_charts', label: '📈 Professional Charts', desc: 'Revenue/PAT trends, shareholding pattern, issue utilization embedded in PDF' },
              ].map(opt => (
                <label key={opt.key} style={{ display: 'flex', gap: '0.75rem', padding: '0.875rem', background: 'rgba(255,255,255,0.03)', borderRadius: '0.625rem', cursor: 'pointer', border: `1px solid ${(form as any)[opt.key] ? 'rgba(59,130,246,0.3)' : 'rgba(255,255,255,0.06)'}` }}>
                  <input type="checkbox" checked={(form as any)[opt.key]} onChange={e => set(opt.key as any, e.target.checked)} style={{ accentColor: '#3B82F6', marginTop: '2px' }} />
                  <div>
                    <p style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>{opt.label}</p>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{opt.desc}</p>
                  </div>
                </label>
              ))}
              <label style={{ display: 'flex', gap: '0.75rem', padding: '0.875rem', background: 'rgba(255,255,255,0.03)', borderRadius: '0.625rem', cursor: 'pointer', border: `1px solid ${useV2 ? 'rgba(139,92,246,0.3)' : 'rgba(255,255,255,0.06)'}` }}>
                <input type="checkbox" checked={useV2} onChange={e => setUseV2(e.target.checked)} style={{ accentColor: '#8B5CF6', marginTop: '2px' }} />
                <div>
                  <p style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>⚡ Enterprise Pipeline (v2)</p>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>12-stage modular pipeline with financial ratios, consistency checks, and resumability. Uncheck for legacy v1 template mode.</p>
                </div>
              </label>
            </div>
          </div>
          <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.75rem', border: '1px solid var(--border)', marginBottom: '1rem' }}>
            <h4 style={{ fontSize: '0.8125rem', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '0.625rem' }}>Pre-Generation Checklist</h4>
            {[
              { ok: form.company_name.length > 2, label: 'Company name provided' },
              { ok: form.cin.length > 5, label: 'CIN provided' },
              { ok: form.description.length > 100, label: 'Business description (>100 chars)' },
              { ok: form.promoters.length > 0 && form.promoters[0].name.length > 0, label: 'At least 1 promoter' },
              { ok: form.promoters.reduce((s, p) => s + (parseFloat(p.holding_pct)||0), 0) <= 100, label: 'Promoter holdings ≤ 100%' },
              { ok: form.financials.length >= 3, label: '3 financial years (SEBI requirement)' },
              { ok: form.financials.filter(f => parseFloat(f.revenue) > 0).length > 0, label: 'Revenue data provided' },
              { ok: parseFloat(form.issue_size_cr) > 0, label: 'Issue size specified' },
              { ok: form.objects_of_issue.length > 50, label: 'Objects of issue described' },
              { ok: form.merchant_banker.length > 2, label: 'Lead manager name provided' },
            ].map(c => (
              <div key={c.label} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.375rem' }}>
                {c.ok ? <CheckCircle size={13} color='#22C55E' /> : <AlertCircle size={13} color='#F59E0B' />}
                <span style={{ fontSize: '0.78rem', color: c.ok ? '#86EFAC' : '#FDE68A' }}>{c.label}</span>
              </div>
            ))}
          </div>
          {error && <div style={{ padding: '0.875rem', background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: '0.625rem', color: '#FCA5A5', fontSize: '0.8125rem', marginBottom: '1rem' }}>⚠ {error}</div>}
        </div>
      );
    }
  };

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '2rem 1.5rem', fontFamily: 'Inter, sans-serif' }}>
      {/* Header */}
      <div style={{ marginBottom: '1.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.375rem' }}>
          <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'linear-gradient(135deg,#3B82F6,#8B5CF6)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <FileText size={16} color='#fff' />
          </div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>Enterprise DRHP Generator</h1>
        </div>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>AI Merchant Banker Platform — SEBI ICDR 2018 Compliant</p>
      </div>

      {/* Step Tabs */}
      <div style={{ display: 'flex', gap: '0.375rem', marginBottom: '1.5rem', padding: '0.25rem', background: 'rgba(255,255,255,0.03)', borderRadius: '0.75rem', border: '1px solid var(--border)' }}>
        {STEPS.map(s => {
          const Icon = s.icon;
          const active = step === s.id;
          return (
            <button key={s.id} onClick={() => !generating && setStep(s.id)}
              style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.375rem', padding: '0.5625rem', borderRadius: '0.5rem', background: active ? 'linear-gradient(135deg,rgba(59,130,246,0.2),rgba(139,92,246,0.15))' : 'transparent', border: active ? '1px solid rgba(59,130,246,0.35)' : '1px solid transparent', color: active ? '#93C5FD' : 'var(--text-muted)', fontSize: '0.8rem', fontWeight: active ? 700 : 400, cursor: generating ? 'not-allowed' : 'pointer', transition: 'all 0.15s' }}>
              <Icon size={14} />{s.label}
            </button>
          );
        })}
      </div>

      {/* Form Card */}
      <div style={{ padding: '1.5rem', background: 'var(--bg-secondary)', borderRadius: '0.875rem', border: '1px solid var(--border)', marginBottom: '1.25rem', minHeight: '400px' }}>
        {renderStep()}
      </div>

      {/* Navigation + Generate */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button onClick={() => setStep(Math.max(1, step - 1))} disabled={step === 1 || generating}
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.6rem 1.25rem', background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border)', borderRadius: '0.625rem', color: 'var(--text-secondary)', fontSize: '0.875rem', cursor: step === 1 ? 'not-allowed' : 'pointer', opacity: step === 1 ? 0.4 : 1 }}>
          <ChevronLeft size={15} /> Previous
        </button>

        {step < 5 ? (
          <button onClick={() => setStep(Math.min(5, step + 1))}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.6rem 1.5rem', background: 'linear-gradient(135deg,#3B82F6,#2563EB)', border: 'none', borderRadius: '0.625rem', color: '#fff', fontSize: '0.875rem', fontWeight: 600, cursor: 'pointer' }}>
            Next <ChevronRight size={15} />
          </button>
        ) : (
          <button onClick={generate} disabled={generating}
            style={{ display: 'flex', alignItems: 'center', gap: '0.625rem', padding: '0.6875rem 1.75rem', background: generating ? 'rgba(59,130,246,0.4)' : 'linear-gradient(135deg,#3B82F6,#8B5CF6)', border: 'none', borderRadius: '0.625rem', color: '#fff', fontSize: '0.9375rem', fontWeight: 700, cursor: generating ? 'not-allowed' : 'pointer' }}>
            {generating ? <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Generating...</> : <><Zap size={16} /> Generate DRHP</>}
          </button>
        )}
      </div>
    </div>
  );
}

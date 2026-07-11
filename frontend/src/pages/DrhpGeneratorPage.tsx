import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Building2, Users, BarChart3, FileText, ChevronRight, ChevronLeft,
  CheckCircle, Download, Loader2, AlertCircle, Plus, Trash2,
} from 'lucide-react';
import api from '../api/client';

/* ─── Types ─────────────────────────────────────────────── */
interface Promoter {
  name: string;
  designation: string;
  qualification: string;
  holding_pct: string;
}

interface FinancialYear {
  year: string;
  revenue: string;
  net_profit: string;
  total_assets: string;
  total_equity: string;
  ebitda: string;
}

interface FormData {
  /* Step 1: Company */
  company_name: string;
  cin: string;
  pan: string;
  incorporation_date: string;
  registered_address: string;
  sector: string;
  sub_sector: string;
  website: string;
  description: string;

  /* Step 2: Promoters */
  promoters: Promoter[];

  /* Step 3: Financials */
  financials: FinancialYear[];

  /* Step 4: Issue Details */
  issue_size_cr: string;
  fresh_issue_cr: string;
  ofs_cr: string;
  price_band_low: string;
  price_band_high: string;
  face_value: string;
  lot_size: string;
  objects_of_issue: string;
  use_of_proceeds: string;
  merchant_banker: string;
}

const SECTORS = [
  'Manufacturing', 'Technology & IT', 'Healthcare & Pharma', 'Financial Services',
  'Retail & FMCG', 'Real Estate & Construction', 'Agriculture & Agro-processing',
  'Infrastructure & Logistics', 'Textiles & Apparel', 'Chemicals & Specialty',
  'Media & Entertainment', 'Education & Skilling', 'Tourism & Hospitality', 'Other',
];

const DEFAULT_PROMOTER: Promoter = { name: '', designation: '', qualification: '', holding_pct: '' };
const DEFAULT_FY: FinancialYear = { year: '', revenue: '', net_profit: '', total_assets: '', total_equity: '', ebitda: '' };

const STEPS = [
  { id: 1, label: 'Company Profile',   icon: Building2 },
  { id: 2, label: 'Promoter Details',  icon: Users },
  { id: 3, label: 'Financial Data',    icon: BarChart3 },
  { id: 4, label: 'Issue Details',     icon: FileText },
];

const INITIAL: FormData = {
  company_name: '', cin: '', pan: '', incorporation_date: '', registered_address: '',
  sector: '', sub_sector: '', website: '', description: '',
  promoters: [{ ...DEFAULT_PROMOTER }],
  financials: [
    { year: '2021-22', revenue: '', net_profit: '', total_assets: '', total_equity: '', ebitda: '' },
    { year: '2022-23', revenue: '', net_profit: '', total_assets: '', total_equity: '', ebitda: '' },
    { year: '2023-24', revenue: '', net_profit: '', total_assets: '', total_equity: '', ebitda: '' },
  ],
  issue_size_cr: '', fresh_issue_cr: '', ofs_cr: '', price_band_low: '', price_band_high: '',
  face_value: '10', lot_size: '', objects_of_issue: '', use_of_proceeds: '', merchant_banker: '',
};

/* ─── Helper Components ──────────────────────────────────── */
const Field: React.FC<{ label: string; required?: boolean; hint?: string; children: React.ReactNode }> = ({
  label, required, hint, children,
}) => (
  <div>
    <label className="form-label">
      {label}{required && <span style={{ color: 'var(--danger)', marginLeft: '2px' }}>*</span>}
    </label>
    {hint && <p style={{ margin: '0 0 0.375rem', fontSize: '0.78125rem', color: 'var(--text-muted)' }}>{hint}</p>}
    {children}
  </div>
);

const Grid: React.FC<{ cols?: number; children: React.ReactNode }> = ({ cols = 2, children }) => (
  <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: '1.25rem' }}>
    {children}
  </div>
);

/* ─── Main Component ─────────────────────────────────────── */
export default function DrhpGeneratorPage() {
  const { workspaceId } = useParams<{ workspaceId: string }>();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<FormData>(INITIAL);
  const [generating, setGenerating] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<'idle' | 'processing' | 'done' | 'error'>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const set = (field: keyof FormData, value: any) =>
    setForm((f) => ({ ...f, [field]: value }));

  const setPromoter = (i: number, field: keyof Promoter, value: string) =>
    setForm((f) => {
      const p = [...f.promoters];
      p[i] = { ...p[i], [field]: value };
      return { ...f, promoters: p };
    });

  const setFinancial = (i: number, field: keyof FinancialYear, value: string) =>
    setForm((f) => {
      const fy = [...f.financials];
      fy[i] = { ...fy[i], [field]: value };
      return { ...f, financials: fy };
    });

  const addPromoter = () =>
    setForm((f) => ({ ...f, promoters: [...f.promoters, { ...DEFAULT_PROMOTER }] }));

  const removePromoter = (i: number) =>
    setForm((f) => ({ ...f, promoters: f.promoters.filter((_, idx) => idx !== i) }));

  const addFY = () =>
    setForm((f) => ({ ...f, financials: [...f.financials, { ...DEFAULT_FY }] }));

  const removeFY = (i: number) =>
    setForm((f) => ({ ...f, financials: f.financials.filter((_, idx) => idx !== i) }));

  /* ── Generate DRHP ── */
  const generate = async () => {
    setGenerating(true);
    setError(null);
    setJobStatus('processing');
    setProgress(0);

    try {
      const payload = {
        company: {
          name: form.company_name, cin: form.cin, pan: form.pan,
          incorporation_date: form.incorporation_date,
          registered_address: form.registered_address,
          sector: form.sector, sub_sector: form.sub_sector,
          website: form.website, description: form.description,
        },
        promoters: form.promoters.map((p) => ({ ...p, holding_pct: parseFloat(p.holding_pct) || 0 })),
        financials: form.financials.map((fy) => ({
          year: fy.year,
          revenue: parseFloat(fy.revenue) || 0,
          net_profit: parseFloat(fy.net_profit) || 0,
          total_assets: parseFloat(fy.total_assets) || 0,
          total_equity: parseFloat(fy.total_equity) || 0,
          ebitda: parseFloat(fy.ebitda) || 0,
        })),
        issue: {
          issue_size_cr: parseFloat(form.issue_size_cr) || 0,
          fresh_issue_cr: parseFloat(form.fresh_issue_cr) || 0,
          ofs_cr: parseFloat(form.ofs_cr) || 0,
          price_band_low: parseFloat(form.price_band_low) || 0,
          price_band_high: parseFloat(form.price_band_high) || 0,
          face_value: parseFloat(form.face_value) || 10,
          lot_size: parseInt(form.lot_size) || 0,
          objects_of_issue: form.objects_of_issue,
          use_of_proceeds: form.use_of_proceeds,
          merchant_banker: form.merchant_banker,
        },
      };

      const res = await api.post(`/workspaces/${workspaceId}/drhp/generate`, payload);
      const jid = res.job_id;
      setJobId(jid);

      // Poll status
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        try {
          const status = await api.get(`/workspaces/${workspaceId}/drhp/status/${jid}`);
          setProgress(status.progress_pct ?? 0);
          if (status.status === 'done') {
            clearInterval(poll);
            setJobStatus('done');
            setGenerating(false);
          } else if (status.status === 'error') {
            clearInterval(poll);
            setJobStatus('error');
            setError(status.message || 'Generation failed.');
            setGenerating(false);
          }
        } catch {
          if (attempts > 60) {
            clearInterval(poll);
            setJobStatus('error');
            setError('Timed out waiting for DRHP generation.');
            setGenerating(false);
          }
        }
      }, 5000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start DRHP generation.');
      setJobStatus('error');
      setGenerating(false);
    }
  };

  const downloadDrhp = async () => {
    if (!jobId) return;
    const response = await api.get(`/workspaces/${workspaceId}/drhp/download/${jobId}`, { responseType: 'blob' });
    const blob = new Blob([response], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `DRHP_${form.company_name.replace(/\s+/g, '_')}_Draft.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  /* ── Render ── */
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">DRHP Generator</h1>
        <p className="page-subtitle">
          Generate a SEBI-compliant Draft Red Herring Prospectus (300–400 pages) from company and financial data
        </p>
      </div>

      {/* Step Indicator */}
      <div className="step-indicator" style={{ marginBottom: '2rem' }}>
        {STEPS.map((s, idx) => (
          <React.Fragment key={s.id}>
            <div className="step-item">
              <div className={`step-circle ${step > s.id ? 'done' : step === s.id ? 'active' : ''}`}>
                {step > s.id ? <CheckCircle size={14} strokeWidth={3} /> : s.id}
              </div>
              <span className={`step-label ${step === s.id ? 'active' : step > s.id ? 'done' : ''}`}>
                {s.label}
              </span>
            </div>
            {idx < STEPS.length - 1 && (
              <div className={`step-connector${step > s.id ? ' done' : ''}`} />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Form Card */}
      <div className="card" style={{ marginBottom: '1.5rem' }}>
        <div className="card-header">
          <h2 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {React.createElement(STEPS[step - 1].icon, { size: 18, color: 'var(--accent)' })}
            Step {step} of {STEPS.length} — {STEPS[step - 1].label}
          </h2>
        </div>
        <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

          {/* ── Step 1: Company Profile ── */}
          {step === 1 && (
            <>
              <Grid>
                <Field label="Company Name" required>
                  <input className="form-input" value={form.company_name} onChange={(e) => set('company_name', e.target.value)} placeholder="Acme Technologies Private Limited" />
                </Field>
                <Field label="Corporate Identity Number (CIN)" required>
                  <input className="form-input" value={form.cin} onChange={(e) => set('cin', e.target.value)} placeholder="U72900MH2020PTC123456" style={{ fontFamily: 'monospace' }} />
                </Field>
                <Field label="Permanent Account Number (PAN)" required>
                  <input className="form-input" value={form.pan} onChange={(e) => set('pan', e.target.value)} placeholder="AABCT1234A" style={{ fontFamily: 'monospace' }} />
                </Field>
                <Field label="Date of Incorporation" required>
                  <input className="form-input" type="date" value={form.incorporation_date} onChange={(e) => set('incorporation_date', e.target.value)} />
                </Field>
                <Field label="Sector" required>
                  <select className="form-input form-select" value={form.sector} onChange={(e) => set('sector', e.target.value)}>
                    <option value="">Select sector</option>
                    {SECTORS.map((s) => <option key={s}>{s}</option>)}
                  </select>
                </Field>
                <Field label="Sub-Sector / Industry Vertical">
                  <input className="form-input" value={form.sub_sector} onChange={(e) => set('sub_sector', e.target.value)} placeholder="e.g. Cloud Software, Generic APIs" />
                </Field>
                <Field label="Website">
                  <input className="form-input" value={form.website} onChange={(e) => set('website', e.target.value)} placeholder="https://www.acme.com" />
                </Field>
              </Grid>
              <Field label="Registered Address" required>
                <input className="form-input" value={form.registered_address} onChange={(e) => set('registered_address', e.target.value)} placeholder="123 Business Park, Andheri East, Mumbai, Maharashtra 400069" />
              </Field>
              <Field label="Business Description" required hint="A concise overview of your business, products/services, and competitive advantages (min 200 words recommended)">
                <textarea
                  className="form-input"
                  rows={5}
                  value={form.description}
                  onChange={(e) => set('description', e.target.value)}
                  placeholder="Describe your company's business, products, target markets, and key strengths..."
                  style={{ resize: 'vertical' }}
                />
              </Field>
            </>
          )}

          {/* ── Step 2: Promoters ── */}
          {step === 2 && (
            <>
              {form.promoters.map((p, i) => (
                <div key={i} style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '1.25rem', position: 'relative' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <p style={{ margin: 0, fontWeight: 600, fontSize: '0.9375rem' }}>Promoter {i + 1}</p>
                    {form.promoters.length > 1 && (
                      <button className="btn btn-danger btn-sm" onClick={() => removePromoter(i)}>
                        <Trash2 size={14} /> Remove
                      </button>
                    )}
                  </div>
                  <Grid>
                    <Field label="Full Name" required>
                      <input className="form-input" value={p.name} onChange={(e) => setPromoter(i, 'name', e.target.value)} placeholder="Rahul Sharma" />
                    </Field>
                    <Field label="Designation" required>
                      <input className="form-input" value={p.designation} onChange={(e) => setPromoter(i, 'designation', e.target.value)} placeholder="Managing Director" />
                    </Field>
                    <Field label="Qualification">
                      <input className="form-input" value={p.qualification} onChange={(e) => setPromoter(i, 'qualification', e.target.value)} placeholder="B.Tech, IIT Bombay; MBA, IIM Ahmedabad" />
                    </Field>
                    <Field label="Shareholding (%)" required>
                      <input className="form-input" type="number" min="0" max="100" step="0.01" value={p.holding_pct} onChange={(e) => setPromoter(i, 'holding_pct', e.target.value)} placeholder="65.00" />
                    </Field>
                  </Grid>
                </div>
              ))}
              <button className="btn btn-secondary btn-sm" onClick={addPromoter} style={{ width: 'fit-content' }}>
                <Plus size={15} /> Add Promoter
              </button>
              <div className="alert alert-info">
                <AlertCircle size={16} style={{ flexShrink: 0 }} />
                <span>As per SEBI ICDR Regulations, the minimum promoter contribution must be at least 20% of post-issue paid-up capital for a period of 3 years.</span>
              </div>
            </>
          )}

          {/* ── Step 3: Financials ── */}
          {step === 3 && (
            <>
              <div className="alert alert-info">
                <AlertCircle size={16} style={{ flexShrink: 0 }} />
                <span>Enter audited financial data for at least 3 preceding financial years. All values in Indian Rupees (INR), in Lakhs (₹ Lakhs) unless stated.</span>
              </div>
              {form.financials.map((fy, i) => (
                <div key={i} style={{ border: '1px solid var(--border)', borderRadius: '8px', padding: '1.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                    <Field label="Financial Year">
                      <input className="form-input" value={fy.year} onChange={(e) => setFinancial(i, 'year', e.target.value)} placeholder="2023-24" style={{ width: '140px' }} />
                    </Field>
                    {i >= 3 && (
                      <button className="btn btn-danger btn-sm" onClick={() => removeFY(i)}>
                        <Trash2 size={14} /> Remove
                      </button>
                    )}
                  </div>
                  <Grid cols={3}>
                    <Field label="Total Revenue (₹ Lakhs)" required>
                      <input className="form-input" type="number" value={fy.revenue} onChange={(e) => setFinancial(i, 'revenue', e.target.value)} placeholder="5000.00" />
                    </Field>
                    <Field label="EBITDA (₹ Lakhs)">
                      <input className="form-input" type="number" value={fy.ebitda} onChange={(e) => setFinancial(i, 'ebitda', e.target.value)} placeholder="800.00" />
                    </Field>
                    <Field label="Net Profit / (Loss) (₹ Lakhs)" required>
                      <input className="form-input" type="number" value={fy.net_profit} onChange={(e) => setFinancial(i, 'net_profit', e.target.value)} placeholder="420.00" />
                    </Field>
                    <Field label="Total Assets (₹ Lakhs)" required>
                      <input className="form-input" type="number" value={fy.total_assets} onChange={(e) => setFinancial(i, 'total_assets', e.target.value)} placeholder="8000.00" />
                    </Field>
                    <Field label="Total Equity / Net Worth (₹ Lakhs)" required>
                      <input className="form-input" type="number" value={fy.total_equity} onChange={(e) => setFinancial(i, 'total_equity', e.target.value)} placeholder="3500.00" />
                    </Field>
                  </Grid>
                </div>
              ))}
              <button className="btn btn-secondary btn-sm" onClick={addFY} style={{ width: 'fit-content' }}>
                <Plus size={15} /> Add Financial Year
              </button>
            </>
          )}

          {/* ── Step 4: Issue Details ── */}
          {step === 4 && (
            <>
              <div className="alert alert-info">
                <AlertCircle size={16} style={{ flexShrink: 0 }} />
                <span>For SME IPOs, the minimum issue size is ₹10 Crore and maximum is ₹25 Crore. The company must have a minimum face value of ₹10 per share.</span>
              </div>
              <Grid>
                <Field label="Total Issue Size (₹ Crore)" required>
                  <input className="form-input" type="number" value={form.issue_size_cr} onChange={(e) => set('issue_size_cr', e.target.value)} placeholder="15.00" />
                </Field>
                <Field label="Fresh Issue (₹ Crore)">
                  <input className="form-input" type="number" value={form.fresh_issue_cr} onChange={(e) => set('fresh_issue_cr', e.target.value)} placeholder="10.00" />
                </Field>
                <Field label="Offer for Sale / OFS (₹ Crore)">
                  <input className="form-input" type="number" value={form.ofs_cr} onChange={(e) => set('ofs_cr', e.target.value)} placeholder="5.00" />
                </Field>
                <Field label="Face Value per Share (₹)" required>
                  <input className="form-input" type="number" value={form.face_value} onChange={(e) => set('face_value', e.target.value)} placeholder="10" />
                </Field>
                <Field label="Price Band — Lower (₹)">
                  <input className="form-input" type="number" value={form.price_band_low} onChange={(e) => set('price_band_low', e.target.value)} placeholder="120" />
                </Field>
                <Field label="Price Band — Upper (₹)" required>
                  <input className="form-input" type="number" value={form.price_band_high} onChange={(e) => set('price_band_high', e.target.value)} placeholder="128" />
                </Field>
                <Field label="Lot Size (shares per lot)" required>
                  <input className="form-input" type="number" value={form.lot_size} onChange={(e) => set('lot_size', e.target.value)} placeholder="1000" />
                </Field>
                <Field label="Lead Merchant Banker" required>
                  <input className="form-input" value={form.merchant_banker} onChange={(e) => set('merchant_banker', e.target.value)} placeholder="Axis Capital Limited" />
                </Field>
              </Grid>
              <Field label="Objects of the Issue" required hint="List the specific purposes for which the IPO proceeds will be used">
                <textarea
                  className="form-input"
                  rows={4}
                  value={form.objects_of_issue}
                  onChange={(e) => set('objects_of_issue', e.target.value)}
                  placeholder="1. Expansion of manufacturing capacity&#10;2. Working capital requirements&#10;3. General corporate purposes"
                  style={{ resize: 'vertical' }}
                />
              </Field>
              <Field label="Use of Net Proceeds (Detailed)" hint="Provide a detailed break-up of how funds will be deployed, with amounts in ₹ Crore">
                <textarea
                  className="form-input"
                  rows={4}
                  value={form.use_of_proceeds}
                  onChange={(e) => set('use_of_proceeds', e.target.value)}
                  placeholder="₹8 Cr — Expansion of Pune plant&#10;₹2 Cr — Working capital&#10;₹2.5 Cr — Debt repayment&#10;Balance — General corporate purposes"
                  style={{ resize: 'vertical' }}
                />
              </Field>
            </>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button
          className="btn btn-secondary"
          onClick={() => setStep((s) => Math.max(1, s - 1))}
          disabled={step === 1}
        >
          <ChevronLeft size={17} /> Previous
        </button>

        {step < 4 ? (
          <button className="btn btn-primary" onClick={() => setStep((s) => Math.min(4, s + 1))}>
            Next <ChevronRight size={17} />
          </button>
        ) : (
          <button
            className="btn btn-primary btn-lg"
            onClick={generate}
            disabled={generating || jobStatus === 'done'}
            style={{ minWidth: '200px' }}
          >
            {generating
              ? <><Loader2 size={18} className="animate-spin" /> Generating ({progress}%)...</>
              : jobStatus === 'done'
              ? <><CheckCircle size={18} /> DRHP Generated</>
              : <><FileText size={18} /> Generate DRHP Document</>}
          </button>
        )}
      </div>

      {/* Progress / Done State */}
      {generating && (
        <div className="card" style={{ marginTop: '1.5rem', padding: '1.5rem' }}>
          <p style={{ margin: '0 0 0.75rem', fontWeight: 600 }}>Generating DRHP...</p>
          <div style={{ height: '8px', background: 'var(--bg-muted)', borderRadius: '99px', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${progress}%`, background: 'var(--accent)', borderRadius: '99px', transition: 'width 0.5s ease' }} />
          </div>
          <p style={{ margin: '0.5rem 0 0', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            Drafting sections, computing financial tables, and assembling PDF...
          </p>
        </div>
      )}

      {jobStatus === 'done' && (
        <div className="card" style={{ marginTop: '1.5rem', padding: '1.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem', marginBottom: '1rem' }}>
            <CheckCircle size={28} color="var(--success)" />
            <div>
              <p style={{ margin: 0, fontWeight: 700, fontSize: '1.0625rem', color: 'var(--text-primary)' }}>
                DRHP Generated Successfully
              </p>
              <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Your Draft Red Herring Prospectus has been generated and is ready for download.
              </p>
            </div>
          </div>
          <div className="alert alert-warning" style={{ marginBottom: '1rem', fontSize: '0.875rem' }}>
            This is an AI-generated draft document. It must be reviewed and approved by a SEBI-registered merchant banker before filing.
          </div>
          <button className="btn btn-primary" onClick={downloadDrhp}>
            <Download size={17} /> Download DRHP PDF
          </button>
        </div>
      )}

      {jobStatus === 'error' && error && (
        <div className="alert alert-danger" style={{ marginTop: '1.5rem' }}>
          <AlertCircle size={16} style={{ flexShrink: 0 }} />
          <span><strong>Generation failed: </strong>{error}</span>
        </div>
      )}
    </div>
  );
}

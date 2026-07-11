import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Building2, Briefcase, ArrowRight, ArrowLeft, CheckCircle, AlertCircle, ShieldCheck } from 'lucide-react';
import { useCreateCompany } from '@/api/companies';
import { useCreateWorkspace, useCreateDemoWorkspace } from '@/api/workspaces';
import { useWorkspaceStore } from '@/store/workspaceStore';

const INDUSTRIES = [
  'Manufacturing', 'Technology & IT', 'Healthcare & Pharma', 'Financial Services',
  'Retail & FMCG', 'Real Estate & Construction', 'Agriculture & Food Processing',
  'Infrastructure & Logistics', 'Textiles & Apparel', 'Chemicals & Pharmaceuticals', 'Other',
];

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [companyId, setCompanyId] = useState<string | null>(null);

  const [companyName, setCompanyName] = useState('');
  const [cin, setCin] = useState('');
  const [pan, setPan] = useState('');
  const [industry, setIndustry] = useState('');
  const [workspaceName, setWorkspaceName] = useState('');
  const [formError, setFormError] = useState('');

  const setCurrentWorkspace = useWorkspaceStore((s) => s.setCurrentWorkspace);
  const createCompany = useCreateCompany();
  const createWorkspace = useCreateWorkspace();
  const createDemoWorkspace = useCreateDemoWorkspace();

  const validateCompany = () => {
    if (!companyName.trim() || companyName.length < 2) return 'Company name must be at least 2 characters.';
    if (cin.length !== 21) return 'CIN must be exactly 21 characters.';
    if (pan.length !== 10) return 'PAN must be exactly 10 characters.';
    if (!industry) return 'Please select an industry.';
    return '';
  };

  const handleCompanyNext = async () => {
    const err = validateCompany();
    if (err) { setFormError(err); return; }
    setFormError('');
    try {
      const company = await createCompany.mutateAsync({ name: companyName, cin, pan, industry });
      setCompanyId(company.id);
      setWorkspaceName(`${companyName} IPO 2026`);
      setStep(2);
    } catch {
      setFormError('Failed to create company. Please try again.');
    }
  };

  const handleWorkspaceLaunch = async () => {
    if (!companyId) return;
    if (!workspaceName.trim()) { setFormError('Workspace name is required.'); return; }
    setFormError('');
    try {
      const ws = await createWorkspace.mutateAsync({ company_id: companyId, name: workspaceName });
      setCurrentWorkspace(ws.id, ws.name);
      navigate(`/app/dashboard/${ws.id}`);
    } catch {
      setFormError('Failed to create workspace. Please try again.');
    }
  };

  const handleLoadDemo = async () => {
    setFormError('');
    try {
      const ws = await createDemoWorkspace.mutateAsync();
      setCurrentWorkspace(ws.id, ws.name);
      navigate(`/app/dashboard/${ws.id}`);
    } catch {
      setFormError('Failed to load demo workspace. Please ensure the API server is running.');
    }
  };

  const isLoading = createCompany.isPending || createWorkspace.isPending || createDemoWorkspace.isPending;

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg-page)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '2rem',
    }}>
      <div style={{ width: '100%', maxWidth: '480px' }}>

        {/* Branding */}
        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: '52px', height: '52px', borderRadius: '14px',
            background: '#003087', marginBottom: '1.25rem',
          }}>
            <ShieldCheck size={26} color="white" strokeWidth={2} />
          </div>
          <h1 style={{ fontSize: '1.625rem', fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 0.375rem', letterSpacing: '-0.025em' }}>
            Company Onboarding
          </h1>
          <p style={{ fontSize: '0.9375rem', color: 'var(--text-secondary)', margin: 0 }}>
            Set up your company profile to begin the IPO preparation process
          </p>
        </div>

        {/* Step Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2rem' }}>
          {[
            { id: 1, label: 'Company Details', icon: Building2 },
            { id: 2, label: 'IPO Workspace',   icon: Briefcase },
          ].map((s, i) => (
            <React.Fragment key={s.id}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <div style={{
                  width: '30px', height: '30px', borderRadius: '50%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.8125rem', fontWeight: 700, flexShrink: 0,
                  border: '2px solid',
                  borderColor: step > s.id ? 'var(--success)' : step === s.id ? 'var(--accent)' : 'var(--border)',
                  background: step > s.id ? 'var(--success)' : step === s.id ? 'var(--accent)' : 'white',
                  color: step >= s.id ? 'white' : 'var(--text-muted)',
                }}>
                  {step > s.id ? <CheckCircle size={14} strokeWidth={3} /> : s.id}
                </div>
                <span style={{
                  fontSize: '0.8125rem', fontWeight: 600,
                  color: step === s.id ? 'var(--accent)' : step > s.id ? 'var(--success)' : 'var(--text-muted)',
                }}>
                  {s.label}
                </span>
              </div>
              {i < 1 && <div style={{ flex: 1, height: '2px', background: step > 1 ? 'var(--success)' : 'var(--border)', margin: '0 0.75rem' }} />}
            </React.Fragment>
          ))}
        </div>

        {/* Card */}
        <div className="card" style={{ padding: '2rem' }}>

          {formError && (
            <div className="alert alert-danger" style={{ marginBottom: '1.25rem' }}>
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{formError}</span>
            </div>
          )}

          {/* Step 1 — Company Details */}
          {step === 1 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.125rem' }}>
              <div>
                <h2 style={{ margin: '0 0 0.25rem', fontSize: '1.0625rem', fontWeight: 700 }}>Company Details</h2>
                <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Enter your company's official registration information</p>
              </div>

              <div>
                <label className="form-label" htmlFor="company-name">Company Name <span style={{ color: 'var(--danger)' }}>*</span></label>
                <input
                  id="company-name"
                  className="form-input"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="Acme Technologies Private Limited"
                />
              </div>

              <div>
                <label className="form-label" htmlFor="cin">Corporate Identity Number (CIN) <span style={{ color: 'var(--danger)' }}>*</span></label>
                <input
                  id="cin"
                  className="form-input"
                  value={cin}
                  onChange={(e) => setCin(e.target.value.toUpperCase())}
                  placeholder="U72900MH2020PTC123456"
                  maxLength={21}
                  style={{ fontFamily: 'var(--font-mono)', letterSpacing: '0.04em' }}
                />
              </div>

              <div>
                <label className="form-label" htmlFor="pan">PAN <span style={{ color: 'var(--danger)' }}>*</span></label>
                <input
                  id="pan"
                  className="form-input"
                  value={pan}
                  onChange={(e) => setPan(e.target.value.toUpperCase())}
                  placeholder="AABCT1234A"
                  maxLength={10}
                  style={{ fontFamily: 'var(--font-mono)', letterSpacing: '0.04em' }}
                />
              </div>

              <div>
                <label className="form-label" htmlFor="industry">Industry / Sector <span style={{ color: 'var(--danger)' }}>*</span></label>
                <select
                  id="industry"
                  className="form-input form-select"
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                >
                  <option value="">Select industry</option>
                  {INDUSTRIES.map((ind) => <option key={ind} value={ind}>{ind}</option>)}
                </select>
              </div>

              <button
                className="btn btn-primary btn-lg"
                style={{ width: '100%', marginTop: '0.5rem' }}
                onClick={handleCompanyNext}
                disabled={isLoading}
              >
                {createCompany.isPending
                  ? <><span className="spinner" style={{ width: '16px', height: '16px', borderTopColor: 'white', borderColor: 'rgba(255,255,255,0.3)' }} /> Saving...</>
                  : <>Continue <ArrowRight size={16} /></>}
              </button>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', margin: '0.5rem 0' }}>
                <hr style={{ flex: 1, border: 'none', borderTop: '1px solid var(--border)' }} />
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Or</span>
                <hr style={{ flex: 1, border: 'none', borderTop: '1px solid var(--border)' }} />
              </div>

              <button
                className="btn btn-secondary"
                style={{ width: '100%' }}
                onClick={handleLoadDemo}
                disabled={isLoading}
              >
                {createDemoWorkspace.isPending
                  ? <><span className="spinner" style={{ width: '14px', height: '14px' }} /> Loading Demo...</>
                  : 'Load Sample Enterprise Workspace'}
              </button>
            </div>
          )}

          {/* Step 2 — Workspace */}
          {step === 2 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.125rem' }}>
              <div>
                <h2 style={{ margin: '0 0 0.25rem', fontSize: '1.0625rem', fontWeight: 700 }}>Create IPO Workspace</h2>
                <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>A secure data room for all your IPO documents and filings</p>
              </div>

              <div>
                <label className="form-label" htmlFor="workspace-name">Workspace Name <span style={{ color: 'var(--danger)' }}>*</span></label>
                <input
                  id="workspace-name"
                  className="form-input"
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  placeholder="Acme Technologies IPO 2026"
                />
              </div>

              <div className="alert alert-info" style={{ fontSize: '0.875rem' }}>
                Your workspace stores all uploaded documents, compliance checks, and generated DRHP drafts in one secure location.
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                <button
                  className="btn btn-secondary"
                  style={{ flex: 1 }}
                  onClick={() => { setStep(1); setFormError(''); }}
                  disabled={isLoading}
                >
                  <ArrowLeft size={16} /> Back
                </button>
                <button
                  className="btn btn-primary"
                  style={{ flex: 2 }}
                  onClick={handleWorkspaceLaunch}
                  disabled={isLoading}
                >
                  {createWorkspace.isPending
                    ? <><span className="spinner" style={{ width: '16px', height: '16px', borderTopColor: 'white', borderColor: 'rgba(255,255,255,0.3)' }} /> Creating...</>
                    : <>Launch Workspace <ArrowRight size={16} /></>}
                </button>
              </div>
            </div>
          )}
        </div>

        <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '1.5rem' }}>
          All data is encrypted and stored securely. SEBI compliance logging is enabled.
        </p>
      </div>
    </div>
  );
}

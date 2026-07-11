import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, UserPlus, AlertCircle, ShieldCheck } from 'lucide-react';
import { useRegister } from '@/api/auth';
import { useAuthStore } from '@/store/authStore';

const ROLE_LABELS: Record<string, string> = {
  company_secretary: 'Company Secretary',
  investment_banker: 'Investment Banker / Merchant Banker',
  legal_counsel: 'Legal Counsel',
  auditor: 'Auditor / Chartered Accountant',
  admin: 'Administrator',
};

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const registerMutation = useRegister();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [error, setError] = useState('');

  React.useEffect(() => {
    if (isAuthenticated) navigate('/app/onboarding', { replace: true });
  }, [isAuthenticated, navigate]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (fullName.trim().length < 2) { setError('Name must be at least 2 characters.'); return; }
    if (!email.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) { setError('Please enter a valid email.'); return; }
    if (!role) { setError('Please select a role.'); return; }
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    if (password !== confirmPassword) { setError('Passwords do not match.'); return; }

    registerMutation.mutate(
      { full_name: fullName, email, password, role },
      {
        onSuccess: () => navigate('/app/onboarding', { replace: true }),
        onError: (err: any) =>
          setError(err.response?.data?.detail || 'Registration failed. Please try again.'),
      }
    );
  };

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg-page)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '2rem',
    }}>
      <div style={{ width: '100%', maxWidth: '440px' }}>

        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
            width: '52px', height: '52px', borderRadius: '14px',
            background: '#003087', marginBottom: '1.25rem',
          }}>
            <ShieldCheck size={26} color="white" strokeWidth={2} />
          </div>
          <h1 style={{ fontSize: '1.625rem', fontWeight: 800, color: 'var(--text-primary)', margin: '0 0 0.375rem', letterSpacing: '-0.025em' }}>
            Create Account
          </h1>
          <p style={{ fontSize: '0.9375rem', color: 'var(--text-secondary)', margin: 0 }}>
            Join IPO Copilot AI — SEBI TechSprint 2026
          </p>
        </div>

        {/* Card */}
        <div className="card" style={{ padding: '2rem' }}>
          {error && (
            <div className="alert alert-danger" style={{ marginBottom: '1.25rem' }}>
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label className="form-label" htmlFor="full-name">Full Name <span style={{ color: 'var(--danger)' }}>*</span></label>
              <input id="full-name" className="form-input" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Rahul Sharma" />
            </div>

            <div>
              <label className="form-label" htmlFor="reg-email">Email Address <span style={{ color: 'var(--danger)' }}>*</span></label>
              <input id="reg-email" type="email" className="form-input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" />
            </div>

            <div>
              <label className="form-label" htmlFor="role">Role <span style={{ color: 'var(--danger)' }}>*</span></label>
              <select id="role" className="form-input form-select" value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="">Select your role</option>
                {Object.entries(ROLE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>

            <div>
              <label className="form-label" htmlFor="password">Password <span style={{ color: 'var(--danger)' }}>*</span></label>
              <div style={{ position: 'relative' }}>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  className="form-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Minimum 8 characters"
                  style={{ paddingRight: '2.75rem' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((p) => !p)}
                  style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex' }}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>

            <div>
              <label className="form-label" htmlFor="confirm">Confirm Password <span style={{ color: 'var(--danger)' }}>*</span></label>
              <div style={{ position: 'relative' }}>
                <input
                  id="confirm"
                  type={showConfirm ? 'text' : 'password'}
                  className="form-input"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat password"
                  style={{ paddingRight: '2.75rem' }}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm((p) => !p)}
                  style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex' }}
                >
                  {showConfirm ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={registerMutation.isPending}
              className="btn btn-primary btn-lg"
              style={{ width: '100%', marginTop: '0.375rem' }}
            >
              {registerMutation.isPending
                ? <span className="spinner" style={{ width: '16px', height: '16px', borderTopColor: 'white', borderColor: 'rgba(255,255,255,0.3)' }} />
                : <UserPlus size={17} />}
              {registerMutation.isPending ? 'Creating Account...' : 'Create Account'}
            </button>
          </form>

          <hr className="divider" />
          <p style={{ textAlign: 'center', fontSize: '0.875rem', color: 'var(--text-secondary)', margin: 0 }}>
            Already have an account?{' '}
            <Link to="/login" style={{ fontWeight: 600, color: 'var(--accent)' }}>Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;

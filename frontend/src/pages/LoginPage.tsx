import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ShieldCheck, AlertCircle } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import api from '../api/client';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await api.post('/auth/login', { email, password });
      const user = data.user ?? { id: '', email, full_name: email, role: 'user' };
      setAuth(user, data.access_token);
      localStorage.setItem('ipo_copilot_token', data.access_token);
      navigate('/app/onboarding');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', background: 'var(--bg-page)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '2rem',
    }}>
      <div style={{ width: '100%', maxWidth: '420px' }}>

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
            Sign in to IPO Copilot
          </h1>
          <p style={{ fontSize: '0.9375rem', color: 'var(--text-secondary)', margin: 0 }}>
            SEBI Securities Market TechSprint 2026
          </p>
        </div>

        {/* Card */}
        <div className="card" style={{ padding: '2rem' }}>
          {error && (
            <div className="alert alert-danger" style={{ marginBottom: '1.25rem' }}>
              <AlertCircle size={16} style={{ flexShrink: 0, marginTop: '1px' }} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.125rem' }}>
            <div>
              <label className="form-label" htmlFor="email">Email Address</label>
              <input
                id="email"
                type="email"
                required
                className="form-input"
                placeholder="you@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div>
              <label className="form-label" htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                required
                className="form-input"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary btn-lg"
              style={{ marginTop: '0.25rem', width: '100%' }}
            >
              {loading ? <span className="spinner" style={{ width: '18px', height: '18px', borderTopColor: 'white', borderColor: 'rgba(255,255,255,0.3)' }} /> : null}
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <hr className="divider" />

          <p style={{ textAlign: 'center', fontSize: '0.875rem', color: 'var(--text-secondary)', margin: 0 }}>
            Don&apos;t have an account?{' '}
            <Link to="/register" style={{ fontWeight: 600, color: 'var(--accent)' }}>
              Create account
            </Link>
          </p>
        </div>

        <p style={{ textAlign: 'center', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '1.5rem' }}>
          This platform is for authorised IPO preparers only.
          All activity is logged per SEBI compliance requirements.
        </p>
      </div>
    </div>
  );
};

export default LoginPage;

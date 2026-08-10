import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props { children: ReactNode; fallback?: ReactNode; }
interface State { hasError: boolean; errorMessage: string; }

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, errorMessage: error?.message ?? 'An unexpected error occurred.' };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Log in development only
    if ((import.meta as any).env?.DEV) {
      // eslint-disable-next-line no-console
      console.error('[ErrorBoundary]', error, info.componentStack);
    }
  }

  handleRetry = () => this.setState({ hasError: false, errorMessage: '' });

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div role="alert" aria-live="assertive" style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-page, #F1F5F9)', padding: '2rem', fontFamily: 'Inter, system-ui, sans-serif' }}>
          <div style={{ background: 'var(--bg-card, #FFFFFF)', border: '1px solid var(--border, #E2E8F0)', borderRadius: '16px', padding: '3rem 2.5rem', maxWidth: '480px', width: '100%', textAlign: 'center', boxShadow: '0 4px 24px rgba(0,0,0,0.06)' }}>
            <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: 'rgba(185,28,28,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem' }}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#B91C1C" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary, #0F172A)', margin: '0 0 0.5rem' }}>Something went wrong</h1>
            <p style={{ fontSize: '0.9375rem', color: 'var(--text-secondary, #475569)', margin: '0 0 2rem', lineHeight: 1.6 }}>
              An unexpected error occurred. Your session and data are safe — this is a display error only.
            </p>
            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              <button onClick={this.handleRetry} style={{ padding: '0.625rem 1.5rem', background: '#003087', color: '#FFFFFF', border: 'none', borderRadius: '8px', fontWeight: 600, fontSize: '0.9rem', cursor: 'pointer', fontFamily: 'inherit' }}>
                Try again
              </button>
              <button onClick={() => window.location.reload()} style={{ padding: '0.625rem 1.5rem', background: 'transparent', color: 'var(--text-secondary, #475569)', border: '1px solid var(--border, #E2E8F0)', borderRadius: '8px', fontWeight: 600, fontSize: '0.9rem', cursor: 'pointer', fontFamily: 'inherit' }}>
                Reload page
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;

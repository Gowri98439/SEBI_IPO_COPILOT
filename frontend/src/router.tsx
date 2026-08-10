import React, { Suspense } from 'react';
import {
  createBrowserRouter,
  RouterProvider,
  Navigate,
  useLocation,
} from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import AppShell from './components/layout/AppShell';

const LoginPage = React.lazy(() => import('./pages/LoginPage'));
const RegisterPage = React.lazy(() => import('./pages/RegisterPage'));
const OnboardingPage = React.lazy(() => import('./pages/OnboardingPage'));
const WorkspacePage = React.lazy(() => import('./pages/WorkspacePage'));
const DocumentUploadPage = React.lazy(() => import('./pages/DocumentUploadPage'));
const ValidationPage = React.lazy(() => import('./pages/ValidationPage'));
const CompliancePage = React.lazy(() => import('./pages/CompliancePage'));
const CopilotPage = React.lazy(() => import('./pages/CopilotPage'));
const DraftReviewPage = React.lazy(() => import('./pages/DraftReviewPage'));
const HumanReviewPage = React.lazy(() => import('./pages/HumanReviewPage'));
const VersionsPage = React.lazy(() => import('./pages/VersionsPage'));
const DashboardPage = React.lazy(() => import('./pages/DashboardPage'));
const ExportPage = React.lazy(() => import('./pages/ExportPage'));
const AuditLogPage = React.lazy(() => import('./pages/AuditLogPage'));
const DrhpGeneratorPage = React.lazy(() => import('./pages/DrhpGeneratorPage'));


// Full-screen loader shown during lazy load
const PageLoader: React.FC = () => (
  <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-page, #F1F5F9)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
      <div style={{ width: '40px', height: '40px', borderRadius: '50%', border: '2px solid #003087', borderTopColor: 'transparent', animation: 'spin 0.8s linear infinite' }} />
      <p style={{ color: '#475569', fontSize: '0.875rem', fontWeight: 500 }}>Loading…</p>
    </div>
  </div>
);

// Inline 404 page — shown when no route matches
const NotFound: React.FC = () => (
  <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-page, #F1F5F9)', padding: '2rem', fontFamily: 'Inter, system-ui, sans-serif' }}>
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: '6rem', fontWeight: 800, color: 'var(--text-primary, #0F172A)', lineHeight: 1, marginBottom: '1rem' }}>404</div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary, #0F172A)', margin: '0 0 0.75rem' }}>Page not found</h1>
      <p style={{ color: 'var(--text-secondary, #475569)', margin: '0 0 2rem', lineHeight: 1.6 }}>The page you’re looking for doesn’t exist or has been moved.</p>
      <a href="/login" style={{ padding: '0.625rem 1.5rem', background: '#003087', color: '#fff', borderRadius: '8px', fontWeight: 600, textDecoration: 'none', fontSize: '0.9rem' }}>Go home</a>
    </div>
  </div>
);

// Protected layout – redirects to /login when unauthenticated
const ProtectedLayout: React.FC = () => {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return (
    <Suspense fallback={<PageLoader />}>
      <AppShell />
    </Suspense>
  );
};

const router = createBrowserRouter([
  // ── Public routes ──────────────────────────────────────────────────────────
  {
    path: '/login',
    element: (
      <Suspense fallback={<PageLoader />}>
        <LoginPage />
      </Suspense>
    ),
  },
  {
    path: '/register',
    element: (
      <Suspense fallback={<PageLoader />}>
        <RegisterPage />
      </Suspense>
    ),
  },

  // ── Protected routes ───────────────────────────────────────────────────────
  {
    path: '/app',
    element: <ProtectedLayout />,
    children: [
      { index: true, element: <Navigate to="/app/onboarding" replace /> },
      { path: 'onboarding', element: <OnboardingPage /> },
      { path: 'workspace/:workspaceId', element: <WorkspacePage /> },
      { path: 'upload/:workspaceId', element: <DocumentUploadPage /> },
      { path: 'validation/:workspaceId', element: <ValidationPage /> },
      { path: 'compliance/:workspaceId', element: <CompliancePage /> },
      { path: 'copilot/:workspaceId', element: <CopilotPage /> },
      { path: 'drhp/:workspaceId', element: <DrhpGeneratorPage /> },
      { path: 'draft/:workspaceId', element: <DraftReviewPage /> },
      { path: 'human-review/:workspaceId', element: <HumanReviewPage /> },
      { path: 'versions/:workspaceId', element: <VersionsPage /> },
      { path: 'dashboard/:workspaceId', element: <DashboardPage /> },
      { path: 'export/:workspaceId', element: <ExportPage /> },
      { path: 'audit-log/:workspaceId', element: <AuditLogPage /> },
    ],
  },

  // ── Fallback ───────────────────────────────────────────────────────────────
  { path: '/', element: <Navigate to="/login" replace /> },
  { path: '*', element: <NotFound /> },
]);

export const AppRouter: React.FC = () => <RouterProvider router={router} />;
export default AppRouter;

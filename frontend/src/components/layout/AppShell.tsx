import React from 'react';
import { Outlet, NavLink, useNavigate, useParams } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderOpen,
  ShieldCheck,
  MessageSquare,
  FileText,
  ScrollText,
  Download,
  LogOut,
  ChevronRight,
} from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { useWorkspaceStore } from '../../store/workspaceStore';
import FloatingCopilot from '../chat/FloatingCopilot';


interface NavItem {
  label: string;
  icon: React.FC<{ size?: number; strokeWidth?: number }>;
  path: string;
}

const AppShell: React.FC = () => {
  const params = useParams<{ workspaceId?: string }>();
  const storedWorkspaceId = useWorkspaceStore((s) => s.currentWorkspaceId);
  const storedWorkspaceName = useWorkspaceStore((s) => s.currentWorkspaceName);
  const workspaceId = params.workspaceId ?? storedWorkspaceId;
  const navigate = useNavigate();
  const clearAuth = useAuthStore((s) => s.clearAuth);
  const user = useAuthStore((s) => s.user);

  const navItems: NavItem[] = [
    { label: 'Dashboard',         icon: LayoutDashboard, path: `/app/dashboard/${workspaceId}` },
    { label: 'Documents',         icon: FolderOpen,       path: `/app/workspace/${workspaceId}` },
    { label: 'Compliance Check',  icon: ShieldCheck,      path: `/app/compliance/${workspaceId}` },
    { label: 'DRHP Generator',    icon: FileText,         path: `/app/drhp/${workspaceId}` },
    { label: 'SEBI Advisor',      icon: MessageSquare,    path: `/app/copilot/${workspaceId}` },
    { label: 'Audit Trail',       icon: ScrollText,       path: `/app/audit-log/${workspaceId}` },
    { label: 'Export Reports',    icon: Download,         path: `/app/export/${workspaceId}` },
  ];

  const handleLogout = () => {
    clearAuth();
    localStorage.removeItem('ipo_copilot_token');
    navigate('/login');
  };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', overflow: 'hidden', background: 'var(--bg-page)' }}>

      {/* ── Sidebar ──────────────────────────────────────── */}
      <aside style={{
        width: '256px',
        minWidth: '256px',
        background: 'var(--bg-sidebar)',
        display: 'flex',
        flexDirection: 'column',
        borderRight: '1px solid rgba(255,255,255,0.06)',
        overflowY: 'auto',
      }}>

        {/* Logo */}
        <div style={{ padding: '1.5rem 1.25rem', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.625rem' }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '8px',
              background: '#1A56DB',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <FileText size={16} strokeWidth={2.5} color="white" />
            </div>
            <div>
              <div style={{ fontSize: '0.875rem', fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.01em' }}>
                IPO Copilot AI
              </div>
              <div style={{ fontSize: '0.6875rem', color: 'rgba(255,255,255,0.4)', marginTop: '1px' }}>
                SEBI TechSprint 2026
              </div>
            </div>
          </div>
        </div>

        {/* Workspace Badge */}
        {workspaceId && (
          <div style={{ padding: '0.875rem 1.25rem', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '0.6875rem', color: 'rgba(255,255,255,0.35)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, marginBottom: '0.25rem' }}>
              Active Workspace
            </div>
            <div style={{ fontSize: '0.8125rem', color: 'rgba(255,255,255,0.8)', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.375rem', overflow: 'hidden' }}>
              <FolderOpen size={12} color="rgba(255,255,255,0.5)" />
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {storedWorkspaceName ?? 'Workspace'}
              </span>
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav style={{ flex: 1, padding: '1rem 0.75rem', display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.5625rem 0.875rem',
                borderRadius: '8px',
                textDecoration: 'none',
                fontSize: '0.875rem',
                fontWeight: isActive ? 600 : 500,
                color: isActive ? '#FFFFFF' : 'rgba(255,255,255,0.55)',
                background: isActive ? 'rgba(26,86,219,0.35)' : 'transparent',
                transition: 'all 150ms ease',
              })}
            >
              {({ isActive }) => (
                <>
                  <item.icon size={17} strokeWidth={isActive ? 2.5 : 2} />
                  <span style={{ flex: 1 }}>{item.label}</span>
                  {isActive && <ChevronRight size={14} color="rgba(255,255,255,0.5)" />}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div style={{ padding: '1rem 0.75rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ padding: '0.625rem 0.875rem', marginBottom: '0.5rem' }}>
            <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'rgba(255,255,255,0.75)' }}>
              {user?.full_name ?? 'User'}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.35)', marginTop: '1px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user?.email ?? ''}
            </div>
          </div>
          <button
            onClick={handleLogout}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.625rem',
              width: '100%', padding: '0.5rem 0.875rem', borderRadius: '8px',
              background: 'transparent', border: '1px solid rgba(255,255,255,0.1)',
              color: 'rgba(255,255,255,0.5)', fontSize: '0.8125rem', fontWeight: 500,
              cursor: 'pointer', transition: 'all 150ms ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(239,68,68,0.12)';
              e.currentTarget.style.color = '#FCA5A5';
              e.currentTarget.style.borderColor = 'rgba(239,68,68,0.25)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = 'rgba(255,255,255,0.5)';
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
            }}
          >
            <LogOut size={15} />
            Sign Out
          </button>
        </div>
      </aside>

      {/* ── Main Content ──────────────────────────────────── */}
      <main style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, padding: '2rem 2.5rem', maxWidth: '1280px', width: '100%', margin: '0 auto', animationName: 'fade-in', animationDuration: '0.2s', animationFillMode: 'forwards' }}>
          <Outlet />
        </div>
      </main>

      {/* ── Persistent Floating SEBI Advisor ──────────────── */}
      <FloatingCopilot />
    </div>
  );
};

export default AppShell;

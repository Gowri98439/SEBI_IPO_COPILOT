import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Building2,
  FolderOpen,
  FileSearch,
  ShieldCheck,
  MessageSquareCode,
  FileEdit,
  ClipboardList,
  GitBranch,
  BarChart3,
  Download,
  ChevronDown,
  LogOut,
  Settings,
  Check,
} from 'lucide-react'
import { useState } from 'react'
import { useWorkspaceStore } from '@/store/workspaceStore'
import { useAuthStore } from '@/store/authStore'
import { useWorkspaces } from '@/api/workspaces'
import { getInitials } from '@/utils/formatters'

interface NavItem {
  icon: React.ElementType
  label: string
  to: string
}

interface NavGroup {
  phase: string
  items: NavItem[]
}

const getNavGroups = (workspaceId: string | null): NavGroup[] => [
  {
    phase: 'PREPARE',
    items: [
      { icon: Building2, label: 'Onboarding', to: '/app/onboarding' },
      { icon: FolderOpen, label: 'Workspace', to: workspaceId ? `/app/workspace/${workspaceId}` : '#' },
      { icon: FileSearch, label: 'Documents', to: workspaceId ? `/app/upload/${workspaceId}` : '#' },
    ],
  },
  {
    phase: 'VALIDATE',
    items: [
      { icon: ShieldCheck, label: 'AI Validation', to: workspaceId ? `/app/validation/${workspaceId}` : '#' },
      { icon: LayoutDashboard, label: 'Compliance', to: workspaceId ? `/app/compliance/${workspaceId}` : '#' },
      { icon: MessageSquareCode, label: 'Copilot', to: workspaceId ? `/app/copilot/${workspaceId}` : '#' },
      { icon: FileEdit, label: 'Draft Review', to: workspaceId ? `/app/draft/${workspaceId}` : '#' },
    ],
  },
  {
    phase: 'REVIEW',
    items: [
      { icon: ClipboardList, label: 'Human Review', to: workspaceId ? `/app/human-review/${workspaceId}` : '#' },
      { icon: GitBranch, label: 'Versions', to: workspaceId ? `/app/versions/${workspaceId}` : '#' },
      { icon: BarChart3, label: 'Dashboard', to: workspaceId ? `/app/dashboard/${workspaceId}` : '#' },
      { icon: Download, label: 'Export', to: workspaceId ? `/app/export/${workspaceId}` : '#' },
    ],
  },
]

export default function Sidebar() {
  const navigate = useNavigate()
  const [workspaceOpen, setWorkspaceOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)

  const { currentWorkspaceId, currentWorkspaceName, setCurrentWorkspace } = useWorkspaceStore()
  const { user, clearAuth } = useAuthStore()
  const { data: workspaces = [] } = useWorkspaces()

  const handleLogout = () => {
    clearAuth()
    localStorage.removeItem('ipo_copilot_token')
    navigate('/login')
  }

  return (
    <aside className="relative flex h-screen w-60 flex-shrink-0 flex-col bg-ipo-elevated border-r border-ipo-border">
      {/* ── Logo ──────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-ipo-ai text-white font-display font-bold text-sm">
          §
        </div>
        <div>
          <p className="font-display text-sm font-semibold text-ipo-text leading-tight">
            IPO Copilot
          </p>
          <p className="text-[10px] font-data font-medium uppercase tracking-widest text-ipo-text-secondary">
            SEBI · SME
          </p>
        </div>
      </div>

      {/* ── Navigation ────────────────────────────────────────────────── */}
      <nav className="no-scrollbar flex-1 overflow-y-auto px-3 pb-4">
        {getNavGroups(currentWorkspaceId).map((group) => (
          <div key={group.phase} className="mb-5">
            <p className="mb-2 px-3 text-[10px] font-data font-semibold uppercase tracking-widest text-ipo-text-secondary">
              {group.phase}
            </p>
            <ul className="space-y-0.5">
              {group.items.map((item) => (
                <li key={item.label}>
                  <NavLink
                    to={item.to}
                    className={({ isActive }) =>
                      `sidebar-item group ${isActive ? 'active' : ''}`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <item.icon
                          className={`h-4 w-4 flex-shrink-0 transition-colors ${
                            isActive ? 'text-ipo-ai' : 'text-ipo-text-secondary group-hover:text-ipo-text'
                          }`}
                        />
                        <span className="font-body text-sm">{item.label}</span>
                      </>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      {/* ── Workspace Selector ────────────────────────────────────────── */}
      <div className="border-t border-ipo-border px-3 py-3">
        <div className="relative">
          <button
            onClick={() => setWorkspaceOpen((o) => !o)}
            className="flex w-full items-center gap-2.5 rounded-md bg-ipo-overlay px-3 py-2.5 text-sm transition-colors hover:bg-ipo-border/50"
          >
            <FolderOpen className="h-3.5 w-3.5 text-ipo-text-secondary flex-shrink-0" />
            <span className="flex-1 truncate text-left text-ipo-text text-sm font-body">
              {currentWorkspaceName ?? 'Select Workspace'}
            </span>
            <ChevronDown
              className={`h-4 w-4 text-ipo-text-secondary transition-transform ${
                workspaceOpen ? 'rotate-180' : ''
              }`}
            />
          </button>

          {workspaceOpen && (
            <div className="absolute bottom-full mb-1 w-full rounded-md bg-ipo-overlay border border-ipo-border py-1 shadow-panel z-50">
              {workspaces.length === 0 ? (
                <p className="px-3 py-2 text-xs text-ipo-text-secondary font-body">No workspaces yet</p>
              ) : (
                workspaces.map((ws) => (
                  <button
                    key={ws.id}
                    onClick={() => {
                      setCurrentWorkspace(ws.id, ws.name)
                      setWorkspaceOpen(false)
                    }}
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm text-ipo-text font-body transition-colors hover:bg-ipo-border/50"
                  >
                    <span className="flex-1 truncate text-left">{ws.name}</span>
                    {currentWorkspaceId === ws.id && (
                      <Check className="h-3.5 w-3.5 text-ipo-ai" />
                    )}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* ── User Menu ─────────────────────────────────────────────────── */}
      <div className="border-t border-ipo-border px-3 py-3">
        <div className="relative">
          <button
            onClick={() => setUserMenuOpen((o) => !o)}
            className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors hover:bg-ipo-overlay"
          >
            <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-ipo-ai text-xs font-semibold text-white font-body">
              {user ? getInitials(user.full_name) : 'U'}
            </div>
            <div className="flex-1 min-w-0 text-left">
              <p className="truncate text-sm font-medium text-ipo-text font-body">
                {user?.full_name ?? 'User'}
              </p>
              <p className="truncate text-xs text-ipo-text-secondary font-body">{user?.email ?? ''}</p>
            </div>
            <ChevronDown
              className={`h-4 w-4 flex-shrink-0 text-ipo-text-secondary transition-transform ${
                userMenuOpen ? 'rotate-180' : ''
              }`}
            />
          </button>

          {userMenuOpen && (
            <div className="absolute bottom-full mb-1 w-full rounded-md bg-ipo-overlay border border-ipo-border py-1 shadow-panel z-50">
              <button
                onClick={() => { navigate('/settings'); setUserMenuOpen(false) }}
                className="flex w-full items-center gap-2.5 px-3 py-2 text-sm text-ipo-text font-body transition-colors hover:bg-ipo-border/50"
              >
                <Settings className="h-4 w-4" />
                Settings
              </button>
              <button
                onClick={handleLogout}
                className="flex w-full items-center gap-2.5 px-3 py-2 text-sm text-ipo-critical font-body transition-colors hover:bg-ipo-critical/10"
              >
                <LogOut className="h-4 w-4" />
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>
  )
}

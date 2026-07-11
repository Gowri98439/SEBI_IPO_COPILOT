import { Bell, Search } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { useDemoStore } from '@/store/demoStore'

const ROUTE_LABELS: Record<string, { title: string; breadcrumb: string[] }> = {
  '/onboarding': { title: 'Company Onboarding', breadcrumb: ['Prepare', 'Onboarding'] },
  '/workspace': { title: 'Workspace', breadcrumb: ['Prepare', 'Workspace'] },
  '/documents': { title: 'Document Management', breadcrumb: ['Prepare', 'Documents'] },
  '/upload': { title: 'Documents', breadcrumb: ['Prepare', 'Documents'] },
  '/validation': { title: 'AI Validation', breadcrumb: ['Validate', 'AI Validation'] },
  '/compliance': { title: 'Compliance Checks', breadcrumb: ['Validate', 'Compliance'] },
  '/copilot': { title: 'AI Copilot', breadcrumb: ['Validate', 'Copilot'] },
  '/draft': { title: 'Draft Review', breadcrumb: ['Validate', 'Draft Review'] },
  '/human-review': { title: 'Human Review', breadcrumb: ['Review', 'Human Review'] },
  '/versions': { title: 'Document Versions', breadcrumb: ['Review', 'Versions'] },
  '/dashboard': { title: 'Dashboard', breadcrumb: ['Review', 'Dashboard'] },
  '/export': { title: 'Export & Reports', breadcrumb: ['Review', 'Export'] },
  '/settings': { title: 'Settings', breadcrumb: ['Settings'] },
}

function matchRoute(pathname: string): { title: string; breadcrumb: string[] } {
  for (const [key, value] of Object.entries(ROUTE_LABELS)) {
    if (pathname.includes(key)) return value
  }
  return { title: 'IPO Copilot', breadcrumb: ['Home'] }
}

export default function Header() {
  const location = useLocation()
  const routeInfo = matchRoute(location.pathname)
  const { isDemoMode, toggleDemo } = useDemoStore()

  return (
    <header className="flex h-14 flex-shrink-0 items-center justify-between border-b border-ipo-border px-6 bg-ipo-elevated">
      {/* Left: title + breadcrumb */}
      <div>
        <div className="mb-0.5 flex items-center gap-1.5 text-xs font-data text-ipo-text-secondary">
          {routeInfo.breadcrumb.map((crumb, idx) => (
            <span key={crumb} className="flex items-center gap-1.5">
              {idx > 0 && <span className="text-ipo-border">/</span>}
              <span className={idx === routeInfo.breadcrumb.length - 1 ? 'text-ipo-text-secondary' : 'text-ipo-text-secondary/60'}>
                {crumb}
              </span>
            </span>
          ))}
        </div>
        <h1 className="font-display text-base font-semibold text-ipo-text">{routeInfo.title}</h1>
      </div>

      {/* Right: demo toggle + search + notifications */}
      <div className="flex items-center gap-3">
        {/* Demo Mode toggle */}
        <button
          onClick={toggleDemo}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-data font-medium transition-colors border ${
            isDemoMode
              ? 'bg-ipo-attention/15 text-ipo-attention border-ipo-attention/30'
              : 'bg-ipo-overlay text-ipo-text-secondary border-ipo-border hover:text-ipo-text'
          }`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${isDemoMode ? 'bg-ipo-attention' : 'bg-ipo-text-secondary/40'}`} />
          {isDemoMode ? 'Demo Mode' : 'Demo'}
        </button>

        {/* Search */}
        <div className="relative hidden sm:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ipo-text-secondary" />
          <input
            type="text"
            placeholder="Search…"
            className="input-base w-48 pl-9 py-1.5 text-xs"
          />
        </div>

        {/* Notifications */}
        <button
          className="relative flex h-8 w-8 items-center justify-center rounded-md bg-ipo-overlay text-ipo-text-secondary transition-colors hover:bg-ipo-border/50 hover:text-ipo-text border border-ipo-border"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-ipo-critical" />
        </button>
      </div>
    </header>
  )
}

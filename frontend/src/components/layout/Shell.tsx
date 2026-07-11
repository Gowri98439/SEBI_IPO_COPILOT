import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'
import EvidenceRail from '@/components/ui/EvidenceRail'
import { EvidenceRailProvider } from '@/hooks/useEvidenceRail'

export default function Shell() {
  return (
    <EvidenceRailProvider>
      <div className="flex h-screen w-full overflow-hidden bg-ipo-base">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header />
          <div className="flex flex-1 overflow-hidden">
            <main className="flex-1 overflow-y-auto">
              <Outlet />
            </main>
            <EvidenceRail />
          </div>
        </div>
      </div>
    </EvidenceRailProvider>
  )
}

import { AppRouter } from './router'
import { ChatProvider } from './context/ChatContext'
import { Toaster } from 'react-hot-toast'

export default function App() {
  return (
    <ChatProvider>
      <AppRouter />
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: 'var(--bg-card, #FFFFFF)',
            color: 'var(--text-primary, #0F172A)',
            border: '1px solid var(--border, #E2E8F0)',
            borderRadius: '8px',
            fontSize: '0.875rem',
            fontFamily: 'Inter, system-ui, sans-serif',
            boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
          },
        }}
      />
    </ChatProvider>
  )
}

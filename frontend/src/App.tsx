import { AppRouter } from './router'
import { ChatProvider } from './context/ChatContext'

export default function App() {
  return (
    <ChatProvider>
      <AppRouter />
    </ChatProvider>
  )
}

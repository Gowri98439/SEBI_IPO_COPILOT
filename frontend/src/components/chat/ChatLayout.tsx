import React, { useState, useEffect, useCallback } from 'react';
import { Sidebar } from './Sidebar';

interface ChatLayoutProps {
  sidebarContent: React.ReactNode;
  mainContent: React.ReactNode;
}

export const ChatLayout: React.FC<ChatLayoutProps> = ({ sidebarContent, mainContent }) => {
  // Initialize from localStorage or default to true on desktop, false on mobile
  const [isOpen, setIsOpen] = useState<boolean>(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('copilot_sidebar_open');
      if (stored !== null) {
        return stored === 'true';
      }
      return window.innerWidth >= 768;
    }
    return true;
  });

  const toggleSidebar = useCallback(() => {
    setIsOpen(prev => {
      const newState = !prev;
      localStorage.setItem('copilot_sidebar_open', String(newState));
      return newState;
    });
  }, []);

  const closeSidebar = useCallback(() => {
    setIsOpen(false);
    localStorage.setItem('copilot_sidebar_open', 'false');
  }, []);

  // Keyboard shortcut Ctrl+B or Cmd+B to toggle sidebar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault();
        toggleSidebar();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleSidebar]);

  return (
    <div className="flex h-full w-full overflow-hidden bg-white text-gray-900" style={{ background: 'var(--bg-page)' }}>
      <Sidebar isOpen={isOpen} onClose={closeSidebar}>
        {sidebarContent}
      </Sidebar>
      <main className="flex-1 flex flex-col h-full min-w-0 transition-all duration-300 relative">
        {/* Pass down toggleSidebar to child if needed, or we can use Context. For now, children can access it via props if cloned, but it's cleaner to handle via context or pass it up. 
            Since we don't have context setup for layout, we will export a hook or let mainContent be a render prop. 
            For simplicity, let's inject it into a context. */}
        <ChatLayoutContext.Provider value={{ isOpen, toggleSidebar }}>
          {mainContent}
        </ChatLayoutContext.Provider>
      </main>
    </div>
  );
};

// Simple context to access sidebar state from children (e.g. ChatHeader)
export const ChatLayoutContext = React.createContext<{ isOpen: boolean; toggleSidebar: () => void }>({
  isOpen: true,
  toggleSidebar: () => {},
});

export const useChatLayout = () => React.useContext(ChatLayoutContext);

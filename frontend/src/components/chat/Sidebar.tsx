import React, { useEffect } from 'react';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose, children }) => {
  // Close on Escape key when mobile overlay is active
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && window.innerWidth < 768 && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  return (
    <>
      {/* Mobile Backdrop Overlay */}
      <div
        className={`fixed inset-0 bg-black/60 z-40 transition-opacity duration-300 md:hidden ${
          isOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sidebar Container */}
      <div
        className={`fixed md:relative z-50 h-full bg-[#1e1e1e] border-r border-[#333] transition-all duration-300 ease-in-out flex flex-col overflow-hidden shadow-2xl md:shadow-none
          ${isOpen ? 'translate-x-0 w-[320px]' : '-translate-x-full md:translate-x-0 w-0'}
        `}
        style={{ background: 'var(--bg-card)', borderColor: 'var(--border)' }}
      >
        {/* Content wrapper with fixed width to prevent wrapping during transition */}
        <div className="w-[320px] h-full flex flex-col">
          {children}
        </div>
      </div>
    </>
  );
};

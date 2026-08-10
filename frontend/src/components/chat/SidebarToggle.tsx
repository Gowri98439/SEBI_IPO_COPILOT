import React from 'react';
import { Menu, PanelLeftClose, PanelLeftOpen } from 'lucide-react';

interface SidebarToggleProps {
  isOpen: boolean;
  toggle: () => void;
  className?: string;
}

export const SidebarToggle: React.FC<SidebarToggleProps> = ({ isOpen, toggle, className = '' }) => {
  return (
    <button
      onClick={toggle}
      aria-label={isOpen ? "Close sidebar" : "Open sidebar"}
      title={isOpen ? "Close sidebar (Ctrl+B)" : "Open sidebar (Ctrl+B)"}
      className={`p-2 rounded-md hover:bg-white/10 transition-colors flex items-center justify-center ${className}`}
      style={{
        background: 'transparent',
        border: 'none',
        cursor: 'pointer',
        color: 'var(--text-secondary)'
      }}
    >
      {isOpen ? <PanelLeftClose size={20} /> : <PanelLeftOpen size={20} />}
    </button>
  );
};

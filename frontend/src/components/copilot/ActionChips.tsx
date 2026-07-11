import React from 'react';

export interface ActionChip {
  id: string;
  emoji: string;
  label: string;
  prompt: string;
}

const DEFAULT_CHIPS: ActionChip[] = [
  {
    id: 'draft',
    emoji: '📋',
    label: 'Draft Section',
    prompt: 'Draft the Risk Factors section for our DRHP based on the uploaded documents.',
  },
  {
    id: 'explain',
    emoji: '⚖️',
    label: 'Explain Rule',
    prompt: 'Explain SEBI ICDR Regulation 6 and how it applies to our IPO filing.',
  },
  {
    id: 'status',
    emoji: '✅',
    label: 'Check Status',
    prompt: 'What is the current compliance status of our IPO preparation? Summarize outstanding issues.',
  },
  {
    id: 'review',
    emoji: '📝',
    label: 'Review Content',
    prompt: 'Review the Business Description section I will paste below for SEBI compliance issues.',
  },
  {
    id: 'checklist',
    emoji: '🗂️',
    label: 'Filing Checklist',
    prompt: 'Generate a complete SEBI IPO filing checklist and indicate which items are complete.',
  },
  {
    id: 'financials',
    emoji: '💰',
    label: 'Financial Check',
    prompt: 'Analyze our uploaded financial statements for SEBI-required disclosures and flag any gaps.',
  },
];

interface ActionChipsProps {
  chips?: ActionChip[];
  onSelect: (prompt: string) => void;
}

const ActionChips: React.FC<ActionChipsProps> = ({ chips = DEFAULT_CHIPS, onSelect }) => {
  return (
    <div className="flex flex-wrap gap-2 font-body">
      {chips.map((chip) => (
        <button
          key={chip.id}
          onClick={() => onSelect(chip.prompt)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-ipo-elevated border border-ipo-border text-ipo-text-secondary hover:text-ipo-text hover:bg-ipo-overlay hover:border-ipo-text-secondary transition-colors text-[10px] font-bold uppercase tracking-wider font-data shadow-sm"
        >
          <span>{chip.emoji}</span>
          <span>{chip.label}</span>
        </button>
      ))}
    </div>
  );
};

export default ActionChips;

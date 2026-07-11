import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  change?: number; // percentage, positive=up negative=down
  changeLabel?: string;
  iconColor?: string;
  gradient?: string; // Kept for API compatibility, but mapped to solid bg
}

const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  icon: Icon,
  change,
  changeLabel,
  iconColor = 'text-ipo-ai',
  gradient, // ignoring gradient, using bg based on iconColor
}) => {
  const isPositive = change !== undefined && change > 0;
  const isNegative = change !== undefined && change < 0;
  const isNeutral = change !== undefined && change === 0;
  
  // Map iconColor to a suitable background
  const bgClass = iconColor.includes('emerald') || iconColor.includes('verified') 
    ? 'bg-ipo-verified/10'
    : iconColor.includes('red') || iconColor.includes('critical')
    ? 'bg-ipo-critical/10'
    : iconColor.includes('amber') || iconColor.includes('attention')
    ? 'bg-ipo-attention/10'
    : 'bg-ipo-ai/10';

  return (
    <div className="bg-ipo-elevated border border-ipo-border rounded-md p-5 shadow-sm transition-colors hover:border-ipo-text-secondary">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-ipo-text-secondary text-[10px] font-bold uppercase tracking-wider mb-2 font-data">{label}</p>
          <p className="text-3xl font-bold font-display text-ipo-text tracking-tight">{value}</p>

          {change !== undefined && (
            <div className="flex items-center gap-1.5 mt-2">
              {isPositive && <TrendingUp className="w-3.5 h-3.5 text-ipo-verified" />}
              {isNegative && <TrendingDown className="w-3.5 h-3.5 text-ipo-critical" />}
              {isNeutral && <Minus className="w-3.5 h-3.5 text-ipo-text-secondary" />}
              <span
                className={`text-[10px] font-bold uppercase tracking-wider font-data ${
                  isPositive ? 'text-ipo-verified' : isNegative ? 'text-ipo-critical' : 'text-ipo-text-secondary'
                }`}
              >
                {isPositive ? '+' : ''}
                {change}%
              </span>
              {changeLabel && (
                <span className="text-[10px] font-bold uppercase tracking-wider font-data text-ipo-text-secondary/70">{changeLabel}</span>
              )}
            </div>
          )}
        </div>

        <div
          className={`w-12 h-12 rounded-lg ${bgClass} flex items-center justify-center flex-shrink-0 ml-3`}
        >
          <Icon className={`w-6 h-6 ${iconColor}`} />
        </div>
      </div>
    </div>
  );
};

export default StatCard;

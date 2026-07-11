import React from 'react';
import {
  RadialBarChart,
  RadialBar,
  ResponsiveContainer,
  PolarAngleAxis,
} from 'recharts';

interface ReadinessGaugeProps {
  score: number; // 0 – 100
  size?: number;
}

// Enterprise colors
const getColor = (score: number): string => {
  if (score >= 75) return '#059669'; // ipo-verified (emerald-600)
  if (score >= 50) return '#d97706'; // ipo-attention (amber-600)
  if (score >= 25) return '#ea580c'; // orange
  return '#dc2626'; // ipo-critical (red-600)
};

const getLabel = (score: number): string => {
  if (score >= 80) return 'Ready to File';
  if (score >= 60) return 'In Progress';
  if (score >= 30) return 'Early Stage';
  return 'Not Ready';
};

const ReadinessGauge: React.FC<ReadinessGaugeProps> = ({ score, size = 240 }) => {
  const clampedScore = Math.min(100, Math.max(0, score));
  const color = getColor(clampedScore);
  const label = getLabel(clampedScore);

  const data = [{ name: 'Score', value: clampedScore, fill: color }];

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            innerRadius="70%"
            outerRadius="100%"
            startAngle={220}
            endAngle={-40}
            data={data}
            barSize={18}
          >
            <PolarAngleAxis
              type="number"
              domain={[0, 100]}
              angleAxisId={0}
              tick={false}
            />
            {/* Background track */}
            <RadialBar
              background={{ fill: 'rgba(148, 163, 184, 0.1)' }} // ipo-border equivalent
              dataKey="value"
              cornerRadius={0}
              angleAxisId={0}
            />
          </RadialBarChart>
        </ResponsiveContainer>

        {/* Center label */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-4xl font-bold font-display"
            style={{ color }}
          >
            {clampedScore}
          </span>
          <span className="text-[10px] font-bold uppercase tracking-wider font-data text-ipo-text-secondary mt-1">out of 100</span>
        </div>
      </div>

      {/* Status badge */}
      <div
        className="mt-3 px-4 py-1.5 rounded-sm text-[10px] font-bold uppercase tracking-wider font-data border"
        style={{
          color,
          borderColor: `${color}40`,
          backgroundColor: `${color}10`,
        }}
      >
        {label}
      </div>
    </div>
  );
};

export default ReadinessGauge;

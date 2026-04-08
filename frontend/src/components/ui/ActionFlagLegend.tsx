import { useState } from 'react';
import { ACTION_FLAG_COLORS, ACTION_FLAG_LABELS } from '../../lib/constants';

const flags = Object.keys(ACTION_FLAG_COLORS);

const FLAG_DESCRIPTIONS: Record<string, string> = {
  solar_now:
    'Solar is cost-competitive today. Grid upgrades are planned and GEAS allocation is sufficient.',
  invest_resilience:
    'Solar is within ~20% of grid parity. Investing now builds resilience against future grid cost increases.',
  grid_first:
    'Solar economics work, but no grid upgrade is planned before 2030 — solar cannot connect until the grid catches up.',
  firming_needed:
    'Solar economics work, but high reliability requirements mean firming (battery/backup) is needed, adding cost.',
  plan_late:
    'Over 60% of planned solar additions in this grid region slip past 2030. RUPTL pipeline needs acceleration.',
  not_competitive: 'Solar LCOE exceeds grid cost by too wide a margin under current assumptions.',
};

export default function ActionFlagLegend() {
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <div className="flex items-center gap-4 relative">
      {flags.map((flag) => (
        <div
          key={flag}
          className="flex items-center gap-1.5 cursor-default"
          onMouseEnter={() => setHovered(flag)}
          onMouseLeave={() => setHovered(null)}
        >
          <span
            className="inline-block w-2 h-2 rounded-full"
            style={{ backgroundColor: ACTION_FLAG_COLORS[flag] }}
          />
          <span className="text-xs text-zinc-400">{ACTION_FLAG_LABELS[flag]}</span>
        </div>
      ))}

      {hovered && FLAG_DESCRIPTIONS[hovered] && (
        <div
          className="absolute top-full left-0 mt-2 px-3 py-2 rounded-md text-[11px] text-zinc-200 leading-relaxed max-w-xs z-50 pointer-events-none"
          style={{
            background: 'var(--glass-heavy)',
            backdropFilter: 'var(--blur-heavy)',
            WebkitBackdropFilter: 'var(--blur-heavy)',
            border: '1px solid var(--glass-border-bright)',
            boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 4px 16px rgba(0, 0, 0, 0.4)',
          }}
        >
          <span className="font-medium" style={{ color: ACTION_FLAG_COLORS[hovered] }}>
            {ACTION_FLAG_LABELS[hovered]}
          </span>
          <span className="text-zinc-400"> — </span>
          {FLAG_DESCRIPTIONS[hovered]}
        </div>
      )}
    </div>
  );
}

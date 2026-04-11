import { useEffect, useRef, useState } from 'react';
import { ACTION_FLAG_COLORS, ACTION_FLAG_LABELS } from '../../lib/constants';
import type { ActionFlag } from '../../lib/types';

const flags = Object.keys(ACTION_FLAG_COLORS) as ActionFlag[];

const FLAG_DESCRIPTIONS: Record<string, string> = {
  solar_now:
    'Solar is cost-competitive today. Grid upgrades are planned and GEAS allocation is sufficient.',
  invest_transmission:
    'Solar can reach a substation, but the KEK is far from grid infrastructure. Build transmission to KEK.',
  invest_substation:
    'KEK is grid-connected, but the best solar site is far from any substation. Build a substation near solar.',
  invest_resilience:
    'Solar is within ~20% of grid parity. Investing now builds resilience against future grid cost increases.',
  grid_first:
    'No substation near the KEK or the solar site. New grid infrastructure (substation + transmission) must be built before solar can connect.',
  invest_battery:
    'Solar economics work, but high reliability requirements mean battery storage is needed, adding cost.',
  plan_late:
    'Over 60% of planned solar additions in this grid region slip past 2030. RUPTL pipeline needs acceleration.',
  not_competitive:
    'Solar LCOE exceeds grid cost, or solar resource quality (PVOUT) is below the minimum threshold.',
};

export default function ActionFlagLegend() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 px-2 py-1 rounded text-xs text-zinc-400 hover:text-white transition-colors cursor-pointer"
      >
        {/* Show compact dot strip as a preview */}
        <span className="flex items-center gap-0.5">
          {flags.slice(0, 4).map((flag) => (
            <span
              key={flag}
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ backgroundColor: ACTION_FLAG_COLORS[flag] }}
            />
          ))}
        </span>
        Legend
        <svg
          className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div
          className="absolute top-full left-0 mt-2 p-3 rounded-lg z-50 min-w-[260px]"
          style={{
            background: 'var(--glass-heavy)',
            backdropFilter: 'var(--blur-heavy)',
            WebkitBackdropFilter: 'var(--blur-heavy)',
            border: '1px solid var(--glass-border-bright)',
            boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 8px 32px rgba(0, 0, 0, 0.5)',
          }}
        >
          <p className="text-[10px] uppercase tracking-wider text-zinc-500 mb-2 font-medium">
            Action Flags
          </p>
          <div className="grid gap-1.5">
            {flags.map((flag) => (
              <div key={flag} className="group flex items-start gap-2">
                <span
                  className="inline-block w-2 h-2 rounded-full mt-[5px] shrink-0"
                  style={{ backgroundColor: ACTION_FLAG_COLORS[flag] }}
                />
                <div>
                  <span className="text-xs text-zinc-200">{ACTION_FLAG_LABELS[flag]}</span>
                  <p className="text-[10px] text-zinc-500 leading-snug hidden group-hover:block">
                    {FLAG_DESCRIPTIONS[flag]}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

import { useEffect, useRef, useState } from 'react';
import { ACTION_FLAG_HIERARCHY_BY_MODE, getActionSectionTitle } from '../../lib/actionFlags';
import { ACTION_FLAG_COLORS, ACTION_FLAG_LABELS } from '../../lib/constants';
import { useDashboardStore } from '../../store/dashboard';

const FLAG_DESCRIPTIONS: Record<string, string> = {
  solar_now:
    'Solar is cost-competitive today. Grid upgrades are planned and GEAS allocation is sufficient.',
  wind_now: 'Wind is cost-competitive today. Deploy wind generation.',
  hybrid_now:
    'Hybrid solar+wind all-in cost beats grid. Wind reduces nighttime storage requirements.',
  invest_resilience:
    'RE is within ~20% of grid parity. Investing now builds resilience against future grid cost increases.',
  invest_battery:
    'RE economics work, but high reliability requirements mean battery storage is needed, adding cost.',
  invest_transmission:
    'RE can reach a substation, but the KEK is far from grid infrastructure. Build transmission to KEK.',
  invest_substation:
    'KEK is grid-connected, but the best RE site is far from any substation. Build a substation near the generation site.',
  grid_first:
    'No substation near the KEK or the RE site. New grid infrastructure must be built before RE can connect.',
  plan_late:
    'Over 60% of planned RE additions in this grid region slip past 2030. RUPTL pipeline needs acceleration.',
  not_competitive:
    'RE LCOE exceeds grid cost under current assumptions.',
  no_solar_resource:
    'All land within the search radius is protected forest, peatland, or unbuildable. No area available for solar.',
  no_wind_resource:
    'No viable wind resource within 50 km. Wind speeds below cut-in threshold or all land is unbuildable.',
  no_re_resource:
    'No viable renewable resource (solar or wind) within 50 km.',
};

export default function ActionFlagLegend() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const energyMode = useDashboardStore((s) => s.energyMode);
  const hierarchy = ACTION_FLAG_HIERARCHY_BY_MODE[energyMode];

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
        className="flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-colors cursor-pointer"
        style={{ color: 'var(--text-secondary)' }}
        onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
        onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
      >
        {/* Show compact dot strip as a preview */}
        <span className="flex items-center gap-0.5">
          {hierarchy.slice(0, 4).map((flag) => (
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
            boxShadow: 'var(--popup-shadow)',
          }}
        >
          <p
            className="text-[10px] uppercase tracking-wider mb-2 font-medium"
            style={{ color: 'var(--text-muted)' }}
          >
            {getActionSectionTitle(energyMode)} Ladder
          </p>
          <div>
            {hierarchy.map((flag, i) => {
              const color = ACTION_FLAG_COLORS[flag];
              const isLast = i === hierarchy.length - 1;
              return (
                <div key={flag} className="group flex items-stretch gap-0">
                  {/* Vertical track */}
                  <div className="flex flex-col items-center" style={{ width: 16 }}>
                    <div
                      className="rounded-full shrink-0 mt-[7px]"
                      style={{ width: 8, height: 8, background: color }}
                    />
                    {!isLast && (
                      <div
                        className="flex-1"
                        style={{
                          width: 2,
                          background: 'var(--border-subtle)',
                          minHeight: 8,
                        }}
                      />
                    )}
                  </div>
                  {/* Label + hover description */}
                  <div className="pl-1.5 pb-1.5">
                    <span className="text-xs" style={{ color: 'var(--text-value)' }}>
                      {ACTION_FLAG_LABELS[flag]}
                    </span>
                    <p
                      className="text-[10px] leading-snug hidden group-hover:block mt-0.5"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {FLAG_DESCRIPTIONS[flag]}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

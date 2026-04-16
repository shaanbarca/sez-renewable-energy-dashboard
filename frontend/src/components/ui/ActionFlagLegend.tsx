import { useEffect, useRef, useState } from 'react';
import { getEconomicTierDescription, getEconomicTierLabel } from '../../lib/actionFlags';
import { ECONOMIC_TIER_COLORS, ECONOMIC_TIER_HIERARCHY } from '../../lib/constants';
import { useDashboardStore } from '../../store/dashboard';

const INFRA_RING_KEY = [
  { label: 'Grid Ready', color: '#ffffff', description: 'Within boundary or nearby substation' },
  {
    label: 'Needs Grid Investment',
    color: '#42A5F5',
    description: 'Transmission line or substation upgrade needed',
  },
  {
    label: 'Major Grid Work',
    color: '#1565C0',
    description: 'No substation near KEK or RE site',
  },
];

export default function ActionFlagLegend() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const energyMode = useDashboardStore((s) => s.energyMode);

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
          {ECONOMIC_TIER_HIERARCHY.map((tier) => (
            <span
              key={tier}
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ backgroundColor: ECONOMIC_TIER_COLORS[tier] }}
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
          {/* Economic tier section */}
          <p
            className="text-[10px] uppercase tracking-wider mb-2 font-medium"
            style={{ color: 'var(--text-muted)' }}
          >
            Fill = RE Viability
          </p>
          <div>
            {ECONOMIC_TIER_HIERARCHY.map((tier, i) => {
              const color = ECONOMIC_TIER_COLORS[tier];
              const isLast = i === ECONOMIC_TIER_HIERARCHY.length - 1;
              return (
                <div key={tier} className="group flex items-stretch gap-0">
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
                  <div className="pl-1.5 pb-1.5">
                    <span className="text-xs" style={{ color: 'var(--text-value)' }}>
                      {getEconomicTierLabel(tier, energyMode)}
                    </span>
                    <p
                      className="text-[10px] leading-snug hidden group-hover:block mt-0.5"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {getEconomicTierDescription(tier, energyMode)}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Infrastructure ring section */}
          <div className="mt-2.5 pt-2.5" style={{ borderTop: '1px solid var(--border-subtle)' }}>
            <p
              className="text-[10px] uppercase tracking-wider mb-2 font-medium"
              style={{ color: 'var(--text-muted)' }}
            >
              Ring = Infrastructure
            </p>
            <div className="flex flex-col gap-1.5">
              {INFRA_RING_KEY.map((item) => (
                <div key={item.label} className="group flex items-center gap-2">
                  <svg width="14" height="14" viewBox="0 0 14 14" className="shrink-0">
                    <circle cx="7" cy="7" r="5" fill="#666" stroke={item.color} strokeWidth="2" />
                  </svg>
                  <div>
                    <span className="text-xs" style={{ color: 'var(--text-value)' }}>
                      {item.label}
                    </span>
                    <p
                      className="text-[10px] leading-snug hidden group-hover:block"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {item.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* CBAM exposure section */}
          <div className="mt-2.5 pt-2.5" style={{ borderTop: '1px solid var(--border-subtle)' }}>
            <p
              className="text-[10px] uppercase tracking-wider mb-2 font-medium"
              style={{ color: 'var(--text-muted)' }}
            >
              Outer Ring = CBAM Exposure
            </p>
            <div className="group flex items-center gap-2">
              <svg width="14" height="14" viewBox="0 0 14 14" className="shrink-0">
                <circle cx="7" cy="7" r="5" fill="none" stroke="#FF6F00" strokeWidth="1.5" />
              </svg>
              <div>
                <span className="text-xs" style={{ color: '#FF6F00' }}>
                  CBAM Exposed
                </span>
                <p
                  className="text-[10px] leading-snug hidden group-hover:block"
                  style={{ color: 'var(--text-muted)' }}
                >
                  EU Carbon Border Adjustment Mechanism applies to exports from this KEK
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

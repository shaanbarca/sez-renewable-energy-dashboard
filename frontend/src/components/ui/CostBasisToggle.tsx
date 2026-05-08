import * as ToggleGroup from '@radix-ui/react-toggle-group';
import * as Tooltip from '@radix-ui/react-tooltip';
import { COST_BASIS_DESCRIPTIONS, COST_BASIS_LABELS, isBasisSupported } from '../../lib/costBasis';
import type { CostBasis } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

const options: CostBasis[] = ['raw', 'firmed', 'delivered'];

/**
 * Three-way cost-view toggle — "Solar LCOE" / "Solar 24/7" / "Supply Blend" —
 * that repoints the action grid (flag, economic tier, gap, carbon breakeven)
 * at a different column in the cost-stack. TAXONOMY §7.3 resolver matrix
 * decides which value maps to which column for each (energyMode × costBasis);
 * unsupported combos (e.g. wind + Supply Blend) are rendered disabled and show
 * "Not modelled" in the tooltip.
 */
export default function CostBasisToggle() {
  const energyMode = useDashboardStore((s) => s.energyMode);
  const costBasis = useDashboardStore((s) => s.costBasis);
  const setCostBasis = useDashboardStore((s) => s.setCostBasis);

  return (
    <Tooltip.Provider delayDuration={200}>
      {/* Toggle group + `?` info button live in the SAME bordered shell so
          the `?` reads as part of the control, not a floating sibling. */}
      <div
        className="flex items-stretch rounded-lg overflow-hidden border"
        style={{ borderColor: 'var(--glass-border-bright)' }}
      >
      <ToggleGroup.Root
        type="single"
        value={costBasis}
        onValueChange={(value) => {
          if (value && isBasisSupported(energyMode, value as CostBasis)) {
            setCostBasis(value as CostBasis);
          }
        }}
        className="flex"
        aria-label="Cost view"
      >
        {options.map((opt) => {
          const supported = isBasisSupported(energyMode, opt);
          const active = costBasis === opt;
          const label = COST_BASIS_LABELS[opt];
          const { title, body } = COST_BASIS_DESCRIPTIONS[opt];
          return (
            <Tooltip.Root key={opt}>
              <Tooltip.Trigger asChild>
                <ToggleGroup.Item
                  value={opt}
                  disabled={!supported}
                  className="px-2.5 py-1.5 text-xs font-medium transition-colors whitespace-nowrap"
                  style={{
                    backgroundColor: active ? 'var(--toggle-on-bg)' : 'transparent',
                    color: !supported
                      ? 'var(--text-tertiary, rgba(255,255,255,0.3))'
                      : active
                        ? 'var(--toggle-on-text)'
                        : 'var(--toggle-off-text)',
                    cursor: supported ? 'pointer' : 'not-allowed',
                    opacity: supported ? 1 : 0.45,
                  }}
                >
                  {label}
                </ToggleGroup.Item>
              </Tooltip.Trigger>
              <Tooltip.Portal>
                <Tooltip.Content
                  side="bottom"
                  sideOffset={6}
                  className="max-w-[280px] px-3 py-2 rounded text-xs leading-relaxed z-50"
                  style={{
                    background: 'var(--glass-heavy)',
                    backdropFilter: 'var(--blur-heavy)',
                    WebkitBackdropFilter: 'var(--blur-heavy)',
                    border: '1px solid var(--glass-border-bright)',
                    boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06)',
                    color: 'var(--text-primary)',
                  }}
                >
                  <div className="font-medium mb-1">{title}</div>
                  <div style={{ color: 'var(--text-secondary)' }}>{body}</div>
                  {!supported && (
                    <div className="mt-1.5 italic" style={{ color: 'var(--text-tertiary)' }}>
                      Not modelled for {energyMode}.
                    </div>
                  )}
                </Tooltip.Content>
              </Tooltip.Portal>
            </Tooltip.Root>
          );
        })}
      </ToggleGroup.Root>
        <Tooltip.Root>
          <Tooltip.Trigger asChild>
            <button
              type="button"
              aria-label="What is Cost basis?"
              className="cursor-help transition-colors flex items-center px-2"
              style={{
                color: 'var(--text-muted)',
                borderLeft: '1px solid var(--glass-border)',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
            >
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
                <text
                  x="8"
                  y="12"
                  textAnchor="middle"
                  fill="currentColor"
                  fontSize="10"
                  fontWeight="600"
                >
                  ?
                </text>
              </svg>
            </button>
          </Tooltip.Trigger>
          <Tooltip.Portal>
            <Tooltip.Content
              side="bottom"
              sideOffset={8}
              className="max-w-[300px] px-3 py-2 rounded text-xs leading-relaxed z-50"
              style={{
                background: 'var(--glass-heavy)',
                backdropFilter: 'var(--blur-heavy)',
                WebkitBackdropFilter: 'var(--blur-heavy)',
                border: '1px solid var(--glass-border-bright)',
                boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06), 0 4px 16px rgba(0,0,0,0.4)',
                color: 'var(--text-primary)',
              }}
            >
              <div className="font-medium mb-1">Cost basis (IEA terminology)</div>
              <div style={{ color: 'var(--text-secondary)' }}>
                Picks which slice of the cost stack feeds the action grid:
                <ul className="mt-1.5 space-y-0.5 list-none">
                  <li>
                    <span style={{ color: 'var(--text-primary)' }}>LCOE</span> —
                    bare generation cost.
                  </li>
                  <li>
                    <span style={{ color: 'var(--text-primary)' }}>24/7 LCOE</span>{' '}
                    — generation + BESS firming (IEA: Full System LCOE).
                  </li>
                  <li>
                    <span style={{ color: 'var(--text-primary)' }}>Supply Blend</span>{' '}
                    — cascade of on-site, remote, and grid backfill (delivered cost).
                  </li>
                </ul>
              </div>
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>
      </div>
    </Tooltip.Provider>
  );
}

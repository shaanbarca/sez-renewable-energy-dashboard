import { useMemo, useState } from 'react';
import { COST_BASIS_LABELS, isBasisSupported } from '../../../lib/costBasis';
import { computeFlipDiff } from '../../../lib/flipDiff';
import type { CostBasis } from '../../../lib/types';
import { useDashboardStore } from '../../../store/dashboard';
import FlipControls from './FlipControls';
import FlipDiffTable from './FlipDiffTable';
import FlipSummary from './FlipSummary';

const BASIS_OPTIONS: CostBasis[] = ['raw', 'firmed', 'delivered'];

function BasisToggle({
  label,
  value,
  onChange,
  allowOff = false,
  disabledBasis,
}: {
  label: string;
  value: CostBasis | null;
  onChange: (b: CostBasis | null) => void;
  allowOff?: boolean;
  disabledBasis?: CostBasis | null;
}) {
  const energyMode = useDashboardStore((s) => s.energyMode);

  return (
    <div className="flex items-center gap-2">
      <span
        className="text-[10px] uppercase tracking-wider whitespace-nowrap"
        style={{ color: 'var(--text-muted)' }}
      >
        {label}
      </span>
      <div
        className="flex rounded overflow-hidden border"
        style={{ borderColor: 'var(--glass-border-bright)' }}
        role="group"
        aria-label={label}
      >
        {allowOff && (
          <button
            type="button"
            onClick={() => onChange(null)}
            className="px-2 py-1 text-[10px] font-medium transition-colors whitespace-nowrap"
            style={{
              backgroundColor: value === null ? 'var(--toggle-on-bg)' : 'transparent',
              color: value === null ? 'var(--toggle-on-text)' : 'var(--toggle-off-text)',
            }}
          >
            Off
          </button>
        )}
        {BASIS_OPTIONS.map((opt) => {
          const supported = isBasisSupported(energyMode, opt);
          const isDupe = disabledBasis === opt;
          const enabled = supported && !isDupe;
          const active = value === opt;
          return (
            <button
              key={opt}
              type="button"
              disabled={!enabled}
              onClick={() => enabled && onChange(opt)}
              className="px-2 py-1 text-[10px] font-medium transition-colors whitespace-nowrap"
              style={{
                backgroundColor: active ? 'var(--toggle-on-bg)' : 'transparent',
                color: !enabled
                  ? 'var(--text-tertiary, rgba(255,255,255,0.3))'
                  : active
                    ? 'var(--toggle-on-text)'
                    : 'var(--toggle-off-text)',
                cursor: enabled ? 'pointer' : 'not-allowed',
                opacity: enabled ? 1 : 0.45,
              }}
              title={
                !supported
                  ? `Not modelled for ${energyMode}`
                  : isDupe
                    ? 'Already selected as primary'
                    : COST_BASIS_LABELS[opt]
              }
            >
              {COST_BASIS_LABELS[opt]}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function ScenarioCompareTab() {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const flipScorecard = useDashboardStore((s) => s.flipScorecard);
  const flipLoading = useDashboardStore((s) => s.flipLoading);
  const energyMode = useDashboardStore((s) => s.energyMode);
  const costBasis = useDashboardStore((s) => s.costBasis);
  const setCostBasis = useDashboardStore((s) => s.setCostBasis);

  const [secondaryBasis, setSecondaryBasis] = useState<CostBasis | null>(null);

  const primaryDiff = useMemo(() => {
    if (!scorecard || !flipScorecard) return null;
    return computeFlipDiff(scorecard, flipScorecard, energyMode, costBasis);
  }, [scorecard, flipScorecard, energyMode, costBasis]);

  const secondaryDiff = useMemo(() => {
    if (!scorecard || !flipScorecard || !secondaryBasis) return null;
    return computeFlipDiff(scorecard, flipScorecard, energyMode, secondaryBasis);
  }, [scorecard, flipScorecard, energyMode, secondaryBasis]);

  const handlePrimaryChange = (b: CostBasis | null) => {
    if (!b) return;
    setCostBasis(b);
    if (b === secondaryBasis) setSecondaryBasis(null);
  };

  const handleSecondaryChange = (b: CostBasis | null) => {
    if (b === costBasis) return;
    setSecondaryBasis(b);
  };

  return (
    <div className="h-full flex">
      {/* Left column: controls */}
      <div className="w-[340px] shrink-0 h-full">
        <FlipControls />
      </div>

      {/* Right column: toggle bar, summary, diff table */}
      <div className="flex-1 min-w-0 h-full flex flex-col">
        {/* Persistent cost-basis toolbar — visible before and after Compute Flip */}
        <div
          className="shrink-0 flex items-center justify-end gap-4 px-3 py-1.5"
          style={{ borderBottom: '1px solid var(--border-subtle)' }}
        >
          <BasisToggle
            label="Compare on"
            value={costBasis}
            onChange={handlePrimaryChange}
            disabledBasis={secondaryBasis}
          />
          <BasisToggle
            label="vs"
            value={secondaryBasis}
            onChange={handleSecondaryChange}
            allowOff
            disabledBasis={costBasis}
          />
        </div>

        <div
          className="shrink-0"
          style={{
            minHeight: 64,
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <FlipSummary summary={primaryDiff?.summary ?? null} />
        </div>
        <div className="flex-1 min-h-0">
          {primaryDiff ? (
            <FlipDiffTable
              rows={primaryDiff.rows}
              secondaryRows={secondaryDiff?.rows ?? null}
              secondaryBasis={secondaryBasis}
            />
          ) : flipLoading ? (
            <div
              className="h-full flex items-center justify-center text-xs"
              style={{ color: 'var(--text-muted)' }}
            >
              Running flip scenario…
            </div>
          ) : (
            <div
              className="h-full flex flex-col items-center justify-center gap-2 px-6 text-center"
              style={{ color: 'var(--text-muted)' }}
            >
              <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                No flip scenario computed yet
              </div>
              <div className="text-xs max-w-md">
                Pick a preset on the left (or edit individual levers), then click{' '}
                <strong style={{ color: 'var(--accent)' }}>Compute Flip</strong>. You'll see which
                sites change tier, which close the LCOE gap, and which flip to CBAM urgent.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

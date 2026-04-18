import {
  FLIP_PRESET_DESCRIPTIONS,
  FLIP_PRESET_LABELS,
  type FlipPreset,
} from '../../../lib/flipPresets';
import type { UserAssumptions } from '../../../lib/types';
import { useDashboardStore } from '../../../store/dashboard';

const PRESETS: FlipPreset[] = [
  'concessional_finance',
  'cheap_capex',
  'cbam_max_exposure',
  'grant_transmission',
];

type LeverKey =
  | 'wacc_pct'
  | 'capex_usd_per_kw'
  | 'lifetime_yr'
  | 'fom_usd_per_kw_yr'
  | 'bess_capex_usd_per_kwh'
  | 'cbam_certificate_price_eur';

interface LeverConfig {
  key: LeverKey;
  label: string;
  unit: string;
  step: number;
  min: number;
  max: number;
}

const LEVERS: LeverConfig[] = [
  { key: 'wacc_pct', label: 'WACC', unit: '%', step: 0.5, min: 2, max: 20 },
  { key: 'capex_usd_per_kw', label: 'Solar CAPEX', unit: '$/kW', step: 25, min: 300, max: 2000 },
  { key: 'lifetime_yr', label: 'Project Life', unit: 'yr', step: 1, min: 10, max: 40 },
  { key: 'fom_usd_per_kw_yr', label: 'FOM', unit: '$/kW·yr', step: 1, min: 0, max: 50 },
  {
    key: 'bess_capex_usd_per_kwh',
    label: 'BESS CAPEX',
    unit: '$/kWh',
    step: 10,
    min: 100,
    max: 800,
  },
  {
    key: 'cbam_certificate_price_eur',
    label: 'CBAM Cert',
    unit: '€/tCO₂',
    step: 5,
    min: 0,
    max: 200,
  },
];

function formatVal(v: number, step: number): string {
  if (step >= 1) return String(Math.round(v));
  return v.toFixed(1);
}

export default function FlipControls() {
  const baseline = useDashboardStore((s) => s.assumptions);
  const flip = useDashboardStore((s) => s.flipAssumptions);
  const flipPreset = useDashboardStore((s) => s.flipPreset);
  const flipLoading = useDashboardStore((s) => s.flipLoading);
  const flipScorecard = useDashboardStore((s) => s.flipScorecard);
  const flipStale = useDashboardStore((s) => s.flipStale);
  const setFlipAssumptions = useDashboardStore((s) => s.setFlipAssumptions);
  const applyPreset = useDashboardStore((s) => s.applyFlipPreset);
  const computeFlip = useDashboardStore((s) => s.computeFlip);
  const clearFlip = useDashboardStore((s) => s.clearFlip);

  if (!baseline) return null;

  const effective: UserAssumptions = flip ?? baseline;

  const isChanged = (key: LeverKey): boolean => {
    return effective[key] !== baseline[key];
  };

  const grantChanged =
    !!effective.grant_funded_transmission !== !!baseline.grant_funded_transmission;

  const computeDisabled = flipLoading || (!flip && !flipPreset);

  return (
    <div
      className="h-full overflow-y-auto px-3 py-3"
      style={{
        borderRight: '1px solid var(--glass-border)',
        scrollbarWidth: 'thin',
        scrollbarColor: 'var(--scrollbar-thumb) transparent',
      }}
    >
      {/* Actions — pinned at top so Compute is always visible without scrolling */}
      <div className="mb-4 pb-3" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
        <button
          type="button"
          onClick={() => computeFlip()}
          disabled={computeDisabled}
          className="w-full py-2 rounded text-[11px] font-medium transition-colors"
          style={{
            background: computeDisabled ? 'var(--card-bg)' : 'var(--accent)',
            color: computeDisabled ? 'var(--text-muted)' : '#0a0a0c',
            cursor: computeDisabled ? 'not-allowed' : 'pointer',
            opacity: computeDisabled ? 0.5 : 1,
          }}
        >
          {flipLoading
            ? 'Computing…'
            : flipStale
              ? 'Recompute Flip'
              : flipScorecard
                ? 'Recompute'
                : 'Compute Flip'}
        </button>
        {(flip || flipScorecard) && (
          <button
            type="button"
            onClick={clearFlip}
            className="w-full mt-1.5 py-1.5 rounded text-[10px] transition-colors"
            style={{
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            Reset
          </button>
        )}
        {flipStale && (
          <div
            className="mt-2 text-[10px] italic text-center"
            style={{ color: 'var(--warning, #f59e0b)' }}
          >
            Baseline changed — recompute to refresh
          </div>
        )}
      </div>

      {/* Preset picker */}
      <div
        className="text-[10px] uppercase tracking-wider mb-2"
        style={{ color: 'var(--text-muted)' }}
      >
        Preset
      </div>
      <div className="space-y-1.5 mb-4">
        {PRESETS.map((p) => {
          const active = flipPreset === p;
          return (
            <button
              key={p}
              type="button"
              onClick={() => applyPreset(p)}
              className="w-full text-left px-2.5 py-1.5 rounded transition-colors"
              style={{
                background: active ? 'var(--accent-muted)' : 'var(--card-bg)',
                border: `1px solid ${active ? 'var(--accent-border)' : 'var(--border-subtle)'}`,
                color: active ? 'var(--accent)' : 'var(--text-secondary)',
              }}
              title={FLIP_PRESET_DESCRIPTIONS[p]}
            >
              <div className="text-[11px] font-medium">{FLIP_PRESET_LABELS[p]}</div>
            </button>
          );
        })}
        {flipPreset === 'custom' && (
          <div className="text-[10px] italic pt-0.5" style={{ color: 'var(--text-muted)' }}>
            Custom edits
          </div>
        )}
      </div>

      {/* Lever editors */}
      <div
        className="text-[10px] uppercase tracking-wider mb-2 pt-2"
        style={{ color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)' }}
      >
        Levers
      </div>
      <div className="space-y-2 mb-4">
        {LEVERS.map((lever) => {
          const val = effective[lever.key] as number;
          const baseVal = baseline[lever.key] as number;
          const changed = isChanged(lever.key);
          return (
            <div key={lever.key} className="flex items-center justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                  {lever.label}
                </div>
                {changed && (
                  <div className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                    was {formatVal(baseVal, lever.step)} {lever.unit}
                  </div>
                )}
              </div>
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  value={val}
                  min={lever.min}
                  max={lever.max}
                  step={lever.step}
                  onChange={(e) => {
                    const n = Number(e.target.value);
                    if (!Number.isFinite(n)) return;
                    setFlipAssumptions({ [lever.key]: n } as Partial<UserAssumptions>);
                  }}
                  className="w-20 px-1.5 py-1 rounded text-[11px] tabular-nums"
                  style={{
                    background: 'var(--card-bg)',
                    border: `1px solid ${changed ? 'var(--accent-border)' : 'var(--border-subtle)'}`,
                    color: changed ? 'var(--accent)' : 'var(--text-value)',
                  }}
                />
                <span className="text-[9px] w-12" style={{ color: 'var(--text-muted)' }}>
                  {lever.unit}
                </span>
              </div>
            </div>
          );
        })}

        {/* Grant-funded transmission checkbox */}
        <label
          className="flex items-center gap-2 text-[11px] px-2 py-1.5 mt-2 rounded cursor-pointer"
          style={{
            color: effective.grant_funded_transmission ? '#4CAF50' : 'var(--text-secondary)',
            background: effective.grant_funded_transmission
              ? 'rgba(76,175,80,0.10)'
              : 'var(--card-bg)',
            border: `1px solid ${grantChanged ? 'var(--accent-border)' : 'var(--border-subtle)'}`,
          }}
        >
          <input
            type="checkbox"
            checked={!!effective.grant_funded_transmission}
            onChange={(e) => setFlipAssumptions({ grant_funded_transmission: e.target.checked })}
            className="accent-green-500"
          />
          Grant-funded transmission
        </label>
      </div>
    </div>
  );
}

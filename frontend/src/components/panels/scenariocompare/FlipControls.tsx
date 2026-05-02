import {
  FLIP_PRESET_DESCRIPTIONS,
  FLIP_PRESET_LABELS,
  type FlipPreset,
} from '../../../lib/flipPresets';
import type { UserAssumptions } from '../../../lib/types';
import { useDashboardStore } from '../../../store/dashboard';
import HelpBadge from '../../ui/HelpBadge';

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
  | 'cbam_certificate_price_eur'
  | 'land_cost_usd_per_kw'
  | 'connection_cost_per_kw_km'
  | 'grid_connection_fixed_per_kw'
  | 'substation_utilization_pct'
  | 'meaningful_share_pct';

interface LeverConfig {
  key: LeverKey;
  label: string;
  unit: string;
  step: number;
  min: number;
  max: number;
  tip: string;
}

const LEVERS: LeverConfig[] = [
  {
    key: 'wacc_pct',
    label: 'WACC',
    unit: '%',
    step: 0.5,
    min: 2,
    max: 20,
    tip: 'Weighted Average Cost of Capital. Lower = cheaper financing → lower LCOE. DFI concessional debt sits ~4-6%, merchant equity ~12-15%.',
  },
  {
    key: 'capex_usd_per_kw',
    label: 'Solar CAPEX',
    unit: '$/kW',
    step: 25,
    min: 300,
    max: 2000,
    tip: 'Installed solar cost per kW of AC capacity. ESDM 2023 central: $850/kW. Low ~$500, high ~$1,200.',
  },
  {
    key: 'lifetime_yr',
    label: 'Project Life',
    unit: 'yr',
    step: 1,
    min: 10,
    max: 40,
    tip: 'Economic project life in years. Drives the CRF annuity factor. Industry standard for utility-scale solar is 25-30 years.',
  },
  {
    key: 'fom_usd_per_kw_yr',
    label: 'FOM',
    unit: '$/kW·yr',
    step: 1,
    min: 0,
    max: 50,
    tip: 'Fixed O&M cost per kW per year (inverter replacements, inspections, cleaning). ESDM default ~$7.5/kW-yr.',
  },
  {
    key: 'bess_capex_usd_per_kwh',
    label: 'BESS CAPEX',
    unit: '$/kWh',
    step: 10,
    min: 100,
    max: 800,
    tip: 'Battery energy storage cost per kWh. Drives firming adder for 24/7 loads. 2025 tracker price ~$150/kWh and falling.',
  },
  {
    key: 'cbam_certificate_price_eur',
    label: 'CBAM Cert',
    unit: '€/tCO₂',
    step: 5,
    min: 0,
    max: 200,
    tip: 'EU CBAM certificate price in €/tCO₂. ~€80 central. Drives CBAM cost exposure on exports to the EU (cement, steel, fertilizer, aluminium).',
  },
  {
    key: 'land_cost_usd_per_kw',
    label: 'Land Cost',
    unit: '$/kW',
    step: 5,
    min: 0,
    max: 300,
    tip: 'Land lease/purchase cost per kW. Typically small vs CAPEX but flips scenarios near parity. Zero if land contributed in-kind.',
  },
  {
    key: 'connection_cost_per_kw_km',
    label: 'Gen-Tie $/km',
    unit: '$/kW·km',
    step: 0.5,
    min: 0,
    max: 20,
    tip: 'Per-km gen-tie line cost to run from solar farm to nearest substation. Default $5/kW·km. Multiplies with solar-to-sub distance.',
  },
  {
    key: 'grid_connection_fixed_per_kw',
    label: 'Gen-Tie Fixed',
    unit: '$/kW',
    step: 5,
    min: 0,
    max: 300,
    tip: 'One-time fixed connection fee per kW (metering, studies, protection). Default $80/kW. Added on top of distance × $/km.',
  },
  {
    key: 'substation_utilization_pct',
    label: 'Sub Utilization',
    unit: '',
    step: 0.05,
    min: 0,
    max: 0.95,
    tip: 'Assumed fraction of nearest substation capacity already in use. Available headroom = rated MVA × (1 - utilization). Higher = less room for new solar.',
  },
  {
    key: 'meaningful_share_pct',
    label: 'Project Sizing',
    unit: '',
    step: 0.05,
    min: 0.1,
    max: 1.0,
    tip: 'First-phase solar sized to cover this share of site demand. Lower = smaller project, fewer substation upgrades. 0.30 = phase-1 realistic, 1.00 = full self-sufficiency.',
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
            background: computeDisabled
              ? 'color-mix(in srgb, var(--accent) 8%, transparent)'
              : 'var(--accent)',
            color: computeDisabled ? 'var(--accent)' : '#0a0a0c',
            cursor: computeDisabled ? 'not-allowed' : 'pointer',
            border: computeDisabled ? `1px dashed var(--accent-border)` : '1px solid transparent',
            opacity: computeDisabled ? 0.85 : 1,
          }}
          title={computeDisabled && !flipLoading ? 'Pick a preset below to enable' : undefined}
        >
          {flipLoading
            ? 'Computing…'
            : flipStale
              ? 'Recompute Flip'
              : flipScorecard
                ? 'Recompute'
                : !flipPreset
                  ? 'Compute Flip (pick a preset)'
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
                background: active
                  ? 'color-mix(in srgb, var(--accent) 18%, transparent)'
                  : 'var(--card-bg)',
                border: `1px solid ${active ? 'var(--accent)' : 'var(--border-subtle)'}`,
                borderLeft: active ? `3px solid var(--accent)` : `1px solid var(--border-subtle)`,
                paddingLeft: active ? 8 : 10,
                color: active ? 'var(--accent)' : 'var(--text-secondary)',
                fontWeight: active ? 600 : 400,
              }}
              title={FLIP_PRESET_DESCRIPTIONS[p]}
            >
              <div className="text-[11px]">{FLIP_PRESET_LABELS[p]}</div>
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
                <div
                  className="text-[11px] flex items-center"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {lever.label}
                  <HelpBadge tip={lever.tip} />
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

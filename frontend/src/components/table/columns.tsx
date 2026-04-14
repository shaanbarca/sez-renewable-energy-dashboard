import { type CellContext, createColumnHelper, type FilterFn } from '@tanstack/react-table';
import { getEffectiveActionFlag, getEffectiveFlagExplanation } from '../../lib/actionFlags';
import { ACTION_FLAG_COLORS, ACTION_FLAG_LABELS } from '../../lib/constants';
import { capitalize, formatSnakeLabel } from '../../lib/format';
import type { ActionFlag, ScorecardRow } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

declare module '@tanstack/react-table' {
  interface FilterFns {
    inRange: FilterFn<unknown>;
  }
}

/* ---------- Column header tooltips ---------- */

const COLUMN_TOOLTIPS: Record<string, string> = {
  kek_name: 'Special Economic Zone (Kawasan Ekonomi Khusus) name',
  province: 'Indonesian province where the KEK is located',
  kek_type: 'KEK classification: Industrial, Tourism, or Mixed',
  category: 'Development stage: Established, Proposed, or Under Construction',
  area_ha: 'Total designated KEK area in hectares',
  max_captive_capacity_mwp:
    'Maximum buildable solar capacity (MWp) within 50km, based on buildability filters (slope, land cover, protected areas)',
  action_flag:
    'Recommended action based on solar economics, grid readiness, and RUPTL pipeline status',
  lcoe_mid_usd_mwh:
    'Levelized Cost of Energy for solar at mid-case WACC (USD per MWh). Lower = cheaper solar.',
  lcoe_wind_mid_usd_mwh:
    'Levelized Cost of Energy for onshore wind at 10% WACC. CAPEX $1,650/kW (ESDM 2024), FOM $40/kW-yr, 27yr. Lower = cheaper wind.',
  solar_competitive_gap_pct:
    'LCOE gap to grid benchmark. Negative = solar is cheaper than grid. Positive = solar is more expensive. Benchmark is BPP or I-4/TT tariff depending on mode.',
  best_re_technology: 'Best available renewable energy technology for this KEK',
  dashboard_rate_usd_mwh:
    'PLN grid cost proxy (BPP cost of supply, not the subsidized industrial tariff)',
  grid_integration_category:
    'Grid readiness: within_boundary (solar inside KEK), grid_ready (substation near both), invest_transmission (build transmission to KEK), invest_substation (build substation near solar), grid_first (major grid expansion needed)',
  grid_investment_needed_usd:
    'Estimated total grid infrastructure cost: gen-tie + new transmission line + substation upgrade. Scales with project capacity (MWp). Screening estimate for DFI investment sizing.',
  solar_supply_coverage_pct:
    "Maximum % of this KEK's electricity demand coverable by renewable energy (solar) built within 50km. Green = 100%+, yellow = 50-99%, red = under 50%.",
  captive_power_type:
    'Captive fossil power near this KEK: Coal (GEM GCPT, within 50km), Nickel smelters (CGSP, within 50km), or both. Subject to Perpres 112/2022 phase-out.',
  captive_coal_mw:
    'Total captive coal plant capacity (MW) within 50km of KEK. Source: GEM Global Coal Plant Tracker.',
  nickel_smelter_count:
    'Number of nickel processing facilities within 50km. Source: CGSP Nickel Tracker.',
  dominant_process_type:
    'Most common nickel smelting process near KEK. RKEF (24/7 baseload, doubles BESS sizing), Ferro Nickel, HPAL, Laterite.',
  solar_replacement_pct:
    'What % of captive coal generation could be replaced by buildable solar within 50km. Assumes 40% coal capacity factor.',
};

function HeaderWithTooltip({ label, columnId }: { label: string; columnId: string }) {
  const tip = COLUMN_TOOLTIPS[columnId];
  if (!tip) return <span>{label}</span>;
  return (
    <span className="flex items-center gap-1">
      <span>{label}</span>
      <span className="relative group/tip">
        <svg
          width="12"
          height="12"
          viewBox="0 0 16 16"
          fill="none"
          className="text-zinc-500 hover:text-zinc-300 transition-colors cursor-help flex-shrink-0"
        >
          <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
          <text x="8" y="12" textAnchor="middle" fill="currentColor" fontSize="10" fontWeight="600">
            ?
          </text>
        </svg>
        <span
          className="absolute left-1/2 -translate-x-1/2 top-full mt-2 w-52 px-2.5 py-2
                     text-[10px] leading-relaxed text-zinc-300 font-normal whitespace-normal
                     rounded-md shadow-lg z-50 pointer-events-none
                     opacity-0 group-hover/tip:opacity-100 transition-opacity duration-150"
          style={{
            background: 'var(--glass-heavy)',
            backdropFilter: 'var(--blur-heavy)',
            WebkitBackdropFilter: 'var(--blur-heavy)',
            border: '1px solid var(--glass-border-bright)',
            boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06), 0 4px 16px rgba(0,0,0,0.4)',
          }}
        >
          {tip}
        </span>
      </span>
    </span>
  );
}

/* ---------- Action flag cell (energy-mode-aware) ---------- */

function ActionFlagCell({ info }: { info: CellContext<ScorecardRow, ActionFlag> }) {
  const energyMode = useDashboardStore((s) => s.energyMode);
  const row = info.row.original;
  const flag = getEffectiveActionFlag(row, energyMode);
  const color = ACTION_FLAG_COLORS[flag] ?? '#666';
  const label = ACTION_FLAG_LABELS[flag] ?? flag;
  const explanation = getEffectiveFlagExplanation(flag, row, energyMode);

  return (
    <span className="relative group/flag flex items-center gap-2">
      <span
        className="inline-block w-2 h-2 rounded-full flex-shrink-0"
        style={{ backgroundColor: color }}
      />
      <span>{label}</span>
      {explanation && (
        <span
          className="absolute left-0 top-full mt-1 w-56 px-2.5 py-2
                     text-[10px] leading-relaxed text-zinc-300 font-normal whitespace-normal
                     rounded-md shadow-lg z-50 pointer-events-none
                     opacity-0 group-hover/flag:opacity-100 transition-opacity duration-150"
          style={{
            background: 'var(--glass-heavy)',
            backdropFilter: 'var(--blur-heavy)',
            WebkitBackdropFilter: 'var(--blur-heavy)',
            border: `1px solid ${color}44`,
            boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06), 0 4px 16px rgba(0,0,0,0.4)',
          }}
        >
          <span className="font-medium" style={{ color }}>
            {label}:
          </span>{' '}
          {explanation}
        </span>
      )}
    </span>
  );
}

/* ---------- Grid Rate (benchmark-aware) ---------- */

function GridRateHeader() {
  const mode = useDashboardStore((s) => s.benchmarkMode);
  const label = mode === 'bpp' ? 'BPP ($/MWh)' : 'Tariff ($/MWh)';
  return <HeaderWithTooltip label={label} columnId="dashboard_rate_usd_mwh" />;
}

function GridRateCell({ info }: { info: CellContext<ScorecardRow, number> }) {
  const mode = useDashboardStore((s) => s.benchmarkMode);
  const row = info.row.original;
  const value = mode === 'bpp' && row.bpp_usd_mwh != null ? row.bpp_usd_mwh : info.getValue();
  return <>{value.toFixed(1)}</>;
}

/* ---------- Column definitions ---------- */

const col = createColumnHelper<ScorecardRow>();

export const columns = [
  col.accessor('kek_name', {
    header: () => <HeaderWithTooltip label="KEK Name" columnId="kek_name" />,
    cell: (info) => info.getValue(),
  }),
  col.accessor('province', {
    header: () => <HeaderWithTooltip label="Province" columnId="province" />,
    cell: (info) => info.getValue(),
  }),
  col.accessor('kek_type', {
    header: () => <HeaderWithTooltip label="Type" columnId="kek_type" />,
    cell: (info) => info.getValue() ?? '—',
  }),
  col.accessor('category', {
    header: () => <HeaderWithTooltip label="Category" columnId="category" />,
    cell: (info) => info.getValue() ?? '—',
  }),
  col.accessor('area_ha', {
    header: () => <HeaderWithTooltip label="Area (ha)" columnId="area_ha" />,
    filterFn: 'inRange',
    cell: (info) => {
      const v = info.getValue();
      return v != null ? v.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '—';
    },
  }),
  col.accessor('max_captive_capacity_mwp', {
    header: () => <HeaderWithTooltip label="Capacity (MWp)" columnId="max_captive_capacity_mwp" />,
    filterFn: 'inRange',
    cell: (info) => {
      const v = info.getValue();
      return v != null ? v.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '—';
    },
  }),
  col.accessor('action_flag', {
    header: () => <HeaderWithTooltip label="Action Flag" columnId="action_flag" />,
    cell: (info) => <ActionFlagCell info={info} />,
  }),
  col.accessor('grid_integration_category', {
    header: () => (
      <HeaderWithTooltip label="Grid Integration" columnId="grid_integration_category" />
    ),
    cell: (info) => {
      const val = info.getValue();
      return val ? formatSnakeLabel(val) : '—';
    },
  }),
  col.accessor('grid_investment_needed_usd', {
    header: () => (
      <HeaderWithTooltip label="Grid Invest ($M)" columnId="grid_investment_needed_usd" />
    ),
    filterFn: 'inRange',
    cell: (info) => {
      const v = info.getValue();
      if (v == null) return <span style={{ color: 'var(--text-muted)' }}>—</span>;
      const millions = v / 1_000_000;
      const color = millions > 500 ? '#EF5350' : millions > 100 ? '#FFC107' : '#4CAF50';
      return <span style={{ color }}>${millions.toFixed(0)}M</span>;
    },
  }),
  col.display({
    id: 'captive_power_type',
    header: () => <HeaderWithTooltip label="Captive" columnId="captive_power_type" />,
    enableColumnFilter: true,
    filterFn: (row, _columnId, filterValue: string) => {
      const r = row.original;
      const hasCoal = !!r.captive_coal_count && r.captive_coal_count > 0;
      const hasNickel = !!r.nickel_smelter_count && r.nickel_smelter_count > 0;
      const type =
        hasCoal && hasNickel ? 'Coal + Nickel' : hasCoal ? 'Coal' : hasNickel ? 'Nickel' : 'None';
      return type === filterValue;
    },
    cell: (info) => {
      const r = info.row.original;
      const hasCoal = !!r.captive_coal_count && r.captive_coal_count > 0;
      const hasNickel = !!r.nickel_smelter_count && r.nickel_smelter_count > 0;
      if (!hasCoal && !hasNickel) return <span style={{ color: 'var(--text-muted)' }}>—</span>;
      return (
        <span className="flex items-center gap-1 flex-wrap">
          {hasCoal && (
            <span
              className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium"
              style={{ background: '#B71C1C33', color: '#EF5350' }}
            >
              Coal {r.captive_coal_mw != null ? `${r.captive_coal_mw} MW` : ''}
            </span>
          )}
          {hasNickel && (
            <span
              className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium"
              style={{ background: '#FF6D0033', color: '#FF8F00' }}
            >
              Ni ×{r.nickel_smelter_count}
            </span>
          )}
        </span>
      );
    },
  }),
  col.accessor('dominant_process_type', {
    header: () => <HeaderWithTooltip label="Ni Process" columnId="dominant_process_type" />,
    cell: (info) => {
      const val = info.getValue();
      if (!val) return <span style={{ color: 'var(--text-muted)' }}>—</span>;
      const isRkef = val.toUpperCase() === 'RKEF';
      return (
        <span style={{ color: isRkef ? '#FF8F00' : 'var(--text-primary)' }}>
          {val}
          {isRkef ? ' (24/7)' : ''}
        </span>
      );
    },
  }),
  col.accessor('solar_replacement_pct', {
    header: () => <HeaderWithTooltip label="Solar Repl." columnId="solar_replacement_pct" />,
    filterFn: 'inRange',
    cell: (info) => {
      const val = info.getValue();
      if (val == null) return <span style={{ color: 'var(--text-muted)' }}>—</span>;
      const color = val >= 100 ? '#4CAF50' : val >= 50 ? '#FFC107' : '#F44336';
      return <span style={{ color }}>{val.toFixed(0)}%</span>;
    },
  }),
  col.accessor('lcoe_mid_usd_mwh', {
    header: () => <HeaderWithTooltip label="Solar LCOE" columnId="lcoe_mid_usd_mwh" />,
    filterFn: 'inRange',
    cell: (info) => info.getValue().toFixed(1),
  }),
  col.accessor('lcoe_wind_mid_usd_mwh', {
    header: () => <HeaderWithTooltip label="Wind LCOE" columnId="lcoe_wind_mid_usd_mwh" />,
    filterFn: 'inRange',
    cell: (info) => {
      const v = info.getValue();
      return v != null ? v.toFixed(1) : '—';
    },
  }),
  col.accessor('solar_competitive_gap_pct', {
    header: () => <HeaderWithTooltip label="LCOE Gap (%)" columnId="solar_competitive_gap_pct" />,
    filterFn: 'inRange',
    cell: (info) => {
      const val = info.getValue();
      const sign = val > 0 ? '+' : '';
      const color = val < 0 ? '#4CAF50' : val > 0 ? '#EF5350' : '#e0e0e0';
      return (
        <span style={{ color }}>
          {sign}
          {val.toFixed(1)}%
        </span>
      );
    },
  }),
  col.accessor('solar_supply_coverage_pct', {
    header: () => <HeaderWithTooltip label="RE Coverage" columnId="solar_supply_coverage_pct" />,
    filterFn: 'inRange',
    cell: (info) => {
      const val = info.getValue();
      if (val == null) return '—';
      const pct = val * 100;
      const color = val >= 1.0 ? '#4CAF50' : val >= 0.5 ? '#FFC107' : '#F44336';
      return <span style={{ color }}>{pct.toFixed(0)}%</span>;
    },
  }),
  col.accessor('best_re_technology', {
    header: () => <HeaderWithTooltip label="Best RE" columnId="best_re_technology" />,
    cell: (info) => capitalize(info.getValue()),
  }),
  col.accessor('dashboard_rate_usd_mwh', {
    header: () => <GridRateHeader />,
    filterFn: 'inRange',
    cell: (info) => <GridRateCell info={info} />,
  }),
];

import { type CellContext, createColumnHelper, type FilterFn } from '@tanstack/react-table';
import {
  getEconomicTierDescription,
  getEconomicTierLabel,
  getEffectiveEconomicTier,
  getEffectiveInfraReadiness,
} from '../../lib/actionFlags';
import {
  ECONOMIC_TIER_COLORS,
  INFRA_READINESS_COLORS,
  INFRA_READINESS_LABELS,
} from '../../lib/constants';
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
  site_name: 'Site name (KEK, industrial plant, or industrial park)',
  province: 'Indonesian province where the KEK is located',
  zone_classification: 'Site classification: Industrial, Tourism, or Mixed',
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
  cbam_adjusted_gap_pct:
    'Competitive gap adjusted for EU CBAM savings. Subtracts avoided carbon border tax ($/MWh) from solar LCOE before comparing to grid cost. At 2030 rates. Only for CBAM-exposed KEKs.',
  economic_tier:
    'Economic competitiveness: Full RE (RE+storage beats grid), Partial RE (daytime RE beats grid), Near Parity (within 20%), Not Competitive, No Resource. Mode-aware (solar/wind/hybrid).',
  infrastructure_readiness:
    'Infrastructure readiness: Within Boundary, Grid Ready, Invest Transmission, Invest/Upgrade Substation, Grid First. Based on three-point proximity analysis.',
  grid_integration_category:
    'Grid readiness: within_boundary (solar inside KEK), grid_ready (substation near both), invest_transmission (build transmission to KEK), invest_substation (build substation near solar), grid_first (major grid expansion needed)',
  grid_investment_needed_usd:
    'Estimated total grid infrastructure cost: gen-tie + new transmission line + substation upgrade. Scales with project capacity (MWp). Screening estimate for DFI investment sizing.',
  solar_supply_coverage_pct:
    "Maximum % of this KEK's electricity demand coverable by renewable energy (solar) built within 50km. Green = 100%+, yellow = 50-99%, red = under 50%.",
  industry:
    'Nearby industry within 50km: captive coal (GEM GCPT), nickel smelters (CGSP), steel plants (GEM GISPT), cement plants (GEM GCPT). CBAM-exposed sectors face EU carbon border pricing from 2026.',
  cbam_2030:
    'EU CBAM cost per tonne of product at 2030 rates (51.5% free allocation remaining). By 2034 free allocation reaches 0% and full EU ETS price applies (~€80/tCO₂). Sortable to find highest-exposure KEKs.',
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

/* ---------- RE Assessment cell (2D: economic tier + infrastructure) ---------- */

function ReAssessmentCell({ info }: { info: CellContext<ScorecardRow, ActionFlag> }) {
  const energyMode = useDashboardStore((s) => s.energyMode);
  const row = info.row.original;
  const tier = getEffectiveEconomicTier(row, energyMode);
  const infra = getEffectiveInfraReadiness(row);
  const color = ECONOMIC_TIER_COLORS[tier] ?? '#666';
  const tierLabel = getEconomicTierLabel(tier, energyMode);
  const infraLabel = INFRA_READINESS_LABELS[infra] ?? infra;
  const description = getEconomicTierDescription(tier, energyMode);

  return (
    <span className="relative group/flag flex items-center gap-1.5">
      <span
        className="relative inline-flex items-center justify-center flex-shrink-0"
        style={{ width: 12, height: 12 }}
      >
        <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
        {row.cbam_exposed && (
          <span
            className="absolute inset-0 rounded-full"
            style={{ border: '1.5px solid #FF6F00' }}
            title="CBAM Exposed"
          />
        )}
      </span>
      <span className="flex flex-col leading-tight">
        <span className="text-xs" style={{ color }}>
          {tierLabel}
        </span>
        <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
          {infraLabel}
        </span>
      </span>
      {description && (
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
            {tierLabel}:
          </span>{' '}
          {description}
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
  col.accessor('site_name', {
    header: () => <HeaderWithTooltip label="Site Name" columnId="site_name" />,
    cell: (info) => info.getValue(),
  }),
  col.accessor('province', {
    header: () => <HeaderWithTooltip label="Province" columnId="province" />,
    cell: (info) => info.getValue(),
  }),
  col.accessor('zone_classification', {
    header: () => <HeaderWithTooltip label="Type" columnId="zone_classification" />,
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
    header: () => <HeaderWithTooltip label="RE Assessment" columnId="action_flag" />,
    cell: (info) => <ReAssessmentCell info={info} />,
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
  col.display({
    id: 'economic_tier',
    header: () => <HeaderWithTooltip label="Econ. Tier" columnId="economic_tier" />,
    enableColumnFilter: true,
    filterFn: (row, _columnId, filterValue: string) => {
      const tier = getEffectiveEconomicTier(row.original, useDashboardStore.getState().energyMode);
      return tier === filterValue;
    },
    cell: (info) => {
      const energyMode = useDashboardStore.getState().energyMode;
      const tier = getEffectiveEconomicTier(info.row.original, energyMode);
      const color = ECONOMIC_TIER_COLORS[tier] ?? '#666';
      const label = getEconomicTierLabel(tier, energyMode);
      return (
        <span className="flex items-center gap-1">
          <span
            className="inline-block w-2 h-2 rounded-full flex-shrink-0"
            style={{ background: color }}
          />
          <span style={{ color, fontSize: 11 }}>{label}</span>
        </span>
      );
    },
  }),
  col.display({
    id: 'infrastructure_readiness',
    header: () => <HeaderWithTooltip label="Infra Ready" columnId="infrastructure_readiness" />,
    enableColumnFilter: true,
    filterFn: (row, _columnId, filterValue: string) => {
      const infra = getEffectiveInfraReadiness(row.original);
      return infra === filterValue;
    },
    cell: (info) => {
      const infra = getEffectiveInfraReadiness(info.row.original);
      const color = INFRA_READINESS_COLORS[infra] ?? '#666';
      const label = INFRA_READINESS_LABELS[infra] ?? formatSnakeLabel(infra);
      return (
        <span className="flex items-center gap-1">
          <span
            className="inline-block w-2 h-2 rounded-full flex-shrink-0"
            style={{ background: color }}
          />
          <span style={{ color, fontSize: 11 }}>{label}</span>
        </span>
      );
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
    id: 'industry',
    header: () => <HeaderWithTooltip label="Industry" columnId="industry" />,
    enableColumnFilter: true,
    filterFn: (row, _columnId, filterValue: string) => {
      const r = row.original;
      const types: string[] = [];
      if (r.captive_coal_count && r.captive_coal_count > 0) types.push('Coal');
      if (r.nickel_smelter_count && r.nickel_smelter_count > 0) types.push('Nickel');
      if (r.steel_plant_count && r.steel_plant_count > 0) types.push('Steel');
      if (r.cement_plant_count && r.cement_plant_count > 0) types.push('Cement');
      if (filterValue === 'None') return types.length === 0;
      return types.includes(filterValue);
    },
    cell: (info) => {
      const r = info.row.original;
      const hasCoal = !!r.captive_coal_count && r.captive_coal_count > 0;
      const hasNickel = !!r.nickel_smelter_count && r.nickel_smelter_count > 0;
      const hasSteel = !!r.steel_plant_count && r.steel_plant_count > 0;
      const hasCement = !!r.cement_plant_count && r.cement_plant_count > 0;
      if (!hasCoal && !hasNickel && !hasSteel && !hasCement)
        return <span style={{ color: 'var(--text-muted)' }}>—</span>;
      const isRkef = r.dominant_process_type?.toUpperCase() === 'RKEF';
      return (
        <span className="flex items-center gap-1 flex-wrap">
          {hasCoal && (
            <span
              className="inline-flex items-center px-1 py-0.5 rounded text-[9px] font-medium"
              style={{ background: '#B71C1C33', color: '#EF5350' }}
              title={`${r.captive_coal_count} coal plant${r.captive_coal_count! > 1 ? 's' : ''}${r.captive_coal_mw ? `, ${r.captive_coal_mw} MW` : ''}`}
            >
              Coal{r.captive_coal_mw ? ` ${r.captive_coal_mw}MW` : ''}
            </span>
          )}
          {hasNickel && (
            <span
              className="inline-flex items-center px-1 py-0.5 rounded text-[9px] font-medium"
              style={{ background: '#FF6D0033', color: '#FF8F00' }}
              title={`${r.nickel_smelter_count} smelter${r.nickel_smelter_count! > 1 ? 's' : ''}${r.dominant_process_type ? ` (${r.dominant_process_type})` : ''}`}
            >
              Ni ×{r.nickel_smelter_count}
              {isRkef ? ' RKEF' : ''}
            </span>
          )}
          {hasSteel && (
            <span
              className="inline-flex items-center px-1 py-0.5 rounded text-[9px] font-medium"
              style={{ background: '#5C6BC033', color: '#7986CB' }}
              title={`${r.steel_plant_count} steel plant${r.steel_plant_count! > 1 ? 's' : ''}${r.steel_capacity_tpa ? `, ${(r.steel_capacity_tpa / 1e6).toFixed(1)}M tpa` : ''}`}
            >
              Steel{r.steel_capacity_tpa ? ` ${(r.steel_capacity_tpa / 1e6).toFixed(1)}Mt` : ''}
            </span>
          )}
          {hasCement && (
            <span
              className="inline-flex items-center px-1 py-0.5 rounded text-[9px] font-medium"
              style={{ background: '#78909C33', color: '#90A4AE' }}
              title={`${r.cement_plant_count} cement plant${r.cement_plant_count! > 1 ? 's' : ''}${r.cement_capacity_mtpa ? `, ${r.cement_capacity_mtpa.toFixed(1)} Mtpa` : ''}`}
            >
              Cement{r.cement_capacity_mtpa ? ` ${r.cement_capacity_mtpa.toFixed(0)}Mt` : ''}
            </span>
          )}
        </span>
      );
    },
  }),
  col.display({
    id: 'cbam_2030',
    header: () => <HeaderWithTooltip label="CBAM '30" columnId="cbam_2030" />,
    enableColumnFilter: true,
    filterFn: (row, _columnId, filterValue: string) => {
      const exposed = !!row.original.cbam_exposed;
      return filterValue === 'Yes' ? exposed : !exposed;
    },
    cell: (info) => {
      const r = info.row.original;
      if (!r.cbam_exposed) {
        return <span style={{ color: 'var(--text-muted)' }}>—</span>;
      }
      const cost2030 = r.cbam_cost_2030_usd_per_tonne;
      const cost2026 = r.cbam_cost_2026_usd_per_tonne;
      const cost2034 = r.cbam_cost_2034_usd_per_tonne;
      const types = r.cbam_product_type
        ? r.cbam_product_type
            .split(',')
            .map((t: string) => {
              const labels: Record<string, string> = {
                iron_steel: 'Iron/Steel',
                aluminium: 'Aluminium',
                fertilizer: 'Fertilizer',
                cement: 'Cement',
              };
              return labels[t] ?? t;
            })
            .join(', ')
        : '';
      const tooltip = `${types}\n2026: $${cost2026?.toLocaleString() ?? '?'}/t\n2030: $${cost2030?.toLocaleString() ?? '?'}/t\n2034: $${cost2034?.toLocaleString() ?? '?'}/t`;
      return (
        <span
          className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium"
          style={{ background: '#FF704433', color: '#FF7043' }}
          title={tooltip}
        >
          {cost2030 != null ? `$${cost2030.toLocaleString()}/t` : 'Exposed'}
        </span>
      );
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
  col.accessor('cbam_adjusted_gap_pct', {
    header: () => <HeaderWithTooltip label="CBAM Gap (%)" columnId="cbam_adjusted_gap_pct" />,
    filterFn: 'inRange',
    cell: (info) => {
      const val = info.getValue();
      if (val == null) return <span style={{ color: '#666' }}>—</span>;
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
  col.accessor('cbam_cost_2030_usd_per_tonne', {
    header: () => <HeaderWithTooltip label="CBAM 2030 ($/t)" columnId="cbam_2030" />,
    filterFn: 'inRange',
    cell: (info) => {
      const val = info.getValue();
      if (val == null) return <span style={{ color: '#666' }}>—</span>;
      return <span style={{ color: '#FF6F00' }}>${val.toFixed(0)}/t</span>;
    },
  }),
];

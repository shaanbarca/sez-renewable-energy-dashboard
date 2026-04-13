import * as Tabs from '@radix-ui/react-tabs';
import { useCallback, useEffect, useState } from 'react';
import { fetchKekSubstations } from '../../lib/api';
import { ACTION_FLAG_COLORS, ACTION_FLAG_HIERARCHY, ACTION_FLAG_LABELS } from '../../lib/constants';
import { capitalize, formatGridRegion, formatSnakeLabel } from '../../lib/format';
import type {
  ActionFlag,
  ScorecardRow,
  SubstationWithCosts,
  UserAssumptions,
} from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';
import EnergyBalanceChart from '../charts/EnergyBalanceChart';
import LcoeCurveChart from '../charts/LcoeCurveChart';
import Slider from '../ui/Slider';
import SubstationComparison from '../ui/SubstationComparison';

/* ---------- Helpers ---------- */

function CloseIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function StatRow({
  label,
  value,
  unit,
}: {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
}) {
  const display = value == null || value === '' ? 'N/A' : `${value}${unit ? ` ${unit}` : ''}`;
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
        {label}
      </span>
      <span className="text-[12px] font-medium tabular-nums" style={{ color: 'var(--text-value)' }}>
        {display}
      </span>
    </div>
  );
}

function StatRowWithTip({
  label,
  value,
  unit,
  tip,
}: {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  tip: string;
}) {
  const [showTip, setShowTip] = useState(false);
  const display = value == null || value === '' ? 'N/A' : `${value}${unit ? ` ${unit}` : ''}`;
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-[11px] relative" style={{ color: 'var(--text-muted)' }}>
        {label}
        <span
          className="ml-1 cursor-help inline-block"
          style={{ color: 'var(--text-muted)' }}
          onMouseEnter={() => setShowTip(true)}
          onMouseLeave={() => setShowTip(false)}
        >
          ?
          {showTip && (
            <span
              className="absolute left-0 top-full mt-1 z-30 px-2.5 py-1.5 rounded text-[10px] leading-snug whitespace-normal w-48"
              style={{
                background: 'var(--popup-bg)',
                color: 'var(--text-value)',
                border: '1px solid var(--popup-border)',
                boxShadow: 'var(--popup-shadow)',
              }}
            >
              {tip}
            </span>
          )}
        </span>
      </span>
      <span className="text-[12px] font-medium tabular-nums" style={{ color: 'var(--text-value)' }}>
        {display}
      </span>
    </div>
  );
}

/** Colored stat value — green/yellow/red based on value. */
function ColoredStatRow({
  label,
  value,
  unit,
  tip,
  color,
}: {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  tip?: string;
  color?: string;
}) {
  const [showTip, setShowTip] = useState(false);
  const display = value == null || value === '' ? 'N/A' : `${value}${unit ? ` ${unit}` : ''}`;
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-[11px] relative" style={{ color: 'var(--text-muted)' }}>
        {label}
        {tip && (
          <span
            className="ml-1 cursor-help inline-block"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={() => setShowTip(true)}
            onMouseLeave={() => setShowTip(false)}
          >
            ?
            {showTip && (
              <span
                className="absolute left-0 top-full mt-1 z-30 px-2.5 py-1.5 rounded text-[10px] leading-snug whitespace-normal w-48"
                style={{
                  background: 'var(--popup-bg)',
                  color: 'var(--text-value)',
                  border: '1px solid var(--popup-border)',
                  boxShadow: 'var(--popup-shadow)',
                }}
              >
                {tip}
              </span>
            )}
          </span>
        )}
      </span>
      <span
        className="text-[12px] font-medium tabular-nums"
        style={{ color: color ?? 'var(--text-value)' }}
      >
        {display}
      </span>
    </div>
  );
}

function StatCard({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="rounded-md px-3 py-2 mb-2"
      style={{
        background: 'var(--card-bg)',
        border: '1px solid var(--card-border)',
      }}
    >
      {children}
    </div>
  );
}

function SectionHeader({
  title,
  tip,
  subtitle,
}: {
  title: string;
  tip?: string;
  subtitle?: string;
}) {
  const [showTip, setShowTip] = useState(false);
  return (
    <div className="mb-1.5 relative">
      <div className="text-[11px] font-medium" style={{ color: 'var(--text-muted)' }}>
        {title}
        {tip && (
          <span
            className="ml-1 cursor-help inline-block"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={() => setShowTip(true)}
            onMouseLeave={() => setShowTip(false)}
          >
            ?
            {showTip && (
              <span
                className="absolute left-0 top-full mt-1 z-30 px-2.5 py-1.5 rounded text-[10px] leading-snug whitespace-normal w-52"
                style={{
                  background: 'var(--popup-bg)',
                  color: 'var(--text-value)',
                  border: '1px solid var(--popup-border)',
                  boxShadow: 'var(--popup-shadow)',
                }}
              >
                {tip}
              </span>
            )}
          </span>
        )}
      </div>
      {subtitle && (
        <div
          className="text-[10px] leading-snug mt-0.5"
          style={{ color: 'var(--text-muted)', opacity: 0.7 }}
        >
          {subtitle}
        </div>
      )}
    </div>
  );
}

/** Single step in the hierarchical flag stepper. */
function FlagStep({
  label,
  color,
  active,
  above,
  isFirst,
  isLast,
  explanation,
}: {
  label: string;
  color: string;
  active: boolean;
  above: boolean;
  isFirst: boolean;
  isLast: boolean;
  explanation?: string;
}) {
  const dotSize = active ? 12 : 8;
  const dotColor = active ? color : above ? 'var(--border-subtle)' : `${color}55`;
  const trackColor = isLast ? 'transparent' : 'var(--border-subtle)';

  return (
    <div className="flex gap-0">
      {/* Track column: always continuous */}
      <div className="flex flex-col items-center shrink-0" style={{ width: 20 }}>
        {/* Top line (above dot) */}
        <div
          style={{
            width: 2,
            height: 6,
            background: isFirst ? 'transparent' : 'var(--border-subtle)',
          }}
        />
        {/* Dot */}
        <div
          className="rounded-full shrink-0"
          style={{
            width: dotSize,
            height: dotSize,
            background: dotColor,
            boxShadow: active ? `0 0 8px ${color}66` : 'none',
          }}
        />
        {/* Bottom line (fills remaining height, including explanation) */}
        <div
          className="flex-1"
          style={{
            width: 2,
            background: trackColor,
            minHeight: 6,
          }}
        />
      </div>
      {/* Content column */}
      <div className="pl-2 flex-1 pb-1">
        <div className="flex items-center" style={{ minHeight: dotSize + 12 }}>
          <span
            className={`text-[11px] ${active ? 'font-medium' : ''}`}
            style={{
              color: active ? color : above ? 'var(--text-muted)' : 'var(--text-secondary)',
              opacity: active ? 1 : above ? 0.5 : 0.7,
            }}
          >
            {label}
          </span>
        </div>
        {active && explanation && (
          <p
            className="text-[10px] leading-relaxed pb-1"
            style={{ color: 'var(--text-secondary)' }}
          >
            {explanation}
          </p>
        )}
      </div>
    </div>
  );
}

function getFlagExplanation(flag: ActionFlag, row: ScorecardRow): string {
  switch (flag) {
    case 'solar_now':
      return 'Solar is cost-competitive with the grid today. Grid upgrades are planned and sufficient GEAS allocation exists.';
    case 'invest_resilience': {
      const gap = row.solar_competitive_gap_pct;
      return `Solar is within ${gap != null ? Math.abs(gap).toFixed(0) : '~20'}% of grid parity. Investing now builds resilience against future grid cost increases.`;
    }
    case 'grid_first':
      return `Solar is cost-competitive here (LCOE $${row.lcoe_mid_usd_mwh?.toFixed(1)}/MWh vs grid $${row.grid_cost_usd_mwh?.toFixed(1)}/MWh), but ${row.grid_upgrade_planned === false ? 'no grid upgrade is planned before 2030' : 'grid infrastructure needs improvement'} — solar cannot connect until the grid catches up.`;
    case 'invest_transmission':
      return `Solar can reach a nearby substation, but the KEK is far from grid infrastructure. Build transmission from substation to KEK${row.dist_to_nearest_substation_km ? ` (${row.dist_to_nearest_substation_km.toFixed(0)}km)` : ''}.`;
    case 'invest_substation':
      return `KEK is grid-connected, but the best solar site is far from any substation. Build a substation or connection point near the solar farm${row.dist_solar_to_nearest_substation_km ? ` (${row.dist_solar_to_nearest_substation_km.toFixed(0)}km)` : ''}.`;
    case 'invest_battery': {
      const parts = ['Solar economics work, but this KEK needs battery storage for reliability.'];
      const sizingHrs = row.bess_sizing_hours ?? 2;
      if (row.battery_adder_usd_mwh)
        parts.push(
          `Battery adds +$${row.battery_adder_usd_mwh.toFixed(0)}/MWh (${sizingHrs}h Li-ion storage${sizingHrs >= 14 ? ', bridge-hours for overnight gap' : sizingHrs > 2 ? ', RKEF 24/7 sizing' : ''}).`,
        );
      if (row.lcoe_with_battery_usd_mwh)
        parts.push(`Solar + battery: $${row.lcoe_with_battery_usd_mwh.toFixed(1)}/MWh.`);
      return parts.join(' ');
    }
    case 'plan_late':
      return 'Over 60% of planned solar additions in this grid region slip past 2030. The RUPTL pipeline needs acceleration for this KEK to benefit.';
    case 'not_competitive': {
      const lcoe = row.lcoe_mid_usd_mwh;
      const gridCost = row.grid_cost_usd_mwh;
      if (lcoe != null && gridCost != null && lcoe <= gridCost) {
        return `Solar LCOE ($${lcoe.toFixed(1)}/MWh) is below grid cost ($${gridCost.toFixed(1)}/MWh), but solar resource quality (PVOUT ${row.pvout_best_50km_kwh_kwp_yr?.toFixed(0) ?? '?'} kWh/kWp/yr) is below the minimum threshold. The site lacks sufficient solar irradiance for a viable project.`;
      }
      return `Solar LCOE ($${lcoe?.toFixed(1)}/MWh) exceeds grid cost ($${gridCost?.toFixed(1)}/MWh) under current assumptions.`;
    }
    case 'no_solar_resource':
      return 'All land within the 50km search radius is protected forest, peatland, or otherwise unbuildable. There is no available area for solar development.';
    default:
      return '';
  }
}

const CAPACITY_COLORS: Record<string, string> = {
  green: '#4CAF50',
  yellow: '#FFC107',
  red: '#F44336',
  unknown: '#666',
};
const CAPACITY_LABELS: Record<string, string> = {
  green: 'Sufficient',
  yellow: 'Marginal',
  red: 'Upgrade needed',
  unknown: 'Unknown',
};

/* ---------- Tab 1: Overview (was Info) ---------- */

function OverviewTab({ row }: { row: ScorecardRow }) {
  const gapPct = row.solar_competitive_gap_pct;
  const gapColor = gapPct < 0 ? '#4CAF50' : gapPct > 0 ? '#EF5350' : '#e0e0e0';
  const gapSign = gapPct > 0 ? '+' : '';

  return (
    <>
      <StatCard>
        <SectionHeader title="KEK Identity" subtitle="Zone classification, size, and location" />
        <StatRowWithTip
          label="Type"
          value={row.kek_type ?? null}
          tip="Industrial KEKs have high baseload demand and strong transition incentives. Tourism KEKs have lighter loads."
        />
        <StatRowWithTip
          label="Category"
          value={row.category ?? null}
          tip="Established = operating with tenants. Proposed = may lack infrastructure. Under Construction = near-term opportunity."
        />
        <StatRowWithTip
          label="Area"
          value={
            row.area_ha != null
              ? row.area_ha.toLocaleString(undefined, { maximumFractionDigits: 0 })
              : null
          }
          unit="ha"
          tip="Larger KEKs have more space for on-site solar. >1,000 ha is significant."
        />
        <StatRow label="Province" value={row.province} />
        <StatRow label="Grid Region" value={formatGridRegion(row.grid_region_id)} />
      </StatCard>

      <EnergyBalanceChart row={row} />

      <StatCard>
        <SectionHeader
          title="At a Glance"
          subtitle="Is solar competitive here, and what's the gap?"
          tip="Key numbers that tell you whether solar makes sense here. Green gap = solar is cheaper than grid."
        />
        <StatRowWithTip
          label="Solar LCOE"
          value={row.lcoe_mid_usd_mwh?.toFixed(1)}
          unit="$/MWh"
          tip="Solar cost per MWh at current assumptions (10% WACC default). Compare to grid cost below."
        />
        <StatRowWithTip
          label="Grid Cost"
          value={row.grid_cost_usd_mwh?.toFixed(1)}
          unit="$/MWh"
          tip="PLN's cost to supply power here. If LCOE is lower, solar is already cheaper."
        />
        <ColoredStatRow
          label="Competitive Gap"
          value={`${gapSign}${gapPct.toFixed(1)}%`}
          color={gapColor}
          tip="Negative = solar beats grid. Positive = solar is more expensive. Below -10% is a strong case."
        />
        <StatRow label="Best RE" value={capitalize(row.best_re_technology)} />
        {row.grid_investment_needed_usd != null && (
          <ColoredStatRow
            label="Grid Investment"
            value={`$${(row.grid_investment_needed_usd / 1_000_000).toFixed(0)}M`}
            color={
              row.grid_investment_needed_usd / 1_000_000 > 500
                ? '#EF5350'
                : row.grid_investment_needed_usd / 1_000_000 > 100
                  ? '#FFC107'
                  : '#4CAF50'
            }
            tip="Total grid infrastructure cost: gen-tie + transmission + substation upgrade. Green (<$100M), yellow ($100-500M), red (>$500M)."
          />
        )}
        {row.solar_supply_coverage_pct != null && (
          <ColoredStatRow
            label="RE Coverage (Annual)"
            value={`${(row.solar_supply_coverage_pct * 100).toFixed(0)}%`}
            color={
              row.solar_supply_coverage_pct >= 1.0
                ? '#4CAF50'
                : row.solar_supply_coverage_pct >= 0.5
                  ? '#FFC107'
                  : '#F44336'
            }
            tip="Total annual solar generation / total annual demand. Does NOT account for day/night mismatch. See Firm Coverage below for physically grounded metric."
          />
        )}
        {row.bess_competitive != null &&
          row.battery_adder_usd_mwh != null &&
          row.battery_adder_usd_mwh > 0 && (
            <div
              className="mt-1 px-3 py-1.5 rounded-md text-[11px] font-medium"
              style={{
                background: row.bess_competitive ? 'rgba(76,175,80,0.12)' : 'rgba(239,83,80,0.12)',
                border: `1px solid ${row.bess_competitive ? 'rgba(76,175,80,0.25)' : 'rgba(239,83,80,0.25)'}`,
                color: row.bess_competitive ? '#4CAF50' : '#EF5350',
              }}
            >
              {row.bess_competitive
                ? `Solar+BESS beats grid ($${row.lcoe_with_battery_usd_mwh?.toFixed(0)}/MWh)`
                : `Solar+BESS exceeds grid (+$${row.battery_adder_usd_mwh?.toFixed(0)}/MWh storage)`}
            </div>
          )}
      </StatCard>

      {(row.demand_2030_gwh != null || row.captive_coal_count || row.nickel_smelter_count) && (
        <StatCard>
          <SectionHeader
            title="Demand Context"
            subtitle="Projected load and existing fossil infrastructure"
          />
          {row.demand_2030_gwh != null && (
            <StatRowWithTip
              label="Est. 2030 Demand"
              value={row.demand_2030_gwh.toFixed(1)}
              unit="GWh"
              tip="Projected from zone area x energy intensity. Provisional estimate, not actual metered demand."
            />
          )}
          {!!row.captive_coal_count && row.captive_coal_count > 0 && (
            <StatRowWithTip
              label="Captive Coal"
              value={
                row.captive_coal_mw != null
                  ? `${row.captive_coal_count} plants, ${row.captive_coal_mw.toLocaleString()} MW`
                  : `${row.captive_coal_count} plants`
              }
              tip="Existing coal plants within 50km. Subject to Perpres 112/2022 phase-out by 2050."
            />
          )}
          {!!row.nickel_smelter_count && row.nickel_smelter_count > 0 && (
            <StatRowWithTip
              label="Nickel Smelters"
              value={
                row.dominant_process_type
                  ? `${row.nickel_smelter_count} (${row.dominant_process_type})`
                  : `${row.nickel_smelter_count}`
              }
              tip="RKEF smelters run 24/7 baseload, doubling battery storage requirements from 2h to 4h."
            />
          )}
        </StatCard>
      )}

      {(row.developer || row.legal_basis) && (
        <StatCard>
          <SectionHeader title="Developer & Legal" subtitle="Zone operator and regulatory basis" />
          <StatRow label="Developer" value={row.developer ?? null} />
          <StatRow label="Legal Basis" value={row.legal_basis ?? null} />
        </StatCard>
      )}
    </>
  );
}

/* ---------- Tab 2: Solar (was Resource) ---------- */

function SolarTab({ row }: { row: ScorecardRow }) {
  const pvoutCentroid = row.pvout_centroid_kwh_kwp_yr;
  const pvoutBest = row.pvout_best_50km_kwh_kwp_yr;
  const cf =
    pvoutBest != null
      ? (pvoutBest / 8760).toFixed(3)
      : pvoutCentroid != null
        ? (pvoutCentroid / 8760).toFixed(3)
        : null;

  const wbLcoe = row.lcoe_within_boundary_usd_mwh;

  return (
    <>
      <StatCard>
        <SectionHeader
          title="Solar Resource Quality"
          subtitle="Is the sun strong enough to justify a project here?"
          tip="Higher PVOUT = more sun = cheaper solar. Above 1,400 kWh/kWp/yr is good for Indonesia."
        />
        <StatRowWithTip
          label="PVOUT Centroid"
          value={pvoutCentroid != null ? pvoutCentroid.toFixed(0) : null}
          unit="kWh/kWp/yr"
          tip="Solar yield at the KEK center. Used for on-site/within-boundary solar scenarios."
        />
        <StatRowWithTip
          label="PVOUT Best (50km)"
          value={pvoutBest != null ? pvoutBest.toFixed(0) : null}
          unit="kWh/kWp/yr"
          tip="Best solar yield on buildable land within 50km. Used for grid-connected scenarios. >1,500 is strong for Indonesia."
        />
        <StatRowWithTip
          label="Capacity Factor"
          value={cf}
          tip="Fraction of time solar produces at full power. 0.15-0.20 is typical for Indonesia. Higher = cheaper LCOE."
        />
        <StatRow label="Best RE" value={capitalize(row.best_re_technology)} />
      </StatCard>

      <StatCard>
        <SectionHeader
          title="Buildable Land"
          subtitle="How much suitable land exists after excluding forests, peat, and slopes?"
          tip="Land within 50km that passes slope, land cover, forest, and peatland filters."
        />
        <StatRowWithTip
          label="Buildable Area"
          value={row.buildable_area_ha != null ? row.buildable_area_ha.toFixed(0) : null}
          unit="ha"
          tip="Sum of suitable ~1km pixels within 50km. Actual contiguous sites for a solar farm may be smaller."
        />
        <StatRowWithTip
          label="Max Capacity"
          value={
            row.max_captive_capacity_mwp != null ? row.max_captive_capacity_mwp.toFixed(0) : null
          }
          unit="MWp"
          tip="MWp buildable at 5 ha/MWp density. This is the upper bound, not a recommended project size."
        />
        {row.buildable_area_ha != null &&
          row.buildable_area_ha > 0 &&
          row.buildable_area_ha < 2000 && (
            <div className="text-[10px] text-amber-400/70 leading-tight mt-1">
              Note: buildable area is the sum of suitable pixels within 50km at ~1km resolution.
              Actual contiguous land for a solar farm may be smaller.
            </div>
          )}
      </StatCard>

      <StatCard>
        <SectionHeader
          title="LCOE Breakdown"
          subtitle="What does solar electricity cost at different financing rates?"
          tip="Levelized Cost of Energy at three discount rates. Low = concessional finance, Mid = market rate, High = high-risk."
        />
        <StatRow label="LCOE Low (4%)" value={row.lcoe_low_usd_mwh?.toFixed(1)} unit="$/MWh" />
        <StatRowWithTip
          label="LCOE Mid (10%)"
          value={row.lcoe_mid_usd_mwh?.toFixed(1)}
          unit="$/MWh"
          tip="Cost at 10% WACC (market rate). This is the primary comparison number. Low=4% (concessional DFI), High=16% (high-risk)."
        />
        <StatRow label="LCOE High (16%)" value={row.lcoe_high_usd_mwh?.toFixed(1)} unit="$/MWh" />
        {wbLcoe != null && (
          <StatRowWithTip
            label="Within-Boundary"
            value={wbLcoe.toFixed(1)}
            unit="$/MWh"
            tip="LCOE for solar built inside the KEK boundary. No grid connection cost, but uses centroid PVOUT which may be lower than best 50km."
          />
        )}
      </StatCard>

      {row.max_captive_capacity_mwp != null && row.max_captive_capacity_mwp > 0 && (
        <LcoeCurveChart row={row} />
      )}
    </>
  );
}

/* ---------- Tab 3: Grid (was split across Pipeline + LCOE) ---------- */

function GridTab({
  row,
  substations,
  loadingSubs,
}: {
  row: ScorecardRow;
  substations: SubstationWithCosts[];
  loadingSubs: boolean;
}) {
  const assumptions = useDashboardStore((s) => s.assumptions);
  const setAssumptions = useDashboardStore((s) => s.setAssumptions);
  const sliderConfigs = useDashboardStore((s) => s.sliderConfigs);
  const utilizationConfig = sliderConfigs?.tier2?.substation_utilization_pct;
  const cap = row.capacity_assessment ?? 'unknown';
  const nearest = substations.find((s) => s.is_nearest);

  return (
    <>
      <StatCard>
        <SectionHeader
          title="Grid Integration"
          subtitle="Is existing infrastructure ready for solar, or does it need upgrades?"
          tip="How ready is the grid for solar at this KEK. Determines what investment is needed to connect."
        />
        <StatRowWithTip
          label="Category"
          value={formatSnakeLabel(row.grid_integration_category) ?? 'N/A'}
          tip="within_boundary = solar inside KEK. grid_ready = substation nearby. invest_transmission = build line from sub to KEK. invest_substation = build sub near solar. grid_first = major grid expansion needed."
        />
        <StatRowWithTip
          label="Grid Upgrade Planned"
          value={
            row.grid_upgrade_planned != null ? (row.grid_upgrade_planned ? 'Yes' : 'No') : 'N/A'
          }
          tip="Whether RUPTL includes grid capacity additions in this region before 2030. 'No' + competitive solar = 'grid_first' flag."
        />
        <StatRow label="Grid Region" value={formatGridRegion(row.grid_region_id)} />
      </StatCard>

      <StatCard>
        <SectionHeader
          title="Substation Proximity"
          subtitle="How far does power need to travel from solar site to KEK?"
        />
        {loadingSubs ? (
          <div className="text-[11px] py-2 text-center" style={{ color: 'var(--text-muted)' }}>
            Loading substations...
          </div>
        ) : nearest ? (
          <>
            <StatRow label="Nearest Sub" value={nearest.name} />
            <StatRow label="KEK-Sub Distance" value={nearest.dist_km.toFixed(1)} unit="km" />
          </>
        ) : (
          <StatRow label="Nearest Sub" value="N/A" />
        )}
        <StatRowWithTip
          label="Solar-Sub Distance"
          value={row.dist_solar_to_nearest_substation_km?.toFixed(1)}
          unit="km"
          tip="Distance from the best solar site to the nearest substation. Drives gen-tie connection cost ($5/kW per km + $80/kW fixed)."
        />
      </StatCard>

      <StatCard>
        <SectionHeader
          title="Grid Connectivity"
          subtitle="Is there an existing transmission path between key substations?"
          tip="Whether existing PLN transmission lines connect the substations near the KEK and the solar site."
        />
        <StatRowWithTip
          label="Transmission Line"
          value={row.line_connected != null ? (row.line_connected ? 'Connected' : 'None') : 'N/A'}
          tip="Whether a PLN transmission line geometrically connects the KEK-nearest and solar-nearest substations. 'None' means new line may be needed."
        />
        <StatRow
          label="Same PLN Region"
          value={row.same_grid_region != null ? (row.same_grid_region ? 'Yes' : 'No') : 'N/A'}
        />
        {row.inter_substation_dist_km != null && (
          <StatRowWithTip
            label="Inter-Sub Distance"
            value={row.inter_substation_dist_km.toFixed(1)}
            unit="km"
            tip="Distance between the KEK's nearest substation and the solar site's nearest substation. Drives new transmission line cost if not already connected."
          />
        )}
      </StatCard>

      {/* Substation capacity — slider + live traffic light */}
      {utilizationConfig && assumptions && (
        <StatCard>
          <SectionHeader
            title="Substation Capacity"
            subtitle="Can the local substation absorb new solar output without upgrades?"
            tip="Can the nearest substation handle the solar output? Green = sufficient headroom. Red = upgrade needed."
          />
          <Slider
            value={assumptions.substation_utilization_pct}
            onChange={(v) =>
              setAssumptions({ substation_utilization_pct: v } as Partial<UserAssumptions>)
            }
            min={utilizationConfig.min}
            max={utilizationConfig.max}
            step={utilizationConfig.step}
            label={utilizationConfig.label}
            unit={utilizationConfig.unit}
            description={utilizationConfig.description}
          />
          <div className="flex items-center gap-2 mt-1">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: CAPACITY_COLORS[cap] }}
            />
            <span className="text-xs" style={{ color: 'var(--text-value)' }}>
              {CAPACITY_LABELS[cap]}
            </span>
          </div>
          <StatRow
            label="Available Capacity"
            value={
              row.available_capacity_mva != null ? row.available_capacity_mva.toFixed(1) : 'N/A'
            }
            unit="MVA"
          />
          <div className="mt-1 text-[9px] text-[var(--text-muted)] leading-relaxed">
            Applies to all KEKs. Actual utilization requires PLN grid study.
          </div>
        </StatCard>
      )}

      {/* Connection costs */}
      {(row.connection_cost_per_kw != null ||
        row.transmission_cost_per_kw != null ||
        row.substation_upgrade_cost_per_kw != null ||
        row.grid_investment_needed_usd != null) && (
        <StatCard>
          <SectionHeader
            title="Connection Costs"
            subtitle="What does it cost to connect solar to the grid here?"
            tip="Estimated infrastructure cost to connect solar to the KEK. Scales with project capacity (MWp)."
          />
          {row.connection_cost_per_kw != null && (
            <StatRowWithTip
              label="Gen-Tie Cost"
              value={row.connection_cost_per_kw.toFixed(0)}
              unit="$/kW"
              tip="Cost to connect the solar farm to the nearest substation. Formula: distance x $5/kW-km + $80/kW fixed."
            />
          )}
          {row.transmission_cost_per_kw != null && row.transmission_cost_per_kw > 0 && (
            <StatRowWithTip
              label="New Line Cost"
              value={row.transmission_cost_per_kw.toFixed(0)}
              unit="$/kW"
              tip="Cost to build a new transmission line between substations. Only applies when KEK-nearest and solar-nearest substations are not already connected."
            />
          )}
          {row.substation_upgrade_cost_per_kw != null && row.substation_upgrade_cost_per_kw > 0 && (
            <StatRow
              label="Sub Upgrade Cost"
              value={row.substation_upgrade_cost_per_kw.toFixed(0)}
              unit="$/kW"
            />
          )}
          {row.grid_investment_needed_usd != null && (
            <StatRowWithTip
              label="Total Grid Investment"
              value={`$${(row.grid_investment_needed_usd / 1_000_000).toFixed(1)}M`}
              tip="Estimated total: gen-tie + new transmission line + substation upgrade. This is the infrastructure price tag for connecting solar to this KEK."
            />
          )}
        </StatCard>
      )}

      {/* M15: Multi-substation cost comparison */}
      {substations.length > 1 && <SubstationComparison substations={substations} />}
    </>
  );
}

/* ---------- Tab 4: Economics (was LCOE) ---------- */

function EconomicsTab({ row }: { row: ScorecardRow }) {
  const assumptions = useDashboardStore((s) => s.assumptions);
  const setAssumptions = useDashboardStore((s) => s.setAssumptions);
  const sliderConfigs = useDashboardStore((s) => s.sliderConfigs);
  const bessCapexConfig = sliderConfigs?.tier2?.bess_capex_usd_per_kwh;
  const bessSizingConfig = sliderConfigs?.tier2?.bess_sizing_hours_override;

  const gapTariffColor =
    row.gap_vs_tariff_pct != null ? (row.gap_vs_tariff_pct < 0 ? '#4CAF50' : '#EF5350') : undefined;
  const gapBppColor =
    row.gap_vs_bpp_pct != null ? (row.gap_vs_bpp_pct < 0 ? '#4CAF50' : '#EF5350') : undefined;

  const sizingHrs = row.bess_sizing_hours ?? 2;
  const bessCompetitive = row.bess_competitive ?? null;

  return (
    <>
      <StatCard>
        <SectionHeader
          title="Solar vs BPP"
          subtitle="Does solar save PLN money versus their actual cost of supply?"
          tip="Compares solar LCOE to PLN's true cost of supply. If solar beats BPP, PLN saves money buying solar. This is the IPP benchmark."
        />
        <StatRow label="Solar LCOE" value={row.lcoe_mid_usd_mwh?.toFixed(1)} unit="$/MWh" />
        <StatRowWithTip
          label="BPP"
          value={row.bpp_usd_mwh != null ? row.bpp_usd_mwh.toFixed(1) : null}
          unit="$/MWh"
          tip="Biaya Pokok Penyediaan — PLN's unsubsidized cost of supply. Unlike the tariff, BPP reflects true generation + transmission cost."
        />
        <ColoredStatRow
          label="Gap to BPP"
          value={
            row.gap_vs_bpp_pct != null
              ? `${row.gap_vs_bpp_pct > 0 ? '+' : ''}${row.gap_vs_bpp_pct.toFixed(1)}%`
              : null
          }
          color={gapBppColor}
        />
      </StatCard>

      <StatCard>
        <SectionHeader
          title="Solar vs Tariff"
          subtitle="Does solar beat what KEK tenants currently pay?"
          tip="Compares solar LCOE to the PLN industrial tariff. This is what a KEK tenant actually pays today."
        />
        <StatRowWithTip
          label="Tariff (I-4/TT)"
          value={row.dashboard_rate_usd_mwh?.toFixed(1)}
          unit="$/MWh"
          tip="PLN industrial tariff rate paid by KEK tenants. Often subsidized below PLN's actual cost (BPP). This is what a tenant actually pays today."
        />
        <ColoredStatRow
          label="Gap to Tariff"
          value={
            row.gap_vs_tariff_pct != null
              ? `${row.gap_vs_tariff_pct > 0 ? '+' : ''}${row.gap_vs_tariff_pct.toFixed(1)}%`
              : null
          }
          color={gapTariffColor}
        />
      </StatCard>

      {/* Battery storage impact — shown for all KEKs with solar resource */}
      {row.battery_adder_usd_mwh != null && row.battery_adder_usd_mwh > 0 && (
        <StatCard>
          <SectionHeader
            title="Battery Storage Impact"
            subtitle="What does 24/7 solar-only power cost with batteries?"
            tip="What happens to economics when you add Li-ion battery storage for reliability."
          />
          {assumptions && bessCapexConfig && (
            <Slider
              value={assumptions.bess_capex_usd_per_kwh}
              onChange={(v) =>
                setAssumptions({ bess_capex_usd_per_kwh: v } as Partial<UserAssumptions>)
              }
              min={bessCapexConfig.min}
              max={bessCapexConfig.max}
              step={bessCapexConfig.step}
              label={bessCapexConfig.label}
              unit={bessCapexConfig.unit}
              description={bessCapexConfig.description}
            />
          )}
          {assumptions && bessSizingConfig && (
            <div>
              <Slider
                value={assumptions.bess_sizing_hours_override ?? sizingHrs}
                onChange={(v) =>
                  setAssumptions({
                    bess_sizing_hours_override: v,
                  } as Partial<UserAssumptions>)
                }
                min={bessSizingConfig.min}
                max={bessSizingConfig.max}
                step={bessSizingConfig.step}
                label={bessSizingConfig.label}
                unit={bessSizingConfig.unit}
                description={bessSizingConfig.description}
              />
              {assumptions.bess_sizing_hours_override != null && (
                <button
                  type="button"
                  onClick={() =>
                    setAssumptions({
                      bess_sizing_hours_override: null,
                    } as Partial<UserAssumptions>)
                  }
                  className="text-[9px] px-1.5 py-0.5 rounded cursor-pointer mt-0.5"
                  style={{
                    color: 'var(--text-muted)',
                    border: '1px solid var(--border-subtle)',
                  }}
                >
                  Reset to auto ({sizingHrs}h)
                </button>
              )}
            </div>
          )}
          {row.battery_adder_usd_mwh != null && (
            <StatRowWithTip
              label="Battery Adder"
              value={`+$${row.battery_adder_usd_mwh.toFixed(0)}`}
              unit="/MWh"
              tip="Li-ion storage cost added to solar LCOE. Includes round-trip efficiency loss (87% RTE). Sizing determines the bulk of this cost."
            />
          )}
          {row.lcoe_with_battery_usd_mwh != null && (
            <StatRow
              label="Solar + Battery"
              value={row.lcoe_with_battery_usd_mwh.toFixed(1)}
              unit="$/MWh"
            />
          )}
          {bessCompetitive != null && (
            <ColoredStatRow
              label="Still Competitive"
              value={
                bessCompetitive
                  ? 'Yes'
                  : row.lcoe_with_battery_usd_mwh != null &&
                      row.grid_cost_usd_mwh != null &&
                      row.grid_cost_usd_mwh > 0
                    ? `No (+${(((row.lcoe_with_battery_usd_mwh - row.grid_cost_usd_mwh) / row.grid_cost_usd_mwh) * 100).toFixed(0)}%)`
                    : 'No'
              }
              color={bessCompetitive ? '#4CAF50' : '#EF5350'}
              tip="Whether solar + battery is still cheaper than grid cost. If yes, the project works even with storage."
            />
          )}
        </StatCard>
      )}

      <StatCard>
        <SectionHeader
          title="Carbon & Policy"
          subtitle="What carbon price or policy change tips the balance?"
          tip="Carbon economics and policy support metrics. Low carbon breakeven = strong decarbonization case."
        />
        <StatRowWithTip
          label="Carbon Breakeven"
          value={
            row.carbon_breakeven_usd_tco2 != null ? row.carbon_breakeven_usd_tco2.toFixed(1) : null
          }
          unit="$/tCO2"
          tip="Carbon price that makes solar cheaper than grid. Below $5 = strong case even without carbon markets. Above $50 = hard to justify on carbon alone."
        />
        <StatRowWithTip
          label="GEAS Green Share"
          value={row.green_share_geas != null ? `${(row.green_share_geas * 100).toFixed(1)}` : null}
          unit="%"
          tip="% of 2030 demand that GEAS-allocated solar could cover. GEAS and captive solar are substitutes — high share means strong policy support."
        />
      </StatCard>
    </>
  );
}

/* ---------- Tab 5: Demand ---------- */

function DemandTab({ row }: { row: ScorecardRow }) {
  const demand2030 = row.demand_2030_gwh;
  const solarGen = row.max_solar_generation_gwh;
  const coverage = row.solar_supply_coverage_pct;
  const wbGen = row.within_boundary_generation_gwh;
  const wbCoverage = row.within_boundary_coverage_pct;

  return (
    <>
      <StatCard>
        <SectionHeader
          title="Electricity Demand"
          subtitle="How much power does this KEK need by 2030?"
        />
        <StatRowWithTip
          label="2030 Demand Estimate"
          value={demand2030 != null ? demand2030.toFixed(1) : null}
          unit="GWh"
          tip="Estimated from zone area x energy intensity by KEK type. Provisional — actual metered demand not available."
        />
        <StatRowWithTip
          label="Max RE Generation (50km)"
          value={solarGen != null ? solarGen.toFixed(1) : null}
          unit="GWh/yr"
          tip="Annual GWh from max buildable solar within 50km at best PVOUT. Upper bound, not a project proposal."
        />
        <StatRowWithTip
          label="Within-Boundary Gen"
          value={wbGen != null ? wbGen.toFixed(1) : null}
          unit="GWh/yr"
          tip="GWh from solar built inside the KEK boundary only. Limited by KEK area and centroid PVOUT."
        />
      </StatCard>

      <StatCard>
        <SectionHeader
          title="Supply Coverage"
          subtitle="Can available solar generation meet the demand?"
        />
        <div className="space-y-3">
          <div>
            <div className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>
              RE Coverage (50km radius)
            </div>
            {coverage != null ? (
              <>
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="text-base font-semibold tabular-nums"
                    style={{
                      color: coverage >= 1.0 ? '#4CAF50' : coverage >= 0.5 ? '#FFC107' : '#F44336',
                    }}
                  >
                    {(coverage * 100).toFixed(0)}%
                  </span>
                  <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                    of annual demand (ignores day/night mismatch)
                  </span>
                </div>
                <div
                  className="w-full h-1.5 rounded-full overflow-hidden"
                  style={{ background: 'var(--bar-bg)' }}
                >
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(coverage * 100, 100)}%`,
                      backgroundColor:
                        coverage >= 1.0 ? '#4CAF50' : coverage >= 0.5 ? '#FFC107' : '#F44336',
                    }}
                  />
                </div>
              </>
            ) : (
              <div className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                Data unavailable
              </div>
            )}
          </div>
          <div>
            <div className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>
              Within-Boundary RE Coverage
            </div>
            {wbCoverage != null ? (
              <>
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="text-base font-semibold tabular-nums"
                    style={{
                      color:
                        wbCoverage >= 1.0 ? '#4CAF50' : wbCoverage >= 0.5 ? '#FFC107' : '#F44336',
                    }}
                  >
                    {(wbCoverage * 100).toFixed(0)}%
                  </span>
                  <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                    of demand coverable inside KEK
                  </span>
                </div>
                <div
                  className="w-full h-1.5 rounded-full overflow-hidden"
                  style={{ background: 'var(--bar-bg)' }}
                >
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(wbCoverage * 100, 100)}%`,
                      backgroundColor:
                        wbCoverage >= 1.0 ? '#4CAF50' : wbCoverage >= 0.5 ? '#FFC107' : '#F44336',
                    }}
                  />
                </div>
              </>
            ) : (
              <div className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                Data unavailable
              </div>
            )}
          </div>
          {row.firm_solar_coverage_pct != null && (
            <div>
              <div className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>
                Firm Coverage (Daytime Only)
              </div>
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="text-base font-semibold tabular-nums"
                  style={{
                    color:
                      row.firm_solar_coverage_pct >= 1.0
                        ? '#4CAF50'
                        : row.firm_solar_coverage_pct >= 0.5
                          ? '#FFC107'
                          : '#F44336',
                  }}
                >
                  {(row.firm_solar_coverage_pct * 100).toFixed(0)}%
                </span>
                <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                  of daytime demand coverable without storage
                </span>
              </div>
              <div
                className="w-full h-1.5 rounded-full overflow-hidden"
                style={{ background: 'var(--bar-bg)' }}
              >
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.min(row.firm_solar_coverage_pct * 100, 100)}%`,
                    backgroundColor:
                      row.firm_solar_coverage_pct >= 1.0
                        ? '#4CAF50'
                        : row.firm_solar_coverage_pct >= 0.5
                          ? '#FFC107'
                          : '#F44336',
                  }}
                />
              </div>
            </div>
          )}
        </div>
        {coverage != null && coverage < 1.0 && demand2030 != null && solarGen != null && (
          <div className="text-[9px] text-[var(--text-muted)] mt-2">
            Shortfall: {(demand2030 - solarGen).toFixed(1)} GWh/yr must come from grid or other
            generation
          </div>
        )}
      </StatCard>
      {row.storage_gap_pct != null && (
        <StatCard>
          <SectionHeader
            title="Temporal Reality"
            subtitle="How much demand falls at night when the sun isn't shining?"
            tip="Solar produces during ~10h of daylight. Industrial loads run 24h. This shows what needs battery storage."
          />
          <div>
            <div
              className="flex items-center justify-between text-[10px] mb-1"
              style={{ color: 'var(--text-muted)' }}
            >
              <span>Needs Storage (Nighttime)</span>
              <span className="font-semibold" style={{ color: '#FFC107' }}>
                {(row.storage_gap_pct * 100).toFixed(0)}%
              </span>
            </div>
            <div
              className="w-full h-1.5 rounded-full overflow-hidden"
              style={{ background: 'var(--bar-bg)' }}
            >
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.min(row.storage_gap_pct * 100, 100)}%`,
                  backgroundColor: '#FFC107',
                }}
              />
            </div>
            <div className="text-[9px] mt-1" style={{ color: 'var(--text-muted)' }}>
              ~58% of demand occurs at night when solar produces nothing. This energy must pass
              through battery storage (87% round-trip efficiency).
            </div>
          </div>
          {row.nighttime_demand_mwh != null && row.storage_required_mwh != null && (
            <div className="mt-2 flex flex-col gap-0.5">
              <StatRowWithTip
                label="Nighttime Demand"
                value={(row.nighttime_demand_mwh / 1000).toFixed(1)}
                unit="GWh/yr"
                tip="Annual electricity demand during non-solar hours (~14h/day). This is the energy that must be stored or sourced from the grid."
              />
              <StatRowWithTip
                label="Storage Throughput"
                value={(row.storage_required_mwh / 1000).toFixed(1)}
                unit="GWh/yr"
                tip="Total battery throughput needed per year to serve nighttime demand. Larger than nighttime demand because 13% is lost to round-trip efficiency (87% RTE)."
              />
            </div>
          )}
        </StatCard>
      )}

      {/* Captive Power Context */}
      {(row.captive_coal_count || row.nickel_smelter_count) && (
        <StatCard>
          <SectionHeader
            title="Captive Power"
            subtitle="What fossil generation exists nearby that solar could replace?"
            tip="Coal plants and nickel smelters within 50km. These are transition targets — existing fossil power that solar could displace."
          />
          {!!row.captive_coal_count && (
            <>
              <StatRow label="Coal Plants" value={row.captive_coal_count} />
              {row.captive_coal_mw != null && (
                <StatRow
                  label="Coal Capacity"
                  value={`${row.captive_coal_mw.toLocaleString()}`}
                  unit="MW"
                />
              )}
              {row.captive_coal_generation_gwh != null && (
                <StatRowWithTip
                  label="Coal Generation"
                  value={`${row.captive_coal_generation_gwh.toFixed(1)}`}
                  unit="GWh/yr"
                  tip="Estimated annual generation assuming 40% capacity factor x 8,760 hours. Industry standard for captive coal utilization."
                />
              )}
              {row.captive_coal_plants && (
                <div className="text-[10px] mt-1 mb-1" style={{ color: 'var(--text-muted)' }}>
                  {row.captive_coal_plants}
                </div>
              )}
            </>
          )}
          {!!row.captive_coal_count && !!row.nickel_smelter_count && (
            <div className="my-1" style={{ borderTop: '1px solid var(--border-subtle)' }} />
          )}
          {!!row.nickel_smelter_count && (
            <>
              <StatRow label="Nickel Smelters" value={row.nickel_smelter_count} />
              {row.dominant_process_type && (
                <StatRowWithTip
                  label="Process Type"
                  value={row.dominant_process_type}
                  tip="RKEF = Rotary Kiln Electric Furnace, runs 24/7 at high temperatures. Doubles battery sizing from 2h to 4h. Highest electricity intensity of all nickel processes."
                />
              )}
              {row.nickel_projects && (
                <div className="text-[10px] mt-1 mb-1" style={{ color: 'var(--text-muted)' }}>
                  {row.nickel_projects}
                </div>
              )}
              {row.has_chinese_ownership && (
                <StatRowWithTip
                  label="Chinese Ownership"
                  value="Present"
                  tip="Indicates Chinese-invested facilities nearby. Relevant for DFI due diligence and ESG screening. Source: CGSP Nickel Tracker."
                />
              )}
            </>
          )}
          {(row.solar_replacement_pct != null || row.perpres_112_status) && (
            <div className="mt-2 pt-2" style={{ borderTop: '1px solid var(--border-subtle)' }}>
              {row.solar_replacement_pct != null && (
                <ColoredStatRow
                  label="Solar Replacement"
                  value={`${row.solar_replacement_pct.toFixed(0)}%`}
                  color={
                    row.solar_replacement_pct >= 100
                      ? '#4CAF50'
                      : row.solar_replacement_pct >= 50
                        ? '#FFC107'
                        : '#F44336'
                  }
                  tip="What % of captive coal generation solar could replace. 100%+ (green) = full displacement possible. <50% (red) = supplementary generation needed."
                />
              )}
              {row.perpres_112_status && (
                <StatRowWithTip
                  label="Perpres 112/2022"
                  value={row.perpres_112_status}
                  tip="Presidential Regulation mandating captive coal phase-out by 2050. Creates regulatory urgency for transition. Plants post-2022 must cut emissions 35% within 10 years."
                />
              )}
            </div>
          )}
        </StatCard>
      )}
    </>
  );
}

/* ---------- Tab 6: Action (was Flags) ---------- */

function ActionTab({ row }: { row: ScorecardRow }) {
  const activeFlag = row.action_flag;
  const activeIdx = ACTION_FLAG_HIERARCHY.indexOf(activeFlag as ActionFlag);

  return (
    <>
      <StatCard>
        <SectionHeader
          title="Solar Readiness"
          subtitle="Where this KEK sits on the path from analysis to deployment"
          tip="Flags are ranked best to worst. The active flag (highlighted) is this KEK's primary action recommendation based on solar economics, grid readiness, and pipeline status."
        />
        {ACTION_FLAG_HIERARCHY.map((flag, i) => {
          const isActive = activeFlag === flag;
          const isAbove = activeIdx >= 0 && i < activeIdx;
          return (
            <FlagStep
              key={flag}
              label={ACTION_FLAG_LABELS[flag] ?? flag}
              color={ACTION_FLAG_COLORS[flag] ?? '#666'}
              active={isActive}
              above={isAbove}
              isFirst={i === 0}
              isLast={i === ACTION_FLAG_HIERARCHY.length - 1}
              explanation={isActive ? getFlagExplanation(flag, row) : undefined}
            />
          );
        })}
      </StatCard>
      <StatCard>
        <SectionHeader title="Key Numbers" subtitle="The metrics behind this recommendation" />
        <StatRowWithTip
          label="Grid Cost Proxy"
          value={row.grid_cost_usd_mwh?.toFixed(1)}
          unit="$/MWh"
          tip="The benchmark used for competitive gap calculation. Either BPP (cost of supply) or I-4/TT tariff, depending on your selected benchmark mode."
        />
        <StatRowWithTip
          label="BPP"
          value={row.bpp_usd_mwh != null ? row.bpp_usd_mwh.toFixed(1) : null}
          unit="$/MWh"
          tip="Biaya Pokok Penyediaan — PLN's unsubsidized cost of supply for this grid region."
        />
        <StatRowWithTip
          label="Project Viable"
          value={row.project_viable ? 'Yes' : 'No'}
          tip="Whether a solar project meets minimum thresholds: PVOUT above cutoff, buildable area exists, and capacity above minimum viable size."
        />
      </StatCard>

      {row.ruptl_region_summary && (
        <StatCard>
          <SectionHeader
            title="RUPTL Pipeline"
            subtitle="What grid and generation additions is PLN planning for this region?"
            tip="RUPTL = PLN's 10-year grid expansion plan. Shows planned generation additions by technology in this KEK's grid region."
          />
          <div className="text-[11px] leading-relaxed" style={{ color: 'var(--text-value)' }}>
            {row.ruptl_region_summary}
          </div>
        </StatCard>
      )}
    </>
  );
}

/* ---------- Main drawer ---------- */

const TABS = [
  { value: 'overview', label: 'Overview' },
  { value: 'solar', label: 'Solar' },
  { value: 'grid', label: 'Grid' },
  { value: 'economics', label: 'Economics' },
  { value: 'demand', label: 'Demand' },
  { value: 'action', label: 'Action' },
] as const;

export default function ScoreDrawer() {
  const selectedKek = useDashboardStore((s) => s.selectedKek);
  const drawerOpen = useDashboardStore((s) => s.drawerOpen);
  const scorecard = useDashboardStore((s) => s.scorecard);
  const closeDrawer = useDashboardStore((s) => s.closeDrawer);

  const [substations, setSubstations] = useState<SubstationWithCosts[]>([]);
  const [loadingSubs, setLoadingSubs] = useState(false);

  const row = scorecard?.find((r) => r.kek_id === selectedKek) ?? null;

  const handleClose = useCallback(() => {
    closeDrawer();
  }, [closeDrawer]);

  // Fetch substations when selected KEK changes
  useEffect(() => {
    if (!selectedKek) {
      setSubstations([]);
      return;
    }

    let cancelled = false;
    setLoadingSubs(true);

    fetchKekSubstations(selectedKek, 50)
      .then((data) => {
        if (!cancelled) {
          const parsed = data as { substations: SubstationWithCosts[] };
          setSubstations(parsed.substations ?? []);
        }
      })
      .catch(() => {
        if (!cancelled) setSubstations([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingSubs(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedKek]);

  // Keyboard escape to close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && drawerOpen) {
        handleClose();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [drawerOpen, handleClose]);

  const flagColor = row ? (ACTION_FLAG_COLORS[row.action_flag] ?? '#666') : '#666';
  const flagLabel = row ? (ACTION_FLAG_LABELS[row.action_flag] ?? row.action_flag) : '';
  const flagDescription = row ? getFlagExplanation(row.action_flag, row) : '';

  return (
    <div
      data-tour="drawer"
      className={`absolute top-0 right-0 z-30 h-full w-[380px] flex flex-col
                  transition-transform duration-300 ease-in-out ${
                    drawerOpen && row ? 'translate-x-0' : 'translate-x-full'
                  }`}
      style={{
        background: 'var(--glass-heavy)',
        backdropFilter: 'var(--blur-heavy)',
        WebkitBackdropFilter: 'var(--blur-heavy)',
        borderLeft: '1px solid var(--glass-border)',
        boxShadow: 'var(--drawer-shadow)',
      }}
    >
      {row && (
        <>
          {/* Header */}
          <div className="px-4 pt-4 pb-2">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h2
                  className="text-sm font-semibold truncate"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {row.kek_name}
                </h2>
                <div className="text-[11px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                  {row.province} &middot; {formatGridRegion(row.grid_region_id)}
                </div>
              </div>
              <button
                onClick={handleClose}
                className="p-1 rounded transition-colors"
                style={{ color: 'var(--text-muted)' }}
                aria-label="Close drawer"
              >
                <CloseIcon />
              </button>
            </div>

            {/* Action flag banner */}
            <div
              className="mt-3 px-3 py-2 rounded-md"
              style={{ background: `${flagColor}22`, border: `1px solid ${flagColor}44` }}
            >
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ background: flagColor }}
                />
                <span className="text-xs font-medium" style={{ color: flagColor }}>
                  {flagLabel}
                </span>
              </div>
              {flagDescription && (
                <p
                  className="text-[10px] mt-1 leading-relaxed pl-[18px]"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {flagDescription}
                </p>
              )}
            </div>
          </div>

          {/* Tabs */}
          <Tabs.Root defaultValue="overview" className="flex-1 flex flex-col min-h-0">
            <Tabs.List
              className="flex px-4 gap-0.5"
              style={{ borderBottom: '1px solid var(--border-subtle)' }}
            >
              {TABS.map((tab) => (
                <Tabs.Trigger
                  key={tab.value}
                  value={tab.value}
                  className="drawer-tab px-2.5 py-2 text-[11px] font-medium transition-colors relative
                             after:absolute after:bottom-0 after:left-1 after:right-1 after:h-[2px]
                             after:rounded-full after:opacity-0
                             data-[state=active]:after:opacity-100 after:transition-opacity"
                >
                  {tab.label}
                </Tabs.Trigger>
              ))}
            </Tabs.List>

            <div className="flex-1 overflow-y-auto px-4 py-3">
              <Tabs.Content value="overview">
                <OverviewTab row={row} />
              </Tabs.Content>
              <Tabs.Content value="solar">
                <SolarTab row={row} />
              </Tabs.Content>
              <Tabs.Content value="grid">
                <GridTab row={row} substations={substations} loadingSubs={loadingSubs} />
              </Tabs.Content>
              <Tabs.Content value="economics">
                <EconomicsTab row={row} />
              </Tabs.Content>
              <Tabs.Content value="demand">
                <DemandTab row={row} />
              </Tabs.Content>
              <Tabs.Content value="action">
                <ActionTab row={row} />
              </Tabs.Content>
            </div>
          </Tabs.Root>
        </>
      )}
    </div>
  );
}

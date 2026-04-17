import { capitalize, formatGridRegion } from '../../../lib/format';
import type { ScorecardRow } from '../../../lib/types';
import { useDashboardStore } from '../../../store/dashboard';
import EnergyBalanceChart from '../../charts/EnergyBalanceChart';
import { computeGapPct, formatGap } from './formatting';
import { IdentityCard } from './IdentityCard';
import { ColoredStatRow, SectionHeader, StatCard, StatRow, StatRowWithTip } from './StatComponents';

export function OverviewTab({ row }: { row: ScorecardRow }) {
  const energyMode = useDashboardStore((s) => s.energyMode);

  const activeLcoe =
    energyMode === 'wind'
      ? row.lcoe_wind_mid_usd_mwh
      : energyMode === 'hybrid'
        ? row.hybrid_allin_usd_mwh
        : energyMode === 'overall'
          ? row.best_re_lcoe_mid_usd_mwh
          : row.lcoe_mid_usd_mwh;

  const activeGap = computeGapPct(activeLcoe, row.grid_cost_usd_mwh);
  const gapPct = energyMode === 'solar' ? row.solar_competitive_gap_pct : activeGap;
  const gapColorVal =
    gapPct != null ? (gapPct < 0 ? '#4CAF50' : gapPct > 0 ? '#EF5350' : '#e0e0e0') : '#e0e0e0';

  const techLabel =
    energyMode === 'wind'
      ? 'Wind'
      : energyMode === 'hybrid'
        ? 'Hybrid'
        : energyMode === 'overall'
          ? capitalize(row.best_re_technology)
          : 'Solar';

  return (
    <>
      <IdentityCard row={row} />
      <StatCard>
        <SectionHeader title="Location & Grid" subtitle="Where the site sits on the PLN system" />
        <StatRow label="Province" value={row.province} />
        <StatRow label="Grid Region" value={formatGridRegion(row.grid_region_id)} />
      </StatCard>

      <EnergyBalanceChart row={row} energyMode={energyMode} />

      <StatCard>
        <SectionHeader
          title="At a Glance"
          subtitle={`Is ${techLabel.toLowerCase()} competitive here, and what's the gap?`}
          tip={`Key numbers that tell you whether ${techLabel.toLowerCase()} makes sense here. Green gap = RE is cheaper than grid.`}
        />
        <StatRowWithTip
          label={`${techLabel} LCOE`}
          value={activeLcoe?.toFixed(1)}
          unit="$/MWh"
          tip={`${techLabel} cost per MWh at current assumptions. Compare to grid cost below.`}
        />
        <StatRowWithTip
          label="Grid Cost"
          value={row.grid_cost_usd_mwh?.toFixed(1)}
          unit="$/MWh"
          tip="PLN's cost to supply power here. If LCOE is lower, RE is already cheaper."
        />
        {gapPct != null && (
          <ColoredStatRow
            label="Competitive Gap"
            value={formatGap(gapPct)}
            color={gapColorVal}
            tip="Negative = RE beats grid. Positive = RE is more expensive. Below -10% is a strong case."
          />
        )}
        <StatRow label="Best RE" value={capitalize(row.best_re_technology)} />
        {energyMode === 'overall' &&
          row.lcoe_mid_usd_mwh != null &&
          row.lcoe_wind_mid_usd_mwh != null && (
            <div className="text-[10px] mt-1" style={{ color: 'var(--text-muted)' }}>
              Solar: ${row.lcoe_mid_usd_mwh.toFixed(0)}/MWh &nbsp;|&nbsp; Wind: $
              {row.lcoe_wind_mid_usd_mwh.toFixed(0)}/MWh
            </div>
          )}
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
        {(() => {
          const covPct =
            energyMode === 'wind'
              ? row.wind_supply_coverage_pct
              : energyMode === 'hybrid'
                ? (row.hybrid_supply_coverage_pct ?? row.solar_supply_coverage_pct)
                : row.solar_supply_coverage_pct;
          const covLabel =
            energyMode === 'wind'
              ? 'Wind Coverage (Annual)'
              : energyMode === 'hybrid'
                ? 'Hybrid Coverage (Annual)'
                : 'RE Coverage (Annual)';
          const covTip =
            energyMode === 'hybrid'
              ? 'Combined solar+wind generation at optimal mix / total annual demand.'
              : energyMode === 'wind'
                ? 'Total annual wind generation / total annual demand.'
                : 'Total annual solar generation / total annual demand. Does NOT account for day/night mismatch.';
          return covPct != null ? (
            <ColoredStatRow
              label={covLabel}
              value={`${(covPct * 100).toFixed(0)}%`}
              color={covPct >= 1.0 ? '#4CAF50' : covPct >= 0.5 ? '#FFC107' : '#F44336'}
              tip={covTip}
            />
          ) : null;
        })()}
        {energyMode !== 'wind' &&
          row.bess_competitive != null &&
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

      {(row.demand_2030_gwh != null ||
        row.captive_coal_count ||
        row.nickel_smelter_count ||
        row.steel_plant_count ||
        row.cement_plant_count) && (
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
          {!!row.steel_plant_count && row.steel_plant_count > 0 && (
            <StatRowWithTip
              label="Steel Plants"
              value={
                row.steel_capacity_tpa
                  ? `${row.steel_plant_count}, ${(row.steel_capacity_tpa / 1e6).toFixed(1)}M tpa`
                  : `${row.steel_plant_count}`
              }
              tip="CBAM-exposed. BF-BOF has highest emissions. EAF is electricity-intensive (~37.5 MWh/t)."
            />
          )}
          {!!row.cement_plant_count && row.cement_plant_count > 0 && (
            <StatRowWithTip
              label="Cement Plants"
              value={
                row.cement_capacity_mtpa
                  ? `${row.cement_plant_count}, ${row.cement_capacity_mtpa.toFixed(1)} Mtpa`
                  : `${row.cement_plant_count}`
              }
              tip="CBAM-exposed. High process emissions (0.52 tCO₂/t from calcination)."
            />
          )}
          {row.cbam_exposed && (
            <ColoredStatRow
              label="EU CBAM"
              value={
                row.cbam_cost_2030_usd_per_tonne != null
                  ? `$${row.cbam_cost_2030_usd_per_tonne}/t (2030)`
                  : row.cbam_product_type
                    ? row.cbam_product_type
                        .split(',')
                        .map((t) => t.replace('_', '/'))
                        .join(', ')
                    : 'Exposed'
              }
              color="#FF7043"
              tip="EU Carbon Border Adjustment Mechanism. Covers iron/steel, aluminium, cement, and fertilizer exports. Carbon pricing escalates from ~€2/tCO₂ (2026) to full EU ETS price (~€80/tCO₂) by 2034."
            />
          )}
        </StatCard>
      )}
    </>
  );
}

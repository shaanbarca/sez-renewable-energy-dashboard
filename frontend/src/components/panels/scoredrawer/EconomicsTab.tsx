import { capitalize } from '../../../lib/format';
import type { ScorecardRow, UserAssumptions } from '../../../lib/types';
import { useDashboardStore } from '../../../store/dashboard';
import Slider from '../../ui/Slider';
import { computeGapPct, formatGap, gapColor } from './formatting';
import { ColoredStatRow, SectionHeader, StatCard, StatRow, StatRowWithTip } from './StatComponents';

export function EconomicsTab({ row }: { row: ScorecardRow }) {
  const assumptions = useDashboardStore((s) => s.assumptions);
  const setAssumptions = useDashboardStore((s) => s.setAssumptions);
  const sliderConfigs = useDashboardStore((s) => s.sliderConfigs);
  const energyMode = useDashboardStore((s) => s.energyMode);
  const bessCapexConfig = sliderConfigs?.tier2?.bess_capex_usd_per_kwh;
  const bessSizingConfig = sliderConfigs?.tier2?.bess_sizing_hours_override;

  const sizingHrs = row.bess_sizing_hours ?? 2;
  const bessCompetitive = row.bess_competitive ?? null;

  const activeLcoe =
    energyMode === 'wind'
      ? row.lcoe_wind_mid_usd_mwh
      : energyMode === 'hybrid'
        ? row.hybrid_allin_usd_mwh
        : energyMode === 'overall'
          ? row.best_re_lcoe_mid_usd_mwh
          : row.lcoe_mid_usd_mwh;

  const activeGapBpp =
    energyMode === 'solar' ? row.gap_vs_bpp_pct : computeGapPct(activeLcoe, row.bpp_usd_mwh);

  const activeGapTariff =
    energyMode === 'solar'
      ? row.gap_vs_tariff_pct
      : computeGapPct(activeLcoe, row.dashboard_rate_usd_mwh);

  const techLabel =
    energyMode === 'wind'
      ? 'Wind'
      : energyMode === 'hybrid'
        ? 'Hybrid'
        : energyMode === 'overall'
          ? capitalize(row.best_re_technology)
          : 'Solar';

  if (energyMode === 'wind' && row.lcoe_wind_mid_usd_mwh == null) {
    return (
      <StatCard>
        <SectionHeader title="Wind Economics" subtitle="Not available for this KEK" />
        <div className="text-[11px] leading-relaxed" style={{ color: 'var(--text-muted)' }}>
          Wind speed at this location ({row.wind_speed_ms?.toFixed(1) ?? '< 3'} m/s) is below the
          viable threshold. Wind LCOE cannot be computed.
        </div>
      </StatCard>
    );
  }

  return (
    <>
      <StatCard>
        <SectionHeader
          title={`${techLabel} vs BPP`}
          subtitle={`Does ${techLabel.toLowerCase()} save PLN money versus their actual cost of supply?`}
          tip={`Compares ${techLabel.toLowerCase()} LCOE to PLN's true cost of supply. If ${techLabel.toLowerCase()} beats BPP, PLN saves money. This is the IPP benchmark.`}
        />
        <StatRow label={`${techLabel} LCOE`} value={activeLcoe?.toFixed(1)} unit="$/MWh" />
        <StatRowWithTip
          label="BPP"
          value={row.bpp_usd_mwh != null ? row.bpp_usd_mwh.toFixed(1) : null}
          unit="$/MWh"
          tip="Biaya Pokok Penyediaan — PLN's unsubsidized cost of supply. Unlike the tariff, BPP reflects true generation + transmission cost."
        />
        <ColoredStatRow
          label="Gap to BPP"
          value={formatGap(activeGapBpp)}
          color={gapColor(activeGapBpp)}
        />
        {energyMode === 'overall' &&
          row.lcoe_mid_usd_mwh != null &&
          row.lcoe_wind_mid_usd_mwh != null && (
            <div
              className="text-[10px] mt-1.5 pt-1.5"
              style={{ color: 'var(--text-muted)', borderTop: '1px solid var(--border-subtle)' }}
            >
              Solar: ${row.lcoe_mid_usd_mwh.toFixed(0)}/MWh &nbsp;|&nbsp; Wind: $
              {row.lcoe_wind_mid_usd_mwh.toFixed(0)}/MWh
            </div>
          )}
      </StatCard>

      <StatCard>
        <SectionHeader
          title={`${techLabel} vs Tariff`}
          subtitle={`Does ${techLabel.toLowerCase()} beat what KEK tenants currently pay?`}
          tip={`Compares ${techLabel.toLowerCase()} LCOE to the PLN industrial tariff. This is what a KEK tenant actually pays today.`}
        />
        <StatRowWithTip
          label="Tariff (I-4/TT)"
          value={row.dashboard_rate_usd_mwh?.toFixed(1)}
          unit="$/MWh"
          tip="PLN industrial tariff rate paid by KEK tenants. Often subsidized below PLN's actual cost (BPP). This is what a tenant actually pays today."
        />
        <ColoredStatRow
          label="Gap to Tariff"
          value={formatGap(activeGapTariff)}
          color={gapColor(activeGapTariff)}
        />
      </StatCard>

      {energyMode !== 'wind' &&
        row.battery_adder_usd_mwh != null &&
        row.battery_adder_usd_mwh > 0 && (
          <StatCard>
            <SectionHeader
              title={energyMode === 'overall' ? 'Solar + Battery Impact' : 'Battery Storage Impact'}
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

      {energyMode === 'hybrid' && row.hybrid_allin_usd_mwh != null && (
        <StatCard>
          <SectionHeader
            title="Hybrid Storage Savings"
            subtitle="Wind fills the nighttime gap, cutting battery needs"
            tip="Combining solar and wind reduces battery storage because wind generates during solar's nighttime gap."
          />
          <StatRowWithTip
            label="Optimal Mix"
            value={
              row.hybrid_solar_share != null
                ? `${Math.round(row.hybrid_solar_share * 100)}% Solar / ${Math.round((1 - row.hybrid_solar_share) * 100)}% Wind`
                : null
            }
            tip="Auto-optimized capacity mix that minimizes total cost (LCOE + battery storage)."
          />
          <StatRowWithTip
            label="Blended LCOE"
            value={row.hybrid_lcoe_usd_mwh != null ? row.hybrid_lcoe_usd_mwh.toFixed(1) : null}
            unit="$/MWh"
            tip="Generation-weighted LCOE of the solar+wind blend (before battery)."
          />
          <StatRowWithTip
            label="Hybrid BESS"
            value={row.hybrid_bess_hours != null ? row.hybrid_bess_hours.toFixed(1) : null}
            unit="hours"
            tip={`Reduced from 14h (solar-only) to ${row.hybrid_bess_hours?.toFixed(1) ?? '?'}h because wind covers ${row.hybrid_nighttime_coverage_pct != null ? Math.round(row.hybrid_nighttime_coverage_pct * 100) : '?'}% of nighttime demand.`}
          />
          <StatRowWithTip
            label="BESS Adder"
            value={
              row.hybrid_bess_adder_usd_mwh != null
                ? `+$${row.hybrid_bess_adder_usd_mwh.toFixed(0)}`
                : null
            }
            unit="/MWh"
            tip="Battery cost at reduced hybrid sizing. Compare to solar-only BESS adder."
          />
          {row.hybrid_bess_reduction_pct != null && (
            <ColoredStatRow
              label="BESS Reduction"
              value={`${row.hybrid_bess_reduction_pct.toFixed(0)}%`}
              color="#4CAF50"
              tip="How much less battery storage is needed vs solar-only (14h bridge)."
            />
          )}
          <StatRow label="All-In LCOE" value={row.hybrid_allin_usd_mwh.toFixed(1)} unit="$/MWh" />
        </StatCard>
      )}

      <StatCard>
        <SectionHeader
          title="Carbon & Policy"
          subtitle="What carbon price or policy change tips the balance?"
          tip="Carbon economics and policy support metrics. Low carbon breakeven = strong decarbonization case."
        />
        {(energyMode === 'solar' || energyMode === 'overall') && (
          <StatRowWithTip
            label={energyMode === 'overall' ? 'Carbon Breakeven (Solar)' : 'Carbon Breakeven'}
            value={
              row.carbon_breakeven_usd_tco2 != null
                ? row.carbon_breakeven_usd_tco2.toFixed(1)
                : null
            }
            unit="$/tCO2"
            tip="Carbon price that makes solar cheaper than grid. Below $5 = strong case even without carbon markets. Above $50 = hard to justify on carbon alone."
          />
        )}
        {(energyMode === 'wind' || energyMode === 'overall') && (
          <StatRowWithTip
            label={energyMode === 'overall' ? 'Carbon Breakeven (Wind)' : 'Carbon Breakeven'}
            value={
              row.wind_carbon_breakeven_usd_tco2 != null
                ? row.wind_carbon_breakeven_usd_tco2.toFixed(1)
                : null
            }
            unit="$/tCO2"
            tip="Carbon price that makes wind cheaper than grid. Below $5 = strong case even without carbon markets. Above $50 = hard to justify on carbon alone."
          />
        )}
        {energyMode === 'hybrid' && (
          <StatRowWithTip
            label="Carbon Breakeven (Hybrid)"
            value={
              row.hybrid_carbon_breakeven_usd_tco2 != null
                ? row.hybrid_carbon_breakeven_usd_tco2.toFixed(1)
                : null
            }
            unit="$/tCO2"
            tip="Carbon price that makes the hybrid solar+wind+battery system cheaper than grid."
          />
        )}
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

import type { ScorecardRow } from '../../../lib/types';
import { useDashboardStore } from '../../../store/dashboard';
import CbamTrajectoryChart from '../../charts/CbamTrajectoryChart';
import { formatGap, gapColor } from './formatting';
import { ColoredStatRow, SectionHeader, StatCard, StatRow, StatRowWithTip } from './StatComponents';

export function DemandTab({ row }: { row: ScorecardRow }) {
  const energyMode = useDashboardStore((s) => s.energyMode);
  const demand2030 = row.demand_2030_gwh;
  const solarGen = row.max_solar_generation_gwh;
  const windGen = row.max_wind_generation_gwh;
  const showSolar = energyMode === 'solar' || energyMode === 'hybrid' || energyMode === 'overall';
  const showWind = energyMode === 'wind' || energyMode === 'hybrid' || energyMode === 'overall';

  const coverage =
    energyMode === 'wind'
      ? row.wind_supply_coverage_pct
      : energyMode === 'hybrid'
        ? row.hybrid_supply_coverage_pct
        : energyMode === 'overall'
          ? row.solar_supply_coverage_pct
          : row.solar_supply_coverage_pct;
  const wbGen = row.within_boundary_generation_gwh;
  const wbCoverage = row.within_boundary_coverage_pct;

  return (
    <>
      <StatCard>
        <SectionHeader
          title="Demand & Generation"
          subtitle="How much power does this KEK need, and can RE supply it?"
        />
        <StatRowWithTip
          label="2030 Demand Estimate"
          value={demand2030 != null ? demand2030.toFixed(1) : null}
          unit="GWh"
          tip="Estimated from zone area x energy intensity by KEK type. Provisional — actual metered demand not available."
        />
        {showSolar && (
          <StatRowWithTip
            label="Max Solar Gen (50km)"
            value={solarGen != null ? solarGen.toFixed(1) : null}
            unit="GWh/yr"
            tip="Annual GWh from max buildable solar within 50km at best PVOUT. Upper bound, not a project proposal."
          />
        )}
        {showWind && (
          <StatRowWithTip
            label="Max Wind Gen (50km)"
            value={windGen != null ? windGen.toFixed(1) : null}
            unit="GWh/yr"
            tip="Annual GWh from max buildable wind within 50km at best wind CF. Upper bound, not a project proposal."
          />
        )}
        {showSolar && (
          <StatRowWithTip
            label="Within-Boundary Gen"
            value={wbGen != null ? wbGen.toFixed(1) : null}
            unit="GWh/yr"
            tip="GWh from solar built inside the KEK boundary only. Limited by KEK area and centroid PVOUT."
          />
        )}
      </StatCard>

      {(row.captive_coal_count ||
        row.nickel_smelter_count ||
        row.steel_plant_count ||
        row.cement_plant_count) && (
        <StatCard>
          <SectionHeader
            title="Captive Power & CBAM Industries"
            subtitle="What fossil generation and CBAM-exposed industry exists nearby?"
            tip="Coal plants, nickel smelters, steel mills, and cement plants within 50km. These are transition targets and CBAM-exposed industries."
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
          {!!row.steel_plant_count && row.steel_plant_count > 0 && (
            <>
              {(!!row.captive_coal_count || !!row.nickel_smelter_count) && (
                <div className="my-1" style={{ borderTop: '1px solid var(--border-subtle)' }} />
              )}
              <StatRow label="Steel Plants" value={row.steel_plant_count} />
              {row.steel_capacity_tpa != null && (
                <StatRowWithTip
                  label="Steel Capacity"
                  value={`${(row.steel_capacity_tpa / 1e6).toFixed(1)}M`}
                  unit="tpa"
                  tip="CBAM-exposed. BF-BOF = blast furnace (highest emissions). EAF = electric arc furnace (lower emissions, high electricity intensity ~37.5 MWh/tonne)."
                />
              )}
              {row.steel_plants && (
                <div className="text-[10px] mt-1 mb-1" style={{ color: 'var(--text-muted)' }}>
                  {row.steel_plants}
                </div>
              )}
              {row.steel_has_chinese_ownership && (
                <StatRowWithTip
                  label="Chinese Ownership"
                  value="Present"
                  tip="Chinese-invested steel facilities nearby. Source: GEM Global Iron and Steel Plant Tracker."
                />
              )}
            </>
          )}
          {!!row.cement_plant_count && row.cement_plant_count > 0 && (
            <>
              {(!!row.captive_coal_count ||
                !!row.nickel_smelter_count ||
                !!row.steel_plant_count) && (
                <div className="my-1" style={{ borderTop: '1px solid var(--border-subtle)' }} />
              )}
              <StatRow label="Cement Plants" value={row.cement_plant_count} />
              {row.cement_capacity_mtpa != null && (
                <StatRowWithTip
                  label="Cement Capacity"
                  value={`${row.cement_capacity_mtpa.toFixed(1)}`}
                  unit="Mtpa"
                  tip="CBAM-exposed. Cement production has high process emissions (0.52 tCO2/tonne from calcination). Low electricity intensity but high scope 1."
                />
              )}
              {row.cement_plants && (
                <div className="text-[10px] mt-1 mb-1" style={{ color: 'var(--text-muted)' }}>
                  {row.cement_plants}
                </div>
              )}
              {row.cement_has_chinese_ownership && (
                <StatRowWithTip
                  label="Chinese Ownership"
                  value="Present"
                  tip="Chinese-invested cement facilities nearby. Source: GEM Global Cement Plant Tracker."
                />
              )}
            </>
          )}
          {(row.solar_replacement_pct != null || row.perpres_112_status || row.cbam_exposed) && (
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
              {row.cbam_exposed && (
                <>
                  <ColoredStatRow
                    label="EU CBAM Exposure"
                    value={
                      row.cbam_product_type
                        ? row.cbam_product_type
                            .split(',')
                            .map((t) => {
                              const labels: Record<string, string> = {
                                nickel_rkef: 'Nickel (RKEF)',
                                steel_eaf: 'Steel (EAF)',
                                steel_bfbof: 'Steel (BF-BOF)',
                                aluminium: 'Aluminium',
                                fertilizer: 'Fertilizer',
                                cement: 'Cement',
                              };
                              return labels[t] ?? t;
                            })
                            .join(', ')
                        : 'Exposed'
                    }
                    color="#FF7043"
                    tip="EU CBAM covers iron/steel (nickel RKEF, base metals), aluminium (bauxite processing), and fertilizer (petrochemical). Exports to EU face carbon border pricing from 2026, escalating to full EU ETS price by 2034."
                  />
                  {row.cbam_emission_intensity_current != null && (
                    <StatRowWithTip
                      label={`Emission Intensity${(row.cbam_product_type ?? '').includes(',') ? ` (${({ nickel_rkef: 'Nickel', steel_eaf: 'Steel EAF', steel_bfbof: 'Steel BF-BOF', aluminium: 'Aluminium', fertilizer: 'Fertilizer', cement: 'Cement' } as Record<string, string>)[(row.cbam_product_type ?? '').split(',')[0]] ?? (row.cbam_product_type ?? '').split(',')[0]})` : ''}`}
                      value={`${row.cbam_emission_intensity_current} tCO₂/t`}
                      tip={`Current: ${row.cbam_emission_intensity_current} tCO₂/tonne (grid electricity + process). With solar: ${row.cbam_emission_intensity_solar ?? '?'} tCO₂/tonne (process only, Scope 2 eliminated).${(row.cbam_product_type ?? '').includes(',') ? ' Showing primary product. See chart for per-product breakdown.' : ''}`}
                    />
                  )}
                  {row.cbam_cost_2030_usd_per_tonne != null && (
                    <StatRowWithTip
                      label="CBAM Cost 2030"
                      value={`$${row.cbam_cost_2030_usd_per_tonne?.toLocaleString()}/t`}
                      tip={`CBAM cost per tonne of product at 2030 rates (51.5% free allocation phased out). 2026: $${row.cbam_cost_2026_usd_per_tonne?.toLocaleString()}/t. 2034: $${row.cbam_cost_2034_usd_per_tonne?.toLocaleString()}/t (full exposure).`}
                    />
                  )}
                  {row.cbam_savings_2030_usd_per_tonne != null &&
                    row.cbam_savings_2030_usd_per_tonne > 0 && (
                      <ColoredStatRow
                        label="RE Savings 2030"
                        value={`$${row.cbam_savings_2030_usd_per_tonne.toLocaleString()}/t`}
                        color="#4CAF50"
                        tip={`CBAM cost avoided per tonne by switching to renewable energy (eliminates Scope 2 emissions). By 2034: $${row.cbam_savings_2034_usd_per_tonne?.toLocaleString()}/t saved. Switching to RE doesn't just lower energy cost, it removes the carbon border tax.`}
                      />
                    )}
                  {row.cbam_adjusted_gap_pct != null && (
                    <ColoredStatRow
                      label="CBAM-Adjusted Gap"
                      value={formatGap(row.cbam_adjusted_gap_pct)}
                      color={gapColor(row.cbam_adjusted_gap_pct)}
                      tip={`Standard gap: ${formatGap(row.solar_competitive_gap_pct)} (LCOE vs grid). CBAM saves $${row.cbam_savings_per_mwh?.toFixed(1)}/MWh (= $${row.cbam_savings_2030_usd_per_tonne?.toLocaleString()}/t ÷ ${({ nickel_rkef: '37.5', steel_eaf: '0.45', steel_bfbof: '0.25', aluminium: '15.0', fertilizer: '10.0', cement: '0.9' } as Record<string, string>)[(row.cbam_product_type ?? '').split(',')[0]] ?? '?'} MWh/t). Adjusted = (LCOE − grid − CBAM savings) / grid. At 2030 rates (51.5% free allocation phased out).`}
                    />
                  )}
                  {Number.isFinite(row.cbam_emission_intensity_current) && (
                    <CbamTrajectoryChart row={row} />
                  )}
                </>
              )}
            </div>
          )}
        </StatCard>
      )}

      <StatCard>
        <SectionHeader
          title={
            energyMode === 'wind'
              ? 'Supply Coverage (Wind)'
              : energyMode === 'overall'
                ? 'Supply Coverage'
                : 'Supply Coverage'
          }
          subtitle={
            energyMode === 'wind'
              ? 'Can available wind generation meet the demand?'
              : 'Can available RE generation meet the demand?'
          }
        />
        <div className="space-y-3">
          <div>
            <div className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>
              {energyMode === 'wind' ? 'Wind' : 'RE'} Coverage (50km radius)
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
                    of annual demand
                    {energyMode === 'wind'
                      ? ' (ignores intermittency)'
                      : ' (ignores day/night mismatch)'}
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
          {energyMode === 'overall' && row.wind_supply_coverage_pct != null && (
            <div>
              <div className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>
                Wind Coverage (50km radius)
              </div>
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="text-base font-semibold tabular-nums"
                  style={{
                    color:
                      row.wind_supply_coverage_pct >= 1.0
                        ? '#4CAF50'
                        : row.wind_supply_coverage_pct >= 0.5
                          ? '#FFC107'
                          : '#F44336',
                  }}
                >
                  {(row.wind_supply_coverage_pct * 100).toFixed(0)}%
                </span>
                <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                  of annual demand (wind only)
                </span>
              </div>
              <div
                className="w-full h-1.5 rounded-full overflow-hidden"
                style={{ background: 'var(--bar-bg)' }}
              >
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.min(row.wind_supply_coverage_pct * 100, 100)}%`,
                    backgroundColor:
                      row.wind_supply_coverage_pct >= 1.0
                        ? '#4CAF50'
                        : row.wind_supply_coverage_pct >= 0.5
                          ? '#FFC107'
                          : '#F44336',
                  }}
                />
              </div>
            </div>
          )}
          {showSolar && (
            <div>
              <div className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>
                Within-Boundary Solar Coverage
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
          )}
          {showSolar && row.firm_solar_coverage_pct != null && (
            <div>
              <div className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>
                Firm Solar Coverage (Daytime Only)
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
          {showWind && row.firm_wind_coverage_pct != null && (
            <div>
              <div className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>
                Firm Wind Coverage
              </div>
              <div className="flex items-center gap-2 mb-1">
                <span
                  className="text-base font-semibold tabular-nums"
                  style={{
                    color:
                      row.firm_wind_coverage_pct >= 1.0
                        ? '#4CAF50'
                        : row.firm_wind_coverage_pct >= 0.5
                          ? '#FFC107'
                          : '#F44336',
                  }}
                >
                  {(row.firm_wind_coverage_pct * 100).toFixed(0)}%
                </span>
                <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
                  of demand (variable output, ~{row.wind_firming_hours ?? 3}h firming gaps)
                </span>
              </div>
              <div
                className="w-full h-1.5 rounded-full overflow-hidden"
                style={{ background: 'var(--bar-bg)' }}
              >
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.min(row.firm_wind_coverage_pct * 100, 100)}%`,
                    backgroundColor:
                      row.firm_wind_coverage_pct >= 1.0
                        ? '#4CAF50'
                        : row.firm_wind_coverage_pct >= 0.5
                          ? '#FFC107'
                          : '#F44336',
                  }}
                />
              </div>
            </div>
          )}
        </div>
        {showSolar &&
          coverage != null &&
          coverage < 1.0 &&
          demand2030 != null &&
          solarGen != null && (
            <div className="text-[9px] text-[var(--text-muted)] mt-2">
              Solar shortfall: {(demand2030 - solarGen).toFixed(1)} GWh/yr must come from grid or
              other generation
            </div>
          )}
        {showWind && windGen != null && demand2030 != null && windGen < demand2030 && (
          <div className="text-[9px] text-[var(--text-muted)] mt-2">
            Wind shortfall: {(demand2030 - windGen).toFixed(1)} GWh/yr must come from grid or other
            generation
          </div>
        )}
      </StatCard>
      {row.storage_gap_pct != null && showSolar && (
        <StatCard>
          <SectionHeader
            title={energyMode === 'overall' ? 'Temporal Reality (Solar)' : 'Temporal Reality'}
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
      {showWind && row.wind_firming_gap_pct != null && (
        <StatCard>
          <SectionHeader
            title={energyMode === 'overall' ? 'Temporal Reality (Wind)' : 'Wind Intermittency'}
            subtitle="How much output is lost to wind variability?"
            tip="Wind produces ~24/7 but at variable output. Unlike solar's 14h overnight gap, wind gaps are shorter (2-4h) but less predictable."
          />
          <div>
            <div
              className="flex items-center justify-between text-[10px] mb-1"
              style={{ color: 'var(--text-muted)' }}
            >
              <span>Needs Firming (Intermittency)</span>
              <span className="font-semibold" style={{ color: '#81D4FA' }}>
                {(row.wind_firming_gap_pct * 100).toFixed(0)}%
              </span>
            </div>
            <div
              className="w-full h-1.5 rounded-full overflow-hidden"
              style={{ background: 'var(--bar-bg)' }}
            >
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.min(row.wind_firming_gap_pct * 100, 100)}%`,
                  backgroundColor: '#81D4FA',
                }}
              />
            </div>
            <div className="text-[9px] mt-1" style={{ color: 'var(--text-muted)' }}>
              Wind output drops to near-zero ~{(row.wind_firming_gap_pct * 100).toFixed(0)}% of
              hours. Firming gaps are typically ~{row.wind_firming_hours ?? 3}h (vs solar's 14h
              overnight gap), requiring smaller BESS or grid backup.
            </div>
          </div>
        </StatCard>
      )}
    </>
  );
}

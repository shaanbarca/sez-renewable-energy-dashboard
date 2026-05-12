import { capitalize } from '../../../lib/format';
import type { ScorecardRow, UserAssumptions } from '../../../lib/types';
import { useDashboardStore } from '../../../store/dashboard';
import LcoeCurveChart from '../../charts/LcoeCurveChart';
import Slider from '../../ui/Slider';
import { SectionHeader, StatCard, StatRow, StatRowWithTip } from './StatComponents';

export function ResourceTab({ row }: { row: ScorecardRow }) {
  const energyMode = useDashboardStore((s) => s.energyMode);
  const assumptions = useDashboardStore((s) => s.assumptions);
  const setAssumptions = useDashboardStore((s) => s.setAssumptions);
  const pvoutCentroid = row.pvout_centroid_kwh_kwp_yr;
  const pvoutBest = row.pvout_best_50km_kwh_kwp_yr;
  const solarCf =
    pvoutBest != null
      ? (pvoutBest / 8760).toFixed(3)
      : pvoutCentroid != null
        ? (pvoutCentroid / 8760).toFixed(3)
        : null;

  const wbLcoe = row.lcoe_within_boundary_usd_mwh;
  const showSolar = energyMode === 'solar' || energyMode === 'hybrid' || energyMode === 'overall';
  const showWind = energyMode === 'wind' || energyMode === 'hybrid' || energyMode === 'overall';

  // Captive Solar buildout-availability haircut. Raw raster picks every vacant
  // pixel inside the fence; in reality factories + roads + buffers eat most of
  // it. User-adjustable assumed share. Default 20% (matches the
  // wb_buildout_footprint_ratio that already gates grid integration).
  const buildoutPct = assumptions?.wb_buildout_footprint_ratio ?? 0.2;
  const rooftopDensity = assumptions?.rooftop_layout_density ?? 0.5;
  const rooftopPanelPower = assumptions?.rooftop_panel_power_w_dc ?? 400;
  const rooftopPanelArea = assumptions?.rooftop_panel_area_m2 ?? 2;

  // Client-side rooftop MWp mirror of scorecard.py:348-353. Keeps the Rooftop
  // Layout density slider feeling instant alongside the captive (ground-mount)
  // slider — server still recomputes rooftop_solar_mwp_potential for RankedTable
  // / RooftopPotentialTable consistency. If the formula evolves, update both sides.
  const rooftopMwpClient = (() => {
    const u = row.usable_roof_area_m2;
    if (u == null || !Number.isFinite(u) || rooftopPanelArea <= 0) return null;
    const m = (u * rooftopDensity * (rooftopPanelPower / rooftopPanelArea)) / 1_000_000;
    return Number.isFinite(m) ? m : null;
  })();

  // v4.0.5 (methodology #40): client-side override math. Mirrors
  // src/dash/logic/grid.py:112 + src/dash/logic/scorecard.py for instant
  // slider feedback (server still recomputes effective coverage for the
  // within_boundary gate + cost cascade on the 300ms refetch). Server
  // outputs `within_boundary_*_mwp` / `within_boundary_*_gwh` /
  // `within_boundary_coverage_pct` as raster BASELINE; the slider value
  // (`wb_buildout_footprint_ratio` = "Land-use override %") interpolates
  // between baseline and the new hard_max columns:
  //
  //   deployable = baseline + (hard_max - baseline) × slider%
  //
  // At slider=0% deployable = baseline (strict raster); at slider=100%
  // deployable = hard_max (override all soft-zoning exclusions; only
  // physical/legal constraints remain). Default 20% = mild owner override.
  //
  // Fallback (no hard_max signal yet, e.g. pre-pipeline-rerun): treat as
  // soft_excluded = 0 so display falls back to baseline. Matches the
  // graceful pre-regen behavior in src/dash/logic/grid.py.
  const baselineCapacity = row.within_boundary_capacity_mwp;
  const baselineArea = row.within_boundary_area_ha;
  const baselineGen = row.within_boundary_generation_gwh;
  const baselineCoverage = row.within_boundary_coverage_pct;
  const hardMaxCapacity = row.within_boundary_capacity_hard_max_mwp;
  const hardMaxArea = row.within_boundary_hard_max_ha;

  const softExcludedCapacity =
    baselineCapacity != null && hardMaxCapacity != null
      ? Math.max(0, hardMaxCapacity - baselineCapacity)
      : 0;
  const softExcludedArea =
    baselineArea != null && hardMaxArea != null ? Math.max(0, hardMaxArea - baselineArea) : 0;
  // soft_excluded_gen = (hard_max_capacity - baseline_capacity) × pvout / 1000
  // — derive from capacity × pvout ratio so we don't need a separate
  // hard_max_generation column on the row. Mirrors the methodology decision
  // to reuse baseline PVOUT for the override portion (sub-5% in-polygon
  // variation at 1km Indonesian resolution).
  const softExcludedGenRatio =
    baselineCapacity != null && baselineCapacity > 0 ? softExcludedCapacity / baselineCapacity : 0;
  const softExcludedGen = baselineGen != null ? baselineGen * softExcludedGenRatio : 0;
  const softExcludedCoverage =
    baselineCoverage != null ? baselineCoverage * softExcludedGenRatio : 0;

  const adjustedCapacity =
    baselineCapacity != null ? baselineCapacity + softExcludedCapacity * buildoutPct : null;
  const adjustedArea = baselineArea != null ? baselineArea + softExcludedArea * buildoutPct : null;
  const adjustedGen = baselineGen != null ? baselineGen + softExcludedGen * buildoutPct : null;
  const adjustedCoverage =
    baselineCoverage != null ? baselineCoverage + softExcludedCoverage * buildoutPct : null;

  // Composition flags for the merged Captive Solar card subsections.
  const hasRooftop = row.rooftop_solar_mwp_potential != null;
  // v4.0.5 (methodology #40): "has ground potential" includes hard_max so the
  // slider stays visible at industrial sites where the strict 4-layer raster
  // returns 0 (e.g., fully-built Palu / Tanjung Sauh / Maloy Batuta polygons).
  // Those sites have meaningful hard_max — the slider lets the user override
  // soft-zoning exclusions back into deployable area. Pre-fix the slider was
  // hidden unless baseline > 0, defeating the whole point of the methodology
  // change at the sites it was designed to fix.
  const hasGround =
    (row.within_boundary_capacity_mwp != null && row.within_boundary_capacity_mwp > 0) ||
    (row.within_boundary_capacity_hard_max_mwp != null &&
      row.within_boundary_capacity_hard_max_mwp > 0);
  const totalCaptiveMwp =
    hasRooftop && hasGround && rooftopMwpClient != null && adjustedCapacity != null
      ? rooftopMwpClient + adjustedCapacity
      : hasRooftop && rooftopMwpClient != null
        ? rooftopMwpClient
        : hasGround && adjustedCapacity != null
          ? adjustedCapacity
          : null;
  const totalCompositionLabel =
    hasRooftop && hasGround
      ? 'Captive MWp (rooftop + ground)'
      : hasRooftop
        ? 'Captive MWp (rooftop only)'
        : 'Captive MWp (ground only)';

  return (
    <>
      {showSolar && (
        <StatCard>
          <SectionHeader
            title="Solar Resource"
            subtitle="Is the sun strong enough to justify a project here?"
            tip="Higher PVOUT = more sun = cheaper solar. Above 1,400 kWh/kWp/yr is good for Indonesia."
          />
          <StatRowWithTip
            label="PVOUT Centroid"
            value={pvoutCentroid != null ? pvoutCentroid.toFixed(0) : null}
            unit="kWh/kWp/yr"
            tip="Solar yield at the site center. Used for on-site/within-boundary solar scenarios."
          />
          <StatRowWithTip
            label="PVOUT Best (50km)"
            value={pvoutBest != null ? pvoutBest.toFixed(0) : null}
            unit="kWh/kWp/yr"
            tip="Best solar yield on buildable land within 50km. Used for grid-connected scenarios. >1,500 is strong for Indonesia."
          />
          <StatRowWithTip
            label="Capacity Factor"
            value={solarCf}
            tip="Fraction of time solar produces at full power. 0.15-0.20 is typical for Indonesia. Higher = cheaper LCOE."
          />
        </StatCard>
      )}

      {showWind && (
        <StatCard>
          <SectionHeader
            title="Wind Resource"
            subtitle="Is wind viable at this location?"
            tip="Wind speed at 100m hub height from Global Wind Atlas v3. Above 6 m/s is marginal, above 7.5 m/s is good."
          />
          <StatRowWithTip
            label="Wind Speed"
            value={row.wind_speed_ms != null ? row.wind_speed_ms.toFixed(1) : null}
            unit="m/s"
            tip="Mean annual wind speed at 100m hub height (Global Wind Atlas v3). Best within 50km radius."
          />
          <StatRowWithTip
            label="Wind CF"
            value={row.cf_wind != null ? row.cf_wind.toFixed(3) : null}
            tip="Wind capacity factor. 0.20-0.30 is typical for good Indonesian sites (IEC Class III low-wind turbines)."
          />
          <StatRowWithTip
            label="Wind LCOE"
            value={row.lcoe_wind_mid_usd_mwh != null ? row.lcoe_wind_mid_usd_mwh.toFixed(1) : null}
            unit="$/MWh"
            tip="Wind LCOE at 10% WACC. CAPEX $1,650/kW (ESDM 2024), FOM $40/kW-yr, 27yr lifetime."
          />
        </StatCard>
      )}

      <StatCard>
        <SectionHeader
          title={energyMode === 'wind' ? 'Technology Comparison' : 'Best RE Technology'}
          subtitle="Which renewable source is cheapest at this site?"
        />
        <StatRow label="Best RE" value={capitalize(row.best_re_technology)} />
        {row.best_re_lcoe_mid_usd_mwh != null && (
          <StatRow
            label="Best RE LCOE"
            value={row.best_re_lcoe_mid_usd_mwh.toFixed(1)}
            unit="$/MWh"
          />
        )}
        {row.lcoe_mid_usd_mwh != null && row.lcoe_wind_mid_usd_mwh != null && (
          <StatRowWithTip
            label="Solar vs Wind"
            value={`$${row.lcoe_mid_usd_mwh.toFixed(0)} vs $${row.lcoe_wind_mid_usd_mwh.toFixed(0)}`}
            unit="$/MWh"
            tip="Solar LCOE (grid-connected, 10% WACC) vs Wind LCOE (10% WACC). Lower wins."
          />
        )}
      </StatCard>

      {showSolar && (hasRooftop || hasGround) && (
        <StatCard>
          <SectionHeader
            title="Captive Solar (on-site)"
            subtitle="On-site solar potential — rooftop + ground-mounted, adjusted via land-use override slider."
            tip="Decomposes into Rooftop (on existing buildings, §14 classifier × layout density) and Ground-mounted (4-layer raster baseline + the Land-use override slider, which lets you treat fraction of soft-excluded land — currently zoned built-up or agricultural — as deployable). Total mixes cost tiers (rooftop ≈ 5× $/MWp vs ground utility-scale)."
          />

          <div
            className="text-[10px] uppercase tracking-wider mt-2 mb-1"
            style={{ color: 'var(--text-muted)' }}
          >
            Rooftop
          </div>
          {hasRooftop ? (
            <>
              <div style={{ marginBottom: 6 }}>
                <Slider
                  label="Layout density"
                  description={`Fraction of usable roof covered by panels after spacing for shading, walkways, and equipment. Default 0.50 is industrial (NREL TP-6A20-65298); bifacials/utility-scale push higher.`}
                  min={0.4}
                  max={0.65}
                  step={0.05}
                  value={rooftopDensity}
                  onChange={(v) =>
                    setAssumptions({ rooftop_layout_density: v } as Partial<UserAssumptions>)
                  }
                />
              </div>
              <StatRowWithTip
                label="Rooftop MWp"
                value={
                  rooftopMwpClient != null
                    ? rooftopMwpClient.toFixed(1)
                    : row.rooftop_solar_mwp_potential != null
                      ? row.rooftop_solar_mwp_potential.toFixed(1)
                      : null
                }
                unit="MWp DC"
                tip={`§14 classifier × ${(rooftopDensity * 100).toFixed(0)}% layout density × panel power. Computed client-side for instant slider feedback; server recomputes for the Ranked Table. Includes standard + soft-derated rooftops.`}
              />
              <StatRow
                label="Standard rooftops"
                value={
                  row.building_count_standard_roof != null
                    ? row.building_count_standard_roof.toLocaleString()
                    : null
                }
                unit={
                  row.building_count_other_excluded != null && row.building_count_other_excluded > 0
                    ? `(${row.building_count_other_excluded.toLocaleString()} excluded)`
                    : ''
                }
              />
              {row.usable_roof_area_m2 != null && row.usable_roof_area_m2 > 0 && (
                <StatRowWithTip
                  label="Usable roof area"
                  value={(row.usable_roof_area_m2 / 10_000).toFixed(1)}
                  unit="ha"
                  tip="Building footprint × usability multiplier from the §14 classifier (1.0 for standard rooftops, derated for elongated / complex / round shapes)."
                />
              )}
              {row.building_data_confidence && (
                <StatRowWithTip
                  label="Data confidence"
                  value={row.building_data_confidence}
                  unit=""
                  tip={`Derived from building count + footprint ratio + imagery vintage. Source: ${row.building_data_source ?? 'gob_v3'} (vintage ${row.building_data_vintage ?? '2023-05'}).`}
                />
              )}
            </>
          ) : (
            <div className="text-xs italic py-1" style={{ color: 'var(--text-muted)' }}>
              {row.building_data_reason_flagged
                ? `No rooftop data — ${row.building_data_reason_flagged.replace(/_/g, ' ')}`
                : 'No buildings detected in 2km buffer'}
            </div>
          )}

          <div
            className="text-[10px] uppercase tracking-wider mt-3 mb-1"
            style={{ color: 'var(--text-muted)' }}
          >
            Ground-mounted
          </div>
          {hasGround ? (
            <>
              {(row.polygon_source_tier === 'none' ||
                row.polygon_source_tier === 'claude_building_hull_estimate') && (
                <div
                  className="text-xs italic py-1 px-2 mb-2 rounded"
                  style={{
                    background: 'rgba(245, 158, 11, 0.10)',
                    color: 'var(--text-muted)',
                    border: '1px solid rgba(245, 158, 11, 0.30)',
                  }}
                >
                  ⚠{' '}
                  {row.polygon_source_tier === 'none'
                    ? 'Low-trust: no fence-line polygon — using a 2 km centroid buffer. Likely over-counts adjacent land in dense corridors. See Polygon source below.'
                    : 'Low-trust: polygon estimated from detected buildings — fence boundary not independently verified. See Polygon source below.'}
                </div>
              )}
              <div style={{ marginBottom: 6 }}>
                <Slider
                  label="Land-use override % (global)"
                  description={`Fraction of soft-excluded land (zoned built-up / agricultural inside the fence) the site owner overrides. At 0% the strict 4-layer raster is the floor (${baselineCapacity?.toFixed(1) ?? '—'} MWp); at 100% all soft exclusions are overridden (hard_max ${hardMaxCapacity?.toFixed(1) ?? baselineCapacity?.toFixed(1) ?? '—'} MWp). Synced with the Grid tab + Advanced Assumptions sliders.`}
                  min={0.0}
                  max={1.0}
                  step={0.05}
                  value={buildoutPct}
                  onChange={(v) =>
                    setAssumptions({ wb_buildout_footprint_ratio: v } as Partial<UserAssumptions>)
                  }
                />
              </div>
              <StatRowWithTip
                label="Captive Capacity"
                value={adjustedCapacity != null ? adjustedCapacity.toFixed(1) : null}
                unit="MWp"
                tip={`Baseline (raster) ${baselineCapacity?.toFixed(1) ?? '—'} MWp + ${(buildoutPct * 100).toFixed(0)}% × ${softExcludedCapacity.toFixed(1)} MWp soft-excluded override. Hard-max ceiling is ${hardMaxCapacity?.toFixed(1) ?? baselineCapacity?.toFixed(1) ?? '—'} MWp (slider = 100%).`}
              />
              <StatRowWithTip
                label="Available Area"
                value={adjustedArea != null ? adjustedArea.toFixed(0) : null}
                unit="ha"
                tip={`Baseline ${baselineArea?.toFixed(0) ?? '—'} ha + ${(buildoutPct * 100).toFixed(0)}% × ${softExcludedArea.toFixed(0)} ha soft-excluded override. Hard-max is ${hardMaxArea?.toFixed(0) ?? baselineArea?.toFixed(0) ?? '—'} ha.`}
              />
              {row.within_boundary_avg_pvout != null && (
                <StatRowWithTip
                  label="Avg PVOUT"
                  value={row.within_boundary_avg_pvout.toFixed(0)}
                  unit="kWh/kWp/yr"
                  tip="Mean solar resource over the buildable polygons inside the fence. Doesn't change with the slider. Soft-excluded override reuses this PVOUT (sub-5% in-polygon variation at 1km resolution)."
                />
              )}
              {adjustedGen != null && (
                <StatRowWithTip
                  label="Annual Generation"
                  value={adjustedGen.toFixed(0)}
                  unit="GWh/yr"
                  tip={`Adjusted Capacity × Avg PVOUT. Baseline = ${baselineGen?.toFixed(0) ?? '—'} GWh/yr; hard-max ceiling ${(baselineGen != null && softExcludedGenRatio > 0 ? baselineGen * (1 + softExcludedGenRatio) : (baselineGen ?? 0)).toFixed(0)} GWh/yr at slider = 100%.`}
                />
              )}
              {adjustedCoverage != null && (
                <StatRowWithTip
                  label="Demand Coverage"
                  value={(adjustedCoverage * 100).toFixed(0)}
                  unit="%"
                  tip="Captive solar generation as a fraction of the site's 2030 demand. >100% means on-site solar over-produces vs the load. Drives the within_boundary self-sufficiency gate in the Grid tab."
                />
              )}
            </>
          ) : (
            <div className="text-xs italic py-1" style={{ color: 'var(--text-muted)' }}>
              {row.polygon_source_tier === 'none' || row.polygon_source_tier == null
                ? 'No buildable land within 2 km centroid buffer (entire buffer excluded by slope, peat, Kawasan Hutan, or buildability data coverage gap). Hunt a real fence-line polygon to refine.'
                : 'No buildable area within fence (entire polygon excluded by slope, peat, or Kawasan Hutan).'}
            </div>
          )}

          {totalCaptiveMwp != null && (
            <>
              <div
                className="text-[10px] uppercase tracking-wider mt-3 mb-1"
                style={{ color: 'var(--text-muted)' }}
              >
                Total
              </div>
              <StatRowWithTip
                label={totalCompositionLabel}
                value={totalCaptiveMwp.toFixed(1)}
                unit="MWp"
                tip={
                  hasRooftop && hasGround
                    ? `Rooftop ${rooftopMwpClient?.toFixed(1)} + Ground ${adjustedCapacity?.toFixed(1)} MWp. Mixes cost tiers — rooftop is ≈ 5× $/MWp vs ground-mounted utility-scale, so this sum is a capacity ceiling, not a unit-economics number.`
                    : hasRooftop
                      ? 'Rooftop only — no buildable ground inside the fence at this site.'
                      : 'Ground only — no rooftop data at this site.'
                }
              />
            </>
          )}

          {row.polygon_source_tier && (
            <StatRowWithTip
              label="Polygon source"
              value={
                {
                  official_kek: 'Official KEK',
                  osm_landuse_industrial: 'OSM',
                  claude_building_hull_estimate: 'Estimated',
                  none: 'No polygon',
                }[row.polygon_source_tier]
              }
              unit=""
              tip={
                {
                  official_kek:
                    'Government-published KEK boundary from the Indonesian OSS portal. High trust.',
                  osm_landuse_industrial:
                    'OpenStreetMap landuse=industrial polygon. Community-verified, not government-issued.',
                  claude_building_hull_estimate:
                    'Estimated fence boundary — Claude unioned the largest detected buildings inside the catchment. Conservative rooftop number, but the polygon itself has not been independently verified. Treat as an estimate.',
                  none: 'No fence-line polygon yet. Both rooftop and ground-mounted estimates use a 2 km centroid buffer, which can over-count adjacent factories and land. Treat as low-trust; verify visually or hunt a real polygon.',
                }[row.polygon_source_tier]
              }
            />
          )}
        </StatCard>
      )}

      <StatCard>
        <SectionHeader
          title="Buildable Land"
          subtitle="How much suitable land exists after excluding forests, peat, and slopes?"
          tip="Land within 50km that passes slope, land cover, forest, and peatland filters. Wind allows steeper slopes and cropland."
        />
        {showSolar && (
          <>
            <StatRowWithTip
              label={energyMode === 'overall' ? 'Solar Buildable' : 'Buildable Area'}
              value={row.buildable_area_ha != null ? row.buildable_area_ha.toFixed(0) : null}
              unit="ha"
              tip="Sum of suitable ~1km pixels within 50km for solar (slope <8°, no forest/peat/cropland)."
            />
            <StatRowWithTip
              label={energyMode === 'overall' ? 'Solar Capacity' : 'Max Capacity'}
              value={
                row.regional_groundmount_potential_mwp_50km != null
                  ? row.regional_groundmount_potential_mwp_50km.toFixed(0)
                  : null
              }
              unit="MWp"
              tip="MWp buildable at 1.5 ha/MWp density."
            />
          </>
        )}
        {showWind && (
          <>
            <StatRowWithTip
              label={energyMode === 'overall' ? 'Wind Buildable' : 'Buildable Area'}
              value={
                row.wind_buildable_area_ha != null ? row.wind_buildable_area_ha.toFixed(0) : null
              }
              unit="ha"
              tip="Sum of suitable ~1km pixels within 50km for wind (slope <20°, wind >3 m/s, cropland allowed)."
            />
            <StatRowWithTip
              label={energyMode === 'overall' ? 'Wind Capacity' : 'Max Capacity'}
              value={
                row.max_wind_capacity_mwp != null ? row.max_wind_capacity_mwp.toFixed(0) : null
              }
              unit="MWp"
              tip="MWp buildable at 25 ha/MWp density (wind turbine spacing)."
            />
          </>
        )}
      </StatCard>

      {showSolar && (
        <StatCard>
          <SectionHeader
            title="Solar LCOE Breakdown"
            subtitle="What does solar electricity cost at different financing rates?"
            tip="Levelized Cost of Energy at three discount rates. Low = concessional finance, Mid = market rate, High = high-risk."
          />
          <StatRow label="LCOE Low (4%)" value={row.lcoe_low_usd_mwh?.toFixed(1)} unit="$/MWh" />
          <StatRowWithTip
            label="LCOE Mid (10%)"
            value={row.lcoe_mid_usd_mwh?.toFixed(1)}
            unit="$/MWh"
            tip="Cost at 10% WACC (market rate). This is the primary comparison number."
          />
          <StatRow label="LCOE High (16%)" value={row.lcoe_high_usd_mwh?.toFixed(1)} unit="$/MWh" />
          {wbLcoe != null && (
            <StatRowWithTip
              label="Within-Boundary"
              value={wbLcoe.toFixed(1)}
              unit="$/MWh"
              tip="LCOE for solar built inside the site boundary. No grid connection cost, but uses centroid PVOUT."
            />
          )}
        </StatCard>
      )}

      {row.regional_groundmount_potential_mwp_50km != null &&
        row.regional_groundmount_potential_mwp_50km > 0 &&
        showSolar && <LcoeCurveChart row={row} />}
    </>
  );
}

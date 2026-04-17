import { capitalize } from '../../../lib/format';
import type { ScorecardRow } from '../../../lib/types';
import { useDashboardStore } from '../../../store/dashboard';
import LcoeCurveChart from '../../charts/LcoeCurveChart';
import { SectionHeader, StatCard, StatRow, StatRowWithTip } from './StatComponents';

export function ResourceTab({ row }: { row: ScorecardRow }) {
  const energyMode = useDashboardStore((s) => s.energyMode);
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
                row.max_captive_capacity_mwp != null
                  ? row.max_captive_capacity_mwp.toFixed(0)
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

      {row.max_captive_capacity_mwp != null && row.max_captive_capacity_mwp > 0 && showSolar && (
        <LcoeCurveChart row={row} />
      )}
    </>
  );
}

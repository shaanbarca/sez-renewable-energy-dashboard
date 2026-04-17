import type { EnergyMode, ScorecardRow } from '../../lib/types';

const COLORS = {
  daytime: '#FFC107',
  nighttime: '#7B1FA2',
  solar: '#4CAF50',
  wind: '#2196F3',
  bess: '#FF9800',
  gap: '#EF5350',
};

function BarSegment({
  widthPct,
  color,
  label,
  gwh,
}: {
  widthPct: number;
  color: string;
  label: string;
  gwh: number;
}) {
  const showLabel = widthPct > 18;
  return (
    <div
      className="relative h-5 flex items-center justify-center overflow-hidden"
      style={{
        width: `${Math.max(widthPct, 2)}%`,
        backgroundColor: `${color}cc`,
        borderRight: '1px solid rgba(0,0,0,0.2)',
      }}
      title={`${label}: ${gwh.toFixed(1)} GWh (${widthPct.toFixed(0)}%)`}
    >
      {showLabel && (
        <span className="text-[9px] font-medium text-white truncate px-1">
          {label} {widthPct.toFixed(0)}%
        </span>
      )}
    </div>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1">
      <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
      <span className="text-[9px]" style={{ color: 'var(--text-muted)' }}>
        {label}
      </span>
    </div>
  );
}

export default function EnergyBalanceChart({
  row,
  energyMode = 'solar',
}: {
  row: ScorecardRow;
  energyMode?: EnergyMode;
}) {
  if (row.demand_2030_gwh == null) return null;
  // Wind mode only needs wind data; solar/hybrid need solar data
  if (energyMode === 'wind') {
    if (row.max_wind_generation_gwh == null) return null;
  } else {
    if (row.max_solar_generation_gwh == null) return null;
  }

  const totalDemand = row.demand_2030_gwh;
  if (totalDemand <= 0) return null;

  const daytimeFraction = 10 / 24; // ~42% — 10h solar production
  const nighttimeFraction = 1 - daytimeFraction; // ~58%
  const daytimeDemand = totalDemand * daytimeFraction;
  const nighttimeDemand = totalDemand * nighttimeFraction;

  const isHybrid = energyMode === 'hybrid' && row.hybrid_allin_usd_mwh != null;
  const isWind = energyMode === 'wind';

  // Supply sources
  const solarGwh = row.max_solar_generation_gwh ?? 0;
  const windGwh = isHybrid || isWind ? (row.max_wind_generation_gwh ?? 0) : 0;
  const windShare =
    isHybrid && row.hybrid_solar_share != null ? 1 - row.hybrid_solar_share : isWind ? 1 : 0;
  const solarShare =
    isHybrid && row.hybrid_solar_share != null ? row.hybrid_solar_share : isWind ? 0 : 1;

  // Scaled generation based on mix
  const scaledSolar = solarGwh * solarShare;
  const scaledWind = windGwh * windShare;
  const totalSupply = isWind ? windGwh : isHybrid ? scaledSolar + scaledWind : solarGwh;

  const coveragePct = isHybrid
    ? (row.hybrid_supply_coverage_pct ?? totalSupply / totalDemand)
    : isWind
      ? (row.wind_supply_coverage_pct ?? totalSupply / totalDemand)
      : (row.solar_supply_coverage_pct ?? totalSupply / totalDemand);

  // Scale: demand bar is always 100%. Supply bar is proportional.
  const totalSupplyPct = Math.min((totalSupply / totalDemand) * 100, 100);

  // Temporal demand-matching split for all modes.
  // Solar covers daytime, BESS stores excess for night, wind covers night in hybrid.
  let solarBarPct: number;
  let windBarPct: number;
  let bessBarPct: number;
  let gapPct: number;

  if (isHybrid) {
    // Wind covers nighttime demand. Solar covers daytime + any uncovered night via BESS.
    const nightCov = row.hybrid_nighttime_coverage_pct ?? 0;
    windBarPct = nighttimeFraction * Math.min(nightCov, 1.0) * totalSupplyPct;
    solarBarPct = Math.max(totalSupplyPct - windBarPct, 0);
    bessBarPct = 0; // wind replaces BESS in hybrid
    gapPct = 100 - totalSupplyPct;
  } else if (isWind) {
    // Wind-only: generation-weighted
    solarBarPct = 0;
    windBarPct = totalSupplyPct;
    bessBarPct = 0;
    gapPct = 100 - totalSupplyPct;
  } else {
    // Solar mode: temporal split — solar for day, BESS (stored solar) for night.
    // Solar directly covers daytime demand. Excess charges BESS for nighttime.
    const solarDayPct = Math.min(coveragePct, daytimeFraction) * 100;
    const bessPct = Math.max(Math.min(coveragePct - daytimeFraction, nighttimeFraction), 0) * 100;
    solarBarPct = solarDayPct;
    bessBarPct = bessPct;
    windBarPct = 0;
    gapPct = Math.max(100 - solarDayPct - bessPct, 0);
  }

  const gapGwh = (gapPct / 100) * totalDemand;

  // Summary line
  let summary: string;
  if (isHybrid) {
    const nightCov =
      row.hybrid_nighttime_coverage_pct != null
        ? Math.round(row.hybrid_nighttime_coverage_pct * 100)
        : 0;
    const bessHrs = row.hybrid_bess_hours?.toFixed(1) ?? '?';
    summary = `Hybrid: wind covers ${nightCov}% of nighttime demand, reducing BESS from 14h to ${bessHrs}h.`;
  } else if (isWind) {
    const firmCov =
      row.firm_wind_coverage_pct != null ? (row.firm_wind_coverage_pct * 100).toFixed(0) : '?';
    const firmHrs = row.wind_firming_hours?.toFixed(0) ?? '?';
    if (coveragePct >= 1.0) {
      summary = `Wind produces more than enough annually. ${firmCov}% firm coverage with ${firmHrs}h firming.`;
    } else if (coveragePct >= 0.5) {
      summary = `Wind covers ${(coveragePct * 100).toFixed(0)}% of annual demand. ${firmCov}% firm coverage, ${firmHrs}h firming.`;
    } else {
      summary = `Wind covers only ${(coveragePct * 100).toFixed(0)}% of demand. Grid power remains essential.`;
    }
  } else if (coveragePct >= 1.0) {
    summary = `Solar covers daytime (${(daytimeFraction * 100).toFixed(0)}%). Storage/grid covers nighttime (${(nighttimeFraction * 100).toFixed(0)}%).`;
  } else if (coveragePct > daytimeFraction) {
    const bessCovPct = Math.round(((coveragePct - daytimeFraction) / nighttimeFraction) * 100);
    summary = `Solar covers daytime fully. Storage/grid covers ${bessCovPct}% of nighttime. ${(gapPct).toFixed(0)}% remains uncovered.`;
  } else {
    summary = `Solar covers only ${(coveragePct * 100).toFixed(0)}% of demand (not enough for full daytime). Grid power essential.`;
  }

  return (
    <div
      className="rounded-md px-3 py-2 mb-2"
      style={{
        background: 'var(--card-bg)',
        border: '1px solid var(--card-border)',
      }}
      role="img"
      aria-label="Energy balance showing renewable supply vs industrial demand"
    >
      <div className="mb-1.5">
        <div className="text-[11px] font-medium" style={{ color: 'var(--text-muted)' }}>
          Energy Balance
        </div>
        <div
          className="text-[10px] leading-snug mt-0.5"
          style={{ color: 'var(--text-muted)', opacity: 0.7 }}
        >
          {isHybrid
            ? 'Can solar + wind power this site?'
            : isWind
              ? 'Can wind power this site?'
              : 'Can solar actually power this site?'}
        </div>
      </div>

      {/* Demand bar */}
      <div className="mb-2">
        <div className="flex items-center justify-between mb-1">
          <span
            className="text-[9px] font-medium uppercase tracking-wider"
            style={{ color: 'var(--text-muted)' }}
          >
            Demand
          </span>
          <span className="text-[10px] tabular-nums" style={{ color: 'var(--text-value)' }}>
            {totalDemand.toFixed(1)} GWh
          </span>
        </div>
        <div className="flex rounded overflow-hidden">
          <BarSegment
            widthPct={daytimeFraction * 100}
            color={COLORS.daytime}
            label="Day"
            gwh={daytimeDemand}
          />
          <BarSegment
            widthPct={nighttimeFraction * 100}
            color={COLORS.nighttime}
            label="Night"
            gwh={nighttimeDemand}
          />
        </div>
      </div>

      {/* Supply bar */}
      <div className="mb-2">
        <div className="flex items-center justify-between mb-1">
          <span
            className="text-[9px] font-medium uppercase tracking-wider"
            style={{ color: 'var(--text-muted)' }}
          >
            Supply
          </span>
          <span className="text-[10px] tabular-nums" style={{ color: 'var(--text-value)' }}>
            {isHybrid || !isWind
              ? Math.min(totalSupply, totalDemand).toFixed(1)
              : totalSupply.toFixed(1)}{' '}
            GWh
          </span>
        </div>
        <div className="flex rounded overflow-hidden" style={{ background: 'var(--bar-bg)' }}>
          {solarBarPct > 0 && (
            <BarSegment
              widthPct={solarBarPct}
              color={COLORS.solar}
              label="Solar"
              gwh={(solarBarPct / 100) * totalDemand}
            />
          )}
          {windBarPct > 0 && (
            <BarSegment
              widthPct={windBarPct}
              color={COLORS.wind}
              label="Wind"
              gwh={(windBarPct / 100) * totalDemand}
            />
          )}
          {bessBarPct > 0 && (
            <BarSegment
              widthPct={bessBarPct}
              color={COLORS.bess}
              label="Storage/Grid"
              gwh={(bessBarPct / 100) * totalDemand}
            />
          )}
          {gapPct > 2 && (
            <div
              className="h-5 flex items-center justify-center"
              style={{
                width: `${gapPct}%`,
                border: `1px dashed ${COLORS.gap}66`,
                background: `${COLORS.gap}11`,
              }}
              title={`Gap: ${gapGwh.toFixed(1)} GWh`}
            >
              {gapPct > 15 && (
                <span className="text-[9px]" style={{ color: `${COLORS.gap}cc` }}>
                  Gap {gapGwh.toFixed(0)} GWh
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 mb-1.5">
        <LegendDot color={COLORS.daytime} label="Daytime" />
        <LegendDot color={COLORS.nighttime} label="Nighttime" />
        {solarBarPct > 0 && <LegendDot color={COLORS.solar} label="Solar" />}
        {windBarPct > 0 && <LegendDot color={COLORS.wind} label="Wind" />}
        {bessBarPct > 0 && <LegendDot color={COLORS.bess} label="Storage/Grid" />}
        {gapPct > 2 && <LegendDot color={COLORS.gap} label="Gap" />}
      </div>

      {/* Summary */}
      <div className="text-[10px] leading-snug" style={{ color: 'var(--text-secondary)' }}>
        {summary}
      </div>
    </div>
  );
}

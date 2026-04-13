import type { ScorecardRow } from '../../lib/types';

const COLORS = {
  daytime: '#FFC107',
  nighttime: '#7B1FA2',
  solar: '#4CAF50',
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

export default function EnergyBalanceChart({ row }: { row: ScorecardRow }) {
  if (row.demand_2030_gwh == null || row.max_solar_generation_gwh == null) return null;

  const totalDemand = row.demand_2030_gwh;
  if (totalDemand <= 0) return null;

  const daytimeFraction = 10 / 24; // ~42% — 10h solar production
  const nighttimeFraction = 1 - daytimeFraction; // ~58%
  const daytimeDemand = totalDemand * daytimeFraction;
  const nighttimeDemand = totalDemand * nighttimeFraction;

  const totalSupply = row.max_solar_generation_gwh;
  const coveragePct = row.solar_supply_coverage_pct ?? totalSupply / totalDemand;

  // Scale: demand bar is always 100%. Supply bar is proportional.
  const supplyPct = Math.min((totalSupply / totalDemand) * 100, 100);
  const gapGwh = Math.max(totalDemand - totalSupply, 0);
  const gapPct = 100 - supplyPct;

  // Summary line
  let summary: string;
  if (coveragePct >= 1.0) {
    const storagePct = row.storage_gap_pct != null ? (row.storage_gap_pct * 100).toFixed(0) : '58';
    summary = `Solar produces more than enough annually, but ${storagePct}% of demand falls at night.`;
  } else if (coveragePct >= 0.5) {
    const storagePct = row.storage_gap_pct != null ? (row.storage_gap_pct * 100).toFixed(0) : '58';
    summary = `Solar covers ${(coveragePct * 100).toFixed(0)}% of annual demand. ${storagePct}% requires grid or storage.`;
  } else {
    summary = `Solar covers only ${(coveragePct * 100).toFixed(0)}% of demand. Grid power remains essential.`;
  }

  return (
    <div
      className="rounded-md px-3 py-2 mb-2"
      style={{
        background: 'var(--card-bg)',
        border: '1px solid var(--card-border)',
      }}
      role="img"
      aria-label="Energy balance showing solar supply vs industrial demand"
    >
      <div className="mb-1.5">
        <div className="text-[11px] font-medium" style={{ color: 'var(--text-muted)' }}>
          Energy Balance
        </div>
        <div
          className="text-[10px] leading-snug mt-0.5"
          style={{ color: 'var(--text-muted)', opacity: 0.7 }}
        >
          Can solar actually power this KEK?
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
            {totalSupply.toFixed(1)} GWh
          </span>
        </div>
        <div className="flex rounded overflow-hidden" style={{ background: 'var(--bar-bg)' }}>
          <BarSegment widthPct={supplyPct} color={COLORS.solar} label="Solar" gwh={totalSupply} />
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
        <LegendDot color={COLORS.solar} label="Solar" />
        {gapPct > 2 && <LegendDot color={COLORS.gap} label="Gap" />}
      </div>

      {/* Summary */}
      <div className="text-[10px] leading-snug" style={{ color: 'var(--text-secondary)' }}>
        {summary}
      </div>
    </div>
  );
}

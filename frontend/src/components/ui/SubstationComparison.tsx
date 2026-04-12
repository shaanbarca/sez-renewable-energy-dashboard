import { useState } from 'react';
import type { SubstationWithCosts } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

const CAPACITY_COLORS: Record<string, string> = {
  green: '#4CAF50',
  yellow: '#FFC107',
  red: '#F44336',
  unknown: '#666',
};

function formatName(name: string): string {
  // Shorten "GI 150 kV Palu" → "GI Palu" for compact display
  return name.replace(/\s*\d+\s*kV\s*/i, ' ').trim();
}

export default function SubstationComparison({
  substations,
}: {
  substations: SubstationWithCosts[];
}) {
  const flyTo = useDashboardStore((s) => s.flyTo);
  const [activeIdx, setActiveIdx] = useState<number | null>(null);

  const ranked = substations.filter((s) => s.rank != null && s.rank <= 3);
  if (ranked.length < 2) return null;

  // Find the lowest-cost option
  const withLcoe = ranked.filter((s) => s.lcoe_estimate_usd_mwh != null);
  const bestLcoeIdx =
    withLcoe.length > 0
      ? ranked.indexOf(
          withLcoe.reduce((a, b) =>
            (a.lcoe_estimate_usd_mwh ?? Infinity) < (b.lcoe_estimate_usd_mwh ?? Infinity) ? a : b,
          ),
        )
      : -1;

  const handleClick = (s: SubstationWithCosts, idx: number) => {
    flyTo(s.lat, s.lon, 13);
    setActiveIdx(idx);
  };

  return (
    <div
      className="rounded-md px-3 py-2 mb-2"
      style={{
        background: 'var(--card-bg)',
        border: '1px solid var(--card-border)',
      }}
    >
      <div className="text-[11px] mb-2" style={{ color: 'var(--text-muted)' }}>
        Substation Options
        <span className="text-[9px] ml-1" style={{ opacity: 0.6 }}>
          (click to locate)
        </span>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <th
                className="text-left py-1 pr-2 font-normal"
                style={{ color: 'var(--text-muted)', width: '30%' }}
              />
              {ranked.map((s, i) => (
                <th
                  key={s.name}
                  className="text-right py-1 px-1 font-medium cursor-pointer transition-colors"
                  style={{
                    color:
                      activeIdx === i
                        ? '#FFD600'
                        : i === bestLcoeIdx
                          ? '#4DD0E1'
                          : 'var(--text-value)',
                    minWidth: 70,
                    borderBottom: i === 0 ? '2px solid #FFD60066' : undefined,
                  }}
                  onClick={() => handleClick(s, i)}
                  title={`${s.name} — click to fly to location`}
                >
                  {formatName(s.name)}
                  {i === bestLcoeIdx && (
                    <span className="ml-0.5" title="Lowest cost option">
                      *
                    </span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {/* Distance */}
            <tr>
              <td className="py-1 pr-2" style={{ color: 'var(--text-muted)' }}>
                Distance
              </td>
              {ranked.map((s, i) => (
                <td
                  key={s.name}
                  className="text-right py-1 px-1 tabular-nums cursor-pointer"
                  style={{
                    color: activeIdx === i ? '#FFD600' : 'var(--text-value)',
                  }}
                  onClick={() => handleClick(s, i)}
                >
                  {s.dist_solar_km != null ? `${s.dist_solar_km} km` : `${s.dist_km} km`}
                </td>
              ))}
            </tr>

            {/* Capacity */}
            <tr>
              <td className="py-1 pr-2" style={{ color: 'var(--text-muted)' }}>
                Capacity
              </td>
              {ranked.map((s, i) => {
                const color = CAPACITY_COLORS[s.capacity_assessment ?? 'unknown'];
                return (
                  <td
                    key={s.name}
                    className="text-right py-1 px-1 tabular-nums cursor-pointer"
                    style={{
                      color: activeIdx === i ? '#FFD600' : 'var(--text-value)',
                    }}
                    onClick={() => handleClick(s, i)}
                  >
                    <span
                      className="inline-block w-1.5 h-1.5 rounded-full mr-1"
                      style={{ backgroundColor: color, verticalAlign: 'middle' }}
                    />
                    {s.available_capacity_mva != null
                      ? `${Math.round(s.available_capacity_mva)} MVA`
                      : 'N/A'}
                  </td>
                );
              })}
            </tr>

            {/* Grid Cost */}
            <tr>
              <td className="py-1 pr-2" style={{ color: 'var(--text-muted)' }}>
                Grid Cost
              </td>
              {ranked.map((s, i) => (
                <td
                  key={s.name}
                  className="text-right py-1 px-1 tabular-nums cursor-pointer"
                  style={{
                    color: activeIdx === i ? '#FFD600' : 'var(--text-value)',
                  }}
                  onClick={() => handleClick(s, i)}
                >
                  {s.total_grid_capex_per_kw != null
                    ? `$${Math.round(s.total_grid_capex_per_kw)}/kW`
                    : 'N/A'}
                </td>
              ))}
            </tr>

            {/* LCOE */}
            <tr style={{ borderTop: '1px solid var(--border-subtle)' }}>
              <td className="py-1 pr-2 font-medium" style={{ color: 'var(--text-muted)' }}>
                LCOE
              </td>
              {ranked.map((s, i) => (
                <td
                  key={s.name}
                  className="text-right py-1 px-1 tabular-nums font-medium cursor-pointer"
                  style={{
                    color:
                      activeIdx === i
                        ? '#FFD600'
                        : i === bestLcoeIdx
                          ? '#4DD0E1'
                          : 'var(--text-value)',
                  }}
                  onClick={() => handleClick(s, i)}
                >
                  {s.lcoe_estimate_usd_mwh != null ? `$${s.lcoe_estimate_usd_mwh}/MWh` : 'N/A'}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      {bestLcoeIdx >= 0 && bestLcoeIdx !== 0 && (
        <div className="text-[9px] mt-1.5 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
          * Farther substation is cheaper overall due to better capacity headroom.
        </div>
      )}
    </div>
  );
}

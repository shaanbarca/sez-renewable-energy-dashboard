import { useMemo } from 'react';
import {
  Area,
  AreaChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ScorecardRow } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

interface DataPoint {
  capacity_mw: number;
  lcoe: number;
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload?: DataPoint }[];
}) {
  if (!active || !payload?.[0]?.payload) return null;
  const d = payload[0].payload;
  return (
    <div
      className="rounded px-3 py-2 text-xs"
      style={{
        background: 'var(--popup-bg)',
        border: '1px solid var(--popup-border)',
        boxShadow: 'var(--popup-shadow)',
        color: 'var(--text-primary)',
      }}
    >
      <div style={{ color: 'var(--text-muted)' }}>{d.capacity_mw} MW</div>
      <div className="font-medium">${d.lcoe.toFixed(1)}/MWh</div>
    </div>
  );
}

export default function LcoeCurveChart({ row }: { row: ScorecardRow }) {
  const assumptions = useDashboardStore((s) => s.assumptions);

  const data = useMemo(() => {
    if (!assumptions) return [];

    const pvout = row.pvout_best_50km_kwh_kwp_yr ?? row.pvout_centroid_kwh_kwp_yr;
    if (!pvout || pvout <= 0) return [];

    const cf = pvout / 8760;
    const maxCap = row.max_captive_capacity_mwp ?? 200;
    if (maxCap <= 0) return [];

    const wacc = assumptions.wacc_pct / 100;
    const n = assumptions.lifetime_yr;
    const fom = assumptions.fom_usd_per_kw_yr;
    const capex = assumptions.capex_usd_per_kw;

    // Connection cost (constant per kW)
    const dist = row.dist_solar_to_nearest_substation_km ?? row.dist_to_nearest_substation_km ?? 0;
    const connCost =
      dist * assumptions.connection_cost_per_kw_km + assumptions.grid_connection_fixed_per_kw;
    const landCost = assumptions.land_cost_usd_per_kw;

    // Inter-substation distance for transmission cost (varies with capacity)
    const needsTransLine =
      row.inter_substation_connected === false && (row.inter_substation_dist_km ?? 0) > 0;
    const interSubDist = row.inter_substation_dist_km ?? 0;

    // CRF
    const crf = (wacc * (1 + wacc) ** n) / ((1 + wacc) ** n - 1);

    // Generate ~25 data points
    const minCap = Math.max(5, maxCap * 0.05);
    const steps = 25;
    const stepSize = (maxCap - minCap) / (steps - 1);

    const points: DataPoint[] = [];
    for (let i = 0; i < steps; i++) {
      const cap = minCap + i * stepSize;
      const transCost = needsTransLine ? (interSubDist * 1_250_000) / (cap * 1000) : 0;
      const effCapex = capex + connCost + landCost + transCost;
      const lcoe = (effCapex * crf + fom) / (cf * 8.76);
      points.push({
        capacity_mw: Math.round(cap * 10) / 10,
        lcoe: Math.round(lcoe * 100) / 100,
      });
    }

    return points;
  }, [assumptions, row]);

  if (data.length === 0) return null;

  const gridCost = row.dashboard_rate_usd_mwh;
  const maxCap = row.max_captive_capacity_mwp;

  return (
    <div
      className="rounded-lg p-3 mt-2"
      style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)' }}
    >
      <div className="text-[11px] mb-2" style={{ color: 'var(--text-muted)' }}>
        LCOE vs Project Scale
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <defs>
            <linearGradient id="lcoeGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.3} />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="capacity_mw"
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            tickLine={false}
            axisLine={{ stroke: 'var(--border-subtle)' }}
            label={{
              value: 'MW',
              position: 'insideBottomRight',
              offset: -5,
              fontSize: 9,
              fill: 'var(--text-muted)',
            }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            tickLine={false}
            axisLine={{ stroke: 'var(--border-subtle)' }}
            domain={['auto', 'auto']}
            label={{
              value: '$/MWh',
              angle: -90,
              position: 'insideLeft',
              offset: 0,
              fontSize: 9,
              fill: 'var(--text-muted)',
            }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="lcoe"
            stroke="var(--accent)"
            strokeWidth={2}
            fill="url(#lcoeGrad)"
          />
          {gridCost != null && (
            <ReferenceLine
              y={gridCost}
              stroke="var(--flag-grid-first)"
              strokeDasharray="6 3"
              strokeWidth={1.5}
              label={{
                value: `Grid $${gridCost.toFixed(0)}`,
                position: 'right',
                fontSize: 9,
                fill: 'var(--flag-grid-first)',
              }}
            />
          )}
          {maxCap != null && maxCap > 0 && (
            <ReferenceLine
              x={maxCap}
              stroke="var(--text-muted)"
              strokeDasharray="4 4"
              strokeWidth={1}
              label={{
                value: 'Max',
                position: 'top',
                fontSize: 9,
                fill: 'var(--text-muted)',
              }}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
      <div className="text-[9px] mt-1 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        LCOE decreases at larger scale as fixed transmission costs spread over more capacity.
      </div>
    </div>
  );
}

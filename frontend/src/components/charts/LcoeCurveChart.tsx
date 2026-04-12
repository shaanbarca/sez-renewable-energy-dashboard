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
  const setAssumptions = useDashboardStore((s) => s.setAssumptions);

  const targetMwp = assumptions?.target_capacity_mwp ?? null;

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
    const landCost = assumptions.land_cost_usd_per_kw;

    // Connection line: total fixed cost that gets spread over capacity
    // $125k/km implied by $5/kW-km at ~25MW reference scale
    const dist = row.dist_solar_to_nearest_substation_km ?? row.dist_to_nearest_substation_km ?? 0;
    const connLineTotal = dist * 125_000;
    // Fixed switchgear/protection: ~$2M one-time cost
    const connFixedTotal = 2_000_000;

    // Transmission line: only if substations not connected
    const needsTransLine =
      row.inter_substation_connected === false && (row.inter_substation_dist_km ?? 0) > 0;
    const interSubDist = row.inter_substation_dist_km ?? 0;

    // Substation capacity for upgrade cost
    const availMva = row.available_capacity_mva ?? null;
    const util = assumptions.substation_utilization_pct;

    // CRF
    const crf = (wacc * (1 + wacc) ** n) / ((1 + wacc) ** n - 1);

    // Generate ~25 data points
    const minCap = Math.max(5, maxCap * 0.05);
    const steps = 25;
    const stepSize = (maxCap - minCap) / (steps - 1);

    const points: DataPoint[] = [];
    for (let i = 0; i < steps; i++) {
      const cap = minCap + i * stepSize;
      const capKw = cap * 1000;

      // Connection: total cost / capacity (economies of scale)
      const connPerKw = capKw > 0 ? (connLineTotal + connFixedTotal) / capKw : 0;

      // Transmission: fixed total / capacity (only if needed)
      const transPerKw = needsTransLine ? (interSubDist * 1_250_000) / capKw : 0;

      // Substation upgrade: deficit grows with capacity
      let upgradePerKw = 0;
      if (availMva != null && availMva > 0) {
        const deficit = Math.max(0, 1 - availMva / (cap * util));
        upgradePerKw = deficit * 80;
      }

      const effCapex = capex + connPerKw + landCost + transPerKw + upgradePerKw;
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
  const effectiveCap = targetMwp != null && maxCap != null ? Math.min(targetMwp, maxCap) : null;

  // Find the LCOE at the effective capacity point (interpolate from data)
  const effectiveLcoe = useMemo(() => {
    if (effectiveCap == null || data.length < 2) return null;
    // Find surrounding points and interpolate
    for (let i = 0; i < data.length - 1; i++) {
      if (data[i].capacity_mw <= effectiveCap && data[i + 1].capacity_mw >= effectiveCap) {
        const t =
          (effectiveCap - data[i].capacity_mw) / (data[i + 1].capacity_mw - data[i].capacity_mw);
        return data[i].lcoe + t * (data[i + 1].lcoe - data[i].lcoe);
      }
    }
    // If effectiveCap is at or beyond the range, use nearest point
    if (effectiveCap <= data[0].capacity_mw) return data[0].lcoe;
    return data[data.length - 1].lcoe;
  }, [effectiveCap, data]);

  const handleChartClick = (e: { activePayload?: { payload?: DataPoint }[] }) => {
    if (!e?.activePayload?.[0]?.payload) return;
    const clickedMw = e.activePayload[0].payload.capacity_mw;
    setAssumptions({ target_capacity_mwp: Math.round(clickedMw / 5) * 5 || 5 });
  };

  return (
    <div
      className="rounded-lg p-3 mt-2"
      style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)' }}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
          LCOE vs Project Scale
          {effectiveCap != null && effectiveLcoe != null && (
            <span style={{ color: 'var(--accent)' }}>
              {' '}
              — ${effectiveLcoe.toFixed(1)}/MWh at {effectiveCap} MW
            </span>
          )}
        </div>
        {targetMwp != null && (
          <button
            type="button"
            onClick={() => setAssumptions({ target_capacity_mwp: null })}
            className="text-[9px] px-1.5 py-0.5 rounded cursor-pointer"
            style={{ color: 'var(--text-muted)', border: '1px solid var(--border-subtle)' }}
          >
            Reset
          </button>
        )}
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart
          data={data}
          margin={{ top: 5, right: 10, bottom: 5, left: 10 }}
          onClick={handleChartClick}
          style={{ cursor: 'pointer' }}
        >
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
          {effectiveCap != null && effectiveCap > 0 && (
            <ReferenceLine
              x={effectiveCap}
              stroke="var(--accent)"
              strokeWidth={2}
              label={{
                value: `${effectiveCap} MW`,
                position: 'top',
                fontSize: 9,
                fill: 'var(--accent)',
              }}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
      <div className="text-[9px] mt-1 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        Click a point to set target build size. LCOE decreases at larger scale as fixed grid costs
        spread over more capacity, but may rise if substation capacity is exceeded.
      </div>
    </div>
  );
}

import { useMemo } from 'react';
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ReferenceLine,
  Tooltip,
} from 'recharts';
import { useDashboardStore } from '../../store/dashboard';
import { ACTION_FLAG_COLORS } from '../../lib/constants';
import type { ScorecardRow } from '../../lib/types';

interface DotProps {
  cx?: number;
  cy?: number;
  payload?: ScorecardRow;
}

function CustomDot(props: DotProps) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null || !payload) return null;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={6}
      fill={ACTION_FLAG_COLORS[payload.action_flag] ?? '#666'}
    />
  );
}

interface TooltipPayload {
  payload?: ScorecardRow;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayload[];
}

function CustomTooltip({ active, payload }: CustomTooltipProps) {
  if (!active || !payload?.[0]?.payload) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-[#1e1e1e] border border-white/10 rounded px-3 py-2 text-xs text-[#e0e0e0]">
      <div className="font-medium mb-1">{d.kek_name}</div>
      <div>LCOE: ${d.lcoe_mid_usd_mwh.toFixed(1)}/MWh</div>
      <div>Grid: ${d.dashboard_rate_usd_mwh.toFixed(1)}/MWh</div>
      <div>Gap: {d.solar_competitive_gap_pct > 0 ? '+' : ''}{d.solar_competitive_gap_pct.toFixed(1)}%</div>
    </div>
  );
}

export default function QuadrantChart() {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const benchmarkMode = useDashboardStore((s) => s.benchmarkMode);

  const chartData = useMemo(() => {
    if (!scorecard) return [];
    return scorecard.map((row) => ({
      ...row,
      gridCost:
        benchmarkMode === 'bpp' && row.bpp_usd_mwh != null
          ? row.bpp_usd_mwh
          : row.dashboard_rate_usd_mwh,
    }));
  }, [scorecard, benchmarkMode]);

  const domain = useMemo(() => {
    if (!chartData.length) return { min: 0, max: 200 };
    const allVals = chartData.flatMap((d) => [d.lcoe_mid_usd_mwh, d.gridCost]);
    const min = Math.floor(Math.min(...allVals) * 0.8);
    const max = Math.ceil(Math.max(...allVals) * 1.2);
    return { min: Math.max(0, min), max };
  }, [chartData]);

  if (!scorecard) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-600">
        Loading...
      </div>
    );
  }

  return (
    <div className="h-full w-full px-4 py-2">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 20 }}>
          <XAxis
            type="number"
            dataKey="lcoe_mid_usd_mwh"
            name="Solar LCOE"
            domain={[domain.min, domain.max]}
            tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }}
            label={{
              value: 'Solar LCOE ($/MWh)',
              position: 'bottom',
              offset: 10,
              fill: 'rgba(255,255,255,0.6)',
              fontSize: 12,
            }}
            stroke="rgba(255,255,255,0.1)"
          />
          <YAxis
            type="number"
            dataKey="gridCost"
            name="Grid Cost"
            domain={[domain.min, domain.max]}
            tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }}
            label={{
              value: 'Grid Cost ($/MWh)',
              angle: -90,
              position: 'insideLeft',
              offset: -5,
              fill: 'rgba(255,255,255,0.6)',
              fontSize: 12,
            }}
            stroke="rgba(255,255,255,0.1)"
          />
          <ReferenceLine
            segment={[
              { x: domain.min, y: domain.min },
              { x: domain.max, y: domain.max },
            ]}
            stroke="white"
            strokeOpacity={0.2}
            strokeDasharray="5 5"
          />
          <Tooltip content={<CustomTooltip />} />
          <Scatter
            data={chartData}
            shape={<CustomDot />}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

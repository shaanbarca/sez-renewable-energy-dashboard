import { useMemo } from 'react';
import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ReferenceLine,
  Tooltip,
  Customized,
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

/**
 * 4-zone diagonal bands matching action flag thresholds.
 *
 * Gap = (LCOE - Grid) / Grid. The ±20% gap lines create 4 bands:
 *   Solar Now (green):         gap < -20%  →  Grid > 1.25 × LCOE
 *   Invest Resilience (amber): gap -20%–0% →  Grid between LCOE and 1.25 × LCOE
 *   Grid First (blue):         gap 0%–20%  →  Grid between 0.833 × LCOE and LCOE
 *   Not Competitive (red):     gap > 20%   →  Grid < 0.833 × LCOE
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function ZoneShading(props: any) {
  const { xAxisMap, yAxisMap } = props;
  if (!xAxisMap || !yAxisMap) return null;

  const xAxis = xAxisMap[Object.keys(xAxisMap)[0]];
  const yAxis = yAxisMap[Object.keys(yAxisMap)[0]];
  if (!xAxis?.scale || !yAxis?.scale) return null;

  const dMin = xAxis.domain[0];
  const dMax = xAxis.domain[1];

  // Convert data coords to pixel coords
  const px = (x: number) => xAxis.scale(x);
  const py = (y: number) => yAxis.scale(y);

  // Clamp a value to domain range
  const clamp = (v: number) => Math.max(dMin, Math.min(dMax, v));

  // Three diagonal lines in data space (Y = factor * X):
  // Parity:  Y = X          (gap = 0%)
  // Upper:   Y = 1.25 * X   (gap = -20%, solar 20% cheaper)
  // Lower:   Y = 0.833 * X  (gap = +20%, solar 20% more expensive)

  // Build polygon points for each zone as pixel coords.
  // We trace along the chart edges and the diagonal boundaries.

  const upperTopX = clamp(dMax / 1.25);
  const lowerBottomX = clamp(dMin / 0.833);

  const zone1 = `${px(dMin)},${py(dMin)} ${px(dMin)},${py(clamp(1.25*dMin))} ${px(upperTopX)},${py(dMax)} ${px(dMin)},${py(dMax)}`;

  // Zone 2: Invest Resilience (amber) — between parity and upper line
  const zone2 = `${px(dMin)},${py(clamp(1.25*dMin))} ${px(dMin)},${py(dMin)} ${px(dMax)},${py(dMax)} ${px(upperTopX)},${py(dMax)}`;

  // Zone 3: Grid First (blue) — between lower line and parity
  const zone3 = `${px(dMin)},${py(dMin)} ${px(dMax)},${py(dMax)} ${px(dMax)},${py(clamp(0.833*dMax))} ${px(lowerBottomX)},${py(dMin)}`;

  // Zone 4: Not Competitive (red) — below lower line
  const zone4 = `${px(lowerBottomX)},${py(dMin)} ${px(dMax)},${py(clamp(0.833*dMax))} ${px(dMax)},${py(dMin)}`;

  // Label positions (placed in center of each zone)
  const lx1 = px(dMin + (dMax - dMin) * 0.15);
  const ly1 = py(dMin + (dMax - dMin) * 0.85);
  const lx2 = px(dMin + (dMax - dMin) * 0.3);
  const ly2 = py(dMin + (dMax - dMin) * 0.62);
  const lx3 = px(dMin + (dMax - dMin) * 0.65);
  const ly3 = py(dMin + (dMax - dMin) * 0.38);
  const lx4 = px(dMin + (dMax - dMin) * 0.82);
  const ly4 = py(dMin + (dMax - dMin) * 0.18);

  return (
    <g>
      <polygon points={zone1} fill="rgba(46, 125, 50, 0.12)" />
      <polygon points={zone2} fill="rgba(245, 124, 0, 0.08)" />
      <polygon points={zone3} fill="rgba(21, 101, 192, 0.08)" />
      <polygon points={zone4} fill="rgba(198, 40, 40, 0.1)" />
      <text x={lx1} y={ly1} fill="rgba(46,125,50,0.4)" fontSize={10} fontWeight={500} textAnchor="middle">
        Solar Now
      </text>
      <text x={lx2} y={ly2} fill="rgba(245,124,0,0.35)" fontSize={10} fontWeight={500} textAnchor="middle">
        Invest Resilience
      </text>
      <text x={lx3} y={ly3} fill="rgba(21,101,192,0.35)" fontSize={10} fontWeight={500} textAnchor="middle">
        Grid First
      </text>
      <text x={lx4} y={ly4} fill="rgba(198,40,40,0.35)" fontSize={10} fontWeight={500} textAnchor="middle">
        Not Competitive
      </text>
    </g>
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
          <Customized component={ZoneShading} />
          {/* Upper boundary: Y = 1.25X (gap = -20%) */}
          <ReferenceLine
            segment={[
              { x: domain.min, y: Math.min(domain.min * 1.25, domain.max) },
              { x: domain.max / 1.25, y: domain.max },
            ]}
            stroke="white"
            strokeOpacity={0.1}
            strokeDasharray="3 6"
          />
          {/* Parity line: Y = X (gap = 0%) */}
          <ReferenceLine
            segment={[
              { x: domain.min, y: domain.min },
              { x: domain.max, y: domain.max },
            ]}
            stroke="white"
            strokeOpacity={0.25}
            strokeDasharray="5 5"
          />
          {/* Lower boundary: Y = 0.833X (gap = +20%) */}
          <ReferenceLine
            segment={[
              { x: domain.min / 0.833, y: domain.min },
              { x: domain.max, y: Math.max(domain.max * 0.833, domain.min) },
            ]}
            stroke="white"
            strokeOpacity={0.1}
            strokeDasharray="3 6"
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

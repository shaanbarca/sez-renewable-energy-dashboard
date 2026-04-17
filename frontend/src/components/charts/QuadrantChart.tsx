import { useMemo } from 'react';
import {
  Customized,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { getEffectiveEconomicTier } from '../../lib/actionFlags';
import { ECONOMIC_TIER_COLORS } from '../../lib/constants';
import type { EnergyMode, ScorecardRow } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

interface ChartRow extends ScorecardRow {
  activeLcoe: number | null;
  gridCost: number;
  economicTierColor: string;
}

function getLcoeForMode(row: ScorecardRow, mode: EnergyMode): number | null | undefined {
  if (mode === 'wind') return row.lcoe_wind_mid_usd_mwh;
  if (mode === 'hybrid') return row.hybrid_allin_usd_mwh;
  if (mode === 'overall') return row.best_re_lcoe_mid_usd_mwh;
  return row.lcoe_mid_usd_mwh;
}

function getModeLabel(mode: EnergyMode): string {
  if (mode === 'wind') return 'Wind';
  if (mode === 'hybrid') return 'Hybrid';
  if (mode === 'overall') return 'RE';
  return 'Solar';
}

interface DotProps {
  cx?: number;
  cy?: number;
  payload?: ChartRow;
}

function CustomDot(props: DotProps) {
  const { cx, cy, payload } = props;
  if (cx == null || cy == null || !payload) return null;
  const fill = payload.economicTierColor ?? '#666';
  if (payload.cbam_exposed) {
    return (
      <g>
        <circle cx={cx} cy={cy} r={8} fill="none" stroke="#FF6F00" strokeWidth={1.5} />
        <circle cx={cx} cy={cy} r={5} fill={fill} />
      </g>
    );
  }
  return <circle cx={cx} cy={cy} r={6} fill={fill} />;
}

interface TooltipPayload {
  payload?: ChartRow;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayload[];
  energyMode?: EnergyMode;
  benchmarkLabel?: string;
}

function CustomTooltip({
  active,
  payload,
  energyMode = 'solar',
  benchmarkLabel = 'Tariff',
}: CustomTooltipProps) {
  if (!active || !payload?.[0]?.payload) return null;
  const d = payload[0].payload;
  const lcoe = d.activeLcoe;
  const gridCost = d.gridCost;
  const gap = lcoe != null && gridCost ? ((lcoe - gridCost) / gridCost) * 100 : null;
  const label = getModeLabel(energyMode);
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
      <div className="font-medium mb-1">{d.site_name}</div>
      <div>
        {label} LCOE: {lcoe != null ? `$${lcoe.toFixed(1)}/MWh` : 'N/A'}
      </div>
      <div>
        Grid ({benchmarkLabel}): ${gridCost.toFixed(1)}/MWh
      </div>
      {gap != null && (
        <div>
          Gap: {gap > 0 ? '+' : ''}
          {gap.toFixed(1)}%
        </div>
      )}
      {d.cbam_exposed && <div style={{ color: '#FF6F00' }}>CBAM Exposed</div>}
    </div>
  );
}

/**
 * Parity line annotation: subtle shading above/below the Y=X line
 * to indicate where RE is cheaper vs grid is cheaper, without
 * misleading zone labels that conflict with the multi-factor action flags.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function ParityAnnotation(props: any) {
  const { xAxisMap, yAxisMap } = props;
  if (!xAxisMap || !yAxisMap) return null;

  const xAxis = xAxisMap[Object.keys(xAxisMap)[0]];
  const yAxis = yAxisMap[Object.keys(yAxisMap)[0]];
  if (!xAxis?.scale || !yAxis?.scale) return null;

  const dMin = xAxis.domain[0];
  const dMax = xAxis.domain[1];

  const px = (x: number) => xAxis.scale(x);
  const py = (y: number) => yAxis.scale(y);

  // Above parity (grid cost > LCOE): RE is cheaper
  const aboveParity = `${px(dMin)},${py(dMin)} ${px(dMax)},${py(dMax)} ${px(dMin)},${py(dMax)}`;
  // Below parity (grid cost < LCOE): grid is cheaper
  const belowParity = `${px(dMin)},${py(dMin)} ${px(dMax)},${py(dMax)} ${px(dMax)},${py(dMin)}`;

  // Label positions: offset from parity line into each half
  const labelX = px(dMin + (dMax - dMin) * 0.18);
  const aboveLabelY = py(dMin + (dMax - dMin) * 0.72);
  const belowLabelY = py(dMin + (dMax - dMin) * 0.28);

  return (
    <g>
      <polygon points={aboveParity} fill="rgba(46, 125, 50, 0.06)" />
      <polygon points={belowParity} fill="rgba(198, 40, 40, 0.05)" />
      <text
        x={labelX}
        y={aboveLabelY}
        fill="rgba(46,125,50,0.35)"
        fontSize={10}
        fontWeight={500}
        textAnchor="middle"
      >
        RE cheaper
      </text>
      <text
        x={px(dMin + (dMax - dMin) * 0.82)}
        y={belowLabelY}
        fill="rgba(198,40,40,0.3)"
        fontSize={10}
        fontWeight={500}
        textAnchor="middle"
      >
        Grid cheaper
      </text>
    </g>
  );
}

export default function QuadrantChart() {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const benchmarkMode = useDashboardStore((s) => s.benchmarkMode);
  const energyMode = useDashboardStore((s) => s.energyMode);

  const chartData = useMemo(() => {
    if (!scorecard) return [];
    return scorecard
      .map((row) => {
        const lcoe = getLcoeForMode(row, energyMode);
        const gridCost =
          benchmarkMode === 'bpp' && row.bpp_usd_mwh != null
            ? row.bpp_usd_mwh
            : row.dashboard_rate_usd_mwh;
        const tier = getEffectiveEconomicTier(row, energyMode);
        return {
          ...row,
          activeLcoe: lcoe ?? null,
          gridCost,
          economicTierColor: ECONOMIC_TIER_COLORS[tier],
        };
      })
      .filter((d) => d.activeLcoe != null && Number.isFinite(d.activeLcoe));
  }, [scorecard, benchmarkMode, energyMode]);

  const modeLabel = getModeLabel(energyMode);

  const domain = useMemo(() => {
    if (!chartData.length) return { min: 0, max: 200 };
    const allVals = chartData.flatMap((d) => [d.activeLcoe as number, d.gridCost]);
    const min = Math.floor(Math.min(...allVals) * 0.8);
    const max = Math.ceil(Math.max(...allVals) * 1.2);
    return { min: Math.max(0, min), max };
  }, [chartData]);

  if (!scorecard) {
    return <div className="flex items-center justify-center h-full text-zinc-600">Loading...</div>;
  }

  return (
    <div className="h-full w-full px-4 py-2">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 10, right: 20, bottom: 30, left: 20 }}>
          <XAxis
            type="number"
            dataKey="activeLcoe"
            name={`${modeLabel} LCOE`}
            domain={[domain.min, domain.max]}
            tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }}
            label={{
              value: `${modeLabel} LCOE ($/MWh)`,
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
          <Customized component={ParityAnnotation} />
          {/* Parity line: Y = X (LCOE = Grid Cost) */}
          <ReferenceLine
            segment={[
              { x: domain.min, y: domain.min },
              { x: domain.max, y: domain.max },
            ]}
            stroke="white"
            strokeOpacity={0.25}
            strokeDasharray="5 5"
          />
          <Tooltip
            content={
              <CustomTooltip
                energyMode={energyMode}
                benchmarkLabel={benchmarkMode === 'bpp' ? 'BPP' : 'Tariff'}
              />
            }
          />
          <Scatter data={chartData} shape={<CustomDot />} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

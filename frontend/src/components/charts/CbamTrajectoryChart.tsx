import { useMemo } from 'react';
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { ScorecardRow } from '../../lib/types';

// EU free allocation phase-out schedule (fixed in EU regulation)
const FREE_ALLOCATION: Record<number, number> = {
  2026: 0.975,
  2027: 0.95,
  2028: 0.9,
  2029: 0.775,
  2030: 0.515,
  2031: 0.39,
  2032: 0.265,
  2033: 0.14,
  2034: 0.0,
};

// EU ETS certificate price: €80/tCO₂ × 1.10 EUR/USD
const CERT_PRICE_USD = 88;

interface DataPoint {
  year: number;
  costCurrent: number;
  costSolar: number;
  savings: number;
  freeAllocationPct: number;
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
      <div className="font-medium">{d.year}</div>
      <div style={{ color: 'var(--text-muted)' }}>
        Free allocation: {(d.freeAllocationPct * 100).toFixed(1)}%
      </div>
      <div style={{ color: '#FF7043' }}>Grid: ${d.costCurrent.toFixed(0)}/t</div>
      <div style={{ color: '#4CAF50' }}>Solar: ${d.costSolar.toFixed(0)}/t</div>
      {d.savings > 0 && (
        <div className="font-medium mt-0.5" style={{ color: '#4CAF50' }}>
          Savings: ${d.savings.toFixed(0)}/t
        </div>
      )}
    </div>
  );
}

export default function CbamTrajectoryChart({ row }: { row: ScorecardRow }) {
  const data = useMemo(() => {
    const eiCurrent = row.cbam_emission_intensity_current;
    const eiSolar = row.cbam_emission_intensity_solar;
    if (eiCurrent == null || eiSolar == null) return [];

    const points: DataPoint[] = [];
    for (const [yearStr, freeAlloc] of Object.entries(FREE_ALLOCATION)) {
      const year = Number(yearStr);
      const exposureFraction = 1 - freeAlloc;
      const costCurrent = eiCurrent * CERT_PRICE_USD * exposureFraction;
      const costSolar = eiSolar * CERT_PRICE_USD * exposureFraction;
      points.push({
        year,
        costCurrent: Math.round(costCurrent * 100) / 100,
        costSolar: Math.round(costSolar * 100) / 100,
        savings: Math.round((costCurrent - costSolar) * 100) / 100,
        freeAllocationPct: freeAlloc,
      });
    }
    return points;
  }, [row.cbam_emission_intensity_current, row.cbam_emission_intensity_solar]);

  if (data.length === 0) return null;

  const maxCost = Math.max(...data.map((d) => d.costCurrent));

  return (
    <div
      className="rounded-lg p-3 mt-2"
      style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)' }}
    >
      <div className="text-[11px] mb-2" style={{ color: 'var(--text-muted)' }}>
        CBAM Cost Trajectory 2026–2034
        <span style={{ color: '#FF7043' }}> Grid</span>
        {' vs '}
        <span style={{ color: '#4CAF50' }}>Solar</span>
        {' ($/tonne)'}
      </div>
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
          <defs>
            <linearGradient id="cbamCurrentGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#FF7043" stopOpacity={0.4} />
              <stop offset="100%" stopColor="#FF7043" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="cbamSolarGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4CAF50" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#4CAF50" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="year"
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            tickLine={false}
            axisLine={{ stroke: 'var(--border-subtle)' }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            tickLine={false}
            axisLine={{ stroke: 'var(--border-subtle)' }}
            domain={[0, Math.ceil(maxCost / 50) * 50]}
            label={{
              value: '$/t',
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
            dataKey="costCurrent"
            stroke="#FF7043"
            strokeWidth={2}
            fill="url(#cbamCurrentGrad)"
          />
          <Area
            type="monotone"
            dataKey="costSolar"
            stroke="#4CAF50"
            strokeWidth={2}
            fill="url(#cbamSolarGrad)"
          />
        </AreaChart>
      </ResponsiveContainer>
      <div className="text-[9px] mt-1 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        EU free allocation phases out 2026–2034. Gap = CBAM cost avoided by switching to RE.
      </div>
    </div>
  );
}

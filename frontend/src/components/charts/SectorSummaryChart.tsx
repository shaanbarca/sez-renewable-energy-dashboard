import { useMemo } from 'react';
import { Bar, BarChart, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ACTION_FLAG_HIERARCHY_BY_MODE } from '../../lib/actionFlags';
import {
  ACTION_FLAG_COLORS,
  ACTION_FLAG_DESCRIPTIONS,
  ACTION_FLAG_LABELS,
} from '../../lib/constants';
import type { Sector } from '../../lib/siteTypes';
import type { ActionFlag, ScorecardRow } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

// Static column order for the action-flag table. Using the `overall` hierarchy
// gives the full superset of flags so column positions stay fixed regardless
// of which sectors currently have which flags populated.
const ACTION_FLAG_COLUMNS: ActionFlag[] = ACTION_FLAG_HIERARCHY_BY_MODE.overall;

const SECTOR_ORDER: Sector[] = [
  'steel',
  'cement',
  'aluminium',
  'fertilizer',
  'ammonia',
  'petrochemical',
  'nickel',
  'mixed',
];

const SECTOR_LABELS: Record<Sector, string> = {
  steel: 'Steel',
  cement: 'Cement',
  aluminium: 'Aluminium',
  fertilizer: 'Fertilizer',
  ammonia: 'Ammonia',
  petrochemical: 'Petrochemical',
  nickel: 'Nickel',
  mixed: 'Mixed (KEK)',
};

const SECTOR_COLORS: Record<Sector, string> = {
  steel: '#E53935',
  cement: '#AB47BC',
  aluminium: '#29B6F6',
  fertilizer: '#FFA726',
  ammonia: '#26A69A',
  petrochemical: '#7E57C2',
  nickel: '#FF7043',
  mixed: '#78909C',
};

type SectorRollup = {
  sector: Sector;
  label: string;
  count: number;
  cbamExposedCount: number;
  totalDemandGwh: number;
  totalCapacityTpa: number;
  cbamCost2026MUsd: number;
  cbamCost2030MUsd: number;
  cbamCost2034MUsd: number;
  actionFlagCounts: Record<string, number>;
};

function rollup(rows: ScorecardRow[]): SectorRollup[] {
  const map = new Map<Sector, SectorRollup>();
  for (const s of SECTOR_ORDER) {
    map.set(s, {
      sector: s,
      label: SECTOR_LABELS[s],
      count: 0,
      cbamExposedCount: 0,
      totalDemandGwh: 0,
      totalCapacityTpa: 0,
      cbamCost2026MUsd: 0,
      cbamCost2030MUsd: 0,
      cbamCost2034MUsd: 0,
      actionFlagCounts: {},
    });
  }
  for (const r of rows) {
    const sec = (r.sector ?? 'mixed') as Sector;
    const entry = map.get(sec);
    if (!entry) continue;
    entry.count += 1;
    if (r.cbam_exposed) entry.cbamExposedCount += 1;
    if (typeof r.demand_2030_gwh === 'number') entry.totalDemandGwh += r.demand_2030_gwh;
    const tpa = r.capacity_annual_tonnes ?? 0;
    entry.totalCapacityTpa += tpa;
    // CBAM cost in USD/tonne × annual tonnes → $/yr → /1e6 → $M/yr
    if (typeof r.cbam_cost_2026_usd_per_tonne === 'number') {
      entry.cbamCost2026MUsd += (r.cbam_cost_2026_usd_per_tonne * tpa) / 1e6;
    }
    if (typeof r.cbam_cost_2030_usd_per_tonne === 'number') {
      entry.cbamCost2030MUsd += (r.cbam_cost_2030_usd_per_tonne * tpa) / 1e6;
    }
    if (typeof r.cbam_cost_2034_usd_per_tonne === 'number') {
      entry.cbamCost2034MUsd += (r.cbam_cost_2034_usd_per_tonne * tpa) / 1e6;
    }
    const flag = r.action_flag;
    entry.actionFlagCounts[flag] = (entry.actionFlagCounts[flag] ?? 0) + 1;
  }
  // Drop sectors with no sites
  return SECTOR_ORDER.map((s) => map.get(s)!).filter((r) => r.count > 0);
}

function CbamBarTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
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
      <div className="font-medium mb-1">{label}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ color: p.color }}>
          {p.name}: ${p.value.toFixed(1)}M/yr
        </div>
      ))}
    </div>
  );
}

function DemandTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload?: SectorRollup }[];
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
      <div className="font-medium mb-1">{d.label}</div>
      <div style={{ color: 'var(--text-muted)' }}>
        Sites: {d.count}
        {d.cbamExposedCount > 0 ? ` (${d.cbamExposedCount} CBAM-exposed)` : ''}
      </div>
      <div>
        2030 Demand: {d.totalDemandGwh.toLocaleString(undefined, { maximumFractionDigits: 0 })} GWh
      </div>
      {d.totalCapacityTpa > 0 && <div>Capacity: {(d.totalCapacityTpa / 1e6).toFixed(1)} Mt/yr</div>}
    </div>
  );
}

export default function SectorSummaryChart() {
  const scorecard = useDashboardStore((s) => s.scorecard);

  const data = useMemo(() => {
    if (!scorecard?.length) return [];
    return rollup(scorecard);
  }, [scorecard]);

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-500 text-sm">
        Loading scorecard...
      </div>
    );
  }

  const cbamChartData = data.map((d) => ({
    label: d.label,
    '2026': Number(d.cbamCost2026MUsd.toFixed(2)),
    '2030': Number(d.cbamCost2030MUsd.toFixed(2)),
    '2034': Number(d.cbamCost2034MUsd.toFixed(2)),
  }));

  const hasCbam = data.some(
    (d) => d.cbamCost2026MUsd > 0 || d.cbamCost2030MUsd > 0 || d.cbamCost2034MUsd > 0,
  );

  return (
    <div className="h-full w-full overflow-y-auto px-4 py-3 flex flex-col gap-4">
      {/* CBAM cost trajectory by sector */}
      {hasCbam && (
        <div className="shrink-0">
          <div className="text-xs mb-1 font-medium" style={{ color: 'var(--text-primary)' }}>
            CBAM Cost Exposure by Sector ($M/year)
          </div>
          <div className="text-[10px] mb-1" style={{ color: 'var(--text-muted)' }}>
            Annual CBAM certificate cost at current grid emission intensity × sector production. EU
            free allocation phases out 2026–2034.
          </div>
          <div style={{ height: 180 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={cbamChartData} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
                  tickLine={false}
                  axisLine={{ stroke: 'var(--border-subtle)' }}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
                  tickLine={false}
                  axisLine={{ stroke: 'var(--border-subtle)' }}
                  label={{
                    value: '$M/yr',
                    angle: -90,
                    position: 'insideLeft',
                    offset: 10,
                    fontSize: 9,
                    fill: 'var(--text-muted)',
                  }}
                />
                <Tooltip content={<CbamBarTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <Bar dataKey="2026" fill="#FFB74D" />
                <Bar dataKey="2030" fill="#FB8C00" />
                <Bar dataKey="2034" fill="#C62828" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* 2030 demand by sector */}
      <div className="shrink-0">
        <div className="text-xs mb-1 font-medium" style={{ color: 'var(--text-primary)' }}>
          2030 Electricity Demand by Sector (GWh)
        </div>
        <div style={{ height: 180 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <XAxis
                dataKey="label"
                tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
                tickLine={false}
                axisLine={{ stroke: 'var(--border-subtle)' }}
              />
              <YAxis
                tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
                tickLine={false}
                axisLine={{ stroke: 'var(--border-subtle)' }}
                label={{
                  value: 'GWh',
                  angle: -90,
                  position: 'insideLeft',
                  offset: 10,
                  fontSize: 9,
                  fill: 'var(--text-muted)',
                }}
              />
              <Tooltip content={<DemandTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
              <Bar dataKey="totalDemandGwh">
                {data.map((d) => (
                  <Cell key={d.sector} fill={SECTOR_COLORS[d.sector]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Action flag distribution table */}
      <div className="shrink-0 pb-2">
        <div className="text-xs mb-1 font-medium" style={{ color: 'var(--text-primary)' }}>
          Sites by Action Flag
        </div>
        <div className="overflow-x-auto">
          <table className="text-[11px] w-full border-collapse">
            <thead>
              <tr style={{ color: 'var(--text-muted)' }}>
                <th
                  className="text-left py-1 pr-3 font-medium cursor-help"
                  title="Sector — industrial sector rollup (CBAM-exposed sectors plus mixed KEKs)."
                >
                  Sector
                </th>
                <th
                  className="text-right py-1 pr-3 font-medium cursor-help"
                  title="Sites — total number of sites (KEKs + industrial facilities) in this sector."
                >
                  Sites
                </th>
                {ACTION_FLAG_COLUMNS.map((f) => {
                  const label = ACTION_FLAG_LABELS[f] ?? f;
                  const desc = ACTION_FLAG_DESCRIPTIONS[f];
                  return (
                    <th
                      key={f}
                      className="text-right py-1 pr-3 font-medium whitespace-nowrap cursor-help"
                      style={{ color: ACTION_FLAG_COLORS[f] }}
                      title={desc ? `${label} — ${desc}` : label}
                    >
                      {label}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr
                  key={d.sector}
                  style={{
                    color: 'var(--text-primary)',
                    borderTop: '1px solid var(--border-subtle)',
                  }}
                >
                  <td className="py-1 pr-3">
                    <span
                      className="inline-block w-2 h-2 rounded-sm mr-1.5 align-middle"
                      style={{ background: SECTOR_COLORS[d.sector] }}
                    />
                    {d.label}
                  </td>
                  <td className="text-right py-1 pr-3">{d.count}</td>
                  {ACTION_FLAG_COLUMNS.map((f) => {
                    const n = d.actionFlagCounts[f] ?? 0;
                    return (
                      <td
                        key={f}
                        className="text-right py-1 pr-3"
                        style={{ color: n > 0 ? 'var(--text-primary)' : 'var(--text-muted)' }}
                      >
                        {n > 0 ? n : '·'}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

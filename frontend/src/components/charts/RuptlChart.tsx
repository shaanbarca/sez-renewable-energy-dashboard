import { useEffect, useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { fetchRuptlMetrics } from '../../lib/api';
import { RUPTL_REGION_COLORS } from '../../lib/constants';
import { formatGridRegion } from '../../lib/format';
import { useDashboardStore } from '../../store/dashboard';

interface RuptlRow {
  grid_region_id: string;
  year: number;
  plts_new_mw_re_base: number;
  plts_new_mw_ared: number;
}

interface RuptlResponse {
  pipeline: RuptlRow[];
  region_colors: Record<string, string>;
}

interface PivotedRow {
  year: number;
  [region: string]: number;
}

export default function RuptlChart() {
  const selectedKek = useDashboardStore((s) => s.selectedKek);
  const scorecard = useDashboardStore((s) => s.scorecard);
  const [data, setData] = useState<RuptlRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchRuptlMetrics()
      .then((res) => {
        if (cancelled) return;
        const typed = res as RuptlResponse;
        setData(typed.pipeline ?? []);
        setLoading(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(String(err));
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const { pivoted, regions } = useMemo(() => {
    if (!data.length) return { pivoted: [], regions: [] };

    const regionSet = new Set<string>();
    const yearMap = new Map<number, Record<string, number>>();

    for (const row of data) {
      regionSet.add(row.grid_region_id);
      if (!yearMap.has(row.year)) {
        yearMap.set(row.year, {});
      }
      const entry = yearMap.get(row.year)!;
      entry[row.grid_region_id] = (entry[row.grid_region_id] ?? 0) + (row.plts_new_mw_re_base ?? 0);
    }

    const regions = Array.from(regionSet).sort();
    const annual: PivotedRow[] = Array.from(yearMap.entries())
      .sort(([a], [b]) => a - b)
      .map(([year, vals]) => ({ year, ...vals }));

    // Accumulate: each year = sum of all previous years + current
    const cumulative: PivotedRow[] = [];
    const running: Record<string, number> = {};
    for (const row of annual) {
      const cum: PivotedRow = { year: row.year };
      for (const region of regions) {
        running[region] = (running[region] ?? 0) + (row[region] ?? 0);
        cum[region] = running[region];
      }
      cumulative.push(cum);
    }

    return { pivoted: cumulative, regions };
  }, [data]);

  const highlightRegion = useMemo(() => {
    if (!selectedKek || !scorecard) return null;
    const row = scorecard.find((r) => r.kek_id === selectedKek);
    return row?.grid_region_id ?? null;
  }, [selectedKek, scorecard]);

  const post2030Stats = useMemo(() => {
    if (!highlightRegion || !data.length) return null;
    const regionRows = data.filter((r) => r.grid_region_id === highlightRegion);
    const totalMW = regionRows.reduce((sum, r) => sum + (r.plts_new_mw_re_base ?? 0), 0);
    const post2030MW = regionRows
      .filter((r) => r.year > 2030)
      .reduce((sum, r) => sum + (r.plts_new_mw_re_base ?? 0), 0);
    if (totalMW === 0) return null;
    const pct = (post2030MW / totalMW) * 100;
    return {
      label: formatGridRegion(highlightRegion),
      totalMW: Math.round(totalMW),
      post2030MW: Math.round(post2030MW),
      pct,
      isPlanLate: pct > 60,
    };
  }, [highlightRegion, data]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-600">
        Loading RUPTL data...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full text-zinc-500 text-sm">
        Failed to load RUPTL data
      </div>
    );
  }

  return (
    <div className="h-full w-full px-4 py-2 flex flex-col">
      {post2030Stats && (
        <div
          className="flex items-center gap-3 px-3 py-1.5 rounded text-xs mb-1 shrink-0"
          style={{
            background: post2030Stats.isPlanLate
              ? 'rgba(123, 31, 162, 0.15)'
              : 'rgba(255, 255, 255, 0.05)',
            color: 'var(--text-primary)',
            border: post2030Stats.isPlanLate
              ? '1px solid rgba(123, 31, 162, 0.3)'
              : '1px solid rgba(255, 255, 255, 0.1)',
          }}
        >
          <span>
            <strong>{post2030Stats.label}</strong>: {post2030Stats.pct.toFixed(0)}% of solar
            additions are post-2030 ({post2030Stats.post2030MW} / {post2030Stats.totalMW} MW)
          </span>
          {post2030Stats.isPlanLate && (
            <span style={{ color: '#7B1FA2', fontWeight: 600 }}>Plan Late</span>
          )}
        </div>
      )}
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={pivoted} margin={{ top: 10, right: 20, bottom: 30, left: 20 }}>
            <XAxis
              dataKey="year"
              tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }}
              stroke="rgba(255,255,255,0.1)"
            />
            <YAxis
              tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }}
              label={{
                value: 'Cumulative Capacity (MW)',
                angle: -90,
                position: 'insideLeft',
                offset: -5,
                fill: 'rgba(255,255,255,0.6)',
                fontSize: 12,
              }}
              stroke="rgba(255,255,255,0.1)"
            />
            <ReferenceLine
              x={2030}
              stroke="var(--text-muted)"
              strokeDasharray="4 4"
              strokeWidth={1}
            />
            <Tooltip
              position={{ y: 0 }}
              offset={10}
              contentStyle={{
                background: 'var(--popup-bg)',
                border: '1px solid var(--popup-border)',
                borderRadius: 4,
                boxShadow: 'var(--popup-shadow)',
                color: 'var(--text-primary)',
                fontSize: 12,
              }}
            />
            <Legend wrapperStyle={{ color: '#e0e0e0', fontSize: 11 }} />
            {regions.map((region) => {
              const dimmed = highlightRegion != null && highlightRegion !== region;
              return (
                <Area
                  key={region}
                  type="monotone"
                  dataKey={region}
                  stackId="a"
                  fill={RUPTL_REGION_COLORS[region] ?? '#666'}
                  stroke={RUPTL_REGION_COLORS[region] ?? '#666'}
                  fillOpacity={dimmed ? 0.15 : 0.6}
                  strokeOpacity={dimmed ? 0.3 : 1}
                  strokeWidth={highlightRegion === region ? 2 : 1}
                  name={formatGridRegion(region)}
                />
              );
            })}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

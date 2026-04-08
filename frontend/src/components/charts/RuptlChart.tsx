import { useEffect, useMemo, useState } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts';
import { fetchRuptlMetrics } from '../../lib/api';
import { RUPTL_REGION_COLORS } from '../../lib/constants';

interface RuptlRow {
  region: string;
  year: number;
  capacity_mw: number;
  technology: string;
  status: string;
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
      regionSet.add(row.region);
      if (!yearMap.has(row.year)) {
        yearMap.set(row.year, {});
      }
      const entry = yearMap.get(row.year)!;
      entry[row.region] = (entry[row.region] ?? 0) + row.capacity_mw;
    }

    const regions = Array.from(regionSet).sort();
    const pivoted: PivotedRow[] = Array.from(yearMap.entries())
      .sort(([a], [b]) => a - b)
      .map(([year, vals]) => ({ year, ...vals }));

    return { pivoted, regions };
  }, [data]);

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
    <div className="h-full w-full px-4 py-2">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={pivoted} margin={{ top: 10, right: 20, bottom: 30, left: 20 }}>
          <XAxis
            dataKey="year"
            tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }}
            stroke="rgba(255,255,255,0.1)"
          />
          <YAxis
            tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 11 }}
            label={{
              value: 'Capacity (MW)',
              angle: -90,
              position: 'insideLeft',
              offset: -5,
              fill: 'rgba(255,255,255,0.6)',
              fontSize: 12,
            }}
            stroke="rgba(255,255,255,0.1)"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e1e1e',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 4,
              color: '#e0e0e0',
              fontSize: 12,
            }}
          />
          <Legend
            wrapperStyle={{ color: '#e0e0e0', fontSize: 11 }}
          />
          {regions.map((region) => (
            <Bar
              key={region}
              dataKey={region}
              stackId="a"
              fill={RUPTL_REGION_COLORS[region] ?? '#666'}
              name={region}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

import { useMemo, useState } from 'react';
import { ECONOMIC_TIER_COLORS, ECONOMIC_TIER_LABELS } from '../../../lib/constants';
import { type FlipDiffRow, flipDiffToCsv } from '../../../lib/flipDiff';
import { useDashboardStore } from '../../../store/dashboard';

type SortKey = 'site_name' | 'sector' | 'tier' | 'lcoe' | 'delta_lcoe' | 'gap_delta' | 'direction';

type SortDir = 'asc' | 'desc';

const DIRECTION_ORDER: Record<FlipDiffRow['flip_direction'], number> = {
  improved: 0,
  worsened: 1,
  unchanged: 2,
};

const DIRECTION_LABEL: Record<FlipDiffRow['flip_direction'], string> = {
  improved: '↑ better',
  worsened: '↓ worse',
  unchanged: '—',
};

const DIRECTION_COLOR: Record<FlipDiffRow['flip_direction'], string> = {
  improved: '#4CAF50',
  worsened: '#F44336',
  unchanged: 'var(--text-muted)',
};

function fmtNum(v: number | null, digits = 1): string {
  if (v == null || !Number.isFinite(v)) return '—';
  return v.toFixed(digits);
}

function fmtDelta(v: number | null, digits = 1): string {
  if (v == null || !Number.isFinite(v)) return '—';
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(digits)}`;
}

function gapDeltaOf(row: FlipDiffRow): number | null {
  if (row.gap_baseline_pct == null || row.gap_flip_pct == null) return null;
  return row.gap_flip_pct - row.gap_baseline_pct;
}

function deltaColor(v: number | null, invert = false): string {
  if (v == null || !Number.isFinite(v) || v === 0) return 'var(--text-muted)';
  const good = invert ? v > 0 : v < 0;
  return good ? '#4CAF50' : '#F44336';
}

export default function FlipDiffTable({ rows }: { rows: FlipDiffRow[] }) {
  const [sortKey, setSortKey] = useState<SortKey>('direction');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const selectSite = useDashboardStore((s) => s.selectSite);

  const sorted = useMemo(() => {
    const copy = [...rows];
    copy.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case 'site_name':
          cmp = a.site_name.localeCompare(b.site_name);
          break;
        case 'sector':
          cmp = a.sector.localeCompare(b.sector);
          break;
        case 'tier':
          cmp = a.tier_flip.localeCompare(b.tier_flip);
          break;
        case 'lcoe': {
          const av = a.lcoe_flip ?? Number.POSITIVE_INFINITY;
          const bv = b.lcoe_flip ?? Number.POSITIVE_INFINITY;
          cmp = av - bv;
          break;
        }
        case 'delta_lcoe': {
          const av = a.delta_lcoe ?? Number.POSITIVE_INFINITY;
          const bv = b.delta_lcoe ?? Number.POSITIVE_INFINITY;
          cmp = av - bv;
          break;
        }
        case 'gap_delta': {
          const av = gapDeltaOf(a) ?? Number.POSITIVE_INFINITY;
          const bv = gapDeltaOf(b) ?? Number.POSITIVE_INFINITY;
          cmp = av - bv;
          break;
        }
        case 'direction':
          cmp = DIRECTION_ORDER[a.flip_direction] - DIRECTION_ORDER[b.flip_direction];
          if (cmp === 0) {
            const av = a.delta_lcoe ?? 0;
            const bv = b.delta_lcoe ?? 0;
            cmp = av - bv;
          }
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return copy;
  }, [rows, sortKey, sortDir]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const handleExport = () => {
    const csv = flipDiffToCsv(rows);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `flip_diff_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const sortIcon = (key: SortKey) => {
    if (sortKey !== key) return '';
    return sortDir === 'asc' ? ' ↑' : ' ↓';
  };

  const HeaderBtn = ({ label, k }: { label: string; k: SortKey }) => (
    <button
      type="button"
      onClick={() => handleSort(k)}
      className="text-left text-[10px] uppercase tracking-wider font-medium"
      style={{ color: sortKey === k ? 'var(--accent)' : 'var(--text-muted)' }}
    >
      {label}
      {sortIcon(k)}
    </button>
  );

  return (
    <div className="h-full flex flex-col">
      {/* Header bar with export */}
      <div
        className="flex items-center justify-between px-3 py-1.5"
        style={{ borderBottom: '1px solid var(--border-subtle)' }}
      >
        <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
          {rows.length} sites — click a row to inspect on map
        </div>
        <button
          type="button"
          onClick={handleExport}
          className="text-[10px] px-2 py-1 rounded"
          style={{
            background: 'var(--card-bg)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-secondary)',
          }}
        >
          Export CSV
        </button>
      </div>

      {/* Table */}
      <div
        className="flex-1 overflow-auto"
        style={{
          scrollbarWidth: 'thin',
          scrollbarColor: 'var(--scrollbar-thumb) transparent',
        }}
      >
        <table className="w-full text-[11px] tabular-nums">
          <thead className="sticky top-0" style={{ background: 'var(--panel-bg)', zIndex: 1 }}>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <th className="px-3 py-1.5">
                <HeaderBtn label="Site" k="site_name" />
              </th>
              <th className="px-2 py-1.5">
                <HeaderBtn label="Sector" k="sector" />
              </th>
              <th className="px-2 py-1.5">
                <HeaderBtn label="Tier (flip)" k="tier" />
              </th>
              <th className="px-2 py-1.5 text-right">
                <HeaderBtn label="Direction" k="direction" />
              </th>
              <th className="px-2 py-1.5 text-right">
                <HeaderBtn label="LCOE flip" k="lcoe" />
              </th>
              <th className="px-2 py-1.5 text-right">
                <HeaderBtn label="Δ LCOE" k="delta_lcoe" />
              </th>
              <th className="px-2 py-1.5 text-right">
                <HeaderBtn label="Δ Gap %" k="gap_delta" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => {
              const gapDelta = gapDeltaOf(r);
              return (
                <tr
                  key={r.site_id}
                  onClick={() => selectSite(r.site_id)}
                  className="cursor-pointer transition-colors"
                  style={{ borderBottom: '1px solid var(--border-subtle)' }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'var(--hover-bg, rgba(255,255,255,0.04))';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <td className="px-3 py-1.5" style={{ color: 'var(--text-value)' }}>
                    {r.site_name}
                  </td>
                  <td className="px-2 py-1.5" style={{ color: 'var(--text-secondary)' }}>
                    {r.sector}
                  </td>
                  <td className="px-2 py-1.5">
                    {r.tier_baseline !== r.tier_flip ? (
                      <span>
                        <span style={{ color: ECONOMIC_TIER_COLORS[r.tier_baseline] }}>
                          {ECONOMIC_TIER_LABELS[r.tier_baseline]}
                        </span>
                        <span style={{ color: 'var(--text-muted)' }}> → </span>
                        <span style={{ color: ECONOMIC_TIER_COLORS[r.tier_flip] }}>
                          {ECONOMIC_TIER_LABELS[r.tier_flip]}
                        </span>
                      </span>
                    ) : (
                      <span style={{ color: ECONOMIC_TIER_COLORS[r.tier_flip] }}>
                        {ECONOMIC_TIER_LABELS[r.tier_flip]}
                      </span>
                    )}
                  </td>
                  <td
                    className="px-2 py-1.5 text-right"
                    style={{ color: DIRECTION_COLOR[r.flip_direction], fontWeight: 500 }}
                  >
                    {DIRECTION_LABEL[r.flip_direction]}
                  </td>
                  <td className="px-2 py-1.5 text-right" style={{ color: 'var(--text-value)' }}>
                    {fmtNum(r.lcoe_flip, 1)}
                  </td>
                  <td
                    className="px-2 py-1.5 text-right"
                    style={{ color: deltaColor(r.delta_lcoe) }}
                  >
                    {fmtDelta(r.delta_lcoe, 1)}
                  </td>
                  <td className="px-2 py-1.5 text-right" style={{ color: deltaColor(gapDelta) }}>
                    {fmtDelta(gapDelta, 1)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

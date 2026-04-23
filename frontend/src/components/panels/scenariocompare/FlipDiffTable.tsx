import { useMemo, useState } from 'react';
import {
  ECONOMIC_TIER_COLORS,
  ECONOMIC_TIER_LABELS,
  INFRA_READINESS_COLORS,
  INFRA_READINESS_HIERARCHY,
  INFRA_READINESS_LABELS,
} from '../../../lib/constants';
import { COST_BASIS_LABELS } from '../../../lib/costBasis';
import { type FlipDiffRow, flipDiffToCsv } from '../../../lib/flipDiff';
import type { CostBasis } from '../../../lib/types';
import { useDashboardStore } from '../../../store/dashboard';

type SortKey =
  | 'site_name'
  | 'sector'
  | 'tier'
  | 'infra'
  | 'lcoe'
  | 'delta_lcoe'
  | 'lcoe_secondary'
  | 'delta_lcoe_secondary'
  | 'gap_delta'
  | 'direction';

const INFRA_RANK: Record<string, number> = INFRA_READINESS_HIERARCHY.reduce(
  (acc, key, idx) => {
    acc[key] = idx;
    return acc;
  },
  {} as Record<string, number>,
);

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

export default function FlipDiffTable({
  rows,
  secondaryRows = null,
  secondaryBasis = null,
}: {
  rows: FlipDiffRow[];
  secondaryRows?: FlipDiffRow[] | null;
  secondaryBasis?: CostBasis | null;
}) {
  const [sortKey, setSortKey] = useState<SortKey>('direction');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const selectSite = useDashboardStore((s) => s.selectSite);
  const costBasis = useDashboardStore((s) => s.costBasis);

  const secondaryById = useMemo(() => {
    if (!secondaryRows) return null;
    const m = new Map<string, FlipDiffRow>();
    for (const r of secondaryRows) m.set(r.site_id, r);
    return m;
  }, [secondaryRows]);

  const hasSecondary = secondaryById != null && secondaryBasis != null;

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
        case 'infra':
          cmp = (INFRA_RANK[a.infra_flip] ?? 99) - (INFRA_RANK[b.infra_flip] ?? 99);
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
        case 'lcoe_secondary': {
          const av = secondaryById?.get(a.site_id)?.lcoe_flip ?? Number.POSITIVE_INFINITY;
          const bv = secondaryById?.get(b.site_id)?.lcoe_flip ?? Number.POSITIVE_INFINITY;
          cmp = av - bv;
          break;
        }
        case 'delta_lcoe_secondary': {
          const av = secondaryById?.get(a.site_id)?.delta_lcoe ?? Number.POSITIVE_INFINITY;
          const bv = secondaryById?.get(b.site_id)?.delta_lcoe ?? Number.POSITIVE_INFINITY;
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
  }, [rows, sortKey, sortDir, secondaryById]);

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
          {hasSecondary && secondaryBasis && (
            <span className="ml-2" style={{ color: 'var(--text-secondary)' }}>
              · comparing {COST_BASIS_LABELS[costBasis]} vs {COST_BASIS_LABELS[secondaryBasis]}
            </span>
          )}
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
              <th className="px-2 py-1.5">
                <HeaderBtn label="Infra Ready (flip)" k="infra" />
              </th>
              <th className="px-2 py-1.5 text-right">
                <HeaderBtn label="Direction" k="direction" />
              </th>
              <th className="px-2 py-1.5 text-right">
                <HeaderBtn label={`${COST_BASIS_LABELS[costBasis]} flip`} k="lcoe" />
              </th>
              <th className="px-2 py-1.5 text-right">
                <HeaderBtn
                  label={hasSecondary ? `Δ ${COST_BASIS_LABELS[costBasis]}` : 'Δ $/MWh'}
                  k="delta_lcoe"
                />
              </th>
              {hasSecondary && secondaryBasis && (
                <>
                  <th
                    className="px-2 py-1.5 text-right"
                    style={{ borderLeft: '1px solid var(--border-subtle)' }}
                  >
                    <HeaderBtn
                      label={`${COST_BASIS_LABELS[secondaryBasis]} flip`}
                      k="lcoe_secondary"
                    />
                  </th>
                  <th className="px-2 py-1.5 text-right">
                    <HeaderBtn
                      label={`Δ ${COST_BASIS_LABELS[secondaryBasis]}`}
                      k="delta_lcoe_secondary"
                    />
                  </th>
                </>
              )}
              <th
                className="px-2 py-1.5 text-right"
                style={hasSecondary ? { borderLeft: '1px solid var(--border-subtle)' } : undefined}
              >
                <HeaderBtn label="Δ Gap %" k="gap_delta" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((r) => {
              const gapDelta = gapDeltaOf(r);
              const sec = secondaryById?.get(r.site_id) ?? null;
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
                  <td className="px-2 py-1.5" style={{ whiteSpace: 'nowrap' }}>
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
                  <td className="px-2 py-1.5" style={{ whiteSpace: 'nowrap' }}>
                    {r.infra_baseline !== r.infra_flip ? (
                      <span>
                        <span style={{ color: INFRA_READINESS_COLORS[r.infra_baseline] }}>
                          {INFRA_READINESS_LABELS[r.infra_baseline]}
                        </span>
                        <span style={{ color: 'var(--text-muted)' }}> → </span>
                        <span style={{ color: INFRA_READINESS_COLORS[r.infra_flip] }}>
                          {INFRA_READINESS_LABELS[r.infra_flip]}
                        </span>
                      </span>
                    ) : (
                      <span style={{ color: INFRA_READINESS_COLORS[r.infra_flip] }}>
                        {INFRA_READINESS_LABELS[r.infra_flip]}
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
                  {hasSecondary && (
                    <>
                      <td
                        className="px-2 py-1.5 text-right"
                        style={{
                          color: 'var(--text-value)',
                          borderLeft: '1px solid var(--border-subtle)',
                        }}
                      >
                        {fmtNum(sec?.lcoe_flip ?? null, 1)}
                      </td>
                      <td
                        className="px-2 py-1.5 text-right"
                        style={{ color: deltaColor(sec?.delta_lcoe ?? null) }}
                      >
                        {fmtDelta(sec?.delta_lcoe ?? null, 1)}
                      </td>
                    </>
                  )}
                  <td
                    className="px-2 py-1.5 text-right"
                    style={{
                      color: deltaColor(gapDelta),
                      ...(hasSecondary ? { borderLeft: '1px solid var(--border-subtle)' } : {}),
                    }}
                  >
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

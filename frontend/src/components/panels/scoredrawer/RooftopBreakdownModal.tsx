import { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchSiteRooftopBreakdown } from '../../../lib/api';
import type {
  RooftopBreakdownBuilding,
  RooftopBreakdownResponse,
  RooftopExclusionReason,
  RooftopFootprintClass,
} from '../../../lib/types';

// Display label for the 9 footprint classes (locked /plan-eng-review decision 1C).
// Neutral geometric language — explicitly NOT industrial vocab like "warehouse"
// because we measure footprint geometry, not OSM-tagged purpose.
const FOOTPRINT_CLASS_LABELS: Record<RooftopFootprintClass, string> = {
  standard_roof: 'Standard roof',
  elongated: 'Elongated (shed)',
  possibly_round: 'Round shape',
  complex: 'Complex shape',
  tank_silo: 'Tank/silo shape',
  conveyor: 'Conveyor',
  too_small: 'Too small',
  residential: 'Residential cluster',
  isolated_cluster: 'Isolated cluster',
};

// Human-readable exclusion reason for the audit (#62) reviewer. Disambiguates
// the overloaded tank_silo category: osm_* tags vs geometric shape.
const EXCLUSION_REASON_LABELS: Record<RooftopExclusionReason, string> = {
  none: '—',
  osm_tank: 'OSM tank',
  osm_basin: 'OSM basin',
  osm_water: 'OSM water',
  geometric_tank_silo: 'Geometric tank/silo',
  geometric_complex: 'Geometric complex',
  geometric_round: 'Geometric round',
  geometric_too_small: 'Geometric too small',
  residential_cluster: 'Residential cluster',
  isolated_cluster: 'Isolated cluster',
};

type SortKey = 'building_id' | 'area_m2' | 'footprint_class' | 'buildable_roof_area_m2';
type SortDir = 'asc' | 'desc';

function csvCell(val: unknown): string {
  if (val == null) return '';
  const s = String(val);
  return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s.replace(/"/g, '""')}"` : s;
}

interface RooftopBreakdownModalProps {
  open: boolean;
  onClose: () => void;
  siteId: string;
}

export function RooftopBreakdownModal({ open, onClose, siteId }: RooftopBreakdownModalProps) {
  const [data, setData] = useState<RooftopBreakdownResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>('area_m2');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    setData(null);
    fetchSiteRooftopBreakdown(siteId)
      .then((d) => setData(d))
      .catch((e) => setError(e?.message ?? 'Failed to load rooftop breakdown'))
      .finally(() => setLoading(false));
  }, [open, siteId]);

  // Esc closes modal
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) onClose();
    },
    [onClose],
  );

  const sortedBuildings = useMemo<RooftopBreakdownBuilding[]>(() => {
    if (!data) return [];
    const arr = [...data.buildings];
    arr.sort((a, b) => {
      const va = a[sortKey] as string | number;
      const vb = b[sortKey] as string | number;
      const cmp = va < vb ? -1 : va > vb ? 1 : 0;
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return arr;
  }, [data, sortKey, sortDir]);

  const toggleSort = useCallback(
    (key: SortKey) => {
      if (sortKey === key) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortKey(key);
        setSortDir('desc');
      }
    },
    [sortKey],
  );

  const handleDownloadCsv = useCallback(() => {
    if (!data) return;
    const headers = [
      'site_id',
      'site_name',
      'estate_area_m2',
      'building_id',
      'building_area_m2',
      'footprint_class',
      'exclusion_reason',
      'usability_multiplier',
      'buildable_roof_area_m2',
    ];
    const lines = sortedBuildings.map((b) =>
      [
        data.site_id,
        data.site_name,
        data.estate_area_m2 ?? '',
        b.building_id,
        b.area_m2,
        b.footprint_class,
        b.exclusion_reason,
        b.usability_multiplier,
        b.buildable_roof_area_m2,
      ]
        .map(csvCell)
        .join(','),
    );
    const metadata = [
      '',
      '--- Export Metadata ---',
      `Total buildings,${data.totals.building_count}`,
      `Total footprint (m²),${data.totals.total_footprint_m2.toFixed(2)}`,
      `Total buildable roof (m²),${data.totals.usable_roof_area_m2.toFixed(2)}`,
      `Building data confidence,${data.building_data_confidence ?? ''}`,
      `Reason flagged,${data.building_data_reason_flagged ?? ''}`,
      `Export date,${new Date().toISOString().slice(0, 10)}`,
      '',
      'Methodology: Footprint class is inferred from building geometry (§14 classifier),',
      'NOT from OSM tags. exclusion_reason disambiguates osm_* (semantic) vs',
      'geometric_* (shape-based). See docs/METHODOLOGY_CONSOLIDATED.md §14.',
    ].join('\n');
    const csv = [headers.join(','), ...lines, metadata].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${data.site_id}_rooftop_breakdown_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [data, sortedBuildings]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={handleBackdropClick}
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}
    >
      <div
        className="relative w-full max-w-4xl rounded-2xl overflow-hidden flex flex-col"
        style={{
          background: 'rgba(24, 24, 28, 0.92)',
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 24px 80px rgba(0,0,0,0.5)',
          maxHeight: '90vh',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-3 shrink-0"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}
        >
          <div>
            <h2 className="text-base font-semibold text-white">Rooftop breakdown</h2>
            <p className="text-[11px] text-zinc-400 mt-0.5">
              {data?.site_name ?? siteId} &middot; per-building footprint detail
            </p>
            <p className="text-[10px] text-zinc-500 mt-1 italic max-w-2xl">
              Footprint class is inferred from building geometry (§14 classifier), NOT from OSM
              tags. <strong>exclusion_reason</strong> distinguishes OSM-tagged exclusions
              (osm_tank/basin/water) from geometric shape filters.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="text-zinc-400 hover:text-white text-xl leading-none px-2 py-1 rounded hover:bg-white/10 transition-colors cursor-pointer"
          >
            &times;
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto px-5 py-3 min-h-[200px]">
          {loading && (
            <div className="text-sm text-zinc-400 text-center py-12">Loading buildings…</div>
          )}
          {error && (
            <div className="text-sm text-red-400 text-center py-12">
              Error loading rooftop breakdown: {error}
            </div>
          )}
          {!loading && !error && data && data.buildings.length === 0 && (
            <div className="text-sm text-zinc-400 text-center py-12 space-y-2">
              <p>No buildings detected for this site.</p>
              {data.building_data_reason_flagged && (
                <p className="text-xs text-zinc-500">
                  Reason: {data.building_data_reason_flagged.replace(/_/g, ' ')}
                </p>
              )}
              <p className="text-xs text-zinc-500">
                See{' '}
                <a
                  href="https://github.com/shaanbarca/eez/issues/62"
                  target="_blank"
                  rel="noreferrer"
                  className="underline hover:text-zinc-300"
                >
                  #62 (rooftop audit)
                </a>{' '}
                for the disposition of zero-building sites.
              </p>
            </div>
          )}
          {!loading && !error && data && data.buildings.length > 0 && (
            <table className="w-full text-xs tabular-nums">
              <thead className="sticky top-0" style={{ background: 'rgba(24,24,28,0.96)' }}>
                <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                  <Th
                    onClick={() => toggleSort('building_id')}
                    active={sortKey === 'building_id'}
                    dir={sortDir}
                    align="left"
                  >
                    Building ID
                  </Th>
                  <Th
                    onClick={() => toggleSort('area_m2')}
                    active={sortKey === 'area_m2'}
                    dir={sortDir}
                    align="right"
                  >
                    Area (m²)
                  </Th>
                  <Th
                    onClick={() => toggleSort('footprint_class')}
                    active={sortKey === 'footprint_class'}
                    dir={sortDir}
                    align="left"
                  >
                    Footprint class
                  </Th>
                  <th
                    className="px-2 py-2 text-left font-medium text-zinc-400"
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}
                  >
                    Excluded because
                  </th>
                  <Th
                    onClick={() => toggleSort('buildable_roof_area_m2')}
                    active={sortKey === 'buildable_roof_area_m2'}
                    dir={sortDir}
                    align="right"
                  >
                    Buildable (m²)
                  </Th>
                </tr>
              </thead>
              <tbody>
                {sortedBuildings.map((b) => (
                  <tr
                    key={b.building_id}
                    className="hover:bg-white/5 transition-colors"
                    style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
                  >
                    <td className="px-2 py-1.5 text-zinc-300 font-mono text-[10px]">
                      {b.building_id}
                    </td>
                    <td className="px-2 py-1.5 text-right text-zinc-200">
                      {b.area_m2.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </td>
                    <td className="px-2 py-1.5 text-zinc-300">
                      {FOOTPRINT_CLASS_LABELS[b.footprint_class] ?? b.footprint_class}
                    </td>
                    <td className="px-2 py-1.5 text-zinc-500 text-[11px]">
                      {b.exclusion_reason === 'none'
                        ? '—'
                        : (EXCLUSION_REASON_LABELS[b.exclusion_reason] ?? b.exclusion_reason)}
                    </td>
                    <td
                      className="px-2 py-1.5 text-right"
                      style={{
                        color: b.buildable_roof_area_m2 > 0 ? '#86efac' : 'var(--text-muted)',
                      }}
                    >
                      {b.buildable_roof_area_m2.toLocaleString(undefined, {
                        maximumFractionDigits: 0,
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer — totals + CSV download */}
        {!loading && !error && data && (
          <div
            className="flex items-center justify-between px-5 py-3 shrink-0 text-[11px] text-zinc-300"
            style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}
          >
            <div className="flex gap-4 tabular-nums">
              <span>
                <span className="text-zinc-500">Buildings:</span>{' '}
                <strong className="text-white">
                  {data.totals.building_count.toLocaleString()}
                </strong>
              </span>
              <span>
                <span className="text-zinc-500">Footprint:</span>{' '}
                <strong className="text-white">
                  {data.totals.total_footprint_m2.toLocaleString(undefined, {
                    maximumFractionDigits: 0,
                  })}{' '}
                  m²
                </strong>
              </span>
              <span>
                <span className="text-zinc-500">Buildable:</span>{' '}
                <strong style={{ color: '#86efac' }}>
                  {data.totals.usable_roof_area_m2.toLocaleString(undefined, {
                    maximumFractionDigits: 0,
                  })}{' '}
                  m²
                </strong>
              </span>
            </div>
            <button
              type="button"
              onClick={handleDownloadCsv}
              disabled={data.buildings.length === 0}
              className="px-3 py-1.5 text-[11px] rounded border border-white/20 text-white hover:bg-white/10 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors"
            >
              Download CSV
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function Th({
  children,
  onClick,
  active,
  dir,
  align,
}: {
  children: React.ReactNode;
  onClick: () => void;
  active: boolean;
  dir: SortDir;
  align: 'left' | 'right';
}) {
  return (
    <th
      onClick={onClick}
      className="px-2 py-2 font-medium text-zinc-400 cursor-pointer hover:text-white transition-colors select-none"
      style={{
        borderBottom: '1px solid rgba(255,255,255,0.08)',
        textAlign: align,
      }}
    >
      {children}
      <span className="ml-1 text-[10px] opacity-60">
        {active ? (dir === 'asc' ? '▲' : '▼') : '↕'}
      </span>
    </th>
  );
}

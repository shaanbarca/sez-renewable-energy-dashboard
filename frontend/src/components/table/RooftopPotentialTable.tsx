/**
 * RooftopPotentialTable — sortable per-site comparison view for v4.1
 * rooftop solar potential. Sits in BottomPanel as the "Solar Potential" tab.
 *
 * Why a separate component vs. extending the main DataTable:
 * - Different reading order (sites ranked by rooftop MWp, not LCOE)
 * - Tighter column set (rooftop-relevant only, no grid/CBAM noise)
 * - Different empty-state UX for the 14 missing-data sites
 *
 * Spec §3.6 F7. Rooftop columns + the comparison view.
 */
import { useMemo, useState } from 'react';
import type { ScorecardRow } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

type SortKey =
  | 'rooftop_mwp'
  | 'building_count'
  | 'usable_area'
  | 'site_name'
  | 'sector'
  | 'confidence';

type SortDir = 'asc' | 'desc';

const CONFIDENCE_ORDER = { high: 3, medium: 2, low: 1 } as const;

const CONFIDENCE_BADGE_COLORS: Record<string, { bg: string; fg: string }> = {
  high: { bg: 'rgba(76, 175, 80, 0.18)', fg: '#81c784' },
  medium: { bg: 'rgba(255, 152, 0, 0.16)', fg: '#ffb74d' },
  low: { bg: 'rgba(244, 67, 54, 0.16)', fg: '#e57373' },
};

const FORMAT_NUMBER = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });

function formatMwp(value: number | null | undefined): string {
  if (value == null) return '—';
  if (value < 1) return value.toFixed(2);
  if (value < 10) return value.toFixed(1);
  return FORMAT_NUMBER.format(value);
}

function formatHa(m2: number | null | undefined): string {
  if (m2 == null || m2 <= 0) return '—';
  return FORMAT_NUMBER.format(m2 / 10_000);
}

interface SortHeaderProps {
  label: string;
  sortKey: SortKey;
  active: SortKey;
  dir: SortDir;
  onSort: (k: SortKey) => void;
  align?: 'left' | 'right';
  tooltip?: string;
}

function SortHeader({ label, sortKey, active, dir, onSort, align, tooltip }: SortHeaderProps) {
  const isActive = active === sortKey;
  const arrow = isActive ? (dir === 'desc' ? ' ↓' : ' ↑') : '';
  return (
    <th
      onClick={() => onSort(sortKey)}
      style={{
        textAlign: align ?? 'left',
        padding: '8px 12px',
        cursor: 'pointer',
        userSelect: 'none',
        color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
        fontWeight: isActive ? 600 : 500,
        fontSize: '11px',
        textTransform: 'uppercase',
        letterSpacing: '0.05em',
        whiteSpace: 'nowrap',
      }}
      title={tooltip}
    >
      {label}
      {arrow}
    </th>
  );
}

/** Sub-toggle inside the Renewable Resource tab. Lets users switch between
 *  per-source potential views — Solar is the only one wired today, the rest
 *  are placeholders mirroring the LayerControl / EnergyToggle "Soon" pattern.
 *  When Wind / Geothermal / Hydro / Biomass land, swap the disabled flag and
 *  branch to the right table component. */
function ResourceSubToggle() {
  const [active, setActive] = useState<'solar' | 'wind' | 'geothermal' | 'hydro' | 'biomass'>(
    'solar',
  );
  const items: { value: typeof active; label: string; comingSoon?: boolean }[] = [
    { value: 'solar', label: 'Solar' },
    { value: 'wind', label: 'Wind', comingSoon: true },
    { value: 'geothermal', label: 'Geothermal', comingSoon: true },
    { value: 'hydro', label: 'Hydro', comingSoon: true },
    { value: 'biomass', label: 'Biomass', comingSoon: true },
  ];
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 16px',
        borderBottom: '1px solid var(--border-subtle)',
        background: 'var(--panel-bg-deep)',
      }}
    >
      <span
        style={{
          fontSize: 10,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: 'var(--text-muted)',
          marginRight: 4,
        }}
      >
        Resource
      </span>
      <div
        style={{
          display: 'flex',
          border: '1px solid var(--glass-border-bright)',
          borderRadius: 8,
          overflow: 'hidden',
        }}
      >
        {items.map((it) => {
          const isActive = it.value === active && !it.comingSoon;
          if (it.comingSoon) {
            return (
              <div
                key={it.value}
                title="Coming soon"
                style={{
                  padding: '4px 10px',
                  fontSize: 11,
                  fontWeight: 500,
                  color: 'var(--text-muted)',
                  opacity: 0.55,
                  cursor: 'not-allowed',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 5,
                  whiteSpace: 'nowrap',
                }}
              >
                {it.label}
                <span
                  style={{
                    fontSize: 8,
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    padding: '1px 4px',
                    border: '1px solid var(--text-muted)',
                    borderRadius: 3,
                    lineHeight: 1,
                  }}
                >
                  Soon
                </span>
              </div>
            );
          }
          return (
            <button
              key={it.value}
              type="button"
              onClick={() => setActive(it.value)}
              style={{
                padding: '4px 10px',
                fontSize: 11,
                fontWeight: 500,
                cursor: 'pointer',
                background: isActive ? 'var(--toggle-on-bg)' : 'transparent',
                color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                border: 'none',
                whiteSpace: 'nowrap',
              }}
            >
              {it.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

export default function RooftopPotentialTable() {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const selectedSite = useDashboardStore((s) => s.selectedSite);
  const selectSite = useDashboardStore((s) => s.selectSite);
  const [sort, setSort] = useState<{ key: SortKey; dir: SortDir }>({
    key: 'rooftop_mwp',
    dir: 'desc',
  });

  const rows = useMemo(() => {
    if (!scorecard) return [] as ScorecardRow[];
    // Only show sites where the v4.1 pipeline has run (rooftop_solar_mwp_potential
    // is set). Missing rows are sites without the optional table — they shouldn't
    // appear here at all.
    return scorecard.filter((r) => r.rooftop_solar_mwp_potential != null);
  }, [scorecard]);

  const sortedRows = useMemo(() => {
    const cmp = (a: ScorecardRow, b: ScorecardRow): number => {
      const dir = sort.dir === 'desc' ? -1 : 1;
      const k = sort.key;
      if (k === 'rooftop_mwp') {
        return (
          ((a.rooftop_solar_mwp_potential ?? -1) - (b.rooftop_solar_mwp_potential ?? -1)) * dir
        );
      }
      if (k === 'building_count') {
        return (
          ((a.building_count_standard_roof ?? -1) - (b.building_count_standard_roof ?? -1)) * dir
        );
      }
      if (k === 'usable_area') {
        return ((a.usable_roof_area_m2 ?? -1) - (b.usable_roof_area_m2 ?? -1)) * dir;
      }
      if (k === 'confidence') {
        const av = CONFIDENCE_ORDER[a.building_data_confidence ?? 'low'] ?? 0;
        const bv = CONFIDENCE_ORDER[b.building_data_confidence ?? 'low'] ?? 0;
        return (av - bv) * dir;
      }
      const av = String(a[k as keyof ScorecardRow] ?? '');
      const bv = String(b[k as keyof ScorecardRow] ?? '');
      return av.localeCompare(bv) * dir;
    };
    return [...rows].sort(cmp);
  }, [rows, sort]);

  const onSort = (key: SortKey) => {
    setSort((prev) => {
      if (prev.key === key) {
        return { key, dir: prev.dir === 'desc' ? 'asc' : 'desc' };
      }
      return { key, dir: 'desc' };
    });
  };

  if (!scorecard || rows.length === 0) {
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 32,
          color: 'var(--text-secondary)',
          fontSize: 13,
          textAlign: 'center',
          maxWidth: 480,
          margin: '0 auto',
        }}
      >
        Rooftop solar potential data not loaded yet. Run{' '}
        <code style={{ color: 'var(--text-primary)' }}>
          uv run python -m src.pipeline.build_fct_site_solar_potential
        </code>{' '}
        to populate this view.
      </div>
    );
  }

  const totalMwp = rows.reduce((acc, r) => acc + (r.rooftop_solar_mwp_potential ?? 0), 0);
  const totalBuildings = rows.reduce((acc, r) => acc + (r.building_count_standard_roof ?? 0), 0);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <ResourceSubToggle />
      {/* Summary bar */}
      <div
        style={{
          padding: '10px 16px',
          borderBottom: '1px solid var(--border-subtle)',
          background: 'var(--panel-bg-deep)',
          fontSize: 12,
          color: 'var(--text-secondary)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'baseline',
          flexWrap: 'wrap',
          gap: 12,
        }}
      >
        <span>
          <strong style={{ color: 'var(--text-primary)' }}>{rows.length}</strong> sites with rooftop
          data · <strong style={{ color: 'var(--text-primary)' }}>{formatMwp(totalMwp)}</strong> MWp
          DC total ·{' '}
          <strong style={{ color: 'var(--text-primary)' }}>
            {FORMAT_NUMBER.format(totalBuildings)}
          </strong>{' '}
          standard rooftops
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          Click a row to select on the map
        </span>
      </div>

      {/* Scrollable table body */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: 12,
            color: 'var(--text-primary)',
          }}
        >
          <thead
            style={{
              position: 'sticky',
              top: 0,
              background: 'var(--panel-bg)',
              zIndex: 1,
              borderBottom: '1px solid var(--border-subtle)',
            }}
          >
            <tr>
              <SortHeader
                label="Site"
                sortKey="site_name"
                active={sort.key}
                dir={sort.dir}
                onSort={onSort}
              />
              <SortHeader
                label="Sector"
                sortKey="sector"
                active={sort.key}
                dir={sort.dir}
                onSort={onSort}
              />
              <SortHeader
                label="Rooftop MWp"
                sortKey="rooftop_mwp"
                active={sort.key}
                dir={sort.dir}
                onSort={onSort}
                align="right"
                tooltip="Total rooftop solar capacity from the §14 building classifier × layout density × panel power."
              />
              <SortHeader
                label="Std. rooftops"
                sortKey="building_count"
                active={sort.key}
                dir={sort.dir}
                onSort={onSort}
                align="right"
                tooltip="Count of buildings classified as standard_roof (full multiplier 1.0)."
              />
              <SortHeader
                label="Usable area (ha)"
                sortKey="usable_area"
                active={sort.key}
                dir={sort.dir}
                onSort={onSort}
                align="right"
                tooltip="Building footprint × usability multiplier from the §14 classifier."
              />
              <SortHeader
                label="Confidence"
                sortKey="confidence"
                active={sort.key}
                dir={sort.dir}
                onSort={onSort}
              />
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row) => {
              const isSelected = row.site_id === selectedSite;
              const conf = row.building_data_confidence ?? 'low';
              const badge = CONFIDENCE_BADGE_COLORS[conf];
              return (
                <tr
                  key={row.site_id}
                  onClick={() => selectSite(row.site_id)}
                  style={{
                    cursor: 'pointer',
                    background: isSelected ? 'var(--selected-bg)' : 'transparent',
                    borderBottom: '1px solid var(--border-subtle-soft)',
                    transition: 'background 0.12s',
                  }}
                  onMouseEnter={(e) => {
                    if (!isSelected) e.currentTarget.style.background = 'var(--row-hover)';
                  }}
                  onMouseLeave={(e) => {
                    if (!isSelected) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <td style={{ padding: '6px 12px', fontWeight: isSelected ? 600 : 400 }}>
                    {row.site_name}
                  </td>
                  <td
                    style={{
                      padding: '6px 12px',
                      color: 'var(--text-secondary)',
                      textTransform: 'capitalize',
                    }}
                  >
                    {row.sector}
                  </td>
                  <td
                    style={{
                      padding: '6px 12px',
                      textAlign: 'right',
                      fontVariantNumeric: 'tabular-nums',
                      fontWeight: 500,
                    }}
                  >
                    {formatMwp(row.rooftop_solar_mwp_potential)}
                  </td>
                  <td
                    style={{
                      padding: '6px 12px',
                      textAlign: 'right',
                      fontVariantNumeric: 'tabular-nums',
                      color: 'var(--text-secondary)',
                    }}
                  >
                    {row.building_count_standard_roof != null
                      ? FORMAT_NUMBER.format(row.building_count_standard_roof)
                      : '—'}
                  </td>
                  <td
                    style={{
                      padding: '6px 12px',
                      textAlign: 'right',
                      fontVariantNumeric: 'tabular-nums',
                      color: 'var(--text-secondary)',
                    }}
                  >
                    {formatHa(row.usable_roof_area_m2)}
                  </td>
                  <td style={{ padding: '6px 12px' }}>
                    <span
                      style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        borderRadius: 4,
                        background: badge.bg,
                        color: badge.fg,
                        fontSize: 10,
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        letterSpacing: '0.04em',
                      }}
                      title={
                        row.building_data_reason_flagged ?? 'F4 confidence flag from §14 classifier'
                      }
                    >
                      {conf}
                    </span>
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

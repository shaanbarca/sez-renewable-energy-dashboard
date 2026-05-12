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
import { useCallback, useMemo, useState } from 'react';
import type { ScorecardRow } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

/** CSV cell escape — wraps values containing commas/quotes in double quotes. */
function csvCell(val: unknown): string {
  if (val == null) return '';
  const s = String(val);
  return s.includes(',') || s.includes('"') || s.includes('\n') ? `"${s.replace(/"/g, '""')}"` : s;
}

type SortKey =
  | 'rooftop_mwp'
  | 'ground_mwp'
  | 'captive_mwp'
  | 'building_count'
  | 'usable_area'
  | 'site_name'
  | 'sector'
  | 'confidence';

/** v4.0.5 (methodology #40): client-side ground-mounted MWp with override math.
 *
 *   deployable = baseline + (hard_max - baseline) × slider%
 *
 * Mirrors the math in src/dash/logic/grid.py:112 + ResourceTab.tsx so the
 * Renewable Resource table stays consistent with the Score Drawer. Falls
 * back to baseline-only when hard_max signal is missing (graceful pre-rerun).
 */
function computeGroundMwp(row: ScorecardRow, slider: number): number | null {
  const baseline = row.within_boundary_capacity_mwp;
  const hardMax = row.within_boundary_capacity_hard_max_mwp;
  if ((baseline == null || baseline <= 0) && (hardMax == null || hardMax <= 0)) {
    return null;
  }
  const b = baseline ?? 0;
  const soft = hardMax != null && hardMax >= b ? hardMax - b : 0;
  return b + soft * slider;
}

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
  const buildoutPct = useDashboardStore((s) => s.assumptions?.wb_buildout_footprint_ratio ?? 0.2);
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
      if (k === 'ground_mwp') {
        // v4.0.5 (methodology #40): use slider-aware override math, not raw raster.
        const av = computeGroundMwp(a, buildoutPct) ?? -1;
        const bv = computeGroundMwp(b, buildoutPct) ?? -1;
        return (av - bv) * dir;
      }
      if (k === 'captive_mwp') {
        // Total captive = rooftop + ground-mounted (both client-computed at
        // current slider positions). Mirrors Score Drawer TOTAL row.
        const aGround = computeGroundMwp(a, buildoutPct) ?? 0;
        const bGround = computeGroundMwp(b, buildoutPct) ?? 0;
        const aTotal = (a.rooftop_solar_mwp_potential ?? 0) + aGround;
        const bTotal = (b.rooftop_solar_mwp_potential ?? 0) + bGround;
        return (aTotal - bTotal) * dir;
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
  // v4.0.5 (methodology #40): totals use new override math.
  // Ground-mounted = baseline + (hard_max - baseline) × slider%.
  // Total Captive = Rooftop + Ground-mounted (matches Score Drawer TOTAL row).
  const totalGroundMwp = rows.reduce((acc, r) => acc + (computeGroundMwp(r, buildoutPct) ?? 0), 0);
  const totalCaptiveMwp = totalMwp + totalGroundMwp;

  // CSV export — captures everything visible in the table plus the raw
  // baseline/hard_max columns so downstream users can recompute under
  // different slider settings. Slider value at export time goes in the
  // metadata footer.
  const handleExport = useCallback(() => {
    const headers = [
      'site_id',
      'site_name',
      'sector',
      'rooftop_mwp',
      'ground_mounted_mwp',
      'total_captive_mwp',
      'building_count_standard',
      'usable_roof_area_ha',
      'data_confidence',
      'baseline_capacity_mwp',
      'hard_max_capacity_mwp',
      'land_use_override_pct_applied',
    ];
    const lines = rows.map((r) => {
      const ground = computeGroundMwp(r, buildoutPct);
      const rooftop = r.rooftop_solar_mwp_potential ?? null;
      const total = ground != null ? (rooftop ?? 0) + ground : rooftop;
      const usableHa =
        r.usable_roof_area_m2 != null ? +(r.usable_roof_area_m2 / 10_000).toFixed(2) : null;
      return [
        r.site_id,
        r.site_name,
        r.sector ?? '',
        rooftop != null ? rooftop.toFixed(1) : '',
        ground != null ? ground.toFixed(1) : '',
        total != null ? total.toFixed(1) : '',
        r.building_count_standard_roof ?? '',
        usableHa ?? '',
        r.building_data_confidence ?? '',
        r.within_boundary_capacity_mwp != null ? r.within_boundary_capacity_mwp.toFixed(1) : '',
        r.within_boundary_capacity_hard_max_mwp != null
          ? r.within_boundary_capacity_hard_max_mwp.toFixed(1)
          : '',
        (buildoutPct * 100).toFixed(0),
      ]
        .map(csvCell)
        .join(',');
    });
    const metadata = [
      '',
      '--- Export Metadata ---',
      `Land-use override (slider),${(buildoutPct * 100).toFixed(0)}%`,
      `Total rooftop MWp,${totalMwp.toFixed(1)}`,
      `Total ground-mounted MWp,${totalGroundMwp.toFixed(1)}`,
      `Total captive MWp,${totalCaptiveMwp.toFixed(1)}`,
      `Sites with data,${rows.length}`,
      `Export Date,${new Date().toISOString().slice(0, 10)}`,
      '',
      'Methodology: Ground-mounted = baseline + (hard_max − baseline) × slider%',
      'Total Captive = Rooftop + Ground-mounted (cost tiers differ — rooftop ≈ 5× $/MWp vs ground utility-scale)',
      'See docs/refinement/industrial_canopy_potential_methodology_2026-05-11.md and DESIGN.md §5.1.1',
    ].join('\n');
    const csv = [headers.join(','), ...lines, metadata].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `renewable_resource_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [rows, buildoutPct, totalMwp, totalGroundMwp, totalCaptiveMwp]);

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
          rooftop ·{' '}
          <strong style={{ color: 'var(--text-primary)' }}>{formatMwp(totalGroundMwp)}</strong> MWp
          ground-mounted ·{' '}
          <strong style={{ color: 'var(--text-primary)' }}>{formatMwp(totalCaptiveMwp)}</strong> MWp
          captive total (at {(buildoutPct * 100).toFixed(0)}% land-use override) ·{' '}
          <strong style={{ color: 'var(--text-primary)' }}>
            {FORMAT_NUMBER.format(totalBuildings)}
          </strong>{' '}
          standard rooftops
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            Click a row to select on the map
          </span>
          <button
            type="button"
            onClick={handleExport}
            className="px-3 py-1 text-xs rounded cursor-pointer transition-colors"
            style={{ color: 'var(--text-secondary)', border: '1px solid var(--text-muted)' }}
          >
            Export CSV
          </button>
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
                label={`Ground-mounted MWp (${(buildoutPct * 100).toFixed(0)}%)`}
                sortKey="ground_mwp"
                active={sort.key}
                dir={sort.dir}
                onSort={onSort}
                align="right"
                tooltip={`Ground-mounted captive solar with the land-use override slider applied: baseline + (hard_max − baseline) × ${(buildoutPct * 100).toFixed(0)}%. At 0% strict 4-layer raster baseline; at 100% all soft-zoning exclusions overridden. Empty for sites without a fence polygon.`}
              />
              <SortHeader
                label="Total Captive MWp"
                sortKey="captive_mwp"
                active={sort.key}
                dir={sort.dir}
                onSort={onSort}
                align="right"
                tooltip="Rooftop + Ground-mounted MWp — matches the Score Drawer TOTAL row. Mixes cost tiers (rooftop ≈ 5× $/MWp vs ground utility-scale)."
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
                  {(() => {
                    const groundMwp = computeGroundMwp(row, buildoutPct);
                    const baseline = row.within_boundary_capacity_mwp ?? 0;
                    const hardMax = row.within_boundary_capacity_hard_max_mwp ?? baseline;
                    const softExcluded = Math.max(0, hardMax - baseline);
                    const rooftopMwp = row.rooftop_solar_mwp_potential ?? 0;
                    const totalCaptive = groundMwp != null ? rooftopMwp + groundMwp : null;
                    const lowTrustPolygon =
                      row.polygon_source_tier === 'none' ||
                      row.polygon_source_tier === 'claude_building_hull_estimate';
                    const lowTrustTooltip =
                      row.polygon_source_tier === 'none'
                        ? 'Low-trust: no fence-line polygon — using 2 km centroid buffer fallback. Likely over-counts adjacent land.'
                        : 'Low-trust: polygon estimated from detected buildings — fence boundary not independently verified.';
                    const groundTitle =
                      groundMwp != null
                        ? `Baseline ${baseline.toFixed(1)} MWp + ${(buildoutPct * 100).toFixed(0)}% × ${softExcluded.toFixed(1)} MWp soft-excluded override (hard-max ${hardMax.toFixed(1)} MWp)${lowTrustPolygon ? ` — ${lowTrustTooltip}` : ''}`
                        : 'No buildable land within fence (or 2 km buffer for no-polygon sites). Slope, peat, or Kawasan Hutan filters eliminated all in-boundary pixels.';
                    return (
                      <>
                        <td
                          style={{
                            padding: '6px 12px',
                            textAlign: 'right',
                            fontVariantNumeric: 'tabular-nums',
                            fontWeight: 500,
                          }}
                          title={groundTitle}
                        >
                          {groundMwp != null ? formatMwp(groundMwp) : '—'}
                          {groundMwp != null && lowTrustPolygon && (
                            <span
                              role="img"
                              style={{ marginLeft: 4, color: 'rgba(245, 158, 11, 0.9)' }}
                              title={lowTrustTooltip}
                              aria-label="low-trust polygon"
                            >
                              ⚠
                            </span>
                          )}
                        </td>
                        <td
                          style={{
                            padding: '6px 12px',
                            textAlign: 'right',
                            fontVariantNumeric: 'tabular-nums',
                            fontWeight: 500,
                          }}
                          title={
                            totalCaptive != null
                              ? `Rooftop ${rooftopMwp.toFixed(1)} + Ground-mounted ${groundMwp?.toFixed(1) ?? '0.0'} MWp (cost tiers differ — rooftop ≈ 5× $/MWp vs ground utility-scale)`
                              : 'Rooftop only — no fence polygon for ground-mounted'
                          }
                        >
                          {totalCaptive != null ? formatMwp(totalCaptive) : formatMwp(rooftopMwp)}
                        </td>
                      </>
                    );
                  })()}
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

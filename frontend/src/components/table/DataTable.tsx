import {
  type Column,
  type ColumnFiltersState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from '@tanstack/react-table';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { getEffectiveEconomicTier, getEffectiveInfraReadiness } from '../../lib/actionFlags';
import { formatFilterValue } from '../../lib/format';
import type { ScorecardRow, UserAssumptions, UserThresholds } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';
import { columns } from './columns';

const ASSUMPTION_LABELS: [keyof UserAssumptions, string, string][] = [
  ['wacc_pct', 'WACC', '%'],
  ['capex_usd_per_kw', 'Solar CAPEX', 'USD/kW'],
  ['fom_usd_per_kw_yr', 'Fixed O&M', 'USD/kW-yr'],
  ['lifetime_yr', 'Lifetime', 'years'],
  ['bess_capex_usd_per_kwh', 'BESS CAPEX', 'USD/kWh'],
  ['bess_sizing_hours_override', 'BESS Sizing Override', 'hours'],
  ['connection_cost_per_kw_km', 'Grid Connection Cost', 'USD/kW-km'],
  ['grid_connection_fixed_per_kw', 'Grid Connection Fixed', 'USD/kW'],
  ['land_cost_usd_per_kw', 'Land Cost', 'USD/kW'],
  ['substation_utilization_pct', 'Substation Utilization', 'fraction'],
  ['idr_usd_rate', 'IDR/USD Rate', 'IDR'],
  ['cbam_certificate_price_eur', 'CBAM Certificate Price', 'EUR/tCO2'],
  ['cbam_eur_usd_rate', 'CBAM EUR/USD Rate', ''],
  ['grant_funded_transmission', 'Grant-Funded Transmission', ''],
  ['target_capacity_mwp', 'Target Capacity', 'MWp'],
  ['hybrid_solar_share', 'Hybrid Solar Share Override', '%'],
];

const THRESHOLD_LABELS: [keyof UserThresholds, string, string][] = [
  ['pvout_threshold', 'PVOUT Threshold', 'kWh/kWp/yr'],
  ['plan_late_threshold', 'Plan Late Threshold', 'fraction'],
  ['geas_threshold', 'GEAS Green Share Threshold', 'fraction'],
  ['resilience_gap_pct', 'Resilience Gap', '%'],
  ['min_viable_mwp', 'Min Viable Project Size', 'MWp'],
  ['reliability_threshold', 'Reliability Threshold', 'fraction'],
];

function exportCsv(rows: Record<string, unknown>[], headers: string[], metadata?: string) {
  const headerLine = headers.join(',');
  const lines = rows.map((row) =>
    headers
      .map((h) => {
        const val = row[h];
        if (val == null) return '';
        const s = String(val);
        return s.includes(',') || s.includes('"') ? `"${s.replace(/"/g, '""')}"` : s;
      })
      .join(','),
  );
  const parts = [headerLine, ...lines];
  if (metadata) parts.push('', metadata);
  const csv = parts.join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'site_scorecard.csv';
  a.click();
  URL.revokeObjectURL(url);
}

// Columns that get dropdown filters (categorical)
const DROPDOWN_COLUMNS = new Set([
  'action_flag',
  'province',
  'zone_classification',
  'category',
  'best_re_technology',
  'grid_integration_category',
  'captive_power_type',
  'dominant_process_type',
  'cbam_exposed',
  'economic_tier',
  'infrastructure_readiness',
  'industry',
  'cbam_2030',
]);
// Columns that get range filters (numeric)
const RANGE_COLUMNS = new Set([
  'max_captive_capacity_mwp',
  'lcoe_mid_usd_mwh',
  'solar_competitive_gap_pct',
  'dashboard_rate_usd_mwh',
  'area_ha',
  'solar_replacement_pct',
  'grid_investment_needed_usd',
  'cbam_cost_2030_usd_per_tonne',
]);

function getCaptivePowerType(row: ScorecardRow): string {
  const hasCoal = !!row.captive_coal_count && row.captive_coal_count > 0;
  const hasNickel = !!row.nickel_smelter_count && row.nickel_smelter_count > 0;
  if (hasCoal && hasNickel) return 'Coal + Nickel';
  if (hasCoal) return 'Coal';
  if (hasNickel) return 'Nickel';
  return 'None';
}

function DropdownFilter({ column, data }: { column: Column<ScorecardRow>; data: ScorecardRow[] }) {
  const filterValue = (column.getFilterValue() as string) ?? '';
  const energyMode = useDashboardStore((s) => s.energyMode);
  const options = useMemo(() => {
    const vals = new Set<string>();
    for (const row of data) {
      if (column.id === 'captive_power_type') {
        vals.add(getCaptivePowerType(row));
      } else if (column.id === 'industry') {
        const hasCoal = !!row.captive_coal_count && row.captive_coal_count > 0;
        const hasNickel = !!row.nickel_smelter_count && row.nickel_smelter_count > 0;
        const hasSteel = !!row.steel_plant_count && row.steel_plant_count > 0;
        const hasCement = !!row.cement_plant_count && row.cement_plant_count > 0;
        if (hasCoal) vals.add('Coal');
        if (hasNickel) vals.add('Nickel');
        if (hasSteel) vals.add('Steel');
        if (hasCement) vals.add('Cement');
        if (!hasCoal && !hasNickel && !hasSteel && !hasCement) vals.add('None');
      } else if (column.id === 'cbam_2030') {
        vals.add('Yes');
        vals.add('No');
      } else if (column.id === 'economic_tier') {
        vals.add(getEffectiveEconomicTier(row, energyMode));
      } else if (column.id === 'infrastructure_readiness') {
        vals.add(getEffectiveInfraReadiness(row));
      } else {
        const v = row[column.id as keyof ScorecardRow];
        if (v != null && v !== '') vals.add(String(v));
      }
    }
    return Array.from(vals).sort();
  }, [data, column.id, energyMode]);

  return (
    <select
      value={filterValue}
      onChange={(e) => column.setFilterValue(e.target.value || undefined)}
      className="w-full bg-transparent text-[10px] outline-none rounded px-1 py-0.5 mt-1 cursor-pointer"
      style={{
        color: 'var(--text-secondary)',
        border: '1px solid var(--input-border)',
        maxWidth: 120,
      }}
    >
      <option value="">All</option>
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {formatFilterValue(column.id, opt)}
        </option>
      ))}
    </select>
  );
}

function RangeFilter({ column, data }: { column: Column<ScorecardRow>; data: ScorecardRow[] }) {
  const filterValue = (column.getFilterValue() as [number | '', number | '']) ?? ['', ''];
  const [min, max] = useMemo(() => {
    let lo = Number.POSITIVE_INFINITY;
    let hi = Number.NEGATIVE_INFINITY;
    for (const row of data) {
      const v = row[column.id as keyof ScorecardRow];
      if (typeof v === 'number' && Number.isFinite(v)) {
        if (v < lo) lo = v;
        if (v > hi) hi = v;
      }
    }
    return [Number.isFinite(lo) ? lo : 0, Number.isFinite(hi) ? hi : 0];
  }, [data, column.id]);

  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const handleChange = (idx: 0 | 1, val: string) => {
    const next = [...filterValue] as [number | '', number | ''];
    next[idx] = val === '' ? '' : Number(val);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      column.setFilterValue(next[0] === '' && next[1] === '' ? undefined : next);
    }, 300);
  };

  return (
    <div className="flex gap-1 mt-1">
      <input
        type="number"
        placeholder={min.toFixed(0)}
        defaultValue={filterValue[0]}
        onChange={(e) => handleChange(0, e.target.value)}
        className="w-14 bg-transparent text-[10px] outline-none rounded px-1 py-0.5 tabular-nums"
        style={{ color: 'var(--text-secondary)', border: '1px solid var(--input-border)' }}
      />
      <input
        type="number"
        placeholder={max.toFixed(0)}
        defaultValue={filterValue[1]}
        onChange={(e) => handleChange(1, e.target.value)}
        className="w-14 bg-transparent text-[10px] outline-none rounded px-1 py-0.5 tabular-nums"
        style={{ color: 'var(--text-secondary)', border: '1px solid var(--input-border)' }}
      />
    </div>
  );
}

export default function DataTable() {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const assumptions = useDashboardStore((s) => s.assumptions);
  const thresholds = useDashboardStore((s) => s.thresholds);
  const energyMode = useDashboardStore((s) => s.energyMode);
  const benchmarkMode = useDashboardStore((s) => s.benchmarkMode);
  const selectedSite = useDashboardStore((s) => s.selectedSite);
  const selectSite = useDashboardStore((s) => s.selectSite);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [cbamOnly, setCbamOnly] = useState(false);

  const data = useMemo(
    () => (cbamOnly ? (scorecard ?? []).filter((r) => r.cbam_exposed) : (scorecard ?? [])),
    [scorecard, cbamOnly],
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter, columnFilters },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    onColumnFiltersChange: setColumnFilters,
    globalFilterFn: (row, _columnId, filterValue: string) => {
      const search = filterValue.toLowerCase();
      const name = (row.original.site_name ?? '').toLowerCase();
      const province = (row.original.province ?? '').toLowerCase();
      return name.includes(search) || province.includes(search);
    },
    filterFns: {
      inRange: (row, columnId, value: [number | '', number | '']) => {
        const v = row.getValue<number>(columnId);
        if (v == null) return true;
        const [lo, hi] = value;
        if (lo !== '' && v < lo) return false;
        if (hi !== '' && v > hi) return false;
        return true;
      },
    },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  });

  // Sync filtered rows to Zustand so map markers update
  const setFilteredSiteIds = useDashboardStore((s) => s.setFilteredSiteIds);
  const filteredRows = table.getRowModel().rows;
  useEffect(() => {
    const ids = new Set(filteredRows.map((r) => r.original.site_id));
    setFilteredSiteIds(ids);
    return () => setFilteredSiteIds(null);
  }, [filteredRows, setFilteredSiteIds]);

  const handleExport = useCallback(() => {
    if (!scorecard) return;
    const headers = [
      'site_name',
      'province',
      'action_flag',
      'lcoe_mid_usd_mwh',
      'solar_competitive_gap_pct',
      'best_re_technology',
      'dashboard_rate_usd_mwh',
      'grid_region_id',
      'grid_integration_category',
      'grid_investment_needed_usd',
      'bpp_usd_mwh',
      'carbon_breakeven_usd_tco2',
      'captive_coal_count',
      'captive_coal_mw',
      'nickel_smelter_count',
      'dominant_process_type',
      'solar_replacement_pct',
      'perpres_112_status',
    ];

    const meta: string[] = [];
    if (assumptions) {
      meta.push('--- Assumptions ---');
      meta.push('Parameter,Value,Unit');
      for (const [key, label, unit] of ASSUMPTION_LABELS) {
        const val = assumptions[key];
        if (val != null) meta.push(`${label},${val},${unit}`);
      }
    }
    if (thresholds) {
      meta.push('');
      meta.push('--- Thresholds ---');
      meta.push('Parameter,Value,Unit');
      for (const [key, label, unit] of THRESHOLD_LABELS) {
        const val = thresholds[key];
        if (val != null) meta.push(`${label},${val},${unit}`);
      }
    }
    meta.push('');
    meta.push('--- Export Metadata ---');
    meta.push(`Energy Mode,${energyMode}`);
    meta.push(`Benchmark Mode,${benchmarkMode}`);
    meta.push(`Export Date,${new Date().toISOString().slice(0, 10)}`);

    exportCsv(scorecard as unknown as Record<string, unknown>[], headers, meta.join('\n'));
  }, [scorecard, assumptions, thresholds, energyMode, benchmarkMode]);

  if (!scorecard) {
    return (
      <div
        className="flex items-center justify-center h-full"
        style={{ color: 'var(--text-muted)' }}
      >
        Loading...
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 px-3 py-1">
        <div
          className="flex items-center gap-1.5 flex-1 max-w-xs px-2 py-1 rounded"
          style={{ border: '1px solid var(--glass-border)', background: 'var(--tab-active-bg)' }}
        >
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="shrink-0"
            style={{ color: 'var(--text-muted)' }}
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Search site or province..."
            className="bg-transparent text-xs outline-none w-full"
            style={{ color: 'var(--text-primary)' }}
          />
          {globalFilter && (
            <button
              type="button"
              onClick={() => setGlobalFilter('')}
              className="text-[10px] cursor-pointer"
              style={{ color: 'var(--text-muted)' }}
            >
              ✕
            </button>
          )}
        </div>
        <div className="flex-1" />
        <button
          type="button"
          onClick={() => setCbamOnly(!cbamOnly)}
          className="px-2 py-1 text-[10px] rounded cursor-pointer transition-colors"
          style={
            cbamOnly
              ? {
                  color: '#FF6F00',
                  border: '1px solid rgba(255,111,0,0.4)',
                  background: 'rgba(255,111,0,0.1)',
                }
              : { color: 'var(--text-muted)', border: '1px solid var(--input-border)' }
          }
        >
          CBAM
        </button>
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className="px-3 py-1 text-xs rounded cursor-pointer transition-colors"
          style={
            showFilters || columnFilters.length > 0
              ? {
                  color: 'var(--accent)',
                  border: '1px solid var(--accent-border)',
                  background: 'var(--accent-soft)',
                }
              : { color: 'var(--text-muted)', border: '1px solid var(--input-border)' }
          }
        >
          Filters{columnFilters.length > 0 ? ` (${columnFilters.length})` : ''}
        </button>
        {columnFilters.length > 0 && (
          <button
            type="button"
            onClick={() => setColumnFilters([])}
            className="text-[10px] cursor-pointer"
            style={{ color: 'var(--text-muted)' }}
          >
            Clear all
          </button>
        )}
        <button
          type="button"
          onClick={handleExport}
          className="px-3 py-1 text-xs rounded cursor-pointer transition-colors"
          style={{ color: 'var(--text-muted)', border: '1px solid var(--input-border)' }}
        >
          Export CSV
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-10" style={{ background: 'var(--glass-heavy)' }}>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    className="text-left px-3 py-2 font-medium cursor-pointer select-none overflow-visible"
                    style={{
                      color: 'var(--text-secondary)',
                      borderBottom: '1px solid var(--tab-border)',
                    }}
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <span className="flex items-center gap-1">
                      {flexRender(header.column.columnDef.header, header.getContext())}
                      {{
                        asc: ' \u25B2',
                        desc: ' \u25BC',
                      }[header.column.getIsSorted() as string] ?? ''}
                    </span>
                  </th>
                ))}
              </tr>
            ))}
            {showFilters && (
              <tr>
                {table.getHeaderGroups()[0].headers.map((header) => (
                  <th
                    key={`filter-${header.id}`}
                    className="px-3 py-1"
                    style={{ borderBottom: '1px solid var(--border-subtle)' }}
                  >
                    {DROPDOWN_COLUMNS.has(header.column.id) && (
                      <DropdownFilter column={header.column} data={data} />
                    )}
                    {RANGE_COLUMNS.has(header.column.id) && (
                      <RangeFilter column={header.column} data={data} />
                    )}
                  </th>
                ))}
              </tr>
            )}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                className="cursor-pointer"
                style={{
                  background:
                    row.original.site_id === selectedSite ? 'var(--selected-bg)' : undefined,
                }}
                onClick={() => selectSite(row.original.site_id)}
              >
                {row.getVisibleCells().map((cell) => (
                  <td
                    key={cell.id}
                    className="px-3 py-2"
                    style={{
                      color: 'var(--text-primary)',
                      borderBottom: '1px solid var(--tab-border)',
                    }}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

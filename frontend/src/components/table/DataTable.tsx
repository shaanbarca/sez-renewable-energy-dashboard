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
import { useCallback, useMemo, useRef, useState } from 'react';
import type { ScorecardRow } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';
import { columns } from './columns';

function exportCsv(rows: Record<string, unknown>[], headers: string[]) {
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
  const csv = [headerLine, ...lines].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'kek_scorecard.csv';
  a.click();
  URL.revokeObjectURL(url);
}

// Columns that get dropdown filters (categorical)
const DROPDOWN_COLUMNS = new Set([
  'action_flag',
  'province',
  'kek_type',
  'category',
  'best_re_technology',
  'grid_integration_category',
]);
// Columns that get range filters (numeric)
const RANGE_COLUMNS = new Set([
  'max_captive_capacity_mwp',
  'lcoe_mid_usd_mwh',
  'solar_competitive_gap_pct',
  'dashboard_rate_usd_mwh',
  'area_ha',
]);

function DropdownFilter({ column, data }: { column: Column<ScorecardRow>; data: ScorecardRow[] }) {
  const filterValue = (column.getFilterValue() as string) ?? '';
  const options = useMemo(() => {
    const vals = new Set<string>();
    for (const row of data) {
      const v = row[column.id as keyof ScorecardRow];
      if (v != null && v !== '') vals.add(String(v));
    }
    return Array.from(vals).sort();
  }, [data, column.id]);

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
          {opt}
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
  const selectedKek = useDashboardStore((s) => s.selectedKek);
  const selectKek = useDashboardStore((s) => s.selectKek);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [showFilters, setShowFilters] = useState(false);

  const data = useMemo(() => scorecard ?? [], [scorecard]);

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter, columnFilters },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    onColumnFiltersChange: setColumnFilters,
    globalFilterFn: (row, _columnId, filterValue: string) => {
      const search = filterValue.toLowerCase();
      const name = (row.original.kek_name ?? '').toLowerCase();
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

  const handleExport = useCallback(() => {
    if (!scorecard) return;
    const headers = [
      'kek_name',
      'province',
      'action_flag',
      'lcoe_mid_usd_mwh',
      'solar_competitive_gap_pct',
      'best_re_technology',
      'dashboard_rate_usd_mwh',
      'grid_region_id',
      'bpp_usd_mwh',
      'carbon_breakeven_usd_tco2',
    ];
    exportCsv(scorecard as unknown as Record<string, unknown>[], headers);
  }, [scorecard]);

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
            placeholder="Search KEK or province..."
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
                    row.original.kek_id === selectedKek ? 'var(--selected-bg)' : undefined,
                }}
                onClick={() => selectKek(row.original.kek_id)}
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

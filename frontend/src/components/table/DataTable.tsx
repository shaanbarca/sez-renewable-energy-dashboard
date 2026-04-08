import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from '@tanstack/react-table';
import { useCallback, useMemo, useState } from 'react';
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

export default function DataTable() {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const selectedKek = useDashboardStore((s) => s.selectedKek);
  const selectKek = useDashboardStore((s) => s.selectKek);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

  const data = useMemo(() => scorecard ?? [], [scorecard]);

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: (row, _columnId, filterValue: string) => {
      const search = filterValue.toLowerCase();
      const name = (row.original.kek_name ?? '').toLowerCase();
      const province = (row.original.province ?? '').toLowerCase();
      return name.includes(search) || province.includes(search);
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
    return <div className="flex items-center justify-center h-full text-zinc-600">Loading...</div>;
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 px-3 py-1">
        <div className="flex items-center gap-1.5 flex-1 max-w-xs px-2 py-1 rounded border border-white/10 bg-white/[0.03]">
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="text-zinc-500 shrink-0"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder="Search KEK or province..."
            className="bg-transparent text-xs text-zinc-200 placeholder-zinc-500 outline-none w-full"
          />
          {globalFilter && (
            <button
              onClick={() => setGlobalFilter('')}
              className="text-zinc-500 hover:text-zinc-300 text-[10px] cursor-pointer"
            >
              ✕
            </button>
          )}
        </div>
        <div className="flex-1" />
        <button
          onClick={handleExport}
          className="text-zinc-500 hover:text-zinc-300 border border-white/10 px-3 py-1 text-xs rounded"
        >
          Export CSV
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    className="text-left px-3 py-2 text-[#999] font-medium cursor-pointer select-none border-b border-white/5"
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
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr
                key={row.id}
                className={`cursor-pointer hover:bg-white/[0.04] ${
                  row.original.kek_id === selectedKek ? 'bg-white/[0.04]' : ''
                }`}
                onClick={() => selectKek(row.original.kek_id)}
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-2 text-[#e0e0e0] border-b border-white/5">
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

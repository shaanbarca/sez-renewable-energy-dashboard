import { createColumnHelper } from '@tanstack/react-table';
import { ACTION_FLAG_COLORS, ACTION_FLAG_LABELS } from '../../lib/constants';
import type { ScorecardRow } from '../../lib/types';

const col = createColumnHelper<ScorecardRow>();

export const columns = [
  col.accessor('kek_name', {
    header: 'KEK Name',
    cell: (info) => info.getValue(),
  }),
  col.accessor('province', {
    header: 'Province',
    cell: (info) => info.getValue(),
  }),
  col.accessor('kek_type', {
    header: 'Type',
    cell: (info) => info.getValue() ?? '—',
  }),
  col.accessor('category', {
    header: 'Category',
    cell: (info) => info.getValue() ?? '—',
  }),
  col.accessor('area_ha', {
    header: 'Area (ha)',
    cell: (info) => {
      const v = info.getValue();
      return v != null ? v.toLocaleString(undefined, { maximumFractionDigits: 0 }) : '—';
    },
  }),
  col.accessor('action_flag', {
    header: 'Action Flag',
    cell: (info) => {
      const flag = info.getValue();
      const color = ACTION_FLAG_COLORS[flag] ?? '#666';
      const label = ACTION_FLAG_LABELS[flag] ?? flag;
      return (
        <span className="flex items-center gap-2">
          <span
            className="inline-block w-2 h-2 rounded-full flex-shrink-0"
            style={{ backgroundColor: color }}
          />
          <span>{label}</span>
        </span>
      );
    },
  }),
  col.accessor('lcoe_mid_usd_mwh', {
    header: 'LCOE ($/MWh)',
    cell: (info) => info.getValue().toFixed(1),
  }),
  col.accessor('solar_competitive_gap_pct', {
    header: 'Gap (%)',
    cell: (info) => {
      const val = info.getValue();
      const sign = val > 0 ? '+' : '';
      const color = val < 0 ? '#4CAF50' : val > 0 ? '#EF5350' : '#e0e0e0';
      return (
        <span style={{ color }}>
          {sign}
          {val.toFixed(1)}%
        </span>
      );
    },
  }),
  col.accessor('best_re_technology', {
    header: 'Best RE',
    cell: (info) => info.getValue(),
  }),
  col.accessor('dashboard_rate_usd_mwh', {
    header: 'Grid Rate ($/MWh)',
    cell: (info) => info.getValue().toFixed(1),
  }),
];

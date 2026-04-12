import * as Tabs from '@radix-ui/react-tabs';
import { useState } from 'react';
import type { BottomTab } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';
import QuadrantChart from '../charts/QuadrantChart';
import RuptlChart from '../charts/RuptlChart';
import DataTable from '../table/DataTable';

const TAB_ITEMS: { value: BottomTab; label: string }[] = [
  { value: 'table', label: 'Ranked Table' },
  { value: 'quadrant', label: 'Quadrant Chart' },
  { value: 'ruptl', label: 'RUPTL Context' },
];

const PANEL_HEIGHT = 288; // h-72 = 18rem = 288px

export default function BottomPanel() {
  const activeTab = useDashboardStore((s) => s.activeTab);
  const setActiveTab = useDashboardStore((s) => s.setActiveTab);
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div
      className="relative transition-[height] duration-300 ease-in-out"
      style={{
        height: collapsed ? 34 : PANEL_HEIGHT,
        backdropFilter: 'var(--blur-heavy)',
        WebkitBackdropFilter: 'var(--blur-heavy)',
        background: 'var(--panel-bg)',
        borderColor: 'var(--glass-border)',
        boxShadow: 'var(--panel-shadow)',
        overflow: 'hidden',
      }}
    >
      <Tabs.Root
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as BottomTab)}
        className="h-full flex flex-col"
      >
        {/* Full-width toggle handle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full h-8 flex items-center justify-center gap-2
                     text-xs font-medium tracking-wide
                     transition-colors cursor-pointer shrink-0"
          style={{
            color: 'var(--accent)',
            background: 'var(--accent-soft)',
            borderTop: '2px solid var(--accent-border)',
          }}
          title={collapsed ? 'Show table panel' : 'Hide table panel'}
        >
          <span>{collapsed ? 'Show Table' : 'Hide Table'}</span>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`transition-transform duration-300 ${collapsed ? 'rotate-180' : ''}`}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>

        <Tabs.List
          className="flex gap-1 px-3 pt-2 pb-0 shrink-0"
          style={{ borderBottom: `1px solid var(--tab-border)` }}
        >
          {TAB_ITEMS.map(({ value, label }) => (
            <Tabs.Trigger
              key={value}
              value={value}
              className="px-4 py-1.5 text-xs rounded-t transition-colors border border-transparent"
              style={
                activeTab === value
                  ? {
                      color: 'var(--text-primary)',
                      background: 'var(--tab-active-bg)',
                      borderColor: 'var(--tab-border)',
                      borderBottomColor: 'transparent',
                    }
                  : { color: 'var(--text-secondary)' }
              }
            >
              {label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        <Tabs.Content value="table" className="flex-1 overflow-hidden">
          <DataTable />
        </Tabs.Content>
        <Tabs.Content value="quadrant" className="flex-1 overflow-hidden">
          <QuadrantChart />
        </Tabs.Content>
        <Tabs.Content value="ruptl" className="flex-1 overflow-hidden">
          <RuptlChart />
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}

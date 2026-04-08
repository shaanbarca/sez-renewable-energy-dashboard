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
        backdropFilter: 'blur(32px) saturate(1.5)',
        WebkitBackdropFilter: 'blur(32px) saturate(1.5)',
        background: 'rgba(20, 20, 24, 0.45)',
        borderColor: 'var(--glass-border)',
        boxShadow: '0 -4px 24px rgba(0,0,0,0.3)',
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
                     text-[#90CAF9] text-xs font-medium tracking-wide
                     hover:bg-white/[0.08] transition-colors cursor-pointer shrink-0"
          style={{
            background: 'rgba(144, 202, 249, 0.08)',
            borderTop: '2px solid rgba(144, 202, 249, 0.3)',
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

        <Tabs.List className="flex gap-1 px-3 pt-2 pb-0 shrink-0 border-b border-white/10">
          {TAB_ITEMS.map(({ value, label }) => (
            <Tabs.Trigger
              key={value}
              value={value}
              className={`px-4 py-1.5 text-xs rounded-t transition-colors ${
                activeTab === value
                  ? 'text-[#e0e0e0] bg-white/[0.08] border border-white/10 border-b-transparent'
                  : 'text-[#999] hover:text-[#ccc] bg-transparent border border-transparent'
              }`}
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

import { useState } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { useDashboardStore } from '../../store/dashboard';
import DataTable from '../table/DataTable';
import QuadrantChart from '../charts/QuadrantChart';
import RuptlChart from '../charts/RuptlChart';
import type { BottomTab } from '../../lib/types';

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
      className="border-t relative transition-[height] duration-300 ease-in-out"
      style={{
        height: collapsed ? 36 : PANEL_HEIGHT,
        backdropFilter: 'var(--blur-heavy)',
        WebkitBackdropFilter: 'var(--blur-heavy)',
        background: 'var(--glass-heavy)',
        borderColor: 'var(--glass-border)',
        boxShadow: '0 -4px 24px rgba(0,0,0,0.3)',
        overflow: 'hidden',
      }}
    >
      {/* Drag handle / collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -top-4 left-1/2 -translate-x-1/2 z-20
                   flex items-center justify-center w-20 h-8 rounded-t-lg cursor-pointer
                   hover:brightness-125 transition-all"
        style={{
          background: 'rgba(50, 50, 55, 0.95)',
          border: '1px solid rgba(255, 255, 255, 0.25)',
          borderBottom: 'none',
          boxShadow: '0 -2px 12px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1)',
        }}
        title={collapsed ? 'Expand panel' : 'Collapse panel'}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`text-white transition-transform duration-300 ${collapsed ? 'rotate-180' : ''}`}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      <Tabs.Root
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as BottomTab)}
        className="h-full flex flex-col"
      >
        <Tabs.List className="flex gap-1 px-3 pt-2 pb-0 shrink-0">
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

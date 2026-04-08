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

export default function BottomPanel() {
  const activeTab = useDashboardStore((s) => s.activeTab);
  const setActiveTab = useDashboardStore((s) => s.setActiveTab);

  return (
    <div
      className="h-72 border-t"
      style={{
        backdropFilter: 'var(--blur-heavy, blur(24px))',
        background: 'var(--glass-heavy, rgba(18, 18, 18, 0.85))',
        borderColor: 'var(--glass-border, rgba(255, 255, 255, 0.08))',
      }}
    >
      <Tabs.Root
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as BottomTab)}
        className="h-full flex flex-col"
      >
        <Tabs.List className="flex gap-1 px-3 pt-2 pb-0">
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

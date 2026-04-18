import * as Tabs from '@radix-ui/react-tabs';
import { useCallback, useRef, useState } from 'react';
import type { BottomTab } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';
import RuptlChart from '../charts/RuptlChart';
import SectorSummaryChart from '../charts/SectorSummaryChart';
import DataTable from '../table/DataTable';

const TAB_ITEMS: { value: BottomTab; label: string }[] = [
  { value: 'table', label: 'Ranked Table' },
  { value: 'ruptl', label: 'RUPTL Context' },
  { value: 'sector', label: 'Sector Summary' },
];

const TABLE_HEIGHT = 448;
const CHART_HEIGHT = 420;
const MIN_HEIGHT = 200;
const MAX_HEIGHT = 700;

export default function BottomPanel() {
  const activeTab = useDashboardStore((s) => s.activeTab);
  const setActiveTab = useDashboardStore((s) => s.setActiveTab);
  const collapsed = useDashboardStore((s) => s.bottomPanelCollapsed);
  const setCollapsed = useDashboardStore((s) => s.setBottomPanelCollapsed);
  const [userHeight, setUserHeight] = useState<number | null>(null);
  const dragging = useRef(false);
  const startY = useRef(0);
  const startH = useRef(0);

  const defaultHeight =
    activeTab === 'table' ? TABLE_HEIGHT : activeTab === 'sector' ? 540 : CHART_HEIGHT;
  const panelHeight = userHeight ?? defaultHeight;

  const onDragStart = useCallback(
    (e: React.PointerEvent) => {
      dragging.current = true;
      startY.current = e.clientY;
      startH.current = panelHeight;
      e.currentTarget.setPointerCapture(e.pointerId);
    },
    [panelHeight],
  );

  const onDragMove = useCallback((e: React.PointerEvent) => {
    if (!dragging.current) return;
    const delta = startY.current - e.clientY;
    setUserHeight(Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, startH.current + delta)));
  }, []);

  const onDragEnd = useCallback(() => {
    dragging.current = false;
  }, []);

  return (
    <div
      className="relative"
      style={{
        height: collapsed ? 34 : panelHeight,
        transition: dragging.current ? 'none' : 'height 0.3s ease-in-out',
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
        {/* Resize handle + toggle */}
        <div
          className="w-full shrink-0 select-none relative"
          style={{
            background: 'var(--accent-soft)',
            borderTop: '2px solid var(--accent-border)',
          }}
        >
          {/* Drag handle — full width behind the button */}
          {!collapsed && (
            <div
              className="absolute inset-0"
              style={{ cursor: 'ns-resize' }}
              onPointerDown={onDragStart}
              onPointerMove={onDragMove}
              onPointerUp={onDragEnd}
              title="Drag to resize panel"
            />
          )}
          {/* Visible drag-grip pill — signals resizable */}
          {!collapsed && (
            <div
              className="absolute left-1/2 -translate-x-1/2 pointer-events-none"
              style={{
                top: 4,
                width: 36,
                height: 4,
                borderRadius: 2,
                background: 'var(--accent-border)',
                opacity: 0.7,
              }}
            />
          )}
          {/* Collapse toggle — always centered */}
          <div className="flex items-center justify-center h-8">
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="relative z-10 h-8 px-3 flex items-center gap-1.5
                         text-xs font-medium tracking-wide
                         transition-colors cursor-pointer"
              style={{ color: 'var(--accent)' }}
              title={collapsed ? 'Show table panel' : 'Hide table panel'}
            >
              <span>{collapsed ? 'Show' : 'Hide'}</span>
              <svg
                width="12"
                height="12"
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
          </div>
        </div>

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
        <Tabs.Content value="ruptl" className="flex-1 overflow-hidden">
          <RuptlChart />
        </Tabs.Content>
        <Tabs.Content value="sector" className="flex-1 overflow-hidden">
          <SectorSummaryChart />
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}

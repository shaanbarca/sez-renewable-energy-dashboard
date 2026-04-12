import * as Accordion from '@radix-ui/react-accordion';
import { useRef, useState } from 'react';
import { useDraggable } from '../../hooks/useDraggable';
import { useScorecard } from '../../hooks/useScorecard';
import type { SliderConfig, UserAssumptions, UserThresholds } from '../../lib/types';
import { hasChangedAssumptions } from '../../lib/urlState';
import { useDashboardStore } from '../../store/dashboard';
import CapexInput from '../ui/CapexInput';
import ScenarioManager from '../ui/ScenarioManager';
import Slider from '../ui/Slider';

/* ---------- sub-components ---------- */

function ChevronDown({ className }: { className?: string }) {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function SummaryBlock() {
  const assumptions = useDashboardStore((s) => s.assumptions);
  if (!assumptions) return null;

  const items = [
    { label: 'WACC', value: `${assumptions.wacc_pct}%` },
    { label: 'CAPEX', value: `$${assumptions.capex_usd_per_kw.toLocaleString()}` },
    { label: 'Life', value: `${assumptions.lifetime_yr}yr` },
  ];

  return (
    <div className="flex gap-2 mt-2 mb-2">
      {items.map((item) => (
        <div
          key={item.label}
          className="flex-1 px-2 py-1.5 rounded text-center"
          style={{ background: 'var(--card-bg)' }}
        >
          <div
            className="text-[9px] uppercase tracking-wider"
            style={{ color: 'var(--text-muted)' }}
          >
            {item.label}
          </div>
          <div className="text-xs font-medium tabular-nums" style={{ color: 'var(--text-value)' }}>
            {item.value}
          </div>
        </div>
      ))}
    </div>
  );
}

function SliderGroup({
  configs,
  values,
  onChange,
}: {
  configs: Record<string, SliderConfig> | undefined;
  values: Record<string, number> | undefined;
  onChange: (key: string, val: number) => void;
}) {
  if (!configs || !values) return null;

  return (
    <div className="space-y-0.5">
      {Object.entries(configs).map(([key, cfg]) => (
        <Slider
          key={key}
          value={values[key] ?? cfg.min}
          onChange={(v) => onChange(key, v)}
          min={cfg.min}
          max={cfg.max}
          step={cfg.step}
          label={cfg.label}
          unit={cfg.unit}
          description={cfg.description}
        />
      ))}
    </div>
  );
}

function WaccSlider() {
  const assumptions = useDashboardStore((s) => s.assumptions);
  const sliderConfigs = useDashboardStore((s) => s.sliderConfigs);
  const setAssumptions = useDashboardStore((s) => s.setAssumptions);

  if (!assumptions || !sliderConfigs?.wacc) return null;

  const wacc = sliderConfigs.wacc;

  return (
    <Slider
      value={assumptions.wacc_pct}
      onChange={(v) => setAssumptions({ wacc_pct: v })}
      min={wacc.min}
      max={wacc.max}
      step={wacc.step}
      label="WACC"
      unit="%"
      description={wacc.description}
      marks={wacc.marks}
    />
  );
}

function BenchmarkToggle() {
  const benchmarkMode = useDashboardStore((s) => s.benchmarkMode);
  const setBenchmarkMode = useDashboardStore((s) => s.setBenchmarkMode);

  const options: { value: 'tariff' | 'bpp'; label: string }[] = [
    { value: 'tariff', label: 'I-4/TT Tariff' },
    { value: 'bpp', label: 'Regional BPP' },
  ];

  return (
    <div className="mt-3 pt-3" style={{ borderTop: '1px solid var(--border-subtle)' }}>
      <div
        className="text-[10px] uppercase tracking-wider mb-1.5"
        style={{ color: 'var(--text-muted)' }}
      >
        Grid Cost Benchmark
      </div>
      <div className="flex rounded overflow-hidden" style={{ background: 'var(--card-bg)' }}>
        {options.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setBenchmarkMode(opt.value)}
            className="flex-1 py-1.5 text-[11px] font-medium transition-colors"
            style={
              benchmarkMode === opt.value
                ? { background: 'var(--accent-muted)', color: 'var(--accent)' }
                : { color: 'var(--text-muted)' }
            }
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  );
}

/* ---------- accordion trigger ---------- */

function AccordionTrigger({ children }: { children: React.ReactNode }) {
  return (
    <Accordion.Trigger
      className="flex items-center justify-between w-full py-1.5 text-[10px] uppercase tracking-wider transition-colors group"
      style={{ color: 'var(--text-muted)' }}
    >
      <span>{children}</span>
      <ChevronDown className="transition-transform duration-200 group-data-[state=open]:rotate-180" />
    </Accordion.Trigger>
  );
}

/* ---------- main component ---------- */

export default function AssumptionsPanel() {
  const [collapsed, setCollapsed] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);

  const assumptions = useDashboardStore((s) => s.assumptions);
  const thresholds = useDashboardStore((s) => s.thresholds);
  const sliderConfigs = useDashboardStore((s) => s.sliderConfigs);
  const setAssumptions = useDashboardStore((s) => s.setAssumptions);
  const setThresholds = useDashboardStore((s) => s.setThresholds);
  const resetDefaults = useDashboardStore((s) => s.resetDefaults);
  const defaultAssumptions = useDashboardStore((s) => s.defaultAssumptions);
  const benchmarkMode = useDashboardStore((s) => s.benchmarkMode);

  const isModified =
    assumptions &&
    defaultAssumptions &&
    (hasChangedAssumptions(assumptions, defaultAssumptions) || benchmarkMode !== 'bpp');

  const { loading } = useScorecard();
  const { position: dragPos, handleMouseDown: onDragStart } = useDraggable();

  if (!assumptions || !sliderConfigs) return null;

  const handleAssumptionChange = (key: string, val: number) => {
    setAssumptions({ [key]: val } as Partial<UserAssumptions>);
  };

  const handleThresholdChange = (key: string, val: number) => {
    setThresholds({ [key]: val } as Partial<UserThresholds>);
  };

  return (
    <div
      className="absolute top-[60px] left-4 z-10 w-[310px] rounded-lg overflow-hidden flex flex-col"
      data-panel="assumptions"
      data-tour="assumptions"
      style={{
        background: 'var(--glass-heavy)',
        backdropFilter: 'var(--blur-heavy)',
        WebkitBackdropFilter: 'var(--blur-heavy)',
        border: '1px solid var(--glass-border)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
        maxHeight: 'calc(100vh - 100px)',
        transform: `translate(${dragPos.x}px, ${dragPos.y}px)`,
      }}
    >
      {/* Drag handle + Header */}
      <div
        onMouseDown={onDragStart}
        className="flex items-center justify-between w-full px-3.5 py-2.5 transition-colors cursor-grab active:cursor-grabbing"
        onClick={() => setCollapsed(!collapsed)}
        role="button"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium" style={{ color: 'var(--text-primary)' }}>
            Assumptions
          </span>
          {isModified && (
            <span
              className="px-1.5 py-0.5 rounded text-[9px] font-medium"
              style={{ background: 'var(--accent-muted)', color: 'var(--accent)' }}
            >
              Modified
            </span>
          )}
          {loading && (
            <span
              className="w-1.5 h-1.5 rounded-full animate-pulse"
              style={{ background: 'var(--accent)' }}
            />
          )}
        </div>
        <ChevronDown
          className={`transition-transform duration-200 ${collapsed ? '' : 'rotate-180'}`}
        />
      </div>

      {/* Expandable body — smooth animated collapse */}
      <div
        className="overflow-y-auto transition-all duration-300 ease-[cubic-bezier(0.33,1,0.68,1)]"
        style={{
          maxHeight: collapsed ? 0 : 'calc(100vh - 150px)',
          opacity: collapsed ? 0 : 1,
          scrollbarWidth: 'thin',
          scrollbarColor: 'var(--scrollbar-thumb) transparent',
        }}
      >
        <div ref={bodyRef} className="px-3.5 pb-3">
          <SummaryBlock />

          {/* Tier 1: Core */}
          <div className="mb-1">
            <WaccSlider />
            {sliderConfigs.tier1?.capex_usd_per_kw && (
              <CapexInput
                value={assumptions.capex_usd_per_kw}
                onChange={(v) => setAssumptions({ capex_usd_per_kw: v })}
                config={sliderConfigs.tier1.capex_usd_per_kw}
              />
            )}
            <SliderGroup
              configs={(() => {
                if (!sliderConfigs.tier1) return undefined;
                const { capex_usd_per_kw: _, ...rest } = sliderConfigs.tier1;
                return Object.keys(rest).length > 0 ? rest : undefined;
              })()}
              values={assumptions as unknown as Record<string, number>}
              onChange={handleAssumptionChange}
            />
          </div>

          {/* Tier 2 + 3: Advanced */}
          <Accordion.Root type="multiple" className="mt-1">
            <Accordion.Item
              value="advanced"
              className="border-t"
              style={{ borderColor: 'var(--border-subtle)' }}
            >
              <Accordion.Header>
                <AccordionTrigger>Advanced Assumptions</AccordionTrigger>
              </Accordion.Header>
              <Accordion.Content className="overflow-hidden data-[state=open]:animate-accordion-down data-[state=closed]:animate-accordion-up">
                <SliderGroup
                  configs={(() => {
                    if (!sliderConfigs.tier2) return undefined;
                    const { substation_utilization_pct: _, ...rest } = sliderConfigs.tier2;
                    return Object.keys(rest).length > 0 ? rest : undefined;
                  })()}
                  values={assumptions as unknown as Record<string, number>}
                  onChange={handleAssumptionChange}
                />
              </Accordion.Content>
            </Accordion.Item>

            <Accordion.Item
              value="thresholds"
              className="border-t"
              style={{ borderColor: 'var(--border-subtle)' }}
            >
              <Accordion.Header>
                <AccordionTrigger>Flag Thresholds</AccordionTrigger>
              </Accordion.Header>
              <Accordion.Content className="overflow-hidden data-[state=open]:animate-accordion-down data-[state=closed]:animate-accordion-up">
                <SliderGroup
                  configs={sliderConfigs.tier3}
                  values={thresholds as unknown as Record<string, number>}
                  onChange={handleThresholdChange}
                />
              </Accordion.Content>
            </Accordion.Item>
          </Accordion.Root>

          <BenchmarkToggle />

          {/* Reset */}
          <button
            onClick={resetDefaults}
            className="w-full mt-3 mb-2 py-1.5 rounded text-[11px] font-medium transition-colors"
            style={{
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            Reset to Defaults
          </button>

          <ScenarioManager />
        </div>
      </div>
    </div>
  );
}

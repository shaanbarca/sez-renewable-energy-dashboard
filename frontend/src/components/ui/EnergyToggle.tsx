import * as Tooltip from '@radix-ui/react-tooltip';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import type { EnergyMode } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

type Option =
  | { value: EnergyMode; label: string; comingSoon?: false }
  | { value: string; label: string; comingSoon: true };

type Section = { title: string; options: Option[] };

// Two sections — single-source modes and composite modes. "Soon" pills
// telegraph the v4.1+ roadmap (mirrors the LayerControl pattern). Adding a
// new RE source is a 1-line addition here, no UI rework needed.
const SECTIONS: Section[] = [
  {
    title: 'Single source',
    options: [
      { value: 'solar', label: 'Solar' },
      { value: 'wind', label: 'Wind' },
      { value: 'geothermal', label: 'Geothermal' },
      { value: 'hydro', label: 'Hydro', comingSoon: true },
      { value: 'biomass', label: 'Biomass', comingSoon: true },
    ],
  },
  {
    title: 'Composite',
    options: [
      { value: 'hybrid', label: 'Hybrid' },
      { value: 'overall', label: 'Overall' },
    ],
  },
];

const ALL_OPTIONS = SECTIONS.flatMap((s) => s.options);

function activeLabel(mode: EnergyMode): string {
  return ALL_OPTIONS.find((o) => o.value === mode)?.label ?? 'Solar';
}

export default function EnergyToggle() {
  const energyMode = useDashboardStore((s) => s.energyMode);
  const setEnergyMode = useDashboardStore((s) => s.setEnergyMode);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (!open) return;
    const update = () => {
      const rect = buttonRef.current?.getBoundingClientRect();
      if (!rect) return;
      setPos({ top: rect.bottom + 6, left: rect.left });
    };
    update();
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, true);
    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('scroll', update, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (buttonRef.current?.contains(target) || panelRef.current?.contains(target)) return;
      setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const handlePick = (mode: EnergyMode) => {
    setEnergyMode(mode);
    setOpen(false);
  };

  return (
    <Tooltip.Provider delayDuration={300}>
      <div className="flex items-center gap-1">
        <button
          ref={buttonRef}
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer whitespace-nowrap"
          style={{
            color: 'var(--text-primary)',
            background: open ? 'var(--selected-bg)' : 'var(--toggle-on-bg)',
            border: `1px solid ${open ? 'var(--glass-border-bright)' : 'var(--glass-border-bright)'}`,
          }}
        >
          <span>{activeLabel(energyMode)}</span>
          <svg
            width="10"
            height="10"
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ opacity: 0.6 }}
          >
            <path d="M3 4.5L6 7.5L9 4.5" />
          </svg>
        </button>
        <Tooltip.Root>
          <Tooltip.Trigger asChild>
            <button
              type="button"
              aria-label="What is Source?"
              className="cursor-help transition-colors"
              style={{ color: 'var(--text-muted)' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
            >
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
                <circle cx="8" cy="8" r="7" stroke="currentColor" strokeWidth="1.5" />
                <text
                  x="8"
                  y="12"
                  textAnchor="middle"
                  fill="currentColor"
                  fontSize="10"
                  fontWeight="600"
                >
                  ?
                </text>
              </svg>
            </button>
          </Tooltip.Trigger>
          <Tooltip.Portal>
            <Tooltip.Content
              side="bottom"
              sideOffset={8}
              className="max-w-[260px] px-3 py-2 rounded text-xs leading-relaxed z-50"
              style={{
                background: 'var(--glass-heavy)',
                backdropFilter: 'var(--blur-heavy)',
                WebkitBackdropFilter: 'var(--blur-heavy)',
                border: '1px solid var(--glass-border-bright)',
                boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06), 0 4px 16px rgba(0,0,0,0.4)',
                color: 'var(--text-primary)',
              }}
            >
              <div className="font-medium mb-1">Renewable energy source</div>
              <div style={{ color: 'var(--text-secondary)' }}>
                Pick which technology drives the cost columns and map layers.
                Single-source modes show one tech at a time. Hybrid sweeps the
                optimal solar+wind mix; Overall picks the cheapest RE per site.
              </div>
            </Tooltip.Content>
          </Tooltip.Portal>
        </Tooltip.Root>
      </div>

      {open &&
        pos &&
        createPortal(
          <div
            ref={panelRef}
            className="rounded-lg px-2 py-2 min-w-[200px]"
            style={{
              position: 'fixed',
              top: pos.top,
              left: pos.left,
              zIndex: 1000,
              backdropFilter: 'blur(28px) saturate(1.4)',
              WebkitBackdropFilter: 'blur(28px) saturate(1.4)',
              background: 'rgba(15, 15, 18, 0.95)',
              border: '1px solid var(--glass-border-bright)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            }}
          >
            {SECTIONS.map((section, sIdx) => (
              <div key={section.title} className={sIdx > 0 ? 'mt-2' : ''}>
                <div
                  className="text-[9px] font-semibold uppercase tracking-wider px-2 mb-1"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {section.title}
                </div>
                <div className="space-y-0.5">
                  {section.options.map((opt) => {
                    const active = !opt.comingSoon && energyMode === opt.value;
                    if (opt.comingSoon) {
                      return (
                        <div
                          key={opt.value}
                          title="Coming soon"
                          className="flex items-center gap-2 px-2 py-1 text-xs cursor-not-allowed"
                          style={{ color: 'var(--text-muted)', opacity: 0.55 }}
                        >
                          <span style={{ flex: 1 }}>{opt.label}</span>
                          <span
                            className="text-[8px] uppercase tracking-wider px-1 py-0.5 rounded"
                            style={{
                              color: 'var(--text-muted)',
                              border: '1px solid var(--text-muted)',
                              lineHeight: 1,
                            }}
                          >
                            Soon
                          </span>
                        </div>
                      );
                    }
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => handlePick(opt.value as EnergyMode)}
                        className="w-full flex items-center gap-2 px-2 py-1 text-xs rounded cursor-pointer transition-colors"
                        style={{
                          color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                          background: active ? 'var(--accent-soft)' : 'transparent',
                        }}
                      >
                        <span style={{ flex: 1, textAlign: 'left' }}>{opt.label}</span>
                        {active && (
                          <svg
                            width="11"
                            height="11"
                            viewBox="0 0 16 16"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            style={{ color: 'var(--accent)' }}
                          >
                            <path d="M3 8.5L6.5 12L13 4.5" />
                          </svg>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>,
          document.body,
        )}
    </Tooltip.Provider>
  );
}

import * as Tooltip from '@radix-ui/react-tooltip';
import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import type { EnergyMode } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

type Option =
  | { value: EnergyMode; label: string; description?: string; comingSoon?: false }
  | { value: string; label: string; description?: string; comingSoon: true };

type Section = { title: string; options: Option[] };

/** Tiny inline SVG icons for the active-mode indicator inside the dropdown
 *  trigger. Each is a 14×14 stroked glyph that reads at small size. */
function ModeIcon({ mode }: { mode: EnergyMode }) {
  const common = {
    width: 14,
    height: 14,
    viewBox: '0 0 16 16',
    fill: 'none' as const,
    stroke: 'currentColor',
    strokeWidth: 1.5,
    strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const,
  };
  switch (mode) {
    case 'solar':
      return (
        <svg {...common}>
          <circle cx="8" cy="8" r="3" />
          <path d="M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4" />
        </svg>
      );
    case 'wind':
      return (
        <svg {...common}>
          <path d="M2 5h7a2 2 0 1 0-2-2M2 11h10a2 2 0 1 1-2 2M2 8h12a2 2 0 1 0-2-2" />
        </svg>
      );
    case 'geothermal':
      return (
        <svg {...common}>
          <path d="M5 9c0-2 2-2 2-4M8 9c0-2 2-2 2-4M11 9c0-2 2-2 2-4" />
          <path d="M2 13h12" strokeWidth="2" />
        </svg>
      );
    case 'hybrid':
      return (
        <svg {...common}>
          <circle cx="6" cy="8" r="3.5" />
          <circle cx="10" cy="8" r="3.5" />
        </svg>
      );
    case 'overall':
      return (
        <svg {...common}>
          <circle cx="8" cy="8" r="6" />
          <circle cx="8" cy="8" r="2.5" fill="currentColor" />
        </svg>
      );
  }
}

// Two sections — single-source modes and composite modes. "Soon" pills
// telegraph the v4.1+ roadmap (mirrors the LayerControl pattern). Adding a
// new RE source is a 1-line addition here, no UI rework needed.
const SECTIONS: Section[] = [
  {
    title: 'Single source',
    options: [
      {
        value: 'solar',
        label: 'Solar',
        description: 'Solar-only LCOE. Map shows PVOUT raster + buildable land.',
      },
      {
        value: 'wind',
        label: 'Wind',
        description: 'Wind-only LCOE. Map shows wind speed + buildable land.',
      },
      {
        value: 'geothermal',
        label: 'Geothermal',
        description:
          'Layers-only. Site-resolved geothermal LCOE isn’t published — the Score Drawer adjacency card carries the per-site signal.',
      },
      {
        value: 'hydro',
        label: 'Hydro',
        description: 'Coming in v4.1b alongside the hydro proximity dataset.',
        comingSoon: true,
      },
      {
        value: 'biomass',
        label: 'Biomass',
        description: 'Spec-pending. Needs its own proximity model (no RUPTL analog).',
        comingSoon: true,
      },
    ],
  },
  {
    title: 'Composite',
    options: [
      {
        value: 'hybrid',
        label: 'Mix',
        description:
          'Optimal solar + wind mix per site. The optimizer sweeps share splits to minimise blended LCOE; cost columns reflect the chosen mix and the BESS hours it implies.',
      },
      {
        value: 'overall',
        label: 'Best fit',
        description:
          'Per-site winner. Each site picks the cheapest of Solar / Wind / Mix; cost columns show that winner. Use this when you want one ranking across all techs.',
      },
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

  // Active mode determines which mode is "real" (not coming-soon) — only those
  // get a leading icon. Soon-modes never become active.
  const isRealMode = (
    ['solar', 'wind', 'geothermal', 'hybrid', 'overall'] as EnergyMode[]
  ).includes(energyMode);

  return (
    <Tooltip.Provider delayDuration={300}>
      {/* Single bordered shell holding both the dropdown trigger and the `?`
          info button, with a thin vertical separator between them. The `?` no
          longer floats outside the chip. */}
      <div
        className="flex items-stretch rounded-lg overflow-hidden transition-colors"
        style={{
          background: open ? 'var(--selected-bg)' : 'var(--toggle-on-bg)',
          border: `1px solid var(--glass-border-bright)`,
        }}
      >
        <button
          ref={buttonRef}
          type="button"
          onClick={() => setOpen(!open)}
          className="flex items-center gap-1.5 pl-2.5 pr-2 py-1.5 text-xs font-medium cursor-pointer whitespace-nowrap"
          style={{ color: 'var(--text-primary)' }}
        >
          {isRealMode && (
            <span style={{ color: 'var(--accent)', display: 'inline-flex' }}>
              <ModeIcon mode={energyMode} />
            </span>
          )}
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
              className="cursor-help transition-colors flex items-center px-2"
              style={{
                color: 'var(--text-muted)',
                borderLeft: '1px solid var(--glass-border)',
              }}
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
                      const soonRow = (
                        <div
                          key={opt.value}
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
                      return opt.description ? (
                        <ModeTooltip
                          key={opt.value}
                          title={opt.label}
                          body={opt.description}
                        >
                          {soonRow}
                        </ModeTooltip>
                      ) : (
                        soonRow
                      );
                    }
                    const button = (
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
                    return opt.description ? (
                      <ModeTooltip key={opt.value} title={opt.label} body={opt.description}>
                        {button}
                      </ModeTooltip>
                    ) : (
                      button
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

/** Side-anchored tooltip for option rows in the dropdown. Wraps either a
 *  clickable mode button or a "Soon" placeholder; renders the title in
 *  primary color and the body explanation below in secondary. */
function ModeTooltip({
  title,
  body,
  children,
}: {
  title: string;
  body: string;
  children: React.ReactNode;
}) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          side="right"
          sideOffset={10}
          className="max-w-[260px] px-3 py-2 rounded text-xs leading-relaxed z-[1100]"
          style={{
            background: 'var(--glass-heavy)',
            backdropFilter: 'var(--blur-heavy)',
            WebkitBackdropFilter: 'var(--blur-heavy)',
            border: '1px solid var(--glass-border-bright)',
            boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06), 0 4px 16px rgba(0,0,0,0.4)',
            color: 'var(--text-primary)',
          }}
        >
          <div className="font-medium mb-1">{title}</div>
          <div style={{ color: 'var(--text-secondary)' }}>{body}</div>
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}

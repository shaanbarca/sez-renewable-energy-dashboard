import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { MAP_STYLES } from '../../lib/constants';
import type { MapStyleKey } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

type LayerItem = { name: string; label: string; comingSoon?: boolean };

const LAYER_SECTIONS: { title: string; items: readonly LayerItem[] }[] = [
  {
    title: 'Renewable resources',
    items: [
      { name: 'pvout', label: 'Solar potential (PVOUT)' },
      { name: 'wind', label: 'Wind speed (100m)' },
      { name: 'geothermal_operating', label: 'Geothermal — operating (PLTP)' },
      { name: 'geothermal_pipeline', label: 'Geothermal — RUPTL pipeline' },
      { name: 'hydro_operating', label: 'Hydro — operating', comingSoon: true },
      { name: 'hydro_pipeline', label: 'Hydro — RUPTL pipeline', comingSoon: true },
      { name: 'biomass', label: 'Biomass / waste-to-energy', comingSoon: true },
    ],
  },
  {
    title: 'Buildable land',
    items: [
      { name: 'buildable_polygons', label: 'Solar buildable areas' },
      { name: 'wind_buildable_polygons', label: 'Wind buildable areas' },
      { name: 'rooftop_tiles', label: 'Rooftop solar tiles' },
    ],
  },
  {
    title: 'Grid',
    items: [
      { name: 'substations', label: 'Substations (PLN)' },
      { name: 'grid_lines', label: 'PLN grid lines' },
    ],
  },
  {
    title: 'Land use',
    items: [
      { name: 'site_boundaries', label: 'Site boundaries' },
      { name: 'peatland', label: 'Peatland' },
      { name: 'protected_forest', label: 'Protected forest' },
    ],
  },
  {
    title: 'Industrial demand',
    items: [
      { name: 'industrial', label: 'Industrial facilities' },
      { name: 'nickel_smelters', label: 'Nickel smelters (CGSP)' },
      { name: 'captive_coal', label: 'Captive coal plants (GEM)' },
      { name: 'steel_plants', label: 'Steel plants (GEM)' },
      { name: 'cement_plants', label: 'Cement plants (GEM)' },
    ],
  },
];

const LAYER_ITEMS = LAYER_SECTIONS.flatMap((s) => s.items.filter((i) => !i.comingSoon));

const STYLE_KEYS = Object.keys(MAP_STYLES) as MapStyleKey[];

export default function LayerControl() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const toggleLayer = useDashboardStore((s) => s.toggleLayer);
  const mapStyle = useDashboardStore((s) => s.mapStyle);
  const setMapStyle = useDashboardStore((s) => s.setMapStyle);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ top: number; right: number } | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const activeCount = LAYER_ITEMS.filter(({ name }) => !!layerVisibility[name]).length;

  const allOn = LAYER_ITEMS.every(({ name }) => !!layerVisibility[name]);
  const noneOn = LAYER_ITEMS.every(({ name }) => !layerVisibility[name]);

  const selectAll = () => {
    for (const { name } of LAYER_ITEMS) {
      if (!layerVisibility[name]) toggleLayer(name);
    }
  };
  const deselectAll = () => {
    for (const { name } of LAYER_ITEMS) {
      if (layerVisibility[name]) toggleLayer(name);
    }
  };

  // Position the portal panel below the button. Recompute on open, on resize,
  // and on scroll so the panel tracks the button if the layout shifts.
  useLayoutEffect(() => {
    if (!open) return;
    const update = () => {
      const rect = buttonRef.current?.getBoundingClientRect();
      if (!rect) return;
      setPos({
        top: rect.bottom + 6,
        right: window.innerWidth - rect.right,
      });
    };
    update();
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, true);
    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('scroll', update, true);
    };
  }, [open]);

  // Close on outside click. Panel now lives in a portal, so we check both the
  // button (trigger) and the panel itself rather than a single container ref.
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

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer"
        style={{
          color: open ? 'var(--text-primary)' : 'var(--text-secondary)',
          background: open ? 'var(--selected-bg)' : 'var(--toggle-on-bg)',
          border: `1px solid var(--glass-border-bright)`,
        }}
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M12 2L2 7l10 5 10-5-10-5z" />
          <path d="M2 17l10 5 10-5" />
          <path d="M2 12l10 5 10-5" />
        </svg>
        Layers
        <span
          className="ml-0.5 px-1.5 rounded-full text-[10px] font-medium leading-none min-w-[20px] text-center"
          style={{
            background: activeCount > 0 ? 'var(--accent-muted)' : 'transparent',
            color: activeCount > 0 ? 'var(--accent)' : 'transparent',
            paddingTop: 2,
            paddingBottom: 2,
          }}
        >
          {activeCount}
        </span>
      </button>

      {/* Portal the panel to document.body so it escapes the Header's stacking
          context. The RasterLegend below it creates its own context via
          backdrop-filter — z-index alone couldn't reliably put the panel on
          top from inside the Header subtree. */}
      {open &&
        pos &&
        createPortal(
          <div
            ref={panelRef}
            className="rounded-lg px-3 py-2.5 min-w-[220px]"
            style={{
              position: 'fixed',
              top: pos.top,
              right: pos.right,
              zIndex: 1000,
              backdropFilter: 'blur(28px) saturate(1.4)',
              WebkitBackdropFilter: 'blur(28px) saturate(1.4)',
              background: 'rgba(15, 15, 18, 0.95)',
              border: '1px solid var(--glass-border-bright)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            }}
          >
            <div className="flex items-center justify-between mb-2">
              <div
                className="text-xs font-semibold uppercase tracking-wider"
                style={{ color: 'var(--text-secondary)' }}
              >
                Layers
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={selectAll}
                  disabled={allOn}
                  className="text-[10px] transition-colors cursor-pointer disabled:cursor-default"
                  style={{ color: 'var(--accent)' }}
                >
                  All
                </button>
                <button
                  type="button"
                  onClick={deselectAll}
                  disabled={noneOn}
                  className="text-[10px] transition-colors cursor-pointer disabled:cursor-default"
                  style={{ color: 'var(--accent)' }}
                >
                  None
                </button>
              </div>
            </div>
            <div className="space-y-2.5">
              {LAYER_SECTIONS.map((section) => (
                <div key={section.title}>
                  <div
                    className="text-[9px] font-semibold uppercase tracking-wider mb-1"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    {section.title}
                  </div>
                  <div className="space-y-1">
                    {section.items.map(({ name, label, comingSoon }) =>
                      comingSoon ? (
                        <div
                          key={name}
                          title="Coming soon"
                          className="flex items-center gap-2 text-xs py-0.5 cursor-not-allowed"
                          style={{ color: 'var(--text-muted)', opacity: 0.55 }}
                        >
                          <input
                            type="checkbox"
                            checked={false}
                            disabled
                            className="w-3.5 h-3.5"
                          />
                          <span style={{ flex: 1 }}>{label}</span>
                          <span
                            className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded"
                            style={{
                              color: 'var(--text-muted)',
                              border: '1px solid var(--text-muted)',
                            }}
                          >
                            Soon
                          </span>
                        </div>
                      ) : (
                        <label
                          key={name}
                          className="flex items-center gap-2 cursor-pointer text-xs transition-colors py-0.5"
                          style={{ color: 'var(--text-primary)' }}
                        >
                          <input
                            type="checkbox"
                            checked={!!layerVisibility[name]}
                            onChange={() => toggleLayer(name)}
                            className="accent-blue-500 w-3.5 h-3.5"
                          />
                          {label}
                        </label>
                      ),
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Map style switcher */}
            <div className="mt-3 pt-2 pb-1" style={{ borderTop: '1px solid var(--glass-border)' }}>
              <div
                className="text-[10px] font-semibold uppercase tracking-wider mb-1.5"
                style={{ color: 'var(--text-muted)' }}
              >
                Map Style
              </div>
              <div className="flex gap-1">
                {STYLE_KEYS.map((key) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setMapStyle(key)}
                    className="px-2 py-1 text-[10px] rounded transition-colors cursor-pointer"
                    style={
                      mapStyle === key
                        ? {
                            background: 'var(--accent-muted)',
                            color: 'var(--accent)',
                            border: '1px solid var(--accent-border)',
                          }
                        : { color: 'var(--text-secondary)', border: '1px solid transparent' }
                    }
                  >
                    {MAP_STYLES[key].label}
                  </button>
                ))}
              </div>
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}

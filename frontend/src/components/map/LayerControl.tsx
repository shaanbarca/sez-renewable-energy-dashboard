import { useEffect, useRef, useState } from 'react';
import { MAP_STYLES } from '../../lib/constants';
import type { MapStyleKey } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

const LAYER_ITEMS = [
  { name: 'substations', label: 'Substations (PLN)' },
  { name: 'kek_polygons', label: 'KEK Boundaries' },
  { name: 'pvout', label: 'Solar Potential (PVOUT)' },
  { name: 'wind', label: 'Wind Speed (100m)' },
  { name: 'buildable_polygons', label: 'Solar Buildable Areas' },
  { name: 'wind_buildable_polygons', label: 'Wind Buildable Areas' },
  { name: 'peatland', label: 'Peatland' },
  { name: 'protected_forest', label: 'Protected Forest' },
  { name: 'industrial', label: 'Industrial Facilities' },
  { name: 'grid_lines', label: 'PLN Grid Lines' },
  { name: 'nickel_smelters', label: 'Nickel Smelters (CGSP)' },
  { name: 'captive_coal', label: 'Captive Coal Plants (GEM)' },
  { name: 'steel_plants', label: 'Steel Plants (GEM)' },
  { name: 'cement_plants', label: 'Cement Plants (GEM)' },
] as const;

const STYLE_KEYS = Object.keys(MAP_STYLES) as MapStyleKey[];

export default function LayerControl() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const toggleLayer = useDashboardStore((s) => s.toggleLayer);
  const mapStyle = useDashboardStore((s) => s.mapStyle);
  const setMapStyle = useDashboardStore((s) => s.setMapStyle);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

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

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors cursor-pointer"
        style={{
          color: open ? 'var(--text-primary)' : 'var(--text-secondary)',
          background: open ? 'var(--selected-bg)' : 'transparent',
          border: `1px solid ${open ? 'var(--glass-border-bright)' : 'transparent'}`,
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
          className="ml-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-medium min-w-[20px] text-center"
          style={{
            background: activeCount > 0 ? 'var(--accent-muted)' : 'transparent',
            color: activeCount > 0 ? 'var(--accent)' : 'transparent',
          }}
        >
          {activeCount}
        </span>
      </button>

      {open && (
        <div
          className="absolute top-[calc(100%+6px)] right-0 z-50 rounded-lg px-3 py-2.5 min-w-[220px]"
          style={{
            backdropFilter: 'var(--blur-heavy)',
            WebkitBackdropFilter: 'var(--blur-heavy)',
            background: 'var(--glass-heavy)',
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
          <div className="space-y-1">
            {LAYER_ITEMS.map(({ name, label }) => (
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
        </div>
      )}
    </div>
  );
}

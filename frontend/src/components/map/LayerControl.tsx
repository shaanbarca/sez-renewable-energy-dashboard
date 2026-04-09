import { useDraggable } from '../../hooks/useDraggable';
import { MAP_STYLES } from '../../lib/constants';
import type { MapStyleKey } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

const LAYER_ITEMS = [
  { name: 'terrain', label: '3D Terrain' },
  { name: 'substations', label: 'Substations (PLN)' },
  { name: 'kek_polygons', label: 'KEK Boundaries' },
  { name: 'pvout', label: 'Solar Potential (PVOUT)' },
  { name: 'buildable', label: 'Solar Buildable Area' },
  { name: 'wind', label: 'Wind Speed (100m)' },
  { name: 'peatland', label: 'Peatland' },
  { name: 'protected_forest', label: 'Protected Forest' },
  { name: 'industrial', label: 'Industrial Facilities' },
  { name: 'grid_lines', label: 'PLN Grid Lines' },
] as const;

const STYLE_KEYS = Object.keys(MAP_STYLES) as MapStyleKey[];

export default function LayerControl() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const toggleLayer = useDashboardStore((s) => s.toggleLayer);
  const mapStyle = useDashboardStore((s) => s.mapStyle);
  const setMapStyle = useDashboardStore((s) => s.setMapStyle);

  const { position: dragPos, handleMouseDown: onDragStart } = useDraggable();

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

  return (
    <div
      className="absolute top-[60px] right-3 z-10 rounded-lg px-3 py-2.5 max-h-[420px] overflow-y-auto"
      style={{
        backdropFilter: 'var(--blur)',
        WebkitBackdropFilter: 'var(--blur)',
        background: 'var(--glass)',
        border: '1px solid var(--glass-border)',
        transform: `translate(${dragPos.x}px, ${dragPos.y}px)`,
      }}
    >
      <div
        className="flex items-center justify-between mb-2 cursor-grab active:cursor-grabbing"
        onMouseDown={onDragStart}
      >
        <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">Layers</div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={selectAll}
            disabled={allOn}
            className="text-[10px] text-[#90CAF9] hover:text-white disabled:text-zinc-600 transition-colors cursor-pointer disabled:cursor-default"
          >
            All
          </button>
          <button
            type="button"
            onClick={deselectAll}
            disabled={noneOn}
            className="text-[10px] text-[#90CAF9] hover:text-white disabled:text-zinc-600 transition-colors cursor-pointer disabled:cursor-default"
          >
            None
          </button>
        </div>
      </div>
      <div className="space-y-1">
        {LAYER_ITEMS.map(({ name, label }) => (
          <label
            key={name}
            className="flex items-center gap-2 cursor-pointer text-xs text-zinc-300 hover:text-white transition-colors py-0.5"
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
      <div className="mt-3 pt-2 pb-3 border-t border-white/10">
        <div className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-1.5">
          Map Style
        </div>
        <div className="flex gap-1">
          {STYLE_KEYS.map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => setMapStyle(key)}
              className={`px-2 py-1 text-[10px] rounded transition-colors cursor-pointer ${
                mapStyle === key
                  ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                  : 'text-zinc-400 hover:text-zinc-200 border border-transparent hover:border-white/10'
              }`}
            >
              {MAP_STYLES[key].label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

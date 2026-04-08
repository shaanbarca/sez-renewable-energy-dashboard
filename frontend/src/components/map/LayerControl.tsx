import { useDashboardStore } from '../../store/dashboard';

const LAYER_ITEMS = [
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

export default function LayerControl() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const toggleLayer = useDashboardStore((s) => s.toggleLayer);

  return (
    <div
      className="absolute top-3 right-3 z-10 rounded-lg px-3 py-2.5 max-h-[340px] overflow-y-auto"
      style={{
        backdropFilter: 'var(--blur)',
        WebkitBackdropFilter: 'var(--blur)',
        background: 'var(--glass)',
        border: '1px solid var(--glass-border)',
      }}
    >
      <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">
        Layers
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
    </div>
  );
}

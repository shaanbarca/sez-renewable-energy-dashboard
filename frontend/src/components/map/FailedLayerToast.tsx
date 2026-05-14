import { useDashboardStore } from '../../store/dashboard';

/**
 * Corner toast that surfaces map layers whose fetch exhausted retries (#59).
 *
 * Before v4.0.6, layer fetch failures were silent — useMapLayers would
 * tight-retry on every render and the symbol layer rendered nothing in
 * between. The user reported this as "substations keep disappearing."
 *
 * Now: after 3 attempts (1s/2s/4s backoff), the layer cache entry is left
 * as `_failed: true`, useMapLayers stops retrying, and this toast appears.
 * Click Retry → calls `retryLayer(name)` which deletes the cache entry,
 * useMapLayers picks it up on the next render and fires fresh fetchWithRetry.
 *
 * Positioned at the bottom-left of the map so it doesn't fight LayerControl
 * (top-right) or the Back-to-National button (top-center).
 */

// Friendly label per layer key. Mirrors LayerControl's labels — when a layer
// gets renamed there, update here too. Single source of truth would be a
// dedicated registry, but at 4 layers the duplication is cheaper than the
// abstraction.
const LAYER_LABELS: Record<string, string> = {
  substations: 'Substations (PLN)',
  grid_lines: 'PLN grid lines',
  kek_polygons: 'KEK boundaries',
  industrial_polygons: 'Industrial polygons',
  peatland: 'Peatland',
  protected_forest: 'Protected forest',
  industrial: 'Industrial facilities',
  nickel_smelters: 'Nickel smelters',
  captive_coal: 'Captive coal plants',
  steel_plants: 'Steel plants',
  cement_plants: 'Cement plants',
  buildable_polygons: 'Solar buildable areas',
  wind_buildable_polygons: 'Wind buildable areas',
};

export default function FailedLayerToast() {
  const layers = useDashboardStore((s) => s.layers);
  const retryLayer = useDashboardStore((s) => s.retryLayer);

  // Find every layer whose cache entry is in the `_failed` state.
  const failed = Object.entries(layers)
    .filter(([_name, entry]) => entry && typeof entry === 'object' && entry._failed === true)
    .map(([name]) => name);

  if (failed.length === 0) return null;

  return (
    <div
      className="absolute bottom-3 left-3 z-40 flex flex-col gap-1.5 pointer-events-auto"
      role="status"
      aria-live="polite"
    >
      {failed.map((name) => (
        <div
          key={name}
          className="px-3 py-2 rounded-md flex items-center gap-3 text-[11px]"
          style={{
            background: 'rgba(244, 67, 54, 0.10)',
            border: '1px solid rgba(244, 67, 54, 0.45)',
            backdropFilter: 'var(--blur)',
            WebkitBackdropFilter: 'var(--blur)',
            color: 'var(--text-primary)',
          }}
        >
          <span
            aria-hidden="true"
            style={{
              color: '#EF5350',
              fontWeight: 700,
              flexShrink: 0,
            }}
          >
            ⚠
          </span>
          <span className="flex-1">
            <span style={{ color: '#EF9A9A', fontWeight: 600 }}>{LAYER_LABELS[name] ?? name}</span>
            <span className="ml-1.5" style={{ color: 'var(--text-secondary)' }}>
              failed to load
            </span>
          </span>
          <button
            type="button"
            onClick={() => retryLayer(name)}
            className="text-[10px] px-2 py-0.5 rounded transition-colors flex-shrink-0"
            style={{
              color: '#EF9A9A',
              border: '1px solid rgba(244, 67, 54, 0.55)',
              background: 'transparent',
              cursor: 'pointer',
            }}
            title={`Retry fetching ${LAYER_LABELS[name] ?? name}`}
          >
            Retry
          </button>
        </div>
      ))}
    </div>
  );
}

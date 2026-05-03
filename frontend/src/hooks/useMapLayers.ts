import { useEffect } from 'react';
import { fetchLayer } from '../lib/api';
import { useDashboardStore } from '../store/dashboard';

/**
 * Lazy-loads layer data when a layer is toggled visible for the first time.
 * Returns the cached layers record.
 */
export function useMapLayers() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const layers = useDashboardStore((s) => s.layers);

  useEffect(() => {
    // Layers handled client-side (not fetched from /api/layers/).
    // rooftop_tiles is per-site (fetched via /api/site/{id}/rooftop-tiles in
    // MapView when a site is selected) — the LayerControl entry is just a
    // visibility toggle.
    const CLIENT_ONLY_LAYERS = new Set(['terrain', 'rooftop_tiles']);

    // Composite layers: a single visibility toggle drives multiple data fetches.
    // `site_boundaries` shows KEK polygons (blue) + non-KEK industrial polygons
    // (orange) together so reviewers can verify rooftop polygon coverage at a glance.
    const COMPOSITE_LAYERS: Record<string, string[]> = {
      site_boundaries: ['kek_polygons', 'industrial_polygons'],
    };

    const fetchAndStore = (name: string) => {
      if (name in layers) return;
      useDashboardStore.setState((state) => ({
        layers: { ...state.layers, [name]: { _loading: true } },
      }));
      fetchLayer(name)
        .then((data) => {
          useDashboardStore.setState((state) => ({
            layers: { ...state.layers, [name]: data },
          }));
        })
        .catch((err) => {
          console.error(`Failed to fetch layer "${name}":`, err);
          useDashboardStore.setState((state) => {
            const next = { ...state.layers };
            delete next[name];
            return { layers: next };
          });
        });
    };

    for (const [name, visible] of Object.entries(layerVisibility)) {
      if (!visible) continue;
      if (CLIENT_ONLY_LAYERS.has(name)) continue;
      if (name in COMPOSITE_LAYERS) {
        for (const target of COMPOSITE_LAYERS[name]) fetchAndStore(target);
        continue;
      }
      fetchAndStore(name);
    }
  }, [layerVisibility, layers]);

  return layers;
}

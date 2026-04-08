import { useEffect } from 'react';
import { useDashboardStore } from '../store/dashboard';
import { fetchLayer } from '../lib/api';

/**
 * Lazy-loads layer data when a layer is toggled visible for the first time.
 * Returns the cached layers record.
 */
export function useMapLayers() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const layers = useDashboardStore((s) => s.layers);

  useEffect(() => {
    for (const [name, visible] of Object.entries(layerVisibility)) {
      if (visible && !(name in layers)) {
        // Mark as loading to prevent duplicate fetches
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
            // Remove the loading sentinel so user can retry
            useDashboardStore.setState((state) => {
              const next = { ...state.layers };
              delete next[name];
              return { layers: next };
            });
          });
      }
    }
  }, [layerVisibility, layers]);

  return layers;
}

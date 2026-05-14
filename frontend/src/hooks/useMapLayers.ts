import { useEffect } from 'react';
import { fetchLayer } from '../lib/api';
import { useDashboardStore } from '../store/dashboard';

/**
 * Lazy-loads layer data when a layer is toggled visible for the first time.
 *
 * Failure handling (#59 — replaces the pre-v4.0.6 tight retry loop):
 *
 * Pre-v4.0.6, fetch failures `delete next[name]` from the cache. The effect
 * deps `[layerVisibility, layers]` would re-fire on state change and re-fetch,
 * looping every few seconds against a flaky backend with no user signal.
 *
 * v4.0.6 (this file):
 *   1. On fetch failure, schedule up to 3 retries with exponential backoff
 *      (1s / 2s / 4s). Retries happen via setTimeout, NOT by re-firing the
 *      effect — the effect's `if (name in layers) return` guard prevents
 *      duplicate fetches while a retry is queued.
 *   2. After 3 failures, the cache entry is left as `{ _failed: true }`. The
 *      effect sees it and skips. The user can re-trigger via the
 *      FailedLayerToast Retry button (toggleLayer in the store deletes
 *      `_failed` entries on off → on transition).
 *
 * Result: the user sees one of three states for every visible layer:
 *   `_loading: true`  → first attempt or in-flight retry
 *   `_failed: true`   → max retries exhausted, awaiting manual retry
 *   data              → success
 *
 * The corner toast renders for any `_failed` entry. See FailedLayerToast.tsx.
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

    const fetchWithRetry = (name: string, attempt: number): void => {
      // Mark in-flight. Effect short-circuits via `name in layers` on the next
      // render so we don't double-fetch while a retry is queued.
      useDashboardStore.setState((state) => ({
        layers: { ...state.layers, [name]: { _loading: true, _attempt: attempt } },
      }));
      fetchLayer(name)
        .then((data) => {
          useDashboardStore.setState((state) => ({
            layers: { ...state.layers, [name]: data },
          }));
        })
        .catch((err) => {
          console.error(
            `Failed to fetch layer "${name}" (attempt ${attempt}/${MAX_RETRIES}):`,
            err,
          );
          if (attempt < MAX_RETRIES) {
            const delay = BACKOFF_BASE_MS * 2 ** (attempt - 1); // 1s, 2s, 4s
            setTimeout(() => fetchWithRetry(name, attempt + 1), delay);
          } else {
            // Final failure — surface to UI. Toggle off → on (via toggleLayer)
            // is the only path that clears this without an explicit Retry click.
            useDashboardStore.setState((state) => ({
              layers: {
                ...state.layers,
                [name]: { _failed: true, _attempt: attempt },
              },
            }));
          }
        });
    };

    const fetchAndStore = (name: string) => {
      if (name in layers) return; // already cached, loading, or _failed
      fetchWithRetry(name, 1);
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

// Exponential backoff config — exported for tests so they can mirror the
// timing assumptions without copy-pasting magic numbers.
export const MAX_RETRIES = 3;
export const BACKOFF_BASE_MS = 1000;

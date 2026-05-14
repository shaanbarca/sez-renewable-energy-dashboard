/**
 * Regression tests for the dashboard Zustand store.
 *
 * These pin the layer-default behavior of `selectSite` + `setEnergyMode` so
 * future refactors can't silently re-introduce the "substations keep
 * disappearing" bug we diagnosed on 2026-05-14 (PR #60):
 *
 *   - On first site-select, substations + grid_lines flip ON automatically.
 *     Before #60, they defaulted to undefined (off) and nothing turned them
 *     on, so every fresh tab was missing critical context for the LCOE.
 *
 *   - The first-time-only guard (`if undefined`) must respect an explicit
 *     user toggle-off. If the user hides substations via LayerControl, they
 *     stay hidden on subsequent site-selects.
 *
 *   - `setEnergyMode` (solar / wind / hybrid / geothermal) must NEVER clobber
 *     substations or grid_lines. Those are independent of the energy mode.
 *
 * The store touches localStorage + window at module load, so vitest runs
 * under happy-dom (configured in vitest.config.ts).
 */

import { beforeEach, describe, expect, it } from 'vitest';
import { useDashboardStore } from '../dashboard';

// Snapshot the pristine initial state so each test starts fresh. The store is
// a singleton across imports; tests that mutate it would otherwise leak.
const INITIAL_STATE = useDashboardStore.getState();

beforeEach(() => {
  useDashboardStore.setState(
    { ...INITIAL_STATE, layerVisibility: {}, selectedSite: null, drawerOpen: false },
    false,
  );
});

describe('selectSite — layer defaults (#26 / #60)', () => {
  it('turns substations ON on first site-select', () => {
    expect(useDashboardStore.getState().layerVisibility.substations).toBeUndefined();
    useDashboardStore.getState().selectSite('kek-palu');
    expect(useDashboardStore.getState().layerVisibility.substations).toBe(true);
  });

  it('turns grid_lines ON on first site-select', () => {
    expect(useDashboardStore.getState().layerVisibility.grid_lines).toBeUndefined();
    useDashboardStore.getState().selectSite('kek-palu');
    expect(useDashboardStore.getState().layerVisibility.grid_lines).toBe(true);
  });

  it('turns buildable_polygons ON unconditionally on every site-select', () => {
    // buildable_polygons differs from the others — it's reset to true every
    // time so the chosen-polygon highlight is always visible.
    useDashboardStore.setState({ layerVisibility: { buildable_polygons: false } });
    useDashboardStore.getState().selectSite('kek-palu');
    expect(useDashboardStore.getState().layerVisibility.buildable_polygons).toBe(true);
  });

  it('respects explicit toggle-off for substations on subsequent site-select', () => {
    // User explicitly hides substations via LayerControl after first select.
    useDashboardStore.getState().selectSite('kek-palu');
    useDashboardStore.setState((s) => ({
      layerVisibility: { ...s.layerVisibility, substations: false },
    }));
    // Switching to a different site must not re-enable substations.
    useDashboardStore.getState().selectSite('kek-mandalika');
    expect(useDashboardStore.getState().layerVisibility.substations).toBe(false);
  });

  it('respects explicit toggle-off for grid_lines on subsequent site-select', () => {
    useDashboardStore.getState().selectSite('kek-palu');
    useDashboardStore.setState((s) => ({
      layerVisibility: { ...s.layerVisibility, grid_lines: false },
    }));
    useDashboardStore.getState().selectSite('kek-mandalika');
    expect(useDashboardStore.getState().layerVisibility.grid_lines).toBe(false);
  });

  it('also enables rooftop_tiles + site_boundaries on first site-select', () => {
    // These were the originally-defaulted layers; pinning them so a refactor
    // can't drop the pattern.
    useDashboardStore.getState().selectSite('kek-palu');
    const lv = useDashboardStore.getState().layerVisibility;
    expect(lv.rooftop_tiles).toBe(true);
    expect(lv.site_boundaries).toBe(true);
  });
});

describe('selectSite(null) — "Back to national view" cleanup (#60)', () => {
  // At national scale (81 sites, 2913 substations, 1595 grid line segments)
  // the per-site context layers become visual noise. Going back to national
  // view should drop them so the map reads cleanly.

  it('clears substations on selectSite(null)', () => {
    useDashboardStore.getState().selectSite('kek-palu');
    expect(useDashboardStore.getState().layerVisibility.substations).toBe(true);
    useDashboardStore.getState().selectSite(null);
    expect(useDashboardStore.getState().layerVisibility.substations).toBeUndefined();
  });

  it('clears grid_lines on selectSite(null)', () => {
    useDashboardStore.getState().selectSite('kek-palu');
    expect(useDashboardStore.getState().layerVisibility.grid_lines).toBe(true);
    useDashboardStore.getState().selectSite(null);
    expect(useDashboardStore.getState().layerVisibility.grid_lines).toBeUndefined();
  });

  it('re-enables substations + grid_lines on the next site-select', () => {
    // The round-trip: select → deselect → select again should restore the
    // auto-enabled layers. Deleting (rather than setting to false) on
    // selectSite(null) is what makes this work — the `if undefined` guard
    // sees the cleared key as a fresh first-time selection.
    useDashboardStore.getState().selectSite('kek-palu');
    useDashboardStore.getState().selectSite(null);
    useDashboardStore.getState().selectSite('kek-bitung');
    expect(useDashboardStore.getState().layerVisibility.substations).toBe(true);
    expect(useDashboardStore.getState().layerVisibility.grid_lines).toBe(true);
  });

  it('preserves other layer toggles on selectSite(null)', () => {
    // Only substations + grid_lines should clear. The user's other layer
    // choices (peatland, protected_forest, nickel_smelters, etc.) stay
    // wherever they were.
    useDashboardStore.setState({
      layerVisibility: { peatland: true, nickel_smelters: true },
    });
    useDashboardStore.getState().selectSite('kek-palu');
    useDashboardStore.getState().selectSite(null);
    const lv = useDashboardStore.getState().layerVisibility;
    expect(lv.peatland).toBe(true);
    expect(lv.nickel_smelters).toBe(true);
  });
});

describe('setEnergyMode — substation/grid invariant (#60)', () => {
  // Energy-mode changes legitimately toggle PVOUT / wind / geothermal /
  // buildable layers. They must NOT touch substations or grid_lines — those
  // are independent infrastructure context that stays as the user set them.
  const MODES = ['solar', 'wind', 'hybrid', 'geothermal'] as const;

  for (const mode of MODES) {
    it(`preserves substations on switch to ${mode}`, () => {
      useDashboardStore.setState({
        layerVisibility: { substations: true, grid_lines: true },
      });
      useDashboardStore.getState().setEnergyMode(mode);
      expect(useDashboardStore.getState().layerVisibility.substations).toBe(true);
    });

    it(`preserves grid_lines on switch to ${mode}`, () => {
      useDashboardStore.setState({
        layerVisibility: { substations: true, grid_lines: true },
      });
      useDashboardStore.getState().setEnergyMode(mode);
      expect(useDashboardStore.getState().layerVisibility.grid_lines).toBe(true);
    });

    it(`preserves substations-off intent on switch to ${mode}`, () => {
      // If the user explicitly hid substations, switching modes must not
      // resurrect them either.
      useDashboardStore.setState({
        layerVisibility: { substations: false, grid_lines: false },
      });
      useDashboardStore.getState().setEnergyMode(mode);
      expect(useDashboardStore.getState().layerVisibility.substations).toBe(false);
      expect(useDashboardStore.getState().layerVisibility.grid_lines).toBe(false);
    });
  }
});

describe('layer fetch failure handling (#59)', () => {
  // useMapLayers marks `_failed` on terminal fetch failure. Toggling a failed
  // layer off→on, or hitting the FailedLayerToast Retry button, must clear
  // the cache entry so the next render re-fetches.

  it('toggleLayer off→on clears a _failed cache entry', () => {
    useDashboardStore.setState({
      layerVisibility: { substations: false },
      layers: { substations: { _failed: true, _attempt: 3 } },
    });
    useDashboardStore.getState().toggleLayer('substations');
    const s = useDashboardStore.getState();
    expect(s.layerVisibility.substations).toBe(true);
    // The _failed entry must be gone so useMapLayers picks the layer up.
    expect('substations' in s.layers).toBe(false);
  });

  it('toggleLayer on→off leaves a _failed entry alone', () => {
    // Toggling visibility off should not destroy state. The user could be
    // hiding a broken layer temporarily; the failure status survives.
    useDashboardStore.setState({
      layerVisibility: { substations: true },
      layers: { substations: { _failed: true, _attempt: 3 } },
    });
    useDashboardStore.getState().toggleLayer('substations');
    const s = useDashboardStore.getState();
    expect(s.layerVisibility.substations).toBe(false);
    expect(s.layers.substations?._failed).toBe(true);
  });

  it('toggleLayer off→on does NOT touch a successfully-loaded cache entry', () => {
    // Sanity: only _failed entries are evicted. Loaded data must survive
    // toggle cycles to avoid wasteful refetches.
    const data = { features: [], _loadedAt: 'snapshot' };
    useDashboardStore.setState({
      layerVisibility: { substations: false },
      layers: { substations: data },
    });
    useDashboardStore.getState().toggleLayer('substations');
    expect(useDashboardStore.getState().layers.substations).toBe(data);
  });

  it('retryLayer clears a _failed cache entry', () => {
    useDashboardStore.setState({
      layers: { substations: { _failed: true, _attempt: 3 } },
    });
    useDashboardStore.getState().retryLayer('substations');
    expect('substations' in useDashboardStore.getState().layers).toBe(false);
  });

  it('retryLayer is a no-op for a non-failed cache entry', () => {
    // Defensive — Retry button click on a layer that recovered between
    // render and click should not nuke valid data.
    const data = { features: [], _loadedAt: 'snapshot' };
    useDashboardStore.setState({
      layers: { substations: data },
    });
    useDashboardStore.getState().retryLayer('substations');
    expect(useDashboardStore.getState().layers.substations).toBe(data);
  });

  it('retryLayer leaves visibility unchanged', () => {
    // Retry is a fetch-only concern. It must not flip the layer on/off
    // (the user controls visibility via LayerControl).
    useDashboardStore.setState({
      layerVisibility: { substations: false },
      layers: { substations: { _failed: true, _attempt: 3 } },
    });
    useDashboardStore.getState().retryLayer('substations');
    expect(useDashboardStore.getState().layerVisibility.substations).toBe(false);
  });
});

describe('polygon override (#26)', () => {
  it('setPolygonOverride writes the feature_index for the given site', () => {
    useDashboardStore.getState().setPolygonOverride('kek-palu', 42);
    expect(useDashboardStore.getState().polygonOverrideBySite['kek-palu']).toBe(42);
  });

  it('clearPolygonOverride removes the entry entirely', () => {
    // The empty-key check in api.ts only sends polygon_overrides when the map
    // is non-empty. Clearing must actually delete the key, not just set to
    // null, or we'd send {kek-palu: null} and the backend would 422 on the
    // unknown-feature-index error.
    useDashboardStore.getState().setPolygonOverride('kek-palu', 5);
    useDashboardStore.getState().clearPolygonOverride('kek-palu');
    expect('kek-palu' in useDashboardStore.getState().polygonOverrideBySite).toBe(false);
  });

  it('multi-site overrides are independent', () => {
    useDashboardStore.getState().setPolygonOverride('kek-palu', 1);
    useDashboardStore.getState().setPolygonOverride('kek-bitung', 2);
    expect(useDashboardStore.getState().polygonOverrideBySite).toEqual({
      'kek-palu': 1,
      'kek-bitung': 2,
    });
    useDashboardStore.getState().clearPolygonOverride('kek-palu');
    expect(useDashboardStore.getState().polygonOverrideBySite).toEqual({ 'kek-bitung': 2 });
  });
});

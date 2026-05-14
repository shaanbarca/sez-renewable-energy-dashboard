import { create } from 'zustand';
import { fetchDefaults, fetchScorecard, listPolygonOverrides, probeAdminMode } from '../lib/api';
import { defaultCostBasis, isBasisSupported } from '../lib/costBasis';
import { computeFlipDiff, type FlipDiffRow, type FlipSummary } from '../lib/flipDiff';
import { applyFlipPreset, type FlipPreset } from '../lib/flipPresets';
import type {
  BenchmarkMode,
  BottomTab,
  CostBasis,
  DefaultsResponse,
  EnergyMode,
  MapStyleKey,
  SavedScenario,
  ScorecardRow,
  UserAssumptions,
  UserThresholds,
} from '../lib/types';
import { parseUrlAssumptions } from '../lib/urlState';

interface DashboardStore {
  // Data
  assumptions: UserAssumptions | null;
  defaultAssumptions: UserAssumptions | null;
  thresholds: UserThresholds | null;
  sliderConfigs: DefaultsResponse['slider_configs'] | null;
  scorecard: ScorecardRow[] | null;

  // UI state
  selectedSite: string | null;
  drawerOpen: boolean;
  assumptionsExpanded: boolean;
  bottomPanelCollapsed: boolean;
  bottomPanelHeight: number;
  activeTab: BottomTab;
  layerVisibility: Record<string, boolean>;
  benchmarkMode: BenchmarkMode;
  energyMode: EnergyMode;
  costBasis: CostBasis;
  mapStyle: MapStyleKey;
  loading: boolean;
  walkthroughPersona: string | null;
  walkthroughStep: number;
  walkthroughDismissed: boolean;
  savedScenarios: SavedScenario[];
  flyToTarget: { lat: number; lon: number; zoom?: number } | null;
  filteredSiteIds: Set<string> | null;

  // Compare scenarios (A/B flip) — the Scenario Compare tab being active IS compare mode
  flipAssumptions: UserAssumptions | null;
  flipPreset: FlipPreset | 'custom' | null;
  flipScorecard: ScorecardRow[] | null;
  flipLoading: boolean;
  flipStale: boolean;

  // Cached layer data
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  layers: Record<string, any>;

  // Admin polygon editor (#31 phase 2)
  adminMode: boolean;
  manualOverrideSiteIds: Set<string>;
  editingPolygonForSite: string | null;

  // #26 — per-site polygon override (click to recompute grid-connected LCOE).
  // Map of site_id → feature_index of the clicked buildable polygon. Cleared
  // when the user switches sites or hits the Score Drawer's Reset button.
  // Sent verbatim in /api/scorecard POST body.
  polygonOverrideBySite: Record<string, number>;

  // Actions
  setAssumptions: (a: Partial<UserAssumptions>) => void;
  setThresholds: (t: Partial<UserThresholds>) => void;
  selectSite: (id: string | null) => void;
  closeDrawer: () => void;
  setBottomPanelCollapsed: (collapsed: boolean) => void;
  setBottomPanelHeight: (height: number) => void;
  setActiveTab: (tab: BottomTab) => void;
  setEnergyMode: (mode: EnergyMode) => void;
  setBenchmarkMode: (mode: BenchmarkMode) => void;
  setCostBasis: (basis: CostBasis) => void;
  setMapStyle: (style: MapStyleKey) => void;
  toggleLayer: (name: string) => void;
  recomputeScorecard: () => Promise<void>;
  resetDefaults: () => void;
  saveScenario: (name: string) => void;
  loadScenario: (id: string) => void;
  deleteScenario: (id: string) => void;
  initialize: () => Promise<void>;
  setWalkthroughPersona: (p: string | null) => void;
  nextWalkthroughStep: () => void;
  prevWalkthroughStep: () => void;
  dismissWalkthrough: () => void;
  restartWalkthrough: () => void;
  flyTo: (lat: number, lon: number, zoom?: number) => void;
  clearFlyTo: () => void;
  setFilteredSiteIds: (ids: Set<string> | null) => void;

  // Compare scenarios actions
  setFlipAssumptions: (a: Partial<UserAssumptions>) => void;
  applyFlipPreset: (p: FlipPreset) => void;
  computeFlip: () => Promise<void>;
  clearFlip: () => void;
  flipDiff: () => { rows: FlipDiffRow[]; summary: FlipSummary } | null;

  // Admin polygon editor actions (#31 phase 2)
  enterPolygonEdit: (siteId: string) => void;
  exitPolygonEdit: () => void;
  refreshManualOverrides: () => Promise<void>;

  // #26 — polygon override actions
  setPolygonOverride: (siteId: string, featureIndex: number) => void;
  clearPolygonOverride: (siteId: string) => void;
}

// Store the original defaults so resetDefaults can restore them
let _defaultAssumptions: UserAssumptions | null = null;
let _defaultThresholds: UserThresholds | null = null;

export const useDashboardStore = create<DashboardStore>((set, get) => ({
  // Data
  assumptions: null,
  defaultAssumptions: null,
  thresholds: null,
  sliderConfigs: null,
  scorecard: null,

  // UI state
  selectedSite: null,
  drawerOpen: false,
  assumptionsExpanded: false,
  bottomPanelCollapsed: false,
  bottomPanelHeight: 380,
  activeTab: 'table',
  layerVisibility: {},
  benchmarkMode: 'bpp',
  energyMode: 'solar',
  costBasis: defaultCostBasis('solar'),
  mapStyle: 'satellite',
  loading: true,
  walkthroughPersona: null,
  walkthroughStep: 0,
  walkthroughDismissed: localStorage.getItem('walkthrough_dismissed') === 'true',
  savedScenarios: (() => {
    try {
      return JSON.parse(localStorage.getItem('kek_saved_scenarios') || '[]');
    } catch {
      return [];
    }
  })(),
  flyToTarget: null,
  filteredSiteIds: null,

  // Admin polygon editor (#31 phase 2) — disabled by default; `initialize`
  // probes /api/admin/polygons to detect when dev has EEZ_ENABLE_ADMIN_TOOLS=1.
  adminMode: false,
  manualOverrideSiteIds: new Set<string>(),
  editingPolygonForSite: null,

  // #26 — polygon override map. Starts empty (auto-pick everywhere).
  polygonOverrideBySite: {},

  // Compare scenarios
  flipAssumptions: null,
  flipPreset: null,
  flipScorecard: null,
  flipLoading: false,
  flipStale: false,

  // Cached layer data
  layers: {},

  // Actions
  setAssumptions: (a) =>
    set((state) => ({
      assumptions: state.assumptions ? { ...state.assumptions, ...a } : null,
      // Baseline assumptions changed — flip scorecard now stale until recomputed
      flipStale: state.flipScorecard != null ? true : state.flipStale,
    })),

  setThresholds: (t) =>
    set((state) => ({
      thresholds: state.thresholds ? { ...state.thresholds, ...t } : null,
      flipStale: state.flipScorecard != null ? true : state.flipStale,
    })),

  selectSite: (id) =>
    set((state) => {
      if (!id)
        return { selectedSite: null, drawerOpen: false, layerVisibility: state.layerVisibility };
      const lv = { ...state.layerVisibility };
      // Always show solar buildable polygons so the amber chosen-polygon highlight is visible.
      lv.buildable_polygons = true;
      // First time a site is selected, default rooftop tiles ON so the
      // user sees the headline visualization. Subsequent selections respect
      // whatever the user toggled (so we only set it when undefined).
      if (lv.rooftop_tiles === undefined) lv.rooftop_tiles = true;
      // Same for site boundaries — first selection turns them on so users
      // immediately see the fence polygon (KEK blue / industrial orange) and
      // can sanity-check the rooftop number against the actual plant area.
      if (lv.site_boundaries === undefined) lv.site_boundaries = true;
      // Substations + transmission lines on by default on first site-select.
      // The grid-connected LCOE depends on substation distance; users need to
      // see what's nearby to evaluate the picker's choice (or pick a polygon
      // near a different substation, per #26). Same `if undefined` guard so
      // users who explicitly toggle them off via LayerControl keep them off.
      if (lv.substations === undefined) lv.substations = true;
      if (lv.grid_lines === undefined) lv.grid_lines = true;
      if (state.energyMode === 'wind') {
        lv.wind_buildable_polygons = true;
        lv.wind = true;
      } else if (state.energyMode === 'solar') {
        lv.pvout = true;
      } else {
        lv.wind_buildable_polygons = true;
      }
      return { selectedSite: id, drawerOpen: true, layerVisibility: lv };
    }),

  closeDrawer: () => set({ drawerOpen: false }),

  setBottomPanelCollapsed: (collapsed) => set({ bottomPanelCollapsed: collapsed }),
  setBottomPanelHeight: (height) => set({ bottomPanelHeight: height }),

  setActiveTab: (tab) => set({ activeTab: tab }),

  setEnergyMode: (mode) =>
    set((state) => {
      const lv = { ...state.layerVisibility };
      if (mode === 'wind') {
        lv.wind = true;
        lv.pvout = false;
        lv.buildable_polygons = false;
        lv.wind_buildable_polygons = true;
        lv.geothermal_operating = false;
        lv.geothermal_pipeline = false;
      } else if (mode === 'solar') {
        lv.pvout = true;
        lv.wind = false;
        lv.buildable_polygons = true;
        lv.wind_buildable_polygons = false;
        lv.geothermal_operating = false;
        lv.geothermal_pipeline = false;
      } else if (mode === 'hybrid') {
        lv.pvout = true;
        lv.wind = true;
        lv.buildable_polygons = true;
        lv.wind_buildable_polygons = true;
        lv.geothermal_operating = false;
        lv.geothermal_pipeline = false;
      } else if (mode === 'geothermal') {
        lv.geothermal_operating = true;
        lv.geothermal_pipeline = true;
        lv.pvout = false;
        lv.wind = false;
        lv.buildable_polygons = false;
        lv.wind_buildable_polygons = false;
      }
      // 'overall' — leave layers as-is, user controls via LayerControl
      // Auto-flip costBasis only when the current choice is invalid for the new mode.
      // Preserves user intent (e.g. firmed on solar stays firmed when switching to wind).
      const nextBasis = isBasisSupported(mode, state.costBasis)
        ? state.costBasis
        : defaultCostBasis(mode);
      return { energyMode: mode, costBasis: nextBasis, layerVisibility: lv };
    }),

  setBenchmarkMode: (mode) => set({ benchmarkMode: mode }),

  setCostBasis: (basis) => set({ costBasis: basis }),

  setMapStyle: (style) => set({ mapStyle: style }),

  toggleLayer: (name) =>
    set((state) => ({
      layerVisibility: {
        ...state.layerVisibility,
        [name]: !state.layerVisibility[name],
      },
    })),

  recomputeScorecard: async () => {
    const { assumptions, thresholds, benchmarkMode, polygonOverrideBySite } = get();
    if (!assumptions || !thresholds) return;

    set({ loading: true });
    try {
      const data = await fetchScorecard(
        assumptions,
        thresholds,
        benchmarkMode,
        polygonOverrideBySite,
      );
      set({ scorecard: data.scorecard, loading: false });
    } catch (err) {
      console.error('Failed to recompute scorecard:', err);
      set({ loading: false });
      // #26 — if the server rejected one of our overrides (e.g. stale
      // feature_index after a pipeline regen), clear all overrides so the
      // next request goes through cleanly. The user can re-click if needed.
      if (err instanceof Error && /422/.test(err.message)) {
        set({ polygonOverrideBySite: {} });
      }
    }
  },

  resetDefaults: () => {
    if (_defaultAssumptions && _defaultThresholds) {
      set({
        assumptions: { ..._defaultAssumptions },
        thresholds: { ..._defaultThresholds },
        benchmarkMode: 'bpp',
      });
      // Clear URL params
      window.history.replaceState(null, '', window.location.pathname);
    }
  },

  setWalkthroughPersona: (p) => set({ walkthroughPersona: p, walkthroughStep: 0 }),

  nextWalkthroughStep: () => set((s) => ({ walkthroughStep: s.walkthroughStep + 1 })),

  prevWalkthroughStep: () => set((s) => ({ walkthroughStep: Math.max(0, s.walkthroughStep - 1) })),

  dismissWalkthrough: () => {
    localStorage.setItem('walkthrough_dismissed', 'true');
    set({ walkthroughDismissed: true, walkthroughPersona: null, walkthroughStep: 0 });
  },

  restartWalkthrough: () =>
    set({ walkthroughDismissed: false, walkthroughPersona: null, walkthroughStep: 0 }),

  flyTo: (lat, lon, zoom) => set({ flyToTarget: { lat, lon, zoom } }),
  clearFlyTo: () => set({ flyToTarget: null }),
  setFilteredSiteIds: (ids) => set({ filteredSiteIds: ids }),

  enterPolygonEdit: (siteId) => set({ editingPolygonForSite: siteId, drawerOpen: false }),
  exitPolygonEdit: () => set({ editingPolygonForSite: null }),
  refreshManualOverrides: async () => {
    if (!get().adminMode) return;
    try {
      const ids = await listPolygonOverrides();
      set({ manualOverrideSiteIds: new Set(ids) });
    } catch (err) {
      console.warn('listPolygonOverrides failed:', err);
    }
  },

  setFlipAssumptions: (a) =>
    set((state) => ({
      flipAssumptions: state.flipAssumptions
        ? { ...state.flipAssumptions, ...a }
        : state.assumptions
          ? { ...state.assumptions, ...a }
          : null,
      flipPreset: 'custom',
      flipStale: state.flipScorecard != null ? true : state.flipStale,
    })),

  applyFlipPreset: (p) =>
    set((state) => {
      const baseline = state.assumptions;
      if (!baseline) return {};
      const overrides = applyFlipPreset(baseline, p);
      return {
        flipAssumptions: { ...baseline, ...overrides },
        flipPreset: p,
        flipStale: state.flipScorecard != null,
      };
    }),

  computeFlip: async () => {
    const { flipAssumptions, thresholds, benchmarkMode } = get();
    if (!flipAssumptions || !thresholds) return;
    set({ flipLoading: true });
    try {
      const data = await fetchScorecard(flipAssumptions, thresholds, benchmarkMode);
      set({ flipScorecard: data.scorecard, flipLoading: false, flipStale: false });
    } catch (err) {
      console.error('Failed to compute flip scorecard:', err);
      set({ flipLoading: false });
    }
  },

  clearFlip: () =>
    set({
      flipAssumptions: null,
      flipPreset: null,
      flipScorecard: null,
      flipLoading: false,
      flipStale: false,
    }),

  flipDiff: () => {
    const { scorecard, flipScorecard, energyMode, costBasis } = get();
    if (!scorecard || !flipScorecard) return null;
    return computeFlipDiff(scorecard, flipScorecard, energyMode, costBasis);
  },

  saveScenario: (name) => {
    const { assumptions, thresholds, benchmarkMode, savedScenarios } = get();
    if (!assumptions || !thresholds || savedScenarios.length >= 3) return;
    const scenario: SavedScenario = {
      id: crypto.randomUUID(),
      name: name.slice(0, 30),
      assumptions: { ...assumptions },
      thresholds: { ...thresholds },
      benchmarkMode,
      createdAt: new Date().toISOString(),
    };
    const updated = [...savedScenarios, scenario];
    localStorage.setItem('kek_saved_scenarios', JSON.stringify(updated));
    set({ savedScenarios: updated });
  },

  loadScenario: (id) => {
    const scenario = get().savedScenarios.find((s) => s.id === id);
    if (!scenario) return;
    set({
      assumptions: { ...scenario.assumptions },
      thresholds: { ...scenario.thresholds },
      benchmarkMode: scenario.benchmarkMode,
    });
  },

  deleteScenario: (id) => {
    const updated = get().savedScenarios.filter((s) => s.id !== id);
    localStorage.setItem('kek_saved_scenarios', JSON.stringify(updated));
    set({ savedScenarios: updated });
  },

  initialize: async () => {
    set({ loading: true });
    try {
      const defaults = await fetchDefaults();

      _defaultAssumptions = defaults.assumptions;
      _defaultThresholds = defaults.thresholds;

      // Hydrate from URL query params (overrides defaults)
      const urlOverrides = parseUrlAssumptions();
      const mergedAssumptions = { ...defaults.assumptions, ...urlOverrides.assumptions };
      const mergedBenchmark = urlOverrides.benchmarkMode || 'bpp';

      set({
        assumptions: mergedAssumptions,
        defaultAssumptions: { ...defaults.assumptions },
        thresholds: defaults.thresholds,
        sliderConfigs: defaults.slider_configs,
        benchmarkMode: mergedBenchmark,
      });

      const data = await fetchScorecard(mergedAssumptions, defaults.thresholds, mergedBenchmark);
      set({ scorecard: data.scorecard, loading: false });

      // Admin polygon editor (#31 phase 2): detect whether the backend has
      // admin tooling enabled. Probe is silent on failure — admin off is the
      // expected production state, not an error.
      probeAdminMode()
        .then(async (enabled) => {
          set({ adminMode: enabled });
          if (enabled) {
            try {
              const ids = await listPolygonOverrides();
              set({ manualOverrideSiteIds: new Set(ids) });
            } catch (err) {
              console.warn('listPolygonOverrides failed:', err);
            }
          }
        })
        .catch(() => {
          // probeAdminMode never throws by contract; defensive.
        });
    } catch (err) {
      console.error('Failed to initialize dashboard:', err);
      set({ loading: false });
    }
  },

  // #26 — polygon override actions
  setPolygonOverride: (siteId, featureIndex) =>
    set((state) => ({
      polygonOverrideBySite: { ...state.polygonOverrideBySite, [siteId]: featureIndex },
    })),

  clearPolygonOverride: (siteId) =>
    set((state) => {
      // Drop the site_id key entirely so empty-map check in fetchScorecard skips
      // the field in the request body.
      const { [siteId]: _removed, ...rest } = state.polygonOverrideBySite;
      return { polygonOverrideBySite: rest };
    }),
}));

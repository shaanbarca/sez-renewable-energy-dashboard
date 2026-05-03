import { create } from 'zustand';
import { fetchDefaults, fetchScorecard } from '../lib/api';
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
      } else if (mode === 'solar') {
        lv.pvout = true;
        lv.wind = false;
        lv.buildable_polygons = true;
        lv.wind_buildable_polygons = false;
      } else if (mode === 'hybrid') {
        lv.pvout = true;
        lv.wind = true;
        lv.buildable_polygons = true;
        lv.wind_buildable_polygons = true;
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
    const { assumptions, thresholds, benchmarkMode } = get();
    if (!assumptions || !thresholds) return;

    set({ loading: true });
    try {
      const data = await fetchScorecard(assumptions, thresholds, benchmarkMode);
      set({ scorecard: data.scorecard, loading: false });
    } catch (err) {
      console.error('Failed to recompute scorecard:', err);
      set({ loading: false });
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
    } catch (err) {
      console.error('Failed to initialize dashboard:', err);
      set({ loading: false });
    }
  },
}));

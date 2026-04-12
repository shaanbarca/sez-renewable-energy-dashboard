import { create } from 'zustand';
import { fetchDefaults, fetchScorecard } from '../lib/api';
import type {
  BenchmarkMode,
  BottomTab,
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
  selectedKek: string | null;
  drawerOpen: boolean;
  assumptionsExpanded: boolean;
  activeTab: BottomTab;
  layerVisibility: Record<string, boolean>;
  benchmarkMode: BenchmarkMode;
  energyMode: EnergyMode;
  mapStyle: MapStyleKey;
  loading: boolean;
  walkthroughPersona: string | null;
  walkthroughStep: number;
  walkthroughDismissed: boolean;
  savedScenarios: SavedScenario[];

  // Cached layer data
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  layers: Record<string, any>;

  // Actions
  setAssumptions: (a: Partial<UserAssumptions>) => void;
  setThresholds: (t: Partial<UserThresholds>) => void;
  selectKek: (id: string | null) => void;
  closeDrawer: () => void;
  setActiveTab: (tab: BottomTab) => void;
  setEnergyMode: (mode: EnergyMode) => void;
  setBenchmarkMode: (mode: BenchmarkMode) => void;
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
  selectedKek: null,
  drawerOpen: false,
  assumptionsExpanded: false,
  activeTab: 'table',
  layerVisibility: {},
  benchmarkMode: 'bpp',
  energyMode: 'solar',
  mapStyle: 'dark',
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

  // Cached layer data
  layers: {},

  // Actions
  setAssumptions: (a) =>
    set((state) => ({
      assumptions: state.assumptions ? { ...state.assumptions, ...a } : null,
    })),

  setThresholds: (t) =>
    set((state) => ({
      thresholds: state.thresholds ? { ...state.thresholds, ...t } : null,
    })),

  selectKek: (id) =>
    set((state) => ({
      selectedKek: id,
      drawerOpen: id !== null,
      layerVisibility: id
        ? { ...state.layerVisibility, buildable_polygons: true }
        : state.layerVisibility,
    })),

  closeDrawer: () => set({ drawerOpen: false }),

  setActiveTab: (tab) => set({ activeTab: tab }),

  setEnergyMode: (mode) => set({ energyMode: mode }),

  setBenchmarkMode: (mode) => set({ benchmarkMode: mode }),

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

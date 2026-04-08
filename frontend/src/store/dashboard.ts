import { create } from 'zustand';
import type {
  UserAssumptions,
  UserThresholds,
  ScorecardRow,
  DefaultsResponse,
  BottomTab,
  EnergyMode,
  BenchmarkMode,
} from '../lib/types';
import { fetchDefaults, fetchScorecard } from '../lib/api';

interface DashboardStore {
  // Data
  assumptions: UserAssumptions | null;
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
  loading: boolean;

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
  toggleLayer: (name: string) => void;
  recomputeScorecard: () => Promise<void>;
  resetDefaults: () => void;
  initialize: () => Promise<void>;
}

// Store the original defaults so resetDefaults can restore them
let _defaultAssumptions: UserAssumptions | null = null;
let _defaultThresholds: UserThresholds | null = null;

export const useDashboardStore = create<DashboardStore>((set, get) => ({
  // Data
  assumptions: null,
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
  loading: true,

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

  selectKek: (id) => set({ selectedKek: id, drawerOpen: id !== null }),

  closeDrawer: () => set({ drawerOpen: false }),

  setActiveTab: (tab) => set({ activeTab: tab }),

  setEnergyMode: (mode) => set({ energyMode: mode }),

  setBenchmarkMode: (mode) => set({ benchmarkMode: mode }),

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
      });
    }
  },

  initialize: async () => {
    set({ loading: true });
    try {
      const defaults = await fetchDefaults();

      _defaultAssumptions = defaults.assumptions;
      _defaultThresholds = defaults.thresholds;

      set({
        assumptions: defaults.assumptions,
        thresholds: defaults.thresholds,
        sliderConfigs: defaults.slider_configs,
      });

      const data = await fetchScorecard(
        defaults.assumptions,
        defaults.thresholds,
        'bpp',
      );
      set({ scorecard: data.scorecard, loading: false });
    } catch (err) {
      console.error('Failed to initialize dashboard:', err);
      set({ loading: false });
    }
  },
}));

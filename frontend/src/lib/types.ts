export interface UserAssumptions {
  capex_usd_per_kw: number;
  lifetime_yr: number;
  wacc_pct: number;
  fom_usd_per_kw_yr: number;
  gentie_cost_per_kw_km: number;
  substation_works_per_kw: number;
  transmission_lease_mid_usd_mwh: number;
  firming_adder_mid_usd_mwh: number;
  idr_usd_rate: number;
}

export interface UserThresholds {
  pvout_threshold: number;
  plan_late_threshold: number;
  geas_threshold: number;
  resilience_gap_pct: number;
  min_viable_mwp: number;
  reliability_threshold: number;
}

export interface ScorecardRow {
  kek_id: string;
  kek_name: string;
  province: string;
  latitude: number;
  longitude: number;
  action_flag: string;
  lcoe_mid_usd_mwh: number;
  lcoe_low_usd_mwh: number;
  lcoe_high_usd_mwh: number;
  solar_competitive_gap_pct: number;
  dashboard_rate_usd_mwh: number;
  carbon_breakeven_usd_tco2: number | null;
  buildable_area_ha: number;
  max_captive_capacity_mwp: number;
  project_viable: boolean;
  best_re_technology: string;
  grid_cost_usd_mwh: number;
  bpp_usd_mwh: number | null;
  grid_region_id: string;

  // Optional fields that may be present depending on pipeline data
  pvout_centroid_kwh_kwp_yr?: number;
  pvout_best_50km_kwh_kwp_yr?: number;
  lcoe_remote_captive_allin_usd_mwh?: number;
  demand_2030_gwh?: number;
  green_share_geas?: number;
  grid_upgrade_planned?: boolean;
  ruptl_region_summary?: string;
}

export interface SliderConfig {
  min: number;
  max: number;
  step: number;
  label: string;
  unit: string;
  description: string;
}

export interface DefaultsResponse {
  assumptions: UserAssumptions;
  thresholds: UserThresholds;
  slider_configs: {
    tier1: Record<string, SliderConfig>;
    tier2: Record<string, SliderConfig>;
    tier3: Record<string, SliderConfig>;
    wacc: {
      min: number;
      max: number;
      step: number;
      default: number;
      marks: Record<string, string>;
      description: string;
    };
  };
}

export interface ScorecardResponse {
  scorecard: ScorecardRow[];
}

export type EnergyMode = 'solar' | 'wind' | 'overall';
export type BenchmarkMode = 'bpp' | 'tariff';
export type BottomTab = 'table' | 'quadrant' | 'ruptl';

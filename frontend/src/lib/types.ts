export interface UserAssumptions {
  capex_usd_per_kw: number;
  lifetime_yr: number;
  wacc_pct: number;
  fom_usd_per_kw_yr: number;
  connection_cost_per_kw_km: number;
  grid_connection_fixed_per_kw: number;
  bess_capex_usd_per_kwh: number;
  land_cost_usd_per_kw: number;
  substation_utilization_pct: number;
  idr_usd_rate: number;
  target_capacity_mwp?: number | null;
}

export interface UserThresholds {
  pvout_threshold: number;
  plan_late_threshold: number;
  geas_threshold: number;
  resilience_gap_pct: number;
  min_viable_mwp: number;
  reliability_threshold: number;
}

export type ActionFlag =
  | 'solar_now'
  | 'invest_transmission'
  | 'invest_substation'
  | 'invest_resilience'
  | 'grid_first'
  | 'invest_battery'
  | 'plan_late'
  | 'not_competitive'
  | 'no_solar_resource';

export interface ScorecardRow {
  kek_id: string;
  kek_name: string;
  province: string;
  latitude: number;
  longitude: number;
  action_flag: ActionFlag;
  lcoe_mid_usd_mwh: number;
  lcoe_low_usd_mwh: number;
  lcoe_high_usd_mwh: number;
  solar_competitive_gap_pct: number;
  gap_vs_tariff_pct?: number;
  gap_vs_bpp_pct?: number;
  dashboard_rate_usd_mwh: number;
  carbon_breakeven_usd_tco2: number | null;
  buildable_area_ha: number;
  max_captive_capacity_mwp: number;
  project_viable: boolean;
  best_re_technology: string;
  grid_cost_usd_mwh: number;
  bpp_usd_mwh: number | null;
  grid_region_id: string;

  // KEK info fields
  kek_type?: string;
  category?: string;
  area_ha?: number;
  developer?: string;
  legal_basis?: string;

  // Optional fields that may be present depending on pipeline data
  pvout_centroid_kwh_kwp_yr?: number;
  pvout_best_50km_kwh_kwp_yr?: number;
  lcoe_within_boundary_usd_mwh?: number;
  lcoe_within_boundary_low_usd_mwh?: number;
  lcoe_within_boundary_high_usd_mwh?: number;
  connection_cost_per_kw?: number;
  grid_integration_category?: string;
  demand_2030_gwh?: number;
  max_solar_generation_gwh?: number;
  solar_supply_coverage_pct?: number;
  within_boundary_generation_gwh?: number;
  within_boundary_coverage_pct?: number;
  green_share_geas?: number;
  grid_upgrade_planned?: boolean;
  ruptl_region_summary?: string;

  // Action flag detail fields (backend always sends these)
  solar_attractive?: boolean;
  grid_first?: boolean;
  invest_transmission?: boolean;
  invest_substation?: boolean;
  invest_battery?: boolean;
  battery_adder_usd_mwh?: number;
  lcoe_with_battery_usd_mwh?: number;
  bess_competitive?: boolean | null;
  land_cost_usd_per_kw?: number;
  dist_to_nearest_substation_km?: number;
  dist_solar_to_nearest_substation_km?: number;

  // V3.1: Grid connectivity and capacity assessment
  same_grid_region?: boolean;
  line_connected?: boolean;
  inter_substation_connected?: boolean;
  inter_substation_dist_km?: number;
  available_capacity_mva?: number;
  capacity_assessment?: 'green' | 'yellow' | 'red' | 'unknown';
  transmission_cost_per_kw?: number;
  substation_upgrade_cost_per_kw?: number;
  grid_investment_needed_usd?: number;
  effective_capacity_mwp?: number;

  // H9: Captive power context
  captive_coal_count?: number | null;
  captive_coal_mw?: number | null;
  captive_coal_plants?: string | null;
  nickel_smelter_count?: number | null;
  nickel_projects?: string | null;
  dominant_process_type?: string | null;
  has_chinese_ownership?: boolean | null;

  // H8: Perpres 112/2022 compliance
  has_captive_coal?: boolean;
  perpres_112_status?: string | null;
  captive_coal_generation_gwh?: number | null;
  solar_replacement_pct?: number | null;
  bess_sizing_hours?: number | null;

  // V3.3: Firm solar metrics (temporal mismatch)
  firm_solar_coverage_pct?: number | null;
  nighttime_demand_mwh?: number | null;
  storage_required_mwh?: number | null;
  storage_gap_pct?: number | null;
}

export interface SubstationWithCosts {
  name: string;
  lat: number;
  lon: number;
  dist_km: number;
  dist_solar_km?: number | null;
  is_nearest: boolean;
  rank?: number | null;
  voltage?: string;
  capacity_mva?: number | string | null;
  regpln?: string;
  available_capacity_mva?: number | null;
  capacity_assessment?: 'green' | 'yellow' | 'red' | 'unknown' | null;
  connection_cost_per_kw?: number | null;
  upgrade_cost_per_kw?: number | null;
  transmission_cost_per_kw?: number | null;
  total_grid_capex_per_kw?: number | null;
  lcoe_estimate_usd_mwh?: number | null;
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
export type MapStyleKey = 'dark' | 'light' | 'voyager' | 'satellite';

export interface SavedScenario {
  id: string;
  name: string;
  assumptions: UserAssumptions;
  thresholds: UserThresholds;
  benchmarkMode: BenchmarkMode;
  createdAt: string;
}

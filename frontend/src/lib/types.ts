export interface UserAssumptions {
  capex_usd_per_kw: number;
  lifetime_yr: number;
  wacc_pct: number;
  fom_usd_per_kw_yr: number;
  connection_cost_per_kw_km: number;
  grid_connection_fixed_per_kw: number;
  bess_capex_usd_per_kwh: number;
  bess_sizing_hours_override?: number | null;
  land_cost_usd_per_kw: number;
  substation_utilization_pct: number;
  meaningful_share_pct: number;
  wb_buildout_footprint_ratio: number;
  idr_usd_rate: number;
  grant_funded_transmission?: boolean;
  target_capacity_mwp?: number | null;
  hybrid_solar_share?: number | null;
  cbam_certificate_price_eur: number;
  cbam_eur_usd_rate: number;
  // V4.1 RV15: rooftop §5.3 sliders. Recompute happens at request time
  // in /api/scorecard against `usable_roof_area_m2` from the rooftop fct.
  rooftop_panel_power_w_dc: number;
  rooftop_panel_area_m2: number;
  rooftop_layout_density: number;
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
  | 'cbam_urgent'
  | 'wind_now'
  | 'hybrid_now'
  | 'invest_transmission'
  | 'invest_substation'
  | 'invest_resilience'
  | 'grid_first'
  | 'invest_battery'
  | 'plan_late'
  | 'not_competitive'
  | 'no_solar_resource'
  | 'no_wind_resource'
  | 'no_re_resource';

export type EconomicTier =
  | 'full_re'
  | 'partial_re'
  | 'near_parity'
  | 'not_competitive'
  | 'no_resource';

export type InfrastructureReadiness =
  | 'within_boundary'
  | 'grid_ready'
  | 'invest_transmission'
  | 'invest_substation'
  | 'grid_first'
  | 'no_resource';

export type ModifierBadge = 'cbam_urgent' | 'plan_late' | 'storage_info';

export interface CbamProductMetrics {
  emission_intensity_current: number;
  emission_intensity_solar: number;
  cost_2026_usd_per_tonne: number;
  cost_2030_usd_per_tonne: number;
  cost_2034_usd_per_tonne: number;
  savings_2026_usd_per_tonne: number;
  savings_2030_usd_per_tonne: number;
  savings_2034_usd_per_tonne: number;
}

export interface ScorecardRow {
  site_id: string;
  site_name: string;
  site_type: string;
  sector: string;
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
  grid_emission_factor_t_co2_mwh?: number | null;
  carbon_breakeven_usd_tco2: number | null;
  buildable_area_ha: number;
  /** @deprecated 2026-04-25 — renamed to `regional_groundmount_potential_mwp_50km`. Alias kept for one release; remove in v4.2. */
  max_captive_capacity_mwp?: number;
  regional_groundmount_potential_mwp_50km: number;

  // Rooftop solar (v4.1, optional — null/missing if pipeline hasn't run)
  rooftop_solar_mwp_potential?: number;
  rooftop_kw_dc?: number;
  rooftop_kw_ac?: number;
  total_building_footprint_m2?: number;
  usable_roof_area_m2?: number;
  type_filter_excluded_m2?: number;
  building_count_total?: number;
  building_count_standard_roof?: number;
  building_count_elongated?: number;
  building_count_tank_silo?: number;
  building_count_conveyor?: number;
  building_count_other_excluded?: number;
  building_data_confidence?: 'high' | 'medium' | 'low';
  building_data_reason_flagged?: string | null;
  building_data_source?: string | null;
  building_data_vintage?: string | null;
  polygon_source_tier?:
    | 'official_kek'
    | 'osm_landuse_industrial'
    | 'claude_building_hull_estimate'
    | 'none';

  project_viable: boolean;
  best_re_technology: string;
  grid_cost_usd_mwh: number;
  bpp_usd_mwh: number | null;
  grid_region_id: string;

  // Site info fields
  zone_classification?: string;
  category?: string;
  area_ha?: number;
  developer?: string;
  legal_basis?: string;

  // Industrial site identity fields (standalone, cluster, ki)
  primary_product?: string;
  capacity_annual?: string;
  capacity_annual_tonnes?: number;
  technology?: string;
  parent_company?: string;
  cluster_members?: string;

  // Optional fields that may be present depending on pipeline data
  pvout_centroid_kwh_kwp_yr?: number;
  pvout_best_50km_kwh_kwp_yr?: number;

  best_solar_site_lat?: number | null;
  best_solar_site_lon?: number | null;

  // Wind resource fields (from precomputed scorecard)
  lcoe_wind_mid_usd_mwh?: number;
  lcoe_wind_allin_mid_usd_mwh?: number;
  cf_wind?: number;
  wind_speed_ms?: number;
  best_re_lcoe_mid_usd_mwh?: number;
  wind_competitive_gap_pct?: number;
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
  within_boundary_coverage_effective_pct?: number;
  /** Captive solar — total MWp that fits inside the site fence (sum across all buildable polygons). */
  within_boundary_capacity_mwp?: number;
  within_boundary_area_ha?: number;
  within_boundary_avg_pvout?: number;
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
  // LCOE waterfall inputs (echoed from assumptions + resolved primary CF)
  capex_usd_per_kw?: number;
  wacc_pct?: number;
  fom_usd_per_kw_yr?: number;
  lifetime_yr?: number;
  primary_cf?: number;
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

  // V3.7: Substation-anchored solar search + regulatory regime
  solar_search_method?: 'substation_anchored' | 'best_pvout_fallback' | null;
  chosen_anchor_substation_name?: string | null;
  solar_supply_share_pct?: number | null;
  solar_delivered_share_pct?: number | null;
  project_scale_solar_mwp?: number | null;
  nearest_substation_capacity_source?: string | null;
  solar_regime?: 'co_located_captive' | 'grid_connected_ipp' | 'unclear' | null;
  lcoe_grid_connected_capped_usd_mwh?: number | null;

  // V3.8: RUPTL-derived per-substation utilization signal
  nearest_substation_name?: string | null;
  nearest_substation_capacity_mva?: number | null;
  substation_utilization_pct_effective?: number | null;
  ruptl_project_type?: 'uprate' | 'extension' | 'line_bay' | 'new' | 'other' | null;
  ruptl_strongest_status?:
    | 'konstruksi'
    | 'committed'
    | 'pengadaan'
    | 'rencana'
    | 'studi'
    | 'other'
    | null;
  ruptl_earliest_target_year?: number | null;
  ruptl_mva_added_total?: number | null;
  ruptl_match_confidence?: 'high' | 'medium' | 'low' | null;

  // H9: Captive power context
  captive_coal_count?: number | null;
  captive_coal_mw?: number | null;
  captive_coal_plants?: string | null;
  nickel_smelter_count?: number | null;
  nickel_projects?: string | null;
  dominant_process_type?: string | null;
  has_chinese_ownership?: boolean | null;
  steel_plant_count?: number | null;
  steel_capacity_tpa?: number | null;
  steel_plants?: string | null;
  steel_has_chinese_ownership?: boolean | null;
  cement_plant_count?: number | null;
  cement_capacity_mtpa?: number | null;
  cement_plants?: string | null;
  cement_has_chinese_ownership?: boolean | null;

  // F2: Geothermal adjacency (drives the dispatchable-RE layer in delivered cost)
  geothermal_adjacency_tier?:
    | 'operating_within_50km'
    | 'operating_within_200km'
    | 'pipeline_within_200km_pre2030'
    | 'pipeline_within_200km_post2030'
    | 'none'
    | null;
  nearest_geothermal_operating_id?: string | null;
  nearest_geothermal_operating_km?: number | null;
  nearest_geothermal_operating_mw?: number | null;
  nearest_geothermal_operating_emission_factor_g_per_kwh?: number | null;
  nearest_geothermal_pipeline_id?: string | null;
  nearest_geothermal_pipeline_km?: number | null;
  nearest_geothermal_pipeline_mw?: number | null;
  nearest_geothermal_pipeline_target_year?: number | null;

  // H8: Perpres 112/2022 compliance
  has_captive_coal?: boolean;
  perpres_112_status?: string | null;
  captive_coal_generation_gwh?: number | null;
  solar_replacement_pct?: number | null;

  // CBAM exposure (EU Carbon Border Adjustment Mechanism)
  cbam_exposed?: boolean;
  cbam_product_type?: string | null;
  cbam_emission_intensity_current?: number | null;
  cbam_emission_intensity_solar?: number | null;
  cbam_cost_2026_usd_per_tonne?: number | null;
  cbam_cost_2030_usd_per_tonne?: number | null;
  cbam_cost_2034_usd_per_tonne?: number | null;
  cbam_savings_2026_usd_per_tonne?: number | null;
  cbam_savings_2030_usd_per_tonne?: number | null;
  cbam_savings_2034_usd_per_tonne?: number | null;
  cbam_per_product?: Record<string, CbamProductMetrics> | null;
  cbam_savings_per_mwh?: number | null;
  cbam_adjusted_gap_pct?: number | null;
  cbam_urgent?: boolean;

  // V3.11: cascaded delivered cost (tenant view) — WB → remote captive → grid
  delivered_cost_usd_mwh?: number | null;
  captive_fraction?: number | null;
  delivered_cost_remote_fraction?: number | null;
  grid_fraction?: number | null;
  delivered_cost_grid_rate_used_usd_mwh?: number | null;
  delivered_cost_wb_lcoe_used_usd_mwh?: number | null;
  delivered_cost_gc_lcoe_used_usd_mwh?: number | null;
  delivered_cost_gap_vs_grid_pct?: number | null;
  bess_sizing_hours?: number | null;

  // V3.3: Firm solar metrics (temporal mismatch)
  firm_solar_coverage_pct?: number | null;
  nighttime_demand_mwh?: number | null;
  storage_required_mwh?: number | null;
  storage_gap_pct?: number | null;

  // Wind parity: buildability, supply coverage, temporal
  max_wind_capacity_mwp?: number;
  wind_buildable_area_ha?: number;
  wind_buildability_constraint?: string;
  max_wind_generation_gwh?: number;
  wind_supply_coverage_pct?: number | null;
  wind_carbon_breakeven_usd_tco2?: number | null;
  firm_wind_coverage_pct?: number | null;
  wind_firming_gap_pct?: number | null;
  wind_firming_hours?: number | null;

  // Hybrid solar+wind fields
  hybrid_lcoe_usd_mwh?: number | null;
  hybrid_bess_hours?: number | null;
  hybrid_bess_adder_usd_mwh?: number | null;
  hybrid_allin_usd_mwh?: number | null;
  hybrid_solar_share?: number | null;
  hybrid_supply_coverage_pct?: number | null;
  hybrid_nighttime_coverage_pct?: number | null;
  hybrid_bess_reduction_pct?: number | null;
  hybrid_carbon_breakeven_usd_tco2?: number | null;

  // 2D classification system (Option C)
  economic_tier?: EconomicTier;
  infrastructure_readiness?: InfrastructureReadiness;
  modifier_badges?: ModifierBadge[];
}

export interface SubstationWithCosts {
  name: string;
  lat: number;
  lon: number;
  dist_km: number;
  dist_solar_km?: number | null;
  is_nearest: boolean;
  is_anchor?: boolean;
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
  default?: number;
  label: string;
  unit?: string;
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
    // V4.1 RV15: rooftop §5.3 sliders (panel power, area, layout density).
    rooftop?: {
      panel_power_w_dc: SliderConfig;
      panel_area_m2: SliderConfig;
      layout_density: SliderConfig;
    };
  };
}

export interface ScorecardResponse {
  scorecard: ScorecardRow[];
}

export type EnergyMode = 'solar' | 'wind' | 'geothermal' | 'hybrid' | 'overall';
export type BenchmarkMode = 'bpp' | 'tariff';
/** Which layer of the cost stack feeds action_flag / economic_tier / gap / carbon_breakeven.
 *  Mirrors `src/model/basic_model.py::CostBasis`. See TAXONOMY §7.3 for the
 *  `(EnergyMode × CostBasis)` resolution matrix. */
export type CostBasis = 'raw' | 'firmed' | 'delivered';
export type BottomTab = 'table' | 'ruptl' | 'sector' | 'compare' | 'rooftop';
export type MapStyleKey = 'dark' | 'light' | 'voyager' | 'satellite';

export interface SavedScenario {
  id: string;
  name: string;
  assumptions: UserAssumptions;
  thresholds: UserThresholds;
  benchmarkMode: BenchmarkMode;
  createdAt: string;
}

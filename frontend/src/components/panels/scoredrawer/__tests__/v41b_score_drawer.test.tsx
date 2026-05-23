/**
 * v4.1b #93: Score Drawer surfaces for destination-weighted CBAM + 3-way hybrid
 * + hydro proximity.
 *
 * Three render-paths covered (one per spec §2.4 / §6A.5 / §6A.4 surface):
 *   1. ActionTab CBAM headline row — only renders for CBAM-exposed sites where
 *      cbam_active_scenario != 'none'; provenance badge keys off
 *      cbam_destination_weighted_shares_source.
 *   2. ResourceTab hybrid 3-way pills — shares sum to 100% (within rounding);
 *      hydro pill renders even when hydro_share = 0 so the user can see hydro
 *      was considered + rejected.
 *   3. ResourceTab hydro proximity row — renders for sites with any of
 *      {tier, operating_km, pipeline_km}; uses the empty-state Pill when
 *      tier = 'none'.
 *
 * Store mock: zustand is mocked at the import boundary so tests don't need the
 * real store + its localStorage-touching side effects.
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ScorecardRow } from '../../../../lib/types';
import { ActionTab, CBAM_SCENARIO_META } from '../ActionTab';
import { ResourceTab } from '../ResourceTab';

// Minimal store mock — the tabs only read energyMode / costBasis / assumptions /
// setAssumptions. Returning a constant object via the selector pattern keeps
// the test deterministic across re-renders.
vi.mock('../../../../store/dashboard', () => ({
  useDashboardStore: (selector: (s: unknown) => unknown) =>
    selector({
      energyMode: 'overall',
      costBasis: 'delivered',
      assumptions: {
        wb_buildout_footprint_ratio: 0.2,
        rooftop_layout_density: 0.5,
        rooftop_panel_power_w_dc: 400,
        rooftop_panel_area_m2: 2,
      },
      setAssumptions: () => {},
    }),
}));

// Stub the modal — its useState + useEffect aren't relevant here and pulling
// in fetchSiteRooftopBreakdown would force the test to mock that boundary too.
vi.mock('../RooftopBreakdownModal', () => ({
  RooftopBreakdownModal: () => null,
}));

vi.mock('../../../charts/LcoeCurveChart', () => ({
  default: () => null,
}));

const BASE_ROW: ScorecardRow = {
  site_id: 'imip-morowali',
  site_name: 'IMIP Morowali',
  site_type: 'industrial',
  sector: 'nickel',
  province: 'Central Sulawesi',
  latitude: -2.8,
  longitude: 122.0,
  action_flag: 'cbam_urgent',
  lcoe_mid_usd_mwh: 65,
  lcoe_low_usd_mwh: 50,
  lcoe_high_usd_mwh: 90,
  solar_competitive_gap_pct: -10,
  dashboard_rate_usd_mwh: 80,
  carbon_breakeven_usd_tco2: 25,
  buildable_area_ha: 5000,
  regional_groundmount_potential_mwp_50km: 3000,
  project_viable: true,
  best_re_technology: 'solar',
  grid_cost_usd_mwh: 70,
  bpp_usd_mwh: 75,
  grid_region_id: 'sulawesi',
};

describe('CBAM_SCENARIO_META', () => {
  it('has every scenario from the spec §2.4 toggle (minus auto sentinel)', () => {
    // 'auto' is the user-facing sentinel — it resolves to a real scenario on
    // the backend, so the active_scenario column never ships as 'auto'.
    const expected = [
      'none',
      'domestic_low',
      'domestic_high',
      'effective_2025',
      'effective_2030',
      'cbam_full_2026',
      'cbam_full_2030',
    ] as const;
    for (const scenario of expected) {
      expect(CBAM_SCENARIO_META[scenario]).toBeDefined();
      expect(CBAM_SCENARIO_META[scenario].label.length).toBeGreaterThan(0);
      expect(CBAM_SCENARIO_META[scenario].tip.length).toBeGreaterThan(20);
    }
  });

  it('flags cbam_full_2026 as the only mature regulation', () => {
    // The label answers the user critique that started v4.1b sub-PR (e):
    // "only EU CBAM is mature" — picking cbam_full_2026 should be visibly
    // the conservative-defensible scenario.
    const tip = CBAM_SCENARIO_META.cbam_full_2026.tip.toLowerCase();
    expect(tip).toMatch(/only.*enforced|conservative|defensible|mature/);
  });
});

describe('ActionTab CBAM headline row (#93)', () => {
  it('renders when the site is CBAM-exposed and active scenario is set', () => {
    render(
      <ActionTab
        row={{
          ...BASE_ROW,
          cbam_exposed: true,
          cbam_active_scenario: 'effective_2025',
          cbam_active_scenario_column: 'cbam_destination_weighted_incumbent_2025_usd_mwh',
          cbam_active_scenario_value_usd_mwh: 102.5,
          cbam_destination_weighted_shares_source: 'sector_default',
        }}
      />,
    );
    expect(screen.getByText('CBAM-Adjusted Incumbent')).toBeTruthy();
    // The headline scenario label + the value should both render.
    expect(screen.getByText(/Effective 2025/)).toBeTruthy();
    expect(screen.getByText(/102\.5 \$\/MWh/)).toBeTruthy();
    // Provenance badge for destination-weighted scenarios.
    expect(screen.getByText(/Sector default/)).toBeTruthy();
  });

  it('hides the CBAM card when scenario is none (user dialed CBAM off)', () => {
    render(
      <ActionTab
        row={{
          ...BASE_ROW,
          cbam_exposed: true,
          cbam_active_scenario: 'none',
          cbam_active_scenario_column: null,
          cbam_active_scenario_value_usd_mwh: null,
        }}
      />,
    );
    expect(screen.queryByText('CBAM-Adjusted Incumbent')).toBeNull();
  });

  it('hides the CBAM card for non-CBAM-exposed sites', () => {
    render(<ActionTab row={BASE_ROW} />);
    expect(screen.queryByText('CBAM-Adjusted Incumbent')).toBeNull();
  });

  it('omits the provenance badge for domestic scenarios (no shares lookup)', () => {
    // Domestic scenarios don't read the per-market shares table — the badge
    // would be meaningless. Only destination-weighted scenarios surface it.
    render(
      <ActionTab
        row={{
          ...BASE_ROW,
          cbam_exposed: true,
          cbam_active_scenario: 'domestic_high',
          cbam_active_scenario_column: 'cbam_domestic_high_incumbent_usd_mwh',
          cbam_active_scenario_value_usd_mwh: 87.0,
          cbam_destination_weighted_shares_source: 'sector_default',
        }}
      />,
    );
    expect(screen.getByText(/Domestic carbon — \$25/)).toBeTruthy();
    expect(screen.queryByText(/Sector default/)).toBeNull();
    expect(screen.queryByText(/Site override/)).toBeNull();
  });
});

describe('ResourceTab hybrid 3-way pills (#93)', () => {
  it('renders solar/wind/hydro pills that sum to 100%', () => {
    render(
      <ResourceTab
        row={{
          ...BASE_ROW,
          hybrid_solar_share: 0.5,
          hybrid_wind_share: 0.2,
          hybrid_hydro_share: 0.3,
          hybrid_full_system_lcoe_usd_mwh: 78.5,
          hybrid_lcos_usd_mwh: 12.3,
        }}
      />,
    );
    expect(screen.getByText(/Solar 50%/)).toBeTruthy();
    expect(screen.getByText(/Wind 20%/)).toBeTruthy();
    expect(screen.getByText(/Hydro 30%/)).toBeTruthy();
    expect(screen.getByText(/78\.5 \$\/MWh/)).toBeTruthy();
    expect(screen.getByText(/12\.3 \$\/MWh/)).toBeTruthy();
  });

  it('still renders the hydro pill at 0% so users can confirm it was considered', () => {
    // Spec §6A.4: at non-hydro sites the 3-way solver returns hydro_share = 0
    // rather than hiding the leg — keeps the UI consistent across sites.
    render(
      <ResourceTab
        row={{
          ...BASE_ROW,
          hybrid_solar_share: 0.7,
          hybrid_wind_share: 0.3,
          hybrid_hydro_share: 0.0,
          hybrid_full_system_lcoe_usd_mwh: 81.0,
        }}
      />,
    );
    expect(screen.getByText(/Hydro 0%/)).toBeTruthy();
  });

  it('hides the hybrid card when the optimizer produced no result', () => {
    render(<ResourceTab row={BASE_ROW} />);
    expect(screen.queryByText('Hybrid Mix')).toBeNull();
  });
});

describe('ResourceTab hydro proximity row (#93)', () => {
  it('renders the operating-within-50km tier with distance + capacity', () => {
    render(
      <ResourceTab
        row={{
          ...BASE_ROW,
          hydro_adjacency_tier: 'operating_within_50km',
          nearest_hydro_operating_id: 'plta-poso',
          nearest_hydro_operating_km: 22.0,
          nearest_hydro_operating_mw: 195.0,
        }}
      />,
    );
    expect(screen.getByText('Hydro Proximity')).toBeTruthy();
    expect(screen.getByText(/Operating <50km/)).toBeTruthy();
    expect(screen.getByText(/22 km · 195 MW/)).toBeTruthy();
  });

  it('renders the pipeline path with target year', () => {
    render(
      <ResourceTab
        row={{
          ...BASE_ROW,
          hydro_adjacency_tier: 'pipeline_within_200km_pre2030',
          nearest_hydro_pipeline_id: 'plta-batang-toru',
          nearest_hydro_pipeline_km: 110.0,
          nearest_hydro_pipeline_mw: 510.0,
          nearest_hydro_pipeline_target_year: 2027,
        }}
      />,
    );
    expect(screen.getByText(/Pipeline <2030/)).toBeTruthy();
    expect(screen.getByText(/110 km · 2027 · 510 MW/)).toBeTruthy();
  });

  it('hides the proximity card when no hydro data exists for the site', () => {
    render(<ResourceTab row={BASE_ROW} />);
    expect(screen.queryByText('Hydro Proximity')).toBeNull();
  });
});

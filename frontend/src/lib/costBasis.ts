/**
 * CostBasis resolver — picks which cost column feeds action_flag / economic_tier /
 * solar_competitive_gap_pct / carbon_breakeven_usd_tco2 at evaluation time.
 *
 * Mirrors `src/model/basic_model.py::CostBasis` and implements the
 * `(EnergyMode × CostBasis)` matrix from TAXONOMY §7.3.
 *
 * Empty matrix cells resolve to `null` and the UI greys that toggle option out
 * (never silent fallback — that's the "why is my chart showing a different number
 * than my column" bug waiting to happen).
 */

import type { CostBasis, EnergyMode, ScorecardRow } from './types';

/** TAXONOMY §7.3 resolver matrix. Returns the value | null if the cell is empty. */
export function resolveCost(
  row: ScorecardRow,
  energyMode: EnergyMode,
  basis: CostBasis,
): number | null {
  const pick = (v: number | null | undefined): number | null =>
    v == null || Number.isNaN(v) ? null : v;

  switch (energyMode) {
    case 'solar':
      switch (basis) {
        case 'raw':
          return pick(row.lcoe_mid_usd_mwh);
        case 'firmed':
          return pick(row.lcoe_with_battery_usd_mwh);
        case 'delivered':
          return pick(row.delivered_cost_usd_mwh);
      }
      break;
    case 'wind':
      switch (basis) {
        case 'raw':
          return pick(row.lcoe_wind_mid_usd_mwh);
        case 'firmed':
          return pick(row.lcoe_wind_allin_mid_usd_mwh);
        case 'delivered':
          return null; // empty cell — no wind-only delivered blend today
      }
      break;
    case 'geothermal':
      // Layers-only mode: site-resolved geothermal LCOE is not a quantity
      // ESDM / PLN publish — the Technology Catalogue only gives a fleet
      // HT/LT range, and real economics depend on the *plant's* resource
      // (depth, well productivity, NCG fraction), not the demand site.
      // Mode flips map layers + emphasizes the GeothermalAdjacencyCard;
      // cost columns intentionally render '—' to avoid a misleading number.
      return null;
    case 'hybrid':
      switch (basis) {
        case 'raw':
          return pick(row.hybrid_lcoe_usd_mwh);
        case 'firmed':
          return pick(row.hybrid_allin_usd_mwh);
        case 'delivered':
          return null; // empty cell
      }
      break;
    case 'overall':
      switch (basis) {
        case 'raw':
          return null; // empty cell — no single "raw" answer across techs
        case 'firmed':
          return pick(row.best_re_lcoe_mid_usd_mwh);
        case 'delivered':
          return null; // empty cell
      }
      break;
  }
  return null;
}

/** True when the (mode, basis) cell exists in the matrix. Dashboard toggle uses this
 *  to grey out unsupported options. */
export function isBasisSupported(energyMode: EnergyMode, basis: CostBasis): boolean {
  if (energyMode === 'overall') return basis === 'firmed';
  // Geothermal mode is layers-only — no basis returns a number, so no
  // basis is "supported". CostBasisToggle will grey all three out.
  if (energyMode === 'geothermal') return false;
  if (basis === 'delivered') return energyMode === 'solar';
  return true; // raw and firmed are always supported for solar/wind/hybrid
}

/** Default basis per energy mode (TAXONOMY §7.3). Preserves today's behaviour:
 *  overall shows firmed (matches current best_re_lcoe_mid path); all others show raw
 *  (matches today's solar T1-driven flags). */
export function defaultCostBasis(energyMode: EnergyMode): CostBasis {
  return energyMode === 'overall' ? 'firmed' : 'raw';
}

/** Human label shown in the toggle. Names each view by what's in the number. */
export const COST_BASIS_LABELS: Record<CostBasis, string> = {
  raw: 'Solar LCOE',
  firmed: 'Solar 24/7',
  delivered: 'Supply Blend',
};

/**
 * Hover-tooltip copy: a short title plus a body that spells out which costs
 * are inside the number. Keep the body to 1–2 short sentences.
 */
export const COST_BASIS_DESCRIPTIONS: Record<CostBasis, { title: string; body: string }> = {
  raw: {
    title: 'Bare solar, no battery',
    body: 'Cheapest solar MWh. Daytime only — tenants still need a grid connection for nights.',
  },
  firmed: {
    title: 'Solar + battery = always on',
    body: 'Adds BESS firming so solar covers overnight demand. The price of a fully renewable site.',
  },
  delivered: {
    title: 'What the tenant actually pays',
    body: 'On-site solar first, then a remote IPP for the daytime gap (up to the ~42% daylight ceiling), then grid overnight.',
  },
};

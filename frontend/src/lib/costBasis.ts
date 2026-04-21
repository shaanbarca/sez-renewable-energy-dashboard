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
  if (basis === 'delivered') return energyMode === 'solar';
  return true; // raw and firmed are always supported for solar/wind/hybrid
}

/** Default basis per energy mode (TAXONOMY §7.3). Preserves today's behaviour:
 *  overall shows firmed (matches current best_re_lcoe_mid path); all others show raw
 *  (matches today's solar T1-driven flags). */
export function defaultCostBasis(energyMode: EnergyMode): CostBasis {
  return energyMode === 'overall' ? 'firmed' : 'raw';
}

/** Human label shown in the toggle and legend. */
export const COST_BASIS_LABELS: Record<CostBasis, string> = {
  raw: 'Raw',
  firmed: 'Firmed',
  delivered: 'Delivered',
};

/** Tier tag shown as a chip on each toggle option (matches TAXONOMY §1). */
export const COST_BASIS_TIER: Record<CostBasis, 'T1' | 'T2' | 'T3'> = {
  raw: 'T1',
  firmed: 'T2',
  delivered: 'T3',
};

/** One-line description used in tooltips and the legend. */
export const COST_BASIS_DESCRIPTIONS: Record<CostBasis, string> = {
  raw: 'Bare LCOE, no storage. "Cheapest MWh of RE."',
  firmed: '+ BESS/firming. "Price of 24/7 RE."',
  delivered: 'Captive + grid blend. "Tenant bill."',
};

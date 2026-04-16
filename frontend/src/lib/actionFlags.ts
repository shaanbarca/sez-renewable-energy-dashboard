import {
  ECONOMIC_TIER_DESCRIPTIONS,
  ECONOMIC_TIER_LABELS,
  INFRA_READINESS_LABELS,
} from './constants';
import type {
  ActionFlag,
  EconomicTier,
  EnergyMode,
  InfrastructureReadiness,
  ModifierBadge,
  ScorecardRow,
} from './types';

/**
 * Priority-ordered flag hierarchy per energy mode.
 * First matching flag wins (same pattern as backend).
 */
export const ACTION_FLAG_HIERARCHY_BY_MODE: Record<EnergyMode, ActionFlag[]> = {
  solar: [
    'solar_now',
    'cbam_urgent',
    'invest_resilience',
    'invest_battery',
    'invest_transmission',
    'invest_substation',
    'grid_first',
    'plan_late',
    'not_competitive',
    'no_solar_resource',
  ],
  wind: [
    'wind_now',
    'cbam_urgent',
    'invest_resilience',
    'invest_transmission',
    'invest_substation',
    'grid_first',
    'plan_late',
    'not_competitive',
    'no_wind_resource',
  ],
  hybrid: [
    'hybrid_now',
    'cbam_urgent',
    'invest_resilience',
    'invest_battery',
    'invest_transmission',
    'invest_substation',
    'grid_first',
    'plan_late',
    'not_competitive',
    'no_re_resource',
  ],
  overall: [
    'solar_now',
    'wind_now',
    'hybrid_now',
    'cbam_urgent',
    'invest_resilience',
    'invest_battery',
    'invest_transmission',
    'invest_substation',
    'grid_first',
    'plan_late',
    'not_competitive',
    'no_re_resource',
  ],
};

/**
 * Compute the effective action flag for a row based on the active energy mode.
 * Solar mode returns the backend-computed flag directly. Other modes derive
 * the flag from mode-specific LCOE, resource availability, and grid readiness.
 */
export function getEffectiveActionFlag(row: ScorecardRow, energyMode: EnergyMode): ActionFlag {
  if (energyMode === 'solar') return row.action_flag;

  let lcoe: number | null;
  let hasResource: boolean;
  let deployFlag: ActionFlag;
  let noResourceFlag: ActionFlag;

  switch (energyMode) {
    case 'wind':
      lcoe = row.lcoe_wind_mid_usd_mwh ?? null;
      hasResource = (row.wind_buildable_area_ha ?? 0) > 0;
      deployFlag = 'wind_now';
      noResourceFlag = 'no_wind_resource';
      break;
    case 'hybrid':
      lcoe = row.hybrid_allin_usd_mwh ?? null;
      hasResource = row.buildable_area_ha > 0 || (row.wind_buildable_area_ha ?? 0) > 0;
      deployFlag = 'hybrid_now';
      noResourceFlag = 'no_re_resource';
      break;
    default:
      lcoe = row.best_re_lcoe_mid_usd_mwh ?? null;
      hasResource = row.buildable_area_ha > 0 || (row.wind_buildable_area_ha ?? 0) > 0;
      deployFlag =
        row.best_re_technology === 'hybrid'
          ? 'hybrid_now'
          : row.best_re_technology === 'wind'
            ? 'wind_now'
            : 'solar_now';
      noResourceFlag = 'no_re_resource';
      break;
  }

  if (!hasResource) return noResourceFlag;
  if (lcoe == null) return 'not_competitive';

  const gridCost = row.grid_cost_usd_mwh;
  const attractive = lcoe < gridCost;
  const gi = row.grid_integration_category;

  if (attractive) {
    if (gi === 'within_boundary' || gi === 'grid_ready') return deployFlag;
    if (gi === 'invest_transmission') return 'invest_transmission';
    if (gi === 'invest_substation') return 'invest_substation';
    return 'grid_first';
  }

  // CBAM urgent: CBAM-adjusted gap is negative (CBAM savings flip economics)
  if (row.cbam_urgent) return 'cbam_urgent';

  // Near-parity resilience check (LCOE within 20% above grid cost)
  const gapPct = ((lcoe - gridCost) / gridCost) * 100;
  if (gapPct > 0 && gapPct <= 20) return 'invest_resilience';

  // plan_late is region-level RUPTL timing, tech-agnostic — reuse from backend
  if (row.action_flag === 'plan_late') return 'plan_late';

  return 'not_competitive';
}

/**
 * Context-aware explanation text for a flag, adapted to the active energy mode.
 */
export function getEffectiveFlagExplanation(
  flag: ActionFlag,
  row: ScorecardRow,
  energyMode: EnergyMode,
): string {
  const gridCost = row.grid_cost_usd_mwh?.toFixed(0) ?? '?';
  const gi = row.grid_integration_category;

  // Mode-specific LCOE for explanation text
  let lcoeStr: string;
  let techDesc: string;
  switch (energyMode) {
    case 'wind':
      lcoeStr = row.lcoe_wind_mid_usd_mwh?.toFixed(0) ?? '?';
      techDesc = 'Wind';
      break;
    case 'hybrid': {
      lcoeStr = row.hybrid_allin_usd_mwh?.toFixed(0) ?? '?';
      const share = row.hybrid_solar_share;
      const solarPct = share != null ? Math.round(share * 100) : '?';
      const windPct = share != null ? Math.round((1 - share) * 100) : '?';
      techDesc = `Hybrid (${solarPct}% solar / ${windPct}% wind)`;
      break;
    }
    case 'overall':
      lcoeStr = row.best_re_lcoe_mid_usd_mwh?.toFixed(0) ?? '?';
      techDesc =
        row.best_re_technology === 'hybrid'
          ? 'Hybrid solar+wind'
          : row.best_re_technology === 'wind'
            ? 'Wind'
            : 'Solar';
      break;
    default:
      lcoeStr = row.lcoe_mid_usd_mwh?.toFixed(0) ?? '?';
      techDesc = 'Solar';
  }

  switch (flag) {
    case 'solar_now':
      return `Solar is cost-competitive with the grid today ($${row.lcoe_mid_usd_mwh?.toFixed(0) ?? '?'}/MWh vs $${gridCost}/MWh). Grid connection is ready${gi === 'within_boundary' ? ' (within KEK boundary)' : ''}.`;

    case 'wind_now':
      return `Wind is cost-competitive with the grid ($${lcoeStr}/MWh vs $${gridCost}/MWh). Deploy wind generation${row.cf_wind ? ` at ${(row.cf_wind * 100).toFixed(0)}% capacity factor` : ''}.`;

    case 'hybrid_now': {
      const bessHrs = row.hybrid_bess_hours?.toFixed(1) ?? '?';
      const reduction =
        row.hybrid_bess_reduction_pct != null ? Math.round(row.hybrid_bess_reduction_pct) : '?';
      return `${techDesc} all-in cost ($${lcoeStr}/MWh) beats grid ($${gridCost}/MWh). Wind reduces storage from 14h to ${bessHrs}h (${reduction}% reduction).`;
    }

    case 'cbam_urgent': {
      const adjGap = row.cbam_adjusted_gap_pct?.toFixed(0) ?? '?';
      const stdGap = row.solar_competitive_gap_pct?.toFixed(0) ?? '?';
      const savMwh = row.cbam_savings_per_mwh?.toFixed(0) ?? '?';
      return `${techDesc} alone is ${stdGap}% above grid parity, but EU CBAM avoidance saves $${savMwh}/MWh. CBAM-adjusted gap: ${adjGap}%. Switching to RE is cheaper than paying the border tax.`;
    }

    case 'invest_transmission': {
      const dist = row.dist_to_nearest_substation_km?.toFixed(0);
      return `${techDesc} is cost-competitive ($${lcoeStr}/MWh vs $${gridCost}/MWh) but the KEK is far from the nearest substation${dist ? ` (${dist} km)` : ''}. Build transmission to connect.`;
    }

    case 'invest_substation': {
      const dist = row.dist_solar_to_nearest_substation_km?.toFixed(0);
      return `${techDesc} is cost-competitive ($${lcoeStr}/MWh vs $${gridCost}/MWh) but the RE site is far from the nearest substation${dist ? ` (${dist} km)` : ''}. Build a substation near the generation site.`;
    }

    case 'invest_battery':
      if (energyMode === 'hybrid' || energyMode === 'overall') {
        const bessHrs = row.hybrid_bess_hours?.toFixed(1) ?? '14';
        return `${techDesc} economics work, but reliability needs require storage. Hybrid wind reduces BESS to ${bessHrs}h (from 14h standalone). All-in: $${lcoeStr}/MWh.`;
      }
      return `Solar economics work, but reliability needs require battery storage (${row.bess_sizing_hours ?? 14}h). Solar + battery: $${row.lcoe_with_battery_usd_mwh?.toFixed(0) ?? '?'}/MWh.`;

    case 'invest_resilience': {
      const gap =
        row.grid_cost_usd_mwh > 0
          ? (
              (((Number(lcoeStr) || 0) - row.grid_cost_usd_mwh) / row.grid_cost_usd_mwh) *
              100
            ).toFixed(0)
          : '~20';
      return `${techDesc} is within ${gap}% of grid parity ($${lcoeStr} vs $${gridCost}/MWh). Investing now builds resilience against future grid cost increases.`;
    }

    case 'grid_first':
      return `${techDesc} is cost-competitive ($${lcoeStr}/MWh) but grid infrastructure needs improvement before RE can connect. ${row.grid_upgrade_planned === false ? 'No grid upgrade is planned in this region.' : 'Grid upgrades are needed.'}`;

    case 'plan_late':
      return 'Over 60% of planned RE additions in this grid region slip past 2030. Early action could capture first-mover advantage.';

    case 'not_competitive':
      return `${techDesc} LCOE ($${lcoeStr}/MWh) exceeds grid cost ($${gridCost}/MWh). Grid power remains the cheaper option.`;

    case 'no_solar_resource':
      return 'All land within 50 km is protected forest, peatland, or otherwise unbuildable for solar.';

    case 'no_wind_resource':
      return 'No viable wind resource within 50 km. Wind speeds below cut-in threshold or all land is unbuildable.';

    case 'no_re_resource':
      return 'No viable renewable resource (solar or wind) within 50 km. All land is protected, peatland, or unbuildable.';

    default:
      return '';
  }
}

/** Section title for the ActionTab, adapting to energy mode. */
export function getActionSectionTitle(energyMode: EnergyMode): string {
  switch (energyMode) {
    case 'wind':
      return 'Wind Readiness';
    case 'hybrid':
      return 'Hybrid Readiness';
    case 'overall':
      return 'RE Readiness';
    default:
      return 'Solar Readiness';
  }
}

// ── 2D Classification System (Option C) ──────────────────────────────────

/** Resolve economic tier per energy mode using mode-specific LCOE/all-in fields. */
export function getEffectiveEconomicTier(row: ScorecardRow, energyMode: EnergyMode): EconomicTier {
  // Overall mode uses backend's precomputed tier (best across all technologies)
  if (energyMode === 'overall') {
    return row.economic_tier || 'not_competitive';
  }

  const gridCost = row.grid_cost_usd_mwh;
  if (!gridCost || gridCost <= 0) return 'not_competitive';

  let hasResource: boolean;
  let lcoeRe: number | null;
  let allin247: number | null;

  switch (energyMode) {
    case 'solar':
      hasResource = row.buildable_area_ha > 0;
      lcoeRe = row.lcoe_mid_usd_mwh ?? null;
      allin247 = row.lcoe_with_battery_usd_mwh ?? null;
      break;
    case 'wind':
      hasResource = (row.wind_buildable_area_ha ?? 0) > 0;
      lcoeRe = row.lcoe_wind_mid_usd_mwh ?? null;
      allin247 = row.lcoe_wind_allin_mid_usd_mwh ?? null;
      break;
    case 'hybrid':
      hasResource = row.buildable_area_ha > 0 || (row.wind_buildable_area_ha ?? 0) > 0;
      lcoeRe = row.hybrid_lcoe_usd_mwh ?? null;
      allin247 = row.hybrid_allin_usd_mwh ?? null;
      break;
    default:
      return row.economic_tier || 'not_competitive';
  }

  if (!hasResource) return 'no_resource';
  if (lcoeRe == null) return 'not_competitive';
  if (allin247 != null && allin247 <= gridCost) return 'full_re';
  if (lcoeRe <= gridCost) return 'partial_re';
  const gapPct = ((lcoeRe - gridCost) / gridCost) * 100;
  if (gapPct <= 20) return 'near_parity';
  return 'not_competitive';
}

/** Mode-specific label for an economic tier. */
export function getEconomicTierLabel(tier: EconomicTier, energyMode: EnergyMode): string {
  if (tier === 'full_re') {
    switch (energyMode) {
      case 'solar':
        return 'Full Solar';
      case 'wind':
        return 'Full Wind';
      default:
        return 'Full RE';
    }
  }
  if (tier === 'partial_re') {
    switch (energyMode) {
      case 'solar':
        return 'Partial Solar';
      case 'wind':
        return 'Partial Wind';
      default:
        return 'Partial RE';
    }
  }
  if (tier === 'no_resource') {
    switch (energyMode) {
      case 'solar':
        return 'No Solar Resource';
      case 'wind':
        return 'No Wind Resource';
      default:
        return 'No Resource';
    }
  }
  return ECONOMIC_TIER_LABELS[tier];
}

/** Mode-specific description for an economic tier. */
export function getEconomicTierDescription(tier: EconomicTier, energyMode: EnergyMode): string {
  if (tier === 'full_re') {
    switch (energyMode) {
      case 'solar':
        return 'Solar + storage beats grid for 24/7 supply. Deploy now.';
      case 'wind':
        return 'Wind + firming beats grid for 24/7 supply. Deploy now.';
      case 'hybrid':
        return 'Hybrid solar+wind beats grid for 24/7 supply. Deploy now.';
      default:
        return 'RE + storage beats grid for 24/7 supply. Deploy now.';
    }
  }
  if (tier === 'partial_re') {
    switch (energyMode) {
      case 'solar':
        return 'Daytime solar beats grid. Nighttime stays on grid. Still cuts 42% of energy cost.';
      case 'wind':
        return 'Wind generation beats grid cost, but firming for 24/7 pushes above grid.';
      case 'hybrid':
        return 'Hybrid generation beats grid, but 24/7 storage cost exceeds grid.';
      default:
        return 'Daytime RE beats grid. Nighttime stays on grid. Still cuts 42% of energy cost.';
    }
  }
  if (tier === 'no_resource') {
    switch (energyMode) {
      case 'solar':
        return 'No buildable solar land within 50 km.';
      case 'wind':
        return 'No viable wind resource within 50 km.';
      default:
        return 'No viable renewable resource within 50 km.';
    }
  }
  return ECONOMIC_TIER_DESCRIPTIONS[tier];
}

/** Context-aware infrastructure readiness label.
 *  Distinguishes "Upgrade Substation" (capacity issue) from "Build Substation" (distance issue). */
export function getInfraReadinessLabel(row: ScorecardRow): string {
  const infra = row.infrastructure_readiness || row.grid_integration_category;
  if (infra === 'invest_substation') {
    // If substation exists nearby but capacity is insufficient, it's an upgrade not a build
    const cap = row.capacity_assessment;
    if (cap === 'red' || cap === 'yellow') return 'Upgrade Substation';
  }
  return (
    INFRA_READINESS_LABELS[infra as InfrastructureReadiness] ?? INFRA_READINESS_LABELS.grid_first
  );
}

/** Resolve infrastructure readiness from backend field or grid_integration_category. */
export function getEffectiveInfraReadiness(row: ScorecardRow): InfrastructureReadiness {
  if (row.infrastructure_readiness) return row.infrastructure_readiness;
  const cat = row.grid_integration_category;
  if (
    cat === 'within_boundary' ||
    cat === 'grid_ready' ||
    cat === 'invest_transmission' ||
    cat === 'invest_substation' ||
    cat === 'grid_first'
  ) {
    return cat;
  }
  return 'grid_first';
}

/** Resolve modifier badges from backend field or derive from existing booleans. */
export function getEffectiveModifiers(row: ScorecardRow): ModifierBadge[] {
  if (row.modifier_badges) return row.modifier_badges;
  const badges: ModifierBadge[] = [];
  if (row.cbam_urgent) badges.push('cbam_urgent');
  if (row.action_flag === 'plan_late') badges.push('plan_late');
  return badges;
}

import { ECONOMIC_TIER_HIERARCHY } from './constants';
import { resolveCost } from './costBasis';
import type {
  CostBasis,
  EconomicTier,
  EnergyMode,
  InfrastructureReadiness,
  ScorecardRow,
} from './types';

export type FlipDirection = 'improved' | 'worsened' | 'unchanged';

export interface FlipDiffRow {
  site_id: string;
  site_name: string;
  sector: string;
  tier_baseline: EconomicTier;
  tier_flip: EconomicTier;
  infra_baseline: InfrastructureReadiness;
  infra_flip: InfrastructureReadiness;
  lcoe_baseline: number | null;
  lcoe_flip: number | null;
  delta_lcoe: number | null;
  gap_baseline_pct: number | null;
  gap_flip_pct: number | null;
  flip_direction: FlipDirection;
  cbam_urgent_baseline: boolean;
  cbam_urgent_flip: boolean;
  cbam_urgent_changed: boolean;
}

export interface FlipSummary {
  total_sites: number;
  flipped_to_better_tier: number;
  flipped_to_worse_tier: number;
  flipped_to_full_re: number;
  median_gap_baseline_pct: number | null;
  median_gap_flip_pct: number | null;
  gap_closed_pct: number | null;
  new_cbam_urgent_count: number;
}

const TIER_RANK: Record<EconomicTier, number> = ECONOMIC_TIER_HIERARCHY.reduce(
  (acc, tier, idx) => {
    acc[tier] = idx;
    return acc;
  },
  {} as Record<EconomicTier, number>,
);

function tierOf(row: ScorecardRow | undefined): EconomicTier {
  return row?.economic_tier ?? 'no_resource';
}

function infraOf(row: ScorecardRow | undefined): InfrastructureReadiness {
  return row?.infrastructure_readiness ?? 'no_resource';
}

function lcoeOf(
  row: ScorecardRow | undefined,
  energyMode: EnergyMode,
  costBasis: CostBasis,
): number | null {
  if (!row) return null;
  return resolveCost(row, energyMode, costBasis);
}

function gapOf(
  row: ScorecardRow | undefined,
  energyMode: EnergyMode,
  costBasis: CostBasis,
): number | null {
  if (!row) return null;
  const cost = resolveCost(row, energyMode, costBasis);
  const grid = row.grid_cost_usd_mwh;
  if (cost == null || grid == null || !Number.isFinite(grid) || grid <= 0) return null;
  return ((cost - grid) / grid) * 100;
}

function median(nums: number[]): number | null {
  if (!nums.length) return null;
  const sorted = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
}

export function computeFlipDiff(
  baseline: ScorecardRow[],
  flip: ScorecardRow[],
  energyMode: EnergyMode,
  costBasis: CostBasis,
): { rows: FlipDiffRow[]; summary: FlipSummary } {
  const flipById = new Map(flip.map((r) => [r.site_id, r]));
  const rows: FlipDiffRow[] = [];

  for (const b of baseline) {
    const f = flipById.get(b.site_id);
    const tierBase = tierOf(b);
    const tierFlip = tierOf(f);
    const infraBase = infraOf(b);
    const infraFlip = infraOf(f);
    const lcoeBase = lcoeOf(b, energyMode, costBasis);
    const lcoeFlip = lcoeOf(f, energyMode, costBasis);
    const gapBase = gapOf(b, energyMode, costBasis);
    const gapFlip = gapOf(f, energyMode, costBasis);
    const cbamBase = !!b.cbam_urgent;
    const cbamFlip = !!f?.cbam_urgent;

    let direction: FlipDirection = 'unchanged';
    if (TIER_RANK[tierFlip] < TIER_RANK[tierBase]) direction = 'improved';
    else if (TIER_RANK[tierFlip] > TIER_RANK[tierBase]) direction = 'worsened';

    rows.push({
      site_id: b.site_id,
      site_name: b.site_name,
      sector: b.sector,
      tier_baseline: tierBase,
      tier_flip: tierFlip,
      infra_baseline: infraBase,
      infra_flip: infraFlip,
      lcoe_baseline: lcoeBase,
      lcoe_flip: lcoeFlip,
      delta_lcoe: lcoeBase != null && lcoeFlip != null ? lcoeFlip - lcoeBase : null,
      gap_baseline_pct: gapBase,
      gap_flip_pct: gapFlip,
      flip_direction: direction,
      cbam_urgent_baseline: cbamBase,
      cbam_urgent_flip: cbamFlip,
      cbam_urgent_changed: cbamBase !== cbamFlip,
    });
  }

  const flippedBetter = rows.filter((r) => r.flip_direction === 'improved').length;
  const flippedWorse = rows.filter((r) => r.flip_direction === 'worsened').length;
  const flippedFullRe = rows.filter(
    (r) => r.tier_baseline !== 'full_re' && r.tier_flip === 'full_re',
  ).length;
  const newCbamUrgent = rows.filter((r) => !r.cbam_urgent_baseline && r.cbam_urgent_flip).length;

  // Exclude no_resource sites from gap medians — they have no LCOE comparison
  const gapsBase = rows
    .filter((r) => r.tier_baseline !== 'no_resource')
    .map((r) => r.gap_baseline_pct)
    .filter((v): v is number => v != null);
  const gapsFlip = rows
    .filter((r) => r.tier_baseline !== 'no_resource')
    .map((r) => r.gap_flip_pct)
    .filter((v): v is number => v != null);
  const medBase = median(gapsBase);
  const medFlip = median(gapsFlip);

  return {
    rows,
    summary: {
      total_sites: rows.length,
      flipped_to_better_tier: flippedBetter,
      flipped_to_worse_tier: flippedWorse,
      flipped_to_full_re: flippedFullRe,
      median_gap_baseline_pct: medBase,
      median_gap_flip_pct: medFlip,
      gap_closed_pct: medBase != null && medFlip != null ? medBase - medFlip : null,
      new_cbam_urgent_count: newCbamUrgent,
    },
  };
}

export function flipDiffToCsv(rows: FlipDiffRow[]): string {
  const headers = [
    'site_id',
    'site_name',
    'sector',
    'tier_baseline',
    'tier_flip',
    'infra_baseline',
    'infra_flip',
    'flip_direction',
    'lcoe_baseline_usd_mwh',
    'lcoe_flip_usd_mwh',
    'delta_lcoe_usd_mwh',
    'gap_baseline_pct',
    'gap_flip_pct',
    'cbam_urgent_baseline',
    'cbam_urgent_flip',
  ];
  const fmt = (v: unknown): string => {
    if (v == null) return '';
    if (typeof v === 'number') return Number.isFinite(v) ? v.toFixed(2) : '';
    const s = String(v);
    return s.includes(',') || s.includes('"') ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = rows.map((r) =>
    [
      r.site_id,
      r.site_name,
      r.sector,
      r.tier_baseline,
      r.tier_flip,
      r.infra_baseline,
      r.infra_flip,
      r.flip_direction,
      r.lcoe_baseline,
      r.lcoe_flip,
      r.delta_lcoe,
      r.gap_baseline_pct,
      r.gap_flip_pct,
      r.cbam_urgent_baseline,
      r.cbam_urgent_flip,
    ]
      .map(fmt)
      .join(','),
  );
  return [headers.join(','), ...lines].join('\n');
}

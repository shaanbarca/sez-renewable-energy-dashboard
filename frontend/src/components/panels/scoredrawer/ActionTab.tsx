import {
  getEconomicTierDescription,
  getEconomicTierLabel,
  getEffectiveEconomicTier,
  getEffectiveInfraReadiness,
  getEffectiveModifiers,
} from '../../../lib/actionFlags';
import {
  ECONOMIC_TIER_COLORS,
  ECONOMIC_TIER_HIERARCHY,
  INFRA_READINESS_COLORS,
  INFRA_READINESS_DESCRIPTIONS,
  INFRA_READINESS_HIERARCHY,
  INFRA_READINESS_LABELS,
} from '../../../lib/constants';
import type { ScorecardRow } from '../../../lib/types';
import { useDashboardStore } from '../../../store/dashboard';
import { FuelTypePill } from '../../ui/FuelTypePill';
import ModifierBadgePill from '../../ui/ModifierBadgePill';
import { TierPill } from '../../ui/TierPill';
import { FlagStep, SectionHeader, StatCard, StatRowWithTip } from './StatComponents';

// v4.1b #93/#96: human-readable label + short tooltip per CBAM scenario.
// Mirrors src/assumptions.py::CBAM_SCENARIO_VALUES. Used only by the Action-tab
// headline row that surfaces cbam_active_scenario_value_usd_mwh.
// Exported for vitest test coverage.
export const CBAM_SCENARIO_META: Record<string, { label: string; tip: string }> = {
  none: {
    label: 'No carbon adder',
    tip: 'Incumbent is the unadjusted grid cost (BPP/I-4 tariff). User has dialed CBAM off.',
  },
  domestic_low: {
    label: 'Domestic carbon — $5/tCO₂',
    tip: 'Indonesia IDX Carbon floor. The actually-enforced domestic carbon price today.',
  },
  domestic_high: {
    label: 'Domestic carbon — $25/tCO₂',
    tip: 'Potential 2030 IDX Carbon ceiling. Forward-looking but in-policy-trajectory.',
  },
  effective_2025: {
    label: 'Effective 2025 (destination-weighted)',
    tip: 'Per-market carbon price blended by 2025 export shares (EU CBAM + China CCM + IDX Carbon). The realistic exposure for export-heavy sites.',
  },
  effective_2030: {
    label: 'Effective 2030 (destination-weighted)',
    tip: 'Same destination-weighted blend, projected to 2030 carbon prices (EU ETS converging, China CCM expanding).',
  },
  cbam_full_2026: {
    label: 'EU CBAM only (mature regulation)',
    tip: 'The only carbon price enforced today — assumes 100% EU exposure at the 2026 certificate price (~$90/tCO₂). Conservative, defensible reference.',
  },
  cbam_full_2030: {
    label: 'EU CBAM at 2030 stress',
    tip: '100% EU exposure × EU ETS 2030 price. Stress test for the worst-case-export site.',
  },
};

export function ActionTab({ row }: { row: ScorecardRow }) {
  const energyMode = useDashboardStore((s) => s.energyMode);
  const costBasis = useDashboardStore((s) => s.costBasis);
  const activeTier = getEffectiveEconomicTier(row, energyMode, costBasis);
  const activeInfra = getEffectiveInfraReadiness(row, energyMode);
  const modifiers = getEffectiveModifiers(row);
  const activeTierIdx = ECONOMIC_TIER_HIERARCHY.indexOf(activeTier);
  const activeInfraIdx = INFRA_READINESS_HIERARCHY.indexOf(activeInfra);

  return (
    <>
      {/* Two-column: Economic Viability + Infrastructure Readiness */}
      <StatCard>
        <div className="grid grid-cols-2 gap-3">
          {/* Left column: Economic Viability */}
          <div>
            <p
              className="text-[10px] uppercase tracking-wider mb-2 font-medium"
              style={{ color: 'var(--text-muted)' }}
            >
              Economic Viability
            </p>
            {ECONOMIC_TIER_HIERARCHY.map((tier, i) => {
              const isActive = activeTier === tier;
              const isAbove = activeTierIdx >= 0 && i < activeTierIdx;
              return (
                <FlagStep
                  key={tier}
                  label={getEconomicTierLabel(tier, energyMode)}
                  color={ECONOMIC_TIER_COLORS[tier]}
                  active={isActive}
                  above={isAbove}
                  isFirst={i === 0}
                  isLast={i === ECONOMIC_TIER_HIERARCHY.length - 1}
                  explanation={isActive ? getEconomicTierDescription(tier, energyMode) : undefined}
                />
              );
            })}
          </div>
          {/* Right column: Infrastructure Readiness */}
          <div>
            <p
              className="text-[10px] uppercase tracking-wider mb-2 font-medium"
              style={{ color: 'var(--text-muted)' }}
            >
              Infrastructure
            </p>
            {INFRA_READINESS_HIERARCHY.map((infra, i) => {
              const isActive = activeInfra === infra;
              const isAbove = activeInfraIdx >= 0 && i < activeInfraIdx;
              const color =
                INFRA_READINESS_COLORS[infra] === 'transparent'
                  ? '#4CAF50'
                  : INFRA_READINESS_COLORS[infra];
              return (
                <FlagStep
                  key={infra}
                  label={INFRA_READINESS_LABELS[infra]}
                  color={color}
                  active={isActive}
                  above={isAbove}
                  isFirst={i === 0}
                  isLast={i === INFRA_READINESS_HIERARCHY.length - 1}
                  explanation={isActive ? INFRA_READINESS_DESCRIPTIONS[infra] : undefined}
                />
              );
            })}
          </div>
        </div>
        {/* Modifier badges */}
        {modifiers.length > 0 && (
          <div
            className="mt-3 pt-2 flex gap-2 flex-wrap"
            style={{ borderTop: '1px solid var(--border-subtle)' }}
          >
            {modifiers.map((badge) => (
              <ModifierBadgePill key={badge} badge={badge} size="md" />
            ))}
          </div>
        )}
      </StatCard>
      <StatCard>
        <SectionHeader title="Key Numbers" subtitle="The metrics behind this recommendation" />
        {/* v4.3 M-AT8b — show the comparator the gap was actually computed against.
            For captive sites this is the captive incumbent, not the grid tariff. */}
        {(() => {
          const kind = row.effective_incumbent_kind ?? 'grid';
          const inc = row.effective_incumbent_lcoe_usd_mwh ?? row.grid_cost_usd_mwh;
          if (kind === 'grid') {
            return (
              <StatRowWithTip
                label="Grid Cost Proxy"
                value={inc?.toFixed(1)}
                unit="$/MWh"
                tip="PLN benchmark for competitive gap. Either BPP (cost of supply) or I-4/TT tariff, depending on selected benchmark mode."
              />
            );
          }
          return (
            <StatRowWithTip
              label="Captive Power"
              value={inc?.toFixed(1)}
              unit="$/MWh"
              tip="On-site captive plant LCOE — what this site actually pays today. The competitive gap above is computed against this incumbent, not the PLN grid tariff. Fuel pill shows what's burned (Coal / Gas / Hydro). See methodology §13.9–§13.11."
              trailing={
                <>
                  <FuelTypePill fuelType={row.captive_fuel_type} ml={6} />
                  <TierPill tier={row.captive_lcoe_tier} ml={0} />
                </>
              }
            />
          );
        })()}
        {row.grid_cost_usd_mwh != null &&
          row.effective_incumbent_kind &&
          row.effective_incumbent_kind !== 'grid' && (
            <StatRowWithTip
              label="Grid Cost Proxy (reference)"
              value={row.grid_cost_usd_mwh.toFixed(1)}
              unit="$/MWh"
              tip="PLN tariff for this grid region. Shown for reference — this site is captive-primary, so the gap above uses the captive incumbent."
            />
          )}
        <StatRowWithTip
          label="BPP"
          value={row.bpp_usd_mwh != null ? row.bpp_usd_mwh.toFixed(1) : null}
          unit="$/MWh"
          tip="Biaya Pokok Penyediaan — PLN's unsubsidized cost of supply for this grid region."
        />
        <StatRowWithTip
          label="Project Viable"
          value={row.project_viable ? 'Yes' : 'No'}
          tip="Whether a solar project meets minimum thresholds: PVOUT above cutoff, buildable area exists, and capacity above minimum viable size."
        />
      </StatCard>

      {/* v4.1b #93: CBAM-adjusted incumbent. Surfaces the active scenario
          (#96/#98 toggle) + the carbon-loaded incumbent it implies. Only
          renders when the site is CBAM-exposed AND the user hasn't dialed
          the scenario to 'none'. The provenance badge surfaces whether the
          underlying export shares came from a site_override / sector_default
          / eu_fallback (destination-weighted scenarios only). */}
      {row.cbam_exposed &&
        row.cbam_active_scenario_value_usd_mwh != null &&
        row.cbam_active_scenario &&
        row.cbam_active_scenario !== 'none' && (
          <StatCard>
            <SectionHeader
              title="CBAM-Adjusted Incumbent"
              subtitle="Grid cost + per-site carbon adder under the active scenario"
              tip="Effective incumbent comparator = grid_cost + (emissions intensity × effective carbon price). The Assumptions sidebar CBAM Scenario picker selects which carbon-pricing assumption drives this. Default is sector-dependent (nickel → 2025 destination-weighted, cement → $25/t domestic, etc.) per spec §2.4."
            />
            <div className="flex items-center gap-2 mb-2">
              <span
                className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                style={{
                  background: 'rgba(255, 112, 67, 0.15)',
                  color: '#FF7043',
                  border: '1px solid rgba(255, 112, 67, 0.40)',
                }}
                title={CBAM_SCENARIO_META[row.cbam_active_scenario]?.tip ?? ''}
              >
                {CBAM_SCENARIO_META[row.cbam_active_scenario]?.label ?? row.cbam_active_scenario}
              </span>
              {/* Provenance badge — only meaningful for destination-weighted
                  scenarios where the export-share lookup actually happened. */}
              {(row.cbam_active_scenario === 'effective_2025' ||
                row.cbam_active_scenario === 'effective_2030') &&
                row.cbam_destination_weighted_shares_source && (
                  <span
                    className="text-[9px] px-1.5 py-0.5 rounded font-medium"
                    style={{
                      background:
                        row.cbam_destination_weighted_shares_source === 'site_override'
                          ? 'rgba(76, 175, 80, 0.15)'
                          : row.cbam_destination_weighted_shares_source === 'sector_default'
                            ? 'rgba(255, 193, 7, 0.15)'
                            : 'rgba(150, 150, 150, 0.15)',
                      color:
                        row.cbam_destination_weighted_shares_source === 'site_override'
                          ? '#4CAF50'
                          : row.cbam_destination_weighted_shares_source === 'sector_default'
                            ? '#FFC107'
                            : 'var(--text-muted)',
                    }}
                    title={
                      row.cbam_destination_weighted_shares_source === 'site_override'
                        ? 'Export shares are a hand-curated per-site override (highest confidence).'
                        : row.cbam_destination_weighted_shares_source === 'sector_default'
                          ? 'Export shares come from the sector default for this subsector (medium confidence).'
                          : 'No shares data — fell back to 100% EU exposure.'
                    }
                  >
                    {row.cbam_destination_weighted_shares_source === 'site_override'
                      ? '● Site override'
                      : row.cbam_destination_weighted_shares_source === 'sector_default'
                        ? '◐ Sector default'
                        : '○ EU fallback'}
                  </span>
                )}
            </div>
            <StatRowWithTip
              label="Adjusted Incumbent"
              value={row.cbam_active_scenario_value_usd_mwh.toFixed(1)}
              unit="$/MWh"
              tip="Carbon-loaded incumbent = grid_cost ($/MWh) + emissions_intensity (tCO₂/MWh) × effective carbon price ($/tCO₂). The competitive gap above does NOT yet use this — it still compares against the unadjusted grid_cost / captive incumbent. Once v4.3 lands, cbam_urgent will key off this column."
            />
          </StatCard>
        )}

      {row.ruptl_region_summary && (
        <StatCard>
          <SectionHeader
            title="RUPTL Pipeline"
            subtitle="What grid and generation additions is PLN planning for this region?"
            tip="RUPTL = PLN's 10-year grid expansion plan. Shows planned generation additions by technology in this site's grid region."
          />
          <div className="text-[11px] leading-relaxed" style={{ color: 'var(--text-value)' }}>
            {row.ruptl_region_summary}
          </div>
        </StatCard>
      )}
    </>
  );
}

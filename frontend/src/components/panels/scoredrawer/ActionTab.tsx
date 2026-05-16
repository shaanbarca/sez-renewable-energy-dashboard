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

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
  MODIFIER_BADGE_COLORS,
  MODIFIER_BADGE_LABELS,
} from '../../../lib/constants';
import type { ScorecardRow } from '../../../lib/types';
import { useDashboardStore } from '../../../store/dashboard';
import { FlagStep, SectionHeader, StatCard, StatRowWithTip } from './StatComponents';

export function ActionTab({ row }: { row: ScorecardRow }) {
  const energyMode = useDashboardStore((s) => s.energyMode);
  const activeTier = getEffectiveEconomicTier(row, energyMode);
  const activeInfra = getEffectiveInfraReadiness(row);
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
              <span
                key={badge}
                className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium"
                style={{
                  backgroundColor: `${MODIFIER_BADGE_COLORS[badge]}22`,
                  color: MODIFIER_BADGE_COLORS[badge],
                  border: `1px solid ${MODIFIER_BADGE_COLORS[badge]}44`,
                }}
              >
                {MODIFIER_BADGE_LABELS[badge]}
              </span>
            ))}
          </div>
        )}
      </StatCard>
      <StatCard>
        <SectionHeader title="Key Numbers" subtitle="The metrics behind this recommendation" />
        <StatRowWithTip
          label="Grid Cost Proxy"
          value={row.grid_cost_usd_mwh?.toFixed(1)}
          unit="$/MWh"
          tip="The benchmark used for competitive gap calculation. Either BPP (cost of supply) or I-4/TT tariff, depending on your selected benchmark mode."
        />
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
            tip="RUPTL = PLN's 10-year grid expansion plan. Shows planned generation additions by technology in this KEK's grid region."
          />
          <div className="text-[11px] leading-relaxed" style={{ color: 'var(--text-value)' }}>
            {row.ruptl_region_summary}
          </div>
        </StatCard>
      )}
    </>
  );
}

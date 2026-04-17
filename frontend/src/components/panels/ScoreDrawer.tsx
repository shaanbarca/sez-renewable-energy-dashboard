import * as Tabs from '@radix-ui/react-tabs';
import { useCallback, useEffect, useState } from 'react';
import {
  getEconomicTierDescription,
  getEconomicTierLabel,
  getEffectiveEconomicTier,
  getEffectiveModifiers,
  getInfraReadinessLabel,
} from '../../lib/actionFlags';
import { fetchSiteSubstations } from '../../lib/api';
import {
  ECONOMIC_TIER_COLORS,
  MODIFIER_BADGE_COLORS,
  MODIFIER_BADGE_LABELS,
} from '../../lib/constants';
import { formatGridRegion } from '../../lib/format';
import type { SubstationWithCosts } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';
import { ActionTab } from './scoredrawer/ActionTab';
import { DemandTab } from './scoredrawer/DemandTab';
import { EconomicsTab } from './scoredrawer/EconomicsTab';
import { GridTab } from './scoredrawer/GridTab';
import { OverviewTab } from './scoredrawer/OverviewTab';
import { ResourceTab } from './scoredrawer/ResourceTab';
import { CloseIcon } from './scoredrawer/StatComponents';

const TABS = [
  { value: 'overview', label: 'Overview' },
  { value: 'resource', label: 'Resource' },
  { value: 'grid', label: 'Grid' },
  { value: 'economics', label: 'Economics' },
  { value: 'industry', label: 'Industry' },
  { value: 'action', label: 'Action' },
] as const;

export default function ScoreDrawer() {
  const selectedSite = useDashboardStore((s) => s.selectedSite);
  const drawerOpen = useDashboardStore((s) => s.drawerOpen);
  const scorecard = useDashboardStore((s) => s.scorecard);
  const closeDrawer = useDashboardStore((s) => s.closeDrawer);
  const energyMode = useDashboardStore((s) => s.energyMode);

  const [substations, setSubstations] = useState<SubstationWithCosts[]>([]);
  const [loadingSubs, setLoadingSubs] = useState(false);

  const row = scorecard?.find((r) => r.site_id === selectedSite) ?? null;

  const handleClose = useCallback(() => {
    closeDrawer();
  }, [closeDrawer]);

  // Fetch substations when selected site changes
  useEffect(() => {
    if (!selectedSite) {
      setSubstations([]);
      return;
    }

    let cancelled = false;
    setLoadingSubs(true);

    fetchSiteSubstations(selectedSite, 50)
      .then((data) => {
        if (!cancelled) {
          const parsed = data as { substations: SubstationWithCosts[] };
          setSubstations(parsed.substations ?? []);
        }
      })
      .catch(() => {
        if (!cancelled) setSubstations([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingSubs(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedSite]);

  // Keyboard escape to close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && drawerOpen) {
        handleClose();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [drawerOpen, handleClose]);

  const effectiveTier = row ? getEffectiveEconomicTier(row, energyMode) : null;
  const tierColor = effectiveTier ? (ECONOMIC_TIER_COLORS[effectiveTier] ?? '#666') : '#666';
  const tierLabel = effectiveTier ? getEconomicTierLabel(effectiveTier, energyMode) : '';
  const tierDescription = effectiveTier
    ? getEconomicTierDescription(effectiveTier, energyMode)
    : '';
  const infraLabel = row ? getInfraReadinessLabel(row) : '';
  const modifiers = row ? getEffectiveModifiers(row) : [];

  return (
    <div
      data-tour="drawer"
      className={`absolute top-0 right-0 z-30 h-full w-[420px] flex flex-col
                  transition-transform duration-300 ease-in-out ${
                    drawerOpen && row ? 'translate-x-0' : 'translate-x-full'
                  }`}
      style={{
        background: 'var(--glass-heavy)',
        backdropFilter: 'var(--blur-heavy)',
        WebkitBackdropFilter: 'var(--blur-heavy)',
        borderLeft: '1px solid var(--glass-border)',
        boxShadow: 'var(--drawer-shadow)',
      }}
    >
      {row && (
        <>
          {/* Header */}
          <div className="px-4 pt-4 pb-2">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h2
                  className="text-sm font-semibold truncate"
                  style={{ color: 'var(--text-primary)' }}
                >
                  {row.site_name}
                </h2>
                <div className="text-[11px] mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                  {row.province} &middot; {formatGridRegion(row.grid_region_id)}
                </div>
              </div>
              <button
                onClick={handleClose}
                className="p-1 rounded transition-colors"
                style={{ color: 'var(--text-muted)' }}
                aria-label="Close drawer"
              >
                <CloseIcon />
              </button>
            </div>

            {/* Economic tier + infrastructure banner */}
            <div
              className="mt-3 px-3 py-2 rounded-md"
              style={{ background: `${tierColor}22`, border: `1px solid ${tierColor}44` }}
            >
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ background: tierColor }}
                />
                <span className="text-xs font-medium" style={{ color: tierColor }}>
                  {tierLabel}
                </span>
                {infraLabel && (
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded"
                    style={{ background: 'var(--glass)', color: 'var(--text-secondary)' }}
                  >
                    {infraLabel}
                  </span>
                )}
              </div>
              {tierDescription && (
                <p
                  className="text-[10px] mt-1 leading-relaxed pl-[18px]"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {tierDescription}
                </p>
              )}
              {modifiers.length > 0 && (
                <div className="flex gap-1.5 mt-1.5 pl-[18px]">
                  {modifiers.map((badge) => (
                    <span
                      key={badge}
                      className="text-[9px] px-1.5 py-0.5 rounded-full font-medium"
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
            </div>
          </div>

          {/* Tabs */}
          <Tabs.Root defaultValue="overview" className="flex-1 flex flex-col min-h-0">
            <Tabs.List
              className="flex px-4 gap-0.5"
              style={{ borderBottom: '1px solid var(--border-subtle)' }}
            >
              {TABS.map((tab) => (
                <Tabs.Trigger
                  key={tab.value}
                  value={tab.value}
                  className="drawer-tab px-2.5 py-2 text-[11px] font-medium transition-colors relative
                             after:absolute after:bottom-0 after:left-1 after:right-1 after:h-[2px]
                             after:rounded-full after:opacity-0
                             data-[state=active]:after:opacity-100 after:transition-opacity"
                >
                  {tab.label}
                </Tabs.Trigger>
              ))}
            </Tabs.List>

            <div className="flex-1 overflow-y-auto px-4 py-3">
              <Tabs.Content value="overview">
                <OverviewTab row={row} />
              </Tabs.Content>
              <Tabs.Content value="resource">
                <ResourceTab row={row} />
              </Tabs.Content>
              <Tabs.Content value="grid">
                <GridTab row={row} substations={substations} loadingSubs={loadingSubs} />
              </Tabs.Content>
              <Tabs.Content value="economics">
                <EconomicsTab row={row} />
              </Tabs.Content>
              <Tabs.Content value="industry">
                <DemandTab row={row} />
              </Tabs.Content>
              <Tabs.Content value="action">
                <ActionTab row={row} />
              </Tabs.Content>
            </div>
          </Tabs.Root>
        </>
      )}
    </div>
  );
}

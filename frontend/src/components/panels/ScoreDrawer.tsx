import * as Tabs from '@radix-ui/react-tabs';
import { useCallback, useEffect, useState } from 'react';
import { fetchKekSubstations } from '../../lib/api';
import { ACTION_FLAG_COLORS, ACTION_FLAG_LABELS } from '../../lib/constants';
import type { ScorecardRow } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

/* ---------- Types ---------- */

interface SubstationInfo {
  name: string;
  dist_km: number;
  is_nearest: boolean;
  lat: number;
  lon: number;
}

/* ---------- Helpers ---------- */

function CloseIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function StatRow({
  label,
  value,
  unit,
}: {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
}) {
  const display = value == null || value === '' ? 'N/A' : `${value}${unit ? ` ${unit}` : ''}`;
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-[11px] text-zinc-500">{label}</span>
      <span className="text-[12px] font-medium text-zinc-200 tabular-nums">{display}</span>
    </div>
  );
}

function StatRowWithTip({
  label,
  value,
  unit,
  tip,
}: {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  tip: string;
}) {
  const [showTip, setShowTip] = useState(false);
  const display = value == null || value === '' ? 'N/A' : `${value}${unit ? ` ${unit}` : ''}`;
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-[11px] text-zinc-500 relative">
        {label}
        <span
          className="ml-1 text-zinc-600 hover:text-zinc-300 cursor-help inline-block"
          onMouseEnter={() => setShowTip(true)}
          onMouseLeave={() => setShowTip(false)}
        >
          ?
          {showTip && (
            <span
              className="absolute left-0 top-full mt-1 z-30 px-2.5 py-1.5 rounded text-[10px] text-zinc-200 leading-snug whitespace-normal w-48"
              style={{
                background: 'rgba(20, 20, 24, 0.95)',
                border: '1px solid rgba(255,255,255,0.15)',
                boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
              }}
            >
              {tip}
            </span>
          )}
        </span>
      </span>
      <span className="text-[12px] font-medium text-zinc-200 tabular-nums">{display}</span>
    </div>
  );
}

function StatCard({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="rounded-md px-3 py-2 mb-2"
      style={{
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.05)',
      }}
    >
      {children}
    </div>
  );
}

function FlagBadge({ active, label, color }: { active: boolean; label: string; color: string }) {
  return (
    <div className="flex items-center justify-between py-1">
      <div className="flex items-center gap-2">
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: active ? color : 'rgba(255,255,255,0.1)' }}
        />
        <span className="text-[11px] text-zinc-400">{label}</span>
      </div>
      <span
        className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
          active ? 'text-white/90' : 'text-zinc-600'
        }`}
        style={active ? { background: `${color}33` } : { background: 'rgba(255,255,255,0.03)' }}
      >
        {active ? 'Active' : 'Inactive'}
      </span>
    </div>
  );
}

const ACTION_FLAG_DESCRIPTIONS: Record<string, string> = {
  solar_now: 'Solar is cost-competitive with the grid today.',
  invest_resilience: 'Near-competitive; invest for reliability and resilience.',
  grid_first: 'Grid power is cheaper; focus on grid improvements first.',
  plan_late: 'Low solar resource; revisit when costs decline further.',
  not_competitive: 'Solar is not competitive under current conditions.',
};

/* ---------- Tab content components ---------- */

function InfoTab({ row }: { row: ScorecardRow }) {
  return (
    <>
      <StatCard>
        <StatRow label="Type" value={row.kek_type ?? null} />
        <StatRow label="Category" value={row.category ?? null} />
        <StatRow
          label="Area"
          value={
            row.area_ha != null
              ? row.area_ha.toLocaleString(undefined, { maximumFractionDigits: 0 })
              : null
          }
          unit="ha"
        />
      </StatCard>
      <StatCard>
        <StatRow label="Province" value={row.province} />
        <StatRow label="Grid Region" value={row.grid_region_id} />
      </StatCard>
      <StatCard>
        <StatRow label="Developer" value={row.developer ?? null} />
        <StatRow label="Legal Basis" value={row.legal_basis ?? null} />
      </StatCard>
      {row.demand_2030_gwh != null && (
        <StatCard>
          <StatRowWithTip
            label="Est. Demand 2030"
            value={row.demand_2030_gwh.toFixed(1)}
            unit="GWh"
            tip="Estimated annual electricity demand in 2030, derived from zone area × energy intensity by KEK type. This is a provisional estimate."
          />
        </StatCard>
      )}
    </>
  );
}

function ResourceTab({
  row,
  substations,
  loadingSubs,
}: {
  row: ScorecardRow;
  substations: SubstationInfo[];
  loadingSubs: boolean;
}) {
  const pvoutCentroid = row.pvout_centroid_kwh_kwp_yr;
  const pvoutBest = row.pvout_best_50km_kwh_kwp_yr;
  const cf =
    pvoutBest != null
      ? (pvoutBest / 8760).toFixed(3)
      : pvoutCentroid != null
        ? (pvoutCentroid / 8760).toFixed(3)
        : null;
  const nearest = substations.find((s) => s.is_nearest);

  return (
    <>
      <StatCard>
        <StatRow
          label="PVOUT Centroid"
          value={pvoutCentroid != null ? pvoutCentroid.toFixed(0) : null}
          unit="kWh/kWp/yr"
        />
        <StatRow
          label="PVOUT Best 50km"
          value={pvoutBest != null ? pvoutBest.toFixed(0) : null}
          unit="kWh/kWp/yr"
        />
        <StatRow label="Capacity Factor" value={cf} />
      </StatCard>
      <StatCard>
        <StatRow
          label="Buildable Area"
          value={row.buildable_area_ha != null ? row.buildable_area_ha.toFixed(0) : null}
          unit="ha"
        />
        <StatRow
          label="Max Capacity"
          value={
            row.max_captive_capacity_mwp != null ? row.max_captive_capacity_mwp.toFixed(0) : null
          }
          unit="MWp"
        />
        {row.buildable_area_ha != null &&
          row.buildable_area_ha > 0 &&
          row.buildable_area_ha < 2000 && (
            <div className="text-[10px] text-amber-400/70 leading-tight mt-1">
              Note: buildable area is the sum of suitable pixels within 50km at ~1km resolution.
              Actual contiguous land for a solar farm may be smaller.
            </div>
          )}
      </StatCard>
      <StatCard>
        {loadingSubs ? (
          <div className="text-[11px] text-zinc-500 py-2 text-center">Loading substations...</div>
        ) : nearest ? (
          <>
            <StatRow label="Nearest Substation" value={nearest.name} />
            <StatRow label="Distance" value={nearest.dist_km.toFixed(1)} unit="km" />
          </>
        ) : (
          <StatRow label="Nearest Substation" value="N/A" />
        )}
      </StatCard>
    </>
  );
}

function LCOETab({ row }: { row: ScorecardRow }) {
  const remoteAllin = row.lcoe_remote_captive_allin_usd_mwh;

  return (
    <>
      <StatCard>
        <StatRow label="LCOE Low" value={row.lcoe_low_usd_mwh?.toFixed(1)} unit="$/MWh" />
        <StatRow label="LCOE Mid" value={row.lcoe_mid_usd_mwh?.toFixed(1)} unit="$/MWh" />
        <StatRow label="LCOE High" value={row.lcoe_high_usd_mwh?.toFixed(1)} unit="$/MWh" />
      </StatCard>
      {remoteAllin != null && (
        <StatCard>
          <StatRow label="All-in Remote LCOE" value={remoteAllin.toFixed(1)} unit="$/MWh" />
        </StatCard>
      )}
      <StatCard>
        <StatRow label="Grid Cost" value={row.grid_cost_usd_mwh?.toFixed(1)} unit="$/MWh" />
        <StatRow
          label="Gap vs Grid Cost"
          value={row.solar_competitive_gap_pct?.toFixed(1)}
          unit="%"
        />
      </StatCard>
      <StatCard>
        <StatRowWithTip
          label="BPP"
          value={row.bpp_usd_mwh?.toFixed(1)}
          unit="$/MWh"
          tip="Biaya Pokok Penyediaan — PLN's unsubsidized cost of electricity supply for this grid region. Unlike the industrial tariff, BPP reflects the true generation + transmission cost."
        />
        <StatRow
          label="Gap vs BPP"
          value={
            row.bpp_usd_mwh != null && row.lcoe_mid_usd_mwh != null && row.bpp_usd_mwh > 0
              ? (((row.lcoe_mid_usd_mwh - row.bpp_usd_mwh) / row.bpp_usd_mwh) * 100).toFixed(1)
              : null
          }
          unit="%"
        />
      </StatCard>
    </>
  );
}

function DemandTab({ row }: { row: ScorecardRow }) {
  const demand2030 = row.demand_2030_gwh;
  const geasShare = row.green_share_geas;

  return (
    <>
      <StatCard>
        <StatRow
          label="2030 Demand Estimate"
          value={demand2030 != null ? demand2030.toFixed(1) : null}
          unit="GWh"
        />
      </StatCard>
      <StatCard>
        <StatRow
          label="GEAS Green Share"
          value={geasShare != null ? `${(geasShare * 100).toFixed(1)}` : null}
          unit="%"
        />
        <StatRow
          label="Carbon Breakeven"
          value={
            row.carbon_breakeven_usd_tco2 != null ? row.carbon_breakeven_usd_tco2.toFixed(1) : null
          }
          unit="$/tCO2"
        />
      </StatCard>
    </>
  );
}

function PipelineTab({ row }: { row: ScorecardRow }) {
  const gridUpgrade = row.grid_upgrade_planned;
  const ruptlSummary = row.ruptl_region_summary;

  return (
    <>
      <StatCard>
        <StatRow label="Grid Region" value={row.grid_region_id} />
        <StatRow
          label="Grid Upgrade Planned"
          value={gridUpgrade != null ? (gridUpgrade ? 'Yes' : 'No') : 'N/A'}
        />
      </StatCard>
      {ruptlSummary && (
        <StatCard>
          <div className="text-[11px] text-zinc-500 mb-1">RUPTL Summary</div>
          <div className="text-[11px] text-zinc-300 leading-relaxed">{ruptlSummary}</div>
        </StatCard>
      )}
    </>
  );
}

function FlagsTab({ row }: { row: ScorecardRow }) {
  const flagKeys = [
    'solar_now',
    'invest_resilience',
    'grid_first',
    'plan_late',
    'not_competitive',
  ] as const;
  const activeFlag = row.action_flag;

  return (
    <>
      <StatCard>
        {flagKeys.map((flag) => (
          <FlagBadge
            key={flag}
            active={activeFlag === flag}
            label={ACTION_FLAG_LABELS[flag] ?? flag}
            color={ACTION_FLAG_COLORS[flag] ?? '#666'}
          />
        ))}
      </StatCard>
      <StatCard>
        <StatRow label="Grid Cost Proxy" value={row.grid_cost_usd_mwh?.toFixed(1)} unit="$/MWh" />
        <StatRow
          label="BPP"
          value={row.bpp_usd_mwh != null ? row.bpp_usd_mwh.toFixed(1) : null}
          unit="$/MWh"
        />
        <StatRow label="Project Viable" value={row.project_viable ? 'Yes' : 'No'} />
      </StatCard>
    </>
  );
}

/* ---------- Main drawer ---------- */

const TABS = [
  { value: 'info', label: 'KEK Info' },
  { value: 'resource', label: 'Resource' },
  { value: 'lcoe', label: 'LCOE' },
  { value: 'demand', label: 'Demand' },
  { value: 'pipeline', label: 'Pipeline' },
  { value: 'flags', label: 'Flags' },
] as const;

export default function ScoreDrawer() {
  const selectedKek = useDashboardStore((s) => s.selectedKek);
  const drawerOpen = useDashboardStore((s) => s.drawerOpen);
  const scorecard = useDashboardStore((s) => s.scorecard);
  const closeDrawer = useDashboardStore((s) => s.closeDrawer);

  const [substations, setSubstations] = useState<SubstationInfo[]>([]);
  const [loadingSubs, setLoadingSubs] = useState(false);

  const row = scorecard?.find((r) => r.kek_id === selectedKek) ?? null;

  const handleClose = useCallback(() => {
    closeDrawer();
  }, [closeDrawer]);

  // Fetch substations when selected KEK changes
  useEffect(() => {
    if (!selectedKek) {
      setSubstations([]);
      return;
    }

    let cancelled = false;
    setLoadingSubs(true);

    fetchKekSubstations(selectedKek, 50)
      .then((data) => {
        if (!cancelled) {
          const parsed = data as { substations: SubstationInfo[] };
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
  }, [selectedKek]);

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

  const flagColor = row ? (ACTION_FLAG_COLORS[row.action_flag] ?? '#666') : '#666';
  const flagLabel = row ? (ACTION_FLAG_LABELS[row.action_flag] ?? row.action_flag) : '';
  const flagDescription = row ? (ACTION_FLAG_DESCRIPTIONS[row.action_flag] ?? '') : '';

  return (
    <div
      className={`absolute top-0 right-0 z-30 h-full w-[380px] flex flex-col
                  transition-transform duration-300 ease-in-out ${
                    drawerOpen && row ? 'translate-x-0' : 'translate-x-full'
                  }`}
      style={{
        background: 'var(--glass-heavy)',
        backdropFilter: 'var(--blur-heavy)',
        WebkitBackdropFilter: 'var(--blur-heavy)',
        borderLeft: '1px solid var(--glass-border)',
        boxShadow: '-8px 0 32px rgba(0,0,0,0.3)',
      }}
    >
      {row && (
        <>
          {/* Header */}
          <div className="px-4 pt-4 pb-2">
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h2 className="text-sm font-semibold text-white truncate">{row.kek_name}</h2>
                <div className="text-[11px] text-zinc-500 mt-0.5">
                  {row.province} &middot; {row.grid_region_id}
                </div>
              </div>
              <button
                onClick={handleClose}
                className="p-1 rounded hover:bg-white/[0.06] transition-colors text-zinc-500 hover:text-zinc-300"
                aria-label="Close drawer"
              >
                <CloseIcon />
              </button>
            </div>

            {/* Action flag banner */}
            <div
              className="mt-3 px-3 py-2 rounded-md"
              style={{ background: `${flagColor}22`, border: `1px solid ${flagColor}44` }}
            >
              <div className="flex items-center gap-2">
                <span
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                  style={{ background: flagColor }}
                />
                <span className="text-xs font-medium" style={{ color: flagColor }}>
                  {flagLabel}
                </span>
              </div>
              {flagDescription && (
                <p className="text-[10px] text-zinc-400 mt-1 leading-relaxed pl-[18px]">
                  {flagDescription}
                </p>
              )}
            </div>
          </div>

          {/* Tabs */}
          <Tabs.Root defaultValue="info" className="flex-1 flex flex-col min-h-0">
            <Tabs.List
              className="flex px-4 gap-0.5"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
            >
              {TABS.map((tab) => (
                <Tabs.Trigger
                  key={tab.value}
                  value={tab.value}
                  className="px-2.5 py-2 text-[11px] font-medium text-zinc-500
                             hover:text-zinc-300 transition-colors relative
                             data-[state=active]:text-[#90CAF9]
                             after:absolute after:bottom-0 after:left-1 after:right-1 after:h-[2px]
                             after:rounded-full after:bg-[#90CAF9] after:opacity-0
                             data-[state=active]:after:opacity-100 after:transition-opacity"
                >
                  {tab.label}
                </Tabs.Trigger>
              ))}
            </Tabs.List>

            <div className="flex-1 overflow-y-auto px-4 py-3">
              <Tabs.Content value="info">
                <InfoTab row={row} />
              </Tabs.Content>
              <Tabs.Content value="resource">
                <ResourceTab row={row} substations={substations} loadingSubs={loadingSubs} />
              </Tabs.Content>
              <Tabs.Content value="lcoe">
                <LCOETab row={row} />
              </Tabs.Content>
              <Tabs.Content value="demand">
                <DemandTab row={row} />
              </Tabs.Content>
              <Tabs.Content value="pipeline">
                <PipelineTab row={row} />
              </Tabs.Content>
              <Tabs.Content value="flags">
                <FlagsTab row={row} />
              </Tabs.Content>
            </div>
          </Tabs.Root>
        </>
      )}
    </div>
  );
}

import { formatGridRegion, formatSnakeLabel } from '../../../lib/format';
import type { ScorecardRow, SubstationWithCosts, UserAssumptions } from '../../../lib/types';
import { useDashboardStore } from '../../../store/dashboard';
import Slider from '../../ui/Slider';
import SubstationComparison from '../../ui/SubstationComparison';
import { SectionHeader, StatCard, StatRow, StatRowWithTip } from './StatComponents';

const CAPACITY_COLORS: Record<string, string> = {
  green: '#4CAF50',
  yellow: '#FFC107',
  red: '#F44336',
  unknown: '#666',
};
const CAPACITY_LABELS: Record<string, string> = {
  green: 'Sufficient',
  yellow: 'Marginal',
  red: 'Upgrade needed',
  unknown: 'Unknown',
};

const RUPTL_PROJECT_LABELS: Record<string, string> = {
  uprate: 'Uprate',
  extension: 'Extension',
  line_bay: 'Line bay addition',
  new: 'New substation',
  other: 'Other',
};
const RUPTL_STATUS_LABELS: Record<string, string> = {
  konstruksi: 'Under construction',
  committed: 'Committed',
  pengadaan: 'In procurement',
  rencana: 'Planned',
  studi: 'Under study',
  other: 'Other',
};

const GEOTHERMAL_TIER_LABELS: Record<string, string> = {
  operating_within_50km: 'Operating PLTP within 50 km',
  operating_within_200km: 'Operating PLTP within 200 km',
  pipeline_within_200km_pre2030: 'RUPTL pipeline within 200 km (pre-2030)',
  pipeline_within_200km_post2030: 'RUPTL pipeline within 200 km (post-2030)',
  none: 'No reachable geothermal',
};
const GEOTHERMAL_TIER_COLORS: Record<string, string> = {
  operating_within_50km: '#4CAF50',
  operating_within_200km: '#8BC34A',
  pipeline_within_200km_pre2030: '#FFB300',
  pipeline_within_200km_post2030: '#9E9E9E',
  none: '#666',
};
const GEOTHERMAL_TIER_IMPLICATIONS: Record<string, string> = {
  operating_within_50km:
    'Scenario 6 (solar+geothermal+battery) viable today — supply blend layer fills ~30% of demand at $90/MWh.',
  operating_within_200km:
    'Reachable with new transmission. Supply blend layer fills ~15% of demand at $90/MWh.',
  pipeline_within_200km_pre2030:
    'Targets COD before 2030. Supply blend layer fills ~10% once online.',
  pipeline_within_200km_post2030:
    'COD after 2030 — does not relieve a 2030 decarbonization decision.',
  none: 'Solar + BESS or grid backfill only — no dispatchable RE layer.',
};

function GeothermalAdjacencyCard({ row }: { row: ScorecardRow }) {
  const tier = row.geothermal_adjacency_tier ?? 'none';
  const tierColor = GEOTHERMAL_TIER_COLORS[tier] ?? '#666';
  const tierLabel = GEOTHERMAL_TIER_LABELS[tier] ?? 'Unknown';
  const showOperating =
    tier === 'operating_within_50km' || tier === 'operating_within_200km';
  const showPipeline =
    tier === 'pipeline_within_200km_pre2030' || tier === 'pipeline_within_200km_post2030';

  return (
    <StatCard>
      <SectionHeader
        title="Geothermal Adjacency"
        subtitle="Dispatchable RE feeds the Supply Blend (delivered cost) cascade for sites within reach."
      />
      <div className="flex items-center gap-2 py-1">
        <span
          style={{
            display: 'inline-block',
            width: 8,
            height: 8,
            borderRadius: 999,
            background: tierColor,
            flexShrink: 0,
          }}
        />
        <span style={{ fontSize: 11, color: 'var(--text-primary)' }}>{tierLabel}</span>
      </div>
      <div
        style={{
          fontSize: 10,
          lineHeight: 1.5,
          color: 'var(--text-secondary)',
          marginBottom: 4,
        }}
      >
        {GEOTHERMAL_TIER_IMPLICATIONS[tier] ?? ''}
      </div>
      {showOperating && row.nearest_geothermal_operating_id && (
        <>
          <StatRow
            label="Nearest PLTP"
            value={formatSnakeLabel(row.nearest_geothermal_operating_id.replace(/^pltp_/, ''))}
          />
          <StatRow
            label="Distance"
            value={row.nearest_geothermal_operating_km?.toFixed(1)}
            unit="km"
          />
          {row.nearest_geothermal_operating_mw != null && (
            <StatRow label="Plant capacity" value={row.nearest_geothermal_operating_mw} unit="MW" />
          )}
          {row.nearest_geothermal_operating_emission_factor_g_per_kwh != null && (
            <StatRowWithTip
              label="NCG emissions"
              value={row.nearest_geothermal_operating_emission_factor_g_per_kwh}
              unit="g CO₂/kWh"
              tip="Per-plant non-condensable-gas emission factor from ESDM 2024. Geothermal isn't truly zero-carbon — Indonesian PLTPs run 42–73 g/kWh (vs ~0 for solar)."
            />
          )}
        </>
      )}
      {showPipeline && row.nearest_geothermal_pipeline_id && (
        <>
          <StatRow
            label="Nearest pipeline project"
            value={formatSnakeLabel(row.nearest_geothermal_pipeline_id.replace(/^pipeline_/, ''))}
          />
          <StatRow
            label="Distance"
            value={row.nearest_geothermal_pipeline_km?.toFixed(1)}
            unit="km"
          />
          {row.nearest_geothermal_pipeline_mw != null && (
            <StatRow label="Planned capacity" value={row.nearest_geothermal_pipeline_mw} unit="MW" />
          )}
          {row.nearest_geothermal_pipeline_target_year != null && (
            <StatRow
              label="Target COD"
              value={String(row.nearest_geothermal_pipeline_target_year)}
            />
          )}
        </>
      )}
    </StatCard>
  );
}

export function GridTab({
  row,
  substations,
  loadingSubs,
}: {
  row: ScorecardRow;
  substations: SubstationWithCosts[];
  loadingSubs: boolean;
}) {
  const assumptions = useDashboardStore((s) => s.assumptions);
  const setAssumptions = useDashboardStore((s) => s.setAssumptions);
  const sliderConfigs = useDashboardStore((s) => s.sliderConfigs);
  const meaningfulShareConfig = sliderConfigs?.tier2?.meaningful_share_pct;
  const wbBuildoutConfig = sliderConfigs?.tier2?.wb_buildout_footprint_ratio;
  const cap = row.capacity_assessment ?? 'unknown';
  const nearest = substations.find((s) => s.is_nearest);
  const isWithinBoundary = row.grid_integration_category === 'within_boundary';
  const wbCoveragePct =
    row.within_boundary_coverage_pct != null ? row.within_boundary_coverage_pct * 100 : null;
  const wbCoverageEffectivePct =
    row.within_boundary_coverage_effective_pct != null
      ? row.within_boundary_coverage_effective_pct * 100
      : null;
  // v4.0.5 (methodology #40): include hard_max so the coverage panel + slider
  // show at industrial sites where the strict raster baseline is 0. The slider
  // can dial soft-excluded coverage back in via the override math at grid.py:112.
  const hasWbCoverage =
    (row.within_boundary_coverage_pct != null && row.within_boundary_coverage_pct > 0) ||
    (row.within_boundary_coverage_hard_max_pct != null &&
      row.within_boundary_coverage_hard_max_pct > 0);

  return (
    <>
      <StatCard>
        <SectionHeader
          title="Grid Integration"
          subtitle="Is existing infrastructure ready for solar, or does it need upgrades?"
          tip="How ready is the grid for solar at this KEK. Determines what investment is needed to connect."
        />
        {isWithinBoundary && (
          <div
            className="mb-3 p-2 rounded text-[10px] leading-relaxed"
            style={{
              background: 'rgba(76, 175, 80, 0.08)',
              border: '1px solid rgba(76, 175, 80, 0.25)',
              color: 'var(--text-value)',
            }}
          >
            <div className="font-medium mb-0.5" style={{ color: '#66BB6A' }}>
              Covered on-site — no grid infrastructure required
            </div>
            {wbCoveragePct != null && wbCoverageEffectivePct != null && assumptions && (
              <>
                Raster baseline covers <strong>{wbCoveragePct.toFixed(0)}%</strong> of 2030 demand.
                With the{' '}
                <strong>{(assumptions.wb_buildout_footprint_ratio * 100).toFixed(0)}%</strong>{' '}
                land-use override (fraction of soft-excluded land treated as deployable), effective
                coverage is <strong>{wbCoverageEffectivePct.toFixed(0)}%</strong> — above the{' '}
                <strong>{(assumptions.meaningful_share_pct * 100).toFixed(0)}%</strong> meaningful
                share threshold. Gen-tie, new transmission, and substation upgrade costs are all
                zero: the project is self-contained.
              </>
            )}
            {wbBuildoutConfig && assumptions && (
              <div className="mt-2">
                <Slider
                  value={assumptions.wb_buildout_footprint_ratio}
                  onChange={(v) =>
                    setAssumptions({ wb_buildout_footprint_ratio: v } as Partial<UserAssumptions>)
                  }
                  min={wbBuildoutConfig.min}
                  max={wbBuildoutConfig.max}
                  step={wbBuildoutConfig.step}
                  label={wbBuildoutConfig.label}
                  unit={wbBuildoutConfig.unit}
                  description={wbBuildoutConfig.description}
                />
              </div>
            )}
          </div>
        )}
        {!isWithinBoundary && hasWbCoverage && wbBuildoutConfig && assumptions && (
          <div
            className="mb-3 p-2 rounded text-[10px] leading-relaxed"
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-value)',
            }}
          >
            <div className="font-medium mb-0.5" style={{ color: 'var(--text-muted)' }}>
              On-site solar below self-sufficiency threshold
            </div>
            {wbCoveragePct != null && wbCoverageEffectivePct != null && assumptions && (
              <>
                Raster baseline covers <strong>{wbCoveragePct.toFixed(0)}%</strong> of demand. With
                the <strong>{(assumptions.wb_buildout_footprint_ratio * 100).toFixed(0)}%</strong>{' '}
                land-use override (fraction of soft-excluded land treated as deployable), effective
                coverage is <strong>{wbCoverageEffectivePct.toFixed(0)}%</strong> — below the{' '}
                <strong>{(assumptions.meaningful_share_pct * 100).toFixed(0)}%</strong> threshold,
                so grid infrastructure still applies.
              </>
            )}
            <div className="mt-2">
              <Slider
                value={assumptions.wb_buildout_footprint_ratio}
                onChange={(v) =>
                  setAssumptions({ wb_buildout_footprint_ratio: v } as Partial<UserAssumptions>)
                }
                min={wbBuildoutConfig.min}
                max={wbBuildoutConfig.max}
                step={wbBuildoutConfig.step}
                label={wbBuildoutConfig.label}
                unit={wbBuildoutConfig.unit}
                description={wbBuildoutConfig.description}
              />
            </div>
          </div>
        )}
        <StatRowWithTip
          label="Category"
          value={formatSnakeLabel(row.grid_integration_category) ?? 'N/A'}
          tip="within_boundary = on-site solar covers demand. grid_ready = substation nearby. invest_transmission = build line from sub to site. invest_substation = build sub near solar. grid_first = major grid expansion needed."
        />
        <StatRowWithTip
          label="Grid Upgrade Planned"
          value={
            row.grid_upgrade_planned != null ? (row.grid_upgrade_planned ? 'Yes' : 'No') : 'N/A'
          }
          tip="Whether RUPTL includes grid capacity additions in this region before 2030. 'No' + competitive solar = 'grid_first' flag."
        />
        <StatRow label="Grid Region" value={formatGridRegion(row.grid_region_id)} />
      </StatCard>

      <StatCard>
        <SectionHeader
          title="Substation Proximity"
          subtitle="How far does power need to travel from solar site to KEK?"
        />
        {loadingSubs ? (
          <div className="text-[11px] py-2 text-center" style={{ color: 'var(--text-muted)' }}>
            Loading substations...
          </div>
        ) : nearest ? (
          <>
            <StatRow label="Nearest Sub" value={nearest.name} />
            <StatRow label="KEK-Sub Distance" value={nearest.dist_km.toFixed(1)} unit="km" />
          </>
        ) : (
          <StatRow label="Nearest Sub" value="N/A" />
        )}
        <StatRowWithTip
          label="Solar-Sub Distance"
          value={row.dist_solar_to_nearest_substation_km?.toFixed(1)}
          unit="km"
          tip="Distance from the chosen solar patch to the nearest substation. Drives gen-tie connection cost ($5/kW per km + $80/kW fixed)."
        />
      </StatCard>

      {row.solar_search_method && (
        <StatCard>
          <SectionHeader
            title="Solar Site Selection"
            subtitle="How was the best solar patch within 50km chosen?"
            tip="V3.7 anchored search: ranks candidate patches by LCOE including gen-tie cost instead of raw PVOUT, so small PVOUT deltas don't override large connection-cost savings."
          />
          <StatRowWithTip
            label="Search Method"
            value={
              row.solar_search_method === 'substation_anchored'
                ? 'Anchored to substation'
                : 'Best PVOUT (fallback)'
            }
            tip="'Anchored' = a buildable patch within 10km of an existing substation met the 30% demand-coverage floor and beat other candidates on all-in LCOE. 'Fallback' = no nearby patch qualified, reverted to pure PVOUT argmax."
          />
          {row.chosen_anchor_substation_name && (
            <StatRow label="Anchor Substation" value={row.chosen_anchor_substation_name} />
          )}
          {row.project_scale_solar_mwp != null && (
            <StatRowWithTip
              label="Project Scale"
              value={row.project_scale_solar_mwp.toFixed(1)}
              unit="MWp"
              tip="Project-scale solar capacity = min(required_mwp, max_buildable). This is what actually gets built to cover site demand, not the full buildable area."
            />
          )}
          {row.solar_delivered_share_pct != null && (
            <StatRowWithTip
              label="Demand Coverage"
              value={(row.solar_delivered_share_pct * 100).toFixed(0)}
              unit="%"
              tip="Share of annual site demand (2030) that the anchored patch can deliver, accounting for capacity factor. Supply share (nameplate) is {row.solar_supply_share_pct}."
            />
          )}
          {row.nearest_substation_capacity_source &&
            row.nearest_substation_capacity_source !== 'actual' && (
              <StatRowWithTip
                label="Capacity Source"
                value={formatSnakeLabel(row.nearest_substation_capacity_source) ?? 'N/A'}
                tip="PLN kapgi (nameplate MVA) was missing for this substation. Used voltage-class proxy × 30% availability as a conservative upper bound."
              />
            )}
        </StatCard>
      )}

      <StatCard>
        <SectionHeader
          title="Grid Connectivity"
          subtitle="Is there an existing transmission path between key substations?"
          tip="Whether existing PLN transmission lines connect the substations near the KEK and the solar site."
        />
        <StatRowWithTip
          label="Transmission Line"
          value={row.line_connected != null ? (row.line_connected ? 'Connected' : 'None') : 'N/A'}
          tip="Whether a PLN transmission line geometrically connects the KEK-nearest and solar-nearest substations. 'None' means new line may be needed."
        />
        <StatRow
          label="Same PLN Region"
          value={row.same_grid_region != null ? (row.same_grid_region ? 'Yes' : 'No') : 'N/A'}
        />
        {row.inter_substation_dist_km != null && (
          <StatRowWithTip
            label="Inter-Sub Distance"
            value={row.inter_substation_dist_km.toFixed(1)}
            unit="km"
            tip="Distance between the KEK's nearest substation and the solar site's nearest substation. Drives new transmission line cost if not already connected."
          />
        )}
      </StatCard>

      {assumptions && (
        <StatCard>
          <SectionHeader
            title="Substation Capacity"
            subtitle="Can the local substation absorb new solar output without upgrades?"
            tip="Can the nearest substation handle the solar output? Green = sufficient headroom. Red = upgrade needed."
          />
          {row.substation_utilization_pct_effective != null && (
            <div
              className="mb-3 p-2 rounded text-[10px] leading-relaxed"
              style={{
                background: row.ruptl_project_type
                  ? 'rgba(33, 150, 243, 0.08)'
                  : 'rgba(255, 255, 255, 0.03)',
                border: row.ruptl_project_type
                  ? '1px solid rgba(33, 150, 243, 0.25)'
                  : '1px solid var(--glass-border-bright)',
                color: 'var(--text-value)',
              }}
            >
              <div
                className="font-medium mb-0.5"
                style={{ color: row.ruptl_project_type ? '#64B5F6' : 'var(--text-muted)' }}
              >
                Utilization default {(row.substation_utilization_pct_effective * 100).toFixed(0)}%
              </div>
              {row.ruptl_project_type ? (
                <>
                  PLN RUPTL plans a{' '}
                  <strong>
                    {RUPTL_PROJECT_LABELS[row.ruptl_project_type] ?? row.ruptl_project_type}
                  </strong>
                  {row.ruptl_mva_added_total != null && row.ruptl_mva_added_total > 0 && (
                    <>
                      {' '}
                      adding <strong>+{row.ruptl_mva_added_total.toFixed(0)} MVA</strong>
                    </>
                  )}
                  {row.ruptl_earliest_target_year != null && (
                    <>
                      {' '}
                      by <strong>{row.ruptl_earliest_target_year}</strong>
                    </>
                  )}
                  {row.ruptl_strongest_status && (
                    <>
                      {' '}
                      (
                      {RUPTL_STATUS_LABELS[row.ruptl_strongest_status] ??
                        row.ruptl_strongest_status}
                      )
                    </>
                  )}
                  . PLN only plans upgrades on capacity-constrained assets, so we default to{' '}
                  {(row.substation_utilization_pct_effective * 100).toFixed(0)}% utilization for
                  this site (vs. the 65% fleet average).
                </>
              ) : row.nearest_substation_capacity_source &&
                row.nearest_substation_capacity_source.startsWith('proxy_') ? (
                <>
                  No nameplate MVA published for this substation. Used a voltage-class proxy with a
                  conservative 30% availability allowance.
                </>
              ) : (
                <>
                  No RUPTL upgrade plan matched this substation — using the fleet-average
                  utilization (65%). Override via the global Substation utilization slider in the
                  Assumptions panel if you have local intel.
                </>
              )}
            </div>
          )}
          {meaningfulShareConfig && (
            <div className="mt-3">
              <Slider
                value={assumptions.meaningful_share_pct}
                onChange={(v) =>
                  setAssumptions({ meaningful_share_pct: v } as Partial<UserAssumptions>)
                }
                min={meaningfulShareConfig.min}
                max={meaningfulShareConfig.max}
                step={meaningfulShareConfig.step}
                label={meaningfulShareConfig.label}
                unit={meaningfulShareConfig.unit}
                description={meaningfulShareConfig.description}
              />
            </div>
          )}
          <div className="flex items-center gap-2 mt-1">
            <span
              className="inline-block w-2.5 h-2.5 rounded-full"
              style={{ backgroundColor: CAPACITY_COLORS[cap] }}
            />
            <span className="text-xs" style={{ color: 'var(--text-value)' }}>
              {CAPACITY_LABELS[cap]}
            </span>
          </div>
          <StatRow
            label="Available Capacity"
            value={
              row.available_capacity_mva != null ? row.available_capacity_mva.toFixed(1) : 'N/A'
            }
            unit="MVA"
          />
          {(cap === 'red' || cap === 'yellow') &&
            row.project_scale_solar_mwp != null &&
            row.available_capacity_mva != null && (
              <div
                className="mt-2 p-2 rounded text-[10px] leading-relaxed"
                style={{
                  background: 'rgba(244, 67, 54, 0.08)',
                  border: '1px solid rgba(244, 67, 54, 0.25)',
                  color: 'var(--text-value)',
                }}
              >
                <div className="font-medium mb-0.5" style={{ color: CAPACITY_COLORS[cap] }}>
                  Why upgrade?
                </div>
                At{' '}
                <strong>
                  {(assumptions.meaningful_share_pct * 100).toFixed(0)}% meaningful share
                </strong>
                , project sizes to <strong>{row.project_scale_solar_mwp.toFixed(0)} MWp</strong>{' '}
                solar, but the anchor substation has only{' '}
                <strong>{(row.available_capacity_mva * 0.85).toFixed(0)} MW</strong> of free
                throughput ({row.available_capacity_mva.toFixed(0)} MVA × 0.85 power factor).
                Transformers need uprating — not a new substation — to absorb the surplus.
                {row.substation_upgrade_cost_per_kw != null &&
                  row.substation_upgrade_cost_per_kw > 0 && (
                    <>
                      {' '}
                      Deficit shows up as{' '}
                      <strong>${row.substation_upgrade_cost_per_kw.toFixed(0)}/kW</strong> of uprate
                      cost below.
                    </>
                  )}
                <div className="mt-1 opacity-80">
                  Lower the meaningful-share slider above to shrink the project and see if the flag
                  flips to Grid Ready.
                </div>
              </div>
            )}
        </StatCard>
      )}

      {!isWithinBoundary &&
        (row.connection_cost_per_kw != null ||
          row.transmission_cost_per_kw != null ||
          row.substation_upgrade_cost_per_kw != null ||
          row.grid_investment_needed_usd != null) && (
          <StatCard>
            <SectionHeader
              title="Connection Costs"
              subtitle="What does it cost to connect solar to the grid here?"
              tip="Estimated infrastructure cost to connect solar to the KEK. Scales with project capacity (MWp)."
            />
            {row.connection_cost_per_kw != null && (
              <StatRowWithTip
                label="Gen-Tie Cost"
                value={row.connection_cost_per_kw.toFixed(0)}
                unit="$/kW"
                tip="Cost to connect the solar farm to the nearest substation. Formula: distance x $5/kW-km + $80/kW fixed."
              />
            )}
            {row.transmission_cost_per_kw != null && row.transmission_cost_per_kw > 0 && (
              <StatRowWithTip
                label="New Line Cost"
                value={row.transmission_cost_per_kw.toFixed(0)}
                unit="$/kW"
                tip="Cost to build a new transmission line between substations. Only applies when KEK-nearest and solar-nearest substations are not already connected."
              />
            )}
            {row.substation_upgrade_cost_per_kw != null &&
              row.substation_upgrade_cost_per_kw > 0 && (
                <StatRow
                  label="Sub Upgrade Cost"
                  value={row.substation_upgrade_cost_per_kw.toFixed(0)}
                  unit="$/kW"
                />
              )}
            {row.grid_investment_needed_usd != null && (
              <StatRowWithTip
                label="Total Grid Investment"
                value={`$${(row.grid_investment_needed_usd / 1_000_000).toFixed(1)}M`}
                tip="Estimated total: gen-tie + new transmission line + substation upgrade. This is the infrastructure price tag for connecting solar to this KEK."
              />
            )}
          </StatCard>
        )}

      {substations.length > 1 && <SubstationComparison substations={substations} />}

      {/* F2: Geothermal adjacency — drives the dispatchable-RE layer in the
          Supply Blend cascade (METHODOLOGY §5.4). Visible on every site so
          users can see "no reachable geothermal" too — that absence is signal. */}
      <GeothermalAdjacencyCard row={row} />
    </>
  );
}

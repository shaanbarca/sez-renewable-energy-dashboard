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
  const utilizationConfig = sliderConfigs?.tier2?.substation_utilization_pct;
  const cap = row.capacity_assessment ?? 'unknown';
  const nearest = substations.find((s) => s.is_nearest);

  return (
    <>
      <StatCard>
        <SectionHeader
          title="Grid Integration"
          subtitle="Is existing infrastructure ready for solar, or does it need upgrades?"
          tip="How ready is the grid for solar at this KEK. Determines what investment is needed to connect."
        />
        <StatRowWithTip
          label="Category"
          value={formatSnakeLabel(row.grid_integration_category) ?? 'N/A'}
          tip="within_boundary = solar inside KEK. grid_ready = substation nearby. invest_transmission = build line from sub to KEK. invest_substation = build sub near solar. grid_first = major grid expansion needed."
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
          tip="Distance from the best solar site to the nearest substation. Drives gen-tie connection cost ($5/kW per km + $80/kW fixed)."
        />
      </StatCard>

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

      {utilizationConfig && assumptions && (
        <StatCard>
          <SectionHeader
            title="Substation Capacity"
            subtitle="Can the local substation absorb new solar output without upgrades?"
            tip="Can the nearest substation handle the solar output? Green = sufficient headroom. Red = upgrade needed."
          />
          <Slider
            value={assumptions.substation_utilization_pct}
            onChange={(v) =>
              setAssumptions({ substation_utilization_pct: v } as Partial<UserAssumptions>)
            }
            min={utilizationConfig.min}
            max={utilizationConfig.max}
            step={utilizationConfig.step}
            label={utilizationConfig.label}
            unit={utilizationConfig.unit}
            description={utilizationConfig.description}
          />
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
          <div className="mt-1 text-[9px] text-[var(--text-muted)] leading-relaxed">
            Applies to all KEKs. Actual utilization requires PLN grid study.
          </div>
        </StatCard>
      )}

      {(row.connection_cost_per_kw != null ||
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
          {row.substation_upgrade_cost_per_kw != null && row.substation_upgrade_cost_per_kw > 0 && (
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
    </>
  );
}

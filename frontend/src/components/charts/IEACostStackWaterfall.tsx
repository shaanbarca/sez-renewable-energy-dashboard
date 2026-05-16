/**
 * IEACostStackWaterfall — inline Recharts waterfall showing the IEA-aligned
 * 4-tier LCOE cost ladder (Generation → Delivered → Firm 4h → Firm 8h).
 *
 * Per /plan-design-review on docs/refinement/v4_1_iea_cost_stack_ui_proposal.md:
 *   - Replaces the numeric "Solar LCOE / Grid Cost" rows in OverviewTab's
 *     "At a Glance" StatCard — waterfall IS the cost section.
 *   - Reuses Recharts (already in stack via LcoeWaterfallModal); inherits
 *     that file's waterfall data shape + tooltip pattern.
 *   - Single canonical IEA vocabulary; no dual labels.
 *
 * Empty-state fallback: when `lcoe_generation_usd_mwh` is null but legacy
 * `lcoe_mid_usd_mwh` is populated (older / wind-only sites), renders a
 * degraded waterfall with one bar at lcoe_mid + "[est]" badge. Tooltip
 * explains why it's not the full IEA stack.
 *
 * Tier meaning (METHODOLOGY §18.6):
 *   - Tier 1 Generation: on-site only, no transmission, no storage.
 *     NREL ATB-aligned.
 *   - Tier 2 Full System (Delivered): + gen-tie + connection cost.
 *     The PPA-relevant number for grid-connected solar IPPs.
 *   - Tier 3 Full System Firm 4h: + 4h battery storage adder.
 *     Adjusted for peaking-gas equivalence.
 *   - Tier 4 Full System Firm 8h: + 8h battery storage adder.
 *     Adjusted for baseload captive coal equivalence.
 */

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ScorecardRow } from '../../lib/types';

interface TierDatum {
  /** Short tick label below each bar */
  name: string;
  /** Full tier label for the tooltip header */
  fullLabel: string;
  /** Recharts stacked-bar range [base, top]. base = sum of prior tier deltas. */
  range: [number, number];
  /** Cumulative tier value, $/MWh */
  value: number;
  /** Delta from the previous tier (or absolute for tier 1) */
  delta: number;
  /** IEA definition for the tooltip body */
  description: string;
  /** Bar fill — distinct per tier so the deltas read as additive layers */
  color: string;
}

const TIER_COLORS = {
  generation: '#4CAF50',  // green — base solar cost
  delivered: '#42A5F5',   // blue — adds transmission
  firm4h: '#AB47BC',      // purple — adds 4h storage
  firm8h: '#7E57C2',      // deeper purple — adds 8h storage
  estimated: '#78909C',   // grey — legacy lcoe_mid fallback
  incumbent: '#EF5350',   // red — incumbent reference line
};

interface IEACostStackWaterfallProps {
  row: ScorecardRow;
  /** Height of the chart inline (default 200px — compact for drawer). */
  height?: number;
}

function buildTiers(row: ScorecardRow): {
  tiers: TierDatum[];
  isEstimated: boolean;
} {
  const gen = row.lcoe_generation_usd_mwh;
  const delivered = row.full_system_lcoe_delivered_usd_mwh;
  const firm4h = row.full_system_lcoe_firm_4h_usd_mwh;
  const firm8h = row.full_system_lcoe_firm_8h_usd_mwh;

  const hasFullStack = gen != null && delivered != null && firm4h != null && firm8h != null;

  if (!hasFullStack) {
    // Empty-state fallback: legacy lcoe_mid as a single Tier-2 estimate
    // (lcoe_mid most closely tracks Full System Delivered in the v4.0 model).
    const lcoeMid = row.lcoe_mid_usd_mwh;
    if (lcoeMid == null) return { tiers: [], isEstimated: true };
    return {
      isEstimated: true,
      tiers: [
        {
          name: 'Est. LCOE',
          fullLabel: 'Estimated LCOE (legacy)',
          range: [0, lcoeMid],
          value: lcoeMid,
          delta: lcoeMid,
          description:
            'IEA cost stack not fully populated for this site. Showing the legacy `lcoe_mid_usd_mwh` value as a single estimate. Full Generation → Delivered → Firm 4h → Firm 8h breakdown will land when the next pipeline regen completes.',
          color: TIER_COLORS.estimated,
        },
      ],
    };
  }

  // Full IEA stack. Each bar's range is [prior-tier-value, this-tier-value]
  // so Recharts renders them as additive deltas climbing the ladder.
  return {
    isEstimated: false,
    tiers: [
      {
        name: 'Gen',
        fullLabel: 'Tier 1 — Generation',
        range: [0, gen],
        value: gen,
        delta: gen,
        description:
          'On-site LCOE only. No transmission, no storage. NREL ATB-aligned. The raw cost to generate a MWh of solar at this site.',
        color: TIER_COLORS.generation,
      },
      {
        name: 'Delivered',
        fullLabel: 'Tier 2 — Full System (Delivered)',
        range: [gen, delivered],
        value: delivered,
        delta: delivered - gen,
        description:
          'Generation + gen-tie + connection cost. The PPA-relevant number for grid-connected solar IPPs.',
        color: TIER_COLORS.delivered,
      },
      {
        name: 'Firm 4h',
        fullLabel: 'Tier 3 — Full System Firm 4h',
        range: [delivered, firm4h],
        value: firm4h,
        delta: firm4h - delivered,
        description:
          'Delivered + 4h battery storage adder. Adjusted for peaking-gas equivalence (LCOS × 0.20 storage share).',
        color: TIER_COLORS.firm4h,
      },
      {
        name: 'Firm 8h',
        fullLabel: 'Tier 4 — Full System Firm 8h',
        range: [firm4h, firm8h],
        value: firm8h,
        delta: firm8h - firm4h,
        description:
          'Firm 4h + an additional 4h of storage (LCOS × 0.50 storage share). Adjusted for baseload captive coal equivalence.',
        color: TIER_COLORS.firm8h,
      },
    ],
  };
}

function TierTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload?: TierDatum }[];
}) {
  if (!active || !payload?.[0]?.payload) return null;
  const d = payload[0].payload;
  return (
    <div
      className="rounded px-3 py-2 text-[11px] max-w-[260px]"
      style={{
        background: 'rgba(24, 24, 28, 0.96)',
        border: '1px solid rgba(255,255,255,0.12)',
        boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
        color: 'rgb(244, 244, 245)',
      }}
    >
      <div className="font-medium mb-0.5" style={{ color: d.color }}>
        {d.fullLabel}
      </div>
      <div className="tabular-nums">
        <span style={{ color: d.color }}>${d.value.toFixed(0)}/MWh</span>
        {d.delta > 0 && d.delta < d.value && (
          <span className="text-zinc-500 ml-2">(+${d.delta.toFixed(0)} vs prior tier)</span>
        )}
      </div>
      <div className="text-[10px] mt-1" style={{ color: 'rgb(161, 161, 170)' }}>
        {d.description}
      </div>
    </div>
  );
}

export default function IEACostStackWaterfall({ row, height = 200 }: IEACostStackWaterfallProps) {
  const { tiers, isEstimated } = buildTiers(row);

  if (tiers.length === 0) {
    return (
      <div
        className="text-[11px] py-4 px-3 rounded"
        style={{ color: 'var(--text-muted)', background: 'var(--card-bg)' }}
      >
        IEA cost stack not available — no LCOE data for this site.
      </div>
    );
  }

  const top = tiers[tiers.length - 1].value;
  // Incumbent reference line — the price this site actually compares against,
  // surfaced by M-AT8b's effective_incumbent_lcoe.
  const incumbent =
    (row.effective_incumbent_lcoe_usd_mwh ?? row.grid_cost_usd_mwh) || null;
  const rawMax = Math.max(top, incumbent ?? 0) * 1.15;
  const tickStep = rawMax > 400 ? 100 : rawMax > 200 ? 50 : rawMax > 100 ? 25 : 10;
  const yMax = Math.ceil(rawMax / tickStep) * tickStep;
  const yTicks: number[] = [];
  for (let v = 0; v <= yMax; v += tickStep) yTicks.push(v);

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <div className="text-[11px] font-medium" style={{ color: 'var(--text-muted)' }}>
          IEA Cost Stack
          {isEstimated && (
            <span
              className="ml-2 text-[9px] px-1.5 py-0.5 rounded"
              style={{
                background: `${TIER_COLORS.estimated}22`,
                color: TIER_COLORS.estimated,
                border: `1px solid ${TIER_COLORS.estimated}55`,
              }}
              title="Site is missing the per-tier IEA columns. Falling back to legacy lcoe_mid as a single Tier-2 estimate. Full stack will populate on next pipeline regen."
            >
              [est]
            </span>
          )}
        </div>
        <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
          $/MWh
        </span>
      </div>
      <div style={{ width: '100%', height }}>
        <ResponsiveContainer>
          <BarChart
            data={tiers}
            margin={{ top: 8, right: 8, left: 0, bottom: 24 }}
            barCategoryGap="10%"
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="name"
              tick={{ fill: 'rgb(161, 161, 170)', fontSize: 10 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: 'rgb(161, 161, 170)', fontSize: 9 }}
              axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
              tickLine={false}
              width={32}
              ticks={yTicks}
              domain={[0, yMax]}
            />
            <Tooltip content={<TierTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
            {incumbent != null && incumbent > 0 && (
              <ReferenceLine
                y={incumbent}
                stroke={TIER_COLORS.incumbent}
                strokeDasharray="4 3"
                strokeWidth={1.5}
                label={{
                  value: `Incumbent $${incumbent.toFixed(0)}`,
                  fill: TIER_COLORS.incumbent,
                  fontSize: 9,
                  position: 'right',
                }}
              />
            )}
            <Bar dataKey="range" radius={[2, 2, 0, 0]}>
              {tiers.map((t) => (
                <Cell key={t.name} fill={t.color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      {!isEstimated && (
        <div
          className="text-[10px] mt-1 flex justify-between tabular-nums px-1"
          style={{ color: 'var(--text-muted)' }}
        >
          {tiers.map((t) => (
            <span key={t.name} style={{ color: t.color }}>
              ${t.value.toFixed(0)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

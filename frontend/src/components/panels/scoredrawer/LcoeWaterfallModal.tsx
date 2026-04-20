import { useCallback, useEffect } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { INFRA_READINESS_COLORS, INFRA_READINESS_LABELS } from '../../../lib/constants';
import type { InfrastructureReadiness, ScorecardRow } from '../../../lib/types';

function InfraBadge({ category }: { category: string }) {
  const key = category as InfrastructureReadiness;
  const raw = INFRA_READINESS_COLORS[key];
  const color = !raw || raw === 'transparent' ? '#4CAF50' : raw;
  const label = INFRA_READINESS_LABELS[key] ?? category;
  return (
    <span
      className="inline-flex items-center text-[10px] px-1.5 py-0.5 rounded-full font-medium"
      style={{
        backgroundColor: `${color}22`,
        color,
        border: `1px solid ${color}44`,
      }}
    >
      {label}
    </span>
  );
}

const DEGRADATION_ANNUAL_PCT = 0.5;

function capitalRecoveryFactor(wacc: number, lifetime: number): number {
  if (wacc <= 0) return 1 / lifetime;
  const factor = (1 + wacc) ** lifetime;
  return (wacc * factor) / (factor - 1);
}

interface Component {
  label: string;
  description: string;
  usdPerMwh: number;
  color: string;
}

interface WaterfallDatum {
  name: string;
  range: [number, number];
  value: number;
  description: string;
  color: string;
  isTotal: boolean;
}

interface LcoeWaterfallModalProps {
  open: boolean;
  onClose: () => void;
  row: ScorecardRow;
}

const COMPONENT_COLORS = {
  capex: '#4C8DFF',
  fom: '#8B5CF6',
  land: '#A16207',
  connection: '#0288D1',
  transmission: '#00838F',
  upgrade: '#EF6C00',
  total: '#22C55E',
};

function computeWaterfallData(components: Component[]): WaterfallDatum[] {
  let running = 0;
  const rows: WaterfallDatum[] = components.map((c) => {
    const start = running;
    const end = running + c.usdPerMwh;
    running = end;
    return {
      name: c.label,
      range: [start, end],
      value: c.usdPerMwh,
      description: c.description,
      color: c.color,
      isTotal: false,
    };
  });
  rows.push({
    name: 'Total',
    range: [0, running],
    value: running,
    description: 'Sum of annuitised components',
    color: COMPONENT_COLORS.total,
    isTotal: true,
  });
  return rows;
}

function WaterfallTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload?: WaterfallDatum }[];
}) {
  if (!active || !payload?.[0]?.payload) return null;
  const d = payload[0].payload;
  return (
    <div
      className="rounded px-3 py-2 text-[11px]"
      style={{
        background: 'rgba(24, 24, 28, 0.96)',
        border: '1px solid rgba(255,255,255,0.12)',
        boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
        color: 'rgb(244, 244, 245)',
      }}
    >
      <div className="font-medium mb-0.5" style={{ color: d.color }}>
        {d.name}
      </div>
      <div className="tabular-nums">${d.value.toFixed(1)}/MWh</div>
      <div className="text-[10px] mt-0.5" style={{ color: 'rgb(161, 161, 170)' }}>
        {d.description}
      </div>
    </div>
  );
}

export function LcoeWaterfallModal({ open, onClose, row }: LcoeWaterfallModalProps) {
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) onClose();
    },
    [onClose],
  );

  if (!open) return null;

  const capex = row.capex_usd_per_kw;
  const wacc = row.wacc_pct != null ? row.wacc_pct / 100 : null;
  const lifetime = row.lifetime_yr;
  const fom = row.fom_usd_per_kw_yr;
  const cf = row.primary_cf;
  const lcoeDisplayed = row.lcoe_mid_usd_mwh;
  const category = row.grid_integration_category ?? null;

  const canCompute =
    capex != null &&
    wacc != null &&
    lifetime != null &&
    lifetime > 0 &&
    fom != null &&
    cf != null &&
    cf > 0;

  if (!canCompute) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center"
        onClick={handleBackdropClick}
        style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}
      >
        <div
          className="relative w-full max-w-md rounded-2xl p-6"
          style={{
            background: 'rgba(24, 24, 28, 0.92)',
            border: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          <h2 className="text-lg font-semibold text-white mb-2">LCOE Breakdown</h2>
          <p className="text-sm text-zinc-400">
            Not enough data to compute the LCOE waterfall for this site.
          </p>
          <button
            type="button"
            onClick={onClose}
            className="mt-4 text-sm text-zinc-400 hover:text-white underline cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  const crf = capitalRecoveryFactor(wacc, lifetime);
  const degFactor = 1 - (DEGRADATION_ANNUAL_PCT / 100) * lifetime * 0.5;
  const annualMwhPerKw = (cf * 8760 * degFactor) / 1000;

  const perKwToPerMwh = (costPerKw: number, annualised: boolean) =>
    annualised ? costPerKw / annualMwhPerKw : (costPerKw * crf) / annualMwhPerKw;

  const isWithinBoundary = category === 'within_boundary';
  const includeConnection =
    category === 'grid_ready' ||
    category === 'invest_transmission' ||
    category === 'invest_substation' ||
    category === 'grid_first';
  const includeTransmission = category === 'invest_transmission' || category === 'grid_first';
  const includeUpgrade = category === 'invest_substation' || category === 'grid_first';

  const components: Component[] = [
    {
      label: 'CAPEX',
      description: `${capex.toFixed(0)} $/kW × CRF ${crf.toFixed(4)}`,
      usdPerMwh: perKwToPerMwh(capex, false),
      color: COMPONENT_COLORS.capex,
    },
    {
      label: 'Fixed O&M',
      description: `${fom.toFixed(1)} $/kW-yr annualised`,
      usdPerMwh: perKwToPerMwh(fom, true),
      color: COMPONENT_COLORS.fom,
    },
  ];

  if (!isWithinBoundary && row.land_cost_usd_per_kw != null && row.land_cost_usd_per_kw > 0) {
    components.push({
      label: 'Land',
      description: `${row.land_cost_usd_per_kw.toFixed(0)} $/kW × CRF`,
      usdPerMwh: perKwToPerMwh(row.land_cost_usd_per_kw, false),
      color: COMPONENT_COLORS.land,
    });
  }
  if (includeConnection && row.connection_cost_per_kw != null && row.connection_cost_per_kw > 0) {
    components.push({
      label: 'Grid connection',
      description: `${row.connection_cost_per_kw.toFixed(0)} $/kW × CRF`,
      usdPerMwh: perKwToPerMwh(row.connection_cost_per_kw, false),
      color: COMPONENT_COLORS.connection,
    });
  }
  if (
    includeTransmission &&
    row.transmission_cost_per_kw != null &&
    row.transmission_cost_per_kw > 0
  ) {
    components.push({
      label: 'New transmission',
      description: `${row.transmission_cost_per_kw.toFixed(0)} $/kW × CRF`,
      usdPerMwh: perKwToPerMwh(row.transmission_cost_per_kw, false),
      color: COMPONENT_COLORS.transmission,
    });
  }
  if (
    includeUpgrade &&
    row.substation_upgrade_cost_per_kw != null &&
    row.substation_upgrade_cost_per_kw > 0
  ) {
    components.push({
      label: 'Substation upgrade',
      description: `${row.substation_upgrade_cost_per_kw.toFixed(0)} $/kW × CRF`,
      usdPerMwh: perKwToPerMwh(row.substation_upgrade_cost_per_kw, false),
      color: COMPONENT_COLORS.upgrade,
    });
  }

  const waterfallData = computeWaterfallData(components);
  const totalComputed = waterfallData[waterfallData.length - 1].value;
  const reconciliationGap = lcoeDisplayed != null ? lcoeDisplayed - totalComputed : null;
  const rawMax = Math.max(totalComputed, lcoeDisplayed ?? 0) * 1.1;
  const tickStep = rawMax > 400 ? 100 : rawMax > 200 ? 50 : rawMax > 100 ? 25 : 10;
  const yMax = Math.ceil(rawMax / tickStep) * tickStep;
  const yTicks: number[] = [];
  for (let v = 0; v <= yMax; v += tickStep) yTicks.push(v);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={handleBackdropClick}
      style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)' }}
    >
      <div
        className="relative w-full max-w-2xl rounded-2xl overflow-hidden flex flex-col"
        style={{
          background: 'rgba(24, 24, 28, 0.92)',
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 24px 80px rgba(0,0,0,0.5)',
          maxHeight: '90vh',
        }}
      >
        <div
          className="flex items-center justify-between px-5 py-3 shrink-0"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}
        >
          <div>
            <h2 className="text-base font-semibold text-white">LCOE breakdown</h2>
            <p className="text-[11px] text-zinc-400 mt-0.5">
              {row.site_name} &middot; solar mid ${lcoeDisplayed?.toFixed(1) ?? '–'}/MWh
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-zinc-400 hover:text-white text-xl leading-none px-2 py-1 rounded hover:bg-white/10 transition-colors cursor-pointer"
          >
            &times;
          </button>
        </div>

        <div className="px-5 py-4 overflow-y-auto">
          <div className="text-[11px] leading-relaxed text-zinc-400 mb-3">
            Each bar shows how a cost component stacks onto the running LCOE. Formula:{' '}
            <span className="text-zinc-200">
              (CAPEX × CRF + FOM + grid costs × CRF) ÷ (CF × 8760 × degradation)
            </span>
            . Grid costs only load when applicable to this site's category{' '}
            {category ? <InfraBadge category={category} /> : <span>n/a</span>}.
          </div>

          <div className="text-[10px] text-zinc-500 mb-1 ml-1">$/MWh</div>
          <div style={{ width: '100%', height: 280 }}>
            <ResponsiveContainer>
              <BarChart data={waterfallData} margin={{ top: 8, right: 16, left: 8, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: 'rgb(161, 161, 170)', fontSize: 10 }}
                  angle={-20}
                  textAnchor="end"
                  height={50}
                  interval={0}
                  stroke="rgba(255,255,255,0.1)"
                />
                <YAxis
                  tick={{ fill: 'rgb(161, 161, 170)', fontSize: 10 }}
                  stroke="rgba(255,255,255,0.1)"
                  domain={[0, yMax]}
                  ticks={yTicks}
                  tickFormatter={(v: number) => v.toFixed(0)}
                  width={40}
                />
                <Tooltip
                  content={<WaterfallTooltip />}
                  cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                />
                <Bar dataKey="range" radius={[3, 3, 0, 0]}>
                  {waterfallData.map((d) => (
                    <Cell
                      key={d.name}
                      fill={d.color}
                      fillOpacity={d.isTotal ? 0.95 : 0.85}
                      stroke={d.isTotal ? d.color : 'none'}
                      strokeWidth={d.isTotal ? 1.5 : 0}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-[10px]">
            {waterfallData.slice(0, -1).map((d) => (
              <div key={d.name} className="flex items-center gap-1.5">
                <span className="inline-block w-2 h-2 rounded-sm" style={{ background: d.color }} />
                <span className="text-zinc-300">{d.name}</span>
                <span className="tabular-nums text-zinc-400">${d.value.toFixed(1)}</span>
              </div>
            ))}
          </div>

          <div
            className="mt-4 pt-3 flex items-center justify-between text-[12px]"
            style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}
          >
            <span className="text-zinc-300 font-medium">Total (computed)</span>
            <span className="tabular-nums text-white font-semibold">
              ${totalComputed.toFixed(1)}/MWh
            </span>
          </div>
          {lcoeDisplayed != null && reconciliationGap != null && (
            <div className="flex items-center justify-between text-[10px] text-zinc-500 mt-1">
              <span>
                Displayed LCOE: ${lcoeDisplayed.toFixed(1)}/MWh
                {Math.abs(reconciliationGap) > 1.5 && ' (gap reflects rounding / firming adders)'}
              </span>
              <span className="tabular-nums">
                &Delta; ${reconciliationGap >= 0 ? '+' : ''}
                {reconciliationGap.toFixed(1)}
              </span>
            </div>
          )}

          <div
            className="mt-4 p-2.5 rounded text-[10px] leading-relaxed"
            style={{
              background: 'rgba(255,255,255,0.03)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
            }}
          >
            <div className="font-medium mb-1 text-zinc-300">Inputs</div>
            WACC {(wacc * 100).toFixed(1)}% &middot; lifetime {lifetime}yr &middot; CRF{' '}
            {crf.toFixed(4)} &middot; CF {(cf * 100).toFixed(1)}% &middot; net energy{' '}
            {(annualMwhPerKw * 1000).toFixed(0)} kWh/kW-yr &middot; degradation{' '}
            {degFactor.toFixed(3)}
            {category && (
              <>
                {' '}
                &middot; category <InfraBadge category={category} />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

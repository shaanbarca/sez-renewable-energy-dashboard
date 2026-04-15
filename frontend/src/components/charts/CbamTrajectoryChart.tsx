import { useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { CbamProductMetrics, ScorecardRow } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

// EU free allocation phase-out schedule (fixed in EU regulation)
const FREE_ALLOCATION: Record<number, number> = {
  2026: 0.975,
  2027: 0.95,
  2028: 0.9,
  2029: 0.775,
  2030: 0.515,
  2031: 0.39,
  2032: 0.265,
  2033: 0.14,
  2034: 0.0,
};

const YEARS = Object.keys(FREE_ALLOCATION).map(Number);

// Default EU ETS certificate price: €80/tCO₂ × 1.10 EUR/USD
// Overridden by user assumptions when available
const DEFAULT_CERT_PRICE_USD = 88;

// Per-product color scheme
const PRODUCT_COLORS: Record<string, { grid: string; solar: string }> = {
  nickel_rkef: { grid: '#FF7043', solar: '#FFAB91' },
  steel_eaf: { grid: '#E53935', solar: '#EF9A9A' },
  steel_bfbof: { grid: '#C62828', solar: '#E57373' },
  cement: { grid: '#AB47BC', solar: '#CE93D8' },
  aluminium: { grid: '#29B6F6', solar: '#81D4FA' },
  fertilizer: { grid: '#FFA726', solar: '#FFD54F' },
};

const PRODUCT_LABELS: Record<string, string> = {
  nickel_rkef: 'Nickel (RKEF)',
  steel_eaf: 'Steel (EAF)',
  steel_bfbof: 'Steel (BF-BOF)',
  cement: 'Cement',
  aluminium: 'Aluminium',
  fertilizer: 'Fertilizer',
};

type ViewMode = 'overall' | 'per_product';

// --- Overall mode (single product pair) ---

interface OverallPoint {
  year: number;
  costCurrent: number;
  costSolar: number;
  savings: number;
  freeAllocationPct: number;
}

function OverallTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload?: OverallPoint }[];
}) {
  if (!active || !payload?.[0]?.payload) return null;
  const d = payload[0].payload;
  return (
    <div
      className="rounded px-3 py-2 text-xs"
      style={{
        background: 'var(--popup-bg)',
        border: '1px solid var(--popup-border)',
        boxShadow: 'var(--popup-shadow)',
        color: 'var(--text-primary)',
      }}
    >
      <div className="font-medium">{d.year}</div>
      <div style={{ color: 'var(--text-muted)' }}>
        Free allocation: {(d.freeAllocationPct * 100).toFixed(1)}%
      </div>
      <div style={{ color: '#FF7043' }}>Grid: ${d.costCurrent.toFixed(0)}/t</div>
      <div style={{ color: '#4CAF50' }}>Solar: ${d.costSolar.toFixed(0)}/t</div>
      {d.savings > 0 && (
        <div className="font-medium mt-0.5" style={{ color: '#4CAF50' }}>
          Savings: ${d.savings.toFixed(0)}/t
        </div>
      )}
    </div>
  );
}

// --- Per-product mode tooltip ---

function PerProductTooltip({
  active,
  payload,
  products,
}: {
  active?: boolean;
  payload?: { payload?: Record<string, number> }[];
  products: string[];
}) {
  if (!active || !payload?.[0]?.payload) return null;
  const d = payload[0].payload;
  const year = d.year;
  const freeAlloc = FREE_ALLOCATION[year] ?? 0;
  return (
    <div
      className="rounded px-3 py-2 text-xs"
      style={{
        background: 'var(--popup-bg)',
        border: '1px solid var(--popup-border)',
        boxShadow: 'var(--popup-shadow)',
        color: 'var(--text-primary)',
      }}
    >
      <div className="font-medium">{year}</div>
      <div style={{ color: 'var(--text-muted)' }} className="mb-1">
        Free allocation: {(freeAlloc * 100).toFixed(1)}%
      </div>
      {[...products]
        .sort((a, b) => (d[`grid_${b}`] ?? 0) - (d[`grid_${a}`] ?? 0))
        .map((p) => {
          const colors = PRODUCT_COLORS[p] ?? PRODUCT_COLORS.iron_steel;
          const grid = d[`grid_${p}`] ?? 0;
          const solar = d[`solar_${p}`] ?? 0;
          const savings = grid - solar;
          return (
            <div
              key={p}
              className="mt-1.5 pl-2 py-0.5"
              style={{ borderLeft: `3px solid ${colors.grid}` }}
            >
              <div className="font-medium" style={{ color: colors.grid }}>
                {PRODUCT_LABELS[p] ?? p}
              </div>
              <div style={{ color: colors.grid }}>Grid: ${grid.toFixed(0)}/t</div>
              <div style={{ color: colors.solar }}>Solar: ${solar.toFixed(0)}/t</div>
              {savings > 0 && (
                <div style={{ color: colors.solar }}>Savings: ${savings.toFixed(0)}/t</div>
              )}
            </div>
          );
        })}
    </div>
  );
}

// --- Helpers ---

function buildOverallData(
  eiCurrent: number,
  eiSolar: number,
  certPriceUsd: number = DEFAULT_CERT_PRICE_USD,
): OverallPoint[] {
  return YEARS.map((year) => {
    const exposure = 1 - FREE_ALLOCATION[year];
    const costCurrent = eiCurrent * certPriceUsd * exposure;
    const costSolar = eiSolar * certPriceUsd * exposure;
    return {
      year,
      costCurrent: Math.round(costCurrent * 100) / 100,
      costSolar: Math.round(costSolar * 100) / 100,
      savings: Math.round((costCurrent - costSolar) * 100) / 100,
      freeAllocationPct: FREE_ALLOCATION[year],
    };
  });
}

function buildPerProductData(
  perProduct: Record<string, CbamProductMetrics>,
  certPriceUsd: number = DEFAULT_CERT_PRICE_USD,
) {
  // Sort by emission intensity descending so highest-cost product is first (chart, legend, tooltip)
  const products = Object.keys(perProduct).sort(
    (a, b) => perProduct[b].emission_intensity_current - perProduct[a].emission_intensity_current,
  );
  const data = YEARS.map((year) => {
    const exposure = 1 - FREE_ALLOCATION[year];
    const point: Record<string, number> = { year };
    for (const p of products) {
      const m = perProduct[p];
      point[`grid_${p}`] =
        Math.round(m.emission_intensity_current * certPriceUsd * exposure * 100) / 100;
      point[`solar_${p}`] =
        Math.round(m.emission_intensity_solar * certPriceUsd * exposure * 100) / 100;
    }
    return point;
  });
  return { products, data };
}

// --- Main component ---

export default function CbamTrajectoryChart({ row }: { row: ScorecardRow }) {
  const perProduct = row.cbam_per_product;
  const hasMultipleProducts = perProduct != null && Object.keys(perProduct).length > 1;
  const [viewMode, setViewMode] = useState<ViewMode>('overall');
  const assumptions = useDashboardStore((s) => s.assumptions);
  const certPriceUsd =
    assumptions != null
      ? assumptions.cbam_certificate_price_eur * assumptions.cbam_eur_usd_rate
      : DEFAULT_CERT_PRICE_USD;

  const overallData = useMemo(() => {
    const eiCurrent = row.cbam_emission_intensity_current;
    const eiSolar = row.cbam_emission_intensity_solar;
    if (eiCurrent == null || eiSolar == null) return [];
    return buildOverallData(eiCurrent, eiSolar, certPriceUsd);
  }, [row.cbam_emission_intensity_current, row.cbam_emission_intensity_solar, certPriceUsd]);

  const perProductResult = useMemo(() => {
    if (!perProduct) return null;
    return buildPerProductData(perProduct, certPriceUsd);
  }, [perProduct, certPriceUsd]);

  if (overallData.length === 0) return null;

  const showPerProduct = viewMode === 'per_product' && perProductResult != null;

  return (
    <div
      className="rounded-lg p-3 mt-2"
      style={{ background: 'var(--card-bg)', border: '1px solid var(--card-border)' }}
    >
      {/* Header with optional toggle */}
      <div className="text-[11px] mb-2 flex items-center justify-between">
        <div style={{ color: 'var(--text-muted)' }}>
          CBAM Cost Trajectory 2026–2034
          {!showPerProduct && (
            <>
              <span style={{ color: '#FF7043' }}> Grid</span>
              {' vs '}
              <span style={{ color: '#4CAF50' }}>Solar</span>
            </>
          )}
          {' ($/tonne)'}
        </div>
        {hasMultipleProducts && (
          <div className="flex gap-1 text-[10px]">
            <button
              type="button"
              onClick={() => setViewMode('overall')}
              className="px-1.5 py-0.5 rounded cursor-pointer transition-colors"
              style={{
                color: viewMode === 'overall' ? 'var(--text-primary)' : 'var(--text-muted)',
                background: viewMode === 'overall' ? 'rgba(255,255,255,0.08)' : 'transparent',
              }}
            >
              Overall
            </button>
            <button
              type="button"
              onClick={() => setViewMode('per_product')}
              className="px-1.5 py-0.5 rounded cursor-pointer transition-colors"
              style={{
                color: viewMode === 'per_product' ? 'var(--text-primary)' : 'var(--text-muted)',
                background: viewMode === 'per_product' ? 'rgba(255,255,255,0.08)' : 'transparent',
              }}
            >
              Per Product
            </button>
          </div>
        )}
      </div>

      {/* Per-product legend */}
      {showPerProduct && perProductResult && (
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] mb-1.5">
          {perProductResult.products.map((p) => {
            const colors = PRODUCT_COLORS[p] ?? PRODUCT_COLORS.iron_steel;
            return (
              <div key={p} className="flex items-center gap-1">
                <span
                  className="inline-block w-2 h-2 rounded-sm"
                  style={{ background: colors.grid }}
                />
                <span style={{ color: colors.grid }}>{PRODUCT_LABELS[p] ?? p}</span>
              </div>
            );
          })}
          <div className="flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
            solid = grid, faded = solar
          </div>
        </div>
      )}

      {/* Chart */}
      {showPerProduct && perProductResult ? (
        <PerProductChart data={perProductResult.data} products={perProductResult.products} />
      ) : (
        <OverallChart data={overallData} />
      )}

      <div className="text-[9px] mt-1 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
        EU free allocation phases out 2026–2034. Gap = CBAM cost avoided by switching to RE.
      </div>
    </div>
  );
}

// --- Overall chart (original behavior) ---

function OverallChart({ data }: { data: OverallPoint[] }) {
  const maxCost = Math.max(...data.map((d) => d.costCurrent));
  return (
    <ResponsiveContainer width="100%" height={180}>
      <AreaChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
        <defs>
          <linearGradient id="cbamCurrentGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#FF7043" stopOpacity={0.4} />
            <stop offset="100%" stopColor="#FF7043" stopOpacity={0.05} />
          </linearGradient>
          <linearGradient id="cbamSolarGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#4CAF50" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#4CAF50" stopOpacity={0.05} />
          </linearGradient>
        </defs>
        <XAxis
          dataKey="year"
          tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
          tickLine={false}
          axisLine={{ stroke: 'var(--border-subtle)' }}
        />
        <YAxis
          tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
          tickLine={false}
          axisLine={{ stroke: 'var(--border-subtle)' }}
          domain={[0, Math.ceil(maxCost / 50) * 50]}
          label={{
            value: '$/t',
            angle: -90,
            position: 'insideLeft',
            offset: 0,
            fontSize: 9,
            fill: 'var(--text-muted)',
          }}
        />
        <Tooltip content={<OverallTooltip />} />
        <ReferenceLine
          x={2030}
          stroke="var(--text-muted)"
          strokeDasharray="3 3"
          label={{
            value: '50% exposed',
            fill: 'var(--text-muted)',
            fontSize: 9,
            position: 'insideTopRight',
          }}
        />
        <Area
          type="monotone"
          dataKey="costCurrent"
          stroke="#FF7043"
          strokeWidth={2}
          fill="url(#cbamCurrentGrad)"
        />
        <Area
          type="monotone"
          dataKey="costSolar"
          stroke="#4CAF50"
          strokeWidth={2}
          fill="url(#cbamSolarGrad)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// --- Per-product chart ---

function PerProductChart({
  data,
  products,
}: {
  data: Record<string, number>[];
  products: string[];
}) {
  const maxCost = Math.max(
    ...data.flatMap((d) => products.map((p) => (d[`grid_${p}`] as number) ?? 0)),
  );
  return (
    <ResponsiveContainer width="100%" height={180}>
      <AreaChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
        <defs>
          {products.map((p) => {
            const colors = PRODUCT_COLORS[p] ?? PRODUCT_COLORS.iron_steel;
            return (
              <linearGradient
                key={`grad_grid_${p}`}
                id={`cbamGrad_grid_${p}`}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop offset="0%" stopColor={colors.grid} stopOpacity={0.3} />
                <stop offset="100%" stopColor={colors.grid} stopOpacity={0.03} />
              </linearGradient>
            );
          })}
        </defs>
        <XAxis
          dataKey="year"
          tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
          tickLine={false}
          axisLine={{ stroke: 'var(--border-subtle)' }}
        />
        <YAxis
          tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
          tickLine={false}
          axisLine={{ stroke: 'var(--border-subtle)' }}
          domain={[0, Math.ceil(maxCost / 50) * 50]}
          label={{
            value: '$/t',
            angle: -90,
            position: 'insideLeft',
            offset: 0,
            fontSize: 9,
            fill: 'var(--text-muted)',
          }}
        />
        <Tooltip content={<PerProductTooltip products={products} />} />
        <ReferenceLine
          x={2030}
          stroke="var(--text-muted)"
          strokeDasharray="3 3"
          label={{
            value: '50% exposed',
            fill: 'var(--text-muted)',
            fontSize: 9,
            position: 'insideTopRight',
          }}
        />
        {products.map((p) => {
          const colors = PRODUCT_COLORS[p] ?? PRODUCT_COLORS.iron_steel;
          return (
            <Area
              key={`grid_${p}`}
              type="monotone"
              dataKey={`grid_${p}`}
              stroke={colors.grid}
              strokeWidth={2}
              fill={`url(#cbamGrad_grid_${p})`}
              name={`${PRODUCT_LABELS[p] ?? p} (grid)`}
            />
          );
        })}
        {products.map((p) => {
          const colors = PRODUCT_COLORS[p] ?? PRODUCT_COLORS.iron_steel;
          return (
            <Area
              key={`solar_${p}`}
              type="monotone"
              dataKey={`solar_${p}`}
              stroke={colors.solar}
              strokeWidth={1.5}
              strokeDasharray="4 3"
              fill="none"
              name={`${PRODUCT_LABELS[p] ?? p} (solar)`}
            />
          );
        })}
      </AreaChart>
    </ResponsiveContainer>
  );
}

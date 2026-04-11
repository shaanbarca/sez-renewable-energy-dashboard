/**
 * URL state persistence for dashboard assumptions.
 *
 * Serializes key assumptions to URL query params so users can share
 * scenario links like ?capex=840&wacc=8. Short param names keep URLs clean.
 */

import type { BenchmarkMode, UserAssumptions } from './types';

/** Short URL param name -> UserAssumptions field. */
const PARAM_MAP: [string, keyof UserAssumptions][] = [
  ['capex', 'capex_usd_per_kw'],
  ['wacc', 'wacc_pct'],
  ['life', 'lifetime_yr'],
  ['fom', 'fom_usd_per_kw_yr'],
  ['conn', 'connection_cost_per_kw_km'],
  ['connfix', 'grid_connection_fixed_per_kw'],
  ['bess', 'bess_capex_usd_per_kwh'],
  ['land', 'land_cost_usd_per_kw'],
  ['subutil', 'substation_utilization_pct'],
  ['idr', 'idr_usd_rate'],
];

const BENCHMARK_PARAM = 'benchmark';

/** Parse URL query params into partial assumptions + optional benchmark mode. */
export function parseUrlAssumptions(): {
  assumptions: Partial<UserAssumptions>;
  benchmarkMode?: BenchmarkMode;
} {
  const params = new URLSearchParams(window.location.search);
  const assumptions: Partial<UserAssumptions> = {};

  for (const [param, field] of PARAM_MAP) {
    const raw = params.get(param);
    if (raw == null) continue;
    const val = Number.parseFloat(raw);
    if (!Number.isFinite(val)) continue;
    // Assign safely — all UserAssumptions fields are numbers
    (assumptions as Record<string, number>)[field] = val;
  }

  const bench = params.get(BENCHMARK_PARAM);
  const benchmarkMode = bench === 'tariff' || bench === 'bpp' ? bench : undefined;

  return { assumptions, benchmarkMode };
}

/** Build query string with only params that differ from defaults. */
export function buildUrlParams(
  assumptions: UserAssumptions,
  defaults: UserAssumptions,
  benchmarkMode: BenchmarkMode,
): string {
  const params = new URLSearchParams();

  for (const [param, field] of PARAM_MAP) {
    if (assumptions[field] !== defaults[field]) {
      params.set(param, String(assumptions[field]));
    }
  }

  if (benchmarkMode !== 'bpp') {
    params.set(BENCHMARK_PARAM, benchmarkMode);
  }

  return params.toString();
}

/** Update URL in-place (replaceState) with current assumptions delta. */
export function updateUrl(
  assumptions: UserAssumptions,
  defaults: UserAssumptions,
  benchmarkMode: BenchmarkMode,
): void {
  const qs = buildUrlParams(assumptions, defaults, benchmarkMode);
  const url = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
  window.history.replaceState(null, '', url);
}

/** Check whether any assumption field differs from defaults. */
export function hasChangedAssumptions(
  current: UserAssumptions,
  defaults: UserAssumptions,
): boolean {
  for (const [, field] of PARAM_MAP) {
    if (current[field] !== defaults[field]) return true;
  }
  return false;
}

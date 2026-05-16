/**
 * FuelTypePill — small text pill rendering captive_fuel_type as a colored badge.
 *
 * Per v4.3 M-AT8b UX refinement: in the score drawer + DataTable, the captive
 * incumbent row uses the generic label "Captive Power" and lets a fuel-type
 * pill (Coal / Gas / Hydro) discriminate. That way new captive fuel types in
 * v4.4+ (biomass CHP, oil diesel) don't require new copy in every drawer.
 *
 * Returns null for non-captive sites (`none` / null / undefined) so callers
 * can pass `row.captive_fuel_type` through without manual gating.
 *
 * Color choices match existing industry-badge palette in DataTable:
 *   - Coal: deep red — matches captive_coal_count badge at columns.tsx:592
 *   - Gas:  amber/yellow (natural gas convention)
 *   - Hydro: cyan/teal (water convention)
 */

import type React from 'react';

export type CaptiveFuel = 'coal_subcritical' | 'coal_supercritical' | 'natural_gas' | 'hydro';

const FUEL_STYLES: Record<CaptiveFuel, { label: string; color: string; bg: string; tooltip: string }> = {
  coal_subcritical: {
    label: 'Coal',
    color: '#EF5350',
    bg: 'rgba(183,28,28,0.18)',
    tooltip: 'Captive coal — subcritical boiler (older Indonesian captive standard)',
  },
  coal_supercritical: {
    label: 'Coal',
    color: '#EF5350',
    bg: 'rgba(183,28,28,0.18)',
    tooltip: 'Captive coal — supercritical boiler (higher efficiency, Krakatau Posco)',
  },
  natural_gas: {
    label: 'Gas',
    color: '#FFB300',
    bg: 'rgba(255,179,0,0.15)',
    tooltip: 'Captive natural gas — typically CCGT under HGBT regulated $7/MMBtu',
  },
  hydro: {
    label: 'Hydro',
    color: '#00B8D4',
    bg: 'rgba(0,184,212,0.15)',
    tooltip: 'Captive hydropower — no fuel cost (Inalum Asahan)',
  },
};

interface FuelTypePillProps {
  fuelType: string | null | undefined;
  /** Smaller padding + font for table-cell context. */
  compact?: boolean;
  /** Override default left margin (default 0). */
  ml?: number;
}

export function FuelTypePill({
  fuelType,
  compact = false,
  ml = 0,
}: FuelTypePillProps): React.ReactElement | null {
  if (
    fuelType !== 'coal_subcritical' &&
    fuelType !== 'coal_supercritical' &&
    fuelType !== 'natural_gas' &&
    fuelType !== 'hydro'
  ) {
    return null;
  }
  const s = FUEL_STYLES[fuelType];
  return (
    <span
      title={s.tooltip}
      aria-label={s.tooltip}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: compact ? '1px 5px' : '2px 7px',
        marginLeft: ml,
        marginRight: 4,
        fontSize: compact ? 9 : 10,
        fontWeight: 600,
        borderRadius: 4,
        color: s.color,
        background: s.bg,
        lineHeight: 1.2,
        verticalAlign: 'middle',
        userSelect: 'none',
      }}
    >
      {s.label}
    </span>
  );
}

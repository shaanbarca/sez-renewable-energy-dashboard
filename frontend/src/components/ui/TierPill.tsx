/**
 * TierPill — small text pill rendering captive_lcoe_tier (T1 / T2 / T3) with
 * a bordered colored background and a rich hover tooltip explaining what
 * each tier means.
 *
 * Per v4.3 M-AT8b design review (`docs/refinement/v4_3_M_AT8b_captive_lcoe_ui_proposal.md`):
 *   - Text + color (not color-alone) for accessibility
 *   - Conventional badge family — matches DataTable's action-flag chips
 *   - Hover popup carries the tier explanation (concrete, not abstract)
 *   - `aria-label` mirrors the popup for screen readers
 *
 * Tier meaning (from METHODOLOGY §13.10):
 *   - T1: high-confidence anchor (multi-source verified, e.g. IMIP, Krakatau Posco)
 *   - T2: industry-archetype extrapolation (~7 sites)
 *   - T3: formula placeholder (low confidence, ~30 sites)
 *
 * Returns null when `tier` is null/undefined so callers can pass through
 * scorecard rows without manual gating.
 */

import type React from 'react';
import { useState } from 'react';

export type LcoeTier = 'T1' | 'T2' | 'T3';

const TIER_STYLES: Record<
  LcoeTier,
  { color: string; border: string; bg: string; title: string; body: string }
> = {
  T1: {
    color: '#2E7D32',
    border: '#2E7D32',
    bg: 'rgba(46,125,50,0.10)',
    title: 'Tier 1 — High confidence anchor',
    body: 'Site-specific LCOE with multi-source verification: Berkeley GSPP 2024 + IESR + CREA triangulation. Example anchors: IMIP $50, Krakatau Posco $62, Pupuk Kaltim $50, Inalum hydro $30. Trustworthy for DFI investment decisions.',
  },
  T2: {
    color: '#F57C00',
    border: '#F57C00',
    bg: 'rgba(245,124,0,0.10)',
    title: 'Tier 2 — Industry-archetype extrapolation',
    body: "Single-source / archetype value. Inherited from a T1 anchor's economics with regional adjustments (e.g. IWIP $55 = IMIP archetype + Maluku logistics premium). Reasonable for screening; site-specific data would tighten the estimate.",
  },
  T3: {
    color: '#C62828',
    border: '#C62828',
    bg: 'rgba(198,40,40,0.10)',
    title: 'Tier 3 — Formula placeholder (low confidence)',
    body: 'Formula default from CAPTIVE_*_DEFAULTS at the active fuel-price scenario. Used when no site-specific data exists. ~$63 coal at DMO, ~$70 gas at HGBT. Use the gap signal cautiously — these sites need real disclosure before locking in investment thesis. See methodology §13.10.',
  },
};

interface TierPillProps {
  tier: LcoeTier | string | null | undefined;
  /** Smaller padding + font for table-cell context. */
  compact?: boolean;
  /** Override default left margin (default 6px). */
  ml?: number;
}

export function TierPill({
  tier,
  compact = false,
  ml = 6,
}: TierPillProps): React.ReactElement | null {
  const [showTip, setShowTip] = useState(false);
  if (tier !== 'T1' && tier !== 'T2' && tier !== 'T3') return null;
  const s = TIER_STYLES[tier];
  const ariaLabel = `${s.title}. ${s.body}`;
  return (
    <span
      aria-label={ariaLabel}
      onMouseEnter={() => setShowTip(true)}
      onMouseLeave={() => setShowTip(false)}
      style={{
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        padding: compact ? '1px 5px' : '2px 7px',
        marginLeft: ml,
        fontSize: compact ? 9 : 10,
        fontWeight: 600,
        borderRadius: 4,
        border: `1px solid ${s.border}`,
        color: s.color,
        background: s.bg,
        lineHeight: 1.2,
        verticalAlign: 'middle',
        userSelect: 'none',
        cursor: 'help',
      }}
    >
      {tier}
      {showTip && (
        <span
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            right: 0,
            zIndex: 50,
            width: 240,
            padding: '6px 8px',
            borderRadius: 4,
            background: 'var(--popup-bg)',
            color: 'var(--text-value)',
            border: '1px solid var(--popup-border)',
            boxShadow: 'var(--popup-shadow)',
            fontSize: 10,
            fontWeight: 400,
            lineHeight: 1.35,
            whiteSpace: 'normal',
            textAlign: 'left',
            pointerEvents: 'none',
          }}
        >
          <div style={{ fontWeight: 600, color: s.color, marginBottom: 3 }}>{s.title}</div>
          <div style={{ color: 'var(--text-secondary)' }}>{s.body}</div>
        </span>
      )}
    </span>
  );
}

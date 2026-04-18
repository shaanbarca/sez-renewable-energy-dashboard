import { ECONOMIC_TIER_COLORS, ECONOMIC_TIER_LABELS } from '../../../lib/constants';
import { computeFlipDiff } from '../../../lib/flipDiff';
import { FLIP_PRESET_LABELS } from '../../../lib/flipPresets';
import type { ScorecardRow } from '../../../lib/types';
import { useDashboardStore } from '../../../store/dashboard';
import { SectionHeader, StatCard } from './StatComponents';

function fmtNum(v: number | null | undefined, digits = 1): string {
  if (v == null || !Number.isFinite(v)) return '—';
  return v.toFixed(digits);
}

function fmtDelta(v: number | null | undefined, digits = 1): string {
  if (v == null || !Number.isFinite(v)) return '—';
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(digits)}`;
}

function CompareRow({
  label,
  before,
  after,
  delta,
  deltaColor,
  unit,
}: {
  label: string;
  before: string;
  after: string;
  delta?: string | null;
  deltaColor?: string;
  unit?: string;
}) {
  return (
    <div className="grid grid-cols-[1fr_auto_auto_auto] gap-2 items-baseline py-1.5">
      <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
        {label}
      </span>
      <span
        className="text-[12px] tabular-nums"
        style={{ color: 'var(--text-secondary)' }}
      >
        {before}
        {unit ? ` ${unit}` : ''}
      </span>
      <span style={{ color: 'var(--text-muted)', fontSize: 10 }}>→</span>
      <span
        className="text-[12px] font-medium tabular-nums text-right"
        style={{ color: 'var(--text-value)' }}
      >
        {after}
        {unit ? ` ${unit}` : ''}
        {delta && (
          <span
            className="ml-2 text-[10px] font-normal"
            style={{ color: deltaColor ?? 'var(--text-muted)' }}
          >
            ({delta})
          </span>
        )}
      </span>
    </div>
  );
}

function deltaColor(v: number | null | undefined, betterIsLower = true): string {
  if (v == null || !Number.isFinite(v) || v === 0) return 'var(--text-muted)';
  const good = betterIsLower ? v < 0 : v > 0;
  return good ? '#4CAF50' : '#F44336';
}

export function FlipTab({ row }: { row: ScorecardRow }) {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const flipScorecard = useDashboardStore((s) => s.flipScorecard);
  const flipPreset = useDashboardStore((s) => s.flipPreset);
  const flipStale = useDashboardStore((s) => s.flipStale);
  const setActiveTab = useDashboardStore((s) => s.setActiveTab);

  if (!scorecard || !flipScorecard) {
    return (
      <StatCard>
        <p className="text-[11px] leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          No flip scenario computed yet. Pick a preset and click{' '}
          <strong style={{ color: 'var(--accent)' }}>Compute Flip</strong> in the
          Scenario Compare tab to see how this site's tier, LCOE, and CBAM exposure would
          shift under the flipped assumptions.
        </p>
        <button
          type="button"
          onClick={() => setActiveTab('compare')}
          className="mt-3 w-full py-1.5 rounded text-[11px] font-medium transition-colors"
          style={{ background: 'var(--accent)', color: '#0a0a0c' }}
        >
          Open Scenario Compare
        </button>
      </StatCard>
    );
  }

  const { rows } = computeFlipDiff(scorecard, flipScorecard);
  const diff = rows.find((r) => r.site_id === row.site_id);

  if (!diff) {
    return (
      <StatCard>
        <p className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>
          No flip data for this site.
        </p>
      </StatCard>
    );
  }

  const presetLabel =
    flipPreset && flipPreset !== 'custom'
      ? FLIP_PRESET_LABELS[flipPreset]
      : 'Custom edits';

  const directionColor =
    diff.flip_direction === 'improved'
      ? '#4CAF50'
      : diff.flip_direction === 'worsened'
        ? '#F44336'
        : 'var(--text-muted)';
  const directionLabel =
    diff.flip_direction === 'improved'
      ? '↑ Improved'
      : diff.flip_direction === 'worsened'
        ? '↓ Worsened'
        : 'Unchanged';

  const gapDelta =
    diff.gap_baseline_pct != null && diff.gap_flip_pct != null
      ? diff.gap_flip_pct - diff.gap_baseline_pct
      : null;

  return (
    <>
      {/* Scenario banner */}
      <StatCard>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              Scenario
            </div>
            <div className="text-[12px] font-medium" style={{ color: 'var(--text-value)' }}>
              {presetLabel}
            </div>
          </div>
          <span
            className="text-[11px] font-medium px-2 py-1 rounded"
            style={{
              color: directionColor,
              background: `${directionColor}18`,
              border: `1px solid ${directionColor}44`,
            }}
          >
            {directionLabel}
          </span>
        </div>
        {flipStale && (
          <div
            className="mt-2 text-[10px] italic"
            style={{ color: 'var(--warning, #f59e0b)' }}
          >
            Baseline changed — recompute to refresh this view
          </div>
        )}
      </StatCard>

      {/* Tier transition */}
      <StatCard>
        <SectionHeader title="Economic Tier" />
        <div className="flex items-center gap-3 py-1">
          <span
            className="text-[12px] font-medium"
            style={{ color: ECONOMIC_TIER_COLORS[diff.tier_baseline] }}
          >
            {ECONOMIC_TIER_LABELS[diff.tier_baseline]}
          </span>
          <span style={{ color: 'var(--text-muted)' }}>→</span>
          <span
            className="text-[12px] font-medium"
            style={{ color: ECONOMIC_TIER_COLORS[diff.tier_flip] }}
          >
            {ECONOMIC_TIER_LABELS[diff.tier_flip]}
          </span>
        </div>
      </StatCard>

      {/* LCOE + gap metrics */}
      <StatCard>
        <SectionHeader title="Key Metrics" />
        <CompareRow
          label="LCOE"
          before={fmtNum(diff.lcoe_baseline, 1)}
          after={fmtNum(diff.lcoe_flip, 1)}
          delta={fmtDelta(diff.delta_lcoe, 1)}
          deltaColor={deltaColor(diff.delta_lcoe, true)}
          unit="$/MWh"
        />
        <CompareRow
          label="Gap to grid"
          before={diff.gap_baseline_pct != null ? `${diff.gap_baseline_pct.toFixed(0)}%` : '—'}
          after={diff.gap_flip_pct != null ? `${diff.gap_flip_pct.toFixed(0)}%` : '—'}
          delta={gapDelta != null ? `${fmtDelta(gapDelta, 0)}%` : null}
          deltaColor={deltaColor(gapDelta, true)}
        />
      </StatCard>

      {/* CBAM urgency */}
      {(diff.cbam_urgent_baseline || diff.cbam_urgent_flip) && (
        <StatCard>
          <SectionHeader title="CBAM Urgency" />
          <div className="flex items-center gap-3 py-1">
            <span
              className="text-[11px]"
              style={{
                color: diff.cbam_urgent_baseline ? '#FF6F00' : 'var(--text-muted)',
              }}
            >
              {diff.cbam_urgent_baseline ? 'Urgent' : 'Not urgent'}
            </span>
            <span style={{ color: 'var(--text-muted)' }}>→</span>
            <span
              className="text-[11px] font-medium"
              style={{
                color: diff.cbam_urgent_flip ? '#FF6F00' : 'var(--text-muted)',
              }}
            >
              {diff.cbam_urgent_flip ? 'Urgent' : 'Not urgent'}
            </span>
            {diff.cbam_urgent_changed && (
              <span
                className="ml-auto text-[10px] px-1.5 py-0.5 rounded"
                style={{
                  color: diff.cbam_urgent_flip ? '#FF6F00' : '#4CAF50',
                  background: diff.cbam_urgent_flip
                    ? 'rgba(255,111,0,0.15)'
                    : 'rgba(76,175,80,0.15)',
                }}
              >
                {diff.cbam_urgent_flip ? 'NEW' : 'CLEARED'}
              </span>
            )}
          </div>
        </StatCard>
      )}
    </>
  );
}

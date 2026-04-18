import type { FlipSummary as FlipSummaryData } from '../../../lib/flipDiff';
import { useDashboardStore } from '../../../store/dashboard';

function Stat({
  label,
  value,
  tint,
  hint,
}: {
  label: string;
  value: string;
  tint?: string;
  hint?: string;
}) {
  return (
    <div
      className="flex-1 min-w-[110px] px-2.5 py-2 rounded"
      style={{
        background: 'var(--card-bg)',
        border: '1px solid var(--border-subtle)',
      }}
    >
      <div className="text-[9px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
        {label}
      </div>
      <div
        className="text-sm font-medium tabular-nums leading-tight"
        style={{ color: tint ?? 'var(--text-value)' }}
      >
        {value}
      </div>
      {hint && (
        <div className="text-[9px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
          {hint}
        </div>
      )}
    </div>
  );
}

function fmtPct(v: number | null): string {
  if (v == null || !Number.isFinite(v)) return '—';
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toFixed(1)}%`;
}

export default function FlipSummary({ summary }: { summary: FlipSummaryData | null }) {
  const flipLoading = useDashboardStore((s) => s.flipLoading);
  const flipStale = useDashboardStore((s) => s.flipStale);

  if (flipLoading) {
    return (
      <div
        className="h-full flex items-center justify-center text-xs"
        style={{ color: 'var(--text-muted)' }}
      >
        Computing flip scenario…
      </div>
    );
  }

  if (!summary) {
    return (
      <div
        className="h-full flex items-center justify-center text-xs"
        style={{ color: 'var(--text-muted)' }}
      >
        Pick a preset and click Compute Flip to see impact.
      </div>
    );
  }

  const gapClosed = summary.gap_closed_pct;
  const gapTint =
    gapClosed == null
      ? undefined
      : gapClosed > 0
        ? '#4CAF50'
        : gapClosed < 0
          ? '#F44336'
          : undefined;

  return (
    <div className="flex items-stretch gap-2 h-full px-3 py-2">
      <Stat
        label="Sites improved"
        value={`${summary.flipped_to_better_tier} / ${summary.total_sites}`}
        tint={summary.flipped_to_better_tier > 0 ? '#4CAF50' : undefined}
      />
      <Stat
        label="Sites worsened"
        value={`${summary.flipped_to_worse_tier} / ${summary.total_sites}`}
        tint={summary.flipped_to_worse_tier > 0 ? '#F44336' : undefined}
      />
      <Stat
        label="New Full RE"
        value={String(summary.flipped_to_full_re)}
        tint={summary.flipped_to_full_re > 0 ? '#2E7D32' : undefined}
      />
      <Stat
        label="Median gap closed"
        value={fmtPct(gapClosed)}
        tint={gapTint}
        hint={
          summary.median_gap_baseline_pct != null && summary.median_gap_flip_pct != null
            ? `${summary.median_gap_baseline_pct.toFixed(0)}% → ${summary.median_gap_flip_pct.toFixed(0)}%`
            : undefined
        }
      />
      <Stat
        label="New CBAM urgent"
        value={String(summary.new_cbam_urgent_count)}
        tint={summary.new_cbam_urgent_count > 0 ? '#FF6F00' : undefined}
      />
      {flipStale && (
        <div
          className="flex items-center px-2 py-1 rounded text-[10px] font-medium self-center"
          style={{
            background: 'rgba(245,158,11,0.15)',
            border: '1px solid rgba(245,158,11,0.4)',
            color: '#f59e0b',
          }}
        >
          STALE
        </div>
      )}
    </div>
  );
}

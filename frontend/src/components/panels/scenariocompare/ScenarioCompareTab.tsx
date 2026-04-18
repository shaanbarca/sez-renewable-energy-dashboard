import { useMemo } from 'react';
import { computeFlipDiff } from '../../../lib/flipDiff';
import { useDashboardStore } from '../../../store/dashboard';
import FlipControls from './FlipControls';
import FlipDiffTable from './FlipDiffTable';
import FlipSummary from './FlipSummary';

export default function ScenarioCompareTab() {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const flipScorecard = useDashboardStore((s) => s.flipScorecard);
  const flipLoading = useDashboardStore((s) => s.flipLoading);

  const diff = useMemo(() => {
    if (!scorecard || !flipScorecard) return null;
    return computeFlipDiff(scorecard, flipScorecard);
  }, [scorecard, flipScorecard]);

  return (
    <div className="h-full flex">
      {/* Left column: controls */}
      <div className="w-[340px] shrink-0 h-full">
        <FlipControls />
      </div>

      {/* Right column: summary on top, diff table below */}
      <div className="flex-1 min-w-0 h-full flex flex-col">
        <div
          className="shrink-0"
          style={{
            minHeight: 64,
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <FlipSummary summary={diff?.summary ?? null} />
        </div>
        <div className="flex-1 min-h-0">
          {diff ? (
            <FlipDiffTable rows={diff.rows} />
          ) : flipLoading ? (
            <div
              className="h-full flex items-center justify-center text-xs"
              style={{ color: 'var(--text-muted)' }}
            >
              Running flip scenario…
            </div>
          ) : (
            <div
              className="h-full flex flex-col items-center justify-center gap-2 px-6 text-center"
              style={{ color: 'var(--text-muted)' }}
            >
              <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                No flip scenario computed yet
              </div>
              <div className="text-xs max-w-md">
                Pick a preset on the left (or edit individual levers), then click{' '}
                <strong style={{ color: 'var(--accent)' }}>Compute Flip</strong>. You'll see which
                sites change tier, which close the LCOE gap, and which flip to CBAM urgent.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

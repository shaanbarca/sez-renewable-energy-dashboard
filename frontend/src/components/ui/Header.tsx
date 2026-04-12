import { useState } from 'react';
import { useDashboardStore } from '../../store/dashboard';
import LayerControl from '../map/LayerControl';
import ActionFlagLegend from './ActionFlagLegend';
import EnergyToggle from './EnergyToggle';
import MethodologyModal from './MethodologyModal';

function GuideButton() {
  const restart = useDashboardStore((s) => s.restartWalkthrough);
  return (
    <button
      type="button"
      onClick={restart}
      className="text-xs transition-colors cursor-pointer"
      style={{ color: 'var(--text-secondary)' }}
      onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
      onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
    >
      Guide
    </button>
  );
}

export default function Header() {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const kekCount = scorecard?.length ?? 0;
  const [methodologyOpen, setMethodologyOpen] = useState(false);

  return (
    <>
      <header
        className="flex items-center justify-between px-5 py-3"
        style={{
          background: 'var(--header-bg)',
          backdropFilter: 'var(--header-backdrop)',
          WebkitBackdropFilter: 'var(--header-backdrop)',
          borderBottom: `1px solid var(--header-border)`,
          boxShadow: 'var(--header-shadow)',
        }}
      >
        <div className="flex items-center gap-5">
          <h1
            className="text-sm font-semibold tracking-wide"
            style={{ color: 'var(--text-primary)' }}
          >
            KEK Power Competitiveness Dashboard
          </h1>
          <ActionFlagLegend />
          <LayerControl />
        </div>

        <div className="flex items-center gap-4">
          <GuideButton />
          <button
            type="button"
            onClick={() => setMethodologyOpen(true)}
            className="text-xs transition-colors cursor-pointer"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
          >
            Methodology
          </button>
          <EnergyToggle />
          <span
            className="px-2.5 py-1 rounded-full text-xs font-medium border"
            style={{
              color: 'var(--text-secondary)',
              background: 'var(--glass)',
              borderColor: 'var(--glass-border-bright)',
            }}
          >
            {kekCount} KEKs
          </span>
        </div>
      </header>

      <MethodologyModal open={methodologyOpen} onClose={() => setMethodologyOpen(false)} />
    </>
  );
}

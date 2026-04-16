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
            SEZ Renewable Energy Dashboard
          </h1>
          <ActionFlagLegend />
          <LayerControl />
          <EnergyToggle />
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
          <a
            href="https://github.com/shaanbarca/sez-renewable-energy-dashboard"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
            </svg>
            Shaan Barca
          </a>
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

import { useEffect, useRef, useState } from 'react';
import { useDashboardStore } from '../../store/dashboard';
import LayerControl from '../map/LayerControl';
import ActionFlagLegend from './ActionFlagLegend';
import CostBasisToggle from './CostBasisToggle';
import EnergyToggle from './EnergyToggle';
import MethodologyModal from './MethodologyModal';

function AboutMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        title="About this dashboard"
        aria-label="About"
        className="flex items-center justify-center w-6 h-6 rounded-full text-xs transition-colors cursor-pointer"
        style={{
          color: 'var(--text-secondary)',
          border: '1px solid var(--glass-border)',
          background: open ? 'var(--glass)' : 'transparent',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
        onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
      >
        i
      </button>
      {open && (
        <div
          className="absolute right-0 mt-2 rounded-lg px-3 py-2 min-w-[200px] z-50"
          style={{
            backdropFilter: 'var(--blur-heavy)',
            WebkitBackdropFilter: 'var(--blur-heavy)',
            background: 'var(--glass-heavy)',
            border: '1px solid var(--glass-border-bright)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
          }}
        >
          <a
            href="https://github.com/shaanbarca/sez-renewable-energy-dashboard"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs py-1.5 transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
          >
            <svg width="13" height="13" viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
            </svg>
            Shaan Barca
          </a>
          <a
            href="https://doi.org/10.5281/zenodo.19570542"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs py-1.5 transition-colors"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-primary)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-secondary)')}
            title="Cite this dashboard · DOI: 10.5281/zenodo.19570542"
          >
            DOI
            <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>↗</span>
            <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
              10.5281/zenodo.19570542
            </span>
          </a>
        </div>
      )}
    </div>
  );
}

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
  const siteCount = scorecard?.length ?? 0;
  const kekCount = scorecard?.filter((r) => r.site_type === 'kek').length ?? 0;
  const industrialCount = siteCount - kekCount;
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
        <div className="flex items-center gap-3">
          <h1
            className="text-[18px] font-bold tracking-tight whitespace-nowrap"
            style={{ color: 'var(--text-primary)' }}
          >
            SEZ Renewable Energy
          </h1>
          <ActionFlagLegend />
          <LayerControl />
          <EnergyToggle />
          <CostBasisToggle />
        </div>

        <div className="flex items-center gap-3">
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
          <AboutMenu />
          <span
            className="px-2.5 py-1 rounded-full text-xs font-medium border whitespace-nowrap"
            style={{
              color: 'var(--text-secondary)',
              background: 'var(--glass)',
              borderColor: 'var(--glass-border-bright)',
            }}
            title={`${kekCount} KEKs (Special Economic Zones) · ${industrialCount} standalone industrial plants (steel, cement, aluminium, copper, fertilizer, nickel)`}
          >
            {siteCount} sites · {kekCount} KEK · {industrialCount} industrial
          </span>
        </div>
      </header>

      <MethodologyModal open={methodologyOpen} onClose={() => setMethodologyOpen(false)} />
    </>
  );
}

import { useDashboardStore } from '../../store/dashboard';
import ActionFlagLegend from './ActionFlagLegend';
import EnergyToggle from './EnergyToggle';

export default function Header() {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const kekCount = scorecard?.length ?? 0;

  return (
    <header
      className="flex items-center justify-between px-5 py-3 border-b"
      style={{
        background: 'var(--glass-heavy)',
        backdropFilter: 'var(--blur-heavy)',
        WebkitBackdropFilter: 'var(--blur-heavy)',
        borderColor: 'var(--glass-border)',
      }}
    >
      <div className="flex items-center gap-5">
        <h1 className="text-sm font-semibold text-white tracking-wide">
          KEK Power Competitiveness Dashboard
        </h1>
        <ActionFlagLegend />
      </div>

      <div className="flex items-center gap-4">
        <EnergyToggle />
        <span
          className="px-2.5 py-1 rounded-full text-xs font-medium text-zinc-300 border"
          style={{
            background: 'var(--glass)',
            borderColor: 'var(--glass-border-bright)',
          }}
        >
          {kekCount} KEKs
        </span>
      </div>
    </header>
  );
}

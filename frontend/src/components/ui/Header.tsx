import { useDashboardStore } from '../../store/dashboard';
import ActionFlagLegend from './ActionFlagLegend';
import EnergyToggle from './EnergyToggle';

export default function Header() {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const kekCount = scorecard?.length ?? 0;

  return (
    <header
      className="flex items-center justify-between px-5 py-3"
      style={{
        background: 'rgba(255, 255, 255, 0.03)',
        backdropFilter: 'blur(48px) saturate(1.8) brightness(1.15)',
        WebkitBackdropFilter: 'blur(48px) saturate(1.8) brightness(1.15)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.06), 0 2px 16px rgba(0, 0, 0, 0.1)',
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

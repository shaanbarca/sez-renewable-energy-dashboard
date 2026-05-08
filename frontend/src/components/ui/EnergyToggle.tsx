import * as ToggleGroup from '@radix-ui/react-toggle-group';
import type { EnergyMode } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

type Option =
  | { value: EnergyMode; label: string; comingSoon?: false }
  | { value: string; label: string; comingSoon: true };

// Layout: single-source modes first, then composite modes. "Soon" pills
// telegraph the v4.1+ roadmap so users see what's coming without us having
// to ship marketing copy elsewhere. Pattern mirrors LayerControl's
// "Coming soon" treatment in the layer panel.
const SINGLE_SOURCES: Option[] = [
  { value: 'solar', label: 'Solar' },
  { value: 'wind', label: 'Wind' },
  { value: 'geothermal', label: 'Geothermal' },
  { value: 'hydro', label: 'Hydro', comingSoon: true },
  { value: 'biomass', label: 'Biomass', comingSoon: true },
];

const COMPOSITE: Option[] = [
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'overall', label: 'Overall' },
];

export default function EnergyToggle() {
  const energyMode = useDashboardStore((s) => s.energyMode);
  const setEnergyMode = useDashboardStore((s) => s.setEnergyMode);

  const renderItem = (opt: Option) => {
    if (opt.comingSoon) {
      return (
        <div
          key={opt.value}
          title="Coming soon"
          className="px-2.5 py-1.5 text-xs font-medium whitespace-nowrap flex items-center gap-1 cursor-not-allowed"
          style={{ color: 'var(--text-muted)', opacity: 0.55 }}
        >
          {opt.label}
          <span
            className="text-[8px] uppercase tracking-wider px-1 py-0.5 rounded"
            style={{
              color: 'var(--text-muted)',
              border: '1px solid var(--text-muted)',
              lineHeight: 1,
            }}
          >
            Soon
          </span>
        </div>
      );
    }
    return (
      <ToggleGroup.Item
        key={opt.value}
        value={opt.value}
        className="px-2.5 py-1.5 text-xs font-medium transition-colors whitespace-nowrap cursor-pointer"
        style={{
          backgroundColor: energyMode === opt.value ? 'var(--toggle-on-bg)' : 'transparent',
          color: energyMode === opt.value ? 'var(--toggle-on-text)' : 'var(--toggle-off-text)',
        }}
      >
        {opt.label}
      </ToggleGroup.Item>
    );
  };

  return (
    <ToggleGroup.Root
      type="single"
      value={energyMode}
      onValueChange={(value) => {
        if (value) setEnergyMode(value as EnergyMode);
      }}
      className="flex rounded-lg overflow-hidden border items-stretch"
      style={{ borderColor: 'var(--glass-border-bright)' }}
    >
      {SINGLE_SOURCES.map(renderItem)}
      {/* Subtle divider between single-source and composite modes */}
      <div
        aria-hidden
        style={{
          width: 1,
          background: 'var(--glass-border)',
          alignSelf: 'stretch',
        }}
      />
      {COMPOSITE.map(renderItem)}
    </ToggleGroup.Root>
  );
}

import * as ToggleGroup from '@radix-ui/react-toggle-group';
import { useDashboardStore } from '../../store/dashboard';
import type { EnergyMode } from '../../lib/types';

const options: { value: EnergyMode; label: string }[] = [
  { value: 'solar', label: 'Solar' },
  { value: 'wind', label: 'Wind' },
  { value: 'overall', label: 'Overall' },
];

export default function EnergyToggle() {
  const energyMode = useDashboardStore((s) => s.energyMode);
  const setEnergyMode = useDashboardStore((s) => s.setEnergyMode);

  return (
    <ToggleGroup.Root
      type="single"
      value={energyMode}
      onValueChange={(value) => {
        if (value) setEnergyMode(value as EnergyMode);
      }}
      className="flex rounded-lg overflow-hidden border"
      style={{ borderColor: 'var(--glass-border-bright)' }}
    >
      {options.map((opt) => (
        <ToggleGroup.Item
          key={opt.value}
          value={opt.value}
          className="px-3 py-1.5 text-xs font-medium transition-colors data-[state=on]:bg-white/15 data-[state=on]:text-white data-[state=off]:text-zinc-500 data-[state=off]:hover:text-zinc-300"
          style={{ backgroundColor: energyMode === opt.value ? undefined : 'transparent' }}
        >
          {opt.label}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
}

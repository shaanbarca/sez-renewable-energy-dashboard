import * as RadixSlider from '@radix-ui/react-slider';

interface SliderProps {
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step: number;
  label: string;
  unit: string;
  description?: string;
  marks?: Record<string, string>;
}

export default function Slider({
  value,
  onChange,
  min,
  max,
  step,
  label,
  unit,
  description,
  marks,
}: SliderProps) {
  return (
    <div className="group py-1.5">
      <div className="flex items-center justify-between mb-1">
        <label
          className="text-[11px] text-zinc-400 leading-tight"
          title={description}
        >
          {label}
          {description && (
            <span className="ml-1 text-zinc-600 opacity-0 group-hover:opacity-100 transition-opacity cursor-help">
              ?
            </span>
          )}
        </label>
        <span className="text-[11px] font-medium text-zinc-200 tabular-nums">
          {value}
          <span className="text-zinc-500 ml-0.5">{unit}</span>
        </span>
      </div>

      <RadixSlider.Root
        className="relative flex items-center w-full h-5 select-none touch-none"
        value={[value]}
        onValueChange={([v]) => onChange(v)}
        min={min}
        max={max}
        step={step}
      >
        <RadixSlider.Track className="relative grow h-[4px] rounded-full bg-white/[0.08]">
          <RadixSlider.Range className="absolute h-full rounded-full bg-[#90CAF9]/60" />
        </RadixSlider.Track>
        <RadixSlider.Thumb
          className="block w-3.5 h-3.5 rounded-full bg-[#90CAF9] border-2 border-white/80 shadow-md
                     hover:bg-[#BBDEFB] focus:outline-none focus:ring-2 focus:ring-[#90CAF9]/40
                     transition-colors cursor-grab active:cursor-grabbing"
          aria-label={label}
        />
      </RadixSlider.Root>

      {marks && (
        <div className="flex justify-between mt-0.5 px-0.5">
          {Object.entries(marks).map(([val, lbl]) => (
            <span key={val} className="text-[9px] text-zinc-600 tabular-nums">
              {lbl}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

import * as RadixSlider from '@radix-ui/react-slider';
import { useState } from 'react';

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
  const [showTip, setShowTip] = useState(false);

  return (
    <div className="group py-1.5">
      <div className="flex items-center justify-between mb-1">
        <label
          className="text-[11px] leading-tight relative"
          style={{ color: 'var(--text-secondary)' }}
        >
          {label}
          {description && (
            <span
              className="ml-1 cursor-help inline-block"
              style={{ color: 'var(--text-muted)' }}
              onMouseEnter={() => setShowTip(true)}
              onMouseLeave={() => setShowTip(false)}
            >
              ?
              {showTip && (
                <span
                  className="absolute left-0 top-full mt-1 z-30 px-2.5 py-1.5 rounded text-[10px] leading-snug whitespace-normal w-48"
                  style={{
                    background: 'var(--popup-bg)',
                    color: 'var(--text-value)',
                    border: '1px solid var(--popup-border)',
                    boxShadow: 'var(--popup-shadow)',
                  }}
                >
                  {description}
                </span>
              )}
            </span>
          )}
        </label>
        <span
          className="text-[11px] font-medium tabular-nums"
          style={{ color: 'var(--text-value)' }}
        >
          {value}
          <span className="ml-0.5" style={{ color: 'var(--text-muted)' }}>
            {unit}
          </span>
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
        <RadixSlider.Track
          className="slider-track relative grow h-[4px] rounded-full"
          style={{ background: 'var(--bar-bg)' }}
        >
          <RadixSlider.Range className="slider-range absolute h-full rounded-full" />
        </RadixSlider.Track>
        <RadixSlider.Thumb
          className="slider-thumb block w-3.5 h-3.5 rounded-full shadow-md
                     focus:outline-none transition-colors cursor-grab active:cursor-grabbing"
          aria-label={label}
        />
      </RadixSlider.Root>

      {marks && (
        <div className="flex justify-between mt-0.5 px-0.5">
          {Object.entries(marks).map(([val, lbl]) => (
            <span
              key={val}
              className="text-[9px] tabular-nums"
              style={{ color: 'var(--text-muted)' }}
            >
              {lbl}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

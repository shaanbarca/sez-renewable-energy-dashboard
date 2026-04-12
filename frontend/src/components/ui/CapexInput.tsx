import * as RadixSlider from '@radix-ui/react-slider';
import { useEffect, useRef, useState } from 'react';
import type { SliderConfig } from '../../lib/types';

interface CapexInputProps {
  value: number;
  onChange: (value: number) => void;
  config: SliderConfig;
}

/** Accepted range for typed CAPEX values (beyond slider bounds for power users). */
const CAPEX_MIN = 0;
const CAPEX_MAX = 10000;

export default function CapexInput({ value, onChange, config }: CapexInputProps) {
  const [localText, setLocalText] = useState(String(value));
  const [invalid, setInvalid] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const [showTip, setShowTip] = useState(false);

  // Sync from store when value changes externally (reset, URL hydration)
  useEffect(() => {
    setLocalText(String(value));
    setInvalid(false);
  }, [value]);

  const commit = (raw: string) => {
    const parsed = Number.parseFloat(raw);
    if (Number.isNaN(parsed) || parsed < CAPEX_MIN) {
      setLocalText(String(value));
      setInvalid(false);
      return;
    }
    const clamped = Math.round(Math.min(CAPEX_MAX, Math.max(CAPEX_MIN, parsed)));
    onChange(clamped);
    setLocalText(String(clamped));
    setInvalid(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      commit(localText);
      inputRef.current?.blur();
    } else if (e.key === 'Escape') {
      setLocalText(String(value));
      setInvalid(false);
      inputRef.current?.blur();
    }
  };

  const handleTextChange = (raw: string) => {
    setLocalText(raw);
    const parsed = Number.parseFloat(raw);
    setInvalid(raw !== '' && (Number.isNaN(parsed) || parsed < CAPEX_MIN));
  };

  // Slider value: clamp to slider range for thumb display
  const sliderVal = Math.min(config.max, Math.max(config.min, value));

  return (
    <div className="py-1.5">
      <div className="flex items-center justify-between mb-1">
        <label
          className="text-[11px] leading-tight relative"
          style={{ color: 'var(--text-secondary)' }}
        >
          {config.label}
          {config.description && (
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
                  {config.description}
                </span>
              )}
            </span>
          )}
        </label>

        {/* Inline text input */}
        <div className="flex items-center gap-0.5 text-[11px]">
          <span style={{ color: 'var(--text-muted)' }}>$</span>
          <input
            ref={inputRef}
            type="text"
            inputMode="numeric"
            value={localText}
            onChange={(e) => handleTextChange(e.target.value)}
            onBlur={() => commit(localText)}
            onKeyDown={handleKeyDown}
            onFocus={() => inputRef.current?.select()}
            className="w-14 bg-transparent text-right font-medium tabular-nums outline-none border-b transition-colors"
            style={{
              color: invalid ? '#f87171' : 'var(--text-value)',
              borderColor: invalid ? 'rgba(248, 113, 113, 0.5)' : 'var(--border-subtle)',
            }}
          />
          <span style={{ color: 'var(--text-muted)' }}>{config.unit}</span>
        </div>
      </div>

      {/* Slider for quick exploration */}
      <RadixSlider.Root
        className="relative flex items-center w-full h-5 select-none touch-none"
        value={[sliderVal]}
        onValueChange={([v]) => onChange(v)}
        min={config.min}
        max={config.max}
        step={config.step}
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
          aria-label={config.label}
        />
      </RadixSlider.Root>

      {/* Out-of-range hint */}
      {(value < config.min || value > config.max) && (
        <div className="text-[9px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
          Custom value (slider range: {config.min}–{config.max})
        </div>
      )}
    </div>
  );
}

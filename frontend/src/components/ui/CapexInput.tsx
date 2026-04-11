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
        <label className="text-[11px] text-zinc-400 leading-tight relative">
          {config.label}
          {config.description && (
            <span
              className="ml-1 text-zinc-600 hover:text-zinc-300 cursor-help inline-block"
              onMouseEnter={() => setShowTip(true)}
              onMouseLeave={() => setShowTip(false)}
            >
              ?
              {showTip && (
                <span
                  className="absolute left-0 top-full mt-1 z-30 px-2.5 py-1.5 rounded text-[10px] text-zinc-200 leading-snug whitespace-normal w-48"
                  style={{
                    background: 'rgba(20, 20, 24, 0.95)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
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
          <span className="text-zinc-500">$</span>
          <input
            ref={inputRef}
            type="text"
            inputMode="numeric"
            value={localText}
            onChange={(e) => handleTextChange(e.target.value)}
            onBlur={() => commit(localText)}
            onKeyDown={handleKeyDown}
            onFocus={() => inputRef.current?.select()}
            className={`w-14 bg-transparent text-right font-medium tabular-nums outline-none
                       border-b transition-colors
                       ${invalid ? 'text-red-400 border-red-400/50' : 'text-zinc-200 border-zinc-700 focus:border-[#90CAF9]/60'}`}
          />
          <span className="text-zinc-500">{config.unit}</span>
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
        <RadixSlider.Track className="relative grow h-[4px] rounded-full bg-white/[0.08]">
          <RadixSlider.Range className="absolute h-full rounded-full bg-[#90CAF9]/60" />
        </RadixSlider.Track>
        <RadixSlider.Thumb
          className="block w-3.5 h-3.5 rounded-full bg-[#90CAF9] border-2 border-white/80 shadow-md
                     hover:bg-[#BBDEFB] focus:outline-none focus:ring-2 focus:ring-[#90CAF9]/40
                     transition-colors cursor-grab active:cursor-grabbing"
          aria-label={config.label}
        />
      </RadixSlider.Root>

      {/* Out-of-range hint */}
      {(value < config.min || value > config.max) && (
        <div className="text-[9px] text-zinc-600 mt-0.5">
          Custom value (slider range: {config.min}–{config.max})
        </div>
      )}
    </div>
  );
}

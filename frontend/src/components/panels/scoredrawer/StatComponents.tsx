import { useState } from 'react';

export function CloseIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

export function StatRow({
  label,
  value,
  unit,
}: {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
}) {
  const display = value == null || value === '' ? 'N/A' : `${value}${unit ? ` ${unit}` : ''}`;
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
        {label}
      </span>
      <span className="text-[12px] font-medium tabular-nums" style={{ color: 'var(--text-value)' }}>
        {display}
      </span>
    </div>
  );
}

export function StatRowWithTip({
  label,
  value,
  unit,
  tip,
}: {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  tip: string;
}) {
  const [showTip, setShowTip] = useState(false);
  const display = value == null || value === '' ? 'N/A' : `${value}${unit ? ` ${unit}` : ''}`;
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-[11px] relative" style={{ color: 'var(--text-muted)' }}>
        {label}
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
              {tip}
            </span>
          )}
        </span>
      </span>
      <span className="text-[12px] font-medium tabular-nums" style={{ color: 'var(--text-value)' }}>
        {display}
      </span>
    </div>
  );
}

export function ColoredStatRow({
  label,
  value,
  unit,
  tip,
  color,
}: {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  tip?: string;
  color?: string;
}) {
  const [showTip, setShowTip] = useState(false);
  const display = value == null || value === '' ? 'N/A' : `${value}${unit ? ` ${unit}` : ''}`;
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-[11px] relative" style={{ color: 'var(--text-muted)' }}>
        {label}
        {tip && (
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
                {tip}
              </span>
            )}
          </span>
        )}
      </span>
      <span
        className="text-[12px] font-medium tabular-nums"
        style={{ color: color ?? 'var(--text-value)' }}
      >
        {display}
      </span>
    </div>
  );
}

export function StatCard({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="rounded-md px-3 py-2 mb-2"
      style={{
        background: 'var(--card-bg)',
        border: '1px solid var(--card-border)',
      }}
    >
      {children}
    </div>
  );
}

export function SectionHeader({
  title,
  tip,
  subtitle,
}: {
  title: string;
  tip?: string;
  subtitle?: string;
}) {
  const [showTip, setShowTip] = useState(false);
  return (
    <div className="mb-1.5 relative">
      <div className="text-[11px] font-medium" style={{ color: 'var(--text-muted)' }}>
        {title}
        {tip && (
          <span
            className="ml-1 cursor-help inline-block"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={() => setShowTip(true)}
            onMouseLeave={() => setShowTip(false)}
          >
            ?
            {showTip && (
              <span
                className="absolute left-0 top-full mt-1 z-30 px-2.5 py-1.5 rounded text-[10px] leading-snug whitespace-normal w-52"
                style={{
                  background: 'var(--popup-bg)',
                  color: 'var(--text-value)',
                  border: '1px solid var(--popup-border)',
                  boxShadow: 'var(--popup-shadow)',
                }}
              >
                {tip}
              </span>
            )}
          </span>
        )}
      </div>
      {subtitle && (
        <div
          className="text-[10px] leading-snug mt-0.5"
          style={{ color: 'var(--text-muted)', opacity: 0.7 }}
        >
          {subtitle}
        </div>
      )}
    </div>
  );
}

export function FlagStep({
  label,
  color,
  active,
  above,
  isFirst,
  isLast,
  explanation,
}: {
  label: string;
  color: string;
  active: boolean;
  above: boolean;
  isFirst: boolean;
  isLast: boolean;
  explanation?: string;
}) {
  const dotSize = active ? 12 : 8;
  const dotColor = active ? color : above ? 'var(--border-subtle)' : `${color}55`;
  const trackColor = isLast ? 'transparent' : 'var(--border-subtle)';

  return (
    <div className="flex gap-0">
      <div className="flex flex-col items-center shrink-0" style={{ width: 20 }}>
        <div
          style={{
            width: 2,
            height: 6,
            background: isFirst ? 'transparent' : 'var(--border-subtle)',
          }}
        />
        <div
          className="rounded-full shrink-0"
          style={{
            width: dotSize,
            height: dotSize,
            background: dotColor,
            boxShadow: active ? `0 0 8px ${color}66` : 'none',
          }}
        />
        <div
          className="flex-1"
          style={{
            width: 2,
            background: trackColor,
            minHeight: 6,
          }}
        />
      </div>
      <div className="pl-2 flex-1 pb-1">
        <div className="flex items-center" style={{ minHeight: dotSize + 12 }}>
          <span
            className={`text-[11px] ${active ? 'font-medium' : ''}`}
            style={{
              color: active ? color : above ? 'var(--text-muted)' : 'var(--text-secondary)',
              opacity: active ? 1 : above ? 0.5 : 0.7,
            }}
          >
            {label}
          </span>
        </div>
        {active && explanation && (
          <p
            className="text-[10px] leading-relaxed pb-1"
            style={{ color: 'var(--text-secondary)' }}
          >
            {explanation}
          </p>
        )}
      </div>
    </div>
  );
}

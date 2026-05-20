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
  trailing,
}: {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  tip: string;
  /** Optional element rendered after the value (e.g. a TierPill badge). v4.3 M-AT8b. */
  trailing?: React.ReactNode;
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
      <span
        className="text-[12px] font-medium tabular-nums inline-flex items-center cursor-help"
        style={{ color: 'var(--text-value)' }}
        title={tip}
      >
        {display}
        {trailing}
      </span>
    </div>
  );
}

/**
 * Pill — small colored chip with a styled hover popup. Use for categorical
 * values where the label alone doesn't tell the reader what it means (OSM,
 * Estimated, No polygon, low confidence, etc.).
 *
 * The popup is anchored to the right edge of the pill so it stays within the
 * drawer width when the pill sits on the right side of a row.
 */
export function Pill({
  label,
  color,
  bg,
  fg,
  borderColor,
  tip,
  align = 'right',
  rounded = 'full',
  textTransform,
}: {
  label: string;
  /** Single accent color — derives bg/border from it. Mutually exclusive with bg/fg. */
  color?: string;
  /** Explicit background (overrides color). Use for legacy palettes already
   *  in the codebase (e.g. RooftopPotentialTable's rgba-based badges). */
  bg?: string;
  /** Explicit text color (overrides color). */
  fg?: string;
  /** Optional explicit border color. Falls back to `${color}55` when color is set. */
  borderColor?: string;
  tip: string;
  /** Side of the pill the popup is anchored to. */
  align?: 'left' | 'right';
  /** Pill shape — 'full' for tag/chip look, 'sm' for table-cell look. */
  rounded?: 'full' | 'sm';
  /** Optional text-transform — e.g. 'uppercase' for table-cell tags. */
  textTransform?: 'uppercase' | 'capitalize' | 'none';
}) {
  const [showTip, setShowTip] = useState(false);
  const resolvedBg = bg ?? (color ? `${color}22` : 'transparent');
  const resolvedFg = fg ?? color ?? 'inherit';
  const resolvedBorder = borderColor ?? (color ? `${color}55` : 'transparent');
  return (
    <span
      className="relative inline-flex items-center"
      onMouseEnter={() => setShowTip(true)}
      onMouseLeave={() => setShowTip(false)}
    >
      <span
        className={`text-[10px] font-medium px-1.5 py-0.5 cursor-help ${rounded === 'full' ? 'rounded-full' : 'rounded'}`}
        style={{
          backgroundColor: resolvedBg,
          color: resolvedFg,
          border: `1px solid ${resolvedBorder}`,
          textTransform,
          letterSpacing: textTransform === 'uppercase' ? '0.04em' : undefined,
          fontWeight: textTransform === 'uppercase' ? 600 : 500,
        }}
      >
        {label}
      </span>
      {showTip && (
        <span
          className="absolute top-full mt-1 z-30 px-2.5 py-1.5 rounded text-[10px] leading-snug whitespace-normal w-56"
          style={{
            background: 'var(--popup-bg)',
            color: 'var(--text-value)',
            border: '1px solid var(--popup-border)',
            boxShadow: 'var(--popup-shadow)',
            ...(align === 'right' ? { right: 0 } : { left: 0 }),
          }}
        >
          {tip}
        </span>
      )}
    </span>
  );
}

export function ColoredStatRow({
  label,
  value,
  unit,
  tip,
  color,
  trailing,
}: {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  tip?: string;
  color?: string;
  /** Optional element rendered after the value. v4.3 M-AT8b. */
  trailing?: React.ReactNode;
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
        className="text-[12px] font-medium tabular-nums inline-flex items-center"
        style={{ color: color ?? 'var(--text-value)' }}
      >
        {display}
        {trailing}
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

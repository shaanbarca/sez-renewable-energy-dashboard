import { useState } from 'react';
import { createPortal } from 'react-dom';

interface HelpBadgeProps {
  tip: string;
  className?: string;
  widthClass?: string;
}

export default function HelpBadge({
  tip,
  className = 'ml-1',
  widthClass = 'w-48',
}: HelpBadgeProps) {
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);

  const show = (el: HTMLElement) => {
    const r = el.getBoundingClientRect();
    setPos({ top: r.bottom + 4, left: r.left });
  };

  return (
    <span
      className={`cursor-help inline-block ${className}`}
      style={{ color: 'var(--text-muted)' }}
      onMouseEnter={(e) => show(e.currentTarget)}
      onMouseLeave={() => setPos(null)}
    >
      ?
      {pos &&
        createPortal(
          <span
            className={`fixed z-[9999] px-2.5 py-1.5 rounded text-[10px] leading-snug whitespace-normal pointer-events-none ${widthClass}`}
            style={{
              top: pos.top,
              left: pos.left,
              background: 'var(--popup-bg)',
              color: 'var(--text-value)',
              border: '1px solid var(--popup-border)',
              boxShadow: 'var(--popup-shadow)',
            }}
          >
            {tip}
          </span>,
          document.body,
        )}
    </span>
  );
}

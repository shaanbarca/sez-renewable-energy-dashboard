import { useState } from 'react';
import { createPortal } from 'react-dom';
import {
  MODIFIER_BADGE_COLORS,
  MODIFIER_BADGE_DESCRIPTIONS,
  MODIFIER_BADGE_LABELS,
} from '../../lib/constants';
import type { ModifierBadge } from '../../lib/types';

interface ModifierBadgePillProps {
  badge: ModifierBadge;
  size?: 'sm' | 'md';
}

export default function ModifierBadgePill({ badge, size = 'sm' }: ModifierBadgePillProps) {
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const color = MODIFIER_BADGE_COLORS[badge];
  const label = MODIFIER_BADGE_LABELS[badge];
  const desc = MODIFIER_BADGE_DESCRIPTIONS[badge];

  const show = (el: HTMLElement) => {
    const r = el.getBoundingClientRect();
    setPos({ top: r.bottom + 6, left: r.left });
  };

  const pillClass =
    size === 'sm'
      ? 'text-[9px] px-1.5 py-0.5 rounded-full font-medium cursor-help'
      : 'text-[10px] px-2 py-0.5 rounded-full font-medium cursor-help';

  return (
    <span
      className={pillClass}
      style={{
        backgroundColor: `${color}22`,
        color: color,
        border: `1px solid ${color}44`,
      }}
      onMouseEnter={(e) => show(e.currentTarget)}
      onMouseLeave={() => setPos(null)}
    >
      {label}
      {pos &&
        createPortal(
          <span
            className="fixed z-[9999] px-3 py-2 rounded text-[10px] leading-snug whitespace-normal pointer-events-none w-64"
            style={{
              top: pos.top,
              left: pos.left,
              background: 'var(--popup-bg)',
              color: 'var(--text-value)',
              border: '1px solid var(--popup-border)',
              boxShadow: 'var(--popup-shadow)',
            }}
          >
            <span className="block font-semibold mb-1" style={{ color }}>
              {label}
            </span>
            {desc}
          </span>,
          document.body,
        )}
    </span>
  );
}

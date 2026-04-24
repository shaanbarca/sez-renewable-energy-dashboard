import { useEffect, useState } from 'react';
import { useDashboardStore } from '../../store/dashboard';

const DISMISSED_KEY = 'map_hint_seen';

// First-landing wayfinding. Shows a subtle center-map hint the first time a
// user opens the dashboard. Once they click any marker, the hint is marked
// as seen in localStorage and never shows again, even after reload or after
// they return to the national view. Onboarding once, not a persistent chrome.
export default function MapHint() {
  const selectedSite = useDashboardStore((s) => s.selectedSite);
  const scorecard = useDashboardStore((s) => s.scorecard);

  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem(DISMISSED_KEY) === 'true';
    } catch {
      return false;
    }
  });

  // First marker click marks the hint as dismissed forever.
  useEffect(() => {
    if (selectedSite && !dismissed) {
      try {
        localStorage.setItem(DISMISSED_KEY, 'true');
      } catch {}
      setDismissed(true);
    }
  }, [selectedSite, dismissed]);

  if (dismissed) return null;
  if (selectedSite) return null;
  const total = scorecard?.length ?? 0;
  if (total === 0) return null;

  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        top: '50%',
        transform: 'translate(-50%, -50%)',
        padding: '10px 18px',
        background: 'rgba(18, 18, 22, 0.7)',
        backdropFilter: 'blur(20px) saturate(1.3)',
        WebkitBackdropFilter: 'blur(20px) saturate(1.3)',
        border: '1px solid var(--glass-border-bright)',
        borderRadius: 999,
        boxShadow: '0 8px 28px rgba(0, 0, 0, 0.35)',
        color: 'var(--text-secondary)',
        fontSize: 12,
        fontFamily: 'inherit',
        pointerEvents: 'none',
        zIndex: 5,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        whiteSpace: 'nowrap',
        opacity: 0.85,
      }}
    >
      <span
        className="tnum"
        style={{
          fontVariantNumeric: 'tabular-nums',
          color: 'var(--text-primary)',
          fontWeight: 600,
        }}
      >
        {total} sites
      </span>
      <span>across Indonesia</span>
      <span style={{ color: 'var(--text-muted)' }}>·</span>
      <span style={{ color: 'var(--accent)' }}>Click a marker to explore</span>
    </div>
  );
}

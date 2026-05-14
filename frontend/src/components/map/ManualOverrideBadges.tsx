// ManualOverrideBadges — small "M" pill overlaid on site markers that have
// a manual_override polygon (#31 phase 3).
//
// Only renders when adminMode is true; production never sees these. Lets a
// local operator scan the whole map at a glance and see which sites have
// been hand-corrected vs which still rely on auto-generated polygons.
//
// Implemented as react-map-gl Markers (one per overridden site) rather than
// a MapLibre layer because the styling is React-friendly and the count is
// tiny (at most 81 markers — total fleet size).

import { Marker } from 'react-map-gl/maplibre';
import { useDashboardStore } from '../../store/dashboard';

export default function ManualOverrideBadges() {
  const adminMode = useDashboardStore((s) => s.adminMode);
  const overrideIds = useDashboardStore((s) => s.manualOverrideSiteIds);
  const scorecard = useDashboardStore((s) => s.scorecard);

  if (!adminMode || overrideIds.size === 0 || !scorecard) return null;

  // Look up each overridden site's lat/lon from the scorecard.
  const overrideRows = scorecard.filter((r) => overrideIds.has(r.site_id));
  if (overrideRows.length === 0) return null;

  return (
    <>
      {overrideRows.map((row) => (
        <Marker
          key={`override-${row.site_id}`}
          longitude={row.longitude}
          latitude={row.latitude}
          anchor="center"
          offset={[10, -10]}
        >
          <div
            className="rounded-full flex items-center justify-center"
            style={{
              width: 14,
              height: 14,
              background: '#FF9800',
              color: '#1a1a1a',
              fontSize: 8,
              fontWeight: 700,
              border: '1.5px solid #fff',
              boxShadow: '0 1px 2px rgba(0,0,0,0.4)',
              pointerEvents: 'none',
            }}
            title={`Manual polygon override for ${row.site_name}`}
          >
            M
          </div>
        </Marker>
      ))}
    </>
  );
}

import { useEffect, useMemo, useRef } from 'react';
import { Layer, Popup, Source, useMap } from 'react-map-gl/maplibre';
import {
  getEconomicTierLabel,
  getEffectiveActionFlag,
  getEffectiveEconomicTier,
  getEffectiveInfraReadiness,
} from '../../lib/actionFlags';
import { ECONOMIC_TIER_COLORS, INFRA_READINESS_LABELS } from '../../lib/constants';
import { registerSectorIcons } from '../../lib/sectorIcons';
import type { Sector } from '../../lib/siteTypes';
import type { ActionFlag, EconomicTier, InfrastructureReadiness } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

interface HoverInfo {
  longitude: number;
  latitude: number;
  site_name: string;
  action_flag: ActionFlag;
  economic_tier: EconomicTier;
  infrastructure_readiness: InfrastructureReadiness;
  province: string;
  site_type: string;
  category: string;
  area_ha: number | null;
  cbam_exposed: boolean;
}

interface SiteMarkersProps {
  hoverInfo: HoverInfo | null;
}

const PULSE_DURATION_MS = 5000;
const PULSE_CYCLES = 3;

export default function SiteMarkers({ hoverInfo }: SiteMarkersProps) {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const selectedSite = useDashboardStore((s) => s.selectedSite);
  const { current: mapInstance } = useMap();
  const hasPulsed = useRef(false);
  const prevFlagsRef = useRef<Record<string, string>>({});
  const animIdRef = useRef<number>(0);
  const timeoutIdRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Register sector pictogram SDF icons with the map. They render as the white
  // silhouette inside the coloured marker disc. Safe to call repeatedly —
  // `registerSectorIcons` skips any image that already exists.
  useEffect(() => {
    if (!mapInstance) return;
    const map = mapInstance.getMap();
    const install = () => registerSectorIcons(map);
    if (map.isStyleLoaded()) install();
    else map.once('load', install);
    map.on('styledata', install);
    return () => {
      map.off('styledata', install);
    };
  }, [mapInstance]);

  // Pulse animation — runs on first load (all markers) and on flag changes (affected markers only)
  useEffect(() => {
    if (!scorecard || !mapInstance) return;

    const map = mapInstance.getMap();

    // Build current flag map
    const currentFlags: Record<string, string> = {};
    for (const row of scorecard) {
      currentFlags[row.site_id] = row.action_flag;
    }

    // Determine which KEKs to pulse
    let changedSiteIds: string[];
    if (!hasPulsed.current) {
      // First load: pulse all
      hasPulsed.current = true;
      changedSiteIds = scorecard.map((r) => r.site_id);
    } else {
      // Subsequent updates: only pulse sites whose action_flag changed
      const prev = prevFlagsRef.current;
      changedSiteIds = [];
      for (const row of scorecard) {
        if (prev[row.site_id] != null && prev[row.site_id] !== row.action_flag) {
          changedSiteIds.push(row.site_id);
        }
      }
    }

    prevFlagsRef.current = currentFlags;

    if (changedSiteIds.length === 0) return;

    // Set filter on pulse layer to only show changed markers
    const isInitial = changedSiteIds.length === scorecard.length;
    const duration = PULSE_DURATION_MS;

    if (map.getLayer('kek-pulse')) {
      if (isInitial) {
        map.setFilter('kek-pulse', null);
      } else {
        map.setFilter('kek-pulse', ['in', ['get', 'site_id'], ['literal', changedSiteIds]]);
      }
    }

    // Cancel any running animation and pending timeout
    cancelAnimationFrame(animIdRef.current);
    if (timeoutIdRef.current != null) clearTimeout(timeoutIdRef.current);

    const start = performance.now();

    const animate = (now: number) => {
      const elapsed = now - start;
      if (elapsed > duration) {
        if (map.getLayer('kek-pulse')) {
          map.setPaintProperty('kek-pulse', 'circle-opacity', 0);
          map.setPaintProperty('kek-pulse', 'circle-radius', 0);
        }
        return;
      }
      const t = elapsed / duration;
      const wave = Math.sin(t * PULSE_CYCLES * 2 * Math.PI);
      const fadeOut = 1 - t;
      const radius = 6 + wave * 6;
      const opacity = Math.max(0, 0.35 * fadeOut * ((wave + 1) / 2));

      if (map.getLayer('kek-pulse')) {
        map.setPaintProperty('kek-pulse', 'circle-radius', radius);
        map.setPaintProperty('kek-pulse', 'circle-opacity', opacity);
      }
      animIdRef.current = requestAnimationFrame(animate);
    };

    timeoutIdRef.current = setTimeout(() => {
      animIdRef.current = requestAnimationFrame(animate);
    }, 200);

    return () => {
      cancelAnimationFrame(animIdRef.current);
      if (timeoutIdRef.current != null) clearTimeout(timeoutIdRef.current);
    };
  }, [scorecard, mapInstance]);

  const energyMode = useDashboardStore((s) => s.energyMode);
  const filteredSiteIds = useDashboardStore((s) => s.filteredSiteIds);

  const geojson = useMemo(() => {
    if (!scorecard) return null;
    const rows = filteredSiteIds
      ? scorecard.filter((r) => filteredSiteIds.has(r.site_id))
      : scorecard;
    return {
      type: 'FeatureCollection' as const,
      features: rows.map((row) => ({
        type: 'Feature' as const,
        geometry: {
          type: 'Point' as const,
          coordinates: [row.longitude, row.latitude],
        },
        properties: {
          site_id: row.site_id,
          site_name: row.site_name,
          action_flag: getEffectiveActionFlag(row, energyMode),
          economic_tier: getEffectiveEconomicTier(row, energyMode),
          province: row.province,
          site_type: row.site_type ?? '',
          sector: (row.sector as Sector) ?? 'mixed',
          category: row.category ?? '',
          area_ha: row.area_ha ?? null,
          grid_integration_category: row.grid_integration_category ?? '',
          infrastructure_readiness: getEffectiveInfraReadiness(row),
          cbam_exposed: row.cbam_exposed ?? false,
        },
      })),
    };
  }, [scorecard, energyMode, filteredSiteIds]);

  // Build the match expression for circle-color from economic tier
  const colorMatch = useMemo(() => {
    const entries: (string | string[])[] = ['match', ['get', 'economic_tier']];
    for (const [tier, color] of Object.entries(ECONOMIC_TIER_COLORS)) {
      entries.push(tier, color);
    }
    entries.push('#999999'); // fallback
    return entries;
  }, []);

  // Build the match expression for circle-stroke-color from infrastructure readiness
  const infraStrokeMatch = useMemo(() => {
    const entries: (string | string[])[] = ['match', ['get', 'infrastructure_readiness']];
    entries.push('within_boundary', '#ffffff');
    entries.push('grid_ready', '#ffffff');
    entries.push('invest_transmission', '#42A5F5');
    entries.push('invest_substation', '#00838F');
    entries.push('grid_first', '#1565C0');
    entries.push('#ffffff'); // fallback
    return entries;
  }, []);

  // Zoom-responsive circle radius for the coloured marker background.
  // Sized so the white pictogram inside is legible at every zoom — including
  // continental zoom-out, not just close-up.
  const circleRadius = useMemo(
    () =>
      [
        'interpolate',
        ['linear'],
        ['zoom'],
        4,
        ['case', ['==', ['get', 'site_id'], selectedSite ?? ''], 9, 7],
        7,
        ['case', ['==', ['get', 'site_id'], selectedSite ?? ''], 12, 9.5],
        9,
        ['case', ['==', ['get', 'site_id'], selectedSite ?? ''], 15, 12],
      ] as unknown as number,
    [selectedSite],
  );

  // CBAM = circular amber ring sized just outside the marker bg. Now that the
  // marker base is itself a circle, a circular ring is the right shape (no
  // mismatch between ring and silhouette).
  const cbamRingRadius = useMemo(
    () =>
      [
        'interpolate',
        ['linear'],
        ['zoom'],
        4,
        ['case', ['==', ['get', 'site_id'], selectedSite ?? ''], 12, 10],
        7,
        ['case', ['==', ['get', 'site_id'], selectedSite ?? ''], 15, 12.5],
        9,
        ['case', ['==', ['get', 'site_id'], selectedSite ?? ''], 18, 15],
      ] as unknown as number,
    [selectedSite],
  );

  // White pictogram inside the circle. SDF is 64px, so icon-size 0.22 ≈ 14px.
  // Scaled to fill ~75% of the circle diameter at every zoom so the icon
  // is visible at continental zoom too — not just close-up.
  const pictogramSize = useMemo(
    () =>
      [
        'interpolate',
        ['linear'],
        ['zoom'],
        4,
        ['case', ['==', ['get', 'site_id'], selectedSite ?? ''], 0.26, 0.2],
        7,
        ['case', ['==', ['get', 'site_id'], selectedSite ?? ''], 0.34, 0.26],
        9,
        ['case', ['==', ['get', 'site_id'], selectedSite ?? ''], 0.42, 0.32],
      ] as unknown as number,
    [selectedSite],
  );

  if (!geojson) return null;

  return (
    <>
      <Source id="kek-markers" type="geojson" data={geojson}>
        {/* Pulse ring layer — animated on first load, then hidden */}
        <Layer
          id="kek-pulse"
          type="circle"
          paint={{
            'circle-radius': 6,
            'circle-color': colorMatch as unknown as string,
            'circle-stroke-width': 0,
            'circle-opacity': 0,
          }}
        />
        {/* CBAM exposure — circular amber ring sitting just outside the marker
            background. The bg is itself a circle now, so a circular ring is
            the right shape (no silhouette mismatch). */}
        <Layer
          id="kek-cbam-ring"
          type="circle"
          filter={['==', ['get', 'cbam_exposed'], true]}
          paint={{
            'circle-radius': cbamRingRadius,
            'circle-color': 'rgba(0,0,0,0)',
            'circle-stroke-color': '#FF6F00',
            'circle-stroke-width': [
              'case',
              ['==', ['get', 'site_id'], selectedSite ?? ''],
              2.5,
              1.5,
            ],
            'circle-stroke-opacity': [
              'case',
              ['==', ['get', 'site_id'], selectedSite ?? ''],
              0.95,
              0.7,
            ],
          }}
        />
        {/* Marker background — coloured disc encoding economic tier (fill) and
            infrastructure readiness (stroke). Same visual vocabulary as the
            captive-power overlay icons (red/grey badges). */}
        <Layer
          id="kek-circles"
          type="circle"
          paint={{
            'circle-radius': circleRadius,
            'circle-color': colorMatch as unknown as string,
            'circle-stroke-color': infraStrokeMatch as unknown as string,
            'circle-stroke-width': [
              'case',
              ['==', ['get', 'site_id'], selectedSite ?? ''],
              2.5,
              1.5,
            ],
            'circle-opacity': 0.95,
          }}
        />
        {/* White sector pictogram on top of the disc. Always visible — the
            user wants the icon legible at continental zoom too, not just up
            close. Disc is sized to keep the pictogram readable at every zoom. */}
        <Layer
          id="kek-pictogram"
          type="symbol"
          layout={{
            'icon-image': ['concat', 'sector-icon-', ['get', 'sector']] as unknown as string,
            'icon-size': pictogramSize,
            'icon-allow-overlap': true,
            'icon-ignore-placement': true,
            'icon-anchor': 'center',
          }}
          paint={{
            'icon-color': '#ffffff',
          }}
        />
      </Source>
      {hoverInfo && (
        <Popup
          longitude={hoverInfo.longitude}
          latitude={hoverInfo.latitude}
          closeButton={false}
          closeOnClick={false}
          anchor="bottom"
          offset={12}
          className="kek-tooltip"
        >
          <div style={{ color: 'var(--text-primary)', fontSize: 11, lineHeight: 1.5 }}>
            <strong style={{ fontSize: 12 }}>{hoverInfo.site_name}</strong>
            <div style={{ color: 'var(--text-secondary)', marginTop: 2 }}>
              {hoverInfo.province}
              {hoverInfo.site_type ? ` · ${hoverInfo.site_type}` : ''}
            </div>
            {hoverInfo.category && (
              <div style={{ color: 'var(--text-secondary)' }}>{hoverInfo.category}</div>
            )}
            {hoverInfo.area_ha != null && (
              <div style={{ color: 'var(--text-secondary)' }}>
                {hoverInfo.area_ha.toLocaleString(undefined, { maximumFractionDigits: 0 })} ha
              </div>
            )}
            <div style={{ marginTop: 2 }}>
              <span
                style={{
                  color: ECONOMIC_TIER_COLORS[hoverInfo.economic_tier] ?? '#999',
                  fontWeight: 500,
                }}
              >
                {getEconomicTierLabel(hoverInfo.economic_tier, energyMode)}
              </span>
              {hoverInfo.cbam_exposed && (
                <span style={{ color: '#FF6F00', fontWeight: 500, marginLeft: 4 }}>CBAM</span>
              )}
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 10 }}>
              {INFRA_READINESS_LABELS[hoverInfo.infrastructure_readiness] ?? ''}
            </div>
          </div>
        </Popup>
      )}
    </>
  );
}

export type { HoverInfo };

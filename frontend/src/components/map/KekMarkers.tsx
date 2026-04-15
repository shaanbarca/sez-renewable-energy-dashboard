import { useEffect, useMemo, useRef } from 'react';
import { Layer, Popup, Source, useMap } from 'react-map-gl/maplibre';
import { getEffectiveActionFlag } from '../../lib/actionFlags';
import { ACTION_FLAG_COLORS, ACTION_FLAG_LABELS } from '../../lib/constants';
import type { ActionFlag } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';

interface HoverInfo {
  longitude: number;
  latitude: number;
  kek_name: string;
  action_flag: ActionFlag;
  province: string;
  kek_type: string;
  category: string;
  area_ha: number | null;
  cbam_exposed: boolean;
}

interface KekMarkersProps {
  hoverInfo: HoverInfo | null;
}

const PULSE_DURATION_MS = 5000;
const PULSE_CYCLES = 3;

export default function KekMarkers({ hoverInfo }: KekMarkersProps) {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const selectedKek = useDashboardStore((s) => s.selectedKek);
  const { current: mapInstance } = useMap();
  const hasPulsed = useRef(false);
  const prevFlagsRef = useRef<Record<string, string>>({});
  const animIdRef = useRef<number>(0);
  const timeoutIdRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Pulse animation — runs on first load (all markers) and on flag changes (affected markers only)
  useEffect(() => {
    if (!scorecard || !mapInstance) return;

    const map = mapInstance.getMap();

    // Build current flag map
    const currentFlags: Record<string, string> = {};
    for (const row of scorecard) {
      currentFlags[row.kek_id] = row.action_flag;
    }

    // Determine which KEKs to pulse
    let changedKekIds: string[];
    if (!hasPulsed.current) {
      // First load: pulse all
      hasPulsed.current = true;
      changedKekIds = scorecard.map((r) => r.kek_id);
    } else {
      // Subsequent updates: only pulse KEKs whose action_flag changed
      const prev = prevFlagsRef.current;
      changedKekIds = [];
      for (const row of scorecard) {
        if (prev[row.kek_id] != null && prev[row.kek_id] !== row.action_flag) {
          changedKekIds.push(row.kek_id);
        }
      }
    }

    prevFlagsRef.current = currentFlags;

    if (changedKekIds.length === 0) return;

    // Set filter on pulse layer to only show changed markers
    const isInitial = changedKekIds.length === scorecard.length;
    const duration = PULSE_DURATION_MS;

    if (map.getLayer('kek-pulse')) {
      if (isInitial) {
        map.setFilter('kek-pulse', null);
      } else {
        map.setFilter('kek-pulse', ['in', ['get', 'kek_id'], ['literal', changedKekIds]]);
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

  const geojson = useMemo(() => {
    if (!scorecard) return null;
    return {
      type: 'FeatureCollection' as const,
      features: scorecard.map((row) => ({
        type: 'Feature' as const,
        geometry: {
          type: 'Point' as const,
          coordinates: [row.longitude, row.latitude],
        },
        properties: {
          kek_id: row.kek_id,
          kek_name: row.kek_name,
          action_flag: getEffectiveActionFlag(row, energyMode),
          province: row.province,
          kek_type: row.kek_type ?? '',
          category: row.category ?? '',
          area_ha: row.area_ha ?? null,
          grid_integration_category: row.grid_integration_category ?? '',
          cbam_exposed: row.cbam_exposed ?? false,
        },
      })),
    };
  }, [scorecard, energyMode]);

  // Build the match expression for circle-color from constants
  const colorMatch = useMemo(() => {
    const entries: (string | string[])[] = ['match', ['get', 'action_flag']];
    for (const [flag, color] of Object.entries(ACTION_FLAG_COLORS)) {
      entries.push(flag, color);
    }
    entries.push('#999999'); // fallback
    return entries;
  }, []);

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
        <Layer
          id="kek-circles"
          type="circle"
          paint={{
            'circle-radius': ['case', ['==', ['get', 'kek_id'], selectedKek ?? ''], 8, 6],
            'circle-color': colorMatch as unknown as string,
            'circle-stroke-color': '#ffffff',
            'circle-stroke-width': ['case', ['==', ['get', 'kek_id'], selectedKek ?? ''], 2.5, 1],
            'circle-opacity': 0.9,
          }}
        />
        {/* CBAM exposure ring — amber outline on CBAM-exposed KEKs */}
        <Layer
          id="kek-cbam-ring"
          type="circle"
          filter={['==', ['get', 'cbam_exposed'], true]}
          paint={{
            'circle-radius': ['case', ['==', ['get', 'kek_id'], selectedKek ?? ''], 11, 9],
            'circle-color': 'transparent',
            'circle-stroke-color': '#FF6F00',
            'circle-stroke-width': 1.5,
            'circle-opacity': 0.8,
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
            <strong style={{ fontSize: 12 }}>{hoverInfo.kek_name}</strong>
            <div style={{ color: 'var(--text-secondary)', marginTop: 2 }}>
              {hoverInfo.province}
              {hoverInfo.kek_type ? ` · ${hoverInfo.kek_type}` : ''}
            </div>
            {hoverInfo.category && (
              <div style={{ color: 'var(--text-secondary)' }}>{hoverInfo.category}</div>
            )}
            {hoverInfo.area_ha != null && (
              <div style={{ color: 'var(--text-secondary)' }}>
                {hoverInfo.area_ha.toLocaleString(undefined, { maximumFractionDigits: 0 })} ha
              </div>
            )}
            <span
              style={{
                color: ACTION_FLAG_COLORS[hoverInfo.action_flag] ?? '#999',
                fontWeight: 500,
              }}
            >
              {ACTION_FLAG_LABELS[hoverInfo.action_flag] ?? hoverInfo.action_flag}
            </span>
            {hoverInfo.cbam_exposed && (
              <span style={{ color: '#FF6F00', fontWeight: 500, marginLeft: 4 }}>CBAM</span>
            )}
          </div>
        </Popup>
      )}
    </>
  );
}

export type { HoverInfo };

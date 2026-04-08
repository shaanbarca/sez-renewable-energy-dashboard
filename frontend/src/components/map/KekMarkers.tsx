import { useEffect, useMemo, useRef } from 'react';
import { Layer, Popup, Source, useMap } from 'react-map-gl/maplibre';
import { ACTION_FLAG_COLORS, ACTION_FLAG_LABELS } from '../../lib/constants';
import { useDashboardStore } from '../../store/dashboard';

interface HoverInfo {
  longitude: number;
  latitude: number;
  kek_name: string;
  action_flag: string;
  province: string;
  kek_type: string;
  category: string;
  area_ha: number | null;
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

  // Pulse animation on first scorecard load
  useEffect(() => {
    if (!scorecard || hasPulsed.current || !mapInstance) return;
    hasPulsed.current = true;

    const map = mapInstance.getMap();
    const start = performance.now();
    let animId: number;

    const animate = (now: number) => {
      const elapsed = now - start;
      if (elapsed > PULSE_DURATION_MS) {
        // Animation done, hide pulse layer
        if (map.getLayer('kek-pulse')) {
          map.setPaintProperty('kek-pulse', 'circle-opacity', 0);
          map.setPaintProperty('kek-pulse', 'circle-radius', 0);
        }
        return;
      }
      const t = elapsed / PULSE_DURATION_MS;
      // Sine wave pulse: 3 full cycles over the duration, fading out
      const wave = Math.sin(t * PULSE_CYCLES * 2 * Math.PI);
      const fadeOut = 1 - t; // linear fade from 1 to 0
      const radius = 6 + wave * 6; // 0 to 12
      const opacity = Math.max(0, 0.35 * fadeOut * ((wave + 1) / 2));

      if (map.getLayer('kek-pulse')) {
        map.setPaintProperty('kek-pulse', 'circle-radius', radius);
        map.setPaintProperty('kek-pulse', 'circle-opacity', opacity);
      }
      animId = requestAnimationFrame(animate);
    };

    // Small delay to let the layer render first
    setTimeout(() => {
      animId = requestAnimationFrame(animate);
    }, 500);

    return () => cancelAnimationFrame(animId);
  }, [scorecard, mapInstance]);

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
          action_flag: row.action_flag,
          province: row.province,
          kek_type: row.kek_type ?? '',
          category: row.category ?? '',
          area_ha: row.area_ha ?? null,
        },
      })),
    };
  }, [scorecard]);

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
          <div style={{ color: '#e0e0e0', fontSize: 11, lineHeight: 1.5 }}>
            <strong style={{ fontSize: 12 }}>{hoverInfo.kek_name}</strong>
            <div style={{ color: '#999', marginTop: 2 }}>
              {hoverInfo.province}
              {hoverInfo.kek_type ? ` · ${hoverInfo.kek_type}` : ''}
            </div>
            {hoverInfo.category && <div style={{ color: '#aaa' }}>{hoverInfo.category}</div>}
            {hoverInfo.area_ha != null && (
              <div style={{ color: '#aaa' }}>
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
          </div>
        </Popup>
      )}
    </>
  );
}

export type { HoverInfo };

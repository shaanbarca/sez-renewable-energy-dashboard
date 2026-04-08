import { useMemo } from 'react';
import { Source, Layer, Popup } from 'react-map-gl/maplibre';
import { useDashboardStore } from '../../store/dashboard';
import { ACTION_FLAG_COLORS, ACTION_FLAG_LABELS } from '../../lib/constants';

interface HoverInfo {
  longitude: number;
  latitude: number;
  kek_name: string;
  action_flag: string;
}

interface KekMarkersProps {
  hoverInfo: HoverInfo | null;
}

export default function KekMarkers({ hoverInfo }: KekMarkersProps) {
  const scorecard = useDashboardStore((s) => s.scorecard);
  const selectedKek = useDashboardStore((s) => s.selectedKek);

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
        <Layer
          id="kek-circles"
          type="circle"
          paint={{
            'circle-radius': [
              'case',
              ['==', ['get', 'kek_id'], selectedKek ?? ''],
              8,
              6,
            ],
            'circle-color': colorMatch as unknown as string,
            'circle-stroke-color': '#ffffff',
            'circle-stroke-width': [
              'case',
              ['==', ['get', 'kek_id'], selectedKek ?? ''],
              2.5,
              1,
            ],
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
          <div style={{ color: '#e0e0e0', fontSize: 12, lineHeight: 1.4 }}>
            <strong>{hoverInfo.kek_name}</strong>
            <br />
            <span
              style={{
                color:
                  ACTION_FLAG_COLORS[hoverInfo.action_flag] ?? '#999',
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

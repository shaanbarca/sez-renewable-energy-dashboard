import turfDistance from '@turf/distance';
import { point } from '@turf/helpers';
import type { MapMouseEvent } from 'maplibre-gl';
import { useCallback, useEffect, useState } from 'react';
import { Layer, Marker, Source, useMap } from 'react-map-gl/maplibre';

interface MeasurePoint {
  lng: number;
  lat: number;
}

function formatDistance(km: number): string {
  if (km < 1) return `${Math.round(km * 1000)} m`;
  return `${km.toFixed(1)} km`;
}

function segmentDistance(a: MeasurePoint, b: MeasurePoint): number {
  return turfDistance(point([a.lng, a.lat]), point([b.lng, b.lat]), { units: 'kilometers' });
}

function segmentMidpoint(a: MeasurePoint, b: MeasurePoint): MeasurePoint {
  return { lng: (a.lng + b.lng) / 2, lat: (a.lat + b.lat) / 2 };
}

export default function MeasureTool({
  onMeasuringChange,
}: {
  onMeasuringChange?: (measuring: boolean) => void;
}) {
  const { current: map } = useMap();
  const [active, setActive] = useState(false);
  const [points, setPoints] = useState<MeasurePoint[]>([]);

  // Notify parent of measuring state
  useEffect(() => {
    onMeasuringChange?.(active);
  }, [active, onMeasuringChange]);

  // Change cursor when measure mode is active
  useEffect(() => {
    if (!map) return;
    const canvas = map.getCanvas();
    if (active) {
      canvas.style.cursor = 'crosshair';
    }
    return () => {
      canvas.style.cursor = '';
    };
  }, [active, map]);

  // Listen for map clicks when active
  useEffect(() => {
    if (!active || !map) return;

    const handleClick = (e: MapMouseEvent) => {
      e.preventDefault();
      setPoints((prev) => [...prev, { lng: e.lngLat.lng, lat: e.lngLat.lat }]);
    };

    map.on('click', handleClick);
    return () => {
      map.off('click', handleClick);
    };
  }, [active, map]);

  // Escape to exit
  useEffect(() => {
    if (!active) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setActive(false);
        setPoints([]);
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [active]);

  const toggle = useCallback(() => {
    if (active) {
      setActive(false);
      setPoints([]);
    } else {
      setActive(true);
      setPoints([]);
    }
  }, [active]);

  const undo = useCallback(() => {
    setPoints((prev) => prev.slice(0, -1));
  }, []);

  // Build GeoJSON for the line
  const lineGeoJSON: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features:
      points.length >= 2
        ? [
            {
              type: 'Feature',
              geometry: {
                type: 'LineString',
                coordinates: points.map((p) => [p.lng, p.lat]),
              },
              properties: {},
            },
          ]
        : [],
  };

  // Point markers GeoJSON
  const pointsGeoJSON: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features: points.map((p) => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [p.lng, p.lat] },
      properties: {},
    })),
  };

  // Compute segments and total
  const segments: { mid: MeasurePoint; dist: number }[] = [];
  let totalKm = 0;
  for (let i = 1; i < points.length; i++) {
    const dist = segmentDistance(points[i - 1], points[i]);
    segments.push({ mid: segmentMidpoint(points[i - 1], points[i]), dist });
    totalKm += dist;
  }

  return (
    <>
      {/* Toggle button */}
      <button
        type="button"
        onClick={toggle}
        className="absolute bottom-[120px] right-[10px] z-30 w-[29px] h-[29px] flex items-center justify-center rounded transition-colors cursor-pointer"
        style={{
          background: active ? 'var(--glass-heavy)' : 'white',
          border: active ? '1px solid var(--glass-border-bright)' : '1px solid #ddd',
          boxShadow: '0 1px 4px rgba(0,0,0,0.3)',
        }}
        title={active ? 'Exit measure mode (Esc)' : 'Measure distance'}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke={active ? '#4DD0E1' : '#333'}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {/* Ruler icon */}
          <path d="M2 22L22 2" />
          <path d="M6 18l2-2" />
          <path d="M10 14l2-2" />
          <path d="M14 10l2-2" />
          <path d="M18 6l2-2" />
        </svg>
      </button>

      {/* Active mode: line + points */}
      {active && (
        <>
          <Source id="measure-line" type="geojson" data={lineGeoJSON}>
            <Layer
              id="measure-line-layer"
              type="line"
              paint={{
                'line-color': '#4DD0E1',
                'line-width': 2.5,
                'line-dasharray': [3, 2],
              }}
            />
          </Source>
          <Source id="measure-points" type="geojson" data={pointsGeoJSON}>
            <Layer
              id="measure-points-layer"
              type="circle"
              paint={{
                'circle-radius': 5,
                'circle-color': '#4DD0E1',
                'circle-stroke-width': 2,
                'circle-stroke-color': '#fff',
              }}
            />
          </Source>

          {/* Segment distance labels */}
          {segments.map((seg, i) => (
            <Marker key={`seg-${i}`} longitude={seg.mid.lng} latitude={seg.mid.lat} anchor="center">
              <div
                className="px-1.5 py-0.5 rounded text-[10px] font-medium whitespace-nowrap"
                style={{
                  background: 'rgba(0,0,0,0.75)',
                  color: '#4DD0E1',
                  pointerEvents: 'none',
                }}
              >
                {formatDistance(seg.dist)}
              </div>
            </Marker>
          ))}

          {/* Summary bar */}
          {points.length >= 1 && (
            <div
              className="absolute bottom-[160px] right-[10px] z-30 rounded-lg px-3 py-2 text-xs"
              style={{
                background: 'var(--glass-heavy)',
                backdropFilter: 'var(--blur-heavy)',
                WebkitBackdropFilter: 'var(--blur-heavy)',
                border: '1px solid var(--glass-border-bright)',
                boxShadow: 'var(--popup-shadow)',
                color: 'var(--text-primary)',
                minWidth: 140,
              }}
            >
              <div className="flex items-center justify-between gap-3 mb-1">
                <span style={{ color: 'var(--text-muted)' }}>
                  {points.length} {points.length === 1 ? 'point' : 'points'}
                </span>
                {points.length > 0 && (
                  <button
                    type="button"
                    onClick={undo}
                    className="text-[10px] cursor-pointer"
                    style={{ color: 'var(--text-secondary)' }}
                  >
                    Undo
                  </button>
                )}
              </div>
              {totalKm > 0 && (
                <div className="text-sm font-medium" style={{ color: '#4DD0E1' }}>
                  {formatDistance(totalKm)}
                </div>
              )}
              {points.length < 2 && (
                <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  Click map to add points
                </div>
              )}
            </div>
          )}
        </>
      )}
    </>
  );
}

// PolygonEditor — admin-mode polygon editor for #31 phase 2.
//
// Active when `editingPolygonForSite` is set in the dashboard store. Click the
// map to add vertices; "Close" stitches the first vertex back to the last;
// "Save" POSTs to /api/admin/polygons/{site_id}; "Cancel" or Esc discards.
//
// Patterned after MeasureTool.tsx — no external draw library, just native
// MapLibre click events + react-map-gl Source/Layer/Marker primitives. Keeps
// the frontend dep tree tight.
//
// What it doesn't do (deliberate scope for Phase 2 MVP):
//   - drag-to-move existing vertices (treat as redraw-from-scratch)
//   - pre-fill from existing override (next iteration; user can re-draw
//     against the satellite imagery currently visible on the map)
//   - undo/redo beyond "Cancel"
//   - simplify / smooth the saved polygon

import { useCallback, useEffect, useState } from 'react';
import { Layer, Marker, Source, useMap } from 'react-map-gl/maplibre';
import { savePolygonOverride } from '../../lib/api';
import { useDashboardStore } from '../../store/dashboard';

interface Vertex {
  lng: number;
  lat: number;
}

/** Shoelace area in km² for a polygon in lon/lat. Approximate — applies a
 *  cos(lat) longitude correction at the polygon centroid latitude. Accurate
 *  enough for the "show user the area while drawing" UX; the saved geometry
 *  is the raw lon/lat ring (downstream pipeline reprojects properly). */
function polygonAreaKm2(verts: Vertex[]): number {
  if (verts.length < 3) return 0;
  const KM_PER_DEG_LAT = 111.0;
  const latAvg = verts.reduce((s, v) => s + v.lat, 0) / verts.length;
  const kmPerDegLon = KM_PER_DEG_LAT * Math.cos((latAvg * Math.PI) / 180);
  let sum = 0;
  for (let i = 0; i < verts.length; i++) {
    const a = verts[i];
    const b = verts[(i + 1) % verts.length];
    sum += a.lng * b.lat - b.lng * a.lat;
  }
  // shoelace gives 2× signed area in deg², multiply by km/deg² conversion
  return (Math.abs(sum) * KM_PER_DEG_LAT * kmPerDegLon) / 2;
}

function formatArea(km2: number): string {
  if (km2 < 0.01) return '— ha';
  return `${(km2 * 100).toFixed(1)} ha`; // 1 km² = 100 ha
}

export default function PolygonEditor() {
  const { current: map } = useMap();
  const editingFor = useDashboardStore((s) => s.editingPolygonForSite);
  const exitEdit = useDashboardStore((s) => s.exitPolygonEdit);
  const refreshOverrides = useDashboardStore((s) => s.refreshManualOverrides);
  const scorecard = useDashboardStore((s) => s.scorecard);
  const [vertices, setVertices] = useState<Vertex[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const siteName =
    editingFor && scorecard?.find((r) => r.site_id === editingFor)?.site_name;
  const active = editingFor != null;

  // Reset state every time we enter/exit edit mode.
  useEffect(() => {
    setVertices([]);
    setError(null);
    setSaving(false);
  }, [editingFor]);

  // Cursor crosshair while editing.
  useEffect(() => {
    if (!map || !active) return;
    const canvas = map.getCanvas();
    canvas.style.cursor = 'crosshair';
    return () => {
      canvas.style.cursor = '';
    };
  }, [map, active]);

  // Click map to add vertex.
  useEffect(() => {
    if (!map || !active) return;
    const handleClick = (
      e: maplibregl.MapMouseEvent & { lngLat: maplibregl.LngLat },
    ) => {
      e.preventDefault();
      setVertices((prev) => [...prev, { lng: e.lngLat.lng, lat: e.lngLat.lat }]);
    };
    map.on('click', handleClick);
    return () => {
      map.off('click', handleClick);
    };
  }, [map, active]);

  // Esc cancels.
  useEffect(() => {
    if (!active) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') exitEdit();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [active, exitEdit]);

  const undo = useCallback(() => setVertices((prev) => prev.slice(0, -1)), []);
  const clear = useCallback(() => setVertices([]), []);

  const handleSave = useCallback(async () => {
    if (!editingFor || vertices.length < 3) return;
    setSaving(true);
    setError(null);
    try {
      // Close the ring — GeoJSON Polygon requires first == last.
      const ring = vertices.map((v) => [v.lng, v.lat]);
      ring.push([vertices[0].lng, vertices[0].lat]);
      const geometry: GeoJSON.Polygon = {
        type: 'Polygon',
        coordinates: [ring],
      };
      await savePolygonOverride(editingFor, geometry, {
        notes: `drawn in-session via #31 polygon editor`,
      });
      await refreshOverrides();
      exitEdit();
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(msg);
      setSaving(false);
    }
  }, [editingFor, vertices, refreshOverrides, exitEdit]);

  if (!active) return null;

  // Build a closed-ring polygon for live preview if we have ≥3 vertices.
  const polygonGeoJSON: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features:
      vertices.length >= 3
        ? [
            {
              type: 'Feature',
              geometry: {
                type: 'Polygon',
                coordinates: [
                  [
                    ...vertices.map((v) => [v.lng, v.lat]),
                    [vertices[0].lng, vertices[0].lat],
                  ],
                ],
              },
              properties: {},
            },
          ]
        : [],
  };

  // Open polyline while drawing (≥2 vertices).
  const lineGeoJSON: GeoJSON.FeatureCollection = {
    type: 'FeatureCollection',
    features:
      vertices.length >= 2
        ? [
            {
              type: 'Feature',
              geometry: {
                type: 'LineString',
                coordinates: vertices.map((v) => [v.lng, v.lat]),
              },
              properties: {},
            },
          ]
        : [],
  };

  const areaKm2 = polygonAreaKm2(vertices);
  const canSave = vertices.length >= 3 && !saving;

  return (
    <>
      <Source id="polygon-editor-fill" type="geojson" data={polygonGeoJSON}>
        <Layer
          id="polygon-editor-fill-layer"
          type="fill"
          paint={{ 'fill-color': '#FF9800', 'fill-opacity': 0.20 }}
        />
        <Layer
          id="polygon-editor-fill-outline"
          type="line"
          paint={{ 'line-color': '#FF9800', 'line-width': 2 }}
        />
      </Source>
      <Source id="polygon-editor-line" type="geojson" data={lineGeoJSON}>
        <Layer
          id="polygon-editor-line-layer"
          type="line"
          paint={{
            'line-color': '#FF9800',
            'line-width': 2,
            'line-dasharray': [3, 2],
          }}
        />
      </Source>

      {/* Vertex markers */}
      {vertices.map((v, i) => (
        <Marker
          // biome-ignore lint/suspicious/noArrayIndexKey: vertex order IS its identity
          key={`vert-${i}`}
          longitude={v.lng}
          latitude={v.lat}
          anchor="center"
        >
          <div
            className="rounded-full"
            style={{
              width: 12,
              height: 12,
              background: i === 0 ? '#FF6F00' : '#FF9800',
              border: '2px solid #fff',
              boxShadow: '0 1px 3px rgba(0,0,0,0.4)',
              pointerEvents: 'none',
            }}
          />
        </Marker>
      ))}

      {/* Editor control panel */}
      <div
        className="absolute bottom-[100px] right-[10px] z-30 rounded-lg px-3 py-3 text-xs"
        style={{
          background: 'var(--glass-heavy)',
          backdropFilter: 'var(--blur-heavy)',
          WebkitBackdropFilter: 'var(--blur-heavy)',
          border: '1px solid var(--glass-border-bright)',
          boxShadow: 'var(--popup-shadow)',
          color: 'var(--text-primary)',
          minWidth: 240,
        }}
      >
        <div className="font-semibold mb-2" style={{ color: '#FFB74D' }}>
          Editing polygon
        </div>
        {siteName && (
          <div className="text-[10px] mb-2 truncate" style={{ color: 'var(--text-secondary)' }}>
            {siteName}
          </div>
        )}
        <div className="flex items-center justify-between mb-2">
          <span style={{ color: 'var(--text-muted)' }}>
            {vertices.length} {vertices.length === 1 ? 'vertex' : 'vertices'}
          </span>
          <span style={{ color: 'var(--text-secondary)' }}>{formatArea(areaKm2)}</span>
        </div>
        {vertices.length < 3 && (
          <div className="text-[10px] mb-2" style={{ color: 'var(--text-muted)' }}>
            Click map to add vertices — need at least 3 to save.
          </div>
        )}
        {error && (
          <div
            className="text-[10px] mb-2 px-1.5 py-1 rounded"
            style={{
              background: 'rgba(244, 67, 54, 0.15)',
              color: '#ef9a9a',
              border: '1px solid rgba(244, 67, 54, 0.30)',
            }}
          >
            {error}
          </div>
        )}
        <div className="flex gap-1.5 flex-wrap">
          <button
            type="button"
            onClick={undo}
            disabled={vertices.length === 0 || saving}
            className="px-2 py-1 rounded text-[10px] cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            style={{
              background: 'var(--glass)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--glass-border-bright)',
            }}
          >
            Undo
          </button>
          <button
            type="button"
            onClick={clear}
            disabled={vertices.length === 0 || saving}
            className="px-2 py-1 rounded text-[10px] cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            style={{
              background: 'var(--glass)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--glass-border-bright)',
            }}
          >
            Clear
          </button>
          <button
            type="button"
            onClick={exitEdit}
            disabled={saving}
            className="px-2 py-1 rounded text-[10px] cursor-pointer disabled:opacity-40"
            style={{
              background: 'var(--glass)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--glass-border-bright)',
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={!canSave}
            className="px-2 py-1 rounded text-[10px] font-medium cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            style={{
              background: canSave ? '#FF9800' : 'var(--glass)',
              color: canSave ? '#1a1a1a' : 'var(--text-muted)',
              border: '1px solid #FF9800',
            }}
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
        <div
          className="text-[9px] mt-2 pt-2 border-t"
          style={{ color: 'var(--text-muted)', borderColor: 'var(--glass-border-bright)' }}
        >
          Esc to cancel · saved as <code style={{ color: 'var(--text-secondary)' }}>manual_override</code>
        </div>
      </div>
    </>
  );
}

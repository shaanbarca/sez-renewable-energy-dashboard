import { useEffect } from 'react';
import { Source, Layer, useMap } from 'react-map-gl/maplibre';
import { useDashboardStore } from '../../store/dashboard';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type LayerData = any;

/** Create a lightning bolt icon as an ImageData for MapLibre */
function createBoltIcon(size: number, color: string): ImageData {
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;

  const s = size;
  ctx.fillStyle = color;
  ctx.beginPath();
  // Lightning bolt shape
  ctx.moveTo(s * 0.55, 0);
  ctx.lineTo(s * 0.2, s * 0.5);
  ctx.lineTo(s * 0.42, s * 0.5);
  ctx.lineTo(s * 0.35, s);
  ctx.lineTo(s * 0.8, s * 0.4);
  ctx.lineTo(s * 0.55, s * 0.4);
  ctx.lineTo(s * 0.65, 0);
  ctx.closePath();
  ctx.fill();

  // White outline
  ctx.strokeStyle = '#ffffff';
  ctx.lineWidth = 1;
  ctx.stroke();

  return ctx.getImageData(0, 0, size, size);
}

/**
 * Renders toggled vector layers: substations, kek_polygons, peatland,
 * protected_forest, industrial. Each has different styling.
 */
export default function VectorOverlay() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const layers = useDashboardStore((s) => s.layers);
  const { current: mapRef } = useMap();

  // Load custom bolt icon onto the map
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    const addIcon = () => {
      if (!map.hasImage('bolt-icon')) {
        map.addImage('bolt-icon', createBoltIcon(24, '#FFD600'), { sdf: false });
      }
    };
    if (map.isStyleLoaded()) {
      addIcon();
    } else {
      map.on('style.load', addIcon);
      return () => { map.off('style.load', addIcon); };
    }
  }, [mapRef]);

  return (
    <>
      {/* Substations — point layer */}
      {layerVisibility['substations'] && layers['substations'] && !(layers['substations'] as LayerData)._loading && (() => {
        const points = layers['substations'].points ?? layers['substations'];
        if (!Array.isArray(points) || !points.length) return null;
        const geojson = {
          type: 'FeatureCollection' as const,
          features: points.map((p: { lat: number; lon: number; name?: string }) => ({
            type: 'Feature' as const,
            geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
            properties: { name: p.name ?? '' },
          })),
        };
        return (
          <Source id="overlay-substations" type="geojson" data={geojson}>
            <Layer
              id="overlay-substations-symbol"
              type="symbol"
              layout={{
                'icon-image': 'bolt-icon',
                'icon-size': 0.7,
                'icon-allow-overlap': true,
                'icon-ignore-placement': true,
              }}
              paint={{
                'icon-opacity': 0.85,
              }}
            />
          </Source>
        );
      })()}

      {/* KEK Polygons */}
      {layerVisibility['kek_polygons'] && layers['kek_polygons'] && !layers['kek_polygons']._loading && (() => {
        const data = layers['kek_polygons'];
        if (!data || !data.features) return null;
        return (
          <Source id="overlay-kek-polygons" type="geojson" data={data}>
            <Layer
              id="overlay-kek-polygons-fill"
              type="fill"
              paint={{ 'fill-color': '#42A5F5', 'fill-opacity': 0.08 }}
            />
            <Layer
              id="overlay-kek-polygons-line"
              type="line"
              paint={{ 'line-color': '#42A5F5', 'line-width': 1.5, 'line-opacity': 0.6 }}
            />
          </Source>
        );
      })()}

      {/* Peatland */}
      {layerVisibility['peatland'] && layers['peatland'] && !layers['peatland']._loading && (() => {
        const data = layers['peatland'];
        if (!data || !data.features) return null;
        return (
          <Source id="overlay-peatland" type="geojson" data={data}>
            <Layer
              id="overlay-peatland-fill"
              type="fill"
              paint={{ 'fill-color': '#8D6E63', 'fill-opacity': 0.3 }}
            />
          </Source>
        );
      })()}

      {/* Protected Forest */}
      {layerVisibility['protected_forest'] && layers['protected_forest'] && !layers['protected_forest']._loading && (() => {
        const data = layers['protected_forest'];
        if (!data || !data.features) return null;
        return (
          <Source id="overlay-protected-forest" type="geojson" data={data}>
            <Layer
              id="overlay-protected-forest-fill"
              type="fill"
              paint={{ 'fill-color': '#2E7D32', 'fill-opacity': 0.25 }}
            />
          </Source>
        );
      })()}

      {/* PLN Grid Lines */}
      {layerVisibility['grid_lines'] && layers['grid_lines'] && !layers['grid_lines']._loading && (() => {
        const data = layers['grid_lines'];
        if (!data || !data.features) return null;
        return (
          <Source id="overlay-grid-lines" type="geojson" data={data}>
            <Layer
              id="overlay-grid-lines-line"
              type="line"
              paint={{
                'line-color': '#FFD600',
                'line-width': 1.2,
                'line-opacity': 0.5,
              }}
            />
          </Source>
        );
      })()}

      {/* Industrial Facilities */}
      {layerVisibility['industrial'] && layers['industrial'] && !layers['industrial']._loading && (() => {
        const points = layers['industrial'].points ?? layers['industrial'];
        if (!Array.isArray(points) || !points.length) return null;
        const geojson = {
          type: 'FeatureCollection' as const,
          features: points.map((p: { lat: number; lon: number; name?: string }) => ({
            type: 'Feature' as const,
            geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
            properties: { name: p.name ?? '' },
          })),
        };
        return (
          <Source id="overlay-industrial" type="geojson" data={geojson}>
            <Layer
              id="overlay-industrial-circles"
              type="circle"
              paint={{
                'circle-radius': 3,
                'circle-color': '#F57C00',
                'circle-stroke-color': '#ffffff',
                'circle-stroke-width': 0.5,
                'circle-opacity': 0.6,
              }}
            />
          </Source>
        );
      })()}
    </>
  );
}

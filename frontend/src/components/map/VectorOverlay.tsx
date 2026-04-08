import { Source, Layer } from 'react-map-gl/maplibre';
import { useDashboardStore } from '../../store/dashboard';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type LayerData = any;

/**
 * Renders toggled vector layers: substations, kek_polygons, peatland,
 * protected_forest, industrial. Each has different styling.
 */
export default function VectorOverlay() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const layers = useDashboardStore((s) => s.layers);

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
              id="overlay-substations-circles"
              type="circle"
              paint={{
                'circle-radius': 3,
                'circle-color': '#FFD600',
                'circle-stroke-color': '#ffffff',
                'circle-stroke-width': 0.5,
                'circle-opacity': 0.7,
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

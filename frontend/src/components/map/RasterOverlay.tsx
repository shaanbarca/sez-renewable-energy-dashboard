import { Source, Layer } from 'react-map-gl/maplibre';
import { useDashboardStore } from '../../store/dashboard';

interface RasterLayerData {
  image_url: string;
  bounds: [[number, number], [number, number]]; // [[lat_min, lon_min], [lat_max, lon_max]]
  _loading?: boolean;
}

const RASTER_LAYERS = ['pvout', 'wind', 'buildable'] as const;

export default function RasterOverlay() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const layers = useDashboardStore((s) => s.layers);

  return (
    <>
      {RASTER_LAYERS.map((name) => {
        if (!layerVisibility[name]) return null;
        const data = layers[name] as RasterLayerData | undefined;
        if (!data || data._loading || !data.image_url) return null;

        // Convert [[lat_min, lon_min], [lat_max, lon_max]] to MapLibre 4-corner format
        // MapLibre expects: [top-left, top-right, bottom-right, bottom-left] as [lon, lat]
        const [[latMin, lonMin], [latMax, lonMax]] = data.bounds;
        const coordinates: [[number, number], [number, number], [number, number], [number, number]] = [
          [lonMin, latMax], // top-left
          [lonMax, latMax], // top-right
          [lonMax, latMin], // bottom-right
          [lonMin, latMin], // bottom-left
        ];

        return (
          <Source
            key={name}
            id={`${name}-raster`}
            type="image"
            url={data.image_url}
            coordinates={coordinates}
          >
            <Layer
              id={`${name}-raster-layer`}
              type="raster"
              paint={{ 'raster-opacity': 0.6 }}
            />
          </Source>
        );
      })}
    </>
  );
}

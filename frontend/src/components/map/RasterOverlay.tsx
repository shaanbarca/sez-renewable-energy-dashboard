import { Source, Layer } from 'react-map-gl/maplibre';
import { useDashboardStore } from '../../store/dashboard';

interface RasterLayerData {
  image_url: string;
  bounds: [[number, number], [number, number], [number, number], [number, number]];
  _loading?: boolean;
}

const RASTER_LAYERS = ['pvout', 'wind_speed', 'buildable_area'] as const;

export default function RasterOverlay() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const layers = useDashboardStore((s) => s.layers);

  return (
    <>
      {RASTER_LAYERS.map((name) => {
        if (!layerVisibility[name]) return null;
        const data = layers[name] as RasterLayerData | undefined;
        if (!data || data._loading || !data.image_url) return null;

        return (
          <Source
            key={name}
            id={`${name}-raster`}
            type="image"
            url={data.image_url}
            coordinates={data.bounds}
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

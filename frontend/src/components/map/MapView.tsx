import { useCallback, useEffect, useRef, useState } from 'react';
import Map, { Source, Layer, NavigationControl } from 'react-map-gl/maplibre';
import type { MapRef, MapLayerMouseEvent } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';

import { useDashboardStore } from '../../store/dashboard';
import { fetchKekPolygon } from '../../lib/api';
import { useMapLayers } from '../../hooks/useMapLayers';
import KekMarkers from './KekMarkers';
import type { HoverInfo } from './KekMarkers';
import LayerControl from './LayerControl';
import RasterOverlay from './RasterOverlay';
import InfraMarkers from './InfraMarkers';

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const INITIAL_CENTER = { longitude: 118.0, latitude: -2.5 };
const INITIAL_ZOOM = 4;
const KEK_ZOOM = 11;

interface PolygonData {
  type: string;
  features: Array<{
    type: string;
    geometry: unknown;
    properties: unknown;
  }>;
}

export default function MapView() {
  const mapRef = useRef<MapRef>(null);
  const selectedKek = useDashboardStore((s) => s.selectedKek);
  const selectKek = useDashboardStore((s) => s.selectKek);
  const [polygon, setPolygon] = useState<PolygonData | null>(null);
  const [hoverInfo, setHoverInfo] = useState<HoverInfo | null>(null);

  // Activate lazy layer loading
  useMapLayers();

  // Fetch KEK polygon when selected
  useEffect(() => {
    if (!selectedKek) {
      setPolygon(null);
      return;
    }
    fetchKekPolygon(selectedKek)
      .then((data) => setPolygon(data as PolygonData))
      .catch((err) => {
        console.error('Failed to fetch KEK polygon:', err);
        setPolygon(null);
      });
  }, [selectedKek]);

  const handleClick = useCallback(
    (e: MapLayerMouseEvent) => {
      const feature = e.features?.[0];
      if (!feature || !feature.properties) return;
      const kekId = feature.properties.kek_id as string;
      selectKek(kekId);
      const coords = (feature.geometry as GeoJSON.Point).coordinates;
      mapRef.current?.flyTo({
        center: [coords[0], coords[1]],
        zoom: KEK_ZOOM,
        duration: 1400,
      });
    },
    [selectKek],
  );

  const handleMouseEnter = useCallback((e: MapLayerMouseEvent) => {
    const feature = e.features?.[0];
    if (!feature || !feature.properties) return;
    const coords = (feature.geometry as GeoJSON.Point).coordinates;
    setHoverInfo({
      longitude: coords[0],
      latitude: coords[1],
      kek_name: feature.properties.kek_name as string,
      action_flag: feature.properties.action_flag as string,
    });
    // Change cursor
    const map = mapRef.current?.getMap();
    if (map) map.getCanvas().style.cursor = 'pointer';
  }, []);

  const handleMouseLeave = useCallback(() => {
    setHoverInfo(null);
    const map = mapRef.current?.getMap();
    if (map) map.getCanvas().style.cursor = '';
  }, []);

  const resetView = useCallback(() => {
    selectKek(null);
    mapRef.current?.flyTo({
      center: [INITIAL_CENTER.longitude, INITIAL_CENTER.latitude],
      zoom: INITIAL_ZOOM,
      duration: 1200,
    });
  }, [selectKek]);

  return (
    <div className="absolute inset-0">
      <Map
        ref={mapRef}
        initialViewState={{
          ...INITIAL_CENTER,
          zoom: INITIAL_ZOOM,
        }}
        mapStyle={MAP_STYLE}
        style={{ width: '100%', height: '100%' }}
        interactiveLayerIds={['kek-circles']}
        onClick={handleClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <NavigationControl position="bottom-right" />

        <KekMarkers hoverInfo={hoverInfo} />
        <RasterOverlay />
        <InfraMarkers />

        {/* Selected KEK polygon */}
        {polygon && (
          <Source id="kek-polygon" type="geojson" data={polygon as GeoJSON.FeatureCollection}>
            <Layer
              id="kek-polygon-fill"
              type="fill"
              paint={{
                'fill-color': '#42A5F5',
                'fill-opacity': 0.15,
              }}
            />
            <Layer
              id="kek-polygon-outline"
              type="line"
              paint={{
                'line-color': '#42A5F5',
                'line-width': 2,
                'line-opacity': 0.8,
              }}
            />
          </Source>
        )}
      </Map>

      <LayerControl />

      {/* Back to National View button */}
      {selectedKek && (
        <button
          onClick={resetView}
          className="absolute top-3 left-3 z-10 rounded-lg px-3 py-1.5 text-xs font-medium text-zinc-200 hover:text-white transition-colors cursor-pointer"
          style={{
            backdropFilter: 'var(--blur)',
            WebkitBackdropFilter: 'var(--blur)',
            background: 'var(--glass)',
            border: '1px solid var(--glass-border)',
          }}
        >
          &larr; National View
        </button>
      )}
    </div>
  );
}

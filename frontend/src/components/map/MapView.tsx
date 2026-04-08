import { useCallback, useEffect, useRef, useState } from 'react';
import Map, { Source, Layer, NavigationControl } from 'react-map-gl/maplibre';
import type { MapRef, MapLayerMouseEvent, ViewStateChangeEvent } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';

import { useDashboardStore } from '../../store/dashboard';
import { fetchKekPolygon } from '../../lib/api';
import { useMapLayers } from '../../hooks/useMapLayers';
import KekMarkers from './KekMarkers';
import type { HoverInfo } from './KekMarkers';
import LayerControl from './LayerControl';
import RasterOverlay from './RasterOverlay';
import VectorOverlay from './VectorOverlay';
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
  const [isZoomedIn, setIsZoomedIn] = useState(false);

  const handleZoom = useCallback((e: ViewStateChangeEvent) => {
    setIsZoomedIn(e.viewState.zoom > INITIAL_ZOOM + 1);
  }, []);

  // Activate lazy layer loading
  useMapLayers();

  // Fly to selected KEK (works from table clicks, search, etc.)
  const scorecard = useDashboardStore((s) => s.scorecard);
  useEffect(() => {
    if (!selectedKek || !scorecard) return;
    const row = scorecard.find((r) => r.kek_id === selectedKek);
    if (!row) return;
    mapRef.current?.flyTo({
      center: [row.longitude, row.latitude],
      zoom: KEK_ZOOM,
      duration: 2200,
    });
  }, [selectedKek, scorecard]);

  // Fetch KEK polygon when selected
  useEffect(() => {
    if (!selectedKek) {
      setPolygon(null);
      return;
    }
    fetchKekPolygon(selectedKek)
      .then((data) => {
        // API returns { feature, bbox, center } — wrap single feature into FeatureCollection
        const resp = data as { feature: unknown; bbox: unknown; center: unknown };
        if (resp.feature) {
          setPolygon({
            type: 'FeatureCollection',
            features: [resp.feature as PolygonData['features'][0]],
          });
        } else {
          setPolygon(null);
        }
      })
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
      duration: 2000,
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
        onZoom={handleZoom}
      >
        <NavigationControl position="bottom-right" />

        <KekMarkers hoverInfo={hoverInfo} />
        <RasterOverlay />
        <VectorOverlay />
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

      {/* Back to National View button — centered top, above assumptions panel */}
      {(selectedKek || isZoomedIn) && (
        <button
          onClick={resetView}
          className="absolute top-3 left-1/2 -translate-x-1/2 z-20 rounded-lg px-5 py-2 text-sm font-medium text-zinc-200 hover:text-white transition-colors cursor-pointer"
          style={{
            backdropFilter: 'blur(24px) saturate(1.4)',
            WebkitBackdropFilter: 'blur(24px) saturate(1.4)',
            background: 'rgba(20, 20, 24, 0.75)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
          }}
        >
          ‹ Back to National View
        </button>
      )}
    </div>
  );
}

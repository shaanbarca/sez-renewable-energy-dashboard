import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { MapLayerMouseEvent, MapRef, ViewStateChangeEvent } from 'react-map-gl/maplibre';
import Map, { Layer, NavigationControl, Source } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';

import { useMapLayers } from '../../hooks/useMapLayers';
import { fetchKekPolygon } from '../../lib/api';
import { useDashboardStore } from '../../store/dashboard';
import InfraMarkers from './InfraMarkers';
import type { HoverInfo } from './KekMarkers';
import KekMarkers from './KekMarkers';
import LayerControl from './LayerControl';
import RasterOverlay from './RasterOverlay';
import VectorOverlay from './VectorOverlay';

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';
const INITIAL_CENTER = { longitude: 118.0, latitude: -2.5 };
const INITIAL_ZOOM = 4;
const KEK_ZOOM = 11;
const RADIUS_KM = 50;

/** Generate a GeoJSON Polygon circle around a center point. */
function createCircleGeoJSON(
  lng: number,
  lat: number,
  radiusKm: number,
  points = 64,
): GeoJSON.FeatureCollection {
  const coords: [number, number][] = [];
  const earthRadiusKm = 6371;
  for (let i = 0; i <= points; i++) {
    const angle = (i / points) * 2 * Math.PI;
    const dLat = (radiusKm / earthRadiusKm) * Math.cos(angle);
    const dLng = (radiusKm / (earthRadiusKm * Math.cos((lat * Math.PI) / 180))) * Math.sin(angle);
    coords.push([lng + (dLng * 180) / Math.PI, lat + (dLat * 180) / Math.PI]);
  }
  return {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [coords] },
        properties: { radius_km: radiusKm },
      },
    ],
  };
}

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
      if (!feature?.properties) return;
      const kekId = feature.properties.kek_id as string;
      selectKek(kekId);
    },
    [selectKek],
  );

  const handleMouseEnter = useCallback((e: MapLayerMouseEvent) => {
    const feature = e.features?.[0];
    if (!feature?.properties) return;
    const coords = (feature.geometry as GeoJSON.Point).coordinates;
    setHoverInfo({
      longitude: coords[0],
      latitude: coords[1],
      kek_name: feature.properties.kek_name as string,
      action_flag: feature.properties.action_flag as string,
      province: feature.properties.province as string,
      kek_type: feature.properties.kek_type as string,
      category: feature.properties.category as string,
      area_ha: feature.properties.area_ha as number | null,
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

  // 50km radius circle around selected KEK
  const radiusCircle = useMemo(() => {
    if (!selectedKek || !scorecard) return null;
    const row = scorecard.find((r) => r.kek_id === selectedKek);
    if (!row) return null;
    return createCircleGeoJSON(row.longitude, row.latitude, RADIUS_KM);
  }, [selectedKek, scorecard]);

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

        {/* 50km radius circle around selected KEK */}
        {radiusCircle && (
          <Source id="kek-radius-circle" type="geojson" data={radiusCircle}>
            <Layer
              id="kek-radius-fill"
              type="fill"
              paint={{
                'fill-color': '#90CAF9',
                'fill-opacity': 0.06,
              }}
            />
            <Layer
              id="kek-radius-outline"
              type="line"
              paint={{
                'line-color': '#90CAF9',
                'line-width': 1.5,
                'line-opacity': 0.4,
                'line-dasharray': [4, 3],
              }}
            />
          </Source>
        )}

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
          className="absolute top-[72px] left-1/2 -translate-x-1/2 z-40 rounded-xl px-5 py-2 text-sm font-medium text-zinc-200 hover:text-white transition-all cursor-pointer hover:scale-[1.02]"
          style={{
            backdropFilter: 'blur(40px) saturate(1.6)',
            WebkitBackdropFilter: 'blur(40px) saturate(1.6)',
            background: 'rgba(20, 20, 24, 0.35)',
            border: '1px solid rgba(255, 255, 255, 0.12)',
            boxShadow: 'inset 0 1px 0 rgba(255, 255, 255, 0.08), 0 8px 32px rgba(0,0,0,0.3)',
          }}
        >
          ‹ Back to National View
        </button>
      )}
    </div>
  );
}

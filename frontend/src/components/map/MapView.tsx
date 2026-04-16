import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { MapLayerMouseEvent, MapRef, ViewStateChangeEvent } from 'react-map-gl/maplibre';
import Map, { Layer, NavigationControl, Source } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';

import { useMapLayers } from '../../hooks/useMapLayers';
import { fetchSiteBuildable, fetchSitePolygon } from '../../lib/api';
import { MAP_STYLES } from '../../lib/constants';
import type { ActionFlag, EconomicTier, InfrastructureReadiness } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';
import InfraMarkers from './InfraMarkers';
import type { HoverInfo } from './SiteMarkers';
import SiteMarkers from './SiteMarkers';

import MeasureTool from './MeasureTool';
import RasterOverlay from './RasterOverlay';
import VectorOverlay from './VectorOverlay';

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
  const selectedSite = useDashboardStore((s) => s.selectedSite);
  const selectSite = useDashboardStore((s) => s.selectSite);
  const [polygon, setPolygon] = useState<PolygonData | null>(null);
  const [wbBuildable, setWbBuildable] = useState<GeoJSON.FeatureCollection | null>(null);
  const [hoverInfo, setHoverInfo] = useState<HoverInfo | null>(null);
  const [isZoomedIn, setIsZoomedIn] = useState(false);
  const [measuring, setMeasuring] = useState(false);
  const mapStyleKey = useDashboardStore((s) => s.mapStyle);

  const mapStyle = (MAP_STYLES[mapStyleKey] ?? MAP_STYLES.dark).style;

  const handleZoom = useCallback((e: ViewStateChangeEvent) => {
    setIsZoomedIn(e.viewState.zoom > INITIAL_ZOOM + 1);
  }, []);

  // Activate lazy layer loading
  useMapLayers();

  // Fly to selected site (works from table clicks, search, etc.)
  const scorecard = useDashboardStore((s) => s.scorecard);
  useEffect(() => {
    if (!selectedSite || !scorecard) return;
    const row = scorecard.find((r) => r.site_id === selectedSite);
    if (!row) return;
    mapRef.current?.flyTo({
      center: [row.longitude, row.latitude],
      zoom: KEK_ZOOM,
      duration: 2200,
    });
  }, [selectedSite, scorecard]);

  // Fly to arbitrary target (e.g. substation clicked in comparison table)
  const flyToTarget = useDashboardStore((s) => s.flyToTarget);
  const clearFlyTo = useDashboardStore((s) => s.clearFlyTo);
  useEffect(() => {
    if (!flyToTarget) return;
    mapRef.current?.flyTo({
      center: [flyToTarget.lon, flyToTarget.lat],
      zoom: flyToTarget.zoom ?? 13,
      duration: 1200,
    });
    clearFlyTo();
  }, [flyToTarget, clearFlyTo]);

  // Fetch site polygon when selected
  useEffect(() => {
    if (!selectedSite) {
      setPolygon(null);
      return;
    }
    fetchSitePolygon(selectedSite)
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
        console.error('Failed to fetch site polygon:', err);
        setPolygon(null);
      });
  }, [selectedSite]);

  // Fetch within-boundary buildable overlay when site is selected
  useEffect(() => {
    if (!selectedSite) {
      setWbBuildable(null);
      return;
    }
    fetchSiteBuildable(selectedSite)
      .then((data) => {
        setWbBuildable(data.features?.length ? data : null);
      })
      .catch(() => setWbBuildable(null));
  }, [selectedSite]);

  // Radiate animation: buildable polygons pulse outward when KEK is selected
  const radiateAnimRef = useRef<number>(0);
  const radiateTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!wbBuildable) return;
    const map = mapRef.current?.getMap();
    if (!map) return;

    cancelAnimationFrame(radiateAnimRef.current);
    if (radiateTimeoutRef.current != null) clearTimeout(radiateTimeoutRef.current);

    const DURATION = 4500;
    const WB_DELAY = 600;
    const OOB_DELAY = 1600;
    const PULSE_CYCLES = 3;
    const WB_REST_OPACITY = 0.35;
    const WB_REST_LINE = 0.7;
    const OOB_REST_OPACITY = 0.25;
    const OOB_REST_LINE = 0.5;
    const WB_PEAK_OPACITY = 0.7; // 2x resting — very visible flash
    const OOB_PEAK_OPACITY = 0.5;

    // Start invisible
    if (map.getLayer('wb-buildable-fill')) {
      map.setPaintProperty('wb-buildable-fill', 'fill-opacity', 0);
      map.setPaintProperty('wb-buildable-outline', 'line-opacity', 0);
      map.setPaintProperty('wb-buildable-outline', 'line-width', 0);
    }
    if (map.getLayer('overlay-buildable-polygons-fill')) {
      map.setPaintProperty('overlay-buildable-polygons-fill', 'fill-opacity', 0);
      map.setPaintProperty('overlay-buildable-polygons-outline', 'line-opacity', 0);
    }

    const start = performance.now();

    const animate = (now: number) => {
      const elapsed = now - start;
      if (elapsed > DURATION + OOB_DELAY) {
        // Settle to resting values
        if (map.getLayer('wb-buildable-fill')) {
          map.setPaintProperty('wb-buildable-fill', 'fill-opacity', WB_REST_OPACITY);
          map.setPaintProperty('wb-buildable-outline', 'line-opacity', WB_REST_LINE);
          map.setPaintProperty('wb-buildable-outline', 'line-width', 2);
        }
        if (map.getLayer('overlay-buildable-polygons-fill')) {
          map.setPaintProperty('overlay-buildable-polygons-fill', 'fill-opacity', OOB_REST_OPACITY);
          map.setPaintProperty('overlay-buildable-polygons-outline', 'line-opacity', OOB_REST_LINE);
        }
        return;
      }

      // Within-boundary buildable
      const wbEl = elapsed - WB_DELAY;
      if (wbEl > 0 && map.getLayer('wb-buildable-fill')) {
        const t = Math.min(wbEl / DURATION, 1);
        // Sharp sine pulse: abs(sin) gives distinct "heartbeat" peaks
        const wave = Math.abs(Math.sin(t * PULSE_CYCLES * Math.PI));
        const fadeIn = Math.min(t * 4, 1); // ramp up in first 25%
        const decay = 1 - t * 0.6; // pulses shrink toward end
        // Interpolate between peak and resting opacity
        const fillOp =
          fadeIn * (WB_REST_OPACITY + (WB_PEAK_OPACITY - WB_REST_OPACITY) * wave * decay);
        const lineOp = fadeIn * (WB_REST_LINE + (1.0 - WB_REST_LINE) * wave * decay);
        const lineW = fadeIn * (2 + wave * 2 * decay);

        map.setPaintProperty('wb-buildable-fill', 'fill-opacity', fillOp);
        map.setPaintProperty('wb-buildable-outline', 'line-opacity', lineOp);
        map.setPaintProperty('wb-buildable-outline', 'line-width', lineW);
      }

      // Out-of-boundary buildable (staggered)
      const oobEl = elapsed - OOB_DELAY;
      if (oobEl > 0 && map.getLayer('overlay-buildable-polygons-fill')) {
        const t = Math.min(oobEl / DURATION, 1);
        const wave = Math.abs(Math.sin(t * PULSE_CYCLES * Math.PI));
        const fadeIn = Math.min(t * 4, 1);
        const decay = 1 - t * 0.6;
        const fillOp =
          fadeIn * (OOB_REST_OPACITY + (OOB_PEAK_OPACITY - OOB_REST_OPACITY) * wave * decay);
        const lineOp = fadeIn * (OOB_REST_LINE + (0.9 - OOB_REST_LINE) * wave * decay);

        map.setPaintProperty('overlay-buildable-polygons-fill', 'fill-opacity', fillOp);
        map.setPaintProperty('overlay-buildable-polygons-outline', 'line-opacity', lineOp);
      }

      radiateAnimRef.current = requestAnimationFrame(animate);
    };

    radiateTimeoutRef.current = setTimeout(() => {
      radiateAnimRef.current = requestAnimationFrame(animate);
    }, 100);

    return () => {
      cancelAnimationFrame(radiateAnimRef.current);
      if (radiateTimeoutRef.current != null) clearTimeout(radiateTimeoutRef.current);
    };
  }, [wbBuildable]);

  const handleClick = useCallback(
    (e: MapLayerMouseEvent) => {
      const feature = e.features?.[0];
      if (!feature?.properties) return;
      const siteId = feature.properties.site_id as string;
      selectSite(siteId);
    },
    [selectSite],
  );

  const handleMouseEnter = useCallback((e: MapLayerMouseEvent) => {
    const feature = e.features?.[0];
    if (!feature?.properties) return;
    const coords = (feature.geometry as GeoJSON.Point).coordinates;
    setHoverInfo({
      longitude: coords[0],
      latitude: coords[1],
      site_name: feature.properties.site_name as string,
      action_flag: feature.properties.action_flag as ActionFlag,
      economic_tier: (feature.properties.economic_tier as EconomicTier) ?? 'not_competitive',
      infrastructure_readiness:
        (feature.properties.infrastructure_readiness as InfrastructureReadiness) ?? 'grid_first',
      province: feature.properties.province as string,
      site_type: feature.properties.site_type as string,
      category: feature.properties.category as string,
      area_ha: feature.properties.area_ha as number | null,
      cbam_exposed:
        feature.properties.cbam_exposed === true || feature.properties.cbam_exposed === 'true',
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

  // 50km radius circle around selected site
  const radiusCircle = useMemo(() => {
    if (!selectedSite || !scorecard) return null;
    const row = scorecard.find((r) => r.site_id === selectedSite);
    if (!row) return null;
    return createCircleGeoJSON(row.longitude, row.latitude, RADIUS_KM);
  }, [selectedSite, scorecard]);

  const resetView = useCallback(() => {
    selectSite(null);
    mapRef.current?.flyTo({
      center: [INITIAL_CENTER.longitude, INITIAL_CENTER.latitude],
      zoom: INITIAL_ZOOM,
      duration: 2000,
    });
  }, [selectSite]);

  return (
    <div className="absolute inset-0">
      <Map
        ref={mapRef}
        initialViewState={{
          ...INITIAL_CENTER,
          zoom: INITIAL_ZOOM,
        }}
        mapStyle={mapStyle as string}
        style={{ width: '100%', height: '100%' }}
        interactiveLayerIds={measuring ? [] : ['kek-circles']}
        onClick={measuring ? undefined : handleClick}
        onMouseEnter={measuring ? undefined : handleMouseEnter}
        onMouseLeave={measuring ? undefined : handleMouseLeave}
        onZoom={handleZoom}
      >
        <NavigationControl position="bottom-right" />

        <SiteMarkers hoverInfo={hoverInfo} />
        <RasterOverlay />
        <VectorOverlay />
        <InfraMarkers />
        <MeasureTool onMeasuringChange={setMeasuring} />

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

        {/* Within-boundary buildable overlay (clipped to KEK) */}
        {wbBuildable && (
          <Source id="wb-buildable" type="geojson" data={wbBuildable}>
            <Layer
              id="wb-buildable-fill"
              type="fill"
              paint={{
                'fill-color': '#66BB6A',
                'fill-opacity': 0.35,
              }}
            />
            <Layer
              id="wb-buildable-outline"
              type="line"
              paint={{
                'line-color': '#43A047',
                'line-width': 1.5,
                'line-opacity': 0.7,
              }}
            />
          </Source>
        )}
      </Map>

      {/* Back to National View button — centered top, above assumptions panel */}
      {(selectedSite || isZoomedIn) && (
        <button
          onClick={resetView}
          className="absolute top-[72px] left-1/2 -translate-x-1/2 z-40 rounded-xl px-5 py-2 text-sm font-medium transition-all cursor-pointer hover:scale-[1.02]"
          style={{
            backdropFilter: 'var(--blur)',
            WebkitBackdropFilter: 'var(--blur)',
            background: 'var(--glass)',
            border: '1px solid var(--glass-border-bright)',
            boxShadow: 'var(--panel-shadow)',
            color: 'var(--text-primary)',
          }}
        >
          ‹ Back to National View
        </button>
      )}
    </div>
  );
}

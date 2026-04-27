import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { MapLayerMouseEvent, MapRef, ViewStateChangeEvent } from 'react-map-gl/maplibre';
import Map, { Layer, NavigationControl, Popup, Source } from 'react-map-gl/maplibre';
import 'maplibre-gl/dist/maplibre-gl.css';

import { useMapLayers } from '../../hooks/useMapLayers';
import {
  fetchSiteBuildable,
  fetchSiteBuildings,
  fetchSitePolygon,
  fetchSiteRooftopTiles,
} from '../../lib/api';
import { MAP_STYLES } from '../../lib/constants';
import type { ActionFlag, EconomicTier, InfrastructureReadiness } from '../../lib/types';
import { useDashboardStore } from '../../store/dashboard';
import InfraMarkers from './InfraMarkers';
import MeasureTool from './MeasureTool';
import RasterOverlay from './RasterOverlay';
import type { HoverInfo } from './SiteMarkers';
import SiteMarkers from './SiteMarkers';
import VectorOverlay from './VectorOverlay';

const INITIAL_CENTER = { longitude: 118.0, latitude: -2.5 };
const INITIAL_ZOOM = 4;
const KEK_ZOOM = 11;
// When the user zooms in past this threshold, auto-collapse the bottom panel
// if the Ranked Table is active. They're focused on a region now, not browsing.
const AUTO_COLLAPSE_ZOOM = 8;
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
  // v4.1 rooftop solar — buildings + tile rectangles for the selected site.
  // Fetched per site (lightweight: per-site tiles are 1-50 KB each).
  const [siteBuildings, setSiteBuildings] = useState<GeoJSON.FeatureCollection | null>(null);
  const [rooftopTiles, setRooftopTiles] = useState<GeoJSON.FeatureCollection | null>(null);
  // Click-aggregate popup state — spec §3.6 F11. Computed from rooftopTiles
  // by filtering to the clicked tile's cluster_id.
  const [tilePopup, setTilePopup] = useState<{
    longitude: number;
    latitude: number;
    clusterId: number;
    tileCount: number;
    panelCount: number;
    kwDc: number;
    kwAc: number;
    mwhPerYear: number | null;
    buildingCount: number;
  } | null>(null);
  const [hoverInfo, setHoverInfo] = useState<HoverInfo | null>(null);
  const [isZoomedIn, setIsZoomedIn] = useState(false);
  const [measuring, setMeasuring] = useState(false);
  const mapStyleKey = useDashboardStore((s) => s.mapStyle);
  // Track the previous crossing so we only auto-collapse on the upward transition,
  // not on every zoom event while already zoomed in (otherwise the user couldn't
  // reopen the panel while still zoomed).
  const wasZoomedPastThresholdRef = useRef(false);

  const mapStyle = (MAP_STYLES[mapStyleKey] ?? MAP_STYLES.dark).style;

  const handleZoom = useCallback((e: ViewStateChangeEvent) => {
    const zoom = e.viewState.zoom;
    setIsZoomedIn(zoom > INITIAL_ZOOM + 1);

    const pastThreshold = zoom > AUTO_COLLAPSE_ZOOM;
    // Fire only on the upward crossing, only on the Ranked Table tab, only
    // when the panel is currently open. Asymmetric by design: zooming out
    // does not re-open the panel — that stays a user decision.
    // Read state via getState() so this callback stays stable and doesn't
    // rebind the onMove listener on every tab/collapse change.
    if (pastThreshold && !wasZoomedPastThresholdRef.current) {
      const { activeTab, bottomPanelCollapsed, setBottomPanelCollapsed } =
        useDashboardStore.getState();
      if (activeTab === 'table' && !bottomPanelCollapsed) {
        setBottomPanelCollapsed(true);
      }
    }
    wasZoomedPastThresholdRef.current = pastThreshold;
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

  // Fetch rooftop solar layers (v4.1) — buildings + tile rectangles. Two
  // separate calls because they live in different parquets server-side.
  // Errors are silenced because pipeline output is optional; the rooftop
  // layers just don't render if the parquets aren't generated yet.
  useEffect(() => {
    if (!selectedSite) {
      setSiteBuildings(null);
      setRooftopTiles(null);
      return;
    }
    fetchSiteBuildings(selectedSite)
      .then((data) => setSiteBuildings(data.features?.length ? data : null))
      .catch(() => setSiteBuildings(null));
    fetchSiteRooftopTiles(selectedSite)
      .then((data) => setRooftopTiles(data.features?.length ? data : null))
      .catch(() => setRooftopTiles(null));
    // Dismiss any stale cluster popup when the user switches sites
    setTilePopup(null);
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

      // v4.1 rooftop tile click → compute cluster aggregate popup (spec §3.6 F11).
      // Branch on the feature's layer id; properties shape differs by source.
      const layerId = feature.layer?.id;
      if (layerId === 'rooftop-tiles-fill' && rooftopTiles) {
        const clusterId = feature.properties.cluster_id as number;
        const clusterTiles = rooftopTiles.features.filter(
          (f) => f.properties?.cluster_id === clusterId,
        );
        const buildingIds = new Set(
          clusterTiles.map((f) => f.properties?.building_id as string),
        );
        const tileCount = clusterTiles.length;
        const panelCount = clusterTiles.reduce(
          (acc, f) => acc + ((f.properties?.panels_in_tile as number) ?? 0),
          0,
        );
        const kwDc = clusterTiles.reduce(
          (acc, f) => acc + ((f.properties?.tile_kw_dc as number) ?? 0),
          0,
        );
        const kwAc = clusterTiles.reduce(
          (acc, f) => acc + ((f.properties?.tile_kw_ac as number) ?? 0),
          0,
        );
        // Annual MWh = AC capacity × PVOUT (kWh/kWp/yr) / 1000. Use the
        // selected site's PVOUT — same number that drives existing wb/gc LCOE.
        const siteRow = scorecard?.find((r) => r.site_id === selectedSite);
        const pvout =
          siteRow?.pvout_centroid_kwh_kwp_yr ?? siteRow?.pvout_best_50km_kwh_kwp_yr ?? null;
        const mwhPerYear = pvout != null ? (kwAc * pvout) / 1000 : null;
        setTilePopup({
          longitude: e.lngLat.lng,
          latitude: e.lngLat.lat,
          clusterId,
          tileCount,
          panelCount,
          kwDc,
          kwAc,
          mwhPerYear,
          buildingCount: buildingIds.size,
        });
        return;
      }

      const siteId = feature.properties.site_id as string;
      selectSite(siteId);
    },
    [selectSite, rooftopTiles, scorecard, selectedSite],
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
        interactiveLayerIds={measuring ? [] : ['kek-circles', 'rooftop-tiles-fill']}
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

        {/* v4.1 rooftop solar — building footprints (gray) below tiles, always
            visible when a site is selected so the user can see what GoB v3
            detected even at low zoom. Spec §3.6 F6 + §3.7 (missing-data flag). */}
        {siteBuildings && (
          <Source id="rooftop-buildings" type="geojson" data={siteBuildings}>
            <Layer
              id="rooftop-buildings-fill"
              type="fill"
              minzoom={11}
              paint={{
                'fill-color': '#666666',
                'fill-opacity': 0.18,
              }}
            />
            <Layer
              id="rooftop-buildings-outline"
              type="line"
              minzoom={11}
              paint={{
                'line-color': '#222222',
                'line-width': 0.5,
                'line-opacity': 0.55,
              }}
            />
          </Source>
        )}

        {/* v4.1 rooftop solar — panel tile rectangles (the "show your work"
            layer). Spec §3.6 F9: render at zoom ≥14, fill #1a3a8a, hover
            shows tile capacity. Mobile (< 768px viewport) gets outlines only
            via the building layer above; tiles render desktop-only via the
            zoom threshold which already gates them. */}
        {rooftopTiles && (
          <Source id="rooftop-tiles" type="geojson" data={rooftopTiles}>
            <Layer
              id="rooftop-tiles-fill"
              type="fill"
              minzoom={14}
              paint={{
                'fill-color': '#1a3a8a',
                'fill-opacity': 0.78,
              }}
            />
            <Layer
              id="rooftop-tiles-outline"
              type="line"
              minzoom={14}
              paint={{
                'line-color': '#0a1f4a',
                'line-width': 0.4,
                'line-opacity': 0.85,
              }}
            />
          </Source>
        )}

        {/* Cluster click popup — spec §3.6 F11. Shows tile-level aggregate when
            a tile is clicked. Closes on the popup's own X button or when site
            changes (via the fetch effect above). */}
        {tilePopup && (
          <Popup
            longitude={tilePopup.longitude}
            latitude={tilePopup.latitude}
            onClose={() => setTilePopup(null)}
            closeOnClick={false}
            anchor="bottom"
            offset={12}
          >
            <div
              style={{
                fontFamily:
                  '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
                fontSize: 12,
                lineHeight: 1.55,
                color: '#1a1a1a',
                minWidth: 220,
                padding: '4px 2px',
              }}
            >
              <div
                style={{
                  fontWeight: 600,
                  marginBottom: 6,
                  color: '#0a1f4a',
                  fontSize: 11,
                  textTransform: 'uppercase',
                  letterSpacing: '0.04em',
                }}
              >
                Cluster #{tilePopup.clusterId}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                <span>Buildings:</span>
                <strong style={{ fontVariantNumeric: 'tabular-nums' }}>
                  {tilePopup.buildingCount.toLocaleString()}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                <span>Tiles:</span>
                <strong style={{ fontVariantNumeric: 'tabular-nums' }}>
                  {tilePopup.tileCount.toLocaleString()}
                </strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                <span>Panels:</span>
                <strong style={{ fontVariantNumeric: 'tabular-nums' }}>
                  {tilePopup.panelCount.toLocaleString()}
                </strong>
              </div>
              <div
                style={{
                  marginTop: 6,
                  paddingTop: 6,
                  borderTop: '1px solid rgba(26, 58, 138, 0.18)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 12,
                  fontWeight: 600,
                  color: '#0a1f4a',
                }}
              >
                <span>kW DC:</span>
                <span style={{ fontVariantNumeric: 'tabular-nums' }}>
                  {tilePopup.kwDc.toFixed(1)}
                </span>
              </div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 12,
                  fontWeight: 600,
                  color: '#0a1f4a',
                }}
              >
                <span>kW AC:</span>
                <span style={{ fontVariantNumeric: 'tabular-nums' }}>
                  {tilePopup.kwAc.toFixed(1)}
                </span>
              </div>
              {tilePopup.mwhPerYear != null && (
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 12,
                    color: '#444',
                  }}
                >
                  <span>Annual energy:</span>
                  <span style={{ fontVariantNumeric: 'tabular-nums' }}>
                    ~{tilePopup.mwhPerYear.toFixed(0)} MWh/yr
                  </span>
                </div>
              )}
            </div>
          </Popup>
        )}
      </Map>

      {/* Back to National View button — sits below the legend strip. Header
          is 61px (measured), strip is 62-94, so button at 106 leaves a 12px
          gap below the strip. A notch smaller than before so it doesn't
          fight the strip for attention. */}
      {(selectedSite || isZoomedIn) && (
        <button
          onClick={resetView}
          className="absolute top-[106px] left-1/2 -translate-x-1/2 z-40 rounded-lg px-3 py-1 text-xs font-medium transition-all cursor-pointer hover:scale-[1.02]"
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

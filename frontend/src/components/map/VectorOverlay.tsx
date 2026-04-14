import type maplibregl from 'maplibre-gl';
import { useEffect, useState } from 'react';
import { Layer, Popup, Source, useMap } from 'react-map-gl/maplibre';
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

/** Create a colored circle icon with a white SVG path symbol (matches InfraMarkers pattern) */
function createIconImage(pathData: string, color: string, size: number): ImageData {
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;

  // Colored circle background
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, size / 2 - 1, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,0.8)';
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // White symbol via SVG path (24x24 viewBox, scaled to fit with padding)
  const scale = (size - 8) / 24;
  const offset = 4;
  ctx.fillStyle = '#ffffff';
  ctx.save();
  ctx.translate(offset, offset);
  ctx.scale(scale, scale);
  const path = new Path2D(pathData);
  ctx.fill(path);
  ctx.restore();

  return ctx.getImageData(0, 0, size, size);
}

// SVG path data (24x24 viewBox) — factory with sawtooth roof
const NICKEL_PATH = 'M2 20V9l6-3v3l4-2v3l4-2v3l6-3v12H2z';
// SVG path data (24x24 viewBox) — power plant with smokestacks + smoke
const COAL_PATH = 'M7 20h10v-9h-3V5h-4v6H7v9zm3-17h1v2h-1V3zm3 0h1v2h-1V3z';

/**
 * Renders toggled vector layers: substations, kek_polygons, peatland,
 * protected_forest, industrial. Each has different styling.
 */
interface SubHover {
  longitude: number;
  latitude: number;
  name: string;
  voltage: string;
  capacity_mva: string | number;
}

interface GridLineHover {
  longitude: number;
  latitude: number;
  name: string;
  voltage: string;
}

interface BuildableClick {
  longitude: number;
  latitude: number;
  area_ha: number;
  avg_pvout_annual: number;
  capacity_mwp: number;
}

interface WindBuildableClick {
  longitude: number;
  latitude: number;
  area_ha: number;
  avg_wind_speed_ms: number;
  avg_cf_wind: number;
  capacity_mwp: number;
}

interface NickelHover {
  longitude: number;
  latitude: number;
  name: string;
  project_type: string;
  capacity_tons: number | null;
  cost_usd: number | null;
  shareholder: string;
  esg_ecological: string;
  esg_social: string;
  status: string;
  province: string;
  is_chinese_owned: boolean;
}

interface CoalHover {
  longitude: number;
  latitude: number;
  name: string;
  capacity_mw: number;
  unit_count: number;
  status: string;
  parent: string;
  province: string;
}

export default function VectorOverlay() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const layers = useDashboardStore((s) => s.layers);
  const { current: mapRef } = useMap();
  const [subHover, setSubHover] = useState<SubHover | null>(null);
  const [gridHover, setGridHover] = useState<GridLineHover | null>(null);
  const [buildableClick, setBuildableClick] = useState<BuildableClick | null>(null);
  const [windBuildableClick, setWindBuildableClick] = useState<WindBuildableClick | null>(null);
  const [nickelHover, setNickelHover] = useState<NickelHover | null>(null);
  const [coalHover, setCoalHover] = useState<CoalHover | null>(null);

  // Substation hover handlers
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    const onEnter = (e: maplibregl.MapLayerMouseEvent) => {
      map.getCanvas().style.cursor = 'pointer';
      const feat = e.features?.[0];
      if (feat) {
        const coords = (feat.geometry as GeoJSON.Point).coordinates;
        setSubHover({
          longitude: coords[0],
          latitude: coords[1],
          name: feat.properties?.name ?? '',
          voltage: feat.properties?.voltage ?? '',
          capacity_mva: feat.properties?.capacity_mva ?? '',
        });
      }
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = '';
      setSubHover(null);
    };
    map.on('mouseenter', 'overlay-substations-symbol', onEnter);
    map.on('mouseleave', 'overlay-substations-symbol', onLeave);
    return () => {
      map.off('mouseenter', 'overlay-substations-symbol', onEnter);
      map.off('mouseleave', 'overlay-substations-symbol', onLeave);
    };
  }, [mapRef]);

  // Grid line hover handlers
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    const onEnter = (e: maplibregl.MapLayerMouseEvent) => {
      map.getCanvas().style.cursor = 'pointer';
      const feat = e.features?.[0];
      if (feat) {
        setGridHover({
          longitude: e.lngLat.lng,
          latitude: e.lngLat.lat,
          name: feat.properties?.namobj ?? '',
          voltage: feat.properties?.tegjar ?? '',
        });
      }
    };
    const onMove = (e: maplibregl.MapLayerMouseEvent) => {
      if (gridHover) {
        setGridHover((prev) =>
          prev ? { ...prev, longitude: e.lngLat.lng, latitude: e.lngLat.lat } : null,
        );
      }
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = '';
      setGridHover(null);
    };
    map.on('mouseenter', 'overlay-grid-lines-line', onEnter);
    map.on('mousemove', 'overlay-grid-lines-line', onMove);
    map.on('mouseleave', 'overlay-grid-lines-line', onLeave);
    return () => {
      map.off('mouseenter', 'overlay-grid-lines-line', onEnter);
      map.off('mousemove', 'overlay-grid-lines-line', onMove);
      map.off('mouseleave', 'overlay-grid-lines-line', onLeave);
    };
  }, [mapRef, gridHover]);

  // Buildable polygon click + hover cursor
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    const onEnter = () => {
      map.getCanvas().style.cursor = 'pointer';
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = '';
    };
    const onClick = (e: maplibregl.MapLayerMouseEvent) => {
      const feat = e.features?.[0];
      if (feat) {
        setWindBuildableClick(null);
        setBuildableClick({
          longitude: e.lngLat.lng,
          latitude: e.lngLat.lat,
          area_ha: feat.properties?.area_ha ?? 0,
          avg_pvout_annual: feat.properties?.avg_pvout_annual ?? 0,
          capacity_mwp: feat.properties?.capacity_mwp ?? 0,
        });
      }
    };
    map.on('mouseenter', 'overlay-buildable-polygons-fill', onEnter);
    map.on('mouseleave', 'overlay-buildable-polygons-fill', onLeave);
    map.on('click', 'overlay-buildable-polygons-fill', onClick);
    return () => {
      map.off('mouseenter', 'overlay-buildable-polygons-fill', onEnter);
      map.off('mouseleave', 'overlay-buildable-polygons-fill', onLeave);
      map.off('click', 'overlay-buildable-polygons-fill', onClick);
    };
  }, [mapRef]);

  // Wind buildable polygon click + hover cursor
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    const onEnter = () => {
      map.getCanvas().style.cursor = 'pointer';
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = '';
    };
    const onClick = (e: maplibregl.MapLayerMouseEvent) => {
      const feat = e.features?.[0];
      if (feat) {
        setBuildableClick(null);
        setWindBuildableClick({
          longitude: e.lngLat.lng,
          latitude: e.lngLat.lat,
          area_ha: feat.properties?.area_ha ?? 0,
          avg_wind_speed_ms: feat.properties?.avg_wind_speed_ms ?? 0,
          avg_cf_wind: feat.properties?.avg_cf_wind ?? 0,
          capacity_mwp: feat.properties?.capacity_mwp ?? 0,
        });
      }
    };
    map.on('mouseenter', 'overlay-wind-buildable-fill', onEnter);
    map.on('mouseleave', 'overlay-wind-buildable-fill', onLeave);
    map.on('click', 'overlay-wind-buildable-fill', onClick);
    return () => {
      map.off('mouseenter', 'overlay-wind-buildable-fill', onEnter);
      map.off('mouseleave', 'overlay-wind-buildable-fill', onLeave);
      map.off('click', 'overlay-wind-buildable-fill', onClick);
    };
  }, [mapRef]);

  // Nickel smelter hover handlers
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    const onEnter = (e: maplibregl.MapLayerMouseEvent) => {
      map.getCanvas().style.cursor = 'pointer';
      const feat = e.features?.[0];
      if (feat) {
        const coords = (feat.geometry as GeoJSON.Point).coordinates;
        setNickelHover({
          longitude: coords[0],
          latitude: coords[1],
          name: (feat.properties?.name as string) ?? '',
          project_type: (feat.properties?.project_type as string) ?? '',
          capacity_tons:
            feat.properties?.capacity_tons != null ? Number(feat.properties.capacity_tons) : null,
          cost_usd: feat.properties?.cost_usd != null ? Number(feat.properties.cost_usd) : null,
          shareholder: (feat.properties?.shareholder as string) ?? '',
          esg_ecological: (feat.properties?.esg_ecological as string) ?? '',
          esg_social: (feat.properties?.esg_social as string) ?? '',
          status: (feat.properties?.status as string) ?? '',
          province: (feat.properties?.province as string) ?? '',
          is_chinese_owned:
            feat.properties?.is_chinese_owned === true ||
            feat.properties?.is_chinese_owned === 'true',
        });
      }
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = '';
      setNickelHover(null);
    };
    map.on('mouseenter', 'overlay-nickel-symbol', onEnter);
    map.on('mouseleave', 'overlay-nickel-symbol', onLeave);
    return () => {
      map.off('mouseenter', 'overlay-nickel-symbol', onEnter);
      map.off('mouseleave', 'overlay-nickel-symbol', onLeave);
    };
  }, [mapRef]);

  // Captive coal hover handlers
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    const onEnter = (e: maplibregl.MapLayerMouseEvent) => {
      map.getCanvas().style.cursor = 'pointer';
      const feat = e.features?.[0];
      if (feat) {
        const coords = (feat.geometry as GeoJSON.Point).coordinates;
        setCoalHover({
          longitude: coords[0],
          latitude: coords[1],
          name: (feat.properties?.name as string) ?? '',
          capacity_mw: Number(feat.properties?.capacity_mw) || 0,
          unit_count: Number(feat.properties?.unit_count) || 1,
          status: (feat.properties?.status as string) ?? '',
          parent: (feat.properties?.parent as string) ?? '',
          province: (feat.properties?.province as string) ?? '',
        });
      }
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = '';
      setCoalHover(null);
    };
    map.on('mouseenter', 'overlay-coal-symbol', onEnter);
    map.on('mouseleave', 'overlay-coal-symbol', onLeave);
    return () => {
      map.off('mouseenter', 'overlay-coal-symbol', onEnter);
      map.off('mouseleave', 'overlay-coal-symbol', onLeave);
    };
  }, [mapRef]);

  // Load custom icons onto the map
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    const addIcons = () => {
      if (!map.hasImage('bolt-icon')) {
        map.addImage('bolt-icon', createBoltIcon(24, '#FFD600'), { sdf: false });
      }
      if (!map.hasImage('nickel-icon')) {
        map.addImage('nickel-icon', createIconImage(NICKEL_PATH, '#FF6D00', 28), { sdf: false });
      }
      if (!map.hasImage('coal-icon')) {
        map.addImage('coal-icon', createIconImage(COAL_PATH, '#B71C1C', 28), { sdf: false });
      }
    };
    if (map.isStyleLoaded()) {
      addIcons();
    } else {
      map.on('style.load', addIcons);
      return () => {
        map.off('style.load', addIcons);
      };
    }
  }, [mapRef]);

  return (
    <>
      {/* Substations — point layer */}
      {layerVisibility.substations &&
        layers.substations &&
        !(layers.substations as LayerData)._loading &&
        (() => {
          const points = layers.substations.points ?? layers.substations;
          if (!Array.isArray(points) || !points.length) return null;
          const geojson = {
            type: 'FeatureCollection' as const,
            features: points.map(
              (p: {
                lat: number;
                lon: number;
                name?: string;
                voltage?: string;
                capacity_mva?: string | number;
              }) => ({
                type: 'Feature' as const,
                geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
                properties: {
                  name: p.name ?? '',
                  voltage: p.voltage ?? '',
                  capacity_mva: p.capacity_mva ?? '',
                },
              }),
            ),
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

      {/* Substation hover popup */}
      {subHover && (
        <Popup
          longitude={subHover.longitude}
          latitude={subHover.latitude}
          closeButton={false}
          closeOnClick={false}
          anchor="bottom"
          offset={12}
          className="substation-popup"
        >
          <div
            style={{
              color: 'var(--text-primary)',
              fontSize: 11,
              lineHeight: 1.5,
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 2 }}>{subHover.name}</div>
            {subHover.voltage && <div>{subHover.voltage}</div>}
            {subHover.capacity_mva && <div>{subHover.capacity_mva} MVA</div>}
          </div>
        </Popup>
      )}

      {/* Grid line hover popup */}
      {gridHover && (
        <Popup
          longitude={gridHover.longitude}
          latitude={gridHover.latitude}
          closeButton={false}
          closeOnClick={false}
          anchor="bottom"
          offset={8}
          className="grid-line-popup"
        >
          <div
            style={{
              color: 'var(--text-primary)',
              fontSize: 11,
              lineHeight: 1.5,
            }}
          >
            {gridHover.name && (
              <div style={{ fontWeight: 600, marginBottom: 2 }}>{gridHover.name}</div>
            )}
            {gridHover.voltage && <div>{gridHover.voltage}</div>}
          </div>
        </Popup>
      )}

      {/* Buildable polygon click popup */}
      {buildableClick && (
        <Popup
          longitude={buildableClick.longitude}
          latitude={buildableClick.latitude}
          closeButton={true}
          closeOnClick={false}
          onClose={() => setBuildableClick(null)}
          anchor="bottom"
          offset={12}
          className="buildable-popup"
        >
          <div
            style={{
              color: 'var(--text-primary)',
              fontSize: 12,
              lineHeight: 1.6,
              minWidth: 220,
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 4, color: '#2E7D32' }}>
              Solar Buildable Area
            </div>
            <div>Area: {buildableClick.area_ha.toLocaleString()} ha</div>
            <div>Avg PVOUT: {buildableClick.avg_pvout_annual.toLocaleString()} kWh/kWp/yr</div>
            <div>Max Capacity: {buildableClick.capacity_mwp.toLocaleString()} MWp</div>
          </div>
        </Popup>
      )}

      {/* KEK Polygons */}
      {layerVisibility.kek_polygons &&
        layers.kek_polygons &&
        !layers.kek_polygons._loading &&
        (() => {
          const data = layers.kek_polygons;
          if (!data?.features) return null;
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
      {layerVisibility.peatland &&
        layers.peatland &&
        !layers.peatland._loading &&
        (() => {
          const data = layers.peatland;
          if (!data?.features) return null;
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
      {layerVisibility.protected_forest &&
        layers.protected_forest &&
        !layers.protected_forest._loading &&
        (() => {
          const data = layers.protected_forest;
          if (!data?.features) return null;
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

      {/* Buildable Areas (Polygons) */}
      {layerVisibility.buildable_polygons &&
        layers.buildable_polygons &&
        !layers.buildable_polygons._loading &&
        (() => {
          const data = layers.buildable_polygons;
          if (!data?.features) return null;
          return (
            <Source id="overlay-buildable-polygons" type="geojson" data={data}>
              <Layer
                id="overlay-buildable-polygons-fill"
                type="fill"
                paint={{ 'fill-color': '#4DD0E1', 'fill-opacity': 0.25 }}
              />
              <Layer
                id="overlay-buildable-polygons-outline"
                type="line"
                paint={{ 'line-color': '#00ACC1', 'line-width': 1, 'line-opacity': 0.5 }}
              />
            </Source>
          );
        })()}

      {/* Wind Buildable Areas (Polygons) */}
      {layerVisibility.wind_buildable_polygons &&
        layers.wind_buildable_polygons &&
        !layers.wind_buildable_polygons._loading &&
        (() => {
          const data = layers.wind_buildable_polygons;
          if (!data?.features) return null;
          return (
            <Source id="overlay-wind-buildable" type="geojson" data={data}>
              <Layer
                id="overlay-wind-buildable-fill"
                type="fill"
                paint={{ 'fill-color': '#B39DDB', 'fill-opacity': 0.28 }}
              />
              <Layer
                id="overlay-wind-buildable-outline"
                type="line"
                paint={{ 'line-color': '#7E57C2', 'line-width': 1, 'line-opacity': 0.55 }}
              />
            </Source>
          );
        })()}

      {/* Wind buildable polygon click popup */}
      {windBuildableClick && (
        <Popup
          longitude={windBuildableClick.longitude}
          latitude={windBuildableClick.latitude}
          closeButton={true}
          closeOnClick={false}
          onClose={() => setWindBuildableClick(null)}
          anchor="bottom"
          offset={12}
          className="wind-buildable-popup"
        >
          <div
            style={{
              color: 'var(--text-primary)',
              fontSize: 12,
              lineHeight: 1.6,
              minWidth: 220,
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 4, color: '#B39DDB' }}>
              Wind Buildable Area
            </div>
            <div>Area: {windBuildableClick.area_ha.toLocaleString()} ha</div>
            <div>Avg Wind Speed: {windBuildableClick.avg_wind_speed_ms} m/s</div>
            <div>Avg CF: {(windBuildableClick.avg_cf_wind * 100).toFixed(1)}%</div>
            <div>Max Capacity: {windBuildableClick.capacity_mwp.toLocaleString()} MWp</div>
          </div>
        </Popup>
      )}

      {/* PLN Grid Lines */}
      {layerVisibility.grid_lines &&
        layers.grid_lines &&
        !layers.grid_lines._loading &&
        (() => {
          const data = layers.grid_lines;
          if (!data?.features) return null;
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
      {layerVisibility.industrial &&
        layers.industrial &&
        !layers.industrial._loading &&
        (() => {
          const points = layers.industrial.points ?? layers.industrial;
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

      {/* Nickel Smelters (CGSP) */}
      {layerVisibility.nickel_smelters &&
        layers.nickel_smelters &&
        !(layers.nickel_smelters as LayerData)._loading &&
        (() => {
          const points = (layers.nickel_smelters as LayerData).points ?? layers.nickel_smelters;
          if (!Array.isArray(points) || !points.length) return null;
          const geojson = {
            type: 'FeatureCollection' as const,
            features: points.map(
              (p: {
                lat: number;
                lon: number;
                name?: string;
                project_type?: string;
                status?: string;
                province?: string;
                is_chinese_owned?: boolean;
              }) => ({
                type: 'Feature' as const,
                geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
                properties: {
                  name: p.name ?? '',
                  project_type: p.project_type ?? '',
                  status: p.status ?? '',
                  province: p.province ?? '',
                  is_chinese_owned: p.is_chinese_owned ?? false,
                },
              }),
            ),
          };
          return (
            <Source id="overlay-nickel" type="geojson" data={geojson}>
              <Layer
                id="overlay-nickel-symbol"
                type="symbol"
                layout={{
                  'icon-image': 'nickel-icon',
                  'icon-size': 0.8,
                  'icon-allow-overlap': true,
                  'icon-ignore-placement': true,
                }}
                paint={{
                  'icon-opacity': 0.9,
                }}
              />
            </Source>
          );
        })()}

      {/* Nickel smelter hover popup */}
      {nickelHover && (
        <Popup
          longitude={nickelHover.longitude}
          latitude={nickelHover.latitude}
          closeButton={false}
          closeOnClick={false}
          anchor="bottom"
          offset={14}
          className="nickel-popup"
        >
          <div
            style={{
              color: 'var(--text-primary)',
              fontSize: 11,
              lineHeight: 1.5,
              maxWidth: 240,
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 3, color: '#FF6D00' }}>
              {nickelHover.name}
            </div>
            {nickelHover.project_type && (
              <div style={{ color: 'var(--text-secondary)' }}>{nickelHover.project_type}</div>
            )}
            {nickelHover.capacity_tons != null && (
              <div style={{ color: 'var(--text-secondary)' }}>
                Capacity: {nickelHover.capacity_tons.toLocaleString()} tons
              </div>
            )}
            {nickelHover.cost_usd != null && (
              <div style={{ color: 'var(--text-secondary)' }}>
                Investment: ${(nickelHover.cost_usd / 1e6).toFixed(0)}M
              </div>
            )}
            {nickelHover.status && (
              <div style={{ color: 'var(--text-secondary)' }}>Status: {nickelHover.status}</div>
            )}
            {nickelHover.shareholder && (
              <div style={{ color: 'var(--text-muted)', fontSize: 10 }}>
                {nickelHover.shareholder}
              </div>
            )}
            {nickelHover.province && (
              <div style={{ color: 'var(--text-muted)' }}>{nickelHover.province}</div>
            )}
            {nickelHover.is_chinese_owned && (
              <div style={{ color: '#FFAB40', fontSize: 10, marginTop: 2 }}>Chinese ownership</div>
            )}
            {(nickelHover.esg_ecological || nickelHover.esg_social) && (
              <div
                style={{ marginTop: 3, paddingTop: 3, borderTop: '1px solid var(--border-subtle)' }}
              >
                {nickelHover.esg_ecological && (
                  <div style={{ color: '#EF5350', fontSize: 10 }}>
                    Ecological: {nickelHover.esg_ecological}
                  </div>
                )}
                {nickelHover.esg_social && (
                  <div style={{ color: '#FFA726', fontSize: 10 }}>
                    Social: {nickelHover.esg_social}
                  </div>
                )}
              </div>
            )}
          </div>
        </Popup>
      )}

      {/* Captive Coal Plants (GEM) */}
      {layerVisibility.captive_coal &&
        layers.captive_coal &&
        !(layers.captive_coal as LayerData)._loading &&
        (() => {
          const points = (layers.captive_coal as LayerData).points ?? layers.captive_coal;
          if (!Array.isArray(points) || !points.length) return null;
          const geojson = {
            type: 'FeatureCollection' as const,
            features: points.map(
              (p: {
                lat: number;
                lon: number;
                name?: string;
                capacity_mw?: number;
                unit_count?: number;
                status?: string;
                parent?: string;
                province?: string;
              }) => ({
                type: 'Feature' as const,
                geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
                properties: {
                  name: p.name ?? '',
                  capacity_mw: p.capacity_mw ?? 0,
                  unit_count: p.unit_count ?? 1,
                  status: p.status ?? '',
                  parent: p.parent ?? '',
                  province: p.province ?? '',
                },
              }),
            ),
          };
          return (
            <Source id="overlay-coal" type="geojson" data={geojson}>
              <Layer
                id="overlay-coal-symbol"
                type="symbol"
                layout={{
                  'icon-image': 'coal-icon',
                  'icon-size': 0.8,
                  'icon-allow-overlap': true,
                  'icon-ignore-placement': true,
                }}
                paint={{
                  'icon-opacity': 0.9,
                }}
              />
            </Source>
          );
        })()}

      {/* Captive coal hover popup */}
      {coalHover && (
        <Popup
          longitude={coalHover.longitude}
          latitude={coalHover.latitude}
          closeButton={false}
          closeOnClick={false}
          anchor="bottom"
          offset={14}
          className="coal-popup"
        >
          <div
            style={{
              color: 'var(--text-primary)',
              fontSize: 11,
              lineHeight: 1.5,
              maxWidth: 240,
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 3, color: '#EF5350' }}>
              {coalHover.name}
            </div>
            {coalHover.capacity_mw > 0 && (
              <div style={{ color: 'var(--text-secondary)' }}>
                {coalHover.capacity_mw.toLocaleString()} MW ({coalHover.unit_count} unit
                {coalHover.unit_count !== 1 ? 's' : ''})
              </div>
            )}
            {coalHover.status && (
              <div style={{ color: 'var(--text-secondary)' }}>Status: {coalHover.status}</div>
            )}
            {coalHover.parent && (
              <div style={{ color: 'var(--text-muted)' }}>Owner: {coalHover.parent}</div>
            )}
            {coalHover.province && (
              <div style={{ color: 'var(--text-muted)' }}>{coalHover.province}</div>
            )}
          </div>
        </Popup>
      )}
    </>
  );
}

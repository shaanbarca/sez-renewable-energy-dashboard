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

export default function VectorOverlay() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const layers = useDashboardStore((s) => s.layers);
  const { current: mapRef } = useMap();
  const [subHover, setSubHover] = useState<SubHover | null>(null);
  const [gridHover, setGridHover] = useState<GridLineHover | null>(null);
  const [buildableClick, setBuildableClick] = useState<BuildableClick | null>(null);

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
      return () => {
        map.off('style.load', addIcon);
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
              background: '#1e1e1e',
              color: '#e0e0e0',
              padding: '6px 10px',
              borderRadius: 4,
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
              background: '#1e1e1e',
              color: '#e0e0e0',
              padding: '6px 10px',
              borderRadius: 4,
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
              background: '#1e1e1e',
              color: '#e0e0e0',
              padding: '8px 14px',
              borderRadius: 4,
              fontSize: 11,
              lineHeight: 1.6,
              minWidth: 200,
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 4, color: '#66BB6A' }}>
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
                paint={{ 'fill-color': '#66BB6A', 'fill-opacity': 0.25 }}
              />
              <Layer
                id="overlay-buildable-polygons-outline"
                type="line"
                paint={{ 'line-color': '#388E3C', 'line-width': 1, 'line-opacity': 0.5 }}
              />
            </Source>
          );
        })()}

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
    </>
  );
}

import type maplibregl from 'maplibre-gl';
import { useEffect, useMemo, useState } from 'react';
import { Layer, Popup, Source, useMap } from 'react-map-gl/maplibre';
import { findContainingPolygon } from '../../lib/map/pointInPolygon';
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
// SVG path data (24x24 viewBox) — anvil/ingot shape for steel
const STEEL_PATH = 'M2 18h20v2H2v-2zm1-2h18l-2-4H5L3 16zm4-6h10v2H7v-2zm2-4h6v2H9V6z';
// SVG path data (24x24 viewBox) — cement kiln/silo
const CEMENT_PATH = 'M4 20h16v-6H4v6zm2-14h2v6H6V6zm4 0h4v6h-4V6zm6 0h2v6h-2V6zM5 4h14v1H5V4z';

/**
 * Geothermal icon — universal hot-springs glyph (semicircle "bowl" + 3 steam
 * plumes rising). Same shape used on Japanese maps and ISO 9008 — instantly
 * reads as "geothermal resource", clearly distinct from circular site markers.
 *
 * Renders at 2× the requested logical size and pairs with `pixelRatio: 2` on
 * `map.addImage`, so the icon stays crisp on retina without the canvas rasterizer
 * upsampling at draw time.
 */
function createGeothermalIcon(color: string, size: number, filled: boolean): ImageData {
  const PR = 2;
  const px = size * PR;
  const canvas = document.createElement('canvas');
  canvas.width = px;
  canvas.height = px;
  const ctx = canvas.getContext('2d')!;
  ctx.scale(PR, PR);
  const s = size;

  // ── Steam plumes (3 wavy curls, top half) ────────────────────────────────
  // Strokes use round caps + joins so the plumes don't terminate in jagged ends.
  ctx.strokeStyle = color;
  ctx.lineWidth = Math.max(1.6, s / 14);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  const plumeYTop = s * 0.08;
  const plumeYBottom = s * 0.5;
  const plumeXs = [s * 0.28, s * 0.5, s * 0.72];
  for (const x of plumeXs) {
    ctx.beginPath();
    ctx.moveTo(x, plumeYBottom);
    // S-curl: bend right then left as we rise
    ctx.bezierCurveTo(
      x + s * 0.08,
      s * 0.4,
      x - s * 0.08,
      s * 0.25,
      x,
      plumeYTop,
    );
    ctx.stroke();
  }

  // ── Hot-springs "bowl" (semicircle, bottom third) ────────────────────────
  ctx.beginPath();
  ctx.arc(s * 0.5, s * 0.62, s * 0.4, 0, Math.PI, false);
  ctx.lineTo(s * 0.1, s * 0.62);
  ctx.closePath();
  if (filled) {
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.9)';
    ctx.lineWidth = 1.4;
    ctx.stroke();
  } else {
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(1.8, s / 12);
    ctx.stroke();
  }
  return ctx.getImageData(0, 0, px, px);
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

interface SteelHover {
  longitude: number;
  latitude: number;
  name: string;
  capacity_tpa: number;
  technology: string;
  status: string;
  parent_company: string;
  province: string;
  is_chinese_owned: boolean;
}

interface CementHover {
  longitude: number;
  latitude: number;
  name: string;
  capacity_mtpa: number;
  plant_type: string;
  status: string;
  parent_company: string;
  province: string;
  is_chinese_owned: boolean;
}

interface GeothermalOpHover {
  longitude: number;
  latitude: number;
  name: string;
  id: string;
  capacity_mw: number;
  year_commissioned: number;
  province: string;
  island: string;
  operator: string;
  emission_factor_g_per_kwh: number;
}

interface GeothermalPipelineHover {
  longitude: number;
  latitude: number;
  name: string;
  id: string;
  capacity_mw: number;
  target_year: number;
  province: string;
  island: string;
  scenario: string;
  confidence: string;
}

export default function VectorOverlay() {
  const layerVisibility = useDashboardStore((s) => s.layerVisibility);
  const layers = useDashboardStore((s) => s.layers);
  const scorecard = useDashboardStore((s) => s.scorecard);
  const selectedSite = useDashboardStore((s) => s.selectedSite);
  const { current: mapRef } = useMap();

  // Part 2B: user override — clicking a different buildable polygon overrides the picker's choice.
  // Resets whenever the selected site changes.
  const [overriddenFeatureIndex, setOverriddenFeatureIndex] = useState<number | null>(null);
  useEffect(() => {
    setOverriddenFeatureIndex(null);
  }, [selectedSite]);

  // Part 2A: resolve the buildable polygon that the picker anchored to for the selected site.
  // PIP against best_solar_site_lat/lon; falls back to nearest centroid if no polygon contains it.
  // Part 2B: user's override wins when set.
  const selectedBuildableFeatureIndex = useMemo<number | null>(() => {
    if (!selectedSite || !scorecard) return null;
    if (overriddenFeatureIndex !== null) return overriddenFeatureIndex;
    const row = scorecard.find((r) => r.site_id === selectedSite);
    if (!row) return null;
    const lat = row.best_solar_site_lat;
    const lon = row.best_solar_site_lon;
    if (lat == null || lon == null) return null;
    const fc = layers.buildable_polygons;
    if (!fc || fc._loading || !fc.features?.length) return null;
    const match = findContainingPolygon(fc, lat, lon);
    return match ? match.feature_index : null;
  }, [selectedSite, scorecard, layers.buildable_polygons, overriddenFeatureIndex]);

  const [subHover, setSubHover] = useState<SubHover | null>(null);
  const [gridHover, setGridHover] = useState<GridLineHover | null>(null);
  const [buildableClick, setBuildableClick] = useState<BuildableClick | null>(null);
  const [windBuildableClick, setWindBuildableClick] = useState<WindBuildableClick | null>(null);
  const [nickelHover, setNickelHover] = useState<NickelHover | null>(null);
  const [coalHover, setCoalHover] = useState<CoalHover | null>(null);
  const [steelHover, setSteelHover] = useState<SteelHover | null>(null);
  const [cementHover, setCementHover] = useState<CementHover | null>(null);
  const [geoOpHover, setGeoOpHover] = useState<GeothermalOpHover | null>(null);
  const [geoPipelineHover, setGeoPipelineHover] = useState<GeothermalPipelineHover | null>(null);

  // Geothermal operating PLTP hover handlers
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    const onEnter = (e: maplibregl.MapLayerMouseEvent) => {
      map.getCanvas().style.cursor = 'pointer';
      const feat = e.features?.[0];
      if (feat) {
        const coords = (feat.geometry as GeoJSON.Point).coordinates;
        setGeoOpHover({
          longitude: coords[0],
          latitude: coords[1],
          name: (feat.properties?.name as string) ?? '',
          id: (feat.properties?.id as string) ?? '',
          capacity_mw: Number(feat.properties?.capacity_mw) || 0,
          year_commissioned: Number(feat.properties?.year_commissioned) || 0,
          province: (feat.properties?.province as string) ?? '',
          island: (feat.properties?.island as string) ?? '',
          operator: (feat.properties?.operator as string) ?? '',
          emission_factor_g_per_kwh: Number(feat.properties?.emission_factor_g_per_kwh) || 0,
        });
      }
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = '';
      setGeoOpHover(null);
    };
    map.on('mouseenter', 'overlay-geothermal-operating-symbol', onEnter);
    map.on('mouseleave', 'overlay-geothermal-operating-symbol', onLeave);
    return () => {
      map.off('mouseenter', 'overlay-geothermal-operating-symbol', onEnter);
      map.off('mouseleave', 'overlay-geothermal-operating-symbol', onLeave);
    };
  }, [mapRef]);

  // Geothermal pipeline (RUPTL) hover handlers
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    const onEnter = (e: maplibregl.MapLayerMouseEvent) => {
      map.getCanvas().style.cursor = 'pointer';
      const feat = e.features?.[0];
      if (feat) {
        const coords = (feat.geometry as GeoJSON.Point).coordinates;
        setGeoPipelineHover({
          longitude: coords[0],
          latitude: coords[1],
          name: (feat.properties?.name as string) ?? '',
          id: (feat.properties?.id as string) ?? '',
          capacity_mw: Number(feat.properties?.capacity_mw) || 0,
          target_year: Number(feat.properties?.target_year) || 0,
          province: (feat.properties?.province as string) ?? '',
          island: (feat.properties?.island as string) ?? '',
          scenario: (feat.properties?.scenario as string) ?? '',
          confidence: (feat.properties?.confidence as string) ?? '',
        });
      }
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = '';
      setGeoPipelineHover(null);
    };
    map.on('mouseenter', 'overlay-geothermal-pipeline-symbol', onEnter);
    map.on('mouseleave', 'overlay-geothermal-pipeline-symbol', onLeave);
    return () => {
      map.off('mouseenter', 'overlay-geothermal-pipeline-symbol', onEnter);
      map.off('mouseleave', 'overlay-geothermal-pipeline-symbol', onLeave);
    };
  }, [mapRef]);

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
    // Hover the BG layer (9px circle) — bigger hit area than the inner bolt
    // symbol, so users can mouse anywhere on the visible marker to trigger
    // the popup. Both layers receive events so the bolt still works.
    map.on('mouseenter', 'overlay-substations-bg', onEnter);
    map.on('mouseleave', 'overlay-substations-bg', onLeave);
    map.on('mouseenter', 'overlay-substations-symbol', onEnter);
    map.on('mouseleave', 'overlay-substations-symbol', onLeave);
    return () => {
      map.off('mouseenter', 'overlay-substations-bg', onEnter);
      map.off('mouseleave', 'overlay-substations-bg', onLeave);
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
      setGridHover((prev) =>
        prev ? { ...prev, longitude: e.lngLat.lng, latitude: e.lngLat.lat } : null,
      );
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
  }, [mapRef]);

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
        // Part 2B: if a site is selected, override the picker's chosen polygon.
        if (selectedSite) {
          const fi = feat.properties?.feature_index;
          if (typeof fi === 'number') setOverriddenFeatureIndex(fi);
        }
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
  }, [mapRef, selectedSite]);

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

  // Steel plant hover handlers
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    const onEnter = (e: maplibregl.MapLayerMouseEvent) => {
      map.getCanvas().style.cursor = 'pointer';
      const feat = e.features?.[0];
      if (feat) {
        const coords = (feat.geometry as GeoJSON.Point).coordinates;
        setSteelHover({
          longitude: coords[0],
          latitude: coords[1],
          name: (feat.properties?.name as string) ?? '',
          capacity_tpa: Number(feat.properties?.capacity_tpa) || 0,
          technology: (feat.properties?.technology as string) ?? '',
          status: (feat.properties?.status as string) ?? '',
          parent_company: (feat.properties?.parent_company as string) ?? '',
          province: (feat.properties?.province as string) ?? '',
          is_chinese_owned:
            feat.properties?.is_chinese_owned === true ||
            feat.properties?.is_chinese_owned === 'true',
        });
      }
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = '';
      setSteelHover(null);
    };
    map.on('mouseenter', 'overlay-steel-symbol', onEnter);
    map.on('mouseleave', 'overlay-steel-symbol', onLeave);
    return () => {
      map.off('mouseenter', 'overlay-steel-symbol', onEnter);
      map.off('mouseleave', 'overlay-steel-symbol', onLeave);
    };
  }, [mapRef]);

  // Cement plant hover handlers
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    const onEnter = (e: maplibregl.MapLayerMouseEvent) => {
      map.getCanvas().style.cursor = 'pointer';
      const feat = e.features?.[0];
      if (feat) {
        const coords = (feat.geometry as GeoJSON.Point).coordinates;
        setCementHover({
          longitude: coords[0],
          latitude: coords[1],
          name: (feat.properties?.name as string) ?? '',
          capacity_mtpa: Number(feat.properties?.capacity_mtpa) || 0,
          plant_type: (feat.properties?.plant_type as string) ?? '',
          status: (feat.properties?.status as string) ?? '',
          parent_company: (feat.properties?.parent_company as string) ?? '',
          province: (feat.properties?.province as string) ?? '',
          is_chinese_owned:
            feat.properties?.is_chinese_owned === true ||
            feat.properties?.is_chinese_owned === 'true',
        });
      }
    };
    const onLeave = () => {
      map.getCanvas().style.cursor = '';
      setCementHover(null);
    };
    map.on('mouseenter', 'overlay-cement-symbol', onEnter);
    map.on('mouseleave', 'overlay-cement-symbol', onLeave);
    return () => {
      map.off('mouseenter', 'overlay-cement-symbol', onEnter);
      map.off('mouseleave', 'overlay-cement-symbol', onLeave);
    };
  }, [mapRef]);

  // Load custom icons onto the map
  useEffect(() => {
    const map = mapRef?.getMap();
    if (!map) return;
    const addIcons = () => {
      if (!map.hasImage('bolt-icon')) {
        map.addImage('bolt-icon', createBoltIcon(24, '#FFD600'), {
          sdf: false,
          pixelRatio: 2,
        });
      }
      // Static PNG bolt — used by the substation layer. loadImage is async; we
      // fire-and-forget here so it lands as soon as the network round-trip
      // returns. MapLibre auto-refreshes layers that reference an image once
      // the image is registered, so the marker fills in retroactively.
      if (!map.hasImage('bolt-png')) {
        map
          .loadImage('/icons/bolt.png')
          .then((response) => {
            if (!response || map.hasImage('bolt-png')) return;
            // MapLibre 4.x returns an object with .data; older versions return
            // a HTMLImageElement directly.
            // biome-ignore lint/suspicious/noExplicitAny: MapLibre typing
            const data: any = (response as any).data ?? response;
            map.addImage('bolt-png', data, { pixelRatio: 2 });
          })
          .catch(() => {
            // PNG missing — substation layer falls back to the inner yellow circle.
          });
      }
      if (!map.hasImage('nickel-icon')) {
        map.addImage('nickel-icon', createIconImage(NICKEL_PATH, '#FF6D00', 28), { sdf: false });
      }
      if (!map.hasImage('coal-icon')) {
        map.addImage('coal-icon', createIconImage(COAL_PATH, '#B71C1C', 28), { sdf: false });
      }
      if (!map.hasImage('steel-icon')) {
        map.addImage('steel-icon', createIconImage(STEEL_PATH, '#5C6BC0', 28), { sdf: false });
      }
      if (!map.hasImage('cement-icon')) {
        map.addImage('cement-icon', createIconImage(CEMENT_PATH, '#78909C', 28), { sdf: false });
      }
      if (!map.hasImage('geo-op-icon')) {
        map.addImage('geo-op-icon', createGeothermalIcon('#E53935', 32, true), {
          sdf: false,
          pixelRatio: 2,
        });
      }
      if (!map.hasImage('geo-pipeline-pre2030-icon')) {
        map.addImage(
          'geo-pipeline-pre2030-icon',
          createGeothermalIcon('#FFB300', 32, false),
          { sdf: false, pixelRatio: 2 },
        );
      }
      if (!map.hasImage('geo-pipeline-post2030-icon')) {
        map.addImage(
          'geo-pipeline-post2030-icon',
          createGeothermalIcon('#9E9E9E', 32, false),
          { sdf: false, pixelRatio: 2 },
        );
      }
    };
    // Always attach the style.load listener so icons are re-registered every
    // time the user switches basemap (satellite ↔ dark ↔ light ↔ voyager).
    // MapLibre wipes all addImage'd images on style.setStyle, so without this
    // re-registration the symbol layers (cement / steel / nickel / coal /
    // geothermal) silently render nothing after the first style swap.
    if (map.isStyleLoaded()) {
      addIcons();
    }
    map.on('style.load', addIcons);
    return () => {
      map.off('style.load', addIcons);
    };
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
              {/* Fully invisible circle — kept only as a 9px hover hit-target
                  around the bolt so the popup is easier to trigger. */}
              <Layer
                id="overlay-substations-bg"
                type="circle"
                paint={{
                  'circle-radius': 9,
                  'circle-color': '#000000',
                  'circle-opacity': 0,
                  'circle-stroke-color': '#FFD600',
                  'circle-stroke-width': 1.5,
                  'circle-stroke-opacity': 0,
                }}
              />
              <Layer
                id="overlay-substations-symbol"
                type="symbol"
                layout={{
                  'icon-image': [
                    'coalesce',
                    ['image', 'bolt-png'],
                    ['image', 'bolt-icon'],
                  ],
                  'icon-size': 0.4,
                  'icon-allow-overlap': true,
                  'icon-ignore-placement': true,
                }}
                paint={{
                  'icon-opacity': 1,
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
              minWidth: 160,
            }}
          >
            <div
              style={{
                fontSize: 10,
                textTransform: 'uppercase',
                letterSpacing: 0.4,
                color: 'var(--text-secondary)',
                marginBottom: 2,
              }}
            >
              Substation
            </div>
            <div style={{ fontWeight: 600, marginBottom: 4 }}>
              {subHover.name || '—'}
            </div>
            {subHover.voltage && (
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <span style={{ color: 'var(--text-secondary)' }}>Voltage</span>
                <span style={{ fontVariantNumeric: 'tabular-nums' }}>
                  {subHover.voltage}
                </span>
              </div>
            )}
            {subHover.capacity_mva && (
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <span style={{ color: 'var(--text-secondary)' }}>Capacity</span>
                <span style={{ fontVariantNumeric: 'tabular-nums' }}>
                  {subHover.capacity_mva} MVA
                </span>
              </div>
            )}
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

      {/* Site Boundaries — combined KEK (blue) + non-KEK industrial (orange) */}
      {layerVisibility.site_boundaries &&
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

      {layerVisibility.site_boundaries &&
        layers.industrial_polygons &&
        !layers.industrial_polygons._loading &&
        (() => {
          const data = layers.industrial_polygons;
          if (!data?.features) return null;
          return (
            <Source id="overlay-industrial-polygons" type="geojson" data={data}>
              <Layer
                id="overlay-industrial-polygons-fill"
                type="fill"
                paint={{ 'fill-color': '#FFA726', 'fill-opacity': 0.1 }}
              />
              <Layer
                id="overlay-industrial-polygons-line"
                type="line"
                paint={{ 'line-color': '#FB8C00', 'line-width': 1.5, 'line-opacity': 0.7 }}
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
              {selectedBuildableFeatureIndex !== null && (
                <Layer
                  id="overlay-buildable-polygons-selected-fill"
                  type="fill"
                  filter={['==', ['get', 'feature_index'], selectedBuildableFeatureIndex]}
                  paint={{ 'fill-color': '#FFD54F', 'fill-opacity': 0.6 }}
                />
              )}
              {selectedBuildableFeatureIndex !== null && (
                <Layer
                  id="overlay-buildable-polygons-selected-outline"
                  type="line"
                  filter={['==', ['get', 'feature_index'], selectedBuildableFeatureIndex]}
                  paint={{ 'line-color': '#FFA000', 'line-width': 3 }}
                />
              )}
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

      {/* Steel Plants (GEM) */}
      {layerVisibility.steel_plants &&
        layers.steel_plants &&
        !(layers.steel_plants as LayerData)._loading &&
        (() => {
          const points = (layers.steel_plants as LayerData).points ?? layers.steel_plants;
          if (!Array.isArray(points) || !points.length) return null;
          const geojson = {
            type: 'FeatureCollection' as const,
            features: points.map(
              (p: {
                lat: number;
                lon: number;
                name?: string;
                capacity_tpa?: number;
                technology?: string;
                status?: string;
                parent_company?: string;
                province?: string;
                is_chinese_owned?: boolean;
              }) => ({
                type: 'Feature' as const,
                geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
                properties: {
                  name: p.name ?? '',
                  capacity_tpa: p.capacity_tpa ?? 0,
                  technology: p.technology ?? '',
                  status: p.status ?? '',
                  parent_company: p.parent_company ?? '',
                  province: p.province ?? '',
                  is_chinese_owned: p.is_chinese_owned ?? false,
                },
              }),
            ),
          };
          return (
            <Source id="overlay-steel" type="geojson" data={geojson}>
              <Layer
                id="overlay-steel-symbol"
                type="symbol"
                layout={{
                  'icon-image': 'steel-icon',
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

      {/* Steel plant hover popup */}
      {steelHover && (
        <Popup
          longitude={steelHover.longitude}
          latitude={steelHover.latitude}
          closeButton={false}
          closeOnClick={false}
          anchor="bottom"
          offset={14}
          className="steel-popup"
        >
          <div
            style={{
              color: 'var(--text-primary)',
              fontSize: 11,
              lineHeight: 1.5,
              maxWidth: 240,
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 3, color: '#5C6BC0' }}>
              {steelHover.name}
            </div>
            {steelHover.capacity_tpa > 0 && (
              <div style={{ color: 'var(--text-secondary)' }}>
                {(steelHover.capacity_tpa / 1e6).toFixed(1)}M tpa
              </div>
            )}
            {steelHover.technology && (
              <div style={{ color: 'var(--text-secondary)' }}>{steelHover.technology}</div>
            )}
            {steelHover.status && (
              <div style={{ color: 'var(--text-secondary)' }}>Status: {steelHover.status}</div>
            )}
            {steelHover.parent_company && (
              <div style={{ color: 'var(--text-muted)' }}>{steelHover.parent_company}</div>
            )}
            {steelHover.province && (
              <div style={{ color: 'var(--text-muted)' }}>{steelHover.province}</div>
            )}
            {steelHover.is_chinese_owned && (
              <div style={{ color: '#FFAB40', fontSize: 10, marginTop: 2 }}>Chinese ownership</div>
            )}
          </div>
        </Popup>
      )}

      {/* Cement Plants (GEM) */}
      {layerVisibility.cement_plants &&
        layers.cement_plants &&
        !(layers.cement_plants as LayerData)._loading &&
        (() => {
          const points = (layers.cement_plants as LayerData).points ?? layers.cement_plants;
          if (!Array.isArray(points) || !points.length) return null;
          const geojson = {
            type: 'FeatureCollection' as const,
            features: points.map(
              (p: {
                lat: number;
                lon: number;
                name?: string;
                capacity_mtpa?: number;
                plant_type?: string;
                status?: string;
                parent_company?: string;
                province?: string;
                is_chinese_owned?: boolean;
              }) => ({
                type: 'Feature' as const,
                geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
                properties: {
                  name: p.name ?? '',
                  capacity_mtpa: p.capacity_mtpa ?? 0,
                  plant_type: p.plant_type ?? '',
                  status: p.status ?? '',
                  parent_company: p.parent_company ?? '',
                  province: p.province ?? '',
                  is_chinese_owned: p.is_chinese_owned ?? false,
                },
              }),
            ),
          };
          return (
            <Source id="overlay-cement" type="geojson" data={geojson}>
              <Layer
                id="overlay-cement-symbol"
                type="symbol"
                layout={{
                  'icon-image': 'cement-icon',
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

      {/* Cement plant hover popup */}
      {cementHover && (
        <Popup
          longitude={cementHover.longitude}
          latitude={cementHover.latitude}
          closeButton={false}
          closeOnClick={false}
          anchor="bottom"
          offset={14}
          className="cement-popup"
        >
          <div
            style={{
              color: 'var(--text-primary)',
              fontSize: 11,
              lineHeight: 1.5,
              maxWidth: 240,
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 3, color: '#78909C' }}>
              {cementHover.name}
            </div>
            {cementHover.capacity_mtpa > 0 && (
              <div style={{ color: 'var(--text-secondary)' }}>
                {cementHover.capacity_mtpa.toFixed(1)} Mtpa
              </div>
            )}
            {cementHover.plant_type && (
              <div style={{ color: 'var(--text-secondary)' }}>{cementHover.plant_type}</div>
            )}
            {cementHover.status && (
              <div style={{ color: 'var(--text-secondary)' }}>Status: {cementHover.status}</div>
            )}
            {cementHover.parent_company && (
              <div style={{ color: 'var(--text-muted)' }}>{cementHover.parent_company}</div>
            )}
            {cementHover.province && (
              <div style={{ color: 'var(--text-muted)' }}>{cementHover.province}</div>
            )}
            {cementHover.is_chinese_owned && (
              <div style={{ color: '#FFAB40', fontSize: 10, marginTop: 2 }}>Chinese ownership</div>
            )}
          </div>
        </Popup>
      )}

      {/* F2: Geothermal — Operating PLTPs.
          Red ring (steam plumes vibe) so they read as "live dispatchable RE". */}
      {layerVisibility.geothermal_operating &&
        layers.geothermal_operating &&
        !(layers.geothermal_operating as LayerData)._loading &&
        (() => {
          const points =
            (layers.geothermal_operating as LayerData).points ?? layers.geothermal_operating;
          if (!Array.isArray(points) || !points.length) return null;
          const geojson = {
            type: 'FeatureCollection' as const,
            features: points.map(
              (p: {
                lat: number;
                lon: number;
                id?: string;
                name?: string;
                capacity_mw?: number;
                year_commissioned?: number;
                province?: string;
                island?: string;
                operator?: string;
                emission_factor_g_per_kwh?: number;
              }) => ({
                type: 'Feature' as const,
                geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
                properties: {
                  id: p.id ?? '',
                  name: p.name ?? '',
                  capacity_mw: p.capacity_mw ?? 0,
                  year_commissioned: p.year_commissioned ?? 0,
                  province: p.province ?? '',
                  island: p.island ?? '',
                  operator: p.operator ?? '',
                  emission_factor_g_per_kwh: p.emission_factor_g_per_kwh ?? 0,
                },
              }),
            ),
          };
          return (
            <Source id="overlay-geothermal-operating" type="geojson" data={geojson}>
              <Layer
                id="overlay-geothermal-operating-symbol"
                type="symbol"
                layout={{
                  'icon-image': 'geo-op-icon',
                  'icon-size': [
                    'interpolate',
                    ['linear'],
                    ['get', 'capacity_mw'],
                    0,
                    0.7,
                    100,
                    0.85,
                    400,
                    1.05,
                  ],
                  'icon-allow-overlap': true,
                  'icon-ignore-placement': true,
                }}
                paint={{ 'icon-opacity': 0.95 }}
              />
            </Source>
          );
        })()}

      {/* F2: Geothermal — RUPTL pipeline projects.
          Hollow amber ring; pre-2030 brighter than post-2030 to telegraph
          decision-horizon relevance at a glance. */}
      {layerVisibility.geothermal_pipeline &&
        layers.geothermal_pipeline &&
        !(layers.geothermal_pipeline as LayerData)._loading &&
        (() => {
          const points =
            (layers.geothermal_pipeline as LayerData).points ?? layers.geothermal_pipeline;
          if (!Array.isArray(points) || !points.length) return null;
          const geojson = {
            type: 'FeatureCollection' as const,
            features: points.map(
              (p: {
                lat: number;
                lon: number;
                id?: string;
                name?: string;
                capacity_mw?: number;
                target_year?: number;
                province?: string;
                island?: string;
                scenario?: string;
                confidence?: string;
              }) => ({
                type: 'Feature' as const,
                geometry: { type: 'Point' as const, coordinates: [p.lon, p.lat] },
                properties: {
                  id: p.id ?? '',
                  name: p.name ?? '',
                  capacity_mw: p.capacity_mw ?? 0,
                  target_year: p.target_year ?? 0,
                  is_pre2030: (p.target_year ?? 0) < 2030,
                  province: p.province ?? '',
                  island: p.island ?? '',
                  scenario: p.scenario ?? '',
                  confidence: p.confidence ?? '',
                },
              }),
            ),
          };
          return (
            <Source id="overlay-geothermal-pipeline" type="geojson" data={geojson}>
              <Layer
                id="overlay-geothermal-pipeline-symbol"
                type="symbol"
                layout={{
                  'icon-image': [
                    'case',
                    ['get', 'is_pre2030'],
                    'geo-pipeline-pre2030-icon',
                    'geo-pipeline-post2030-icon',
                  ],
                  'icon-size': [
                    'interpolate',
                    ['linear'],
                    ['get', 'capacity_mw'],
                    0,
                    0.7,
                    100,
                    0.85,
                    400,
                    1.05,
                  ],
                  'icon-allow-overlap': true,
                  'icon-ignore-placement': true,
                }}
                paint={{ 'icon-opacity': 0.95 }}
              />
            </Source>
          );
        })()}

      {/* F2: Geothermal operating-PLTP hover popup */}
      {geoOpHover && (
        <Popup
          longitude={geoOpHover.longitude}
          latitude={geoOpHover.latitude}
          closeButton={false}
          closeOnClick={false}
          anchor="bottom"
          offset={14}
          className="geothermal-popup"
        >
          <div
            style={{
              color: 'var(--text-primary)',
              fontSize: 11,
              lineHeight: 1.5,
              maxWidth: 240,
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: 3, color: '#E53935' }}>
              {geoOpHover.name} PLTP
            </div>
            <div style={{ color: 'var(--text-secondary)' }}>
              {geoOpHover.capacity_mw.toFixed(0)} MW · operating since {geoOpHover.year_commissioned}
            </div>
            {geoOpHover.operator && (
              <div style={{ color: 'var(--text-muted)' }}>{geoOpHover.operator}</div>
            )}
            {geoOpHover.province && (
              <div style={{ color: 'var(--text-muted)' }}>
                {geoOpHover.province}
                {geoOpHover.island ? ` · ${geoOpHover.island}` : ''}
              </div>
            )}
            {geoOpHover.emission_factor_g_per_kwh > 0 && (
              <div style={{ color: 'var(--text-secondary)', marginTop: 2 }}>
                NCG: {geoOpHover.emission_factor_g_per_kwh} g CO₂/kWh
              </div>
            )}
          </div>
        </Popup>
      )}

      {/* F2: Geothermal pipeline (RUPTL) hover popup */}
      {geoPipelineHover && (
        <Popup
          longitude={geoPipelineHover.longitude}
          latitude={geoPipelineHover.latitude}
          closeButton={false}
          closeOnClick={false}
          anchor="bottom"
          offset={14}
          className="geothermal-pipeline-popup"
        >
          <div
            style={{
              color: 'var(--text-primary)',
              fontSize: 11,
              lineHeight: 1.5,
              maxWidth: 240,
            }}
          >
            <div
              style={{
                fontWeight: 600,
                marginBottom: 3,
                color: geoPipelineHover.target_year < 2030 ? '#FFB300' : '#9E9E9E',
              }}
            >
              {geoPipelineHover.name}
            </div>
            <div style={{ color: 'var(--text-secondary)' }}>
              {geoPipelineHover.capacity_mw.toFixed(0)} MW · target COD{' '}
              {geoPipelineHover.target_year}
            </div>
            {geoPipelineHover.scenario && (
              <div style={{ color: 'var(--text-muted)' }}>RUPTL {geoPipelineHover.scenario}</div>
            )}
            {geoPipelineHover.province && (
              <div style={{ color: 'var(--text-muted)' }}>
                {geoPipelineHover.province}
                {geoPipelineHover.island ? ` · ${geoPipelineHover.island}` : ''}
              </div>
            )}
            {geoPipelineHover.confidence === 'low' && (
              <div style={{ color: '#FFAB40', fontSize: 10, marginTop: 2 }}>
                Low-confidence location (aggregate)
              </div>
            )}
          </div>
        </Popup>
      )}
    </>
  );
}

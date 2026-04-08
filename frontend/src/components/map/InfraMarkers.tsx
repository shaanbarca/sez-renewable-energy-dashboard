import { useEffect, useMemo, useState } from 'react';
import { Layer, Popup, Source, useMap } from 'react-map-gl/maplibre';
import { fetchInfrastructure, fetchKekSubstations } from '../../lib/api';
import { useDashboardStore } from '../../store/dashboard';

interface InfraMarker {
  kek_id: string;
  lat: number;
  lon: number;
  title: string;
  category: string;
}

interface SubstationMarker {
  lat: number;
  lon: number;
  name: string;
  dist_km: number;
  is_nearest: boolean;
  voltage?: string;
  capacity_mva?: string;
}

// ---------------------------------------------------------------------------
// Infrastructure type classification
// ---------------------------------------------------------------------------

const INFRA_TYPES = {
  airport: { label: 'Airport', color: '#90CAF9' },
  port: { label: 'Port', color: '#42A5F5' },
  road: { label: 'Road / Toll', color: '#78909C' },
  railway: { label: 'Railway', color: '#AB47BC' },
  power: { label: 'Power', color: '#FFD600' },
  water: { label: 'Water', color: '#26C6DA' },
  telecom: { label: 'Telecom', color: '#66BB6A' },
  facility: { label: 'Facility', color: '#EF5350' },
  other: { label: 'Other', color: '#BDBDBD' },
} as const;

type InfraType = keyof typeof INFRA_TYPES;

function classifyInfraType(title: string, category: string): InfraType {
  const t = title.toLowerCase();
  if (/airport|air\s?strip/.test(t)) return 'airport';
  if (/seaport|port|pier|marina|ferry|dryport/.test(t)) return 'port';
  if (/toll|flyover/.test(t)) return 'road';
  if (/railway|train/.test(t)) return 'railway';
  // "station" alone is ambiguous — check for railway/train station vs substation/power
  if (/station/.test(t) && !/sub\s?station|switching|power/.test(t)) return 'railway';
  if (/power|electric|solar power|gas engine|sub\s?station|switching|listrik|pln/.test(t))
    return 'power';
  if (/wtp|wwtp|water|wastewater|clean\s?water|osmosis|canal|pengolahan air|limbah/.test(t))
    return 'water';
  if (/telecom|internet|communication/.test(t)) return 'telecom';
  if (/road|main gate|gate/.test(t)) return 'road';
  if (
    /hospital|clinic|mosque|fire|dormitory|apartment|garden|evacuation|warehouse|hangar|apron|tank farm|shop|studio/i.test(
      t,
    )
  )
    return 'facility';
  // Category-level fallback
  const c = category.toLowerCase();
  if (c.includes('substation')) return 'power';
  if (c.includes('toll')) return 'road';
  if (c.includes('wtp') || c.includes('wwtp')) return 'water';
  return 'other';
}

// ---------------------------------------------------------------------------
// SVG icon generation — colored circle with white symbol
// ---------------------------------------------------------------------------

/** SVG path data for each infrastructure type (24x24 viewBox, centered) */
const ICON_PATHS: Record<InfraType, string> = {
  // Plane
  airport: 'M12 2 L14.5 8 L21 9 L16 13.5 L17 20 L12 17 L7 20 L8 13.5 L3 9 L9.5 8 Z',
  // Anchor
  port: 'M12 3a2 2 0 1 0 0 4 2 2 0 0 0 0-4zm0 6c-1.1 0-2-.9-2-2h-1v2H7l5 9 5-9h-2v-2h-1c0 1.1-.9 2-2 2z',
  // Road/highway
  road: 'M11 3h2v4h2l-3 4-3-4h2V3zm-2 8h6v2h-6v-2zm-2 4h10v2H7v-2zm-2 4h14v2H5v-2z',
  // Train
  railway:
    'M12 2C8.7 2 6 3 6 5v9.5C6 16 7.3 17 9 17l-1.5 2h9L15 17c1.7 0 3-1 3-2.5V5c0-2-2.7-3-6-3zm-2 13a1 1 0 1 1 0-2 1 1 0 0 1 0 2zm4 0a1 1 0 1 1 0-2 1 1 0 0 1 0 2zm3-6H7V6h10v3z',
  // Lightning bolt
  power: 'M13 2L5 14h5l-1 8 8-12h-5z',
  // Water droplet
  water: 'M12 2C8 8 5 11 5 14.5 5 18.1 8.1 21 12 21s7-2.9 7-6.5C19 11 16 8 12 2z',
  // Antenna
  telecom:
    'M12 5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM7 3.5l1.4 1.4A5 5 0 0 0 7 8.5h2a3 3 0 0 1 1-2.2L7 3.5zM17 3.5l-3.4 3.3A3 3 0 0 1 15 8.5h2a5 5 0 0 0-1.4-3.6L17 3.5zM11 10h2v11h-2z',
  // Building
  facility:
    'M5 3v18h6v-5h2v5h6V3H5zm3 14H6v-2h2v2zm0-4H6v-2h2v2zm0-4H6V7h2v2zm4 8h-2v-2h2v2zm0-4h-2v-2h2v2zm0-4h-2V7h2v2zm4 8h-2v-2h2v2zm0-4h-2v-2h2v2zm0-4h-2V7h2v2z',
  // Simple circle
  other: 'M12 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12z',
};

const ICON_SIZE = 32; // canvas pixels (renders at 16px on map due to pixelRatio=2)

function createIconImage(type: InfraType): ImageData {
  const canvas = document.createElement('canvas');
  canvas.width = ICON_SIZE;
  canvas.height = ICON_SIZE;
  const ctx = canvas.getContext('2d')!;
  const color = INFRA_TYPES[type].color;

  // Colored circle background
  ctx.beginPath();
  ctx.arc(ICON_SIZE / 2, ICON_SIZE / 2, ICON_SIZE / 2 - 1, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,0.8)';
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // White symbol via SVG path
  const scale = (ICON_SIZE - 8) / 24; // fit 24x24 path inside circle with 4px padding
  const offset = 4;
  ctx.fillStyle = '#ffffff';
  ctx.save();
  ctx.translate(offset, offset);
  ctx.scale(scale, scale);
  const path = new Path2D(ICON_PATHS[type]);
  ctx.fill(path);
  ctx.restore();

  return ctx.getImageData(0, 0, ICON_SIZE, ICON_SIZE);
}

let iconsRegistered = false;

function registerIcons(map: maplibregl.Map) {
  if (iconsRegistered) return;
  for (const type of Object.keys(INFRA_TYPES) as InfraType[]) {
    const id = `infra-${type}`;
    if (!map.hasImage(id)) {
      map.addImage(id, createIconImage(type), { pixelRatio: 2 });
    }
  }
  iconsRegistered = true;
}

// ---------------------------------------------------------------------------
// GeoJSON helpers
// ---------------------------------------------------------------------------

function infraToGeojson(markers: InfraMarker[]) {
  return {
    type: 'FeatureCollection' as const,
    features: markers.map((m) => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [m.lon, m.lat] },
      properties: {
        title: m.title,
        category: m.category,
        kek_id: m.kek_id,
        infra_type: classifyInfraType(m.title, m.category),
      },
    })),
  };
}

function substationsToGeojson(markers: SubstationMarker[]) {
  return {
    type: 'FeatureCollection' as const,
    features: markers.map((m) => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [m.lon, m.lat] },
      properties: { ...m },
    })),
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface HoverInfo {
  longitude: number;
  latitude: number;
  title: string;
  infraType: InfraType;
}

export default function InfraMarkers() {
  const selectedKek = useDashboardStore((s) => s.selectedKek);
  const [infraMarkers, setInfraMarkers] = useState<InfraMarker[]>([]);
  const [substationMarkers, setSubstationMarkers] = useState<SubstationMarker[]>([]);
  const [hoverInfo, setHoverInfo] = useState<HoverInfo | null>(null);
  const { current: mapInstance } = useMap();

  // Register icons once the map is available
  useEffect(() => {
    if (!mapInstance) return;
    const map = mapInstance.getMap();
    const doRegister = () => registerIcons(map);
    if (map.isStyleLoaded()) {
      doRegister();
    } else {
      map.once('style.load', doRegister);
    }
  }, [mapInstance]);

  // Set up hover handlers for infra-symbols layer
  useEffect(() => {
    if (!mapInstance) return;
    const map = mapInstance.getMap();

    const onEnter = (
      e: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] },
    ) => {
      const feature = e.features?.[0];
      if (!feature?.properties) return;
      const coords = (feature.geometry as GeoJSON.Point).coordinates;
      setHoverInfo({
        longitude: coords[0],
        latitude: coords[1],
        title: feature.properties.title as string,
        infraType: feature.properties.infra_type as InfraType,
      });
      map.getCanvas().style.cursor = 'pointer';
    };

    const onLeave = () => {
      setHoverInfo(null);
      map.getCanvas().style.cursor = '';
    };

    map.on('mouseenter', 'infra-symbols', onEnter);
    map.on('mouseleave', 'infra-symbols', onLeave);
    return () => {
      map.off('mouseenter', 'infra-symbols', onEnter);
      map.off('mouseleave', 'infra-symbols', onLeave);
    };
  }, [mapInstance]);

  useEffect(() => {
    if (!selectedKek) {
      setInfraMarkers([]);
      setSubstationMarkers([]);
      return;
    }

    fetchInfrastructure()
      .then((data) => {
        const resp = data as { markers: InfraMarker[] };
        const forKek = resp.markers.filter((m) => m.kek_id === selectedKek);
        setInfraMarkers(forKek);
      })
      .catch((err) => console.error('Failed to fetch infrastructure:', err));

    fetchKekSubstations(selectedKek)
      .then((data) => {
        const resp = data as { substations: SubstationMarker[] };
        setSubstationMarkers(resp.substations ?? []);
      })
      .catch((err) => console.error('Failed to fetch substations:', err));
  }, [selectedKek]);

  const infraGeojson = useMemo(() => {
    if (!infraMarkers.length) return null;
    return infraToGeojson(infraMarkers);
  }, [infraMarkers]);

  const substationGeojson = useMemo(() => {
    if (!substationMarkers.length) return null;
    return substationsToGeojson(substationMarkers);
  }, [substationMarkers]);

  if (!selectedKek) return null;

  return (
    <>
      {infraGeojson && (
        <Source id="infra-markers" type="geojson" data={infraGeojson}>
          <Layer
            id="infra-symbols"
            type="symbol"
            layout={{
              'icon-image': ['concat', 'infra-', ['get', 'infra_type']],
              'icon-size': 1,
              'icon-allow-overlap': true,
              'icon-ignore-placement': true,
              'text-field': ['get', 'title'],
              'text-size': 10,
              'text-offset': [0, 1.4],
              'text-anchor': 'top',
              'text-optional': true,
              'text-max-width': 12,
            }}
            paint={{
              'text-color': '#e0e0e0',
              'text-halo-color': 'rgba(0,0,0,0.8)',
              'text-halo-width': 1,
              'text-opacity': ['interpolate', ['linear'], ['zoom'], 10, 0, 11, 1],
            }}
          />
        </Source>
      )}

      {/* Hover tooltip for infrastructure */}
      {hoverInfo && (
        <Popup
          longitude={hoverInfo.longitude}
          latitude={hoverInfo.latitude}
          closeButton={false}
          closeOnClick={false}
          anchor="bottom"
          offset={12}
          className="infra-popup"
        >
          <div
            style={{
              padding: '6px 10px',
              background: 'rgba(20, 20, 24, 0.92)',
              borderRadius: 8,
              border: '1px solid rgba(255,255,255,0.12)',
              backdropFilter: 'blur(12px)',
              maxWidth: 220,
            }}
          >
            <div style={{ fontSize: 12, fontWeight: 600, color: '#fff', marginBottom: 3 }}>
              {hoverInfo.title}
            </div>
            <span
              style={{
                fontSize: 10,
                fontWeight: 500,
                color: INFRA_TYPES[hoverInfo.infraType].color,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              {INFRA_TYPES[hoverInfo.infraType].label}
            </span>
          </div>
        </Popup>
      )}

      {substationGeojson && (
        <Source id="substations-nearby" type="geojson" data={substationGeojson}>
          <Layer
            id="substations-circles"
            type="circle"
            paint={{
              'circle-radius': ['case', ['==', ['get', 'is_nearest'], true], 8, 5],
              'circle-color': ['case', ['==', ['get', 'is_nearest'], true], '#FFD600', '#42A5F5'],
              'circle-stroke-color': '#ffffff',
              'circle-stroke-width': 1,
              'circle-opacity': 0.9,
            }}
          />
        </Source>
      )}
    </>
  );
}

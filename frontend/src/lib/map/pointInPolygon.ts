import distance from '@turf/distance';
import { point } from '@turf/helpers';

type Ring = number[][];

interface PolygonFeature {
  type: 'Feature';
  geometry: {
    type: 'Polygon' | 'MultiPolygon';
    coordinates: Ring[] | Ring[][];
  };
  properties?: Record<string, unknown> & { feature_index?: number };
}

interface FeatureCollection {
  type: 'FeatureCollection';
  features: PolygonFeature[];
}

export interface PipMatch {
  feature_index: number;
  distance_km: number;
  matchType: 'contained' | 'nearest';
}

function pointInRing(lon: number, lat: number, ring: Ring): boolean {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const xi = ring[i][0];
    const yi = ring[i][1];
    const xj = ring[j][0];
    const yj = ring[j][1];
    const intersect = yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function pointInPolygonFeature(lon: number, lat: number, feat: PolygonFeature): boolean {
  const geom = feat.geometry;
  if (geom.type === 'Polygon') {
    const rings = geom.coordinates as Ring[];
    if (!rings.length || !pointInRing(lon, lat, rings[0])) return false;
    for (let h = 1; h < rings.length; h++) {
      if (pointInRing(lon, lat, rings[h])) return false;
    }
    return true;
  }
  if (geom.type === 'MultiPolygon') {
    for (const poly of geom.coordinates as Ring[][]) {
      if (!poly.length) continue;
      if (!pointInRing(lon, lat, poly[0])) continue;
      let inHole = false;
      for (let h = 1; h < poly.length; h++) {
        if (pointInRing(lon, lat, poly[h])) {
          inHole = true;
          break;
        }
      }
      if (!inHole) return true;
    }
  }
  return false;
}

function centroidLonLat(feat: PolygonFeature): [number, number] | null {
  const props = feat.properties ?? {};
  const lat = (props as Record<string, unknown>).centroid_lat;
  const lon = (props as Record<string, unknown>).centroid_lon;
  if (typeof lat === 'number' && typeof lon === 'number') return [lon, lat];
  return null;
}

export function findContainingPolygon(
  fc: FeatureCollection | null | undefined,
  lat: number,
  lon: number,
): PipMatch | null {
  if (!fc?.features?.length) return null;
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;

  for (const feat of fc.features) {
    const idx = (feat.properties?.feature_index ?? -1) as number;
    if (idx < 0) continue;
    if (pointInPolygonFeature(lon, lat, feat)) {
      return { feature_index: idx, distance_km: 0, matchType: 'contained' };
    }
  }

  const target = point([lon, lat]);
  let best: PipMatch | null = null;
  for (const feat of fc.features) {
    const idx = (feat.properties?.feature_index ?? -1) as number;
    if (idx < 0) continue;
    const c = centroidLonLat(feat);
    if (!c) continue;
    const d = distance(target, point(c), { units: 'kilometers' });
    if (best === null || d < best.distance_km) {
      best = { feature_index: idx, distance_km: d, matchType: 'nearest' };
    }
  }
  return best;
}

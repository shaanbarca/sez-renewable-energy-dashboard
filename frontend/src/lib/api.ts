import type {
  BenchmarkMode,
  DefaultsResponse,
  ScorecardResponse,
  UserAssumptions,
  UserThresholds,
} from './types';

export async function fetchDefaults(): Promise<DefaultsResponse> {
  const res = await fetch('/api/defaults');
  if (!res.ok) throw new Error(`GET /api/defaults failed: ${res.status}`);
  return res.json();
}

export async function fetchScorecard(
  assumptions: UserAssumptions,
  thresholds: UserThresholds,
  benchmarkMode: BenchmarkMode,
  polygonOverrides?: Record<string, number> | null,
): Promise<ScorecardResponse> {
  const body: Record<string, unknown> = {
    assumptions,
    thresholds,
    benchmark_mode: benchmarkMode,
  };
  // #26 — only include polygon_overrides when at least one site has an active
  // override. Empty/null is the no-op signal so the server can return faster.
  if (polygonOverrides && Object.keys(polygonOverrides).length > 0) {
    body.polygon_overrides = polygonOverrides;
  }
  const res = await fetch('/api/scorecard', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`POST /api/scorecard failed: ${res.status}`);
  return res.json();
}

export async function fetchLayer(name: string): Promise<unknown> {
  const res = await fetch(`/api/layers/${encodeURIComponent(name)}`);
  if (!res.ok) throw new Error(`GET /api/layers/${name} failed: ${res.status}`);
  return res.json();
}

export async function fetchSitePolygon(siteId: string): Promise<unknown> {
  const res = await fetch(`/api/site/${encodeURIComponent(siteId)}/polygon`);
  if (!res.ok) throw new Error(`GET /api/site/${siteId}/polygon failed: ${res.status}`);
  return res.json();
}

export async function fetchSiteBuildable(siteId: string): Promise<GeoJSON.FeatureCollection> {
  const res = await fetch(`/api/site/${encodeURIComponent(siteId)}/buildable`);
  if (!res.ok) throw new Error(`GET /api/site/${siteId}/buildable failed: ${res.status}`);
  return res.json();
}

/** Detected building footprints (Google Open Buildings v3) inside the site's
 * 2 km buffer. Renders as the gray "what was detected" layer beneath rooftop
 * tiles. Empty FeatureCollection when no buildings (post-2023 sites,
 * tourism KEKs). v4.1 rooftop solar feature. */
export async function fetchSiteBuildings(siteId: string): Promise<GeoJSON.FeatureCollection> {
  const res = await fetch(`/api/site/${encodeURIComponent(siteId)}/buildings`);
  if (!res.ok) throw new Error(`GET /api/site/${siteId}/buildings failed: ${res.status}`);
  return res.json();
}

/** Per-tile panel rectangles for the rooftop solar map layer. Each feature is
 * a 6m × 4m tile in EPSG:4326 with properties: tile_idx, cluster_id,
 * building_id, panels_in_tile, tile_kw_dc, tile_kw_ac. Render at zoom ≥14. */
export async function fetchSiteRooftopTiles(siteId: string): Promise<GeoJSON.FeatureCollection> {
  const res = await fetch(`/api/site/${encodeURIComponent(siteId)}/rooftop-tiles`);
  if (!res.ok) throw new Error(`GET /api/site/${siteId}/rooftop-tiles failed: ${res.status}`);
  return res.json();
}

export async function fetchSiteSubstations(siteId: string, radiusKm?: number): Promise<unknown> {
  const params = radiusKm != null ? `?radius_km=${radiusKm}` : '';
  const res = await fetch(`/api/site/${encodeURIComponent(siteId)}/substations${params}`);
  if (!res.ok) throw new Error(`GET /api/site/${siteId}/substations failed: ${res.status}`);
  return res.json();
}

export async function fetchRuptlMetrics(): Promise<unknown> {
  const res = await fetch('/api/ruptl-metrics');
  if (!res.ok) throw new Error(`GET /api/ruptl-metrics failed: ${res.status}`);
  return res.json();
}

export async function fetchInfrastructure(): Promise<unknown> {
  const res = await fetch('/api/layers/infrastructure');
  if (!res.ok) throw new Error(`GET /api/layers/infrastructure failed: ${res.status}`);
  return res.json();
}

export async function fetchMethodology(): Promise<string> {
  const res = await fetch('/api/methodology');
  if (!res.ok) throw new Error(`GET /api/methodology failed: ${res.status}`);
  return res.text();
}

// ---------------------------------------------------------------------------
// Admin polygon override API (#31 phase 2)
//
// All these routes are env-gated server-side: when EEZ_ENABLE_ADMIN_TOOLS is
// unset the router isn't mounted, so calls return either a normal 404 or the
// SPA index.html (depending on whether the SPA fallback is in play). The
// frontend infers admin availability via `probeAdminMode` — it resolves true
// ONLY when the response is real JSON with the expected shape, never on the
// SPA fallback. The localhost-only dependency on the backend additionally
// rejects 403 for non-loopback requests; that also returns false here.
// ---------------------------------------------------------------------------

export interface PolygonOverrideFeature {
  type: 'Feature';
  geometry: GeoJSON.Polygon | GeoJSON.MultiPolygon;
  properties: {
    site_id: string;
    edited_at: string;
    edited_by: string | null;
    notes: string | null;
  };
}

/** Probe `/api/admin/polygons` to determine whether admin tooling is enabled.
 *  Resolves true only when the response is real JSON with the expected shape.
 *  Never throws — admin availability is a soft check; failure means "off." */
export async function probeAdminMode(): Promise<boolean> {
  try {
    const res = await fetch('/api/admin/polygons', { method: 'GET' });
    if (!res.ok) return false;
    const ct = res.headers.get('content-type') ?? '';
    if (!ct.includes('application/json')) return false;
    const body = await res.json();
    return typeof body === 'object' && body !== null && 'site_ids' in body;
  } catch {
    return false;
  }
}

export async function getPolygonOverride(siteId: string): Promise<PolygonOverrideFeature | null> {
  const res = await fetch(`/api/admin/polygons/${encodeURIComponent(siteId)}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GET admin polygon ${siteId} failed: ${res.status}`);
  return res.json();
}

export async function listPolygonOverrides(): Promise<string[]> {
  const res = await fetch('/api/admin/polygons');
  if (!res.ok) throw new Error(`GET admin polygons list failed: ${res.status}`);
  const body = (await res.json()) as { site_ids: string[]; count: number };
  return body.site_ids;
}

export async function savePolygonOverride(
  siteId: string,
  geometry: GeoJSON.Polygon | GeoJSON.MultiPolygon,
  opts: { notes?: string | null; editedBy?: string | null } = {},
): Promise<PolygonOverrideFeature> {
  const res = await fetch(`/api/admin/polygons/${encodeURIComponent(siteId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      geometry,
      notes: opts.notes ?? null,
      edited_by: opts.editedBy ?? null,
    }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`POST admin polygon ${siteId} failed: ${res.status} ${detail}`);
  }
  return res.json();
}

export async function deletePolygonOverride(siteId: string): Promise<void> {
  const res = await fetch(`/api/admin/polygons/${encodeURIComponent(siteId)}`, {
    method: 'DELETE',
  });
  if (!res.ok && res.status !== 404) {
    throw new Error(`DELETE admin polygon ${siteId} failed: ${res.status}`);
  }
}

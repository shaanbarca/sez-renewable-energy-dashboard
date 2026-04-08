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
): Promise<ScorecardResponse> {
  const res = await fetch('/api/scorecard', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      assumptions,
      thresholds,
      benchmark_mode: benchmarkMode,
    }),
  });
  if (!res.ok) throw new Error(`POST /api/scorecard failed: ${res.status}`);
  return res.json();
}

export async function fetchLayer(name: string): Promise<unknown> {
  const res = await fetch(`/api/layers/${encodeURIComponent(name)}`);
  if (!res.ok) throw new Error(`GET /api/layers/${name} failed: ${res.status}`);
  return res.json();
}

export async function fetchKekPolygon(kekId: string): Promise<unknown> {
  const res = await fetch(`/api/kek/${encodeURIComponent(kekId)}/polygon`);
  if (!res.ok) throw new Error(`GET /api/kek/${kekId}/polygon failed: ${res.status}`);
  return res.json();
}

export async function fetchKekSubstations(kekId: string, radiusKm?: number): Promise<unknown> {
  const params = radiusKm != null ? `?radius_km=${radiusKm}` : '';
  const res = await fetch(`/api/kek/${encodeURIComponent(kekId)}/substations${params}`);
  if (!res.ok) throw new Error(`GET /api/kek/${kekId}/substations failed: ${res.status}`);
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

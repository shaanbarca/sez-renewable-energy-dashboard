import { useEffect, useMemo, useState } from 'react';
import { Layer, Source } from 'react-map-gl/maplibre';
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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function markersToGeojson(markers: any[]) {
  return {
    type: 'FeatureCollection' as const,
    features: markers.map((m) => ({
      type: 'Feature' as const,
      geometry: { type: 'Point' as const, coordinates: [m.lon, m.lat] },
      properties: { ...m },
    })),
  };
}

export default function InfraMarkers() {
  const selectedKek = useDashboardStore((s) => s.selectedKek);
  const [infraMarkers, setInfraMarkers] = useState<InfraMarker[]>([]);
  const [substationMarkers, setSubstationMarkers] = useState<SubstationMarker[]>([]);

  useEffect(() => {
    if (!selectedKek) {
      setInfraMarkers([]);
      setSubstationMarkers([]);
      return;
    }

    fetchInfrastructure()
      .then((data) => {
        const resp = data as { markers: InfraMarker[] };
        // Filter to infrastructure for this KEK
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
    return markersToGeojson(infraMarkers);
  }, [infraMarkers]);

  const substationGeojson = useMemo(() => {
    if (!substationMarkers.length) return null;
    return markersToGeojson(substationMarkers);
  }, [substationMarkers]);

  if (!selectedKek) return null;

  return (
    <>
      {infraGeojson && (
        <Source id="infra-markers" type="geojson" data={infraGeojson}>
          <Layer
            id="infra-circles"
            type="circle"
            paint={{
              'circle-radius': 5,
              'circle-color': '#4CAF50',
              'circle-stroke-color': '#ffffff',
              'circle-stroke-width': 1,
              'circle-opacity': 0.85,
            }}
          />
        </Source>
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

import { useEffect, useState, useMemo } from 'react';
import { Source, Layer } from 'react-map-gl/maplibre';
import { useDashboardStore } from '../../store/dashboard';
import { fetchInfrastructure, fetchKekSubstations } from '../../lib/api';

interface InfraFeature {
  type: 'Feature';
  geometry: { type: 'Point'; coordinates: [number, number] };
  properties: {
    name?: string;
    inside_sez: boolean;
    nearest_substation?: boolean;
  };
}

interface InfraResponse {
  type: 'FeatureCollection';
  features: InfraFeature[];
}

interface SubstationFeature {
  type: 'Feature';
  geometry: { type: 'Point'; coordinates: [number, number] };
  properties: {
    name?: string;
    distance_km?: number;
    nearest?: boolean;
  };
}

interface SubstationResponse {
  type: 'FeatureCollection';
  features: SubstationFeature[];
}

export default function InfraMarkers() {
  const selectedKek = useDashboardStore((s) => s.selectedKek);
  const [infra, setInfra] = useState<InfraResponse | null>(null);
  const [substations, setSubstations] = useState<SubstationResponse | null>(null);

  useEffect(() => {
    if (!selectedKek) {
      setInfra(null);
      setSubstations(null);
      return;
    }

    fetchInfrastructure()
      .then((data) => setInfra(data as InfraResponse))
      .catch((err) => console.error('Failed to fetch infrastructure:', err));

    fetchKekSubstations(selectedKek)
      .then((data) => setSubstations(data as SubstationResponse))
      .catch((err) => console.error('Failed to fetch substations:', err));
  }, [selectedKek]);

  // Split infra into inside/outside SEZ
  const insideGeojson = useMemo(() => {
    if (!infra) return null;
    return {
      type: 'FeatureCollection' as const,
      features: infra.features.filter((f) => f.properties.inside_sez),
    };
  }, [infra]);

  const outsideGeojson = useMemo(() => {
    if (!infra) return null;
    return {
      type: 'FeatureCollection' as const,
      features: infra.features.filter((f) => !f.properties.inside_sez),
    };
  }, [infra]);

  // Nearest substation highlighted
  const substationGeojson = useMemo(() => {
    if (!substations) return null;
    return substations;
  }, [substations]);

  if (!selectedKek) return null;

  return (
    <>
      {insideGeojson && insideGeojson.features.length > 0 && (
        <Source id="infra-inside" type="geojson" data={insideGeojson}>
          <Layer
            id="infra-inside-circles"
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
      {outsideGeojson && outsideGeojson.features.length > 0 && (
        <Source id="infra-outside" type="geojson" data={outsideGeojson}>
          <Layer
            id="infra-outside-circles"
            type="circle"
            paint={{
              'circle-radius': 5,
              'circle-color': '#42A5F5',
              'circle-stroke-color': '#ffffff',
              'circle-stroke-width': 1,
              'circle-opacity': 0.85,
            }}
          />
        </Source>
      )}
      {substationGeojson && substationGeojson.features.length > 0 && (
        <Source id="substations-nearby" type="geojson" data={substationGeojson}>
          <Layer
            id="substations-circles"
            type="circle"
            paint={{
              'circle-radius': [
                'case',
                ['==', ['get', 'nearest'], true],
                8,
                5,
              ],
              'circle-color': [
                'case',
                ['==', ['get', 'nearest'], true],
                '#FFD600',
                '#FFF176',
              ],
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

import type { ActionFlag, MapStyleKey } from './types';

export const ACTION_FLAG_COLORS: Record<ActionFlag, string> = {
  solar_now: '#2E7D32',
  invest_resilience: '#F57C00',
  grid_first: '#1565C0',
  firming_needed: '#FFA726',
  plan_late: '#7B1FA2',
  not_competitive: '#C62828',
};

export const ACTION_FLAG_LABELS: Record<ActionFlag, string> = {
  solar_now: 'Solar Now',
  invest_resilience: 'Invest Resilience',
  grid_first: 'Grid First',
  firming_needed: 'Firming Needed',
  plan_late: 'Plan Late',
  not_competitive: 'Not Competitive',
};

export const MAP_STYLES: Record<MapStyleKey, { label: string; style: string | object }> = {
  dark: {
    label: 'Dark',
    style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  },
  light: {
    label: 'Light',
    style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
  },
  voyager: {
    label: 'Voyager',
    style: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
  },
  satellite: {
    label: 'Satellite',
    style: {
      version: 8,
      sources: {
        'esri-satellite': {
          type: 'raster',
          tiles: [
            'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
          ],
          tileSize: 256,
          maxzoom: 18,
          attribution: 'Esri, Maxar, Earthstar Geographics',
        },
      },
      layers: [
        {
          id: 'esri-satellite-layer',
          type: 'raster',
          source: 'esri-satellite',
        },
      ],
    },
  },
};

export const RUPTL_REGION_COLORS: Record<string, string> = {
  JAVA_BALI: '#1976D2',
  SUMATERA: '#388E3C',
  KALIMANTAN: '#F57C00',
  SULAWESI: '#00897B',
  MALUKU: '#7B1FA2',
  PAPUA: '#C62828',
  NTB: '#5D4037',
};

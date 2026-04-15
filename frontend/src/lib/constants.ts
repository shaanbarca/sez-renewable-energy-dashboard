import type { ActionFlag, MapStyleKey } from './types';

export const ACTION_FLAG_COLORS: Record<ActionFlag, string> = {
  solar_now: '#2E7D32',
  cbam_urgent: '#FF6F00',
  wind_now: '#1B5E20',
  hybrid_now: '#2E7D32',
  invest_resilience: '#F57C00',
  invest_battery: '#FFA726',
  invest_transmission: '#0277BD',
  invest_substation: '#00838F',
  grid_first: '#1565C0',
  plan_late: '#7B1FA2',
  not_competitive: '#C62828',
  no_solar_resource: '#78909C',
  no_wind_resource: '#78909C',
  no_re_resource: '#78909C',
};

export const ACTION_FLAG_LABELS: Record<ActionFlag, string> = {
  solar_now: 'Solar Now',
  cbam_urgent: 'CBAM Urgent',
  wind_now: 'Wind Now',
  hybrid_now: 'Hybrid Now',
  invest_resilience: 'Invest Resilience',
  invest_battery: 'Add Battery Storage',
  invest_transmission: 'Build Transmission',
  invest_substation: 'Build Substation',
  grid_first: 'Build Grid',
  plan_late: 'Plan Late',
  not_competitive: 'Not Competitive',
  no_solar_resource: 'No Solar Resource',
  no_wind_resource: 'No Wind Resource',
  no_re_resource: 'No RE Resource',
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

export const GRID_INTEGRATION_COLORS: Record<string, string> = {
  within_boundary: '#4CAF50',
  grid_ready: '#2196F3',
  invest_transmission: '#0277BD',
  invest_substation: '#00838F',
  grid_first: '#F44336',
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

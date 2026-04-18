import type {
  ActionFlag,
  EconomicTier,
  InfrastructureReadiness,
  MapStyleKey,
  ModifierBadge,
} from './types';

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

export const ACTION_FLAG_DESCRIPTIONS: Record<ActionFlag, string> = {
  solar_now:
    'Solar LCOE is already below grid cost at this site. Build now — no subsidy or policy push required.',
  cbam_urgent:
    'Solar alone does not beat grid power, but this plant is a CBAM-tariffed exporter (cement, steel, fertilizer, aluminium, ferronickel). Once you credit the EU carbon tariff avoided by greening, renewable energy becomes cheaper net of CBAM. As EU free allocations phase out 2026–2034, the pressure only grows — act before the tariff bites.',
  wind_now: 'Wind LCOE is already below grid cost at this site. Build now.',
  hybrid_now:
    'A solar+wind blend (optimally sized) beats grid cost at this site. Hybrid reduces the battery bridge you would need for 24/7 supply.',
  invest_resilience:
    'Solar LCOE is within 20% of grid cost, but the site demands high reliability (≥75% uptime). The decision is not price alone — it is the cost of outages. BESS or firming is the gating investment.',
  invest_battery:
    'Daytime solar is competitive, but covering overnight demand requires a battery storage adder. Sizing the BESS correctly is what closes the 24/7 gap.',
  invest_transmission:
    'The best nearby solar buildable area sits close to a substation, but that substation is not connected to this site. A transmission line is the missing piece — not more capacity.',
  invest_substation:
    'A substation is near the site, but its existing capacity cannot absorb the new solar MWp. Upgrading (or building) substation capacity is what unlocks the project.',
  grid_first:
    'No substation within reach of either the site or the nearest solar buildable area. Grid expansion must come before any renewable investment is viable here.',
  plan_late:
    'This site is long-dated. Solar LCOE keeps falling every year — locking in today at current capex is leaving money on the table. Plan the project, stage the capital.',
  not_competitive:
    'Solar LCOE is more than 20% above grid cost here. No near-term economic case for RE; revisit as grid prices rise or solar capex falls further.',
  no_solar_resource:
    'PVOUT below the buildability threshold within a 50 km radius. Solar is not the answer at this location — look at wind, hybrid, or grid power.',
  no_wind_resource:
    'Wind capacity factor too low within 50 km (insufficient wind speed or buildable area). Wind is not the answer here.',
  no_re_resource: 'Neither solar nor wind meets the threshold. This site is grid-dependent.',
};

// ── 2D Classification System (Option C) ──────────────────────────────────

export const ECONOMIC_TIER_COLORS: Record<EconomicTier, string> = {
  full_re: '#2E7D32',
  partial_re: '#66BB6A',
  near_parity: '#F57C00',
  not_competitive: '#C62828',
  no_resource: '#78909C',
};

export const ECONOMIC_TIER_LABELS: Record<EconomicTier, string> = {
  full_re: 'Full RE',
  partial_re: 'Partial RE',
  near_parity: 'Near Parity',
  not_competitive: 'Not Competitive',
  no_resource: 'No Resource',
};

export const ECONOMIC_TIER_DESCRIPTIONS: Record<EconomicTier, string> = {
  full_re: 'RE + storage beats grid for 24/7 supply. Deploy now.',
  partial_re: 'Daytime RE beats grid. Nighttime stays on grid. Still cuts 42% of energy cost.',
  near_parity: 'RE is within 20% of grid cost. CBAM savings or future cost drops could tip it.',
  not_competitive: 'RE costs exceed grid by more than 20%.',
  no_resource: 'No viable renewable resource within search radius.',
};

export const INFRA_READINESS_COLORS: Record<InfrastructureReadiness, string> = {
  within_boundary: 'transparent',
  grid_ready: '#42A5F5',
  invest_transmission: '#0277BD',
  invest_substation: '#00838F',
  grid_first: '#1565C0',
};

export const INFRA_READINESS_LABELS: Record<InfrastructureReadiness, string> = {
  within_boundary: 'Within Boundary',
  grid_ready: 'Grid Ready',
  invest_transmission: 'Build Transmission',
  invest_substation: 'Build Substation',
  grid_first: 'Build Grid',
};

export const INFRA_READINESS_DESCRIPTIONS: Record<InfrastructureReadiness, string> = {
  within_boundary: 'RE can be sited within KEK boundary. No grid extension needed.',
  grid_ready: 'Substation nearby with capacity. Standard grid connection.',
  invest_transmission: 'RE site is far from substation. Transmission line needed.',
  invest_substation: 'Substation upgrade or new substation needed near RE site.',
  grid_first: 'No substation near KEK or RE site. Major grid infrastructure required.',
};

export const MODIFIER_BADGE_COLORS: Record<ModifierBadge, string> = {
  cbam_urgent: '#FF6F00',
  plan_late: '#7B1FA2',
  storage_info: '#FFA726',
};

export const MODIFIER_BADGE_LABELS: Record<ModifierBadge, string> = {
  cbam_urgent: 'CBAM Urgent',
  plan_late: 'Plan Late',
  storage_info: 'Storage Info',
};

export const ECONOMIC_TIER_HIERARCHY: EconomicTier[] = [
  'full_re',
  'partial_re',
  'near_parity',
  'not_competitive',
  'no_resource',
];

export const INFRA_READINESS_HIERARCHY: InfrastructureReadiness[] = [
  'within_boundary',
  'grid_ready',
  'invest_transmission',
  'invest_substation',
  'grid_first',
];

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

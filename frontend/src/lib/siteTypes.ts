/**
 * Site type registry — TypeScript mirror of src/model/site_types.py.
 *
 * Adding a new site type = adding one entry to SITE_TYPES below
 * and one member to the SiteType union. The compiler will flag
 * any missing entries via Record<SiteType, ...>.
 */

export type SiteType = 'kek' | 'standalone' | 'cluster' | 'ki';
export type Sector =
  | 'steel'
  | 'cement'
  | 'aluminium'
  | 'fertilizer'
  | 'nickel'
  | 'ammonia'
  | 'petrochemical'
  | 'mixed';

interface SiteTypeConfig {
  markerShape: 'circle' | 'diamond' | 'hexagon' | 'square';
  identityFields: string[];
  demandLabel: string;
  filterLabel: string;
  badgeColor: string;
}

export const SITE_TYPES: Record<SiteType, SiteTypeConfig> = {
  kek: {
    markerShape: 'circle',
    identityFields: ['zone_classification', 'category', 'developer', 'legal_basis', 'area_ha'],
    demandLabel: 'Area-based demand',
    filterLabel: 'KEK (Special Economic Zone)',
    badgeColor: 'blue',
  },
  standalone: {
    markerShape: 'diamond',
    identityFields: ['primary_product', 'technology', 'capacity_annual', 'parent_company'],
    demandLabel: 'Production-based demand',
    filterLabel: 'Standalone Plant',
    badgeColor: 'amber',
  },
  cluster: {
    markerShape: 'hexagon',
    identityFields: ['primary_product', 'cluster_members', 'capacity_annual', 'parent_company'],
    demandLabel: 'Cluster aggregate demand',
    filterLabel: 'Industrial Cluster',
    badgeColor: 'violet',
  },
  ki: {
    markerShape: 'square',
    identityFields: ['sector', 'area_ha', 'developer'],
    demandLabel: 'Area-based demand',
    filterLabel: 'Industrial Park (KI)',
    badgeColor: 'teal',
  },
};

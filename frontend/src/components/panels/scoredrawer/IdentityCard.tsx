import { capitalize, formatSnakeLabel } from '../../../lib/format';
import { SITE_TYPES, type SiteType } from '../../../lib/siteTypes';
import type { ScorecardRow } from '../../../lib/types';
import { SectionHeader, StatCard, StatRow } from './StatComponents';

const IDENTITY_LABELS: Record<string, string> = {
  zone_classification: 'Type',
  category: 'Category',
  area_ha: 'Area',
  developer: 'Developer',
  legal_basis: 'Legal Basis',
  primary_product: 'Primary Product',
  capacity_annual: 'Capacity',
  technology: 'Technology',
  parent_company: 'Parent Company',
  cluster_members: 'Cluster Members',
  sector: 'Sector',
};

function renderIdentityValue(field: string, raw: unknown): string | number | null {
  if (raw == null || raw === '') return null;
  if (field === 'area_ha' && typeof raw === 'number') {
    return `${raw.toLocaleString(undefined, { maximumFractionDigits: 0 })} ha`;
  }
  if (field === 'primary_product' || field === 'sector') {
    return capitalize(String(raw).replace(/_/g, ' '));
  }
  return String(raw);
}

export function IdentityCard({ row }: { row: ScorecardRow }) {
  const rawType = (row.site_type ?? 'kek').toLowerCase() as SiteType;
  const config = SITE_TYPES[rawType] ?? SITE_TYPES.kek;
  const headerTitle = rawType === 'kek' ? 'KEK Identity' : `${config.filterLabel} — Identity`;
  const subtitle =
    rawType === 'kek' ? 'Zone classification, size, and operator' : 'Plant details and ownership';
  const rows = config.identityFields
    .map((field) => ({
      field,
      label: IDENTITY_LABELS[field] ?? formatSnakeLabel(field),
      value: renderIdentityValue(field, (row as unknown as Record<string, unknown>)[field]),
    }))
    .filter((r) => r.value != null);

  if (rows.length === 0) return null;

  return (
    <StatCard>
      <SectionHeader title={headerTitle} subtitle={subtitle} />
      {rows.map((r) => (
        <StatRow key={r.field} label={r.label} value={r.value} />
      ))}
    </StatCard>
  );
}

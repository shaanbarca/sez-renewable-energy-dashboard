/** Display formatting for raw backend values (snake_case, UPPER_SNAKE, lowercase). */

const GRID_REGION_LABELS: Record<string, string> = {
  JAVA_BALI: 'Java-Bali',
  SUMATERA: 'Sumatera',
  KALIMANTAN: 'Kalimantan',
  SULAWESI: 'Sulawesi',
  MALUKU: 'Maluku',
  PAPUA: 'Papua',
  NTB: 'NTB',
};

/** JAVA_BALI → "Java-Bali", NTB → "NTB" */
export function formatGridRegion(id: string | null | undefined): string {
  if (!id) return '—';
  return GRID_REGION_LABELS[id] ?? id;
}

/** snake_case → "Title Case" (e.g. invest_substation → "Invest Substation") */
export function formatSnakeLabel(str: string | null | undefined): string {
  if (!str) return '—';
  return str
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Capitalize first letter (e.g. "solar" → "Solar") */
export function capitalize(str: string | null | undefined): string {
  if (!str) return '—';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/** Format a dropdown filter value based on column ID. */
export function formatFilterValue(columnId: string, raw: string): string {
  switch (columnId) {
    case 'grid_integration_category':
      return formatSnakeLabel(raw);
    case 'best_re_technology':
      return capitalize(raw);
    case 'dominant_process_type':
      return formatSnakeLabel(raw);
    default:
      return raw;
  }
}

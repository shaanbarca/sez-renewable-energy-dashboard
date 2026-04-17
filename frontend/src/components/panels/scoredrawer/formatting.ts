export function computeGapPct(
  lcoe: number | null | undefined,
  ref: number | null | undefined,
): number | null {
  if (lcoe == null || ref == null || ref <= 0) return null;
  return ((lcoe - ref) / ref) * 100;
}

export function formatGap(gap: number | null | undefined): string | null {
  if (gap == null) return null;
  return `${gap > 0 ? '+' : ''}${gap.toFixed(1)}%`;
}

export function gapColor(gap: number | null | undefined): string | undefined {
  if (gap == null) return undefined;
  return gap < 0 ? '#4CAF50' : '#EF5350';
}

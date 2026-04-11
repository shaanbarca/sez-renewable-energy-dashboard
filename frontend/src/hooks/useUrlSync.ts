import { useEffect } from 'react';
import { updateUrl } from '../lib/urlState';
import { useDashboardStore } from '../store/dashboard';

/**
 * Syncs assumption state → URL query params.
 * Uses replaceState (no history pollution) with 300ms debounce to avoid
 * thrashing during slider drags.
 */
export function useUrlSync() {
  const assumptions = useDashboardStore((s) => s.assumptions);
  const benchmarkMode = useDashboardStore((s) => s.benchmarkMode);
  const defaultAssumptions = useDashboardStore((s) => s.defaultAssumptions);

  useEffect(() => {
    if (!assumptions || !defaultAssumptions) return;
    const timeout = setTimeout(() => {
      updateUrl(assumptions, defaultAssumptions, benchmarkMode);
    }, 300);
    return () => clearTimeout(timeout);
  }, [assumptions, benchmarkMode, defaultAssumptions]);
}

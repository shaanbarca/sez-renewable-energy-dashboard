import { useEffect, useRef, useState } from 'react';
import { useDashboardStore } from '../store/dashboard';

/**
 * Watches assumptions, thresholds, and benchmarkMode in the store.
 * Debounces 300ms then calls recomputeScorecard() with AbortController
 * to cancel any in-flight request when a new value arrives.
 */
export function useScorecard() {
  const assumptions = useDashboardStore((s) => s.assumptions);
  const thresholds = useDashboardStore((s) => s.thresholds);
  const recomputeScorecard = useDashboardStore((s) => s.recomputeScorecard);

  const [loading, setLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const initializedRef = useRef(false);

  useEffect(() => {
    // Skip the very first render (initial load is handled by initialize())
    if (!initializedRef.current) {
      initializedRef.current = true;
      return;
    }

    if (!assumptions || !thresholds) return;

    // Cancel any in-flight request
    if (abortRef.current) {
      abortRef.current.abort();
    }

    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);

    const timeout = setTimeout(async () => {
      if (controller.signal.aborted) return;

      try {
        await recomputeScorecard();
      } catch (_err) {
        // AbortError or network error — silently ignore if aborted
        if (!controller.signal.aborted) {
          console.error('Scorecard recomputation failed');
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }, 300);

    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, [assumptions, thresholds, recomputeScorecard]);

  return { loading };
}

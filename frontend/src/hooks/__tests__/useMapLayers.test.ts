/**
 * Integration tests for useMapLayers retry-with-backoff (#59).
 *
 * Pins the bug fix: pre-v4.0.6 useMapLayers deleted cache entries on fetch
 * failure, triggering a tight loop. Post-v4.0.6, failures retry up to 3 times
 * with exponential backoff (1s/2s/4s), then leave `_failed: true` for the
 * FailedLayerToast Retry button.
 *
 * Strategy: mock fetchLayer at the module boundary, render a tiny component
 * that calls useMapLayers, and use vi.useFakeTimers() to step through the
 * backoff windows. Assertions read straight from the Zustand store.
 */

import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../../lib/api';
import { useDashboardStore } from '../../store/dashboard';
import { BACKOFF_BASE_MS, useMapLayers } from '../useMapLayers';

// Snapshot the pristine initial state so each test starts fresh.
const INITIAL_STATE = useDashboardStore.getState();

beforeEach(() => {
  vi.useFakeTimers();
  useDashboardStore.setState(
    { ...INITIAL_STATE, layerVisibility: {}, layers: {}, selectedSite: null },
    false,
  );
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

// Helper: advance through the full retry backoff window (1s + 2s + 4s = 7s)
// plus a buffer to flush microtasks. flushPromises lets the awaited fetch
// resolutions propagate to setState.
async function flushBackoffWindow() {
  // First retry at 1s
  await act(async () => {
    await vi.advanceTimersByTimeAsync(BACKOFF_BASE_MS);
  });
  // Second retry at 2s after that
  await act(async () => {
    await vi.advanceTimersByTimeAsync(BACKOFF_BASE_MS * 2);
  });
  // Third (final) at 4s
  await act(async () => {
    await vi.advanceTimersByTimeAsync(BACKOFF_BASE_MS * 4);
  });
}

describe('useMapLayers — fetch failure handling (#59)', () => {
  it('terminal failure marks the cache entry _failed instead of deleting', async () => {
    // The pre-v4.0.6 bug: delete on failure → effect re-fires → tight loop.
    // Fix: keep the entry in cache with _failed flag.
    const err = new Error('500 Internal Server Error');
    const spy = vi.spyOn(api, 'fetchLayer').mockRejectedValue(err);

    renderHook(() => useMapLayers());
    await act(async () => {
      useDashboardStore.setState({ layerVisibility: { substations: true } });
    });

    await flushBackoffWindow();

    const entry = useDashboardStore.getState().layers.substations;
    expect(entry).toBeDefined();
    expect(entry._failed).toBe(true);
    expect(entry._attempt).toBe(3); // hit MAX_RETRIES
    expect(spy).toHaveBeenCalledTimes(3); // 1 initial + 2 retries
  });

  it('recovers when retry eventually succeeds', async () => {
    // Fail twice, succeed on the third attempt. Cache should end with data,
    // not _failed.
    const data = { features: [{ id: 'sub-1' }] };
    const spy = vi
      .spyOn(api, 'fetchLayer')
      .mockRejectedValueOnce(new Error('blip 1'))
      .mockRejectedValueOnce(new Error('blip 2'))
      .mockResolvedValueOnce(data);

    renderHook(() => useMapLayers());
    await act(async () => {
      useDashboardStore.setState({ layerVisibility: { substations: true } });
    });

    await flushBackoffWindow();

    expect(useDashboardStore.getState().layers.substations).toEqual(data);
    expect(spy).toHaveBeenCalledTimes(3);
  });

  it('does NOT re-fetch while a retry is queued (no tight loop)', async () => {
    // The whole point of the fix. After the first failure, the cache entry
    // is { _loading: true, _attempt: N }, and the effect's `name in layers`
    // guard prevents a second concurrent fetch even though `layers` state
    // changed.
    const err = new Error('transient');
    const spy = vi.spyOn(api, 'fetchLayer').mockRejectedValue(err);

    renderHook(() => useMapLayers());
    await act(async () => {
      useDashboardStore.setState({ layerVisibility: { substations: true } });
    });

    // After the first attempt resolves, BEFORE the first backoff timer fires,
    // there should be exactly 1 fetch in flight (or just resolved).
    await act(async () => {
      // Flush microtasks but don't advance timers — fetch rejects synchronously
      // in the mock, but the next retry is gated by setTimeout.
      await Promise.resolve();
    });
    expect(spy).toHaveBeenCalledTimes(1);

    // Manually trigger a no-op state change to force a re-render. Effect
    // should NOT fire another fetch — the _loading entry blocks it.
    await act(async () => {
      useDashboardStore.setState({
        layerVisibility: { substations: true, peatland: false },
      });
    });
    expect(spy).toHaveBeenCalledTimes(1);

    // Now flush the rest of the backoff window. We expect 3 total fetches
    // by the end (initial + 2 retries), not 4+ from spurious re-fires.
    await flushBackoffWindow();
    expect(spy).toHaveBeenCalledTimes(3);
  });

  it('Retry path via retryLayer() triggers a fresh fetch cycle', async () => {
    // After max retries, the user clicks Retry in the corner toast. retryLayer
    // deletes the _failed entry; useMapLayers' effect picks it up on the next
    // render and starts a brand-new fetch sequence.
    vi.spyOn(api, 'fetchLayer').mockRejectedValue(new Error('still down'));

    renderHook(() => useMapLayers());
    await act(async () => {
      useDashboardStore.setState({ layerVisibility: { substations: true } });
    });
    await flushBackoffWindow();
    expect(useDashboardStore.getState().layers.substations._failed).toBe(true);

    // Backend recovers between failure and Retry click.
    const data = { features: [{ id: 'sub-1' }] };
    vi.spyOn(api, 'fetchLayer').mockReset().mockResolvedValue(data);

    await act(async () => {
      useDashboardStore.getState().retryLayer('substations');
    });
    // Allow the new fetch to resolve.
    await act(async () => {
      await Promise.resolve();
    });

    expect(useDashboardStore.getState().layers.substations).toEqual(data);
  });
});

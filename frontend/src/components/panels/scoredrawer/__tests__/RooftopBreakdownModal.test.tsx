/**
 * Component test for RooftopBreakdownModal (#82).
 *
 * Covers the happy path, zero-building empty state, CSV download mechanics,
 * and Esc-to-close. Mocks the fetch boundary so the test runs offline.
 *
 * Note: the /plan-eng-review (2026-05-19) locked test decision 3A called for
 * a Playwright E2E test. The codebase doesn't have Playwright infra wired up
 * yet — using vitest + @testing-library/react instead matches the existing
 * pattern (see frontend/src/hooks/__tests__/, frontend/src/store/__tests__/).
 * Full browser E2E is tracked as a follow-up.
 */

import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { RooftopBreakdownResponse } from '../../../../lib/types';
import { RooftopBreakdownModal } from '../RooftopBreakdownModal';

const SAMPLE_RESPONSE: RooftopBreakdownResponse = {
  site_id: 'krakatau-steel-cilegon',
  site_name: 'Krakatau Steel Cilegon',
  estate_area_m2: 10_000_000,
  building_data_confidence: 'medium',
  building_data_reason_flagged: null,
  buildings: [
    {
      building_id: 'gob_v3:100',
      area_m2: 500,
      footprint_class: 'standard_roof',
      exclusion_reason: 'none',
      usability_multiplier: 1.0,
      buildable_roof_area_m2: 500,
    },
    {
      building_id: 'gob_v3:101',
      area_m2: 80,
      footprint_class: 'tank_silo',
      exclusion_reason: 'osm_tank',
      usability_multiplier: 0,
      buildable_roof_area_m2: 0,
    },
    {
      building_id: 'gob_v3:102',
      area_m2: 1200,
      footprint_class: 'elongated',
      exclusion_reason: 'none',
      usability_multiplier: 0.6,
      buildable_roof_area_m2: 720,
    },
  ],
  totals: {
    building_count: 3,
    total_footprint_m2: 1780,
    usable_roof_area_m2: 1220,
  },
};

const ZERO_BUILDING_RESPONSE: RooftopBreakdownResponse = {
  site_id: 'buli-industrial-park',
  site_name: 'Buli Industrial Park',
  estate_area_m2: null,
  building_data_confidence: 'low',
  building_data_reason_flagged: 'no_buildings_detected',
  buildings: [],
  totals: {
    building_count: 0,
    total_footprint_m2: 0,
    usable_roof_area_m2: 0,
  },
};

function mockFetchOnce(response: RooftopBreakdownResponse) {
  global.fetch = vi.fn().mockResolvedValueOnce({
    ok: true,
    json: async () => response,
  } as Response);
}

describe('RooftopBreakdownModal', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders nothing when closed', () => {
    const onClose = vi.fn();
    render(<RooftopBreakdownModal open={false} onClose={onClose} siteId="x" />);
    expect(screen.queryByText('Rooftop breakdown')).toBeNull();
  });

  it('fetches and renders building rows when opened', async () => {
    mockFetchOnce(SAMPLE_RESPONSE);
    const onClose = vi.fn();
    render(
      <RooftopBreakdownModal open onClose={onClose} siteId="krakatau-steel-cilegon" />,
    );

    expect(screen.getByText('Rooftop breakdown')).toBeTruthy();
    await waitFor(() => expect(screen.getByText('Standard roof')).toBeTruthy());

    // The three sample buildings render
    expect(screen.getByText('Standard roof')).toBeTruthy();
    expect(screen.getByText('Tank/silo shape')).toBeTruthy();
    expect(screen.getByText('Elongated (shed)')).toBeTruthy();

    // OSM exclusion reason surfaces as a human label (audit's key disambiguation)
    expect(screen.getByText('OSM tank')).toBeTruthy();

    // Totals match what the endpoint returned
    expect(screen.getByText(/3$/)).toBeTruthy(); // building count
    expect(screen.getByText(/1,?780.*m²/)).toBeTruthy(); // footprint
  });

  it('shows empty-state with link to #62 for zero-building sites', async () => {
    mockFetchOnce(ZERO_BUILDING_RESPONSE);
    const onClose = vi.fn();
    render(<RooftopBreakdownModal open onClose={onClose} siteId="buli-industrial-park" />);

    await waitFor(() =>
      expect(screen.getByText(/No buildings detected for this site/)).toBeTruthy(),
    );
    // Reason flagged renders with underscores replaced (no_buildings_detected → no buildings detected)
    expect(screen.getByText(/Reason: no buildings detected/i)).toBeTruthy();
    const issueLink = screen.getByText(/#62 \(rooftop audit\)/);
    expect(issueLink.getAttribute('href')).toContain('issues/62');
  });

  it('closes on Esc key', async () => {
    mockFetchOnce(SAMPLE_RESPONSE);
    const onClose = vi.fn();
    render(<RooftopBreakdownModal open onClose={onClose} siteId="x" />);
    await waitFor(() => expect(screen.getByText('Standard roof')).toBeTruthy());

    act(() => {
      fireEvent.keyDown(window, { key: 'Escape' });
    });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('closes on X button click', async () => {
    mockFetchOnce(SAMPLE_RESPONSE);
    const onClose = vi.fn();
    render(<RooftopBreakdownModal open onClose={onClose} siteId="x" />);
    await waitFor(() => expect(screen.getByText('Standard roof')).toBeTruthy());

    const closeBtn = screen.getByLabelText('Close');
    fireEvent.click(closeBtn);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('triggers CSV blob download when Download CSV is clicked', async () => {
    mockFetchOnce(SAMPLE_RESPONSE);
    const createObjectURL = vi.fn().mockReturnValue('blob://test');
    const revokeObjectURL = vi.fn();
    global.URL.createObjectURL = createObjectURL;
    global.URL.revokeObjectURL = revokeObjectURL;
    // Stub anchor.click so we can detect the download invocation
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => undefined);

    const onClose = vi.fn();
    render(
      <RooftopBreakdownModal open onClose={onClose} siteId="krakatau-steel-cilegon" />,
    );
    await waitFor(() => expect(screen.getByText('Standard roof')).toBeTruthy());

    const downloadBtn = screen.getByText('Download CSV');
    fireEvent.click(downloadBtn);

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    const [blob] = createObjectURL.mock.calls[0];
    expect(blob).toBeInstanceOf(Blob);
    expect((blob as Blob).type).toBe('text/csv');
    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledTimes(1);
  });

  it('shows an error message when the fetch fails', async () => {
    global.fetch = vi.fn().mockRejectedValueOnce(new Error('network down'));
    const onClose = vi.fn();
    render(<RooftopBreakdownModal open onClose={onClose} siteId="x" />);
    await waitFor(() => expect(screen.getByText(/Error loading/)).toBeTruthy());
    expect(screen.getByText(/network down/)).toBeTruthy();
  });
});

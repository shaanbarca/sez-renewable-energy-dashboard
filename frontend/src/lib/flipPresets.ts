import type { UserAssumptions } from './types';

export type FlipPreset =
  | 'concessional_finance'
  | 'cheap_capex'
  | 'cbam_max_exposure'
  | 'grant_transmission';

export const FLIP_PRESET_LABELS: Record<FlipPreset, string> = {
  concessional_finance: 'Concessional Finance (8% WACC)',
  cheap_capex: 'Cheap CAPEX ($600/kW)',
  cbam_max_exposure: 'CBAM Max Exposure (2034 free-allocation = 0)',
  grant_transmission: 'Grant-Funded Transmission',
};

export const FLIP_PRESET_DESCRIPTIONS: Record<FlipPreset, string> = {
  concessional_finance:
    'DFI / blended-finance scenario: drops project WACC from default ~10% to 8%. Quantifies what cheaper capital unlocks.',
  cheap_capex:
    'Module + balance-of-system cost decline: solar CAPEX drops to $600/kW. Mirrors NREL ATB low case.',
  cbam_max_exposure:
    'EU CBAM free allocation reaches zero (2034 terminal state). Maximises Scope-2 CBAM cost per tonne — sites with steel/cement/aluminium exposure flip first.',
  grant_transmission:
    'Donor or government grant absorbs transmission CAPEX — sites flagged invest_transmission stop carrying that cost.',
};

export function applyFlipPreset(
  baseline: UserAssumptions,
  preset: FlipPreset,
): Partial<UserAssumptions> {
  switch (preset) {
    case 'concessional_finance':
      return { wacc_pct: 8 };
    case 'cheap_capex':
      return { capex_usd_per_kw: 600 };
    case 'cbam_max_exposure':
      return {
        cbam_certificate_price_eur: Math.max(baseline.cbam_certificate_price_eur, 80),
      };
    case 'grant_transmission':
      return { grant_funded_transmission: true };
  }
}

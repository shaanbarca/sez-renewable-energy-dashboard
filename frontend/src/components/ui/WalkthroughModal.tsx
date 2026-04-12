import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useDashboardStore } from '../../store/dashboard';

// ---------------------------------------------------------------------------
// Persona definitions
// ---------------------------------------------------------------------------

const PERSONAS = [
  {
    id: 'economist',
    title: 'Energy Economist',
    subtitle: 'Multilateral development bank analyst',
    description:
      'Compare solar LCOE against grid cost across KEKs and quantify the carbon arbitrage opportunity.',
    icon: '📊',
  },
  {
    id: 'dfi',
    title: 'DFI Infrastructure Investor',
    subtitle: 'Infrastructure fund analyst',
    description:
      'Identify where grid infrastructure investment unlocks solar potential for industrial zones.',
    icon: '💰',
  },
  {
    id: 'policymaker',
    title: 'Policy Maker',
    subtitle: 'BKPM / KESDM official or energy adviser',
    description:
      'Identify which KEKs need policy intervention — WACC de-risking, RUPTL acceleration, or GEAS allocation.',
    icon: '🏛️',
  },
  {
    id: 'ipp',
    title: 'IPP / Solar Developer',
    subtitle: 'Solar developer selling to PLN via PPA',
    description:
      'Find the strongest solar-to-BPP economics for grid-connected solar — good resource, grid access, and PLN procurement potential.',
    icon: '⚡',
  },
] as const;

// ---------------------------------------------------------------------------
// Tour step definitions per persona
// ---------------------------------------------------------------------------

interface TourStep {
  title: string;
  description: string;
  target: string; // data-tour attribute value
  action?: (store: ReturnType<typeof useDashboardStore.getState>) => void;
}

const ECONOMIST_STEPS: TourStep[] = [
  {
    title: 'Overview Map',
    description:
      'Start by scanning the map. Green markers mean solar is already competitive at that KEK. Red means not yet. Notice the geographic clustering — Java vs. eastern islands.',
    target: 'map',
  },
  {
    title: 'Quadrant Chart',
    description:
      'The Quadrant Chart plots solar LCOE vs grid cost. KEKs above the diagonal line have grid costs higher than solar — meaning solar is already competitive there.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('quadrant'),
  },
  {
    title: 'Adjust WACC to 8%',
    description:
      'Try lowering WACC to 8% (concessional DFI financing). Watch which KEKs flip from red to green — these are the concessional finance cases, the core policy argument.',
    target: 'assumptions',
  },
  {
    title: 'Ranked Table',
    description:
      'Sort the table by LCOE gap (ascending) to find KEKs closest to grid parity. These are the easiest wins for solar.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'Carbon Breakeven',
    description:
      'Check the carbon breakeven column — the carbon price (USD/tCO₂) needed to make solar competitive. Low values are easy carbon finance candidates.',
    target: 'bottom-panel',
  },
  {
    title: 'KEK Scorecard',
    description:
      'Click any KEK marker or table row to open its scorecard. Review resource data, LCOE breakdown across WACC scenarios, and action flags.',
    target: 'map',
    action: (s) => {
      const scorecard = s.scorecard;
      if (scorecard?.length) s.selectKek(scorecard[0].kek_id);
    },
  },
  {
    title: 'Export Data',
    description:
      'Use the Export CSV button in the table view to download the full scorecard for your economic analysis annex.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: "You're Ready!",
    description:
      'Explore freely. Adjust assumptions with the sliders, toggle map layers, and drill into any KEK. Re-launch this guide anytime from the "Guide" button in the header.',
    target: 'header',
  },
];

const DFI_STEPS: TourStep[] = [
  {
    title: 'Overview Map',
    description:
      'Start with the map. Green markers (solar_now) and orange (invest_resilience) are your actionable sites — solar is competitive or nearly so.',
    target: 'map',
  },
  {
    title: 'Rank by Capacity',
    description:
      'Open the table and sort by capacity (MWp) descending. You want sites large enough for utility-scale captive solar — at least 50 MWp.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'Check Grid Integration',
    description:
      'Look at the Grid Integration column. "within boundary" means solar fits inside the KEK. "grid ready" means substation access is good. "invest transmission" or "invest substation" means targeted infrastructure investment would unlock solar.',
    target: 'bottom-panel',
  },
  {
    title: 'Buildability Constraints',
    description:
      'Check the buildability constraint. "Slope" or "unconstrained" = low risk. "Peat" or "kawasan_hutan" = land tenure risk. "Agriculture" = negotiation needed.',
    target: 'bottom-panel',
  },
  {
    title: 'KEK Resource Tab',
    description:
      'Click a KEK to open its scorecard. The Solar tab shows PVOUT, buildable area, LCOE breakdown, and the scale curve.',
    target: 'map',
    action: (s) => {
      const scorecard = s.scorecard;
      if (scorecard?.length) s.selectKek(scorecard[0].kek_id);
    },
  },
  {
    title: 'LCOE at Your Hurdle Rate',
    description:
      'Switch to the Economics tab in the scorecard. Compare solar LCOE against tariff and BPP, check battery impact, and verify the carbon breakeven.',
    target: 'drawer',
  },
  {
    title: 'Grid Connection',
    description:
      'Check substation distance in the scorecard. The grid connection cost depends on distance from the solar site to the nearest PLN substation.',
    target: 'drawer',
  },
  {
    title: "You're Ready!",
    description:
      'Export CSV or GeoJSON for your site team. Re-launch this guide from the "Guide" button anytime.',
    target: 'header',
  },
];

const POLICYMAKER_STEPS: TourStep[] = [
  {
    title: 'Action Flag Distribution',
    description:
      'View the spatial distribution of action flags on the map. If "not_competitive" KEKs cluster in one region, it suggests a system-level grid problem, not site-specific.',
    target: 'map',
  },
  {
    title: 'RUPTL Pipeline',
    description:
      'Switch to the RUPTL tab. See which grid regions have significant RE pipeline additions vs. which are flat — low grid improvement expected by 2030.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('ruptl'),
  },
  {
    title: 'Plan Late KEKs',
    description:
      'Switch to the table and look for KEKs with plan_late = True. These are most at risk: grid improvement is planned but arrives after 2030. Flag for RUPTL acceleration.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'Concessional Finance Case',
    description:
      'Set WACC to 8% in the Assumptions panel. Count how many KEKs flip from "not_competitive" to "solar_now". This is the case for concessional finance instruments.',
    target: 'assumptions',
  },
  {
    title: 'GEAS Allocation',
    description:
      "Check green_share_geas in the table — how much of each KEK's 2030 demand could GEAS-allocated solar cover? High values mean GEAS is a viable policy lever.",
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'KEK Pipeline Detail',
    description:
      'Click a KEK to open its scorecard. The Demand tab shows captive power context and RUPTL pipeline status for this region.',
    target: 'map',
    action: (s) => {
      const scorecard = s.scorecard;
      if (scorecard?.length) s.selectKek(scorecard[0].kek_id);
    },
  },
  {
    title: 'Export for Policy Brief',
    description:
      'Export the ranked table CSV filtered to plan_late KEKs for your RUPTL review submission. Screenshot the RUPTL view for presentations.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: "You're Ready!",
    description:
      'Explore freely. The Methodology button in the header shows the full analytical methodology. Re-launch this guide from "Guide" anytime.',
    target: 'header',
  },
];

const IPP_STEPS: TourStep[] = [
  {
    title: 'Rank by Capacity',
    description:
      'Start with the table. Sort by capacity (MWp) descending. IPP threshold: ≥30 MWp — below this, project economics are marginal for a developer.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'Filter Actionable Sites',
    description:
      'Focus on KEKs flagged "solar_now" or "invest_resilience". These are sites where the PPA pitch is straightforward — solar is already competitive or within striking distance.',
    target: 'bottom-panel',
  },
  {
    title: 'Sort by Demand',
    description:
      'Sort by demand descending. Larger electricity demand = larger potential PPA = better project economics for your development pipeline.',
    target: 'bottom-panel',
  },
  {
    title: 'Check Grid Integration',
    description:
      'Prefer "within boundary" or "grid ready" sites — these have low grid connection cost. "invest transmission" or "invest substation" sites need infrastructure investment to connect solar to the grid.',
    target: 'bottom-panel',
  },
  {
    title: 'Buildability Risk',
    description:
      'Check the buildability constraint column. "Slope" and "unconstrained" are low-risk. "Agriculture" means land negotiation. "Peat" or "kawasan_hutan" are high-risk.',
    target: 'bottom-panel',
  },
  {
    title: 'Quadrant Confirmation',
    description:
      'Switch to the Quadrant Chart to visually confirm your shortlisted KEKs sit in the "Solar now" quadrant at WACC=10%.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('quadrant'),
  },
  {
    title: 'KEK Deep Dive',
    description:
      'Click your top KEK to see the full scorecard: solar resource (Solar tab), grid connection (Grid tab), economics (Economics tab), and demand (Demand tab).',
    target: 'map',
    action: (s) => {
      const scorecard = s.scorecard;
      if (scorecard?.length) s.selectKek(scorecard[0].kek_id);
    },
  },
  {
    title: "You're Ready!",
    description:
      'Export your top 10 KEKs as CSV for your BD pipeline tracker. Re-launch this guide from "Guide" in the header anytime.',
    target: 'header',
  },
];

const STEPS_BY_PERSONA: Record<string, TourStep[]> = {
  economist: ECONOMIST_STEPS,
  dfi: DFI_STEPS,
  policymaker: POLICYMAKER_STEPS,
  ipp: IPP_STEPS,
};

// ---------------------------------------------------------------------------
// Spotlight position hook
// ---------------------------------------------------------------------------

function useSpotlightRect(target: string | null) {
  const [rect, setRect] = useState<DOMRect | null>(null);
  const rafRef = useRef(0);

  useEffect(() => {
    if (!target) {
      setRect(null);
      return;
    }
    const update = () => {
      const el = document.querySelector(`[data-tour="${target}"]`);
      if (el) {
        setRect(el.getBoundingClientRect());
      } else {
        setRect(null);
      }
      rafRef.current = requestAnimationFrame(update);
    };
    rafRef.current = requestAnimationFrame(update);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target]);

  return rect;
}

// ---------------------------------------------------------------------------
// Components
// ---------------------------------------------------------------------------

function PersonaSelector() {
  const setPersona = useDashboardStore((s) => s.setWalkthroughPersona);
  const dismiss = useDashboardStore((s) => s.dismissWalkthrough);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
      <div
        className="relative z-10 max-w-lg w-full mx-4 rounded-2xl p-8"
        style={{
          background: 'rgba(20, 20, 24, 0.92)',
          border: '1px solid rgba(255,255,255,0.12)',
          backdropFilter: 'blur(40px)',
          boxShadow: '0 24px 80px rgba(0,0,0,0.5)',
        }}
      >
        <h2 className="text-xl font-semibold text-white mb-2">How will you use this dashboard?</h2>
        <p className="text-sm text-zinc-400 mb-6">
          We&apos;ll walk you through the features most relevant to your role.
        </p>

        <div className="grid grid-cols-2 gap-3">
          {PERSONAS.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setPersona(p.id)}
              className="text-left p-4 rounded-xl transition-all hover:scale-[1.02] cursor-pointer group"
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.08)',
              }}
            >
              <div className="text-2xl mb-2">{p.icon}</div>
              <div className="text-sm font-semibold text-white group-hover:text-blue-300 transition-colors">
                {p.title}
              </div>
              <div className="text-[10px] text-zinc-500 mb-1.5">{p.subtitle}</div>
              <div className="text-xs text-zinc-400 leading-relaxed">{p.description}</div>
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={dismiss}
          className="mt-5 w-full text-center text-xs text-zinc-500 hover:text-zinc-300 transition-colors cursor-pointer py-2"
        >
          Skip — I&apos;ll explore on my own
        </button>
      </div>
    </div>
  );
}

function StepOverlay() {
  const persona = useDashboardStore((s) => s.walkthroughPersona);
  const step = useDashboardStore((s) => s.walkthroughStep);
  const next = useDashboardStore((s) => s.nextWalkthroughStep);
  const prev = useDashboardStore((s) => s.prevWalkthroughStep);
  const dismiss = useDashboardStore((s) => s.dismissWalkthrough);

  const steps = useMemo(() => (persona ? (STEPS_BY_PERSONA[persona] ?? []) : []), [persona]);
  const currentStep = steps[step];

  // Run step action when step changes
  useEffect(() => {
    if (!currentStep?.action) return;
    const state = useDashboardStore.getState();
    currentStep.action(state);
  }, [currentStep]);

  const isLastStep = step >= steps.length - 1;
  const spotlightRect = useSpotlightRect(currentStep?.target ?? null);

  const handleNext = useCallback(() => {
    if (isLastStep) {
      dismiss();
    } else {
      next();
    }
  }, [isLastStep, dismiss, next]);

  // Keyboard nav
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') dismiss();
      if (e.key === 'ArrowRight' || e.key === 'Enter') handleNext();
      if (e.key === 'ArrowLeft' && step > 0) prev();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [dismiss, handleNext, prev, step]);

  if (!currentStep) return null;

  // If the target covers most of the viewport, don't spotlight it — just show tooltip centered
  const isLargeTarget =
    spotlightRect &&
    spotlightRect.width > window.innerWidth * 0.6 &&
    spotlightRect.height > window.innerHeight * 0.6;

  // Position the tooltip near the spotlight (or center if large/missing target)
  const tooltipStyle: React.CSSProperties = {};
  if (spotlightRect && !isLargeTarget) {
    const pad = 16;
    const tooltipWidth = 340;
    if (spotlightRect.right + tooltipWidth + pad < window.innerWidth) {
      tooltipStyle.left = spotlightRect.right + pad;
      tooltipStyle.top = Math.max(pad, spotlightRect.top);
    } else if (spotlightRect.left - tooltipWidth - pad > 0) {
      tooltipStyle.left = spotlightRect.left - tooltipWidth - pad;
      tooltipStyle.top = Math.max(pad, spotlightRect.top);
    } else {
      tooltipStyle.left = Math.max(pad, (window.innerWidth - tooltipWidth) / 2);
      tooltipStyle.top = Math.max(pad, spotlightRect.top + 60);
    }
  } else {
    // Center the tooltip
    tooltipStyle.left = '50%';
    tooltipStyle.top = '40%';
    tooltipStyle.transform = 'translate(-50%, -50%)';
  }

  return (
    <div className="fixed inset-0 z-[60]" style={{ pointerEvents: 'none' }}>
      {/* Dimming backdrop */}
      <div
        className="absolute inset-0"
        style={{
          background: isLargeTarget || !spotlightRect ? 'rgba(0,0,0,0.5)' : 'transparent',
          pointerEvents: 'none',
        }}
      />

      {/* Spotlight hole (only for small/medium targets) */}
      {spotlightRect && !isLargeTarget && (
        <div
          className="absolute rounded-lg"
          style={{
            left: spotlightRect.left - 4,
            top: spotlightRect.top - 4,
            width: spotlightRect.width + 8,
            height: spotlightRect.height + 8,
            boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.65)',
            border: '2px solid rgba(144, 202, 249, 0.5)',
            pointerEvents: 'none',
          }}
        />
      )}

      {/* Step tooltip */}
      <div
        className="absolute rounded-xl p-5"
        style={{
          ...tooltipStyle,
          width: 340,
          background: 'rgba(20, 20, 24, 0.95)',
          border: '1px solid rgba(255,255,255,0.15)',
          backdropFilter: 'blur(24px)',
          boxShadow: '0 16px 64px rgba(0,0,0,0.5)',
          pointerEvents: 'auto',
        }}
      >
        {/* Step counter */}
        <div className="flex items-center gap-2 mb-3">
          <span className="text-[10px] font-medium text-[#90CAF9] uppercase tracking-wider">
            Step {step + 1} of {steps.length}
          </span>
          <div className="flex-1 flex gap-1">
            {steps.map((s, i) => (
              <div
                key={s.title}
                className="h-1 flex-1 rounded-full transition-colors"
                style={{
                  background: i <= step ? '#90CAF9' : 'rgba(255,255,255,0.1)',
                }}
              />
            ))}
          </div>
        </div>

        <h3 className="text-sm font-semibold text-white mb-2">{currentStep.title}</h3>
        <p className="text-xs text-zinc-400 leading-relaxed mb-4">{currentStep.description}</p>

        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={dismiss}
            className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors cursor-pointer"
            style={{ pointerEvents: 'auto' }}
          >
            Skip tour
          </button>
          <div className="flex gap-2">
            {step > 0 && (
              <button
                type="button"
                onClick={prev}
                className="px-3 py-1.5 rounded-lg text-xs text-zinc-300 hover:text-white transition-colors cursor-pointer"
                style={{
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid rgba(255,255,255,0.1)',
                }}
              >
                Back
              </button>
            )}
            <button
              type="button"
              onClick={handleNext}
              className="px-4 py-1.5 rounded-lg text-xs font-medium text-white cursor-pointer transition-colors"
              style={{
                background: 'rgba(144, 202, 249, 0.2)',
                border: '1px solid rgba(144, 202, 249, 0.4)',
              }}
            >
              {isLastStep ? 'Finish' : 'Next'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------

export default function WalkthroughModal() {
  const persona = useDashboardStore((s) => s.walkthroughPersona);
  const dismissed = useDashboardStore((s) => s.walkthroughDismissed);
  const loading = useDashboardStore((s) => s.loading);

  // Don't show while data is loading
  if (loading) return null;

  // Show persona selector if not dismissed and no persona selected
  if (!dismissed && !persona) return <PersonaSelector />;

  // Show step overlay if persona is selected
  if (persona) return <StepOverlay />;

  return null;
}

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
      'Compare solar and wind LCOE against grid cost, quantify carbon arbitrage, and model concessional finance impact.',
    icon: '📊',
  },
  {
    id: 'dfi',
    title: 'DFI Infrastructure Investor',
    subtitle: 'Grid infrastructure fund analyst',
    description:
      'Identify where grid investment unlocks solar potential — ranked by capacity unlocked per infrastructure dollar.',
    icon: '💰',
  },
  {
    id: 'policymaker',
    title: 'Policy Maker',
    subtitle: 'BKPM / KESDM official or energy adviser',
    description:
      'Map grid integration gaps, captive coal exposure, and RUPTL pipeline timing to prioritize policy interventions.',
    icon: '🏛️',
  },
  {
    id: 'ipp',
    title: 'IPP / RE Developer',
    subtitle: 'Solar or wind developer selling to PLN via PPA',
    description:
      'Find sites where RE undercuts PLN cost of supply (BPP) — strong resource, grid-ready substations, and buildable land.',
    icon: '⚡',
  },
  {
    id: 'industrial',
    title: 'Industrial Investor',
    subtitle: 'KEK tenant or smelter operator',
    description:
      'Compare KEKs by electricity cost risk, grid reliability, green energy trajectory, and captive coal phase-out exposure.',
    icon: '🏭',
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
      'Scan the map. Green markers = solar already competitive. Red = not yet. Notice the geographic clustering: Java manufacturing belt vs. eastern islands with higher BPP.',
    target: 'map',
  },
  {
    title: 'Energy Mode',
    description:
      'Use the Solar / Wind / Hybrid / Overall toggle in the header. The dashboard recomputes LCOE, action flags, and competitiveness metrics for each technology. Start with "Overall" to see which RE technology wins at each KEK.',
    target: 'header',
    action: (s) => s.setEnergyMode('overall'),
  },
  {
    title: 'Quadrant Chart',
    description:
      'Plots RE LCOE vs grid cost (BPP). KEKs above the diagonal have grid costs higher than RE — solar or wind is already cheaper. Below = not yet competitive.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('quadrant'),
  },
  {
    title: 'Switch WACC to 8%',
    description:
      'Lower WACC to 8% (concessional DFI financing). Watch which KEKs flip from red to green. This is the case for concessional finance instruments — quantified, site by site.',
    target: 'assumptions',
  },
  {
    title: 'Ranked Table',
    description:
      'Sort by LCOE Gap (ascending) to find KEKs closest to grid parity. Check the Carbon Breakeven column — the carbon price ($/tCO2) needed to close the gap. Low values = easy carbon finance candidates.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'KEK Scorecard — Economics',
    description:
      'Click any KEK to open its scorecard. The Economics tab shows LCOE across WACC bands, BESS storage cost (14h bridge-hours for 24/7 loads), and firm solar coverage — the split between daytime-direct supply and storage-dependent nighttime demand.',
    target: 'map',
    action: (s) => {
      const scorecard = s.scorecard;
      if (scorecard?.length) s.selectKek(scorecard[0].kek_id);
    },
  },
  {
    title: 'Export CSV',
    description:
      'Download the full scorecard CSV from the table view. Includes LCOE bands, carbon breakeven, wind LCOE, best RE technology, and grid investment estimates — ready for your economic analysis annex.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: "You're Ready!",
    description:
      'Explore freely. Toggle energy modes, adjust assumptions, switch map layers, and drill into any KEK. Re-launch this guide from the "Guide" button anytime.',
    target: 'header',
  },
];

const DFI_STEPS: TourStep[] = [
  {
    title: 'Grid Integration Map',
    description:
      'The map color-codes KEKs by grid integration category. Your opportunity set: "invest transmission" and "invest substation" sites where solar resource and demand exist, but specific grid infrastructure is the bottleneck.',
    target: 'map',
  },
  {
    title: 'Filter Investment Targets',
    description:
      'Open the table. Filter Grid Integration to "Invest Transmission" or "Invest Substation". These are KEKs where targeted DFI capital unlocks solar. Check the Grid Invest ($M) column for order-of-magnitude costs.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'Rank by ROI',
    description:
      'Sort by Capacity (MWp) descending, cross-referencing Grid Invest ($M). The highest ratio of solar capacity unlocked per infrastructure dollar is your best use of DFI capital.',
    target: 'bottom-panel',
  },
  {
    title: 'BPP Economics',
    description:
      'Check the LCOE Gap column. Where solar is cheaper than PLN cost of supply (BPP), grid investment enables solar that reduces PLN operating costs. A self-supporting investment case.',
    target: 'bottom-panel',
  },
  {
    title: 'KEK Grid Tab',
    description:
      'Click a top KEK to open its scorecard. The Grid tab shows substation distance, capacity assessment (green/yellow/red traffic light), connectivity status, and transmission cost breakdown.',
    target: 'map',
    action: (s) => {
      const scorecard = s.scorecard;
      if (scorecard?.length) s.selectKek(scorecard[0].kek_id);
    },
  },
  {
    title: 'Economics & Storage',
    description:
      'The Economics tab shows LCOE with BESS storage (14h bridge-hours for 24/7 industrial loads, 87% round-trip efficiency). Honest storage costs matter for investment committee presentations.',
    target: 'drawer',
  },
  {
    title: 'Energy Mode — Hybrid',
    description:
      'Switch to "Hybrid" mode in the header. Wind nighttime generation can reduce BESS sizing, lowering the all-in cost. Check whether hybrid RE changes the investment case at your target KEKs.',
    target: 'header',
    action: (s) => s.setEnergyMode('hybrid'),
  },
  {
    title: "You're Ready!",
    description:
      'Export CSV with grid integration category, investment estimates, and solar potential for your investment committee screening memo. Re-launch this guide from "Guide" anytime.',
    target: 'header',
  },
];

const POLICYMAKER_STEPS: TourStep[] = [
  {
    title: 'Grid Integration Map',
    description:
      'The map shows grid integration categories. "Grid ready" KEKs can procure solar now. "Invest transmission" / "invest substation" KEKs need specific infrastructure. "Grid first" needs major expansion. This is the policy triage.',
    target: 'map',
  },
  {
    title: 'Captive Power Exposure',
    description:
      'Check the Captive column in the table. KEKs near coal plants and nickel smelters face Perpres 112/2022 phase-out pressure. Solar replacement potential shows what % of captive coal could be replaced by buildable solar.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'RUPTL Pipeline',
    description:
      'Switch to the RUPTL tab. Which grid regions have RE pipeline additions by 2030, and which are flat? Cross-reference with "plan late" KEKs — grid improvement planned but arriving after 2030.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('ruptl'),
  },
  {
    title: 'BPP vs Solar Economics',
    description:
      'Back to the table. Sort by LCOE Gap — where solar undercuts PLN cost of supply (BPP), the economic case for enabling procurement is self-evident. Negative gap = PLN saves money.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'Concessional Finance Case',
    description:
      'Set WACC to 8% in the Assumptions panel. Count how many KEKs flip to "solar now". This quantifies the impact of concessional finance instruments — the core DFI policy argument.',
    target: 'assumptions',
  },
  {
    title: 'Energy Mode — Overall',
    description:
      'Switch to "Overall" mode. The dashboard selects the cheapest RE technology per KEK (solar, wind, or hybrid). Some eastern KEKs may favor wind. Best RE Technology shows the winner.',
    target: 'header',
    action: (s) => s.setEnergyMode('overall'),
  },
  {
    title: 'KEK Demand & Action Tabs',
    description:
      'Click a KEK. The Demand tab shows captive coal/nickel context and RUPTL pipeline status. The Action tab shows the specific policy recommendation — 9 flags, each naming an intervention.',
    target: 'map',
    action: (s) => {
      const scorecard = s.scorecard;
      if (scorecard?.length) s.selectKek(scorecard[0].kek_id);
    },
  },
  {
    title: 'Firm Solar Coverage',
    description:
      'In the scorecard Economics tab, check firm solar coverage — the split between daytime-direct supply and storage-dependent nighttime demand. 24/7 industrial loads need 14h of BESS. This grounds "100% RE" claims in physical reality.',
    target: 'drawer',
  },
  {
    title: 'Export for Policy Brief',
    description:
      'Export the ranked table CSV with grid integration categories, action flags, grid investment estimates, and captive power data. The Methodology button shows the full analytical methodology for citations.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: "You're Ready!",
    description:
      'Explore freely. Toggle energy modes, adjust assumptions, and drill into any KEK. Re-launch this guide from "Guide" anytime.',
    target: 'header',
  },
];

const IPP_STEPS: TourStep[] = [
  {
    title: 'Strong Solar Resource',
    description:
      'Start with the table. Sort by Capacity (MWp) descending — you want sites large enough for utility-scale development (30+ MWp). Filter to "solar now" or "grid ready" action flags.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'BPP Economics',
    description:
      'Check the LCOE Gap column. Where solar undercuts PLN cost of supply (BPP), the procurement pitch writes itself: "procure solar here and your generation cost drops." Negative gap = PLN saves money.',
    target: 'bottom-panel',
  },
  {
    title: 'Grid Readiness',
    description:
      'Check Grid Integration: "grid ready" = substation accessible with capacity. Review the capacity assessment traffic light (green/yellow/red) — can the local grid absorb your project output?',
    target: 'bottom-panel',
  },
  {
    title: 'Wind & Hybrid',
    description:
      'Switch to "Wind" or "Hybrid" mode in the header. Some eastern KEKs have strong wind resource. The Best RE column shows which technology wins. Hybrid mode optimizes solar+wind mix to minimize all-in cost.',
    target: 'header',
    action: (s) => s.setEnergyMode('overall'),
  },
  {
    title: 'Quadrant Confirmation',
    description:
      'Open the Quadrant Chart to visually confirm your shortlisted KEKs sit in the competitive quadrant at market WACC (10%). KEKs above the diagonal are your targets.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('quadrant'),
  },
  {
    title: 'KEK Deep Dive',
    description:
      'Click your top KEK. Resource tab: PVOUT and buildable area. Grid tab: substation distance, capacity, connectivity. Economics tab: LCOE bands with BESS storage (14h bridge-hours). Action tab: recommended next step.',
    target: 'map',
    action: (s) => {
      const scorecard = s.scorecard;
      if (scorecard?.length) s.selectKek(scorecard[0].kek_id);
    },
  },
  {
    title: 'Map Layers',
    description:
      'Toggle buildable area overlays (solar and wind) in the Layers menu. Purple = wind buildable, cyan = solar buildable. Enable PLN Grid Lines and Substations to visualize grid connectivity.',
    target: 'header',
  },
  {
    title: "You're Ready!",
    description:
      'Export your top KEKs as CSV for your BD pipeline tracker or PLN engagement deck. Re-launch this guide from "Guide" in the header anytime.',
    target: 'header',
  },
];

const INDUSTRIAL_STEPS: TourStep[] = [
  {
    title: 'Understanding the Baseline',
    description:
      'All KEKs pay the same PLN I-4 industrial tariff today ($63/MWh). The differentiation is risk and trajectory: which KEKs face future tariff hikes, grid reliability issues, or lack of green energy?',
    target: 'map',
  },
  {
    title: 'Subsidy Exposure',
    description:
      'Open the table. Check the BPP column — PLN cost of supply by region. Papua: $133/MWh, but tariff is $63/MWh. That $70 gap is a subsidy that is a future tariff hike waiting to happen. High BPP = high risk.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'Grid Reliability Proxies',
    description:
      'Check Grid Integration and Capacity columns. KEKs near large substations with green capacity assessments offer better reliability. Continuous-process industries (smelters, data centers) cannot tolerate outages.',
    target: 'bottom-panel',
  },
  {
    title: 'Captive Coal Exposure',
    description:
      'Check the Captive column. Coal plants and nickel smelters within 50km face Perpres 112/2022 phase-out by 2050. RKEF smelters need 24/7 baseload — doubles BESS sizing. This is regulatory risk for co-located industry.',
    target: 'bottom-panel',
  },
  {
    title: 'Green Energy Trajectory',
    description:
      'Where solar could lower the regional BPP, your electricity cost is safer long-term. Check the LCOE Gap — KEKs where RE undercuts BPP will see improving grid economics. RE Coverage shows buildable RE potential.',
    target: 'bottom-panel',
  },
  {
    title: 'RUPTL Pipeline Risk',
    description:
      'Switch to the RUPTL tab. Check if grid improvements in your target region arrive before or after 2030. A 15-year facility commitment needs confidence that grid capacity keeps pace.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('ruptl'),
  },
  {
    title: 'KEK Comparison',
    description:
      'Click a KEK to review its full scorecard. Overview tab: key metrics at a glance. Demand tab: captive power context. Grid tab: infrastructure quality. Compare 3-4 candidate KEKs.',
    target: 'map',
    action: (s) => {
      const scorecard = s.scorecard;
      if (scorecard?.length) s.selectKek(scorecard[0].kek_id);
    },
  },
  {
    title: "You're Ready!",
    description:
      'Export the comparison matrix CSV — KEKs ranked by risk factors (BPP gap, grid quality, green share, captive exposure) for your site selection team. Re-launch from "Guide" anytime.',
    target: 'header',
  },
];

const STEPS_BY_PERSONA: Record<string, TourStep[]> = {
  economist: ECONOMIST_STEPS,
  dfi: DFI_STEPS,
  policymaker: POLICYMAKER_STEPS,
  ipp: IPP_STEPS,
  industrial: INDUSTRIAL_STEPS,
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
          background: 'var(--glass-heavy)',
          border: '1px solid var(--glass-border-bright)',
          backdropFilter: 'var(--blur-heavy)',
          WebkitBackdropFilter: 'var(--blur-heavy)',
          boxShadow: '0 24px 80px rgba(0,0,0,0.5)',
        }}
      >
        <h2 className="text-xl font-semibold text-white mb-2">How will you use this dashboard?</h2>
        <p className="text-sm text-zinc-400 mb-6">
          We&apos;ll walk you through the features most relevant to your role.
        </p>

        <div className="grid grid-cols-2 gap-3 [&>:last-child:nth-child(odd)]:col-span-2 [&>:last-child:nth-child(odd)]:max-w-[calc(50%-6px)] [&>:last-child:nth-child(odd)]:mx-auto">
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
          background: 'var(--glass-heavy)',
          border: '1px solid var(--glass-border-bright)',
          backdropFilter: 'var(--blur-heavy)',
          WebkitBackdropFilter: 'var(--blur-heavy)',
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

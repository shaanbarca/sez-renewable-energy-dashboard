import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
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
    subtitle: 'KEK tenant, smelter operator, or industrial site planner',
    description:
      'Compare sites by electricity cost risk, grid reliability, CBAM export exposure, and captive coal phase-out pressure.',
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
      'Use the Solar / Wind / Hybrid / Overall toggle in the header. The dashboard recomputes LCOE, action flags, and competitiveness metrics for each technology. Start with "Overall" to see which RE technology wins at each site.',
    target: 'header',
    action: (s) => s.setEnergyMode('overall'),
  },
  {
    title: 'Switch WACC to 8%',
    description:
      'Lower WACC to 8% (concessional DFI financing). Watch which sites flip from red to green. This is the case for concessional finance instruments — quantified, site by site.',
    target: 'assumptions',
  },
  {
    title: 'Ranked Table — LCOE Gap',
    description:
      'This column shows each site\u2019s LCOE gap to the grid benchmark. Sort ascending to surface the sites closest to parity. Click a site and check Carbon Breakeven in the Economics tab \u2014 the carbon price ($/tCO2) needed to close the gap. Low values = easy carbon finance candidates.',
    target: 'column:solar_competitive_gap_pct',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'Site Scorecard — Economics',
    description:
      'Click any site to open its scorecard. The Economics tab shows LCOE across WACC bands, BESS storage cost (14h bridge-hours for 24/7 loads), and firm solar coverage — the split between daytime-direct supply and storage-dependent nighttime demand.',
    target: 'map',
    action: (s) => {
      const scorecard = s.scorecard;
      if (scorecard?.length) s.selectSite(scorecard[0].site_id);
    },
  },
  {
    title: 'CBAM Carbon Arbitrage',
    description:
      'Check the Industry tab for CBAM-exposed sites. The CBAM trajectory chart shows EU border tax costs from 2026-2034 as free allocation phases out. Where CBAM savings exceed the RE premium, the "CBAM Urgent" flag fires — carbon arbitrage at the trade border.',
    target: 'drawer',
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
      'Explore freely. Toggle energy modes, adjust assumptions, switch map layers, and drill into any site. Re-launch this guide from the "Guide" button anytime.',
    target: 'header',
  },
];

const DFI_STEPS: TourStep[] = [
  {
    title: 'Grid Integration Map',
    description:
      'The map color-codes sites by grid integration category. Your opportunity set: "invest transmission" and "invest substation" sites where solar resource and demand exist, but specific grid infrastructure is the bottleneck.',
    target: 'map',
  },
  {
    title: 'Filter Investment Targets',
    description:
      'Open the table. Filter Grid Integration to "Invest Transmission" or "Invest Substation". These are sites where targeted DFI capital unlocks solar. The highlighted Grid Invest ($M) column shows order-of-magnitude costs.',
    target: 'column:grid_investment_needed_usd',
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
      'This column shows LCOE Gap. Where solar is cheaper than PLN cost of supply (BPP), grid investment enables solar that reduces PLN operating costs. A self-supporting investment case.',
    target: 'column:solar_competitive_gap_pct',
  },
  {
    title: 'Site Grid Tab',
    description:
      'Click a top site to open its scorecard. The Grid tab shows substation distance, capacity assessment (green/yellow/red traffic light), connectivity status, and transmission cost breakdown.',
    target: 'map',
    action: (s) => {
      const scorecard = s.scorecard;
      if (scorecard?.length) s.selectSite(scorecard[0].site_id);
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
      'Switch to "Hybrid" mode in the header. Wind nighttime generation can reduce BESS sizing, lowering the all-in cost. Check whether hybrid RE changes the investment case at your target sites.',
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
      'The map shows grid integration categories. "Grid ready" sites can procure solar now. "Invest transmission" / "invest substation" sites need specific infrastructure. "Grid first" needs major expansion. This is the policy triage.',
    target: 'map',
  },
  {
    title: 'Captive Power Exposure',
    description:
      'The Industry column tags sites near coal plants and nickel smelters — those face Perpres 112/2022 phase-out pressure. Solar replacement potential shows what % of captive coal could be replaced by buildable solar.',
    target: 'column:industry',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'RUPTL Pipeline',
    description:
      'Switch to the RUPTL tab. Which grid regions have RE pipeline additions by 2030, and which are flat? Cross-reference with "plan late" sites — grid improvement planned but arriving after 2030.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('ruptl'),
  },
  {
    title: 'BPP vs Solar Economics',
    description:
      'This LCOE Gap column shows the gap between solar and PLN cost of supply (BPP). Where solar undercuts BPP (negative gap), the economic case for enabling procurement is self-evident — PLN saves money.',
    target: 'column:solar_competitive_gap_pct',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'Concessional Finance Case',
    description:
      'Set WACC to 8% in the Assumptions panel. Count how many sites flip to "solar now". This quantifies the impact of concessional finance instruments — the core DFI policy argument.',
    target: 'assumptions',
  },
  {
    title: 'Energy Mode — Overall',
    description:
      'Switch to "Overall" mode. The dashboard selects the cheapest RE technology per site (solar, wind, or hybrid). Some eastern sites may favor wind. Best RE Technology shows the winner.',
    target: 'header',
    action: (s) => s.setEnergyMode('overall'),
  },
  {
    title: 'Site Industry & Action Tabs',
    description:
      'Click a site. The Industry tab shows captive coal/nickel/steel/cement context, CBAM exposure, and RUPTL pipeline status. The Action tab shows the specific policy recommendation — flags across 4 energy modes, each naming an intervention.',
    target: 'map',
    action: (s) => {
      const scorecard = s.scorecard;
      if (scorecard?.length) s.selectSite(scorecard[0].site_id);
    },
  },
  {
    title: 'CBAM Trade Pressure',
    description:
      '68 of 81 sites export products subject to the EU Carbon Border Adjustment Mechanism (cement, iron/steel, fertilizer, aluminium). This column shows the 2030 cost per tonne. The "CBAM Urgent" flag fires where border tax savings alone justify RE — an international financial stick alongside Perpres 112 domestic regulation.',
    target: 'column:cbam_2030',
    action: (s) => s.setActiveTab('table'),
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
      'Explore freely. Toggle energy modes, adjust assumptions, and drill into any site. Re-launch this guide from "Guide" anytime.',
    target: 'header',
  },
];

const IPP_STEPS: TourStep[] = [
  {
    title: 'Strong Solar Resource',
    description:
      'Start with the table. Sort by Capacity (MWp) descending — you want sites large enough for utility-scale development (30+ MWp). Filter Action Flag to "solar now". Also filter Grid Integration to "grid ready" or "within boundary" for grid-connected sites.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'BPP Economics',
    description:
      'This LCOE Gap column shows where solar undercuts PLN cost of supply (BPP). Where the gap is negative, the procurement pitch writes itself: "procure solar here and your generation cost drops." PLN saves money.',
    target: 'column:solar_competitive_gap_pct',
  },
  {
    title: 'Grid Readiness',
    description:
      'Grid Integration tags each site: "grid ready" = substation accessible with capacity. Review the capacity assessment traffic light (green/yellow/red) — can the local grid absorb your project output?',
    target: 'column:grid_integration_category',
  },
  {
    title: 'Wind & Hybrid',
    description:
      'Switch to "Wind" or "Hybrid" mode in the header. Some eastern sites have strong wind resource. The Best RE column shows which technology wins. Hybrid mode optimizes solar+wind mix to minimize all-in cost.',
    target: 'header',
    action: (s) => s.setEnergyMode('overall'),
  },
  {
    title: 'Site Deep Dive',
    description:
      'Click your top site. Resource tab: PVOUT and buildable area. Grid tab: substation distance, capacity, connectivity. Economics tab: LCOE bands with BESS storage (14h bridge-hours). Action tab: recommended next step.',
    target: 'map',
    action: (s) => {
      const scorecard = s.scorecard;
      if (scorecard?.length) s.selectSite(scorecard[0].site_id);
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
      'Export your top sites as CSV for your BD pipeline tracker or PLN engagement deck. Re-launch this guide from "Guide" in the header anytime.',
    target: 'header',
  },
];

const INDUSTRIAL_STEPS: TourStep[] = [
  {
    title: 'Understanding the Baseline',
    description:
      'All 81 sites pay the same PLN I-4 industrial tariff today ($63/MWh). The differentiation is risk and trajectory: which sites face future tariff hikes, grid reliability issues, or lack of green energy?',
    target: 'map',
  },
  {
    title: 'Subsidy Exposure',
    description:
      'This Grid Rate column shows PLN cost of supply (BPP) by region. Papua sits at $133/MWh while tariff is only $63/MWh — that $70 gap is a subsidy that is a future tariff hike waiting to happen. High BPP = high risk.',
    target: 'column:dashboard_rate_usd_mwh',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'Grid Reliability Proxies',
    description:
      'The Grid Integration column tags each site by infrastructure readiness. Sites near large substations with green capacity assessments offer better reliability. Continuous-process industries (smelters, data centers) cannot tolerate outages.',
    target: 'column:grid_integration_category',
  },
  {
    title: 'Captive Coal Exposure',
    description:
      'The Industry column tags coal plants and nickel smelters within 50km — those face Perpres 112/2022 phase-out by 2050. RKEF smelters and other 24/7 loads need 14h of BESS bridge-hours storage. Regulatory and cost risk for co-located industry.',
    target: 'column:industry',
  },
  {
    title: 'Green Energy Trajectory',
    description:
      'This LCOE Gap column ranks sites by RE economics. Where RE undercuts BPP (negative gap), grid economics improve over time and your electricity cost is safer long-term. Cross-reference with RE Coverage for buildable potential.',
    target: 'column:solar_competitive_gap_pct',
  },
  {
    title: 'RUPTL Pipeline Risk',
    description:
      'Switch to the RUPTL tab. Check if grid improvements in your target region arrive before or after 2030. A 15-year facility commitment needs confidence that grid capacity keeps pace.',
    target: 'bottom-panel',
    action: (s) => s.setActiveTab('ruptl'),
  },
  {
    title: 'CBAM Exposure',
    description:
      '68 of 81 sites face EU Carbon Border Adjustment Mechanism costs on exports (cement, iron/steel, fertilizer, aluminium). This CBAM 2030 column shows the carbon border tax per tonne. Sites flagged "CBAM Urgent" can justify RE switching on trade economics alone.',
    target: 'column:cbam_2030',
    action: (s) => s.setActiveTab('table'),
  },
  {
    title: 'Site Comparison',
    description:
      'Click a site to review its full scorecard. Overview tab: key metrics. Industry tab: captive power, CBAM trajectory chart (2026-2034), per-product cost breakdown. Grid tab: infrastructure quality. Compare 3-4 candidate sites.',
    target: 'map',
    action: (s) => {
      const scorecard = s.scorecard;
      if (scorecard?.length) s.selectSite(scorecard[0].site_id);
    },
  },
  {
    title: "You're Ready!",
    description:
      'Export the comparison matrix CSV — sites ranked by risk factors (BPP gap, grid quality, green share, captive exposure) for your site selection team. Re-launch from "Guide" anytime.',
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

// Compute the union rect for a column: TH cell horizontal extent,
// extended vertically to the table bottom (so the full column lights up).
function computeColumnRect(columnId: string): DOMRect | null {
  const anchor = document.querySelector(`[data-tour="column-${columnId}"]`);
  const th = anchor?.closest('th');
  const table = th?.closest('table');
  if (!th || !table) return null;
  const thRect = th.getBoundingClientRect();
  const tableRect = table.getBoundingClientRect();
  const bottom = Math.max(thRect.bottom, tableRect.bottom);
  return new DOMRect(thRect.left, thRect.top, thRect.width, bottom - thRect.top);
}

function useSpotlightRect(target: string | null) {
  const [rect, setRect] = useState<DOMRect | null>(null);
  const rafRef = useRef(0);

  useEffect(() => {
    if (!target) {
      setRect(null);
      return;
    }
    const update = () => {
      if (target.startsWith('column:')) {
        setRect(computeColumnRect(target.slice('column:'.length)));
      } else {
        const el = document.querySelector(`[data-tour="${target}"]`);
        setRect(el ? el.getBoundingClientRect() : null);
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

  // Run step action when step changes. Before running the persona's custom
  // action, auto-expand the bottom panel if this step targets it — otherwise
  // we'd spotlight a 34px collapsed bar with no content behind it. Column
  // targets also force the table tab, since columns only render there.
  useEffect(() => {
    if (!currentStep) return;
    const state = useDashboardStore.getState();
    const target = currentStep.target;
    if (target === 'bottom-panel' || target.startsWith('column:')) {
      if (state.bottomPanelCollapsed) state.setBottomPanelCollapsed(false);
      if (target.startsWith('column:') && state.activeTab !== 'table') {
        state.setActiveTab('table');
      }
    }
    currentStep.action?.(state);
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

  // Measured tooltip size — starts as an estimate, updated after first paint.
  // We re-measure on every step + spotlight change so position stays correct
  // even when description length varies wildly between steps.
  const tooltipRef = useRef<HTMLDivElement | null>(null);
  const [tooltipSize, setTooltipSize] = useState<{ w: number; h: number }>({ w: 340, h: 320 });
  useLayoutEffect(() => {
    if (!tooltipRef.current) return;
    const r = tooltipRef.current.getBoundingClientRect();
    if (Math.abs(r.width - tooltipSize.w) > 1 || Math.abs(r.height - tooltipSize.h) > 1) {
      setTooltipSize({ w: r.width, h: r.height });
    }
  });

  if (!currentStep) return null;

  // If the target covers most of the viewport, don't spotlight it — just show tooltip centered
  const isLargeTarget =
    spotlightRect &&
    spotlightRect.width > window.innerWidth * 0.6 &&
    spotlightRect.height > window.innerHeight * 0.6;

  // Position the tooltip near the spotlight (or center if large/missing target).
  // Final step always clamps with the *measured* tooltip size so it can never
  // spill off any edge of the viewport, regardless of step description length
  // or where the spotlight sits.
  const tooltipStyle: React.CSSProperties = {};
  const pad = 16;
  const { w: tw, h: th } = tooltipSize;
  const clampLeft = (l: number) => Math.max(pad, Math.min(l, window.innerWidth - tw - pad));
  const clampTop = (t: number) => Math.max(pad, Math.min(t, window.innerHeight - th - pad));

  if (spotlightRect && !isLargeTarget) {
    if (spotlightRect.right + tw + pad < window.innerWidth) {
      tooltipStyle.left = clampLeft(spotlightRect.right + pad);
      tooltipStyle.top = clampTop(spotlightRect.top);
    } else if (spotlightRect.left - tw - pad > 0) {
      tooltipStyle.left = clampLeft(spotlightRect.left - tw - pad);
      tooltipStyle.top = clampTop(spotlightRect.top);
    } else {
      // No room left or right — stack vertically. Prefer above when the
      // spotlight is in the lower half (bottom-panel case).
      tooltipStyle.left = clampLeft((window.innerWidth - tw) / 2);
      const spaceAbove = spotlightRect.top - pad * 2;
      const spaceBelow = window.innerHeight - spotlightRect.bottom - pad * 2;
      if (spaceAbove >= th || spaceAbove > spaceBelow) {
        tooltipStyle.top = clampTop(spotlightRect.top - th - pad);
      } else {
        tooltipStyle.top = clampTop(spotlightRect.bottom + pad);
      }
    }
  } else {
    // Center the tooltip
    tooltipStyle.left = clampLeft((window.innerWidth - tw) / 2);
    tooltipStyle.top = clampTop((window.innerHeight - th) / 2);
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
        ref={tooltipRef}
        className="absolute rounded-xl p-5"
        style={{
          ...tooltipStyle,
          width: Math.min(340, window.innerWidth - pad * 2),
          maxHeight: window.innerHeight - pad * 2,
          overflowY: 'auto',
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

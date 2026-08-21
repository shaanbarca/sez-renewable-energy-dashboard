# Who Pays, For What, and How Much

**Date:** 2026-08-19 · **Status:** commercial analysis, for the developer conversation
**Question:** assuming we get the proprietary government and developer data, to what extent can
project developers actually use this such that it is worth paying for?

**Related:** [DEVELOPER_WORKFLOW.md](DEVELOPER_WORKFLOW.md) · [PROJECT_CANVAS_SPEC.md](PROJECT_CANVAS_SPEC.md) ·
[GOV_DATA_REQUEST.md](GOV_DATA_REQUEST.md)

> All monetary figures are illustrative models with stated assumptions, not quotes or market data.
> They exist to frame the negotiation, not to settle it.

---

## 0. The short answer

**Yes, but the value is concentrated in a narrower band than it first appears — and it is not where
the engineering effort naturally wants to go.**

Three findings drive everything below:

1. **Avoided waste dominates time saved, roughly 4:1.** Do not sell "screen sites faster." Sell
   "stop spending RM300k studies on sites that were never going to clear the grid gate."
2. **Value scales with sites screened per year.** A high-volume originator gets 10× the value of a
   developer with one project. This is the single cleanest segmentation rule, and it says who to
   sell to.
3. **The willingness to pay attaches to the proprietary grid data, not the software.** That is
   simultaneously the moat and the business's biggest risk (§5).

---

## 1. The value model

A mid-size solar developer, screening sites for LSS6 and CRESS. Assumptions: analyst loaded cost
RM1,400/day · desk screening 3 days/site today, 0.5 with the tool · prefeasibility study RM250–350k ·
half of sites reaching prefeasibility currently die there · the tool improves shortlist quality
enough to cut that kill rate to a quarter.

| Scenario | Labour saved | Waste avoided | Total/yr | Fee at 20% of value |
|---|---:|---:|---:|---:|
| Small — 15 sites/yr | RM52,500 | RM127,500 | **RM180,000** | RM36,000 |
| Mid — 40 sites/yr | RM140,000 | RM600,000 | **RM740,000** | RM148,000 |
| Large — 100 sites/yr | RM350,000 | RM1,575,000 | **RM1,925,000** | RM385,000 |

**Read the middle column, not the left one.** Avoided waste is 4× labour savings in the mid case.
The pitch is loss avoidance, not productivity.

**And the single-event case is stronger still.** A 250 MW data centre site that dies at the grid gate
nine months in — after the land option, legal, and preliminary studies are sunk — costs on the order
of **RM5.6M** (RM2M sunk + 9 months of team and carry at RM400k/month). Avoiding that **once**
exceeds a decade of subscription. That is the story to tell a DC developer, and it is exactly what
the 382 MVA output in the canvas spec surfaces on day one.

---

## 2. The stories

Ordered by how strongly each supports a price.

### S1 — Origination Manager, solar developer 🟢 *Daily user, drives renewal*

> "I get four or five land offers a week from brokers and landowners. Most are junk. Today I can't
> tell which to take seriously without burning a week per site, so I either say no to everything or
> waste analyst time. I want to draw the parcel, and know in two minutes whether there's grid
> headroom within reach, whether the land category is workable, and what it'd clear under LSS6
> versus CRESS."

**Needs the proprietary data?** Yes — B1 (headroom) and B4 (land status) are the whole answer.
**Value:** the RM740k/yr mid case above. **Frequency:** daily-to-weekly. **This is the seat that
makes the product sticky**, because it becomes part of a weekly routine rather than a quarterly
report.

### S2 — Data-centre site selection lead 🟢 *Highest value per use*

> "We've committed to 250 MW by 2029. I need to know which locations in Malaysia can physically
> deliver that — power, water, fibre, and land that won't take 18 months to convert — before we
> option anything."

**Needs the proprietary data?** Critically — B1, B2 (queue), B3 (grid build plan and dates), B7
(water). Without the queue, the answer is unreliable in exactly the way that matters.
**Value:** the RM5.6M single-event case. **Frequency:** a handful of times a year, but each is a
board-level decision. **Willingness to pay is the highest of any persona** and least price-sensitive.

### S3 — Bid team during an LSS6 window 🟢 *Spiky, urgent, high WTP in-window*

> "RFP closes in three weeks. I have eleven candidate sites and need to rank them on deliverable
> cost against the ceiling price, with the mandatory BESS costed to spec, and drop the ones that
> can't connect."

**Needs the proprietary data?** Yes — headroom and queue decide which sites are even biddable.
**Value:** directly revenue-linked — bidding better, or bidding at all. **Frequency:** tender-driven,
concentrated. Suggests a burst-pricing or per-tender option alongside subscription.

### S4 — Investment Committee / CFO 🟡 *Doesn't use it, but must trust it*

> "Don't show me a map. Show me the IRR, the DSCR, and what you assumed — and tell me why this site
> and not the other four."

**Needs the proprietary data?** Indirectly; needs the *provenance* of it.
**Value:** this is the gate that releases study budget. **This is where M2 (project finance) earns
its keep** — without NPV/IRR/DSCR the tool never reaches the person who approves spending.
**Design implication:** an exportable, assumption-transparent decision pack matters as much as the
interactive UI.

### S5 — Head of Development / Country Manager 🟡 *Signs the cheque*

> "Where should we be hunting next year, before our competitors work it out?"

Portfolio and strategy view: where headroom exists, where it's opening (B3), where land is workable.
**Frequency:** quarterly. **Low usage, high influence** — buys on the strategic map, renews on S1's
daily use.

### S6 — Corporate offtaker under CRESS 🟡 *A different, larger market*

> "I'm a manufacturer with an RE target. Who can supply me, from where, at what delivered cost?"

This is the **other side of the market** — and there are far more corporate buyers in Malaysia than
there are developers. Same engine, inverted query. Worth flagging as adjacent expansion, **not** as
v1 scope.

### S7 — Lender / technical due diligence 🔴 *Poor fit, be honest*

Lenders need bankable P90, geotech, and an actual TNB Connection Assessment Study. The tool provides
none of these. It can inform a lender's early view; it cannot support credit. **Do not sell here.**

### S8 — Government / regulator ⚪ *Not a customer — the counterparty*

The original Indonesia persona, and the source of B1–B7. They may well want access **in exchange**
for the data. Treat this as part of the data deal, not a revenue line — and price it at zero
deliberately, as the cost of the moat.

---

## 3. Where it is genuinely not worth paying

Stating this plainly is what makes the rest credible:

- **After site selection.** The tool contributes essentially nothing to the RM6–10M development
  stage — geotech, EIA, detailed design, owner's engineer. That work is untouched.
- **Single-project developers.** Value scales with volume screened. One project, one site, no
  recurring need. They should buy a study, not a subscription.
- **Anything contractual or bankable.** No P90, no CAS, no title opinion. Never position it as
  underwriting.
- **Developers with a locked pipeline.** If their next five sites are already optioned, screening
  value is near zero — sell them canvas mode for the *sixth*, or don't sell yet.

---

## 4. Pricing structures worth considering

| Model | Fit | Note |
|---|---|---|
| **Seat-based SaaS** | S1, S5 | Aligns with daily use; ties revenue to team size, which grows |
| **Tiered by data layer** | All | Open-data tier cheap or free; **proprietary grid layer is the premium tier**. Matches where value actually sits, and makes the moat the paywall |
| **Per-tender burst licence** | S3 | Captures spiky LSS-window demand from firms that won't hold a subscription |
| **Enterprise site licence** | S2, large DC | Fits infrequent, very-high-stakes use |
| **Success fee at FID** | — | Aligns beautifully, near-impossible to police. Avoid as primary |
| **JV / equity with the developer** | — | Different question entirely: are they a customer or a partner? (§6) |

Anchor on the value table: a fee at ~20% of modelled annual value lands at **RM150–400k/yr** for
mid-to-large developers, and **RM36k/yr** for small ones — which suggests small developers are a
self-serve tier, not a sales target.

---

## 5. The two risks that decide whether this is a business

**Risk 1 — The moat is the data, not the code.** Everything else in the tool is reproducible by a
competent consultant with open data in a few weeks. If the government publishes B1/B2 openly, or
TNB launches a public capacity map, the premium tier's justification evaporates overnight. Mitigate
by: contracting for freshness and exclusivity where possible, layering proprietary *developer*
calibration data (actual EPC costs, actual connection charges, actual timelines) that no government
will ever publish, and building enough workflow stickiness (saved projects, comparisons, decision
packs) that switching costs exist independent of the data.

**Risk 2 — The Malaysian market is small.** Realistically 50–150 organisations across solar
developers, IPPs, DC operators, and large corporates. At RM50–400k/yr that is a low-tens-of-millions
TAM at absolute saturation, which no one reaches. **This is the commercial argument for the
multi-country architecture** — the same engine over Vietnam, the Philippines, Thailand and Indonesia,
each with the identical grid-constraint-plus-data-centre shape. The architecture decision in the
strategy doc was justified on engineering grounds; it is justified at least as strongly on market
size.

---

## 6. The question to settle with the developer

**Are they a customer, a channel, or a partner?** These are very different deals and it is worth
deciding before the meeting rather than during it:

- **Customer** — they pay a licence. Cleanest, smallest, keeps the rest of the market open.
- **Channel** — they open doors to other Malaysian developers and to government, for a share.
  Their credibility solves the cold-start problem; that is worth real equity or margin.
- **Partner / JV** — shared ownership of a Malaysian entity. Highest upside, most entangled, hardest
  to unwind.

**And the single most important commercial term: exclusivity.** If they want exclusive Malaysian
rights, that forecloses every other persona in §2 — S3, S6, and the rest of the market. If they ask
for it, the price should reflect the whole market, not one customer.

**What to ask them for regardless of structure:** their calibration data — actual EPC cost per MWp,
actual land lease rates, actual grid connection charges paid, actual application-to-energisation
timelines. It costs them nothing, no government will ever publish it, and per Risk 1 it may end up
being the more durable half of the moat.

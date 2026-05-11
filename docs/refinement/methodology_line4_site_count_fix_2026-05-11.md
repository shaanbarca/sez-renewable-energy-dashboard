# METHODOLOGY_CONSOLIDATED.md line 4 — site count arithmetic fix

**Finding date:** 2026-05-11
**Reviewer:** Wiki LLM (Energy/Renewables vault)
**Surfaced by:** Pre-publish fact-check on the Substack and LinkedIn launch posts (both posts had copied the bad number from line 4 and would have published with a sum that doesn't add to 81). Posts now fixed wiki-side; this note flags the dashboard-side root cause.

---

## TL;DR

`METHODOLOGY_CONSOLIDATED.md` line 4 currently states:

> *"81 sites (25 KEKs + 56 industrial: 32 cement + 17 steel + 5 fertilizer + 2 aluminium + 10 nickel IIA)"*

The arithmetic doesn't work. 25 + 32 + **17** + 5 + 2 + 10 = **91**, not 81. The industrial-breakdown line sums to 66, not 56.

**Fix:** change `17 steel` to `7 steel`. New sum: 25 + 32 + **7** + 5 + 2 + 10 = **81** ✓; industrial = 32 + 7 + 5 + 2 + 10 = 56 ✓.

One-character edit. Substantively zero impact on any methodology or output. Pure documentation hygiene.

---

## Why the bug happened (and why "17" is plausible-looking)

The dashboard uses two different breakdowns of the same 81-site universe:

| Breakdown | Steel count | Source |
|---|---|---|
| **Universe breakdown** (one row per physical site) | **7 steel mills** | `EXECUTIVE_SUMMARY.md` line 27 + line 119; `GEM Global Iron & Steel Plant Tracker (7 active plants)` |
| **CBAM-classification breakdown** (one row per CBAM Annex I product) | **17 iron_steel** | `EXECUTIVE_SUMMARY.md` line 132: `32 cement + 17 iron_steel + 5 fertilizer + 2 aluminium` |

The difference: **CBAM Annex I classifies nickel pig iron as iron and steel**, so the 10 non-KEK nickel IIA sites contribute to the iron_steel CBAM count. 7 dedicated steel mills + 10 nickel sites (CBAM-classified iron_steel) = 17 iron_steel for CBAM exposure purposes.

Line 4 appears to have mixed the two breakdowns: it used "17 steel" (the CBAM classification number) while *also* listing "10 nickel IIA" separately (the universe convention). Result: the 10 nickel sites are double-counted, and the sum overflows.

The CBAM-classification breakdown is itself correct in its context (line 132 of EXECUTIVE_SUMMARY) and should not change.

---

## Exact diff

Current (line 4):

```
**Status:** Implemented in code. 81 sites (25 KEKs + 56 industrial: 32 cement + 17 steel + 5 fertilizer + 2 aluminium + 10 nickel IIA), 541 tests passing.
```

Proposed:

```
**Status:** Implemented in code. 81 sites (25 KEKs + 56 industrial: 32 cement + 7 steel + 5 fertilizer + 2 aluminium + 10 nickel IIA), 541 tests passing.
```

---

## Other places to check (recommendation, not part of this fix)

I grepped `METHODOLOGY_CONSOLIDATED.md` and `EXECUTIVE_SUMMARY.md` for `17 steel`, `17 iron_steel`, `32 cement.*17`, and `56 industrial`. Findings:

| Location | Number | Verdict |
|---|---|---|
| `METHODOLOGY_CONSOLIDATED.md` line 4 | 17 steel | **Bug** — fix per above |
| `EXECUTIVE_SUMMARY.md` line 27 | 7 steel mills | Correct (universe breakdown) |
| `EXECUTIVE_SUMMARY.md` line 119 | GEM Iron & Steel Tracker = 7 active plants | Correct (source-of-truth) |
| `EXECUTIVE_SUMMARY.md` line 132 | 17 iron_steel | Correct (CBAM-classification breakdown, in CBAM context) |
| `EXECUTIVE_SUMMARY.md` line 156 | 25 KEK + 56 industrial | Correct |
| `EXECUTIVE_SUMMARY.md` line 164 | 12 KEK 3-signal + 56 industrial direct | Correct |

No other instances of the bug in either doc. Safe to fix line 4 in isolation.

---

## Adjacent observation (not part of this fix)

`METHODOLOGY_CONSOLIDATED.md` line 4 says **541 tests passing**. `EXECUTIVE_SUMMARY.md` line 132 says **686 automated tests, including 67 new rooftop pipeline tests**. These are inconsistent — likely because EXECUTIVE_SUMMARY was updated for v4.1 rooftop (which added the 67 tests + other v4.1 work) and METHODOLOGY line 4 wasn't updated alongside.

This is a separate documentation-staleness issue, not the same bug. Flagging in case a methodology version bump is part of the same fix cycle — at that point updating the test count to match the current `make test` output would be a natural co-fix. Not blocking the steel count fix.

---

## Why this matters for credibility

Pre-publish fact-check on the Substack and LinkedIn posts (scheduled for 2026-05-12 LinkedIn / 2026-05-13–14 Substack) caught the arithmetic issue when the wiki LLM summed the sector counts and got 91. A sharp reader on LinkedIn would have done the same sum in their head within ~10 seconds. Credibility cost would have been: *"if this person can't add five numbers, why should I trust their methodology?"*

The dashboard's methodology doc is the single authoritative reference (per its own line 7: *"This document is the single authoritative methodology reference"*). Any future post, press, paper, or grant application citing the 81-site breakdown will copy from line 4. Fixing the source kills the bug downstream.

---

## Connections

- **Surfaced by**: pre-publish fact-check on `posts/substack/2026-05-09_post-1-v2-tight.md` and `posts/linkedin/2026-05-08_dashboard_announcement.md` (both fixed wiki-side 2026-05-11).
- **Adjacent refinement docs**: `RUPTL_INTEGRATION_review_2026-05-10.md` (also has cross-doc consistency findings; same review pattern).
- **Pattern**: this is a "documentation drift" issue, structurally similar to the GEAS abbreviation drift flagged in the RUPTL review (`EXECUTIVE_SUMMARY.md` says "Government Energy Allocation for Solar"; METHODOLOGY says "Green Energy Auction Scheme"; RUPTL_INTEGRATION.md says "Green Energy as a Service"). Both suggest that a one-pass cross-doc consistency lint on canonical numbers and definitions would catch the next instance.

---

## Recommended action

1. **Fix**: change `17 steel` to `7 steel` on `METHODOLOGY_CONSOLIDATED.md` line 4.
2. **Optional co-fix**: bump test count `541` → current `make test` output (if a methodology update is happening anyway).
3. **No other downstream changes needed**: EXECUTIVE_SUMMARY is already correct; the CBAM-classification "17 iron_steel" on line 132 is correctly in context and should not change.

Effort: <2 minutes. Lowest-hanging-fruit fix on the dashboard side this week.

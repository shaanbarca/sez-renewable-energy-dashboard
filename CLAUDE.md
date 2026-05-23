# CLAUDE.md

Guidance for Claude Code working on this repo. Trimmed 2026-05-07 from 361 → ~190 lines: detail moved to the pointer docs below; this file keeps project intent, conventions, and workflow.

## Project context

Python modelling + dashboard for **Indonesia's industrial decarbonization**. 81 sites — 25 KEKs (Special Economic Zones) + 56 industrial (32 cement + 7 steel + 10 nickel IIA clusters + 2 aluminium + 5 fertilizer). The dashboard answers: *"Which Indonesian industrial site can offer low-cost, low-carbon, reliable electricity, how exposed is it to EU CBAM, and what must change to get there?"*

**Site selection is pipeline-driven** — cement/steel/nickel rows generated in `src/pipeline/build_industrial_sites.py` from public trackers (GEM, CGSP). Aluminium + fertilizer are residual manual rows in `data/industrial_sites/priority1_sites.csv` with provenance enforced at build time. Site-type behavior (demand, captive matching, CBAM detection, marker shape) is driven by `src/model/site_types.py::SITE_TYPES` registry mirrored in `frontend/src/lib/siteTypes.ts` — adding a type is a 1-dict-entry change.

**Core documents — read first:**

| File | Purpose |
|---|---|
| [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | Plain-language overview |
| [PLAN.md](PLAN.md) | Implementation plan |
| [DESIGN.md](DESIGN.md) | Dashboard UX spec |
| [PERSONAS.md](PERSONAS.md) | 5 user personas |
| [docs/METHODOLOGY_CONSOLIDATED.md](docs/METHODOLOGY_CONSOLIDATED.md) | Methodology spec — `src/model/basic_model.py` implements this |
| [docs/TAXONOMY.md](docs/TAXONOMY.md) | Cost-column taxonomy — read before adding a new $/MWh column |
| [DATA_DICTIONARY.md](DATA_DICTIONARY.md) | Every column, every status (✅/⚠️/❌/🔒) |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Data flow, pipeline graph, design decisions |
| [TODOS.md](TODOS.md) | Pre-spec deferred items (rooftop RV, JETP, etc.) |
| [docs/refinement/dashboard_roadmap_v4_v5.md](docs/refinement/dashboard_roadmap_v4_v5.md) | v4.0.5 → v5.0 roadmap |

## Setup

```bash
uv sync                              # install deps + create .venv
uv run pytest tests/                 # run tests
uv run ruff check src/ tests/        # lint
uv run ruff format src/ tests/       # format
```

Copy `.env_template` → `.env` and fill: `MAPBOX_TOKEN`, `S3_ACCESS_KEY`, `S3_SECRET_ACCESS_KEY`. Frontend reads `MAPBOX_TOKEN` from root via `frontend/vite.config.ts`.

## Running the dashboard

```bash
# Terminal 1 — API (loads pipeline data at startup)
uv run uvicorn src.api.main:app --port 8000

# Terminal 2 — Vite dev server (proxies /api to :8000)
cd frontend && npm run dev
```

Frontend at `http://localhost:5173`. API at `http://localhost:8000`.

**Frontend lint/type:**
```bash
cd frontend
npm run lint          # biome check (no auto-fix)
npm run format        # biome --write
npx tsc --noEmit      # type-check
```

## Where things live

| What | Where |
|---|---|
| FastAPI backend | `src/api/main.py` (entry), `src/api/routes/` |
| Pipeline modules | `src/pipeline/build_*.py` (run via `run_pipeline.py`) |
| Model / methodology | `src/model/basic_model.py` (LCOE, action flags, CostBasis enum) |
| Dash logic | `src/dash/logic/` — assumptions, lcoe, cbam, grid, technology, scorecard |
| Constants | `src/assumptions.py` (single source of truth for thresholds + defaults) |
| Frontend | `frontend/src/` — Zustand store at `store/dashboard.ts`, API at `lib/api.ts`, types at `lib/types.ts`, MapLibre map at `components/map/`, Recharts at `components/charts/` |
| Raw data | `data/` (mostly gitignored — large geospatial files) |
| Pipeline outputs | `outputs/data/processed/` (CSVs that the API loads) |
| Tests | `tests/` — 1170+ tests, golden fixture at `tests/fixtures/scorecard_golden.pkl` (225 cols as of v4.1b), v4.0 baseline lock at `tests/fixtures/scorecard_v4_0_baseline.csv` |

For specific function signatures or column schemas, read the source / `DATA_DICTIONARY.md` directly. This file used to enumerate them — they drift fast and the source is canonical.

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool as the FIRST action. Don't answer directly, don't use other tools first.

Key routing rules:
- Product ideas / brainstorming → `office-hours`
- Bugs / errors / "why is this broken" → `investigate`
- Ship / deploy / push / create PR → `ship`
- QA / test the site → `qa`
- Code review → `review`
- Update docs after shipping → `document-release`
- Weekly retro → `retro`
- Design system → `design-consultation`
- Visual audit → `design-review`
- Architecture review → `plan-eng-review`
- Save / resume progress → `context-save` / `context-restore`
- Code quality / health → `health`

## F-findings — GitHub issues + grouped branches (convention 2026-05-07)

**Every numbered finding in `docs/refinement/*.md` (F1, F2, ...) gets a GitHub issue on `shaanbarca/eez`.** Issues are the unit of tracking; **branches/PRs are the unit of shipping**. Branches group findings by **methodological theme**, not by size — solo-dev pace, content-coherent reviews.

### Per-batch workflow

1. Pick a thematic group (see roadmap or below). Branch like `v4.0.5/<theme-slug>` — e.g., `v4.0.5/carbon-emissions`, `v4.0.5/grid-captive`, `v4.0.5/geothermal-proximity`.
2. Work through the batch's findings as commits. Each commit message: `[F<N>] <subject> (#<issue>)` — multiple `[F<N>]` per commit is fine when changes are tightly coupled.
3. When the batch is ready: open ONE PR with body `Closes #N, #M, #P`. All issues in the batch auto-close on merge.
4. Issue links in `docs/refinement/*.md` are enforced by the pre-commit hook (`scripts/check_finding_issue_links.py`) — every `(Finding N)` reference must include `[#NN](.../issues/NN)`.

### v4.0.5 batch suggestions (12 remaining findings — F1 already shipped as PR #16)

| Branch slug | Findings | Theme |
|---|---|---|
| `v4.0.5/carbon-emissions` | F4, F9 | Solar lifecycle correction + Scope 1 abatement flags |
| `v4.0.5/grid-captive` | F5, F6, F7, F12 | RUPTL §V.11 + Perpres 112 + RUPTL feedback doc + captive contractual |
| `v4.0.5/geothermal-proximity` | F2 | Standalone — new spatial signal |
| `v4.0.5/hybrid-wind` | F3, F10, F11 | Wind nighttime + binding constraint + MacKay correction |
| `v4.0.5/supply-blend` | F8, F13 | Curtailment cost + GEAS empirical |

Workflow scripts (`scripts/start_finding.sh`, `scripts/finish_finding.sh`) currently support single-finding mode. **Batched-mode helpers TBD** — for now, `git checkout -b v4.0.5/<theme>` manually + commit through with `[F<N>]` prefixes + open PR with multi-issue `Closes` body.

## Follow-up tracking — every loose thread gets an issue

Whenever a session surfaces a follow-up that isn't being fixed in the current PR — a deferred bug, a bucket of sites that needs validation, a methodology gap, a "we'll do this in v4.1" item — **file a GitHub issue immediately on `shaanbarca/eez`**. Don't rely on memory, chat scrollback, or "I'll come back to this." Issues are the persistent layer; conversations and PR bodies decay.

What counts as a follow-up worth an issue:
- A bug we found but explicitly deferred (e.g., "21 polygon-missing sites — buffer fallback now, real polygons later")
- A scope split surfaced during RCA or review (e.g., "bucket B is a separate UX problem from bucket A")
- A methodology gap noted in passing ("KEK coarse-raster optimism — measure in v4.1")
- A `/codex review` or `/plan-eng-review` finding classified as deferred / non-blocking
- A `TODO` / `FIXME` / `HACK` comment landed in code that represents real future work (not a trivial inline note)
- Tier-3 polygon hunts, sector-specific calibrations, or any "the dashboard isn't lying but we know it could be better" item

What doesn't:
- Things you're about to fix in the same PR (those go in the PR body, not a separate issue)
- Trivial polish ideas with no acceptance criteria (those go in TODOS.md if anywhere)
- Anything already covered by an existing open issue (link to it instead of duplicating)

Pattern:

```bash
gh issue create --repo shaanbarca/eez \
  --title "v4.1: <one-liner — version-tag the target release if known>" \
  --body "<context (what was found + why deferred) + acceptance criteria>"
```

Reference the new issue number in the PR body of the work that surfaced it (`Closes #X` if fixed here, "follow-up: #Y" if deferred), and add the follow-up to TODOS.md's "Today's deltas" section so the next session sees it. The next "what's next" question starts with `gh issue list --repo shaanbarca/eez --state open`.

Surfaced from the PR #44 → #45/#46/#43-rescope/#47/#48 chain on 2026-05-12–13 where every loose thread got an issue. That's the working pattern — keep it consistent.

## Issue and PR template — enforced (2026-05-15)

**Every `gh issue create` and `gh pr create` body must follow the Rich template.** The body is validated by `scripts/check_template.py`; calls with non-conforming bodies are blocked at three layers:

1. **`.claude/hooks/validate_gh_body.py`** — PreToolUse hook intercepts `Bash` calls to `gh issue/pr create`, runs the validator, blocks with diagnostic on failure. Triggers BEFORE the call hits GitHub.
2. **`.github/workflows/check-pr-body.yml`** — backstop GitHub Action runs the same validator on PR open / edit / reopen / synchronize. Fails the check until the body conforms.
3. **Scaffold files** — `.github/ISSUE_TEMPLATE/feature_request.md` and `.github/pull_request_template.md` pre-fill the structure when opening from `gh` CLI or github.com UI.

**Required sections (issues):** `## Problem`, `## Outcome`, `## Demo`, `## Scope`, `## Acceptance criteria`, `## Risk`, `## Anchor`.

**Required sections (PRs):** `## What changed`, `## Why this matters`, `## Demo`, `## Risk`, `## Reviewer checklist`, `## Tests`.

Each section needs ≥30 chars of real content (HTML comment hints don't count). Heading text is matched case-insensitively by prefix, so `## What changed for a dashboard user` matches the required `## What changed`.

Authoring pattern:

```bash
# Write body to a file (heredoc avoids shell escaping pain)
cat > /tmp/pr_body.md <<'EOF'
## What changed
...
## Why this matters
...
(etc — all 6 sections)
EOF

# Validate locally before opening
uv run python scripts/check_template.py --kind pr --file /tmp/pr_body.md

# Open the PR using --body-file (so the hook reads the same file the validator just OK'd)
gh pr create --repo shaanbarca/eez --base main --title "..." --body-file /tmp/pr_body.md
```

If the hook blocks unexpectedly, the diagnostic names the failing section. Fix the body and retry — **do not bypass** with `--no-verify`-style escape hatches; the Action will fail anyway.

### Auth state (2026-05-07)

Auth gate is commented out in `src/api/main.py` and `frontend/src/App.tsx`. Code preserved for easy re-enable. Re-enable is a user decision — don't proactively suggest it.

## Before every commit — required checklist

When the user says "commit" or asks to commit, prompt with this checklist:

```
1. /review run? — catch breaking changes before they're in git history
2. Output CSVs spot-checked? — if a pipeline ran this session, paste the
   output so we can sanity-check (distances, row counts, LCOE plausible?)
3. Docs updated? — see Documentation update rule below; every change
   type has specific files that must be updated before committing

Ready to commit, or do any of these need attention?
```

**Before big phase transitions** (data pipeline → Dash app, etc.): run `/autoplan` for full CEO + Eng + Design review simultaneously.

## Documentation update rule

Every code change — feature, column, bug fix that changes output, deferred item now implemented — updates the relevant docs **before commit**.

| What changed | Files to update |
|---|---|
| New pipeline step or `fct_*` / `dim_*` table | `DATA_DICTIONARY.md` + this file (table list) + `run_pipeline.py` + `ARCHITECTURE.md` (if topology changed) |
| New column on existing table | `DATA_DICTIONARY.md` + `PERSONAS.md` (if persona-relevant) |
| New column surfaced in a UI table or drawer with non-obvious name | Must have a tooltip on the column header AND on per-row badges/values. Ambiguous column names (anything a smart user couldn't infer from the label alone — confidence tiers, provenance flags, raw metric names like "PVOUT", computed indices) explain themselves on hover. Pattern: `<SortHeader ... tooltip="..."/>` for headers, `title={...}` or `<StatRowWithTip tip={...}/>` for cells. If the tooltip would need to be longer than a couple of sentences, link to the relevant METHODOLOGY §. |
| New site type or sector | `src/model/site_types.py` + `frontend/src/lib/siteTypes.ts` + `DATA_DICTIONARY.md` |
| Method or formula changed | `docs/METHODOLOGY_CONSOLIDATED.md` |
| Deferred item implemented | METHODOLOGY (remove deferred note) + DATA_DICTIONARY (status ✅) + PERSONAS (gap → built) |
| Bug fix that changes outputs | METHODOLOGY (if behavior changes) + DATA_DICTIONARY (if semantics shift) |
| New assumption or threshold | METHODOLOGY (rationale) + `src/assumptions.py` (constant) |
| Phase / step completed | `PLAN.md` ✅ |
| Design or architecture change | `DESIGN.md` (+ §9 changelog) + `ARCHITECTURE.md` (if boundary changed) + `EXECUTIVE_SUMMARY.md` |
| Deferred item identified | `TODOS.md` (priority + source + personas affected) |

**Commit checklist's item 3 ("Docs updated?") references this table.** `/review` flags stale docs as INFORMATIONAL.

## Data notes

- Grid cost proxy uses **PLN BPP** (cost of supply), NOT industrial tariff. They differ — industrial tariffs are often subsidized below BPP. Label this distinction in any output.
- RUPTL data (`fct_ruptl_pipeline`) is region/system-level, not KEK-specific. Provides system context only.
- Big static datasets in `data/`: `substation.geojson` (2,913 PLN substations, used for proximity), `pln_grid_lines.geojson` (1,595 lines, used for connectivity), `industrial_data/` (50k+ employee firms 2023), GEM steel/cement plants in `data/captive_power/`.

## Operational state

Production deploy is on Render via `private` remote (`https://github.com/shaanbarca/eez.git`). Render auto-deploys on push to main. Health endpoint: `/api/health` returns sites count. Memory diagnostic: `/api/health/memory` returns RSS + `lru_cache` state for the buildings/tiles parquets — hit it from prod to debug OOM issues.

`origin` remote is the public mirror (`shaanbarca/sez-renewable-energy-dashboard`); push to both.

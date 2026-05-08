---
name: finish-finding
description: Implement and commit a numbered finding from any release spec under docs/refinement/. Auto-detects the release by scanning spec files, finds the linked GitHub issue, ensures the right batch branch, runs the change-doc-test-commit cycle per CLAUDE.md, and produces a prefixed commit that auto-closes the issue on merge. Use when the user says "do F<N>", "finish finding N", "implement F<N> for v4.1", or invokes /finish-finding <args>.
---

# /finish-finding <N> [release]

Ship a single finding from any `docs/refinement/*_spec.md`.

## Inputs
- `<N>`: finding number (e.g. `4`, `F4`, `f4` — all valid).
- `[release]` (optional): release slug like `v4.0.5`, `v4.1`, `v4.2`. Omit if unambiguous.

## Step 1 — Resolve the finding
1. List `docs/refinement/*_spec.md` files. Each is a release spec.
2. Grep each for `Finding <N>` (case-insensitive). Build a map of `{release_slug: spec_path}`.
   - Release slug parsed from filename: `v4_0_*` → `v4.0.5`, `v4_1_*` → `v4.1`, `v4_2_*` → `v4.2`, `v4_3_*` → `v4.3`, `v4_4_*` → `v4.4`, `v4_5_*` → `v4.5`. If a different naming scheme appears, ask the user.
3. Resolution rule:
   - **One match, no `[release]` arg** → use it.
   - **Multiple matches, no `[release]` arg** → tell the user which releases contain Finding <N> and ask which one.
   - **`[release]` arg given** → use that, error if not found.
4. Read the spec section in full. Find the linked issue via the `[#NN](.../issues/NN)` pattern on the section heading line. Read it: `gh issue view NN --repo <repo>`.
5. Identify the batch theme from the spec's batch table. The spec's batch suggestions section maps findings → batch slug.

## Step 2 — Branch
- Branch convention: `<release>/<theme-slug>` (e.g. `v4.0.5/hybrid-wind`, `v4.1/foundation-hydro`).
- If already on the expected branch: continue.
- If on a different release/theme branch: ask before switching.
- If on `main`: `git checkout -b <release>/<theme-slug>`.

## Step 3 — Find the commit prefix convention for this release
- Default v4.0.5 convention is `[F<N>] <type>: ...` (per CLAUDE.md).
- Other releases may use a different prefix. Resolution order:
  1. If the spec frontmatter has `commit_prefix:`, use that template.
  2. If the spec's batch table or intro shows a sample commit, infer the prefix from that.
  3. Otherwise default to `[F<N>]`.
- Confirm with the user once per release if uncertain.

## Step 4 — Implement
- Read the full spec section + the linked issue. Don't shortcut.
- Implement the code change. Always thread site context (region, sector, etc.) where the spec calls for site-specific behavior — uniform fallbacks must be explicit, not implicit.
- For doc-only findings: edit the relevant doc, skip to Step 6 (test) and Step 7 (commit).

## Step 5 — Doc updates (per CLAUDE.md "Documentation update rule" table)
Match the change type. Common cases:
- **New column / table:** `DATA_DICTIONARY.md` (status + formula) + METHODOLOGY (rationale).
- **Method/formula changed:** METHODOLOGY with date marker `(F<N>, YYYY-MM-DD)`.
- **New assumption/threshold:** METHODOLOGY (rationale) + `src/assumptions.py` (constant + comment).
- **Deferred item implemented:** METHODOLOGY (drop deferred note) + DATA_DICTIONARY (✅) + TODOS.md.
- **Phase / step completed:** PLAN.md ✅.

The CLAUDE.md doc-update table is the canonical source — re-read it if uncertain.

## Step 6 — Test
- `uv run ruff check src/ tests/`
- `uv run pytest tests/ -x` — full run; findings ripple.
- New scorecard column: `PYTHONPATH=. uv run python scripts/capture_scorecard_golden.py` then re-run `pytest tests/test_scorecard_golden.py`. Note column count delta in commit message.
- Frontend changes: `cd frontend && npx tsc --noEmit && npm run lint`.

## Step 7 — Commit
Format (substitute prefix per Step 3):
```
[F<N>] <type>: <one-line subject>

<paragraph: what changed + why — pull from spec "Why this matters">

<bulleted file list with one-line rationale per file>

Closes #<NN>.
```

- `<type>`: `feat` (new column/signal), `fix` (changed output), `doc` (doc-only), `refactor`, `test`.
- Stage explicit paths only — avoid `git add -A`. Pre-commit reformats can muddy the stage; unrelated untracked files sneak in.
- If pre-commit hook reformats: re-stage and create a NEW commit (not amend).

## Step 8 — STOP — do not push
Per user's standing rule: never `git push` without explicit user direction. Report:
- Commit SHA
- Files changed
- Issue that will close on merge
- Whether more findings remain in the same batch — if yes, name the next finding number and ask whether to continue.

## Notes
- Multiple findings per commit are fine when tightly coupled (per CLAUDE.md). Subject line: `[F<A>][F<B>] <subject>`.
- One PR per batch (not per finding). PR opens after the batch completes — separate user decision.
- Deferred-in-spec findings (marked "deferred to v4.4" or similar): note the deferral in a comment on the linked issue, do not implement, stop.
- Spec section line numbers drift — always grep, never trust a remembered line number.
- Release slug parser is best-effort. If a future spec uses a naming scheme that doesn't match `v4_X_*.md`, ask the user once and remember the mapping (saved as a feedback memory).

## Examples
- `/finish-finding 4` → if Finding 4 only in v4_0_dashboard_fixes_spec.md, proceed on `v4.0.5/<theme>`.
- `/finish-finding 2 v4.1` → finds Finding 2 in v4_1_foundation_spec.md, branches `v4.1/<theme>`.
- `/finish-finding F11` → strips the `F` prefix, same as `/finish-finding 11`.
- `/finish-finding 7` (in v4.0.5 spec marked "deferred to v4.4") → comment on issue, stop.

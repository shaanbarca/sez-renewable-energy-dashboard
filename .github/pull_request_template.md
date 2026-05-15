<!--
This scaffold is validated by scripts/check_template.py.
Required sections: What changed, Why this matters, Demo, Risk, Reviewer checklist, Tests.
Each section needs ≥30 chars of real content (HTML comments don't count).

If this PR closes one or more issues, link them in "Why this matters":
"Closes #N, #M" — those will auto-close on merge.
-->

## What changed

<!--
User-facing description first. New columns, new UI, new endpoints — what
someone using the dashboard now experiences differently.
A table works well when multiple features ship together. Code paths go below
in the "Tech details" collapsed block.
-->

## Why this matters

<!--
The gap this closes, the decision it unblocks. If this PR closes issues, link
them here ("Closes #N"). If it's a prerequisite for downstream work, name it.
Avoid "as discussed in slack" — write it down.
-->

## Demo

<!--
Concrete verification:
1. Pull this branch
2. Run X (e.g. `uv run python run_pipeline.py`)
3. Open Y
4. See Z change
-->

## Risk

<!--
Blast radius + mitigations. What columns/files/behavior could break?
What's the rollback if a default value is wrong?
"Low — additive" is acceptable when true; otherwise list the load-bearing changes.
-->

## Reviewer checklist

<!--
Concrete items the reviewer can confirm by looking at specific files/outputs.
Beats "tests pass" — name the file or table to inspect.
-->

- [ ]

## Tests

<!--
Test counts, golden status, what was added vs preserved. Name the test file(s)
that cover the new code paths.

For PRs touching ≥5 files, add a collapsible "Tech details" block after this
section grouping NEW vs MODIFIED so reviewers can navigate without `git diff --stat`:

<details>
<summary>Tech details: files changed</summary>

NEW:
- path/to/new_file.py — one-liner on purpose

MODIFIED:
- path/to/edited_file.py — what changed

</details>
-->


#!/bin/bash
# Finish work on F-findings: push, open PR with Closes #N (or multi-issue Closes).
#
# Usage: scripts/finish_finding.sh
#
# Auto-detects branch mode:
#   f<N>/<slug>           → single-finding PR with body "Closes #<N>"
#   v<release>/<slug>     → batched PR; finds all [F<N>] in commit messages,
#                           looks up matching issues by [F<N>] title prefix,
#                           PR body has "Closes #N, #M, #P"
#
# Steps in both modes:
#   1. Verify branch format and commits ahead of main
#   2. Run pytest
#   3. Push to private + origin
#   4. Open PR with appropriate Closes syntax
#   5. Comment on each closed issue with PR link
# Stops short of merging — user reviews + merges.

set -euo pipefail

REPO="shaanbarca/eez"
BRANCH=$(git branch --show-current)

# ─── 1. Detect branch mode ───────────────────────────────────────────────────

if [[ "$BRANCH" =~ ^f([0-9]+)/(.+)$ ]]; then
  MODE=single
  F_NUM="${BASH_REMATCH[1]}"
elif [[ "$BRANCH" =~ ^v([0-9]+\.[0-9a-z]+(\.[0-9a-z]+)*)/(.+)$ ]]; then
  MODE=batch
  RELEASE="v${BASH_REMATCH[1]}"
else
  echo "ERROR: branch '$BRANCH' doesn't match a known format." >&2
  echo "  Single mode: f<N>/<slug>" >&2
  echo "  Batched mode: v<release>/<slug>" >&2
  exit 1
fi

echo "→ Branch:  $BRANCH"
echo "→ Mode:    $MODE"

# ─── 2. Find issues to close ─────────────────────────────────────────────────

if [ "$MODE" = "single" ]; then
  echo "→ Finding: F$F_NUM"
  ISSUE=$(gh issue list --repo "$REPO" --label "F-finding" --state all --limit 100 --json number,title \
    | python3 -c "
import json, sys
data = json.load(sys.stdin)
for i in data:
    if i['title'].startswith('[F$F_NUM]'):
        print(i['number'])
        break
")
  if [ -z "$ISSUE" ]; then
    echo "ERROR: couldn't find issue with [F$F_NUM] prefix on $REPO." >&2
    exit 1
  fi
  echo "→ Issue:   #$ISSUE"
  declare -a ISSUES=("$ISSUE")
  declare -a F_NUMS=("$F_NUM")
else
  # Batched: scan commit messages for [F<N>] prefixes; map to issues
  echo "→ Release: $RELEASE"
  echo "→ Scanning commit messages for [F<N>] tags..."
  COMMIT_FNUMS=$(git log main..HEAD --format="%s" | grep -oE '\[F[0-9]+\]' | tr -d '[]F' | sort -u)
  if [ -z "$COMMIT_FNUMS" ]; then
    echo "ERROR: no [F<N>] tags found in commit messages on this branch." >&2
    echo "Each commit message should be: [F<N>] <subject> (#<issue>)" >&2
    exit 1
  fi
  declare -a ISSUES=()
  declare -a F_NUMS=()
  for fnum in $COMMIT_FNUMS; do
    issue=$(gh issue list --repo "$REPO" --label "F-finding" --state all --limit 100 --json number,title \
      | python3 -c "
import json, sys
data = json.load(sys.stdin)
for i in data:
    if i['title'].startswith('[F$fnum]'):
        print(i['number'])
        break
")
    if [ -z "$issue" ]; then
      echo "WARN: F$fnum referenced in commits but no matching issue on $REPO." >&2
      continue
    fi
    F_NUMS+=("$fnum")
    ISSUES+=("$issue")
    echo "  F$fnum → #$issue"
  done
  if [ ${#ISSUES[@]} -eq 0 ]; then
    echo "ERROR: no issues matched any [F<N>] tag." >&2
    exit 1
  fi
fi

# ─── 3. Verify commits + run tests ───────────────────────────────────────────

COMMITS_AHEAD=$(git rev-list --count main..HEAD)
if [ "$COMMITS_AHEAD" -eq 0 ]; then
  echo "ERROR: no commits ahead of main. Nothing to PR." >&2
  exit 1
fi
echo "→ $COMMITS_AHEAD commits ahead of main"

echo
echo "→ Running pytest..."
if ! uv run pytest tests/ -q 2>&1 | tail -5; then
  echo "ERROR: tests failed. Fix before opening PR." >&2
  exit 1
fi

# ─── 4. Push to remotes ──────────────────────────────────────────────────────

echo
echo "→ Pushing to private + origin..."
git push -u private "$BRANCH" 2>&1 | tail -3
git push origin "$BRANCH" 2>&1 | tail -3 || echo "  (origin push failed, continuing — fix manually)"

# ─── 5. Open PR ──────────────────────────────────────────────────────────────

CLOSES=$(printf "Closes #%s, " "${ISSUES[@]}" | sed 's/, $//')
PR_TITLE=$(git log main..HEAD --reverse --format="%s" | head -1)

if [ "$MODE" = "single" ]; then
  PR_BODY=$(cat <<EOF
## Summary

Implements F$F_NUM. $CLOSES.

## Commits
$(git log main..HEAD --reverse --format="- \`%h\` %s")

## Spec
See \`docs/refinement/v4_0_dashboard_fixes_spec.md\` (Finding $F_NUM, [#${ISSUES[0]}](https://github.com/$REPO/issues/${ISSUES[0]}))

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)
else
  # Batched: list each finding + its issue
  FINDINGS_TABLE=""
  for i in "${!ISSUES[@]}"; do
    fn="${F_NUMS[i]}"
    iss="${ISSUES[i]}"
    FINDINGS_TABLE+="- F$fn (#$iss): see \`docs/refinement/v4_0_dashboard_fixes_spec.md\` Finding $fn"$'\n'
  done
  PR_TITLE="$RELEASE: ${BRANCH#*/} — ${#ISSUES[@]} findings"
  PR_BODY=$(cat <<EOF
## Summary

$RELEASE batch — ${#ISSUES[@]} findings shipped together as a thematic group. $CLOSES.

## Findings
$FINDINGS_TABLE

## Commits
$(git log main..HEAD --reverse --format="- \`%h\` %s")

## Spec
See \`docs/refinement/v4_0_dashboard_fixes_spec.md\` for finding-level scope and validation.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)
fi

echo
echo "→ Opening PR on $REPO..."
PR_URL=$(gh pr create \
  --repo "$REPO" \
  --base main \
  --head "$BRANCH" \
  --title "$PR_TITLE" \
  --body "$PR_BODY" 2>&1 | grep -oE "https://github.com/[^ ]+/pull/[0-9]+" || echo "")

if [ -z "$PR_URL" ]; then
  echo "WARN: PR creation may have failed. Check manually." >&2
else
  echo "→ PR: $PR_URL"
fi

# ─── 6. Comment on each issue ────────────────────────────────────────────────

ISSUE_LIST=$(printf "#%s, " "${ISSUES[@]}" | sed 's/, $//')

for issue in "${ISSUES[@]}"; do
  if [ "$MODE" = "single" ]; then
    BODY="✅ PR opened: $PR_URL

Tests green. Branch \`$BRANCH\` ready for review.

Will auto-close on PR merge via \`Closes #$issue\`."
  else
    BODY="✅ Batched PR opened: $PR_URL

This issue is part of the $RELEASE thematic batch \`${BRANCH#*/}\` — grouped with: $ISSUE_LIST.

Tests green. Branch \`$BRANCH\` ready for review.
Will auto-close on PR merge via \`Closes #$issue\`."
  fi
  gh issue comment "$issue" --repo "$REPO" --body "$BODY" 2>&1 | tail -1 || true
done

echo
if [ "$MODE" = "single" ]; then
  echo "✅ F$F_NUM packaged. Issue #${ISSUES[0]} will auto-close on PR merge."
else
  echo "✅ $RELEASE batch packaged. ${#ISSUES[@]} issues will auto-close on PR merge: $ISSUE_LIST"
fi
echo "   Review the PR + merge when ready."

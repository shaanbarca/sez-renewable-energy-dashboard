#!/bin/bash
# Finish work on an F-finding: push branch, open PR with Closes #N, comment.
#
# Usage: scripts/finish_finding.sh
#
# What it does (assumes you're on a `f<N>/<slug>` branch with commits):
#   1. Verify branch name format and commits ahead of main
#   2. Run the test suite
#   3. Push branch to private (deploy) and origin (public mirror)
#   4. Open PR with body containing `Closes #<issue>` (auto-resolves on merge)
#   5. Comment on the issue with the PR link
#
# Stops short of merging — the user reviews the PR + decides when to land.

set -euo pipefail

REPO="shaanbarca/eez"
BRANCH=$(git branch --show-current)

# 1. Verify branch name format
if ! [[ "$BRANCH" =~ ^f([0-9]+)/(.+)$ ]]; then
  echo "ERROR: branch '$BRANCH' doesn't match expected format f<N>/<slug>." >&2
  echo "Did you forget to run scripts/start_finding.sh first?" >&2
  exit 1
fi

F_NUM="${BASH_REMATCH[1]}"

# 2. Find issue from branch — match by title prefix [F<N>]
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
  echo "ERROR: couldn't find an issue with [F$F_NUM] prefix on $REPO." >&2
  exit 1
fi

echo "→ Branch:  $BRANCH"
echo "→ Finding: F$F_NUM"
echo "→ Issue:   #$ISSUE"

# 3. Verify commits ahead of main
COMMITS_AHEAD=$(git rev-list --count main..HEAD)
if [ "$COMMITS_AHEAD" -eq 0 ]; then
  echo "ERROR: no commits ahead of main. Nothing to PR." >&2
  exit 1
fi
echo "→ $COMMITS_AHEAD commits ahead of main"

# 4. Run tests
echo
echo "→ Running pytest..."
if ! uv run pytest tests/ -q 2>&1 | tail -5; then
  echo
  echo "ERROR: tests failed. Fix before opening PR." >&2
  exit 1
fi

# 5. Push to both remotes
echo
echo "→ Pushing to private + origin..."
git push -u private "$BRANCH" 2>&1 | tail -3
git push origin "$BRANCH" 2>&1 | tail -3 || echo "  (origin push failed, continuing — fix manually)"

# 6. Open PR
PR_TITLE=$(git log main..HEAD --reverse --format="%s" | head -1)
PR_BODY=$(cat <<EOF
## Summary

Implements F$F_NUM. Closes #$ISSUE.

## Commits
$(git log main..HEAD --reverse --format="- \`%h\` %s")

## Spec
See \`docs/refinement/v4_0_dashboard_fixes_spec.md\` (Finding $F_NUM, [#$ISSUE](https://github.com/$REPO/issues/$ISSUE))

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)

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

# 7. Final issue comment
COMMENT="✅ PR opened: $PR_URL

Tests green. Branch \`$BRANCH\` ready for review.

Will auto-close this issue on PR merge via \`Closes #$ISSUE\`."

gh issue comment "$ISSUE" --repo "$REPO" --body "$COMMENT" 2>&1 | tail -3 || true

echo
echo "✅ F$F_NUM packaged. Issue #$ISSUE will auto-close when PR merges."
echo "   Review the PR + merge when ready."

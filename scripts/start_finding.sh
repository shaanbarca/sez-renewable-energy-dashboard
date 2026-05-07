#!/bin/bash
# Start work on an F-finding: create branch, post initial issue comment.
#
# Usage: scripts/start_finding.sh <issue_number>
# Example: scripts/start_finding.sh 3   # F1 / "Reframe pure solar+12hr battery"
#
# What it does:
#   1. Verify clean working tree on main
#   2. Fetch issue details via gh CLI
#   3. Derive branch name from issue title (f<N>/short-slug-from-title)
#   4. Create branch from main
#   5. Post a comment on the issue: "🚧 Branch <name> opened, work in progress"
#
# After this script runs, work normally. Every commit message on the branch
# should include [F<N>] and #<issue_num> for traceability. When done, run
# scripts/finish_finding.sh to push + open PR with `Closes #N`.

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <issue_number>" >&2
  echo "Example: $0 3   # for F1 / issue #3" >&2
  exit 1
fi

ISSUE="$1"
REPO="shaanbarca/eez"

# 1. Verify no uncommitted modifications to tracked files (untracked files are fine).
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "ERROR: working tree has uncommitted modifications to tracked files." >&2
  echo "Commit, stash, or discard them first. (Untracked files are OK.)" >&2
  git status --short --untracked-files=no >&2
  exit 1
fi

# 2. Fetch issue details
echo "→ Fetching issue #$ISSUE from $REPO..."
ISSUE_JSON=$(gh issue view "$ISSUE" --repo "$REPO" --json title,number,labels,state)
TITLE=$(echo "$ISSUE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['title'])")
STATE=$(echo "$ISSUE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['state'])")
LABELS=$(echo "$ISSUE_JSON" | python3 -c "import json,sys; print(','.join(l['name'] for l in json.load(sys.stdin)['labels']))")

if [ "$STATE" = "CLOSED" ]; then
  echo "ERROR: issue #$ISSUE is already CLOSED. Pick another." >&2
  exit 1
fi

echo "  title:  $TITLE"
echo "  labels: $LABELS"

# 3. Derive F-number from title (expect "[F<N>] ...")
F_NUM=$(echo "$TITLE" | grep -oE '^\[F[0-9]+\]' | tr -d '[]F' || echo "")
if [ -z "$F_NUM" ]; then
  echo "WARN: issue title doesn't start with [F<N>]. Branch will use issue number only." >&2
  BRANCH_PREFIX="issue-$ISSUE"
else
  BRANCH_PREFIX="f$F_NUM"
fi

# 4. Derive slug from title (lowercase, drop [F<N>], collapse whitespace, max 40 chars)
SLUG=$(echo "$TITLE" \
  | sed -E 's/^\[F[0-9]+\]\s*//' \
  | tr '[:upper:]' '[:lower:]' \
  | sed -E 's/[^a-z0-9]+/-/g' \
  | sed -E 's/^-+|-+$//g' \
  | cut -c1-40 \
  | sed -E 's/-+$//')

BRANCH="${BRANCH_PREFIX}/${SLUG}"
echo "  branch: $BRANCH"

# 5. Verify on main + create branch
CUR_BRANCH=$(git branch --show-current)
if [ "$CUR_BRANCH" != "main" ]; then
  echo "→ Switching to main first (was on $CUR_BRANCH)..."
  git checkout main
fi

# Pull latest main to avoid stale-base issue
echo "→ Updating main from origin..."
git pull --ff-only origin main 2>&1 | tail -3 || true

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "ERROR: branch $BRANCH already exists. Delete it first or pick a different issue." >&2
  exit 1
fi

git checkout -b "$BRANCH"
echo "→ Created and switched to $BRANCH"

# 6. Post initial comment on issue
COMMENT="🚧 Branch [\`$BRANCH\`](https://github.com/$REPO/tree/$BRANCH) opened, work in progress.

Started: $(date -u +"%Y-%m-%d %H:%M UTC")
Base: \`main\` @ $(git rev-parse --short HEAD~0)

Commits on this branch will reference \`[F$F_NUM]\` and \`#$ISSUE\`. PR will close this issue on merge."

echo "→ Commenting on #$ISSUE..."
gh issue comment "$ISSUE" --repo "$REPO" --body "$COMMENT" 2>&1 | tail -3

echo
echo "✅ Ready to work on F$F_NUM (#$ISSUE)."
echo "   Branch: $BRANCH"
echo "   Issue:  https://github.com/$REPO/issues/$ISSUE"
echo
echo "When done, run: scripts/finish_finding.sh"

#!/bin/bash
# Start work on F-findings: create branch, post WIP comment on each issue.
#
# Usage:
#   scripts/start_finding.sh <issue_number>
#       Single-finding mode. Branch: f<N>/<slug-from-title>
#       Example: scripts/start_finding.sh 6   # F4 / lifecycle correction
#
#   scripts/start_finding.sh <theme-slug> <issue_num> <issue_num> ...
#       Batched mode. Branch: v<release>/<theme-slug>
#       Example: scripts/start_finding.sh carbon-emissions 6 11
#                # → branch v4.0.5/carbon-emissions, F4 (#6) + F9 (#11)
#
# What it does:
#   1. Verify clean tree on main (untracked files OK)
#   2. Fetch issue titles via gh
#   3. Single mode: derive slug from title, branch = f<N>/<slug>
#      Batched: caller-supplied slug, release prefix from issue labels
#   4. Pull main fast-forward, create branch
#   5. Post a "🚧 work in progress" comment on each included issue
#
# After this runs, work normally. Each commit message: [F<N>] <subject> (#<NN>).
# When done, run scripts/finish_finding.sh — it auto-detects single vs batched.

set -euo pipefail

REPO="shaanbarca/eez"

# ─── Argument parsing ────────────────────────────────────────────────────────

print_usage() {
  cat <<EOF >&2
Usage:
  $0 <issue_num>                                      # single mode
  $0 <theme-slug> <issue_num1> <issue_num2> ...       # batched mode
EOF
}

if [ $# -lt 1 ]; then
  print_usage
  exit 1
fi

if [ $# -eq 1 ] && [[ "$1" =~ ^[0-9]+$ ]]; then
  MODE=single
  ISSUES=("$1")
elif [ $# -ge 2 ] && [[ ! "$1" =~ ^[0-9]+$ ]]; then
  MODE=batch
  SLUG="$1"
  shift
  ISSUES=("$@")
  for i in "${ISSUES[@]}"; do
    if ! [[ "$i" =~ ^[0-9]+$ ]]; then
      echo "ERROR: '$i' is not a numeric issue number." >&2
      print_usage
      exit 1
    fi
  done
else
  echo "ERROR: ambiguous arguments." >&2
  print_usage
  exit 1
fi

# ─── 1. Verify clean tree (tracked files only) ───────────────────────────────

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "ERROR: working tree has uncommitted modifications to tracked files." >&2
  echo "Commit, stash, or discard them first. (Untracked files are OK.)" >&2
  git status --short --untracked-files=no >&2
  exit 1
fi

# ─── 2. Fetch each issue + collect metadata ──────────────────────────────────

declare -a ISSUE_TITLES=()
declare -a ISSUE_F_NUMS=()
RELEASE_LABEL=""

for issue in "${ISSUES[@]}"; do
  echo "→ Fetching issue #$issue from $REPO..."
  ISSUE_JSON=$(gh issue view "$issue" --repo "$REPO" --json title,number,labels,state)
  TITLE=$(echo "$ISSUE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['title'])")
  STATE=$(echo "$ISSUE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['state'])")
  LABELS=$(echo "$ISSUE_JSON" | python3 -c "import json,sys; print(','.join(l['name'] for l in json.load(sys.stdin)['labels']))")

  if [ "$STATE" = "CLOSED" ]; then
    echo "ERROR: issue #$issue is already CLOSED. Pick another." >&2
    exit 1
  fi

  # Derive F-number from "[F<N>] ..."
  F_NUM=$(echo "$TITLE" | grep -oE '^\[F[0-9]+\]' | tr -d '[]F' || echo "")

  # Detect release label (v4.0.5, v4.1a, etc.). All issues in a batch must agree.
  ISSUE_RELEASE=$(echo "$LABELS" | tr ',' '\n' | grep -E '^v[0-9]+(\.[0-9a-z]+)+$' | head -1)
  if [ -z "$ISSUE_RELEASE" ]; then
    echo "WARN: issue #$issue has no release label (v4.0.5 / v4.1a / etc.)." >&2
  else
    if [ -z "$RELEASE_LABEL" ]; then
      RELEASE_LABEL="$ISSUE_RELEASE"
    elif [ "$RELEASE_LABEL" != "$ISSUE_RELEASE" ]; then
      echo "ERROR: issue #$issue has release label '$ISSUE_RELEASE' but other issues in batch are '$RELEASE_LABEL'." >&2
      echo "Don't mix releases in one batch." >&2
      exit 1
    fi
  fi

  echo "  #$issue: $TITLE [F${F_NUM:-?}, release=${ISSUE_RELEASE:-none}]"
  ISSUE_TITLES+=("$TITLE")
  ISSUE_F_NUMS+=("$F_NUM")
done

# ─── 3. Determine branch name ────────────────────────────────────────────────

if [ "$MODE" = "single" ]; then
  TITLE="${ISSUE_TITLES[0]}"
  F_NUM="${ISSUE_F_NUMS[0]}"
  if [ -z "$F_NUM" ]; then
    echo "WARN: issue #${ISSUES[0]} title doesn't start with [F<N>]; using issue-N prefix." >&2
    BRANCH_PREFIX="issue-${ISSUES[0]}"
  else
    BRANCH_PREFIX="f$F_NUM"
  fi
  SLUG=$(echo "$TITLE" \
    | sed -E 's/^\[F[0-9]+\]\s*//' \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g' \
    | sed -E 's/^-+|-+$//g' \
    | cut -c1-40 \
    | sed -E 's/-+$//')
  BRANCH="${BRANCH_PREFIX}/${SLUG}"
else
  # Batched: v<release>/<theme-slug>. Slug already provided, validated below.
  if [ -z "$RELEASE_LABEL" ]; then
    echo "ERROR: no release label found across the issues. Can't determine branch prefix." >&2
    exit 1
  fi
  # Sanitize slug
  SLUG=$(echo "$SLUG" \
    | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9]+/-/g' \
    | sed -E 's/^-+|-+$//g')
  BRANCH="${RELEASE_LABEL}/${SLUG}"
fi

echo "→ Branch: $BRANCH"

# ─── 4. Pull main + create branch ────────────────────────────────────────────

CUR_BRANCH=$(git branch --show-current)
if [ "$CUR_BRANCH" != "main" ]; then
  echo "→ Switching to main first (was on $CUR_BRANCH)..."
  git checkout main
fi

echo "→ Updating main from origin..."
git pull --ff-only origin main 2>&1 | tail -3 || true

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  echo "ERROR: branch $BRANCH already exists. Delete it first or pick a different slug/issue." >&2
  exit 1
fi

git checkout -b "$BRANCH"
echo "→ Created and switched to $BRANCH"

# ─── 5. Comment on each issue ────────────────────────────────────────────────

BASE_SHA=$(git rev-parse --short HEAD)
NOW=$(date -u +"%Y-%m-%d %H:%M UTC")

if [ "$MODE" = "single" ]; then
  COMMENT="🚧 Branch [\`$BRANCH\`](https://github.com/$REPO/tree/$BRANCH) opened, work in progress.

Started: $NOW
Base: \`main\` @ $BASE_SHA

Commits will reference \`[F${ISSUE_F_NUMS[0]}]\` and \`#${ISSUES[0]}\`. PR will close this issue on merge."
  echo "→ Commenting on #${ISSUES[0]}..."
  gh issue comment "${ISSUES[0]}" --repo "$REPO" --body "$COMMENT" 2>&1 | tail -1
else
  # Batched: same comment posted on each issue, naming the batch
  ISSUE_LIST=$(printf "#%s, " "${ISSUES[@]}" | sed 's/, $//')
  COMMENT="🚧 Batched into [\`$BRANCH\`](https://github.com/$REPO/tree/$BRANCH), work in progress.

This issue groups with: $ISSUE_LIST
Started: $NOW
Base: \`main\` @ $BASE_SHA

The PR for this branch will close all grouped issues on merge via \`Closes\` syntax."
  for issue in "${ISSUES[@]}"; do
    echo "→ Commenting on #$issue..."
    gh issue comment "$issue" --repo "$REPO" --body "$COMMENT" 2>&1 | tail -1
  done
fi

echo
echo "✅ Ready to work on $BRANCH"
if [ "$MODE" = "single" ]; then
  echo "   F${ISSUE_F_NUMS[0]} (#${ISSUES[0]}): https://github.com/$REPO/issues/${ISSUES[0]}"
else
  echo "   Batch: ${#ISSUES[@]} findings — ${ISSUE_LIST}"
fi
echo
echo "When done, run: scripts/finish_finding.sh"

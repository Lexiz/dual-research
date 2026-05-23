#!/usr/bin/env bash
# Sweeps stale `spec/*` branches from origin — a backstop to the verified
# per-cycle delete added in /dev-next step 19 by spec 0201 §2.1.
#
# The per-cycle verified delete is the primary mechanism: every /dev-next
# cycle now confirms `gh pr merge --delete-branch` actually removed the
# branch from both sides, with one explicit retry. This sweeper exists for
# the rare case where even the retry loses to a race, plus a recovery path
# for any historical drift.
#
# Safety:
# - Lists `spec/*` branches on origin via `git ls-remote --heads`.
# - For each, queries the PR state via `gh pr view --json state,mergedAt`.
# - Deletes from origin ONLY when `state == "MERGED"`.
# - Branches with state OPEN, CLOSED-not-merged, or no PR at all are
#   reported and kept, and contribute to a non-zero exit code so an
#   operator notices.
#
# Idempotent. Safe to re-run.
#
# Usage:
#   scripts/sweep_stale_branches.sh
#   scripts/sweep_stale_branches.sh --remote NAME      # default: origin
#
# Exit code: count of branches kept-but-not-merged (0 = clean origin).
set -uo pipefail

REMOTE="origin"

while (( $# > 0 )); do
  case "$1" in
    --remote)  REMOTE="${2:?--remote requires a value}"; shift 2 ;;
    *)         echo "sweep: unknown argument: $1" >&2; exit 1 ;;
  esac
done

if ! refs="$(git ls-remote --heads "$REMOTE" 'spec/*' 2>/dev/null)"; then
  echo "sweep: git ls-remote failed for remote=$REMOTE" >&2
  exit 1
fi

# Extract branch names from refs (lines look like "<sha>\trefs/heads/spec/...").
mapfile -t branches < <(printf '%s\n' "$refs" | awk -F'refs/heads/' 'NF==2 {print $2}')

if (( ${#branches[@]} == 0 )); then
  echo "sweep: no stale spec/* branches on $REMOTE"
  exit 0
fi

kept_count=0
for branch in "${branches[@]}"; do
  if ! pr_json="$(gh pr view "$branch" --json state,mergedAt 2>/dev/null)"; then
    echo "kept $branch (no PR)"
    kept_count=$((kept_count + 1))
    continue
  fi

  state="$(printf '%s' "$pr_json" | jq -r '.state // ""')"
  merged_at="$(printf '%s' "$pr_json" | jq -r '.mergedAt // ""')"

  if [[ "$state" == "MERGED" ]]; then
    merged_date="${merged_at:0:10}"
    if git push "$REMOTE" --delete "$branch" >/dev/null 2>&1; then
      echo "swept $branch (merged $merged_date)"
    else
      echo "kept $branch (merged $merged_date — delete failed)" >&2
      kept_count=$((kept_count + 1))
    fi
  else
    echo "kept $branch (state=$state)"
    kept_count=$((kept_count + 1))
  fi
done

exit $kept_count

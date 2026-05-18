#!/usr/bin/env bash
# scripts/setup-stable-worktree.sh
#
# Creates a stable worktree of dual-research at ~/dual-research-stable
# (or the path given as $1) so the user can run CLI invocations in
# parallel with active orchestrator / feature-branch work in the
# primary checkout. See CONTRIBUTING.md for full context.

set -euo pipefail

# Locate primary checkout
if ! REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  echo "error: not inside a git repository. Run this from inside the dual-research repo." >&2
  exit 1
fi

STABLE_PATH="${1:-${HOME}/dual-research-stable}"

cd "$REPO_ROOT"

# Ensure stable branch exists
if ! git show-ref --verify --quiet refs/heads/stable; then
  git branch stable main
  echo "Created 'stable' branch at main ($(git rev-parse --short main))."
else
  echo "'stable' branch already exists at $(git rev-parse --short stable)."
fi

# Ensure worktree exists
if [ -d "$STABLE_PATH" ]; then
  if git worktree list --porcelain | grep -q "^worktree $STABLE_PATH\$"; then
    echo "Worktree already registered at $STABLE_PATH — no change."
  else
    echo "error: $STABLE_PATH exists but is not a registered worktree. Remove it or pick a different path." >&2
    exit 1
  fi
else
  git worktree add "$STABLE_PATH" stable
  echo "Worktree created at $STABLE_PATH on branch 'stable'."
fi

# Sync dependencies inside the worktree
(cd "$STABLE_PATH" && uv sync --quiet)
echo "Dependencies synced inside worktree."

cat <<EOF

Stable worktree ready at: $STABLE_PATH

Run dual-research in parallel with active development:
  cd $STABLE_PATH
  uv run dual-research --notion <url>

Roll forward to the latest shipped main:
  cd $STABLE_PATH
  git fetch origin
  git merge --ff-only origin/main
  uv sync --quiet
EOF

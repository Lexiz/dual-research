#!/usr/bin/env bash
# scripts/run-queue-v2.sh
#
# Queue v2 — single entrypoint for the 13-spec design-system rebuild
# (specs 0092 → 0104). Validates preconditions, seeds queue/state.json,
# launches the dashboard, and prints the URL the operator can monitor.
#
# Per the design, the queue is exercised in a separate Claude Code
# session — this script is what an operator runs from the terminal to
# kick that session off. It does NOT itself drive the lifecycle; it
# just stages everything and tells the operator where to point their
# browser.
#
# Exit codes
#   0  — preconditions OK, dashboard up
#   2  — working tree dirty / wrong branch
#   3  — one of the 13 spec files missing on the working main
#   4  — design-system briefing bundle missing
#   5  — queue scripts not importable
#
# Re-run safety: if a previous queue run is mid-flight, state.json is
# preserved and the dashboard resumes where it left off. To start
# fresh, delete queue/state.json and queue/runs/ manually.

set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/Users/alexlisitzky/dual-research}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8089}"
DASHBOARD_URL="http://127.0.0.1:${DASHBOARD_PORT}/"
SPECS=(0092 0093 0094 0095 0096 0097 0098 0099 0100 0101 0102 0103 0104)

red()    { printf "\033[31m%s\033[0m\n" "$*"; }
green()  { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
blue()   { printf "\033[34m%s\033[0m\n" "$*"; }
dim()    { printf "\033[2m%s\033[0m\n" "$*"; }

cd "$REPO_ROOT"

# 1 · Working tree on main + clean.
current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$current_branch" != "main" ]]; then
  red "✗ current branch is '$current_branch' — switch to main before running the queue"
  dim   "   git checkout main && git pull --ff-only"
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  red "✗ working tree is dirty — commit or stash before running the queue"
  git status --short
  exit 2
fi
green "✓ working tree clean on main ($(git rev-parse --short HEAD))"

# 2 · Spec files exist on the working main.
missing_specs=()
for n in "${SPECS[@]}"; do
  if ! ls "specs/${n}-"*.md > /dev/null 2>&1; then
    missing_specs+=("$n")
  fi
done
if (( ${#missing_specs[@]} > 0 )); then
  red "✗ spec file(s) missing on main: ${missing_specs[*]}"
  dim   "   the specs-v2-draft branch needs to land first (PR #?)"
  exit 3
fi
green "✓ all 13 spec files present"

# 3 · Briefing bundle present (read by Step 5 Verify).
briefing_root="docs/design-system-v2"
required=(
  "${briefing_root}/README.md"
  "${briefing_root}/notion-issues/ISSUES.md"
  "${briefing_root}/assets/Design System v2.html"
)
missing=()
for f in "${required[@]}"; do
  if [[ ! -f "$f" ]]; then
    missing+=("$f")
  fi
done
if (( ${#missing[@]} > 0 )); then
  red "✗ briefing bundle files missing:"
  for f in "${missing[@]}"; do
    dim "   $f"
  done
  dim   "   the design-system-v2-briefing branch needs to land first (PR #95)"
  exit 4
fi
# Spot-check screenshot reference set: 17 issues × at least one PNG each.
shots_dir="${briefing_root}/notion-issues/screenshots"
shot_count="$(find "$shots_dir" -maxdepth 1 -name "*.png" 2>/dev/null | wc -l | tr -d ' ')"
if (( shot_count < 17 )); then
  yellow "⚠ only $shot_count reference screenshots under $shots_dir (expected ≥17)"
else
  green "✓ briefing bundle present ($shot_count reference screenshots)"
fi

# 4 · Queue package importable.
if ! uv run python -c "from dual_research.queue_v2 import cli, state, timings" 2>/dev/null; then
  red "✗ queue v2 package not importable — try 'uv sync'"
  exit 5
fi
green "✓ queue v2 package importable"

# 5 · Initialise / resume queue state.
if [[ -f queue/state.json ]]; then
  yellow "ℹ queue/state.json exists — resuming previous run"
  uv run python -m dual_research.queue_v2.cli status > /tmp/queue-v2-status.json
  # grep returns 1 when no active spec is present; absorb so set -o pipefail
  # doesn't kill the script during a normal "queue staged but idle" run.
  active="$(grep -o '"spec": "[^"]*"' /tmp/queue-v2-status.json 2>/dev/null | head -1 | cut -d'"' -f4 || true)"
  if [[ -n "$active" ]]; then
    yellow "  in-flight spec: $active"
  fi
else
  uv run python -m dual_research.queue_v2.cli init "${SPECS[@]}" > /dev/null
  green "✓ queue/state.json seeded with 13 specs (${SPECS[0]} → ${SPECS[-1]})"
fi

# 6 · Launch the dashboard (background; log to queue/dashboard.log).
mkdir -p queue
if lsof -ti:"$DASHBOARD_PORT" > /dev/null 2>&1; then
  yellow "ℹ port $DASHBOARD_PORT already in use — assuming the dashboard is running"
else
  nohup uv run python -m dual_research.queue_v2.cli dashboard \
    >> queue/dashboard.log 2>&1 &
  echo $! > queue/dashboard.pid
  # Wait up to 5s for the server to bind the port.
  for _ in 1 2 3 4 5; do
    if lsof -ti:"$DASHBOARD_PORT" > /dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if ! lsof -ti:"$DASHBOARD_PORT" > /dev/null 2>&1; then
    red "✗ dashboard failed to bind port $DASHBOARD_PORT — check queue/dashboard.log"
    exit 5
  fi
  green "✓ dashboard up (pid $(cat queue/dashboard.pid))"
fi

# 7 · Print the operator's monitoring URL + next-step prompt.
echo
blue "============================================================"
blue "  queue v2 ready — dashboard at ${DASHBOARD_URL}"
blue "============================================================"
echo
cat <<EOF
The queue is staged but NOT firing the first spec from this script.
Start the queue from a fresh Claude Code session — paste:

  Resume dual-research queue v2. The dashboard is live at
  ${DASHBOARD_URL}. State is at queue/state.json. Begin with the
  next spec returned by:

      uv run python -m dual_research.queue_v2.cli next

  For each spec, run the 8-step lifecycle:

      uv run python -m dual_research.queue_v2.cli read <NNNN>
      uv run python -m dual_research.queue_v2.cli reason <NNNN>
      uv run python -m dual_research.queue_v2.cli rewrite-skip <NNNN>   # OR rewrite-complete
      uv run python -m dual_research.queue_v2.cli implement-begin <NNNN>
        ... apply edits in the working tree ...
      uv run python -m dual_research.queue_v2.cli implement-complete <NNNN> --diff "+N -M (K files)"
      uv run python -m dual_research.queue_v2.cli verify-begin <NNNN>
        ... use preview_resize/preview_screenshot per planned shot ...
      uv run python -m dual_research.queue_v2.cli verify-finalize <NNNN>
      uv run python -m dual_research.queue_v2.cli pr-push <NNNN> --branch <name>
      uv run python -m dual_research.queue_v2.cli pr-open <NNNN> --branch <name>
      uv run python -m dual_research.queue_v2.cli pr-complete <NNNN> --url <url>
      uv run python -m dual_research.queue_v2.cli deploy-wait-ci <NNNN> --url <url>
      uv run python -m dual_research.queue_v2.cli deploy-merge <NNNN> --url <url> --target-version X.Y.Z
      uv run python -m dual_research.queue_v2.cli handover <NNNN> --next-spec <NNNN+1>

  Read docs/queue-v2/RUNBOOK.md for the full operator runbook
  (abort / resume / fail-and-retry).

EOF

green "Done."

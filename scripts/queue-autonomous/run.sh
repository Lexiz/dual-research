#!/usr/bin/env bash
# scripts/queue-autonomous/run.sh
#
# Autonomous queue v2 driver. Spawns a fresh `claude --print` session
# per spec; each session drives that spec through all 8 steps
# (Read → Reason → Rewrite → Implement → Verify → PR → Deploy →
# Handover). The wrapper loops over the remaining queue, never pauses,
# and never asks the operator a question.
#
# When to use:
#   - You want the full queue (or its remainder) shipped end-to-end
#     while you do something else.
#
# When NOT to use:
#   - You're picking up a single spec by hand. Drive via the per-step
#     CLI instead (see docs/queue-v2/RUNBOOK.md).
#   - You want to review each spec before merge. The wrapper merges
#     every PR that passes its own Step 5 Verify; there is no human
#     gate between merge and fly deploy.
#
# Side effects:
#   - Pushes spec branches to origin
#   - Opens GitHub PRs with `gh`
#   - Squash-merges PRs to main via `gh pr merge --admin`
#   - Runs `fly deploy` after each merge
#   - Writes screenshots under queue/runs/<NNNN>/screenshots/
#   - Writes handovers under handoffs/<date>-spec-<NNNN>-<slug>.md
#
# The dashboard at http://127.0.0.1:8089/ is left running so the
# user can watch progress.

set -euo pipefail

REPO="${REPO:-/Users/alexlisitzky/dual-research}"
cd "$REPO"

POLICY_FILE="$REPO/scripts/queue-autonomous/policy.md"
PROMPT_SH="$REPO/scripts/queue-autonomous/prompt.sh"
LOG_ROOT="$REPO/queue/autonomous-logs"
mkdir -p "$LOG_ROOT"

# Tools the inner session is permitted to use without prompt.
# --dangerously-skip-permissions is what actually disables the permission
# system; --allowedTools is belt+braces for sanity.
ALLOWED_TOOLS=(
  "Bash"
  "Read" "Edit" "Write"
  "Grep" "Glob"
  "WebFetch" "WebSearch"
  "TaskCreate" "TaskUpdate" "TaskList" "TaskGet"
  "mcp__Claude_Preview__*"
)

# Model. Opus 4.7 is the strongest available; the inner sessions need
# to reason about CSS, contradictions, and multi-step lifecycles.
MODEL="${MODEL:-opus}"

red()    { printf "\033[31m%s\033[0m\n" "$*"; }
green()  { printf "\033[32m%s\033[0m\n" "$*"; }
yellow() { printf "\033[33m%s\033[0m\n" "$*"; }
blue()   { printf "\033[34m%s\033[0m\n" "$*"; }
dim()    { printf "\033[2m%s\033[0m\n" "$*"; }

trap 'red "✗ wrapper aborted"; exit 1' INT

# 1. Ensure repo preconditions + dashboard up.
#    The existing run-queue-v2.sh checks working tree clean + on main,
#    verifies the spec/briefing files are present, and starts the
#    dashboard. Idempotent.
green "▶ preflight via scripts/run-queue-v2.sh"
"$REPO/scripts/run-queue-v2.sh" >/dev/null

# 2. Loop over remaining queue. The CLI's `next` subcommand returns
#    the next spec; exit code 1 = queue empty.
loop_idx=0
while true; do
  loop_idx=$((loop_idx + 1))
  NEXT=$(uv run python -m dual_research.queue_v2.cli next 2>/dev/null || true)
  if [[ -z "${NEXT:-}" ]]; then
    green "✓ queue empty — all specs delivered + deployed"
    exit 0
  fi

  echo
  blue "════════════════════════════════════════════════════════════"
  blue "  Iteration $loop_idx · spec $NEXT · fresh claude session"
  blue "════════════════════════════════════════════════════════════"
  dim  "  dashboard: http://127.0.0.1:8089/"
  dim  "  policy:    $POLICY_FILE"
  dim  "  log:       $LOG_ROOT/spec-$NEXT.log"
  echo

  # Record the queue's view of state BEFORE the session, so we can
  # detect whether the session actually moved the spec forward.
  STATE_BEFORE=$(uv run python -m dual_research.queue_v2.cli status 2>/dev/null \
                 | grep -E '"spec"|"failure"' | head -2 || true)

  # Build the per-spec prompt.
  PROMPT=$("$PROMPT_SH" "$NEXT")

  # Spawn the session. --print = non-interactive one-shot.
  # --dangerously-skip-permissions = no human in the loop.
  # --append-system-prompt = load the autonomous policy.
  # --no-session-persistence = each spec is a fresh transcript.
  # --max-budget-usd = belt+braces against runaway spend per spec.
  LOG="$LOG_ROOT/spec-$NEXT.log"
  set +e
  claude --print \
    --model "$MODEL" \
    --dangerously-skip-permissions \
    --append-system-prompt "$(cat "$POLICY_FILE")" \
    --allowedTools "${ALLOWED_TOOLS[@]}" \
    --no-session-persistence \
    --max-budget-usd "${MAX_BUDGET_USD_PER_SPEC:-20}" \
    --verbose \
    "$PROMPT" 2>&1 | tee "$LOG"
  RC=$?
  set -e

  # 3. Detect whether the spec actually moved. Two checks:
  #    a) The CLI's `next` subcommand should now return a DIFFERENT
  #       spec (or empty) — i.e., this spec is no longer at head.
  #    b) The state's `failure` field should be null.
  POST_NEXT=$(uv run python -m dual_research.queue_v2.cli next 2>/dev/null || true)
  FAILURE=$(uv run python -m dual_research.queue_v2.cli status 2>/dev/null \
            | python3 -c "import json,sys; print(json.load(sys.stdin).get('failure'))")

  if [[ "$POST_NEXT" == "$NEXT" ]]; then
    red "✗ spec $NEXT did not advance (still at head of queue). Halting."
    red "  See $LOG for the session transcript."
    if [[ "$FAILURE" != "None" && -n "$FAILURE" ]]; then
      red "  Failure detail: $FAILURE"
    fi
    exit 2
  fi
  if [[ "$FAILURE" != "None" && -n "$FAILURE" ]]; then
    red "✗ spec $NEXT reported a failure in state.json. Halting."
    red "  Failure detail: $FAILURE"
    exit 3
  fi

  green "✓ spec $NEXT delivered + deployed. Loop continues."
done

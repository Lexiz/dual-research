#!/usr/bin/env bash
# Destroys Fly machines whose metadata carries fly_bluegreen_deployment_tag:
# "safe_to_destroy". Fly sets this tag itself on machines its orchestrator
# has already decided are eligible for destroy — so this script is safe by
# construction: it can never hit a live green, only stale blues Fly itself
# marked for cleanup.
#
# Spec 0162 — added to work around an upstream Fly orchestrator bug where
# the destroy-lease for blues fails to acquire after a bluegreen rollout
# (handoffs/2026-05-22-spec-0160 and 0161 documented 2/2 occurrences).
#
# Diagnostic fallback (also spec 0162): if the filter finds 0 stale blues
# but the live cluster has more than --expected-count machines, dump the
# full metadata of every machine to stderr. This captures evidence the
# next time the bug fires with a different tag scheme than we expect, so
# we can correct the filter on a follow-up without manual triage.
#
# Usage:
#   scripts/sweep_stale_blues.sh
#   scripts/sweep_stale_blues.sh --app NAME
#   scripts/sweep_stale_blues.sh --app NAME --expected-count 2
#   scripts/sweep_stale_blues.sh --input fixture.json   # testing only
#
# Exit code is always 0 — best-effort hygiene. The deploy that precedes
# this sweep has already determined success; the sweep must never fail
# the caller. Failures are logged to stderr.
set -uo pipefail

APP="dual-research-alex"
EXPECTED_COUNT=2
INPUT_FILE=""

while (( $# > 0 )); do
  case "$1" in
    --app)             APP="${2:?--app requires a value}"; shift 2 ;;
    --expected-count)  EXPECTED_COUNT="${2:?--expected-count requires a value}"; shift 2 ;;
    --input)           INPUT_FILE="${2:?--input requires a value}"; shift 2 ;;
    *)                 echo "sweep: unknown argument: $1" >&2; exit 0 ;;
  esac
done

# Read machine state — from --input file when testing, otherwise call Fly.
if [[ -n "$INPUT_FILE" ]]; then
  if ! machines_json="$(cat "$INPUT_FILE" 2>/dev/null)"; then
    echo "sweep: --input file not readable: $INPUT_FILE" >&2
    exit 0
  fi
else
  if ! machines_json="$(fly machine list --app "$APP" --json 2>/dev/null)"; then
    echo "sweep: fly machine list failed for app=$APP" >&2
    exit 0
  fi
fi

# Fly tags machines its orchestrator has decided to destroy with
# metadata.fly_bluegreen_deployment_tag == "safe_to_destroy". That tag is
# Fly's own verdict; we never set it. Selecting on it cannot hit a live
# green by construction.
JQ_FILTER='.[] | select(.config.metadata.fly_bluegreen_deployment_tag == "safe_to_destroy") | .id'

mapfile -t stale < <(printf '%s' "$machines_json" | jq -r "$JQ_FILTER")
total="${#stale[@]}"
machine_count="$(printf '%s' "$machines_json" | jq -r 'length' 2>/dev/null || echo "?")"

if (( total == 0 )); then
  echo "sweep: no stale blues on $APP"

  # Diagnostic: if there's more in the cluster than we expect AND no stale
  # blues were found, the filter is probably looking at the wrong field /
  # value. Dump full metadata so the next handoff captures evidence we
  # can use to correct the filter.
  if [[ "$machine_count" =~ ^[0-9]+$ ]] && (( machine_count > EXPECTED_COUNT )); then
    echo "sweep: cluster has $machine_count machines (expected $EXPECTED_COUNT) — dumping metadata for filter diagnosis:" >&2
    printf '%s' "$machines_json" \
      | jq '[.[] | {id, name, state, metadata: .config.metadata}]' >&2
  fi
  exit 0
fi

failed=0
if [[ -z "$INPUT_FILE" ]]; then
  for id in "${stale[@]}"; do
    if ! fly machine destroy --app "$APP" --force "$id" >/dev/null 2>&1; then
      failed=$((failed + 1))
      echo "sweep: destroy failed for $id" >&2
    fi
  done
fi

destroyed=$(( total - failed ))
echo "sweep: destroyed $destroyed/$total stale blues on $APP (failed=$failed)"
exit 0

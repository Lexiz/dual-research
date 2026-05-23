#!/usr/bin/env bash
# Sweeps Fly machines that the live cluster shouldn't be carrying — either
# stale blues from a bluegreen rollout the destroy-lease failed to clean
# up (the historical case, spec 0162), or any machine not on the current
# release image (the spec-0193 image-based fallback, which is the primary
# recovery path under rolling — see spec 0200).
#
# The tag-based primary filter still selects on
# fly_bluegreen_deployment_tag == "safe_to_destroy". Under bluegreen Fly
# sets this tag on machines its orchestrator has already decided are
# eligible for destroy — so the filter is safe by construction: it can
# never hit a live green, only stale blues Fly itself marked for cleanup.
# Under rolling (spec 0200) the tag is no longer set on new deploys, so
# this filter finds zero candidates on a healthy rolling cluster — that
# is the expected/healthy state, and the script logs
# `sweep: no stale blues on …` and exits 0.
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
# Spec 0193 — image-based fallback filter. When the spec-0162 tag filter
# finds zero candidates AND the cluster is oversize, query Fly's current
# release-image and destroy machines NOT on that image. Safe by
# construction in the same sense as the tag-based filter: Fly's release-
# history is authoritative; a machine on a previous release was
# definitionally superseded. Four gates must hold before any fallback
# destroy fires (see §2.1 of the spec for the cascade) — the strictest
# being that AT LEAST ONE machine must be on the current release image,
# so the fallback can never zero the cluster. Under spec 0200 (rolling)
# this image-based fallback is the *primary* mechanism for cleaning up
# any machine the rolling replace didn't fully cycle; the tag-based
# primary stays for backward compatibility with any pre-0200 zombies.
#
# Usage:
#   scripts/sweep_stale_blues.sh
#   scripts/sweep_stale_blues.sh --app NAME
#   scripts/sweep_stale_blues.sh --app NAME --expected-count 2
#   scripts/sweep_stale_blues.sh --input fixture.json   # testing only
#                                                         (sibling
#                                                         fixture.release.json
#                                                         supplies the
#                                                         spec-0193 current
#                                                         release image)
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

# Spec 0193 — image-based fallback filter. Used only when the tag filter
# above found nothing AND the cluster is oversize. Selects machines whose
# `.config.image` does not equal the current release image (supplied at
# runtime via the `--arg CURRENT_IMG …` jq invocation).
JQ_FALLBACK_FILTER='.[] | select(.config.image != $CURRENT_IMG) | .id'

# Spec 0193 — return the image string Fly currently considers the live
# release, or empty on failure. In live mode this calls `fly releases
# --app "$APP" --json` and picks the most recent release whose status is
# "running" (the active rollout) or "complete" (the last successful
# release). Fly's JSON shape uses PascalCase keys (`Status`, `ImageRef`,
# `CreatedAt`) as of v0.4.54.
# In test mode (--input given) it reads a sibling `.release.json` file
# next to the input fixture; the fixture must carry `{"image_ref": "…"}`
# at top level (lowercase, since fixtures are hand-authored).
get_current_release_image() {
  if [[ -n "$INPUT_FILE" ]]; then
    local release_file="${INPUT_FILE%.json}.release.json"
    if [[ -f "$release_file" ]]; then
      jq -r '.image_ref // empty' "$release_file" 2>/dev/null
    fi
  else
    fly releases --app "$APP" --json 2>/dev/null | \
      jq -r '[.[] | select(.Status == "running" or .Status == "complete")] | sort_by(.CreatedAt) | last | .ImageRef // empty' 2>/dev/null
  fi
}

mapfile -t stale < <(printf '%s' "$machines_json" | jq -r "$JQ_FILTER")
total="${#stale[@]}"
machine_count="$(printf '%s' "$machines_json" | jq -r 'length' 2>/dev/null || echo "?")"

if (( total == 0 )); then
  echo "sweep: no stale blues on $APP"

  # When there's more in the cluster than we expect AND no `safe_to_destroy`
  # tagged machines were found, fall through to the spec-0193 image-based
  # filter. Gated behind a cascade so the fallback can never destroy the
  # only live green:
  #   1. Tag-based filter returned 0 (already checked).
  #   2. Cluster oversize per --expected-count.
  #   3. get_current_release_image returned a non-empty string.
  #   4. At least one machine in the cluster is on that current image
  #      (so destroying the others can never zero the cluster).
  if [[ "$machine_count" =~ ^[0-9]+$ ]] && (( machine_count > EXPECTED_COUNT )); then
    echo "sweep: cluster has $machine_count machines (expected $EXPECTED_COUNT) — checking image-release fallback filter (spec 0193)" >&2

    current_image="$(get_current_release_image)"
    if [[ -z "$current_image" ]]; then
      echo "sweep: spec-0193 fallback skipped — could not determine current release image" >&2
      printf '%s' "$machines_json" \
        | jq '[.[] | {id, name, state, image: .config.image, metadata: .config.metadata}]' >&2
      exit 0
    fi

    # Gate 4 — refuse if no machine matches the current image. That
    # would mean destroying ALL machines (no live green present), which
    # is never the right answer; dump for triage instead.
    green_count="$(printf '%s' "$machines_json" \
      | jq --arg CURRENT_IMG "$current_image" '[.[] | select(.config.image == $CURRENT_IMG)] | length')"
    if (( green_count == 0 )); then
      echo "sweep: spec-0193 fallback refused — zero machines on current image ($current_image); something is wrong, dumping for triage" >&2
      printf '%s' "$machines_json" \
        | jq '[.[] | {id, name, state, image: .config.image, metadata: .config.metadata}]' >&2
      exit 0
    fi

    mapfile -t fallback_stale < <(printf '%s' "$machines_json" \
      | jq -r --arg CURRENT_IMG "$current_image" "$JQ_FALLBACK_FILTER")
    fallback_total="${#fallback_stale[@]}"
    if (( fallback_total == 0 )); then
      echo "sweep: spec-0193 fallback found no off-image machines either; dumping metadata for triage" >&2
      printf '%s' "$machines_json" \
        | jq '[.[] | {id, name, state, image: .config.image, metadata: .config.metadata}]' >&2
      exit 0
    fi

    echo "sweep: spec-0193 fallback destroying $fallback_total machine(s) not on current image ($current_image)" >&2
    fallback_failed=0
    if [[ -z "$INPUT_FILE" ]]; then
      for id in "${fallback_stale[@]}"; do
        if ! fly machine destroy --app "$APP" --force "$id" >/dev/null 2>&1; then
          fallback_failed=$((fallback_failed + 1))
          echo "sweep: fallback destroy failed for $id" >&2
        fi
      done
    fi
    fallback_destroyed=$(( fallback_total - fallback_failed ))
    echo "sweep: fallback destroyed $fallback_destroyed/$fallback_total stale machines on $APP (failed=$fallback_failed)"
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

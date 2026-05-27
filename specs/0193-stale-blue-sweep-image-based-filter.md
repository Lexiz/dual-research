---
kind: dev
spec: "0193"
slug: stale-blue-sweep-image-based-filter
title: Stale-blue sweep filter — catch machines on an out-of-release image
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.39.0
status: deployed
depends_on: ["0162"]
complexity: S
created: 2026-05-23
queued_at: "2026-05-23T00:00:00Z"
started_at: "2026-05-23T16:28:39Z"
merged_at: "2026-05-23T16:34:25Z"
deployed_at: "2026-05-23T16:39:52Z"
pr: "https://github.com/Lexiz/dual-research/pull/222"
handover: "handoffs/2026-05-23-spec-0193-stale-blue-sweep-image-based-filter.md"
failure_step: ""
source_session: deferred-from-0186
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0193 — Stale-blue sweep filter — catch machines on an out-of-release image

> **Type:** new-feature  |  **Complexity:** S  |  **Depends on:** 0162
> **Bump:** MINOR — adds a second, stricter filter branch to `scripts/sweep_stale_blues.sh`. Backwards-compatible: the existing `safe_to_destroy`-tag branch fires first and unchanged; the new image-based branch only runs as a fallback when the tag-based one finds zero candidates but the cluster is still over the expected count.
> **Evidence:** Spec 0186 handoff `## Deferred during implementation` third bullet — [handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:62](handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:62): *"the deploy notes above record the second occurrence of fly leaving stale machines that are not tagged `safe_to_destroy` (the first was spec 0162's motivation). The sweep filter doesn't catch this shape. A follow-up could extend `scripts/sweep_stale_blues.sh` to also catch machines on a not-currently-released image, gated behind a stricter heuristic so it never hits a green."* Direct evidence from spec 0186's deploy: [handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:46](handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:46): *"Sweep ran twice during the recovery, both reported `sweep: no stale blues on dual-research-alex` — the stale machines weren't tagged `safe_to_destroy`, so the existing filter didn't fire. Fly destroyed them itself before the second sweep ran."*

---

## 1. Context

`scripts/sweep_stale_blues.sh` exists because Fly's bluegreen orchestrator periodically leaves blues hanging after a deploy, requiring manual destroy. The original spec 0162 fix (cited at [scripts/sweep_stale_blues.sh:8](scripts/sweep_stale_blues.sh)) keys on `metadata.fly_bluegreen_deployment_tag == "safe_to_destroy"` — a tag Fly itself sets on machines its orchestrator has already decided to destroy. That filter is **safe by construction**: it can only match machines Fly has marked, never a live green.

But the spec 0186 deploy ([handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:44](handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:44)) hit the second occurrence of a different shape: Fly left blues hanging that were **not** tagged `safe_to_destroy`. The cluster ended up with v403 (old) + v406-attempt (new) machines coexisting, and the existing filter said `sweep: no stale blues on dual-research-alex` while the cluster was still oversize. The existing diagnostic fallback at [scripts/sweep_stale_blues.sh:72](scripts/sweep_stale_blues.sh) does fire in that case (dumps metadata so the next handoff captures evidence) — and the spec 0186 handoff is exactly that captured evidence.

The new shape: a machine on an image release that is **older than the currently-released image** (the one Fly considers the live version) is, by definition, a stale blue. Fly hasn't tagged it yet — that's the bug — but the release-version mismatch is itself a load-bearing signal.

## 2. Proposed change

Extend [scripts/sweep_stale_blues.sh:54](scripts/sweep_stale_blues.sh) with a second filter that runs only as a fallback when the existing tag-based filter finds nothing AND the cluster is oversize. The new filter selects machines whose `config.image` does NOT equal the currently-released image for the app.

### 2.1 New helper inside the script

Add a function (or inline block) after the existing `JQ_FILTER` at [scripts/sweep_stale_blues.sh:59](scripts/sweep_stale_blues.sh):

```bash
# Spec 0193 fallback filter. Runs only when the spec-0162 tag-based filter
# found zero candidates AND the cluster is oversize. Selects machines
# whose image release version is older than the current release for the
# app. Safe by construction in the same sense as the tag-based filter:
# Fly's release-history is authoritative — a machine on a previous
# release was definitionally superseded, no live green can be on an
# older release than the currently-released one.
get_current_release_image() {
  # Returns the image string Fly currently considers the live release,
  # or empty on failure.
  if [[ -n "$INPUT_FILE" ]]; then
    # Test mode: read alongside machines, named after the input file
    # with .release.json suffix. Allows fixture-based testing.
    local release_file="${INPUT_FILE%.json}.release.json"
    if [[ -f "$release_file" ]]; then
      jq -r '.image_ref' "$release_file" 2>/dev/null
    fi
  else
    fly releases --app "$APP" --json 2>/dev/null | \
      jq -r '[.[] | select(.status == "complete")] | sort_by(.created_at) | last | .image_ref' 2>/dev/null
  fi
}

JQ_FALLBACK_FILTER='.[] | select(.config.image != $CURRENT_IMG) | .id'
```

The fallback filter is **gated** behind both conditions to prevent ever hitting a green:

1. The tag-based filter returned 0 machines (existing condition at [scripts/sweep_stale_blues.sh:65](scripts/sweep_stale_blues.sh) `if (( total == 0 ))`).
2. The cluster is oversize per `--expected-count` (existing condition at [scripts/sweep_stale_blues.sh:72](scripts/sweep_stale_blues.sh) `(( machine_count > EXPECTED_COUNT ))`).
3. `get_current_release_image` returned a non-empty string (so we know what "current" means).
4. The fallback identifies AT LEAST ONE machine whose image matches the current release (i.e. a live green exists — we are not about to destroy the only running machine).

Only when all four hold does the fallback destroy the non-current-image machines.

### 2.2 Wiring inside the existing oversized-cluster branch

The current diagnostic-dump block at [scripts/sweep_stale_blues.sh:72](scripts/sweep_stale_blues.sh):

```bash
if [[ "$machine_count" =~ ^[0-9]+$ ]] && (( machine_count > EXPECTED_COUNT )); then
  echo "sweep: cluster has $machine_count machines (expected $EXPECTED_COUNT) — dumping metadata for filter diagnosis:" >&2
  printf '%s' "$machines_json" \
    | jq '[.[] | {id, name, state, metadata: .config.metadata}]' >&2
fi
exit 0
```

Becomes (additive — the diagnostic dump is preserved):

```bash
if [[ "$machine_count" =~ ^[0-9]+$ ]] && (( machine_count > EXPECTED_COUNT )); then
  echo "sweep: cluster has $machine_count machines (expected $EXPECTED_COUNT) — checking image-release fallback filter (spec 0193)" >&2

  current_image="$(get_current_release_image)"
  if [[ -z "$current_image" ]]; then
    echo "sweep: spec-0193 fallback skipped — could not determine current release image" >&2
    printf '%s' "$machines_json" \
      | jq '[.[] | {id, name, state, image: .config.image, metadata: .config.metadata}]' >&2
    exit 0
  fi

  # Safety check: at least one machine MUST be on the current image.
  # Otherwise we have no live green and the fallback would destroy
  # everything in the cluster — refuse and dump metadata for triage.
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
    echo "sweep: spec-0193 fallback found no stale machines either; dumping metadata for triage" >&2
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
```

The fallback path is **strictly additive** — the existing `safe_to_destroy`-tag branch runs first and unchanged (the same lines remain at [scripts/sweep_stale_blues.sh:59–88](scripts/sweep_stale_blues.sh)). The fallback only activates inside the existing oversized-cluster diagnostic block, which itself only runs when the tag-based filter found nothing.

### 2.3 What does NOT change

- The exit code is still always 0 — sweep is best-effort hygiene per [scripts/sweep_stale_blues.sh:25](scripts/sweep_stale_blues.sh).
- The `safe_to_destroy`-tag-based filter is unchanged. It still runs first, and when Fly does tag a stale blue correctly, the original spec 0162 path handles it without ever reaching the fallback.
- The `--input` test fixture path is preserved; the fallback reads its release image from a sibling `.release.json` fixture (per §2.1) so the existing test pattern at [scripts/sweep_stale_blues.sh:44](scripts/sweep_stale_blues.sh) continues to work.
- Caller integration (`/dev-next` step 19 deploy / Makefile / fly.toml) is unchanged.

## 3. UX / Behavior

- **Before this spec, after a deploy where Fly left stale blues without the `safe_to_destroy` tag:** the sweep prints `sweep: no stale blues on dual-research-alex` and dumps machine metadata to stderr for triage. The cluster stays oversize until manually cleaned up (Fly often self-heals after several minutes, but not always).
- **After this spec, same situation:** the sweep checks the current release image via `fly releases --app "$APP" --json`, identifies machines NOT on that image, confirms there is at least one machine on the current image, and destroys the off-version ones. Output: `sweep: spec-0193 fallback destroying N machine(s) not on current image (registry.fly.io/...:vXYZ)`.

User-visible: one new log line on the failure mode this spec targets; identical output on the happy path (where the tag-based filter handles it) and on the safety-refusal path (where no live green exists — fallback bails with diagnostic dump).

## 4. Data / Schema deltas

None. The script reads existing Fly API data (`fly machine list` and `fly releases`) and writes only to stderr / stdout. No new files, no schema, no config.

## 5. Out of scope

- **Retroactive sweep of historical deploys.** The script runs after each `/dev-next` deploy per the existing call chain; we don't go back through past deploys.
- **Notifying the user when the fallback fires.** The output is logged to the deploy stdout, which `/dev-next` step 19 already surfaces verbatim. No new notification mechanism (no Slack ping, no email).
- **Tuning the `EXPECTED_COUNT` default.** Still 2, matching spec 0162. Per-app overrides via `--expected-count` are unchanged.
- **Replacing the tag-based filter.** Spec 0162's filter stays primary — Fly's own verdict (`safe_to_destroy`) is the strongest signal we have. The fallback is exactly that: a fallback when Fly doesn't tag.
- **Smarter image comparison.** This spec compares image strings literally (`config.image != current_image`). Sub-shape comparisons (registry prefix, digest, version semver) are out of scope; Fly's release_image is already a canonical pinned reference.
- **Time-bounded fallback.** A more permissive shape would also destroy old machines that have been around for N minutes regardless of image. Out of scope — the gating cascade (oversize cluster + at-least-one-green + tag-filter-empty) is what keeps the fallback safe; adding a time gate doesn't strengthen it.

## 6. Test plan

- [ ] **Fallback fires on documented shape.** Build a fixture JSON modelled on the spec 0186 deploy: 4 machines, two on `image:v403`, two on `image:v406-attempt`, none tagged `safe_to_destroy`. Sibling `.release.json` declares `image_ref: registry.fly.io/dual-research-alex:v406-attempt`. Run `scripts/sweep_stale_blues.sh --input fixture.json --expected-count 2`. Assert: stdout contains `sweep: spec-0193 fallback destroying 2 machine(s)`, exit code 0.
- [ ] **Fallback does NOT fire when tag-based filter handles it.** Fixture: 4 machines, 2 on current image, 2 on previous image AND tagged `safe_to_destroy`. Assert: stdout contains the existing `sweep: destroyed 2/2 stale blues` line, no `spec-0193 fallback` line.
- [ ] **Fallback refuses when zero machines on current image.** Fixture: 4 machines, all on `image:v406-attempt`, sibling `.release.json` declares `image_ref: …:v407`. Assert: stdout contains `sweep: spec-0193 fallback refused — zero machines on current image`, exit 0, no destroy attempts.
- [ ] **Fallback skipped when current image undeterminable.** Fixture: 4 machines, no sibling `.release.json` file. Assert: stdout contains `sweep: spec-0193 fallback skipped — could not determine current release image`, falls through to metadata dump, exit 0.
- [ ] **Cluster at expected size: neither filter fires, no fallback.** Fixture: exactly 2 machines, both untagged, both on current image. Assert: `sweep: no stale blues on dual-research-alex`, no oversize block triggers, exit 0.
- [ ] **Full suite still green:** `uv run pytest tests/ -q` — this spec is shell-only but the broader test suite must remain green.

## 7. Risks

- **Fallback destroys a live green by mistake.** This would be a P0. *Mitigation:* four gates must all hold before any destroy is issued: (1) tag-based filter found 0, (2) cluster is oversize per `EXPECTED_COUNT`, (3) `get_current_release_image` returned a non-empty string, (4) at least one machine in the cluster is on that current image (so destroying the others can never zero the cluster). The `green_count == 0` refusal path explicitly handles the worst case (somehow the release reports a version no machine is on yet) by bailing out and dumping for triage, never destroying.
- **`fly releases --app … --json` shape drift.** The fallback parses `.[] | select(.status == "complete") | .image_ref` from the output. If Fly changes the shape, `get_current_release_image` returns empty and the fallback skips itself (per gate 3 above), falling back to today's diagnostic dump. *Mitigation:* the dump captures the new shape; a single-line patch updates the jq selector on the next spec.
- **Performance regression.** The fallback adds one `fly releases` API call per sweep, but only in the rare oversize-cluster case. Per [scripts/sweep_stale_blues.sh:25](scripts/sweep_stale_blues.sh) the sweep is post-deploy and best-effort; an extra API call adds < 1 second.
- **Missed call site.** The sweep is invoked from `/dev-next` step 19 (post-deploy). No other caller in the repo. *Mitigation:* `git grep sweep_stale_blues.sh` to enumerate callers before merging — if a new caller appeared since spec 0162, verify it still gets the additive shape.
- **Race with concurrent deploys.** Two `/dev-next` runs interleaving would call the sweep twice on overlapping state. *Mitigation:* the existing `/dev-queue-run` supervisor is strictly sequential per spec 0186 §5; concurrent deploys don't happen in the supported workflow. If they ever do (parallel-drain follow-up), the sweep is idempotent — destroying an already-destroyed machine is a no-op per `fly machine destroy --force`.

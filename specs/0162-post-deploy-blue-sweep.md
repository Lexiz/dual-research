---
kind: dev
spec: "0162"
slug: post-deploy-blue-sweep
title: "Fix: post-deploy sweep for safe_to_destroy blue machines"
type: bug
label: bug
version_bump: PATCH
target_version: 1.23.2
status: merged
queue_position: 1
depends_on: []
complexity: S
created: 2026-05-22
queued_at: "2026-05-22"
started_at: "2026-05-22T15:32:34Z"
merged_at: "2026-05-22T15:47:09Z"
deployed_at: ""
pr: "https://github.com/Lexiz/dual-research/pull/185"
handover: ""
failure_step: ""
source_session: dbc5aed3-25f2-4ed3-a7b1-4dc61161a4c0
promoted_from_draft: "005"
---

# Spec 0162 — Fix: post-deploy sweep for safe_to_destroy blue machines

> **Type:** bug  |  **Severity:** P2  |  **Affects:** `/dev-next` deploy stage on the Fly app `dual-research-alex`
> **Bump:** PATCH — bug fix (deploy hygiene)
> **Evidence:** handoffs [2026-05-22-spec-0160](handoffs/2026-05-22-spec-0160-dashboard-live-data-via-pages-function.md) and [2026-05-22-spec-0161](handoffs/2026-05-22-spec-0161-js-test-stack-for-pages-function.md). 2 of 2 bluegreens under spec 0159's config left stale blue machines alive.

---

## 1. Reproduction

**Environment:** `/dev-next` running `fly deploy` against `dual-research-alex` with bluegreen strategy configured in spec 0159's `fly.toml`.

**Steps:**
1. Run `/dev-next` on any queued spec end-to-end through the deploy stage.
2. `fly deploy` completes successfully — greens are healthy, traffic switches.
3. Fly's orchestrator enters its destroy phase to remove the old blues. The lease-holder is an internal Fly token (`*@tokens.fly.io`) that we cannot revoke.
4. `fly machine list --json` after the deploy returns: blue machines still present, each carrying `metadata.fly_bluegreen_deployment_tag == "safe_to_destroy"`.

**Expected:** After a successful bluegreen deploy, no machines remain with `fly_bluegreen_deployment_tag: safe_to_destroy`. The app has only the new greens.

**Actual:** Blues persist indefinitely with the `safe_to_destroy` tag set by Fly itself, accumulating ~$5/mo of idle compute per stale machine. Observed in 2 of 2 deploys since spec 0159.

## 2. Root cause hypothesis

Fly's orchestrator fails to acquire the destroy-lease during its cleanup phase. The lease is held by an internal Fly token (`*@tokens.fly.io`) — we have no API surface to revoke it, and only Fly can fix the underlying orchestrator behavior.

This is **not** a defect in our `fly.toml` or `/dev-next` logic; it's an upstream Fly bug. But we own the consequence (stale machines on our account, our bill), so we own the workaround.

Reference points:
- `/dev-next`'s deploy stage runs `fly deploy` and reports success on a 0 exit code, but does not inspect machine state afterward.
- Fly itself stamps `metadata.fly_bluegreen_deployment_tag: safe_to_destroy` on machines its orchestrator has already decided are eligible for destroy. The tag is Fly's own verdict, not ours.

## 3. Fix

Add a post-deploy sweep step in `/dev-next`'s deploy section. The sweep is also exposed as a standalone command so existing stragglers (and any future ones) can be cleaned without waiting for the next deploy.

### 3a. Sweep script

New file: `scripts/sweep_stale_blues.sh` (executable bash).

```bash
#!/usr/bin/env bash
# Destroys Fly machines whose metadata carries fly_bluegreen_deployment_tag:
# "safe_to_destroy". Fly sets this tag itself on machines its orchestrator has
# already decided are eligible for destroy, so this is safe — it cannot hit a
# live green.
#
# Usage:
#   scripts/sweep_stale_blues.sh [--app <app-name>]
#
# Default app: dual-research-alex.
set -uo pipefail

APP="${1:-dual-research-alex}"
if [[ "${1:-}" == "--app" ]]; then APP="${2:?--app requires a value}"; fi

machines_json="$(fly machine list --app "$APP" --json 2>/dev/null)" || {
  echo "sweep: fly machine list failed for app=$APP" >&2
  exit 0  # best-effort: do not fail the caller
}

mapfile -t stale < <(printf '%s' "$machines_json" \
  | jq -r '.[] | select(.config.metadata.fly_bluegreen_deployment_tag == "safe_to_destroy") | .id')

total="${#stale[@]}"
if (( total == 0 )); then
  echo "sweep: no stale blues on $APP"
  exit 0
fi

failed=0
for id in "${stale[@]}"; do
  if ! fly machine destroy --app "$APP" --force "$id" >/dev/null 2>&1; then
    failed=$((failed + 1))
    echo "sweep: destroy failed for $id" >&2
  fi
done

destroyed=$(( total - failed ))
echo "sweep: destroyed $destroyed/$total stale blues on $APP (failed=$failed)"
exit 0
```

Best-effort semantics: any failure (list call failed, individual destroy failed) is logged and the script exits 0. The deploy itself already succeeded by the time the sweep runs — cosmetic cleanup must never fail the deploy stage.

### 3b. `/dev-next` hook

Append a sweep step at the end of `/dev-next`'s deploy section (after `fly deploy` returns success):

```
Run scripts/sweep_stale_blues.sh and surface its single-line summary in the
handoff under the "Deploy" section. The sweep's exit code is ignored — the
deploy step's success is determined by `fly deploy` itself, not by the sweep.
```

The change to the `/dev-next` skill file is a single new sub-step; no source-code changes elsewhere.

### 3c. One-time retroactive cleanup

Out of band of this spec's PR, run `scripts/sweep_stale_blues.sh` once against `dual-research-alex` to clear the existing stragglers from spec 0160 and spec 0161. This is documented in the spec's handoff, not gated on it.

## 4. Regression-prevention test

A jq-filter test using a hand-rolled fixture. Goal: confirm the filter selects only machines tagged `safe_to_destroy` — never live greens, never tag-less machines, never machines with other bluegreen tags.

- [ ] Test: `tests/scripts/test_sweep_stale_blues_filter.py` — feeds `tests/fixtures/fly_machine_list_bluegreen.json` (a hand-rolled JSON file with mixed entries: 2 live greens with no `fly_bluegreen_deployment_tag`, 2 stale blues tagged `safe_to_destroy`, 1 machine tagged with an unrelated bluegreen tag value, 1 machine with no `metadata` block at all) through the same `jq` expression used in the script and asserts the result is exactly the IDs of the 2 stale blues.

The test does not exercise `fly machine destroy` — that's an external command. The filter is the load-bearing safety logic; that's what we lock in.

## 5. Blast radius

- **The sweep script itself**: only invokes `fly machine list --json` (read-only) and `fly machine destroy --force` against IDs Fly itself flagged with `safe_to_destroy`. There is no path by which a live green can be selected — Fly's own orchestrator owns that tag.
- **The `/dev-next` hook**: appends one new sub-step. The deploy step's pass/fail criterion is unchanged (still `fly deploy`'s exit code). The sweep's exit code is intentionally ignored.
- **Other callers of `scripts/`**: none — this is a new file.
- **The Fly app's runtime traffic**: zero impact. The sweep runs after the deploy completes; greens are already serving traffic by the time the sweep runs.

## 6. Out of scope

- **Fixing Fly's destroy-lease bug itself.** We cannot — it's an internal Fly orchestrator concern. Only Fly can resolve the root cause.
- **Dashboard or UI surfacing of "stale machine" state.** The sweep's single-line summary in the handoff is enough; a richer surface can be its own spec if pain persists.
- **Sweeping any tag other than `safe_to_destroy`.** Other bluegreen lifecycle tags (e.g. machines mid-deploy, machines in `attached` or other transitional states) are explicitly excluded — only Fly's `safe_to_destroy` verdict is acted on.
- **Generalising the sweep to other Fly apps.** The script accepts `--app` but the default and the `/dev-next` hook both target `dual-research-alex`.

## 7. Risks

- **The jq selector path could change.** If Fly renames `metadata.fly_bluegreen_deployment_tag` or moves it under `config.*` vs top-level, the filter silently selects nothing and stale blues accumulate again. Mitigation: the sweep's "destroyed N/M" log line is visible in every deploy handoff — a long run of `0/0` after a real bluegreen will be the canary.
- **A destroy could race with a Fly-internal retry.** If Fly's own orchestrator finally manages to acquire the lease and destroy the machine just as our sweep is calling destroy, one call returns "not found". Mitigation: best-effort semantics — we log the failure and move on. No state corruption is possible.
- **Best-effort exit-0 hides real problems.** If `fly machine list` consistently fails (auth, network), we silently produce "no stale blues" log lines forever. Mitigation: the log line distinguishes "list failed" from "no stale blues on $APP", and the handoff surfaces it. A future spec can add stricter alerting if needed.
- **The `--force` flag.** `fly machine destroy --force` skips Fly's "are you sure" check. This is required for unattended use, but means a bug in the filter would destroy real machines without prompting. Mitigation: regression test in §4 locks in the filter; the filter only ever selects machines Fly itself tagged for destruction.

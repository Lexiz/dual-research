---
kind: dev
spec: "0200"
slug: fly-deploy-simplification-drop-bluegreen-no-retry-rule-codify-recovery
title: Fly deploy simplification — drop bluegreen, no-retry-on-failure rule, codify recovery path
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: in_progress
depends_on: ["0198"]
complexity: M
created: 2026-05-24
queued_at: "2026-05-23T22:24:29Z"
started_at: "2026-05-23T22:54:17Z"
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: orchestrator-hardening-series-2026-05-23
promoted_from_draft: ""
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0200 — Fly deploy simplification: drop bluegreen, no-retry-on-failure rule, codify recovery path

> **Type:** refactoring  |  **Complexity:** M  |  **Depends on:** 0198 (validator/skill gates this spec is authored against)
> **Bump:** PATCH — internal deploy mechanics; no user-facing change, no API contract change.
> **Evidence:** Spec 3 of a 7-spec orchestrator-hardening series. Author: the user, 2026-05-23 orchestrator-audit conversation. Recurring pain over ~70 spec deploys: bluegreen lease-acquisition failures strand old machines, the `/dev-next` deploy step blindly retries on failure and amplifies the orphan count, and the recovery procedure lives only in operator memory (see [project_fly_lease_drift_recovery.md](/Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md)). Concrete signal: `fly releases -a dual-research-alex` shows 4 failed releases in the last 4 hours alone.

---

## 1. Current state

The Fly app `dual-research-alex` deploys with `strategy = "bluegreen"` per [fly.toml:21](fly.toml:21). Bluegreen creates a parallel cohort of new ("green") machines, waits for them to pass health checks, promotes traffic, then destroys the old ("blue") cohort. Comment at [fly.toml:14-19](fly.toml:14) notes bluegreen was adopted in spec 0159 to mitigate "9-in-a-row machines-API mid-rolling timeout" patterns where slow cold-boots stranded half-rolled rolling deploys.

Three concrete pain modes accumulated since spec 0159:

1. **Lease-acquisition failures strand blues as zombies.** Fly's bluegreen orchestrator promotes greens before destroying blues, and the destroy step needs a lease on each blue VM. When another fly-tokens process (a hung CI job, an orphan `flyctl` from an earlier crashed deploy, a parallel orchestration session) holds a lease, the destroy fails. Greens are live, blues stay alive. The cluster grows from 2 → 3 → 4 machines across consecutive deploys. Documented in [project_fly_lease_drift_recovery.md](/Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md) and handoffs 0187/0188/0189 (2026-05-23).

2. **`/dev-next` step 21 retries `fly deploy` on failure, amplifying the orphan count.** Current step 21 at [~/.claude/skills/dev-next/SKILL.md:237](~/.claude/skills/dev-next/SKILL.md:237) reads: *"Emit `deploy_started`, then `fly deploy`. On failure: `status: failed, failure_step: deploy`, emit `failed`. Surface, exit."* That sentence's intent is "halt on failure", but in practice multiple recent sessions have re-invoked `fly deploy` after a lease error — each retry spawns *another* green pair before the previous blues are cleaned. 2 → 4 → 6 machines in three retries.

3. **The recovery path is operator-only knowledge.** [scripts/sweep_stale_blues.sh:74](scripts/sweep_stale_blues.sh:74) (spec 0162) catches the `safe_to_destroy` tag-set case; [scripts/sweep_stale_blues.sh:80](scripts/sweep_stale_blues.sh:80) (spec 0193) catches the image-based fallback. But the *decision* — "is this deploy actually broken, or did only the cleanup fail?" — lives in `project_fly_lease_drift_recovery.md`, not in the skill. Future sessions (and future Claude instances reading the skill cold) re-derive the recovery procedure each time or, worse, skip the diagnosis and retry.

### Verified against current code

- [fly.toml:21](fly.toml:21) — `strategy = "bluegreen"`. Confirmed.
- [fly.toml:34](fly.toml:34) — `min_machines_running = 1`. Confirmed.
- [fly.toml:49](fly.toml:49) — `grace_period = "90s"`. Confirmed; bumped from 30s in spec 0159 to accommodate cold-boot on `shared-cpu-1x:512MB`.
- [fly.toml:54-55](fly.toml:54) — VM size `shared-cpu-1x` / `512mb`. Confirmed.
- [~/.claude/skills/dev-next/SKILL.md:237](~/.claude/skills/dev-next/SKILL.md:237) — step 21 fail-handling prose. Confirmed: no diagnostic branch, no explicit "do not retry" rule.
- [~/.claude/skills/dev-next/SKILL.md:246-252](~/.claude/skills/dev-next/SKILL.md:246) — post-deploy sweep call. Confirmed: sweep runs *only* on `fly deploy` success; the failure path skips it.
- [scripts/sweep_stale_blues.sh:74](scripts/sweep_stale_blues.sh:74) — `safe_to_destroy` tag filter. Confirmed.
- [scripts/sweep_stale_blues.sh:80](scripts/sweep_stale_blues.sh:80) — image-based fallback filter (spec 0193). Confirmed; gated behind four checks so it can never zero the cluster.
- Current cluster state (2026-05-23T22:06Z): `fly status -a dual-research-alex` reports 2 machines (`287d9d6a57e7e8`, `811e91a9214668`) on version 540, image `dual-research-alex:deployment-01KSBDY3QAC6QH124DD54133EZ`, both healthy. Bluegreen tag `1779573939` on both. **No zombies present at author time** — the one-time pre-merge cleanup in §6 may end up a no-op, which is fine; the spec is sized for the typical (dirty) case.

### Traceability table — source items → spec sections

Source: this spec's atomic items come from the user's brief in the 2026-05-23 orchestrator-audit conversation (no NOTES.md or ideation file). Per the gate added by spec 0198 §2.2, every named atomic item in the source must land in this spec body or be explicitly deferred to §5 with a follow-up target. The conversation called out four atomic items and one baked-in decision; this table enumerates all five.

| source item | source quote/ref | spec section |
|---|---|---|
| Switch the fly.toml deploy strategy (rolling vs single-machine immediate) | user's brief, "the fix — three parts", part 1 | §2.1 |
| Hard rule in `/dev-next`: never blindly retry `fly deploy` on failure | user's brief, "the fix — three parts", part 2 | §2.2 |
| Codify the recovery path (memory → skill step 21 failure branch) | user's brief, "the fix — three parts", part 3 | §2.3 |
| One-time zombie cleanup as pre-merge action | user's brief, "one-time migration" | §6 (pre-merge action) |
| Stay on Fly — no platform migration | user's brief, "one baked-in decision" | §5 (Out of scope, named as non-decision) |

No items deferred. All five ship in this spec.

---

## 2. Target state

After this spec:

- `fly.toml` uses `strategy = "rolling"`. Per-machine replacement, no parallel cohort, no destroy-lease race on a batch of blues.
- `/dev-next` step 21 has an explicit failure decision matrix: diagnose with `fly status` before any retry; **never** auto-retry on a non-zero `fly deploy` exit; surface a clear halt with the diagnosed state.
- The recovery procedure documented in `project_fly_lease_drift_recovery.md` is mirrored into the skill itself, so future sessions don't have to look it up.
- `scripts/sweep_stale_blues.sh` remains in place under the same name (rationale in §2.4). Its image-based fallback path (spec 0193) becomes the primary mechanism under rolling, since the bluegreen tag will no longer be set.

### 2.1 — Switch `fly.toml` from bluegreen to rolling

**Decision: rolling, not single-machine immediate.** Both options were on the table; rolling wins for these reasons:

- **Zero downtime in the success case.** Rolling replaces one of two machines at a time, so capacity goes 2 → 1 → 2 across the rollout. Health-check serving never drops to zero. Single-machine immediate would introduce ~30s downtime per deploy — acceptable for a hobby app but explicitly worse than the status quo, and pointless when rolling delivers the same simplicity.
- **Narrower failure surface than bluegreen.** Rolling does not create a parallel cohort, so there is no "destroy-blue" stage to fail. Each replacement acquires its own lease briefly during in-place restart and releases it on completion — no inter-machine lease races. The known lease-acquisition failure mode in `project_fly_lease_drift_recovery.md` is structurally eliminated, not just patched.
- **No reduction in HA.** Bluegreen and rolling both keep at least one machine serving traffic during a deploy. `min_machines_running = 1` ([fly.toml:34](fly.toml:34)) is unchanged and still honored by rolling.

The single-machine immediate option (`strategy = "immediate"` + explicit `count = 1`) was rejected because: it removes HA entirely (one machine → one failure domain), it forces ~30s downtime per deploy, and it does not actually simplify the orchestrator's failure handling any further than rolling does. Hobby app or not, "rolling with 2 machines" is the boring-correct default for HTTP services on Fly.

**Concrete `fly.toml` change:**

```toml
[deploy]
  strategy = "rolling"
```

Replaces the existing `strategy = "bluegreen"` at [fly.toml:21](fly.toml:21). The `[deploy]` block comment at [fly.toml:14-19](fly.toml:14) is rewritten to reference this spec and explain the rolling choice (and the no-retry rule it pairs with). `min_machines_running = 1` ([fly.toml:34](fly.toml:34)) and `grace_period = "90s"` ([fly.toml:49](fly.toml:49)) stay as-is — rolling needs both, and the 90s grace is calibrated for our cold-boot envelope per spec 0159.

No `count` setting is added. Fly determines machine count from existing app state (currently 2). If a future change wants to drop to 1 machine or expand to N, that's a separate spec.

### 2.2 — `/dev-next` step 21: no-retry-on-failure rule

The current step 21 prose at [~/.claude/skills/dev-next/SKILL.md:237](~/.claude/skills/dev-next/SKILL.md:237) is replaced with an explicit decision matrix. On any non-zero exit from `fly deploy`, the orchestrator runs `fly status -a dual-research-alex` first and routes based on what it sees:

1. **All machines on the new version, all healthy** → deploy actually succeeded; only the post-deploy cleanup (or terminal command framing) failed. Run `scripts/sweep_stale_blues.sh`, verify cluster health, emit `deployed` + `deploy_health_check_ok`, proceed to step 22 as if the deploy returned 0.

2. **Mixed old/new versions, all healthy** → new image is live and serving, but Fly didn't fully converge cleanup (the historical bluegreen blue-sweep failure mode; under rolling this is rare but possible mid-rollout). Run the sweep, verify cluster health, mark deployed.

3. **Only old-version machines present** → deploy genuinely failed; no new image is live. Mark `status: failed, failure_step: deploy`, emit `failed`, surface the original `fly deploy` stderr + the `fly status` output, halt. **Do not invoke `fly deploy` again in this step.**

4. **Mixed old/new but new is unhealthy** → genuine partial failure. Same halt branch as case 3. The next session decides whether to roll back, redeploy from a clean state, or investigate.

5. **`fly status` itself errors** → halt with the original deploy error. Do not retry.

The hard rule: the orchestrator NEVER calls `fly deploy` more than once within one `/dev-next` invocation. If the user wants to retry after fixing whatever's wrong, they re-invoke `/dev-next` (or fix manually). The two-shots-in-one-cycle behavior that amplified the orphan count is eliminated by construction.

Status parsing uses the JSON form to avoid table-text drift:

```bash
fly machine list -a dual-research-alex --json \
  | jq -r '.[] | "\(.id) \(.state) \(.config.image)"'
```

Compared against the most recent release image from `fly releases -a dual-research-alex --json` (same query the sweep script already uses at [scripts/sweep_stale_blues.sh:91-101](scripts/sweep_stale_blues.sh:91)). The skill prose names this query but does not inline the full jq — implementers may use equivalent forms.

### 2.3 — Codify recovery path into the skill

The memory at [project_fly_lease_drift_recovery.md](/Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md) currently documents the recovery procedure: run `fly status`, classify by version mix, run `sweep_stale_blues.sh`, fall back to manual `fly machine destroy --force` if the sweep finds nothing tagged. After this spec, the same procedure is encoded directly in `/dev-next` step 21's failure branch — case 1 and case 2 above ARE the codified recovery path. A future session reading the skill cold sees the diagnose-then-sweep cascade in place; it doesn't need to consult the memory to know the right shape.

The memory itself stays — it remains the authoritative incident-log narrative and may pick up new variants. But it's no longer load-bearing for the orchestrator: the skill is self-sufficient. A pointer line is added to the skill's step 21 prose: *"See `project_fly_lease_drift_recovery.md` for incident history; the decision matrix below is the actionable distillation."*

### 2.4 — `scripts/sweep_stale_blues.sh`: keep name, update comments

The script is not renamed. Two reasons:

- **Renaming cascades.** The skill at [~/.claude/skills/dev-next/SKILL.md:249](~/.claude/skills/dev-next/SKILL.md:249), the handoffs referencing it (~25 files across `handoffs/`), and any future incident write-up that quotes its name would all need updates. The cost-to-clarity ratio is poor for a script whose function is unchanged.
- **The script already handles the rolling case.** Its primary tag filter at [scripts/sweep_stale_blues.sh:74](scripts/sweep_stale_blues.sh:74) selects on `fly_bluegreen_deployment_tag == "safe_to_destroy"` — under rolling that filter finds zero candidates, which is correct (rolling doesn't tag machines as bluegreen-stale). Its image-based fallback at [scripts/sweep_stale_blues.sh:80](scripts/sweep_stale_blues.sh:80) (spec 0193) destroys any machine not on the current release image — which IS the rolling-era recovery path. Zero code changes needed.

What changes: the header comment block ([scripts/sweep_stale_blues.sh:1-42](scripts/sweep_stale_blues.sh:1)) is updated to note that bluegreen is no longer the primary strategy (this spec) and that the image-based fallback is now the primary recovery path. The script's runtime behavior is unchanged.

The output line `sweep: no stale blues on …` ([scripts/sweep_stale_blues.sh:108](scripts/sweep_stale_blues.sh:108)) stays — it's the expected/healthy signal under rolling, and renaming it would just create a churn commit. The "blues" terminology is now vestigial; that's acceptable for a recovery tool whose contract is "destroy machines Fly's authoritative state says shouldn't be there."

---

## 3. Stepwise migration

Each step is independently revertable. The migration is small but ordered to keep the cluster clean throughout.

- **Step 1 — One-time zombie cleanup (pre-merge).** Run on the queue-control checkout against the live app. Verifies the new strategy starts from a clean cluster. See §6 for the exact commands. If no zombies present (as is the case at author time), this step is a no-op.

- **Step 2 — Edit `fly.toml`.** Change `strategy = "bluegreen"` to `strategy = "rolling"` at [fly.toml:21](fly.toml:21). Rewrite the `[deploy]` block comment at [fly.toml:14-19](fly.toml:14) to cite this spec and the rolling rationale (§2.1). Verifies: `grep -n 'strategy' fly.toml` shows `rolling`; `fly config validate` passes.

- **Step 3 — Edit `~/.claude/skills/dev-next/SKILL.md` step 21.** Replace the failure prose with the §2.2 decision matrix and add the §2.3 pointer line. Verifies: a hand-read of the updated step 21 matches §2.2's five cases; the post-deploy sweep call still fires on case 1 / case 2 paths.

- **Step 4 — Update `scripts/sweep_stale_blues.sh` header comment.** Document the rolling-era role per §2.4. No code change. Verifies: `bash -n scripts/sweep_stale_blues.sh` parses; existing fixture tests (if any) still pass.

- **Step 5 — Smoke-deploy.** This is the `/dev-next` step 21 invocation that ships *this* spec. Under the new strategy and the new skill rules, the deploy should succeed cleanly with exactly 2 machines on the new version and zero zombies. If it fails: the new decision matrix runs (its own validation in production).

---

## 4. Behavior preservation

This is a refactoring spec — no user-facing change.

- [ ] `dual-research-alex.fly.dev/` returns 200 before and after the deploy (homepage smoke).
- [ ] `dual-research-alex.fly.dev/api/health` returns 200 before and after the deploy.
- [ ] After deploy: exactly 2 machines on the new version per `fly machine list -a dual-research-alex --json`; zero machines on the prior version.
- [ ] After deploy: no machine carries a stale `fly_bluegreen_deployment_tag` (since rolling doesn't set it; any tag present is from a prior bluegreen deploy and should have been swept in step 1).
- [ ] `/dev-next` end-to-end on this spec runs without manual intervention through step 24.

---

## 5. Out of scope

**Explicit: no new feature ships here.** This spec does NOT add any new feature surface — it changes internal deploy mechanics only. Any feature work that depends on the rolling deploy lives in a follow-up spec.

- **Migrating off Fly.** Stay on Fly. The platform is not the problem; the strategy was. Not deferred to a follow-up — actively a non-decision.
- **Multi-region.** Stay single-region `iad`. If multi-region is wanted later, that is its own spec.
- **Building a new sweep script.** The existing one's image-based fallback path is the right shape for rolling; reuse it. Not deferred.
- **Changing the app's cold-boot performance.** Image size, dependency graph, and startup latency are a separate concern. The 90s grace period covers our current envelope; if rolling exposes a cold-boot regression, that's a follow-up spec (likely titled "cold-boot budget for rolling deploys") and is deferred to a follow-up dev spec to be drafted post-merge.
- **Adding `count` to `fly.toml`.** Current machine count (2) stays implicit. Spec'ing count would be its own decision.
- **Renaming `scripts/sweep_stale_blues.sh`.** Decided against in §2.4 with rationale. Not deferred — the no-rename decision is final.
- **A rollback procedure for the rolling strategy itself.** If rolling turns out worse than bluegreen, a follow-up spec reverts. Not pre-planned here; one decision per spec.

---

## 6. Test plan

### Pre-merge action — one-time zombie cleanup

Run this on the queue-control checkout (`/Users/alexlisitzky/dual-research/`) against the live app, before the PR for this spec merges. The new strategy starts from a clean cluster.

```bash
# 1. Inspect current cluster state.
fly status -a dual-research-alex
fly machine list -a dual-research-alex --json \
  | jq '[.[] | {id, name, state, image: .config.image, bluegreen_tag: .config.metadata.fly_bluegreen_deployment_tag}]'

# 2. Identify the current release image.
fly releases -a dual-research-alex --json \
  | jq -r '[.[] | select(.Status == "running" or .Status == "complete")] | sort_by(.CreatedAt) | last | .ImageRef'

# 3. If any machine's .config.image differs from the current release image, OR
#    any machine carries fly_bluegreen_deployment_tag != "<current-tag-on-live-machines>",
#    that machine is a zombie. Destroy it with:
fly machine destroy --app dual-research-alex --force <MACHINE-ID>

# 4. Re-verify: machine list now shows exactly the expected count (2) on the
#    current release image, no stale bluegreen tags. fly status all healthy.
```

At author time (2026-05-23T22:06Z) the cluster has 2 healthy machines, both on the current release image, identical bluegreen tags — no zombies. The step may be a no-op when actually run; the diagnostic commands still execute so the cleanup is *verified*, not assumed.

### Behavior preservation tests

Run after step 5 of the migration (the smoke-deploy):

```bash
# a. Homepage smoke.
curl -sf https://dual-research-alex.fly.dev/ > /dev/null && echo "OK: /"

# b. Health endpoint.
curl -sf https://dual-research-alex.fly.dev/api/health > /dev/null && echo "OK: /api/health"

# c. Machine count + version uniformity.
fly machine list -a dual-research-alex --json \
  | jq -r '[.[] | .config.image] | unique | length' \
  | xargs -I{} test {} -eq 1 && echo "OK: uniform image"

fly machine list -a dual-research-alex --json \
  | jq -r 'length' \
  | xargs -I{} test {} -eq 2 && echo "OK: 2 machines"
```

### Decision-matrix tests

The §2.2 decision matrix is exercised in production by the deploy that ships this spec. There is no unit-test scaffolding for the skill prose itself (skills are markdown, not code); the matrix's correctness is verified by:

- Reading the updated step 21 and confirming all five cases are spelled out.
- Inspecting the next failed deploy after merge (if any) and confirming the orchestrator follows the matrix rather than retrying.

If the next 5 deploys after merge succeed cleanly with no zombies, the matrix is validated by absence of pathology.

---

## 7. Risks

- **Rolling cold-boot exceeds grace period.** Our health-check grace is 90s ([fly.toml:49](fly.toml:49)). If a `shared-cpu-1x:512MB` cold-boot exceeds 90s for the new image, Fly will halt the rollout with the new machine unhealthy — same failure mode that prompted spec 0159's switch to bluegreen. Mitigation: spec 0159 already widened the grace from 30s to 90s precisely for this, and we've shipped ~40 specs under that window without grace-period failures (the failures since 0159 have been lease races, not cold-boot timeouts). `min_machines_running = 1` keeps one machine serving while the other rolls, so even a stuck rollout doesn't drop capacity to zero. If rolling exposes a regression, the follow-up "cold-boot budget" spec from §5 is the response.

- **Image-based sweep fallback misclassifies a legitimate stragger.** [scripts/sweep_stale_blues.sh:80-150](scripts/sweep_stale_blues.sh:80) (spec 0193) destroys machines not on the current release image. Under rolling, mid-rollout there will be a brief window where one machine is on the old image and one is on the new — if the sweep runs *during* that window, it could destroy the old machine prematurely. Mitigation: in the new step 21 matrix, the sweep is only invoked AFTER `fly status` confirms either case 1 (all new) or case 2 (mixed but all healthy). Case 2's "all healthy" gate plus the sweep's gate-4 ("at least one machine on the current image") protect against zeroing the cluster. The pre-existing four-gate cascade at [scripts/sweep_stale_blues.sh:113-150](scripts/sweep_stale_blues.sh:113) was designed for this exact scenario.

- **One-time cleanup fails before merge.** §6's pre-merge action might not be runnable (network blip, Fly API outage, lease error on the zombie destroy itself). Mitigation: the cluster at author time is clean, so the step is most likely a no-op. If it fails for real, halt the spec, fix the cluster manually, then merge. The new strategy must start from a clean cluster.

- **The decision matrix has a case I haven't anticipated.** Five cases is a finite enumeration; reality is messier. Mitigation: case 5 ("`fly status` itself errors") is a catch-all halt — any state that doesn't cleanly match cases 1–4 falls through to "surface the error, do not retry." The matrix biases toward halting, not toward auto-recovery, which is the conservative default.

- **Rolling still races on Fly's machine API during the swap.** The per-machine lease during rolling replacement is briefer than the bluegreen destroy-cohort lease, but it's nonzero. If Fly's machine API has a generic flakiness mode that lease-races trigger, rolling reduces but does not eliminate exposure. Mitigation: the new step 21 matrix handles this — a transient machine-API failure that leaves the cluster mid-rollout (case 4) halts without amplifying, and the next `/dev-next` invocation starts from a clean diagnose-first flow.

---

## 8. User stories & acceptance criteria

### 8.1 — User stories

> As a **dev running `/dev-next`**, I want each `fly deploy` to either succeed cleanly with exactly the target machine count OR fail loudly without spawning zombie machines, so that the cluster never silently drifts into a multi-cohort state across consecutive runs.

> As a **dev whose deploy returned a non-zero exit**, I want the orchestrator to diagnose with `fly status` and route to the matching branch of the decision matrix rather than blindly retrying, so that one transient lease error doesn't compound into three orphan greens.

> As a **dev inheriting the cluster on a fresh day**, I want to see exactly N machines on the latest release image with no stranded blues and no orphan greens, so that "what's running" matches "what's released" without manual reconciliation.

### 8.2 — BDD acceptance scenarios

> **Scenario 1:** rolling deploy succeeds end-to-end with clean cluster.
> GIVEN a healthy 2-machine cluster on release image R, and `fly.toml` configured with `strategy = "rolling"`
> WHEN `fly deploy` runs from `/dev-next` step 21 and returns exit code 0
> THEN `fly machine list -a dual-research-alex --json` reports exactly 2 machines, both with `.config.image` equal to the new release image R+1, and zero machines on R.

> **Scenario 2:** `fly deploy` non-zero exit triggers diagnose-then-decide, never blind retry.
> GIVEN `fly deploy` returned non-zero with a lease-acquisition error mid-rollout
> WHEN `/dev-next` step 21 handles the failure
> THEN the orchestrator runs `fly status -a dual-research-alex` first, classifies the cluster against the §2.2 five-case matrix, runs `scripts/sweep_stale_blues.sh` if (and only if) the matrix routes to case 1 or case 2, and does NOT invoke `fly deploy` a second time within the same `/dev-next` invocation.

> **Scenario 3:** post-cleanup verification — no stranded bluegreen tags.
> GIVEN this spec has shipped and the one-time §6 zombie cleanup completed
> WHEN I run `fly machine list -a dual-research-alex --json | jq '[.[] | .config.metadata.fly_bluegreen_deployment_tag] | unique'`
> THEN the result is either a single value (the tag inherited from the last bluegreen deploy before the strategy switched — vestigial but harmless) OR `[null]` (rolling never set one), and the cluster size matches the target count (2).

> **Scenario 4:** genuine deploy failure halts without amplification.
> GIVEN `fly deploy` returned non-zero AND `fly status` shows only old-version machines (case 3 of the §2.2 matrix)
> WHEN `/dev-next` step 21 routes the failure
> THEN the spec frontmatter is updated to `status: failed, failure_step: deploy`, the `failed` event is emitted, the original `fly deploy` stderr and the `fly status` output are surfaced to the user, AND `fly deploy` is NOT invoked again before the user re-runs `/dev-next`.

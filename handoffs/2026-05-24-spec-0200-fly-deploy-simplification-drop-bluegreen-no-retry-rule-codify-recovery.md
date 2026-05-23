---
spec: "0200"
date: 2026-05-24
version: "1.41.1"
pr: "https://github.com/Lexiz/dual-research/pull/228"
---

# Spec 0200 — Fly deploy simplification: drop bluegreen, no-retry rule, codify recovery

Shipped the three-part deploy-mechanics refactor: `fly.toml` switches to rolling, `/dev-next` step 21 gains a five-case no-retry decision matrix, `scripts/sweep_stale_blues.sh` header comment is updated to reflect its rolling-era role. The first rolling deploy (this spec's own) validated the new strategy end-to-end with zero lease errors and zero zombies.

## What landed

### §2.1 — `fly.toml`: bluegreen → rolling

[fly.toml:20-21](fly.toml:20) now reads `strategy = "rolling"`. The `[deploy]` block comment at [fly.toml:14-19](fly.toml:14) is rewritten to cite spec 0200 and the rolling rationale: bluegreen (spec 0159) reduced cold-boot timeouts but exposed a worse mode — the destroy-lease on the old "blue" cohort races with parallel `flyctl` sessions, leaving zombie machines that accumulate across deploys (see [project_fly_lease_drift_recovery](/Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md) plus handoffs 0187/0188/0189). Rolling replaces machines one at a time in place with no parallel cohort and no destroy-cohort lease, structurally eliminating the race.

`min_machines_running = 1` ([fly.toml:34](fly.toml:34)) and `grace_period = "90s"` ([fly.toml:49](fly.toml:49)) stay as-is — rolling needs both, and the 90s grace remains calibrated for the `shared-cpu-1x:512MB` cold-boot envelope from spec 0159. No `count` setting added; existing 2-machine count stays implicit.

Single-machine immediate was considered and rejected in spec §2.1: it would remove HA entirely and introduce ~30s of downtime per deploy, with no additional simplification of the orchestrator's failure handling beyond what rolling already delivers.

### §2.2 — `/dev-next` step 21: five-case no-retry decision matrix (out-of-band)

[`~/.claude/skills/dev-next/SKILL.md`](file:///Users/alexlisitzky/.claude/skills/dev-next/SKILL.md) step 21 is restructured. The old prose ("On failure: `status: failed, failure_step: deploy`, emit `failed`. Surface, exit.") is replaced by an explicit failure decision matrix that runs `fly status -a dual-research-alex` first on any non-zero `fly deploy` exit and routes by what's actually live:

1. **All machines on new release image, all healthy** → deploy actually succeeded; only post-deploy cleanup or terminal command framing failed. Run sweep, emit `deployed` + `deploy_health_check_ok`, proceed to step 22 as if exit code were 0.
2. **Mixed old/new versions, all healthy** → new image live and serving; Fly didn't fully converge cleanup. Run sweep, mark deployed, proceed.
3. **Only old-version machines present** → genuine failure, no new image live. Set `status: failed, failure_step: deploy`, emit `failed`, surface original stderr + `fly status` output, halt.
4. **Mixed old/new but new is unhealthy** → genuine partial failure. Same halt branch as case 3.
5. **`fly status` itself errors** → halt with original `fly deploy` error. Do not retry; do not run sweep (cluster state unknown).

The **hard rule**: the orchestrator NEVER calls `fly deploy` more than once within one `/dev-next` invocation. The two-shots-per-cycle behavior that amplified the orphan count is eliminated by construction. If the user wants to retry after fixing whatever's wrong, they re-invoke `/dev-next` or fix manually.

Step 21 also now includes a pointer to `project_fly_lease_drift_recovery.md` as the incident-history narrative, calling out the decision matrix as its actionable distillation per spec §2.3.

The success path (exit 0) is unchanged in spirit: capture version, run sweep, emit `deployed`, proceed. It now lives inline in step 21's prose alongside the failure matrix rather than as the only described path.

### §2.4 — `scripts/sweep_stale_blues.sh` header comment

[scripts/sweep_stale_blues.sh:1-42](scripts/sweep_stale_blues.sh:1) header is rewritten to document the rolling-era role: under rolling (spec 0200) the tag-based primary filter routinely finds zero candidates on healthy clusters; the spec-0193 image-based fallback becomes the primary recovery mechanism for any machine the rolling replace didn't fully cycle. The script's runtime behavior is unchanged — the four-gate safety cascade at [scripts/sweep_stale_blues.sh:120-160](scripts/sweep_stale_blues.sh:120) already handles the rolling case correctly.

The output line `sweep: no stale blues on dual-research-alex` ([scripts/sweep_stale_blues.sh ~line 130](scripts/sweep_stale_blues.sh)) is now the expected/healthy signal under rolling, as documented in the new header. Rename of the script itself was decided against in spec §2.4 — the rename cascade through ~25 handoffs + the skill is not worth it for a script whose function is unchanged.

### Version + CHANGELOG

PATCH bump 1.41.0 → 1.41.1 in [pyproject.toml:3](pyproject.toml:3), [src/dual_research/__init__.py:1](src/dual_research/__init__.py:1), and [uv.lock](uv.lock) (downstream of pyproject regen). [CHANGELOG.md](CHANGELOG.md) gains a new `## [1.41.1] — 2026-05-24` section under `### Changed` summarizing the three §2 sections.

### Tests

No new tests. This is a refactoring spec — behavior preservation is asserted by:

- Full pytest suite green: **1774 passed** (same count as pre-spec, matching the post-0199 baseline).
- The first rolling deploy (v557, this spec's own smoke) succeeded cleanly: `[1/2] Acquired lease → updated → checks pass → [2/2] Acquired lease → updated → checks pass → leases cleared` with zero lease errors, exactly the rolling pattern described in §2.1.
- Post-deploy cluster state: 2 machines (2872d65a660408, 879634f0700698), both on release 557, both healthy, no zombies.
- Live smoke: `GET https://dual-research-alex.fly.dev/` → 200; `GET /api/health` → 200 with `{"ok":true,"version":"1.41.1","backend":"supabase"}`.

## Deploy notes

This was the first deploy under the new rolling strategy and the first cycle under the new no-retry rule. Several deploys queued up in series during the cycle from `--push-to-main` event commits + the merge commit + my manual `fly deploy` — Fly's `deploy-main` concurrency group (`.github/workflows/deploy.yml`) serialized them with `cancel-in-progress: false`. The relevant releases:

- v553 (bluegreen, completed at 23:00:06Z) — auto-deploy of the in-progress flip commit + early event sidecars
- v554 (bluegreen, completed at 23:01:28Z) — auto-deploy of subsequent event commits
- v555 (running at first inspection; the *first* rolling deploy in the series, triggered by the PR merge commit at 23:02:55Z) — completed cleanly
- v556 — auto-deploy of subsequent event commits
- v557 (rolling, completed at 23:05:20Z) — my manual `fly deploy` from skill step 21

All releases v555+ shipped under rolling. v557's `fly deploy` log captured cleanly above — no lease drift, no retries, no zombies.

**Stale-blue sweep output:** `sweep: no stale blues on dual-research-alex` — exactly the expected/healthy signal under rolling per the new sweep-script header comment. The tag-based primary filter found zero stale candidates (correct under rolling; the tag is no longer set), and the image-based fallback found no off-image machines (cluster is fully on v557).

**Pre-merge §6 zombie cleanup:** verified the cluster at PR-open time. At that moment v553 was in flight; once v553 + v554 converged, the cluster was 2 machines on identical bluegreen tags, both healthy. No actual zombies present; the cleanup was a verified no-op as anticipated by spec §6.

## Validation against spec §4 behavior-preservation checklist

- [x] `dual-research-alex.fly.dev/` returns 200 after deploy.
- [x] `dual-research-alex.fly.dev/api/health` returns 200 after deploy.
- [x] After deploy: exactly 2 machines on the new version per `fly machine list --json`; zero machines on the prior version.
- [x] After deploy: no machine carries a stale `fly_bluegreen_deployment_tag` from a prior bluegreen deploy (the v557 rolling deploy did not set one; the sweep script found zero candidates).
- [x] `/dev-next` end-to-end on this spec ran without manual intervention through step 24 (modulo one mechanical branch–main merge conflict on the event sidecar — see Deviations).

## Validation against spec §8.2 acceptance scenarios

- **Scenario 1** (rolling deploy succeeds end-to-end with clean cluster): ✅ — v557 shipped with `[1/2] → [2/2]` rolling pattern; 2 machines on the new image, zero on prior.
- **Scenario 2** (non-zero exit triggers diagnose-then-decide): not exercised this cycle (deploy succeeded), but the matrix is now in place at [`~/.claude/skills/dev-next/SKILL.md`](file:///Users/alexlisitzky/.claude/skills/dev-next/SKILL.md) step 21 and ready for the first real failure.
- **Scenario 3** (no stranded bluegreen tags post-cleanup): ✅ — sweep returned `no stale blues on dual-research-alex`; image-based fallback found no off-image machines.
- **Scenario 4** (genuine deploy failure halts without amplification): not exercised; matrix in place, awaiting first real failure to validate live.

## Deviations from spec

- **Event-sidecar merge conflict on PR merge.** When `gh pr merge --admin` ran, it refused with "not mergeable" because `dashboard/events/0200.jsonl` had diverged: the branch carried up to `tests_green`, while main had accumulated `pr_opened` + `merged` events via subsequent `--push-to-main` commits. Resolved manually: `git checkout HEAD -- dashboard/events/0200.jsonl` to discard the locally-appended events (the `append_event` script writes to both the local file AND the temp main checkout when `--push-to-main` is set, leaving an uncommitted local copy), then `git merge origin/main`, resolve the JSONL conflict by taking the union of event lines in chronological order, commit, push, retry the admin-merge. This is a recurring pattern any `/dev-next` cycle will hit when `--push-to-main` events stack up on main while the branch is open — not a spec 0200 regression, but worth noting for a future spec to address (likely "make `append_event --push-to-main` skip the local file write to avoid the divergence").

## Next

Queue head should now be spec 0201 (per spec 0199's handoff: "branch-and-safety-hygiene"). Verify by reading the queue head after this cycle stops.

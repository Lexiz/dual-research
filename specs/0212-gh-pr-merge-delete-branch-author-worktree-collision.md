---
kind: dev
spec: "0212"
slug: gh-pr-merge-delete-branch-author-worktree-collision
title: "Refactor: /dev-next — eliminate the post-merge race window (split `gh pr merge` from branch-cleanup, buffer all post-merge `--push-to-main` writes until step 23)"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
depends_on: ["0210", "0211.2", "0211.3"]
complexity: S
created: 2026-05-25
queued_at: "2026-05-25T09:42:30Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0212 — Refactor: `/dev-next` — eliminate the post-merge race window by (a) splitting `gh pr merge` from branch-cleanup and (b) buffering all post-merge `--push-to-main` writes until step 23's atomic flush

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** 0210 (queue-worktree-detached doctrine), 0211.2 (MERGE_SHA captured at merge time), 0211.3 (concurrency-cancellation pivot)
> **Bump:** PATCH — `/dev-next` skill body change; no app runtime code change
> **Scope consolidation:** this spec closes two distinct frictions that share the same post-merge window (between step 19's `gh pr merge` and step 20's `gh run watch` returning success). The first is the `gh pr merge --delete-branch` author-worktree collision recorded across `handoffs/2026-05-25-spec-0211.1-ci-sweep-flyctl-not-fly-binary.md:46`, `handoffs/2026-05-25-spec-0211.2-merge-sha-capture-race-with-post-merge-pushes.md:40`, and `handoffs/2026-05-25-spec-0211.3-deploy-concurrency-cancels-merge-commit-run.md` (Cycle anomalies — recurred this cycle). The second is the `deploy-main` concurrency-group cancellation race that spec 0211.3's watch-side pivot patches symptomatically — this spec closes the race at its source by removing every `--push-to-main` call between merge and deploy completion, which structurally eliminates the queue-collapse condition the pivot exists to recover from. Bundled because (i) both fixes touch the same step 19/20 window in the same skill body; (ii) both are PATCH refactors with orthogonal mechanics; (iii) shipping them together avoids a second-cycle deferral chain.

---

## 1. Current state

`/dev-next` step 19 invokes `gh pr merge --admin --squash --delete-branch` as a single composite call, then step 20 emits a `--push-to-main` `deploy_started` event before watching the deploy.yml run. Two independent friction surfaces share this window:

### 1a. `gh pr merge --delete-branch` collides with the author worktree's hold on `main`

`gh pr merge --delete-branch` runs `git checkout main` internally to step off the head branch before deleting it. The author worktree at `/Users/alexlisitzky/dual-research-author/` has `main` checked out per `CLAUDE.md` §"Two-worktree split"; git refuses the second checkout and `gh` reports `failed to run git: fatal: 'main' is already used by worktree at '/Users/alexlisitzky/dual-research-author'`.

- **Step 19 invocation** at `~/.claude/skills/dev-next/SKILL.md:292`: `gh pr merge --admin --squash --delete-branch`. The merge itself + remote branch delete succeed BEFORE the local-checkout attempt; the operator-visible failure is only the local-cleanup half.
- **The post-merge verified-delete block** at `~/.claude/skills/dev-next/SKILL.md:306`–`:323` (spec 0201 §2.1) catches and recovers — it operates on branch refs by name without `git checkout main` — but every cycle pays the recovery cost and pollutes the handoff with the warning.
- **Why spec 0210 didn't close this**: spec 0210 keeps the queue worktree detached; the collision is with the AUTHOR worktree, whose hold on `main` is structural per the spec workflow. Spec 0210 is necessary but not sufficient.
- **Recurrence record**: three consecutive cycles have hit this warning (0211.1, 0211.2, 0211.3). The 0211.2 handoff at `handoffs/2026-05-25-spec-0211.2-merge-sha-capture-race-with-post-merge-pushes.md:40` named the threshold: "If this becomes a habit, worth a small spec." It is a habit.

### 1b. Post-merge `--push-to-main` writes cancel the merge-commit's deploy run via the `deploy-main` concurrency group

`.github/workflows/deploy.yml`'s concurrency policy at `:27`–`:29` is `group: deploy-main` with `cancel-in-progress: false`. `cancel-in-progress: false` protects the in-flight job only; GitHub Actions still applies a queue-collapse rule for *pending* runs in the same group — when ≥ 2 runs are queued behind an in-flight job, the older pending runs are cancelled and only the newest pending run survives.

- **The race window** is between step 19's `gh pr merge` (which pushes the squash-merge commit to `origin/main` and queues deploy run M) and step 20's `gh run watch` returning success for M. Every `--push-to-main` call inside that window adds another commit to `origin/main` and queues another deploy.yml run in the same `deploy-main` group. Two such calls (plus the merge run itself) trigger the queue-collapse rule.
- **Current post-merge `--push-to-main` calls** (between merge and deploy completion):
  - **Step 20** at `~/.claude/skills/dev-next/SKILL.md:342`: `append-event --push-to-main NNNN deploy_started '{}'` — fires immediately after `gh pr merge` and before `gh run watch`. This is the first race-amplifying push.
  - **Step 20 pivot path** at `~/.claude/skills/dev-next/SKILL.md` (post-0211.3 shape): on `cancelled`, `append-event --push-to-main NNNN deploy_pivoted '{...}'` runs before the second watch — adds yet another push during the pivot's race window.
  - **Step 20 happy-path completion** at `~/.claude/skills/dev-next/SKILL.md:372`: `append-event --push-to-main NNNN deployed '{...}'` — runs AFTER `gh run watch` returns success, so it's outside the race window for M but still adds main-side noise.
  - **Step 21** at `~/.claude/skills/dev-next/SKILL.md`: `append-event --push-to-main NNNN deploy_health_check_ok '{}'` — also after deploy completes, but still inside the broader "between merge and step 23" window.
  - **`queue_state.py:373`–`:402`** retry loop can amplify any of the above into multiple commits under non-fast-forward pressure.
- **What spec 0211.3 added** (the symptom-patch): a watch-side pivot block at `~/.claude/skills/dev-next/SKILL.md` step 20 that detects `cancelled` and re-watches the latest `origin/main` run. The pivot's correctness depends on an emergent property — that `--push-to-main` commits don't change Docker layers, so the pivoted run ships an image-equivalent build. The pivot also opens new edge cases: ≥ 3 racing pushes (recursive pivot) and the image-equivalence regression vector. Both edge cases are the deferrals the 0211.3 handoff named.
- **Why this is structurally guaranteed under the current skill body**: every cycle that hits the cancellation window does so because the skill body MUST emit `deploy_started` between merge and watch (it's the current contract). The race is not a probabilistic anomaly; it's a contract-level consequence of where `--push-to-main` calls are placed.

### 1c. The pre-flight buffered-events clobber bug (spec 0211.2 cycle history)

Documented at `handoffs/2026-05-25-spec-0211.2-merge-sha-capture-race-with-post-merge-pushes.md:44`: `queue_state set --push-to-main` rebuilds the spec's entry from `origin/main` before pushing, which discards any local-only `append-event` writes buffered before the `set` call. Today this affects only the pre-flight events (`cycle_started`, `preflight_ok`, etc.) because no other code path mixes local-only events with `set --push-to-main`. Under this spec's buffer-events doctrine the same shape could affect post-merge events if any `set --push-to-main` ran between merge and step 23. Step 23's existing structure already uses local-only `set` followed by `push-files-to-main`; the doctrine extends that pattern by ensuring no `set --push-to-main` runs between merge and step 23 on the happy path.

**Pain points:**

- **Author-worktree warning recurs every cycle** (1a). Operators read each occurrence to confirm it's the known class — three cycles in a row of cumulative noise.
- **The merge-commit's deploy run is unreliable on its own terms** (1b). Today the cycle ships because of the emergent property that all post-merge `--push-to-main` writes ship Docker-identical images. The correctness of every `/dev-next` cycle depends on no `--push-to-main` caller ever accidentally landing code in the post-merge window — an undocumented invariant.
- **The 0211.3 pivot block is symptom-patching**, not root-fixing. It works, but it's defensive code for a race that shouldn't exist in the first place. Keeping it as live happy-path code obscures the race; demoting it to a defensive regression-detector (per §2 below) makes the design intent legible.
- **Two queued follow-up deferrals from 0211.3** (recursive-pivot guard, image-SHA cross-check) are both consequences of the pivot being a symptom-patch. Closing the race eliminates the need for both.

## 2. Target state

`/dev-next` issues `gh pr merge --admin --squash` (WITHOUT `--delete-branch`), deletes the head branch explicitly, and emits ALL post-merge events between step 19's merge and step 23's atomic flush via local-only `append-event` writes. The 0211.3 pivot block stays in step 20 as a defensive regression-detector but is documented as expected-inert under the new doctrine; if it ever fires, a regression has been introduced (a new `--push-to-main` caller landed in the post-merge window).

The fix is entirely in the `/dev-next` skill body. No change to `.github/workflows/deploy.yml`, no change to `scripts/spec_lifecycle/queue_state.py`, no change to app runtime code.

### 2a. Split merge from branch-cleanup (closes 1a)

- **Step 19's merge invocation** at `~/.claude/skills/dev-next/SKILL.md:292` drops `--delete-branch`:
  ```bash
  gh pr merge --admin --squash
  ```
  GitHub REST API squash-merge with admin override. `gh` touches no local git state.

- **New: explicit branch-cleanup block** added directly after the `MERGE_SHA` capture block (which currently ends at `~/.claude/skills/dev-next/SKILL.md:304`) and before the "Verified delete after merge" block at `:306`:
  ```bash
  # spec 0212: delete the head branch explicitly. `gh pr merge --delete-branch`
  # used to run `git checkout main` internally, which collides with the author
  # worktree at /Users/alexlisitzky/dual-research-author/ that holds main per
  # CLAUDE.md's two-worktree split. Doing the deletes by name avoids the checkout.
  BRANCH="spec/${SPEC_ID}-${SLUG}"   # SPEC_ID is NNNN or NNNN.M per spec 0199 grammar
  git push origin --delete "$BRANCH" 2>/dev/null || true
  git branch -D "$BRANCH" 2>/dev/null || true
  ```
  The `2>/dev/null || true` is intentional: if the remote branch was already deleted or the local branch doesn't exist (the queue worktree is detached per spec 0210), the deletes are no-ops. The verified-delete block at `~/.claude/skills/dev-next/SKILL.md:306`–`:323` is the authoritative absence check.

- **The verified-delete block** at `~/.claude/skills/dev-next/SKILL.md:306`–`:323` stays unchanged. Its retry path remains as the authoritative correctness guard for genuine delete failures (network blip, permissions glitch).

### 2b. Buffer all post-merge `--push-to-main` writes until step 23 (closes 1b)

The buffer doctrine: **between step 19's `gh pr merge` call and step 23's `push-files-to-main` flush, no `--push-to-main` invocation runs on the happy path.** Failure paths still push immediately so the dashboard reflects halts in real time.

- **Step 20's `deploy_started` emission** at `~/.claude/skills/dev-next/SKILL.md:342` drops `--push-to-main`:
  ```bash
  uv run python -m scripts.spec_lifecycle.queue_state append-event NNNN deploy_started '{}'
  ```
  Local-only write to `dashboard/queue-state.json`. No new commit to `origin/main`. No new deploy.yml run queued. The merge-commit's run M is the only run in the `deploy-main` group during step 20's poll + watch.

- **Step 20's `deployed` emission** at `~/.claude/skills/dev-next/SKILL.md:372` drops `--push-to-main`:
  ```bash
  uv run python -m scripts.spec_lifecycle.queue_state append-event NNNN deployed "{\"version\":\"$VERSION\"}"
  ```
  Local-only. Step 23 pushes all accumulated events in one commit alongside the handoff/archive.

- **Step 20's pivot-path emissions** stay as defensive code but switch to local-only too:
  ```bash
  uv run python -m scripts.spec_lifecycle.queue_state append-event NNNN deploy_pivoted "{\"original_run\":\"$RUN_ID\",\"pivot_run\":\"$PIVOT_RUN_ID\",\"merge_sha\":\"$MERGE_SHA\",\"pivot_sha\":\"$LATEST_SHA\"}"
  ```
  Under the new doctrine the pivot block should never fire (no concurrency cancellation possible because no newer runs queue in the window). If it does fire, the event records the anomaly in the local buffer; step 23 flushes it to main along with everything else; the dashboard surfaces it as a regression signal.

- **Step 20's failure-path emissions** stay as `--push-to-main`:
  ```bash
  # deploy_run_not_found halt:
  uv run python -m scripts.spec_lifecycle.queue_state set --push-to-main NNNN status=failed failure_step=deploy
  uv run python -m scripts.spec_lifecycle.queue_state append-event --push-to-main NNNN failed '{"reason":"deploy_run_not_found"}'
  # real-failure halt:
  uv run python -m scripts.spec_lifecycle.queue_state set --push-to-main NNNN status=failed failure_step=deploy
  uv run python -m scripts.spec_lifecycle.queue_state append-event --push-to-main NNNN failed "{\"run_url\":\"$RUN_URL\",\"conclusion\":\"$CONCLUSION\"}"
  ```
  On halt the cycle exits anyway, so there's no subsequent step 23 to flush local events. Push immediately so the dashboard reflects the halt.

- **Step 21's `deploy_health_check_ok` emission** drops `--push-to-main`:
  ```bash
  uv run python -m scripts.spec_lifecycle.queue_state append-event NNNN deploy_health_check_ok '{}'
  ```
  Local-only. Flushed by step 23.

- **Step 22's `handoff_written` emission** drops `--push-to-main`:
  ```bash
  uv run python -m scripts.spec_lifecycle.queue_state append-event NNNN handoff_written '{"path":"handoffs/<file>"}'
  ```
  Local-only. Flushed by step 23.

- **Step 23's structure is already buffer-friendly**: it currently calls local-only `set` + local-only `append-event deployed`, then `push-files-to-main` to atomically commit `dashboard/queue-state.json` + the handoff + any archive churn. All the events buffered above land in that same atomic commit. No change to step 23's invocation pattern.

- **The 0211.3 pivot block stays in step 20** as defensive code. Its comment is updated to cite spec 0212:
  ```
  # spec 0211.3 pivot: defensive — should never fire under the spec 0212
  # buffer-events doctrine (no --push-to-main calls between merge and step 23
  # → no newer deploy.yml runs queue behind the merge-commit run → no
  # concurrency-group cancellation). If this block ever fires, a regression
  # has been introduced (a new --push-to-main caller landed in the post-merge
  # window). The buffered deploy_pivoted event will surface it.
  ```
  The pivot logic itself is unchanged; only the comment is updated.

### 2c. Why this is the right closure

- **The author-worktree collision becomes structurally impossible** (1a closed): `gh pr merge --admin --squash` no longer runs `git checkout main`. The author worktree's hold on `main` is irrelevant.
- **The concurrency cancellation becomes structurally impossible on the happy path** (1b closed at source): no `--push-to-main` runs between merge and `gh run watch` returning, so the merge-commit's deploy run M has no newer queued runs behind it in the `deploy-main` group. The queue-collapse rule cannot trigger.
- **The 0211.3 pivot block becomes a regression-detector** instead of live happy-path code. If a future spec adds a new `--push-to-main` caller in the post-merge window, the pivot fires and the `deploy_pivoted` event signals the regression. The block is small (~30 lines); keeping it is cheaper than reasoning about future regressions.
- **The 0211.3 follow-up deferrals are now moot** (recursive-pivot guard, image-SHA cross-check). Both exist only because the pivot is happy-path code. Demoted to defensive code, both deferrals dissolve.

## 3. Stepwise migration

Each step independently shippable / revertable. The SKILL.md edits land in the `/dev-next` cycle that runs this spec; the skill file is outside the repo, so the spec's git commit contains only the test + version bump + CHANGELOG artifacts.

- **Step 1: Drop `--delete-branch` from `~/.claude/skills/dev-next/SKILL.md:292`.** Change the line to `gh pr merge --admin --squash`.
  - Verified by: post-cycle, step 19's body contains `gh pr merge --admin --squash` and does NOT contain `--delete-branch`.

- **Step 2: Add the explicit-cleanup block in step 19** (per §2a above), inserted after the `MERGE_SHA` capture block and before the verified-delete block.
  - Verified by: post-cycle, step 19's body contains `git push origin --delete "$BRANCH"` AND `git branch -D "$BRANCH"` immediately after the `MERGE_SHA` capture block.

- **Step 3: Convert post-merge happy-path event emissions to local-only** in steps 20, 21, 22 (per §2b above). Five specific lines change: step 20's `deploy_started`, step 20's `deployed` (happy path), step 20's `deploy_pivoted` (pivot path), step 21's `deploy_health_check_ok`, step 22's `handoff_written`. Each drops the `--push-to-main` flag. Failure-path emissions (the two `failed` paths in step 20) keep `--push-to-main`.
  - Verified by: post-cycle, step 20's body emits `deploy_started`, `deployed`, and `deploy_pivoted` without `--push-to-main`; step 21's `deploy_health_check_ok` and step 22's `handoff_written` likewise; the two step-20 failure paths retain `--push-to-main` on `set status=failed` and `append-event failed`.

- **Step 4: Update the 0211.3 pivot block's comment to cite spec 0212** (per §2b above). The pivot logic is unchanged; only the explanatory comment is updated to mark the block as defensive-only under the new doctrine.
  - Verified by: post-cycle, step 20's pivot-block comment contains `spec 0212 buffer-events doctrine` or equivalent prose marking the block as defensive.

- **Step 5: Add a source-pattern test at `tests/test_spec_0212_post_merge_doctrine.py`.** Pure stdlib, same `_step_block` doctrine as `tests/test_spec_0211_2_merge_sha_captured_at_merge_time.py:31`. Six assertions:
  - Step 19 does NOT contain `--delete-branch`.
  - Step 19 contains both `gh pr merge --admin --squash` AND `git push origin --delete`.
  - Step 19 contains a `spec 0212` breadcrumb comment.
  - Step 20's `deploy_started` line does NOT contain `--push-to-main`.
  - Step 20's `deployed` line (happy path) does NOT contain `--push-to-main`.
  - Step 20's `failed` lines (both failure paths) DO contain `--push-to-main`.
  - Verified by: `uv run pytest tests/test_spec_0212_post_merge_doctrine.py -v` green; the test asserts SKIP when SKILL.md is absent (CI doesn't carry the user's skill files).

- **Step 6: PATCH version bump + CHANGELOG.** Bump `pyproject.toml`, `src/dual_research/__init__.py`, refresh `uv.lock`. Add a `## [X.Y.Z] — YYYY-MM-DD` section to `CHANGELOG.md` under `### Changed` citing this spec.
  - Verified by: dashboard at `https://lexiz.github.io/dual-research/` renders the new CHANGELOG entry post-deploy.

- **Step 7: Verify next cycle's handoff is collision-free AND pivot-inert.** Observation-only — the cycle that ships this spec writes a handoff whose body should NOT contain `is already used by worktree` (1a closed) AND should NOT cite a `deploy_pivoted` event (1b closed; pivot block should not fire).
  - Verified by: post-cycle, `handoffs/YYYY-MM-DD-spec-0212-...md` contains neither substring.

## 4. Behavior preservation

- [ ] Existing `tests/` suite passes unchanged — `~/.claude/skills/dev-next/SKILL.md` is not part of the repo's pytest collection; the new test is additive.
- [ ] `tests/test_spec_0211_2_merge_sha_captured_at_merge_time.py` continues to pass — its assertions (no `git rev-parse origin/main` in step 20; `gh pr view ... mergeCommit` in step 19; `spec 0211.2` breadcrumb in step 19) are orthogonal to both fixes.
- [ ] `tests/test_spec_0211_3_concurrency_pivot.py` continues to pass — its assertions (`WATCH_RC` capture in step 20; `git ls-remote origin main` + `cancelled` tokens in step 20; `spec 0211.3` breadcrumb in step 20) are orthogonal to this spec's changes. The pivot block stays in place; only its comment is updated.
- [ ] `tests/test_spec_0211_no_local_fly_deploy.py` continues to pass — its assertions (no bare `fly deploy`, `gh run watch` + `deploy.yml` referenced) are orthogonal.
- [ ] Spec 0201's verified-delete invariant at `~/.claude/skills/dev-next/SKILL.md:306`–`:323` continues to enforce that the head branch is gone from both sides. After this spec, the verified-delete usually finds both already zero (because the new explicit-cleanup block ran first).
- [ ] Spec 0210's queue-worktree-detached doctrine is preserved — the re-detach at `origin/main` still runs after the verified-delete confirms branch cleanup.
- [ ] Spec 0202's queue-state-in-state-file invariant is preserved — all events still land in `dashboard/queue-state.json`. The only change is WHEN they're pushed to `origin/main` (atomically at step 23 instead of one-by-one).
- [ ] `dashboard/events/NNNN.jsonl` event ordering is preserved — `deploy_started`, `deployed`, `deploy_health_check_ok`, `handoff_written`, `deployed` (step 23's), `archive_*` arrive in the same sequence. The buffer-doctrine changes only the commit-timing of each event, not its order or payload.
- [ ] `scripts/spec_lifecycle/render_dashboard.py` is unchanged — it tolerates unknown event types; the existing renderer reads the JSONL with no schema assumption beyond `event.get("type", "")`.
- [ ] `gh pr merge --admin --squash` continues to perform the squash-merge with admin override. `gh pr view --json mergeCommit` at the subsequent line returns the same SHA shape.
- [ ] The `--push-to-main` plumbing at `scripts/spec_lifecycle/queue_state.py:354`–`:402` is unchanged. Failure-path callers still use it directly.
- [ ] `.github/workflows/deploy.yml` is unchanged — same `concurrency.group: deploy-main` at `:27`–`:29`, same `cancel-in-progress: false`, same `flyctl deploy --remote-only`. The fix is entirely in the `/dev-next` skill body.

## 5. Out of scope

**Explicit: this spec does NOT add any new feature.** No new feature surfaces — no new dashboard signals, no new `/dev-next` skills, no changes to the deploy.yml workflow, no changes to the verified-delete halt guard. It changes how step 19's branch cleanup is invoked and where step 20+21+22's events are committed to `origin/main`.

- **Setting `git config alias.merge-without-checkout`** (alternative (a) from `handoffs/2026-05-25-spec-0211.2-merge-sha-capture-race-with-post-merge-pushes.md:40`). Rejected — couples the fix to per-machine git config, invisible from the skill body. (Deferred to: no follow-up planned.)
- **Post-processing `gh pr merge`'s stderr to detect the checkout error and skip cleanup** (alternative (b) from the same handoff line). Rejected — brittle to `gh` and git version drift. (Deferred to: no follow-up planned.)
- **Restructuring the author worktree to NOT hold `main`** (moving the author worktree to detached HEAD). Rejected — the author worktree's hold on `main` is structural per `CLAUDE.md`'s spec workflow; spec-creation skills (`/spec-draft`, `/spec-queue`, `/spec-promote`) write to `main` and need a held branch ref. (Deferred to: future spec only if a second class of cross-worktree collision appears.)
- **Loosening `.github/workflows/deploy.yml`'s `concurrency.group` to allow per-SHA runs.** Rejected (originally in 0211.3 §5): per-SHA grouping would allow multiple deploys to race for the same Fly app's machines, defeating serialisation. (Deferred to: no follow-up planned.)
- **Sequencing `--push-to-main` calls so no queue-state push fires until after the merge run completes** (alternative (b) from 0211.2's handoff, originally deferred by 0211.3). **No longer deferred — this spec IS that fix.** Implemented as the buffer-events doctrine in §2b. (Closed by this spec.)
- **Removing the 0211.3 pivot block entirely.** Rejected — under the new doctrine the block becomes a defensive regression-detector for "did a new `--push-to-main` caller leak into the post-merge window?" The cost (~30 lines of inert bash) is small; the value (catching a silent future regression) is high. (Deferred to: future spec only if the block costs more than it saves — no current signal it does.)
- **Recursive-pivot guard for ≥ 3 concurrent `--push-to-main` writes** (originally deferred by 0211.3). **Now moot.** Under the buffer-events doctrine, no `--push-to-main` runs in the post-merge window on the happy path; the recursive case requires three such writes in the same window, which the doctrine forbids. The defensive pivot block's existing `set -e` halt-on-second-failure remains a sufficient last-ditch guard for the impossible-but-not-disallowed case. (Closed by this spec.)
- **Image-SHA cross-check on the pivoted run** (originally deferred by 0211.3). **Now moot.** The check existed to guard the emergent property that `--push-to-main` commits don't change Docker layers. Under this doctrine no `--push-to-main` runs in the post-merge window at all, so the pivot block doesn't fire and there's no pivoted run to cross-check. If the pivot ever fires (regression signal), the operator's response is "find the leaking `--push-to-main` caller and fix the regression", not "validate the pivoted run's image". (Closed by this spec.)
- **Generalising the buffer-events doctrine to other windows** (e.g., the pre-flight buffered-events clobber bug at 1c). Today only the post-merge window has a concurrency-group race. The pre-flight window's clobber bug is independently tolerable (the buffered events are diagnostic, not load-bearing). If a future spec adds a `--push-to-main` caller in another concurrency-sensitive window, extend the doctrine there. YAGNI. (Deferred to: future spec when a second concurrency-sensitive window emerges.)
- **Fixing the `queue_state set --push-to-main` clobber bug** (per 1c above). The buffer-events doctrine avoids the bug by ensuring no `set --push-to-main` runs between local-event-writing and `push-files-to-main`. The bug itself is in `scripts/spec_lifecycle/queue_state.py`'s set+push interaction; fixing it would require restructuring how `set --push-to-main` merges local + remote state. Out of scope here — the doctrine sidesteps it. (Deferred to: future spec if a third caller hits the same clobber pattern.)
- **Adding a backstop sweep for branches that survive the explicit-delete + verified-delete combo.** `scripts/sweep_stale_branches.sh` (spec 0201 §2.4) already exists. (Deferred to: no follow-up planned.)
- **Touching `~/.claude/projects/-Users-alexlisitzky/memory/`.** No memory file references the post-merge race or the `gh pr merge --delete-branch` collision. (Deferred to: no follow-up planned.)

## 6. Risks

- **Risk: `gh pr merge --admin --squash` (without `--delete-branch`) behaves differently from the composite call.** *Mitigation:* `gh`'s documented behavior is that flags are independent — `--delete-branch` controls only the post-merge cleanup, not the merge itself. The merge call's API contract (squash-merge with admin override) is identical with or without `--delete-branch`. Verified against `gh version 2.x` man page.

- **Risk: `git push origin --delete "$BRANCH"` fails on a transient API issue.** *Mitigation:* `||true` swallows the exit code; the verified-delete block at `~/.claude/skills/dev-next/SKILL.md:306`–`:323` is the authoritative absence check and retries the same calls.

- **Risk: `git branch -D` fails because the local branch doesn't exist in the detached queue worktree.** *Mitigation:* `||true` swallows it; the call is a no-op in the spec-0210-compliant queue worktree. Verified-delete confirms absence.

- **Risk: a future spec re-introduces `--delete-branch` because someone forgets the worktree-collision rationale.** *Mitigation:* the source-pattern test at step 5 asserts step 19 does NOT contain `--delete-branch`; the `spec 0212` breadcrumb comment near the cleanup block makes the rationale discoverable.

- **Risk: local-only buffered events get clobbered if a future caller introduces a `set --push-to-main` between merge and step 23.** *Mitigation:* the buffer-events doctrine forbids this, and the source-pattern test at step 5 locks the failure-vs-happy-path split (failure-path `--push-to-main` retained; happy-path `--push-to-main` dropped). A future regression that adds a happy-path `--push-to-main` between merge and step 23 fails the test immediately. The defensive 0211.3 pivot block is the second line of defence — if the test missed it but the actual cycle hit cancellation, the pivot fires and the `deploy_pivoted` event surfaces the regression on the dashboard.

- **Risk: step 23's `push-files-to-main` flush fails for an unrelated reason and the buffered events stay local-only, never reaching `origin/main`.** *Mitigation:* `push-files-to-main` is the same plumbing used today for the handoff push; its failure mode is the same shape (network blip, non-fast-forward) with the same `:373`–`:402` retry loop. No new failure surface. If the flush still fails after the retry loop, the cycle halts with the events still buffered locally; the operator can re-run `push-files-to-main` manually. The local file is the source of truth; the push is recoverable.

- **Risk: dashboard rendering breaks because events arrive in a single commit instead of one-by-one.** *Mitigation:* `scripts/spec_lifecycle/render_dashboard.py` reads `dashboard/events/NNNN.jsonl` (or queue-state) line-by-line with no commit-boundary assumption. Events arrive in the same JSONL order regardless of how many commits land them. Renderer tested against multi-event commits today (step 23 already lands `deployed` + `deployed` from set together).

- **Risk: the 0211.3 pivot block becomes truly dead code and rots.** *Mitigation:* the source-pattern test at `tests/test_spec_0211_3_concurrency_pivot.py` continues to enforce the block's structure. If a future spec wants to remove the block (because the buffer doctrine has held for many cycles), it explicitly does so with its own test removal — not via silent drift.

- **Risk: the cycle that runs this spec hits the very cancellation 0211.3's pivot was designed for (because the buffer-events fix lands in the same cycle that needs it).** *Mitigation:* steps 1+2+3+4 of this spec apply to `~/.claude/skills/dev-next/SKILL.md` BEFORE the cycle calls step 20. The skill body is re-read at each step; by the time step 20 runs, the buffer-events fix is in place. The pivot block, if any cancellation does fire, picks up the fallback automatically. If the cycle ships cleanly without the pivot firing, the handoff records that as evidence the fix works at source.

- **Risk: source-pattern test is brittle to SKILL.md prose changes.** *Mitigation:* `_step_block` helper scopes each assertion to the specific step number. Prose changes outside the asserted steps don't trip the test.

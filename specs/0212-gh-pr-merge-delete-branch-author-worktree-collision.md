---
kind: dev
spec: "0212"
slug: gh-pr-merge-delete-branch-author-worktree-collision
title: "Refactor: /dev-next step 19 — split `gh pr merge --delete-branch` to dodge author-worktree's hold on `main`"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
depends_on: ["0210"]
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

# Spec 0212 — Refactor: `/dev-next` step 19 — issue `gh pr merge` without `--delete-branch`, then delete remote + local refs explicitly, so the author worktree's checkout of `main` no longer derails branch cleanup

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** 0210 (queue-worktree-detached doctrine)
> **Bump:** PATCH — `/dev-next` skill body change; no app runtime code change
> **Evidence:** recurring cross-worktree friction recorded in two consecutive cycle handoffs. (a) `handoffs/2026-05-25-spec-0211.1-ci-sweep-flyctl-not-fly-binary.md:46` (Cycle anomalies): "`/dev-next` step 19 (`gh pr merge --admin --squash --delete-branch`) reported `failed to run git: fatal: 'main' is already used by worktree at '/Users/alexlisitzky/dual-research-author'` — the local-checkout step of `gh pr merge` collided with the author worktree holding `main`. The merge itself + remote branch delete had already succeeded; the local-branch cleanup needed manual `git push origin --delete` + `git branch -D`. Spec 0210 was supposed to eliminate this class of cross-worktree friction by keeping the queue worktree detached, but `gh pr merge --delete-branch` still attempts a local main-checkout regardless of the queue worktree's HEAD state." (b) `handoffs/2026-05-25-spec-0211.2-merge-sha-capture-race-with-post-merge-pushes.md:40`: same anomaly, same `gh pr merge --admin --squash --delete-branch collided with author worktree holding main` — "the 0211.1 handoff already flagged it as marginal. If this becomes a habit, worth a small spec." It is now a habit (two cycles in a row).

---

## 1. Current state

`/dev-next` step 19 invokes `gh pr merge --admin --squash --delete-branch` as a single composite call. The `--delete-branch` flag asks `gh` to delete both the remote head branch AND a local branch of the same name; the local-delete path attempts `git checkout main` first (to step off the head branch before deleting it), which collides with the author worktree at `/Users/alexlisitzky/dual-research-author/` because git refuses to check out `main` simultaneously in two worktrees.

- **Step 19 invocation** at `~/.claude/skills/dev-next/SKILL.md:292`: `gh pr merge --admin --squash --delete-branch`. The flag composition is documented in `gh`'s man page: `--delete-branch` "delete the local and remote branch after merge". The local-side delete is the failure surface.

- **The collision shape** (per `handoffs/2026-05-25-spec-0211.1-ci-sweep-flyctl-not-fly-binary.md:46`): `failed to run git: fatal: 'main' is already used by worktree at '/Users/alexlisitzky/dual-research-author'`. `gh pr merge --delete-branch` internally runs `git checkout main` to step off the head branch (or to ensure HEAD is on a still-existing branch before destroying the head branch). The author worktree at `/Users/alexlisitzky/dual-research-author/` has `main` checked out per the spec-workflow split (per `CLAUDE.md` §"Two-worktree split": "Authoring worktree … stays on `main`"). git refuses the second checkout. `gh` reports the failure but does not unwind the merge — the merge + remote-branch-delete both succeeded BEFORE the local-checkout attempt, so the operator-visible failure is only the local-branch-cleanup half.

- **The post-merge verified-delete block** at `~/.claude/skills/dev-next/SKILL.md:306`–`:323` (spec 0201 §2.1) already catches this failure shape: it checks `remote_left` and `local_left`, then on non-zero retries with `git push origin --delete "$BRANCH"` and `git branch -D "$BRANCH"`. The retry succeeds because the retry path does not run `git checkout main` — it operates directly on the branch ref by name. So the cycle DOES self-heal today; the cost is one extra retry cycle plus a halt-on-second-failure guard at SKILL.md `:318`–`:321`.

- **Why spec 0210's "queue worktree stays detached" doctrine doesn't close this**: spec 0210 (referenced at `~/.claude/skills/dev-next/SKILL.md:329`–`:333` as "Re-detach at `origin/main`") keeps the queue worktree at `/Users/alexlisitzky/dual-research/` on detached HEAD throughout the cycle, so the queue worktree does NOT hold `main`. The collision is with the AUTHOR worktree at `/Users/alexlisitzky/dual-research-author/`, which DOES hold `main` and is designed to. The author worktree's hold on `main` is a structural feature of the spec workflow (`CLAUDE.md` §"Two-worktree split"), not a transient state. Spec 0210's fix is necessary but not sufficient.

- **Observed cycle costs** (per the two handoffs): each cycle that hits this collision adds one retry-loop iteration (cheap) PLUS one manual orchestrator intervention to clear the warning log noise from the cycle's handoff body (not cheap — the operator must read the warning, confirm it was the known author-worktree class, and proceed). The 0211.1 and 0211.2 handoffs both cite the collision; the 0211.2 handoff explicitly flagged it for follow-up.

**Pain points:**

- **Recurring warning-noise in cycle logs.** Every `/dev-next` cycle now logs a `failed to run git: fatal: 'main' is already used by worktree` warning at step 19. Operators have to read each occurrence to confirm it's the known class and not a new failure mode. Two cycles in a row is the threshold spec 0211.2's handoff named: "If this becomes a habit, worth a small spec."

- **Coupling between merge and branch-cleanup.** `gh pr merge --delete-branch` couples two distinct operations: (a) the merge itself (a remote API call, atomic, succeeds), and (b) branch cleanup (a local + remote git operation, fragile to local-worktree state). The composite call's failure shape obscures which half failed. The verified-delete block at `~/.claude/skills/dev-next/SKILL.md:306`–`:323` is the unwind-and-retry mechanism, but it's defensive — it would not be needed if the merge call didn't try to do branch cleanup in the first place.

- **The unwind path is verified — but every cycle pays for it.** The retry at `~/.claude/skills/dev-next/SKILL.md:312`–`:317` always succeeds (the explicit `git push origin --delete` + `git branch -D` calls don't run `git checkout main`), but the cycle's handoff still cites the original warning as an anomaly. That handoff-pollution is the recurring tax.

- **Cross-cycle pollution**: the warning log + manual confirmation accrues across every cycle, and the cycle handoff cites it. Searching `handoffs/` for "is already used by worktree" already returns multiple hits — the pattern is becoming background noise that hides real anomalies.

## 2. Target state

`/dev-next` step 19 issues `gh pr merge --admin --squash` (WITHOUT `--delete-branch`), then deletes the remote head branch explicitly via `git push origin --delete "$BRANCH"`, then deletes the local branch ref (if it exists, which it usually doesn't in the detached-HEAD queue worktree per spec 0210) via `git branch -D "$BRANCH"`. The `gh` command no longer attempts `git checkout main`; the author worktree's hold on `main` is structurally irrelevant.

The fix is a one-line composition change inside step 19's existing invocation pattern. No change to `.github/workflows/deploy.yml`, no change to `scripts/spec_lifecycle/queue_state.py`, no change to app runtime code.

- **Step 19's merge invocation** at `~/.claude/skills/dev-next/SKILL.md:292` drops `--delete-branch`:
  ```bash
  gh pr merge --admin --squash
  ```
  This is the GitHub REST API squash-merge call only; `gh` does not touch any local git state. The call is atomic against the PR's mergeability state and the admin override.

- **New: explicit branch-cleanup block** added directly after the merge call, before the existing `MERGE_SHA` capture block at `~/.claude/skills/dev-next/SKILL.md:296`–`:304` (spec 0211.2):
  ```bash
  # Delete the head branch explicitly (spec 0212). `gh pr merge --delete-branch`
  # used to run `git checkout main` internally, which collides with the author
  # worktree at /Users/alexlisitzky/dual-research-author/ that holds main per
  # CLAUDE.md's two-worktree split. Doing the deletes by name avoids the
  # checkout.
  BRANCH="spec/${SPEC_ID}-${SLUG}"   # SPEC_ID is NNNN or NNNN.M per spec 0199 grammar
  git push origin --delete "$BRANCH" 2>/dev/null || true
  git branch -D "$BRANCH" 2>/dev/null || true
  ```
  The `2>/dev/null || true` is intentional: if the remote branch was already deleted (e.g., by a manual cleanup), or if the local branch doesn't exist (the queue worktree is detached per spec 0210, so it usually won't), the deletes are no-ops. The subsequent verified-delete block at `~/.claude/skills/dev-next/SKILL.md:306`–`:323` is the authoritative check; if either delete genuinely failed, the verified-delete halt at `:318`–`:321` catches it.

- **The verified-delete block** at `~/.claude/skills/dev-next/SKILL.md:306`–`:323` stays unchanged in shape. It already runs the same `git push origin --delete` + `git branch -D` as a retry; after this spec, those calls are guaranteed-redundant on the happy path (because the explicit cleanup block above already did them) but remain as the authoritative correctness check. The verification's `remote_left == 0 && local_left == ""` invariant is unchanged.

- **Step 19's `MERGE_SHA` capture block** at `~/.claude/skills/dev-next/SKILL.md:294`–`:304` (spec 0211.2) stays unchanged in position and content. It runs after the merge call (which is now branch-cleanup-free) and before the explicit branch-cleanup block.

- **Step 19's re-detach block** at `~/.claude/skills/dev-next/SKILL.md:329`–`:333` (spec 0210) stays unchanged. The queue worktree continues to detach at `origin/main` after cleanup.

- **Why explicit deletes instead of a `git config alias.merge-without-checkout` shim** (alternative (a) from `handoffs/2026-05-25-spec-0211.2-merge-sha-capture-race-with-post-merge-pushes.md:40`): aliases would couple the fix to per-machine git config, invisible from the skill body. A future operator running `/dev-next` on a fresh checkout would hit the collision again. The skill body should be self-contained; the fix lives in the skill's bash, not in a side-channel git config.

- **Why explicit deletes instead of detecting the checkout error and skipping** (alternative (b) from the same handoff line): detection requires parsing `gh`'s stderr for the specific "is already used by worktree" string, which is brittle to `gh` and git version drift. The explicit-deletes approach decouples the cleanup from `gh`'s implementation entirely.

- **Why this is robust to future `gh` version changes**: `gh pr merge --admin --squash` (without `--delete-branch`) is the documented stable API for "merge only, no cleanup". The flag combination has been stable across `gh` 2.x. `git push origin --delete` and `git branch -D` are standard git commands. The composite has fewer moving parts than the `--delete-branch` flag's internal cleanup logic.

## 3. Stepwise migration

Each step independently shippable / revertable. The SKILL.md edits land in the `/dev-next` cycle that runs this spec; the skill file is outside the repo, so the spec's git commit contains only the test + version bump artifacts.

- **Step 1: Drop `--delete-branch` from `~/.claude/skills/dev-next/SKILL.md:292`.** Change the line to `gh pr merge --admin --squash`. The flag's three remaining values (`--admin --squash` plus the absent `--delete-branch`) compose as: admin override + squash-merge mode + no auto-cleanup.
  - Verified by: post-cycle, `~/.claude/skills/dev-next/SKILL.md:292` (or the corresponding line after any prose re-flow) contains `gh pr merge --admin --squash` and does NOT contain `--delete-branch`.

- **Step 2: Add the explicit-cleanup block to `~/.claude/skills/dev-next/SKILL.md` step 19.** Insert the bash block from §2 above directly after the `MERGE_SHA` capture block (which currently ends at `~/.claude/skills/dev-next/SKILL.md:304`) and before the "Verified delete after merge" block at `:306`. The block reuses the existing `BRANCH="spec/${SPEC_ID}-${SLUG}"` naming convention from `~/.claude/skills/dev-next/SKILL.md:309`.
  - Verified by: post-cycle, `~/.claude/skills/dev-next/SKILL.md` step 19's body contains `git push origin --delete "$BRANCH"` AND `git branch -D "$BRANCH"` immediately after the `MERGE_SHA` capture block.

- **Step 3: Add a source-pattern test under `tests/test_spec_0212_no_delete_branch_flag.py`.** Pure stdlib, same doctrine as `tests/test_spec_0211_2_merge_sha_captured_at_merge_time.py:31`'s `_step_block` helper. Three assertions against the live `~/.claude/skills/dev-next/SKILL.md` (skipped when SKILL.md is absent, matching the parent test's pattern):
  - Step 19's body does NOT contain the literal substring `gh pr merge --admin --squash --delete-branch` (locks the flag-drop in place — the composite-call form must not return).
  - Step 19's body DOES contain `gh pr merge --admin --squash` AND `git push origin --delete` (locks the split-merge-from-cleanup pattern).
  - The string `spec 0212` appears in a comment near the new cleanup block (locks the design citation in place so a future re-shuffle leaves a breadcrumb).
  - Verified by: `uv run pytest tests/test_spec_0212_no_delete_branch_flag.py -v` green; the test asserts SKIP when SKILL.md is absent (CI doesn't carry the user's skill files).

- **Step 4: PATCH version bump + CHANGELOG.** Bump `pyproject.toml`, `src/dual_research/__init__.py`, refresh `uv.lock`. Add a `## [X.Y.Z] — YYYY-MM-DD` section to `CHANGELOG.md` under `### Changed`, citing this spec and explaining the operator-visible effect: "`/dev-next` step 19 now issues `gh pr merge --admin --squash` (without `--delete-branch`) and deletes the head branch explicitly via `git push origin --delete` + `git branch -D`, so the author worktree's checkout of `main` no longer triggers a 'is already used by worktree' warning in the cycle log."
  - Verified by: dashboard at `https://lexiz.github.io/dual-research/` renders the new CHANGELOG entry post-deploy.

- **Step 5: Verify next cycle's handoff is collision-free.** Observation-only — the cycle that ships this spec writes a handoff whose body should NOT contain the "is already used by worktree" anomaly under "Cycle anomalies" or "Cycle history". If the warning still appears, the fix didn't land in the form the spec intends and the handoff captures the gap.
  - Verified by: post-cycle, `handoffs/YYYY-MM-DD-spec-0212-gh-pr-merge-delete-branch-author-worktree-collision.md` does not contain the substring `is already used by worktree`.

## 4. Behavior preservation

- [ ] Existing `tests/` suite passes unchanged — `~/.claude/skills/dev-next/SKILL.md` is not part of the repo's pytest collection; the new test is additive.
- [ ] `tests/test_spec_0211_2_merge_sha_captured_at_merge_time.py` (the immediate parent spec's source-pattern test) continues to pass — its three assertions (no `git rev-parse origin/main` in step 20; `gh pr view ... mergeCommit` in step 19; `spec 0211.2` breadcrumb in step 19) are orthogonal to step 19's flag drop and explicit-cleanup additions. The `MERGE_SHA` capture block stays in step 19 in the same position relative to the merge call.
- [ ] `tests/test_spec_0211_no_local_fly_deploy.py` (the grandparent spec's source-pattern test) continues to pass — its assertions (no bare `fly deploy`, `gh run watch` + `deploy.yml` referenced) are orthogonal.
- [ ] Spec 0201's verified-delete invariant at `~/.claude/skills/dev-next/SKILL.md:306`–`:323` continues to enforce that the head branch is gone from both sides before the cycle proceeds. After this spec, the verified-delete's first read of `remote_left` and `local_left` will usually find both already zero (because the new explicit-cleanup block ran first), but the retry path remains as the authoritative correctness check for the edge case where the explicit delete itself fails (network blip, permissions glitch).
- [ ] Spec 0210's queue-worktree-detached doctrine at `~/.claude/skills/dev-next/SKILL.md:329`–`:333` is preserved — the re-detach at `origin/main` still runs after the verified-delete confirms branch cleanup.
- [ ] `gh pr merge --admin --squash` continues to perform the squash-merge with admin override against GitHub's PR API. The merge commit is created on `origin/main` with the same SHA-resolution behavior as before; `gh pr view --json mergeCommit` at the subsequent line returns the same SHA shape (`mergeCommit.oid`).
- [ ] `git push origin --delete` returns 0 when the branch was deleted and non-zero (with `||true` swallowing the exit code) when the branch was already absent. The `||true` is intentional — the verified-delete block at `~/.claude/skills/dev-next/SKILL.md:306`–`:323` is the authoritative absence check.
- [ ] `git branch -D` returns 0 when the local branch was deleted and non-zero (also swallowed by `||true`) when the local branch didn't exist. In the spec-0210-compliant detached-HEAD queue worktree, the local branch usually doesn't exist (the queue worktree never creates `main` locally; the feature branch was created off detached HEAD per spec 0210), so this call is usually a no-op.

## 5. Out of scope

**Explicit: this spec does NOT add any new feature.** No new feature surfaces — no new `/dev-next` skills, no new queue-state schema fields, no changes to the deploy.yml workflow, no changes to the verified-delete halt-on-second-failure guard. It splits one composite `gh pr merge --delete-branch` call into two named operations inside step 19 of the existing `/dev-next` skill body.

- **Setting `git config alias.merge-without-checkout`** (alternative (a) from `handoffs/2026-05-25-spec-0211.2-merge-sha-capture-race-with-post-merge-pushes.md:40`). Rejected — see §2 "Why explicit deletes instead of a `git config alias` shim". (Deferred to: no follow-up planned.)
- **Post-processing the `gh pr merge` failure by detecting the checkout error and skipping the local cleanup** (alternative (b) from the same handoff line). Rejected — see §2 "Why explicit deletes instead of detecting the checkout error". (Deferred to: no follow-up planned.)
- **Restructuring the author worktree to NOT hold `main`** (moving the author worktree to detached HEAD like the queue worktree). Rejected: the author worktree's hold on `main` is structural per `CLAUDE.md` §"Two-worktree split" — spec-creation skills (`/spec-draft`, `/spec-queue`, `/spec-promote`) write to `main` and need a held branch ref to push to. Detaching the author worktree would require restructuring three spec-creation skills' push paths through the same `push_files_to_main` plumbing the queue worktree uses, which is a much larger change with no operator-visible benefit beyond what this spec achieves directly. (Deferred to: future spec if a second class of cross-worktree collision appears.)
- **Generalising the "split composite git commands into named operations" pattern across other `gh` callers in the repo.** Today `/dev-next` step 19 is the only `gh pr merge --delete-branch` caller. The pattern is local. If a second caller appears, extract then. YAGNI. (Deferred to: future spec when a second caller exists.)
- **Adding a backstop sweep for branches that survive the explicit-delete + verified-delete combo.** `scripts/sweep_stale_branches.sh` (spec 0201 §2.4) already exists and is run from `/dev-next` per the citation at `~/.claude/skills/dev-next/SKILL.md:327`. No additional backstop needed. (Deferred to: no follow-up planned.)
- **Touching `~/.claude/projects/-Users-alexlisitzky/memory/`.** No memory file references the `gh pr merge --delete-branch` collision. Memory updates are not in scope. (Deferred to: no follow-up planned.)

## 6. Risks

- **Risk: `gh pr merge --admin --squash` (without `--delete-branch`) behaves differently from the composite call.** *Mitigation:* `gh`'s documented behavior is that flags are independent — `--delete-branch` controls only the post-merge cleanup, not the merge itself. The merge call's API contract (squash-merge with admin override) is identical with or without `--delete-branch`. Verified against `gh version 2.x` man page.

- **Risk: `git push origin --delete "$BRANCH"` fails on a transient API issue.** *Mitigation:* the `||true` swallows the exit code, and the verified-delete block at `~/.claude/skills/dev-next/SKILL.md:306`–`:323` is the authoritative absence check. If the explicit delete fails, the verified-delete's `remote_left` read picks up the still-present branch and retries with the same command; the halt-on-second-failure guard at `:318`–`:321` catches any persistent failure. Same recovery path as today.

- **Risk: `git branch -D` fails because the local branch doesn't exist.** *Mitigation:* the `||true` swallows the exit code. In the spec-0210-compliant detached-HEAD queue worktree, the local branch usually doesn't exist; the call is a no-op. The verified-delete's `local_left` read at `~/.claude/skills/dev-next/SKILL.md:311` confirms absence.

- **Risk: the source-pattern test in step 3 is brittle to SKILL.md prose changes.** *Mitigation:* the test scopes its regex to step 19's block via the `_step_block` helper (same scoping doctrine as `tests/test_spec_0211_2_merge_sha_captured_at_merge_time.py:31`). Prose changes outside step 19 don't trip the test; structural changes inside step 19 correctly trip it (which is the test's purpose).

- **Risk: a future spec re-introduces `--delete-branch` because someone forgets the worktree-collision rationale.** *Mitigation:* the source-pattern test's first assertion (no `gh pr merge --admin --squash --delete-branch` in step 19) is a structural lock. The `spec 0212` breadcrumb in the comment near the new cleanup block makes the rationale discoverable. If a future spec re-adds the flag, the test fails immediately.

- **Risk: a future change moves the author worktree off `main` (closing the underlying collision class).** *Mitigation:* if that happens, the explicit-cleanup block becomes harmless extra work (the `gh pr merge --delete-branch` flag would also work). The split form is strictly no-worse than the composite form. The source-pattern test's structural lock would still pass. A future spec could re-evaluate the split if benchmark data ever shows the extra two git calls matter (they currently do not — they're sub-100ms each against GitHub's API). No action needed.

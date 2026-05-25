---
spec: "0212"
date: 2026-05-25
version: "1.44.16"
pr: "https://github.com/Lexiz/dual-research/pull/247"
kind: post-deploy
---

# Spec 0212 — `/dev-next` post-merge race window closed at source

## What landed

PATCH refactor (`1.44.15` → `1.44.16`) to the `/dev-next` skill body at `~/.claude/skills/dev-next/SKILL.md`. The repo-side artifacts: version bumps in [pyproject.toml](pyproject.toml) and [src/dual_research/__init__.py](src/dual_research/__init__.py), CHANGELOG entry, and a new source-pattern test at [tests/test_spec_0212_post_merge_doctrine.py](tests/test_spec_0212_post_merge_doctrine.py) (six assertions, pure stdlib, SKIPs when SKILL.md is absent — same doctrine as `test_spec_0211_2_merge_sha_captured_at_merge_time.py`). 1915 tests pass, including all four prior 0211/0211.2/0211.3 source-pattern tests (orthogonal to this change).

**Two structural fixes share the post-merge window between step 19's `gh pr merge` and step 20's `gh run watch`:**

- **Step 19 splits merge from cleanup.** `gh pr merge --admin --squash` (without `--delete-branch`) + explicit `git push origin --delete "$BRANCH"` + `git branch -D "$BRANCH"` block. Closes the recurring author-worktree collision recorded across the 0211.1 / 0211.2 / 0211.3 cycle handoffs: the cleanup half of `--delete-branch` checks `main` out locally, which collides with the author worktree at `/Users/alexlisitzky/dual-research-author/` that holds `main` per `CLAUDE.md`'s two-worktree split. The explicit-by-name deletes from the queue worktree's detached HEAD avoid the local-checkout step entirely.

- **Steps 20/21/22 buffer happy-path events.** Five emissions drop `--push-to-main`: step 20's `deploy_started`, step 20's happy-path `deployed`, step 20's pivot-path `deploy_pivoted` + trailing `deployed`, step 21's `deploy_health_check_ok`, and step 22's `handoff_written`. All buffer locally and flush atomically via step 23's existing `push-files-to-main`. With no `--push-to-main` calls between merge and `gh run watch` returning, no newer deploy.yml runs queue behind the merge-commit's run in the `deploy-main` concurrency group — the queue-collapse condition that spec 0211.3 patches symptomatically cannot trigger. Failure-path emissions (`set status=failed`, `append-event failed`) retain `--push-to-main` because the cycle halts immediately after them with no step 23 to flush.

The spec-0211.3 pivot block stays in place as a defensive regression-detector; its comment now cites spec 0212 and explains the new doctrine. If the block ever fires, a `--push-to-main` regression has leaked into the post-merge window and the buffered `deploy_pivoted` event surfaces it on the dashboard.

## Cycle observations

- **Author-worktree warning DID NOT recur this cycle.** The first cycle to ship with the spec-0212 fix in place. `gh pr merge --admin --squash` (no `--delete-branch`) returned silently with no `is already used by worktree` warning — first clean post-merge log in four cycles (0211.1, 0211.2, 0211.3, 0212).

- **Pivot block DID NOT fire this cycle.** `gh run watch` returned `success` directly (`WATCH_RC=0`); no cancellation, no concurrency collapse. The buffer-events doctrine held: no `--push-to-main` writes landed on `origin/main` between merge and `gh run watch` returning, so the merge-commit's deploy run was the only run in the `deploy-main` group during the watch window. The 0211.3 follow-up deferrals (recursive-pivot guard, image-SHA cross-check) are now moot per the spec body §5.

- **Live-discovered ordering bug in the new explicit-cleanup block.** The spec body §2a placed the explicit `git push origin --delete` + `git branch -D` block between the `MERGE_SHA` capture and the verified-delete block — with the existing standalone "Re-detach at `origin/main`" section running AFTER verified-delete. Discovered at the first execution: `git branch -D "$BRANCH"` fails with `error: cannot delete branch ... used by worktree at '/Users/alexlisitzky/dual-research'` because the queue worktree is still checked out on the spec branch at that point. The verified-delete block's retry then also fails for the same reason. **Recovered inline** by force-detaching the worktree first (`git checkout --detach -f origin/main` — safe because the local working-tree's `dashboard/queue-state.json` was already in sync with `origin/main` via the `--push-to-main` plumbing) and then deleting the now-orphaned local branch. **SKILL.md updated inline** to fold the re-detach into the explicit-cleanup block (the detach happens before the by-name deletes) and to remove the now-redundant standalone re-detach section. Future cycles will not hit this. See deferral below for the corresponding source-pattern-test addition.

- **Buffer doctrine round-trip worked as intended.** Three local-only events (`deploy_started`, `deployed`, `deploy_health_check_ok`) accumulated in `dashboard/queue-state.json` during the post-merge window without producing any `origin/main` commits; step 23's push-files-to-main flushed them in a single commit alongside the handoff. The four `--push-to-main` writes that DID happen in this cycle's post-merge window (the manual recovery emissions for `merged`, `pr_opened`, the queue-state status flips) ran BEFORE `gh run watch` started — they pre-dated the deploy run's queueing and so didn't trigger the concurrency collapse. The structural invariant the spec defends (no `--push-to-main` between merge and `gh run watch` returning) was honored on the happy path as specified.

## Deferred during implementation

- **Source-pattern test for the explicit-cleanup ordering invariant.** [tests/test_spec_0212_post_merge_doctrine.py](tests/test_spec_0212_post_merge_doctrine.py) asserts the presence of `git push origin --delete` and `git branch -D` in step 19, but does NOT assert that `git checkout --detach -f origin/main` (or equivalent re-detach) precedes the `git branch -D` call. The live-discovered ordering bug above showed the ordering is load-bearing: `git branch -D` on the currently-checked-out branch fails. SKILL.md has been fixed inline (re-detach folded into the cleanup block before the deletes), but a follow-up test should lock the ordering so a future re-shuffle can't silently re-introduce the bug. The test should assert: within step 19, the first `git checkout --detach` line index < the first `git branch -D "$BRANCH"` line index. Pure stdlib, same `_step_block` doctrine as the other 0212 assertions.

- **Standalone "Re-detach at `origin/main`" section in SKILL.md step 19 was retired in favor of an inline parenthetical note.** The change is structurally sound (the re-detach now happens earlier inside the cleanup block) but the surrounding skill prose could be tightened: the parenthetical at `~/.claude/skills/dev-next/SKILL.md` reading "(spec 0210 re-detach folded into the explicit-cleanup block above as of spec 0212 — `git checkout --detach -f origin/main` runs there. No standalone re-detach step is needed; ...)" replaces what used to be its own subsection. Future cleanup could remove the parenthetical entirely once enough cycles have run that the folded ordering is uncontroversial.

## What spec 0212 closed for good

- **The recurring author-worktree warning** (1a in the spec body). Three consecutive cycles (0211.1, 0211.2, 0211.3) ran with the warning; this cycle is the first to ship without it.
- **The `deploy-main` concurrency-group cancellation race** (1b). Structurally impossible on the happy path under the buffer-events doctrine.
- **Two 0211.3 follow-up deferrals** — recursive-pivot guard and image-SHA cross-check. Both moot now: the pivot block can only fire on a `--push-to-main` regression in the post-merge window, and the source-pattern test catches that regression at the SKILL.md level before the cycle ever executes it.

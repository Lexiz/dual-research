---
spec: "0250"
date: 2026-05-29
version: 1.61.2
pr: https://github.com/Lexiz/dual-research/pull/288
kind: post-deploy
---

# Spec 0250 — Refactor: buffer /dev-next pre-merge telemetry into two batched flushes

**Shipped v1.61.2** via PR [#288](https://github.com/Lexiz/dual-research/pull/288). Deploy run `26606766480` green; app live at `https://dual-research-alex.fly.dev/` (root 200).

## What landed

The pre-merge window of the `/dev-next` cycle now mirrors the proven post-merge buffering (specs 0212/0247). Edits to `~/.claude/skills/dev-next/SKILL.md` (the user-level skill — outside the repo, same as 0212/0247):

- **Flush 1 (step 12).** The `status=in_progress` set and the `in_progress` event dropped `--push-to-main` and became local-only; a single `queue_state push-files-to-main` flushes them together with the buffered step-1/8–11 events (`cycle_started`, `preflight_ok`, `handoff_read`, `spec_read`, `planning_started`, `reconcile_complete`) in one batched commit. The line-30 prose and the step-12 trailing prose were reworded so the long-standing "committed at step 12" promise now describes a real flush.
- **Steps 14–17 local-only.** `branched`, `implementing_started` (step 14), `implement_complete` (step 15), `tests_started` + `tests_green` (step 16, green path), and `pr_opened` (step 17) all dropped `--push-to-main`.
- **Flush 2 (step 17).** A second `push-files-to-main` fires immediately after `pr_opened`, carrying the six buffered step-14–17 events in one batched commit. A comment documents why no branch-identity assertion wraps the flush (the plumbing targets an explicit `<sha>:refs/heads/main` refspec, same as step 23).
- **Step-14 preamble** reworded from "branch-phase events get `--push-to-main`" to "buffered until step 17's Flush 2."
- **Step 16 failure path made explicit.** The tests-red branch now shows the `set --push-to-main status=failed failure_step=tests` and `tests_failed --push-to-main` writes inline (previously prose-only), locking the never-buffer-failures invariant.

Net: ~8 individual `spec(NNNN): queue-state update` commits per cycle → **2**.

## Behavior preservation (spec 0250 §4) — audited

- **Failure writes never buffer.** Audited every pre-merge `status=failed` write and `*_failed`/`failed` event: semantic drift (step 11) and tests-red (step 16) both retain `--push-to-main`. The post-merge deploy-failure paths (step 20) were already `--push-to-main` and untouched.
- **Resume / L-spec checkpoint paths.** `resume_started` and `checkpoint_written` retain `--push-to-main` — verified, not on the two flush milestones.
- **Post-merge window (steps 18–23) untouched** — `handoff_written` stays local-only, the step-23 atomic flush is intact.

## Test

`tests/test_spec_0250_dev_next_pre_merge_buffering.py` — pure-stdlib source-pattern test reading `~/.claude/skills/dev-next/SKILL.md` with a skip-when-absent guard (the spec 0247 precedent). 12 tests covering: step-12/14/15/16/17 happy-path local-only; exactly-two flushes (step 12 + step 17, none at steps 13–16); both failure branches keep `--push-to-main`; post-merge window unchanged. Full suite 2391 passed.

## Self-referential note

This cycle ran under the *old* (pre-0250) skill instructions loaded into context — it issued the individual `--push-to-main` pre-merge commits one last time. The buffering takes effect for the **next** `/dev-next` cycle, which will read the edited `SKILL.md` from disk. The first cycle after this one should show exactly two pre-merge `queue-state` commits (Flush 1 + Flush 2) instead of ~8.

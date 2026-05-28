---
kind: dev
spec: "0250"
slug: dev-next-pre-merge-telemetry-batched-flushes
title: "Refactor: buffer /dev-next pre-merge telemetry into two batched flushes"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: S
created: 2026-05-28
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: ship
disposition_reason: "Directly-authored cadence refactor that mirrors already-proven post-merge buffering; ready for /dev-next."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0250 — Refactor: buffer /dev-next pre-merge telemetry into two batched flushes

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** —
> **Bump:** PATCH — internal restructure, no behavior change. Same events, same lifecycle states, same event vocabulary — only the push cadence to `origin/main` changes. **This is not a contract change.**
> **Evidence:** The post-merge window already buffers + single-flushes (specs 0212, 0247). 147 of the last 200 commits on `origin/main` (74%) are `spec(NNNN): queue-state update` noise; the pre-merge window is the remaining un-batched source.

---

## 1. Current state

The `/dev-next` cycle records lifecycle telemetry to `dashboard/queue-state.json` on `origin/main`. The **post-merge** window already buffers these locally and flushes once via `push-files-to-main` (specs 0212 + 0247): the `merged`, `deploy_started`, `deployed`, `deploy_health_check_ok`, and `handoff_written` events are emitted local-only (no `--push-to-main`) at `~/.claude/skills/dev-next/SKILL.md` steps 18/20/22, then flushed in a single atomic commit at step 23 (`~/.claude/skills/dev-next/SKILL.md:478-491`).

The **pre-merge** window does not. Across the happy path it issues ~8 individual `--push-to-main` calls, each producing its own `spec(NNNN): queue-state update` commit (message hardcoded at `scripts/spec_lifecycle/queue_state.py:393`):

- **Step 12** (`~/.claude/skills/dev-next/SKILL.md:127-129`): `set --push-to-main status=in_progress started_at` + `append-event --push-to-main in_progress` — 2 commits.
- **Step 14** (`~/.claude/skills/dev-next/SKILL.md:145-146`): `branched` + `implementing_started` — 2 commits.
- **Step 15** (`~/.claude/skills/dev-next/SKILL.md:233`): `implement_complete` — 1 commit.
- **Step 16** (`~/.claude/skills/dev-next/SKILL.md:239-241`): `tests_started` + `tests_green` — 2 commits.
- **Step 17** (`~/.claude/skills/dev-next/SKILL.md:281`): `pr_opened` — 1 commit.

Two adjacent facts:

1. The earliest events — `cycle_started` (`~/.claude/skills/dev-next/SKILL.md:27`), and steps 8–11's `preflight_ok`, `handoff_read`, `spec_read`, `planning_started`, `reconcile_complete` (`~/.claude/skills/dev-next/SKILL.md:79,89-91,118`) — are **already** local-only `append-event` calls (no `--push-to-main`).
2. The skill text claims those buffered early events are "committed at step 12" (`~/.claude/skills/dev-next/SKILL.md:29,132`). But step 12 uses `set --push-to-main` / `append-event --push-to-main`, which read and rewrite **origin** state via the plumbing in `scripts/spec_lifecycle/queue_state.py` — they never flush the local working-tree file. So today those early events are not actually pushed; they live only in the local `queue-state.json`, which step 19's `git checkout --detach -f origin/main` later discards. The "committed at step 12" promise is currently unfulfilled.

**Pain:** ~8 redundant commits to `origin/main` per spec (≈74% of recent main history is this noise), plus a latent loss of the step-8–11 timeline events.

## 2. Target state

The pre-merge window mirrors the proven post-merge pattern: every happy-path event is emitted **local-only**, and the buffer is flushed in exactly **two** batched commits via the existing `push_files_to_main` plumbing (`scripts/spec_lifecycle/queue_state.py:273`, which works from a detached HEAD or a feature branch, targets an explicit `<sha>:refs/heads/main` refspec, and resyncs a detached HEAD automatically).

### 2.1 Flush 1 — at step 12 (cycle start / `in_progress`)

Carries the buffered `cycle_started`, `preflight_ok`, `handoff_read`, `spec_read`, `planning_started`, `reconcile_complete` events **and** the `status=in_progress` / `started_at` scalar set + `in_progress` event. This is the "spec is now in flight" anchor — it fires promptly here so the dashboard shows the cycle live, and it makes the previously-unfulfilled "committed at step 12" promise real.

- Drop `--push-to-main` from the `set` and the `in_progress append-event` at `~/.claude/skills/dev-next/SKILL.md:127-129`.
- Append a single flush, shaped like the step-23 invocation (`~/.claude/skills/dev-next/SKILL.md:488-491`):

```bash
uv run python -m scripts.spec_lifecycle.queue_state push-files-to-main \
  --message "spec(NNNN): cycle start (preflight + reconcile + in_progress)" \
  --file dashboard/queue-state.json
```

- Update the prose at `~/.claude/skills/dev-next/SKILL.md:29,132` so "committed at step 12" describes the real flush.

### 2.2 Flush 2 — at step 17 (PR opened)

Carries `branched`, `implementing_started`, `implement_complete`, `tests_started`, `tests_green`, `pr_opened`.

- Drop `--push-to-main` from `branched` + `implementing_started` (`~/.claude/skills/dev-next/SKILL.md:145-146`), `implement_complete` (`:233`), `tests_started` + `tests_green` (`:239-241`), and `pr_opened` (`:281`).
- After `pr_opened` is emitted local-only, append a single flush:

```bash
uv run python -m scripts.spec_lifecycle.queue_state push-files-to-main \
  --message "spec(NNNN): branch built, tests green, PR open" \
  --file dashboard/queue-state.json
```

Net: ~8 pre-merge commits → 2. The post-merge window (steps 18–23) is left exactly as-is.

## 3. Stepwise migration

All edits are to `~/.claude/skills/dev-next/SKILL.md` (the user-level skill — the same file specs 0212/0247 edited). No repo app-code change.

- **Step 1 — Make step 12 happy-path emissions local-only + add Flush 1.** Drop `--push-to-main` from the `set` and `in_progress append-event` at `~/.claude/skills/dev-next/SKILL.md:127-129`; add the Flush-1 `push-files-to-main` immediately after; reword lines 29/132. — Verifies: the dashboard shows the cycle live after step 12 and the early events survive.
- **Step 2 — Make steps 14–17 happy-path emissions local-only.** Drop `--push-to-main` from `branched` + `implementing_started` (`:145-146`), `implement_complete` (`:233`), `tests_started` + `tests_green` (`:239-241`), and `pr_opened` (`:281`). — Verifies: no individual `queue-state update` commit lands between step 12 and step 17.
- **Step 3 — Add Flush 2 at step 17.** After `pr_opened` is emitted local-only, add the Flush-2 `push-files-to-main`. — Verifies: the six step-14–17 events land in one commit.
- **Step 4 — Audit + preserve every failure branch.** Confirm each pre-merge halt path still uses `--push-to-main` for both its `set ... status=failed failure_step=<step>` and its `... failed`/`*_failed` `append-event` (see §4). — Verifies: failures stay immediately visible on the dashboard.
- **Step 5 — Source-pattern test.** Add `tests/test_spec_0250_dev_next_pre_merge_buffering.py` (§4).

## 4. Behavior preservation

**Invariants that MUST hold (no contract change — same events, states, vocabulary):**

- **Anchor liveness (Cowork Q3).** `cycle_started` still lands at Flush 1 (step 12), promptly, as today. The `merged` event and deploy outcome remain owned by the **post-merge** window (steps 18/20/23) and are **not touched** — the existing post-merge buffering stays byte-for-byte as-is.
- **Failure writes never buffer.** Every pre-merge halt — semantic drift at step 11 (`~/.claude/skills/dev-next/SKILL.md:115`), tests red at step 16 (`~/.claude/skills/dev-next/SKILL.md:236`), and any other `status=failed` write in steps 8–17 — MUST retain `--push-to-main` on both the scalar `set ... status=failed failure_step=<step>` and the `append-event ... failed`/`*_failed` call, so a halt is visible on the dashboard immediately even though no flush milestone was reached. Buffering must not swallow failure visibility.
- **Branch-side safety.** Flush 2 runs while the worktree is on the feature branch (cut at step 14). `push_files_to_main` targets `origin/main` via plumbing with an explicit refspec and does **not** commit to or move the feature branch; `dashboard/queue-state.json` is never added to a branch commit. No branch-identity assertion is needed for the flush — same as the step-23 flush (`~/.claude/skills/dev-next/SKILL.md:258`).
- **Resume-mode + L-spec checkpoint paths.** `resume_started` (`~/.claude/skills/dev-next/SKILL.md:102`) and `checkpoint_written` (`:210`) keep `--push-to-main` — they are not on the two happy-path flush milestones and must remain immediately visible.

**Test plan** — skill files live outside the repo, so a pure-stdlib source-pattern test reads `~/.claude/skills/dev-next/SKILL.md` directly with a **skip-when-absent** guard (the spec 0247 precedent — see `handoffs/2026-05-28-spec-0247-*.md`):

- [ ] Step-12 and step-17 happy-path event emissions carry **no** `--push-to-main`.
- [ ] Exactly **two** `push-files-to-main --file dashboard/queue-state.json` flushes exist in the pre-merge window (one at step 12, one at step 17).
- [ ] Every pre-merge **failure** branch still uses `--push-to-main` for its `status=failed` set and its `failed`/`*_failed` event.
- [ ] The post-merge window (steps 18–23) is unchanged — its buffered events stay local-only and its single step-23 flush is intact.

## 5. Out of scope

**Explicit: this spec adds no new feature and changes no behavior contract.** It does not introduce, remove, or modify any event type, lifecycle state, convergence rule, phase mechanic, categorisation, or verifier invariant — only the `origin/main` push cadence of pre-merge telemetry. Specifically out of scope:

- The post-merge buffering window (steps 18–23) — already shipped by 0212/0247; left untouched.
- The `deploy.yml` path filter — separate spec.
- The carve-out disposition gate — separate spec.
- Any change to `scripts/spec_lifecycle/queue_state.py` itself (the `push_files_to_main` plumbing at `:273` and the hardcoded commit message at `:393` are reused as-is).

## 6. Risks

- **Early-event loss if Flush 1 is misplaced.** If Flush 1 lands before the early events are emitted, the buffered `cycle_started`/preflight/reconcile events miss the commit. Mitigation: Flush 1 sits immediately after the `in_progress` write at step 12, after all step-8–11 emissions.
- **A failure branch silently converted to buffered.** If Step 4's audit misses a halt path, a failure would not surface on the dashboard until a flush that never comes (the cycle exits first). Mitigation: the test's failure-branch assertion enumerates each `status=failed` write and requires `--push-to-main`.
- **Flush 2 from the feature branch.** Already de-risked: `push_files_to_main` uses an explicit `<sha>:refs/heads/main` refspec and never touches the branch ref (same as step 23). The test asserts no branch-identity guard is wrongly added around the flush.

---
kind: draft
draft_id: "001"
slug: skill-fix-dev-next-early-event-push-to-main-contract
title: "skill-fix: dev-next early-event push-to-main contract"
type: bug
status: draft
created: 2026-05-24
source_session: spec-0203.1-deferred-subagent
---

# Draft 001 — skill-fix: dev-next early-event push-to-main contract

## Context

During the `/dev-next` cycle for spec 0203.1, the early-cycle events `cycle_started`, `preflight_ok`, `handoff_read`, `spec_read`, `planning_started`, and `reconcile_complete` were emitted via `append-event` **without** the `--push-to-main` flag. They wrote only to the local working copy.

The next `queue_state set --push-to-main` (step 12 in the skill) then did a `git fetch` + read-modify-write against `origin/main`, which **overwrote** the local buffered events that hadn't been pushed yet. Net effect on this run: the dashboard timeline for 0203.1 shows zero-duration pre-flight / read-handoff / read-spec / planning / reconcile stages — the events that would have anchored those durations were silently discarded.

This is a contradiction inside the skill text itself. The skill step 12 narrative says these events "should already have been emitted via `append-event --push-to-main`", but the example commands at steps 8 / 9 / 11 do not include the `--push-to-main` flag. The example wins (operators copy-paste it), so the events never make it to origin and are wiped on the first `set --push-to-main`.

This deferral is logged in [handoffs/2026-05-24-spec-0203.1-dashboard-queue-state-parity-and-l-spec-event-vocab.md:86](handoffs/2026-05-24-spec-0203.1-dashboard-queue-state-parity-and-l-spec-event-vocab.md).

## Affected surface

- **`~/.claude/skills/dev-next/SKILL.md`** — the canonical skill file Claude reads when `/dev-next` is invoked. Lives **outside** the dual-research repo, in the operator's `~/.claude/skills/` directory. Not under git in the project; carried in the operator's Claude Code config.
- **Concrete symptom in-repo:** [dashboard/queue-state.json](dashboard/queue-state.json) `specs.0203.1.events` — compare against any well-instrumented prior cycle (e.g. `specs.0156.events` from spec 0156's cycle) to see the missing early-cycle steps.
- **Concrete impact:** [scripts/spec_lifecycle/render_dashboard.py](scripts/spec_lifecycle/render_dashboard.py) `compute_stages` falls back to zero-duration estimates when the early events are absent, so spec 0203.1's timeline understates real wall-clock spent in pre-flight / planning / reconcile.

## Why this is a draft, not a dev spec

The fix target (`~/.claude/skills/dev-next/SKILL.md`) is **not in this repo**. A normal `/dev-next` cycle:

1. Cuts a branch in the dual-research repo.
2. Edits files under that repo.
3. Opens a PR against `Lexiz/dual-research`.

None of those steps can touch the operator's `~/.claude/skills/dev-next/SKILL.md`. So a queued dev spec for this work would either (a) deadlock at the implement step or (b) silently produce an empty PR. The right move is to capture the problem and ask the operator how they want to land the fix.

## Sketch / proposed direction

Two plausible fixes; the operator needs to pick.

### Option A — Edit the skill file directly (out-of-repo)

Patch the example commands in `~/.claude/skills/dev-next/SKILL.md` steps 8 / 9 / 11 to include `--push-to-main` on every `append-event` for the early-cycle events:

```bash
# Before (current example):
uv run python -m scripts.spec_lifecycle.queue_state append-event 0203 cycle_started '{}'

# After:
uv run python -m scripts.spec_lifecycle.queue_state append-event 0203 cycle_started '{}' --push-to-main
```

Same edit for `preflight_ok`, `handoff_read`, `spec_read`, `planning_started`, `reconcile_complete`.

Pros: minimal, one-line change per command, no in-repo code change.
Cons: lives outside the dual-research repo so the fix isn't versioned with the project; can drift again if a future skill rev forgets the flag.

### Option B — In-repo wrapper that defaults to push-to-main for early events

Add a wrapper (e.g. `scripts/spec_lifecycle/emit_early_event.py`) that the skill calls instead of raw `queue_state append-event`. The wrapper hard-codes `push_to_main=True` for the early-cycle steps. This puts the behaviour under version control in the dual-research repo, with tests.

Pros: lives inside the repo; tested; future-proof against skill-file drift.
Cons: wider surface change; the operator still has to edit the skill file once to point at the new wrapper.

### Option C — Document destructive-pull semantics + add a "flush local events" step

Don't change the example commands. Instead, add a step before any `queue_state set --push-to-main` call: explicitly push the local file to main first, OR document loudly that `set --push-to-main` does a destructive pull and the operator must have flushed local events already.

Pros: zero example-command churn.
Cons: relies on operator discipline; same failure mode if the warning is missed.

## Unresolved questions

These need the operator's judgement before the fix can be authored as a dev spec or applied directly.

- **Where to land the fix.** Option A (out-of-repo skill edit), Option B (in-repo wrapper), or Option C (docs-only)? Option A is fastest; Option B is most durable. The operator may also want a hybrid: A as the immediate fix + B as a follow-up dev spec for hardening.

- **Does the dual-research repo carry a copy of `SKILL.md`?** Spec 0152 introduced the spec-lifecycle skills; some of them may have an in-repo reference copy under `scripts/spec_lifecycle/skills/` or similar. If a reference copy exists, the fix should update both. (A grep for `SKILL.md` in the repo would settle this; not done here because the answer changes the scope of the eventual spec.)

- **Whether `--push-to-main` should also be added to the post-implement events** (`branched`, `implementing_started`, `implement_complete`, `tests_started`, `tests_green`, `pr_opened`) for symmetry, or whether the skill's existing step-12 `set --push-to-main` is sufficient for those (it gathers them in a single push). The handoff narrative implies only the early-cycle events are at risk because they're emitted **before** the first push, but a deliberate decision should be recorded.

- **Whether the broader contract should be inverted** — i.e. `append-event` defaults to `--push-to-main` and the flag becomes `--local-only` for the rare batching case. This is a wider design call and would touch [scripts/spec_lifecycle/queue_state.py:238-263](scripts/spec_lifecycle/queue_state.py) (`append_event_to_state` default for `push_to_main`).

- **How to verify the fix landed.** Re-run `/dev-next` on the next queued spec (currently 0203.2 after this batch) and inspect `dashboard/queue-state.json` for the early-cycle events — if all five steps land as ≥ 1-second-apart events with reasonable durations, the fix is good. Manual smoke vs. a regression test that exercises the skill is itself a sub-question.

## Out of scope

- Reconstructing the lost events for spec 0203.1's cycle. Cosmetic loss; the spec deployed successfully and the handoff captures the real story. Synthetic backfill would lie about timestamps.
- Sweeping every `/spec-*` skill (`/spec-queue`, `/spec-promote`, `/spec-draft`, `/spec-next`) for the same pattern. They write differently and may or may not have the same risk — separate audit if the operator wants it.

## Pointers

- Handoff with the full deferral context: [handoffs/2026-05-24-spec-0203.1-dashboard-queue-state-parity-and-l-spec-event-vocab.md:86](handoffs/2026-05-24-spec-0203.1-dashboard-queue-state-parity-and-l-spec-event-vocab.md)
- Parent spec body: [specs/0203.1-dashboard-queue-state-parity-and-l-spec-event-vocab.md](specs/0203.1-dashboard-queue-state-parity-and-l-spec-event-vocab.md)
- Queue-state CLI surface (where `--push-to-main` is defined): [scripts/spec_lifecycle/queue_state.py:425-440](scripts/spec_lifecycle/queue_state.py)
- The push-to-main git plumbing the flag triggers: [scripts/spec_lifecycle/queue_state.py:268-333](scripts/spec_lifecycle/queue_state.py)

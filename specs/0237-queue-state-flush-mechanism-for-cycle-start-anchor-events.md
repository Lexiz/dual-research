---
kind: dev
spec: "0237"
slug: queue-state-flush-mechanism-for-cycle-start-anchor-events
title: "Refactor: stop losing cycle-start anchor events on the first `--push-to-main` resync by adding a `queue_state flush` subcommand and wiring `/dev-next` to call it at step 12"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: S
created: 2026-05-27
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
disposition_reason: "The cycle-start anchor events (cycle_started / preflight_ok / handoff_read / spec_read / planning_started / reconcile_complete) are silently lost every `/dev-next` cycle today, which means the dashboard's stage-duration breakdown for the pre-implementation phases is structurally broken — observability we explicitly added via spec 0156 is regressed and must be repaired."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0237 — Refactor: `queue_state flush` subcommand + `/dev-next` step-12 wiring to preserve cycle-start anchor events

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** —
> **Bump:** PATCH — internal CLI surface addition + skill plumbing; no behaviour change for cycles that already pass `--push-to-main` on every emit. The dashboard observably gains the missing cycle-start events, which is the bug-being-undone, not new functionality.
> **Evidence:** The spec 0231 handoff at [`handoffs/2026-05-27-spec-0231-parser-heading-tolerance-and-repair-fallback.md:30`](handoffs/2026-05-27-spec-0231-parser-heading-tolerance-and-repair-fallback.md) records the failure mode verbatim: "Steps 1, 8, 9, 11 (`cycle_started` / `preflight_ok` / `handoff_read` / `spec_read` / `planning_started` / `reconcile_complete`) were emitted via `append-event` *without* `--push-to-main` and never made it to `origin/main` — the first `--push-to-main` call at step 12 syncs local from remote first, overwriting the buffered events. The skill's step-12 commentary mentions a 'later flush' path, but the queue_state CLI has no flush command." The deferral in [`handoffs/2026-05-27-spec-0231-parser-heading-tolerance-and-repair-fallback.md:36`](handoffs/2026-05-27-spec-0231-parser-heading-tolerance-and-repair-fallback.md) names this spec as the follow-up.

---

## 1. Current state

The `/dev-next` skill at [`~/.claude/skills/dev-next/SKILL.md`](.claude/skills/dev-next/SKILL.md) (out of repo, lives under the user's `~/.claude/skills/` directory) drives every dev-spec cycle through ~24 numbered steps. Steps 1, 8, 9, 11 each emit anchor events via:

```
uv run python -m scripts.spec_lifecycle.queue_state append-event NNNN <step> '<json>'
```

…with **no** `--push-to-main` flag. The skill's step-12 commentary at SKILL.md line ~132 explicitly says: *"The buffered preflight / handoff_read / spec_read / planning_started / reconcile_complete events from steps 8–11 should already have been emitted via `queue_state append-event --push-to-main` (or `append-event` then a later flush) — they land in queue-state.json as they're emitted."* The "later flush" path is referenced but not implemented.

### 1.1 — The CLI surface today

The `queue_state` CLI is at [`scripts/spec_lifecycle/queue_state.py`](scripts/spec_lifecycle/queue_state.py) and exposes four subcommands via `argparse`:

- `set` at [`scripts/spec_lifecycle/queue_state.py:537`](scripts/spec_lifecycle/queue_state.py:537) — set scalar fields on one spec (`--push-to-main` optional).
- `append-event` at [`scripts/spec_lifecycle/queue_state.py:545`](scripts/spec_lifecycle/queue_state.py:545) — append one `{ts, step, data}` event to a spec's entry (`--push-to-main` optional).
- `show` — read-only printer.
- `push-files-to-main` at [`scripts/spec_lifecycle/queue_state.py:558`](scripts/spec_lifecycle/queue_state.py:558) — push arbitrary file additions/updates/deletions to `origin/main` via git plumbing.

The two write paths — `update_state` at [`scripts/spec_lifecycle/queue_state.py:167`](scripts/spec_lifecycle/queue_state.py:167) and `append_event_to_state` at [`scripts/spec_lifecycle/queue_state.py:238`](scripts/spec_lifecycle/queue_state.py:238) — both write to the local `dashboard/queue-state.json`, then optionally push to `origin/main` via `_push_state_to_main`. **There is no read-local-then-push path.** Every `--push-to-main` invocation re-reads from `origin/main` first (the canonical "sync local from remote first" doctrine that keeps the queue worktree's detached HEAD coherent), which means any locally-buffered events written without `--push-to-main` are silently overwritten when a later `--push-to-main` call resyncs the file.

### 1.2 — The dashboard cost

The renderer at [`scripts/spec_lifecycle/render_dashboard.py`](scripts/spec_lifecycle/render_dashboard.py) derives per-stage durations from the events list inside each spec's `queue-state.json` entry (and the legacy `dashboard/events/NNNN.jsonl` sidecar). Events that never reach `origin/main` never reach the renderer; the pre-implementation stages (`cycle_started → preflight_ok`, `preflight_ok → handoff_read`, etc., spec 0156) all show zero duration on the dashboard because the bookend events are absent. The dashboard's value-add for the pre-implementation phases is structurally negated — observability we explicitly designed (spec 0156) is regressed today on every cycle.

### 1.3 — The failure pattern is reproducible

Replay: open any recent handoff (e.g. [`handoffs/2026-05-27-spec-0231-parser-heading-tolerance-and-repair-fallback.md`](handoffs/2026-05-27-spec-0231-parser-heading-tolerance-and-repair-fallback.md)) and check the corresponding `dashboard/queue-state.json` entry's `events` array. The first event landing on `origin/main` is `in_progress` (emitted at step 12 with `--push-to-main`); the cycle-start anchor events from steps 1, 8, 9, 11 are absent. Cross-check the dashboard's per-spec card at [`https://lexiz.github.io/dual-research/`](https://lexiz.github.io/dual-research/) — the pre-implementation stages render with zero or near-zero duration despite the cycle having taken non-trivial time on those steps.

## 2. Target state

A `queue_state flush` subcommand exists at [`scripts/spec_lifecycle/queue_state.py`](scripts/spec_lifecycle/queue_state.py) (the same CLI module). It pushes any local events that are present in `dashboard/queue-state.json` but missing from `origin/main:dashboard/queue-state.json` to the remote via the existing `push_files_to_main` plumbing at [`scripts/spec_lifecycle/queue_state.py:273`](scripts/spec_lifecycle/queue_state.py:273). It is **idempotent** — running it twice in succession against the same local + remote state produces a no-op on the second invocation.

The `/dev-next` skill at [`~/.claude/skills/dev-next/SKILL.md`](.claude/skills/dev-next/SKILL.md) invokes `queue_state flush <spec-id>` once, at step 12, immediately before its first `--push-to-main` call. The flush ships the buffered cycle-start events to `origin/main`; the subsequent `--push-to-main` calls then resync from the now-updated remote and the dashboard renders the events.

### 2.1 — `flush` subcommand semantics

The new subcommand at [`scripts/spec_lifecycle/queue_state.py`](scripts/spec_lifecycle/queue_state.py) (added adjacent to the existing `append-event` subparser at line 545):

```
queue_state flush <spec-id> [--repo-root PATH]
```

Behaviour:

1. Read local `dashboard/queue-state.json` (via existing `read_state`) and extract the events list for `<spec-id>`.
2. Fetch `origin/main:dashboard/queue-state.json` via git plumbing (read-only — the same `_read_blob_from_origin_main` shape used by `_push_state_to_main`), parse it, and extract the events list for the same `<spec-id>`.
3. Compute the diff: events present locally but missing on `origin/main`, keyed by `(ts, step)` tuple (the natural primary key — `data` may legitimately differ across runs but `(ts, step)` is unique within a spec's event sequence).
4. If the diff is empty, print `flush: 0 events to push for <spec-id>` and exit 0.
5. If the diff is non-empty, build the merged events list (origin events + missing local events, sorted by `ts`) and push the merged `dashboard/queue-state.json` to `origin/main` via `push_files_to_main` with commit message `flush(NNNN): N buffered events`. After the push, resync the local detached HEAD to `origin/main` via the existing `_resync_detached_head_to_origin_main` helper.

### 2.2 — `/dev-next` step-12 invocation

The skill at [`~/.claude/skills/dev-next/SKILL.md`](.claude/skills/dev-next/SKILL.md) gains one line at the head of step 12 (immediately before the first `queue_state set --push-to-main` invocation):

```
uv run python -m scripts.spec_lifecycle.queue_state flush NNNN
```

The skill's step-12 commentary that today says "*…or `append-event` then a later flush*" is updated to reference the new subcommand explicitly. The step-1, 8, 9, 11 commands themselves keep their existing form (no `--push-to-main`) — the flush is the consolidation point, which preserves the buffering optimisation (steps 1, 8, 9, 11 don't each make their own git-push round trip).

### 2.3 — `append_event_to_state` and `update_state` signatures unchanged

The two Python entrypoints at [`scripts/spec_lifecycle/queue_state.py:167`](scripts/spec_lifecycle/queue_state.py:167) and [`scripts/spec_lifecycle/queue_state.py:238`](scripts/spec_lifecycle/queue_state.py:238) keep their signatures. A new private helper `_flush_buffered_events(repo_root, spec_id)` is added in the same module and called from the new CLI subcommand. No public Python surface change; the only new surface is the CLI subcommand itself.

## 3. Stepwise migration

- **Step 1:** Add `_flush_buffered_events(repo_root, spec_id)` helper in [`scripts/spec_lifecycle/queue_state.py`](scripts/spec_lifecycle/queue_state.py) (private, module-level). It implements the read-local / read-origin / diff / merge / push pipeline described in §2.1. Verified by a unit test that constructs a fixture local state with two events, an origin state with zero events, calls the helper, and asserts the returned diff is `2` and the new origin state contains both events.
- **Step 2:** Add the `flush` subparser at [`scripts/spec_lifecycle/queue_state.py`](scripts/spec_lifecycle/queue_state.py) adjacent to the existing `append-event` subparser (around line 545), and wire `args.cmd == "flush"` to call `_flush_buffered_events`. Verified by a CLI-level smoke test asserting `python -m scripts.spec_lifecycle.queue_state flush 0237` runs end-to-end against a tmp repo.
- **Step 3:** Add the idempotency test — running the helper twice in succession produces 0 events pushed on the second call. Verified directly by the new test in `tests/test_queue_state_flush.py`.
- **Step 4:** Update `~/.claude/skills/dev-next/SKILL.md` to call `queue_state flush NNNN` at the head of step 12 and to update the step-12 commentary block that today says *"…or `append-event` then a later flush"* to reference the new subcommand by name. **This file lives outside the repo** (per the standing two-worktree split documented in [`CLAUDE.md`](CLAUDE.md)); the SKILL.md edit is made manually as part of the same PR cycle and verified by re-reading the file post-edit. The repo PR itself contains only the Python + tests change; the SKILL.md edit is part of the implementer's checklist but produces no in-repo diff.
- **Step 5:** Bump version per CLAUDE.md ("refactoring → PATCH") — update `pyproject.toml`, `src/dual_research/__init__.py`, `uv.lock`, and the auto-regenerated version-notes JSON via `scripts/build_version_notes.py`. Add the `## [X.Y.Z] — YYYY-MM-DD` section in [`CHANGELOG.md`](CHANGELOG.md) directly under `## [Unreleased]` with a single `### Added` bullet referencing this spec.

## 4. Behavior preservation

- [ ] Existing test `test_queue_state_set_pushes_to_main` (or whatever the closest current name) still passes — the `set` subcommand's behaviour is untouched.
- [ ] Existing test `test_queue_state_append_event_appends` still passes — the `append-event` subcommand's behaviour is untouched.
- [ ] New parity test `test_flush_with_no_buffered_events_is_noop` — when local and origin event lists are equal, `flush` exits 0 with `flush: 0 events to push` and produces no commit on `origin/main`. This is the behaviour-preservation guarantee for cycles that already pass `--push-to-main` on every `append-event` (the data-already-on-main case).
- [ ] New parity test `test_flush_with_buffered_events_merges_and_pushes` — when local has events absent from origin, `flush` pushes the merged list and a follow-up read of `origin/main:dashboard/queue-state.json` shows both event sequences interleaved by timestamp.
- [ ] New parity test `test_flush_idempotent` — running `flush` twice in succession against the same starting state produces exactly one origin commit (the second invocation is a no-op).

## 5. Out of scope

**Explicit: no new feature ships here.** The `flush` subcommand is a recovery mechanism for the existing buffer-then-resync pattern — it preserves observability the system was already designed to have (spec 0156's stage-duration breakdown). It does not change which events are emitted, what their schema is, or how the dashboard renders them. Any feature work that depends on this fix (e.g. a richer pre-implementation timeline, a stage-duration alert) lives in a follow-up spec.

The following are explicitly NOT in scope and are deferred:

- **Converting `/dev-next` steps 1, 8, 9, 11 to use `--push-to-main` on every call (the alternative fix B from the spec 0231 handoff deferral).** Two reasons. (1) It adds four extra round-trip pushes to `origin/main` per cycle, which is a measurable cycle-time regression on cycles where the user has slow connectivity (the queue worktree's push plumbing is git-over-https). (2) The buffer-then-flush pattern is the more idiomatic shape — single round trip at consolidation point, which mirrors the doctrine `--push-to-main` was added for in the first place. The spec 0231 deferral named both fixes as options; this spec picks (A) because it preserves the buffering invariant. The skill change in §3 step 4 is the load-bearing piece — if a future cycle adds anchor events between steps 12 and the implementation start, the flush picks them up automatically.
- **Backfilling lost cycle-start events for already-shipped specs.** The events that were lost on prior cycles cannot be reconstructed (the `ts` and `data` payloads weren't persisted anywhere). They stay lost; the dashboard's pre-implementation timeline for shipped specs remains as it is. Going forward, every cycle that runs the updated `/dev-next` skill gets the full event sequence on `origin/main`.
- **Extending the flush mechanism to the spec-creation skills (`/spec-queue`, `/spec-promote`, `/spec-draft`).** Those skills emit events too, but their event sequences are short (typically 2-3 events) and they don't follow the buffer-then-push pattern — they typically pass `--push-to-main` on each call already. If a future spec changes that, the `flush` subcommand is already available to them and only the SKILL.md call-site changes — no further code change.
- **A `flush` subcommand variant that operates on all queued specs at once.** The current shape takes a single `<spec-id>` argument. A multi-spec flush would be useful for batch recovery after a long-lived branch lands, but the immediate failure pattern is per-cycle, so per-spec invocation is sufficient. Multi-spec flush is a follow-up if the need materialises.

## 6. Risks

- **R1 — Race condition: another `--push-to-main` caller advances `origin/main` between the `flush` subcommand's read and write.** The merge step in §2.1 reads `origin/main:dashboard/queue-state.json`, computes a diff, builds a merged list, and pushes. If a parallel session lands a `set --push-to-main` between read and push, the flush's tree-build would be stale relative to the latest origin. *Mitigation:* the existing `push_files_to_main` plumbing at [`scripts/spec_lifecycle/queue_state.py:273`](scripts/spec_lifecycle/queue_state.py:273) already handles non-fast-forward errors by re-reading the latest `origin/main` and rebuilding the tree on top — see the retry loop in the helper. The flush subcommand inherits that retry behaviour; on non-fast-forward, the merge is recomputed against the freshest origin and the second push succeeds. The retry budget `DEFAULT_PUSH_RETRIES` is already tuned for parallel-session contention.
- **R2 — Diff computation by `(ts, step)` tuple double-counts when two events legitimately share both fields.** The natural primary key is `(ts, step)` — `ts` is granular to seconds and `step` is unique-ish per cycle phase. Two events with identical `ts` and `step` would be deduplicated, losing one. *Mitigation:* in practice this is the buffering optimisation working as intended — `/dev-next` does not emit the same step twice within one second. If a future skill change does, the merge logic can be tightened to include `data` in the key. The current shape is documented and tested.
- **R3 — The skill edit lives outside the repo, so the spec's "implementation complete" signal is partly visual.** The Python + tests change is reviewable in the PR; the SKILL.md edit is verified by the implementer re-reading the file post-edit. *Mitigation:* the implementer's checklist for this spec includes a final verification: cd to `~/.claude/skills/dev-next/` and confirm the step-12 block contains a `queue_state flush` invocation. If the SKILL.md edit is dropped accidentally, the next `/dev-next` cycle will fail the regression check (cycle-start events still missing on `origin/main`) and the spec is re-opened. The PR description includes a screenshot or `cat` excerpt of the post-edit SKILL.md step-12 block for reviewer audit.
- **R4 — The flush helper introduces a new git-plumbing read path (`origin/main:dashboard/queue-state.json` content fetch) that didn't exist before.** Existing pushes read the index via `GIT_INDEX_FILE` and write a tree, but read paths use git plumbing too. *Mitigation:* the read path is `git cat-file -p origin/main:dashboard/queue-state.json` (via `subprocess.run`), which is the same shape as the existing `_read_blob_from_origin_main` helper if one exists, or a thin new wrapper if not. Any failure surfaces as a clear `subprocess.CalledProcessError`. The unit tests exercise the read path against a fixture repo.
- **R5 — The skill's step-12 invocation makes step 12 measurably slower (one extra git round-trip).** The `flush` subcommand always does the read-origin / diff step even when the diff is empty; that's a single `git cat-file -p` call (~50-100ms on slow connections). *Mitigation:* trivial cost relative to step 12's existing first `--push-to-main` call (which is itself a full push round-trip). The flush is at most one extra read; on cycles where it's a no-op, it adds < 200ms.

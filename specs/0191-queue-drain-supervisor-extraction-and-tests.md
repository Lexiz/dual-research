---
kind: dev
spec: "0191"
slug: queue-drain-supervisor-extraction-and-tests
title: "Refactor: extract queue-drain supervisor to Python with unit tests"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 5
depends_on: ["0186"]
complexity: M
created: 2026-05-23
queued_at: "2026-05-23T00:00:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: deferred-from-0186
promoted_from_draft: ""
---

# Spec 0191 — Refactor: extract queue-drain supervisor to Python with unit tests

> **Type:** refactoring  |  **Complexity:** M  |  **Depends on:** 0186
> **Bump:** PATCH — extract existing supervisor logic from shell-in-SKILL.md into a Python module the skill wraps. No behavior change end-to-end.
> **Evidence:** Spec 0186 handoff `## Deferred during implementation` first bullet — [handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:60](handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:60): *"the supervisor itself is shell logic in `~/.claude/skills/dev-queue-run/SKILL.md` — that file is not Python code, it's instructions the agent follows, so it's not directly unit-testable. A follow-up spec could either (a) factor the supervisor into a Python `scripts/queue_drain_supervisor.py` that the skill body merely wraps, then unit-test that; or (b) write integration tests that spawn `claude` against a stub spec dir."* This spec picks (a): the Python-extraction approach. Existing supervisor-adjacent helpers already live in [scripts/spec_lifecycle/checkpoint.py:129](scripts/spec_lifecycle/checkpoint.py) (`build_headless_command`) and are covered by [tests/spec_lifecycle/test_checkpoint.py:1](tests/spec_lifecycle/test_checkpoint.py) — but the loop, queue-re-read, log-tail-on-failure, and resume-mode dispatch are still prose in the skill body, untested.

---

## 1. Current state

The `/dev-queue-run` supervisor model shipped in spec 0186 lives almost entirely in prose at `~/.claude/skills/dev-queue-run/SKILL.md`. The Python side covers only the small leaf helpers:

- [scripts/spec_lifecycle/checkpoint.py:129](scripts/spec_lifecycle/checkpoint.py) — `build_headless_command(spec_number, log_path, project_dir)` returns the `claude -p` argv. Tested.
- [scripts/spec_lifecycle/checkpoint.py:100](scripts/spec_lifecycle/checkpoint.py) — `find_active_checkpoint(handoffs_dir, spec_number, spec_status)` returns the resume-mode checkpoint when one is in flight. Tested.
- [scripts/spec_lifecycle/pick_next_number.py:46](scripts/spec_lifecycle/pick_next_number.py) — `current_queue(specs_dir)` returns the queued specs sorted by `queue_position`. Tested indirectly.

But the **loop** itself — the part that decides which spec runs next, calls the helpers, spawns `claude -p`, captures the log path, waits, classifies the exit code, halts on non-zero, surfaces a tailed-log on failure, and re-reads the queue between iterations — is shell pseudo-code in `~/.claude/skills/dev-queue-run/SKILL.md`. That file is instructions the agent follows; it is not unit-testable, and its three top-line scenarios from spec 0186 §6 are still unchecked:

> [specs/0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:149](specs/0186-queue-drain-session-isolation-and-l-spec-checkpointing.md): *"Supervisor end-to-end: create a synthetic 2-spec test queue (both S complexity, trivial bodies). Run `/dev-queue-run`. Both specs ship in separate sessions. Assert: two distinct log files under `runs/queue-drain/`, two distinct PR URLs, two distinct handoff files, both specs reach `status: deployed`."*

> [specs/0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:150](specs/0186-queue-drain-session-isolation-and-l-spec-checkpointing.md): *"Supervisor halts on failure: synthetic queue where spec 2 has an intentional test failure. ... Assert: spec 1 ships green; spec 2 lands at `status: failed`; supervisor halts; spec 3 (if added) is not touched."*

> [specs/0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:151](specs/0186-queue-drain-session-isolation-and-l-spec-checkpointing.md): *"L-spec checkpoint round-trip: synthetic L spec ... Force checkpoint after `## 2.1`. Spawn a second `/dev-next` invocation. Assert: it reads the checkpoint handoff, enters resume mode, skips re-branching, starts at `## 2.2`."*

The pain: the supervisor model is the load-bearing piece of spec 0186 (the whole point was to fix a real drain failure), yet its loop logic is not covered by any test. A future edit to the skill body — a typo in the halt-on-failure path, an off-by-one in queue re-read, a stale env var name — would not be caught until the next live drain breaks.

## 2. Target state

A new module `scripts/queue_drain_supervisor.py` owns the loop. The skill body becomes a thin wrapper that calls one entry point and surfaces its output.

End-state file layout:

- [scripts/queue_drain_supervisor.py](scripts/queue_drain_supervisor.py) — new. Exports `drain_queue(specs_dir, handoffs_dir, runs_dir, project_dir, *, spawn_command=..., now=..., quiet=False) -> DrainResult`. The injected `spawn_command` makes the subprocess hand-off testable without ever invoking `claude`.
- [tests/spec_lifecycle/test_queue_drain_supervisor.py](tests/spec_lifecycle/test_queue_drain_supervisor.py) — new. Unit tests against `drain_queue` with a fake `spawn_command` that simulates success / failure / checkpoint-then-resume / queue-empty.
- [~/.claude/skills/dev-queue-run/SKILL.md](~/.claude/skills/dev-queue-run/SKILL.md) — body shrinks. The "Per-iteration recipe" subsection (cited at [handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:16](handoffs/2026-05-23-spec-0186-queue-drain-session-isolation-and-l-spec-checkpointing.md:16)) becomes a single call: `uv run python -m scripts.queue_drain_supervisor --project-dir /Users/alexlisitzky/dual-research`. The skill keeps the pre-flight greenlight prose and the final summary prose; everything mechanical moves to Python.

`DrainResult` dataclass shape (declared in the new module):

```python
@dataclass(frozen=True)
class DrainResult:
    completed: list[str]           # spec numbers that shipped this drain
    failed: str | None             # spec number that halted the supervisor, or None
    failure_log_tail: str | None   # last 50 lines of the failed iteration's log
    iterations: int                # total subprocess invocations (counts resume re-spawns)
```

The `spawn_command` parameter signature: `Callable[[list[str], Path], int]` — argv + log path → exit code. The default implementation is a thin `subprocess.run` wrapper that opens the log file and pipes stdout+stderr to it. Tests pass a fake that records argv per call and returns rigged exit codes.

The loop body (inside `drain_queue`):

1. Re-read `current_queue(specs_dir)` from [scripts/spec_lifecycle/pick_next_number.py:46](scripts/spec_lifecycle/pick_next_number.py). If empty, return early with `iterations=0`.
2. Pick the head of the queue. Build `log_path = runs_dir / f"{now()}-spec-{NNNN}.log"`.
3. Check `find_active_checkpoint(handoffs_dir, spec_number, fm['status'])` from [scripts/spec_lifecycle/checkpoint.py:100](scripts/spec_lifecycle/checkpoint.py) to determine whether this iteration is a resume — informational only here; the per-iteration `/dev-next` subprocess does the same check and dispatches itself.
4. Build argv via `build_headless_command(spec_number, log_path, project_dir)` from [scripts/spec_lifecycle/checkpoint.py:129](scripts/spec_lifecycle/checkpoint.py).
5. Call `spawn_command(argv, log_path)`. Capture exit code.
6. If exit code != 0: read last 50 lines of `log_path`; return `DrainResult(completed=[…], failed=spec_number, failure_log_tail=…, iterations=…)`.
7. If exit code == 0: append `spec_number` to `completed`, re-loop from step 1. (Resume mode means the re-loop will pick the same spec again because its status is still `in_progress` — the queue re-read short-circuits to `find_active_checkpoint`, the helper returns the same spec.)

The supervisor is strictly sequential and matches the existing in-skill semantics — this is a pure restructure.

## 3. Stepwise migration

Each step independently shippable / revertable.

- **Step 1 — Add `scripts/queue_drain_supervisor.py` with `drain_queue` + `DrainResult`.** The module is imported and tested but not yet wired into the skill body. The existing skill continues to run the inlined shell-loop. *Verifies:* `uv run pytest tests/spec_lifecycle/test_queue_drain_supervisor.py -q` passes the new cases.

- **Step 2 — Add a CLI entry point.** Wire `python -m scripts.queue_drain_supervisor --project-dir … --specs-dir specs --handoffs-dir handoffs --runs-dir runs/queue-drain` to `drain_queue` + a default `subprocess`-based `spawn_command`. Print a one-line-per-spec summary on success; print the failure tail on halt. *Verifies:* `uv run python -m scripts.queue_drain_supervisor --help` prints usage; a manual smoke against an empty queue exits with `iterations=0` and a "no specs queued" line.

- **Step 3 — Rewrite the skill body to call the CLI.** Edit `~/.claude/skills/dev-queue-run/SKILL.md`: replace the "Per-iteration recipe" + halt-on-failure + log-tail prose with a single bullet that says "After the greenlight, run `uv run python -m scripts.queue_drain_supervisor --project-dir /Users/alexlisitzky/dual-research` and surface its stdout verbatim." Keep the pre-flight greenlight, the single-confirmation invariant, and the final summary prose unchanged. *Verifies:* the skill body's source-of-truth is now the Python module; a real drain (run by the user, not by this spec) exercises it end-to-end.

- **Step 4 — Drop the now-orphan prose from `~/.claude/skills/dev-queue-run/SKILL.md`.** Anything that previously duplicated argv shape / log path format / queue re-read mechanics is gone. The skill body becomes load-bearing only for human-readable invariants (single greenlight, halt semantics, what success looks like). *Verifies:* a diff of the pre-spec-0191 skill body against the post-spec-0191 one shrinks by roughly the line count of the migrated logic; no shell pseudo-code remains inside the body except as illustrative examples.

## 4. Behavior preservation

- [ ] Existing test `uv run pytest tests/ -q` still green — no behavior change for `/dev-next`, no behavior change for any currently-tested helper.
- [ ] New unit tests under [tests/spec_lifecycle/test_queue_drain_supervisor.py](tests/spec_lifecycle/test_queue_drain_supervisor.py): empty-queue early-return, two-spec happy path with a fake `spawn_command` that returns 0 twice (assert `completed == [A, B]`, `failed is None`, `iterations == 2`), halt-on-failure (fake returns 0 then 1 — assert `completed == [A]`, `failed == B`, log tail captured), resume-mode re-pick (fake `spawn_command` writes a checkpoint handoff into the temp `handoffs_dir` and leaves spec `in_progress`; the next iteration re-picks the same spec — assert `iterations == 2`, `completed == [A]` only after the resume sub-iteration also returns 0). At least four cases.
- [ ] Manual smoke: from `/Users/alexlisitzky/dual-research/`, run `uv run python -m scripts.queue_drain_supervisor --project-dir /Users/alexlisitzky/dual-research --dry-run` against the live queue and confirm the printed plan matches what the today-shape skill body would have spawned (same arg shapes, same log paths, same ordering).
- [ ] No behavior change in `/dev-next` — this spec doesn't touch `~/.claude/skills/dev-next/SKILL.md` at all. The per-spec subprocess body is the same as today.
- [ ] No behavior change in the dashboard renderer at [scripts/spec_lifecycle/render_dashboard.py](scripts/spec_lifecycle/render_dashboard.py) — events emitted are the same set; the supervisor itself doesn't emit any new event kinds.

## 5. Out of scope

**Explicit: no new feature ships here.** This spec only restructures existing supervisor logic from prose-in-SKILL.md to Python-with-tests. Any new behavior — different log retention, parallel execution, fancier failure reporting — is a follow-up.

- **Integration tests that actually spawn `claude`** — option (b) from the deferral text. Explicitly not pursued here; the spawned-subprocess path is unit-tested via `spawn_command` injection, which gives the same assertions without the flakiness, infrastructure cost, and CLI-drift exposure of real subprocess spawning. If a true end-to-end integration test is wanted, a separate spec can layer it on top of the new module.
- **L-spec checkpoint heuristic refinements.** Spec 0186 §5 explicitly defers this to a follow-up (spec 0192 in this same drain). Not in scope here.
- **Parallel drain.** Spec 0186 §5 says the supervisor stays strictly sequential. Restated here.
- **Retention policy for `runs/queue-drain/`.** Spec 0186 §7 says logs accumulate and the user can `rm -rf` whenever. Not in scope.
- **Changes to `/dev-next`.** Untouched. The subprocess contract is exactly what `build_headless_command` already returns.

## 6. Risks

- **Argv drift between the helper and the new CLI.** The supervisor used to build the argv inline from prose; the new module calls `build_headless_command` directly. If a future edit changes the helper's shape without updating callers, the supervisor breaks silently. *Mitigation:* the test suite asserts the argv shape returned to the fake `spawn_command` is exactly what `build_headless_command` produces — a single source of truth, regression-locked.
- **Skill body falls out of sync with the Python module.** If the skill body still claims "the supervisor does X" after the Python module no longer does X, the user reads stale prose. *Mitigation:* step 4 explicitly drops the now-orphan prose so the skill body keeps only the human-readable invariants (greenlight, halt semantics). Mechanical detail lives in code.
- **Hidden behavior depending on internals.** If anything else in the repo greps the skill body for prose patterns (e.g. a doc-renderer), shrinking the body could break it. *Mitigation:* grep `.claude/skills/dev-queue-run/SKILL.md` references repo-wide before the restructure; reconcile any prose-reading consumers.
- **Performance regression.** N/A — the supervisor was already sequential; replacing a shell loop with a Python loop has no measurable runtime delta for a queue of 10–20 specs.
- **Missed call site.** If `/dev-queue-run` is invoked from somewhere other than the queue session (e.g. a future cron-style runner), that caller might still inline the old shell recipe. *Mitigation:* grep `dev-queue-run` and `claude -p .*dev-next` across the repo to enumerate callers before merging step 3.

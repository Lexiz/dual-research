---
spec: "0191"
date: 2026-05-23
version: 1.37.3
pr: "https://github.com/Lexiz/dual-research/pull/220"
---

# Spec 0191 — queue-drain supervisor extracted to Python — shipped

The `/dev-queue-run` supervisor loop is now real Python code, unit-tested.
Before this spec the loop lived as prose in
`~/.claude/skills/dev-queue-run/SKILL.md` — agent-followed instructions,
not executable. After this spec, that prose is a thin wrapper around
`scripts/queue_drain_supervisor.py`, and the supervisor's three load-bearing
spec-0186 scenarios (drain end-to-end, halt-on-failure, resume-mode
re-pick on checkpoint) are regression-locked.

## What landed

- **[scripts/queue_drain_supervisor.py](../scripts/queue_drain_supervisor.py)** — new module. ~340 lines.
  - Public API: `drain_queue(specs_dir, handoffs_dir, runs_dir, project_dir, *, spawn_command=..., now=..., quiet=False) -> DrainResult`.
  - Frozen `DrainResult` dataclass: `completed: list[str]`, `failed: str | None`, `failure_log_tail: str | None`, `iterations: int`, `log_paths: list[Path]`.
  - Injection points: `spawn_command: Callable[[list[str], Path], int]` (subprocess hand-off — argv + log path → exit code) and `now: Callable[[], str]` (filename-safe timestamp). The default `spawn_command` opens the log file and pipes subprocess stdout+stderr into it.
  - Loop semantics: re-read queue each iteration; if empty, probe for an `in_progress` spec with an active checkpoint handoff via `find_active_checkpoint` and re-pick that one; spawn via `build_headless_command` (the spec-0194 contract — no `--cwd`); on non-zero exit, capture the last 50 lines of the log file and halt.
  - CLI entry: `uv run python -m scripts.queue_drain_supervisor --project-dir <repo> [--dry-run]`. `--dry-run` prints the planned argv per queue head without spawning.

- **[tests/spec_lifecycle/test_queue_drain_supervisor.py](../tests/spec_lifecycle/test_queue_drain_supervisor.py)** — 10 new tests:
  - The four canonical spec §4 scenarios: empty queue / two-spec happy path / halt-on-failure / resume-mode re-pick on checkpoint.
  - Log-path uniqueness across iterations (the spec-0186 session-isolation invariant).
  - `_tail` last-N-lines helper, `_read_log_tail` missing-file handling.
  - `_default_now` filename-safe format (no colons, no spaces, ends with `Z`).
  - `DrainResult` immutability (frozen dataclass).
  - `DEFAULT_FAILURE_TAIL_LINES == 50` constant guard.

- **[~/.claude/skills/dev-queue-run/SKILL.md](~/.claude/skills/dev-queue-run/SKILL.md)** — rewritten as a thin wrapper. **NOT in this PR's diff** — the skill file lives on the user's machine, not in the repo (same pattern as spec 0194's skill update). The body shrunk 136 → 96 lines. What changed:
  - Pre-flight step 3 now uses `--dry-run` to print the queue plan, keeping the listing and the loop in sync.
  - The "Per-iteration recipe" subsection (the inlined `TS=`/`LOG=`/`cd …` shell block) is gone — replaced by one CLI call: `DR_DEV_NEXT_NONINTERACTIVE=1 uv run python -m scripts.queue_drain_supervisor --project-dir /Users/alexlisitzky/dual-research`.
  - The "Exit code semantics" + "Output surfacing" + "Between iterations" subsections collapse into "Drain" + "Halt on failure" + "On empty queue / clean drain" — human-readable invariants only. Mechanical detail (argv shape, log paths, queue re-read, exit-code branches) lives in the Python module.

- **CHANGELOG / version** — `1.37.2` → `1.37.3` (PATCH per refactoring type).

Full suite: 1710 passed (was 1700).

## Live smoke

```
$ uv run python -m scripts.queue_drain_supervisor --project-dir /Users/alexlisitzky/dual-research --dry-run
[supervisor] dry-run plan (5 specs):
  1. spec 0192 (pos 2) — l-spec-checkpoint-budget-heuristic
     argv: ['claude', '-p', '/dev-next']
  2. spec 0193 (pos 3) — stale-blue-sweep-image-based-filter
     argv: ['claude', '-p', '/dev-next']
  ...
```

The CLI sees the same queue the agent would have spawned, with the same argv shape per iteration.

`fly status -a dual-research-alex`: two app machines on version 497 running
image `01KSASQZN71GGJ7TKQYGJVB4B4`. Smoke: `200`.

## Deploy notes

- `fly deploy` hit a "machine not found" lease error (now-routine variant
  documented in
  [memory: project-fly-lease-drift-recovery](file:///Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/project_fly_lease_drift_recovery.md)).
  This time the new v497 greens came up healthy AND fly itself cleared the
  prior generation — no manual `fly machine destroy --force` needed. Health
  checks started in `critical` state and rolled to `passing` after ~15 s.
- Image: `01KSASQZN71GGJ7TKQYGJVB4B4` on two v497 machines.

## What this DOES NOT do

- **Spawn `claude` for real in tests.** Option (b) from the deferral text
  (integration tests that spawn real subprocesses) is explicitly out of
  scope per spec §5. The `spawn_command` injection gives the same
  assertions without the flakiness of real CLI spawns.
- **L-spec checkpoint heuristic refinements.** Spec 0192 (next in queue)
  handles that; this spec only restructures the supervisor.
- **Parallel drain.** The supervisor stays strictly sequential per spec
  0186 §5; this spec preserves that.
- **Log-file retention policy.** `runs/queue-drain/` still accumulates;
  user purges manually.
- **Change `/dev-next`.** Untouched. The subprocess contract is exactly
  what `build_headless_command` already returns.

## Rebase note

PR #220's first squash-merge attempt failed with `DIRTY` mergeable state,
same pattern as all six previous specs in this drain. Resolved by rebasing
onto `origin/main`, keeping both sides' append-only additions on
`dashboard/events/0191.jsonl`, force-with-lease-pushing, then admin-squashing.

The fix for this recurring conflict pattern is part of this very spec
indirectly: now that the supervisor's event-emission cadence is owned by
the Python module, a future spec can choose to batch `--push-to-main`
emissions (or defer them until after merge) to eliminate the conflict
class entirely. That's a follow-up, not in scope here.

## Stray-tree note

The branch had three unstaged modifications under `prototypes/timeline-iteration/`
when staging this PR — leftover canvas-skill sandbox state from an earlier
session, not related to this spec. Left them unstaged per
[memory: feedback_dirty_tree_not_intentional](file:///Users/alexlisitzky/.claude/projects/-Users-alexlisitzky/memory/feedback_dirty_tree_not_intentional.md);
they remained behind on `main` and will surface again the next time the user
opens a queue session.

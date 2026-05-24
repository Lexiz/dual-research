---
spec: "0186"
date: 2026-05-23
version: 1.33.0
pr: https://github.com/Lexiz/dual-research/pull/196
---

# Spec 0186 — Queue-drain session isolation and L-spec checkpointing

v1.33.0 lands the two-layer fix for context-burn during multi-spec drains. `/dev-queue-run` no longer inlines `/dev-next`'s body — it now supervises a sequential loop of headless `claude -p "/dev-next"` subprocesses, one fresh Claude Code session per queued spec. The supervisor itself only handles pre-flight, queue listing, the single greenlight, per-iteration spawn/wait/result-surfacing, and halt-on-failure. Each subprocess inherits the today-shape `/dev-next` body but with `DR_DEV_NEXT_NONINTERACTIVE=1` set so the per-spec confirmation is suppressed — the user already greenlit the whole queue at the supervisor's pre-flight.

For specs with `complexity: L`, `/dev-next` may now write a `kind: in-spec-checkpoint` handoff after each completed `## 2.N` subsection and halt cleanly with `status: in_progress`. The next iteration's subprocess reads the checkpoint via the new resume-mode branch in step 5 / step 9, re-checks out the branch (`spec/NNNN-<slug>` was already cut last cycle), and jumps to `next_subsection` — honouring `version_bumped` and `changelog_written` so the bump and CHANGELOG entry don't get double-written. M and S specs are unchanged; the cadence is dormant for them.

## What landed

- **`~/.claude/skills/dev-queue-run/SKILL.md`** — full rewrite to the supervisor model. Single greenlight at start. Per-iteration recipe: `mkdir -p runs/queue-drain`; `DR_DEV_NEXT_NONINTERACTIVE=1 claude -p "/dev-next" --cwd /Users/alexlisitzky/dual-research > "$LOG" 2>&1`. Halt-on-failure path tails the last 50 log lines so the user sees what broke without opening the file. Between iterations the supervisor re-reads `current_queue('specs')` from disk and also calls `find_active_checkpoint` so resume-mode iterations re-pick the same spec instead of advancing.

- **`~/.claude/skills/dev-next/SKILL.md`**:
  - Step 5 — new resume-mode exception. If exactly one spec is `in_progress` AND its latest handoff is `kind: in-spec-checkpoint` for that same spec, that's the iteration's target (skip step 6's queue pick).
  - Step 6 — skipped under resume mode.
  - Step 7 — `DR_DEV_NEXT_NONINTERACTIVE=1` bypass for the per-spec greenlight. Still surfaces the one-line summary to the log.
  - Step 9 — new resume-mode branch. When the picked spec resolved via `find_active_checkpoint`, skip steps 10–14 (reconcile / in_progress flip / title stamp / branching all done last cycle), `git checkout <branch>`, jump to step 15 at `next_subsection`, emit `resume_started`.
  - Step 15-CP — L-spec checkpoint cadence. After each `## 2.N`, assess coarse context pressure; if past threshold, write the checkpoint handoff, commit + push branch, emit `checkpoint_written`, leave status at `in_progress`, exit `RC == 0`.

- **`scripts/spec_lifecycle/checkpoint.py`** ([scripts/spec_lifecycle/checkpoint.py](../scripts/spec_lifecycle/checkpoint.py)):
  - `classify_handoff_kind(fm)` — `"post-deploy"` is the default for missing/empty `kind:` (backwards-compat with every handoff written before this spec). Unknown kinds pass through as-is so future specs can add new kinds without touching this function.
  - `CheckpointHandoff` dataclass + `read_checkpoint(path)` — typed parse, returns `None` for non-checkpoint handoffs.
  - `find_active_checkpoint(handoffs_dir, spec_number, spec_status)` — the resume-mode predicate. Gated on `kind == "in-spec-checkpoint"` AND `spec_status == "in_progress"`. Anything else returns `None` and the caller falls through to today's clean-start path.
  - `build_headless_command(spec_number, log_path, project_dir)` — supervisor argv shape, isolated in one helper per spec 0186 §7 (mitigation against `claude -p` CLI drift).

- **`tests/spec_lifecycle/test_checkpoint.py`** ([tests/spec_lifecycle/test_checkpoint.py](../tests/spec_lifecycle/test_checkpoint.py)) — 21 cases. Kind classifier with backwards-compat against legacy handoffs + pass-through of unknown kinds. Checkpoint frontmatter parse with typed fields, safe defaults, parametrised `tests_status`, optional-field omission. Resume-mode predicate: not-in-progress halt, post-deploy handoff falls through, latest-checkpoint wins on multiple, other specs' checkpoints ignored, missing dir tolerated. Supervisor argv shape (literal + path-object input).

- **Version + CHANGELOG.** `pyproject.toml` and `src/dual_research/__init__.py` bumped 1.32.0 → 1.33.0. CHANGELOG.md gained a `## [1.33.0] — 2026-05-23` section. The spec's stale `target_version: 1.32.0` got displaced because 0173 shipped 1.32.0 between this spec's queue time and its cycle.

- **`runs/queue-drain/`** is automatically gitignored under the existing top-level `runs/` rule in `.gitignore`.

## Tests

- New unit tests: 21/21 green.
- Full suite: `uv run pytest tests/ -q` — **1574 passed**.

## Deploy notes

The deploy hit an upstream Fly lease contention on the first attempt (`lease currently held by 89f4c34c-…@tokens.fly.io, expires at 2026-05-22T23:10:01Z`). The retry surfaced fly's "Found 2 different images" guard because the first attempt had left a partially-promoted state with v403 (old) + v406-attempt (new) machines coexisting. Fly resolved the cluster itself before the retry's bluegreen completed; v407 (the 1.33.0 image) is now sole live with 2 healthy machines.

Sweep ran twice during the recovery, both reported `sweep: no stale blues on dual-research-alex` — the stale machines weren't tagged `safe_to_destroy`, so the existing filter didn't fire. Fly destroyed them itself before the second sweep ran. The cluster ended up at the expected 2-machine size organically.

```
sweep: no stale blues on dual-research-alex
```

Smoke: `curl -sf https://dual-research-alex.fly.dev/api/health` → `{"ok":true,"version":"1.33.0","backend":"supabase"}`.

## What I'd watch next time

This is meta — spec 0186 was supposed to fix the very drain problem that caused it to be bumped to position 1. It implemented itself in a fresh context and shipped cleanly under the *old* inline-supervisor contract. The remaining 13 specs in the queue need the *new* supervisor contract — which only takes effect on a fresh `/dev-queue-run` invocation, because the current invocation already loaded the old skill body into context.

## Deferred during implementation

- **Supervisor end-to-end integration tests (spec 0186 §6 first three bullets)** — the synthetic-2-spec drain test, the supervisor-halts-on-failure test, and the L-spec checkpoint round-trip test all need a subprocess-spawning harness that mocks or wraps `claude -p`. The unit-testable helpers are covered ([tests/spec_lifecycle/test_checkpoint.py](../tests/spec_lifecycle/test_checkpoint.py)), but the supervisor itself is shell logic in `~/.claude/skills/dev-queue-run/SKILL.md` — that file is not Python code, it's instructions the agent follows, so it's not directly unit-testable. A follow-up spec could either (a) factor the supervisor into a Python `scripts/queue_drain_supervisor.py` that the skill body merely wraps, then unit-test that; or (b) write integration tests that spawn `claude` against a stub spec dir and assert the resulting handoffs/PRs match expectations. Both are non-trivial — the harness alone is its own spec.
- **L-spec budget-check heuristic specifics** — spec 0186 §5 ("Out of scope") explicitly says "no token-counter infra" and "the L-spec checkpoint trigger uses a simple heuristic". The current spec body shipped the cadence (per-`## 2.N`) and the artefact shape, but does not specify *what* the heuristic should be — "session age" or "coarse signal" are both gestured at. The first real L-spec drain will be the calibration moment; if the per-`## 2.N` trigger is too aggressive or too lax, refine in a follow-up.
- **Stale-blue sweep filter** — the deploy notes above record the second occurrence of fly leaving stale machines that are *not* tagged `safe_to_destroy` (the first was spec 0162's motivation). The sweep filter doesn't catch this shape. A follow-up could extend `scripts/sweep_stale_blues.sh` to also catch machines on a not-currently-released image, gated behind a stricter heuristic so it never hits a green.

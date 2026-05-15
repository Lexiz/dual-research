---
spec: 0007
title: Rate-limit-aware retry + resume from prior session
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.8.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/7"
---

# Spec 0007 — Rate-limit backoff + resume

## Context

Spec 0006 shipped prompt caching, which helps a lot but doesn't fully solve the prod-tier rate-limit problem. Phase 2 around round 6 still hits the Anthropic 30K-tok/min cap because cache _writes_ (the dynamic suffix that grows each round) count toward the per-minute input budget. Two complementary fixes make the orchestrator resilient:

1. **Rate-limit-aware backoff** — catch 429 errors at the agent layer, read the `retry-after` header (or a sensible default), sleep, retry once. The Anthropic SDK does this automatically for transient 429s but the budget-exhaustion 429 we see comes back without retry-after and surfaces immediately. We need our own bounded retry.

2. **Resume from prior session** — if a run dies (rate limit, crash, Ctrl-C, network), the session directory has full state on disk. `dual-research --resume <session-dir>` should load existing state and pick up at the phase where it left off, skipping completed phases.

Together these mean: a partial run is recoverable, and most rate-limited runs will heal themselves automatically.

After this spec, the backend is feature-complete and the orchestrator can be left to run unattended even on rate-limited tiers.

## Proposed change

### Rate-limit retry

Add a small helper in `agents/base.py`:

```python
async def with_rate_limit_retry(
    call: Callable[[], Awaitable[T]],
    *,
    max_attempts: int = 3,
    base_backoff_seconds: float = 30.0,
) -> T:
    """Retry on 429. Honour retry-after header; default to exponential backoff."""
```

`ClaudeAgent.run` and `GptAgent.run` wrap their SDK call in `with_rate_limit_retry`. On 429:

- Parse the `retry-after` header from the response (Anthropic and OpenAI both include it when known).
- If absent, sleep `base_backoff_seconds * 2**attempt + jitter`.
- Retry up to `max_attempts` times. After exhaustion, raise `AgentError`.

Per-call attempts logged to transcript via a `rate_limited_backoff` event so we can audit how often it kicks in.

### Resume from prior session

Add `--resume PATH` to the CLI:

```
dual-research --resume runs/20260515-120623-prod-postgres-vs-sqlite
```

On resume:

1. Load `<path>/state.json`. If absent, fail loud.
2. Read the brief from `<path>/brief.md` (no re-ingest).
3. Skip phases whose state has already advanced past them (Phase 0 if state.phase in {phase1, phase2, ...}; etc.).
4. For each in-progress phase, the existing turn-file IO helpers already let the phase pick up at the next round (`startRound = max(turn_round) + 1`). Spec 0003's Phase 2 driver already does this implicitly via `list_turns`.
5. Re-build the `SessionContext` with the existing `metrics.json` so the cost ticker resumes its running total.

Edge cases:

- **Mid-round failure**: if Phase 2 round 3 wrote claude's turn but failed before openai's, the orchestrator should re-call only the missing agent on round 3. The simplest impl: detect partial round (one turn file present, the other absent) and re-call the missing side. Defer this complexity to a later spec if needed; for v1 we re-run the entire interrupted round.
- **Phase 4 in-progress with drafter revising**: `state.draft_round` is persisted; the resumed run reads the current draft file.

### CLI surface

```
dual-research --resume <path>            # resume an existing session
dual-research --resume <path> --extend-caps 4   # bonus: bump both caps by N
```

The resume path is mutually-exclusive with `--prompt`/`--brief`/`--notion`.

### Files added or modified

- `src/dual_research/agents/base.py` — `with_rate_limit_retry` helper
- `src/dual_research/agents/anthropic_agent.py` — wrap stream-init in retry
- `src/dual_research/agents/openai_agent.py` — wrap responses.create in retry
- `src/dual_research/cli.py` — `--resume` arg, `--extend-caps`, mutual exclusion
- `src/dual_research/orchestrator/run.py` — resume path: load state, skip completed phases
- `src/dual_research/orchestrator/_resume.py` (new) — small helpers to detect partial round, find next round number, etc.
- `tests/agents/test_retry.py` (new) — mock 429 and verify backoff
- `tests/orchestrator/test_resume.py` (new) — make a session dir with phase2 partially done, resume, verify it skips phase0/1 and continues
- `CHANGELOG.md`, `pyproject.toml`, `__init__.py` — 0.7.0 → 0.8.0

## Out of scope

- **Mid-round partial-turn recovery.** v1 re-runs the entire interrupted round (paying the cost of one duplicate call). A future spec could detect partial rounds and only re-call the missing agent.
- **Resumed-run cost rollup.** New metrics.json starts from scratch on resume; the prior run's costs are in the existing file. A future spec could merge them. For v1 we accept the simple behaviour and let the transcript be the source of truth.
- **Inter-round sleep.** Could add a `--inter-round-sleep N` flag for proactive rate-limit avoidance. v1 relies on reactive retry-on-429 instead — simpler, more reliable.

## Test plan

- [ ] Unit: `with_rate_limit_retry` calls the inner function once on success; up to N times on repeated 429; raises after exhaustion
- [ ] Unit: rate-limit retry honours `retry-after` header value
- [ ] Unit: `--resume` rejects `--prompt`/`--brief`/`--notion` combinations
- [ ] Unit: `--resume` fails loud when the path doesn't exist or has no state.json
- [ ] Unit: `run_session` with an existing session-state at phase2 skips phase0+phase1
- [ ] Unit (stub agents): an interrupted Phase 2 round 3 (claude turn-file present, openai missing) resumes correctly into round 3
- [ ] Live verification: run a tiny end-to-end with caps so small it hard-caps in Phase 2 → use `--resume --extend-caps 4` to extend → run completes
- [ ] All 93 prior tests still pass

## Risks

- **Bad retry-after parsing → over-sleep or under-sleep.** Mitigation: clamp to [5s, 300s]; default to base_backoff_seconds if parsing fails.
- **Resume picks up stale state.** Mitigation: rely on existing on-disk artifacts only; never re-execute completed phases. If user wants a fresh run, they start a new session.
- **Resume on a partial-round leaves orphan turn files.** Defensive: when re-running a round, overwrite any existing turn files for that round. The `write_atomic` helper handles this idempotently.

---
spec: 0002
title: Orchestrator scaffold + Phase 0/1 end-to-end
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.3.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/2"
---

# Spec 0002 — Orchestrator scaffold + Phase 0/1 end-to-end

## Context

Steps 1–4 built the static pieces: CLI, input ingest, agent runners, protocol module (prompts + parsers + convergence + tiebreak). Nothing actually runs the protocol yet.

This spec adds the orchestrator scaffolding (session directory, state persistence, transcript log, event bus, metrics) and wires up the first two phases of the protocol so we can do an end-to-end run on a synthetic brief — both agents preflight the brief in parallel, then both agents produce a Phase 1 research draft in parallel. All artifacts land on disk in a session directory. No human-in-loop at any decision point.

The end-state of this spec: `dual-research --prompt "..."` produces a session directory at `runs/<id>/` containing the brief, both preflight reports, both Phase 1 drafts, a state file, a transcript, and metrics. Phases 2–4 come in subsequent specs.

Web search wiring is deliberately deferred to a follow-up spec — Phase 0 and Phase 1 work fine without it for synthetic-brief verification, and Phase 2 corroboration is where search becomes load-bearing.

## Proposed change

### New modules

```
src/dual_research/
  persistence/
    __init__.py
    session.py         # SessionDirectory: dir layout, mkdir, write helpers
    state.py           # SessionState dataclass, load/save with atomic writes
    transcript.py      # append-only JSONL event writer
    metrics.py         # per-agent + total token/cost rollup, persisted
  events/
    __init__.py
    types.py           # event dataclasses (RunStarted, PhaseStarted, TurnEnded, ...)
    bus.py             # in-memory async pub/sub
  orchestrator/
    __init__.py
    run.py             # the state-machine driver
    phase0.py          # preflight (parallel)
    phase1.py          # research (parallel)
```

### Session directory layout

```
runs/<YYYYMMDD-HHMMSS>-<slug>/
  brief.md             # already written by ingest
  state.json           # phase, drafter, agreed_plan_hash, etc.
  transcript.jsonl     # append-only event log
  metrics.json         # tokens + USD per agent + totals
  phase0/
    preflight-claude.md
    preflight-openai.md
  phase1/
    draft-claude.md
    draft-openai.md
  # phase2/ phase3/ phase4/ added in later specs
```

### State shape

```python
@dataclass(frozen=True)
class SessionState:
    phase: str                          # "phase0" | "phase1" | "phase2" | "phase3" | "phase4" | "done"
    drafter: str | None                 # set after Phase 2 convergence
    agreed_plan: str | None             # verbatim AGREED_PLAN block
    final_surfaced_disagreements: list  # list[FsdItem]
    draft_round: int                    # 1-indexed; bumps on Phase 4 revisions
    final_emitted_to: str | None
```

New sessions start at `phase: "phase0"`. Persisted to `state.json` via atomic write (temp file → fsync → rename).

### Event bus

In-memory async pub/sub. The orchestrator publishes events; the transcript writer subscribes and persists every event to `transcript.jsonl`. Future SSE / UI subscribers attach to the same bus without orchestrator changes.

Event types for this spec:
- `RunStarted` (session_dir, slug, model_tier)
- `PhaseEntered` (phase)
- `PhaseExited` (phase, duration_ms)
- `TurnStarted` (agent, phase, label)
- `TurnEnded` (agent, phase, label, usage, cost_usd, duration_ms, finish_reason)
- `Phase0Complete` (claude_status, openai_status, brief_issues_claude, brief_issues_openai, brief_needs_input)
- `Phase1Complete` (claude_chars, openai_chars)
- `CostUpdate` (per-agent + total running totals)
- `RunCompleted` (phase reached, exit_code)
- `RunFailed` (phase reached, error message)

### Phase 0 orchestration

Both agents call `preflight_prompt(brief_content, agent_name)` in parallel via `asyncio.gather`. Each result is written to `phase0/preflight-<agent>.md`. Parsed with `parse_preflight_turn`. If either agent emits `BRIEF_NEEDS_INPUT`, log a warning to stdout + emit a `Phase0Complete` event with `brief_needs_input=true` BUT continue (autonomous). The intent here is observability, not a pause point.

### Phase 1 orchestration

Same shape: both agents call `research_prompt` in parallel. Outputs to `phase1/draft-<agent>.md`. No parsing / convergence at this phase — these are free-form research drafts.

### CLI wiring

Default behaviour changes: without `--ingest-only`, the CLI now runs Phase 0 + Phase 1 after ingest. Output messages show live cost ticker and exit with code 0 on success.

After Phase 1 completes successfully, the CLI prints a message indicating Phases 2–4 are not yet wired up. This is the natural in-progress state during build.

### Cost ticker

Each `TurnEnded` event triggers a stdout line like:

```
[claude] phase0  in=140  out=320  $0.0061  3.2s
[openai] phase0  in=140  out=290  $0.0046  4.1s
                                  total: $0.0107
```

### Files added or modified

- `src/dual_research/persistence/` (new package — 4 modules)
- `src/dual_research/events/` (new package — 2 modules)
- `src/dual_research/orchestrator/` (new package — 3 modules)
- `src/dual_research/cli.py` — wire orchestrator into the default flow
- `tests/persistence/` (new) — unit tests for state round-trip, transcript writer, metrics rollup
- `tests/events/` (new) — bus pub/sub tests
- `tests/orchestrator/` (new) — phase logic mocked-LLM tests
- `CHANGELOG.md`, `pyproject.toml`, `__init__.py` — version 0.2.0 → 0.3.0

## Out of scope

- **Web search wiring.** Defer to spec 0003 alongside Phase 2 (where corroboration on `[U]` claims actually needs search).
- **Phase 2/3/4 orchestration.** Each gets its own spec.
- **Repair-turn flow.** Not exercised in Phase 0/1 (preflight + research are single-shot, not turn-based).
- **Resume from prior session.** Defer until Phase 2 lands, since that's the first place a long-running negotiation makes resume valuable.
- **`--auto-continue` flag.** Autonomous-only design means soft cap = log + continue by default; the flag from the original is not needed.
- **Cost-budget cap / abort.** Future spec.

## Test plan

- [ ] Unit: `SessionState` round-trips through JSON without loss
- [ ] Unit: atomic write does not corrupt the existing state.json on a simulated failure
- [ ] Unit: `Transcript` appends one JSON line per event, recoverable via `for line in open(...)`
- [ ] Unit: `Metrics` rollup matches per-call sums; persisted JSON re-loads correctly
- [ ] Unit: `EventBus` delivers a published event to all subscribers; unsubscribe stops delivery
- [ ] Unit: `Phase0` orchestration runs against mocked agents, writes correct artifacts, publishes the right events in the right order
- [ ] Unit: `Phase1` orchestration same
- [ ] E2E: `dual-research --prompt "<synthetic-brief>" --models test` completes successfully against real API; verify session dir has all expected files; verify `phase0_complete` and `phase1_complete` events are in transcript.jsonl; verify metrics.json totals match observed stdout
- [ ] All 36 existing tests still pass

## Risks

- **Synthetic E2E costs real money.** Mitigation: use test tier (`claude-haiku-4-5` + `gpt-5-mini`) with a short brief. Expected: $0.05–0.30 total. If it exceeds $0.50, abort and inspect.
- **State drift on partial failures.** Mitigation: state.json writes are atomic; transcript.jsonl is append-only and resumable; metrics.json is best-effort.
- **Phase 0 / Phase 1 prompts produce malformed output.** No parsing required for Phase 1; Phase 0 has lenient parser. If preflight fails to parse, log clearly and continue (autonomous).
- **Future event-bus subscribers (UI) might be high-frequency, slow, or fail.** Out of scope for this spec — the bus is async, slow subscribers don't block publishers. Subscriber failures are caught and logged.

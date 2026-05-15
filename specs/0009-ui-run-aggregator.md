---
spec: 0009
title: UI run aggregator
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.10.0
created: 2026-05-15
pr: "https://github.com/Lexiz/dual-research/pull/9"
---

# Spec 0009 — UI run aggregator

## Context

The Claude Design output (in `~/Trimble/handoff/`) is a complete React prototype for a read-only monitoring dashboard. Its data layer expects a single nested `Run` object (`agents.{claude,gpt}`, `disagreements[]` with per-round progression, `errors[]`, `phaseTimings`, `round.{current,soft,hard}`, `budget`). The backend at v0.9.0 emits a different shape: granular events on an in-memory `EventBus` plus persisted artifacts under `runs/<id>/`.

This spec adds a Python-side **read-only aggregator** that bridges the two. Given a session directory, it returns a `Run` matching the UI shape verbatim. This is the foundation for specs 0010 (HTTP server + SSE) and 0011 (UI bundle integration); on its own it has no user-visible surface.

Per project decision, **the backend is not changing** to fit the UI. Where the UI asks for something the backend doesn't emit (per-token streaming, rich error taxonomy, budget caps), the aggregator either derives a sensible approximation from existing data or returns `null` and the UI adapts (specs 0010 / 0011).

## Proposed change

### New package `src/dual_research/ui/`

Pure read-side module. No new dependencies. No changes to existing backend code.

```
src/dual_research/ui/
├── __init__.py
├── models.py          dataclasses for Run, AgentState, Disagreement, RunError, RunListRow
├── aggregator.py      load_run_snapshot(), apply_event(), summarize_run()
├── disagreements.py   parse Phase 2/4 round files into Disagreement[] with progression
├── errors.py          map transcript events → RunError[] (UI taxonomy)
└── labels.py          backend↔UI agent-label translation; display-id derivation; status maps
```

### `models.py` — UI-shaped dataclasses

Frozen `kw_only` dataclasses mirroring `~/Trimble/handoff/README.md` §5.1 / §5.2 / §5.3 field-for-field. Every field is JSON-serializable via `dataclasses.asdict`. The UI consumes JSON via SSE; the aggregator returns dataclasses internally, the server layer (spec 0010) serializes.

Key shapes (abbreviated):

- `Run(id, display_id, topic, status, phase, started_at_ago, drafter, phase_timings, round, budget, agents, disagreements, errors, error?)`
- `AgentState(status, current_turn, last_turn, tokens, cost, model_id)` — adds `model_id` so the UI can show the actual model name from `RunStarted` instead of hard-coding `claude-sonnet-4.5` / `gpt-5.1`.
- `Disagreement(id, phase, round, opened_round, closed_round?, status, deadlocked?, raised_by, short_label, point, claude_position, gpt_position, resolution?, progression[])`
- `RunError(id, timestamp, rel_ago, code, severity, run_id, agent, phase, where, summary, detail, retried, resolved)`
- `RunListRow(id, display_id, status, phase, topic, started_at_ago, duration, cost, rounds?)`

### `labels.py` — translation tables

- `BACKEND_TO_UI_AGENT = {"claude": "claude", "openai": "gpt"}` — translation happens once, here. Everything downstream uses the UI vocabulary.
- `display_id(session_dir: Path) -> str` — `sha1(session_dir.name)[:4]` to match the UI's `7f3a`-style 4-char id. Full dir name remains the canonical id; the 4-char form is for chrome only.
- `derive_agent_status(phase: str, agent_active: bool, drafter: str | None) -> str` — maps `(phase, role)` to one of `idle | thinking | drafting | responding | reviewing | waiting`:
  - phase0 + active → `thinking`
  - phase1 + active → `drafting`
  - phase2 + active → `responding`
  - phase3 + active + drafter → `drafting`
  - phase4 + active + drafter → `drafting`
  - phase4 + active + reviewer → `reviewing`
  - phase in progress + agent inactive → `waiting`
  - run terminal (`done` / `failed` / hard cap) → `idle`

### `aggregator.py` — three entry points

```python
def load_run_snapshot(session_dir: Path) -> Run:
    """Build a complete Run by replaying transcript.jsonl + reading session files.

    Works for both in-flight and completed runs. Caller decides how often to
    re-call; this is a pure function over disk state."""

def apply_event(run: Run, event: dict, session_dir: Path) -> Run:
    """Incrementally update a Run with one transcript event.

    Returns a new Run (frozen dataclasses). Used by the SSE tail loop in
    spec 0010 to avoid full reloads on every line."""

def summarize_run(session_dir: Path) -> RunListRow:
    """Cheap one-row summary for the /api/runs list endpoint.

    Reads state.json + metrics.json + brief.md H1 only — does not parse turn
    files or reconstruct disagreements."""
```

**`load_run_snapshot` outline:**

1. Read `state.json`, `metrics.json`, `brief.md` (H1 → `topic`).
2. Read `transcript.jsonl` line-by-line, feed each event through `apply_event` starting from an empty Run.
3. Augment with on-disk file lookups (phase round bodies, drafts, final.md) — done lazily / referenced by path, since the UI fetches bodies via a separate endpoint (spec 0010).
4. Call `disagreements.reconstruct(session_dir)` to populate `run.disagreements`.
5. Call `errors.derive(transcript)` to populate `run.errors`.
6. Set `budget = None` — budget meter is a client-side preference (localStorage); the aggregator has nothing to populate.

**`apply_event` event handling table:**

| Transcript event | Run mutation |
|---|---|
| `run_started` | set `id`, `display_id`, `status='running'`, model ids on agents, `round = {current: 0, soft, hard}` |
| `phase_entered` | set `phase` (parse `phase0..phase4` → 0..4); update agent statuses |
| `phase_exited` | record `phase_timings[N] = duration_ms / 1000` |
| `turn_started` | set the named agent's status to active state (per `labels.derive_agent_status`) |
| `turn_ended` | accumulate `tokens.in/out` and `cost`; set status to `waiting`; populate `last_turn.index` |
| `phase2_round_complete` | set `round.current`; trigger lazy disagreement re-parse on next snapshot |
| `phase4_round_complete` | set `round.current` (Phase 4 reuses the cap); flag review-phase context |
| `cost_update` | redundant with `turn_ended` accumulation; ignored to avoid double-count |
| `final_emitted` | set `status` per terminal: `completed` if approved, `deadlocked` if hard cap, etc. |
| `run_completed` | set terminal status; record final cost |
| `run_failed` | set `status='errored'`, populate `error = {when, where, code, detail}` |
| `repair_invoked`, `soft_cap_hit`, `hard_cap_hit` | handled in `errors.py`, no Run-shape mutation |

**Phase enum mapping:** UI uses `phase: 0..5` where 5 = done. Backend writes `state.json["phase"]` as `"phase0".."phase4" | "done"`. Aggregator translates:

```python
PHASE_MAP = {"phase0": 0, "phase1": 1, "phase2": 2, "phase3": 3, "phase4": 4, "done": 5}
```

### `disagreements.py` — parse the `Substantive disagreements I'm holding` section

The Phase 2 protocol asks each agent to list their tracked disagreements in a `## Substantive disagreements I'm holding` section with **stable D-N identifiers** that both agents reuse (verified against `runs/20260515-124552-cache-multi-round/phase2/round-02-openai.md` and `round-04-claude.md`). This makes reconstruction precise — no fuzzy clustering needed.

```python
def reconstruct(session_dir: Path) -> list[Disagreement]:
    """Reconstruct the Disagreement list for both Phase 2 and Phase 4.

    For each round file (phase{2,4}/round-NN-{claude,openai}.md):
      1. extract_fenced_section(text, "Substantive disagreements I'm holding")
      2. parse D-N entries: "- D-N: <label> — status: <state>"
      3. extract sub-fields:
           (a) "<the contested-point statement>"
           (b) My position: <agent's position>
           (c) <Other>'s position: <other agent's position>
           (d) Why I'm not yet conceding: <reasoning>
           (e) Materiality: <impact>
      4. Cross-merge claude and openai turns for the same round to fill both
         `claude_position` and `gpt_position`.
      5. Build the progression timeline by diffing successive rounds:
         - first appearance → 'raised' (by the agent in whose file it appears)
         - status flip 'open' → 'open' across rounds → 'pushed back' or 'restated'
         - status 'resolved' → 'conceded' (by the agent who flipped it)
         - status 'non_blocking_limitation' → 'aligned'
         - disappearance from both agents' sections → finalize closed_round
    """
```

**Edge cases handled:**

- **Round file missing** (run still in-progress mid-round): aggregator returns the disagreements parsed so far.
- **Malformed-N rerolls** (`round-NN-{agent}.malformed-N.md`): ignored; only the canonical `round-NN-{agent}.md` is parsed.
- **Agent disagreement-section absent**: the disagreement still appears if the other agent listed it (raised-by = the other agent).
- **D-N renumbering between rounds**: not handled in v1. The protocol is stable on this; if observed in real runs, follow-up spec.

**Heuristic limitations documented in module docstring:**

- The action taxonomy (`raised`, `rejected`, `pushed back`, `restated`, `conceded`, `aligned`) is derived from status transitions, not directly emitted. Edge cases where an agent restates without changing status are labeled `pushed back` (close enough for the timeline visualization).
- The `short_label` is the head of the D-N line ("Compiler performance (tsc-go)"). The UI's 4–6 word headlines are usually that already; longer labels truncate at the UI layer.

### `errors.py` — sparse but correct UI error taxonomy

Maps the four backend event types that signal something error-shaped:

| Backend event | UI `code` | severity | resolved |
|---|---|---|---|
| `repair_invoked` | `INVALID_TURN_FORMAT` | `error` | `recovered` (the next turn parsed) |
| `soft_cap_hit` | (info-level entry; UI shows as a yellow row) | `warning` | `recovered` |
| `hard_cap_hit` | (a synthetic `HARD_CAP_HIT` code; UI taxonomy doesn't have this — added to `code` enum loosely) | `warning` | `halted` |
| `run_failed` | `ORCHESTRATOR_PANIC` | `critical` | `halted` |

Other UI codes (`STREAM_DISCONNECTED`, `RATE_LIMIT_EXCEEDED`, `TIMEOUT_EXCEEDED`, `CONTEXT_OVERFLOW`, `CHECKPOINT_WRITE_FAILED`) are documented as placeholders that don't fire in v1. The agent rate-limit retries happen silently inside `with_rate_limit_retry`; surfacing them would need a new event type (deferred).

`where` is built as `"phase-{N} / round-{NN} / {agent}"` mirroring the UI samples.

### Tests under `tests/ui/`

Goldens against fixture session dirs (we already have nine real runs in `runs/`):

- `test_aggregator.py`
  - `test_load_completed_run` — uses `runs/20260515-124552-cache-multi-round` (full Phase 0–4 + final.md). Assert `Run.status == 'completed'`, `phase == 5`, agents have expected token totals, drafter set, all phase_timings populated.
  - `test_load_partial_run` — uses an early-phase fixture run (Phase 2 in-progress). Assert phase + round, status `running`, drafter possibly null.
  - `test_phase_map_translation` — every backend phase string maps correctly.
  - `test_display_id_stable` — same dir always produces the same 4-char id.
  - `test_agent_label_translation` — `openai` always becomes `gpt` in the output.
- `test_disagreements.py`
  - `test_parse_d_lines` — golden test against `runs/20260515-124552-cache-multi-round/phase2/round-04-claude.md` (real file with D-1..D-6 in resolved states).
  - `test_progression_timeline` — across multiple rounds, ensure first appearance is `raised` and final `resolved` flip is `conceded`.
  - `test_cross_agent_merge` — claude's view of D-3 + openai's view of D-3 merge into one Disagreement with both positions filled.
  - `test_missing_round_file` — aggregator returns partial results when a mid-round file is absent.
- `test_errors.py`
  - `test_repair_invoked_to_invalid_format` — synthetic transcript with one `repair_invoked` event yields one `RunError` with code `INVALID_TURN_FORMAT`.
  - `test_run_failed_to_orchestrator_panic` — synthetic `run_failed` event maps correctly.
  - `test_cap_hits` — soft/hard cap mappings.
- `test_labels.py`
  - `test_derive_agent_status_truth_table` — every `(phase, active, drafter)` combination produces the expected UI status.

Total: ~15 tests. Target ~95% line coverage on the new module.

### CHANGELOG + version bump

- `pyproject.toml` and `src/dual_research/__init__.py`: `0.9.0` → `0.10.0`.
- `CHANGELOG.md`: new `## [0.10.0]` section under `[Unreleased]`, plus the placeholder back at top.

## Out of scope

- **HTTP server, SSE, REST endpoints.** Spec 0010.
- **UI bundle integration (static files, fetch wiring, hash router).** Spec 0011.
- **New backend events.** Per project decision: backend stays at its v0.9.0 surface. If a UI requirement can't be met (live token streams, rich error taxonomy, budget enforcement), the spec documents the limitation and the UI adapts (or a future spec backfills the event).
- **Disagreement reconstruction for Phase 0 / 1 / 3.** Phase 0/1 don't have negotiation; Phase 3 is single-shot. Only Phase 2 and Phase 4 produce `Disagreement` entries.
- **File-body endpoints.** Returning raw markdown for round files / briefs / drafts is the server's job (spec 0010). This spec defines paths only.

## Test plan

- [ ] All 15 new tests pass (`uv run pytest tests/ui/ -q`)
- [ ] All 104 existing tests still pass (`uv run pytest tests/ -q`)
- [ ] `load_run_snapshot(runs/20260515-124552-cache-multi-round)` returns a `Run` whose `disagreements` list non-empty, has at least D-1..D-6, all status `resolved` (matches the on-disk reality)
- [ ] `summarize_run` over each of the 9 existing fixture session dirs produces a valid `RunListRow` with no exceptions
- [ ] mypy / type-checking passes on the new module (matches existing src/ standard)

## Risks

- **Disagreement parser brittleness.** The `## Substantive disagreements I'm holding` section format isn't a hard contract — it's the agent following the protocol prompt. If an agent deviates (formatting variations, missing sub-fields), the parser silently drops fields. Mitigation: parser is forgiving (returns partial Disagreement with available fields); tests against real fixtures verify the common case; documented as v1 limitation.
- **D-N ID stability assumption.** Cross-round D-N reuse is observable in our fixtures but not enforced by the protocol. If a run renumbers D-N between rounds, the progression timeline fragments. Mitigation: log a warning when a round drops a D-N that the next round reintroduces with a different number; the visible failure is "two disagreement cards instead of one" which is acceptable for v1.
- **Phase 4 disagreement section.** I haven't visually confirmed Phase 4 round files use the same `## Substantive disagreements I'm holding` section as Phase 2 (Phase 4 may emit `## Open issues for drafter` instead). Mitigation: during implementation, inspect Phase 4 fixtures; if the section name differs, the parser tries both ("Open issues for drafter", "Substantive disagreements I'm holding"). If neither is present, the Phase 4 tab shows an empty disagreement list — gracefully degraded, not broken.
- **Aggregator perf on large transcripts.** `load_run_snapshot` reads the entire `transcript.jsonl` on each call. Real transcripts are ~50–500 lines (one line per event over ~10–25 model calls). Even a 5,000-line transcript is sub-millisecond to parse. `apply_event`-from-current-state is the incremental path the SSE server uses. No perf concern in v1.

## Open questions

None — the user explicitly said the frontend should follow what the backend emits and we'll iterate together later if anything looks thin.

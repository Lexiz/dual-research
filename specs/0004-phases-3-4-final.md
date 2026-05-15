---
spec: 0004
title: Phases 3 + 4 — drafting, review, and final document emission
label: new-feature
version-bump: MINOR
status: proposed
target-version: 0.5.0
created: 2026-05-15
pr: ""
---

# Spec 0004 — Phases 3 + 4 + final document emission

## Context

Spec 0003 brought the orchestrator to phase3-ready: Phase 2 produces an agreed plan + drafter + (optional) FSDs in `state.json`. This spec implements the last two phases and emits the final converged document.

Phase 3 is a single-shot agent call by the agreed drafter: read the brief + both Phase 1 drafts + agreed plan + FSDs + full Phase 2 conversation, write `phase3/draft-v1.md`.

Phase 4 is a turn-based review loop similar in shape to Phase 2: both agents alternate, the DRAFTER may emit revisions (new `draft-vN.md` files), the REVIEWER comments. Loop ends when both emit `STATUS: APPROVED` with `OPEN_ISSUES: 0`, or hard cap hit.

On Phase 4 convergence, a metadata header is prepended to the final draft and written to `final.md` in the session root (plus copied to `--out` if user specified one). The metadata header records the run shape (rounds, drafter, cost, tokens, confidence tag).

End state: `dual-research --prompt "..."` produces a coherent converged final document on disk. Cost: ~$1–3 per real-tier run, ~$0.10–0.50 per test-tier run.

## Proposed change

### Phase 3 — drafting (single-shot)

`src/dual_research/orchestrator/phase3.py`:

```python
async def run_phase3(*, ctx, claude_agent, openai_agent, event_bus, brief_content) -> Phase3Outcome:
    """Single agent call: the agreed drafter writes draft-v1.md."""
    drafter = ctx.state.drafter  # must be set
    agreed_plan = ctx.state.agreed_plan  # hash-verified by Phase 2
    fsds = [FsdItem(**d) for d in ctx.state.final_surfaced_disagreements]

    # Read inputs
    p1 = ctx.session.phase_dir("phase1")
    own_draft = (p1 / f"draft-{drafter}.md").read_text()
    other = "openai" if drafter == "claude" else "claude"
    other_draft = (p1 / f"draft-{other}.md").read_text()
    prior_turns = list_turns(ctx.session, phase="phase2")

    agent = claude_agent if drafter == "claude" else openai_agent
    prompt = drafting_prompt(...)

    result = await run_one_call(agent=agent, prompt=prompt, ...)
    write_atomic(ctx.session.phase_dir("phase3") / "draft-v1.md", result.text)

    ctx.state.phase = "phase4"
    ctx.session.save_state(ctx.state)
    return Phase3Outcome(...)
```

The drafter is determined from state; the other agent does nothing in Phase 3.

### Phase 4 — review loop

`src/dual_research/orchestrator/phase4.py`:

```python
async def run_phase4(*, ctx, claude_agent, openai_agent, event_bus, brief_content,
                    soft_cap, hard_cap) -> Phase4Outcome:
    """Turn-based review. Loop until both APPROVED with OPEN_ISSUES: 0 or hard cap."""
```

Mechanics mirror Phase 2 but use `review_turn_prompt`:
- Each round, both agents call in parallel with the CURRENT draft inlined
- Drafter may emit a revised draft inside the response under `## Revised draft` heading; the orchestrator detects it and writes `phase4/draft-vN.md`, bumping `state.draft_round`
- Validation via `assert_well_formed_review_turn(parsed, agent, round=r)` — strict on round 1 and any APPROVED turn
- Convergence via `is_review_approved`
- Repair flow (same `parse_with_repair` helper, just different validator)
- Soft cap = log + continue (autonomous). Hard cap = emit final with deadlock appendix, exit 51.

### Detecting revised drafts

Convention: the DRAFTER, when revising, writes a `## Revised draft` section inside their turn containing the full updated text of all six required sections. The orchestrator scans for this heading and, if found, extracts the body (up to the next top-level `##`) and writes it as `draft-v{N+1}.md`, then bumps `state.draft_round` and saves state.

A small extractor in `protocol/parse.py`:

```python
def extract_revised_draft(turn_text: str) -> str | None:
    """Return the body of the `## Revised draft` section, or None."""
```

### Final document emission

`src/dual_research/orchestrator/finalize.py`:

```python
def render_metadata_header(*, metrics, state, phase2_outcome, phase4_outcome) -> str:
    """Return the blockquote header that prepends every final document."""

async def emit_final(*, ctx, out_path, phase2_outcome, phase4_outcome) -> None:
    """Write the final draft + metadata header to session/final.md and out_path."""
```

The final document is `phase4/draft-v{state.draft_round}.md` + a metadata header. Both go to:
1. `<session-dir>/final.md`
2. `<out-path>` if `--out` was given

The header records:
- Model IDs + thinking levels
- Run timestamp
- Outcome (APPROVED / DEADLOCKED)
- Phase 2 rounds + drafter
- Phase 4 rounds + draft revisions
- Token totals + cost estimate
- FSD count
- Confidence tag: HIGH / MODERATE / LOW based on rounds and cap hits

### CLI: `--out`

`--out PATH` already exists in the CLI from spec 0001 but was unwired. This spec makes it functional: if set, the converged final is copied (or moved) there in addition to `session/final.md`.

### Events added

- `Phase3Complete(drafter, draft_chars)`
- `Phase4RoundComplete(round, approved, claude_status, openai_status, claude_open_issues, openai_open_issues, draft_round)`
- `Phase4DraftRevised(round, new_draft_round)`
- `Phase4Complete(rounds, approved, final_draft_round)`
- `RunCompleted` already exists; final state extends it

### Files added or modified

- `src/dual_research/orchestrator/phase3.py` (new)
- `src/dual_research/orchestrator/phase4.py` (new)
- `src/dual_research/orchestrator/finalize.py` (new)
- `src/dual_research/orchestrator/run.py` — invoke `run_phase3`, `run_phase4`, `emit_final`
- `src/dual_research/protocol/parse.py` — `extract_revised_draft`
- `src/dual_research/protocol/__init__.py` — re-export
- `src/dual_research/events/types.py` — four new event types
- `src/dual_research/events/__init__.py` — re-export
- `src/dual_research/cli.py` — propagate `--out` to `run_session`
- `tests/orchestrator/test_phase3.py` (new)
- `tests/orchestrator/test_phase4.py` (new)
- `tests/orchestrator/test_finalize.py` (new)
- `CHANGELOG.md`, `pyproject.toml`, `__init__.py` — 0.4.0 → 0.5.0

## Out of scope

- **Web search wiring** — still deferred (spec 0005).
- **Resume from prior session** — still deferred.
- **Phase 4 hard-cap deadlock heuristics beyond "include both last turns"** — minimal; refine later if real runs surface a need.

## Test plan

- [ ] Unit: `extract_revised_draft` returns body of `## Revised draft` section, `None` when absent
- [ ] Unit (stub agents): `run_phase3` writes `draft-v1.md`, advances state to phase4
- [ ] Unit (stub agents): `run_phase4` converges in round 2 with both APPROVED
- [ ] Unit (stub agents): `run_phase4` detects revised draft, bumps `draft_round`, writes `draft-v2.md`
- [ ] Unit (stub agents): `run_phase4` hard-cap path emits final with deadlock appendix
- [ ] Unit: `render_metadata_header` produces expected fields given a Metrics + RunResult
- [ ] E2E (test tier, small caps): full run produces `final.md`. Verify all six required sections present.
- [ ] All 58 existing tests still pass

## Risks

- **Phase 4 prompts produce inconsistent revised-draft formats.** Mitigation: the protocol prompt explicitly tells the drafter "emit a REVISED DRAFT in this turn under a separate `## Revised draft` heading, containing the full updated draft text". If agents emit alternative formats (e.g., diffs), we live with no revision detected and the original draft stays; that's a workable degraded mode.
- **E2E cost.** Phase 4 can run multiple rounds. With test tier and `--hard-cap 5`, expect $0.50–1.50. If a real run hits hard cap, ~$2–5. The cost ticker keeps this visible.
- **Final-document section completeness.** The drafter is responsible for emitting Summary / Findings / Disagreements left open / Open questions / Sources / Confidence ledger. If a section is missing, no automated check fails — the document is what the drafter produced. Future spec may add a post-hoc structural check.

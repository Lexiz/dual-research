---
kind: dev
spec: "0215"
slug: fix-in-round-partner-blindness
title: "Fix in-round partner blindness in list_turns"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: S
created: 2026-05-25
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: unknown
promoted_from_draft: "003"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0215 — Fix in-round partner blindness in list_turns

> **Type:** bug  |  **Severity:** P1 (silent procedural-blocker misfires)  |  **Affects:** all 3 interaction phases (0, 2, 4) — every round after the first
> **Bump:** PATCH — bug fix
> **Evidence:** local run `runs/20260521-010637-dvs-backend-language-choice/phase2/round-05-openai.md` — OpenAI explicitly cites a still-`open` blocker that Claude RESOLVED on disk milliseconds before OpenAI's prompt was built. `runs/` is gitignored; cited for human reference.

This is **Spec 2 of 3** in a sequenced bug-fix batch from the phase-4 / phase-2 investigation. Sibling fixes: spec 0214 (hash-gate deadlock, already queued) and the raiser self-ADDRESS validator gap (draft 004).

---

## 1. Reproduction

**Environment:** dual-research orchestrator at HEAD on 2026-05-25; Deep Research protocol, any of the three interaction phases (0 input-negotiation, 2 plan-negotiation, 4 cross-review). Models: prod-tier `claude` + `openai`.

**Steps:**

1. Fire any DR run that reaches round ≥ 2 of any interaction phase.
2. Watch agents execute sequentially within a round: Claude turn → on disk → OpenAI turn built.
3. In OpenAI's round-N prompt, observe that Claude's `round-N` turn is **not** present in the `Prior turns` section, even though the file exists on disk by the time the prompt is rendered.

**Expected:** Each agent's prompt for round N includes every prior round's turns AND the partner's same-round turn (the one already written to disk), but never the agent's own same-round file. The receiving agent can therefore ADDRESS / acknowledge items the partner emitted moments earlier.

**Actual:** `list_turns` at [`src/dual_research/orchestrator/_turns.py:42`](src/dual_research/orchestrator/_turns.py:42) filters with `if up_to_round is not None and r >= up_to_round: continue`, which excludes **all** same-round files regardless of which agent wrote them. So the second-to-execute agent in each round never sees the first agent's same-round turn.

**Smoking-gun quote** (local `runs/20260521-010637-dvs-backend-language-choice/phase2/round-05-openai.md`):

> "The only remaining procedural blocker is that D-plan-c-05 was raised by Claude and is now in addressed state after my prior turn; Claude, as raiser, still needs to resolve it."

OpenAI was blind to Claude's r5 RESOLVE that had just landed on disk milliseconds before its prompt was built. OpenAI then defers convergence, the orchestrator runs another round, and the run pays an extra full agent round-trip for state that was already on disk.

## 2. Root cause hypothesis

The orchestrator runs the two agents **sequentially** within a round at [`src/dual_research/orchestrator/dr_run.py:271-309`](src/dual_research/orchestrator/dr_run.py:271): Claude's turn is parsed, persisted (`write_atomic(turn_path, result.text)` at L308), and only then does the loop body iterate to build OpenAI's prompt. So the partner file IS on disk before the second prompt builds.

But the prior-turns reader is intentionally strict:

```python
# src/dual_research/orchestrator/_turns.py:42
if up_to_round is not None and r >= up_to_round: continue
```

The strict `>=` was correct as a default — without per-agent context, `list_turns` cannot tell which same-round file is "yours" (to exclude) vs "your partner's" (to include). Today every call site passes `up_to_round=round`, so every call drops both same-round files, even when one is the partner's freshly-written turn.

The fix is purely on the read path: thread `for_agent` through `list_turns` and the three build sites.

## 3. Fix

Add an opt-in `for_agent: str | None = None` parameter to `list_turns`. When set, the same-round filter switches from "drop all" to "drop only the file whose agent matches `for_agent`". When `None`, existing semantics are preserved — no behaviour change for external callers.

### Code changes (verified file:line refs at HEAD on 2026-05-25)

**1. `src/dual_research/orchestrator/_turns.py:25-50` — extend `list_turns`.**

Signature:

```python
def list_turns(
    session: SessionDirectory,
    *,
    phase: str,
    up_to_round: int | None = None,
    for_agent: str | None = None,
) -> list[PriorTurn]:
```

Rewrite the same-round filter to:

```python
if up_to_round is not None:
    if r > up_to_round:
        continue
    if r == up_to_round:
        if for_agent is None or agent == for_agent:
            continue
```

Read literally: skip strictly-future rounds always; for the same round, skip the agent's own file (or skip both files when `for_agent` is unset, preserving the legacy default). Update the docstring to document `for_agent`'s "include partner's same-round turn" semantics, including: when `for_agent` is set, the agent's own same-round file is dropped (the prompt should never echo the agent's own turn back at it).

**2. `src/dual_research/orchestrator/dr_run.py:647-648` — phase 0 build site.** Add `for_agent=agent_name` to the `list_turns` kwargs.

**3. `src/dual_research/orchestrator/dr_run.py:965-966` — phase 2 build site.** Add `for_agent=agent_name` to the `list_turns` kwargs.

**4. `src/dual_research/orchestrator/dr_run.py:1339-1341` — phase 4 build site.** Add `for_agent=agent_name` to the `list_turns` kwargs.

All three live inside `_build` closures that already have `agent_name` in scope from the enclosing call signature — no further plumbing needed.

**Invariant:** "each agent sees the partner's same-round turn, never its own". Apply unconditionally to all three interaction phases — this is the correct semantics in every phase that runs agents sequentially within a round. No phase-specific gating.

## 4. User stories & acceptance criteria

Not a UI bug — skipped per the bug template's "REQUIRED for UI bug fixes" gate. The §5 regression-prevention tests are the load-bearing acceptance criteria.

## 5. Regression-prevention test

**New unit tests in `tests/orchestrator/test_turns.py`** (or wherever `list_turns` is tested; locate via `grep -l "def test.*list_turns" tests/`):

- [ ] `test_list_turns_for_agent_includes_partners_same_round_turn` — write round-N files for both `claude` and `openai`; call `list_turns(..., up_to_round=N, for_agent="openai")`; assert the returned list includes Claude's round-N entry and excludes OpenAI's round-N entry.
- [ ] `test_list_turns_for_agent_excludes_own_same_round_turn` — same fixture; call `list_turns(..., up_to_round=N, for_agent="claude")`; assert Claude's round-N entry is excluded, OpenAI's round-N entry is included.
- [ ] `test_list_turns_default_for_agent_preserves_legacy_semantics` — same fixture; call `list_turns(..., up_to_round=N)` with no `for_agent`; assert both same-round entries are excluded (legacy `r >= up_to_round` behaviour).
- [ ] `test_list_turns_strictly_future_rounds_always_excluded` — write round-(N+1) files for both agents; call with `up_to_round=N, for_agent="openai"`; assert round-(N+1) is excluded regardless of `for_agent` value.

**New regression test: `tests/orchestrator/test_spec_0215_in_round_partner_visibility.py`:**

- [ ] `test_phase2_round_n_openai_prompt_includes_claudes_same_round_turn` — fixture-driven: copy `round-04-claude.md`, `round-04-openai.md`, `round-05-claude.md` from the local failing-run directory into `tests/fixtures/in_round_partner_visibility/phase2/` and commit them. Set up a `SessionDirectory` pointing at the fixture. Rebuild OpenAI's round-5 phase-2 prompt via the same `list_turns(..., up_to_round=5, for_agent="openai")` call the fix wires in. Assert `round-05-claude.md` content (or a unique substring of it) appears in the rendered `prior_turns` block in OpenAI's prompt. Locks in that the actual failing scenario would now show Claude's RESOLVE to OpenAI in the same round.

**Existing `list_turns` callers:**

- [ ] Run the full orchestrator test suite (`uv run pytest tests/orchestrator/ -q`) — the four `_build` call sites change behaviour, but only by *adding* the partner's same-round turn to the prompt context (a strict superset of what the previous prompt contained). Existing tests that assert specific prompt content should pass unless they assert on the *absence* of a same-round partner turn — flag any such test in implementation and update the assertion.

## 6. Blast radius

- `list_turns` callers — grep `list_turns(` across the repo:
  - Three `_build` sites in `dr_run.py` (the ones being updated) pass `for_agent=agent_name`. Each is in an `else` branch handling rounds > 1 — round 1 builds a separate prompt path that does not call `list_turns` at all.
  - Any other callers (dashboard, transcript replay, tests) that pass no `for_agent` get the unchanged legacy behaviour. Verify with `grep -rn "list_turns(" src/ tests/` during implementation; document any hit that needs a different decision.
- `_turns.py` itself — pure read path; no I/O ordering or persistence changes.
- Token budget — agents now see exactly one additional turn per round (the partner's). Negligible for phases 0 and 2; for phase 4 the draft body is already in the prompt, so the partner-turn delta is small. No prompt-size regression risk worth gating on.
- Phase 4 hash gate (spec 0214) — independent. This fix changes prompt-build input; the gate fix changes the convergence check. Either ships first without conflict.

## 7. Out of scope

- Refactoring `list_turns`'s broader semantics — the conservative `for_agent=None` default keeps the change strictly opt-in.
- Phase-4 hash-gate deadlock — spec 0214 (already queued; sibling fix).
- Raiser self-ADDRESS validator gap — draft 004 (separate spec in the same batch).
- Parallelising the in-round agent execution — out of scope; would change the on-disk ordering invariant this fix depends on. Sequential execution remains the contract.
- CHANGELOG / version bump — handled by the standard `/dev-next` flow (`pyproject.toml`, `src/dual_research/__init__.py`, PATCH bump, `### Fixed` entry linking back to this spec).

## 8. Risks

- **Risk:** Some existing test asserts on the *absence* of a same-round partner turn from a built prompt (i.e. depends on the bug as load-bearing behaviour).
  **Mitigation:** Run `uv run pytest tests/orchestrator/ -q` early in implementation; update any such assertion to expect the partner turn. Low likelihood — the bug is silent and most prompt-content tests assert positive presence, not absence.

- **Risk:** Phase 0 round 1 has no prior turns, so the same-round partner turn could leak into rendering paths that assume "round 1 = empty prior_turns".
  **Mitigation:** Round-1 build paths in `dr_run.py:640-644`, `960-963`, `1335-1338` take the `if` branch (no `list_turns` call at all). The `else` branches that call `list_turns` only execute for rounds > 1. No round-1 leakage path exists.

- **Risk:** An external/future caller of `list_turns` passes `for_agent` and expects strict-future filtering on `r > up_to_round` rather than `r >= up_to_round`.
  **Mitigation:** Docstring update explicitly states the semantics; the `for_agent=None` default preserves legacy strict `>=` behaviour for every caller that doesn't opt in. New callers read the docstring.

- **Risk:** OpenAI seeing Claude's RESOLVE same-round causes premature convergence elsewhere (e.g. a phase-2 plan-equality check that now trips one round earlier than before).
  **Mitigation:** This is the intended behaviour — the bug is *delaying* convergence by an extra round. Convergence-gate tests already exist (`tests/orchestrator/test_deep_research.py`, `tests/protocol/test_convergence_spec0089.py`); if they assert specific round counts on a fixture replay, update those counts to reflect the corrected (one-round-earlier) convergence.

## 9. CHANGELOG language

For the version's `### Fixed` section:

> ### Fixed
> - **In-round partner blindness in `list_turns` (spec 0215):** every interaction phase (0, 2, 4) runs agents sequentially within a round, but `list_turns(up_to_round=N)` was dropping both agents' round-N files. The second-to-execute agent never saw its partner's freshly-written turn until the *next* round, silently delaying convergence by one full round in every phase. Added a `for_agent: str | None = None` parameter to `list_turns`; the three `_build` call sites in `dr_run.py` now pass `for_agent=agent_name`, so each agent sees its partner's same-round turn (but never its own). Default behaviour for callers that don't opt in is unchanged.

## Pointers

- Sequential-execution proof: [`src/dual_research/orchestrator/dr_run.py:271-309`](src/dual_research/orchestrator/dr_run.py:271).
- The broken filter: [`src/dual_research/orchestrator/_turns.py:42`](src/dual_research/orchestrator/_turns.py:42).
- Failing run: local `runs/20260521-010637-dvs-backend-language-choice/phase2/round-05-openai.md` (untracked; `runs/` is gitignored).
- Sibling specs in this batch: spec 0214 (hash-gate deadlock, already queued), raiser self-ADDRESS validator gap (draft 004).

---
kind: draft
draft_id: "003"
slug: fix-in-round-partner-blindness
title: Fix in-round partner blindness in list_turns
type: bug
status: draft
created: 2026-05-25
source_session: unknown
---

# Draft 003 — Fix in-round partner blindness in list_turns

## Context

In every interaction phase (0, 2, 4) the agents run sequentially within a
round: agent A writes its turn file to disk, then agent B's prompt is
built and run. But `list_turns` in `src/dual_research/orchestrator/_turns.py`
filters with `if up_to_round is not None and r >= up_to_round: continue`,
which excludes **all** same-round files regardless of which agent wrote
them. So when agent B's prompt is built, A's same-round turn is on disk
but invisible to B.

Smoking gun in
`runs/20260521-010637-dvs-backend-language-choice/phase2/round-05-openai.md`:
"The only remaining procedural blocker is that D-plan-c-05 was raised by
Claude and is now in addressed state after my prior turn; Claude, as
raiser, still needs to resolve it." OpenAI was blind to Claude's r5
RESOLVE that had just landed on disk milliseconds before its prompt was
built. Bug → PATCH bump.

## Sketch / proposed direction

- `src/dual_research/orchestrator/_turns.py:42` — add
  `for_agent: str | None = None` parameter to `list_turns`. When set,
  same-round files (`r == up_to_round`) are included only where
  `agent != for_agent`. When `None`, preserve existing semantics (no
  same-round inclusion at all) so external callers are untouched.
- `src/dual_research/orchestrator/dr_run.py` — three build sites need
  `for_agent=agent_name` passed through:
  - `dr_run.py:647-648` (phase 0 build)
  - `dr_run.py:965-966` (phase 2 build)
  - `dr_run.py:1339-1341` (phase 4 build)
- Verified at HEAD: sequential execution at
  `src/dual_research/orchestrator/dr_run.py:271-309` confirms the
  partner file is on disk by the time the second agent's prompt is
  built. The fix is purely on the read path.
- Apply to all three interaction phases unconditionally — the
  invariant is "agents see their partner's same-round turn, never
  their own".

## Test plan

- New unit test in `tests/orchestrator/test_turns.py` (or wherever
  `list_turns` is tested): after writing a round-N claude turn,
  `list_turns(..., up_to_round=N, for_agent="openai")` includes it;
  `for_agent="claude"` excludes it; default (`None`) preserves
  pre-fix behavior.
- New replay test
  `tests/orchestrator/test_spec_NNNN_in_round_partner_visibility.py`:
  rebuild OpenAI's r5 prompt for phase 2 using the fixture at
  `runs/20260521-010637-dvs-backend-language-choice/phase2/` with the
  fix wired in → assert claude's `round-05-claude.md` content appears
  in the rendered `prior_turns` block.
- Existing `list_turns` tests stay green (default behavior unchanged).

## Files touched

- `src/dual_research/orchestrator/_turns.py` (param + logic)
- `src/dual_research/orchestrator/dr_run.py` (3 call sites)
- `tests/orchestrator/test_turns.py` (extend)
- `tests/orchestrator/test_spec_NNNN_in_round_partner_visibility.py` (new)
- `CHANGELOG.md`
- `pyproject.toml` + `src/dual_research/__init__.py` (PATCH bump)

## UI scope

None. Pure orchestrator change; no frontend / `design-system/` impact.

## Out of scope

- Refactoring `list_turns`'s broader semantics (the conservative default
  keeps it scoped).
- Bug #1 and any other unrelated bugs surfaced in the same review pass —
  each gets its own spec.

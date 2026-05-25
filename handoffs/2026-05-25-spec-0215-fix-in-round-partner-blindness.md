---
spec: "0215"
date: 2026-05-25
version: 1.44.20
pr: https://github.com/Lexiz/dual-research/pull/251
kind: deploy
---

# Spec 0215 — Fix in-round partner blindness in list_turns

Shipped as v1.44.20. The phase-0/2/4 prior-turns reader no longer drops the
partner's freshly-written same-round turn. The second-to-execute agent now
sees the first agent's round-N output in its round-N prompt, eliminating the
silent one-round convergence delay observed in the `20260521-010637-dvs-
backend-language-choice` failing run.

## What landed

- **`list_turns` signature change** at [src/dual_research/orchestrator/_turns.py](src/dual_research/orchestrator/_turns.py):
  added opt-in `for_agent: str | None = None`. Same-round filter rewritten
  to drop strictly-future rounds (`r > up_to_round`) always; for same-round
  files (`r == up_to_round`), drop only the agent's own file when
  `for_agent` is set, else fall through to the legacy "drop both" default.
  Docstring updated to document both branches and the spec-0215 rationale.
- **Three `_build` call sites updated** in [src/dual_research/orchestrator/dr_run.py](src/dual_research/orchestrator/dr_run.py):
  the phase-0 (line 647), phase-2 (line 1002), and phase-4 (line 1376)
  `list_turns(...)` calls now pass `for_agent=agent_name`. All three live
  in `else` branches that only execute for rounds > 1 — round-1 build
  paths don't call `list_turns` at all, so no round-1 leakage path exists.
- **Legacy `phase2.py` / `phase4.py` build paths kept on the default.**
  These paths build both agents' prompts upfront before a parallel
  `asyncio.gather` — neither file is on disk when its sibling's prompt is
  built, so opting into `for_agent` would give them nothing. They continue
  to drop both same-round files (correctly).
- **Unit tests** at [tests/orchestrator/test_turns.py](tests/orchestrator/test_turns.py) cover the four
  `for_agent` branches:
  - `test_list_turns_for_agent_includes_partners_same_round_turn`
  - `test_list_turns_for_agent_excludes_own_same_round_turn`
  - `test_list_turns_default_for_agent_preserves_legacy_semantics`
  - `test_list_turns_strictly_future_rounds_always_excluded`
- **Fixture-driven regression test** at [tests/orchestrator/test_spec_0215_in_round_partner_visibility.py](tests/orchestrator/test_spec_0215_in_round_partner_visibility.py)
  using a literal copy of three turns from the local failing run, committed
  under [tests/fixtures/in_round_partner_visibility/phase2/](tests/fixtures/in_round_partner_visibility/phase2/):
  `round-04-claude.md`, `round-04-openai.md`, `round-05-claude.md`. The
  test asserts that the post-fix `list_turns(..., up_to_round=5,
  for_agent="openai")` call surfaces Claude's round-5 RESOLVE (referencing
  `D-plan-c-05`) in the inlined `prior_turns` block, and that the legacy
  `for_agent=None` path still drops both same-round files (antipodal
  absence).

## Verification

- Full suite: `uv run pytest tests/ -q` → **1950 passed** locally (1944
  baseline + 6 new); deploy-pipeline pytest job ✅.
- Deploy: GH Actions run [26401558212](https://github.com/Lexiz/dual-research/actions/runs/26401558212) — `conclusion: success`.
- Live: `curl https://dual-research-alex.fly.dev/api/health` →
  `{"ok":true,"version":"1.44.20","backend":"supabase"}` (HTTP 200).

## Implementation notes

- Spec line refs to `dr_run.py:647-648 / 965-966 / 1339-1341` drifted to
  `647 / 1002 / 1376` between spec write-up and implementation. The
  reconciler flagged one mechanical-drift hit (`dr_run.py:640 — file
  moved? candidates: …` — the file didn't move, just line numbers
  shifted); the call sites are findable by content (`list_turns(`) and the
  `agent_name` variable was in scope at every site, so the fix was
  mechanical.
- Spec §6 noted that other `list_turns` callers (legacy `phase2.py:165`,
  legacy `phase4.py:169`, the drafting-site `dr_run.py:1206` which doesn't
  pass `up_to_round` at all, and the existing unit tests) should be left
  on the default. Verified during implementation — all three categories
  match the spec's stated expectation; no further plumbing needed.
- No prompt-content test asserted on the *absence* of a same-round
  partner turn (risk §8.1). The full suite passed without any assertion
  updates.
- Convergence-gate tests did not need to be rebased to one-round-earlier
  counts either — the existing tests assert on synthetic fixtures rather
  than replays of the failing run, so round counts were unchanged.
- `dashboard/queue-state.json` was kept out of the feature-branch commit
  per the spec-0214 handoff convention (it diverges from branch-base
  only because `--push-to-main` writes go direct to `origin/main`;
  committing it on the branch would have rolled back later events at
  squash-merge time).

## Pointers

- Failing run that motivated the spec: local
  `runs/20260521-010637-dvs-backend-language-choice/` (untracked).
- The pre-fix filter: prior `_turns.py:42`, now rewritten as a two-clause
  `up_to_round is not None` block.
- Sibling specs in the same bug-fix batch: [spec 0214 — phase-4 hash gate](handoffs/2026-05-25-spec-0214-drop-phase4-agent-emitted-hash-gate.md)
  (already shipped as v1.44.19); raiser self-ADDRESS validator gap (draft 004,
  still queued upstream).

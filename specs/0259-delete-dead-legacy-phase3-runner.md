---
kind: dev
spec: "0259"
slug: delete-dead-legacy-phase3-runner
title: "Refactor: delete the dead legacy phase3 runner (orchestrator/phase3.py:run_phase3)"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: S
created: 2026-05-31
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
# Spec 0229 §2.5 carve-out-disposition convention. Pick one of:
#   ship     — high-priority follow-up, should reach /dev-next
#   defer    — recorded but not actionable soon
#   archive  — informational record only (the default for carve-outs)
disposition: ship
disposition_reason: "Clean low-risk dead-code removal directly mirroring the already-shipped 0257.1 (legacy phase2/phase4 runner deletion); the legacy run_phase3 has no production caller and its only exercises are two test functions, so it ships straight through /dev-next."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0259 — Refactor: delete the dead legacy phase3 runner

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** —
> **Bump:** PATCH — internal dead-code removal, no behavior change on any live path
> **Evidence:** Sibling-phase cleanup noticed while shipping [spec 0257.1](0257.1-delete-dead-legacy-standing-items-surface.md). Its [handoff](../handoffs/2026-05-31-spec-0257.1-delete-dead-legacy-standing-items-surface.md) "Deferred during implementation" records that, while removing the legacy phase2/phase4 runners, the implementer confirmed `orchestrator/phase3.py:run_phase3` is the exact same dead-legacy-runner pattern but left it untouched because it sat outside 0257.1's named scope (the single-drafter synthesis phase 3 has no standing-items surface). This spec finishes that parallel cleanup for phase 3.

---

## 1. Current state

`orchestrator/phase3.py` carries a legacy `run_phase3` runner that has been **unreachable from the live entry point since the spec-0118 v2 rewrite**, exactly mirroring the legacy `run_phase2` / `run_phase4` runners deleted by spec 0257.1. The live phase-3 driver is `dr_run.run_dr_phase3`, invoked from `run.py` via the alias `run_dr_phase3 as run_phase3`.

Dead surface, with citations:

- **Legacy `run_phase3`** at [`src/dual_research/orchestrator/phase3.py:29`](../src/dual_research/orchestrator/phase3.py) — an `async def run_phase3(...)` that returns `Phase3Outcome`. It carries the identical dead-path comment to the runners 0257.1 removed: "Spec 0118: legacy run_phase3 path no longer emits Consumption-tab piece breakdowns; dr_run.run_dr_phase3 is the active code path" ([`src/dual_research/orchestrator/phase3.py:66`](../src/dual_research/orchestrator/phase3.py)).
- **No production caller.** The only `run_phase3` reference in `run.py` is the *alias* `run_dr_phase3 as run_phase3` ([`src/dual_research/orchestrator/run.py:35`](../src/dual_research/orchestrator/run.py)); the live call at [`src/dual_research/orchestrator/run.py:482`](../src/dual_research/orchestrator/run.py) therefore resolves to `dr_run.run_dr_phase3`, **not** the legacy `phase3.run_phase3`. A tree-wide `grep -rn run_phase3 src/` returns only the legacy def, its own dead comment, and that alias/call pair — no live import of `phase3.run_phase3`.
- **Only remaining callers are test-only** — [`tests/orchestrator/test_phase3_4_final.py:104`](../tests/orchestrator/test_phase3_4_final.py) and [`:125`](../tests/orchestrator/test_phase3_4_final.py), with the import at [`tests/orchestrator/test_phase3_4_final.py:15`](../tests/orchestrator/test_phase3_4_final.py).

**Pain:** A second, diverging phase-3 runner is the same wrong-layer / dead-surface hazard 0257.1 closed for phase2/phase4 — a citable `file:line` that passes a string-check reconcile while pointing at code dead since spec-0118. Leaving it in keeps the 0231→0238 / 0257 dead-surface trap armed for the next phase-3 spec. Deleting it leaves `dr_run.run_dr_phase3` as the only phase-3 runner in the tree.

## 2. Target state

The dead `run_phase3` runner is gone; the only phase-3 runner in the tree is the live `dr_run.run_dr_phase3`.

- `run_phase3` (and its now-unused module-local helpers, if any become orphaned by its removal) deleted from [`src/dual_research/orchestrator/phase3.py`](../src/dual_research/orchestrator/phase3.py), including the dead-path comment at [`src/dual_research/orchestrator/phase3.py:66`](../src/dual_research/orchestrator/phase3.py).
- **Preserve `Phase3Outcome` and `current_draft_path`** — both live in `orchestrator/phase3.py` but are STILL imported by live code:
  - `Phase3Outcome` ([`src/dual_research/orchestrator/phase3.py:23`](../src/dual_research/orchestrator/phase3.py)) — imported by [`src/dual_research/orchestrator/run.py:41`](../src/dual_research/orchestrator/run.py) and [`src/dual_research/orchestrator/dr_run.py:80`](../src/dual_research/orchestrator/dr_run.py) (the live `run_dr_phase3` constructs it at [`src/dual_research/orchestrator/dr_run.py:1367`](../src/dual_research/orchestrator/dr_run.py)).
  - `current_draft_path` ([`src/dual_research/orchestrator/phase3.py:123`](../src/dual_research/orchestrator/phase3.py)) — imported by [`src/dual_research/orchestrator/dr_run.py:80`](../src/dual_research/orchestrator/dr_run.py) and [`src/dual_research/orchestrator/finalize.py:9`](../src/dual_research/orchestrator/finalize.py), used across `dr_run.py` (e.g. `:839`, `:1472`) and `finalize.py:150`.
  - Delete only the `run_phase3` function body and any imports/symbols that become unused *solely* because of its removal; verify each surviving symbol still resolves.

## 3. Stepwise migration

Each step independently shippable / revertable.

- **Step 1:** Delete the `run_phase3` async function from `orchestrator/phase3.py` (the def at `:29` through the end of its body) plus the dead-path comment at `:66`. Remove any module-level imports in `phase3.py` left unused *only* by that deletion (e.g. `drafting_prompt`, `drafting_input_bundle`, `EventBus`, `list_turns` — verify each is not also referenced by `current_draft_path` or `Phase3Outcome` before dropping). Keep `Phase3Outcome` and `current_draft_path` intact. Verifies: `grep -rn "def run_phase3\|async def run_phase3" src/` returns nothing, and `grep -rn run_phase3 src/` returns only the `run.py` alias/call pair (which target `run_dr_phase3`).
- **Step 2:** Confirm the live import surface still resolves: `uv run python -c "import dual_research.orchestrator.run, dual_research.orchestrator.dr_run, dual_research.orchestrator.finalize, dual_research.orchestrator.phase3"` imports clean, and `Phase3Outcome` / `current_draft_path` are still importable from `dual_research.orchestrator.phase3`.
- **Step 3:** Surgically update [`tests/orchestrator/test_phase3_4_final.py`](../tests/orchestrator/test_phase3_4_final.py): drop the `run_phase3` import from the line-15 import (keep `current_draft_path`), and delete the two `run_phase3`-exercising test functions `test_phase3_writes_draft_and_advances_state` ([`:94`](../tests/orchestrator/test_phase3_4_final.py)) and `test_phase3_raises_without_drafter` ([`:121`](../tests/orchestrator/test_phase3_4_final.py)). Keep every other test in the file — `test_current_draft_path_routes_by_round`, the `confidence_tag` / `render_metadata_header` / `emit_final` tests, and the `Phase2Outcome` / `Phase4Outcome` contract helpers — all of which exercise live finalize/outcome surfaces, not the dead runner. Verifies: `uv run pytest tests/ -q` green with no collection errors and no orphaned imports.

## 4. Behavior preservation

This is a dead-code deletion — no live behavior changes. The deleted tests exercise only the dead `run_phase3` runner; removing them removes coverage of unreachable code, not of any live path. Live phase-3 behaviour is covered against `dr_run.run_dr_phase3` elsewhere.

- [ ] `tests/orchestrator/test_phase3_4_final.py::test_current_draft_path_routes_by_round` still passes (covers the preserved `current_draft_path`).
- [ ] The `confidence_tag` / `render_metadata_header` / `emit_final` tests in `test_phase3_4_final.py` still pass (cover live finalize behaviour and the preserved `Phase3Outcome` / `Phase4Outcome` contracts).
- [ ] `uv run python -c "from dual_research.orchestrator.phase3 import Phase3Outcome, current_draft_path"` succeeds after deletion (preserved live symbols still resolve).
- [ ] `uv run pytest tests/ -q` green with no collection errors.

## 5. Out of scope

**Explicit: this spec adds no new feature.** It does not touch `dr_run.run_dr_phase3`, the live phase-3 prompt builders, the `Phase3Outcome` / `current_draft_path` symbols (preserve-only), or any verifier invariant. It does not relocate `Phase3Outcome` / `current_draft_path` to a non-legacy module — an optional cleanup, not a requirement here. It does not re-touch the phase2/phase4 surfaces already cleaned by spec 0257.1.

## 6. Risks

- **A missed live call site for `run_phase3`.** Mitigation: the deletion is guarded by `grep -rn run_phase3 src/` returning only the `run.py` alias/call pair (both targeting `run_dr_phase3`) and by a clean import of the four orchestrator modules (`run`, `dr_run`, `finalize`, `phase3`).
- **Accidentally deleting `Phase3Outcome` / `current_draft_path`.** Mitigation: §2 names both as preserve-only with every live import site enumerated at `file:line`; Step 2 re-imports them explicitly as a gate.
- **Dropping a module-level import in `phase3.py` still needed by `current_draft_path` / `Phase3Outcome`.** Mitigation: Step 1 requires verifying each candidate import is unused by the surviving symbols before removal; the clean-import gate in Step 2 catches any over-deletion.
- **Revert plan:** pure deletion with no migration and no state — if anything breaks, revert the commit; nothing to unwind.

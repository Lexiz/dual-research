---
kind: dev
spec: "0258"
slug: reconciler-citation-liveness-reporting-check
title: Flag spec citations unreachable from the live entry points at reconcile time
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.67.0
status: queued
depends_on: []
complexity: M
created: 2026-05-30
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
disposition_reason: "The CLAUDE.md prose rule 'cite the live surface, not the dead one' is only an interim guard until this executable reporting check lands; ship to retire the manual-vigilance gap that retargeted spec 0257 in-flight."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0258 — Flag spec citations unreachable from the live entry points at reconcile time

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** —
> **Bump:** MINOR — adds a new reporting verdict to the `/dev-next` reconcile step (a contract change to reconcile per CLAUDE.md "Contract-changing specs are not bugs"); no existing behaviour removed.
> **Evidence:** spec 0257 `## 0. Post-merge correction`; `handoffs/2026-05-30-spec-0257-*.md`; the dead-vs-live diagnosis recorded in the v1.65.0 release notes.

---

## 1. Context

Spec 0257's §2 citations ALL pointed at dead code. `ledger/prompt.py:build_standing_items_section`, a proposed new `LedgerState.ratifiable_entries`, and the non-`_v2` prompt builders were reachable only from the LEGACY phase runners (`src/dual_research/orchestrator/phase1.py:30` `run_phase1` and its `phase0`/`phase2`/`phase3`/`phase4` siblings) — NOT from the live entry points `run_dr_phase2` (`src/dual_research/orchestrator/dr_run.py:1015`) / `run_dr_phase4` (`src/dual_research/orchestrator/dr_run.py:1533`), which compose standing items through `_format_standing_items` (`src/dual_research/orchestrator/dr_run.py:602`, called at `src/dual_research/orchestrator/dr_run.py:300`). The legacy surface has been dead since the spec-0118 v2 rewrite; spec 0257.1 has since deleted `ledger/prompt.py` outright and reduced `phase2.py`/`phase4.py` to their `*Outcome` dataclasses, while the `run_phase1` / `run_phase0` / `run_phase3` legacy runners remain on disk and dead. The 0257 fix had to be retargeted onto the live surface in-flight during `/dev-next`.

The reconciler reported the spec "clean" because `reconcile_spec` (`scripts/spec_lifecycle/reconcile.py:89`) only classifies whether a cited `file:line` still EXISTS within range — `clean` / `mechanical` / `semantic` / `out_of_tree` — via `_extract_citations` (`scripts/spec_lifecycle/reconcile.py:141`) and the per-citation existence check in the `reconcile_spec` loop (`scripts/spec_lifecycle/reconcile.py:101`). It has no notion of whether the cited symbol sits on a live call path. The interim guard today is the CLAUDE.md prose rule "cite the live surface, not the dead one," enforced only by operator vigilance — which is exactly what missed on 0257. This spec makes that rule executable as a **reporting** check at the same reconcile-time decision point where the dead→live retarget gets made.

## 2. Proposed change

Add a coarse, name-based caller-chain heuristic to `scripts/spec_lifecycle/reconcile.py` that surfaces a **WARN-level reporting flag** for any Python-function citation in a spec's `## 2` whose symbol is not reachable from the live entry points. This is reporting, NOT a gate — it does not contribute to `has_blocking_drift` (`scripts/spec_lifecycle/reconcile.py:85`) and does not halt `/dev-next`.

**Reachable-symbol set (cheap heuristic, not a sound call graph).**

- Seed from a small allowlist of live entry points, default `{"run_dr_phase2", "run_dr_phase4"}`, anchored to `src/dual_research/orchestrator/dr_run.py`. The allowlist is a module-level constant `LIVE_ENTRY_POINTS: tuple[str, ...]` so future live roots can be added in one place.
- Build a name → `def`-locations index over `src/dual_research/` by walking the package with `ast` (parse each module; record every `FunctionDef` / `AsyncFunctionDef` name). For each function body, record the set of bare `Name` / `Attribute.attr` identifiers it references (an `ast.NodeVisitor` collecting referenced names — coarse, ignores scoping and dynamic dispatch by design).
- BFS from the seed names: a symbol is *reachable* if it is referenced (by bare name) transitively from any live entry point. The result is a `reachable_symbols: set[str]` of function names.

**New reporting bucket.**

- Add `unreachable: list[Citation]` to `ReconcileReport` (`scripts/spec_lifecycle/reconcile.py:71`) and a `classification` value `"unreachable"` (alongside `clean | mechanical | semantic | out_of_tree`, `scripts/spec_lifecycle/reconcile.py:67`).
- A new helper `_check_citation_liveness(report, *, repo_root, section_2_symbols)` runs AFTER the existing existence classification. For each citation that classified `clean` AND whose `file:line` resolves to a Python `def`/`async def` whose name is NOT in `reachable_symbols`, append a *copy* of the citation to `report.unreachable` with `note="citation not reachable from live entry points — possible dead-surface citation"`. The citation stays in `clean` too (it does exist on disk) — `unreachable` is an orthogonal advisory overlay, not a reclassification, so existing `clean`-count consumers are untouched.
- Scope the liveness check to citations that appear inside the spec's `## 2 Proposed change` section only (parse the section span from the body), matching the spec mechanics that §2 is where implementation citations live. Citations elsewhere (Context, Evidence) are not flagged.

**Resolution of a `file:line` to a symbol name.** Open the cited file, find the nearest enclosing `def`/`async def` at or above `cit.line` via `ast` (walk top-level and nested function defs, pick the innermost whose lineno ≤ cit.line and whose end_lineno ≥ cit.line). If the line is not inside any function (module-level, class body without a method, a `.css`/`.md` citation), skip — no flag. Non-`.py` citations are never flagged.

**Reporting surface.** Extend `format_report` (`scripts/spec_lifecycle/reconcile.py:170`) with an `unreachable (informational): N` block listing each flagged `raw` + note, rendered like the existing `out_of_tree` informational block. The CLI `main` (`scripts/spec_lifecycle/reconcile.py:186`) return code is UNCHANGED — `unreachable` never affects exit status.

**Worked dead-vs-live example the test pins.** A §2 citation to `src/dual_research/orchestrator/phase1.py:30` (`run_phase1`, the legacy Phase-1 runner dead since the spec-0118 v2 rewrite and replaced by `run_dr_phase1`) MUST land in `report.unreachable` — `run_phase1`'s name is not reachable by bare-name BFS from `run_dr_phase2` / `run_dr_phase4`, yet the file still exists on disk so the citation classifies `clean` and reaches the liveness overlay. A §2 citation to `src/dual_research/orchestrator/dr_run.py:1015` (`run_dr_phase2`) or `src/dual_research/orchestrator/dr_run.py:602` (`_format_standing_items`) MUST NOT be flagged — the first is an entry point itself, the second is reached from it at `src/dual_research/orchestrator/dr_run.py:300`.

> **Fixture-retarget note (reconcile against `main`, 2026-05-31).** This spec was authored citing `build_standing_items_section` in `ledger/prompt.py` (line 47) as the dead-surface worked example. Spec 0257.1 then **deleted** that file outright, so it no longer demonstrates the liveness check (a deleted path classifies `semantic`, never reaching the `clean`-only liveness overlay). The worked example + §6 test fixture were retargeted at `/dev-next` reconcile time onto `run_phase1` — a still-on-disk legacy runner empirically confirmed unreachable under the very bare-name BFS this spec ships (560 of 764 package functions are unreachable from the two live entry points; `run_phase1` is among them). The dead→live mapping is recorded in the implementing PR.

The CLAUDE.md prose rule "cite the live surface, not the dead one" remains the interim guard until this lands, and stays in place as the human-readable statement of the contract this check makes executable.

## 3. User stories & acceptance criteria

Non-UI spec — touches only `scripts/spec_lifecycle/`. User stories / BDD scenarios optional; documented as before/after below.

**Before:** `/dev-next` reconcile reports a spec citing a dead legacy runner such as `run_phase1` as fully clean; the operator has no signal the surface is dead until implementation fails on the wrong function.

**After:** reconcile additionally prints `unreachable (informational): 1 — src/dual_research/orchestrator/phase1.py:30 — citation not reachable from live entry points — possible dead-surface citation`, at the same step where the retarget decision is made; exit status unchanged, `/dev-next` proceeds.

## 4. Data / Schema deltas

None. No migrations, no persisted state, no event types. `ReconcileReport` is an in-process dataclass.

## 5. Out of scope

Stated explicitly — these are deliberately NOT built:

- **A precise / sound call graph.** No import resolution, no scope analysis, no type inference. The heuristic is bare-name BFS and accepts false positives as WARN noise by design.
- **Making the check a hard gate.** `unreachable` never contributes to `has_blocking_drift` and never changes the `reconcile.py` exit code. It does not halt `/dev-next`. (Promoting it to a gate would be a separate spec, only after false-positive rate is measured on real specs.)
- **Resolving dynamic-dispatch / string-keyed / reflective call sites.** Symbols reached only via `getattr`, registry dicts, or string dispatch will read as unreachable and may be flagged — accepted noise.
- **Multi-language reachability.** Only `.py` citations under `src/dual_research/` are analysed. JS/CSS/MD citations are never flagged.
- **Removing the CLAUDE.md prose rule.** It stays as the human-readable contract statement.
- **Deleting the remaining dead legacy surfaces** (the `run_phase0` / `run_phase1` / `run_phase3` runners in `phase0.py` / `phase1.py` / `phase3.py`; the non-`_v2` prompt builders). Spec 0257.1 already deleted `ledger/prompt.py` and the `run_phase2` runner; finishing the cleanup is flagged for deletion elsewhere, not this spec.

## 6. Test plan

New stdlib-only unit test `tests/test_spec_0258_reconcile_liveness.py`:

- [ ] Feeds `reconcile_spec` (or a focused `_check_citation_liveness` entry) a synthetic spec whose `## 2` cites `src/dual_research/orchestrator/phase1.py:30` (`run_phase1`, a known-dead legacy runner that still exists on disk) and asserts the citation appears in `report.unreachable` with the dead-surface note.
- [ ] Feeds the same path a `## 2` citation to `src/dual_research/orchestrator/dr_run.py:1015` (`run_dr_phase2`, a live entry point) and asserts it is NOT in `report.unreachable`.
- [ ] Feeds a `## 2` citation to `src/dual_research/orchestrator/dr_run.py:602` (`_format_standing_items`, reached from a live entry point) and asserts it is NOT in `report.unreachable`.
- [ ] Asserts that adding the `unreachable` overlay leaves `report.has_blocking_drift` `False` and the `reconcile.py` CLI exit code unchanged for the dead-citation case (reporting, not gating).
- [ ] Asserts a non-`.py` citation (e.g. a `.css:NN`) is never added to `unreachable`.

All checks run against the real `src/dual_research/` tree via the repo root, so the reachability index is exercised against live source — not a fixture stub.

## 7. Risks

- **False positives from dynamic dispatch.** A live-but-string-dispatched symbol reads as unreachable and gets flagged. Mitigation: it is WARN-only and informational; the operator reads it at the same step they already make the retarget call. Accepted by design.
- **AST index cost on every reconcile.** Walking all of `src/dual_research/` per reconcile adds a parse pass. Mitigation: the package is small and parsing is one-shot per `reconcile_spec` call; if it ever becomes slow we cache the index — not needed now.
- **Heuristic lets a real dead citation through** (false negative, e.g. the dead symbol shares a name with a live one). Mitigation: this is strictly additive over today's zero-signal baseline; the CLAUDE.md prose rule remains the backstop. If the name-collision false-negative rate proves material, a follow-up tightens resolution to file-qualified names.
- **If the heuristic proves too noisy in practice**, we revert the `format_report` surfacing (one block) and keep the bucket dark — low blast radius, no gating coupling to unwind.

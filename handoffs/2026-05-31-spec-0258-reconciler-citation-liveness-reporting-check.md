---
spec: "0258"
date: 2026-05-31
version: "1.67.0"
pr: "https://github.com/Lexiz/dual-research/pull/300"
kind: post-deploy
---

# Spec 0258 — Flag spec citations unreachable from the live entry points

Shipped in **v1.67.0** (PR [#300](https://github.com/Lexiz/dual-research/pull/300),
deploy run [26706253793](https://github.com/Lexiz/dual-research/actions/runs/26706253793)
green; homepage smoke 200). Makes the CLAUDE.md "cite the live surface, not
the dead one" rule **executable** as a reporting check at `/dev-next`
reconcile time.

## What landed

A WARN-level citation-liveness overlay in
[`scripts/spec_lifecycle/reconcile.py`](../scripts/spec_lifecycle/reconcile.py).

- **Reachability index** (`_build_reachable_symbols`): coarse bare-name BFS
  over `src/dual_research/`, seeded from `LIVE_ENTRY_POINTS = ("run_dr_phase2",
  "run_dr_phase4")`. Each `def`/`async def` is indexed against the bare
  `Name` / `Attribute.attr` identifiers its body references (`_RefCollector`);
  a symbol is reachable if referenced transitively from an entry point.
- **`unreachable` bucket** on `ReconcileReport`: for each citation already
  classified `clean` whose `(path, line)` falls inside the spec's `## 2`
  section (`_extract_section_2`), resolves to a Python function
  (`_resolve_symbol_at_line` — innermost enclosing `def`), and is **not**
  reachable, a *copy* is appended with the dead-surface note. The original
  stays in `clean` — orthogonal overlay, not a reclassification
  (`_check_citation_liveness`).
- **Reporting, not gating:** never contributes to `has_drift` /
  `has_blocking_drift`, never changes the CLI exit code. `format_report` adds
  an `unreachable (informational): N` block.
- **Scoped to `.py` under `src/dual_research/` only** (spec §5). Citations to
  dev tooling (`scripts/…`), tests, or non-`.py` files are never flagged —
  the reachability index covers only that package, so anything outside it has
  no reachability data.

## Self-demonstration

`reconcile specs/0258-*.md` now prints
`unreachable (informational): 1 — src/dual_research/orchestrator/phase1.py:30 …`
and exits 0 — the check flags its own retargeted worked example.

## Reconcile-time fixture retarget (dead→live mapping)

The spec was authored citing `ledger/prompt.py:build_standing_items_section`
(line 47) as its dead-surface worked example. **Spec 0257.1 had deleted that
file**, so the reconciler flagged it as semantic drift at `/dev-next` time —
ironically, the dead-citation detector blocked by a dead citation in its own
body. Resolved inline (commit `spec(0258): reconcile against main`):

- Worked example (§2) + test fixture (§6) retargeted onto **`run_phase1`**
  (`src/dual_research/orchestrator/phase1.py:30`) — a still-on-disk legacy
  Phase-1 runner, dead since the spec-0118 v2 rewrite (replaced by
  `run_dr_phase1`), empirically confirmed unreachable under the shipped BFS
  (560 of 764 package functions are unreachable from the two entry points).
- The stale §2 reasoning ("reachable only from `phase2.py`/`phase4.py`") was
  corrected — 0257.1 also reduced those runners to their `*Outcome`
  dataclasses.
- 10 bare-filename citations (`reconcile.py:NN`, `dr_run.py:NN`) disambiguated
  to full paths.

The non-`_v2` prompt builders (`negotiation_turn_prompt` etc.) were rejected
as fixture candidates because the coarse BFS reads them as **reachable** (a
reachable function references them by bare name) — a deliberate false-negative
the spec's §7 risks already document. `run_phase1` was chosen precisely
because it is empirically unreachable under the very heuristic shipped.

## Tests

`tests/test_spec_0258_reconcile_liveness.py` — 7 stdlib + pytest cases run
against the **real** `src/dual_research/` tree per spec §6:

- dead surface (`run_phase1`) flagged with the dead-surface note;
- live entry point (`run_dr_phase2`) and a reached symbol
  (`_format_standing_items`) NOT flagged;
- overlay reporting-not-gating (`has_blocking_drift` False, citation stays in
  `clean`, CLI exit 0);
- non-`.py` (`.css`) citation never flagged;
- citation outside `## 2` not flagged;
- `format_report` renders the block.

Full suite: **2451 passed** (2444 + 7 new).

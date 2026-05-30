---
spec: "0256"
date: 2026-05-30
version: "1.65.0"
pr: "https://github.com/Lexiz/dual-research/pull/296"
kind: post-deploy
---

# Spec 0256 — drafter-delta apply guard, resync, strict anchor contract

Shipped in **v1.65.0** (PR #296, deploy run
[26684174466](https://github.com/Lexiz/dual-research/actions/runs/26684174466)
green; homepage smoke 200).

## What landed

Phase 4's revision loop wrapped only the **parse** step in a no-op
fallback. When the parse succeeded but an `EDIT_SECTION` anchor failed at
**apply** time, `apply_revised_draft_deltas` raised
`edit_section_anchor_not_found` *outside* the fallback, propagated to the
run-level tombstone, and the run died at `EXIT_RUNTIME` with no `final.md`.
Captured live run `20260529-164844-backend-language-choice` died exactly
this way. Four changes:

- **§2.1 APPLY-GUARD** — `_apply_drafter_revised_draft`
  ([dr_run.py](../src/dual_research/orchestrator/dr_run.py)) now wraps the
  `apply_revised_draft_deltas` call in the same `ProtocolParseError` →
  no-op fallback as the parse step. Both paths share one
  fallback-construction site and set `fallback_fired`/`fallback_errors`
  identically, so the `phase4_drafter_repair_failed` dashboard signal is
  uniform regardless of which step failed. The function now returns a
  `RevisedDraftApplyResult(written, noop, errors)` NamedTuple instead of a
  bare bool (the spec-0231 tests were updated to the new contract).
- **§2.2 DRAFTER RESYNC** — `run_dr_phase4` threads a transient
  `last_revision_noop` flag (set on any fallback, cleared on clean apply)
  into the round-N prompt builder. When set, the DRAFTER's next-round
  prompt carries a `_drafter_resync_banner(...)` ("YOUR PREVIOUS REVISION
  DID NOT APPLY") so it re-anchors against the real on-disk draft. The
  banner is drafter-only and never shown to the reviewer.
- **§2.3 STRICT ANCHOR NORMALIZATION** —
  [parse.py](../src/dual_research/protocol/parse.py) gains
  `_normalize_with_map` / `_normalize_anchor_for_match` /
  `_edit_section_apply_one`. EDIT_SECTION matches under a closed,
  deterministic canonicalization (inner-whitespace-run collapse,
  smart→straight quotes, one trailing-`.`/`,`/`:`/`;` tolerance on the
  anchor) while writing back the **original draft bytes** for the
  unmatched span — normalization governs *where* the match is, not *what*
  survives. **Not fuzzy:** a similar-but-different anchor still raises
  `edit_section_anchor_not_found`; `>1` still raises
  `edit_section_anchor_ambiguous`. The drafter anchor-contract prompt now
  requires short, single-line, structurally-unique anchors.
- **§2.4** — the round-N drafter prompt
  ([prompts.py](../src/dual_research/protocol/prompts.py)) no longer leaks
  an `ADDRESS` affordance for the drafter's own items (`raiser_self_address`
  ×7 in the evidence run). The "Addressing items raised against me" /
  "Ratifying my own items" sections now make "ADDRESS only the other
  agent's items; RESOLVE/ACKNOWLEDGE/WITHDRAW for your own" unambiguous.
  Apply-layer drop semantics (deep_research.py) unchanged.

## Tests

- **Load-bearing real-entry-point regression** (spec-0238 discipline) at
  `tests/test_spec_0256_drafter_apply_guard.py`: drives the real
  `_apply_drafter_revised_draft` over the captured `round-02-claude.md`
  (parse-step no-op) → `round-03-claude.md` (apply-step no-op) sequence
  against vendored `draft-v2.md`. Asserts no raise, a final draft always
  produced, one `phase4_drafter_repair_failed` per round, and **no
  wrong-section corruption** of the four "Tier 2 Scoring" sections.
- Apply-guard unit (parseable turn, anchor absent at apply time).
- Resync banner gating; strict normalization both directions (match
  tolerated diffs; reject absent + similar-but-different; ambiguous
  raises) via helper and the public `apply_revised_draft_deltas`;
  drafter-prompt self-address fix + apply-layer drop-semantics pin.
- Fixtures vendored under `tests/fixtures/spec_0256/phase4/`.
- Full suite: **2456 passed**. Spec-0231 tests adapted to the new
  `RevisedDraftApplyResult` return.

## Verification it actually fixes the captured death

Replaying the captured r3 turn through `_apply_drafter_revised_draft`
against the on-disk `draft-v2.md`: pre-fix this raised and killed the run;
post-fix it returns `written=True, noop=True`, writes a byte-equal
`draft-v3.md`, emits `phase4_drafter_repair_failed` citing
`edit_section_anchor_not_found`, and the round loop survives.

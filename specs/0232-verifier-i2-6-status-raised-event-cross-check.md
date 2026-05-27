---
kind: dev
spec: "0232"
slug: verifier-i2-6-status-raised-event-cross-check
title: Verifier I2.6 — STATUS-RAISED-array event cross-check (reporting)
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: []
complexity: S
created: 2026-05-27
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0232 — Verifier I2.6 — STATUS-RAISED-array event cross-check (reporting)

> **Type:** new-feature  |  **Complexity:** S  |  **Depends on:** —
> **Bump:** MINOR — adds a new verifier invariant; verifier invariants ARE the contract per CLAUDE.md "Contract-changing specs are not bugs".
> **Evidence:** Cowork design sign-off `cowork/briefs/2026-05-27-parser-tolerance-proposal-signoff.md`; reconciliation `cowork/briefs/2026-05-27-live-run-findings-reconciliation.md`; failing-run fixture `tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/`.

---

## 1. Context

The 2026-05-27 live run `20260527-054652-backend-language-choice` converged FALSELY in phase 2. Claude's phase-2 round-1 turn declared 6 IDs in `STATUS.RAISED_THIS_TURN` (`D-plan-c-01/02/03` + `Q-plan-c-01/02/03`, visible at [tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/phase2/round-01-claude.md:7](tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/phase2/round-01-claude.md:7)) but the parser dropped its `## New items I'm raising` body section (heading glued to prose). Zero `item_raised` events fired for those 6 IDs. Phase 2 then "converged organically" with only OpenAI's items in the ledger.

The existing verifier did not catch this because [src/dual_research/contract/verifier.py:788](src/dual_research/contract/verifier.py:788) (`_check_i3_3`) only checks STATUS-array ID *format* (canonical regex) and [src/dual_research/contract/verifier.py:949](src/dual_research/contract/verifier.py:949) (`_check_i4_4`) only cross-checks body-section ops, not STATUS-array IDs. Neither rule asks "did the IDs claude said it raised actually register as events?" — which is the executable form of the false-convergence failure mode. Cowork's design sign-off in `cowork/briefs/2026-05-27-parser-tolerance-proposal-signoff.md` (amendments 3.a–3.f) authorizes a new invariant I2.6 to fill that gap.

## 2. Proposed change

Add `_check_i2_6` to [src/dual_research/contract/verifier.py](src/dual_research/contract/verifier.py), landing directly after `_check_i2_5` at [src/dual_research/contract/verifier.py:641](src/dual_research/contract/verifier.py:641) and registered in the aggregator block at [src/dual_research/contract/verifier.py:1206](src/dual_research/contract/verifier.py:1206) (insert after `_check_i2_5(events, turn_files)`).

**Invariant I2.6 — STATUS-RAISED-array event cross-check (Area 2: self-report ⇄ ledger).**

For every turn file in phases 0, 2, 4 (the interaction phases — same scope as `_check_i2_5`):

1. Parse `RAISED_THIS_TURN` from the turn's STATUS footer. Let `declared = len(RAISED_THIS_TURN)`.
2. Count `item_raised` events scoped to the same `(phase, round, agent)` triple — i.e. `ev.event == "item_raised" AND _phase_to_int(ev.phase) == tf.phase AND ev.round == tf.round AND ev.raiser == tf.agent`. Let `registered = <that count>`.
3. If `declared != registered`, emit an Evidence row of the form `phase {p} r{r} {agent}: RAISED_THIS_TURN declared {declared}, item_raised events registered {registered}`.

Return `InvariantResult("I2.6", "reporting", ...)`:
- `not_applicable` — no eligible turn files seen.
- `fail` — one or more mismatches.
- `pass` — all eligible turns match.

**Severity: `reporting` initially.** Per Cowork amendment 3.b, promote to `gating` only after spec 0231 (parser-heading-tolerance) lands and reference-run baselines are regenerated — that promotion is a separate small spec, deliberately out of scope here (see §5). The reporting/gating split mirrors the existing I4.4/I2.4 handled-vs-unhandled pattern in the same file.

**Count comparison, NOT ID-set comparison.** Per Cowork amendment 3.d: OpenAI's STATUS arrays carry slug-shaped IDs (Finding 3 in `cowork/briefs/2026-05-27-live-run-findings-reconciliation.md`) that don't match the canonical body-RAISE IDs. An ID-set comparison would false-positive on every OpenAI turn (slugs in STATUS vs canonical IDs in `item_raised` events). The count-based design decouples I2.6 from the open Finding 3 work — claude's 6-vs-0 mismatch surfaces; OpenAI's 6-vs-6 passes regardless of ID-shape mismatch. Slug-ID normalisation lands separately (see §5).

**Coverage scope: `RAISED_THIS_TURN` only**, not all 5 STATUS arrays. Per Cowork amendment 3.c: `ADDRESSED_THIS_TURN`, `RESOLVED_THIS_TURN`, `WITHDRAWN_THIS_TURN`, `ACKNOWLEDGED_THIS_TURN` are downstream of `RAISED_THIS_TURN` — once raise-registration is correct, the items those arrays reference exist in the ledger and `_check_i4_4` + `_check_i2_5` cover the resulting transition coherence. Adding the other four arrays now is redundant + speculative; revisit only if a real gap surfaces in a future run.

## 3. User stories & acceptance criteria

Not a UI spec — §3 is non-applicable per the new-feature template. Acceptance is encoded as falsifiable items in §6.

## 4. Data / Schema deltas

None. The verifier consumes existing `transcript.jsonl` events and existing turn-file STATUS footers; no new event types, no new state-file fields, no migrations.

## 5. Out of scope

- **Extending the cross-check to `ADDRESSED_THIS_TURN` / `RESOLVED_THIS_TURN` / `WITHDRAWN_THIS_TURN` / `ACKNOWLEDGED_THIS_TURN`.** Deferred to a follow-up dev spec to be drafted only if a real downstream gap surfaces post-merge — per Cowork amendment 3.c those arrays self-correct once raise-registration is fixed.
- **Slug-ID normalisation (Finding 3).** Deferred to a separate spec (to be drafted once spec 0231 lands and Finding 3 has its own evidence base). The count-based I2.6 design here intentionally avoids coupling.
- **Severity promotion to `gating`.** Deferred to a separate small spec that runs only after spec 0231 ships AND the failing-run fixture's baseline regenerates green. Promotion criterion is documented in §6 below so the follow-up spec has its trigger condition pre-stated.
- **Re-running or amending the failing-run fixture.** This spec consumes [tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/](tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/) as-is and adds an I2.6 entry to its expected baseline; it does NOT modify the captured transcript or per-phase turn files.

## 6. Test plan

Tests live in [tests/test_verifier.py](tests/test_verifier.py) (extend; do not branch a new file).

- [ ] **Positive synthetic** — build a transcript where `count(RAISED_THIS_TURN) == count(item_raised)` per `(phase, round, agent)` for at least one phase-2 turn → `_check_i2_6` returns `InvariantResult("I2.6", "reporting", "pass")`.
- [ ] **Negative synthetic** — build a transcript with `count(RAISED_THIS_TURN) == 6` and `count(item_raised) == 0` for `(phase=2, round=1, agent="claude")` → `_check_i2_6` returns `"fail"` with an Evidence row naming `(phase 2 r1 claude, declared 6, registered 0)`.
- [ ] **Backwards-compat on clean reference run** — running the full verifier on `tests/fixtures/anchor-runs/20260521-010637-dvs-backend-language-choice/` reports I2.6 as `pass`. No other invariant's status changes (`expected.json` for the clean fixture grows by exactly one I2.6 entry).
- [ ] **Snapshot on the failing-run fixture** — running the full verifier on `tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/` reports I2.6 as `fail` with an Evidence row containing the exact tuple `(phase 2 r1 claude, declared 6, registered 0)`. `expected.json` for the failing fixture updates accordingly.
- [ ] **`uv run pytest tests/test_verifier.py -q` passes** with all four cases above asserted.
- [ ] **CHANGELOG entry under a new `## [X.Y+1.0] — 2026-05-27` heading** (MINOR bump) with `### Added` bullet linking back to this spec; `pyproject.toml` and `src/dual_research/__init__.py` bumped to the same X.Y+1.0.
- [ ] **Severity-promotion trigger pre-documented** — after this spec merges, the promotion-to-gating spec is unblocked the moment BOTH (a) spec 0231 has shipped AND (b) re-running the verifier against the regenerated `20260527-054652` baseline reports I2.6 as `pass`. Both conditions are objectively checkable; the promotion spec does not require fresh design work.

## 7. Risks

- **False-positive on OpenAI-shaped IDs.** Mitigated by Cowork amendment 3.d — count comparison, not ID-set comparison. Verified in the negative test plan: an OpenAI turn declaring 6 slug-IDs and registering 6 `item_raised` events still passes I2.6.
- **Reporting noise on historical fixtures.** Any pre-existing fixture with a raise-drop will surface as an I2.6 failure on first re-run. Mitigated by the reporting (non-gating) severity — failures are visible but do not block. Promotion to gating is gated on §5's deferred spec, which only fires after spec 0231 makes such failures real bugs rather than expected drops.
- **Implementation drift from `_check_i2_5`.** I2.6 shares `_check_i2_5`'s phase/round/agent scoping logic. Mitigated by landing I2.6 immediately adjacent to I2.5 in the source file and re-using the same `_TurnFile` iteration shape — the diff stays visually paired and copy-pasta divergence is obvious in review.
- **Revert path.** If I2.6 misbehaves post-merge, the entire change is a single new function plus one line in the aggregator and one CHANGELOG entry — reverting is mechanical and isolated. We will revert (not patch) if the noise rate on the reporting channel exceeds usefulness.

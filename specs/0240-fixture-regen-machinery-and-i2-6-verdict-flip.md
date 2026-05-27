---
kind: dev
spec: "0240"
slug: fixture-regen-machinery-and-i2-6-verdict-flip
title: "Fixture regen machinery + I2.6 verdict flip on the 142625 fixture (unblocks I2.6 → gating promotion)"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: ["0232", "0238"]
complexity: S
created: 2026-05-27
queued_at: "2026-05-27T19:05:53Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: ship
disposition_reason: "Unblocks two named downstream triggers — spec 0232 §6's I2.6 reporting → gating promotion (gated on a 0231/0238-aware regen of the failing fixtures reporting I2.6 = pass) and the spec 0238 §6 verdict-flip line item (142625 fixture moves I2.6 from fail to pass once the frozen transcript is regenerated through the post-fix parser)"
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0240 — Fixture regen machinery + I2.6 verdict flip on the 142625 fixture

> **Type:** new-feature  |  **Complexity:** S  |  **Depends on:** 0232 (I2.6 invariant exists and is registered), 0238 (parser primitive consolidation so a re-run actually populates `item_raised` events for the previously-dropped 5 IDs).
> **Bump:** MINOR — introduces a new executable fixture-regeneration entry point (the test-suite gains a callable for re-running a frozen transcript through the current parser + `apply_turn`) and flips one captured snapshot verdict (`test_snapshot_142625_i2_6_slug_drop_fail` → assert `pass`). Both are first-class to the verifier contract under the CLAUDE.md "verifier invariants ARE the contract" rule.
> **Evidence:** [`handoffs/2026-05-27-spec-0238-parser-section-heading-primitive-consolidation.md`](handoffs/2026-05-27-spec-0238-parser-section-heading-primitive-consolidation.md) §"Deferred during implementation" (the 142625 fixture's I2.6 entry does not flip on parser fix alone — frozen `transcript.jsonl` has zero `item_raised` events and the verifier reads the transcript, not the live parser); [`handoffs/2026-05-27-spec-0232-verifier-i2-6-status-raised-event-cross-check.md`](handoffs/2026-05-27-spec-0232-verifier-i2-6-status-raised-event-cross-check.md) §"Notes for follow-ups → Severity promotion spec" (promotion gated on regenerated 054652 baseline reporting I2.6 = pass).

---

## 1. Context

Spec 0238 shipped the parser fix that would have prevented the 142625 phase-2 r1 claude turn from dropping its 5 raised IDs (`D-go-vs-csharp-21`, `D-java-rank`, `D-kotlin-mcp`, `Q-csharp-implicit-penalty`, `Q-rust-azure-sdk-ga`). The spec body's §6 test plan carried the line item "the 142625 fixture's I2.6 entry must move from `fail (5 declared, 0 registered)` to `pass`." That expectation did not hold post-merge.

The reason, surfaced in the 0238 handoff's "Deferred during implementation" section: the verifier at [`src/dual_research/contract/verifier.py:713`](src/dual_research/contract/verifier.py:713) reads `transcript.jsonl` (frozen at the dead state — zero `item_raised` events were ever registered for that turn) plus the turn files; the parser fix does not retroactively populate the frozen transcript. The captured snapshot test at [`tests/test_verifier.py:946`](tests/test_verifier.py:946) (`test_snapshot_142625_i2_6_slug_drop_fail`) continues to pass green post-fix — the snapshot and the frozen reality remain consistent, no regression — but the verdict-flip line item from 0238 §6 was conflating the parser fix's effect on *new* runs with its effect on *frozen* fixtures.

This is the same downstream work the 0232 handoff §"Notes for follow-ups → Severity promotion spec" already named: I2.6's promotion from `reporting` → `gating` (per 0232 §6) is gated on (a) 0231 having shipped (done), and (b) re-running the verifier against a regenerated 20260527-054652 baseline reporting I2.6 = `pass`. The 0238 deferral and the 0232 follow-up are different framings of the same regen-fixture machinery. This spec ships that machinery once, applies it to the two failing fixtures (142625 and 054652), and updates the corresponding snapshot test assertions in lock-step so both downstream triggers unblock atomically.

## 2. Proposed change

Three small layers ship together in one PR.

### 2.1 — Promote `regenerate_baseline()` from a manual helper to a parametrised regen entry point

The existing helper at [`tests/test_verifier.py:1004`](tests/test_verifier.py:1004) (`regenerate_baseline()`) currently rewrites every fixture's `expected.json` from the live verifier output. It is not a test, just a callable. It rewrites the *baseline* (the contract assertion of "what the verifier should report") but it does NOT regenerate the underlying `transcript.jsonl` from the turn files — which is exactly the gap the 0238 deferral identifies.

Promote it to a small module under `tests/_fixture_regen.py` (pure stdlib + project imports, no `pytest` dependency at import time), exposing two callables:

- `regenerate_transcript(run_dir: Path) -> None` — for each turn file in `run_dir/{phase0,phase1,phase2,phase3,phase4,phase5}/` (or whatever subset exists), call `parse_turn_v2(text)` followed by `apply_turn(...)` against an in-memory state seeded from the existing `transcript.jsonl`'s pre-turn events (so artifact and convergence events that pre-date the dead-state cutover are preserved). Rewrite `run_dir/transcript.jsonl` with the resulting event sequence. **Before overwriting, the function preserves the original `transcript.jsonl` as `transcript.captured.jsonl` in the same directory — idempotent: if `transcript.captured.jsonl` already exists, it is NOT overwritten (the captured evidence is immutable, the working transcript is regen-output).** This preservation is load-bearing for any spec whose tests depend on dead-state orchestrator runtime events (e.g. `empty_turn_detected`, retry `turn_started`) that the turn-file replay cannot reconstruct — spec 0239's I2.7 integration test on 142625 is the first such consumer. This is the entry point the 0238 deferral names; it is the natural attachment surface flagged in `tests/test_verifier.py:1004`'s docstring as "manual; not a test."
- `regenerate_baseline(run_dir: Path) -> None` — preserved from the existing helper, unchanged in spirit. After `regenerate_transcript` has run, this recomputes `run_dir/expected.json` from the now-regenerated transcript + turn files.

The existing `regenerate_baseline()` function at [`tests/test_verifier.py:1004`](tests/test_verifier.py:1004) is preserved as a thin one-line wrapper that delegates to `_fixture_regen.regenerate_baseline` over the fixtures directory, so any out-of-tree caller that imports it does not break.

### 2.2 — Run the regen against the two failing fixtures and commit the new artefacts

Apply `regenerate_transcript` then `regenerate_baseline` to:

- `tests/fixtures/anchor-runs/20260527-142625-backend-language-choice/` — the captured failing fixture from 0238. Post-regen, the phase-2 r1 claude turn must produce 5 `item_raised` events; `expected.json`'s I2.6 entry flips from `fail` to `pass`.
- `tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/` — the other failing fixture named in 0232's empirical table. Post-regen, the phase-2 r1 claude turn must produce 6 `item_raised` events; `expected.json`'s I2.6 entry flips from `fail` to `pass`.

The three already-passing fixtures (010637 clean, 135006, 102321) are NOT regenerated by this spec — their I2.6 entries are already `pass` and a regen would only churn the snapshot. They get a no-op test-time assertion (see §2.3) that re-running their regen would not change their `expected.json` content.

### 2.3 — Flip the snapshot tests in lock-step

Update [`tests/test_verifier.py:946`](tests/test_verifier.py:946) (`test_snapshot_142625_i2_6_slug_drop_fail`):

- Rename to `test_snapshot_142625_i2_6_post_regen_pass`.
- Replace the `assert i2_6.verdict == "fail"` block with `assert i2_6.verdict == "pass"` and drop the "declared 5 registered 0" evidence assertions (no fail-evidence on a pass verdict). The `_verdict_diff` baseline-match assertion is preserved — it now asserts the post-regen baseline.

Apply the analogous rename + verdict flip to `test_snapshot_054652_i2_6_drop_class_fail` (the sibling at the surrounding line range — exact line varies after the 0232 merge; locate by name).

Add one new test, `test_fixture_regen_idempotent_on_clean_fixtures`, that calls `_fixture_regen.regenerate_baseline` (with a guard that captures the pre/post `expected.json` bytes) on each of 010637 / 135006 / 102321 and asserts byte-equality pre vs post. This is the executable lock against the regen machinery silently churning clean fixtures.

Add a second idempotency test, `test_fixture_regen_idempotent_on_regenerated_fixtures`, that calls `_fixture_regen.regenerate_transcript` and `_fixture_regen.regenerate_baseline` TWICE in succession against `tmp_path`-copies of the two regenerated fixtures (142625, 054652) and asserts byte-equality of both `transcript.jsonl` and `expected.json` between the first and second regen pass. This protects the gating precondition from silent drift: if a future change to `parse_turn_v2` or `apply_turn` makes regen non-deterministic on the regenerated fixtures, the test fails and we investigate before the I2.6 promotion-to-gating spec consumes the baseline. (Per Cowork sign-off — gap closure for the regen-twice convergence on the very fixtures the gating promotion depends on.)

## 3. User stories & acceptance criteria

Not a UI spec. §3 is non-applicable per the new-feature template. Acceptance is encoded as falsifiable items in §6.

## 4. Data / Schema deltas

None. No new event types, no state-file field changes, no migrations. The change rewrites two existing `transcript.jsonl` files and two existing `expected.json` files using the same event vocabulary already in use; the regen machinery itself is a test-tree module, not a runtime contract.

## 5. Out of scope

- **I2.6 severity promotion from `reporting` to `gating`.** Tracked under spec 0232 §6. Promotion fires only after this spec ships; the actual promotion is a one-line change to the `severity=` argument on the `InvariantResult` returns at [`src/dual_research/contract/verifier.py:760-763`](src/dual_research/contract/verifier.py:713) and is a separate spec (the promotion is the contract change, this spec is the unblocker for it). Named promotion target: a future spec under the 0232 lineage. **The promotion spec MUST key its readiness check off the next LIVE re-run's I2.6 = pass verdict, not solely off this spec's regenerated baseline — regen replays the post-fix parser over the exact case the fix was built for (mildly circular), so the live re-run is the non-circular proof. Per Cowork sign-off.**
- **Other verifier invariants whose snapshot tests might benefit from regen.** This spec narrowly targets I2.6 on the two named fixtures. If a future verifier invariant has the same "captured-at-dead-state" snapshot lock-in pattern, that's a separate spec; the `_fixture_regen` module this spec adds is the surface that future spec would reuse.
- **A general "regenerate all fixtures from scratch" CI workflow.** Tempting but out of scope — would couple the test suite to live-network behaviour. Regen remains a deliberate, in-PR, reviewed operation; the new module just makes it scriptable rather than ad-hoc.
- **Changes to `parse_turn_v2` or `apply_turn`.** This spec consumes the post-0238 parser as-is; no shape changes to the parser API.

## 6. Test plan

Tests live alongside the existing verifier suite in [`tests/test_verifier.py`](tests/test_verifier.py) (snapshot flips) plus a small new file [`tests/test_spec_0240_fixture_regen.py`](tests/test_spec_0240_fixture_regen.py) (regen-machinery unit tests). Pure stdlib + `pytest`.

- [ ] **`test_fixture_regen_142625_yields_5_raised_events`** — Run `regenerate_transcript` against the 142625 fixture in a `tmp_path`-copy of the fixture dir. Assert the resulting `transcript.jsonl` contains exactly 5 `item_raised` events with `phase=2, round=1, raiser="claude"` whose `id` set equals `{"D-go-vs-csharp-21", "D-java-rank", "D-kotlin-mcp", "Q-csharp-implicit-penalty", "Q-rust-azure-sdk-ga"}`.
- [ ] **`test_fixture_regen_054652_yields_6_raised_events`** — Same shape for the 054652 fixture, asserting 6 `item_raised` events for the phase-2 r1 claude turn (count per the 0232 evidence row: `declared 6 registered 0` → post-regen `registered 6`).
- [ ] **`test_fixture_regen_idempotent_on_clean_fixtures`** — Calling `regenerate_baseline` on 010637 / 135006 / 102321 produces byte-identical `expected.json` (and `transcript.jsonl`) pre vs post. The clean fixtures are stable under the regen; only the two failing fixtures legitimately shift.
- [ ] **`test_snapshot_142625_i2_6_post_regen_pass`** (renamed from `test_snapshot_142625_i2_6_slug_drop_fail`) — verdict assertion flips from `fail` to `pass`; `_verdict_diff` baseline match preserved.
- [ ] **`test_snapshot_054652_i2_6_post_regen_pass`** (renamed sibling) — verdict assertion flips from `fail` to `pass`; `_verdict_diff` baseline match preserved.
- [ ] **Backwards-compat on the full verifier suite.** Run `uv run pytest tests/test_verifier.py -q` end-to-end after the change. No pre-existing test changes verdict beyond the four named rename/flip cases.
- [ ] **Full-suite green.** Run `uv run pytest tests/ -q`. No pre-existing test outside the verifier suite changes verdict.
- [ ] **CHANGELOG entry under a new `## [1.54.0] — 2026-05-27` heading** (MINOR bump) with `### Added` bullets for the `_fixture_regen` module and a `### Changed` bullet for the 142625/054652 `expected.json` baselines (I2.6 verdict flips). `pyproject.toml` and `src/dual_research/__init__.py` bumped to `1.54.0`.

## 7. Risks

- **Regen produces a transcript that diverges from the pre-fix transcript in ways beyond the 5/6 dropped IDs.** Mitigation: the regen seeds from pre-turn events (artifact, convergence, etc.) and only re-derives `item_raised` / `item_transitioned` / parser-emitted events from the turn-file replay. The `test_fixture_regen_idempotent_on_clean_fixtures` test is the lock against silent drift on the three fixtures whose transcripts should NOT shift. If a clean fixture's transcript shifts under regen, the test fails and we investigate before the spec lands.
- **Snapshot lock-in inverts.** The renamed `test_snapshot_142625_i2_6_post_regen_pass` now asserts `pass`. If a future parser regression re-drops the 5 IDs without the test catching it, we're back to the 0238-class miss. Mitigation: 0238's worked-example test (`tests/test_spec_0238_parser_section_tolerance.py:178`'s integration on the captured `phase2/round-01-claude.md`) remains the floor — it would catch the regression at the parser entry point regardless of the snapshot's verdict. The renamed snapshot is the *complement* asserting the regen-derived view; both layers must continue to hold.
- **I2.6 promotion-to-gating misfires if the 054652 fixture's regen drifts.** Mitigation: the 054652 regen is committed in this spec's PR; the promotion spec (separate) consumes the resulting `expected.json` as its precondition. The two-step gating (this spec lands the precondition, the promotion spec lands the severity flip) means a drift would surface as a PR-time review point, not a silent promotion.
- **Revert path.** All artefacts are local: a new `tests/_fixture_regen.py` module, two updated `transcript.jsonl` + `expected.json` fixture files, two renamed/flipped snapshot tests, one new idempotency test, the CHANGELOG + version bumps. Revert is a single `git revert` of this spec's PR; no migration to unwind. If post-merge surveillance shows the regen produced a wrong-shape transcript, we revert and re-design the seeding rule before re-shipping.

---
kind: dev
spec: "0244"
slug: promote-verifier-i2-6-i2-7-i2-8-from-reporting-to-gating
title: "Verifier: promote I2.6 (RAISED cross-check), I2.7 (empty-turn retry hardening), I2.8 (turn termination) from reporting → gating, atomic + reversible"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: ["0232", "0239", "0241"]
complexity: S
created: 2026-05-28
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: ship
disposition_reason: "All three reporting-only invariants pass on the first clean reference run (20260528-094743-backend-language-choice — $8.66, 39KB final.md, clean shutdown). The promotion-to-gating preconditions documented in 0232 §6, 0239 §6, and 0241 §6 are all satisfied. Promoting now locks in the contract before a future regression silently degrades these invariants; staying at reporting indefinitely would mean a real bug in the parser/retry/liveness surfaces could land green for one or more cycles before someone notices."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0244 — Promote I2.6 / I2.7 / I2.8 from reporting → gating

> **Type:** new-feature  |  **Complexity:** S  |  **Depends on:** 0232 (I2.6 invariant), 0239 (I2.7 invariant), 0241 (I2.8 invariant) — all deployed.
> **Bump:** MINOR — promotes three verifier invariants to gating severity. Verifier invariants ARE the contract per CLAUDE.md "contract-changing specs are not bugs"; promotion is a contract change.
> **Evidence:** clean reference run [`runs/20260528-094743-backend-language-choice/`](runs/20260528-094743-backend-language-choice/) ($8.66, 39KB `final.md`, `metrics.ended_at` populated, all currently-gating invariants pass except the known Finding 3 I3.3 slug-IDs); verifier output verified directly via `uv run dual-research verify runs/20260528-094743-backend-language-choice/` showing `I2.6 [reporting] pass`, `I2.7 [reporting] pass`, `I2.8 [reporting] pass`. Cowork sign-off `cowork/briefs/2026-05-28-arc-closeout-signoff.md` Q3 ("promote all three together, atomic; keep reversible").

---

## 1. Context

Spec 0232 introduced verifier invariant I2.6 (STATUS-RAISED-array event cross-check) at `reporting` severity. The promotion-to-gating trigger was documented in 0232 §6 checkbox 7: *"after this spec merges, the promotion-to-gating spec is unblocked the moment BOTH (a) spec 0231 has shipped AND (b) re-running the verifier against the regenerated 20260527-054652 baseline reports I2.6 as `pass`."*

Spec 0239 introduced I2.7 (empty-turn retry hardening) with the same reporting-first, promote-on-clean-fixture pattern. Spec 0241 introduced I2.8 (turn termination — every `turn_started` must be followed by `turn_ended` OR a terminal `ProtocolViolation` OR a `tombstone`) with the same pattern.

The clean reference run `20260528-094743-backend-language-choice` satisfies all three preconditions in a single fixture:

```
I2.6  [reporting] pass
I2.7  [reporting] pass
I2.8  [reporting] pass
```

(verified directly via `uv run dual-research verify runs/20260528-094743-backend-language-choice/`).

Per Cowork's arc-closeout sign-off, promote all three together in a single atomic PR. Reversibility is preserved: each promotion is a one-line `severity=` change; if a future fixture surfaces an edge-case fail, demote the affected invariant back to reporting in a separate follow-up commit rather than crisis-patching the invariant's logic.

## 2. Proposed change

Single PR, three trivial edits + baseline regen.

### 2.1 — Change `severity="reporting"` → `severity="gating"` for three invariants

In [`src/dual_research/contract/verifier.py`](src/dual_research/contract/verifier.py), locate the three `InvariantResult` returns:

- I2.6 — introduced by spec 0232, currently returns `InvariantResult("I2.6", "reporting", ...)`. Change to `"gating"`.
- I2.7 — introduced by spec 0239, currently returns `InvariantResult("I2.7", "reporting", ...)`. Change to `"gating"`.
- I2.8 — introduced by spec 0241, currently returns `InvariantResult("I2.8", "reporting", ...)`. Change to `"gating"`.

No other logic changes. The invariants' detection rules, evidence-row emission, and edge-case handling all remain unchanged — only the severity label flips.

### 2.2 — Regenerate `expected.json` baselines

For every fixture under [`tests/fixtures/anchor-runs/`](tests/fixtures/anchor-runs/), regenerate the `expected.json` baseline so the snapshot tests' severity field matches the new gating label. Use the existing `_fixture_regen.regenerate_baseline` machinery from spec 0240 — invoke it on each fixture directory in turn, commit the resulting deltas.

Expected post-regen state per fixture:

| Fixture | I2.6 | I2.7 | I2.8 |
|---|---|---|---|
| `20260521-010637-dvs-backend-language-choice/` (clean baseline) | gating pass | gating pass | gating pass |
| `20260527-054652-backend-language-choice/` (post-0240 regen) | gating pass | gating pass | gating pass |
| `20260527-142625-backend-language-choice/` (post-0240 regen) | gating pass | gating pass | gating pass |
| `20260528-094743-backend-language-choice/` (NEW fixture — see §2.3) | gating pass | gating pass | gating pass |

The 054652 and 142625 fixtures get their I2.6/I2.7/I2.8 verdicts updated via the 0240 regen — both should already be `pass` post-regen (0240's whole point was to flip the captured-at-dead-state verdicts).

### 2.3 — Promote `20260528-094743-backend-language-choice/` to the fixture corpus

Add this run to [`tests/fixtures/anchor-runs/`](tests/fixtures/anchor-runs/) as a permanent reference fixture. It is the first run in project history to complete end-to-end post-0238 and post-H4-mitigation; locking it in as a regression baseline prevents any future change from silently re-introducing a phase-2 parser drop or a phase-4 liveness gap.

Steps:

1. `cp -r runs/20260528-094743-backend-language-choice/ tests/fixtures/anchor-runs/20260528-094743-backend-language-choice/`.
2. Add a `fixture-notes.md` documenting:
   - This is the first end-to-end clean reference run.
   - It is the verification artifact for I2.6 / I2.7 / I2.8 gating promotion (this spec).
   - Pre-fix conditions that would have killed it: 0231 / 0238 parser bugs; 0241 silent-hang surface; H4 Claude Code reap.
3. Run `_fixture_regen.regenerate_baseline` to produce `expected.json` capturing the gating verdicts.
4. Commit.

### 2.4 — CHANGELOG entry

`## [X.Y+1.0] — 2026-05-28` under a new heading (MINOR bump per the verifier-invariant-promotion contract). Bullets:

- `### Changed`: I2.6 / I2.7 / I2.8 promoted from `reporting` to `gating` severity. Verifier failures on these three invariants now block CI rather than reporting silently.
- `### Added`: `tests/fixtures/anchor-runs/20260528-094743-backend-language-choice/` as the first clean end-to-end reference fixture.

`pyproject.toml` and `src/dual_research/__init__.py` bumped to the same X.Y+1.0.

## 3. User stories & acceptance criteria

Not a UI spec. §3 is non-applicable per the new-feature template. Acceptance is encoded as falsifiable items in §6.

## 4. Data / Schema deltas

None. The verifier output structure (`InvariantResult.severity` field) is unchanged; only the value emitted by three specific invariants flips. The `expected.json` schema is unchanged; the verdicts inside it shift for the three named invariants.

## 5. Out of scope

- **Promoting any other reporting invariants to gating.** I1.5 and I2.5 remain at their current severities. Each promotion has its own reference-fixture-pass precondition; not bundling them avoids carrying a different invariant's risk into this PR.
- **Adding new invariants.** This spec promotes existing invariants; new invariants land in their own specs.
- **Changing the reporting/gating dichotomy itself** (e.g. adding a `warning` middle severity). Out of scope; current two-level system is sufficient.
- **Demoting an invariant.** If a post-merge surveillance fixture surfaces an edge-case `fail` on one of these three invariants, demote that one invariant in a follow-up commit — do NOT crisis-patch the invariant's logic. The demote-vs-patch discipline is the Cowork-named reversibility guarantee.
- **Auto-regen of `expected.json` on every CI run.** Regen remains a deliberate, in-PR operation per spec 0240's design.

## 6. Test plan

Tests live alongside the existing verifier suite. Mostly snapshot-test verdict adjustments + one new fixture-snapshot.

- [ ] **All existing snapshot tests pass post-merge.** The fixture `expected.json` baselines regenerate via `_fixture_regen.regenerate_baseline`; the snapshot-comparison tests pass on the regenerated baselines.
- [ ] **`test_i2_6_gating_severity`** — call the verifier on a fixture; assert the I2.6 entry in the result list has `severity == "gating"`.
- [ ] **`test_i2_7_gating_severity`** — same shape for I2.7.
- [ ] **`test_i2_8_gating_severity`** — same shape for I2.8.
- [ ] **`test_094743_fixture_present_and_clean`** — assert `tests/fixtures/anchor-runs/20260528-094743-backend-language-choice/` exists with `transcript.jsonl`, `final.md`, `metrics.json`, `state.json`, `expected.json`, and `fixture-notes.md`. Assert `expected.json` shows I2.6/I2.7/I2.8 all `gating pass`.
- [ ] **`test_054652_fixture_gating_post_regen`** — assert the 054652 fixture's `expected.json` shows I2.6/I2.7/I2.8 all `gating pass` post-spec-0240 regen.
- [ ] **`test_142625_fixture_gating_post_regen`** — same shape for the 142625 fixture.
- [ ] **`test_clean_baseline_fixture_gating`** — `20260521-010637-dvs-backend-language-choice/expected.json` shows I2.6/I2.7/I2.8 all `gating pass`.
- [ ] **`uv run pytest tests/test_verifier.py -q`** passes end-to-end.
- [ ] **`uv run pytest tests/ -q`** passes end-to-end. No pre-existing test outside the verifier suite changes verdict.
- [ ] **CI corpus job goes red on a synthetic fixture violation.** Add a one-off ad-hoc test (`test_gating_blocks_synthetic_i2_8_violation`): construct a synthetic fixture with a bare `turn_started` and no terminal event; run the verifier; assert the I2.8 result is `gating fail` AND that the overall verifier exits non-zero (the CI corpus job would now red on this). This is the executable proof that gating actually gates.
- [ ] **CHANGELOG entry** as per §2.4. Version bumps land in the same commit.

## 7. Risks

- **A latent reporting-only failure becomes a CI block** post-promotion. Mitigation: the four fixtures all pass `pass` pre-merge (verified directly). If a fifth captured run surfaces a real `fail`, that's the kind of bug we want gating to catch — exactly the point of promotion. If it's a false-positive specific to one invariant, demote that invariant in a follow-up commit; do not crisis-patch.
- **`_fixture_regen` produces a regen-twice drift** on a previously-clean fixture. Mitigation: 0240's idempotency tests (`test_fixture_regen_idempotent_on_clean_fixtures`) are the executable lock; if those pass, the regen is stable.
- **A future fixture promoted to the corpus has a legitimately-fail verdict** on one of these three invariants. Mitigation: the corpus-promotion process per the Cowork-discussed pattern requires verifying the fixture's verdicts before adding it; this spec sets the precedent ("only add a fixture once you've verified its verdicts match the gating contract").
- **The promotion locks in a contract that we later regret** (e.g. discovers an edge case where the invariant is wrong). Mitigation: per Cowork sign-off, demote-don't-patch. The reversibility is the safety net.
- **Revert path.** Three one-line severity changes + a fixture directory addition + baseline regen artefacts. Revert is a single `git revert` of this spec's PR; the fixture directory and the baselines disappear cleanly; no migration to unwind.

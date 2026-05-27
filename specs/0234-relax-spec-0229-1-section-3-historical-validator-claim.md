---
kind: dev
spec: "0234"
slug: relax-spec-0229-1-section-3-historical-validator-claim
title: "Refactor: amend spec 0229.1 §3 acceptance criterion to scope the post-backfill validator claim to disposition-class checks only, aligning the spec text with the test that ships (`test_no_existing_spec_fails_specifically_on_disposition`)"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
depends_on: ["0229.1"]
complexity: S
created: 2026-05-27
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: "deferred-from-0229.1"
promoted_from_draft: ""
disposition: defer
disposition_reason: "Documentation cleanup with no operational impact — the actual behaviour is already correctly captured by the test, only the spec prose overstated the claim."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0234 — Refactor: tighten spec 0229.1 §3 historical-validator claim

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** 0229.1 (the spec whose acceptance criterion this scopes)
> **Bump:** PATCH — spec-text amendment only; no code or test change to landed behaviour.
> **Evidence:** The spec 0229.1 handoff at [`handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:32`](handoffs/2026-05-27-spec-0229.1-validator-enforce-disposition-frontmatter.md:32) flags: *"Spec §3 says '`uv run python -m scripts.spec_lifecycle.validator specs/<any-existing-spec>.md` returns 0 post-backfill — every existing spec carries `disposition: archive` + a reason and the validator passes.' That is overstated — 236 dev specs fail the full validator today (and have failed for months) on rules that landed after they were queued: citation-count, source-traceability tables, UI-test path conventions, etc."*

---

## 1. Current state

Spec 0229.1 §3 currently asserts at [`specs/0229.1-validator-enforce-disposition-frontmatter.md:143`](specs/0229.1-validator-enforce-disposition-frontmatter.md:143):

> `uv run python -m scripts.spec_lifecycle.validator specs/<any-existing-spec>.md` returns 0 post-backfill — every existing spec carries `disposition: archive` + a reason and the validator passes.

The second clause overstates what landed. The first clause is correct: every existing spec was backfilled with `disposition: archive` + a reason. The second clause ("the validator passes") is not — 236 specs fail the full validator today on rules that landed after they were queued. Citation-count enforcement, source-traceability tables, UI-test path conventions, and the various spec-0198 / spec-0206 invariants accumulated over time and were never retroactively applied to older specs.

The actual landed test is in [`tests/test_spec_0229_1_validator_disposition.py`](tests/test_spec_0229_1_validator_disposition.py) — specifically `test_no_existing_spec_fails_specifically_on_disposition`, which iterates every existing spec, calls `validate_dev_spec`, and asserts that no error in the result mentions the literal string `"disposition"`. That is the right post-backfill invariant: "no spec fails on disposition-class checks," NOT "no spec fails the full validator."

This is the same discipline named in [`CLAUDE.md` lines 75-87](CLAUDE.md:75) — *"A spec that introduces, removes, or modifies behaviour in [the verifier invariant set] … must carry a `new-feature`, `breaking`, or `refactoring` label, **not** `bug`."* Spec 0229.1 didn't introduce the citation-count or source-traceability invariants; it introduced the disposition invariant. The §3 acceptance criterion should match that scope.

## 2. Target state

Edit [`specs/0229.1-validator-enforce-disposition-frontmatter.md:141-148`](specs/0229.1-validator-enforce-disposition-frontmatter.md:141) — the §3 acceptance-criteria list. The first bullet currently reads:

```
- `uv run python -m scripts.spec_lifecycle.validator specs/<any-existing-spec>.md`
  returns 0 post-backfill — every existing spec carries `disposition: archive`
  + a reason and the validator passes.
```

Rewrite as:

```
- For every existing spec post-backfill, `validate_dev_spec` returns no
  errors whose message contains the literal string `"disposition"`. The
  full-validator-passes claim is out of scope — older specs fail on
  citation-count, source-traceability, and UI-test path rules that landed
  after they were queued, and bringing the historical corpus into compliance
  with the current rule-set is itself a future refactoring spec (path (b)
  in the spec 0229.1 handoff's deferred-item analysis).
```

This matches what `test_no_existing_spec_fails_specifically_on_disposition` actually asserts. The remaining four bullets in §3 stay unchanged — they're per-spec checks on canonical test specs (0230, 0229.1 itself, a synthetic missing-`disposition` spec, full pytest run).

## 3. Stepwise migration

- **Step 1:** Edit [`specs/0229.1-validator-enforce-disposition-frontmatter.md:141-148`](specs/0229.1-validator-enforce-disposition-frontmatter.md:141) per §2. One spec-text amendment, one commit. Verifies by: `git diff specs/0229.1-validator-enforce-disposition-frontmatter.md` shows the rewritten bullet; `uv run python -m scripts.spec_lifecycle.validator specs/0229.1-validator-enforce-disposition-frontmatter.md` still returns 0.
- **Step 2:** Add a one-line note to [`CHANGELOG.md`](CHANGELOG.md) under `### Changed` of the next PATCH bump, referencing this spec and spec 0229.1.
- **Step 3:** Verify the existing `test_no_existing_spec_fails_specifically_on_disposition` still runs green — no test change is needed because the test already encodes the narrower scope.

## 4. Behavior preservation

- [ ] `test_no_existing_spec_fails_specifically_on_disposition` still passes — this spec changes spec text only, not the test.
- [ ] `uv run pytest tests/ -q` stays green.
- [ ] No validator code is touched.

## 5. Out of scope

**Explicit: this spec does NOT feature any new validator capability or behaviour change.** It is a documentation correction of a single acceptance criterion in an already-shipped spec.

Specifically out of scope:

- **Path (b) from the handoff — bringing the historical 236-spec corpus into compliance with every current validator rule.** That is a separate large refactoring spec; this one is path (a) (cheap, scope the claim to what's actually tested).
- **Adding new validator rules or invariants.** Validator behaviour stays exactly as it was at the close of spec 0229.1.
- **Reissuing spec 0229.1 in any larger sense.** Frontmatter, status (`merged`), and code references in 0229.1 are untouched — only the prose of one §3 bullet is amended.

## 6. Risks

- **R1 — Amending a shipped spec post-merge is unusual.** *Mitigation:* CLAUDE.md doesn't prohibit prose corrections to shipped specs, and the alternative (leaving the misleading claim) is worse. The spec frontmatter `status` stays `merged`; this is a body-text-only amendment.
- **R2 — Future readers see two seemingly-conflicting statements in §3 if the edit is ambiguous.** *Mitigation:* the rewrite explicitly names what landed (the narrow disposition-class check) AND what didn't (the full-validator claim) AND points at the future spec path (b) that could close the gap. Future readers get the full picture.

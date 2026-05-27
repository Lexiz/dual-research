---
kind: draft
draft_id: "005"
slug: edit-section-exact-literal-anchor-brittleness
title: "EDIT_SECTION delta application matches anchors by exact string literal — latent same-class brittleness on the drafter delta path"
status: draft
created: 2026-05-27
source_session: deferred-from-0238-investigation
parent_spec: "0238"
disposition: defer
disposition_reason: "Latent brittleness on a separate parser layer (drafter delta application) — not currently blocking any live run, but same bug-class as 0231/0238 (parser intolerance to model-emitted variation). Park until a live run actually surfaces an anchor-not-found in production. Defer rather than archive because the failure mode is real and falsifiable from real-run telemetry."
---

# Draft 005 — EDIT_SECTION anchor matching is exact-string-literal

> **Source:** Step-0 verification of 0231 during the 20260527-142625 investigation. The probe ran `apply_revised_draft_deltas` against the captured failing turn and surfaced `edit_section_anchor_not_found` for ~19 anchors. Investigated and confirmed: the failure was a *test artifact* of the synthetic prior_draft used in the probe. Cowork and the queue session agreed the underlying brittleness is real but out of scope for the 0238 arc.

## Context

`EDIT_SECTION` ops carry an `ANCHOR:` field containing the literal substring inside a draft section that the op wants to find and replace. The current implementation at `src/dual_research/protocol/parse.py` matches the anchor by **exact string literal** — no whitespace tolerance, no normalisation, no fuzziness. If the drafter emits an anchor whose whitespace, capitalisation, or punctuation drifts even slightly from what is actually in the prior draft, the op raises `ProtocolParseError(edit_section_anchor_not_found, …)`.

Example concrete failure shape (from the step-0 probe):

```
edit_section_anchor_not_found:
  EDIT_SECTION '## 2. Findings' anchor
  '| Kotlin | `modelcontextprotocol/kotlin-sdk`, …'
  did not match
```

The drafter is being asked to emit, verbatim, multi-line table rows and prose blocks as anchor strings. Any single character of drift — a trailing space, a smart-quote vs straight-quote, a hyphen variant, a re-flowed multi-line cell — fails the lookup.

This is the **same bug class** as spec 0231 (parser intolerance to model-emitted variation), at a **different surface** (delta application rather than heading anchoring). 0238 closes the heading-anchoring surface. This draft names the delta-anchor surface as the next candidate for the same treatment.

## Why this is a draft, not a spec

Three reasons to park rather than ship now:

1. **No live failure yet.** Step-0 surfaced the brittleness only via a synthetic prior_draft. The real-run prior draft typically does contain the literal anchor (the drafter copies from it). We do not have a captured live-run failure on this path to drive the fix against.

2. **Spec 0232's verifier doesn't observe this class.** I2.6 cross-checks `RAISED_THIS_TURN` against `item_raised` events — a structural invariant on the protocol layer. An anchor-not-found failure is a runtime parser exception that 0232 wouldn't naturally surface unless we add a specific I-* invariant for it.

3. **Two materially different remediation paths, neither obviously right yet.**
   - **Anchor tolerance**: normalise whitespace, quote variants, and trailing punctuation on both sides of the comparison before string-equality testing. Cheap, narrow, preserves the "anchor is a literal" contract.
   - **Diff-based anchor matching**: replace exact-substring lookup with a fuzzy match (e.g. longest-common-substring at ≥0.95 similarity), with anchor-too-ambiguous error on multi-match. Higher coverage, but introduces a similarity threshold that has to be empirically tuned and may mask real drift.
   - The right choice depends on what the first real failure looks like — fuzz-matching is overkill if the failures are all whitespace; tolerance is insufficient if the failures are paragraph re-flows.

## Trigger to promote

Promote to a queued spec when **any** of:

- A live run dies with `edit_section_anchor_not_found` on a real prior_draft (not a synthetic one).
- Spec 0238 ships and we want to close the class symmetrically across all parser surfaces.
- The drafter prompt is changed in a way that increases the probability of anchor drift (e.g. tighter token budget forcing the drafter to elide whitespace).

## Out of scope for this draft

- Fixing `apply_revised_draft_deltas` now. Without a real captured failure, any fix is speculative.
- Changing the `ANCHOR:` field format in the drafter prompt (e.g. switching to line-range or hash-based anchors). That's a separate, larger conversation about the drafter contract.

## Pointers

- Probe that surfaced the brittleness: queue session, step-0 of the 20260527-142625 investigation, ran `apply_revised_draft_deltas(prior_draft=<synthetic>, payload=<from captured turn>)` against `tests/fixtures/anchor-runs/20260527-054652-backend-language-choice/phase4/round-02-claude.malformed-1.md`.
- Implementation: `src/dual_research/protocol/parse.py`, `apply_revised_draft_deltas` (kwargs-only signature: `*, prior_draft: str, payload: RevisedDraftPayload`).
- Related parked work: spec 0238 (parser primitive consolidation) — the heading-anchoring sister of this surface.

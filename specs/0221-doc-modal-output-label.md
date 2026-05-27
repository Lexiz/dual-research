---
kind: dev
spec: "0221"
slug: doc-modal-output-label
title: "Fix: Document modal labels the converged/final draft tab \"Output\" instead of \"Content\""
type: bug
label: bug
version_bump: PATCH
target_version: 1.45.2
status: queued
depends_on: []
complexity: S
created: 2026-05-26
queued_at: ""
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §7 Out of scope with a
named follow-up target. -->

# Spec 0221 — Fix: Document modal labels the converged/final draft tab "Output" instead of "Content"

> **Type:** bug  |  **Severity:** P2  |  **Affects:** v1.45.1 — Phase 3 (Converge Draft) and Phase 5 (Final) full-view document modal
> **Bump:** PATCH — UX label correction, no behavior change
> **Evidence:** [src/dual_research/ui/static/run-detail.jsx:5063-5075](src/dual_research/ui/static/run-detail.jsx#L5063-L5075) — `DocumentModal` builds its tabs list with the draft body under `label: 'Content'`. Readers misread "Content" as prompt/spec content and miss that the converged/final draft sits behind that tab.

---

## 1. Reproduction

**Environment:** Live app at `dual-research-alex.fly.dev` on any completed run with a Phase 3 converged draft and a Phase 5 final draft.

**Steps:**
1. Open any completed run with a converged Phase 3 draft.
2. In the timeline, click the Phase 3 converged-draft card to open the full-view modal.
3. Observe the two tabs: **Agent Input** and **Content**.
4. Repeat for the Phase 5 final-draft card — modal has a single **Content** tab.

**Expected:** The tab containing the converged/final draft markdown is labeled in a way that makes it unambiguous that this is the phase's *output* (the draft body the drafter produced). On a Phase 3 modal that's the second tab; on a Phase 5 modal it's the only tab.

**Actual:** Both tabs use the generic label "Content". Readers expect "Content" to mean the prompt/spec content and miss that the draft body — the actual deliverable of the phase — is sitting one tab away.

## 2. Root cause hypothesis

[src/dual_research/ui/static/run-detail.jsx:5063-5075](src/dual_research/ui/static/run-detail.jsx#L5063-L5075) — `DocumentModal` constructs the same `{ id: 'content', label: 'Content', content: <LazyMarkdownBody …/> }` tab descriptor regardless of `item.kind`. The descriptor is correct for `turn` / `plan` items (where "Content" is a reasonable label for the agent's turn output), but for `doc` / `doc-live` items the body IS the converged/final draft — the phase output — and deserves a clearer label that distinguishes it from "Agent Input".

The id `'content'` is also referenced in [src/dual_research/ui/static/run-detail.jsx:4962](src/dual_research/ui/static/run-detail.jsx#L4962) (`TABS_CANON`), so only the user-facing `label` string can change — the `id` must stay `'content'` to preserve canonical tab ordering.

## 3. Fix

In [src/dual_research/ui/static/run-detail.jsx:5063-5075](src/dual_research/ui/static/run-detail.jsx#L5063-L5075), branch the `label` on `item.kind`:

```jsx
const isDocItem = item.kind === 'doc' || item.kind === 'doc-live';
const tabs = sortByCanon([
  {
    id: 'content',
    label: isDocItem ? 'Output' : 'Content',
    content: <LazyMarkdownBody filePath={item.filePath} />,
  },
  item.turnKey && {
    id: 'input',
    label: 'Agent Input',
    content: <InputTabContent turnKey={item.turnKey} />,
  },
  webSearch,
].filter(Boolean));
```

- The tab `id` stays `'content'` so [src/dual_research/ui/static/run-detail.jsx:4962](src/dual_research/ui/static/run-detail.jsx#L4962) `TABS_CANON = ['input', 'content', 'webSearch', 'sources', 'files']` continues to position this tab second (or first when "Agent Input" is absent on Phase 5).
- No new tab. No new file read. No data-model change.
- `turn`, `turn-live`, `plan`, `plan-live` modals keep `label: 'Content'`.

## 4. User stories & acceptance criteria

### 4.1 — User stories

> As a `researcher` reviewing a completed run, I want the tab that holds the Phase 3 converged draft (and the Phase 5 final draft) to be labeled in a way that signals "this is the phase's output", so that I don't mistake it for prompt/spec content and miss the actual deliverable of the phase.

### 4.2 — Acceptance scenarios (BDD)

> **Scenario 1:** Phase 3 converged-draft modal has Agent Input + Output
> GIVEN a completed run whose Phase 3 converged-draft card has been clicked open in full-view mode
> WHEN the user looks at the modal's tab bar
> THEN they see exactly two tabs whose visible labels are "Agent Input" and "Output", in that canonical order

> **Scenario 2:** Phase 5 final-draft modal has a single Output tab
> GIVEN a completed run whose Phase 5 final-draft card has been clicked open in full-view mode
> WHEN the user looks at the modal's tab bar
> THEN they see a single tab whose visible label is "Output" (no "Agent Input" tab, since the Phase 5 doc item carries no `turnKey`)

> **Scenario 3:** Turn and plan modals are not affected
> GIVEN a completed run with Phase 2 turn cards and Phase 1 plan-draft cards
> WHEN the user opens any turn / turn-live / plan / plan-live full-view modal
> THEN the body tab label remains "Content" (rename is scoped to `doc` / `doc-live` only)

## 5. Regression-prevention test

Per spec 0206 UI test doctrine — source-pattern tests at `tests/test_spec_0221_doc_modal_output_label.py` using [tests/_ui_pattern_helpers.py](tests/_ui_pattern_helpers.py):

- [ ] Positive — `assert_jsx_contains(jsx, r"label:\s*isDocItem\s*\?\s*'Output'\s*:\s*'Content'", msg=…)` (or equivalent regex tolerant of the chosen formatting — locks in that `'Output'` is the label gated on `item.kind === 'doc'` / `'doc-live'`).
- [ ] Positive — `assert_jsx_contains(jsx, r"const\s+isDocItem\s*=\s*item\.kind\s*===\s*'doc'\s*\|\|\s*item\.kind\s*===\s*'doc-live'", msg=…)` confirms the gating predicate is present and correctly scoped (matches both `doc` and `doc-live`).
- [ ] Antipodal-absence — `assert_jsx_lacks(jsx, r"id:\s*'content',\s*\n\s*label:\s*'Content',\s*\n\s*content:\s*<LazyMarkdownBody", msg=…)` — the unconditional `label: 'Content'` shape for the doc-modal body tab descriptor is gone.

Pre-fix shape (rejected by the antipodal test): the literal three-line block at [src/dual_research/ui/static/run-detail.jsx:5064-5067](src/dual_research/ui/static/run-detail.jsx#L5064-L5067).

Post-fix shape (asserted by the positive tests): the body tab descriptor's `label` is a ternary keyed on `isDocItem`, and `isDocItem` is defined as `item.kind === 'doc' || item.kind === 'doc-live'`.

A Claude Preview MCP screenshot showing the Phase 3 doc modal with the new "Output" tab label is mandatory in the PR description (per spec 0206 — runtime rendering verified via screenshot, not Playwright).

## 6. Blast radius

- **`DocumentModal` consumers:** `ArtifactModal` dispatches to `DocumentModal` only for `doc` / `doc-live` items (see [src/dual_research/ui/static/run-detail.jsx:5037](src/dual_research/ui/static/run-detail.jsx#L5037) — the default branch after `input`, `preflight`, `turn`/`turn-live`, `plan`/`plan-live` are dispatched elsewhere). Turn modals use `NegotiateReviewModal`; plan modals use `DraftReviewModal`. Neither is touched.
- **`TABS_CANON`:** the tab `id` stays `'content'`, so canonical ordering in [src/dual_research/ui/static/run-detail.jsx:4962-4969](src/dual_research/ui/static/run-detail.jsx#L4962-L4969) (`sortByCanon`) continues to position this tab correctly.
- **Modal `tabs` prop:** existing Modal primitive, `tabs-solid` variant (per spec 0053). The primitive renders `label` as a plain string — no markup, no a11y impact beyond the visible string change.
- **Tests:** no other test asserts the literal `label: 'Content'` against `DocumentModal`; greps for `label: 'Content'` would otherwise hit `turn` / `plan` paths in unrelated modals which are NOT changed.

## 7. Out of scope

- **Inline timeline card body rendering.** The doc card on the timeline still shows the gist + "View in full mode" button — no inline body. If we want the converged/final draft body inline on the timeline card itself, file a separate follow-up dev spec; not in 0221.
- **Side-by-side comparison logic for Phase 3.** There is no side-by-side viewer for Phase 3 today (doc items are single-pane by design). Not in 0221.
- **Renaming the `Content` tab on `turn` / `turn-live` / `plan` / `plan-live` modals.** Those modals are `NegotiateReviewModal` / `DraftReviewModal` paths, not `DocumentModal`, and their "Content" tab label is semantically correct (it's a turn body, not a phase output). If we want to revisit those labels, file a separate spec.

## 8. Risks

- **Wrong gating predicate.** If the conditional is mistyped (e.g. only `=== 'doc'` and not `=== 'doc-live'`), Phase 3 in-flight live modals would still show "Content". The positive test for the `isDocItem` predicate locks both kinds in.
- **Tab-order regression.** Changing the `id` from `'content'` to anything else would push the body tab to the end of the canonical order (since unknown ids sort to position 999, see [src/dual_research/ui/static/run-detail.jsx:4965-4967](src/dual_research/ui/static/run-detail.jsx#L4965-L4967)). The fix preserves the `id` — the antipodal-absence test's regex is anchored on `id: 'content',` so any accidental id rename would also fail the negative assertion's scope and force a review.
- **Translation / i18n.** None — the app has no i18n layer; labels are hard-coded English strings throughout.

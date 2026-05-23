---
kind: dev
spec: "NNNN"
slug: <kebab>
title: <imperative phrase>
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: []
complexity: S | M | L
created: YYYY-MM-DD
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

# Spec NNNN — <title>

> **Type:** new-feature  |  **Complexity:** <S/M/L>  |  **Depends on:** <list or —>
> **Bump:** <MAJOR/MINOR/PATCH> — <one-line justification>
> **Evidence:** <links to prior specs, run IDs, screenshots, mockups>

---

## 1. Context

Why now? Problem statement. Current state — cite specific files and lines that motivate the change. Two paragraphs max.

## 2. Proposed change

Concrete implementation: file paths, function/component signatures, schema deltas, new endpoints. Cite ≥ 2 file:line locations. A future reader should be able to read this section and understand the full scope of the change.

## 3. User stories & acceptance criteria

### 3.1 — User stories

REQUIRED for any spec that touches files under `src/dual_research/ui/` or `design-system/`. Format:

> As a `<role>`, I want `<goal>`, so that `<outcome>`.

At least one story per user-visible feature. Roles: `researcher`, `dev`, `viewer`, `admin`, `unauthenticated visitor`.

### 3.2 — Acceptance scenarios (BDD)

REQUIRED for any UI-touching spec. ≥ 2 scenarios per spec. Format:

> **Scenario 1:** `<short name>`
> GIVEN `<precondition observable in the DOM or app state>`
> WHEN `<user action: click, type, navigate, hover>`
> THEN `<observable result: element visible, attribute set, text content matches, network call fires>`

> **Scenario 2:** `<short name>`
> GIVEN `<another precondition>`
> WHEN `<another user action>`
> THEN `<another observable result>`

Each scenario must be expressible as a Playwright test. The validator regex-matches `/GIVEN.+\n.*WHEN.+\n.*THEN.+/i` and requires ≥ 2 hits.

For non-UI specs, this section is optional — document before/after, explicit user flows, or screenshot links if helpful.

## 4. Data / Schema deltas

Omit if no schema impact. If included: migrations, backfills, new tables, broken contracts.

## 5. Out of scope

Explicit list of what this spec deliberately does NOT touch. Cuts ambiguity for the implementer.

## 6. Test plan

- [ ] <falsifiable check 1>
- [ ] <falsifiable check 2>
- [ ] <…>

At least two checkboxes, each falsifiable.

## 7. Risks

What could go wrong. How we'll mitigate. If a risk is "we'll revert if it breaks", say so.

---
kind: dev
spec: "NNNN"
slug: <kebab>
title: Fix: <symptom>
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 0
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

# Spec NNNN — Fix: <symptom>

> **Type:** bug  |  **Severity:** <P0/P1/P2>  |  **Affects:** <versions / surfaces>
> **Bump:** PATCH — bug fix
> **Evidence:** <run IDs / screenshots / error logs / first-bad commit if known>

---

## 1. Reproduction

**Environment:** <browser/OS/app version/run context>

**Steps:**
1. …
2. …
3. …

**Expected:** <what should happen>

**Actual:** <what happens, with evidence link>

## 2. Root cause hypothesis

What's wrong and why. Cite ≥ 1 file:line location.

## 3. Fix

Concrete change — exact code, diff sketch, or pseudocode pointing at the file(s) to edit.

## 4. User stories & acceptance criteria

REQUIRED for UI bug fixes (any spec that touches files under `src/dual_research/ui/` or `design-system/`). Optional otherwise — the §5 Regression-prevention test below is the load-bearing gate for non-UI bugs.

### 4.1 — User stories

> As a `<role>`, I want `<goal>`, so that `<outcome>`.

At least one story per user-visible regression. Roles: `researcher`, `dev`, `viewer`, `admin`, `unauthenticated visitor`.

### 4.2 — Acceptance scenarios (BDD)

REQUIRED for any UI-touching bug spec. ≥ 2 scenarios per spec. Format:

> **Scenario 1:** `<short name>`
> GIVEN `<precondition observable in the DOM or app state>`
> WHEN `<user action: click, type, navigate, hover>`
> THEN `<observable result: element visible, attribute set, text content matches, network call fires>`

> **Scenario 2:** `<short name>`
> GIVEN `<another precondition>`
> WHEN `<another user action>`
> THEN `<another observable result>`

Each scenario must be expressible as a Playwright test. The validator regex-matches `/GIVEN.+\n.*WHEN.+\n.*THEN.+/i` and requires ≥ 2 hits.

## 5. Regression-prevention test

A test that fails before this fix and passes after.

- [ ] Test: <name / what it asserts / failure mode it locks in>

## 6. Blast radius

What else uses this code path? Why this fix doesn't break adjacent callers.

## 7. Out of scope

Adjacent issues we noticed but won't fix here.

## 8. Risks

What could go wrong with the fix itself.

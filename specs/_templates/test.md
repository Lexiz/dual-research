---
kind: dev
spec: "NNNN"
slug: <kebab>
title: Tests: <area>
type: test
label: test
version_bump: PATCH
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
either answered here or explicitly deferred via §4 Risks or an explicit
follow-up target in §3. -->

# Spec NNNN — Tests: <area>

> **Type:** test  |  **Complexity:** <S/M/L>
> **Bump:** PATCH — test additions only
> **Evidence:** <prior bugs/incidents this would have caught, coverage report excerpts>

---

## 1. Coverage gap

Which surface lacks tests today? Cite ≥ 2 file:line locations for the un-covered code.

## 2. Test approach

What kinds of tests (unit / integration / E2E). Frameworks. Fixtures needed.

## 3. What it would catch

Reference at least one historical bug / incident or a concrete class of failure mode this coverage prevents.

## 4. Risks

Mostly flakiness, slow test runs, false confidence from over-mocking.

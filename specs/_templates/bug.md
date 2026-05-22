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

## 4. Regression-prevention test

A test that fails before this fix and passes after.

- [ ] Test: <name / what it asserts / failure mode it locks in>

## 5. Blast radius

What else uses this code path? Why this fix doesn't break adjacent callers.

## 6. Out of scope

Adjacent issues we noticed but won't fix here.

## 7. Risks

What could go wrong with the fix itself.

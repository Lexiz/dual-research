---
kind: dev
spec: "NNNN"
slug: <kebab>
title: <imperative phrase>
type: breaking
label: breaking
version_bump: MAJOR
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
either answered here or explicitly deferred via §6 Out of scope with a
named follow-up target. -->

# Spec NNNN — <title>

> **Type:** breaking  |  **Complexity:** <S/M/L>  |  **Depends on:** <list or —>
> **Bump:** MAJOR — breaking change
> **Evidence:** <prior specs being broken, contracts being removed, blast-radius investigation>

---

## 1. Context

Why this breaks. Cite ≥ 2 file:line locations for the contracts being changed.

## 2. Proposed change

Concrete change. File paths, function/component signatures, schema deltas, new endpoints.

## 3. Compatibility break statement

What's breaking. Who's affected (callers, consumers, persisted data, deployed clients).

## 4. Migration plan

Concrete steps to migrate existing data, callers, and any downstream system. If single-user, this is "what I'll do after merge."

## 5. Rollback plan

If the break turns out wrong: how to revert. Includes data restoration if relevant.

## 6. Out of scope

Adjacent contracts we're NOT touching in this break.

## 7. Test plan

- [ ] <falsifiable check 1>
- [ ] <falsifiable check 2>

## 8. Risks

Risks specific to the break itself: silent data loss, missed call sites, version skew during deploy.

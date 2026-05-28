---
kind: dev
spec: "NNNN"
slug: <kebab>
title: "Refactor: <area>"
type: refactoring
label: refactoring
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
# Spec 0229 §2.5 carve-out-disposition convention. Pick one of:
#   ship     — high-priority follow-up, should reach /dev-next
#   defer    — recorded but not actionable soon
#   archive  — informational record only (the default for carve-outs)
disposition: ship | defer | archive
disposition_reason: "One-sentence justification for the disposition choice."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec NNNN — Refactor: <area>

> **Type:** refactoring  |  **Complexity:** <S/M/L>  |  **Depends on:** <list or —>
> **Bump:** PATCH — internal restructure, no behavior change
> **Evidence:** <pain points being closed, prior specs that struggled with this>

---

## 1. Current state

What exists today. Cite ≥ 2 file:line locations. Explain the pain.

## 2. Target state

What it should look like after. Cite the target files / structure.

## 3. Stepwise migration

Each step independently shippable / revertable.

- **Step 1:** <change> — verifies <how>
- **Step 2:** …
- **Step N:** …

## 4. Behavior preservation

- [ ] Existing test <name> still passes (covers behavior X)
- [ ] New parity test for behavior Y (if any contract isn't already covered)

## 5. Out of scope

**Explicit: this spec does NOT add any new feature.** Any feature work that depends on this refactor lives in a follow-up spec.

## 6. Risks

What could go wrong. Refactoring risks: hidden behavior depending on internals, performance regression, missed call site.

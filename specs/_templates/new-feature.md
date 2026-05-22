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

# Spec NNNN — <title>

> **Type:** new-feature  |  **Complexity:** <S/M/L>  |  **Depends on:** <list or —>
> **Bump:** <MAJOR/MINOR/PATCH> — <one-line justification>
> **Evidence:** <links to prior specs, run IDs, screenshots, mockups>

---

## 1. Context

Why now? Problem statement. Current state — cite specific files and lines that motivate the change. Two paragraphs max.

## 2. Proposed change

Concrete implementation: file paths, function/component signatures, schema deltas, new endpoints. Cite ≥ 2 file:line locations. A future reader should be able to read this section and understand the full scope of the change.

## 3. UX / Behavior

Omit if not user-facing. If included: before/after, explicit user flows, screenshot links if any.

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

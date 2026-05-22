---
kind: draft
draft_id: "003"
slug: timeline-refresh
title: Timeline refresh — align live pane with design-system reference
type: unclassified
status: draft
created: 2026-05-22
source_session: pre-lifecycle-bootstrap
parked_from: prototypes/timeline-iteration/ (untracked working files)
---

# Draft 003 — Timeline refresh

> **Status:** unclassified. Promotion to dev queue requires picking a `type` (likely `new-feature` for visual refresh, or `refactoring` if the live timeline DOM is being restructured without adding behavior).

---

## What this is

Pre-spec iteration captured in [`prototypes/timeline-iteration/`](../../prototypes/timeline-iteration/). The directory contains a side-by-side comparison harness for the run-detail timeline pane:

- `live.html` — verbatim `.rdvc__pane` outerHTML dumped from the live dev server at `http://localhost:6173/#/runs/20260521-…` on 2026-05-22.
- `ds.html` — verbatim `<section id="timeline">` from Design System v2.html §16.
- `proposed.html` — proposed target.
- `mockup.html` — wrapper that loads `live.html` and `ds.html` into iframes for tab-switched comparison.

Both iframes pull the same CSS files the underlying pages use (live: `src/dual_research/ui/static/*.css`; ds: `design-system/assets/styles/v2-m3{,-page}.css`). The comparison is verbatim, not transcribed.

## Unresolved questions

These must be answered before this draft can be promoted to a dev spec:

- What's the actual change the spec should ship? (Full DOM rewrite of `.rdvc__pane` to match `ds.html`? Token-level alignment only? Per-element delta list?)
- Does this require touching the live data flow, or is it purely visual?
- What's the version bump — MINOR if user-visible, PATCH if internal refactor?
- Is this one spec or several? (Per-row alignment is granular enough to split.)

## Next step

Either:

1. Iterate in a fresh authoring session to flesh out the scope and call `/spec-promote 003` when complete.
2. Or `rm specs/drafts/draft-003-timeline-refresh.md && rm -rf prototypes/timeline-iteration/` to discard.

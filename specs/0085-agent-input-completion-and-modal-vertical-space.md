---
spec: 0085
title: Agent Input panel — system-prompt fallback, structural hierarchy, modal vertical space
label: new-feature
version-bump: PATCH
status: in-review
target-version: 0.69.9
created: 2026-05-18
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0085 — Agent Input panel completion + modal vertical space

## Context

The 2026-05-18 tweak-cycle audit
([`audits/2026-05-18-tweak-cycle-screenshot-audit.md`](../../dual-research-automation/audits/2026-05-18-tweak-cycle-screenshot-audit.md))
graded the Agent Input arc as the biggest unshipped piece of arc M1. Three
deltas remain open and they are tightly coupled — they share the same
modal infrastructure, the same backend bundle path, and the same surface
the user invests the most reading time in:

- **Delta `15.30`** ([audit:1516](../../dual-research-automation/audits/2026-05-18-tweak-cycle-screenshot-audit.md:1516))
  — when an older run's input bundle was never recorded, the panel falls
  back to a single placeholder sentence "Agent input bundle was not
  recorded for this run…". The user explicitly said this is impossible:
  every agent session begins with a system prompt that we ALREADY have
  in source (`protocol/prompts.py::*_input_bundle()`), so the panel must
  always be able to surface at least the agent's default system prompt
  plus a contextual note about what's missing.
- **Delta `17.13`** ([audit:1778](../../dual-research-automation/audits/2026-05-18-tweak-cycle-screenshot-audit.md:1778))
  — the broader Agent Input structural rework. The current panel renders
  a flat list of `INPUT_PIECE_ORDER` keys; the spec calls for a 3-tier
  hierarchy with **System Prompt** first (collapsed), **User Prompt**
  second (expanded, with nested "From chat" + "External resources
  mentioned" sub-sections), then **Child Pages** as top-level entries
  per resource pulled. The shipped flat list is on the right track but
  doesn't break the User Prompt down into chat-content vs external-
  resource sub-blocks, and child pages aren't surfaced at all.
- **Delta `15.13` (deferred checks)** ([audit:1403](../../dual-research-automation/audits/2026-05-18-tweak-cycle-screenshot-audit.md:1403))
  — the modal sub-tab rename to "Agent Input" + first-position default
  shipped for single-view modals, but split-view modals
  (`NegotiateReviewModal`, `DraftReviewModal`) and the search palette's
  index of tab names were never verified.

Layered on top of those, the **2026-05-19 user-feedback addendum** flagged
a fourth, broader issue: **modals do not utilise full vertical screen
space.** The user's screenshot shows the `Input — brief` modal capping
at ~38% of viewport height with empty backdrop below, despite having
many pages of brief content available to read. `.dr-modal` has
`max-height: 92vh` but no floor on size — short bodies produce short
modals even when the surrounding viewport could comfortably hold more.
This penalises exactly the surfaces (Agent Input, Content) where the
user reads the most.

These four items belong in one spec because they share infrastructure:
the bundle synthesis fallback (15.30) is the prerequisite for the 3-tier
rework to render anything useful on historical runs (17.13); the modal
sizing fix (vertical space) is most valuable on the same modals
(`InputBriefModal`, `NegotiateReviewModal`, `DraftReviewModal`) the
Agent Input rework touches; and the split-view + search-palette
verification (15.13) is the last loose end of the same modal-chrome
work. Splitting would force a sequential dependency.

## Proposed change

### A. Backend — bundle synthesis fallback for historical runs

When a run's per-phase input bundle is not on disk (older runs that
pre-date spec 0033's input auditing), the server currently returns
`None` from `_read_input_bundle_fs` / `_read_input_bundle_supabase`
for every phase except Phase 0 (which already synthesises from
`brief.md` via `build_phase0_input_bundle`).

**Extend the synthesis pattern to all phases.** Add a sibling helper
`build_input_bundle_fallback(session_dir, turn_key)` in
[`src/dual_research/ui/aggregator.py`](src/dual_research/ui/aggregator.py)
that, given a turn key (e.g. `phase1Claude`, `phase2Round1GPT`,
`phase4Round2Claude`), dispatches to the matching builder in
[`src/dual_research/protocol/prompts.py`](src/dual_research/protocol/prompts.py)
(`preflight_input_bundle`, `research_input_bundle`,
`negotiation_round1_input_bundle`, `negotiation_turn_input_bundle`,
`drafting_input_bundle`, `review_input_bundle`, `repair_input_bundle`).
The builder is called with the run's `brief.md` content and the
agent name; the function returns the canonical
`{system, brief, d1, d2, plan, hist, draft, histp}` dict with the
**system prompt populated from the agent default** and the other keys
left empty (or with explicit `null`/placeholder sentinels indicating
"not recorded for this historical run").

Update `_read_input_bundle_fs` and `_read_input_bundle_supabase` in
[`src/dual_research/ui/server.py`](src/dual_research/ui/server.py) so
that when the persisted bundle JSON is missing, they call
`build_input_bundle_fallback` instead of returning `None`. The
response carries a new top-level boolean `synthesized: true` (default
`false` when the bundle was loaded from disk) so the frontend can
render the right caveat.

The dispatcher uses turn-key parsing already implemented in
`_normalize_input_key` and the existing `phaseN` / `RoundN` /
`Claude`/`GPT` lexer; if the key cannot be parsed, return `None`
and let the existing empty-state path handle it.

### B. Backend — expose agent default system prompt as a stable field

Add a single new aggregator field
`bundle.system_source: 'recorded' | 'agent-default'` indicating where
the `system` piece came from. When the full bundle was loaded from
disk, this is `'recorded'`; when synthesised via the fallback, it is
`'agent-default'`. The frontend uses this to decide whether to render
the "this is the default for this agent — the per-run system prompt
may have differed" caveat.

No new endpoint is needed — this is a field added to the existing
`GET /api/runs/{id}/input-bundle/{turn_key}` response.

### C. Frontend — `InputTabContent` 3-tier hierarchy

Restructure
[`run-detail.jsx::InputTabContent`](src/dual_research/ui/static/run-detail.jsx:4637)
(currently a flat map over `INPUT_PIECE_ORDER`) into the 3-tier
layout from delta 17.13's fix spec:

1. **System Prompt** (always first, collapsed by default).
   Sourced from `bundle.pieces.system`. If
   `bundle.system_source === 'agent-default'`, prepend a small italic
   `--fg-3` note inside the section body: _"This is the agent's
   default system prompt — the per-run system prompt for this older
   run was not recorded."_
2. **User Prompt** (second, expanded by default). The existing
   `brief` piece becomes the **From chat** sub-section (rendered via
   the existing `<Markdown>` component). When the brief contains
   external-resource references (Notion links, URLs), they are
   surfaced as a second **External resources mentioned** nested
   sub-section that lists each link as a compact `[link · name]`
   row. Use the existing markdown-link extractor (`marked` already in
   tree). Each link in the sub-section is clickable and scrolls to
   the corresponding Child Page entry below (anchor link).
3. **Child Pages** (zero or more, each as its own top-level
   collapsible entry below User Prompt). For runs whose bundle
   records pulled external pages, the bundle adds a new optional
   `child_pages: [{id, name, url, parent_resource, content}]` array.
   Each child page is one collapsible entry titled
   `Child page · {page.name}` with subtitle `from {page.parent_resource}`.
   For runs without `child_pages` (the common case today), the tier
   is simply absent — no empty placeholder.
4. **Other canonical pieces** (`d1`, `d2`, `plan`, `hist`, `draft`,
   `histp`) continue to render below Child Pages in their existing
   canonical order, using the existing `InputSection` component.
   They keep their current default-collapsed/expanded states.

The existing `InputSection` and `CollapsibleSection` primitives are
re-used end-to-end; the only new wrapper is a `NestedSubSection`
helper for the User Prompt's internal sub-sections (a thin variant
of `CollapsibleSection` with reduced left padding to communicate
nesting).

`bundle.child_pages` is opt-in: the backend never adds it for runs
that didn't capture child pages, and the frontend simply omits the
tier when the field is missing or empty.

### D. Frontend — empty-state replacement

Delete the body of `InputEmptyState` at
[`run-detail.jsx:4708`](src/dual_research/ui/static/run-detail.jsx:4708)
for the "bundle not recorded" branch. That code path no longer
triggers because the backend always returns a synthesised bundle
(at minimum the System Prompt) for historical runs. `InputEmptyState`
stays only for the two other branches: `error` (network failure
fetching the bundle) and `renderKeys.length === 0` (turn key
genuinely has no input — e.g., a synthetic placeholder turn).

### E. Frontend — modals use full vertical space

In [`components.css`](src/dual_research/ui/static/components.css:898)
update the `.dr-modal` rule to claim a floor on viewport height:

```css
.dr-modal {
  /* …existing… */
  min-height: min(72vh, max-content);
  max-height: 92vh;
}
```

Rationale: `min(72vh, max-content)` means "always at least 72% of
viewport when content can fill that, but stay short for genuinely
short modals" (e.g., a confirmation dialog with one paragraph). The
ceiling stays at 92vh; the body's existing `flex: 1; min-height: 0;
overflow: auto` continues to handle scroll inside.

The same rule applies automatically to `.dr-modal.is-split` since the
selector cascades. Verify the split-view modals don't regress —
their internal `dr-modal-split` already declares `min-height: 60vh`
and `flex: 1`, so they should fill the modal's new floor.

### F. Split-view modals — sub-tab rename + reorder verification

Audit
[`NegotiateReviewModal`](src/dual_research/ui/static/run-detail.jsx:3705)
and
[`DraftReviewModal`](src/dual_research/ui/static/run-detail.jsx:4091)
for any remaining `'Input'` sub-tab labels and confirm they read
`'Agent Input'` and that the renamed tab is first across BOTH panes.
If any case is missed, fix in-place (same one-line rename + array
reorder pattern that landed in single-view modals).

### G. Search palette index

In [`search-palette.jsx`](src/dual_research/ui/static/search-palette.jsx)
verify that typing `"agent"` surfaces the `Agent Input` tab as a
hit. Internal tab identifier stays `"input"` (URL deep-links don't
break); only the displayed label and search-token list change.
Add `"agent input"` and `"agent"` as additional search tokens for
the `input` tab if they aren't already there.

## Out of scope

- **Metadata footer chip clusters** on Issue/Comment cards (deltas
  19.36/19.47) — belongs in the cross-cutting polish spec (Spec 3 of
  the consolidation plan).
- **Consumption tab rework** (deltas 20.14/20.18) — separate spec
  (Spec 2 of the consolidation plan).
- **`<QuoteCallout>` extraction for `> quote:` lines inside the
  User Prompt body** — already shipped per delta 19.36's
  acceptance check; this spec inherits that behavior via the
  existing `<Markdown>` wrap. No new work needed.
- **Capturing child-page content at runtime** — this spec only adds
  the OPTIONAL `child_pages` field to the bundle schema and renders
  it when present. Populating it for new runs (orchestrator-side
  capture as agents resolve Notion links / URLs) is a separate
  follow-up; without that follow-up the tier simply doesn't render.
- **Modal width** — the user's feedback was about vertical space
  specifically. `max-width: 1100px` and `is-split` 1300px stay as
  they are.
- **Dark-theme verification of the new layout** — covered by the
  existing global theme regression, not part of this spec's QA.

## Test plan

- [ ] **Unit**: extend the existing aggregator tests with a case for
  `build_input_bundle_fallback` covering Phase 1, Phase 2 Round 1,
  Phase 2 Round 3 (negotiation_turn), Phase 4 review, and the repair
  path. Assert the returned dict has a non-empty `system` piece and
  `system_source === 'agent-default'`.
- [ ] **Unit**: snapshot a `_read_input_bundle_fs` call for a
  historical run with no `inputs/phase1Claude.json` on disk; assert
  the response is the synthesised bundle, not `None`.
- [ ] **Manual — empty bundle (delta 15.30 acceptance)**: open the
  partner-vetting `3a4a` run → Phase 0 Claude `brief critique` →
  Agent Input tab. Expect: System Prompt section visible (collapsed,
  click to expand → see the default Claude critique system prompt
  + the italic "agent default" caveat); NO dashed-border empty
  placeholder anywhere.
- [ ] **Manual — bundle present**: open `live-integration-test` (the
  most recent completed run) → Phase 1 Claude `plan draft` → Agent
  Input tab. Expect: 3-tier hierarchy with System Prompt first
  (collapsed, no caveat — `system_source === 'recorded'`), User
  Prompt expanded with "From chat" sub-section rendered via
  Markdown, no Child Pages tier (this fixture has no `child_pages`).
- [ ] **Manual — modal vertical space (user-feedback acceptance)**:
  open any `Input — brief` modal in a tall viewport (≥900px).
  Modal occupies at least ~70% of viewport height; the backdrop
  region below the modal is no greater than the symmetric region
  above it. Scrolling inside the modal body works; backdrop click
  still closes.
- [ ] **Manual — split-view (delta 15.13 deferred check)**: open
  any Phase 2 Negotiate turn → "View in full mode" → split modal
  appears. Both panes' first tab reads "Agent Input" and is the
  default-active tab in each pane.
- [ ] **Manual — search palette**: open `Cmd+K` palette, type
  "agent" → "Agent Input" tab appears as a result; type "input" →
  same result still appears.
- [ ] **Regression**: open a Phase 0 modal on a NEW run (one with a
  recorded bundle) — the existing `build_phase0_input_bundle`
  synthesis path stays intact; bundle loads from disk; nothing
  regresses.

## Risks

- **Synthesised system prompt drift.** If the agent's default system
  prompt has changed between when the historical run executed and
  today's codebase, the displayed System Prompt is the CURRENT
  default, not the actual prompt used. Mitigation: the
  `system_source: 'agent-default'` caveat tells the user exactly
  this. Acceptable — the user explicitly hedged on this trade-off
  in the briefing.
- **`min-height: 72vh` on short-content modals.** Confirmation
  dialogs or single-tab modals with very little content could
  suddenly feel oversized. Mitigation: `min(72vh, max-content)` lets
  genuinely short content render short. Verify by smoke-testing the
  `PreflightResponseModal` and any other small modals during manual
  QA.
- **Markdown extractor mis-identifying external resources.** If the
  link-extraction regex picks up code-fence URLs or other false
  positives, the "External resources mentioned" sub-section noises
  up. Mitigation: extract only markdown-link syntax (`[label](url)`),
  not bare URLs in code blocks. The existing `marked` AST exposes
  link nodes directly — use the AST, not a regex.
- **Empty `child_pages` array vs `undefined`.** Backend MUST omit
  the field rather than serialise `[]` to keep the frontend's
  "tier absent" branch clean. Add a unit test.

## Open questions

- Should the "External resources mentioned" sub-list be expanded or
  collapsed by default? Spec calls for collapsed; defer the call to
  implementation when the live UI is visible. (My recommendation:
  collapsed — most users won't need to drill in, but power users get
  one click to the list.)
- For runs WHOSE bundle is present but is partial (e.g., has a
  recorded `system` but no recorded `brief`), should
  `system_source` be `'recorded'` (because the system piece is real)
  or `'mixed'` (a new value)? Recommendation: keep two values
  (`'recorded'` and `'agent-default'`); a partial bundle reports
  `'recorded'` for what it has and renders nothing for what it
  doesn't. Simpler, and no real run today hits the "partial" case.

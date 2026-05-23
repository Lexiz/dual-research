---
kind: dev
spec: "0188"
slug: item-card-issue-comment-bodies-via-thread-view
title: Route ItemCardIssueBody and ItemCardCommentBody through ItemCardThreadView
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
queue_position: 11
depends_on: ["0173"]
complexity: S
created: 2026-05-23
queued_at: "2026-05-23T00:00:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: deferred-from-0173
promoted_from_draft: ""
---

# Spec 0188 — Route ItemCardIssueBody + ItemCardCommentBody through ItemCardThreadView

> **Type:** new-feature  |  **Complexity:** S  |  **Depends on:** 0173
> **Bump:** MINOR — visible behavior change: Issue + Comment cards gain the QuestionThread-bubble anatomy in their expanded view. Same data, new render path. No API / schema change.
> **Evidence:** Spec 0173 handoff `## Deferred during implementation` second bullet — [handoffs/2026-05-23-spec-0173-drain-deferrals-from-0166-0167-0168.md:43](handoffs/2026-05-23-spec-0173-drain-deferrals-from-0166-0167-0168.md:43): *"spec §2.9 says 'Restructure the expanded layout to use the QuestionThread anatomy' for all kinds. The implementation wired the bubble timeline into `ItemCardDQBody` only … the spec's literal reading wants all four kinds threaded."*

---

## 1. Context

Spec 0173 §2.9 promised that **all four** ItemCard kinds (Question, Disagreement, Issue, Comment) would render their expanded view as a QuestionThread-anatomy stack of tonal-tinted message bubbles. The implementation wired the bubble timeline into `ItemCardDQBody` only — Question and Disagreement got the new view; Issue and Comment kept their pre-0173 per-kind chrome. The component infrastructure for the bubble view is fully built and shipped: `ItemCardThreadView({ item })` exists at [src/dual_research/ui/static/run-detail.jsx:1511–1545](src/dual_research/ui/static/run-detail.jsx) and is exercised by `ItemCardDQBody` at [src/dual_research/ui/static/run-detail.jsx:1688](src/dual_research/ui/static/run-detail.jsx). It accepts a single `item` prop, reads `item.transitions`, `item.raiser`, `item.raisedRound`, etc. — all four kinds already carry that data shape because the `ItemCard` parent resolves the same item record before delegating to a per-kind body ([src/dual_research/ui/static/run-detail.jsx:1860–1880](src/dual_research/ui/static/run-detail.jsx)).

The pain — and why this is queued, not deferred again:

- **Visible inconsistency in the expanded state.** A run that has a Question and an Issue side-by-side renders the Question as bubbles but the Issue as the older flat `.item-card__seen-row` strip. The two cards now look like different primitives even though they're the same kind-of-thing on the data layer. Spec 0173 §2.9's stated rule was the opposite: all four should look like the same primitive.
- **`ItemCardThreadView` already handles the degenerate case.** An Issue with a single "raised" transition and no follow-up transitions just renders one bubble. A Comment with one `raisedRound` and no transitions renders one bubble. The view doesn't blow up on thin data — spec 0173 already exercised it through `ItemCardDQBody` when a Question has zero transitions and only the raise event.
- **No schema change required.** Both `ItemCardIssueBody` and `ItemCardCommentBody` already receive the full `item` prop ([src/dual_research/ui/static/run-detail.jsx:1699, 1746](src/dual_research/ui/static/run-detail.jsx)) — exactly the shape `ItemCardThreadView` consumes.

This spec is the catch-up: extend Issue + Comment bodies to render `<ItemCardThreadView item={item} />` in place of (or alongside) their existing per-kind chrome, closing the §2.9 promise.

## 2. Proposed change

Extend two body components in [src/dual_research/ui/static/run-detail.jsx](src/dual_research/ui/static/run-detail.jsx):

### 2.1 — ItemCardIssueBody

Current shape at [src/dual_research/ui/static/run-detail.jsx:1699–1738](src/dual_research/ui/static/run-detail.jsx):

```jsx
<div className="item-card__body item-card__body--issue">
  <div className="item-card__title-row">
    <strong className="item-card__sid">{shortCode}</strong>
    <Chip tone={stateTone} size="sm">{stateLabel}</Chip>
    <span className="item-card__title-sep">—</span>
    <span className="item-card__title">{titleLine}</span>
  </div>
  {/* optional quote inline */}
  {/* optional restBody markdown */}
  <div className="item-card__seen-row">
    {/* flagged-by / first-seen / last-seen chips */}
  </div>
  {/* optional anchor bottom blockquote */}
</div>
```

After this spec — the title row stays (it carries the short code + Issue title which is the load-bearing summary), the optional quote stays, the optional body markdown stays, but **the `.item-card__seen-row` triple-chip block is replaced** by `<ItemCardThreadView item={item} />`:

```jsx
<div className="item-card__body item-card__body--issue">
  <div className="item-card__title-row">…</div>
  {/* optional quote */}
  {/* optional body markdown */}
  {/* NEW: bubble thread replaces the seen-row strip */}
  <ItemCardThreadView item={item} />
  {/* optional bottom anchor blockquote — retained */}
</div>
```

The bubble view captures the same data the seen-row strip carried (raiser identity, first-seen round, transition rounds + actors) but in the canonical QuestionThread anatomy. The two-chip `first seen R{N}` / `last seen R{M}` summary becomes implicit — the bubble timeline shows the raise round as the first bubble and the latest transition round as the last bubble.

### 2.2 — ItemCardCommentBody

Current shape at [src/dual_research/ui/static/run-detail.jsx:1746–1767](src/dual_research/ui/static/run-detail.jsx):

```jsx
<div className="item-card__body item-card__body--comment">
  {item.body && <div className="item-card__text"><Markdown text={String(item.body)} /></div>}
  {/* optional quote */}
  <div className="item-card__seen-row">
    {/* noted-by Agent · R{round} */}
  </div>
  {/* optional bottom anchor blockquote */}
</div>
```

After — same pattern as §2.1: replace the `.item-card__seen-row` with `<ItemCardThreadView item={item} />`. Comments often have only the raise transition (no follow-ups), so the bubble view will render a single bubble for most comments — and that single bubble already carries the `noted by {agent}` + `R{round}` data via the provider chip + round chip cluster.

### 2.3 — ItemCardThreadView verb-label adjustment (optional polish)

`ItemCardThreadView` today emits the verdict-chip label from `_transitionVerb(t)` ([src/dual_research/ui/static/run-detail.jsx:1469–1478](src/dual_research/ui/static/run-detail.jsx)) which maps transitions to verbs that fit Question / Disagreement vocabulary (`raised`, `pushed back`, `restated`, `aligned`, `conceded`). For Comment items where the only transition is the raise event, the verdict chip label `raised` is fine and reads correctly. For Issue items, the existing verbs are also a reasonable match (`raised`, `pushed back`, `conceded`).

No verb-map change is required — the polish is letting the existing tone-toned verb chips do the work. If a future spec finds the vocabulary jarring for one kind, it can extend `_transitionVerb` to be kind-aware. Out of scope here.

### 2.4 — What does NOT change

- The card head ([src/dual_research/ui/static/run-detail.jsx:1813–1968](src/dual_research/ui/static/run-detail.jsx)) is unchanged. Provider chip / kind chip / evidence-needed modifier / head-spacer / lifecycle chip composition stays exactly as spec 0173 §2.5 + §2.6 + §2.7 + §2.8 left it.
- Collapse default (`data-expanded="false"`) per spec 0173 §2.11 is unchanged.
- The title row inside `ItemCardIssueBody` (the `Issue I-N — title` line) stays — Issue cards lean on the title as the primary summary; replacing it with a bubble would lose the load-bearing copy.
- The Markdown body of Comments stays — comments are the one kind whose primary content is a free-form markdown paragraph (the "comment text"), distinct from the transition arc. Both render together: markdown body up top, bubble timeline below.
- No CSS additions — `ItemCardThreadView`'s styles at [src/dual_research/ui/static/components.css:4548–4593](src/dual_research/ui/static/components.css) already cover Issue and Comment usage because the component is kind-agnostic.

## 3. UX / Behavior

**Before this spec.** Expanding a Question or Disagreement card shows tonal bubbles (post-0173). Expanding an Issue or Comment card shows flat `.item-card__seen-row` chip strips. Side-by-side, the two look like different design primitives.

**After this spec.** Expanding any of the four kinds shows the same bubble anatomy. The bubble count varies — Disagreements typically have 2–4 bubbles, Comments typically have 1, Issues have 1–2 — but the visual idiom is identical across kinds. Provider color tint, round chip, and verdict chip read consistently across the four kinds, so the reader's eye doesn't have to switch parsing modes between an Issue card and the Disagreement next to it.

User-visible artifacts:
- Issue and Comment cards: expanded body switches from triple-chip strip to bubble timeline. Same data, new render.
- DS reference [design-system/assets/Design System v2.html](design-system/assets/Design System v2.html) §13 is **not** updated in this spec — spec 0187 covers that catch-up. If 0187 ships first, its example pair already covers I + C in the new shape; if this spec ships first, 0187 picks up the I + C examples with no extra work.

## 4. Data / Schema deltas

No schema change. Both `ItemCardIssueBody` and `ItemCardCommentBody` already receive the full `item` prop, and `ItemCardThreadView` reads only fields that already exist on every kind (`raiser`, `raisedRound`, `transitions`, `body`).

## 5. Out of scope

- **Title-row removal in Issue cards.** The `Issue I-N — title` line at the top of `ItemCardIssueBody` is the primary summary chrome and stays. This spec does not collapse it into the bubble view.
- **Markdown-body removal in Comment cards.** Comments carry meaningful free-form text in `item.body`; the markdown block stays above the bubble timeline.
- **Kind-aware vocabulary in `_transitionVerb`.** The existing verb map is reused. If the implementer notices a verb that reads oddly for Issues / Comments (e.g. a Comment in `addressed` state showing the verb `pushed back`), they may surface that as a follow-up but should not fix it in this cycle.
- **DS reference page updates.** Spec 0187 handles [design-system/assets/Design System v2.html](design-system/assets/Design System v2.html) §13. No duplicate effort here.
- **Hover / click behavior on individual bubbles.** Spec 0173 §2.9 did not add per-bubble interactivity, and neither does this spec.
- **`anchorType === 'quote' && anchorText` rendering.** Both Issue and Comment cards optionally render an inline + bottom blockquote when the item carries an anchor quote. Both blockquotes stay — they're document-level chrome, not part of the transition arc.

## 6. Test plan

- [ ] **Visual parity (Disagreement → Issue).** Pick a run that has both a resolved Disagreement and a resolved Issue in the same phase (the anchor run `20260521-010637-dvs-backend-language-choice` Phase 4 is the spec-0173 anchor — it carries both). Expand both. Assert: both render the same bubble anatomy (provider chip + round chip + verdict chip in a `.item-card__bubble` with the styled blockquote).
- [ ] **Single-transition Comment renders one bubble.** Pick a Comment that has only the `raised` event and no follow-up transitions. Expand it. Assert: one bubble renders, carrying the raiser provider chip + `R{round}` chip + `raised` verdict chip + the comment text as blockquote — equivalent data to the old `.item-card__seen-row` but in canonical anatomy.
- [ ] **Issue title row stays above the bubble.** Expand an Issue card. Assert: the title row (`I-N — title`) renders above the bubble stack, not inside it. The bubble stack carries only the transition timeline; the title is document-level.
- [ ] **No regression on Question / Disagreement.** Spec-0173 anchor tests continue to pass. The `ItemCardThreadView` API does not change in this spec; only its call sites multiply.
- [ ] **`uv run pytest tests/ -q` green.** No new test file required — the change is JSX-only, structural, and lives at component-composition layer. The existing run-detail structural fixtures cover the wider page render. If the implementer wants an extra structural regex test ("`ItemCardIssueBody` body contains `<ItemCardThreadView`"), that's a one-line addition under [tests/spec0173/](tests/spec0173/) and welcome but not required.
- [ ] **Collapsed state unchanged.** Default-collapsed cards (every card on initial render per spec 0173 §2.11) still render head-only. The new body is hidden by the existing `.item-card[data-expanded="false"] .item-card__body { display: none }` rule at [src/dual_research/ui/static/components.css:4641–4665](src/dual_research/ui/static/components.css) — verify by inspecting an Issue card in collapsed state and confirming the bubble DOM nodes exist but are hidden.

## 7. Risks

- **Visual density of single-bubble cards.** Comments and many Issues will render with only one bubble. A single tinted bubble with one chip cluster + one blockquote could look chunkier than the prior single-line chip strip. Mitigation: this is what spec 0173 §2.9 explicitly asked for — "all four kinds threaded" — and the bubble has padding tuned for the multi-bubble case. If the single-bubble density reads as too heavy, a follow-up spec can add a `--compact` modifier to the bubble for the degenerate case, but we ship the literal §2.9 reading first.
- **Verb-label drift on rare-state Issues.** An Issue that transitions through `acknowledged` will show the `aligned` verb in its bubble — same as a Disagreement does. The verb map is kind-agnostic. If this reads wrong, the follow-up is to make `_transitionVerb` kind-aware. Mitigation: spec 5 explicitly lists this as out of scope; implementer logs any oddities as a future spec but does not fix here.
- **Markdown body + bubble visual stacking.** Comment cards now render markdown body + bubble timeline. The two competing "primary content" regions could fight for visual hierarchy. Mitigation: the markdown body uses `.item-card__text` styling (smaller, lighter weight, left-aligned); the bubbles use tinted containers with provider chip clusters. Visual separation is structural, not just spatial — the reader's eye treats them as "summary text" vs. "transition timeline" naturally.
- **Test coverage gap.** Pytest does not exercise JSX runtime, so visual regressions are not caught automatically. Mitigation: the test plan above lists the visual checks the implementer must run by hand on the anchor run before merging. The structural regression test pattern in `tests/spec0173/` could be extended, but the spec body does not require it.
- **DS reference doc drift if 0187 ships in a different order.** If this spec ships before 0187, the live render is bubble-everywhere but the DS reference still shows the old `.item-card__seen-row` chip strip. Mitigation: 0187 is queued at position 16 and this at position 17 — they should ship close in time. If this lands first, 0187's authoring picks up the I + C examples in the new shape; the temporary drift is one cycle at most.

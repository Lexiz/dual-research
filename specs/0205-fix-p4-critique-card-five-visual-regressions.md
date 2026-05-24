---
kind: dev
spec: "0205"
slug: fix-p4-critique-card-five-visual-regressions
title: "Fix: P4 critique card — five visual regressions (sources layout/icon, lifecycle-first ordering, coloured kind filter chips, raiser badge defaulting to System)"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
depends_on: []
complexity: M
created: 2026-05-24
queued_at: "2026-05-24T02:19:30Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
---

# Spec 0205 — Fix: P4 critique card — five visual regressions

> **Type:** bug  |  **Severity:** P1  |  **Affects:** P4 Review critique pane on run-detail page (all critique-item kinds: Question / Disagreement / Issue / Comment)
> **Bump:** PATCH — bug fix
> **Evidence:** five screenshots captured in the queueing conversation (user-supplied), referenced inline below as *screenshot #1 .. #5*

A recent critique-section spec was intended to close the remaining visual gaps; five regressions slipped through. This spec captures the full pack: a single coherent bundle (one surface, one test plan, one initiative the user named as "bugfix pack") rather than five micro-specs.

---

## 1. Reproduction

**Environment:** dual-research dashboard (`https://dual-research-alex.fly.dev/`), latest `main`, any modern browser, run-detail page → P4 Review tab.

### Bug 1 — Sources segment stretches full width; expanded source row does not match reference

**Steps:**
1. Open any run-detail with critique items that carry `evidence`/`sources`.
2. Navigate to P4 Review.
3. Expand any card that has `Sources (N)`.

**Expected:** the Sources segment renders per `design-system/SPEC.md:493`–`504` (§4.7) — `t-overline` "Sources (N)" header above a dashed top border, vertical stack of `SourceRow` instances each indented inside the card chrome (NOT full-bleed). Expanded source row matches the reference: URL · FETCHED timestamp · SEARCH QUERY · CONTENT EXCERPT inside a styled blockquote with the card's interior padding.

**Actual:** the `.item-card__sources` block (`src/dual_research/ui/static/run-detail.jsx:2068`–`2075`) stretches edge-to-edge across the card and the expanded `SourceRow` (`src/dual_research/ui/static/run-detail.jsx:1373`) inner content does not match the reference layout (no proper field/blockquote treatment). Evidence: screenshot #1.

### Bug 2 — Card opens with raw body text first; lifecycle absent

**Steps:**
1. P4 Review → click any individual Issue or Comment card to expand.

**Expected:** the first body section the user sees is the LIFECYCLE — `ItemCardLifecycleSection` (`src/dual_research/ui/static/run-detail.jsx:1535`–`1594`) emits the `LIFECYCLE` overline, then a stack of `.lc-row` entries with the raise row leading (provider chip of the raising agent + the raise quote rendered inside the row). The raw `<Markdown text={item.body} />` block is NOT rendered as a separate full-bleed paragraph above it — the body text lives inside the raise row's quote slot.

**Actual:** `ItemCardIssueBody` (`src/dual_research/ui/static/run-detail.jsx:1758`–`1769`) and `ItemCardCommentBody` (`src/dual_research/ui/static/run-detail.jsx:1782`–`1793`) render `<Markdown text={item.body} />` ABOVE `<ItemCardLifecycleSection />`, double-rendering the body and pushing the lifecycle below an unformatted full-bleed text block. Evidence: screenshot #2 — opened Issue card shows raw text jammed against the card edges with no lifecycle header visible.

### Bug 3 — Sources icon glyph is wrong on header chip and expanded segment header

**Steps:**
1. Inspect any critique card with `Sources (N)` chip in the header (`src/dual_research/ui/static/run-detail.jsx:1857`–`1862`).
2. Expand the card; inspect the Sources segment header at `src/dual_research/ui/static/run-detail.jsx:2070`.

**Expected:** both the header chip and the expanded segment header use a sources/citations glyph (e.g. Material `mdi:book-open-variant`, `mdi:source-branch`, `mdi:bookmark-outline`, or `mdi:link-variant` — whichever the DS canonical references at `design-system/SPEC.md` §4.7 + the badge governance §9.3 sanction). Same glyph in both locations for visual consistency.

**Actual:** the current glyph is generic / wrong and inconsistent between collapsed-card chip and expanded-segment header. Evidence: screenshots #1 + #2.

### Bug 4 — Kind filter chips render as plain buttons, not the four coloured category badges

**Steps:**
1. P4 Review → look at the filter row (above the Open / Resolved / Drift groups).

**Expected:** per `design-system/SPEC.md:366` (§4.1, Bar 2 — *"kind tabs in the canonical order Questions · Disagreements · Issues · Comments"*) AND the principle of one card primitive per surface (`design-system/SPEC.md:36`), the four kind filters should render with the same coloured-tone Chip primitive used on card heads — `<Chip tone={kindTone} categoryBubble={kindLetter} label={kindLabel} value={count} />` per the head's kind chip at `src/dual_research/ui/static/run-detail.jsx:1952`–`1954`. Tones: Q→info, D→warn, I→err, C→idle (`src/dual_research/ui/static/run-detail.jsx:1508`–`1510`). Each chip carries the Q/D/I/C category bubble icon and the trailing count.

**Actual:** the filter row uses `<Tab variant="kind">` (`src/dual_research/ui/static/run-detail.jsx:7505`–`7530`) — plain segmented-tab buttons without the per-kind brand colour, without the `cat-bubble` icon, just text + count. Evidence: screenshot #3 (red-outlined filter row showing `Questions 1 / Disagreements 1 / Issues 8 / Comments 2` as monochrome tab buttons).

### Bug 5 — Raiser badge shows "System" on every card

**Steps:**
1. P4 Review → inspect the leading chip on any card in any group (Open / Resolved / Drift).

**Expected:** the first chip is always the actual provider that raised the card — `<Chip tone="claude" label="Claude" leadingIcon={<AgentIcon agent="claude" />} />` or the GPT equivalent (`src/dual_research/ui/static/run-detail.jsx:1933`–`1940`). Per `design-system/SPEC.md:36` (principle 11) and §9.3 (fixed mappings, never swap): an agent identity chip on the head, never `System` — `System` is reserved for the orchestrator (Phase 0 brief card per `design-system/SPEC.md` §4.4 *"Agentless brief card"*), NOT for critique items, which are always raised by Claude or GPT.

**Actual:** `providerChip` falls back to `<SystemChip />` at `src/dual_research/ui/static/run-detail.jsx:1940` whenever `raisedByAgent` resolves to null. Every card in the screenshots ends up with `System` as the leading chip — the data flow is dropping `raisedBy` on the wire, OR the wire field name is different from what `_resolveAgent` expects (`src/dual_research/ui/static/run-detail.jsx:1519`–`1523`). Evidence: screenshot #4 (red-circled `System` chip on every visible card row).

## 2. Root cause hypothesis

| # | File:line | Hypothesis |
|---|---|---|
| 1 | `src/dual_research/ui/static/components.css` (and `design-system/assets/styles/composed-components.css`) `.item-card__sources` + `.src-row` rules | Selectors missing the per-card interior gutter (probably no `padding-inline` on `.item-card__sources` and no inner blockquote / metadata grid on the expanded `SourceRow`). Fix is CSS-only against §4.7 reference. |
| 2 | `src/dual_research/ui/static/run-detail.jsx:1758`–`1769` and `:1782`–`1793` | `ItemCardIssueBody` / `ItemCardCommentBody` render `<Markdown text={item.body}/>` as a standalone block BEFORE `<ItemCardLifecycleSection />`. The body text already lives inside the lifecycle's raise-row `quote` slot (`src/dual_research/ui/static/run-detail.jsx:1540`, `:1552`), so the standalone `<Markdown>` block is a duplicate. Remove the standalone block; keep the inline `<blockquote class="item-card__quote-inline">` anchor since it carries a different field (anchor text, not body). For DQ bodies (`ItemCardDQBody` at `src/dual_research/ui/static/run-detail.jsx:1733`–`1744`) the lifecycle is already the leading body section — no change needed there; spot-check parity. |
| 3 | Wherever the Sources chip + segment header pick their icon (`src/dual_research/ui/static/run-detail.jsx:5972` for one chip variant; the `.item-card__sources-hd` at `:2070` has no icon currently and the header `Sources {N}` chip at `:1857`–`:1862` carries an icon-or-none chip via the Chip primitive). The glyph in use is not the DS-sanctioned sources glyph. Pick one glyph (e.g. `mdi:book-open-variant` or `mdi:link-variant` — defer to `design-system/SPEC.md` §4.7 + §9 governance; if no canonical glyph is documented, add a one-line clarification to §4.7 in the same commit). |
| 4 | `src/dual_research/ui/static/run-detail.jsx:7505`–`7530` | Filter row uses `<Tab variant="kind">` instead of the kind `<Chip>` primitive. Replace each `<Tab variant="kind">` with `<Chip tone={kindTone[kind]} categoryBubble={kindLetter[kind]} label={kindLabel[kind]} value={count} onClick={…} data-active={kindFilter === kind} />`. Reuse `_ITEM_KIND_TONE` / `_ITEM_KIND_LETTER` / `_ITEM_KIND_LABEL` at `:1504`–`:1513`. Toggle behaviour preserved (clicking active deselects). Add CSS hover / active treatment scoped to the filter-row variant if needed (the same Chip primitive already supports `[data-active]`). |
| 5 | `src/dual_research/ui/static/run-detail.jsx:1940` (fallback) + the data layer that supplies `raisedBy` to critique items. | Critique items must always carry a provider raiser. Two-pronged fix: (a) at the data layer (server-side wire format, in `src/dual_research/ui/server.py` or wherever `raisedBy` is projected) confirm the field is populated for every item rendered in P4 — investigate the projection path that produces the items rendered on the run-detail page. (b) Tighten the JSX fallback: if `raisedByAgent` is null, log a console.warn with `item.id` so future regressions surface, and either render the kind chip first (no leading provider) or render a `tone="err"` error chip — NOT a `<SystemChip />` which falsely claims an orchestrator raise. |

## 3. Fix

Concrete touch-list (dev-next will refine; not all five must land in identical commits but a single PR):

### 3.1 Bug 1 — Sources segment CSS

- In `src/dual_research/ui/static/components.css` AND `design-system/assets/styles/composed-components.css`: add `padding-inline: var(--md-spacing-4)` (or whatever matches the card's interior gutter token) to `.item-card__sources` so the segment indents inside the card body rather than going full-bleed. Mirror the canonical layout in `design-system/notion-issues/screenshots/` for the Sources reference shot.
- In the same files: scope the expanded `.src-row` (or the SourceRow CSS class name; resolve at edit time) to render `URL` / `FETCHED` / `SEARCH QUERY` rows as a two-column grid (label · value, label in `t-overline`) and the `CONTENT EXCERPT` as a `<blockquote>` with `--md-surface-container-low` background and brand-toned left border, matching screenshot #1 (the Rust survey reference shot).

### 3.2 Bug 2 — Lifecycle leads in body renderers

Edit `src/dual_research/ui/static/run-detail.jsx`:

```jsx
// ItemCardIssueBody (currently :1758)
function ItemCardIssueBody({ item, anchorType, anchorText }) {
  return (
    <div className="item-card__body item-card__body--issue">
      <ItemCardLifecycleSection item={item} />
      {anchorType === 'quote' && anchorText && (
        <blockquote className="item-card__quote-inline">quote: {anchorText}</blockquote>
      )}
    </div>
  );
}
// Same pattern for ItemCardCommentBody at :1782
```

The standalone `<Markdown text={item.body}/>` is removed because `ItemCardLifecycleSection` already renders `item.body` as the raise row's quote (`run-detail.jsx:1540`, `:1552`). The inline `item-card__quote-inline` anchor (a different field) is kept and moved below the lifecycle, since it's a structural annotation, not duplicate body.

`ItemCardDQBody` (`:1733`–`:1744`) already renders LifecycleSection as the leading body block — no change, but visually verify parity per `design-system/SPEC.md:378` (ItemCard parity verification, spec 0179: the 8-capture side-by-side grid must accompany this PR).

### 3.3 Bug 3 — Single canonical Sources glyph

Pick the glyph in `design-system/SPEC.md` §4.7 (add a one-line note if not yet documented: *"Sources segment + header chip use `mdi:<chosen-name>` glyph; no per-card variation."*). Apply to (a) the Sources Chip in card-head at `run-detail.jsx:5972` (and the analogous in-`Chip` head usage near `:1857`–`:1862`), and (b) the `.item-card__sources-hd` at `:2070` (which currently has no leading icon — add an `<Mdi name="…" size={11} />` adjacent to the "Sources (N)" overline text).

### 3.4 Bug 4 — Replace filter Tabs with kind Chips

Edit `src/dual_research/ui/static/run-detail.jsx:7505`–`7530`:

```jsx
{['questions', 'disagreements', 'issues', 'comments'].map((kind) => {
  const singular = kind.slice(0, -1);  // 'questions' -> 'question'
  return (
    <Chip
      key={kind}
      tone={_ITEM_KIND_TONE[singular]}
      size="sm"
      categoryBubble={_ITEM_KIND_LETTER[singular]}
      label={_ITEM_KIND_LABEL[singular] + 's'}
      value={kindCounts[kind] || 0}
      data-active={kindFilter === kind ? 'true' : 'false'}
      onClick={() => setKindFilter(kindFilter === kind ? 'all' : kind)}
    />
  );
})}
```

Plus a scoped CSS rule for the active state on filter-row Chips (`.crit-filter-row .chip[data-active="true"]` — lifted elevation, slightly stronger fill, or whatever the DS canonical reference for "active kind chip" prescribes). Keep `_ITEM_KIND_TONE` / `_ITEM_KIND_LETTER` / `_ITEM_KIND_LABEL` as the single source of truth — they're already used for card-head kind chips, which is the parity we want.

Remove the now-unused `variant="kind-tabs"` and `variant="kind"` branches in `shared.jsx` IFF nothing else depends on them (grep before deletion; if still used elsewhere, leave them and only stop emitting from this call site).

### 3.5 Bug 5 — Restore provider raiser on critique cards

Investigate at edit time:

1. Grep for the wire-format projection that builds the items array consumed at `run-detail.jsx:7148`–`7151` (`questions` / `disagreements` / `issues` / `comments` props). Most likely in `src/dual_research/ui/server.py` or an adjacent projector.
2. Confirm `raisedBy` is set per item to `'claude'` / `'gpt'` / `'openai'`. If the wire is sending it under a different name (e.g. `raised_by`, `raiser`, `actor`), either rename on the wire OR add the alias to `_resolveAgent` (`run-detail.jsx:1519`–`:1523`).
3. Tighten the JSX fallback at `run-detail.jsx:1940`: replace `<SystemChip />` with an `err`-toned error chip (`<Chip tone="err" leadingIcon={<Mdi name="alert-circle" size={10} />} label="Unknown raiser" />`) AND log a `console.warn('critique item missing raisedBy', item.id)` so future regressions are loud.
4. Add a regression-prevention test (see §5) that asserts the rendered chip text for a synthetic item with `raisedBy: 'claude'` is "Claude", not "System".

## 4. User stories & acceptance criteria

### 4.1 User stories

> As a **viewer** reviewing a P4 critique pane, I want every card to show the **agent that raised it** (Claude or GPT), so that I can scan who is owning each issue without expanding the card.

> As a **viewer** opening any critique card (Question / Disagreement / Issue / Comment), I want the **lifecycle to lead the body** with the raise row showing the raising agent and the raise quote, so that I see "who said what when" before any other detail.

> As a **viewer**, I want the **kind filters** at the top of the critique pane to use the same coloured-category badges I see on card heads, so that filtering and reading carry one visual vocabulary.

> As a **viewer** expanding a card with cited sources, I want the **Sources segment** to sit inside the card's interior gutter (not full-bleed), with each expanded source rendered as `URL / FETCHED / SEARCH QUERY / CONTENT EXCERPT` per the reference layout, so that I can read citations without the layout fighting the card chrome.

> As a **viewer**, I want a recognisable **citations glyph** on every Sources chip and segment header, consistently across the collapsed and expanded states, so that I can spot evidence-bearing cards at a glance.

### 4.2 Acceptance scenarios (BDD)

> **Scenario 1:** Filter row renders the four kind chips with brand tones
> GIVEN the P4 Review tab is active on a run that has at least one Question, Disagreement, Issue, and Comment
> WHEN the filter row at `.crit-filter-row` is queried
> THEN the row contains exactly four `<button class="chip ...">` elements with tones `info`, `warn`, `err`, `idle` respectively, each carrying a `.cat-bubble` element with the letter Q/D/I/C, each with a trailing `.chip-value` count.

> **Scenario 2:** Active kind chip lifts; second click deselects
> GIVEN the filter row is rendered with no kind selected (default)
> WHEN the user clicks the "Issues" chip
> THEN the chip carries `data-active="true"`, the body filters to issues only, and clicking the chip a second time restores `data-active="false"` and the unfiltered view.

> **Scenario 3:** Every critique card head shows the raising agent, never "System"
> GIVEN a run with critique items where every item has a `raisedBy` of `claude` or `gpt`
> WHEN P4 Review is rendered
> THEN no `.item-card__head` contains the text "System"; every head's leading chip is either tone-claude with label "Claude" or tone-gpt with label "GPT".

> **Scenario 4:** Expanded Issue card opens with lifecycle leading
> GIVEN an Issue card with a non-empty `item.body` and `raisedBy: 'claude'`
> WHEN the user expands the card
> THEN the first element inside `.item-card__body` is `.item-card__lifecycle-section` (with the `LIFECYCLE` overline visible), and no standalone `<Markdown>` block carrying `item.body` is rendered above it.

> **Scenario 5:** Expanded source row matches reference layout
> GIVEN a critique card with at least one evidence record carrying `url`, `fetched_at`, `search_query`, and `content_excerpt` fields
> WHEN the source row is in its expanded state
> THEN the row renders `URL`, `FETCHED`, `SEARCH QUERY` as label-value rows inside the card's interior gutter (NOT full-bleed) and `CONTENT EXCERPT` inside a `<blockquote>` with the DS-canonical surface tint and left border.

## 5. Regression-prevention test

- [ ] **`tests/ui/test_p4_critique_card.py::test_raiser_chip_never_system_for_critique_items`** — Playwright; loads a fixture run with `raisedBy='claude'` on every critique item; asserts `await page.locator('.item-card__head:has-text("System")').count() == 0` and asserts both `.item-card__head .chip.tone-claude` AND `.item-card__head .chip.tone-gpt` are present (at least one of each across the page). Locks in Bug 5.
- [ ] **`tests/ui/test_p4_critique_card.py::test_kind_filter_chips_use_chip_primitive`** — asserts the filter row contains four `.chip.cat-bubble`-bearing elements with the expected `tone-{info,warn,err,idle}` classes and trailing `.chip-value` counts. Locks in Bug 4.
- [ ] **`tests/ui/test_p4_critique_card.py::test_expanded_issue_card_lifecycle_leads`** — expands a fixture Issue card and asserts the first child of `.item-card__body--issue` is `.item-card__lifecycle-section`. Locks in Bug 2.
- [ ] **`tests/ui/test_p4_critique_card.py::test_sources_segment_indented_and_blockquoted`** — asserts the computed `padding-inline` on `.item-card__sources` is non-zero AND the expanded source row contains a `blockquote` with the DS surface-tint background token. Locks in Bug 1.
- [ ] **`tests/ui/test_p4_critique_card.py::test_sources_chip_and_header_share_icon`** — asserts the `Mdi` name on both the head `Sources` chip and the segment header glyph match a single canonical value (whatever §3.3 picks). Locks in Bug 3.

All five tests fail on `main` before the fix and pass after.

## 6. Blast radius

- **`run-detail.jsx`** is the consumer. No other consumers — the affected functions (`ItemCard`, `ItemCardIssueBody`, `ItemCardCommentBody`, `ItemCardDQBody`, `SourceRow`, `ItemCardLifecycleSection`, the kind filter row) are only invoked from the critique pane on run-detail.
- **`Tab variant="kind"` deletion** (if §3.4 retires the variant) — grep before deletion. If anything outside this row uses it, leave the variant alive and only switch the call site.
- **`<SystemChip />` retention** — `SystemChip` is still used legitimately for the Phase 0 agentless brief card (`design-system/SPEC.md` §4.4 *"Agentless brief card"*) at `run-detail.jsx:1257`, `:1262`. Bug 5 only removes the FALLBACK usage on critique-item heads; the brief-card usage is untouched.
- **CSS in two files** — both `src/dual_research/ui/static/components.css` (live) AND `design-system/assets/styles/composed-components.css` (canonical) must move in the same commit per `CLAUDE.md` (*"New components land in two places in one commit"*). This rule applies to edits as well as additions.
- **Wire-format change for `raisedBy`** (if §3.5 confirms a server-side gap) — touches the JSON projector serving the run-detail page. Verify any other consumer of the same projection (e.g. timeline pane, drift listing) doesn't depend on the missing field with an inverted assumption.

## 7. Out of scope

- Any change to the lifecycle-row formatting itself (chip cluster, quote rendering inside `.lc-row`) — `ItemCardLifecycleSection` at `run-detail.jsx:1535`–`1594` stays as-is; this spec only changes WHERE it's rendered (leading the body) and what the SIBLING blocks render.
- Any change to terminal-state footer logic (`lifecycleFooter` at `run-detail.jsx:1843`–`1849`) — footer continues to render in its current position.
- Wire-format changes beyond restoring `raisedBy` on critique items. If the investigation in §3.5 finds the data layer has a broader issue (e.g. `transitions[].actor` also missing on some items), file a follow-up dev spec — do not expand scope here.
- Any change to the Σ Summary or P0 / P2 critique sub-renderers — this spec is P4-only as documented in the user-reported screenshots. Deferred to a follow-up dev spec only if a regression surfaces.
- Updates to the `design-system/SPEC.md` §4.7 / §4.8 prose UNLESS §3.3 needs to add the canonical Sources glyph name (one-line addition only).

## 8. Risks

- **Lifecycle-first ordering departs from `design-system/SPEC.md:510`–`517` (§4.8) prose** which currently lists `Header → Body → Evidence-needed → Lifecycle → Footer → SOURCES`. Reconcile in the same PR: either update the §4.8 stacking order to `Header → Lifecycle → quote-inline (when applicable) → Footer → SOURCES` for Issue + Comment kinds, OR clarify that the per-kind body sub-renderers are allowed to depart from the canonical order when the lifecycle's raise row carries the body. The user-facing requirement (Scenario 4) is what ships; the DS prose must match what ships.
- **`Tab variant="kind"` removal** could leave unused CSS / JS dead-weight if not fully grepped before deletion. Mitigation: leave the variant alive and only switch the call site if grep finds other consumers.
- **`raisedBy` server-side change** risks shifting data for other consumers if the field is renamed rather than aliased. Prefer adding an alias in `_resolveAgent` over renaming the wire field, unless the wire field is unambiguously wrong.
- **Visual parity verification** per `design-system/SPEC.md:378` (spec 0179) requires the 8-capture side-by-side grid in the PR description. PRs without the grid are blocked at merge — dev-next must produce the captures during step 14 / 15.

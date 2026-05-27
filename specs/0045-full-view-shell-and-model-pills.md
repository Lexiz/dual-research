---
spec: 0045
title: Full-view shell standardisation + model pill layout
label: refactoring
version-bump: MINOR
status: merged
target-version: 0.43.0
created: 2026-05-17
pr: "https://github.com/Lexiz/dual-research/pull/46"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0045 — Full-view shell standardisation + model pill layout

## Context

Layout-and-shell tightening across the run-detail view. None of
this is data work (the wire format is already what it needs to be
after specs 0042 / 0043 / 0044); the spec exists to make the
*chrome* consistent so the eye doesn't have to re-orient between
modals or between the two model headers.

Three threads, all visual:

1. **Full-view modal tabs render in different orders depending on
   which surface opened them.** Today:
   - `DocumentModal` (Phase 3 doc, brief, etc.) → `[Content | Input | Web Search]`
   - `NegotiateReviewModal` (P2/P4 turns, after spec 0044) →
     `[Original (with doc-tabs) | Input | Web Search]`
   - `DraftReviewModal` (Phase 1 plan-draft) →
     `[Original (left pane) | Input (left pane)]` PLUS
     `[Draft | Web Search]` (right pane)
   - `InputBriefModal` (Phase 0 input card) →
     `[Input content | Sources | Files]`

   The labels and the order shift between modals. A user opening
   two different full-views in quick succession has to re-find each
   tab. The user's original feedback was unambiguous: "For all full
   views, the sequence of the tabs should always be the same: input
   content, sources. It cannot flip around."

2. **Input bundle full-view shows every protocol input piece, even
   ones the turn didn't use.** Today the Input tab renders the
   per-turn input bundle with "not used in this turn: …" annotations
   beneath the used ones. The user's complaint: "Don't show the
   sections that are not used in this turn. Just show the ones that
   are only used in this turn." Empty sections are visual noise;
   absence is the signal.

   Related: the Input full-view doesn't have an obvious "this is the
   user's prompt" anchor. The brief.md is the user-supplied prompt
   for the run, but it's rendered as one piece among many without
   any framing. User reported: "Where is the user prompt? I'm missing
   that section."

3. **Side-by-side modal columns are unequal width.** The
   `NegotiateReviewModal` uses `gridTemplateColumns: 'minmax(0,
   1.5fr) minmax(0, 1fr)'` (left pane 50% wider than the right);
   `DraftReviewModal` uses `'minmax(0, 1fr) minmax(0, 1.3fr)'`
   (right pane 30% wider). The unequal widths are arbitrary inheritance
   from earlier specs; the user wants both panes equal so the eye
   reads them as parallel surfaces, not as a primary + secondary.

4. **Model pills in the timeline header are unequal width.** The
   Claude pill is meaningfully wider than the GPT pill (the model
   names have different lengths and the cost/token strings vary).
   User wants both pills equal width, with logo + provider + model
   name left-aligned and tokens + cost + status right-aligned. They
   also asked to bump the Claude pill +20% and match GPT to it.

Prior context:
- [Spec 0025](./0025-modal-shell.md) — established `Modal` +
  `tabs` API.
- [Spec 0027](./0027-side-by-side-review.md) — Phase 2 side-by-side
  modal pattern.
- [Spec 0033](./0033-inputs-foundation-and-header.md) — per-turn
  Input bundle + Input tab.
- [Spec 0036](./0036-web-search-audit-foundation.md) — Web Search
  tab plumbing.
- [Spec 0038](./0038-web-search-audit-ui.md) — model pill alignment
  fix (toolbar reordering), but pill widths were unaddressed.
- [Spec 0044](./0044-turn-input-semantics-and-badge-redesign.md) —
  added `NegotiateDocTabs` strip under the left pane's Original
  sub-mode; this spec keeps that strip but standardises the
  outer-tab ordering.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Canonical tab order across every full-view modal: `[Content \| Input \| Web Search \| Sources \| Files]`.** | Tabs that don't apply to a given modal are omitted; tabs that DO apply always render in this order. `Content` is the primary surface (markdown body / draft / etc.). The order is locked by a shared `TABS_CANON` array consumed by every modal that builds a tabs list. Modals with a side-by-side structure (Negotiate, Draft) use the inner left-pane sub-tabs (`Original | Input | Web Search`) and follow the same canonical order. |
| D2  | **Hide tabs whose content is empty.** | If a modal's `Files` data is empty, the Files tab is not rendered (not "Files (0)"). Same for Sources, Web Search, etc. The user reads tab presence as "this surface has data here." Absence is the signal. |
| D3  | **Input full-view: hide protocol input pieces with zero tokens / no body.** | The per-turn input bundle today renders all spec-0033 pieces (`brief`, `d1`, `d2`, `plan`, `hist`, `draft`, etc.) with "not used in this turn" annotations on the absent ones. After this spec only the used pieces render; absent pieces don't render at all (the per-turn input is necessarily a subset of the possible pieces — that subset IS the input). |
| D4  | **Input full-view: rename "Brief" → "User prompt: Brief" and float to the top of the section list.** | The brief is the user-supplied research prompt for the run. The label "Brief" is implementation language; "User prompt: Brief" tells the reader what role this section plays. Always renders first when present (it's always the most relevant input piece). **Forward-compatibility note:** if a future spec adds a CLI argument for a distinct "user prompt" string separate from the brief file, the label re-points to that. v1 treats the brief AS the user prompt because that's what the current CLI surfaces. |
| D5  | **Equal-width Original / Draft panes in side-by-side modals.** | `NegotiateReviewModal` and `DraftReviewModal` both move to `gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)'`. Reads as parallel surfaces. The doc-tab strip inside the left pane (spec 0044 D4) is unchanged. |
| D6  | **Model pill layout: equal-width, left-aligned identity, right-aligned metrics.** | The two pills in the timeline header (`Claude`, `GPT`) become equal width via a shared CSS `min-width` derived from the larger of the two. Internal layout: `[logo] [provider] [model]` left-aligned, `[flex] [tokens] [·] [cost] [·] [status]` right-aligned. The Claude pill grows ≈20% over its current width to accommodate the new alignment; GPT matches. |
| D7  | **Shared `Sources` tab is the canonical name for what's currently called "Files" in some places.** | Spec 0033's input full-view used "Sources" + "Files" interchangeably across iterations. Canonicalise on `Sources` for citation-source bundles (web search → cited URLs), `Files` for uploaded / referenced files. The user's original feedback listed both: `[Input content | Sources | Files]`. Most full-views today only have `Sources` data (cited URLs from web search); the `Files` tab is unused. Render `Files` only when actual files exist. |
| D8  | **Tab labels do not carry counts.** | Pre-spec some tab labels show `Web Search ⚠` (spec 0038 hallucination chip) or `Files (3)`. The badge/count goes back to the tab content body, not the tab label. Tabs themselves become single-word/short noun labels. Exception kept: the `⚠` indicator on Web Search when a hallucination is flagged — it stays as a tab-label badge because the user needs to see it without clicking. |
| D9  | **No data-model changes.** | Pure JSX + CSS. The wire format from specs 0033 / 0036 / 0038 / 0042 / 0043 carries everything needed. No new endpoints, no new `Run` fields. |

## Proposed change

### 1. Canonical tab order — `src/dual_research/ui/static/run-detail.jsx` + `shared.jsx`

Add a shared canonical-order constant near the existing modal helpers:

```js
// Spec 0045 D1 — canonical tab order across every full-view modal.
// Modals build their tabs list, then sort by this index. Tabs whose
// id isn't in TABS_CANON keep their author-declared order at the end.
const TABS_CANON = ['content', 'input', 'webSearch', 'sources', 'files'];
function sortByCanon(tabs) {
  return [...tabs].sort((a, b) => {
    const ia = TABS_CANON.indexOf(a.id);
    const ib = TABS_CANON.indexOf(b.id);
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
  });
}
```

`DocumentModal`, `NegotiateLeftSubTabs`, `DraftRightSubTabs`,
`InputBriefModal`, and any other full-view tab-builder call
`sortByCanon(tabs)` before passing into `<Modal tabs={...} />` or
the inline sub-tab rendering.

### 2. Hide empty tabs — D2

Each tab-builder filters tabs whose content is empty BEFORE
sorting:

```js
const tabs = sortByCanon([
  { id: 'content',   label: 'Content',    content: <LazyMarkdownBody filePath={item.filePath} /> },
  bundle && hasInputData(bundle) && { id: 'input', label: 'Input', content: <InputTabContent ... /> },
  webSearchData && webSearchData.totalQueries > 0 && { id: 'webSearch', label: 'Web Search', ... },
].filter(Boolean));
```

`hasInputData(bundle)` checks whether the bundle has at least one
non-empty piece. `webSearchData` is the existing
`SearchIndexContext` summary lookup.

### 3. Input full-view: hide unused sections + user-prompt section — D3, D4

`InputTabContent` (per-turn input bundle render) walks the bundle
pieces. Today it renders all known piece keys with "not used" tags
on absent ones. After spec 0045:

```js
const PIECE_ORDER = ['brief', 'd1', 'd2', 'plan', 'hist', 'draft', 'histp'];
const PIECE_LABEL = {
  brief: 'User prompt: Brief',          // D4 — rename + float to top
  d1:    "Claude's Phase 1 draft",
  d2:    "GPT's Phase 1 draft",
  plan:  'Agreed plan',
  hist:  'Prior Phase 2 turns',
  draft: 'Current draft',
  histp: 'Prior Phase 4 review turns',
};

const piecesPresent = PIECE_ORDER
  .map((key) => ({ key, tokens: bundle.promptPieces?.[key] || 0,
                   label: PIECE_LABEL[key] }))
  .filter((p) => p.tokens > 0);  // D3 — only present pieces

if (piecesPresent.length === 0) {
  return <EmptyInputBundle />;
}
return piecesPresent.map((p) => <InputPieceCard key={p.key} piece={p} />);
```

The "not used in this turn: …" footer line is removed entirely.

### 4. Equal-width columns — D5

`NegotiateReviewModal` and `DraftReviewModal` shift to
`gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)'`. Verify the
markdown bodies still render readably at the new ratio (the right
pane's review-cards stack should still fit; if it doesn't, narrow
the card max-width rather than re-bias the columns).

### 5. Model pill layout — D6

Find the timeline-header model-pill render. Today each pill is its
own `<span>` with auto width. New layout:

```jsx
// Spec 0045 D6 — equal-width pills with left/right zones.
function ModelPill({ agent, name, modelId, tokens, cost, status, minWidth }) {
  return (
    <span className="mono" style={{
      display: 'inline-flex',
      alignItems: 'center',
      minWidth,                    // shared across both pills
      padding: '4px 12px',
      border: '1px solid var(--border-1)',
      borderRadius: 999,
      gap: 8,
    }}>
      {/* Left zone — identity, left-aligned */}
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
        <AgentIcon agent={agent} size={14} />
        <span style={{ fontWeight: 600 }}>{name}</span>
        <span style={{ color: 'var(--fg-3)', fontSize: 11 }}>{modelId}</span>
      </span>
      {/* Spacer */}
      <span style={{ flex: 1 }} />
      {/* Right zone — metrics, right-aligned */}
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <span className="num">{tokensFmt}</span>
        <span style={{ color: 'var(--fg-3)' }}>·</span>
        <span className="num">{costFmt}</span>
        <span style={{ color: 'var(--fg-3)' }}>·</span>
        <StatusInline label={status} />
      </span>
    </span>
  );
}
```

`minWidth` is computed by the parent: render both pills' content
into a measurement DOM node, take the max, apply to both. v1 can
hard-code `min-width: 480px` (≈ the wider of the two pills + 20%);
v2 can measure dynamically if hard-coding bites.

### 6. Tests

Frontend-only changes; no Python test infrastructure exists for
JSX rendering. Regression-guard tests in Python for the wire-format
fields the new code reads:

- `tests/ui/test_aggregator_input_bundles.py` extend:
  - per-turn input bundle's `prompt_pieces` dict only contains
    non-zero entries for pieces the orchestrator actually inlined
    (or alternatively: the existing serialiser emits zeros for
    absent pieces and the frontend filters — assert whichever path
    we land on).
  - `bundle.brief` is non-empty for runs whose `brief.md` exists.
- Manual verification on the partner-vetting fixture + a fresh
  test run after deploy.

### 7. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.42.0 → 0.43.0.
- `CHANGELOG.md`: `## [0.43.0]` heading.
- `VERSION_NOTES` entry at the top of `how-it-works.jsx`:
  > **0.43.0 — Full-view shell standardisation + model pill layout.**
  > Tabs on every full-view modal now render in a canonical order
  > (`Content | Input | Web Search | Sources | Files`); tabs without
  > data are hidden entirely. The Input full-view drops the "not
  > used in this turn" footer; absent pieces don't render. The
  > brief is now labelled "User prompt: Brief" and floats to the
  > top of the input bundle. Side-by-side modals (Phase 1 plan-
  > draft, Phase 2 / Phase 4 turn modals) render with equal-width
  > columns. Timeline-header model pills (Claude, GPT) are now
  > equal-width with identity left-aligned and metrics right-
  > aligned.

### 8. Files touched

Frontend:
- `src/dual_research/ui/static/run-detail.jsx` — `TABS_CANON` +
  `sortByCanon`; `DocumentModal`, `NegotiateReviewModal`,
  `DraftReviewModal`, `InputBriefModal` tab-builders; column-width
  CSS; `ModelPill` component; `InputTabContent` rewrite for D3/D4.
- `src/dual_research/ui/static/shared.jsx` — if a `Modal`
  signature change is needed for the canonical-order helper.
- `src/dual_research/ui/static/how-it-works.jsx` — VERSION_NOTES.

Tests:
- `tests/ui/test_aggregator_input_bundles.py` — extend.

Backend:
- No changes.

## Out of scope

- **Critique panel rework** (P2 / P4 / Summary buttons in the
  Critique pane header; filter chip relabeling; uniform button
  design across panels; Summary tab redesign; per-card ghosted
  annotation). Spec 0046.
- **Consumption tab rework** (single-row card with inline expand;
  web-search dedup; total cost). Spec 0046.
- **Phase 4 card cryptic IDs cleanup.** Spec 0046.
- **A real "user prompt" CLI field distinct from the brief.**
  D4's v1 treats the brief as the user prompt. If a future spec
  adds a separate `--prompt` argument that the CLI captures
  alongside the brief file, the label re-points to that.
- **Dynamic pill-width measurement.** v1 hard-codes a shared
  min-width; v2 can measure if needed.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec adds 1-2 wire-
      format regression-guard tests.
- [ ] Manual: open every full-view modal on the partner-vetting
      fixture. Tab order matches `[Content | Input | Web Search |
      Sources | Files]` (any subset of those tabs, but always in
      that order).
- [ ] Manual: a turn whose input bundle didn't use Phase 4 review
      turns (Phase 2 R1) → no "Prior Phase 4 review turns" section
      renders.
- [ ] Manual: the input full-view's first section is now labelled
      "User prompt: Brief" instead of "Brief".
- [ ] Manual: open a Phase 2 turn modal; verify the left and right
      panes are visually equal-width.
- [ ] Manual: timeline header — Claude and GPT pills are visually
      equal-width; logo + name on the left, tokens/cost/status on
      the right; no awkward left-padding from cost strings of
      different lengths.
- [ ] Preview-verified at `localhost:6173`.

## Risks

- **D3's "hide unused" change removes information some users may
  have relied on as a checklist** ("did this turn use the Agreed
  plan?"). Mitigation: the Consumption tab still surfaces per-turn
  piece breakdowns + token usage; the input full-view becomes a
  read-only view of what WAS used, not a checklist of what could
  have been.
- **D5's equal-width columns reduce the markdown body width on
  side-by-side modals.** The longer markdown sections (Phase 4
  converged drafts) wrap more tightly. Mitigation: the modal width
  itself (`width=1300`) is unchanged; only the column ratio shifts.
  Typical content remains readable.
- **D6's hard-coded `min-width` may waste space on small viewports
  if it's tuned for a larger one.** Mitigation: pick a value that
  fits a 1200px viewport comfortably; v2 measures.
- **D7's `Files` vs `Sources` rename may break any code that
  refers to `Files` by id.** Audit usage; in practice the only
  references are inside this spec's own scope.
- **D8's "no counts in tab labels" removes the at-a-glance "this
  tab has 3 things" cue.** Mitigation: tab content shows the
  count in the body header. The `⚠` exception for Web Search
  hallucinations stays.

## Open questions

- Whether to keep the `Web Search ⚠` indicator at the tab-label
  level or move it inside the tab body. v1 keeps it at the tab
  level per D8's exception clause because the user needs to see
  it without clicking. If clicker-fatigue isn't a real concern,
  v2 could fold it into the body.
- Whether the model pill should also expose the per-agent context-
  window remaining (e.g. `345k / 1M`) inline. Currently surfaced
  on the Consumption tab; pulling it up to the pill would compete
  for right-zone space. Defer.

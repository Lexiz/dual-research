---
spec: 0120
title: Turn-modal items panel — provider badge, segment labelling, Claims panel removal
label: new-feature
version-bump: PATCH
status: implemented
target-version: 1.4.1
created: 2026-05-20
pr: ""
---

# Spec 0120 — Turn-modal items panel rework

> Ship bucket: **Composed**
> Depends on: **0119 (badge governance — vocabulary + Chip primitive)**, **0044 D6 (structured-items extraction)**, **0114 (claim kind removal)**
> Complexity: **S–M** (one component cluster, frontend-only, no backend, no migrations).
> Targeted version bump: **PATCH** — visible UI change to one modal surface, no API contract change, applies 0119's already-shipped vocabulary.

## 1. Context

The turn modal's right pane renders structured items (Open Questions, Claims, etc.) extracted from the draft being reviewed. Spec 0044 D6 introduced the extraction; subsequent specs (0042, 0085, 0116) kept the visual rendering essentially unchanged: each item displayed as a `> markdown blockquote` followed by `**bold heading**` followed by a plain paragraph, with no per-segment delineation and no provider attribution on the card.

The audit conducted in conversation 2026-05-20 — and confirmed by a user screenshot of the Claude Phase 2 turn 1 modal — found three specific problems with this panel:

1. **No provider attribution per card.** The panel header reads "OPEN QUESTIONS 5" with no signal of which agent raised each item. The user's complaint: *"when it says 'open questions,' maybe you should mention from whom, by adding a batch."* The data already carries `Item.raiser` (see [`ui/models.py:447`](src/dual_research/ui/models.py)); the UI just doesn't render it.

2. **Card body has no per-segment labels.** Each card renders as `> quote / **bold heading** / paragraph` in raw markdown. To a reader, these three pieces are visually distinct (blockquote bar vs bold weight vs plain text) but semantically uncategorized — what IS the quote? What is the heading? Is the paragraph the question or the rationale? The user's complaint: *"the way that the questions are formatted is a little bit strange. You have a quote sign, then you have something between stars, and then you have a paragraph. Can you please be precise by also adding a batch exactly which one of these means."*

3. **"CLAIMS" panel renders a category that no longer exists.** Per [`contract/categories.py:8`](src/dual_research/contract/categories.py): *"The legacy `claim` kind is gone — the new prompts never ask for it."* The new-protocol parser does not extract claims; the Claims panel on a new-protocol run shows whatever the legacy extraction pipeline happens to surface, which is at best stale and at worst misleading.

The problem is narrow in surface — one component cluster, one modal pane — but real: every user opening a turn modal sees this. Spec 0119 (badge governance) ships the canonical vocabulary and the `<Chip>` primitive this spec applies; this spec is the first application of 0119's rules to a previously-untouched surface and it tests whether the governance generalises beyond timeline + critique pane.

The companion documents:
- **Spec 0119** — `specs/0119-badge-governance.md` — the badge primitive + vocabulary this spec reuses without modification.
- **Ideation mockup** — `/tmp/badge-governance-mockup.html` (iteration 3, 2026-05-20) — the visual reference for the chip palette.
- **User screenshot** — referenced in conversation 2026-05-20; shows the OPEN QUESTIONS / CLAIMS panel as it currently renders.

## 2. Goals

1. **Provider badge on every item card** in the panel, using spec 0119's Provider chip primitive (same component, same brand color, same icon) so the surface reads consistently with the rest of the UI.
2. **Three explicit per-segment labels** on each card: **Anchor** (the quoted reference), **Title** (the one-line claim/question summary), **Rationale** (the elaborating paragraph). Each label is a small caps section header — not a chip — so the body stays visually quiet and the labels feel structural rather than ornamental.
3. **Drop the Claims panel** entirely from new-protocol render paths. Legacy renderer (for pre-0114 runs) is untouched.
4. **Apply spec 0119's category-bubble Chip** to the panel header itself — "Questions" panel header becomes `[Q] Questions  N`, "Disagreements" panel becomes `[D] Disagreements  N`, etc. So the modal's panel headers match the critique pane's filter legend.
5. **Confirm sources widget is unchanged.** If an item in the panel has linked evidence (per spec 0115's `EvidenceRecord`), the existing `SourceRow` rendering is used verbatim — no visual changes. (Explicitly listed because the user called out: *"please verify that the sources are indeed visualised the way that they are shown in this HTML."*)

## 3. Non-goals

- **The chip primitive itself, the canonical vocabulary, or the design-system documentation.** All of that is spec 0119's territory. This spec only APPLIES 0119's rules; it does not modify them.
- **Backend / parser / data-layer changes.** The data already carries everything we need: `Item.raiser`, `Item.anchor_text`, `Item.anchor_type`, `Item.body`. The "Title" segment is extracted from `body` via the same markdown convention agents already use (first bold line is the title; the rest is the rationale). If the parser ever changes the body structure, that's a separate spec.
- **Legacy renderer.** Pre-0114 runs continue to render via the legacy `DraftRightPane` path with Claims panel intact. This spec touches the new-protocol render only.
- **Left pane of the modal.** Spec 0116 already handled that (sub-tab default, PhaseRail removal). This spec is right-pane only.
- **Cross-review (Phase 4) modal differences.** The same component renders Phase 4 review modals; the changes here apply uniformly. No Phase-4-specific branches needed.
- **Per-item click-to-jump-to-brief behavior.** Spec 0044 D6's anchor-jump-to-left-pane is preserved as-is.

## 4. Audit of current rendering

Current code paths in `src/dual_research/ui/static/run-detail.jsx`:

| location | what it renders | spec origin |
|---|---|---|
| `~:4504` `DraftReviewModal` | The whole modal: left pane (draft + sub-tabs) + right pane (structured items strip). | 0085 |
| `~:4604` `DraftRightPane` | Right pane container; switches between Draft body and Web Search sub-tabs. | 0038 + 0044 D6 |
| `~:4518-4540` `reviewItemsFor(run, item)` | Pulls structured items from the run (Phase 1 claims + Phase 2/4 raised items). | 0044 D6 |
| `~:4723-4900` panel renderers | Renders the items as cards inside the right pane. Each card: `> {quote}` + `**{heading}**` + `{body}`. | 0044 D6 |
| `~:3447-3448` | Phase 1/2 panel-kind allow-list still includes `claims`. | 0044 D6 (legacy) |
| `~:3501` `claim` counter | Aggregates claim counts for the strip badge. | 0044 D6 (legacy) |
| `~:3575` `claim: { label: 'claims', tint: 'info' }` | Label map entry for the legacy claim kind. | 0044 D6 (legacy) |
| `~:3599` `'claims' ? 'claim' : …` | Branch translating allow-set keys to UI kind. | 0044 D6 (legacy) |
| `~:6393` `claims: 'Claims'` | UI label for the claims panel header. | unknown (early spec) |
| `~:6413` `claims: 'Show only Claims'` | Tooltip for filter chip. | unknown |
| `~:6706, 6719, 6826, 6879` `claims` references | Various branches in critique explorer / aggregation that mention claim kind. | 0044 D6 |

The "Claims panel" rendering itself lives in the panel-renderer cluster (~:4723-4900). Implementation will trace the exact JSX during the implementation pass.

## 5. Proposed change

### 5.1 — Remove the Claims panel from new-protocol render

In `reviewItemsFor()` and the panel allow-list (`~:3447-3448`), remove `'claims'` from the new-protocol path. Phase 1 still extracts open questions and disagreements (if any); claims are no longer pulled. The aggregator's claim counter (~:3501) becomes a no-op for new-protocol runs and is wrapped in `if (legacyMode)` or removed if the legacy renderer doesn't reach this code.

Detection of new-vs-legacy protocol: `run.protocol === 'deep_research'` (the field already exists; the legacy renderer falls back when absent). All claim-related branches gated on `!run.protocol || run.protocol !== 'deep_research'`.

Strip the kind-label-map entries (~:3575, 6393, 6413) of claim references. The label map becomes:

```js
const KIND_LABELS = {
  question:     'Questions',
  disagreement: 'Disagreements',
  issue:        'Issues',
  comment:      'Comments',
};
// 'claim' key removed entirely.
```

### 5.2 — Provider badge on every item card

The panel renders one card per item. Per spec 0119 § 6.1 ("Provider FIRST"), every card header begins with a Provider chip:

```jsx
<div className="rp-item-card-head">
  <Chip
    tone={item.raiser === 'claude' ? 'claude' : 'gpt'}
    leadingIcon={<AgentIcon agent={item.raiser} />}
    label={agentName(item.raiser)}
  />
  <Chip
    tone={CATEGORY_TONE[item.kind]}
    categoryBubble={CATEGORY_BUBBLE[item.kind]}
    label={CATEGORY_LABEL_SINGULAR[item.kind]}
  />
  {item.raised_round != null && (
    <Chip mono tone="neutral" label={`raised in r${item.raised_round}`} />
  )}
  {item.evidence?.length > 0 && (
    <Chip tone="neutral" label="Sources" value={item.evidence.length} />
  )}
</div>
```

`CATEGORY_TONE`, `CATEGORY_BUBBLE`, `CATEGORY_LABEL_SINGULAR` are exported from spec 0119's chip module — no new constants invented locally.

### 5.3 — Per-segment labelling of card body

The card body is restructured from raw markdown into three labelled sections:

```jsx
<div className="rp-item-card-body">
  {item.anchor_text && (
    <section className="rp-segment">
      <div className="rp-segment-label">Anchored to {otherAgentName(item.raiser)}'s draft</div>
      <blockquote className="rp-anchor">{item.anchor_text}</blockquote>
    </section>
  )}
  <section className="rp-segment">
    <div className="rp-segment-label">Title</div>
    <div className="rp-title">{extractTitle(item.body)}</div>
  </section>
  <section className="rp-segment">
    <div className="rp-segment-label">Rationale</div>
    <div className="rp-rationale">{extractRationale(item.body)}</div>
  </section>
</div>
```

Where:

- **Anchored to <agent>** — the small-caps label above the `> quoted` block. Only rendered if `item.anchor_text` is non-empty (some items don't have an anchor).
- **Title** — the small-caps label above the bold heading. Sourced from the first bold-stars line in `item.body` (the canonical convention; agents emit `**Title here**` as the first content line).
- **Rationale** — the small-caps label above the elaborating paragraph(s). Everything after the title line.

`.rp-segment-label` is the same visual treatment as `.crit-section-title` used elsewhere (~:`crit-section-title` in `components.css`): small caps, 11 px, letter-spacing 0.06 em, color `--fg-3`. Reusing the existing class keeps the visual language consistent.

#### 5.3.1 — Title / Rationale extraction

A small pure helper splits `item.body` into `{title, rationale}`:

```js
function splitTitleAndRationale(body) {
  // Convention: first non-empty line wrapped in `**…**` is the title.
  // Everything after is rationale.
  const lines = body.split('\n');
  let i = 0;
  while (i < lines.length && lines[i].trim() === '') i++;
  if (i < lines.length && /^\s*\*\*.+\*\*\s*$/.test(lines[i])) {
    const title = lines[i].trim().replace(/^\*\*|\*\*$/g, '').trim();
    const rationale = lines.slice(i + 1).join('\n').trim();
    return { title, rationale };
  }
  // No bold-stars title — return the whole body as rationale.
  return { title: '', rationale: body.trim() };
}
```

Lives in a small helper module — likely `src/dual_research/ui/static/item-body.js` (new tiny file).

Fallback behaviour: when no title is parseable, the "Title" section is omitted; the "Rationale" section renders the full body. Robust against parser variations.

### 5.4 — Panel header

The panel header itself (`OPEN QUESTIONS 5`, `DISAGREEMENTS 3`, etc.) uses spec 0119's category-filter chip primitive:

```jsx
<div className="rp-panel-head">
  <Chip
    tone={CATEGORY_TONE[panelKind]}
    categoryBubble={CATEGORY_BUBBLE[panelKind]}
    label={CATEGORY_LABEL_PLURAL[panelKind]}
    value={panelCount}
  />
</div>
```

Replaces the current heading text. Visual result: `[Q] Questions  5` — identical to the critique pane's filter chip for that category, satisfying the uniformity invariant in 0119 § 9 ("the filter row IS the legend; the same chip appears anywhere a category is named").

### 5.5 — Sources, preserved

Per § 2 goal 5 and per the user's explicit confirmation that the sources visualisation in the iteration-3 mockup is the intended form, the existing `SourceRow` rendering (spec 0115 step 3) is used verbatim inside the card when `item.evidence.length > 0`:

```jsx
{item.evidence.length > 0 && (
  <section className="rp-segment">
    <div className="rp-segment-label">Sources ({item.evidence.length})</div>
    {item.evidence.map((rec, i) => <SourceRow key={i} record={rec} />)}
  </section>
)}
```

`SourceRow` is unchanged from `run-detail.jsx:1074` onward (its v2 form per spec 0115).

## 6. Files touched (exhaustive list)

| file | change | sections |
|---|---|---|
| `src/dual_research/ui/static/run-detail.jsx` | gut + rewrite the panel-renderer cluster (~:4723-4900); update label map (~:3575, 6393, 6413); remove `claim` branches (~:3447-3448, 3501, 3599, 6706, 6719, 6826, 6879); update `reviewItemsFor()` ~:4518; new `rp-item-card-*` and `rp-segment-*` JSX | §5.1-5.4 |
| `src/dual_research/ui/static/item-body.js` (new) | `splitTitleAndRationale(body)` helper per §5.3.1 | §5.3 |
| `src/dual_research/ui/static/components.css` | new classes `.rp-panel-head`, `.rp-item-card-head`, `.rp-item-card-body`, `.rp-segment`, `.rp-segment-label`, `.rp-anchor`, `.rp-title`, `.rp-rationale` — most reuse existing tokens; only `.rp-segment-label` is alias for `.crit-section-title` styles | §5.3 |
| `src/dual_research/ui/static/icons.jsx` | no changes; existing icons sufficient | — |
| `CHANGELOG.md` | entry under `[Unreleased]` | — |
| `src/dual_research/__init__.py` | version bump to `1.4.1` at PR-merge time | — |
| `src/dual_research/ui/static/index.html` | static cache-bust bump at PR-merge time | — |

No backend files. No `pyproject.toml`. No migrations. No new dependencies. No new icons.

## 7. Acceptance criteria

- [ ] Every item card in the turn-modal right pane begins with a Provider chip whose tone matches `item.raiser` (DOM probe: `.rp-item-card-head > .chip:first-child[class*="t-claude"], .rp-item-card-head > .chip:first-child[class*="t-gpt"]` matches every card).
- [ ] The Claims panel does not render on any new-protocol run (DOM: `document.querySelectorAll('[data-panel-kind="claim"]').length === 0` when `run.protocol === 'deep_research'`).
- [ ] Every item card with `item.anchor_text` renders an "Anchored to <agent>'s draft" small-caps label above the blockquote.
- [ ] Every item card body renders a "Title" small-caps label above the bold heading (when parseable) and a "Rationale" small-caps label above the elaborating text.
- [ ] When `item.evidence.length > 0`, the card renders a "Sources (N)" segment containing the unchanged `<SourceRow>` components — `getComputedStyle(.src-row).borderRadius === '4px'` (matches the spec 0115 SourceRow CSS).
- [ ] The panel header for "Questions" renders as a `[Q] Questions  N` Chip — visually identical to the critique pane's filter chip for Questions (computed background + leading-bubble shape + tone identical).
- [ ] `git grep -E "'(Claim|claims)'"` returns 0 hits in `src/dual_research/ui/static/run-detail.jsx` except inside a comment block describing the legacy renderer.
- [ ] `git grep "claim" src/dual_research/ui/static/run-detail.jsx | grep -v '//'` returns 0 hits in non-comment code (except inside a `protocol === 'legacy'` branch if one is kept).
- [ ] Manual: open a Phase 2 turn modal on a new-protocol fixture run. The right pane shows Questions and Disagreements panels (no Claims). Each card carries Provider chip + Category chip + raised-in-rN chip + (optional) Sources chip, in that order. Body has Anchor / Title / Rationale labels.
- [ ] Manual: open a Phase 4 turn modal on a new-protocol fixture run. Same structure but with Issues and Comments panels also present.
- [ ] Manual: open a pre-0114 legacy run. The legacy renderer's Open Questions / Claims panels still display correctly via the legacy code path (no regression).
- [ ] `uv run pytest tests/ -q` → green.

## 8. Test plan

- [ ] **Unit — `splitTitleAndRationale(body)`**: returns `{title, rationale}` correctly for:
  - well-formed `**Title**\n\nBody text.` → `{ title: 'Title', rationale: 'Body text.' }`
  - missing title (no leading bold line) → `{ title: '', rationale: '<full body>' }`
  - empty body → `{ title: '', rationale: '' }`
  - title with markdown inside → preserves inner markdown in title
  - multiple bold lines → only the first is treated as title; subsequent bold lines stay in rationale
- [ ] **Snapshot — item card** with full data (Provider, Category, raised-in-rN, Sources, Anchor, Title, Rationale): asserts chip order in header, segment-label presence, sources segment rendering.
- [ ] **Snapshot — item card** without anchor (`anchor_text === ''`): asserts Anchor segment is omitted; rest renders.
- [ ] **Snapshot — item card** without parseable title: asserts Title segment is omitted; Rationale shows full body.
- [ ] **Snapshot — panel header**: `[Q] Questions  5` matches the critique pane's `[Q] Questions  30` legend chip pixel-for-pixel (modulo count).
- [ ] **Regression snapshot — legacy run**: load `runs/<fixture-legacy-run>` and verify legacy renderer's panels render correctly with no changes.
- [ ] **Manual — color/contrast**: small-caps section labels have ≥ 4.5:1 contrast against card background.
- [ ] **Manual — keyboard navigation**: item cards remain keyboard-focusable per spec 0044 D6's anchor-jump behavior (not regressed).
- [ ] **Manual — anchor-jump-to-brief**: clicking an item card still scrolls the left pane to the anchored content (preserves spec 0044 D6).

## 9. Risks

- **Title extraction fragility.** The convention "first bold-stars line is the title" is a soft convention enforced only by the prompt, not the parser. If an agent emits a body without a bold-stars title (e.g., the question text starts directly with prose), the fallback omits the Title segment and renders the full body as Rationale. Mitigation: the fallback is graceful (no broken layout); manual QA on a few fixture runs confirms the convention holds in practice. If it turns out to fail often, a follow-up spec would move title extraction into the parser proper.
- **Claims panel removal breaks legacy navigation.** Pre-0114 runs DO have claims and users may want to navigate them. Mitigation: the legacy renderer is fully preserved (`run.protocol !== 'deep_research'` keeps old code path). Only new-protocol runs lose the Claims panel.
- **Visual density of multiple cards with Anchor + Title + Rationale + Sources.** Each card grows vertically. If a panel has 10+ cards, the right pane becomes scroll-heavy. Mitigation: cards remain individually compact (the labels are small caps, not chips, taking minimal vertical space); the right pane already scrolls. Acceptable.
- **`item.raiser` vs orchestrator vocabulary.** The data uses `"claude"` / `"openai"` (orchestrator vocab) but the UI elsewhere uses `"claude"` / `"gpt"`. Mitigation: `agentName()` helper from spec 0119 handles the translation; spec 0119's Provider chip already maps both vocabularies correctly.
- **Spec 0119 not yet merged.** This spec depends on 0119's Chip primitive being present. Mitigation: 0120 cannot merge until 0119 is on `main`; PR description references the 0119 PR explicitly.

## 10. Out of scope (explicit)

- Spec 0119's primitive itself, vocabulary, or governance rules — that's 0119's territory.
- Backend / contract module / parser changes.
- Migration of legacy run artifacts.
- The left pane of the modal — handled by spec 0116.
- The Web Search sub-tab on the right pane — spec 0038, untouched.
- Anchor-jump-to-brief click behavior — spec 0044 D6, preserved.
- Sources widget visual design — spec 0115, preserved verbatim.
- Run-list page, header chrome, consumption tab chip migration — listed in 0119 § 14 as deferred to future specs.

## 11. Open questions

- **Q1.** Should the "Anchored to <agent>'s draft" label name the agent explicitly, or just say "Anchored to draft"? Default in this spec: name the agent (clearer attribution).
- **Q2.** When `item.anchor_type` is not `'quote'` (e.g., `'block'` or `'section'`), should the Anchor segment use a different label phrasing? Default in this spec: always "Anchored to <agent>'s draft" — implementer to verify the data variants and adjust.
- **Q3.** Should the Sources segment on the item card render the same `SourceRow` as the critique pane (verified identical), or a denser variant for the modal's limited width? Default in this spec: identical (per the user's "I really like how the sources are visualised" confirmation).
- **Q4.** If a Phase 1 draft contains no items (questions or disagreements) on a new-protocol run, the right pane has nothing structured to show — should it render an empty-state message ("No items raised in this draft.") or the prior behavior (draft body fills the right pane)? Default in this spec: render the draft body when no items exist, exactly as before.

## 12. Backend touched?

**no.** Pure frontend.

---
spec: 0087
title: Cross-cutting polish — every remaining gap from the 2026-05-18 tweak-cycle audit
label: refactoring
version-bump: PATCH
status: in-review
target-version: 0.69.11
created: 2026-05-18
pr: ""
---

# Spec 0087 — Cross-cutting polish (final spec from the 3-spec consolidation)

## Context

This is the third and final spec from the 2026-05-18 audit consolidation
plan. Specs **0085** (Agent Input completion + modal vertical space)
and **0086** (Consumption tab rework) shipped their respective major
reworks. Everything else flagged by the audit
([`audits/2026-05-18-tweak-cycle-screenshot-audit.md`](../../dual-research-automation/audits/2026-05-18-tweak-cycle-screenshot-audit.md))
plus three pieces of new user feedback raised during the 0085/0086
review need a home.

The user's explicit ask:

> "I need you to now move to the last bit, which is the third and last
> spec with all the remaining changes that were left. Please carefully
> screen through this thread, understand all the requirements for the
> last spec, make sure that all of it is going to go into it so that
> we don't miss any details from our original analysis file."

This spec covers **22 audit deltas with open gaps** plus **3 new
feedback items**. Most are small (5–20 lines of code each); a few are
structural (PhaseRail rework, critique-pane header rebalancing). All
are grouped here by **surface** so an implementer (or a series of
small PRs against this spec) can pick a coherent slice at a time.

Open gaps as of `main @ 6b1a5a6` (post-0086 deploy):

| # | Delta | Priority in audit | Section |
|---|-------|-------|---------|
| 1 | 12.52 — status pill column-gap, height/font shrink, run-detail pill variant | sooner | § A |
| 2 | 13.22 — re-assertion of 12.52 spacing | sooner | § A |
| 3 | 13.07 — left-cluster tab uniform-width + top breathing-room | sooner | § B |
| 4 | 13.12 — "How it works" rect icon → MDI `help-circle-outline` | sooner | § B |
| 5 | 13.03 — run-list header chip icons + tooltips | later | § C |
| 6 | 14.23 — PhaseRail legibility (green-on-green), anchoring, `<Chip>` migration | sooner | § D |
| 7 | 14.28 — AgentStrip Claude/GPT pill left-edge equalization | sooner | § E |
| 8 | 14.40 — phase-tab chip-primitive migration + tone colors + tooltips | later | § F |
| 9 | 14.45 — critique pane filter strip tooltips | sooner | § F |
|10 | 14.49 — phase header band visual hierarchy + card vertical-density | sooner | § G |
|11 | 14.57 — Agent Input card chip variant unification (`<Pill>` → `<SB>`) | sooner | § H |
|12 | 15.55 — orphan `−N` chips missing trailing noun | nice-to-have | § I |
|13 | 17.39 — split `+1 −1` into 2 chips; `r4` as proper R4 chip; singular inflection | nice-to-have | § I |
|14 | 18.05 — chevron on right side; RESOLVED default-collapsed | nice-to-have | § J |
|15 | 18.47 — `raised by X` chip + BrandMark icons inside agent chips | nice-to-have | § K |
|16 | 19.03 — drop redundant uppercase `RESOLUTION` block; add "in round N" suffix | nice-to-have | § K |
|17 | 19.16 — Question/Disagreement variant byte-identical structurally | nice-to-have | § K |
|18 | 19.36 — Issue metadata footer → chip cluster with BrandMark | nice-to-have | § L |
|19 | 19.41 — Comments default-collapsed; R-round sub-chip in CodeCluster | nice-to-have | § J + § L |
|20 | 19.47 — Comment metadata footer → chip cluster; `[Self-raised]` chip | nice-to-have | § L |
|21 | 20.41 — solid 48 brand-mark variant + per-card description text | nice-to-have | § N |
|22 | 20.46 — `?full=1` URL gate + Accessibility Construction principle | nice-to-have | § N |
|23 | NEW — "Critique" pane heading typography parity with "Timeline" heading | (user-flagged) | § F |
|24 | NEW — Critique filter strip multi-row pile-up restructure | (user-flagged) | § F |
|25 | NEW — Timeline phase-header band full-width consistency | (user-flagged) | § G |

## Proposed change

### § A. Run-list status pill spacing + run-detail header pill variant

Covers deltas **12.52** + **13.22** (both flag the same spacing
complaint — the second is a re-assertion in close-up). Three concrete
items:

1. **Column gap** between the run-list's `<StatusBadge>` and the
   `TOPIC` column needs to grow from ~8 px to ~20 px. Locate the
   run-list grid in
   [`run-list.jsx`](src/dual_research/ui/static/run-list.jsx) — the
   `grid-template-columns` rule for the row grid. Bump the gap
   between STATUS and TOPIC columns by adding `padding-left: 12px`
   to the TOPIC cell OR adjusting the `gap` value in the row's
   `display: grid`.
2. **Pill height/font shrink** — the original 12.52 spec asked for
   `height: 22→20 px` and `font-size: 11→10.5 px`. Apply in
   [`components.css`](src/dual_research/ui/static/components.css)
   `.sb` rule (line 65). Verify against the run-list AND the
   run-detail header to confirm both surfaces inherit.
3. **Run-detail header pill** — the agent-color pill in the
   run-detail header today uses a non-`.sb` variant (a bespoke
   inline-styled element). Migrate the call site in
   [`run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx)
   (search for the per-agent pill near `Phase 2 · 8/6 rounds`) to
   `<SB tone="a"|"b" size="sm">…</SB>` so it inherits the new
   uniform-width + height/font rules along with the run-list.

### § B. Top-chrome tab cluster

Covers **13.07** + **13.12**:

1. **Uniform-width** rule on the left tab cluster (`All runs` /
   `Compare` / `Search`) — pass `variant="solid"` to each `<Tab>` so
   the SPEC-0053 width/height tokens apply. Look in
   [`router.jsx`](src/dual_research/ui/static/router.jsx) or
   wherever the global chrome `<Tab>` instances are declared.
2. **Top breathing-room** — bump the chrome strip's top padding so
   the tabs aren't flush against the viewport top. Add ~6 px to the
   chrome container in `components.css`'s `.app-chrome` rule (or
   equivalent).
3. **"How it works" icon swap** — find the `<Tab>` instance with the
   `How it works` label; replace the leading `<rect>` placeholder
   SVG with `<Mdi name="help-circle-outline" />`. One-line change.

### § C. Run-list header chip icons + tooltips (delta 13.03)

The three header chips (`N runs`, `N running`, `$N.NNNN spent`) ship
with placeholder `<rect>` SVGs. Swap to the spec'd MDI glyphs in
[`run-list.jsx`](src/dual_research/ui/static/run-list.jsx):

- `N runs` → `Mdi name="format-list-bulleted"`
- `N running` → `Mdi name="circle-medium"` (kept pulsing if already
  animated via spec 0023)
- `$N.NNNN spent` — leaves icon alone OR adopt `Mdi name="cash"` per
  the original spec

Add `title=` attributes to all three chips explaining what they count
(e.g. `title="Total runs in this view"`, `title="Currently running
runs"`, `title="Aggregate cost across the visible runs"`).

### § D. PhaseRail rework (delta 14.23)

Three open items on the run-detail left-rail phase indicator:

1. **Drop the green-on-green legibility regression** — the
   `.phase-rail-node.is-completed` (and `.is-current`) labels render
   as muted green text on a green-tinted background. Inspect
   [`components.css`](src/dual_research/ui/static/components.css)
   `.phase-rail-node` rule (~line 742). Either bump the text to
   `--fg-0` (white in dark, dark-ink in light) OR drop the green
   tint on the active state and only keep the `--pr-dot` accent.
2. **Header-to-pill anchoring** — currently the PhaseRail's pills
   are evenly spaced down a column. The original spec asked for
   each pill to anchor on the y-position of its corresponding phase
   header in the timeline. This requires JS measurement: in the
   PhaseRail component, on mount + on scroll, query each
   `[data-phase-id="N"]` header's `getBoundingClientRect().y` and
   set the matching `.phase-rail-node`'s `top` to track it. Throttle
   to `requestAnimationFrame`.
3. **`<Chip>` primitive migration** — replace bespoke
   `.phase-rail-node` DIVs with `<Chip>` primitive instances. The
   chip variants we need: completed (ok tone), current (info tone,
   pulsing), upcoming (muted tone). May require a new
   `<Chip pulsing tone="info">` flag; check
   [`shared.jsx`](src/dual_research/ui/static/shared.jsx)'s `<Chip>`
   API.

### § E. AgentStrip equal-width pills (delta 14.28)

The user wants both Claude and GPT pills in the run-detail header to
have the SAME outer width (left-edge equalization), regardless of
agent-name string length. Today the pills self-size to content;
"gpt-5.5" produces a 37 px narrower pill than "claude-sonnet-4-6".

Fix in
[`components.css`](src/dual_research/ui/static/components.css)
`.as` rule (~line 162): make `.as-group` a `display: grid` with
`grid-template-columns: 1fr 1fr` so both child pills get the same
column width. Add `width: 100%` on `.as.is-a` and `.as.is-b` inside
the group. Verify no regression on the Compare tab (which renders
two AgentStrip groups side-by-side).

### § F. Critique pane header + filter strip (NEW user feedback + 14.40 + 14.45)

This is the most user-visible item in this spec — the user has flagged
this twice and explicitly asked for it to be addressed here. Three
coupled problems on the Critique pane's top band (right column of
the run-detail page):

1. **Heading typography mismatch.** The left pane's "Timeline · N
   artifacts" renders at `font-size: 14px; font-weight: 600;
   color: var(--fg-0)`. The right pane's "Critique" renders at
   `font-size: 11.5px; font-weight: 500; color: var(--fg-3)` — by
   design today, because the `PaneHeader` component
   ([`run-detail.jsx:2395`](src/dual_research/ui/static/run-detail.jsx:2395))
   demotes the title when a `left` slot is provided (which Critique
   uses for its phase-tab navigation). The user reads this as
   inconsistent typography. **Fix**: drop the conditional in
   `PaneHeader`. Title always renders at 14/600/`--fg-0`,
   regardless of whether `left` is provided. The phase-tab
   navigation gets a new home (see item 2).

2. **Filter-strip pile-up.** Today the Critique pane's chrome row
   is asked to hold three things on one line:
   (a) title + count chip,
   (b) phase-scope navigation (`P2 Negotiate · 24 questions ·
       9 disagreements` + `P4 Review` + `Σ Summary`),
   (c) the kind-filter chip strip (`All · Questions · Disagreements
       · Claims`) + the secondary agent/status filter strip
       (`All · Claude · GPT · All · Open · Resolved · Drift`).
   When they don't fit, they pile up vertically and visually
   "stretch" the heading band, breaking the left/right parity with
   the Timeline pane. **Fix**: restructure the right pane's chrome
   into TWO horizontal strips:
   - **Top strip** (height matches Timeline pane = 52 px): just
     `Critique` title + count chip on the left; aggregate stats
     (`33 introduced · 0 open · 21 resolved · ⚠ 1 drift`) on the
     right.
   - **Below the top strip** (separate row, not piled into the
     header): the phase-scope tab group (`P2 Negotiate / P4 Review
     / Σ Summary`). One single horizontal row, left-aligned
     under the title.
   - **Below the phase-scope row** (another separate row): the
     kind-filter + agent/status filter strips, **right-aligned**
     (not center) so they sit under the aggregate-stats column. If
     they still wrap on narrow viewports, wrap them naturally with
     `flex-wrap: wrap` and `justify-content: flex-end`.
   Net effect: the title bar reads visually identical to the
   Timeline pane's title bar (same height, same typography), and
   the filter chips live in their own controlled rows below.

3. **Filter chip tooltips** (14.45). Each chip in the kind /
   agent / status strips should carry a `title=` attribute
   describing what it filters in / out (e.g.
   `title="Show only questions"`,
   `title="Show only items raised by Claude"`,
   `title="Show items that have been resolved"`). This is the
   single remaining gap from the 14.45 audit verdict.

4. **Phase-tab chip-primitive migration** (14.40). The phase-scope
   tabs (`P2 Negotiate · 24 questions · 9 disagreements`) currently
   render their inner stats as plain text. The 14.40 verdict
   flagged that they should use `<Chip>` primitives with tone-tinted
   backgrounds (info-tone on questions, warn-tone on
   disagreements) + leading icons. After the restructure in item 2,
   the phase-scope tabs have a dedicated row — wider — so the
   chip-cluster migration becomes natural. Migrate the inner stats
   inside each phase-tab from `<span>N questions</span>` to
   `<Chip tone="info" leadingIcon="comment-question">{n} questions</Chip>`
   patterns. Tooltips on hover.

### § G. Timeline phase-header band (delta 14.49 + NEW user feedback)

Two related items:

1. **Phase-header band visual hierarchy (14.49)**. The current
   collapsed Timeline phase-header band renders as a narrow,
   rounded compact pill **inside** the row content width. The
   original spec asked for a band that:
   - Uses `--bg-2` as its background (already mostly done — verify
     in [`components.css`](src/dual_research/ui/static/components.css)
     `.cs-header` rule).
   - Has top + bottom 1 px borders in `--border-2`.
   - Extends **6 px beyond** the rows it heads — i.e., the band's
     left and right edges sit 6 px outside the row content area.
2. **Full-width consistency across phases** (NEW user feedback).
   The user screenshot shows phase headers rendering at
   **different widths** in the collapsed state — PHASE 0 narrower
   than PHASE 2 — because each band sizes to its content. Fix:
   apply `display: block` + `width: 100%` (or `display: flex;
   align-self: stretch`) on the `.cs-header` rule so every phase
   header band spans the same full content width regardless of
   its label length. After this fix all five phase-header bands
   sit at identical left/right x-positions.

Plus the deferred half from 14.49:

3. **Card vertical-density reduction**. Artifact cards in the
   timeline are currently ~58 px tall; the original spec asked for
   ~32 px to compress the timeline and let users scan more rows at
   once. Adjust the `.timeline-card` padding/min-height rules in
   `components.css`. Verify on partner-vetting `3a4a` — 29 cards
   total — that the timeline scrolls noticeably less after the
   change.

### § H. Card-chip variant unification (delta 14.57)

The Agent Input card's status chip uses the legacy bordered-outline
`<Pill>` variant (gray), while the Claude / GPT cards' chips use the
new `<SB tone="ok">` rounded-pill variant (green). The audit verdict:
single-line fix at the Agent Input card render site. Find the
`<Pill>` instance in
[`run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) on the
Phase 0 Agent Input card and replace with `<SB tone="ok" size="sm">…</SB>`
matching the sibling cards.

### § I. Chip vocabulary polish (deltas 15.55 + 17.39)

Three small inflection / split-chip / round-chip cleanups on the
timeline card stats clusters. The helper that produces stats-chip
labels lives near `toneFromColor` in
[`run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) (or
the chip-generation helper from spec 0067 — `statsChipLabel`).

1. **Orphan `−N` chips need their noun** (15.55). Today a few GPT
   rows render bare `−5` / `−6` chips with no trailing word
   (decrement-only mixed-action cases). Fix: always emit the noun,
   so `−5` becomes `−5 prior claims`, `−6` becomes `−6 prior
   issues`. The spec-0086-vintage helper already supports this
   shape; the issue is that some call-sites pass the kind argument
   inconsistently.
2. **Split mixed `+1 −1` chips into two** (17.39). Today
   `+1 issues −1` renders as ONE warn-toned chip. Spec calls for
   two chips: `[+1 issue]` (info tone) + `[−1 prior issue]` (ok
   tone, muted). Modify the helper to emit two chips when both
   raised and resolved counts are non-zero in the same turn.
3. **Render `r4` as a proper `R4` chip** (17.39). Today `r4`
   renders as bare lowercase text without a chip border. Fix: emit
   `<Chip mono compact tone="neutral">R4</Chip>` or
   `<Chip mono compact tone="neutral">round 4</Chip>` (the
   17.39 spec preferred the compact `R4`).
4. **Singular inflection bug** (17.39). `+1 issues` violates the
   `count === 1 ? noun : noun + 's'` rule from 15.55's fix-spec.
   The mixed-chip merger from item 2 above accidentally drops the
   inflection when count = 1. Fix in the helper: every
   chip-emitter uses the singular form when count is 1.

### § J. CollapsibleSection chrome (deltas 18.05 + 19.41 defaults)

1. **Chevron on the right.** Today the chevron renders on the LEFT
   of the section header label. The 18.05 fix-spec called for it
   on the RIGHT. In
   [`shared.jsx`](src/dual_research/ui/static/shared.jsx)'s
   `<CollapsibleSection>` component, swap the chevron's position
   in the `.cs-header` flex order. (Today: `<Chevron /><Label />`
   with `.cs-chevron` margin-right; change to `<Label /><spacer
   flex: 1><Chevron />`.)
2. **RESOLVED default-collapsed** (18.05). Today the
   `Resolved / answered` section in the critique pane is open by
   default. Find its `<CollapsibleSection>` instance and pass
   `defaultOpen={false}`.
3. **Comments default-collapsed** (19.41). Same fix, applied to
   the Phase 4 `Comments` section's `<CollapsibleSection>` —
   `defaultOpen={false}`.

### § K. Disagreement chips + detail view (deltas 18.47 + 19.03 + 19.16)

Three items affecting the Disagreement list and the expanded
detail view:

1. **`raised by X` chip** (18.47). Today resolved disagreement rows
   render as `Disagreement NN · [conceded by GPT] · v1 scope`.
   The 18.47 spec called for a chip PAIR: `[raised by Claude] +
   [conceded by GPT]` (with the raised-by chip carrying the
   originator's brand-mark). Add the chip in the row builder for
   `phase === 2 && resolved` (and the same for unresolved
   `[open] + [raised by X]` cases, if data is available).
2. **BrandMark inside agent attribution chips** (18.47). Today
   "conceded by GPT" / "conceded by Claude" / "both aligned" pills
   render as plain text. Each should carry the appropriate
   BrandMark glyph (claude burst / openai knot) as a 12 px leading
   icon: `<Chip><BrandMark name="claude" size={12}/> conceded by
   Claude</Chip>`. Apply uniformly to the row pair AND to the
   detail view's resolution footer.
3. **Drop the redundant uppercase `RESOLUTION` block from
   disagreement detail** (19.03 + 19.16). Today the disagreement
   detail view (when expanded) renders the QuestionThread turn
   cards followed by a `✓ conceded by GPT` footer — AND THEN an
   extra uppercase `RESOLUTION` block at the bottom that duplicates
   the converged-text from the last conceded turn. The 19.03 fix
   asked to drop this block; 19.16 confirmed the asymmetry (the
   Question variant has no such block). Remove the
   `<ResolutionBlock>` / `<UppercaseSection title="RESOLUTION">`
   render in the disagreement-detail render path.
4. **"in round N" resolution-footer suffix** (19.03). Change the
   resolution footer from `✓ conceded by GPT` to
   `✓ conceded by GPT in round 3` (where the round number is the
   `resolvedRound` of the disagreement, available on the data
   model). Mirror the format the Question variant already uses
   (`✓ Answered by GPT in round 3` per 19.16).

### § L. Critique-card metadata footers (deltas 19.36 + 19.47 + 19.41 R-round)

1. **Issue metadata footer → chip cluster** (19.36). Today an
   expanded Issue card's metadata line reads
   `flagged by Claude · first seen R1 · last seen R2` as a
   single muted-gray punctuation-separated text line. Replace with
   a chip cluster:
   - `<Chip tone="info" leadingIcon={<BrandMark name="claude"
     size={12}/>}>flagged by Claude</Chip>`
   - `<Chip tone="neutral" mono>first seen R1</Chip>`
   - `<Chip tone="neutral" mono>last seen R2</Chip>`
2. **Comment metadata footer → chip cluster** (19.47). Same fix
   for the Comment card's `noted by Claude · R1` footer:
   - `<Chip tone="info" leadingIcon={<BrandMark name="claude"
     size={12}/>}>noted by Claude</Chip>`
   - `<Chip tone="neutral" mono>R1</Chip>`
3. **Promote `[Self-raised]` to a distinct chip** (19.47). Today
   the Comment topic prefix `[Self-raised]` is literal text inside
   the topic line AND inside the body's bold title. Add a
   `<Chip tone="muted">self-raised</Chip>` adjacent to the kind
   chip in the Comment header strip; drop the literal `[Self-raised]`
   prefix from both the topic line and the body's title text.
4. **R-round sub-chip in the CodeCluster** (19.41). The
   CodeCluster on every Issue / Comment header today renders
   `[Issue 01] [Claude with BrandMark] [resolved]`. The 19.41 spec
   asked for an additional `R<n>` sub-chip representing the round
   in which the item was raised (e.g. `[R1]` after the agent
   chip). Add this in the `<CodeCluster>` primitive output for
   items that carry a `roundFirstSeen` field. Items without a
   round (Phase 0 / 1 items) skip the sub-chip.

### § M. (deferred) Children of § E + § F — Compare tab + AgentStrip group container

After § E's grid-stretch, audit any `<AgentStripGroup>` usage on
the Compare tab to confirm it works there too. Not a separate item
but a regression-check.

### § N. Design Language page polish (deltas 20.41 + 20.46)

Three small DNA-page fixes on
[`design-language.jsx`](src/dual_research/ui/static/design-language.jsx):

1. **`solid 48` brand-mark variant** (20.41). The current Brand
   marks section renders sizes `32 / 24 / 16 / ghost 16 / ghost 12`.
   The briefing had a larger `solid 48` size as the leftmost
   variant. Add it back — the `<BrandMark size={48}>` invocation
   exists in `window.BRAND_SVGS` already; just include it in the
   row.
2. **Description text under glyph row** (20.41). The briefing
   showed a one-line description below each brand-mark card:
   "Used everywhere the OpenAI agent is identified — list rows,
   run-detail headers, timeline cards, error rows, and the
   disagreement explorer." Restore it on both cards (Claude +
   OpenAI) with appropriate per-agent copy.
3. **`?full=1` URL gate to FullReference** (20.46). Today
   `#/language` renders only the DNA one-pager; the long-form
   reference document is gone. Either (a) bring back the
   comprehensive sections behind `?full=1`, OR (b) formally
   document the decision to drop the full reference. The
   pragmatic choice is (b): add a small footer to the DNA page —
   "_Detailed reference moved to spec docs; see
   `docs/design-system.md` for the long-form._" — and create that
   markdown file if it doesn't exist, copying the previous
   long-form content out of git history.
4. **Accessibility Construction principle** (20.46). The
   Construction section today lists three principles ("Tokens
   only colors", "Full-word vocabulary", "Brand fidelity"). Add
   a fourth bullet:
   - **Accessibility** — `:focus-visible` ring on every
     interactive primitive; `prefers-reduced-motion` honored on
     every animation; semantic ARIA where the markup needs it.

## Out of scope

- **Spec 0085 / 0086 follow-ups** that were already addressed in
  those PRs (system-prompt fallback, modal vertical space, top-row
  compact-bar removal in Consumption, phase-name-above-row).
- **New runs / orchestrator-side changes** — every change in this
  spec is frontend-only or static-asset (CSS).
- **i18n / non-English vocabulary** — singular/plural inflection
  rules are English-only by spec.
- **Compare tab polish** beyond the regression-check in § M. If
  Compare needs its own follow-up, that's a separate spec.
- **Dark-theme verification** — covered by the existing global
  theme regression process, not item-by-item in this spec.
- **Search palette tab indexing** — out of scope as documented in
  spec 0085. The palette is nav-level; adding tab-level indexing
  is a separate feature.

## Test plan

### Unit tests

- [ ] **`statsChipLabel` inflection** — add a test in
  [`tests/ui/`](tests/ui/) (or wherever the chip-generation helper
  is exercised) covering:
  - count=1 → singular ("+1 issue", not "+1 issues")
  - count=0 → omit the chip (or render `—` per current behaviour)
  - mixed-action (raised + resolved): two chips, not one merged
  - resolved chip carries the `prior` prefix when applicable
- [ ] **`buildResolutionFooter`** — small test in the disagreement
  data layer asserting the format `✓ conceded by {agent} in round
  {N}` matches the Question variant's format byte-for-byte (per
  19.16 cross-check).

### JSX regression

- [ ] `pytest tests/test_ui_jsx_syntax.py` — green after every
  section's edits.

### Manual verification (always at **2200×1300** viewport per the
session's resolution policy)

Group by surface for batched verification:

**Run-list + chrome (§ A + § B + § C)**
- [ ] Run-list row: STATUS pill ends, then ~20 px gap, then TOPIC
  starts. Pill height now 20 px (was 22), font 10.5 px (was 11).
- [ ] Run-detail header: agent-color pill renders via `.sb`,
  inherits the same size + spacing rules.
- [ ] Top chrome: `All runs` / `Compare` / `Search` tabs all
  ≥110 px wide; tabs sit ~6 px below viewport top (not flush).
- [ ] `How it works` tab: real help icon (not square outline).
- [ ] Run-list header chips: real icons (`format-list-bulleted`
  for runs, `circle-medium` for running, optional `cash` for
  spent); hover shows tooltip.

**PhaseRail (§ D)**
- [ ] No green-on-green text. Active phase label is legible.
- [ ] On scroll, each PhaseRail pill tracks the y-position of its
  phase header in the timeline (anchoring works).
- [ ] DOM inspection: PhaseRail nodes are `<Chip>` instances, not
  bespoke `<div>.phase-rail-node`.

**AgentStrip (§ E)**
- [ ] Claude pill and GPT pill have identical OUTER widths (both
  left edges align, both right edges align). Confirmed at viewport
  2000+ px so the truncation case doesn't hide a regression.

**Critique pane chrome (§ F)**
- [ ] "Critique" heading renders at the same font-size, weight, and
  color as "Timeline" — open both panes side by side and confirm.
- [ ] Critique pane header is a SINGLE 52 px row carrying just
  title + count + aggregate stats; no multi-row pile-up.
- [ ] Phase-scope tab group lives in its own row below the title.
- [ ] Kind-filter + agent/status-filter strips sit in their own
  row(s) below the phase-scope tabs, RIGHT-ALIGNED (not center).
- [ ] Every filter chip carries a tooltip on hover.
- [ ] Phase-scope tabs' inner stats use `<Chip>` primitives with
  tone-tinted backgrounds (info on questions, warn on
  disagreements).

**Timeline phase-header band (§ G)**
- [ ] All five phase-header bands (P0 / P1 / P2 / P3 / P4) render
  at the same left/right x in their collapsed state. No ragged
  left-edge.
- [ ] Each band has `--bg-2` background + 1 px top/bottom borders
  + extends 6 px beyond the row content area.
- [ ] Timeline cards are noticeably shorter (~32 px vs ~58 px);
  visible row-count on a 1300 px viewport is ~50% higher than
  before.

**Card-chip variant (§ H)**
- [ ] Agent Input card on Phase 0: chip renders via `<SB tone="ok"
  size="sm">` (rounded green pill), matching the Claude / GPT
  brief-critique cards.

**Chip vocabulary (§ I)**
- [ ] No bare `−N` chips without a trailing noun on any timeline
  card.
- [ ] Any row with mixed-action stats shows TWO chips
  (`[+1 issue] [−1 prior issue]`) — not a merged single chip.
- [ ] `R4` round chip is bordered, mono, uppercase — not bare
  lowercase text.
- [ ] No `+1 issues` (plural for count=1) anywhere.

**CollapsibleSection chrome (§ J)**
- [ ] Every collapsible-section chevron renders on the RIGHT side
  of the header label.
- [ ] `Resolved / answered` (critique pane) defaults to COLLAPSED
  on page load.
- [ ] `Comments` (Phase 4 critique pane) defaults to COLLAPSED on
  page load.

**Disagreement chips + detail (§ K)**
- [ ] Every resolved disagreement row shows `[raised by X]` +
  `[conceded by Y]` chip pair. Each agent chip carries the
  BrandMark glyph.
- [ ] Expanded disagreement detail: no uppercase RESOLUTION block
  at the bottom. Resolution footer reads `✓ conceded by X in
  round N`.
- [ ] DOM check: Question detail view + Disagreement detail view
  share the same `<QuestionThread>` outer structure; no
  Disagreement-only extra blocks.

**Critique-card metadata footers (§ L)**
- [ ] Expanded Issue card: metadata footer is a chip cluster, not
  a middot-separated text line. First chip carries a BrandMark.
- [ ] Expanded Comment card: same chip-cluster footer.
- [ ] Comment header: `[self-raised]` chip visible adjacent to the
  kind chip when applicable; no literal `[Self-raised]` prefix in
  the topic line or body title.
- [ ] CodeCluster on Issue / Comment headers includes an `R<n>`
  sub-chip for items with `roundFirstSeen`.

**Design Language page (§ N)**
- [ ] Brand marks section shows sizes `48 / 32 / 24 / 16 / ghost
  16 / ghost 12` (solid 48 restored).
- [ ] Each brand-mark card has a one-line description below the
  glyph row.
- [ ] DNA page footer references the spec docs / long-form
  reference location.
- [ ] Construction section has 4 bullets including the new
  Accessibility principle.

## Risks

- **Scope size**. This is 14 sections. Land the high-priority
  sections first (§ A, B, F, G, H per the audit's "sooner"
  tagging) — the rest can ship in follow-up PRs against this same
  spec without re-scoping.
- **PhaseRail anchoring (§ D)** is the trickiest item; touches
  scroll-position tracking. Risk of jitter on fast scrolls.
  Mitigation: `requestAnimationFrame` throttle + `IntersectionObserver`
  as primary signal rather than scroll listener.
- **Critique-pane restructure (§ F)** changes the heights of the
  right pane's chrome. Verify that the run-detail two-pane layout
  doesn't break — the panes are independent flex columns with
  their own scroll containers, so a height bump on the right's
  chrome should be absorbed without affecting the left.
- **Variant unification (§ H)** — confirm there are no other
  `<Pill>` callsites elsewhere that need to migrate. The 14.57
  audit verdict said the orphan was at the Agent Input card
  specifically.
- **Chip vocabulary helper (§ I)** — touch the central helper
  carefully; many timeline-card rows feed through it. Have unit
  tests in place before refactoring.
- **`?full=1` decision (§ N)** — taking option (b) (document the
  decision rather than restore the long-form) is the pragmatic
  call. If the user pushes back during review, switch to (a) and
  copy the long-form sections back into `<FullReference>`.

## Open questions

- **PhaseRail anchoring** — should the rail be sticky-positioned
  (always visible during scroll) or scroll with the page? The 14.23
  audit verdict suggested the spec wanted anchoring; recommendation:
  sticky-positioned for the rail container, with each pill
  tracking its phase header's y-offset.
- **`R<n>` sub-chip in CodeCluster (§ L item 4)** — the audit
  flagged that rounds surface today via the trailing `ghosted N
  rounds` warn chip on un-resolved items. Recommendation: add the
  `[R<n>]` sub-chip ONLY when the item has a stable
  `roundFirstSeen` field AND the row isn't ghosted (the ghosted
  chip already carries round info). Avoid double-display.
- **Card vertical-density target (§ G item 3)** — the audit cited
  ~32 px as the spec'd height. Verify on a real run that this
  doesn't crowd the card content (chips + summary line). If 32 px
  is too tight, settle on a number in the 36–40 px range with the
  user during implementation.

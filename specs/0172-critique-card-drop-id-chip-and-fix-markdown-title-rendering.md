---
kind: dev
spec: "0172"
slug: critique-card-drop-id-chip-and-fix-markdown-title-rendering
title: "Fix: critique cards render literal ** markdown and re-show cryptic compound IDs"
type: bug
label: bug
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 3
depends_on: []
complexity: S
created: 2026-05-22
queued_at: "2026-05-22T20:30:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: notion-specs-2205-claude-bug-2
promoted_from_draft: ""
---

# Spec 0172 — Fix: critique cards render literal `**` markdown and re-show cryptic compound IDs

> **Type:** bug  |  **Severity:** P1  |  **Affects:** v1.29.0 (current main). Every critique card on every run with critique items — visible on the Critique pane.
> **Bump:** PATCH — bug fix
> **Evidence:** Product-owner regression report on Notion page `Specs 2205 (AL)` Issue 2 → restated in `Specs 2205 (Claude)` Bug 2. Two distinct symptoms: literal `**` characters at the top of Issue card bodies, and cryptic compound IDs (e.g. `I-DEQ-PLAN-C-01`) shown as chips in both the card header and inside D/Q/I card bodies. Both regressions were introduced by spec 0151 §3.4.3 ("ItemCard rewritten so each kind matches its design-system reference") and were planned for fix in spec 0168 §2.3 + §2.7, but those sub-sections were **deferred** when spec 0168 shipped only its §2.1 (M3 frame catch-up) on [PR #191](https://github.com/Lexiz/dual-research/pull/191) (commit `f5ea4d4`).

---

## 1. Reproduction

**Environment:** dual-research UI at HEAD = `8042a40` (deployed v1.29.0). Any run with at least one card of each critique kind (Issue, Question, Disagreement, Comment). The anchor run `20260521-010637-dvs-backend-language-choice` has all four.

**Steps:**

1. Open the run-detail page on a run with critique items.
2. Navigate to the Critique pane.
3. Scroll through the cards in both collapsed and expanded states.

**Expected:** Card chrome matches the design-system reference screenshots `design-system/notion-issues/screenshots/07-question-card-duplicate.png`, `08-disagreement-card.png`, `09-issue-card.png`, `10-comments-card.png`. No literal `**` characters visible anywhere on a card. No compound IDs (e.g. `I-DEQ-PLAN-C-01`, `Q-…`, `D-…`, `C-…`) shown to the user — the kind / agent / round signals already surface through their existing chips (kind label, state chip, per-turn agent badge, round chip).

**Actual:**

- Every critique card header shows a `<code>{item.id}</code>` chip rendering the raw compound ID as the first chip in the head row.
- Issue cards render literal `**Title**` at the top of their body: the first line of `item.body` is split off and rendered through a plain `<span>` rather than through the project's `<Markdown>` component, so the bold delimiters appear as text.
- Disagreement and Question card bodies repeat the same compound ID via a `__sid` `<code>` element inside the body meta row — a *second* surface of the same noisy identifier per card.
- Issue card bodies show a `__sid` short-code (`I-N` style derived from `parseCodeId`) as a `<strong>` element — a *third* cryptic identifier adding noise.

## 2. Root cause hypothesis

Four code sites in [`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) introduced by spec 0151 §3.4.3:

1. [`run-detail.jsx:1787`](src/dual_research/ui/static/run-detail.jsx) — `<span className="md-chip md-chip--sm"><code>{item.id}</code></span>` is the first chip rendered inside `.item-card__head`. Surfaces the compound ID in the card header.
2. [`run-detail.jsx:1542`](src/dual_research/ui/static/run-detail.jsx) — `<code className="item-card__sid">{item.id}</code>` inside `.item-card__bmeta` for Disagreement / Question bodies. Second surface of the same compound ID.
3. [`run-detail.jsx:1602`](src/dual_research/ui/static/run-detail.jsx) — `<strong className="item-card__sid">{shortCode}</strong>` inside Issue body title row. Renders a derived short-code that the product owner has explicitly said is not wanted.
4. [`run-detail.jsx:1586–1605`](src/dual_research/ui/static/run-detail.jsx) — `ItemCardIssueBody` splits `item.body` on `\n`, treats `lines[0]` as the title, and renders it as plain text inside `<span className="item-card__title">{titleLine}</span>`. When the upstream body is `**Title**\n\nbody…`, the `**` delimiters appear verbatim because there is no Markdown render of that line.

Spec 0168 §2.3 ("Card head rebuild") explicitly called out the chip drop: "ID chip + sources chip — dropped (drift 3.D). The ID chip is removed from the card head." Spec 0168 §2.7 ("Expanded view — `.item-card__lifecycle` layout") would have retired `ItemCardIssueBody` entirely in favour of a quoted blockquote (Markdown-rendered). Both sub-sections were planned to fix Bug 2's two symptoms together — but spec 0168 deferred §2.2 through §2.9, shipping only §2.1 (M3 frame catch-up). The four sites above are the unfixed surface area of that deferral.

## 3. Fix

Narrow, surgical fixes for the four sites. This spec does **not** attempt the full §2.3 / §2.7 head + lifecycle rebuild from spec 0168 — that broader work belongs in the Bug 4 spec.

1. **Delete the header ID chip** at [`run-detail.jsx:1787`](src/dual_research/ui/static/run-detail.jsx). Remove the entire `<span className="md-chip md-chip--sm"><code>{item.id}</code></span>` line. The `item.id` remains preserved on the `<article>` element's DOM `id` attribute (set elsewhere in `ItemCard`), in the URL hash for deep-linking, and in any cross-reference UI — only the visible head chip is dropped, matching the design-system rule restated in spec 0168 §2.3.

2. **Delete the DQ body `__sid`** at [`run-detail.jsx:1542`](src/dual_research/ui/static/run-detail.jsx). Remove the entire `<code className="item-card__sid">{item.id}</code>` line. The `.item-card__bmeta` row keeps the state chip, the flexible spacer, and the `N turns` count — same anatomy as the design-system reference `08-disagreement-card.png`.

3. **Delete the Issue body `__sid`** at [`run-detail.jsx:1602`](src/dual_research/ui/static/run-detail.jsx). Remove the entire `<strong className="item-card__sid">{shortCode}</strong>` line. Also remove the now-dead `parsed` / `shortCode` derivation at lines 1587–1590.

4. **Replace the title-line plain rendering with a single Markdown render in `ItemCardIssueBody`** ([`run-detail.jsx:1586–1605`](src/dual_research/ui/static/run-detail.jsx)). Drop the `split('\n')` / `titleLine` / `restBody` heuristic. Render the entire `item.body` through `<Markdown text={item.body || ''} />` — the same path Comment cards already use in `ItemCardCommentBody`. Side effect: the bold first line renders as actual `<strong>` via Markdown; no literal `**` remains. The `.item-card__title-row` JSX block is removed; the state chip and meta row composition is preserved alongside the new Markdown render.

After the four edits, verify via repo-grep across [`src/dual_research/ui/static/`](src/dual_research/ui/static/) that `.item-card__sid`, `.item-card__title-row`, `.item-card__title-sep`, and `.item-card__title` CSS classes have no remaining consumers. Any class confirmed dead is removed from both [`src/dual_research/ui/static/components.css`](src/dual_research/ui/static/components.css) and [`design-system/assets/styles/composed-components.css`](design-system/assets/styles/composed-components.css) in the same commit, per the CLAUDE.md stylesheet-sync rule.

### 3.1 Design-system citations

- **ID-chip drop:** [`design-system/SPEC.md` §4.7](design-system/SPEC.md) (CritiqueCard / ItemCard primitive composition). Spec 0168 §2.3 rewrote the head composition contract and added the explicit forbidden pattern "no ID chip in the card head" — this spec partially executes that contract.
- **§4.8 — ID display rule:** spec 0168 §2.3 updated §4.8 to "the ID does NOT render as an in-card head chip; ID lives in URL hash / anchor / cross-reference contexts only." This spec aligns the live rendering with that rule for the chip surface.
- **Markdown rendering:** the project's `<Markdown>` component is already imported in [`run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) and consumed by other `ItemCard` sub-renderers (Comment body at the existing Markdown callsite). No new DS primitive, no new dependency.

## 4. Regression-prevention test

A test that fails before this fix and passes after:

- [ ] **Vitest DOM test** in `tests/ui/static/` that mounts a `<ItemCard>` for each of the four kinds (Question, Disagreement, Issue, Comment) using fixtures whose `item.body` begins with `**Title text**\n\nbody paragraph…` and whose `item.id` is a compound code like `I-DEQ-PLAN-C-01`. For each kind, assert:
  - No element in the card subtree has `textContent` containing two consecutive `*` characters.
  - No element in the card subtree has `textContent` containing the literal `item.id` string.
  - The card subtree contains no element with class `item-card__sid`.
- [ ] **Specific Issue-card assertion:** the rendered Issue card has at least one `<strong>` element whose `textContent` equals "Title text" — proves the Markdown render produced real bold formatting in place of the literal asterisks.

## 5. Blast radius

- Header chip site at line 1787 — `ItemCard` is the only consumer; one render path.
- `ItemCardDQBody.__sid` — only the Disagreement and Question kinds, both via `ItemCard`.
- `ItemCardIssueBody.__title-row` + `__sid` — only the Issue kind, only via `ItemCard`.
- `<Markdown>` component — already imported and used multiple times in [`run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx); no new import; consistent behaviour with Comment card body which already renders identically.
- `.item-card__sid`, `.item-card__title-row`, `.item-card__title-sep`, `.item-card__title` CSS rules in [`src/dual_research/ui/static/components.css`](src/dual_research/ui/static/components.css) — confirm dead via grep, then remove from both stylesheets.
- Net diff: ~10 lines removed in JSX, ~4 lines added (the Markdown render in `ItemCardIssueBody`), ~15–25 lines of dead CSS removed if grep confirms.

## 6. Out of scope

- Bug 1 (Agent Input horizontal cards) — separate spec 0171.
- Bug 3 (Expanding section chevrons reveals empty body) — separate spec.
- Bug 4 (Critique cards still diverge from the design system — chip order, per-turn row redesign, lifecycle footer refinements, full §2.3 head rebuild from spec 0168) — separate spec.
- Bug 5 (Consumption tab's unfolded card does not match Design System V2) — separate spec.
- Bug 6 (All-Runs table reports `running` for runs that died days ago) — separate spec.
- Full execution of spec 0168 §2.2 (BEM rename of DS), §2.3 (full head rebuild beyond ID-chip drop), §2.4 (round + state lifecycle chip), §2.5 (evidence-needed inline chip), §2.6 (resolver icon inside state chip), §2.7 (full expanded `.item-card__lifecycle` layout beyond the Markdown fix), §2.8 (source attribution), §2.9 (per-card collapse) — large scope, belongs in a dedicated spec.
- Any change to `parseCodeId` itself, the upstream `item.id` shape, or the aggregator's item-id generation — the ID stays in the data model; only its visible rendering is removed.
- The bottom anchor blockquote on Issue cards (`.item-card__anchor--bottom`) — already renders correctly; not touched.

## 7. Risks

- **`item.id` was useful for cross-referencing items across surfaces.** Mitigation: the DOM `id` attribute on the `<article>` element stays, the URL hash stays, the spec-0168 §2.3 design rationale already accepted this trade-off ("cards are identified visually by their position in the phase view + their state + their content"). If product feedback later reverses this, a hover tooltip (`title={item.id}` on `<article>`) is a non-visible-by-default way to re-expose it.
- **Markdown render of full body might surface unexpected block structures** — e.g. if `item.body` contains a heading line like `# Heading`, the `<Markdown>` component will render an `<h1>` inside the card. Mitigation: verify against the existing Comment-card behaviour which already uses the same render path; if heading rendering is too prominent, consider scoping a heading-demoting variant — but only after verifying the problem actually exists in real data.
- **Regression to Disagreement / Question body row layout** if the `.item-card__bmeta` row layout depended on the deleted `<code>__sid</code>` element for flex sizing. Mitigation: the existing flex spacer at `style={{ flex: 1 }}` between the state chip and the turn count remains; the row keeps its left-to-right composition. CSS at [`components.css:4351`](src/dual_research/ui/static/components.css) confirms `.item-card__bmeta` uses `display: flex; gap: 8px` and does not depend on `__sid` for any size calculation.
- **Dead-CSS removal regression** if grep misses a consumer. Mitigation: grep across both `src/dual_research/ui/static/` and `design-system/` before deletion; if uncertain, comment out the rule first and verify the running app before deleting.
- **PR conflict with the Bug 4 spec** if Bug 4 lands in parallel and touches the same head / body files. Mitigation: this spec is `complexity: S` (~10-line JSX diff) and should ship fast; Bug 4 will be a separate spec with its own queue position and can rebase on whatever lands first.

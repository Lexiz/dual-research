---
kind: dev
spec: "0151"
slug: critique-parity-agent-input-grouping-run-id-copy
title: Design-system parity for critique surface + canonical Agent Input grouping + run-ID copy affordance
type: bug
label: bug
version_bump: MINOR
target_version: 1.16.0
status: deployed
depends_on: []
complexity: M
created: 2026-05-22
queued_at: ""
started_at: ""
merged_at: "2026-05-22T07:16:27Z"
deployed_at: "2026-05-22T07:16:27Z"
pr: "https://github.com/Lexiz/dual-research/pull/173"
handover: "handoffs/2026-05-22-spec-0151-design-system-parity-critique-and-agent-input.md"
failure_step: ""
source_session: pre-lifecycle-bootstrap
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---
# Spec 0151 — Design-system parity for critique surface + canonical Agent Input grouping + run-ID copy affordance

> Ship bucket: **Close out four UI regressions accumulated across the 0140–0150 batch — the critique-section header/cards never matched the design-system reference; the split-view Agent Input tab in preflight modals still uses a pre-canonical flat renderer; the three-section Agent Input panel silently hides empty pieces; and the run-ID badge has no explicit copy affordance.**
> Depends on:
> - **0144** (ItemCard router) — defines the `transitions`-gated routing between `ItemCard` and the legacy `QuestionThread` renderer that §3.4 retires.
> - **0145** (Canonical prompt-pieces) — established the canonical dot-keyed schema (`system.task.*`, `user_prompt.*`, `phase1.*`) that `InputTabContent` groups via `sectionFor()`. §3.1 and §3.2 inherit this schema.
> - **0147** (Phase 0 critique section) — last touched the critique header; introduced the P0 phase tab that the design-system reference predates (see §7).
> - **0150** (Legacy-shim sunset) — removed the data shims but did not touch any UI surface in this spec; all line numbers below are anchored to HEAD = 403c83b.
> - **Design-system reference**: `design-system/notion-issues/ISSUES.md` Issue 2 + screenshots `02-critique-target.png`, `07-question-card-duplicate.png`, `08-disagreement-card.png`, `09-issue-card.png`, `10-comments-card.png`. Notion is the verbatim source of truth; ISSUES.md mirrors it.
> Complexity: **M** — four discrete UI fixes; no schema changes; no new dependencies. Bug 4 (critique parity) is the bulk of the work.
> Targeted version bump: **MINOR (1.15.0 → 1.16.0)** — visible UI changes across the critique section, the Agent Input panel, and the run-ID badge.

---

## 1. Context

Across specs 0140–0150 several UI surfaces drifted from their design-system references or never landed the affordances they were intended to ship with. The product owner reviewed the running app after the batch deployed and flagged four regressions. None are functional bugs — the underlying data flows correctly — but each diverges from the canonical visual treatment defined in `design-system/notion-issues/ISSUES.md` or from an originally-requested affordance that was dropped during scoping.

This spec closes those four gaps in a single release.

### 1.1 Symptoms

1. **Bug 1 — Preflight Agent Input tab uses a non-canonical renderer.** Opening a Phase-0 preflight turn modal (e.g. "Preflight turn · Claude · round 1") shows the agent's prompt pieces as flat rows inside per-agent cards — `PREFLIGHT INSTRUCTIONS (system.task.input)` / `CHAT MESSAGE (user_prompt.message)` stacked vertically. Every other full-view modal (`DocumentModal`, `PreflightResponseModal`, `InputBriefModal`) groups the pieces into three collapsible sections: SYSTEM PROMPT / USER PROMPT / DERIVED INPUTS, with piece counts. The preflight path skipped that migration in spec 0145.

2. **Bug 2 — Three-section Agent Input panel renders empty.** `InputTabContent` filters out any piece whose value is a falsy string before rendering ([`run-detail.jsx:5748`](src/dual_research/ui/static/run-detail.jsx)). When the backend emits a canonical piece with an empty string (e.g. `phase1.claude = ""` for a turn where Claude's draft hasn't been written yet — see [`protocol/prompts.py:1095-1096, 1135`](src/dual_research/protocol/prompts.py)), the piece silently disappears. If every piece in a section is empty, the entire section header vanishes too. Users see an empty modal with no signal that the field exists.

3. **Bug 3 — Run-ID badge has no explicit copy button.** Spec 0138 §5.3 introduced `RunIDChip` as a single click-anywhere pill that copies the run ID; spec 0143 extended the payload to `id · cost · tokens`. The original product request — a small visual divider on the right of the badge and a dedicated copy button beside it — was never written into a spec and never shipped. The single-pill affordance is non-discoverable; users have to know that clicking the badge does something.

4. **Bug 4 — Critique section visual rework not applied.** The critique-pane header (`CritiqueExplorer`, [`run-detail.jsx:6842+`](src/dual_research/ui/static/run-detail.jsx)) and the card bodies (`ItemCard` at [`run-detail.jsx:1410+`](src/dual_research/ui/static/run-detail.jsx); legacy `QuestionThread` at [`shared.jsx:1133+`](src/dual_research/ui/static/shared.jsx)) diverge from the design-system targets. The product owner flagged this with `design-system/notion-issues/screenshots/02-critique-target.png` (toolbar) and the four card-kind references `07/08/09/10` (Question / Disagreement / Issue / Comment).

### 1.2 Prior investigation

A two-pass code investigation confirmed all four bugs are still present at HEAD = 403c83b:

- **Bug 1**: `AgentInputDualPane` ([`run-detail.jsx:5576`](src/dual_research/ui/static/run-detail.jsx)) still mounts `AgentInputPane` ([`5597`](src/dual_research/ui/static/run-detail.jsx)) instead of the canonical `InputTabContent`.
- **Bug 2**: filter at [`run-detail.jsx:5748`](src/dual_research/ui/static/run-detail.jsx) — `Object.keys(pieces).filter((k) => pieces[k])` — still drops empty-string pieces.
- **Bug 3**: `RunIDChip` ([`shared.jsx:845-852`](src/dual_research/ui/static/shared.jsx)) is unchanged from spec 0138; no divider, no separate button.
- **Bug 4**: `CritiqueExplorer` toolbar and `ItemCard`/`QuestionThread` card bodies have never been aligned to the design-system references; the two-renderer routing at [`run-detail.jsx:6747-6783`](src/dual_research/ui/static/run-detail.jsx) still gates on `transitions` presence.

---

## 2. Goals

1. **Bug 1** — Refactor `AgentInputPane` to share the three-section grouping logic with `InputTabContent`. Preflight (and any other split-view Agent Input consumer) renders SYSTEM PROMPT / USER PROMPT / DERIVED INPUTS collapsible sections per agent column, with the existing dual-pane frame and per-agent status pill retained.

2. **Bug 2** — Empty-string prompt pieces render with a muted `(empty)` placeholder in the Agent Input panel. Section headers always render for sections that have at least one piece (populated or empty). Per-piece visibility never depends on the value's truthiness; only on the piece being present in the bundle.

3. **Bug 3** — `RunIDChip` becomes inert (badge no longer copies on click). A vertical divider and an explicit copy-button glyph are appended on the right side of the badge. The button is the sole copy affordance; clicking it writes `id · cost · tokens` to clipboard and surfaces the same "copied" tooltip as today.

4. **Bug 4** — The critique-section header and card bodies match the design-system references pixel-by-pixel:
   - Toolbar → `02-critique-target.png`
   - Question card → `07-question-card-duplicate.png`
   - Disagreement card → `08-disagreement-card.png`
   - Issue card → `09-issue-card.png`
   - Comment card → `10-comments-card.png`

---

## 3. Proposed change

### 3.1 Bug 1 — Refactor `AgentInputPane` to share three-section grouping

**File:** [`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx)

**Current state:**
- `AgentInputDualPane` (lines 5576–5594) renders two `AgentInputPane` columns side by side.
- `AgentInputPane` (lines 5597–5636) takes a `turnKey`, fetches the prompt pieces, and maps each to a flat `<InputSection>` row. No grouping.
- `InputTabContent` (lines 5729–5816) is the canonical three-section renderer used in single-view modals. It calls `sectionFor()` (5721) to bucket each piece into `system` / `user_prompt` / `derived`, then renders one `<InputSectionGroup>` per bucket.

**Change:**
1. Extract the three-section grouping logic from `InputTabContent` (the `grouped` / `populated` / `renderKeys` / `.map()` block at ~5760–5810 that emits `InputSectionGroup`) into a new internal helper `<PromptPiecesThreeSectionView turnKey attachmentTitles frame />` where `frame` is `'single' | 'split'`.
2. Rewrite `InputTabContent` to delegate to `<PromptPiecesThreeSectionView frame="single" turnKey={…} />`.
3. Rewrite `AgentInputPane` to wrap `<PromptPiecesThreeSectionView frame="split" turnKey={…} />` inside its existing per-agent card frame (the `slot`-aware card with agent name + status pill).
4. The `frame` prop controls only minor padding/border differences between single and split contexts; the section structure, piece rendering, and default-open behaviour are identical across both consumers.
5. Delete the old flat-row mapping in `AgentInputPane` (lines 5615–5631).

**Expected diff size:** ~40 LOC removed, ~30 LOC added in the same file. Net ~−10 LOC.

### 3.2 Bug 2 — Empty-string pieces render with `(empty)` placeholder

**Files:**
- [`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) (filter + section rendering)
- [`src/dual_research/ui/static/components.css`](src/dual_research/ui/static/components.css) or `theme.css` (placeholder styling)

**Current state:**
- `InputTabContent` at line 5748: `const populated = Object.keys(pieces).filter((k) => pieces[k]);`
- Empty-string pieces are stripped before grouping; if every piece in a section is empty, the section header doesn't render either (the `filtered` short-circuit at 5786 hides empty groups).

**Change:**
1. Remove the truthy filter at 5748. Replace with: keep every key present in `pieces`, regardless of value.
2. In `InputSection` (line 5856), if `text` is falsy or zero-length, render `<span className="prompt-piece__empty">(empty)</span>` inside the body region instead of the markdown content.
3. Section headers render whenever the section has ≥1 piece (populated or empty). A section with zero pieces in the bundle stays hidden (i.e. don't render an empty group whose backing keys aren't in the bundle at all).
4. Piece-count badge in `InputSectionGroup` (line 5818) counts all pieces in the section (populated + empty) — matches the count the user expects from the bundle shape.
5. Add `.prompt-piece__empty` to `components.css` / `theme.css` with muted foreground (`var(--ink-muted)` or equivalent) and italic styling.

**Expected diff size:** ~10 LOC in `run-detail.jsx`, ~6 LOC of CSS.

### 3.3 Bug 3 — Run-ID badge becomes inert; add divider + explicit copy button

**Files:**
- [`src/dual_research/ui/static/shared.jsx`](src/dual_research/ui/static/shared.jsx) (`RunIDChip` definition, lines 844–852)
- [`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) (consumer, lines 273–324)
- [`src/dual_research/ui/static/icons.jsx`](src/dual_research/ui/static/icons.jsx) (add `Icon.Copy` if not already present)
- [`src/dual_research/ui/static/components.css`](src/dual_research/ui/static/components.css) (divider + button styling)

**Current state:**
- `RunIDChip` is a `<button>` if `onClick` is provided, else a `<span>`. Clicking copies the payload.
- `run-detail.jsx:281–295` defines `copyRunId`; `run-detail.jsx:317` wires it to the chip via `onClick`.

**Change:**
1. Rewrite `RunIDChip` as a compound component:
   ```jsx
   <div className="rid">
     <span className="rid__id">{id}</span>
     <span className="rid__divider" aria-hidden="true" />
     <button className="rid__copy" type="button" onClick={onCopy} title={copyTitle} aria-label="Copy run ID">
       <Icon.Copy />
     </button>
   </div>
   ```
   The outer container is non-interactive (no `onClick` handler).
2. Add `Icon.Copy` to `icons.jsx` using Material Symbols `content_copy` at 16 px — match the existing icon convention.
3. Update the consumer at `run-detail.jsx:317–323`: replace `onClick={copyRunId}` with `onCopy={copyRunId}` and pass `copyTitle` derived from the existing tooltip logic (copied state vs idle state).
4. Keep the click-handler logic (`copyRunId`, lines 281–295) centralised so the tooltip swap behaviour (copied/idle) is unchanged.
5. Divider styling: 1 px vertical line at `var(--border-subtle)` (or equivalent token), 60% of badge height, 8 px horizontal margin.
6. Copy-button styling: same baseline as other inline icon-buttons in the header (28 px hit area, 16 px glyph, hover/focus states from the existing `.icon-btn` token).

**Expected diff size:** ~25 LOC across `shared.jsx` / `icons.jsx` / `run-detail.jsx`; ~15 LOC of CSS.

### 3.4 Bug 4 — Critique section toolbar + card bodies match design-system

**Files:**
- [`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) (`CritiqueExplorer` header at 6842–6883, `KIND_TABS` at 6804+, `bar2` filter row at 6891–6940, `ItemCard` at 1410–1557, legacy `QuestionThread` callsites at 6747–6783 / 7018+)
- [`src/dual_research/ui/static/shared.jsx`](src/dual_research/ui/static/shared.jsx) (`QuestionThread` definition near line 1133)
- [`src/dual_research/ui/static/theme.css`](src/dual_research/ui/static/theme.css) / [`components.css`](src/dual_research/ui/static/components.css) (any necessary token tweaks)

**Reference screenshots (canonical):**
- Toolbar: [`design-system/notion-issues/screenshots/02-critique-target.png`](design-system/notion-issues/screenshots/02-critique-target.png)
- Question card: [`design-system/notion-issues/screenshots/07-question-card-duplicate.png`](design-system/notion-issues/screenshots/07-question-card-duplicate.png)
- Disagreement card: [`design-system/notion-issues/screenshots/08-disagreement-card.png`](design-system/notion-issues/screenshots/08-disagreement-card.png)
- Issue card: [`design-system/notion-issues/screenshots/09-issue-card.png`](design-system/notion-issues/screenshots/09-issue-card.png)
- Comment card: [`design-system/notion-issues/screenshots/10-comments-card.png`](design-system/notion-issues/screenshots/10-comments-card.png)

#### 3.4.1 Header (target = `02-critique-target.png`)

1. **Top row (`bar1`)** contains `Critique [vbar] [phase tabs] [right: totals + ⚠ N drift]`. The current implementation already has this structure — verify spacing/typography (font size, weight, gaps between elements) match the target.
2. **Phase tabs**: current order P0 / P2 / P4 / Σ. Target shows P2 / P4 / Σ — but the target screenshot predates spec 0147's P0 tab. **Keep P0** as the post-0147 reality; preserve all other phase-tab styling per target. (See §7 Open question; default = keep P0.)
3. **Run-wide drift chip**: target shows `⚠ 1 drift` as a warn-tone pill on the far right of bar1 alongside the totals. Spec 0119 §8.6 retired it; this spec reinstates it conditional on `runWideDrift > 0`. Cite this supersession in the handoff.
4. **Bottom row (`bar2`) — kind filter**: target order is `All / Issues / Comments / Questions / Disagreements`. Current code emits `questions / disagreements / issues / comments` then `All` (at 6893–6940). Reorder.
5. **Kind-filter count rendering**: target shows the numeric count as a separate visual token next to the label (e.g. "All 28", "Questions 19"), not appended to the label string. Drop the `(${t.count})` munging at line 6817 and pass `value` to the `Chip` primitive (which already renders it as a separate token).
6. **Bar2 right side — agent filter**: target shows compact dot+label segmented control (`All • Claude • GPT`) with subtle agent-tone dots. Current implementation uses fuller chips with full agent badges. Replace with the segmented-control variant from `shared.jsx`.
7. **Bar2 right side — state filter**: target shows `All / Open / Resolved / Drift` as a segmented control. Current implementation is close; align typography/spacing.

#### 3.4.2 Card bodies — common changes

1. **Retire the legacy fallback router.** The current router at `run-detail.jsx:6747–6783` falls back to `QuestionThread` for items without `transitions`. After this spec, `ItemCard` renders every kind. The aggregator already populates `transitions` for new-protocol items (per [`ui/items.py:252`](src/dual_research/ui/items.py)); for legacy items lacking the field, add a one-line guard in [`ui/item_projection.py`](src/dual_research/ui/item_projection.py) (or wherever items are projected) that defaults `transitions` to `[]` when absent. The router then becomes unconditional.
2. **Delete** `_normalizeToThread` (`run-detail.jsx:7018+`).
3. **Audit `QuestionThread` callers.** Search for every `QuestionThread` usage. If no non-critique surface uses it, delete the definition in `shared.jsx`. If any surface still uses it, keep the definition but remove the critique-side import.
4. **Implement kind-specific body layouts** inside `ItemCard` — either as inline conditional blocks keyed off `item.kind`, or as four dedicated sub-renderers (`<QuestionBody>`, `<DisagreementBody>`, `<IssueBody>`, `<CommentBody>`). Default = sub-renderers, scoped locally inside `run-detail.jsx`.
5. **Hover elevation** per `design-system/notion-issues/ISSUES.md` Issue 3 — apply `data-hoverable="true"` (see [`shared.jsx:872`](src/dual_research/ui/static/shared.jsx)) to the `ItemCard` wrapper.

#### 3.4.3 Card bodies — per-kind anatomy

For each kind, the design-system screenshots define the exact layout. Implementation must match.

**Disagreement** (`08-disagreement-card.png`):
- Collapsed header: `Disagreement NN · <state badge> · <summary>` with chevron right.
- Expanded body:
  - `d-NN · <state badge>` row with `N turns` right-aligned.
  - Resolved verdict text (when state = resolved).
  - Per-turn rows: `<AgentBadge> · r<N> · <verdict badge>` followed by quoted text.
  - Footer strip (when resolved): green `✓ both aligned in round N`.

**Issue** (`09-issue-card.png`):
- Group header: `ISSUES <count> ▼` (collapsible group).
- Card collapsed header: `Issue NN · <Claude or GPT badge> · <state badge> · <title>` with chevron.
- Expanded body:
  - `C-N — <state> — <title>`.
  - Quoted anchor (blockquote).
  - Body paragraph.
  - Metadata row: `<AgentBadge> flagged by · first seen R<N> · last seen R<M>`.
  - Anchor blockquote at the bottom.

**Comment** (`10-comments-card.png`):
- Collapsed header: `Comment NN · <Agent badge> · <state badge> · <summary>` with chevron.
- Expanded body:
  - Full markdown body (bold lead-in supported).
  - Quoted anchor (inline).
  - Metadata row: `<AgentBadge> <verb> by · R<N>`.
  - Anchor blockquote at the bottom.

**Question** (`07-question-card-duplicate.png`):
- Collapsed/expanded headers and per-turn rows analogous to Disagreement but with question-state verbs (`answered`, `addressed`, etc.).
- Use the existing transition timeline rendering with question-appropriate labels.

**Expected diff size:** ~250–350 LOC across `run-detail.jsx` + `shared.jsx` + CSS. This is the bulk of the spec.

---

## 4. Out of scope

- Backend / aggregator changes beyond the one-line `transitions: []` default in §3.4.2.
- New design-system tokens or primitives. This spec uses existing tokens (Chip, Card, Icon, segmented control). If a card-body element in the references genuinely requires a new primitive, surface it in §7 Open questions and the corresponding card-kind sub-task waits.
- Other notion-issues entries. Issue 3 hover-elevation is partially included via §3.4.2.5; Issues 1 (badge heights), 4 (OK-badge style), 5 (phase indicators), 6+ stay in the backlog.
- Mobile / responsive treatment. The references are desktop captures; mobile parity is a separate audit.
- `PromptPiecesThreeSectionView` (§3.1) is not exposed beyond the two existing consumers (`InputTabContent`, `AgentInputPane`); not hoisted to `shared.jsx`.

---

## 5. Test plan

### 5.1 Manual / visual

- [ ] Open a preflight turn modal (Phase-0 round-1, Claude side). Verify the Agent Input tab renders three collapsible sections (System Prompt / User Prompt / Derived Inputs) inside each agent column. Repeat for round-2 if available.
- [ ] Open a turn where `phase1.claude` is an empty string (e.g. the `20260521-010637-dvs-backend-language-choice` run at Phase 2 round 1). Verify the piece renders with `(empty)` placeholder and the Derived Inputs section header stays visible.
- [ ] Header — confirm `RunIDChip` shows badge + divider + copy button. Click the badge: nothing happens. Click the copy button: clipboard receives `id · cost · tokens` and the tooltip swaps to "copied".
- [ ] Critique section toolbar — compare to `02-critique-target.png`. Phase-tab row, kind-filter row (order + count tokens), agent/state filters, totals + drift pill all match.
- [ ] Critique cards — for each kind (Question, Disagreement, Issue, Comment), compare to the corresponding reference screenshot at collapsed and expanded states. Badges, lifecycle rendering, footer all match.
- [ ] Hover over an `ItemCard` — verify elevation animates per design-system audit Issue 3.

### 5.2 Regression

- [ ] Verify the canonical three-section panel still works in `DocumentModal`, `PreflightResponseModal`, `InputBriefModal` after §3.1's extraction (side-by-side before/after on the same run).
- [ ] Verify legacy runs (pre-spec-0144) still render their critique items via `ItemCard` — the `transitions: []` shim should keep the router path working.
- [ ] Run `npm` / build script: confirm no JS errors from `Icon.Copy` import or component refactor.
- [ ] CI: `pytest` should be green (no Python changes expected besides the optional one-line projection shim).

### 5.3 Smoke

- [ ] Deploy to fly, open the latest production run, walk through preflight → Phase 2 → critique pane. Capture screenshots and diff against the design-system references.

---

## 6. Risks

1. **Critique card-body rework breaks layouts for edge-case items.** Items with unusual transition histories (e.g. capped, drift-flagged, multi-round disagreements) may not match the design references because the references don't show those edge cases. Mitigation: §3.4 audit pass explicitly checks all states defined in `stateTone` ([`run-detail.jsx:1419-1426`](src/dual_research/ui/static/run-detail.jsx)); fall back to the "least surprising" rendering for states not in the references and capture in the handoff.
2. **Retiring `QuestionThread` may break a forgotten consumer.** Search for every `QuestionThread` usage before deletion; keep the definition if any non-critique surface still uses it.
3. **`PromptPiecesThreeSectionView` extraction risks regressing single-view modals.** Mitigation: deliberate side-by-side review of `DocumentModal`, `PreflightResponseModal`, `InputBriefModal` rendering before / after the extraction.
4. **Re-introducing the run-wide drift chip (§3.4.1.3) contradicts spec 0119 §8.6.** This spec supersedes that decision. Cite in the handoff.
5. **`Icon.Copy` may collide with an existing icon name.** Verify before adding.

---

## 7. Open questions

- **P0 tab parity**: design-system `02-critique-target.png` predates spec 0147 and does not show P0. This spec keeps P0 (post-0147 reality) and treats the target's phase-tab list as a non-exhaustive reference. Confirm with product owner during review or accept the default.
- **Per-card kind primitive**: open whether `<QuestionBody>` / `<DisagreementBody>` / `<IssueBody>` / `<CommentBody>` live as separate functions inside `run-detail.jsx` or get hoisted to `shared.jsx`. Default = local until reuse demands hoisting.

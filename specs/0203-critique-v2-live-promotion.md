---
kind: dev
spec: "0203"
slug: critique-v2-live-promotion
title: Critique V2 → live promotion (C1–C8 + V2.A/B/C)
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
depends_on: []
complexity: L
created: 2026-05-24
queued_at: "2026-05-24T00:26:05Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: ""
promoted_from_draft: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

<!-- DEV SPEC RULE: this body must contain NO open questions, unresolved
items, TBD markers, or "we'll figure it out later" prose. Every decision is
either answered here or explicitly deferred via §5 Out of scope with a
named follow-up target. -->

# Spec 0203 — Critique V2 → live promotion (C1–C8 + V2.A/B/C)

> **Type:** new-feature  |  **Complexity:** L  |  **Depends on:** —
> **Bump:** MINOR — promotes new UI behavior (eight user-visible critique-pane changes) to production.
> **Evidence:** [`prototypes/critique-iteration/V2-SNAPSHOT.md`](../prototypes/critique-iteration/V2-SNAPSHOT.md) (canonical snapshot, landed in commit `466934c`); [`prototypes/critique-iteration/NOTES.md`](../prototypes/critique-iteration/NOTES.md) (full iter record); [`prototypes/critique-iteration/proposed.html`](../prototypes/critique-iteration/proposed.html) + [`_inline-script.js`](../prototypes/critique-iteration/_inline-script.js) (pixel target); [`prototypes/critique-iteration/live.html`](../prototypes/critique-iteration/live.html) (diff target); Notion [Critique & Timeline](https://www.notion.so/36999f3e507f8083b551f2c8fcbe46d3) (the C1–C8 source).

---

## 1. Context

The critique-pane workshop at [`prototypes/critique-iteration/`](../prototypes/critique-iteration/) ran 15 iterations on 2026-05-22 and locked a target visual + interaction model. The user audited the live app against that target on 2026-05-23 and flagged eight specific discrepancies (the "C-items"), all of which the workshop's `proposed.html` already resolves. This spec promotes the whole workshop canvas to live in one coherent change.

The whole canvas IS the spec — no filtering, no prioritisation. Three "promotion patches" (V2.A / V2.B / V2.C) adapt the workshop stack for live (collapse-rule scope, drop the workshop demo's auto-expand, system-actor head + lifecycle alignment). Per [`CLAUDE.md`](../CLAUDE.md) §Design system, the DS authoritative copy [`design-system/assets/styles/composed-components.css`](../design-system/assets/styles/composed-components.css) and the live copy [`src/dual_research/ui/static/components.css`](../src/dual_research/ui/static/components.css) land in the same commit (strict scope: only the V2-delta classes; full parity backfill is deferred).

### 1.1 — Source-artifact traceability

Every atomic item from the source artifacts maps to a §2.N section below OR a §5 deferral with a named follow-up.

| source item | source quote/ref | spec section |
|---|---|---|
| C1 | [`V2-SNAPSHOT.md`](../prototypes/critique-iteration/V2-SNAPSHOT.md) §2 row C1 — "Resolved unfolded by default (first section in P0/P2/P4 starts expanded)" | §2.1 |
| C2 | [`V2-SNAPSHOT.md`](../prototypes/critique-iteration/V2-SNAPSHOT.md) §2 row C2 — "Wide filter header: four kind badges with cat-bubble on left + segmented agent + status on right + brand icons + no All buttons + per-option counts" | §2.2 |
| C3 | [`V2-SNAPSHOT.md`](../prototypes/critique-iteration/V2-SNAPSHOT.md) §2 row C3 — "Narrow filter header (viewport ≤1799px): kind badges drop text labels, segmented counts disappear, both sides stay on one row" | §2.3 |
| C4 | [`V2-SNAPSHOT.md`](../prototypes/critique-iteration/V2-SNAPSHOT.md) §2 row C4 — "Collapsed card height matches timeline `.tl-thread` (≈36px), not the current ~64px" | §2.4 |
| C5 | [`V2-SNAPSHOT.md`](../prototypes/critique-iteration/V2-SNAPSHOT.md) §2 row C5 — "Collapsed card head pattern: `[Provider · Raised·R1 · Kind] [State · R<N>]` with System chip in lead slot when actor is orchestrator/system" | §2.5 |
| C6 | [`V2-SNAPSHOT.md`](../prototypes/critique-iteration/V2-SNAPSHOT.md) §2 row C6 — "Expanded card: `LIFECYCLE` overline + sequence of `.lc-row` items, each with chip cluster above an italic-serif quote; left edges align across rows" | §2.6 |
| C7 | [`V2-SNAPSHOT.md`](../prototypes/critique-iteration/V2-SNAPSHOT.md) §2 row C7 — "Source-request signal: blue tone-info evidence-needed chip in head (icon-only with hover tooltip), plus `[🔗 source requested]` / `[🔗 source provided]` extras in lifecycle rows" | §2.7 |
| C8 | [`V2-SNAPSHOT.md`](../prototypes/critique-iteration/V2-SNAPSHOT.md) §2 row C8 — "Sources segment: provider+round attribution chip right-aligned; title truncates at ~280px; first row pre-expanded" | §2.8 |
| V2.A | [`V2-SNAPSHOT.md`](../prototypes/critique-iteration/V2-SNAPSHOT.md) §3.A — "Scope the collapse rules so iter-12's lifecycle wrapper hides when card is collapsed (new disambiguating class `.item-card__lifecycle-section`)" | §2.6 |
| V2.B | [`V2-SNAPSHOT.md`](../prototypes/critique-iteration/V2-SNAPSHOT.md) §3.B — "Do NOT ship iter-15's whole-card auto-expand to live; cards default collapsed" | §2.1 |
| V2.C | [`V2-SNAPSHOT.md`](../prototypes/critique-iteration/V2-SNAPSHOT.md) §3.C — "System chip in the head's actor slot + `align-self: stretch` on lc-row chip clusters" | §2.5 + §2.6 |
| Drift 3.E | [`NOTES.md`](../prototypes/critique-iteration/NOTES.md) §3.E — "Resolved group title misrepresents terminal-state mix (resolved + acknowledged + capped lumped under one heading)" | §5 (deferred to a follow-up dev spec to be drafted post-merge) |
| Drift 3.F | [`NOTES.md`](../prototypes/critique-iteration/NOTES.md) §3.F — "Σ Summary bar-1 totals reset to 0/0/0 when Σ tab is active; should be tab-invariant" | §5 (deferred to a follow-up dev spec to be drafted post-merge) |
| Drift 3.G | [`NOTES.md`](../prototypes/critique-iteration/NOTES.md) §3.G — "Σ Summary body uses ~25 inline style attributes; promote into reusable CSS classes" | §5 (deferred to a follow-up dev spec to be drafted post-merge) |
| Drift 3.H | [`NOTES.md`](../prototypes/critique-iteration/NOTES.md) §3.H — "DS Σ Summary section diverges from live Σ Summary body; neither locked in SPEC.md §4.1" | §5 (deferred to a follow-up dev spec to be drafted post-merge) |

---

## 2. Proposed change

Each subsection below: (a) cites the design-system section that governs the change (per the [`CLAUDE.md`](../CLAUDE.md) DS gate); (b) verifies the live state at file+line (per the spec 0198 §1f gate); (c) specifies the V2 target; (d) names the files touched. The three promotion targets — [`src/dual_research/ui/static/components.css`](../src/dual_research/ui/static/components.css), [`design-system/assets/styles/composed-components.css`](../design-system/assets/styles/composed-components.css), [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) — land in a single commit (§6 Test plan verifies this).

### 2.1 — C1: Resolved section unfolded by default (in P0 / P2 / P4)

**DS citation.** [`design-system/SPEC.md`](../design-system/SPEC.md) §4.1 (critique pane — status-grouped collapsible sections).

**Live currently.** The `renderGroup(title, items, tone, countClass, collapsed)` helper at [`run-detail.jsx:7311-7330`](../src/dual_research/ui/static/run-detail.jsx#L7311) accepts a `collapsed` boolean and emits `<section className="crit-group" data-collapsed={collapsed ? 'true' : 'false'}>`. The CSS at [`components.css:2449-2450`](../src/dual_research/ui/static/components.css#L2449) hides `.crit-group__body` when `[data-collapsed="true"]`. The caller currently passes `collapsed = true` for the Resolved group (confirmed by the user's 2026-05-23 Notion audit: "by default starts with the resolved section being collapsed").

**Target.** The caller of `renderGroup` passes `collapsed = false` for the Resolved group whenever the active phase has ≥ 1 resolved item. The Open · new / Open · carried / Drift groups keep their current defaults. No CSS change; this is a JSX caller change.

**V2.B note.** The workshop's [`_inline-script.js:318`](../prototypes/critique-iteration/_inline-script.js#L318) `initCollapseState()` unfolds ALL groups and ALL cards by default — that is a workshop affordance, not the product target. Spec 0203 only unfolds the **Resolved group section**; cards inside it stay `data-expanded="false"`.

**Files.** [`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) only (caller of `renderGroup`).

### 2.2 — C2: Wide filter header (≥ 1800px) — kind badges + segmented controls + brand icons

**DS citation.** [`design-system/SPEC.md`](../design-system/SPEC.md) §4.1 (critique bar 2) + §9.6 (letter-bubble rule, the `.cat-bubble` primitive carrying kind identity across panes).

**Live currently.** The bar-2 baseline at [`components.css:1046-1052`](../src/dual_research/ui/static/components.css#L1046) defines `.crit2 .bar2.crit-filter-row` with `flex-wrap: nowrap`. Live ships explicit "All" buttons in both the agent and status clusters and uses `.chip-dot` swatches (not brand icons) for agent identity. No `.tab-group-solid` wrapper around the agent/status chips.

**Target.** Drop the "All" buttons from kind, agent, and status clusters (no active chip = "show all"). Wrap agent + status chips in `<div class="tab-group-solid" data-group="agent|status">` per `proposed.html` `<style id="iter-1-ds-aligned-headers">`. Use the live brand icons (Claude sunburst in sable tinted square; OpenAI rosette in sage tinted square) for the agent cluster, restoring the `chip-leading-icon` slot in place of `chip-dot`. Every option carries a `(N)` count next to its label (rendered via the existing `.chip-value` span restyled to drop the tinted-pill background and emit `(`/`)` via `::before`/`::after`).

**Files.** [`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) (filter render: remove the "All" emit; add the `tab-group-solid` wrapper; switch agent identity from `chip-dot` to `chip-leading-icon` with brand SVG); [`components.css`](../src/dual_research/ui/static/components.css) (new `.tab-group-solid` rules per `proposed.html` iter-1 — see verbatim CSS at [`proposed.html:96-149`](../prototypes/critique-iteration/proposed.html#L96)); [`composed-components.css`](../design-system/assets/styles/composed-components.css) (mirror the same new rules).

### 2.3 — C3: Narrow filter header (viewport ≤ 1799px) — labels drop, counts drop, single row

**DS citation.** [`design-system/SPEC.md`](../design-system/SPEC.md) §4.1 + §7.2 (responsiveness breakpoints).

**Live currently.** [`components.css:1079-1099`](../src/dual_research/ui/static/components.css#L1079) `@media (max-width: 1799px)` already drops `.chip[data-kind-filter] .chip-label` and labels for `chip-dot` / `chip-leading-icon` chips. But: there is no rule dropping the `(N)` counts from segmented chips because counts aren't currently in the live render; AND the row CAN wrap when content overflows because the `flex-wrap: nowrap` from line 1046 is overridden elsewhere (Notion screenshot for Issue 3 shows the right cluster disappearing off-canvas).

**Target.** After C2 lands, add `@media (max-width: 1799px) { .crit2 .bar2 .tab-group-solid .chip .chip-value { display: none !important } }` per `proposed.html` iter-1 (lines 150-157). Backstop the row with `.crit2 .bar2.crit-filter-row { flex-wrap: nowrap !important }` and `.crit2 .bar2 .kind-tabs { flex-wrap: nowrap !important }` per iter-7.2 (no wrap under any state). Kind chips keep dropping their labels at narrow per the pre-existing rule.

**Files.** [`components.css`](../src/dual_research/ui/static/components.css) + [`composed-components.css`](../design-system/assets/styles/composed-components.css) (mirror).

### 2.4 — C4: Collapsed card height matches timeline (≈ 36 px, not 64 px)

**DS citation.** [`design-system/SPEC.md`](../design-system/SPEC.md) §4.8 (critique card composition) + §4.4 (timeline pane — the dimensional target).

**Live currently.** [`components.css:4499-4513`](../src/dual_research/ui/static/components.css#L4499) `.item-card { padding: 12px 14px; gap: 10px; margin: 0 }` yields a ~64 px collapsed head. [`components.css:4528-4533`](../src/dual_research/ui/static/components.css#L4528) `.item-card__head` has no explicit padding, inheriting the parent's 12×14.

**Target.** Per `proposed.html` iter-7.1: `.item-card { padding: 0 }` and `.item-card__head { padding: 6px 12px; min-height: 0 }`. Collapsed card height becomes 36 px (matches timeline `.tl-thread` within 1 px). Per-card spacing is already handled by the gap on `.crit-group__body` ([`components.css:4527`](../src/dual_research/ui/static/components.css#L4527)).

**Files.** [`components.css`](../src/dual_research/ui/static/components.css) + [`composed-components.css`](../design-system/assets/styles/composed-components.css) (mirror).

### 2.5 — C5: Collapsed card head pattern + System-chip fallback

**DS citation.** [`design-system/SPEC.md`](../design-system/SPEC.md) §4.8 (ItemCard composition) + §9.5 (state vocabulary).

**Live currently.** [`run-detail.jsx:1969-1983`](../src/dual_research/ui/static/run-detail.jsx#L1969) renders the head as `[providerChip][kindChip][evidenceModifierChip]<spacer/>[lifecycleChip]`. The round and the state are folded into a single composite `lifecycleChip` ([`run-detail.jsx:1900-1935`](../src/dual_research/ui/static/run-detail.jsx#L1900)) — there is no separate "Raised · R1" round chip. The system-actor fallback exists at [`run-detail.jsx:1881`](../src/dual_research/ui/static/run-detail.jsx#L1881) (`raisedByAgent ? <Chip /> : <SystemChip />`) but emits markup that differs from the iter-7 rebuild.

**Target.** Head emits, left to right:

1. Provider chip — Claude / GPT / System. System chip path is taken whenever `_resolveAgent(item.raisedBy)` returns `null`, `"orchestrator"`, or `"system"`. Per V2.C, verify `_resolveAgent` maps `orchestrator` to a value that triggers the SystemChip branch; if it doesn't, fix it so the head shows `[System]` (gear-icon, idle-tinted) for orchestrator-raised cards.
2. Round chip — `Raised · R<N>` (mono neutral, capitalised leading word per iter-8.1).
3. Kind chip — Q / D / I / C with `.cat-bubble` (info / warn / err / idle tones per §9.3).
4. Optional evidence-needed chip (see §2.7).
5. Spacer (existing `.item-card__head-spacer`).
6. State chip — `<Verb> · <resolver icon?> · R<N>` (capitalised, with the resolver's brand icon inside the chip per iter-10; orchestrator/system resolvers skip the icon and the chip falls back to `Capped · R<N>` per iter-10).

**Files.** [`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) (rebuild head per iter-7/iter-8/iter-10 — emit four chips left-aligned plus state chip right-aligned via `.item-card__head-spacer`; the previous composite `lifecycleChip` cluster is replaced by the explicit round + state pair); [`components.css`](../src/dual_research/ui/static/components.css) (new `.item-card__head` padding per §2.4 plus chip-tone rules per iter-5/iter-8); [`composed-components.css`](../design-system/assets/styles/composed-components.css) (mirror).

### 2.6 — C6: Expanded card body — LIFECYCLE overline + `.lc-row` stack

**DS citation.** [`design-system/SPEC.md`](../design-system/SPEC.md) §4.8 (ItemCard composition — expanded body) + §4.2 (QuestionThread legacy pattern, the structural ancestor).

**Live currently.** [`run-detail.jsx:1518-1592`](../src/dual_research/ui/static/run-detail.jsx#L1518) renders `ItemCardThreadView` → `<ol className="item-card__qt-rows">` with `<li className="item-card__qt-row item-card__qt-row--<agent>">` containing `.item-card__qt-chips` + `.item-card__qt-quote`. No `LIFECYCLE` overline header. The `.lc-row*` CSS at [`components.css:1202-1224`](../src/dual_research/ui/static/components.css#L1202) IS defined but is unreferenced by the live JSX — it is dead code today.

**Target (with V2.A wrapper rename + V2.C alignment).** Replace `ItemCardThreadView` for expanded cards with a new `ItemCardLifecycleSection` component that emits:

```
<section className="item-card__lifecycle-section">
  <div className="item-card__lifecycle-section-hd">LIFECYCLE</div>
  <div className="lc-rows">
    {transitions.map(t => (
      <div className="lc-row" data-actor={t.actor}>
        <div className="lc-row-chips">{providerChip}{roundChip}{verbChip}{modifierChip?}{extrasChip?}</div>
        <p className="lc-row-quote">"{t.quote}"</p>
      </div>
    ))}
  </div>
</section>
```

**V2.A — disambiguate the wrapper class.** The new section uses `.item-card__lifecycle-section` (NOT `.item-card__lifecycle`, which already exists at [`components.css:4542`](../src/dual_research/ui/static/components.css#L4542) as the legacy head-chip cluster used by the OLD collapsed-head `lifecycleChip`). After §2.5's head rebuild drops the composite `lifecycleChip`, the old `.item-card__lifecycle` rule and its JSX call sites are removed; this prevents class collision and lets §4691 collapse rules cleanly extend to the new section.

**V2.C — alignment override.** Add `.item-card__lifecycle-section .lc-rows { align-items: stretch }` and `.lc-row { align-self: stretch }` so each row's chip cluster left-aligns regardless of quote length. Do NOT inherit `align-items: center` from any ancestor. This rule is load-bearing for C6's visual contract — calling it out so a future "clean up" pass cannot silently drop it.

**Collapse extension (V2.A).** Add `.item-card[data-expanded="false"] .item-card__lifecycle-section { display: none }` to the existing block at [`components.css:4691-4697`](../src/dual_research/ui/static/components.css#L4691).

**Files.** [`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) (new `ItemCardLifecycleSection`, replace `ItemCardThreadView` call site in `ItemCardDQBody` / `ItemCardIssueBody` / `ItemCardCommentBody`); [`components.css`](../src/dual_research/ui/static/components.css) (the `.lc-row*` rules at line 1202-1224 are repurposed and extended; add `.item-card__lifecycle-section`/`-hd` rules; extend the collapse block; drop the orphaned `.item-card__lifecycle` chip-cluster rules + `.item-card__lifecycle-sep` if no other call site remains); [`composed-components.css`](../design-system/assets/styles/composed-components.css) (mirror).

### 2.7 — C7: Source-request signal — blue evidence-needed chip + lifecycle-row extras

**DS citation.** [`design-system/SPEC.md`](../design-system/SPEC.md) §4.7 (sources segment) + §9.4 (composition rules — icon-only chip variant).

**Live currently.** [`run-detail.jsx:1887-1894`](../src/dual_research/ui/static/run-detail.jsx#L1887) emits `<Chip tone="warn" leadingIcon=alert label="evidence needed" />` — full-text warn-toned chip. No source-request / source-provided signals in the lifecycle rows because the lifecycle rows themselves don't exist yet (§2.6 introduces them).

**Target (per iter-9 + iter-13).** Replace the evidence-needed chip with `<Chip tone="info" iconOnly leadingIcon=link title="Evidence needed — addresses must cite consulted sources." aria-label="Evidence needed" />`. The chip renders as a small (28 × 28 px) blue icon-only pill with a native browser tooltip on hover; the previous full-text label is gone (text moves to the `title` attribute).

In the lifecycle rows (§2.6), inject two extras when conditions are met:

- The raise row gets a `[🔗 source requested]` extras chip when `item.evidenceRequired === true`.
- The first Claude/GPT transition gets a `[🔗 source provided]` extras chip when the card has ≥ 1 evidence record.

Per-row attribution chip in `.source-row__head` (a small `[provider-icon · R<N>]` mono chip showing which round + agent provided that source) is added in §2.8.

**Files.** [`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) (`evidenceModifierChip` rewrite to icon-only; extras chip injection in `ItemCardLifecycleSection`); [`components.css`](../src/dual_research/ui/static/components.css) (`.chip.chip-icon-only` variant if not yet present, evidence-chip color rules); [`composed-components.css`](../design-system/assets/styles/composed-components.css) (mirror).

### 2.8 — C8: Sources segment — right-aligned attribution + title truncation

**DS citation.** [`design-system/SPEC.md`](../design-system/SPEC.md) §4.7 (sources segment).

**Live currently.** [`run-detail.jsx:1420-1437`](../src/dual_research/ui/static/run-detail.jsx#L1420) renders `.source-row__head` as `<chev> <title> {attributionChip} <host>` inline — attribution sits inline between title and host. No `margin-left: auto`. No `max-width` / ellipsis on the title. First-row pre-expand IS already wired at [`run-detail.jsx:1990`](../src/dual_research/ui/static/run-detail.jsx#L1990) (`defaultExpanded={i === 0}`) — kept.

**Target (per iter-14).** Add to `components.css`:

```css
.source-row__attribution { margin-left: auto; }
.source-row__title { max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
```

The attribution chip itself is rendered per iter-13 as `<Chip mono leadingIcon=AgentIcon label="R<N>" title="Provided by <Agent> in round <N>" />`.

**Files.** [`run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) (verify attribution-chip rendering at [`run-detail.jsx:1432`](../src/dual_research/ui/static/run-detail.jsx#L1432) carries the mono+icon contract; adjust if not); [`components.css`](../src/dual_research/ui/static/components.css) + [`composed-components.css`](../design-system/assets/styles/composed-components.css).

---

## 3. User stories & acceptance criteria

### 3.1 — User stories

> **US1.** As a `researcher` reviewing a run, I want the Resolved section to be unfolded by default in P0/P2/P4, so that I can scan the resolved items without an extra click on the most common review path.

> **US2.** As a `researcher` on a wide-screen monitor, I want a single-row filter header with kind badges on the left and segmented agent + status controls on the right (each option labelled with its count), so that I can pick a slice of the critique without horizontal scanning or guessing what each chip filters.

> **US3.** As a `researcher` on a narrower viewport (laptop or half-screen), I want the same filter header to collapse to icon + count only — never wrap to two rows — so that the critique pane keeps its predictable single-row chrome.

> **US4.** As a `researcher` scanning a phase, I want collapsed critique cards to be the same compact height as the timeline cards so the two panes feel like one workspace.

> **US5.** As a `researcher` opening a critique card, I want to see the full lifecycle (raised → addressed → resolved/capped) as a sequence of provider-attributed rows with quotes, so that I can follow who said what in what round without click-spelunking.

> **US6.** As a `researcher` reviewing source-backed items, I want a clear blue signal when sources were requested and provided, so that I can tell at a glance which items have an evidence trail.

### 3.2 — Acceptance scenarios (BDD)

> **Scenario 1 — C1: Resolved unfolded by default.**
> GIVEN the run-detail page loads on phase P0, P2, or P4, AND the phase has ≥ 1 resolved item,
> WHEN no user interaction has occurred,
> THEN the `.crit-group` whose title is "Resolved" renders with `data-collapsed="false"` AND all its `.item-card` children are visible.

> **Scenario 2 — C2: Wide filter header.**
> GIVEN the viewport width is ≥ 1800px,
> WHEN the critique filter bar renders,
> THEN four `.chip[data-kind-filter]` badges (Q / D / I / C) appear in `.kind-tabs` on the left, AND the right cluster contains two `.tab-group-solid` segmented controls (agent then status), AND every option in those segments carries a `(N)` count label, AND no element with text "All" appears in either segment, AND the agent chips contain `.chip-leading-icon` with brand SVGs (not `.chip-dot`).

> **Scenario 3 — C3: Narrow filter header.**
> GIVEN the viewport width is ≤ 1799px,
> WHEN the critique filter bar renders,
> THEN `.chip[data-kind-filter] .chip-label` is hidden AND `.tab-group-solid .chip .chip-value` is hidden AND `.crit2 .bar2.crit-filter-row` has computed `flex-wrap: nowrap` AND the bar's height equals the timeline `.tl__head` height (within 1px).

> **Scenario 4 — C4: Collapsed card height matches timeline.**
> GIVEN an `.item-card[data-expanded="false"]` inside the critique pane,
> WHEN it renders,
> THEN its computed height equals the timeline `.tl-thread` collapsed card height within 1px (target: 36px ± 1).

> **Scenario 5 — C5: Collapsed card head pattern.**
> GIVEN a collapsed `.item-card` whose `data-raised-by` is `claude` or `gpt`,
> WHEN it renders,
> THEN the head's first five chips are, in order: provider chip (Claude or GPT with brand SVG) · round chip with label matching `/^Raised · R\d+$/` · kind chip (Q/D/I/C with `.cat-bubble`) · optional evidence-needed chip · spacer · state chip with label matching `/^(Resolved|Capped|Acknowledged|Withdrawn|Addressed|Open|Drift)( · .+)? · R\d+$/`.
> GIVEN a collapsed `.item-card` whose `data-raised-by` is `system`,
> WHEN it renders,
> THEN the head's first chip is the System chip (gear icon, idle-tinted) instead of a provider chip; the remaining order is unchanged.

> **Scenario 6 — C6: Expanded card lifecycle stack.**
> GIVEN an `.item-card[data-expanded="true"]`,
> WHEN it renders,
> THEN the body contains exactly one `.item-card__lifecycle-section` with a `LIFECYCLE` overline header (text content matches `/^LIFECYCLE$/i` after trim), AND every `.lc-row` child has computed `align-self: stretch`, AND every `.lc-row > .lc-row-chips` left edge is within 1px of every other `.lc-row > .lc-row-chips` left edge.

> **Scenario 7 — C7: Source-request signal.**
> GIVEN an expanded `.item-card` whose underlying item has `evidenceRequired === true`,
> WHEN it renders,
> THEN exactly one chip in `.item-card__head` has class `tone-info` AND has no visible `.chip-label` text AND has a non-empty `title` attribute AND has a `link` Material icon, AND the first `.lc-row` (the raise row) inside `.item-card__lifecycle-section` contains an extras chip whose text content includes the substring "source requested".

> **Scenario 8 — C8: Sources segment chrome.**
> GIVEN an expanded `.item-card` with ≥ 1 source,
> WHEN the `.item-card__sources` segment renders,
> THEN each `.source-row__head .source-row__attribution` has computed `margin-left: auto` (right-aligned), AND `.source-row__head .source-row__title` has computed `max-width: 280px` with `text-overflow: ellipsis`, AND the first `.source-row` has `aria-expanded="true"` (pre-expanded showing URL / fetched / search query / context excerpt).

---

## 5. Out of scope

- **Drift 3.E — Resolved-group title split by terminal state.** Deferred to a follow-up dev spec to be drafted post-merge. Splitting Resolved into per-state buckets (Resolved / Acknowledged / Capped / Withdrawn) per [`design-system/SPEC.md`](../design-system/SPEC.md) §9.5 vocabulary is its own change; this spec only changes Resolved's default collapsed/expanded state (§2.1).
- **Drift 3.F / 3.G / 3.H — Σ Summary cluster.** Deferred to a follow-up dev spec to be drafted post-merge. Bar-1 totals on the Σ tab (3.F), Σ body's inline-style cleanup (3.G), and the DS-vs-live Σ divergence (3.H) are coupled to each other but independent of the V2 promotion. This spec touches no Σ Summary code path.
- **Timeline pane V2 → live promotion.** Will be its own spec.
- **Canvas skill regeneration logic.** Will be its own spec.
- **Full DS/live parity backfill for `composed-components.css`.** The DS file is 2,423 lines vs the live file at 5,337 lines for the critique-pane region alone. Spec 0203 mirrors ONLY the V2-delta classes touched here. A follow-up DS-backfill spec covers the existing gap.
- **`_resolveAgent` mapping audit beyond the orchestrator/system path.** V2.C verifies the `orchestrator` → SystemChip path only. Broader actor-resolution work is a separate concern.

---

## 6. Test plan

- [ ] All three target files appear in the commit diff: `git diff --name-only main...HEAD` includes `src/dual_research/ui/static/components.css` AND `design-system/assets/styles/composed-components.css` AND `src/dual_research/ui/static/run-detail.jsx`. Mitigates the DS/live drift risk (§7).
- [ ] Every new or modified class in `components.css` has an identical rule in `composed-components.css` (selector + declarations match modulo whitespace). Verified by a diff-comparison script run as a one-off check in the PR description.
- [ ] Playwright test asserts BDD Scenario 1 (Resolved unfolded by default) passes on the `20260521-010637-dvs-backend-language-choice` anchor run for all three of P0, P2, P4.
- [ ] Playwright test asserts BDD Scenario 2 (wide filter header composition) at viewport width 1920px.
- [ ] Playwright test asserts BDD Scenario 3 (narrow filter header) at viewport width 1440px AND at 1800px (the breakpoint edge — must be wide) AND at 1799px (must be narrow).
- [ ] Playwright test asserts BDD Scenario 4 (collapsed card height ≤ 37px and ≥ 35px).
- [ ] Playwright test asserts BDD Scenario 5 (head chip order) for at least one Claude-raised, one GPT-raised, and one system-raised item from the anchor run.
- [ ] Playwright test asserts BDD Scenario 6 (lifecycle section + alignment) on an expanded card with ≥ 3 transitions.
- [ ] Playwright test asserts BDD Scenario 7 (evidence-needed chip + source-requested extra) on a P2 card with `evidenceRequired === true`.
- [ ] Playwright test asserts BDD Scenario 8 (source-row chrome + first-row pre-expanded).
- [ ] Manual smoke: open the live-deployed PR preview at all four phase tabs (P0 / P2 / P4 / Σ) for the anchor run; the Σ tab visually unchanged from pre-merge (this spec touches no Σ code).
- [ ] `uv run pytest tests/ -q` passes.
- [ ] No regression in the timeline pane (the file edits scope to critique-pane classes; the timeline shares some primitives like `.cat-bubble` and `.tab-group-solid` — confirm timeline visual unchanged via a screenshot diff on the anchor run's Timeline tab).

---

## 7. Risks

- **DS/live file drift (severity: catastrophic).** If `components.css` ships changes that don't land in `composed-components.css`, the design system silently goes out of date and future specs cite a stale reference. **Mitigation:** §6 Test plan first two checkboxes verify both files appear in the commit AND the new/modified rules match. The reviewer is asked to spot-check this in the PR.

- **No-op risk on C-items (severity: high — already burned us in spec 0165 §2.1).** A "verify against current code" gap means a spec ships CSS that's already in place. **Mitigation:** every §2.N above cites the live file + line and quotes (or describes) the current rule. The spec author has read every cited location.

- **`align-self: stretch` regression on `.lc-row` (severity: high — load-bearing for C6).** The alignment rule from V2.C is the kind of thing a future "clean up" pass might delete because it "looks like a default". **Mitigation:** §2.6 explicitly names this rule as load-bearing AND BDD Scenario 6 asserts the per-row left-edge alignment within 1px — a Playwright test will catch any regression on the next CI run.

- **Click-handler binding: card head toggle vs. full-view modal (severity: medium).** The current head click toggles `data-expanded` via [`run-detail.jsx:1975`](../src/dual_research/ui/static/run-detail.jsx#L1975) `onClick={toggleExpanded}`. If a full-view modal button is added in-head, its `onClick` must `stopPropagation` (mirroring `handleSourcesChipClick` at [`run-detail.jsx:1799-1822`](../src/dual_research/ui/static/run-detail.jsx#L1799)) so it doesn't also collapse the card. **Mitigation:** §2.5 does NOT add a full-view modal button — that stays out of scope here. If one is added in a follow-up, the implementer extends §2.5's BDD Scenario 5 with a "click full-view does not toggle expanded" assertion.

- **Class collision on `.item-card__lifecycle` (severity: medium).** The legacy class at [`components.css:4542`](../src/dual_research/ui/static/components.css#L4542) is the OLD head-chip cluster (kept alive by the OLD lifecycleChip render path). V2.A renames the new expanded-body wrapper to `.item-card__lifecycle-section` to avoid the collision. **Mitigation:** §2.6 spells out the rename AND removes the orphaned `.item-card__lifecycle` chip-cluster rules once §2.5's head rebuild drops the call site. The PR diff will show the removal.

- **Partial revert difficulty.** If C5 ships fine but C6 needs revert, the JSX changes to `ItemCardDQBody` / `ItemCardIssueBody` / `ItemCardCommentBody` (§2.6) are intertwined with the head rebuild (§2.5) through shared transition-parsing logic. **Mitigation:** revert is at the spec level (revert the merge commit). If a finer revert is needed, the implementer adds component-level feature flags in a follow-up spec — out of scope here per spec 0157 bundle-by-default heuristic.

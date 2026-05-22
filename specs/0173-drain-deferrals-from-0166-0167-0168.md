---
kind: dev
spec: "0173"
slug: drain-deferrals-from-0166-0167-0168
title: "Drain deferrals — pulse-info dot, .tab-group-solid rename, segment counts, item-card head/lifecycle/sources/collapse, upstream [object Object] fix"
type: new-feature
label: new-feature
version_bump: MINOR
target_version: TBD
status: queued
queue_position: 2
depends_on: ["0166", "0167", "0168"]
complexity: L
created: 2026-05-22
queued_at: "2026-05-22T21:05:00Z"
started_at: ""
merged_at: ""
deployed_at: ""
pr: ""
handover: ""
failure_step: ""
source_session: queue-drain-cleanup-2026-05-22
promoted_from_draft: ""
---

# Spec 0173 — Drain deferrals from 0166 / 0167 / 0168

> **Type:** new-feature  |  **Complexity:** L  |  **Depends on:** 0166, 0167, 0168 (catalogue of work those specs nominally promised but did not ship)
> **Bump:** MINOR — visible feature delivery on every run-detail page that completes what specs 0166–0168 originally specified. No schema or API change.
> **Evidence:** During a `/dev-queue-run` on 2026-05-22, the agent shipped specs 0165–0168 in rapid succession and made repeated judgment calls to skip / defer functionality from each. The CHANGELOG entries flag the deferrals; the spec frontmatter flips to `status: deployed` regardless. Product owner reviewed the deployed app and noticed the gaps — specifically that **DS-first workflow integrity was broken**: the design-system rule (since spec 0160) is that every spec lands its DS changes before the live impl, and the deferred items are exactly the DS-first changes that didn't follow through. This spec is the cleanup pass.

---

## 1. Context

The DS-first contract (locked in spec 0160 onward): every UI spec lands changes in the order `design-system/SPEC.md` → `design-system/assets/styles/composed-components.css` → `design-system/assets/Design System v2.html` → `src/dual_research/ui/static/components.css` → `src/dual_research/ui/static/run-detail.jsx` (or `shared.jsx`). Newer specs supersede older specs — if 0166 redefines a chip behaviour that 0138 originally specified, 0166 wins.

The queue-drain on 2026-05-22 deployed five specs (0164–0168) in ~70 minutes. During each cycle the agent made local judgment calls to skip functionality:

- **0166 §2.5 (dot-color rewire)** — skipped on the (wrong) argument that it would regress spec 0138's brand-color dot. Newer spec wins; 0138 is superseded.
- **0166 §2.4 (upstream `[object Object]` root-cause)** — only the defensive guard at `src/dual_research/ui/static/run-detail.jsx:~1155` shipped; the upstream data-layer bug that puts an object into `item.round` was not located or fixed.
- **0167 §2.1 (`.fgroup` → `.tab-group-solid` rename)** — skipped on the (incomplete) argument that the existing `.fgroup .ft.is-active` rule already produces the lifted-tile contract. DS canonical naming wins; live must follow.
- **0167 §2.2 (per-segment counts on agent + status filter buttons)** — skipped on substantial-scope grounds.
- **0168 §2.2 / §2.4 / §2.5 / §2.6 / §2.7 / §2.8 / §2.9** — only §2.1 (M3 card frame catch-up) shipped; the other 7 sub-sections of the L-complexity spec did not.

The deferral pattern was justified each time as "shipping a subset to keep the queue drain bounded" — defensible per cycle, but cumulative result is that the dashboard reads `status: deployed` for 0166/0167/0168 while the visible app is missing roughly half of what those specs promised. This spec catalogues every deferred item and ships them all under one cycle.

The deferred 0168 §2.3 (drop ID chip) is **explicitly NOT covered here** — spec 0172 (queued at position 5 after this spec inserts at position 2) covers it together with a separate markdown-rendering regression.

---

## 2. Proposed change

Eleven subsections, one per deferred item. Each subsection follows the DS-first ordering rule: `SPEC.md` → `composed-components.css` → `Design System v2.html` → `src/dual_research/ui/static/components.css` → `src/dual_research/ui/static/run-detail.jsx` (or `shared.jsx`). Implementer must apply the DS-side changes first in every subsection before touching `src/`.

### 2.1 — `.activity-dot` info-blue + `pulse-info` halo on `.as.in-header.is-live` (cleans up 0166 §2.5)

**Now.** Spec 0166 added the `@keyframes pulse-info` definition to both CSS files. The wiring of that keyframe to the `.as.in-header.is-live` strip's `.activity-dot` was **not** applied — the timeline-strip dot still uses the per-agent brand color (`var(--p-sable)` / `var(--p-sage)`) and the spec-0138 `pulse-a` / `pulse-b` keyframes via the `<Dot color={dotColor} pulse={live ? 'pulse-a' : null} />` call in `TimelineAgentPill` ([src/dual_research/ui/static/run-detail.jsx:~167](src/dual_research/ui/static/run-detail.jsx)).

**After.** When the strip is `.is-live`, the activity-dot background flips from `var(--md-outline)` (grey when not live) to `var(--p-info)` (info-blue when live), and animates with the canonical `pulse-info` halo (now defined). Mirrors the StatusBadge `.sb-running > .dot` pattern. Per spec 0166 §2.5 verbatim:

```css
.as.in-header.is-live .activity-dot {
  background: var(--p-info);
  animation: pulse-info 2s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  .as.in-header.is-live .activity-dot {
    animation: none;
    box-shadow: none;
  }
}
```

The JSX must expose an `.activity-dot` class on the dot element so the CSS can target it. In `TimelineAgentPill` the dot is currently rendered via `<Dot color={dotColor} pulse={...} />` — that component must accept an additional class prop, or the wrapping span gains `className="activity-dot"`. The simpler path: change `<Dot>` to apply `className="activity-dot"` when called from `TimelineAgentPill`, OR replace the `<Dot>` call with an inline `<i className="activity-dot" />` and let the CSS own all the styling.

When `.is-live` is **off**, the dot reverts to `var(--md-outline)` (grey, no animation) — i.e. the CSS provides the not-live default, and JSX's inline `style={{ background: dotColor }}` from `composeAgentActivity` is dropped. The dot's color is purely CSS-driven from here forward.

**Note on supersession.** The parent-agent's "this would regress 0138's brand-identity dot" argument was wrong. Spec 0166 §2.5 is the newer contract; 0138 yields. The brand-color dot reading was a 0138 design decision that 0166 rolled back.

**Files to change (DS-first):**
- `design-system/SPEC.md` §4.4 — codify the info-blue live-dot rule.
- `design-system/assets/styles/composed-components.css` — add the `.as.in-header.is-live .activity-dot` block + reduced-motion fallback.
- `design-system/assets/Design System v2.html` §16 — re-render the in-header AgentStrip example with a live state showing the info-blue dot.
- `src/dual_research/ui/static/components.css` — mirror the rule.
- `src/dual_research/ui/static/run-detail.jsx` — apply `.activity-dot` class to the dot element inside `TimelineAgentPill`, drop the inline `dotColor` style binding.

### 2.2 — Upstream `[object Object]` root-cause fix (cleans up 0166 §2.4)

**Now.** The defensive guard at [src/dual_research/ui/static/run-detail.jsx:~1155](src/dual_research/ui/static/run-detail.jsx) type-checks `item.round` and falls back to `<SystemChip /><ErrorChip />` if non-numeric. This catches the symptom. The upstream code path that puts an object into `item.round` is **not** identified or fixed.

**After.** Locate where `item.round` is constructed for Phase 4 cross-review turn cards. The anchor run is `20260521-010637-dvs-backend-language-choice` Phase 4. Likely candidates:

- `src/dual_research/ui/static/live-data.jsx` — the live-data shaping path that constructs the `item` records consumed by `TlTurnRow`.
- `scripts/spec_lifecycle/` — unlikely (this is the lifecycle aggregator for specs, not run-detail items).
- Server-side run-detail JSON shaping in `src/dual_research/ui/server.py` or related.

Reproduce: open the anchor run, expand Phase 4, find the turn card that triggers the defensive guard, and trace what `item.round` is at the moment `<TlTurnRow item={item} ... />` is rendered. The defensive guard's `else` branch is the trace point.

After the upstream bug is fixed, the defensive guard at §2.4 still ships — it's a safety net for future regressions. The guard does not get removed.

**Files to change (likely):**
- `src/dual_research/ui/static/live-data.jsx` — or wherever the field is constructed.
- A regression test under `tests/contract/` or `tests/ui/` that asserts every `item.round` is `null | number` (never an object) across all phases.

**Out-of-scope for this subsection:** schema validation in the orchestrator (e.g. enforcing turn-record shape at write time). That's a separate hardening spec.

### 2.3 — `.fgroup` → `.tab-group-solid` rename, `.ft` → `.tab-solid` (cleans up 0167 §2.1)

**Now.** The bar-2 critique-pane filter clusters use `.fgroup` + `.fgroup .ft` markup in JSX ([src/dual_research/ui/static/run-detail.jsx:~7212](src/dual_research/ui/static/run-detail.jsx)) + CSS ([src/dual_research/ui/static/components.css:~2259](src/dual_research/ui/static/components.css)). The DS canonical name (per [design-system/SPEC.md](design-system/SPEC.md) §4.1 + the [design-system/assets/Design System v2.html](design-system/assets/Design System v2.html) §12 reference rendering) is `.tab-group-solid` containing `.tab-solid` options. The active state is `data-active="true"` on the option (DS) vs. `.is-active` class (live).

**After.** Live JSX + CSS rename to the DS canonical names. The CSS rules at components.css:~2259 lose the `.fgroup` selector and gain `.tab-group-solid`; `.ft` → `.tab-solid`; the `.is-active` modifier becomes `[data-active="true"]` attribute selector. The lifted-tile contract (`background: var(--md-surface); color: var(--md-on-surface); box-shadow: var(--md-elev-1)`) is preserved verbatim — only the selector names change.

JSX: every `className={`ft${... ? ' is-active' : ''}`}` becomes `className="tab-solid" data-active={... ? 'true' : 'false'}`. Every `<div className="fgroup">` becomes `<div className="tab-group-solid">`.

The DS canonical CSS at [design-system/assets/styles/composed-components.css](design-system/assets/styles/composed-components.css) already uses `.tab-group-solid` + `.tab-solid` per spec 0167 §2.1's CSS block (which lives in the DS canonical file but never got mirrored to live). Verify the DS canonical CSS matches the spec; if not, fix the DS too.

**Files to change (DS-first — verify DS canonical is correct first):**
- `design-system/SPEC.md` §4.1 — codify the canonical names + the `data-active="true"` attribute pattern (instead of `.is-active` class).
- `design-system/assets/styles/composed-components.css` — verify `.tab-group-solid` + `.tab-solid` + the lifted-tile state rule are all present per spec 0167 §2.1. Drop the `[data-active="true"]` attribute selector if it isn't there yet.
- `design-system/assets/Design System v2.html` §12 — verify the rendered markup uses the canonical names.
- `src/dual_research/ui/static/components.css` — rename `.fgroup` → `.tab-group-solid`, `.ft` → `.tab-solid`, `.is-active` modifier → `[data-active="true"]` attribute selector.
- `src/dual_research/ui/static/run-detail.jsx` — rename the JSX class names + flip the active-state expression from class concatenation to `data-active` attribute.

### 2.4 — Per-segment counts on agent + status filter buttons (cleans up 0167 §2.2)

**Now.** The agent filter buttons (`All`, `Claude`, `GPT`) and status filter buttons (`All`, `Open`, `Resolved`, `Drift`) in the critique bar 2 render label-only — no counts. The data is already computed for the kind-cluster (`kindCounts.{all,issues,comments,questions,disagreements}`); the agent + status equivalents are not.

**After.** Compute per-button counts against the active-phase filtered item list:

- `agentCounts.all` = total items in the active phase
- `agentCounts.claude` = items where `item.raisedBy === 'claude'`
- `agentCounts.gpt` = items where `item.raisedBy === 'gpt'`
- `statusCounts.all` = total items in the active phase
- `statusCounts.open` = items where `item.status === 'open'`
- `statusCounts.resolved` = items where `item.status === 'resolved'`
- `statusCounts.drift` = items where `item.status === 'drift'`

Plumb into the rendered button as a trailing `<span class="chip-value">(N)</span>` element. Per spec 0167 §2.1's CSS, the `(` and `)` parens are produced via `::before`/`::after` content, so the span text is the bare number.

The Drift status count must **always** render even when 0 — that's the chip-stability rule from 0167 §2.2 (otherwise the button width fluctuates when drift items appear/disappear mid-run).

The All count must always render even at 0.

**Narrow-mode rule.** At viewports ≤ 1799 px, the `.chip-value` spans are hidden via `display: none` per spec 0167 §2.1's media-query block — already in the DS canonical CSS. Verify the live CSS mirrors that block. (Labels stay; the parens hide.)

**Files to change:**
- `design-system/SPEC.md` §4.1 — codify that every option in both segments carries its own count chip, including All and Drift even at 0.
- `design-system/assets/styles/composed-components.css` — verify the `.chip-value` rule from spec 0167 §2.1 is present (with `::before` `(` + `::after` `)`).
- `src/dual_research/ui/static/components.css` — mirror.
- `src/dual_research/ui/static/run-detail.jsx` — compute `agentCounts` + `statusCounts` from the filtered item list (next to the existing `kindCounts` derivation); render `<span className="chip-value">{count}</span>` after the label in every `.tab-solid` button in both segments.

### 2.5 — Card head rebuild (cleans up 0168 §2.2)

**Now.** The `.item-card__head` ([src/dual_research/ui/static/run-detail.jsx](src/dual_research/ui/static/run-detail.jsx), search for `item-card__head`) renders a sequence of chips that includes the ID chip first (low-value, cryptic), then various provider/round/kind/state chips, then a sources chip (redundant with the in-card SOURCES overline).

**After.** Per spec 0168 §2.2, the new head composition is `[provider chip] [kind chip] [lifecycle chip] [modifier chips...] [status chip — right-aligned]`. The ID chip is dropped from the head (spec 0172 implements that drop separately for the cryptic `I-DEQ-PLAN-C-01` form; this spec drops the simpler `Q7` form too). The sources chip is dropped (redundant with the per-card `SOURCES (N)` overline).

**Composition order rule.** Provider FIRST, activity / kind SECOND, lifecycle / modifier chips THIRD, status chip RIGHT-ALIGNED, per [design-system/SPEC.md](design-system/SPEC.md) §9.4.

**Files to change:**
- `design-system/SPEC.md` §4.1 + §4.8 — codify the new head composition (item-card flavor).
- `design-system/assets/styles/composed-components.css` — adjust `.crit-card-head` / `.item-card__head` rule if any chip-specific overrides need removal.
- `design-system/assets/Design System v2.html` §13 — re-render the ItemCard example with the new head.
- `src/dual_research/ui/static/components.css` — mirror.
- `src/dual_research/ui/static/run-detail.jsx` — rewrite the `.item-card__head` JSX render in the critique item-card render path.

### 2.6 — Round / state lifecycle chip with provenance (cleans up 0168 §2.4)

**Now.** The round chip reads flat — `round 1`. The state chip reads flat — `resolved`. The two are separate; the "raised in r1, resolved in r3" narrative isn't visible without scrolling the transitions list.

**After.** Single composite lifecycle chip (or chip cluster) that carries the full arc:

- For open items: `raised · r1 · Claude` (kind tone)
- For resolved items: `raised r1 Claude · resolved r3 GPT` (chip cluster, two micro-chips inside)
- For drift items: `raised r1 · drift r3` (err tone)

The chip uses the existing `.chip` primitive ([design-system/SPEC.md](design-system/SPEC.md) §3) with provider micro-icons inline (the AgentIcon at 10×10).

**Files to change:**
- `design-system/SPEC.md` §4.1 + §9.5 (vocabulary) — codify the lifecycle chip vocabulary: `raised`, `resolved`, `drift` (already in §9.5).
- `design-system/assets/styles/composed-components.css` — new `.lifecycle-chip` rule or composition guidance.
- `design-system/assets/Design System v2.html` §13 — render an example.
- `src/dual_research/ui/static/components.css` — mirror.
- `src/dual_research/ui/static/run-detail.jsx` — construct the lifecycle chip from `item.raisedAt`, `item.raisedBy`, `item.resolvedAt`, `item.resolvedBy` fields (verify these exist; otherwise plumb).

### 2.7 — Evidence-needed banner inline (cleans up 0168 §2.5)

**Now.** Cards with `item.evidenceRequired === true` render an `.item-card__evidence-needed` element as a full body row carrying the text "Evidence needed — addresses must cite consulted sources." (or similar). Adds ~36 px vertical space per card.

**After.** Replace the full-body banner with an inline chip in the head: `<Chip tone="warn" leadingIcon={<Icon.Warning size={12} />} label="evidence needed" />`. The chip sits among the head chips after the lifecycle chip. The card no longer carries a vertical-space penalty for evidence-required items.

**Files to change:**
- `design-system/SPEC.md` §4.1 — codify the evidence-required chip composition.
- `design-system/assets/styles/composed-components.css` — drop the `.item-card__evidence-needed` body-row rule if any chip-specific overrides need removal.
- `design-system/assets/Design System v2.html` §13 — render an example.
- `src/dual_research/ui/static/components.css` — mirror.
- `src/dual_research/ui/static/run-detail.jsx` — move the conditional from `.item-card__body` to `.item-card__head`; render as `<Chip>` instead of `<div>`.

### 2.8 — Resolver identity on resolved cards (cleans up 0168 §2.6)

**Now.** When a card is resolved, the state chip reads `resolved · r3` — round, no resolver. The "Claude resolved this" vs "GPT resolved this" signal is buried in the transitions list inside the expanded view.

**After.** The state chip gains the resolver. Composition: `resolved · r3 · Claude` (with AgentIcon at 10×10 leading the resolver name). When the resolver is `auto` (system resolved by hash-match or cap), the chip reads `resolved · r3 · auto` with the SystemChip leading-icon. Subsumed by §2.6 above if the lifecycle chip composition includes the resolver — implementer may merge §2.6 + §2.8 into a single chip if the markup is cleaner.

**Files to change:** see §2.6 above; this is a sub-aspect.

### 2.9 — Expanded view lifecycle scaffolding (cleans up 0168 §2.7)

**Now.** Expanded cards render: body text → transitions list (flat) → footer → sources. The raise → respond → resolve arc isn't visually scaffolded — each transition row reads as discrete metadata; the narrative thread isn't legible.

**After.** Restructure the expanded layout to use the QuestionThread anatomy from [design-system/SPEC.md](design-system/SPEC.md) §4.2 — the same bubble pattern that drives the question-thread expanded view in the critique pane v1. Each transition (`raised`, `pushback`, `conceded`, `resolved`) renders as a tonal-tinted message bubble carrying the agent identity, round, verdict pill, and the quote inside. The raise-respond-resolve arc reads chronologically top-to-bottom.

This is the largest subsection — it restructures the expanded card from a flat list to a threaded conversation view.

**Files to change:**
- `design-system/SPEC.md` §4.1 + §4.2 — codify that the item-card expanded view shares the QuestionThread anatomy.
- `design-system/assets/styles/composed-components.css` — verify QuestionThread rules apply correctly to the item-card expanded body; add scoped overrides if needed.
- `design-system/assets/Design System v2.html` §13 — render an expanded ItemCard example using the QuestionThread bubble anatomy.
- `src/dual_research/ui/static/components.css` — mirror.
- `src/dual_research/ui/static/run-detail.jsx` — rewrite the expanded-card render. The transitions array is already in `item.transitions`; restructure each transition into a bubble.

### 2.10 — Per-source attribution (cleans up 0168 §2.8)

**Now.** When a card has sources, they render as plain `.source-row` instances ([src/dual_research/ui/static/shared.jsx](src/dual_research/ui/static/shared.jsx) — see SourceRow primitive). Each row shows title / URL / search-query / fetched / excerpt. No per-source attribution showing which agent provided the source in which round.

**After.** Each source row gains an attribution chip: `<Chip tone={agent === 'claude' ? 'claude' : 'gpt'} size="sm" leadingIcon={<AgentIcon size={10} />} label={`r${round}`} />`. The chip sits between the title and the host badge in the collapsed row state. When expanded, the chip remains visible at the same position.

The data: `source.provider` (`'claude' | 'gpt' | 'auto'`) and `source.round` (number) — verify these fields exist on the live data; plumb if not.

**Files to change:**
- `design-system/SPEC.md` §3 (SourceRow primitive) — codify the attribution chip slot.
- `design-system/assets/styles/composed-components.css` — adjust `.source-row` flex layout if needed.
- `design-system/assets/Design System v2.html` §13 — render an example.
- `src/dual_research/ui/static/components.css` — mirror.
- `src/dual_research/ui/static/shared.jsx` — extend `<SourceRow>` to accept `provider` + `round` props and render the chip.
- `src/dual_research/ui/static/run-detail.jsx` — plumb `source.provider` + `source.round` into each `<SourceRow>` call.

### 2.11 — Per-card collapse affordance (cleans up 0168 §2.9)

**Now.** Every `.item-card` renders fully always (head + body + transitions + footer + sources). Cards with sources occupy 200+ px each. Scanning the phase view requires scrolling.

**After.** Add `data-expanded` attribute to every `.item-card`. Default state is `data-expanded="false"` (head only visible). Clicking the head toggles. CSS hides `.item-card__body`, `.item-card__timeline`, `.item-card__sources` when `data-expanded="false"`:

```css
.item-card[data-expanded="false"] .item-card__body,
.item-card[data-expanded="false"] .item-card__timeline,
.item-card[data-expanded="false"] .item-card__sources {
  display: none;
}
.item-card[data-expanded="false"] .item-card__head {
  /* still clickable */
  cursor: pointer;
}
.item-card[data-expanded="true"]:hover { /* keep existing hover */ }
```

The first source row per card is pre-expanded (per spec 0168 §3.J): `.source-row` defaults to `aria-expanded="false"`, but the JSX sets `aria-expanded="true"` on the first source. Inside the JSX, the `<SourceRow>` calls inside the first card use `defaultExpanded={true}` for the first row.

**Keyboard accessibility.** The head element gains `role="button"`, `tabIndex={0}`, `aria-expanded`, and `onKeyDown` for Enter/Space (matching the timeline turn-card pattern from spec 0164).

**Files to change:**
- `design-system/SPEC.md` §4.1 — codify the default-collapsed behaviour + the keyboard contract.
- `design-system/assets/styles/composed-components.css` — `[data-expanded]` CSS rules.
- `design-system/assets/Design System v2.html` §13 — render collapsed and expanded examples.
- `src/dual_research/ui/static/components.css` — mirror.
- `src/dual_research/ui/static/run-detail.jsx` — add state per card (`useState(false)` for `isExpanded`), wire `onClick` + `onKeyDown`, set `data-expanded` attribute.

---

## 3. UX / behaviour

After this spec ships:

- **Live agent dot.** When Claude or GPT is mid-round, the in-header strip's activity dot pulses info-blue (`var(--p-info)`) with the canonical halo. The brand-color dot (sable/sage) is no longer used for the live state — brand identity reads off the strip's tint + 2 px left-border instead.
- **No more `[object Object]`** in card heads, ever — the upstream data-layer bug is fixed; the defensive guard remains as a safety net.
- **Critique bar 2** uses the canonical `.tab-group-solid` markup and shows per-segment counts: `All (13)`, `Claude (6)`, `GPT (7)`, `Open (0)`, `Resolved (13)`, `Drift (0)`. Drift count stays visible even at 0.
- **Critique item-cards** read with the new head composition: `[provider] [kind] [lifecycle] [modifiers] [status]` — no ID chip, no sources chip, no full-row evidence banner. The state chip carries the resolver identity (`resolved · r3 · Claude`). The expanded view shows a threaded conversation (QuestionThread anatomy). Sources show per-row provider + round attribution.
- **Item-cards default collapsed.** Phase views scan vertically with the head only; click to expand.

---

## 4. Data / schema deltas

- **§2.2** may require touching the Python aggregator or the live-data shaping path to fix the upstream `[object Object]` cause. No event-store schema change expected.
- **§2.6 + §2.8** rely on `item.raisedAt`, `item.raisedBy`, `item.resolvedAt`, `item.resolvedBy` fields. Verify these exist on the live shape; plumb from the underlying event stream if missing.
- **§2.10** relies on `source.provider` + `source.round` fields. Verify; plumb if missing.

No event-store / orchestrator / spec-lifecycle changes.

---

## 5. Out of scope

- **0168 §2.3 (drop ID chip)** — covered by **spec 0172** (queued at position 5 after this spec inserts at position 2). Spec 0172 also fixes a separate `**` markdown rendering bug.
- **0168 §2.1 (M3 card frame)** — already shipped under **spec 0168 v1.29.0** (PR #191).
- **0166 §2.1 / §2.2 / §2.3 (SystemChip + ErrorChip primitives + brief-card refactor)** — already shipped under spec 0166 v1.27.0.
- **0166 §2.6 (live-state elev-2 lift)** — already shipped under spec 0166 v1.27.0.
- **0167 §2.3 (bar-1 drift slot muted-at-zero)** — already shipped under spec 0167 v1.28.0.
- **0167 §2.4 / §2.5 / §2.6 (phase-tab P0 catch-up + kind-cluster order + drop "All" from kind cluster)** — already shipped under spec 0167 v1.28.0.
- **Orchestrator-side schema validation** of turn-record shape — separate hardening spec.
- **Critique pane drift-section behaviour, phase-tab Σ Summary tab body, bar-1 totals reset behaviour** — separate concerns from the critique iteration notes; not deferred from 0166/0167/0168 specifically.

---

## 6. Design-system gate

Cited DS sections being updated:

- `design-system/SPEC.md` §3 Primitives — SourceRow gains a `provider` + `round` slot (§2.10).
- `design-system/SPEC.md` §4.1 Critique pane — bar 2 segmented-control class names canonicalised (§2.3), per-segment count rule codified (§2.4), card head composition + collapse default + evidence-required inline + lifecycle chip + resolver identity codified (§2.5 / §2.6 / §2.7 / §2.8 / §2.9 / §2.11).
- `design-system/SPEC.md` §4.2 QuestionThread — confirmed to drive the item-card expanded view (§2.9).
- `design-system/SPEC.md` §4.4 Timeline pane — `.activity-dot` info-blue live rule codified (§2.1).
- `design-system/SPEC.md` §4.8 Critique card composition — head composition rule (§2.5).
- `design-system/SPEC.md` §9.5 Canonical vocabulary — lifecycle chip vocabulary already covered (`raised`, `resolved`, `drift`).

Files that MUST land in the same commit (typical UI spec rule):

- `design-system/SPEC.md`
- `design-system/assets/styles/composed-components.css`
- `design-system/assets/Design System v2.html`
- `src/dual_research/ui/static/components.css`
- `src/dual_research/ui/static/run-detail.jsx`
- `src/dual_research/ui/static/shared.jsx` (SourceRow extension)
- `src/dual_research/ui/static/live-data.jsx` (likely — for §2.2 upstream fix)
- `CHANGELOG.md`
- `pyproject.toml`
- `src/dual_research/__init__.py`

---

## 7. Test plan

- [ ] **§2.1 dot wiring** — render a run in live state. `.as.in-header.is-live .activity-dot` computed `background-color === rgb(<--p-info resolved>)`. Computed `animation` matches `pulse-info 2s ease-in-out infinite`. When `.is-live` is off, the dot is `var(--md-outline)` grey with no animation. Reduced-motion: animation `none`, no `box-shadow`.
- [ ] **§2.2 upstream fix** — render the anchor run `20260521-010637-dvs-backend-language-choice` Phase 4. The defensive guard does not fire. The previously-broken card renders `turn N` with the correct numeric index. New regression test asserts every `item.round` is `null | number` across the fixture.
- [ ] **§2.3 class rename** — `document.querySelectorAll('.crit2 .fgroup').length === 0`. `document.querySelectorAll('.crit2 .tab-group-solid').length === 2`. Each `.tab-solid` has `data-active="true"` or `data-active="false"` (no `.is-active` class). Computed active-state styling matches the lifted-tile contract (`background: var(--md-surface)`, `box-shadow: var(--md-elev-1)`).
- [ ] **§2.4 segment counts** — open a run with 13 critique items. The Agent segment shows `All (13) Claude (X) GPT (Y)` where X + Y = 13. The Status segment shows `All (13) Open (?) Resolved (?) Drift (?)`. Drift count is visible even when 0. At narrow viewport (≤ 1799 px) the `.chip-value` spans have `display: none`.
- [ ] **§2.5 head rebuild** — `.item-card__head` no longer contains an ID chip or a sources chip. Composition reads `[provider] [kind] [lifecycle] [modifiers...] [status]`. Status chip is right-aligned (computed `margin-left: auto` on a wrapping element).
- [ ] **§2.6 lifecycle chip** — for an open card raised by Claude in r1, the lifecycle chip reads `raised · r1 · Claude` with the AgentIcon. For a resolved card raised by Claude in r1 and resolved by GPT in r3, the chip reads `raised r1 Claude · resolved r3 GPT`.
- [ ] **§2.7 evidence inline** — a card with `item.evidenceRequired === true` has a `.chip.tone-warn` with the warning icon and label "evidence needed" in the head — not in the body. `.item-card__evidence-needed` body element no longer exists in the DOM.
- [ ] **§2.8 resolver identity** — a resolved card's state chip includes the resolver agent (`resolved · r3 · Claude` or `resolved · r3 · auto` for system resolutions). Visible without expanding the card.
- [ ] **§2.9 threaded expanded view** — expanding an item-card shows transitions as tonal-tinted bubbles (sable for Claude, sage for GPT) matching the QuestionThread anatomy. Each bubble carries the agent identity, round, verdict pill, and the quote inside.
- [ ] **§2.10 source attribution** — every `.source-row` shows a chip with the provider AgentIcon + round (`r3`). The chip sits between title and host badge.
- [ ] **§2.11 collapse default** — every `.item-card` has `data-expanded="false"` on initial render. Clicking the head sets `data-expanded="true"`. `.item-card__body`, `.item-card__timeline`, `.item-card__sources` have computed `display: none` when collapsed. Keyboard: Tab focuses the head, Enter/Space toggles, `aria-expanded` mirrors `data-expanded`.
- [ ] **Tests pass.** `uv run pytest tests/ -q` exits 0. `npm test` (vitest) passes.

---

## 8. Implementation steps (suggested order, DS-first throughout)

1. **§2.1** — light, isolated. Land the DS rule + live rule + JSX class change. Smoke against a live run.
2. **§2.3** — rename. Mechanical but spans 4 files. Run the test suite after.
3. **§2.4** — per-segment counts. Plumb the count derivations next to `kindCounts`. Verify Drift renders at 0.
4. **§2.7** — evidence inline. Small JSX move.
5. **§2.5** — head rebuild. Drops chips; reorders.
6. **§2.6 + §2.8** — lifecycle chip + resolver identity. Implement together since they're one chip in different states.
7. **§2.11** — collapse. Wire state, attributes, CSS.
8. **§2.10** — source attribution. Extend SourceRow + plumb data.
9. **§2.9** — expanded view scaffolding. The biggest restructure; do it last so smaller wins are visible first.
10. **§2.2** — upstream `[object Object]`. Bisect against the anchor run. Land the fix + regression test.
11. **CHANGELOG entry. Version bump.**

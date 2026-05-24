# Critique pane V2 — canonical snapshot (2026-05-24)

> **Purpose.** This is the canonical reference for the V2 critique-pane state that spec [0203](../../specs/0203-critique-v2-live-promotion.md) promotes from workshop to live. It freezes (a) the user-visible issues against the live app (C1–C8), (b) the patches on top of the iter-1→iter-15 lock that make the workshop state shippable to live (V2.A / V2.B / V2.C), (c) what stays out of scope, and (d) the file list the promotion commit touches.
>
> **Pixel target** is [`proposed.html`](./proposed.html) (workshop CSS stack iter-1→iter-15 plus the V2.A–C patches below).
> **Diff target** is [`live.html`](./live.html) (verbatim live-app dump from 2026-05-22).
> **Source of issues** is the Notion page [Critique & Timeline](https://www.notion.so/36999f3e507f8083b551f2c8fcbe46d3) (2026-05-23), section "Critique".

---

## 1. Background

The workshop at [`prototypes/critique-iteration/`](./) ran 15 iterations on 2026-05-22 ([NOTES.md](./NOTES.md)). The user audited the live app against the workshop state on 2026-05-23 ([Notion page](https://www.notion.so/36999f3e507f8083b551f2c8fcbe46d3)) and flagged eight discrepancies. This snapshot collapses the iter record + the Notion audit into a single index spec 0203 can cite verbatim.

The Notion page uses six "Issue" headings but contains eight distinct items because two headings are reused (two "Issue 3" + two "Issue 4"). The C-numbering below disambiguates.

---

## 2. User-flagged discrepancies (C1–C8)

Each row maps to a specific iter (or set) in [NOTES.md](./NOTES.md) and the corresponding Notion issue heading. The "Live currently" cell points at the live-app file + line that needs to change; the "Pixel target" cell points at the workshop artifact carrying the V2 behavior.

| C# | Title | Notion issue | NOTES.md iter | Live currently | Pixel target |
|---|---|---|---|---|---|
| C1 | Resolved unfolded by default (first section in P0/P2/P4 starts expanded) | Issue 1 | iter-4 + workshop collapse affordance §0.2 | [run-detail.jsx:7311](../../src/dual_research/ui/static/run-detail.jsx#L7311) `renderGroup(…, collapsed)` — caller hardcodes Resolved to collapsed; [components.css:2449-2450](../../src/dual_research/ui/static/components.css#L2449) `[data-collapsed="true"]` hides body | `proposed.html` `initCollapseState()` in [_inline-script.js:318](./_inline-script.js#L318) — wrapper sets `data-collapsed="false"` on every `.crit-group`, but V2.B (below) drops that because for promotion we only need Resolved-unfolded-by-default, not all-sections-unfolded |
| C2 | Wide filter header: four kind badges with cat-bubble on left + segmented agent + status on right + brand icons (Claude sunburst, OpenAI rosette) + no "All" buttons + per-option counts | Issue 2 | iter-1, iter-1.1, iter-1.2, iter-2, iter-3 | [run-detail.jsx](../../src/dual_research/ui/static/run-detail.jsx) Critique filter render still ships explicit "All" buttons + `chip-dot` agent identity (no brand icons); [components.css:1046-1052](../../src/dual_research/ui/static/components.css#L1046) `.crit2 .bar2.crit-filter-row` baseline rules exist; no `.tab-group-solid` wrapping around agent/status | [`proposed.html`](./proposed.html) `<style id="iter-1-ds-aligned-headers">` (lines 71-200ish) + JS injection in [_inline-script.js](./_inline-script.js) |
| C3 | Narrow filter header (viewport ≤1799px): kind badges drop text labels, segmented counts disappear, both sides stay on one row | Issue 3 (first occurrence) | iter-7.2, iter-7.3 | [components.css:1079-1099](../../src/dual_research/ui/static/components.css#L1079) `@media (max-width: 1799px)` already drops kind labels and segment-chip labels, BUT segment counts aren't dropped (no rule), and the row can wrap when content overflows (Notion screenshot: right side "disappears") | `proposed.html` iter-1 + iter-7.2 + iter-7.3 — `flex-wrap: nowrap !important` on `.bar2.crit-filter-row` AND `.kind-tabs`; `@media (max-width: 1799px) .tab-group-solid .chip .chip-value { display: none }` |
| C4 | Collapsed card height matches timeline `.tl-thread` (≈36px), not the current ~64px | Issue 3 (second occurrence — labelled "Issue 3:") | iter-7.1 | [components.css:4499-4513](../../src/dual_research/ui/static/components.css#L4499) `.item-card { padding: 12px 14px; gap: 10px; margin: 0; }` → ~64px head height; head has no explicit padding ([components.css:4528-4533](../../src/dual_research/ui/static/components.css#L4528)) | `proposed.html` iter-7.1 — `.item-card { padding: 0 }` + `.item-card__head { padding: 6px 12px; min-height: 0 }` → 36px collapsed |
| C5 | Collapsed card head pattern: `[Provider · Raised·R1 · Kind] [State · R<N>]` (with System chip in lead slot when actor is orchestrator/system) | issue 4 (lowercase) | iter-7, iter-8, iter-8.1, iter-10 | [run-detail.jsx:1969-1983](../../src/dual_research/ui/static/run-detail.jsx#L1969) head renders `[providerChip][kindChip][evidenceModifierChip]<spacer/>[lifecycleChip]` — no separate round chip; round is folded into the lifecycle chip's label; system fallback exists ([run-detail.jsx:1881](../../src/dual_research/ui/static/run-detail.jsx#L1881)) but emits `<SystemChip />` markup that differs from the iter-7 rebuild | `proposed.html` + [_inline-script.js:97-128](./_inline-script.js#L97) — JS rebuild emits `[provider][round "Raised·R<N>"][kind][...][state "<verb>·<icon?>·R<N>"]`; capitalised round/state labels per iter-8.1; resolver icon inside state chip per iter-10 |
| C6 | Expanded card: `LIFECYCLE` overline + sequence of `.lc-row` items, each with chip cluster (provider · round · verb · modifier?) above an italic-serif quote; left edges align across rows | Issue 4 (second occurrence — capitalised) | iter-12 | [run-detail.jsx:1518-1592](../../src/dual_research/ui/static/run-detail.jsx#L1518) renders `ItemCardThreadView` → `.item-card__qt-rows` / `.item-card__qt-row`/`__qt-chips`/`__qt-quote`; the new `.lc-row*` CSS at [components.css:1202-1224](../../src/dual_research/ui/static/components.css#L1202) IS defined but is unused by the live JSX | `proposed.html` iter-12 stylesheet + [_inline-script.js](./_inline-script.js) `parseTransition` + `.lc-row` injection (lines 175-220ish) |
| C7 | Source-request signal: blue `tone-info` evidence-needed chip in head (icon-only with hover tooltip), plus `[🔗 source requested]` / `[🔗 source provided]` extras in lifecycle rows | Issue 5 | iter-9, iter-13 | [run-detail.jsx:1887-1894](../../src/dual_research/ui/static/run-detail.jsx#L1887) emits `<Chip tone="warn" leadingIcon=alert label="evidence needed" />` — warn tone, full text label, no lifecycle-row extras | `proposed.html` iter-9 (`.chip.tone-info.chip-icon-only.no-dot.evidence-chip` with `title` attribute) + iter-13 (extras chip injection in lc-rows) |
| C8 | Sources segment: provider+round attribution chip right-aligned (`margin-left: auto`); title truncates at ~280px; first row pre-expanded | Issue 6 | iter-14 + iter-15 (sources-pre-expand kept; not the auto-expand of the whole card) | [run-detail.jsx:1420-1437](../../src/dual_research/ui/static/run-detail.jsx#L1420) `.source-row__head` renders `<chev><title><attribution><host>` inline; no right-alignment or max-width on title; first-row defaultExpanded already wired ([run-detail.jsx:1990](../../src/dual_research/ui/static/run-detail.jsx#L1990)) ✓ | `proposed.html` iter-14 — `.source-row__attribution { margin-left: auto }` + `.source-row__title { max-width: 280px; text-overflow: ellipsis }` |

---

## 3. Promotion patches on top of the iter-15 lock (V2.A / V2.B / V2.C)

The iter-1→iter-15 stack in the workshop targets the workshop wrapper, not a runnable React app. Three deltas must apply on top of that stack when promoting to live:

### V2.A — Scope the collapse rules so iter-12's lifecycle wrapper hides when card is collapsed

The iter-12 lifecycle section is injected as `.item-card__lifecycle` (the JS-rebuilt expanded body). Live's existing CSS at [components.css:4691-4697](../../src/dual_research/ui/static/components.css#L4691) collapses `.item-card__body`, `.item-card__timeline`, `.item-card__sources`, `.item-card__footer`, `.item-card__lifecycle-footer` when `data-expanded="false"` but **not** `.item-card__lifecycle` (because it didn't exist when those rules were written — live's `.item-card__lifecycle` at [components.css:4542-4546](../../src/dual_research/ui/static/components.css#L4542) is the legacy inline chip cluster, a different element).

The promotion needs to either (a) extend the existing `data-expanded="false"` rule to add `.item-card__lifecycle-section` (new class for the iter-12 wrapper, to disambiguate from the existing chip cluster) or (b) rename the iter-12 wrapper class to avoid the collision and add its own collapse rule. Spec 0203 §2.6 picks the disambiguating class name.

### V2.B — Do NOT ship iter-15's whole-card auto-expand to live

The workshop wrapper's [_inline-script.js:349-356](./_inline-script.js#L349) auto-expands the first `.item-card` per phase that has sources, so the workshop demo always shows one fully-rendered card per phase. This is a workshop demo affordance, not a product feature. For live, **cards default collapsed** even when they have sources — the source segment is reachable via card-head click (C1's affordance) and via the existing `item-card__sources-chip` jump-to-segment button [run-detail.jsx:1799-1822](../../src/dual_research/ui/static/run-detail.jsx#L1799).

What IS kept from iter-14/iter-15 is the FIRST `.source-row` pre-expanded inside any expanded card (already wired live at [run-detail.jsx:1990](../../src/dual_research/ui/static/run-detail.jsx#L1990) as `defaultExpanded={i === 0}`).

C1's "Resolved unfolded by default" is implemented at the `.crit-group` level (the renderGroup caller passes `collapsed={false}` for the Resolved group when the phase has any resolved items), NOT via the workshop wrapper's blanket `data-collapsed="false"` reset.

### V2.C — System chip in the head's actor slot + `align-self: stretch` on lc-row chip clusters

Two coupled fixes for orchestrator/system-raised cards:

1. **Head's actor slot.** The workshop's iter-7 head rebuild ([_inline-script.js:95-100](./_inline-script.js#L95)) handles three actor values — `claude` / `gpt` / `system` — and emits the gear-icon System chip when the actor is `system` or `orchestrator`. Live's [run-detail.jsx:1874-1881](../../src/dual_research/ui/static/run-detail.jsx#L1874) handles this with `raisedByAgent ? <Chip /> : <SystemChip />` — but `_resolveAgent` may return `null` for `orchestrator` actors, causing the SystemChip fallback to fire correctly. Verify against the actual `_resolveAgent` implementation; if `orchestrator` is not mapped to a non-null value that triggers the chip path, fix it.

2. **Lifecycle-row alignment.** The `LIFECYCLE` overline + `.lc-row` stack relies on each row's chip cluster (`.lc-row-chips`) sitting at the same left edge regardless of quote length. The workshop's `.lc-row { padding: 8px 0; }` rule at [components.css:1202-1210](../../src/dual_research/ui/static/components.css#L1202) is fine, BUT the parent `.item-card__lifecycle-section` flex container (V2.A's renamed wrapper) must NOT set `align-items: center` — it must use `align-items: stretch` so each row gets full-width treatment. Explicit `align-self: stretch` on `.lc-row` is the defensive override.

This is the single highest-regression-risk patch — a careless cleanup pass that drops `align-self: stretch` (because "it looks like a default") would silently break C6.

---

## 4. Deliberately deferred (NOT in scope for spec 0203)

Per the user's promotion brief on 2026-05-24, these drift items stay out of scope for the V2-promotion spec and are deferred to a follow-up dev spec to be drafted post-merge:

- **Drift 3.E ([NOTES.md §3.E](./NOTES.md))** — "Resolved" group title misrepresents terminal-state mix (resolved + acknowledged + capped lumped under one heading). Split into per-state groups per spec 0119 §9.5 vocabulary.
- **Drift 3.F ([NOTES.md §3.F](./NOTES.md))** — Σ Summary bar-1 totals reset to `0/0/0` when the Σ tab is active. Should be tab-invariant.
- **Drift 3.G ([NOTES.md §3.G](./NOTES.md))** — Σ Summary body uses ~25 inline `style="…"` attributes per element. Promote into reusable CSS classes.
- **Drift 3.H ([NOTES.md §3.H](./NOTES.md))** — DS Σ Summary section diverges from live Σ Summary body. Neither is locked in `design-system/SPEC.md` §4.1.

Other out-of-scope:

- **Timeline pane** — separate spec.
- **Canvas skill regeneration logic** — separate spec.
- **Full DS/live parity backfill** — `composed-components.css` is currently 2,423 lines vs `components.css` at 5,337 lines for the critique-pane region alone. Spec 0203 mirrors ONLY the V2-delta classes; full backfill is a separate spec.

---

## 5. Promotion target files (all three updated in the same commit)

Per [`CLAUDE.md`](../../CLAUDE.md) §Design system: DS authoritative copy and live-app copy stay in sync — additions to one MUST land in the other in the same commit.

| File | Role |
|---|---|
| [`src/dual_research/ui/static/components.css`](../../src/dual_research/ui/static/components.css) | Live-app critique CSS. Add/replace the C1–C8 + V2.A–C rules. |
| [`design-system/assets/styles/composed-components.css`](../../design-system/assets/styles/composed-components.css) | DS authoritative copy. Mirror the same classes/rules added above (strict scope — only the V2-delta classes, not the existing 2.9k-line gap). |
| [`src/dual_research/ui/static/run-detail.jsx`](../../src/dual_research/ui/static/run-detail.jsx) | React components for the critique pane. Rebuild the head per C5, replace the expanded body per C6, adjust evidence-needed chip per C7, adjust source-row chrome per C8, default Resolved expanded per C1. |

---

## 6. References

- [`prototypes/critique-iteration/NOTES.md`](./NOTES.md) — full iter record (iters 1-15 + drift items 3.A-3.K)
- [`prototypes/critique-iteration/CARD-DESIGN-PROMPT.md`](./CARD-DESIGN-PROMPT.md) — the card-design brief that drove iters 4-15
- [`prototypes/critique-iteration/KICKOFF-PROMPT.md`](./KICKOFF-PROMPT.md) — the workshop bootstrap brief
- [`prototypes/critique-iteration/proposed.html`](./proposed.html) — pixel target (workshop CSS stack)
- [`prototypes/critique-iteration/live.html`](./live.html) — diff target (live-app dump 2026-05-22)
- [`prototypes/critique-iteration/_inline-script.js`](./_inline-script.js) — JS behaviors for head rebuild + lifecycle injection
- Notion: [Critique & Timeline](https://www.notion.so/36999f3e507f8083b551f2c8fcbe46d3) (the C1–C8 source)
- [`design-system/SPEC.md`](../../design-system/SPEC.md) — DS sections cited by spec 0203 (§4.1 critique header, §4.7 sources, §4.8 ItemCard composition, §6.3.d ItemCard composition, §9.5 state vocabulary)

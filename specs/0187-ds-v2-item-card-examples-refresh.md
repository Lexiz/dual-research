---
kind: dev
spec: "0187"
slug: ds-v2-item-card-examples-refresh
title: "Refactor: DS reference §13 ItemCard examples — match post-0173 head, evidence-inline, collapse, and QuestionThread bubbles"
type: refactoring
label: refactoring
version_bump: PATCH
target_version: TBD
status: queued
queue_position: 7
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

# Spec 0187 — Refactor: DS reference §13 ItemCard examples — match post-0173 anatomy

> **Type:** refactoring  |  **Complexity:** S  |  **Depends on:** 0173
> **Bump:** PATCH — reference-doc-only edit, no JSX / live CSS impact, no behavior change. DS HTML reference brought back in sync with what ships live.
> **Evidence:** Spec 0173 handoff `## Deferred during implementation` first bullet — [handoffs/2026-05-23-spec-0173-drain-deferrals-from-0166-0167-0168.md:41](handoffs/2026-05-23-spec-0173-drain-deferrals-from-0166-0167-0168.md:41): *"DS reference (`Design System v2.html`) §13 — ItemCard examples were not re-rendered to match the new `[provider][kind][evidence?][lifecycle]` head composition + collapse behavior. … The DS reference page diverges from live until this is closed out."* Spec 0173 §2.5 / §2.7 / §2.9 / §2.11 all cited [design-system/assets/Design System v2.html](design-system/assets/Design System v2.html) §13 as a target file.

---

## 1. Current state

The DS reference for the ItemCard primitive lives at [design-system/assets/Design System v2.html:1010–1318](design-system/assets/Design System v2.html). It shows the pre-0173 anatomy — both the stacking-order callout and the two rendered example cards still depict:

- The `id` chip rendered inline in the head ([design-system/assets/Design System v2.html:1027](design-system/assets/Design System v2.html:1027) — *"`{id}` (mono inline, not a chip) · `agent` · `kind` · `raised in rN` · `Sources N` (when N>0) · right-aligned `status` chip"*) — this row is now `[provider chip][kind chip][evidence-needed modifier?][head-spacer][lifecycle chip — right-aligned]` per spec 0173 §2.5 implementation at [src/dual_research/ui/static/run-detail.jsx:1813–1968](src/dual_research/ui/static/run-detail.jsx).
- The `Sources N` chip in the head ([design-system/assets/Design System v2.html:1045](design-system/assets/Design System v2.html:1045)) — dropped per spec 0173 §2.5 ("ID chip + sources chip dropped").
- The evidence-needed marker as a full-body banner italic line ([design-system/assets/Design System v2.html:1029, 1052](design-system/assets/Design System v2.html:1029)) — replaced per spec 0173 §2.7 by an inline `<Chip tone="warn">evidence needed</Chip>` between the kind chip and the head-spacer, with the legacy `.item-card__evidence-needed` body row hidden via `display: none` in [src/dual_research/ui/static/components.css:4540–4546](src/dual_research/ui/static/components.css).
- The example cards rendered default-expanded with the body, lifecycle list, and sources section all visible at once — per spec 0173 §2.11 every `.item-card` now carries `data-expanded="false"` by default with the body, timeline, sources, footer, and lifecycle-footer hidden until the head is clicked ([src/dual_research/ui/static/run-detail.jsx:1923–1972](src/dual_research/ui/static/run-detail.jsx), CSS at [src/dual_research/ui/static/components.css:4641–4665](src/dual_research/ui/static/components.css)).
- The expanded view renders flat `.lc-row` lifecycle entries ([design-system/assets/Design System v2.html:1058–1089](design-system/assets/Design System v2.html:1058)) — replaced per spec 0173 §2.9 by the new `ItemCardThreadView` component which emits QuestionThread-anatomy tonal-tinted message bubbles ([src/dual_research/ui/static/run-detail.jsx:1511–1545](src/dual_research/ui/static/run-detail.jsx)) with provider/round/verdict chip clusters and styled `<blockquote>` quotes inside an 8% color-mix provider-tinted bubble + 2px left-border ([src/dual_research/ui/static/components.css:4548–4593](src/dual_research/ui/static/components.css)).

The pain: anyone reading `Design System v2.html` to understand how ItemCard renders today gets a stale model. The DS-first contract (`CLAUDE.md` design-system block) requires the DS HTML reference to mirror live; spec 0173 left this one bullet off the cycle because re-authoring four hand-rolled example HTML blocks was disproportionate effort vs. the rest of the spec. Catching it up here.

## 2. Target state

§13 of [design-system/assets/Design System v2.html](design-system/assets/Design System v2.html) updated to mirror the post-0173 anatomy. Four concrete edits:

1. **Stacking-order callout** at [design-system/assets/Design System v2.html:1020–1034](design-system/assets/Design System v2.html:1020) rewritten to reflect the new head composition:
   - Drop *"`{id}` (mono inline, not a chip)"* from item 1.
   - Drop *"`Sources N` (when N>0)"* from item 1.
   - Replace item 1 wording with: *"Header chip row. **provider** · **kind** (with category letter Q/D/I/C bubble) · optional inline **evidence needed** modifier · head-spacer · right-aligned **lifecycle** chip carrying the raise→respond→resolve arc as a chip cluster (open: `raised · rN · raiser-icon`; resolved: `[raised rN raiser-icon] · [resolved rM resolver-icon]`; drift: `raised r? · drift`)."*
   - Drop item 3 (the standalone evidence-needed body row); fold it into item 1 as the inline modifier.
   - Update item 4 wording: *"Expanded view. Vertical stack of QuestionThread-anatomy bubbles — one bubble per transition (raise + each transition), each bubble carrying a `[provider chip][round chip][verdict chip]` cluster + the reason quote inside as a styled `<blockquote>`. Bubble container uses 8% `color-mix` provider tint + 2px left-border."*
   - Add a new item: *"Collapse affordance. The card defaults `data-expanded="false"` — only the head renders; body, timeline, sources, footer, and lifecycle-footer are hidden until the head is clicked. The head carries `role="button"` and `aria-expanded`."*

2. **Example card 1** at [design-system/assets/Design System v2.html:1037–1199](design-system/assets/Design System v2.html:1037) (currently *"Resolved Question · with sources"* in default-expanded state) restructured into **two paired example cards** both showing a resolved question:
   - **(1a) Collapsed-resolved.** `data-expanded="false"` on the outer article. Head only: provider chip (Claude), kind chip (Question + Q letter bubble), head-spacer, lifecycle cluster `[raised r1 raiser-icon] · [resolved r2 resolver-icon]` muted+ok tones. Body / timeline / sources / footer all hidden via the collapse CSS (which the live `.item-card[data-expanded="false"]` rules at [src/dual_research/ui/static/components.css:4641–4665](src/dual_research/ui/static/components.css) handle automatically — the HTML still includes them in the DOM, the CSS hides them).
   - **(1b) Expanded-resolved.** `data-expanded="true"` on the outer article — same data as (1a) but everything visible. Lifecycle entries restructured from flat `.lc-row` to the new bubble shape: each bubble is a `<div class="item-card__bubble">` carrying the same provider/round/verdict chip cluster, wrapping a `<blockquote class="item-card__bubble-quote">` for the reason text.

3. **Example card 2** at [design-system/assets/Design System v2.html:1140–1316](design-system/assets/Design System v2.html:1140) (currently *"Capped Question · evidence-needed, no sources"* in default-expanded state) similarly restructured into a **collapsed-open** + **expanded-open** pair:
   - **(2a) Collapsed-open.** `data-expanded="false"`. Head only: provider chip (GPT), kind chip (Disagreement + D letter bubble), inline `evidence needed` warn chip (since the example carries `evidence_required: true`), head-spacer, lifecycle chip kind-toned `raised · r2 · GPT-icon` (single-chip open form, not the resolved two-chip cluster).
   - **(2b) Expanded-open.** `data-expanded="true"`. Same as (2a) plus the body bubble stack and the evidence-needed row removed (the modifier is now in the head, not the body).

4. **§13 lede paragraph** at [design-system/assets/Design System v2.html:1016–1018](design-system/assets/Design System v2.html:1016) updated: replace *"header chips, the item text, an optional Evidence needed helper, a vertical Lifecycle timeline of transitions, a terminal-state footer, and (when N>0) a SOURCES (N) segment"* with *"a tight head (provider · kind · optional inline evidence-needed · lifecycle chip), a collapsed default state, and — when expanded — a QuestionThread-anatomy bubble timeline of transitions plus the optional SOURCES (N) segment beneath."*

The four new example HTML blocks each get a small `<div class="ds-example-label">collapsed open</div>` / `expanded open` / etc. caption above them so the reader knows which state they're looking at.

No `composed-components.css` or `components.css` edits — the collapse CSS, the bubble CSS, and the inline-evidence-needed chip styling all already exist in both files (landed under spec 0173). This spec only edits the reference HTML.

## 3. Stepwise migration

Each step independently shippable / revertable. All edits are confined to [design-system/assets/Design System v2.html](design-system/assets/Design System v2.html).

- **Step 1 — Stacking-order callout rewrite.** Edit [design-system/assets/Design System v2.html:1020–1034](design-system/assets/Design System v2.html:1020). New `<ol>` entries per §2 item 1 above. *Verifies:* the rendered §13 page now describes the live anatomy; manual diff against the live ItemCard JSX. The example cards below are still stale at this point — that's intentional, step 2 picks them up.

- **Step 2 — Example card 1: split into collapsed-resolved + expanded-resolved pair.** Edit the resolved-question example block at [design-system/assets/Design System v2.html:1037–1199](design-system/assets/Design System v2.html:1037). Restructure the two articles per §2 item 2 above: drop the `id` chip element, drop the `Sources N` chip element, add `data-expanded` to the article tag, rewrite the lifecycle area as bubble divs. *Verifies:* opening §13 in the DS HTML shows two states of the resolved-question card; the collapsed one renders head-only; the expanded one renders the bubble timeline. Manual visual diff against the live ItemCard at the anchor run `20260521-010637-dvs-backend-language-choice`.

- **Step 3 — Example card 2: split into collapsed-open + expanded-open pair.** Edit the second example block at [design-system/assets/Design System v2.html:1140–1316](design-system/assets/Design System v2.html:1140). Same restructure as step 2 but with the kind changed to disagreement (or keep question — the deferral text doesn't bind kind, so disagreement is a more interesting demo since it carries `evidence_required`). Drop the standalone `<em class="evidence-needed">` body banner; add the inline warn chip to the head. Single-chip lifecycle (kind-toned `raised · r2 · agent-icon`, no resolver cluster since the item is still open). *Verifies:* §13 now demonstrates all four states (collapsed open, expanded open, collapsed resolved, expanded resolved) with no stale chrome.

- **Step 4 — Lede paragraph + section index note.** Edit [design-system/assets/Design System v2.html:1016–1018](design-system/assets/Design System v2.html:1016) per §2 item 4 above. Optionally bump the section-index from `spec 0144` to `spec 0144 · refreshed 0173 / 0187` so a future reader sees the doc's most recent rebase. *Verifies:* the §13 lede reads correctly against the live anatomy.

## 4. Behavior preservation

This is a reference-doc edit. There is no runtime behavior to preserve. The verifications here are about doc fidelity, not test execution.

- [ ] Existing test `uv run pytest tests/ -q` still green — confirms no JSX / CSS file was accidentally touched. (The DS HTML reference is not under pytest coverage; the assertion is "we didn't break anything else by editing this file.")
- [ ] New parity check (manual, written into the implementation handoff): screenshot the live ItemCard on the anchor run in collapsed-resolved, expanded-resolved, collapsed-open, expanded-open states; screenshot the corresponding DS §13 examples; confirm visual parity by eye. Not a pytest check — the DS HTML doesn't render under a test harness — but it's the one falsifiable check that closes out the deferral.

## 5. Out of scope

**Explicit: no new feature ships here.** All four example states already exist in the live JSX (spec 0173 §2.5 / §2.7 / §2.9 / §2.11 landed them); this spec catches the reference HTML up to what already ships. Any feature work that depends on this catch-up lives in a follow-up spec.

- The `§13b · QuestionThread (legacy)` block at [design-system/assets/Design System v2.html:1318+](design-system/assets/Design System v2.html:1318) is **not** touched. That block intentionally documents the legacy pre-0114 fallback and remains useful as historical reference. Updating it to mirror the new bubble anatomy would conflate "legacy fallback" with "current canonical".
- No DS token, primitive, composed-component CSS, or live JSX / CSS edits. The reference catches up to live — live does not move.
- The SOURCES (N) section in the example cards is left as-is. Spec 0173 §2.10 extended `SourceRow` with provider/round attribution but did not re-author the §13 source-row HTML; that catch-up is a separate follow-up if anyone notices the gap.
- No section renumbering. §13 stays §13; §13b stays §13b. Adding more state examples does not break the index.

## 6. Risks

What could go wrong with a reference-doc refresh:

- **Hidden behavior depending on internals.** Some other DS section (or another doc page) might link into §13 via fragment IDs (`#itemcard`, the `ic-1` aria id, etc.). Mitigation: grep [design-system/](design-system/) for `#itemcard` and `ic-1` / `ic-2` before editing; preserve the fragment IDs in the new article elements. The lede paragraph's hash link from §13b at line 1327 (`href="#itemcard"`) must keep working.
- **Drift from the next spec that touches ItemCard.** If another spec lands between this one being queued and being implemented, the post-0173 anatomy might already have moved on. Mitigation: the implementer must read the latest [src/dual_research/ui/static/run-detail.jsx](src/dual_research/ui/static/run-detail.jsx) `ItemCard` + `ItemCardThreadView` + `ItemCardDQBody` definitions at implementation time, not just what spec 0173 documented. Live JSX is the source of truth for the HTML examples.
- **Visual parity is human-judged.** Without a pixel-diff harness for the DS HTML page (which is intentional — the page is hand-authored, not regenerated), parity is by eye. The implementer must open both the live ItemCard and the rendered §13 side-by-side at implementation time. Mitigation: include the live-app URL `/runs/20260521-010637-dvs-backend-language-choice/` in the handoff so the next reader can re-run the visual diff if they suspect drift.
- **Missed call site.** The collapse CSS (`.item-card[data-expanded="false"]`) reads from class names that may have changed under spec 0173. Mitigation: the new example HTML must use the same outer class (`crit-card` or `item-card`, whichever the live CSS targets) — grep the live CSS at [src/dual_research/ui/static/components.css:4641–4665](src/dual_research/ui/static/components.css) for the canonical selector and mirror it. The current §13 uses `crit-card`; the live JSX uses `item-card`. If those are aliases via shared CSS, fine; if not, this spec must reconcile.
- **Performance regression.** N/A — the DS HTML page is static, not rendered per request. Zero runtime cost.

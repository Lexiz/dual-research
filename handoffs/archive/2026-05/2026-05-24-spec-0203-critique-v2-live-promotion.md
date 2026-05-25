---
spec: "0203"
date: 2026-05-24
kind: post-deploy
version: "1.43.0"
pr: "https://github.com/Lexiz/dual-research/pull/231"
---

# Spec 0203 — Critique V2 → live promotion (v1.43.0)

Shipped in two sessions across one day: checkpoint 1 (§2.1 / §2.2 / §2.3 / §2.4 / §2.8) and a resume session that landed §2.5 / §2.6 / §2.7 plus the §2.8 cosmetic touch-up and the §2.3 dead-code follow-up. Both `src/dual_research/ui/static/components.css` AND `design-system/assets/styles/composed-components.css` were kept in lockstep throughout — the DS/live drift risk called out in spec 0203 §7 did not manifest.

## What landed

### Head pattern rebuild (§2.5)

`src/dual_research/ui/static/run-detail.jsx` — composite `lifecycleChip` cluster replaced by explicit chips. Head emits, left → right: `[Provider]` (Claude / GPT / System via the existing `<SystemChip />` fallback) → `[Raised · R<N>]` mono neutral with `data-chip-role="round"` → `[Kind]` (Q / D / I / C with `.cat-bubble`) → `[evidence-needed?]` (now icon-only per §2.7) → spacer → `[<Verb> · <resolver icon?> · R<N>]` with `data-chip-role="state"` right-aligned via `margin-left: auto`. Capitalisation lives in CSS (`text-transform: capitalize` on the chip-label) so JSX labels stay lowercase and `R<N>` keeps its case.

The state chip shows the resolver brand icon inline (between verb and round, separated by `.chip-sep` dots) only when the resolver is Claude or GPT; orchestrator / system resolutions skip the icon (the `isAutoResolve` predicate gates this). `_resolveAgent` already returned `null` for `orchestrator` / `system` actors, so no fix was needed there — V2.C's "verify the system-fallback path" check was a no-op.

Also flipped `_ITEM_KIND_TONE.comment` from `muted` → `idle` so the Comment kind chip matches the V2 vocabulary (info / warn / err / idle).

### Lifecycle section (§2.6)

New component `ItemCardLifecycleSection` replaces `ItemCardThreadView` inside `ItemCardDQBody` / `ItemCardIssueBody` / `ItemCardCommentBody`. The old function was removed entirely (no other call sites). Anatomy:

```jsx
<section className="item-card__lifecycle-section">
  <div className="item-card__lifecycle-section-hd">LIFECYCLE</div>
  <div className="lc-rows">
    {rows.map(r => (
      <div className="lc-row" data-actor={r.actor}>
        <div className="lc-row-chips">[provider?][round][verb][extras?]</div>
        <div className="lc-row-quote">italic-serif quote</div>
      </div>
    ))}
  </div>
</section>
```

Orchestrator-actor rows skip the provider chip. The synthetic raise row uses `item.body` as its quote; subsequent rows come from `item.transitions` in chronological order. V2.A's wrapper-class disambiguation (`-section` suffix vs the legacy `.item-card__lifecycle` head-cluster name, which is gone) is enforced both by the JSX class and by CSS rules scoped to `.item-card__lifecycle-section`. V2.C's `align-items: stretch` + `align-self: stretch` rules are explicit and called out in CSS comments so a future "cleanup" pass cannot silently drop them.

The collapse rule was extended: `.item-card[data-expanded="false"] .item-card__lifecycle-section { display: none }` in both live and DS CSS.

### Source-request signal (§2.7)

Two pieces:

1. **Head evidence chip** rewritten from `tone="warn"` + full-text "evidence needed" to `tone="info"` + `iconOnly` + `<Mdi name="link-variant" />` + native `title="Evidence needed — addresses must cite consulted sources."` + `aria-label="Evidence needed"`. CSS `.item-card__head .chip.evidence-chip` adds the 22px square sizing + `cursor: help`.

2. **Lifecycle row extras**, injected by `ItemCardLifecycleSection`:
   - `[source requested]` chip (tone-info, link icon) on the raise row when `item.evidenceRequired === true`.
   - `[source provided]` chip (tone-ok, link icon) on the first Claude / GPT transition when the card carries ≥ 1 evidence record (`item.evidence` / `item.sources` / `item.references`).

   The "first agent transition" index is precomputed once per render so the row loop is cheap.

### §2.8 cosmetic + §2.3 follow-up

- Attribution chip at `run-detail.jsx` (`SourceRow` body) now ships per iter-13: `mono` + `R<N>` (capital) + native `title="Provided by <Agent> in round <N>"`. The auto-attributed variant (`provider === 'auto'/'orchestrator'/'system'`) gets `Auto · R<N>` with a parallel title.
- §2.3's `kind labels drop at narrow` contract is now real: a new `@media (max-width: 1799px) { .crit2 .bar2 .kind-tab .chip-label, .kind-tab > span:not(.chip-value):not(.cat-bubble):not(.chip-leading-icon) { display: none } }` rule fires on the actual `.kind-tab` element (the legacy `.chip[data-kind-filter]` rule was dead code because spec 0151 §3.4.1 had already migrated the kind tabs). Mirrored to DS.

## Verification

- `uv run pytest tests/ -q` — **1835 passed**. One test was updated: `test_item_card_dq_lifecycle_section_preserved` now asserts the new `<ItemCardLifecycleSection>` mount instead of the removed `<ItemCardThreadView>`.
- Local browser preview at `1920×1080` on `/#/runs/20260521-010637-dvs-backend-language-choice`:
  - Head order verified via `data-chip-role` reads — `[round, kind, evidence, state]` (provider is `<SystemChip />` without a role attribute).
  - State chip carries the inline `<span class="state-actor">` brand icon with `chip-sep` dots flanking it.
  - Expanded Disagreement card shows `LIFECYCLE` overline + 3 `.lc-row` entries with the `[source requested]` / `[source provided]` extras chips landing on the correct rows.
- Local browser preview at `1440×900`: kind-tab labels + counts both hide (BDD Scenario 3 satisfied).
- Zero runtime console errors.
- Post-deploy smoke: `https://dual-research-alex.fly.dev/` returns 200.

## Deploy notes

- `fly deploy` succeeded on the first attempt; both machines reached `good state` and the post-deploy sweep reported `sweep: no stale blues on dual-research-alex` (the spec 0193 image-based fallback found nothing — rolling deploy fully converged).
- `gh pr merge --admin --squash --delete-branch` succeeded on the merge but the post-merge `git checkout` inside `gh` failed because `dashboard/queue-state.json` was dirty in the working tree (the `--push-to-main` plumbing for `merged` had updated the file locally without the local main pointer following). Manual recovery: stash, fast-forward main, drop stash, then explicit branch deletion on both sides. The branch is now fully gone (verified per spec 0201 §2.1).

## Deferred during implementation

- **Playwright tests for BDD Scenarios 1–8** — spec 0203 §6 calls for Playwright assertions across all eight scenarios at multiple viewport widths. The repo currently has no Playwright setup (no dependency, no test runner, no CI integration). Adding the harness is meaningful infrastructure work that should land on its own spec rather than bloat this UI promotion. The visual contract was instead verified via manual browser-preview reads against the new chip-role attributes and a viewport-width sweep. A follow-up spec should: (1) add `@playwright/test` as a dev dep with a minimal `playwright.config.ts`; (2) wire a CI job to run `npx playwright test` against a locally-served build of the app on the anchor run; (3) translate the eight BDD scenarios from spec 0203 §3.2 into Playwright assertions (adjusting selectors per the handoff notes — Scenario 2's `.tab-group-solid .chip` → `.tab-solid`, Scenario 3's `.chip[data-kind-filter]` → `.kind-tab`).

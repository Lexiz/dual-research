---
spec: 0113
title: Full-view modals — fixed 92vh height + remove the 360px accordion-body cap
label: bug
version-bump: PATCH
status: merged
target-version: 0.76.15
created: 2026-05-19
pr: "https://github.com/Lexiz/dual-research/pull/121"
---

# Spec 0113 — Modal vertical fill + accordion cap removal

> Ship bucket: **Composed**
> Depends on: **0096, 0109, 0110**
> Complexity: **S**
> Targeted version bump: **PATCH** (visual layout fix to the modal primitive + one helper rule; no API changes, no new features).

## 1. Context

Source: [Notion · Known issues v2](https://www.notion.so/Known-issues-v2-36599f3e507f80a8ad5fdb26b143a695) — Notion **issues 6, 7, 9**.

User report (verbatim, summarised):

- **Issue 6.** Opening the "brief critique" full-view modal leaves a strip of empty space below the content — the modal doesn't use the full vertical space of the viewport.
- **Issue 7.** The Phase 1 draft full-view modal's left brief column "stops half way across the screen".
- **Issue 9.** The Converged document full-view modal has the same vertical-space problem as the brief critique modal, AND once expanded its inner accordion sections don't fill the modal's available height either.

**Grounded measurements on the post-spec-0110 build** (viewport 1400 × 900):

- **Brief critique modal** ("Input — brief"): renders at 1300 × 648. CSS resolves `min-height: 72vh = 648 px`, `max-height: 92vh = 828 px`, `height: auto`. Because the brief content is shorter than 72vh, the modal floors at 648 — leaving the empty strip the user reported.
- **Phase 1 draft modal** ("Claude — Phase 1 draft"): renders at 1300 × 828 (= 92vh on a 900-tall viewport, because the draft markdown is tall). The split grid is `592.5px 592.5px`. Inside the left pane (593 wide), markdown renders at 533 wide — the lost 60 px is ~32 px column padding + ~17 px scrollbar gutter + ~10 px misc. **The original Issue 7 root cause (modal at 1080 px wide) was already fixed by spec 0110's bump to 1300 px;** the user's screenshot predates that change. Defensive coverage only.
- **Converged document modal**: same modal-height story as Brief critique. Plus `.agent-input-body` (the accordion body class inside the Agent Input tab) has a hardcoded `max-height: 360px; overflow: auto` — accordions are limited to 360 px regardless of how tall the modal is, producing a nested-scroll experience the user explicitly disliked.

Net diagnosis: two real bugs (modal floor too low; accordion body capped too tight) + one defensive verification (Phase 1 draft horizontal — already fixed, just confirm).

This is the third of the four Notion-issues-v2 specs:

- **0111 (merged)** — Critique cards: bucket / scroll / badges / height (Notion 1, 2, 4, 5).
- **0112 (merged)** — Agent strip text overflow (Notion 3).
- **0113 (this spec)** — Full-view modal vertical fill + accordion cap (Notion 6, 7, 9).
- *Future* — Turn / Cross-review modal cleanup + input/output data correctness (Notion 8, 10).

## 2. Proposed change

Three sub-changes, in implementation order (lowest-risk first):

### 2.1 — Force modal height to 92vh (Notion Issue 6 & 9 root cause)

**Current state.** `components.css:1140-1153`:

```css
.md-dialog {
  …
  display: flex;
  flex-direction: column;
  min-height: 72vh;
  max-height: 92vh;
  overflow: hidden;
  …
}
```

The modal grows to fit content, capped at 92vh, with a floor of 72vh. When the modal's intrinsic content is shorter than 72vh (the typical case for short briefs, short converged documents, short Agent Input tab contents), the modal sits at 72vh and the user sees a strip of empty space below — exactly Notion issue 6 and the modal-half of issue 9.

**Fix.**

Change `.md-dialog` to use a fixed `height: 92vh` (with a matching `max-height: 92vh` for safety):

```css
.md-dialog {
  …
  height: 92vh;
  max-height: 92vh;
  …
}
```

The `min-height: 72vh` line is removed — it's superseded by the fixed `height`. The modal is now always 92% of the viewport, regardless of content length. Short content sits at its natural height inside the body (with `.dr-modal-body { overflow: auto }`, which is already in place from spec 0110, handling tall content). Empty space below short content is the body's, not the modal's — and the body can be styled later if needed (out of scope here).

**Acceptance.** A short brief (`Input — brief` on the canonical run) renders the modal at `height === 92vh` exactly. A tall draft (`Claude — Phase 1 draft` on the same run) renders at the same `92vh` height. Both modals are visually the same size.

### 2.2 — Remove the 360 px cap on `.agent-input-body` (Notion Issue 9 accordion half)

**Current state.** `components.css:888-897`:

```css
.agent-input-body {
  border-top: 1px solid var(--border-1);
  padding: 10px 12px;
  max-height: 360px;
  overflow: auto;
  background: var(--bg-0);
  font-size: 12px;
  line-height: 1.6;
  color: var(--fg-1);
}
```

Each accordion section inside the Agent Input tab caps its own body at 360 px and scrolls internally. Inside a 92vh modal (≈ 600-900 px tall depending on viewport), 360 px is a small fraction; the user spends most of their reading inside a tiny sub-scroller embedded in the larger modal body that's also scrollable — a classic nested-scroll pain point.

**Fix.**

Drop the local `max-height` + `overflow` rules from `.agent-input-body`. The outer `.dr-modal-body { flex: 1; min-height: 0; overflow: auto }` (already in place from spec 0110) becomes the single scroll surface — the user scrolls the whole modal body instead of fighting two nested scroll regions. Expanded accordions claim whatever vertical space they need; collapsed ones contribute zero.

```css
.agent-input-body {
  border-top: 1px solid var(--border-1);
  padding: 10px 12px;
  background: var(--bg-0);
  font-size: 12px;
  line-height: 1.6;
  color: var(--fg-1);
  /* Spec 0113 — removed max-height: 360px + overflow: auto. Outer
     .dr-modal-body is the single scroll surface; accordion content
     grows naturally and the modal body scrolls when total height
     exceeds the modal. Avoids nested-scroll inside the modal. */
}
```

**Acceptance.** Expanding any accordion inside the Agent Input tab grows the accordion to its full content height. The modal body's outer scrollbar is the only vertical scroll affordance inside the modal. No `.agent-input-body` ever shows its own scrollbar.

### 2.3 — Phase 1 draft horizontal fill (Notion Issue 7 defensive verification)

**Current state.** Spec 0110 bumped the modal canvas from 1080 px to 1300 px; this was the original root cause of the user's "stops half way across the screen" report. Inside the now-1300 px modal, the split grid (`minmax(0, 1fr) minmax(0, 1fr)`) gives ~593 px per column. The markdown content inside the left pane renders at ~533 px (column 593 px − inline column padding 32 px − scrollbar gutter 17 px − misc 10 px). That's an acceptable reading width; no further structural change required.

**Fix (defensive only).**

- Verify on the live build that the brief column markdown fills its expected ~533 px width on a 1400 px viewport, with both columns at exactly equal width.
- If the visual matrix § 5 surfaces any unexpected narrowing, address it then. Do not introduce a speculative change here — the structural rules are already correct.

**Acceptance.** Phase 1 draft modal on a 1400 × 900 viewport renders both columns at identical computed widths (≈ 593 px each). The left-pane markdown content occupies ≥ 80 % of the pane's inner content area.

## 3. Files touched

- `src/dual_research/ui/static/components.css`:
  - `.md-dialog` (~`:1140-1153`) — replace `min-height: 72vh; max-height: 92vh;` with `height: 92vh; max-height: 92vh;`. § 2.1
  - `.dr-modal` (~`:1037-1050`) — same change. **Discovered during implementation:** the modal DOM element carries both `.dr-modal` (legacy chrome from pre-spec-0109) and `.md-dialog` (M3 chrome) classes; only updating `.md-dialog` left `.dr-modal { min-height: 72vh }` in the cascade. Functionally inert (because `height: 92vh > min-height: 72vh` always), but the acceptance criterion explicitly required no `min-height: 72vh` in the rule block. Both rules are now harmonised. § 2.1
  - `.agent-input-body` (~`:888-897`) — drop `max-height: 360px;` and `overflow: auto;`. Comment that retention of `padding`, `background`, `font-size`, `line-height`, `color` is intentional. § 2.2
- `src/dual_research/ui/static/index.html` — cache-bust `?v=0104` → `?v=0105`.
- `pyproject.toml` — `0.76.14` → `0.76.15`.
- `src/dual_research/__init__.py` — `__version__` `0.76.14` → `0.76.15`.
- `CHANGELOG.md` — `0.76.15` entry under `## [0.76.15] — 2026-05-19`.

No JSX changes. No new tokens. No new classes. The whole spec is two CSS-rule edits + the standard version-and-cachebust scaffolding.

## 4. Acceptance criteria

- [ ] `.md-dialog` computed style on the live page reports `height: 92vh` (or its pixel equivalent on the test viewport) and `max-height: 92vh`. No `min-height: 72vh` in the rule block.
- [ ] On a 1400 × 900 viewport, the Brief critique modal (`Input — brief`) renders at exactly 828 px tall (92vh). The Phase 1 draft modal renders at the same 828 px tall. Verified via DevTools/Playwright `getBoundingClientRect().height`.
- [ ] `.agent-input-body` computed style on the live page does NOT contain `max-height` (or contains `max-height: none`). Does NOT show its own `overflow: auto` scrollbar even when expanded with very long content.
- [ ] Open the Converged document modal, expand all Agent-Input accordions. Single scrollbar visible — the outer `.dr-modal-body` scrollbar. No inner accordion scrollbars.
- [ ] Phase 1 draft modal: Claude column ≈ 593 px wide; GPT column ≈ 593 px wide; left-pane markdown content ≥ 480 px wide (≈ 80 % of column inner width).
- [ ] `uv run pytest tests/ -q` → 924+ green.
- [ ] Cache-bust `?v` value in `index.html` matches `pyproject.toml` `0.76.15`.

## 5. Visual verification matrix

- `2200×1300 dark` — route `#/runs/<canonical>`. Open: (a) Input — brief modal, (b) Phase 1 draft modal, (c) Converged document modal (with Agent Input tab active, accordions expanded). Capture each.
- `2200×1300 light` — same three modals.
- `1400×900 dark` — same three modals. This is the viewport where the user originally reported.
- `1400×900 light` — same three modals.
- `820×1180 dark` — same three modals. Stress test for narrow viewports — the modal should still be 92vh tall; the Phase 1 draft's split grid may collapse to single-column if needed (verify behaviour).
- `820×1180 light` — same three modals.

All six viewport × theme combos required, each with three modal screenshots = 18 shots total. The modal sizing change cascades across every full-view modal in the app; broad visual coverage is the safety net against an unexpected regression elsewhere.

## 6. Anti-pattern checks

- [ ] No emoji as icons.
- [ ] No hex colours in the modified CSS rules; existing tokens are preserved.
- [ ] No JavaScript size measurement / ResizeObserver added. The fix is pure CSS.
- [ ] No new nested scroll regions; § 2.2 explicitly removes one. The modal body is the single scroller.
- [ ] No per-modal-type overrides — both fixes apply uniformly to every modal that uses `.md-dialog` and every Agent Input tab respectively.

## 7. Risks

- **Risk: `height: 92vh` is too tall on small viewports**, e.g. 820 × 600 px. Mitigation: 92 % of 600 = 552 px, which is still usable for a modal. Visual matrix § 5 includes 820 × 1180 to confirm. If the user runs the app on an even smaller viewport, the body's `overflow: auto` continues to work; the modal just becomes more constrained.
- **Risk: removing the 360 px accordion cap lets a single huge accordion (e.g. 30 prior turns) push the modal body very tall**. Mitigation: the modal body itself has `overflow: auto` (from spec 0110), so it scrolls. The total scrolled distance is identical to today — the user just scrolls in one place instead of two.
- **Risk: short content + 92vh modal leaves a visible empty strip inside the modal body**. This is conceptually fine ("modal is big enough for the document"), but if the empty space looks awkward, a separate spec could centre short content vertically inside the body. Out of scope here — the user explicitly asked for "more vertical space for the model so you could read the document," not for centred short content.
- **Risk: spec 0110's behaviour relied on min-height as a floor**. Mitigation: I read 0110's body — the only rule there was `.dr-modal-body { flex: 1; min-height: 0; overflow: auto }` and `:only-child { flex: 1 }`. None of those depend on the `.md-dialog`'s own min-height. The dependency chain is clean.

## 8. Out of scope

- Centring short content vertically inside the modal body (potential future polish).
- Modal-type-specific height overrides (e.g. "the consumption modal can be shorter"). Apply the uniform 92vh and revisit later if needed.
- Anything in Notion Issues 1, 2, 4, 5 (covered by spec 0111).
- Anything in Notion Issue 3 (covered by spec 0112).
- Anything in Notion Issues 8, 10 (separate spec covering turn / cross-review modal cleanup + input/output orientation + data correctness).
- Modifying the Phase 1 draft modal's structure or its inline padding values — current measurements show the column layout is fine post-spec-0110. § 2.3 is verification only.
- Touching `CollapsibleSection` (the accordion-header primitive in `shared.jsx`). Only the per-modal `.agent-input-body` rule changes.

## 9. Backend touched?

**no.** Pure CSS rule changes plus the standard version bump and cache-bust. No data, no APIs.

## 10. Handover read

> *First task on running this spec: read `handoffs/<latest>-spec-0112-agent-strip-text-overflow.md` end-to-end. Spec 0112 added a `.as-activity` rule and changed the agent-strip flex sizing — confirm none of the rules added there are affected by the modal-height change in § 2.1.*

## 11. Spec rewrite mandate

> *If implementation surfaces a constraint that invalidates any acceptance criterion above, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec.*

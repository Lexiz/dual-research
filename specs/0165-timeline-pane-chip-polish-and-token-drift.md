---
kind: dev
spec: "0165"
slug: timeline-pane-chip-polish-and-token-drift
title: Timeline pane — chip polish (identity / activity / category bubble / cost) + light-mode token drift fix
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.26.0
status: deployed
depends_on: ["0164"]
complexity: M
created: 2026-05-22
queued_at: "2026-05-22T17:08:41Z"
started_at: "2026-05-22T20:00:00Z"
merged_at: "2026-05-22T20:10:00Z"
deployed_at: "2026-05-22T20:13:30Z"
pr: "https://github.com/Lexiz/dual-research/pull/188"
handover: "handoffs/2026-05-22-spec-0165-timeline-pane-chip-polish-and-token-drift.md"
failure_step: ""
source_session: timeline-iteration-2026-05-22
promoted_from_draft: "005"
---

# Spec 0165 — Timeline pane chip polish + light-mode token drift fix

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** 0164 (M3 card chrome must land first so chip-vs-card contrast lands on the right card surface)
> **Bump:** MINOR — visible chip readability improvements on every timeline card, plus one app-wide light-mode token-drift fix that affects every Claude/GPT chip everywhere in the app.

---

## 1. Context

After spec 0164 lands the M3 card chrome, the chips that sit inside `.tl-card-head` still have five readability gaps:

1. **Identity-chip backgrounds are too subtle.** `.chip.tone-claude` / `.chip.tone-gpt` use `var(--md-primary-container)` / `var(--md-secondary-container)` which resolve to ~18 %-tinted backgrounds in dark and ~26 % in light. Against the new `--md-surface-container-high` card surface (delivered by 0164), the chip reads as essentially no background.
2. **System chip equals card surface.** The agentless identity chip on the brief and on render-error cards uses `.chip.tone-neutral` with default styling — which on the new card surface is invisible.
3. **Activity chip equals card surface.** `.chip.tone-neutral.mono` (the `turn N` / `brief` / `plan` / `draft` activity badge) uses `var(--md-surface-container-high)` — exactly the new card surface. The chip vanishes against the card.
4. **Phase-header category bubbles render at 100 % brand saturation.** The `.cat-bubble` inside `.tl-phase__chips` is filled at full brand colour, so the bubble dominates the visual weight of the chip when the chip background itself is only an 18 % tinted tone.
5. **Light-mode token drift is app-wide.** The live `src/dual_research/ui/static/tokens.css` does NOT override `--md-on-primary-container` / `--md-on-secondary-container` in its `body.light` block. The dark-mode values (`#f3deca` light cream / `#cfece6` light mint) leak into light mode and read washed-out on the cream surface. Every Claude / GPT chip everywhere in the app — timeline, critique, `/#/language` — is affected.
6. **Cost precision is too granular.** The expanded-card action row (`.tl-thread__actions`) renders cost chips at 4-decimal precision (e.g. `$0.0312`). The run-detail footer aggregate at `src/dual_research/SPEC.md` §4.3 uses 4-decimal as the audit number, but card-internal displays read cleaner with 2-decimal precision (`$0.03`).

Four locked visual changes + one token-drift fix + one cost precision tweak. All ship in one MINOR release.

## 2. Proposed change

### 2.1 Token drift — light-mode `--md-on-{primary,secondary}-container`

**Now.** `src/dual_research/ui/static/tokens.css` has a `body.light { … }` block with light-mode overrides for the M3 token set, but it is missing two specific keys. The keys exist correctly in the canonical token source at `design-system/assets/styles/tokens-and-primitives.css` (search the canonical file for `body.light` → `--md-on-primary-container: #3b2810`). Live falls through to the dark-mode root values.

**Reference values** (already canonical in `design-system/assets/styles/tokens-and-primitives.css`):

```css
body.light {
  /* … existing light overrides … */
  --md-on-primary-container:   #3b2810;
  --md-on-secondary-container: #0a322d;
}
```

**Files to change.**
- `src/dual_research/ui/static/tokens.css` — add the two overrides inside the existing `body.light` block.
- `design-system/assets/styles/tokens-and-primitives.css` — verify the values are already there; if any drift, this commit re-establishes them as canonical.
- No SPEC.md change — the canonical values are already documented in `design-system/SPEC.md` §2.1.

**Downstream impact.** Every chip using `.tone-claude` / `.tone-gpt` everywhere in the app (timeline cards, critique cards, future surfaces, `/#/language` route examples) will render with the correct dark text on light surfaces. A visual-regression sweep against the live `/#/language` page + the critique pane is part of the test plan.

### 2.2 Identity-chip backgrounds (scoped to `.tl-card-head`)

**Now.** `.chip.tone-claude` background resolves to `var(--md-primary-container)` (sable @ 18 % in dark). On the new `--md-surface-container-high` card surface (delivered by 0164) the chip is barely visible. Same for `.chip.tone-gpt` (sage container) and `.chip.tone-neutral` (System on flat neutral).

**After.** Scoped overrides inside `.tl-card-head` only — do NOT touch the global `.chip.tone-X` rules. The critique pane and other surfaces may need different tunings; this change is timeline-card-head-specific.

```css
.tl-card-head .chip.tone-claude {
  background: color-mix(in srgb, var(--p-sable) 30%, transparent);
}
.tl-card-head .chip.tone-gpt {
  background: color-mix(in srgb, var(--p-sage)  30%, transparent);
}
.tl-card-head .chip.tone-neutral:not(.mono) {
  background: color-mix(in srgb, var(--p-idle)  20%, transparent);
  color: var(--md-on-surface);
}
```

The System (`.tone-neutral:not(.mono)`) is held at 20 % rather than 30 % because the idle palette tone is itself dimmer than sable/sage; 30 % reads too prominent. The text colour is forced to `var(--md-on-surface)` because the System chip's identity is neutral, not branded.

**Files to change.**
- `src/dual_research/ui/static/components.css` — add the three scoped rules.
- `design-system/assets/styles/composed-components.css` — same.
- `design-system/SPEC.md` §4.4 — codify the three card-head-scoped backgrounds. Note the deliberate scope (`.tl-card-head`) to avoid affecting critique-pane chips.

### 2.3 Activity-chip surface bump (scoped to `.tl-card-head`)

**Now.** `.chip.tone-neutral.mono` (activity chip with labels like `turn 1` / `brief` / `plan` / `draft`) uses `var(--md-surface-container-high)` — same as the new card surface. Invisible.

**After.** Bump to one tier brighter than the card:

```css
.tl-card-head .chip.tone-neutral.mono {
  background: var(--md-surface-container-highest);
}
```

This bump is load-bearing — without it, the activity-chip identity is lost on the new card surface.

**Files to change.**
- `src/dual_research/ui/static/components.css` — add the scoped rule.
- `design-system/assets/styles/composed-components.css` — same.
- `design-system/SPEC.md` §4.4 — add: *"The mono activity chip inside `.tl-card-head` carries `--md-surface-container-highest` (one tier brighter than the card surface)."*

### 2.4 Phase-header category bubble — 70 % alpha dim (scoped to `.tl-phase__chips`)

**Now.** The category counter chips on phase headers (`.tl-phase__chips`) contain a `.cat-bubble` — a 14 px filled circle in the brand-tone colour (info blue / warn amber / err red / idle grey) with a knockout-white letter (Q / D / I / C). The bubble is filled at 100 % brand saturation. Against the chip's own 18 %-tinted background, the bubble dominates the visual weight.

**After.** Bubble background dimmed to 70 % alpha. The bubble is still distinctly brighter than the chip's 18 %-tinted background, but the 100 % saturation no longer dominates. Knockout-white letter is preserved (readable on all four tones at 70 % alpha).

```css
.tl-phase__chips .chip.tone-info  .cat-bubble { background: color-mix(in srgb, var(--p-info)  70%, transparent); }
.tl-phase__chips .chip.tone-warn  .cat-bubble { background: color-mix(in srgb, var(--p-warn)  70%, transparent); }
.tl-phase__chips .chip.tone-err   .cat-bubble { background: color-mix(in srgb, var(--p-err)   70%, transparent); }
.tl-phase__chips .chip.tone-idle  .cat-bubble { background: color-mix(in srgb, var(--p-idle)  70%, transparent); }
```

Scoped to `.tl-phase__chips` so the global `.chip .cat-bubble` rule is untouched (the critique-pane kind cluster uses the same `.cat-bubble` primitive and needs to keep its 100 % saturation per a different visual budget).

**Files to change.**
- `src/dual_research/ui/static/components.css` — add the four scoped rules.
- `design-system/assets/styles/composed-components.css` — same.
- `design-system/SPEC.md` §9.6 letter-bubble — add a one-line note: *"On phase-header chip clusters (`.tl-phase__chips`), the bubble may be rendered at 70 % alpha; the brand colour must remain the dominant hue."*

### 2.5 Cost precision — 2-decimal on expanded-card action chips

**Now.** The expanded-card action row at the bottom of an expanded turn card (`.tl-thread__actions`) renders a cost chip via the existing `fmtCost(value)` helper. The helper produces 4-decimal output (e.g. `$0.0312` for a 3.12 cent turn). The same helper is also used for the run-detail footer aggregate where 4-decimal is the correct audit precision.

**After.** Introduce a `fmtCost2(value)` helper that:
- Returns `<$0.01` when `value < 0.01` (sub-cent values would otherwise round to `$0.00`).
- Returns `$X.XX` (2-decimal trailing zero preserved) otherwise.

Place the new helper next to the existing `fmtCost` in `src/dual_research/ui/static/run-detail.jsx`. The expanded-card action chip switches to `fmtCost2`. The run-detail footer aggregate continues using `fmtCost` (4-decimal audit value, unchanged).

```js
function fmtCost2(value) {
  if (value == null || isNaN(value)) return '$—';
  if (value < 0.01) return '<$0.01';
  return '$' + value.toFixed(2);
}
```

**Files to change.**
- `src/dual_research/ui/static/run-detail.jsx` — add `fmtCost2` next to `fmtCost`; switch the expanded action-row cost chip from `fmtCost` to `fmtCost2`. Search for `tl-thread__actions` to locate the call site.
- `design-system/SPEC.md` §4.4 — add: *"Cost chips in the expanded turn-card actions row use 2-decimal precision (`fmtCost2`). Values under 1 cent render as `<$0.01`. The run-detail footer aggregate retains 4-decimal precision as the audit number."*
- `design-system/assets/Design System v2.html` §16 — update the expanded-turn example's cost chip from a 4-decimal display to a 2-decimal display (e.g. `$0.06`).

### 2.6 Light-mode chip-text fallback (belt and braces after §2.1)

**Now.** Even after §2.1 lands the canonical light-mode token override, a defensive overlay scoped to `.tl-card-head` documents the intended dark text colours in case the token drifts again in future work.

**After.**

```css
body.light .tl-card-head .chip.tone-claude,
body.light .tl-card-head .chip.tone-claude .chip-label {
  color: #3b2810;
}
body.light .tl-card-head .chip.tone-gpt,
body.light .tl-card-head .chip.tone-gpt .chip-label {
  color: #0a322d;
}
```

These are the same values §2.1 adds to the token set — duplicated here as a scoped backstop. If §2.1's tokens are correct, these rules are no-ops (the `--md-on-primary-container` / `--md-on-secondary-container` resolution already produces these hex values). If the tokens drift again, the scoped rules keep the timeline chip text correct.

**Files to change.**
- `src/dual_research/ui/static/components.css` — add the four scoped rules.
- `design-system/assets/styles/composed-components.css` — same.

## 3. UX / behaviour

After this spec lands:

- **Dark mode.** Identity chips (Claude / GPT) on timeline cards render with a clearly visible 30 % brand-tinted background — the chip's brand identity reads at a glance. The System chip renders with a 20 % idle-tinted background and on-surface text. The activity chip (`turn 1` / `brief` / `plan` / `draft`) reads as a discrete badge one surface tier brighter than the card surface.
- **Light mode.** Same anatomy. After §2.1's token fix, Claude / GPT chip labels render in their canonical dark text colours (deep brown `#3b2810` for sable, deep teal `#0a322d` for sage) on the tinted background. This applies *everywhere* the chips appear — timeline cards, critique cards, `/#/language` page, future surfaces.
- **Phase headers.** The category counter chips' `.cat-bubble` renders with softer 70 % brand tone. The chip's overall visual weight is balanced: the brand-tone bubble still wins on hue, but no longer overpowers the chip's 18 %-tinted background. The knockout-white letter (Q / D / I / C) remains readable.
- **Expanded turn cards.** The cost chip in the action row shows 2-decimal precision: `$0.03`, `$13.51`, `<$0.01` for sub-cent values. The run-detail footer aggregate (separate location, see `design-system/SPEC.md` §4.3) continues to display 4-decimal precision as the audit value.

No data migrations. No new components. The chip primitives are unchanged — only their surface and text rules are scoped or polished.

## 4. Data / schema deltas

None. Presentation only. The cost rendering helper change is pure UI — the underlying numeric value in run-detail JSON is unchanged.

## 5. Out of scope

- **M3 card chrome + phase header + pane gutter + provider stripes + narrow-mode strip equalisation** — delivered by spec 0164 (this spec depends on it).
- **System + Error chip primitives + brief-card refactor to `[System][brief]` + `[object object]` data-layer fix + live-state agent strip wiring** — covered by spec 0166.
- **Critique-pane chip backgrounds** — separate critique spec.
- **Other surfaces' chip palettes** — out of scope unless §2.1's token change exposes a regression. The test plan §7 includes an app-wide light-mode sweep to catch regressions.
- **Cost precision on the run-detail footer aggregate** — explicitly preserved at 4-decimal (audit value).

## 6. Design-system gate

Cited DS sections being updated:

- `design-system/SPEC.md` §2.1 / §2.3 — confirm canonical `--md-on-{primary,secondary}-container` light-mode values are documented (they already are; §2.1's live token fix brings the live file in line).
- `design-system/SPEC.md` §4.4 — codify the card-head-scoped chip background rules, the activity-chip surface bump, the 2-decimal cost rule.
- `design-system/SPEC.md` §9.6 — letter-bubble note allowing alpha-modulated fills on phase-header chips (per §2.4).

Files that MUST land in the same commit:

- `design-system/SPEC.md`
- `design-system/assets/styles/composed-components.css`
- `design-system/assets/styles/tokens-and-primitives.css` (verify canonical light overrides, no drift)
- `design-system/assets/Design System v2.html` (cost-chip example update + light-mode visual reference)
- `src/dual_research/ui/static/tokens.css` (light-mode override)
- `src/dual_research/ui/static/components.css` (scoped chip rules)
- `src/dual_research/ui/static/run-detail.jsx` (`fmtCost2` helper + call-site swap)
- `CHANGELOG.md` (new MINOR section)
- `pyproject.toml` (version bump)
- `src/dual_research/__init__.py` (version bump)

## 7. Test plan

- [ ] **Token drift fix.** Open the live app in light mode. Computed style on a Claude-toned chip's label resolves `color === rgb(59, 40, 16)` (`#3b2810`). On a GPT-toned chip, `color === rgb(10, 50, 45)` (`#0a322d`). Before this spec, these resolved to the dark-mode cream/mint values.
- [ ] **App-wide light-mode sweep.** Open the live `/#/language` route in light mode. Every Claude- or GPT-toned chip on the page reads with dark text on its tinted background. No regressions from previous light-mode rendering.
- [ ] **Critique-pane sanity.** Open a run with critique items in light mode. Critique-card Claude/GPT chips read with the canonical dark text colours (they share the same token). No layout breakage.
- [ ] **Timeline identity chips dark mode.** `.tl-card-head .chip.tone-claude` has computed `background-color === color-mix(in srgb, rgb(212, 165, 116) 30%, transparent)`. `.chip.tone-gpt` resolves to 30 % sage. `.chip.tone-neutral:not(.mono)` resolves to 20 % idle + `color === var(--md-on-surface)` resolved.
- [ ] **Activity chip surface.** `.tl-card-head .chip.tone-neutral.mono` has computed `background-color` equal to the resolved `--md-surface-container-highest` value, one tier brighter than the card. The chip is visibly distinct from the card surface in both themes.
- [ ] **Phase-header category bubble dim.** Open a run with `.tl-phase__chips` rendering. `.tl-phase__chips .chip.tone-info .cat-bubble` background resolves to a 70 % info-blue color-mix. Knockout-white letter is legible.
- [ ] **Cost precision — sub-cent.** Expand a turn card with cost `< $0.01`. The action-row cost chip renders `<$0.01`. The DOM text content matches `<$0.01` exactly.
- [ ] **Cost precision — typical.** Expand a turn card with cost between $0.01 and $99.99. Chip text matches `/^\$\d+\.\d{2}$/` (2-decimal mandatory).
- [ ] **Cost precision — footer audit unchanged.** The run-detail footer aggregate cost displays 4-decimal precision (its existing `fmtCost` behaviour).
- [ ] **No global chip regression.** Open the live `/#/language` route. Standalone `.chip.tone-claude` / `.chip.tone-gpt` chips (NOT inside a `.tl-card-head` scope) render at their original 18 %/26 %-tinted backgrounds, unchanged. The scoping is correct.
- [ ] **Tests pass.** `uv run pytest tests/ -q` exits 0.

## 8. Implementation steps (suggested order)

1. Add the two missing light-mode tokens to `src/dual_research/ui/static/tokens.css` (§2.1). Verify the canonical `design-system/assets/styles/tokens-and-primitives.css` has the same values; if drifted, fix there too.
2. Run the app-wide light-mode sweep (§7) to baseline what the token fix changes visually.
3. Update `design-system/SPEC.md` §4.4 + §9.6 with the scoped chip rules + cost precision rule.
4. Add the scoped rules to `design-system/assets/styles/composed-components.css`.
5. Mirror to `src/dual_research/ui/static/components.css`.
6. Add `fmtCost2` to `src/dual_research/ui/static/run-detail.jsx` and switch the expanded-card action call site.
7. Re-render `design-system/assets/Design System v2.html` examples that show cost chips.
8. Run the test plan in full (§7).
9. Write the CHANGELOG entry. Bump version files.

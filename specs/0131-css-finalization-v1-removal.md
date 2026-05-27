---
spec: 0131
title: CSS finalization + v1 token block removal + IBM Plex removal (close the migration arc)
label: refactoring
version-bump: PATCH
status: proposed
target-version: 1.6.9
created: 2026-05-20
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0131 — CSS finalization + v1 token block removal

> Depends on: 0127, 0128, 0129, 0130 (entire JSX side of the migration arc).
> Part of: 5-spec migration arc 0127 → 0131. **Fifth and final spec; closes the loop.**
> Complexity: **H** (~374 CSS token replacements + theme.css legacy-class drain + v1 token block deletion + IBM Plex removal + SPEC § 12 deletion + cross-route visual matrix). The riskiest spec in the arc because it's the no-return moment.
> Drive mode: **by hand** (mechanical token sweep + targeted deletions + careful verification).

> Pre-flight: this branch was created off `main` at the time of spec 0127 planning. Before executing, run `git fetch && git rebase origin/main` to pick up specs 0128 + 0129 + 0130. Re-run the audit greps in § 4 to confirm CSS v1 counts still match — drift > ~20 references means the spec needs a refresh.
>
> **HARD PREREQUISITE.** Run `grep -clE 'var\(--(bg|fg|border|r|t)-' src/dual_research/ui/static/*.jsx` first. If this returns any matches, **stop and do not execute 0131**. Some JSX file from spec 0130 still has v1 references; that work must finish before 0131 can delete the v1 token definitions.

## 1. Context

After specs 0127 (canonicalization), 0128 (run-detail.jsx), 0129 (design-language.jsx), and 0130 (other JSX) ship, **every `.jsx` file in `src/dual_research/ui/static/` reads from the v2 (`--md-*`) token vocabulary**. The remaining v1 token consumers live in three places:

1. **CSS files** — `base.css` (~36 v1 refs), `components.css` (~323 v1 refs), `theme.css` (~15 v1 refs + 8 legacy classes). Combined ~374 v1 references across CSS.
2. **The v1 token *definition* block** at the top of `src/dual_research/ui/static/tokens.css` (roughly lines 1–164). These DEFINE the v1 tokens (`--bg-0: #...`, `--fg-1: #...`, etc.); deleting them is the act that retires v1.
3. **IBM Plex font `<link>` tags** in `index.html` plus the `--sans` / `--serif` / `--mono` v1 font aliases in `tokens.css`. With JSX migrated to `--md-font-data` / `--md-font-plain` / `--md-font-brand`, these are unused.
4. **`design-system/SPEC.md § 12 Migration status`** — the temporary tracking table introduced by spec 0127. Deleting it is the formal "the migration is done" signal.
5. **FullReference SwatchGrid items + narration line in `design-language.jsx`** — deferred out of spec 0129 (handover: [`handoffs/2026-05-20-spec-0129-design-language-jsx-m3-migration.md` § "Deferred from this spec"](../handoffs/2026-05-20-spec-0129-design-language-jsx-m3-migration.md)). Three call sites carry v1 vocabulary as **literal display content** — not via `var()` — so the 0129 mechanical sweep grep couldn't reach them. The hardcoded v1 dark-mode hex values in these items will become orphan references the moment 0131 deletes the v1 token block from `tokens.css`, so re-baselining them belongs in the same PR. ~14 SwatchGrid items + 1 narration line, ~30 lines of content rewrite.

This spec ships all five in one PR. After it lands:

- Any leftover `var(--bg-*)` / `var(--fg-*)` / `var(--border-*)` / `var(--r-*)` / `var(--t-*)` / `var(--mono)` / `var(--sans)` / `var(--serif)` reference in the repo resolves to undefined and breaks visibly — **no silent fallback masks a missed migration**.
- IBM Plex stops loading. Roboto Flex + Roboto Serif + Material Symbols are the only font stacks.
- `design-system/SPEC.md` no longer carries the migration-status section; the design system is documented as a single coherent state.

This is the **no-return** spec. Treat it accordingly: visual regression matrix is comprehensive (every routed surface in both themes at both density breakpoints), and the implementer must hold the PR until each matrix shot has been hand-verified against `main`.

## 2. Goals

1. Migrate every v1 token reference inside `base.css`, `components.css`, `theme.css` to its v2 equivalent per § 5.
2. Drain `theme.css` of its 8 legacy v1 component classes — for each: either rewrite under v2 tokens and move into `components.css`, or delete if no consumer remains.
3. Delete the v1 token *definition* block from `tokens.css` (the `--bg-*`, `--fg-*`, `--border-*`, `--r-*`, `--t-*` definitions + the `--sans` / `--serif` / `--mono` font aliases + the light-mode `body.light` v1 overrides).
4. Remove the IBM Plex `<link>` tags from `index.html`.
5. Delete `design-system/SPEC.md § 12 Migration status` (the section becomes obsolete once 0131 ships).
6. Rewrite the FullReference SwatchGrid items at `design-language.jsx:451-472` (5 Surfaces + 5 Foreground + 4 Status = **14 items**) with v2 token short-names + v2-resolved hex values + updated role text. Rewrite the inline narration string at `design-language.jsx:~587` (`"border-1 (#1c1f24) hairline · border-2 medium · border-3 strong"`) to name `--md-outline-hair` / `--md-outline-variant` / `--md-outline` instead. See § 5d for the full replacement table.
7. Acceptance grep `grep -rE 'var\(--(bg|fg|border|r|t|mono|sans|serif)-?[0-9]*\)' src/dual_research/ui/static/` returns **0** matches.
8. Acceptance grep `grep -i "IBM Plex" src/dual_research/ui/static/index.html` returns **0** matches.
9. Acceptance grep `grep -nE "'(bg|fg|border)-[0-9]'" src/dual_research/ui/static/design-language.jsx` returns **0** matches (no v1 short-names left as display content).
10. Full pytest suite (1194+) passes.
11. Every routed surface renders without visible regression in dark + light, comfortable + compact density.

## 3. Non-goals

- **No JSX edits beyond the FullReference content rewrite carried over from 0129 (see § 5d).** Every `.jsx` was already migrated by 0128/0129/0130 at the `var()` level; this spec only touches the 14 SwatchGrid items + 1 narration line in `design-language.jsx` that carry v1 vocabulary as literal display content (handover deferred work).
- **No new components or features.** Pure removal + token sweep + targeted content rewrite of v1-vocabulary literals.
- **No design system spec rewrite beyond removing § 12.** SPEC.md content is already v2-canonical (set by spec 0127); this spec only deletes the temporary migration-status section.
- **No diagram skill alignment.** The cream + indigo palette of the diagram skill stays as-is (deferred to a future optional spec per the spec 0127 decision).
- **No CHANGELOG history rewrite.** Old entries that reference v1 tokens stay as historical record.
- **No removal of the `_archive/v1/` folder.** Historical reference preserved per spec 0127.

## 4. Current-state audit

CSS v1 token counts (re-audited 2026-05-20 post-rebase against main `c907463` — i.e. after 0128/0129/0130 merged):

| File | v1 refs (`bg/fg/border/r/t`) | + font aliases (`mono/sans/serif`) | Notes |
|---|---:|---:|---|
| `tokens.css` | 0 in `var(…)` usage | 1 (`--mono: var(--sans)` alias) | The v1 *definition* block lives here (lines 1–162; v1 light-mode overrides lines 348–362). Deletion target. |
| `base.css` | **43** (was 36 at draft) | 10 (`--sans` ×6, `--serif` ×4) | Re-audit drift: +7. Concentrated in `.t-*` type utility classes + scrollbar / focus / selection helpers. |
| `components.css` | **383** (was 323 at draft) | 33 (`--sans` ×15, `--mono` ×13, `--serif` ×5) | Re-audit drift: **+60, above the spec's ~20 refresh trigger**. No strategic change — same mechanical sweep covers it. Pre-M3 component catalog: every `.chip`, `.card`, `.tab`, `.as`, `.sb`, `.cs-*`, `.qthread`, `.consumption-*`, `.phase-rail-*`, `.dr-modal-*`, etc. |
| `theme.css` | **15** (clean match) | 2 (`--mono`) | Eight legacy classes — `.phase-step-line`, `.uppercase-label`, `.dr-ghost-block` + `.dr-ghost-block::before` + `.dr-ghost-block-kind`, `.dr-section-brief-btn` + `:hover`, `.cap-bar` + `> i` + `> .soft-mark`, `.bg-grid`. |
| **Total** | **441** | **46** | Plus the v1 token block (definitions) in `tokens.css`. |

**Plus two unmapped tokens discovered at re-audit** (see § 5 addendum):
- `var(--r-pill)` — 10 refs in `components.css`. Maps to `var(--md-shape-full)`.
- `var(--r-4)` — 0 refs anywhere; just delete the definition.
- `var(--t-sm)` — 1 orphan ref at `components.css:848` (`.quote-callout font-size`). The token is **undefined** — the line silently inherits parent `font-size`. Pre-existing quiet bug. Fix as part of the sweep: map to `var(--md-body-s-size)` (12 / 16) — the closest M3 role to the implied size (v1 had no `--t-sm` defined; the typo most likely intended `--t-meta` = 12 px).

**Plus two residual JSX targets absorbed from 0130's handover + one extra discovered:**
- `run-list.jsx` — 2 `var(--mono)` refs.
- `search-palette.jsx` — 5 `var(--mono)` refs **+ 1 `var(--sans)` ref at line 153** (the `--sans` was not in 0130's handover; surfaced at this re-audit).
- These pre-date the 0128 convention; they must sweep in this PR because 0131 deletes `--mono` / `--sans` from `tokens.css`.

### Legacy-class disposition (decided at re-audit time)

| Class | Functional consumers (grepped 2026-05-20) | Disposition |
|---|---|---|
| `.phase-step-line` | none found | **DELETE** |
| `.uppercase-label` | `design-language.jsx` × 4 sites (`:73`, `:773`, `:808`, `:845`) | **MIGRATE** to `components.css` under v2 tokens |
| `.dr-ghost-block` family | `run-detail.jsx` | **MIGRATE** to `components.css` under v2 tokens |
| `.dr-section-brief-btn` (+`:hover`) | `run-detail.jsx` | **MIGRATE** to `components.css` under v2 tokens |
| `.cap-bar` family (+`>i`, `>.soft-mark`) | `design-language.jsx:674` | **MIGRATE** to `components.css` under v2 tokens |
| `.bg-grid` | none found | **DELETE** |

> **Execution note:** re-run counts at execution start:
> ```
> for f in tokens.css base.css components.css theme.css; do printf "%4d  %s\n" $(grep -cE 'var\(--(bg|fg|border|r|t)-[0-9]+\)' src/dual_research/ui/static/$f) $f; done
> ```

### Theme.css legacy-class disposition

For each legacy class, decide one of: **migrate** (rewrite under v2 tokens, move to `components.css`), **delete** (no consumer remains), **keep** (still needed; rewrite under v2 tokens in place).

| Class | Current consumers (grep at execution time) | Disposition (decide at execution) |
|---|---|---|
| `.phase-step-line` | (re-grep) | likely: migrate to `components.css` under M3 tokens |
| `.uppercase-label` | (re-grep) — superseded by `.t-label-s` | likely: delete if no consumer; otherwise migrate |
| `.dr-ghost-block` family | (re-grep) | likely: keep / migrate — used by review-item placeholders |
| `.dr-section-brief-btn` | (re-grep) | likely: migrate to `components.css` |
| `.cap-bar` family | (re-grep) | likely: migrate — used by consumption cards |
| `.bg-grid` | (re-grep) | likely: migrate — used by streaming surfaces |

Recommended: a one-pass grep per class to enumerate consumers (`grep -rl "<class>" src/dual_research/ui/static/`) and document the disposition decisions in the PR description.

### IBM Plex disposition

- `index.html:10` — `<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@400;500;600;700&display=swap" rel="stylesheet" />` — **delete**.
- `index.html:11` — comment about SPEC-0092 keeping IBM Plex as the body default — **delete** (the comment is stale).
- `tokens.css:82-84` — `--sans` / `--serif` / `--mono` v1 font aliases — **delete** as part of the v1 token block removal.

After deletion, the only `<link>` font stacks loaded are Roboto Flex + Roboto Serif + Material Symbols.

## 5. Token mapping (mechanical, applies to all three CSS files)

Same as 0128 / 0129 / 0130:

| Find | Replace with |
|---|---|
| `var(--bg-0)` | `var(--md-surface)` |
| `var(--bg-1)` | `var(--md-surface-container-low)` |
| `var(--bg-2)` | `var(--md-surface-container)` |
| `var(--bg-3)` | `var(--md-surface-container-high)` |
| `var(--bg-4)` | `var(--md-surface-container-highest)` |
| `var(--fg-0)` | `var(--md-on-surface)` |
| `var(--fg-1)` | `var(--md-on-surface-variant)` |
| `var(--fg-2)` | `var(--md-on-surface-muted)` |
| `var(--fg-3)` | `var(--md-on-surface-faint)` |
| `var(--fg-4)` | `var(--md-on-surface-decor)` |
| `var(--border-1)` | `var(--md-outline-hair)` |
| `var(--border-2)` | `var(--md-outline-variant)` |
| `var(--border-3)` | `var(--md-outline)` |
| `var(--r-1)` | `var(--md-shape-xs)` |
| `var(--r-2)` | `var(--md-shape-sm)` |
| `var(--r-3)` | `var(--md-shape-md)` |
| `var(--mono)` | `var(--md-font-data)` |
| `var(--sans)` | `var(--md-font-plain)` |
| `var(--serif)` | `var(--md-font-brand)` |
| `var(--t-display)` | `var(--md-display-s-size)` + `var(--md-display-s-lh)` |
| `var(--t-title)` | `var(--md-title-l-size)` + `var(--md-title-l-lh)` |
| `var(--t-h3)` | `var(--md-title-m-size)` + `var(--md-title-m-lh)` |
| `var(--t-body)` | `var(--md-body-m-size)` + `var(--md-body-m-lh)` |
| `var(--t-meta)` | `var(--md-body-s-size)` + `var(--md-body-s-lh)` |
| `var(--t-mono)` | `var(--md-label-s-size)` + `var(--md-label-s-lh)` |
| `var(--t-label)` | `var(--md-label-s-size)` + `var(--md-label-s-lh)` (10/11 px shift acceptable) |
| `var(--r-pill)` | `var(--md-shape-full)` (999 px → 9999 px; visually identical at common sizes — 10 refs in `components.css`; not in original draft) |
| `var(--t-sm)` | `var(--md-body-s-size)` + `var(--md-body-s-lh)` (1 orphan ref at `components.css:848`; the v1 token was never defined — this swap also fixes a pre-existing inherit-from-parent bug) |
| `var(--sans)` *(in JSX)* | `var(--md-font-plain)` (1 ref at `search-palette.jsx:153` — JSX residual not in 0130's handover) |
| `var(--mono)` *(in JSX)* | `var(--md-font-data)` (2 refs in `run-list.jsx`, 5 in `search-palette.jsx` — absorbed from 0130's handover) |

## 5d. FullReference SwatchGrid + narration rewrite (deferred from 0129)

Three call sites in `src/dual_research/ui/static/design-language.jsx` carry v1 token vocabulary as **literal display content** — no `var()` reference, so spec 0129's mechanical sweep grep couldn't reach them. They must be rewritten in this spec because the hardcoded v1 dark-mode hex values become orphan references the moment § 6 step 5 deletes the v1 token block from `tokens.css`.

**Hex re-baseline source:** every v2 hex in the tables below is the resolved dark-mode value from `src/dual_research/ui/static/tokens.css` (the M3 block). Re-verify at execution time — if a hex in `tokens.css` has shifted since this spec was drafted, use the live value.

### 5d.1 — Surfaces SwatchGrid (`design-language.jsx:451-457`)

Replace the 5 items in the Surfaces `SwatchGrid`:

| Before | After |
|---|---|
| `{ name: 'bg-0', hex: '#08090b', role: 'Page / streaming body' }` | `{ name: 'surface', hex: '#0d0f12', role: 'Default surface — panels, sheets' }` |
| `{ name: 'bg-1', hex: '#0d0f12', role: 'Panels' }` | `{ name: 'surf-low', hex: '#111317', role: 'Recessed surface — default panel' }` |
| `{ name: 'bg-2', hex: '#131519', role: 'Elevated rows' }` | `{ name: 'surf-mid', hex: '#14171c', role: 'Elevated row / chip background / modal header' }` |
| `{ name: 'bg-3', hex: '#191c21', role: 'Hover / chip' }` | `{ name: 'surf-high', hex: '#191c21', role: 'Hover / active chip' }` |
| `{ name: 'bg-4', hex: '#1f2329', role: 'High contrast' }` | `{ name: 'surf-highest', hex: '#21252b', role: 'Highest static tier — dropdown row' }` |

(Short-names match the DnaSwatch labels that 0129 introduced at lines 48-61, so the DNA and Full reference grids agree.)

### 5d.2 — Foreground SwatchGrid (`design-language.jsx:459-465`)

Replace the 5 items in the Foreground `SwatchGrid`:

| Before | After |
|---|---|
| `{ name: 'fg-0', hex: '#f2f4f7', role: 'Primary text / numbers' }` | `{ name: 'on-surface', hex: '#ffffff', role: 'Primary text / numbers / headings' }` |
| `{ name: 'fg-1', hex: '#c8ccd3', role: 'Body text' }` | `{ name: 'on-variant', hex: '#b4bac4', role: 'Body prose' }` |
| `{ name: 'fg-2', hex: '#8c929c', role: 'Secondary / meta' }` | `{ name: 'on-muted', hex: '#9aa0ac', role: 'Secondary text / meta / labels' }` |
| `{ name: 'fg-3', hex: '#5e636d', role: 'Muted / labels' }` | `{ name: 'on-faint', hex: '#7d8290', role: 'Muted / column headers' }` |
| `{ name: 'fg-4', hex: '#3f444c', role: 'Decorative' }` | `{ name: 'on-decor', hex: '#50545d', role: 'Decorative / inline dividers' }` |

### 5d.3 — Status SwatchGrid (`design-language.jsx:467-472`)

Names stay (status hues are M3-orthogonal). Hexes get re-baselined against the resolved values in `tokens.css`:

| Before | After |
|---|---|
| `{ name: 'ok', hex: '#6fb380', role: 'Resolved / converged / completed' }` | `{ name: 'ok', hex: '#6fb380', role: 'Resolved / converged / completed' }` (verify hex against `--p-ok`) |
| `{ name: 'info', hex: '#6b9cf0', role: 'Running / current phase' }` | `{ name: 'info', hex: '#6b9cf0', role: 'Running / current phase' }` (verify hex against `--p-info`) |
| `{ name: 'warn', hex: '#d4a056', role: 'Approaching cap / deadlocked' }` | `{ name: 'warn', hex: '#d4a056', role: 'Approaching cap / deadlocked' }` (verify hex against `--p-warn`) |
| `{ name: 'err', hex: '#d96a6a', role: 'Errored / halted' }` | `{ name: 'err', hex: '#d96a6a', role: 'Errored / halted' }` (verify hex against `--p-err`) |

(If the resolved values in `tokens.css` haven't drifted from the hexes shown, the only change is a "verified against tokens.css" line in the PR description.)

### 5d.4 — Border narration line (`design-language.jsx:~587`)

Replace the inline narration string:

| Before | After |
|---|---|
| `"border-1 (#1c1f24) hairline · border-2 medium · border-3 strong"` | `"outline-hair (#1c1f24) hairline · outline-variant medium · outline strong"` |

(Hex re-verified against `--md-outline-hair` in `tokens.css`; the v1 → v2 mapping for `--border-1` resolves to the same color, so the hex stays.)

### 5d.5 — Acceptance grep

After the rewrites, this must return 0:

```
grep -nE "'(bg|fg|border)-[0-9]'" src/dual_research/ui/static/design-language.jsx
```

(Catches any leftover v1 short-name in the file's display content. Goal #9.)

## 6. Execution order (recommended)

Strict order — earlier steps must be green before later steps run.

1. **Pre-flight gate.** Confirm `grep -rclE 'var\(--(bg|fg|border|r|t|mono)-?[0-9]*\)' src/dual_research/ui/static/*.jsx` returns 0. If not, stop — 0130 isn't done.
2. **Migrate `base.css`** per § 5. Visual-check `/#/runs` chrome.
3. **Migrate `theme.css`** per § 5. For each legacy class: re-grep consumers; either rewrite under v2 in place, move to `components.css`, or delete (record decision in PR description).
4. **Migrate `components.css`** per § 5. Largest file; expect 300+ replacements. After: visual-check every routed surface (the full matrix in § 8).
5. **Delete the v1 token *definition* block** from `tokens.css`. Specifically:
   - Lines roughly 1–164: every `--bg-*` / `--fg-*` / `--border-*` / `--r-*` / `--t-*` definition.
   - The `--sans` / `--serif` / `--mono` v1 font aliases.
   - The v1 `body.light` overrides for the deleted tokens.
   - The header comment "dual-research — Design System V1 — Tokens" line; replace with v2-canonical comment.
   - Leave intact: agent-identity tokens, status hues, and every `--md-*` block.
6. **Remove IBM Plex from `index.html`.** Delete the `<link>` tag + the stale SPEC-0092 comment about IBM Plex.
7. **Delete `design-system/SPEC.md § 12 Migration status`.** The section becomes obsolete; this is the formal completion signal.
8. **FullReference SwatchGrid + narration rewrite** per § 5d. Edit `design-language.jsx` to replace the 14 SwatchGrid items + 1 narration line. Run the § 5d.5 acceptance grep.
9. **Bump versions** (pyproject + __init__ + uv.lock) → `1.6.9`. Cache-bust to next increment.
10. **Run pytest.** Must be 1194+ passing.
11. **Visual matrix.** Capture every shot in § 8. Compare against `main`. Hold the PR until all shots are clean.

## 7. Files touched

- `src/dual_research/ui/static/tokens.css` — delete v1 token *definition* block (~164 lines removed); update header comment; remove v1 light-mode overrides.
- `src/dual_research/ui/static/base.css` — migrate 36 v1 refs to v2.
- `src/dual_research/ui/static/components.css` — migrate 323 v1 refs to v2.
- `src/dual_research/ui/static/theme.css` — migrate 15 v1 refs to v2; drain or rewrite 8 legacy classes. After drain, the file may be empty enough to consider deleting; if so, also drop the `<link rel="stylesheet" href="theme.css?v=…">` from `index.html` and the cache-bust string.
- `src/dual_research/ui/static/index.html` — remove IBM Plex `<link>` tags; remove stale comment; cache-bust to next increment.
- `src/dual_research/ui/static/design-language.jsx` — FullReference SwatchGrid + narration rewrite per § 5d (14 SwatchGrid items + 1 narration line, ~30 lines of content). Deferred from spec 0129's mechanical sweep because the literal display content isn't reachable via `var()`-based find/replace.
- `src/dual_research/ui/static/run-list.jsx` — 2 `var(--mono)` → `var(--md-font-data)` (residual not in 0130's scope; absorbed here so the `--mono` deletion in `tokens.css` doesn't orphan these refs).
- `src/dual_research/ui/static/search-palette.jsx` — 5 `var(--mono)` → `var(--md-font-data)` + 1 `var(--sans)` → `var(--md-font-plain)`. Same rationale as `run-list.jsx`. The `--sans` ref at `:153` was not in 0130's handover — surfaced at 0131 re-audit.
- `design-system/SPEC.md` — delete § 12 Migration status; update SPEC version notes (the "spec authoritative" note at the top can drop its reference to "migration in flight").
- `design-system/CHANGELOG.md` — update line 27 reference to `SPEC.md § 12` (the section is being removed; rephrase as historical "migration completed in spec 0131").
- `design-system/PROMPT-FOR-CLAUDE-DESIGN.md` — update line 107 reference to `SPEC.md § 12` (the migration is now complete; rephrase from active-tense to past-tense).
- `design-system/CHANGELOG.md` — new entry: "v1 → v2 migration arc complete (spec 0131)".
- `CHANGELOG.md` (root) — new `[1.6.9]` / `### Changed` (or `### Removed`) entry referencing this spec; calls out the v1 token block deletion + IBM Plex removal as the headline change.
- `pyproject.toml` — `1.6.8` → `1.6.9`.
- `src/dual_research/__init__.py` — `__version__` `"1.6.8"` → `"1.6.9"`.
- `uv.lock` — refresh.

## 8. Test plan

### Acceptance criteria

- [ ] `grep -rE 'var\(--(bg|fg|border|r|t)-[0-9]+\)' src/dual_research/ui/static/` returns **0**.
- [ ] `grep -rE 'var\(--(mono|sans|serif)\)' src/dual_research/ui/static/` returns **0**.
- [ ] `grep -i "IBM Plex" src/dual_research/ui/static/index.html` returns **0**.
- [ ] `grep -nE '^\s*--(bg|fg|border|r|t)-[0-9]+:' src/dual_research/ui/static/tokens.css` returns **0** (v1 definitions deleted).
- [ ] `grep -c "Migration status" design-system/SPEC.md` returns **0** (§ 12 deleted).
- [ ] `grep -c "V1" src/dual_research/ui/static/tokens.css` returns **0** (header comment updated).
- [ ] `grep -nE "'(bg|fg|border)-[0-9]'" src/dual_research/ui/static/design-language.jsx` returns **0** (no v1 short-names left as display content per § 5d.5).
- [ ] `uv run pytest tests/ -q` → **1194+ passed**, 0 new failures.
- [ ] Visual matrix (§ below) shows no regression beyond the documented shape bump on residual classes (if any).
- [ ] `/#/language?full=1` Surfaces + Foreground + Status grids display v2 short-names (`surface`, `surf-low`, …, `on-faint`, `ok`, …) — verify by eye against the swatch labels.
- [ ] `/#/language?full=1` border-narration paragraph reads `"outline-hair (#1c1f24) hairline · outline-variant medium · outline strong"` (not `border-1/2/3`).

### Visual regression matrix

This is the comprehensive matrix. Every routed surface, both themes, both density breakpoints. Capture from `main` before branch; compare side-by-side at PR review time.

| Route | Dark 2200×1300 | Light 2200×1300 | Dark 1400×900 | Light 1400×900 |
|---|---|---|---|---|
| `/#/runs` | ✓ | ✓ | ✓ | ✓ |
| `/r/<finished-run>` top | ✓ | ✓ | ✓ | ✓ |
| `/r/<finished-run>` items panel scrolled | ✓ | ✓ | — | — |
| `/r/<finished-run>` consumption panel | ✓ | ✓ | — | — |
| `/#/compare` (≥ 2 runs) | ✓ | ✓ | — | — |
| `/#/search?q=test` | ✓ | ✓ | — | — |
| `/#/settings` allowlist | ✓ | ✓ | — | — |
| `/#/settings#users` (admin) | ✓ | — | — | — |
| `/#/how-it-works` overview | ✓ | ✓ | — | — |
| `/#/how-it-works#cost` | ✓ | — | — | — |
| `/#/language` DNA | ✓ | ✓ | ✓ | — |
| `/#/language?full=1` | ✓ | ✓ | — | — |
| Onboarding step 4 (modal) | ✓ | — | — | — |
| 404 / error route | ✓ | ✓ | — | — |
| `body.compact` active (force via DevTools) | spot-check 3 routes | spot-check 3 routes | — | — |

**Total: ~32 hand-captured shots.** Yes, this is a lot — it's the cost of the no-return spec. Don't shortcut.

### Smoke checks during execution

- After each file migration: load `/#/runs` once, look at console, look at network, scroll. If any new red flag, stop and investigate before proceeding to the next file.
- After the v1 token block deletion: load every route once. **Any visible regression here means a `var(--bg-*)` consumer was missed** — find it via DevTools (search computed styles for "undefined" or fallback values) and fix before continuing.

## 9. Risks

1. **A consumer was missed.** Most consequential risk. Mitigation: pre-flight gate in § 6, comprehensive visual matrix in § 8. If a regression slips into prod, roll back the merge and identify the missed consumer.

2. **A `--md-*` token has wrong contrast in a corner case.** Every mapping in § 5 has shipped via 0128 + 0129 + 0130 across JSX without incident, so CSS-level swaps should behave identically. Mitigation: full visual matrix in both themes.

3. **`theme.css` legacy class drain misjudges a consumer.** Mitigation: re-grep before each class disposition; document decisions in PR description; if uncertain, **migrate rather than delete** — leftover classes are cheap, missing classes break the consumer.

4. **Light mode shadow opacity tuning.** The v1 token block contained per-theme shadow tuning. Confirm the M3 elevation tokens (which already have light-mode overrides in `tokens.css`) cover every shadow consumer. If a `box-shadow: var(--e-1)` style reference exists somewhere, that's a v1 elevation token — map to `--md-elev-1`.

5. **Cache-bust collision.** If two specs land cache-bust at the same time, browsers may serve stale CSS. Mitigation: pick a fresh `?v=` string distinct from anything used by 0127–0130.

6. **`design-system/SPEC.md § 12` removal misses a reference.** Other docs may link to § 12 (e.g., the v1 archive README). Re-grep `grep -rn "§ 12\|Migration status" design-system/` and update any pointer accordingly.

7. **Counts have drifted significantly from the audit.** The ~374 number is from 2026-05-20; by the time this spec executes, several other specs may have touched CSS. Re-run § 4 audit at execution start.

## 10. Roll-out and roll-back

- **Roll-out.** Single PR to `main`. CI green + full visual matrix captured + PR description lists every theme.css class disposition decision. Fly deploy on merge. **After deploy, smoke-test prod immediately** — every route, both themes.
- **Roll-back.** Revert the merge commit. Because this spec is comprehensive, a revert is safer than a forward fix if any post-deploy regression is unclear. The pre-merge state is byte-for-byte recoverable.

## 11. After this ships — the migration arc is complete

Final state, post-0131:

- **One design system**: v2 (Material 3), documented in `design-system/SPEC.md`, canonical visual reference at `design-system/assets/Design System v2.html`, source-of-truth CSS at `design-system/assets/styles/{tokens-and-primitives,composed-components}.css`.
- **One token vocabulary in code**: `--md-*` everywhere. Agent identity tokens (`--agent-*`) and status hues (`--ok`/`--info`/`--warn`/`--err`/`--idle`) preserved as M3-orthogonal extras.
- **One font stack**: Roboto Flex + Roboto Serif + Material Symbols Outlined. No IBM Plex.
- **One historical record**: the v1 spec preserved at `design-system/_archive/v1/SPEC.md`; the seeding artifacts at `design-system/_archive/seeding/`. Specs 0050–0126 reference v1 paths as historical record of how the migration unfolded; nothing is rewritten retroactively.
- **No drift trap**: the additive layering pattern is gone. Any `var(--bg-*)` reference fails visibly. CI vocabulary checks (already in `tests/contract/test_ui_vocabulary.py`) can be extended to grep for `var(--bg|fg|border)-` and fail builds that re-introduce v1 syntax.

**Optional follow-ups** (outside the 5-spec arc, low priority):
- Diagram skill palette alignment (cream + indigo → sable + sage) — if/when the diagram-skill output should share visual DNA with the in-app UI.
- CI lint that asserts `pyproject.toml` and `__init__.py` versions agree, preventing the kind of drift that spec 0127 had to catch up.

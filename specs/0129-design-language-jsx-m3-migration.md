---
spec: 0129
title: design-language.jsx v1 → v2 token migration
label: refactoring
version-bump: PATCH
status: accepted
target-version: 1.6.7
created: 2026-05-20
pr: ""
---

# Spec 0129 — `design-language.jsx` v1 → v2 token migration

> Depends on: 0127 (design-system v2 canonicalization), 0128 (run-detail.jsx token migration), 0092 (additive M3 token layer).
> Part of: 5-spec migration arc 0127 → 0131. **Third spec; second live-code spec.**
> Complexity: **M** (~965-line file, 179 token replacements + 8 DnaSwatch relabels, no logic changes). Lower than 0128 because the file is much smaller and has more consistent inline-style patterns.
> Drive mode: **by hand** (token sweep — mechanical but visible since this file IS the design-system showcase).

> Pre-flight: this branch was created off `main` at the time of spec 0127 / 0128 planning. Before executing, run `git fetch && git rebase origin/main` to pick up any commits that landed in between. Re-run the audit greps in § 4 to confirm the token counts still match — drift > ~10 references means the spec needs a refresh.

## 1. Context

Spec 0128 (shipped, v1.6.6) completed the v1 → v2 token migration for `run-detail.jsx`, leaving `design-language.jsx` as the next-largest concentration of v1 tokens in the live frontend: **173** `var(--(bg|fg|border|t|r)-*)` references plus **6** `var(--mono)` references — **179 total replacements** in style blocks and JSX props. On top of the mechanical sweep, the **DNA palette swatches** (8 entries) also need their `label=` / `token=` display props relabeled to M3 short-names, because the swatch labels are display content — not just style — and a pure sweep would leave the page actively misleading (a swatch labeled "bg-0" rendering the v2 surface color).

`design-language.jsx` is the in-app design-system reference page, served at `/#/language`. It holds the DNA one-pager (default view) plus the Full reference (`?full=1`) — every component spotlight, every token swatch, every typography ladder is rendered here as a live, browsable specimen of the design system. Today, this file is **100% on the v1 token vocabulary**, which means the in-app reference page actively misrepresents the design system — it shows the v1 surfaces, v1 inks, v1 outlines, even while the v2 (M3) tokens are documented in `design-system/SPEC.md` and used by every M3-migrated component on every other route.

After this spec lands, the design-language page reads from the v2 (`--md-*`) token vocabulary end-to-end, and the in-app reference is once again an honest representation of what the rest of the app uses. The remaining v1 token consumers move to spec 0130 (`app/errors/compare/auth/search/shared.jsx`) and spec 0131 (CSS finalization + v1 token block removal).

## 2. Goals

1. Replace every `var(--bg-*)` / `var(--fg-*)` / `var(--border-*)` / `var(--r-*)` / `var(--mono)` reference inside `src/dual_research/ui/static/design-language.jsx` with its v2 equivalent per the table in § 5.
2. Relabel the 8 `DnaSwatch` entries in the DNA palette (`design-language.jsx:48-61`) from v1 token short-names to M3 short-names — `label="bg-0"` / `token="--bg-0"` → `label="surface"` / `token="--md-surface"`, etc. This is a content change scoped to display props, not a markup/logic change. Required for the DNA page to not misrepresent the new palette after the sweep.
3. Leave all other code paths untouched: agent identity tokens (`--agent-a`, `--agent-b`, `--claude`, `--gpt`), status hues (`--ok`, `--info`, `--warn`, `--err`, `--idle` + their `-bg` / `-border` variants), local `COLORS` JS constants, and existing `--md-*` references stay as-is.
4. Acceptance grep `grep -cE 'var\(--(bg|fg|border|r|t)-' design-language.jsx` → **0**.
5. Acceptance grep `grep -cE 'var\(--mono' design-language.jsx` → **0**.
6. The DNA one-pager (`/#/language`) and Full reference (`/#/language?full=1`) both render with no visual regression beyond the documented shape bump (§ 8, risk 1) in dark + light mode at 2200 × 1300 and 1400 × 900.
7. Full pytest suite (1194+) passes.

## 3. Non-goals

- **No `.css` file edits.** `tokens.css` (v1 block), `base.css`, `components.css`, `theme.css` stay untouched until spec 0131.
- **No font-family changes** beyond the in-JSX swap (`var(--mono)` → `var(--md-font-data)`). IBM Plex still loads from `index.html` until 0131.
- **No other JSX files.** `app/errors/compare/auth/search/shared.jsx` are out of scope (0130).
- **No content changes to the design-language page, beyond the 8-swatch DNA palette relabel covered in § 2 goal 2.** Same DNA one-pager, same Full reference, same spotlights. If a Component Spotlight visibly disagrees with the production component after the swap, that's a separate fix; file it as a follow-up, don't quietly edit the markup here.
- **No FullReference `SwatchGrid` rewrite, no narration rewrite.** The literal `name: 'bg-0', hex: '#08090b'` items at `design-language.jsx:451-465` and the narration string at `:587` (`"border-1 (#1c1f24) hairline · border-2 medium · border-3 strong"`) stay v1 in this spec — they need v2 hex re-baselining and editorial rewriting that doesn't belong in a mechanical sweep. Tracked as a follow-up in § 10.
- **No markup, no logic, no other prop changes.** Same React tree, same handlers, same conditional rendering.
- **No new tokens.** Every replacement is to an existing `--md-*` token already defined in `tokens.css`.
- **No new tests.** Existing 1194+ pytest cases must continue to pass. Visual verification is hand-shot.

## 4. Current-state audit

Token reference inventory in `design-language.jsx` (965 lines, audited 2026-05-20 against main `6b24d6b`):

| v1 token | Count | Maps to (v2) | Notes |
|---|---:|---|---|
| `--fg-3` | 43 | `--md-on-surface-faint` | Muted, column headers — typically the dominant ink in spotlight bodies. |
| `--border-1` | 28 | `--md-outline-hair` | Hairline (most spotlight cards). |
| `--fg-2` | 21 | `--md-on-surface-muted` | Secondary text, labels. |
| `--fg-0` | 21 | `--md-on-surface` | Primary text / numbers / headings. |
| `--r-3` | 17 | `--md-shape-md` | 8 px → 12 px (see § 8 risks). |
| `--bg-1` | 15 | `--md-surface-container-low` | Default panel. |
| `--fg-1` | 9 | `--md-on-surface-variant` | Body prose. |
| `--border-2` | 8 | `--md-outline-variant` | Medium. |
| `--mono` | 6 | `--md-font-data` | `font-family` only. Pre-empts the 0131 deletion. |
| `--bg-0` | 6 | `--md-surface` | Page surface. |
| `--bg-3` | 2 | `--md-surface-container-high` | Hover / active chip. |
| `--r-2` | 1 | `--md-shape-sm` | 6 px → 8 px (see § 8 risks). |
| `--border-3` | 1 | `--md-outline` | Strong outline. |
| `--bg-2` | 1 | `--md-surface-container` | Elevated row / chip bg. |
| **Total** | **179** | — | |

Not present in `design-language.jsx` (rows the spec originally listed but the audit grep returned zero for — dropped to keep the mapping table honest): `--fg-4`, `--r-1`, `--bg-4`, and all `--t-*` type tokens. § 5b previously documented the `--t-*` mapping; with no `--t-*` references in the file, that subsection is removed.

In addition to the 179 `var(--…)` swaps, the **8 DnaSwatch entries at `design-language.jsx:48-61`** carry the v1 token short-name as display content via the `label=` / `token=` props. Those need a content swap to M3 short-names, scoped to those props only — see § 5c.

Adjacencies kept as-is (not v1):
- `var(--agent-a)` / `var(--agent-b)` — agent identity, M3-orthogonal.
- `var(--info)` / `var(--ok)` / `var(--warn)` / `var(--err)` / `var(--idle)` — status hues, M3-orthogonal.
- All existing `var(--md-*)` references.

Edge-case scan (executed 2026-05-20):
- **DNA palette swatches (lines 48-61).** 8 `DnaSwatch` entries pass v1 token names as display props (`label="bg-0"`, `token="--bg-0"`). The mechanical sweep covers the `color="var(--bg-0)"` prop on each swatch, but the `label=` / `token=` strings need a content swap — handled in this spec per § 5c.
- **FullReference `SwatchGrid` items (lines 451-465).** 13 items with `name: 'bg-0', hex: '#08090b', role: '…'` baked in as v1 literals. These don't use `var()`, so the sweep grep doesn't touch them. Rewriting them requires re-baselining hex codes against the resolved v2 dark-mode values in `tokens.css` and editorial decisions on role text — **deferred to the follow-up in § 10**.
- **Inline narration at line 587:** `"border-1 (#1c1f24) hairline · border-2 medium · border-3 strong"` is teaching content naming v1 tokens. Same deferral — § 10 follow-up.
- The Full reference contains no other "before/after" or literal-token spotlights that would conflict with the sweep.

## 5. Token mapping (mechanical, file-wide)

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

### 5b — DnaSwatch palette relabel (`design-language.jsx:48-61`)

The 8 DNA palette swatches carry v1 token names as display content. After this spec lands the DNA page reads from v2 surfaces and inks, so the labels must match. Scoped to the `label=` and `token=` props on those exact lines — no markup, no logic.

| Before (props on each swatch) | After |
|---|---|
| `label="bg-0" color="var(--bg-0)" token="--bg-0"` | `label="surface" color="var(--md-surface)" token="--md-surface"` |
| `label="bg-1" color="var(--bg-1)" token="--bg-1"` | `label="surf-low" color="var(--md-surface-container-low)" token="--md-surface-container-low"` |
| `label="bg-2" color="var(--bg-2)" token="--bg-2"` | `label="surf-mid" color="var(--md-surface-container)" token="--md-surface-container"` |
| `label="bg-3" color="var(--bg-3)" token="--bg-3"` | `label="surf-high" color="var(--md-surface-container-high)" token="--md-surface-container-high"` |
| `label="fg-0" color="var(--fg-0)" token="--fg-0"` | `label="on-surface" color="var(--md-on-surface)" token="--md-on-surface"` |
| `label="fg-1" color="var(--fg-1)" token="--fg-1"` | `label="on-variant" color="var(--md-on-surface-variant)" token="--md-on-surface-variant"` |
| `label="fg-2" color="var(--fg-2)" token="--fg-2"` | `label="on-muted" color="var(--md-on-surface-muted)" token="--md-on-surface-muted"` |
| `label="fg-3" color="var(--fg-3)" token="--fg-3"` | `label="on-faint" color="var(--md-on-surface-faint)" token="--md-on-surface-faint"` |

Short-name choices favour brevity (`surface`, `surf-low`, `surf-mid`, `surf-high`, `on-variant`, `on-muted`, `on-faint`, `on-surface`) so the swatch labels stay readable in the 28×28 swatch grid. The `token=` prop carries the full canonical token name for users who copy it out.

## 6. Files touched

- `src/dual_research/ui/static/design-language.jsx` — 179 `var()` swaps per § 5 + 8 DnaSwatch relabels per § 5b. ~185 line edits total.
- `src/dual_research/ui/static/index.html` — cache-bust `?v=0128a` → `?v=0129a` on every static asset link/script (25 occurrences).
- `pyproject.toml` — `1.6.6` → `1.6.7`.
- `src/dual_research/__init__.py` — `__version__` `"1.6.6"` → `"1.6.7"`.
- `uv.lock` — refresh.
- `CHANGELOG.md` — new `[1.6.7]` entry under the `## [Unreleased]` heading.

Notably **not** touched: `tokens.css`, `base.css`, `components.css`, `theme.css`, every other `.jsx`, the FullReference `SwatchGrid` items at `design-language.jsx:451-465`, the narration at `:587`, `design-system/SPEC.md § 12` (updated by 0131).

## 7. Test plan

### Acceptance criteria

- [ ] `grep -cE 'var\(--(bg|fg|border|r|t)-' src/dual_research/ui/static/design-language.jsx` returns **0**.
- [ ] `grep -cE 'var\(--mono' src/dual_research/ui/static/design-language.jsx` returns **0**.
- [ ] `grep -cE 'var\(--md-' src/dual_research/ui/static/design-language.jsx` returns **≥ ~160** (existing M3 refs + the new ones).
- [ ] `uv run pytest tests/ -q` → **1194+ passed**, 0 new failures.
- [ ] Browser load of `/#/language` and `/#/language?full=1`: **no new console errors**, **no new network 404s**. Every spotlight renders. Every swatch shows the documented color.
- [ ] The Component Spotlights for `<Chip>`, `<StatusBadge>`, `<Card>`, `<Tab>` visibly match what those components render on a real `/r/<id>` page (i.e., the in-app reference is an honest mirror of production).

### Visual regression matrix

Hand-captured via Playwright with `dr_onboarded=true` injected:

- `2200 × 1300 dark` — DNA one-pager, top.
- `2200 × 1300 dark` — DNA one-pager, scrolled to component spotlights.
- `2200 × 1300 light` — same two states.
- `1400 × 900 dark` — DNA one-pager (compact density triggers at < 1500).
- `1400 × 900 light` — DNA one-pager.
- `2200 × 1300 dark` — Full reference (`?full=1`), top.
- `2200 × 1300 light` — Full reference, top.

Compared against a same-route screenshot captured from `main` immediately before branch. The two sets must read identically modulo the radius bump and minor type-size shifts noted in § 8.

## 8. Risks

1. **Radius visual bump.** Same as 0128: `--r-2: 6px` → `--md-shape-sm: 8px` (+2 px); `--r-3: 8px` → `--md-shape-md: 12px` (+4 px). Acceptable per design-system contract (SPEC.md § 2.6). Captured in the visual matrix.

2. **Type-size shifts** (§ 5b). The M3 type scale differs from v1 by 1–2 px at most sizes. Mostly invisible; occasionally noticeable on tight layouts. Mitigation: visual matrix covers this; one-shot layout tweaks acceptable if needed.

3. **`--mono` → `--md-font-data` font-feature shift.** Same as 0128: a quiet upgrade to Roboto Flex + tabular-nums. The 6 sites where this appears are likely numeric data (token IDs, scale numbers, swatch labels).

4. **A v1 token reference is missed by the sweep.** Grep-based acceptance criteria catch this — the PR cannot land if grep returns non-zero.

5. **A `--md-*` token chosen here turns out to have wrong contrast.** Every mapping in § 5 mirrors what spec 0128 used for run-detail, which has shipped without incident. Mitigation: light-mode visual matrix.

6. **Spotlight literally references a v1 token name in its body text.** If a spotlight teaches the reader about `var(--bg-1)` by name, the literal string must stay. Find/replace only inside `style={{ … }}` and `className` props. Acceptance grep would falsely flag these as misses — exempt by adding a `// design-spotlight:literal-token-ok` comment near the literal and updating the grep to exclude that line.

7. **DnaSwatch relabel introduces a small content delta.** The DNA palette swatches will display M3 short-names ("surface", "on-faint", …) instead of v1 short-names ("bg-0", "fg-3", …). Intentional and required for the page to be honest after the sweep. Captured in the visual matrix.

## 9. Roll-out and roll-back

- **Roll-out.** Single PR to `main`, merged when CI is green and the visual matrix is captured. Fly deploy on merge.
- **Roll-back.** Single-file revert. No DB / no API / no schema changes.

## 10. Follow-ups (already planned)

After 0129 merges, the remaining two specs in the arc are unchanged:

| Spec | Scope |
|---|---|
| 0130 | `app.jsx` / `errors.jsx` / `compare.jsx` / `auth.jsx` / `search.jsx` / `shared.jsx` v2 sweep (~204 v1 refs across 6 files) |
| 0131 | CSS finalization: v1 token block removal from `tokens.css`, IBM Plex `<link>` removal from `index.html`, `theme.css` legacy-class drain, `design-system/SPEC.md § 12` removal |

`design-system/SPEC.md § 12 Migration status` (the temporary tracking table) is updated in spec 0131's PR, not here.

### Newly opened by this spec

| Item | Scope | Why deferred |
|---|---|---|
| **FullReference v2 swatch + narration rebuild** | Rewrite the `SwatchGrid` items at `design-language.jsx:451-465` (13 entries: v1 names + v1 dark-mode hexes + role text) to v2 token short-names + v2-resolved hex values + updated role text. Same treatment for the inline narration string at `:587` (`"border-1 (#1c1f24) hairline · …"`). | Requires re-baselining hex codes against the resolved v2 dark-mode values in `tokens.css` and editorial decisions on role text — out of scope for the mechanical sweep this spec promises. Naturally rides spec 0131 (v1 token block removal forces re-baselining anyway) or can be a standalone hotfix. |

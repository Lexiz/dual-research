---
spec: 0129
title: design-language.jsx v1 → v2 token migration
label: refactoring
version-bump: PATCH
status: proposed
target-version: 1.6.7
created: 2026-05-20
pr: ""
---

# Spec 0129 — `design-language.jsx` v1 → v2 token migration

> Depends on: 0127 (design-system v2 canonicalization), 0128 (run-detail.jsx token migration), 0092 (additive M3 token layer).
> Part of: 5-spec migration arc 0127 → 0131. **Third spec; second live-code spec.**
> Complexity: **M** (~3,400-line file, ~160 token replacements, no logic changes). Lower than 0128 because the file is smaller and has more consistent inline-style patterns.
> Drive mode: **by hand** (token sweep — mechanical but visible since this file IS the design-system showcase).

> Pre-flight: this branch was created off `main` at the time of spec 0127 / 0128 planning. Before executing, run `git fetch && git rebase origin/main` to pick up any commits that landed in between. Re-run the audit greps in § 4 to confirm the token counts still match — drift > ~10 references means the spec needs a refresh.

## 1. Context

Spec 0128 (shipped, v1.6.6) completed the v1 → v2 token migration for `run-detail.jsx`, leaving `design-language.jsx` as the next-largest concentration of v1 tokens in the live frontend: **154** `var(--(bg|fg|border|t|r)-*)` references plus **6** `var(--mono)` references — **~160 total replacements**.

`design-language.jsx` is the in-app design-system reference page, served at `/#/language`. It holds the DNA one-pager (default view) plus the Full reference (`?full=1`) — every component spotlight, every token swatch, every typography ladder is rendered here as a live, browsable specimen of the design system. Today, this file is **100% on the v1 token vocabulary**, which means the in-app reference page actively misrepresents the design system — it shows the v1 surfaces, v1 inks, v1 outlines, even while the v2 (M3) tokens are documented in `design-system/SPEC.md` and used by every M3-migrated component on every other route.

After this spec lands, the design-language page reads from the v2 (`--md-*`) token vocabulary end-to-end, and the in-app reference is once again an honest representation of what the rest of the app uses. The remaining v1 token consumers move to spec 0130 (`app/errors/compare/auth/search/shared.jsx`) and spec 0131 (CSS finalization + v1 token block removal).

## 2. Goals

1. Replace every `var(--bg-*)` / `var(--fg-*)` / `var(--border-*)` / `var(--r-*)` / `var(--t-*)` / `var(--mono)` reference inside `src/dual_research/ui/static/design-language.jsx` with its v2 equivalent per the table in § 5.
2. Leave all other code paths untouched: agent identity tokens (`--agent-a`, `--agent-b`, `--claude`, `--gpt`), status hues (`--ok`, `--info`, `--warn`, `--err`, `--idle` + their `-bg` / `-border` variants), local `COLORS` JS constants, and existing `--md-*` references stay as-is.
3. Acceptance grep `grep -cE 'var\(--(bg|fg|border|r|t)-' design-language.jsx` → **0**.
4. Acceptance grep `grep -cE 'var\(--mono' design-language.jsx` → **0**.
5. The DNA one-pager (`/#/language`) and Full reference (`/#/language?full=1`) both render with no visual regression beyond the documented shape bump (§ 8, risk 1) in dark + light mode at 2200 × 1300 and 1400 × 900.
6. Full pytest suite (1194+) passes.

## 3. Non-goals

- **No `.css` file edits.** `tokens.css` (v1 block), `base.css`, `components.css`, `theme.css` stay untouched until spec 0131.
- **No font-family changes** beyond the in-JSX swap (`var(--mono)` → `var(--md-font-data)`). IBM Plex still loads from `index.html` until 0131.
- **No other JSX files.** `app/errors/compare/auth/search/shared.jsx` are out of scope (0130).
- **No content changes to the design-language page.** Same DNA one-pager, same Full reference, same spotlights — only the token strings inside inline `style={{ … }}` objects change. If a Component Spotlight visibly disagrees with the production component after the swap, that's a separate fix; file it as a follow-up, don't quietly edit the markup here.
- **No markup, no logic, no prop changes.** Same React tree, same handlers, same conditional rendering. Pure token sweep.
- **No new tokens.** Every replacement is to an existing `--md-*` token already defined in `tokens.css`.
- **No new tests.** Existing 1194+ pytest cases must continue to pass. Visual verification is hand-shot.

## 4. Current-state audit

Token reference inventory in `design-language.jsx` (audited 2026-05-20 against main `93d0538`):

| v1 token | Count | Maps to (v2) | Notes |
|---|---:|---|---|
| `--fg-3` | (audit) | `--md-on-surface-faint` | Muted, column headers — typically the dominant ink in spotlight bodies. |
| `--fg-2` | (audit) | `--md-on-surface-muted` | Secondary text, labels. |
| `--border-1` | (audit) | `--md-outline-hair` | Hairline (most spotlight cards). |
| `--fg-1` | (audit) | `--md-on-surface-variant` | Body prose. |
| `--bg-2` | (audit) | `--md-surface-container` | Elevated row / chip bg. |
| `--r-2` | (audit) | `--md-shape-sm` | 6 px → 8 px (see § 8 risks). |
| `--bg-0` | (audit) | `--md-surface` | Page surface. |
| `--border-2` | (audit) | `--md-outline-variant` | Medium. |
| `--bg-1` | (audit) | `--md-surface-container-low` | Default panel. |
| `--fg-0` | (audit) | `--md-on-surface` | Primary text / numbers / headings. |
| `--fg-4` | (audit) | `--md-on-surface-decor` | Decorative / inline dividers. |
| `--bg-3` | (audit) | `--md-surface-container-high` | Hover / active chip. |
| `--mono` | 6 | `--md-font-data` | `font-family` only. Pre-empts the 0131 deletion. |
| `--r-3` | (audit) | `--md-shape-md` | 8 px → 12 px (see § 8 risks). |
| `--border-3` | (audit) | `--md-outline` | Strong outline. |
| `--r-1` | (audit) | `--md-shape-xs` | 4 px → 4 px. No visual change. |
| `--t-display` / `--t-title` / `--t-h3` / `--t-body` / `--t-meta` / `--t-mono` / `--t-label` | (audit) | M3 type-role utility classes (see § 5b) | The v1 `--t-*` tokens are font-size + line-height pairs; in M3 we either use `.t-<category>-<size>` utility classes or compose with `--md-<role>-size` / `--md-<role>-lh`. |
| **Total** | **~160** | — | |

> **Execution note:** populate the (audit) counts by running, at the top of the executing session, `grep -oE 'var\(--(bg|fg|border|r|t|mono)[a-z0-9-]*\)' src/dual_research/ui/static/design-language.jsx | sort | uniq -c | sort -rn` and pasting the result into this table. The counts below 0128's baseline have shifted as upstream files evolved; freshness matters.

Adjacencies kept as-is (not v1):
- `var(--agent-a)` / `var(--agent-b)` — agent identity, M3-orthogonal.
- `var(--info)` / `var(--ok)` / `var(--warn)` / `var(--err)` / `var(--idle)` — status hues, M3-orthogonal.
- All existing `var(--md-*)` references.

Edge-case scan (re-verify at execution time):
- The Full reference (`?full=1`) contains "before/after" or historical-style spotlights that may intentionally show v1 tokens as illustration. If any spotlight is captioned with literal token names, the spotlight content is shown as text — DO NOT migrate the literal text references, only the inline `style={{ … }}` references. Examples to look for: any chip or code-block that literally renders the string `var(--bg-1)` in its body.

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

### 5b — Type token replacements (special handling)

The v1 `--t-*` tokens are font-size values, not full type roles. Map each to its closest M3 equivalent. Prefer the M3 utility class where the JSX uses `className`; if the file inlines `style={{ fontSize: 'var(--t-body)', lineHeight: 'var(--lh-body)' }}`, swap both the size and line-height variables.

| Find | Replace with (size only) | Or replace with (class) |
|---|---|---|
| `var(--t-display)` (28 px) | `var(--md-display-s-size)` + `var(--md-display-s-lh)` | `.t-display-s` |
| `var(--t-title)` (20 px) | `var(--md-title-l-size)` + `var(--md-title-l-lh)` (22 px) | `.t-title-l` |
| `var(--t-h3)` (16 px) | `var(--md-title-m-size)` + `var(--md-title-m-lh)` | `.t-title-m` |
| `var(--t-body)` (13 px) | `var(--md-body-m-size)` + `var(--md-body-m-lh)` (14 px) | `.t-body-m` |
| `var(--t-meta)` (12 px) | `var(--md-body-s-size)` + `var(--md-body-s-lh)` | `.t-body-s` |
| `var(--t-mono)` (11 px) | `var(--md-label-s-size)` + `var(--md-label-s-lh)` | `.t-label-s` (uppercase) |
| `var(--t-label)` (10 px) | `var(--md-label-s-size)` + `var(--md-label-s-lh)` | `.t-label-s` (uppercase, smaller — fall back to inline 10 px if 11 px breaks layout) |

> **Caveat:** the v1 type scale and the M3 scale diverge by 1–2 px at most sizes. The design-system principle is to converge on M3 (per `SPEC.md § 2.5`); minor pixel shifts on the design-language page are acceptable and documented. If a layout in the Full reference breaks because of a 2 px size change, fix the layout (one-shot tweak); don't keep the v1 size.

## 6. Files touched

- `src/dual_research/ui/static/design-language.jsx` — token sweep per § 5 + § 5b. ~160 replacements.
- `src/dual_research/ui/static/index.html` — cache-bust `?v=0128a` → `?v=0129a` on every static asset link/script (or current cache-bust string at execution time → next increment).
- `pyproject.toml` — `1.6.6` → `1.6.7`.
- `src/dual_research/__init__.py` — `__version__` `"1.6.6"` → `"1.6.7"`.
- `uv.lock` — refresh.
- `CHANGELOG.md` — new `[1.6.7]` / `### Changed` entry referencing this spec.

Notably **not** touched: `tokens.css`, `base.css`, `components.css`, `theme.css`, every other `.jsx`, `design-system/SPEC.md § 12` (updated by 0131).

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

7. **File grows or shrinks between spec draft and execution.** Counts in § 4 are placeholders (marked "(audit)") — populate at execution time.

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

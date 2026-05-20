---
spec: 0128
title: run-detail.jsx v1 → v2 token migration
label: refactoring
version-bump: PATCH
status: proposed
target-version: 1.6.6
created: 2026-05-20
pr: ""
---

# Spec 0128 — `run-detail.jsx` v1 → v2 token migration

> Depends on: 0127 (design-system v2 canonicalization), 0092 (additive M3 token layer).
> Part of: 5-spec migration arc 0127 → 0131. **Second spec; first live-code spec.**
> Complexity: **M** (~7,260-line file, 243 + 22 + 4 = 269 token replacements, no logic changes).
> Drive mode: **by hand** (token sweep — mechanical but bulky).

## 1. Context

Spec 0127 (shipped 2026-05-20, v1.6.5) promoted the M3 (`--md-*`) design system to single source of truth in `design-system/SPEC.md`. The live frontend, however, still runs on the additive layering pattern introduced by spec 0092: v1 tokens (`--bg-*`, `--fg-*`, `--border-*`, `--r-*`, `--mono`) and v2 tokens (`--md-*`) coexist, and every `.jsx` file is free to use either vocabulary. `run-detail.jsx` is the page where this drift is most visible: it carries **243** `var(--(bg|fg|border)-*)` references plus **22** `var(--r-*)` and **4** `var(--mono)` references — by far the largest single concentration of v1 tokens in the live code.

This spec is the first of four live-code migration specs (0128 → 0131) that complete the v1 → v2 consolidation. It rewrites every v1 surface / ink / outline / shape / font reference inside `run-detail.jsx` to its `--md-*` equivalent. No logic, no markup structure, no behavior changes — pure token sweep against the precedent set by spec 0108 (run-list M3 migration).

After this spec lands, `run-detail.jsx` is fully on the v2 vocabulary and harmonises with run-list, design-language and the shared M3 primitives. The remaining v1 token consumers move to specs 0129 (`design-language.jsx`), 0130 (other JSX), and 0131 (CSS finalization + v1 token block removal).

## 2. Goals

1. Replace every `var(--bg-*)` / `var(--fg-*)` / `var(--border-*)` / `var(--r-*)` / `var(--mono)` reference inside `src/dual_research/ui/static/run-detail.jsx` with its v2 equivalent per the table in § 5.
2. Leave all other code paths untouched: agent identity tokens (`--agent-a`, `--agent-b`, `--claude`, `--gpt`), status hues (`--ok`, `--info`, `--warn`, `--err`, `--idle` + their `-bg` / `-border` variants), `COLORS` JS constants, and existing `--md-*` references stay as-is.
3. Acceptance grep `grep -cE 'var\(--(bg|fg|border|r)-' run-detail.jsx` → **0**.
4. Acceptance grep `grep -cE 'var\(--mono' run-detail.jsx` → **0**.
5. Dark- and light-mode visual parity with main on the `/r/<id>` route at 2200×1300 and 1400×900.
6. Full pytest suite (1194+) passes.

## 3. Non-goals

- **No `.css` file edits.** `tokens.css` (v1 block), `base.css`, `components.css`, `theme.css` stay untouched. The v1 token block deletion lives in spec 0131.
- **No font-family changes.** IBM Plex still loads from `index.html` until 0131; this spec only swaps `var(--mono)` → `var(--md-font-data)` at the JSX consumption site so that when `--mono` is deleted in 0131 nothing breaks.
- **No other JSX files.** `design-language.jsx`, `app.jsx`, `errors.jsx`, `compare.jsx`, `auth.jsx`, `search.jsx`, `shared.jsx` are out of scope (0129 + 0130).
- **No markup, no logic, no prop changes.** Same components, same handlers, same data flow. Only the token strings inside inline `style={{ … }}` objects (and the handful in template literals) change.
- **No new tokens.** Every replacement is to an existing `--md-*` token already defined in `tokens.css`.
- **No new tests.** Existing 1194 pytest cases must continue to pass. Visual verification is hand-shot.

## 4. Current-state audit

Token reference inventory in `run-detail.jsx` (7,260 lines, audited 2026-05-20):

| v1 token | Count | Maps to (v2) | Notes |
|---|---:|---|---|
| `--fg-3` | 67 | `--md-on-surface-faint` | Muted, column headers — already the dominant on-surface ink in the file. |
| `--fg-2` | 36 | `--md-on-surface-muted` | Secondary text, labels. |
| `--border-1` | 29 | `--md-outline-hair` | Hairline. |
| `--fg-1` | 28 | `--md-on-surface-variant` | Body prose. |
| `--bg-2` | 19 | `--md-surface-container` | Elevated row / chip bg. |
| `--r-2` | 18 | `--md-shape-sm` | 6 px → 8 px (see § 8 risks). |
| `--bg-0` | 16 | `--md-surface` | Page surface. |
| `--border-2` | 13 | `--md-outline-variant` | Medium. |
| `--bg-1` | 13 | `--md-surface-container-low` | Default panel. |
| `--fg-0` | 12 | `--md-on-surface` | Primary text / numbers / headings. |
| `--fg-4` | 11 | `--md-on-surface-decor` | Decorative / inline dividers. |
| `--bg-3` | 5 | `--md-surface-container-high` | Hover / active chip. |
| `--mono` | 4 | `--md-font-data` | `font-family` only. Pre-empts the 0131 deletion. |
| `--r-3` | 3 | `--md-shape-md` | 8 px → 12 px (see § 8 risks). |
| `--border-3` | 3 | `--md-outline` | Strong outline (focus, live-dot ring). |
| `--r-1` | 1 | `--md-shape-xs` | 4 px → 4 px. No visual change. |
| **Total** | **278** | — | |

Adjacencies kept as-is (not v1):
- `var(--agent-a)` / `var(--agent-b)` (3 + 3) — agent identity, M3-orthogonal.
- `var(--info)` / `var(--info-bg)` / `var(--ok)` / `var(--warn)` / `var(--err)` — status hues, M3-orthogonal.
- `var(--consumption-label-w)` — local CSS variable defined inside the file.
- All existing `var(--md-*)` references (already migrated by prior incidental sweeps).

Edge-case scan:
- **No `color-mix(...)` expressions** consume v1 tokens. No opacity / alpha tricks that could behave differently across the swap.
- **No `@keyframes` or `animation` declarations** reference v1 tokens. The only animations in the file (flash, expand/collapse) operate on numeric properties or status hues.
- **No light-mode-specific code paths** inside `run-detail.jsx`. Theme switching is entirely CSS-driven (`theme.css`), and the v2 tokens already have light-mode pairs defined in `tokens.css`. The swap is symmetric across themes.
- **30 ternary expressions** contain a v1 token in at least one branch. Every one of them is either `<status-hue> : <v1-token>` or `<v1-token-a> : <v1-token-b>` — both branches map mechanically with no semantic change.

## 5. Token mapping (mechanical, file-wide)

| Find | Replace with |
|---|---|
| `var(--bg-0)` | `var(--md-surface)` |
| `var(--bg-1)` | `var(--md-surface-container-low)` |
| `var(--bg-2)` | `var(--md-surface-container)` |
| `var(--bg-3)` | `var(--md-surface-container-high)` |
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

Sixteen mechanical find/replace operations across one file. No conditional logic in the swap.

## 6. Files touched

- `src/dual_research/ui/static/run-detail.jsx` — token sweep per § 5. ~278 replacements across 7,260 lines.
- `src/dual_research/ui/static/index.html` — cache-bust `?v=0126a` → `?v=0128a` on every static asset link/script that JSX consumers may have hot-loaded (the JSX itself must rev so browsers fetch the new file). Matches the bump convention from spec 0108.
- `pyproject.toml` — `1.6.5` → `1.6.6`.
- `src/dual_research/__init__.py` — `__version__` `"1.6.5"` → `"1.6.6"`.
- `uv.lock` — refresh.
- `CHANGELOG.md` — new `[1.6.6]` entry under Changed, referencing this spec and noting the 278-replacement scope + dark/light visual matrix.

Notably **not** touched: `tokens.css`, `base.css`, `components.css`, `theme.css`, every other `.jsx`, `design-system/SPEC.md` (§ 12 Migration status stays — it's updated by 0131).

## 7. Test plan

### Acceptance criteria

- [ ] `grep -cE 'var\(--(bg|fg|border|r)-' src/dual_research/ui/static/run-detail.jsx` returns **0**.
- [ ] `grep -cE 'var\(--mono' src/dual_research/ui/static/run-detail.jsx` returns **0**.
- [ ] `grep -cE 'var\(--md-' src/dual_research/ui/static/run-detail.jsx` returns **≥ 278** (existing M3 refs + the 278 new ones; today's baseline is 37, so target is ≥ 315).
- [ ] `uv run pytest tests/ -q` → **1194+ passed**, 0 new failures.
- [ ] Browser load of `/r/<any-finished-run>`: **no new console errors**, **no new network 404s** beyond the existing baseline. Header, timeline cards, items panel, consumption panel, footer all render.
- [ ] `getComputedStyle(document.body)` after the page settles shows the same `color` and `background-color` resolved values as pre-PR on a dark-mode build (the v1 tokens and v2 tokens are colour-equivalent by the design-system contract — see `tokens.css` § "Surfaces" and `SPEC.md § 2.2`).

### Visual regression matrix

Hand-captured via Playwright with `dr_onboarded=true` injected during init, on a finished run with timeline depth ≥ 5, items panel populated, and at least one warning event:

- `2200 × 1300 dark` — full run-detail page, scrolled to top.
- `2200 × 1300 dark` — scrolled into the items panel.
- `2200 × 1300 light` — top.
- `2200 × 1300 light` — items panel.
- `1400 × 900 dark` — top (compact density triggers at < 1500).
- `1400 × 900 light` — top.

Compared against a same-route screenshot captured from `main` immediately before branch. The two sets must read identically modulo the radius bump noted in § 8.

## 8. Risks

1. **Radius visual bump.** `--r-2: 6px` → `--md-shape-sm: 8px` (+2 px) and `--r-3: 8px` → `--md-shape-md: 12px` (+4 px). 21 surfaces in `run-detail.jsx` get this bump. **This is the same bump spec 0108 applied to run-list** and the design-system § 2.6 (Shape scale) is canonical — the file is converging to the documented shape vocabulary, not introducing a divergence. Mitigation: included in the visual-regression matrix; expect a perceptible-but-correct radius change on cards, chips, and pill backgrounds. Acceptable per design-system contract.

2. **`--mono` → `--md-font-data` font-feature shift.** `--mono` is a v1 alias to `--sans` (IBM Plex Sans). `--md-font-data` is Roboto Flex + `font-variant-numeric: tabular-nums`. At the 4 sites where this appears in `run-detail.jsx`, the surrounding context is numeric data (round costs, IDs). Roboto Flex + tabular nums is the **intended** typography per design-system § 2.5; this swap is a quiet upgrade, not a regression. Mitigation: visual-regression matrix covers all 4 sites (consumption panel + run-id pill + timestamp).

3. **A v1 token reference is missed by the sweep.** Grep-based acceptance criteria catch this — the PR cannot land if `grep -cE 'var\(--(bg|fg|border|r)-' run-detail.jsx` returns non-zero. Mitigation: criterion is in § 7 and will be checked pre-commit.

4. **A `--md-*` token chosen here turns out to have wrong contrast in light mode.** Every mapping in § 5 mirrors what spec 0108 used for run-list, which has shipped in light mode without incident since 2026-05-19. Mitigation: light-mode visual matrix in § 7.

5. **File grows or shrinks between spec draft and execution.** The 7,260-line / 269-v1-ref audit was taken at the spec draft moment. If a hotfix lands between approval and execution, the sweep grep still catches everything (it's not a per-line patch). Mitigation: re-run audit grep at the start of execution; if drift is > ~10 references, surface it before continuing.

## 9. Roll-out and roll-back

- **Roll-out.** Single PR to `main`, merged when CI is green and the visual matrix is captured. Fly deploy on merge (project convention).
- **Roll-back.** Single-file revert. No DB / no API / no schema changes. Reverting the commit restores the pre-PR state byte-for-byte.

## 10. Follow-ups (already planned)

After 0128 merges, the remaining three specs in the arc are unchanged:

| Spec | Scope |
|---|---|
| 0129 | `design-language.jsx` v2 rebuild (142 v1 refs) |
| 0130 | `app.jsx` / `errors.jsx` / `compare.jsx` / `auth.jsx` / `search.jsx` / `shared.jsx` v2 sweep (172 v1 refs) |
| 0131 | CSS finalization: v1 token block removal from `tokens.css`, IBM Plex `<link>` removal from `index.html`, `theme.css` legacy-class drain, `design-system/SPEC.md § 12` removal |

`design-system/SPEC.md § 12 Migration status` (the temporary tracking table) is updated in spec 0131's PR, not here — this spec leaves it alone.

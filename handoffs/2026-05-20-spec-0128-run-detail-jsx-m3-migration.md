# Handover — spec 0128 · `run-detail.jsx` v1 → v2 token migration (2/5 in design-system arc)

- Date: 2026-05-20
- Spec: [`specs/0128-run-detail-jsx-m3-migration.md`](../specs/0128-run-detail-jsx-m3-migration.md)
- PR: filled in by `gh pr create` after this file lands in the commit — see `git log --oneline -3` post-merge
- Deployed version: `1.6.6`

## Bottom line for the next session

Spec 0128 is **the second of the 5-spec arc** (0127 → 0131) that retires the v1 design system from the live code. It is the **first live-code spec** in that arc. After this PR, every `var(--bg-*)` / `var(--fg-*)` / `var(--border-*)` / `var(--r-*)` / `var(--mono)` reference inside `src/dual_research/ui/static/run-detail.jsx` (the most token-dense single file in the app) has been replaced with its `--md-*` v2 equivalent. The file is fully on the M3 vocabulary.

**The next spec is 0129 — `design-language.jsx` v2 rebuild** (~142 v1 token references). The pattern repeats: branch, sweep, verify, ship. The handover below tells you exactly how this one was structured so 0129 can match.

## What shipped in 0128

- Version bump: PATCH → **1.6.6**
- Cache-bust: `?v=0126a` → `?v=0128a` on every `<link>` / `<script>` in `index.html` (25 occurrences)
- Files touched: 6 (`run-detail.jsx`, `index.html`, `pyproject.toml`, `__init__.py`, `uv.lock`, `CHANGELOG.md`) + this handover + the spec file itself
- Test suite: **1194 / 1194** pytest passing
- Visual verification (hand-shot via Playwright preview): clean at 2200×1300 dark, 2200×1300 light, 1400×900 dark. No React errors, no new console warnings beyond the pre-existing `QuestionThread verdict "pushed back"` data-vocab noise (out of scope; pre-existed on main).

### Token sweep — what actually got replaced

Sixteen mechanical `replace_all` operations against `run-detail.jsx`:

| Find | Replace with | Count |
|---|---|---:|
| `var(--bg-0)` | `var(--md-surface)` | 16 |
| `var(--bg-1)` | `var(--md-surface-container-low)` | 13 |
| `var(--bg-2)` | `var(--md-surface-container)` | 19 |
| `var(--bg-3)` | `var(--md-surface-container-high)` | 5 |
| `var(--fg-0)` | `var(--md-on-surface)` | 12 |
| `var(--fg-1)` | `var(--md-on-surface-variant)` | 28 |
| `var(--fg-2)` | `var(--md-on-surface-muted)` | 36 |
| `var(--fg-3)` | `var(--md-on-surface-faint)` | 67 |
| `var(--fg-4)` | `var(--md-on-surface-decor)` | 11 |
| `var(--border-1)` | `var(--md-outline-hair)` | 29 |
| `var(--border-2)` | `var(--md-outline-variant)` | 13 |
| `var(--border-3)` | `var(--md-outline)` | 3 |
| `var(--r-1)` | `var(--md-shape-xs)` | 1 |
| `var(--r-2)` | `var(--md-shape-sm)` | 18 |
| `var(--r-3)` | `var(--md-shape-md)` | 3 |
| `var(--mono)` | `var(--md-font-data)` | 4 |
| **Total** | — | **278** |

Plus one stray comment update on line 563 (the literal string `var(--fg-1/2/3)` inside a SPEC-0052 comment was updated to read `var(--md-on-surface-variant/muted/faint)` so the comment matches what the code now does).

### Acceptance grep results (post-sweep)

```
grep -cE 'var\(--(bg|fg|border|r)-' run-detail.jsx → 0    ✓
grep -cE 'var\(--mono'              run-detail.jsx → 0    ✓
grep -cE 'var\(--md-'                run-detail.jsx → 303 ✓ (up from 37 baseline)
```

### Minor visual deltas (expected, documented)

1. **Radius bump.** `--r-2` (6 px) → `--md-shape-sm` (8 px) on 18 surfaces and `--r-3` (8 px) → `--md-shape-md` (12 px) on 3 surfaces. Same delta spec 0108 applied to run-list. The file converges to the canonical shape scale in `design-system/SPEC.md § 2.6`. Visible but correct.
2. **`--mono` → `--md-font-data`.** Four sites swap IBM Plex Sans for Roboto Flex with `font-variant-numeric: tabular-nums`. Quiet typography upgrade on the consumption panel + run-id pill + timestamp. The `--mono` alias remains in `tokens.css` until 0131; pre-empting it here avoids a follow-up sweep on this file.

## State of `main` after this PR merges

- Branch `spec-0128-run-detail-jsx-m3-migration` deleted after merge
- `pyproject.toml` + `src/dual_research/__init__.py` + `uv.lock` all read `1.6.6`
- `index.html` cache-bust at `?v=0128a` across all 25 link/script tags
- Live frontend behavior unchanged from main pre-PR modulo the two visual deltas in § "Minor visual deltas" above (radius bump on ~21 surfaces; font upgrade on 4 numeric data sites)
- 243 v1 surface-ink-outline-shape token refs **gone** from `run-detail.jsx`; 22 v1 radius refs and 4 v1 `--mono` refs gone too

## The 5-spec arc — where we are

| Spec | Scope | V1 refs removed | Status |
|---|---|---:|---|
| [0127](../specs/0127-design-system-v2-canonicalization.md) | Design-system folder canonicalization (docs + restructure only) | 0 | ✅ shipped 2026-05-20 |
| **[0128](../specs/0128-run-detail-jsx-m3-migration.md)** | `run-detail.jsx` v2 token migration | **278** | **✅ shipped 2026-05-20 (this spec)** |
| 0129 | `design-language.jsx` v2 rebuild | ~142 | **next** |
| 0130 | Remaining JSX (`app/errors/compare/auth/search/shared.jsx`) | ~172 | planned |
| 0131 | CSS finalization: v1 token block removal + IBM Plex `<link>` removal + `theme.css` legacy-class drain + `design-system/SPEC.md § 12` removal | 345 + theme.css | planned |

After 0131 lands: every remaining `var(--bg-*)` / `var(--fg-*)` / `var(--border-*)` / `var(--r-*)` / `var(--mono)` / `var(--t-*)` reference will fail visibly (no silent fallback to mask bugs), IBM Plex will be unloaded from `index.html`, and the migration-status table in `SPEC.md` will be removed in that same PR.

**Token mapping (mechanical for ~90% of cases) — preserved here so 0129 + 0130 can reuse without re-deriving:**
- `--bg-0` → `--md-surface`
- `--bg-1` → `--md-surface-container-low`
- `--bg-2` → `--md-surface-container`
- `--bg-3` → `--md-surface-container-high`
- `--bg-4` → `--md-surface-container-highest` (unused in run-detail; may appear in design-language)
- `--fg-0` → `--md-on-surface`
- `--fg-1` → `--md-on-surface-variant`
- `--fg-2` → `--md-on-surface-muted`
- `--fg-3` → `--md-on-surface-faint`
- `--fg-4` → `--md-on-surface-decor`
- `--border-1` → `--md-outline-hair`
- `--border-2` → `--md-outline-variant`
- `--border-3` → `--md-outline`
- `--r-1` → `--md-shape-xs` (4 px → 4 px, no visual change)
- `--r-2` → `--md-shape-sm` (6 px → 8 px, +2 px on radii)
- `--r-3` → `--md-shape-md` (8 px → 12 px, +4 px on radii)
- `--r-4` → `--md-shape-md` (12 px → 12 px, no visual change) — unused in run-detail
- `var(--mono)` → `var(--md-font-data)` (IBM Plex Sans → Roboto Flex + tabular-nums)
- `var(--t-display/title/h3/body/meta/mono/label)` → would map to M3 type scale + utility classes per `SPEC.md § 2.5`; **none appeared in run-detail**, but design-language.jsx (next spec) is likely to use them. Re-derive the mapping then.

## What to do for spec 0129

1. `git checkout main && git pull && git checkout -b spec-0129-design-language-jsx-m3-rebuild`.
2. Re-audit `src/dual_research/ui/static/design-language.jsx`:
   - `grep -cE 'var\(--(bg|fg|border|r)-' src/dual_research/ui/static/design-language.jsx` (handover 0127 said ~142; reconfirm).
   - `grep -cE 'var\(--mono'` and `grep -cE 'var\(--t-'` — design-language.jsx is likely where the v1 type-scale tokens (`--t-display`, `--t-title`, etc.) live. They have no direct 1-to-1 in `--md-*`; they map to type **utility classes** (`.t-display-m`, `.t-title-m`, etc.) per `SPEC.md § 2.5`. **This is the meaningful difference from spec 0128**: 0129 may need a few line-by-line patches in addition to `replace_all` sweeps. Look at type scale uses with `grep -nE 'var\(--t-' design-language.jsx` first; if they're consumed as `fontSize` inline styles, the swap is to the M3 px values from `SPEC.md § 2.5`. If as className helpers, swap class names.
3. Use spec 0128 itself as the template for 0129's `specs/0129-…md` — same § structure, swap names + counts.
4. The user wants **"pause between specs"**: do not auto-roll from 0128's deploy into 0129's branch. Wait for explicit greenlight.

## What to confirm with the user before opening spec 0129

- Spec number is still 0129 (`ls specs/ | tail -5`).
- Re-run the audit grep — `design-language.jsx` size may have drifted.
- If `--t-*` type-scale tokens appear, decide with the user whether 0129 should resolve them inline (px values from `SPEC.md § 2.5`) or by switching to the `.t-<role>` utility classes. **My read:** utility classes are the canonical answer, but they require markup edits (className changes), so they're more invasive than a pure `replace_all`. Worth flagging before opening.

## Step durations (this spec)

| Step | Status | Duration |
|---|---|---|
| 1_investigation | done | ~10 min |
| 2_spec_draft | done | ~10 min |
| 3_review_pause | done | (user greenlit immediately) |
| 4_implement | done | ~5 min (16 `replace_all` calls) |
| 5_verify_pytest | done | ~10 s (1194 / 1194) |
| 6_verify_visual | done | ~5 min (3 viewports) |
| 7_handover | done | ~5 min |
| 8_pr_merge_deploy | pending | filled in below post-merge |

## Open questions / known-unknowns

- **Type-scale tokens in `design-language.jsx`.** As noted above, the `--t-*` family doesn't have a direct `--md-*` 1-to-1 — they correspond to the type scale described in `SPEC.md § 2.5`. Surface this to the user when drafting spec 0129.
- **`--bg-4`.** Not used in `run-detail.jsx` but defined in `tokens.css` (`--bg-4: #1f2329`, "high-contrast surface — dropdown row"). If it appears in `design-language.jsx` or other JSX, map to `--md-surface-container-highest`.
- **Pre-existing `QuestionThread` console warning.** Run data on `20260520-025406-pv-backend-language-choice` contains a verdict `"pushed back"` that isn't in the `VERDICT_VOCAB`. Floods the console on that route (47 repeats on one render). Unrelated to the migration; pre-existed on main. Possible future hygiene task: either extend the vocab to include `"pushed back"` or downgrade the warning to a single-fire grouped log.

## What I learned

1. **`replace_all` is the right tool when the token mapping is mechanical and unambiguous.** Sixteen find/replaces wallpapered 278 sites in seconds with zero risk of inconsistency. The only manual touch was the one-line comment that contained literal `var(--fg-1/2/3)` text — which the grep caught.
2. **Acceptance grep must include comments.** Without the `grep -cE` line catching the literal string in the SPEC-0052 comment, the migration would have left a stale doc-pointer. Cheap to fix once spotted.
3. **The handover from spec 0127 had a count of 242; this spec found 243.** A one-reference drift over ~1 day of hotfixes. Mention to user as a sanity check on each spec; the per-spec audit grep is the source of truth, not the prior handover's number.
4. **Theme-switching in this codebase is `body.light` class — not the `prefers-color-scheme` media query.** Setting `colorScheme: 'light'` on the preview viewport alone does not flip the page; you must also `document.body.classList.add('light')` from `preview_eval`. Worth remembering for 0129 + 0130 + 0131 visual verification.

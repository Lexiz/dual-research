---
spec: 0130
title: Remaining JSX (app / errors / compare / auth / search / shared) v1 → v2 token migration
label: refactoring
version-bump: PATCH
status: proposed
target-version: 1.6.8
created: 2026-05-20
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0130 — Remaining JSX v1 → v2 token migration

> Depends on: 0127 (design-system v2 canonicalization), 0128 (run-detail.jsx token migration), 0129 (design-language.jsx token migration), 0092 (additive M3 token layer).
> Part of: 5-spec migration arc 0127 → 0131. **Fourth spec; third live-code spec.**
> Complexity: **M** (6 files, ~204 token replacements total, no logic changes). Bulkier than 0128/0129 because of file count, but smaller per-file scopes mean lower per-file risk.
> Drive mode: **by hand** (token sweep across 6 files in sequence).

> Pre-flight: this branch was created off `main` at the time of spec 0127 planning. Before executing, run `git fetch && git rebase origin/main` to pick up specs 0128 + 0129. Re-run the audit greps in § 4 to confirm per-file counts still match — drift > ~10 references per file means the spec needs a refresh.

## 1. Context

Specs 0128 (run-detail.jsx) and 0129 (design-language.jsx) cleared the two largest concentrations of v1 tokens in the live JSX. The remaining six JSX files together hold the last block of v1 token references in JSX: `app.jsx`, `errors.jsx`, `compare.jsx`, `auth.jsx`, `search.jsx`, `shared.jsx` — **~204** `var(--(bg|fg|border|t|r)-*)` references plus **~20** `var(--mono)` references.

`shared.jsx` is the most sensitive of the six because it holds the React function-components that the rest of the app consumes as design-system primitives (`<Chip>`, `<Card>`, `<Tab>`, `<TabGroup>`, `<AgentStrip>`, `<StatusBadge>`, `<CollapsibleSection>`, `<QuoteCallout>`, `<LoadingState>`, `<BrandMark>`, `<ModalDialog>`). A wrong mapping here propagates everywhere. Migrate it last in the per-file order below and visually verify against multiple consumer surfaces.

After this spec lands, **every `.jsx` file in `src/dual_research/ui/static/` is on the v2 token vocabulary**, and the live `var(--(bg|fg|border|r|t)-*)` references exist only inside CSS files. Spec 0131 closes the loop with CSS finalization + v1 token block removal.

## 2. Goals

1. Replace every `var(--bg-*)` / `var(--fg-*)` / `var(--border-*)` / `var(--r-*)` / `var(--t-*)` / `var(--mono)` reference inside the six target JSX files with its v2 equivalent per § 5.
2. Leave all other code paths untouched: agent identity tokens, status hues, `COLORS` constants, existing `--md-*` references.
3. Acceptance grep `grep -clE 'var\(--(bg|fg|border|r|t)-' src/dual_research/ui/static/{app,errors,compare,auth,search,shared}.jsx` returns **0** files.
4. Acceptance grep `grep -clE 'var\(--mono' src/dual_research/ui/static/{app,errors,compare,auth,search,shared}.jsx` returns **0** files.
5. Full pytest suite (1194+) passes.
6. Browser load of every route touched by these files (`/#/runs`, `/#/compare`, `/#/search`, error states, auth flow) renders without console errors or visible regression in dark + light mode at 2200 × 1300 and 1400 × 900.

## 3. Non-goals

- **No `.css` file edits.** All `.css` files stay untouched until spec 0131.
- **No font-family changes** beyond the in-JSX swap (`var(--mono)` → `var(--md-font-data)`). IBM Plex still loads until 0131.
- **No `run-detail.jsx` or `design-language.jsx` edits.** Already migrated by 0128 and 0129.
- **No application logic / behavior changes.** Only the token strings inside inline `style={{ … }}` objects (and any in template literals) change.
- **No new primitives.** `shared.jsx` keeps every primitive's external API stable. Internal token swaps only.
- **No new tests.** Existing 1194+ pytest cases must continue to pass.

## 4. Current-state audit

Per-file v1 token counts (re-audited 2026-05-20 post-rebase, against main after 0129 merged):

| File | `var(--bg|fg|border|r|t)-*)` | `var(--mono)` | Approx total |
|---|---:|---:|---:|
| `app.jsx` | 40 | 3 | 43 |
| `errors.jsx` | 39 | 1 | 40 |
| `compare.jsx` | 35 | 7 | 42 |
| `auth.jsx` | 33 | 3 | 36 |
| `search.jsx` | 24 | 3 | 27 |
| `shared.jsx` | 16 | 3 | 19 |
| **Total** | **187** | **20** | **207** |

> **Execution note:** drift will happen between draft and execution. Re-run `for f in app errors compare auth search shared; do printf "%4d (+ %d mono) %s.jsx\n" $(grep -cE 'var\(--(bg|fg|border|r|t)-' src/dual_research/ui/static/$f.jsx) $(grep -cE 'var\(--mono' src/dual_research/ui/static/$f.jsx) $f; done` at execution start and update the table.

Per-file scope notes:

- **`app.jsx`** — top-level shell, route mounting, chrome wrapper. Inline styles primarily for the chrome bar + theme toggle row. Low risk; standard mapping.
- **`errors.jsx`** — error / 404 / empty-state surfaces. Inline styles primarily for the error card + retry CTA. Low risk; standard mapping.
- **`compare.jsx`** — multi-run compare table. Inline styles primarily for the column headers + row dividers. Medium risk because the table grid is wide and a 2 px radius bump on row pills may shift column widths by a pixel or two. Visual check after.
- **`auth.jsx`** — sign-in / sign-out screens. Inline styles for the auth card, brand mark wrapper, error banner. Low risk; isolated surface.
- **`search.jsx`** — search results surface (distinct from `search-palette.jsx`, which is already on v2). Inline styles for result cards + meta row. Low risk.
- **`shared.jsx`** — **the design-system primitives.** Inline styles inside `<Chip>`, `<Card>`, etc. **Migrate this file LAST** in the per-file order so any surprise propagates to a smaller scope first. Visual check should include at least three consumer surfaces (run-detail timeline, critique pane, settings allowlist row).

## 5. Token mapping (mechanical, file-wide — same as 0128 / 0129)

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

Type tokens (`var(--t-*)`) — same handling as spec 0129 § 5b. If a target file uses `--t-*` size tokens, prefer the `.t-<category>-<size>` utility class when the call site uses `className`; otherwise inline the `--md-<role>-size` + `--md-<role>-lh` pair.

### 5b. Type-token resolutions (4 call sites — re-audit identified)

Unlike 0128 (none) and 0129 (none), this spec hits four real `--t-*` call sites. All four are `fontSize:` inside inline-style objects (no `className` route), so we inline the M3 `<role>-size` + `<role>-lh` pair per § 5 / 0129 § 5b. Decision table:

| File:line | Call site | v1 value | M3 role chosen | New tokens | Δ |
|---|---|---|---|---|---|
| `compare.jsx:89` | chrome-bar `<span>` "Compare runs" (semibold) | `--t-title` (20px) | `title-l` (22 / 28) | `fontSize: 'var(--md-title-l-size)', lineHeight: 'var(--md-title-l-lh)'` | +2 px |
| `search.jsx:69` | page `<h2>` "Cross-run search" (semibold) | `--t-title` (20px) | `title-l` (22 / 28) | same as above | +2 px |
| `search.jsx:78` | subtitle `<p>` under the h2 | `--t-body` (13px) | `body-m` (14 / 20) | `fontSize: 'var(--md-body-m-size)', lineHeight: 'var(--md-body-m-lh)'` | +1 px |
| `shared.jsx:930` | `<AgentStrip>` model-ID `<span>` | `--t-mono` (11px) | `label-s` (11 / 16) | `fontSize: 'var(--md-label-s-size)', lineHeight: 'var(--md-label-s-lh)'` | 0 |

Rationale:
- `--t-title` (20 px) falls between `title-l` (22) and `title-m` (16). `title-l` is the closer match by size and the matching role for "section H2 / modal title" in `SPEC.md § 2.5`. The +2 px bump is consistent with the radius-bump pattern of the rest of the arc.
- `--t-body` (13 px) → `body-m` (14 px) per `SPEC.md § 2.5`: "Body default is `body-m` (14 / 20)."
- `--t-mono` (11 px) → `label-s` (11 px) is an exact size match. Skip the M3 letter-spacing token (`--md-label-s-track: 0.5px`) — that's intended for uppercase labels; this call site is a model-ID string, not a label.

These four edits replace four lines of inline style and are committed alongside the file's surface/ink/outline/shape sweep — one commit per file per § 6.

## 6. Per-file execution order (recommended)

Do them in this order so the lowest-blast-radius files go first; `shared.jsx` is last so any surprise lands first in a single surface:

1. `errors.jsx` (smallest blast radius — isolated error states)
2. `auth.jsx` (smallest blast radius — auth screen only)
3. `search.jsx`
4. `compare.jsx`
5. `app.jsx` (chrome wrapper — affects every route, but the inline-style surface is small)
6. `shared.jsx` (primitives — affects everything)

Commit each file as a separate logical step within the same PR (one commit per file) so reverts can be surgical if a single file regresses.

## 7. Files touched

- `src/dual_research/ui/static/app.jsx` — token sweep per § 5.
- `src/dual_research/ui/static/errors.jsx` — token sweep per § 5.
- `src/dual_research/ui/static/compare.jsx` — token sweep per § 5.
- `src/dual_research/ui/static/auth.jsx` — token sweep per § 5.
- `src/dual_research/ui/static/search.jsx` — token sweep per § 5.
- `src/dual_research/ui/static/shared.jsx` — token sweep per § 5. **Last in the order; verify against multiple consumer surfaces.**
- `src/dual_research/ui/static/index.html` — cache-bust to the next version increment.
- `pyproject.toml` — `1.6.7` → `1.6.8`.
- `src/dual_research/__init__.py` — `__version__` `"1.6.7"` → `"1.6.8"`.
- `uv.lock` — refresh.
- `CHANGELOG.md` — new `[1.6.8]` / `### Changed` entry referencing this spec and noting per-file counts.

Notably **not** touched: every `.css` file, `index.html` (beyond cache-bust), `tokens.css` (v1 block still present), `design-system/SPEC.md § 12` (updated by 0131), the diagram skill, the audits.

## 8. Test plan

### Acceptance criteria

- [ ] For each of the 6 files: `grep -cE 'var\(--(bg|fg|border|r|t)-' <file>` returns **0**.
- [ ] For each of the 6 files: `grep -cE 'var\(--mono' <file>` returns **0**.
- [ ] After all 6 files migrated: combined grep `grep -lE 'var\(--(bg|fg|border|r|t)-' src/dual_research/ui/static/*.jsx` returns **no matches**.
- [ ] `uv run pytest tests/ -q` → **1194+ passed**, 0 new failures.
- [ ] Browser load of `/#/runs` (chrome via `app.jsx`), an error route (via `errors.jsx`), `/#/compare`, `/#/auth/sign-in` if visible, `/#/search`: **no new console errors**, **no new network 404s**. Every primitive renders.
- [ ] Three `shared.jsx` consumer-surface spot-checks: timeline cards on `/r/<id>`, critique cards on `/r/<id>`, settings allowlist row. All chips, status badges, agent strips render visually identical to pre-PR.

### Visual regression matrix

For each of the 6 files, capture the primary surface in both themes at the wide breakpoint. Targeted because the per-file blast radius is smaller than 0128/0129:

| File | Surface to capture | Themes / sizes |
|---|---|---|
| `app.jsx` | `/#/runs` top chrome | dark + light, 2200×1300 |
| `errors.jsx` | Force a 404 route | dark, 1400×900 |
| `compare.jsx` | `/#/compare` with ≥ 2 runs selected | dark + light, 2200×1300 |
| `auth.jsx` | `/#/auth/sign-in` (or a forced auth state) | dark + light, 1400×900 |
| `search.jsx` | `/#/search?q=test` | dark, 2200×1300 |
| `shared.jsx` | `/r/<id>` items panel + critique pane (consumer surfaces) | dark + light, 2200×1300 + 1400×900 |

Compared against same-route screenshots captured from `main` immediately before branch.

## 9. Risks

0. **Out-of-scope landmine spotted during audit: `var(--w-semibold)` is undefined.** `compare.jsx:90`, `search.jsx:70`, and `shortcuts-overlay.jsx:43` all reference `var(--w-semibold)`, but `tokens.css` only defines `--w-regular / --w-medium / --w-semi / --w-bold`. The token is a typo (should be `--w-semi`) and currently resolves to default weight (400, not 600) — a quiet pre-existing visual bug. The `--w-*` family is **outside** this arc's removal scope (0131 only removes `--bg/fg/border/r/t/mono`), so 0130 does NOT touch these lines. Flag in the handover; consider a follow-up spec.

1. **Radius visual bump.** Same as 0128/0129: `--r-2: 6px` → `--md-shape-sm: 8px`; `--r-3: 8px` → `--md-shape-md: 12px`. Acceptable per design-system contract. Captured in visual matrix.

2. **`shared.jsx` propagation.** A wrong mapping in `<Chip>` or `<Card>` affects every consumer. Mitigation: file order (last), per-file commits (revertable), three-surface visual check.

3. **`compare.jsx` table column widths** may shift by 1–2 px because of the radius bump on row pills. Acceptable; flag in CHANGELOG entry.

4. **`--mono` → `--md-font-data` font-feature shift.** Same as 0128/0129. The 20 sites where `--mono` appears across these 6 files should all be on numeric or ID content; tabular-nums is the upgrade, not a regression. If a non-numeric site uses `--mono` (e.g., a code-style snippet that wants monospace look), document the exception and switch that one site back to `font-family: ui-monospace, monospace` instead.

5. **A v1 token reference is missed.** Grep-based acceptance criteria catch this.

6. **Per-file counts have drifted** between spec draft and execution. Counts in § 4 are the post-0128 audit; re-run at execution start.

## 10. Roll-out and roll-back

- **Roll-out.** Single PR to `main` with 6 logical commits (one per file). CI green + visual matrix captured. Fly deploy on merge.
- **Roll-back.** If a single file regresses, revert that file's commit. If the whole PR regresses, revert the merge commit. No DB / schema / API changes.

## 11. Follow-ups (already planned)

After 0130 merges, **the only spec left** in the arc is:

| Spec | Scope |
|---|---|
| 0131 | CSS finalization: migrate ~374 v1 token refs in `base.css` + `components.css` + `theme.css` to v2; drain `theme.css` legacy classes (8 classes); delete v1 token block from `tokens.css` (lines 1–164); remove `--mono` / `--sans` v1 aliases; remove IBM Plex `<link>` tags from `index.html`; remove `design-system/SPEC.md § 12 Migration status` section. |

After 0131 ships, every `var(--bg-*)` / `var(--fg-*)` / `var(--border-*)` / `var(--r-*)` / `var(--t-*)` / `var(--mono)` reference in the repo will resolve to undefined — so any leftover v1 reference becomes a visible bug, no silent fallback. The 5-spec arc is complete.

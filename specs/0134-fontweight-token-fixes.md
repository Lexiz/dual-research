---
spec: 0134
title: Migrate hardcoded JSX fontWeight numbers to --md-w-* tokens (close the bypass gap)
label: refactoring
version-bump: PATCH
status: proposed
target-version: 1.6.11
created: 2026-05-20
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0134 — JSX fontWeight bypass cleanup

> Follows: 0132 (design-system pollution scrub). Same shape, different surface.
> Complexity: **S** (mechanical replace_all across 8 JSX files).
> Drive mode: **by hand** (small, scoped sweeps).

## 1. Context

A post-0132 audit of the frontend turned up a structural gap the 0127→0131 arc missed and 0132 didn't catch: **32 JSX call sites use raw `fontWeight: 600` (or 500 / 700) instead of consuming `var(--md-w-*)`**. The hardcoded numbers happen to match the M3 token values today (400/500/600/700), so they render correctly — but they're not actually subscribed to the design system. If the token values ever change, those 32 elements would not move.

This is structurally identical to the v1 token consumption problem the arc cleaned up in CSS, just in JSX inline-style props instead.

Three `rgba(...)` decorations in `auth.jsx` are also flagged: two teal gradient overlays (`rgba(124, 196, 184, 0.06)` — the agent-b/sage palette source value) and one black scrim shadow (`rgba(0,0,0,0.10)`). The teal overlays bypass the agent-color tokens; the black scrim follows the codebase's existing shadow-recipe pattern (`--md-elev-*` uses raw rgba too) so it stays.

## 2. Goals

1. Replace every JSX `fontWeight: NNN` literal with `fontWeight: 'var(--md-w-X)'` per this map:
   - `400` → `'var(--md-w-regular)'`
   - `500` → `'var(--md-w-medium)'`
   - `600` → `'var(--md-w-semi)'`
   - `700` → `'var(--md-w-bold)'`
2. Replace the 2 teal gradient `rgba(124, 196, 184, 0.06)` literals in `auth.jsx` with `color-mix(in srgb, var(--md-secondary) 6%, transparent)`.
3. Acceptance grep `grep -rnE "fontWeight:\\s*[0-9]+" src/dual_research/ui/static/*.jsx` returns **0** matches (no bare numeric `fontWeight`).
4. Full pytest suite (1194+) passes.
5. Live computed-style verification post-deploy: any element previously hardcoded at `fontWeight: 600` still computes to `600`.

## 3. Non-goals

- **No font-size tokenization sweep.** The CSS-side font-size fragmentation (audit § 5) is a separate, larger decision — most of those literals are deliberate micro-scale tweaks (9px, 10.5px) that don't fit the M3 type roles cleanly. Defer.
- **No legacy `.chip`/`.btn` vs `.md-chip`/`.md-btn` migration.** The legacy primitives are internally M3-tokenized; the two coexist by design. Different decision, different spec.
- **No IBM Plex sweep in auth.jsx SVG.** Auth-page SVG text elements use `fontFamily="IBM Plex Sans, system-ui, sans-serif"`; `system-ui` is the fallback so IBM Plex is opportunistic, not load-bearing. Move to a separate decision if desired.
- **No `rgba(0,0,0,0.10)` shadow tokenization** in auth.jsx:182 — follows the codebase's existing shadow-recipe pattern.

## 4. Files touched

8 JSX files. Replace_all per file, one per distinct weight number:

| File | 600 | 500 | 700 | Total |
|---|---:|---:|---:|---:|
| `app.jsx` | 1 | 0 | 0 | 1 |
| `auth.jsx` | 2 | 1 | 0 | 3 (+ 2 rgba) |
| `design-language.jsx` | 0 | 3 | 0 | 3 |
| `errors.jsx` | 1 | 2 | 0 | 3 |
| `run-list.jsx` | 3 | 0 | 0 | 3 |
| `run-detail.jsx` | 11 | 4 | 2 | 17 |
| `settings.jsx` | 2 | 0 | 0 | 2 |
| `shared.jsx` | 1 | 0 | 0 | 1 |
| **Total** | **21** | **10** | **2** | **33 + 2 rgba** |

Plus the version-bump trio (`pyproject.toml`, `__init__.py`, `uv.lock`), `index.html` cache-bust, `CHANGELOG.md`.

## 5. Risks

- **Risk:** a fontWeight inside a non-style context (string, comment) accidentally caught by replace_all. **Mitigation:** the grep before the sweep shows every match is in an inline style context. Manual diff review pre-commit.
- **Risk:** the spelling I have wrong on one of the new `--md-w-X` tokens (e.g. `semi` vs `semibold`). **Mitigation:** `tokens.css:227-230` defines them — confirmed `regular/medium/semi/bold`.

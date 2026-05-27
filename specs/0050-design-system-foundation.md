---
spec: 0050
title: Design-system foundation — tokens, base, a11y, MDI icons, emoji removal
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.48.0
created: 2026-05-17
pr: "https://github.com/Lexiz/dual-research/pull/53"
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0050 — Design-system foundation

## Context

Claude Design delivered a unified design system (V1 + V2 + review
feedback folded into one canonical spec) at
[`/Users/alexlisitzky/Downloads/Dual-research dashboard/`](../../Downloads/Dual-research%20dashboard/CLAUDE-CODE-BRIEFING.md).
The implementation plan for the full migration is **11 specs across
4 ships** (see [handoffs/2026-05-17-design-system-kickoff.md](../handoffs/2026-05-17-design-system-kickoff.md)
for the planning conversation that produced the arc).

This is **Ship 1 — Foundation**. Token + base-sheet + icon-set
replacement. Invisible to no user (fonts and colors change
everywhere), invisible to most workflows (no surface restructure
yet). Everything in Ships 2–4 depends on the tokens, focus ring,
reduced-motion contract, and `<Mdi>` component this spec lands.

Single spec for what Claude Design proposed as two parallel specs
(tokens vs. icons). Our workflow is one-PR-at-a-time → deploy →
verify; parallel landing doesn't help. Tokens + base + a11y + MDI
swap + emoji-kill are all invisible-but-pervasive sweeps that
review better as one Foundation PR than two interleaved ones.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Replace [`theme.css`](../src/dual_research/ui/static/theme.css) with two-file split**: `tokens.css` (authoritative tokens — color, type, spacing, radii, elevation, motion) + `base.css` (body, type utilities, focus ring, reduced-motion contract, markdown rendering). | Mirrors the brief's source layout. Tokens stay separable from behavior — when Ships 2+ add component CSS, it imports tokens only. **Implements** TYPE-01..05, CLR-01..07, SP-01..04, LIT-01..04, A11Y-01..02. |
| D2  | **Source tokens.css + base.css verbatim from the brief** ([`Downloads/Dual-research dashboard/styles/`](../../Downloads/Dual-research%20dashboard/styles/)), copied into `src/dual_research/ui/static/`. | The brief's CSS *is* the contract. Copy verbatim; future spec-specific edits become diffs against a known baseline. Comment header in each file references this spec + the brief checksum. |
| D3  | **Drop JetBrains Mono entirely; load IBM Plex Sans + Inter via Google Fonts** with `display=swap` + preconnects in `index.html`. `font-feature-settings: "tnum"` on `.num` / `.mono` utility classes for tabular figures. | TYPE-01, TYPE-02. No build step → Google Fonts CDN is the only delivery. |
| D4  | **Theme toggle stays class-based** (`body.dark` / `body.light`) — existing pattern in the codebase. Tokens flip via `body.light { … }` block in `tokens.css`. | Backward-compatible with the current `ThemeToggle` call sites. ThemeToggle component itself (the segmented restore — CMP-02) lands in SPEC-0051. |
| D5  | **Status-background tokens added**: `--ok-bg`, `--info-bg`, `--warn-bg`, `--err-bg` + matching `--*-border` rgba forms. Existing inline `rgba(…)` in components is **not** swept in this spec. | CLR-06. The component sweep happens in SPEC-0051. Tokens land here so the targets exist; call-sites migrate later. |
| D6  | **Global `:focus-visible` ring** — 2 px solid `--info` at 2 px offset, in `base.css`. No component opts out. | A11Y-01. Highest-priority a11y bug per the brief. |
| D7  | **Reduced-motion contract** — `@media (prefers-reduced-motion: reduce)` in `base.css` forces all durations ≤1 ms, disables halos / caret blink / scroll-behavior. | A11Y-02. |
| D8  | **MDI icon swap** — new [`src/dual_research/ui/static/icons.jsx`](../src/dual_research/ui/static/icons.jsx) copied verbatim from the brief ([`scripts/icons.jsx`](../../Downloads/Dual-research%20dashboard/scripts/icons.jsx)). Exposes `<Mdi name size color />` on `window`. Loaded via new `<script type="text/babel" src="icons.jsx">` in `index.html`. | ICN-01. ~60 MDI paths inlined; no external SVG fetch. |
| D9  | **Replace `Icon` in `shared.jsx`** to be a thin wrapper that forwards to `Mdi` (preserves existing `<Icon name="…">` call sites unchanged where the name maps to an MDI equivalent; logs a console warning + renders nothing for unknown names). | Lets existing surfaces keep working through the sweep without forcing every call site to rename in the same PR. Future specs migrate to `<Mdi>` directly as they touch each surface. |
| D10 | **Emoji elimination across `static/*.jsx`** — sweep removes every emoji currently present and replaces with `<Mdi>` per the brief's mapping table (§4). Inventory below. | ICN-02. The wrapper from D9 plus the per-emoji mapping makes each replacement a 1-line swap. |
| D11 | **`tweaks-panel.jsx` not touched** — emoji or otherwise. Per brief §5 it's intentionally off-brand. | Hard constraint from the brief. |
| D12 | **`theme.css` is deleted, not deprecated.** All `<link rel="stylesheet" href="theme.css">` updated to `<link rel="stylesheet" href="tokens.css">` + `<link rel="stylesheet" href="base.css">`. | Clean break. Nothing inside the static folder consumes `theme.css` outside the link tag. |

### Emoji inventory (current state on `main`)

| File | Emoji present | MDI replacement (per brief §4 + mapping) |
| --- | --- | --- |
| `run-detail.jsx` | `⏳ ⚠ ✓ 📄 📎 🔎 🔗` | `clock-outline`, `alert`, `check`, `file-document-outline`, `paperclip`, `magnify`, `link-variant` |
| `run-list.jsx` | `⏎` | `keyboard-return` |
| `how-it-works.jsx` | `⎯ ★ ⚠ ✓ 🔎 🔗` | `minus`, `star`, `alert`, `check`, `magnify`, `link-variant` |
| `live-data.jsx` | `✓` | `check` |
| `theme.css` | `🔗` | Likely a comment marker — strip; if it's content-`url()` data, migrate to `<Mdi>` at the call site. |
| `tweaks-panel.jsx` | (not swept — off-brand) | — |

Final per-emoji MDI name choices are confirmed during implementation against `scripts/icons.jsx` — if a brief mapping doesn't have an exact match in the dictionary, the closest semantic neighbor is used and the choice is noted in the PR description.

## Files touched

- [`src/dual_research/ui/static/theme.css`](../src/dual_research/ui/static/theme.css) — **deleted**.
- [`src/dual_research/ui/static/tokens.css`](../src/dual_research/ui/static/tokens.css) — **new**, copied from brief.
- [`src/dual_research/ui/static/base.css`](../src/dual_research/ui/static/base.css) — **new**, copied from brief.
- [`src/dual_research/ui/static/icons.jsx`](../src/dual_research/ui/static/icons.jsx) — **new**, copied from brief; exposes `Mdi` on `window`.
- [`src/dual_research/ui/static/index.html`](../src/dual_research/ui/static/index.html) — Google Fonts preconnect + IBM Plex Sans + Inter `@import`; replace `<link href="theme.css">` with tokens + base; add `<script type="text/babel" src="icons.jsx">` ahead of `shared.jsx`.
- [`src/dual_research/ui/static/shared.jsx`](../src/dual_research/ui/static/shared.jsx) — `Icon` rewritten to forward to `Mdi`; keep export surface unchanged.
- [`src/dual_research/ui/static/run-detail.jsx`](../src/dual_research/ui/static/run-detail.jsx) — emoji sweep per inventory.
- [`src/dual_research/ui/static/run-list.jsx`](../src/dual_research/ui/static/run-list.jsx) — emoji sweep.
- [`src/dual_research/ui/static/how-it-works.jsx`](../src/dual_research/ui/static/how-it-works.jsx) — emoji sweep + VERSION_NOTES entry.
- [`src/dual_research/ui/static/live-data.jsx`](../src/dual_research/ui/static/live-data.jsx) — emoji sweep.
- `pyproject.toml` + `src/dual_research/__init__.py` + `CHANGELOG.md` — 0.47.0 → 0.48.0.

## Out of scope

- **All Ship 2 work.** No primitive refactors (Button, Chip, StatusBadge, RunIDChip, Tab, Card, AgentStrip, QuestionThread, QuestionRef) — those land in SPEC-0051 through SPEC-0056. Existing primitives (`PaneButton`, `FilterChip`, `ReconcileChip`, etc.) keep working unchanged; they just inherit new tokens.
- **No restyle of `ReconcileChip` / `RepairChip` / `GhostedAnnotation` / `CardHeadline` / `ProviderBilledLine`.** They get the new tokens via cascade; the migration onto `StatusBadge`/`Chip`/etc. is SPEC-0051's job.
- **No surface restructure.** Header layout, critique pane filters, run-list sort, modal layout — all unchanged. Only tokens, fonts, focus ring, and icon substance change.
- **No light-mode `ThemeToggle` restoration to segmented.** Token-side support is in (`body.light` flips everything correctly), but the segmented control swap is CMP-02 → SPEC-0051.
- **`tweaks-panel.jsx`** — not touched per brief §5.
- **`auth.jsx` / `settings.jsx` / `router.jsx` / `errors.jsx` / `app.jsx`** — these surfaces don't contain emoji per the inventory; no structural changes here.
- **`design-language.jsx`** — typography section's `FontCard` props updated to reflect IBM Plex Sans + IBM Plex Serif (was Geist + JetBrains Mono); full retire of this surface is deferred to SPEC-0051 per brief §2.

### Deferred emoji (carved out of D10's "every emoji" promise)

Three emoji remain on `main` after this spec lands. Each has a specific reason to defer to a later spec rather than force-fit in Foundation:

| Where | Char | Why deferred |
| --- | --- | --- |
| `live-data.jsx:23` `PHASES[5].short` | `✓` | `short` is a data-layer string consumed as text across many call sites. Swapping to `<Mdi>` requires a typed PhaseChip primitive — lands with SPEC-0051's primitive vocabulary or SPEC-0052's Tab/PhaseChip work. |
| `run-list.jsx:121` keyboard hint | `⏎` | The brief's MDI subset (`scripts/icons.jsx`) doesn't include `keyboard-return`; the brief's mapping table only covers ⚠ / 🔎 / ↩ / ↗. Sweep happens when SPEC-0058 (keyboard contract + shortcuts overlay) adds the keyboard-return path to icons.jsx. |
| `how-it-works.jsx` narrative prose | `⚠` / `✓` in version-notes markdown | These describe historical UI state (`"the chip shows ✓ verified"`). Markdown body can't render JSX inline. Brief §2 marks how-it-works.jsx for V2 §3.12 rework — emoji-strip happens with that rewrite. |

These are flagged in the PR description with the SPEC-NNNN that will close each.

### Additional cleanups shipped (beyond D1–D12)

- **Hardcoded `JetBrains Mono, monospace` font references in SVG `<text>` attributes** (how-it-works.jsx ×13 sites) — swapped to `IBM Plex Sans, ui-monospace, monospace`. Required for SVG attribute-level font references that can't resolve `var(--mono)`. TYPE-01 compliance.
- **Hardcoded `Geist, system-ui, sans-serif` SVG font references** (auth.jsx ×2, how-it-works.jsx ×1, design-language.jsx ×1) — swapped to `IBM Plex Sans, system-ui, sans-serif`. TYPE-02 compliance.
- **`how-it-works.jsx` codeS object** — `fontFamily: 'JetBrains Mono, monospace'` → `'IBM Plex Sans, ui-monospace, monospace'`.
- **Old `theme.css` token names** — if any component file references a `--foo` that doesn't exist in the new `tokens.css`, it gets fixed in SPEC-0051. This spec verifies no broken-token references via a grep; missing tokens are added to `tokens.css` as an aliased token (with `/* TODO: SPEC-0051 — remove after primitive migration */`) rather than left to render as the CSS default.

## Test plan

- [ ] `uv run pytest tests/ -q` — 725 baseline green (no Python changes; pure asset shuffle).
- [ ] Manual preview-verify on `localhost:6173`:
  - [ ] Landing page renders with IBM Plex Sans + Inter (no JetBrains Mono anywhere).
  - [ ] Run list, run detail, how-it-works, design-language, settings, errors — all surfaces render in both themes.
  - [ ] Theme toggle still flips colors (existing `body.dark`/`body.light` plumbing).
  - [ ] Focus ring visible on every focusable (tab through the run list + run detail).
  - [ ] `prefers-reduced-motion: reduce` honored (toggle macOS Reduce Motion → halos + caret blink stop).
  - [ ] Verification chip in run-detail header still shows all 5 states (`verified` / `drift` / `partial` / `unverified` / `awaiting_provider_data`) — partner-vetting run (`runs/20260516-035048-partner-vetting-arch-critique/`) should still show the `drift` state with the +$0.71 finding.
- [ ] Emoji grep on `static/*.jsx` returns zero hits (except `tweaks-panel.jsx`).
- [ ] No broken-token references: grep `var(--` across `static/*.jsx` + `static/*.css`; every token referenced exists in `tokens.css`.
- [ ] Hosted smoke after deploy: `curl https://dual-research-alex.fly.dev/api/health` reports `0.48.0`.

## Risks

- **Token-name drift.** Existing components reference tokens by name (`--bg-1`, `--fg-0`, etc.). If the brief's `tokens.css` renames or drops any token the current code relies on, components silently fall back to inherited / default CSS. **Mitigation:** D12-attached grep step in the test plan; aliased tokens land here if needed with a TODO referencing SPEC-0051.
- **Google Fonts as a dependency.** First-paint now waits on a Google Fonts request. `display=swap` ensures text shows in fallback first; preconnect minimizes the swap window. If Google Fonts is down, fallbacks (system-ui sans-serif + serif Georgia stack) render. **Acceptable** — the brief sources from there and we mirror.
- **Icon-name mismatch.** `Icon` call sites pass names like `"check"`, `"warn"`, `"refresh"` — the MDI dictionary may use different canonical names (`"check"`, `"alert"`, `"refresh"`). **Mitigation:** D9 maps known legacy names → MDI equivalents inside the `Icon` wrapper; unknown names log a console warning + render an empty 14 px box (visible regression cue, not a crash).
- **Light-mode regressions.** Light mode is half-tested per the brief. Foundation lands first because of this — but expect to find at least one component that renders illegibly in light mode and needs a follow-up patch. **Mitigation:** preview-verify every surface in both themes before merge; file follow-ups as bugs against SPEC-0051 (where call sites get touched anyway).
- **`how-it-works.jsx` VERSION_NOTES** — Foundation is user-visible (new font, new colors, focus ring). Entry required.

## Open questions

- The brief's `tokens.css` includes `--bg-4` (high-contrast surface for dropdown rows) which current components don't reference. Land it anyway (per D2 verbatim copy) or strip unused tokens to keep the sheet lean? **Default this spec:** land verbatim. Unused tokens cost nothing and Ships 2+ will consume them.
- `index.html` currently loads scripts in a specific order (`shared.jsx` before per-surface JSX). New `icons.jsx` slots **before** `shared.jsx` so the wrapper in D9 can reference `window.Mdi`. **Default:** confirmed via implementation check.

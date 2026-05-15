---
spec: 0012
title: UI polish and navigation
label: new-feature
version-bump: MINOR
status: merged
target-version: 0.13.0
created: 2026-05-15
pr: ""
---

# Spec 0012 — UI polish and navigation

## Context

After live-verifying spec 0011 the user surfaced eight specific issues with the UI. The bundle works end-to-end but several surfaces feel rough: the mono font is unpleasant, the run-id column wraps awkwardly, run topics overflow without graceful truncation, the brand glyphs are placeholders, the run-detail top bar buries the topic, the navigation lacks a back-to-list affordance, the design-language tab is over-promoted, and the top-right controls (dark toggle, connection indicator) feel under-formed.

This spec tightens all of the above without changing the backend or the aggregator. It's UI-only (HTML/CSS/JSX under `src/dual_research/ui/static/`).

## Proposed change

### 1. Mono font swap — `Geist Mono` → `JetBrains Mono`

The current pairing is Geist (sans) + Geist Mono. Geist Mono reads awkwardly at the 10–12px sizes the UI uses for IDs, costs, and status pills. **JetBrains Mono** is free on Google Fonts, broadly used in tooling UIs, and has higher x-height + clearer numerals at small sizes. Keep Geist as the sans face — the user's note specifies the mono should be different from Geist, not the sans.

Concretely:

- `index.html` — replace the `Geist+Mono` family in the Google Fonts URL with `JetBrains+Mono` at weights 400 and 500.
- `theme.css` — change `--mono: 'Geist Mono', ...` to `--mono: 'JetBrains Mono', ui-monospace, 'JetBrains Mono', 'SF Mono', Menlo, monospace`. The downstream `.mono` class and `font-family: var(--mono)` usages pick this up automatically.

No JSX changes needed.

### 2. Run-id column treatment in the "All runs" list

Today: 80px-wide column shows the full session-dir slug (`20260515-124552-cache-multi-round`) which wraps over 3–4 lines and dominates the row visually.

New treatment: a stacked, two-line cell:

```
┌─────────┐
│  7f3a   │   ← 4-char displayId in mono, 14px, fg-0 (primary)
│ 12:45 · │   ← time + leading slug fragment, 10.5px, fg-3 (meta)
│ cache-…│
└─────────┘
```

- Primary line: `run.displayId` (the 4-char hash the aggregator already computes).
- Secondary line: `HH:MM` extracted from the timestamp prefix + the slug suffix (everything after `YYYYMMDD-HHMMSS-`) truncated to ~16 chars with ellipsis.
- Column width drops from 80px to **64px** (the 4-char id needs much less room than the full slug).
- Full slug appears in the row's `title` attribute (browser tooltip) for power users who want to see it.

Implementation: edit `run-list.jsx::RunRow` — replace the single `<span>{run.id}</span>` with the two-line block. Adjust the grid template columns accordingly.

### 3. Topic column truncation

Today: long topics like "Compare PostgreSQL with SQLite for storing 1-10M rows of structured user data in a single-tenant backend service. Output: a one-page comparison memo..." cut off ugly mid-word.

Fix:

- Show **at most the first sentence** of the topic, ending at the first `?`, `.`, or `!` (whichever comes first). The full topic stays available in `title="..."`.
- If the first sentence is itself >120 chars, fall back to `text-overflow: ellipsis` with a 120-char cap.

Lives in a new helper `formatTopic(topic)` in `live-data.jsx` so the same rule applies in the list and detail views.

### 4. Real brand icons — Claude + OpenAI

The user has authorized using the official Anthropic and OpenAI brand marks for this internal hobby project. Source the SVGs from **`simple-icons.org`** (CC0-licensed community library; widely accepted as canonical brand marks):

- `anthropic.svg` → the Claude glyph (the "asterisk" mark).
- `openai.svg` → the OpenAI glyph (the hexagonal swirl).

Replace the two abstract glyphs in `shared.jsx::AgentIcon` with the official SVG paths. Keep:

- The component API (`<AgentIcon agent="claude|gpt" size={N} variant="solid|ghost" />`).
- The agent-tinted backgrounds (sable for Claude, sage for GPT).
- The 12 / 14 / 15 / 16 px scaling.

Drop:

- The original `polygon`/`circle` paths in the `solid` variant — replaced byte-for-byte with the simple-icons paths.

Add a new section to the design-language page ("01.5 — Brand marks") that shows both icons at 12/14/16/24/32 px, the solid + ghost variants, and the agent color tokens that drive them. Wires the icons into the documented design surface so future contributors know they're load-bearing.

### 5. Run-detail top bar redesign

Today the top bar is a single 56-px row crammed with: brand chip, full session-dir id, topic, cost, status badge. Topic clamps to one line and gets ellipsed early.

New shape: **two stacked rows** inside the header, separated only by line-height (no extra border).

```
Row 1 (44 px):  [← All runs]  [dual-research]  [ 7f3a ]   ─────   $0.79  [● completed]
Row 2 (32 px):  Topic in 14px sans, wraps to two lines if needed; no ellipsis.
                Below the topic in 10.5px mono fg-3:
                started 14:45 · drafter gpt · 14m 06s elapsed
```

- The `← All runs` chip on the left replaces the implicit tab nav for going back. Sets the URL hash to `#/`.
- `[ 7f3a ]` is a clickable display-id chip; clicking copies the full session-dir name to the clipboard (small "copied" toast).
- The topic row uses `-webkit-line-clamp: 2` so a long topic wraps cleanly to two lines but never explodes the header height.
- The meta line ("started · drafter · elapsed") moves DOWN here from the phase strip below.

Implementation: rewrite `run-detail.jsx::TopBar` to the two-row layout. The existing `PhaseStrip` below it stays, minus the elapsed/converged line which is now in the meta row.

### 6. Default landing → All runs; explicit back nav

Today: clicking the `dual-research` tab strip's first tab (`Run detail`) when no run is selected falls back to list (already), but the visual default tab is Run detail.

Changes:

- The top tab strip becomes a **single tab**: `All runs`. No more `Run detail` tab. The detail view is reached only by clicking a row.
- Default landing for `#/` is the list (already true; just removing the misleading tab affordance).
- The `← All runs` chip in the run-detail top bar (per item 5) is now the canonical back-nav.
- Browser back button (history) works because `navigate()` uses `window.location.hash` (already true).

Implementation: edit `app.jsx::ViewSwitcher` — remove the detail tab from the tabs array; also remove the language tab from this strip (per item 7).

### 7. Demote design language

Move "Design language" from a top-level tab to a small icon button on the right side of the top chrome, sitting next to the dark/light toggle. Clicking it sets the hash to `#/language`. Clicking the All-runs tab from the language view goes back to list.

Concretely:

- Remove the `language` entry from `app.jsx::ViewSwitcher.tabs`.
- Add a new `<DesignLanguageButton />` in the top-right cluster (per item 8): a 32 × 32 px ghost-style icon button rendering `Icon.Palette` with a tooltip "Design language".

### 8. Top-right cluster — three sibling controls

Today the dark toggle (small, awkward) and the connection indicator (semi-permanent label) are inconsistently sized. Reshape them into three sibling controls of equal visual weight:

```
┌──────────────────┬──────────────────┬──────────────────┐
│  ● connected     │   [☀ / ☾]        │      [◐]         │
│    localhost     │   light · dark   │    design        │
└──────────────────┴──────────────────┴──────────────────┘
```

- **Connection indicator** — same data source (SSE state via `window.__lastSseConnected`), but rendered as a 32-px tall pill with a `Dot` + two-line stack: `connected` / `localhost · 6173` or `idle` / `—`.
- **Theme toggle** — a 32 × 60 px segmented control with sun and moon glyphs, the active half highlighted. Replaces the current text-with-icon button.
- **Design language button** — 32 × 32 px ghost button with the palette icon, opens `#/language`.

All three live in a horizontal row with a hairline divider on the left of each (except the first). Total height matches the tab strip (36 px now, becoming 44 px to fit the larger controls).

Implementation: rewrite the right-side of `app.jsx::ViewSwitcher` (everything after `<div style={{ flex: 1 }} />`). The existing `ConnectedIndicator` and `ThemeToggle` components are replaced; `DesignLanguageButton` is new.

### Files touched

- `src/dual_research/ui/static/index.html` — font URL.
- `src/dual_research/ui/static/theme.css` — mono var; possibly a few small spacing tokens for the new chrome height.
- `src/dual_research/ui/static/shared.jsx` — `AgentIcon` SVG replacement; possibly an `IconButton` primitive for the cluster.
- `src/dual_research/ui/static/app.jsx` — ViewSwitcher rewrite (tab strip + right cluster), routing untouched.
- `src/dual_research/ui/static/run-list.jsx` — RunRow id-column treatment, topic formatting.
- `src/dual_research/ui/static/run-detail.jsx` — TopBar rewrite, PhaseStrip cleanup.
- `src/dual_research/ui/static/live-data.jsx` — new `formatTopic` helper.
- `src/dual_research/ui/static/design-language.jsx` — new "Brand marks" subsection.

No Python changes. No backend changes. No schema changes.

### CHANGELOG + version bump

`0.12.0 → 0.13.0` (MINOR — user-visible feature additions: back nav, brand icons, redesigned chrome).

## Out of scope

- **Adding a build step (Vite / esbuild).** Still CDN React + Babel.
- **Replacing the React + Babel CDN stack.** Out of scope here; future spec if/when.
- **Truncation of disagreement labels** in the right pane. The current labels are usually short already; revisit if real data exposes a length problem.
- **Filter chips on the per-run errors view** — still deferred from spec 0011.
- **Accessibility audit** — keyboard nav between cards, ARIA roles, focus rings. Not regressing anything but not advancing either.
- **Copy-to-clipboard "copied" toast component** beyond the run-id chip — single-use here is fine.
- **Brand-icon licensing for redistribution.** simple-icons.org is CC0; if the bundle is ever distributed publicly we'd re-audit. Internal hobby project for now.

## Test plan

- [ ] All 200 existing Python tests still pass (`uv run pytest tests/ -q`)
- [ ] `dual-research serve` boots; `http://127.0.0.1:6173/` lands on the All-runs view by default (no Run-detail tab visible)
- [ ] JetBrains Mono renders in the run-id, cost, and SSE-endpoint cells (verified via `preview_inspect` on a `.mono` element)
- [ ] Run-id column shows the 4-char display id as the primary line, with the time-and-slug suffix as a secondary line; full slug visible in the row tooltip
- [ ] A row with a very long topic (e.g. the prod-cached-e2e row) truncates to the first sentence + ellipsis, no mid-word wrap
- [ ] Clicking a row navigates to the detail view; the detail-view top bar shows `← All runs`, a `7f3a` chip, brand+status+cost in row 1, topic + meta in row 2
- [ ] Clicking `← All runs` returns to the list with the row scrolled into view
- [ ] Clicking the display-id chip copies the full session-dir name to clipboard
- [ ] Top-right cluster shows three equal-height controls: connection state, theme toggle, design-language button
- [ ] Theme toggle is a segmented sun/moon control; clicking switches `body.light`
- [ ] Design-language button opens `#/language`; the page renders the new "Brand marks" subsection with both icons
- [ ] `AgentIcon` in run rows, run-detail headers, error rows, and the disagreement explorer all use the new brand SVGs
- [ ] Screenshots of: list view, detail view, design-language view (with brand marks) attached to the PR

## Risks

- **Trademark.** Anthropic and OpenAI brand marks remain trademarked even when sourced from simple-icons. We're using them on a single-user local app; the user explicitly authorized this for this project. If the bundle ever ships publicly, revisit.
- **CDN font-load latency.** Switching to JetBrains Mono is still Google Fonts — same loader cadence. No new risk.
- **TopBar rewrite breaks layout in narrow viewports.** The two-row design is more vertical; on a 1024-wide window it works fine. Below 800 px the topic-row line clamp keeps it bounded. Below 600 px no commitment — the prototype was never designed for mobile.
- **Behavior change: removing the Run-detail tab.** Anyone with `#/runs/<id>` bookmarked still works. The change is purely cosmetic at the chrome level.

## Open questions

None — all eight points are concrete and we'll iterate post-implementation if the visual choices need tweaking.

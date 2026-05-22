# dual-research — Design System Spec

**Status:** canonical text reference for the dual-research design system.
**Visual reference:** [`assets/Design System v2.html`](assets/Design%20System%20v2.html) — open in a browser to see every primitive and composed component rendered.
**Token + primitive CSS:** [`assets/styles/tokens-and-primitives.css`](assets/styles/tokens-and-primitives.css) and [`assets/styles/composed-components.css`](assets/styles/composed-components.css).
**Live implementation:** [`src/dual_research/ui/static/`](../src/dual_research/ui/static/) — `tokens.css`, `base.css`, `components.css`, `theme.css`, `design-language.jsx`, `shared.jsx`. **Authoritative for what users actually see.**
**Live in-app reference:** [`/#/language`](../src/dual_research/ui/static/design-language.jsx).

> This spec describes the Material 3 design system that the dual-research dashboard runs on. There is no "v1" / "v2" framing in this document — the previous design system was archived under [`_archive/v1/`](_archive/v1/) on 2026-05-20 (spec 0127). When a reader encounters references to v1 tokens (`--bg-1`, `--fg-2`, IBM Plex) in older PRs, CHANGELOG entries, or specs 0001–0091, those refer to the archived system.

---

## 0 — Mission

> A calm, dense observability surface for a two-agent convergence loop.
> Read-only, terminal-adjacent, single user. Information density is a feature. Decoration that fights the signal is removed.

The whole design follows three rules: **never compete with the agent output, never compete with the terminal next to it, never hide the one number that matters.**

The Material 3 vocabulary is applied selectively. M3 gives us a coherent token system (color roles, surfaces, elevation, state layers, motion, type) and a primitive library that scales across themes and densities without per-component overrides. It does **not** give us our identity — the pastel-palette (sable + sage), the calm motion profile, the read-only discipline, and the information-density bias are all dual-research-specific decisions that survive the M3 mapping.

---

## 1 — Principles

1. **Read-only is a discipline.** No buttons that mutate state. Every affordance is a view filter, a tab, or a focus shift. If the user wants to act, they go to the terminal.
2. **One color per agent, everywhere.** Sable (`--p-sable`) for Claude, sage (`--p-sage`) for GPT. Status colors are the only other hues. A third hue in a wireframe gets cut.
3. **Type pairs by role.** `--md-font-plain` (Roboto Flex) for chrome, body, labels, IDs, numbers (with tabular-nums via `font-feature-settings`). `--md-font-brand` (Roboto Serif) for hero text, page-level headings, blockquotes, QuestionThread quotes — anything that should read as "the agent's voice." `--md-font-data` is an alias for the plain font with tabular-nums baked in. The project does **not** ship a separate monospace font; tabular figures come from feature settings, not a separate face.
4. **Density is a feature.** Comfortable density (`--md-density: 0`) by default. Compact (`--md-density: 1`, applied via `body.compact`) tightens paddings, row heights, rail width, and the display/headline type scale for laptop-class viewports. A run-list row fits eight columns at 1200 px without ellipses below the topic.
5. **Calm transitions or none.** No bounces, no scale, no springs. Motion uses M3's `--md-easing-standard` / `--md-easing-emphasized` family; durations sit in the `short-1` (50 ms) to `medium-2` (300 ms) range. The "loud" states (cap approaching, deadlock, error) use a slow 2.2 s soft-pulse halo. Never a hard flash.
6. **Show why a run is slow.** The disagreements panel always tells the operator which contested point is blocking convergence. No buried logs.
7. **Token-only colors.** No hex codes in components. Every color reads from a `--md-*` token. If a needed color doesn't have a token, add it to `tokens.css` first.
8. **Full-word vocabulary.** Labels use complete words, never abbreviated codes. "conceded by Claude", not "→ c". Codified in [§ 9 Badge governance](#9--badge-governance--spec-0119) and SPEC-0067.
9. **Brand fidelity.** Official Anthropic sunburst and OpenAI hexagonal rosette everywhere an agent is identified. No generic substitutes.
10. **Accessibility.** `:focus-visible` ring via `--md-focus-ring` on every interactive primitive; `prefers-reduced-motion` honored on every animation; semantic ARIA where the markup needs it. Codified in SPEC-0087.
11. **One card primitive per surface.** All four critique-item kinds (Question, Disagreement, Issue, Comment) render with the same card layout; only the category chip varies. Spec 0144 — the rule that closes B08 (Phase 4 cards missing Issue/Comment patches) and B14 (per-card sources) on the same primitive: a kind-specific variant would force the layout to be done twice.

---

## 2 — Foundations

All foundation values are CSS custom properties defined in [`src/dual_research/ui/static/tokens.css`](../src/dual_research/ui/static/tokens.css) (live) and mirrored in [`assets/styles/tokens-and-primitives.css`](assets/styles/tokens-and-primitives.css) (canonical reference). Components MUST read from `--md-*` tokens; no hex codes anywhere in component CSS.

### 2.1 — Palette

The pastel palette is the dual-research identity. Sable and sage sit on opposite sides of the warm/cool axis at near-identical L\*, so neither agent feels louder than the other.

#### Base palette (preserved across themes)

| Token | Hex | Role |
|---|---|---|
| `--p-sable` | `#d4a574` | **Claude.** Track A. Primary brand surface. |
| `--p-sable-dim` | `#8a6d4e` | Dimmed sable for muted states. |
| `--p-sage` | `#7cc4b8` | **GPT.** Track B. Secondary brand surface. |
| `--p-sage-dim` | `#4f8079` | Dimmed sage. |
| `--p-info` | `#6b9cf0` | Running · current phase · live cursor · focus ring base. |
| `--p-ok` | `#6fb380` | Resolved · converged · completed · approved. |
| `--p-warn` | `#d4a056` | Approaching cap · deadlocked · drift. |
| `--p-err` | `#d96a6a` | Errored · halted. |
| `--p-idle` | `#5e636d` | Idle · paused · awaiting. |

#### M3 color roles

The palette feeds the M3 role tokens. Components read the roles, not the base palette.

| Role | Maps to | On-role pair | Container pair |
|---|---|---|---|
| `--md-primary` | `var(--p-sable)` | `--md-on-primary` | `--md-primary-container` / `--md-on-primary-container` |
| `--md-secondary` | `var(--p-sage)` | `--md-on-secondary` | `--md-secondary-container` / `--md-on-secondary-container` |
| `--md-tertiary` | `var(--p-info)` | `--md-on-tertiary` | `--md-tertiary-container` / `--md-on-tertiary-container` |
| `--md-error` | `var(--p-err)` | `--md-on-error` | `--md-error-container` / `--md-on-error-container` |
| `--md-warning` | `var(--p-warn)` | — (use status pills) | — |
| `--md-success` | `var(--p-ok)` | — (use status pills) | — |

Containers are rgba tints of the base hue (~18% in dark mode, ~26% in light), giving the agent-tagged backgrounds room to read against the surface tier without competing.

### 2.2 — Surfaces (M3 tonal scale)

M3 expresses elevation through both **shadow** and **tonal surface tint**. The surface tier set is:

| Token | Dark mode | Light mode | Role |
|---|---|---|---|
| `--md-surface-dim` | `#08090b` | `#ece8de` | Page background, streaming body. |
| `--md-surface` | `#0d0f12` | `#faf9f6` | Default surface. |
| `--md-surface-bright` | `#21242a` | `#ffffff` | Bright surface (rare; used for callouts on pure-black backgrounds). |
| `--md-surface-container-lowest` | `#0a0c0f` | `#ffffff` | Lowest tier (recessed). |
| `--md-surface-container-low` | `#111317` | `#f5f3ec` | Default panel. |
| `--md-surface-container` | `#14171c` | `#f0ede4` | Elevated row / chip bg / modal header. |
| `--md-surface-container-high` | `#191c21` | `#e9e5d9` | Hover, active chip, secondary sticky surfaces. |
| `--md-surface-container-highest` | `#21252b` | `#e3decf` | Highest static tier. |

On top of the static tiers, M3 layers **tonal-overlay surfaces** that mix the surface tint into the surface at increasing opacity. Components read these for "this surface is elevated above context."

| Token | Recipe | Use |
|---|---|---|
| `--md-surface-1` | `surface + tint @ 5%` | Slight lift (resting card). |
| `--md-surface-2` | `surface + tint @ 8%` | Hover lift. |
| `--md-surface-3` | `surface + tint @ 11%` | Dialogs, modal frames. |
| `--md-surface-4` | `surface + tint @ 12%` | Dragged / picked-up. |
| `--md-surface-5` | `surface + tint @ 14%` | Topmost (sticky bars, app bars when scrolled). |

`--md-surface-tint` is `var(--md-primary)` by default. The `body.tint-secondary` class swaps it to `var(--md-secondary)` — used on GPT-led routes so sage tints the surface instead of sable.

### 2.3 — On-surface inks

| Token | Dark | Light | Use |
|---|---|---|---|
| `--md-on-surface` | `#ffffff` | `#04060a` | Primary text, numbers, headings. |
| `--md-on-surface-variant` | `#b4bac4` | `#3a3f47` | Body prose. |
| `--md-on-surface-muted` | `#9aa0ac` | `#4d5159` | Secondary, meta, labels. |
| `--md-on-surface-faint` | `#7d8290` | `#6f7480` | Muted, column headers. |
| `--md-on-surface-decor` | `#50545d` | `#a8aab0` | Decorative, dividers in copy. |

### 2.4 — Outlines

| Token | Dark | Light | Use |
|---|---|---|---|
| `--md-outline` | `#343941` | `#aaa599` | Strong outline (focus, active boundaries). |
| `--md-outline-variant` | `#262a31` | `#d2cdc0` | Medium (cards, panels needing more definition). |
| `--md-outline-hair` | `#1c1f24` | `#e7e3d9` | Hairline (default container border). |

### 2.5 — Typography

| Token | Family | Use |
|---|---|---|
| `--md-font-plain` | Roboto Flex (variable) | UI chrome, body, labels, buttons, navigation, status pills, IDs, costs, tokens. |
| `--md-font-brand` | Roboto Serif | Hero text, page-level headings, blockquotes, QuestionThread quotes. The agent's voice. |
| `--md-font-data` | Roboto Flex with `font-variant-numeric: tabular-nums` and `font-feature-settings: "tnum","ss01"` | Numbers, IDs, costs — anywhere column alignment matters. Alias to plain with feature settings; not a separate font face. |

Fallbacks: `--md-font-plain` → `"Roboto", system-ui, -apple-system, "Segoe UI", sans-serif` · `--md-font-brand` → `ui-serif, Charter, Georgia, serif`.

#### M3 type scale — 15 roles

The scale is `<category>-<size>` where category ∈ {display, headline, title, body, label} and size ∈ {l, m, s}. Each role has a size, line-height, and (for some) letter-spacing token, plus a `.t-<category>-<size>` utility class.

| Role | Size / Line height | Track | Utility class |
|---|---|---|---|
| `display-l` | 57 / 64 | -0.25 px | `.t-display-l` |
| `display-m` | 45 / 52 | 0 | `.t-display-m` |
| `display-s` | 36 / 44 | 0 | `.t-display-s` |
| `headline-l` | 32 / 40 | — | `.t-headline-l` |
| `headline-m` | 28 / 36 | — | `.t-headline-m` |
| `headline-s` | 24 / 32 | — | `.t-headline-s` |
| `title-l` | 22 / 28 | — | `.t-title-l` |
| `title-m` | 16 / 24 | 0.15 px | `.t-title-m` |
| `title-s` | 14 / 20 | 0.1 px | `.t-title-s` |
| `body-l` | 16 / 24 | — | `.t-body-l` |
| `body-m` | 14 / 20 | — | `.t-body-m` |
| `body-s` | 12 / 16 | — | `.t-body-s` |
| `label-l` | 14 / 20 | 0.1 px | `.t-label-l` |
| `label-m` | 12 / 16 | 0.5 px (uppercase) | `.t-label-m` |
| `label-s` | 11 / 16 | 0.5 px (uppercase) | `.t-label-s` |

Display + headline roles use the brand font (Roboto Serif). Everything else uses the plain font. `.t-data` is a helper class that sets the data font + tabular-nums.

Body default is `body-m` (14 / 20). Display + headline tighten under `body.compact` density.

#### Weights

| Token | Value |
|---|---|
| `--md-w-regular` | 400 |
| `--md-w-medium` | 500 |
| `--md-w-semi` | 600 |
| `--md-w-bold` | 700 |

### 2.6 — Shape scale

| Token | Value | Use |
|---|---|---|
| `--md-shape-xs` | 4 px | Status pills, mini indicators. |
| `--md-shape-sm` | 8 px | Chips, small cards. |
| `--md-shape-md` | 12 px | **Default card / panel radius.** |
| `--md-shape-lg` | 16 px | FAB, large showcase frames. |
| `--md-shape-xl` | 28 px | Dialogs, modal frames. |
| `--md-shape-full` | 9999 px | True pills — buttons, status, run IDs, segmented controls. |

### 2.7 — Spacing (M3 8 dp grid + 4 dp half-step)

All spacing reads from `--md-sp-<N>` tokens. No values outside this scale.

| Token | Value |
|---|---|
| `--md-sp-0` | 0 |
| `--md-sp-1` | 4 px |
| `--md-sp-2` | 8 px |
| `--md-sp-3` | 12 px |
| `--md-sp-4` | 16 px |
| `--md-sp-5` | 20 px |
| `--md-sp-6` | 24 px |
| `--md-sp-8` | 32 px |
| `--md-sp-10` | 40 px |
| `--md-sp-12` | 48 px |
| `--md-sp-14` | 56 px |
| `--md-sp-16` | 64 px |
| `--md-sp-20` | 80 px |

### 2.8 — Density

Two density modes — comfortable (default) and compact. Compact is applied via `body.compact` and tightens M3 spacing tokens, row height, rail width, and the display/headline type scale.

| Token | Comfortable | Compact |
|---|---|---|
| `--md-density` | 0 | 1 |
| `--md-pad-card` | `--md-sp-6` (24) | `--md-sp-4` (16) |
| `--md-pad-card-y` | `--md-sp-5` (20) | `--md-sp-3` (12) |
| `--md-gap-row` | `--md-sp-8` (32) | `--md-sp-5` (20) |
| `--md-gap-col` | `--md-sp-6` (24) | `--md-sp-4` (16) |
| `--md-row-h` | 56 px | 44 px |
| `--md-rail-w` | 280 px | 240 px |

### 2.9 — Elevation (6 levels)

| Token | Recipe |
|---|---|
| `--md-elev-0` | `none` |
| `--md-elev-1` | Subtle (resting card). |
| `--md-elev-2` | Hover. |
| `--md-elev-3` | Dialogs, modals, FAB. |
| `--md-elev-4` | Drag / pick-up state. |
| `--md-elev-5` | Topmost (rarely needed). |

Light mode reduces opacity in every shadow recipe so elevation reads softer on cream backgrounds without losing the hierarchy. M3 also layers **tonal overlay** (`--md-surface-1..5`) on elevated surfaces — in dark mode the tint visibly lifts the surface; in light mode it adds a subtle warmth.

### 2.10 — State layers

Hover / focus / pressed / dragged are rendered as `currentColor` overlays at fixed opacity, not as background-color swaps. This keeps the underlying element identity stable.

| Token | Opacity |
|---|---|
| `--md-state-hover` | 0.08 |
| `--md-state-focus` | 0.10 |
| `--md-state-pressed` | 0.12 |
| `--md-state-dragged` | 0.16 |

Standard pattern (used by every interactive primitive):

```css
.thing { position: relative; }
.thing::before {
  content: ""; position: absolute; inset: 0;
  background: currentColor; opacity: 0;
  transition: opacity var(--md-dur-short-3) var(--md-easing-standard);
}
.thing:hover::before { opacity: var(--md-state-hover); }
.thing:active::before { opacity: var(--md-state-pressed); }
```

### 2.11 — Motion

M3's emphasized + standard easings, 8 named durations.

| Token | Value | Use |
|---|---|---|
| `--md-easing-emphasized` | `cubic-bezier(0.2, 0, 0, 1)` | Default "make the user notice" curve. |
| `--md-easing-emphasized-decel` | `cubic-bezier(0.05, 0.7, 0.1, 1)` | Entry. |
| `--md-easing-emphasized-accel` | `cubic-bezier(0.3, 0, 0.8, 0.15)` | Exit. |
| `--md-easing-standard` | `cubic-bezier(0.2, 0, 0, 1)` | Most state transitions. |
| `--md-easing-standard-decel` | `cubic-bezier(0, 0, 0, 1)` | Subtle entry. |
| `--md-easing-standard-accel` | `cubic-bezier(0.3, 0, 1, 1)` | Subtle exit. |
| `--md-dur-short-1` | 50 ms | Color flips, opacity toggles. |
| `--md-dur-short-2` | 100 ms | Hover. |
| `--md-dur-short-3` | 150 ms | Default state transition. |
| `--md-dur-short-4` | 200 ms | Default layout transition. |
| `--md-dur-medium-1` | 250 ms | Modal entry. |
| `--md-dur-medium-2` | 300 ms | Page transitions. |
| `--md-dur-medium-4` | 400 ms | Long layout shifts. |
| `--md-dur-long-2` | 500 ms | Loud-state pulses (rare). |

**Streaming output** uses a soft per-token append at 60–90 chars/sec; the caret is a 0.9-opacity block that pulses at 1.05 s to anchor the eye. **Loud states** (cap approaching, deadlock, error) use the slow soft-pulse halo. `prefers-reduced-motion` is honored everywhere.

### 2.12 — Icons

| Family | Use |
|---|---|
| Material Symbols Outlined | General UI iconography. ~60 glyphs across 6 grouped catalogues. Loaded via Google Fonts CDN in `index.html`. `.ms` sizing helper class. |
| Anthropic sunburst (custom) | Claude agent identity. Sizes 48 / 32 / 24 / 16. Variants solid + ghost. Lives in `shared.jsx` as `<BrandMark>` primitive. |
| OpenAI hexagonal rosette (custom) | GPT agent identity. Same sizes + variants. |

Brand marks are the only custom icons. Everything else is Material Symbols Outlined.

### 2.13 — Focus ring

| Token | Value |
|---|---|
| `--md-focus-ring` | `3px solid color-mix(in srgb, var(--md-tertiary) 80%, transparent)` |
| `--md-focus-offset` | 2 px |

Applied via `:focus-visible` on every interactive primitive. The tertiary (info) hue is the focus color across the system.

### 2.14 — Layout constants

| Token | Value | Role |
|---|---|---|
| `--md-content-max` | 1440 px | Max width of page-level content columns. |
| `--md-rail-w` | 280 px (comfortable) / 240 px (compact) | Side navigation rail width. |

---

## 3 — Primitives

Primitives are the M3 atoms — the closed set of building blocks that every composed component is built from. Each lives as a CSS class (`.md-*`) and, where it has component behavior, as a React function in [`src/dual_research/ui/static/shared.jsx`](../src/dual_research/ui/static/shared.jsx).

| Primitive | CSS class(es) | React component | Used for |
|---|---|---|---|
| **Button** | `.md-btn`, `.md-btn--{filled,tonal,outlined,text,elevated}`, `.md-btn--{sm,lg}` | — | All interactive buttons. Filled = primary action; tonal = secondary; outlined = tertiary; text = inline; elevated = on-surface emphasis. Pill radius (`--md-shape-full`), 40 dp default height, 24 dp horizontal padding, label-large type. State layers via `::before`. |
| **FAB** | `.md-fab`, `.md-fab--ext` | — | Floating action — 56 × 56 dp, `--md-shape-lg`, elevation-3. Extended FAB carries label after icon. Rare in this app (read-only) but spec'd for completeness. |
| **Icon button** | `.md-icon-btn` | — | 40 × 40 dp circular icon-only action. State layer overlay. |
| **Chip** | `.md-chip`, `.md-chip--{selected,filter-a,sm}` | `<Chip>` (see § 9 Badge governance) | Assist · filter · input · suggestion. 32 dp height (24 dp sm), `--md-shape-sm` corners, label-large type. **Every chip on every surface uses this primitive.** |
| **SourceRow** | `.source-row`, `.source-row.is-unverified` | `<SourceRow>` | Spec 0144 — per-evidence-record collapsible row inside a critique card. Collapsed: ▶ chevron + title + host badge + optional `⚠ unverified` chip. Expanded: URL link · fetched-at · search-query · content-excerpt (bounded scroll above 800 chars). One instance per record; multiple per card. The `⚠ unverified` chip slot uses `.md-chip--sm` + the warn tone and renders only when `record.unverified === true`. |
| **Status pill** | `.md-status`, `.md-status--{running,converged,drift,errored,idle,queued}` | `<StatusBadge>` | 22 dp height, pill, leading 6 dp dot in currentColor. Six states. Tinted via `color-mix` from the base palette. |
| **Switch** | `.md-switch` | — | 52 × 32 dp, M3 thumb-grows-on-on. Rare (read-only). |
| **Segmented buttons** | `.md-seg`, `.md-seg__opt` | `<TabGroup variant="solid">` (CSS class compat) | Pill container with inset divider lines. M3 secondary-container on selected. Used for phase tabs, kind filters, agent filters, status filters. |
| **Card** | `.md-card`, `.md-card--{elevated,filled,outlined,tonal-a,tonal-b}` | `<Card>` | Four base variants + two agent-tonal (primary-container / secondary-container). `--md-shape-md` (12 dp). Card header (`.md-card__hd`), title (`.md-card__title`), support (`.md-card__support`). |
| **Tab** | `.md-tabs`, `.md-tab` | `<Tab>`, `<TabGroup>` | Primary tabs with active-indicator bar. M3 secondary as solid segmented pill (used for theme + density + agent + status filters). |
| **Dialog / Modal** | `.md-dialog`, `.md-dialog__{icon,title,body,actions}` | `<ModalDialog>` (in `shared.jsx`) | `--md-shape-xl` (28 dp), elevation-3, max-width 560 dp basic / 1080 dp rich (spec 0096). Rich variant has scrim, focus trap, ESC close. |
| **Top app bar** | `.md-appbar`, `.md-appbar__{title,spacer}` | — | 64 dp, surface-container, sticky. |
| **Navigation rail** | `.md-rail`, `.md-rail__{brand,group-label}`, `.md-rail nav a` | — | 280 dp open, collapses to 80 dp icon-only under 1500 px. |
| **List item** | `.md-list`, `.md-list__{item,lead,body,overline,headline,support}` | — | M3 three-line list anatomy (lead · headline · support). |
| **Divider** | `.md-divider`, `.md-divider--inset` | — | Hairline, optional inset. |
| **AgentStrip** | `.as` | `<AgentStrip>` | Equal-width agent identifier with model, tokens, cost, status. Both pills share width via `flex: 1 1 0`. Compact 4 px vertical padding. Inside `.tl__head` / `.tl__tabs` (the `.in-header` variant), the strip carries an 8 % `color-mix` tonal background matching the provider (spec 0164 §2.5). |
| **Timeline card** | `.tl-thread` (always rendered as `.qthread.tl-thread`) | — (JSX inline in `run-detail.jsx`) | Filled M3 card for one turn row in the timeline pane (spec 0164 §2.4). Surface-container-high background, outline-variant border, 16 dp radius. Four states (rest / hover / expanded-rest / expanded-hover) — hover lifts to `--md-elev-1`, expanded to `--md-elev-2`. Provider stripe via native CSS `:has()` against the card-head identity chip: 2 px sable for Claude, sage for GPT, idle grey for System cards. `overflow: hidden` clips the expanded body's bottom corners during the lift transition. |
| **CollapsibleSection** | `.cs-*` | `<CollapsibleSection>` | Generic disclosure primitive. Rotating chevron + count chip. Persists open/closed to `localStorage`. Used inside critique pane sections, How-It-Works sections, timeline phase groups. |
| **QuoteCallout** | `.quote-callout` | `<QuoteCallout>` | Styled callout for quote fields on critique cards. Left border tinted by agent + serif italic + muted bg. |
| **LoadingState** | `.dr-loading-*` | `<LoadingState>` | Three sizes: `inline` (14 px spinner, row), `panel` (28 px, column), `page` (44 px, column). Spinner + label + optional hint. Default hint: "Just a moment, please." **The one loading visual everywhere.** |
| **BrandMark** | — | `<BrandMark>` | Anthropic sunburst / OpenAI rosette. Sizes 48 / 32 / 24 / 16. Variants solid + ghost. |

The full rendered catalog lives at `assets/Design System v2.html` and at the live `/#/language` page.

---

## 4 — Composed components

Composed components are surface-level patterns built from the primitives. They are conventions — surfaces consume them, they don't reinvent them.

### 4.1 — Critique pane

Two-bar header + status-grouped body. The canonical reference for this lives in spec 0098 (M3 rework) and was tightened by spec 0124 (filter header parity + responsive compaction).

**Bar 1** carries: title (`Critique`) · phase tabs (P2 Negotiate / P4 Review / Σ Summary) · run-wide totals (`introduced` · `open` · `resolved`) + drift chip on the right.

**Bar 2** carries: kind tabs (All / Issues / Comments / Questions / Disagreements) with **per-phase counts** baked into each tab as a tinted chip · agent segmented filter (All / Claude / GPT) · status segmented filter (All / Open / Resolved / Drift). **Hidden in Σ Summary state.**

**Body** is **status-grouped collapsible sections** with rotating chevron headers:
- `Open · new this round` — info-strong tint, info count chip
- `Open · carried over` — warn tint, warn count chip
- `Resolved` — ok tint, ok count chip (collapsed by default)
- `Drift` — err tint, err count chip (collapsed by default)

**Phase header sizing** — phase headers use `t-title-m`; card titles use `t-body-m`. Phase headers are taller than the cards inside them.

**Hover** — every card (not the section header) gains elevation-2 on hover.

### 4.2 — QuestionThread

The thread component lives inside the expanded state of a question / disagreement / issue / comment card. Anatomy (spec 0097):

1. **Card header (always visible).** First chip = agent who raised it (AgentStrip, sable or sage). Second chip = `qref` (e.g. `Q · 03` with the kind letter colour-coded — see § 9). Third chip = status (`open · new`, `open · carried`, `resolved · r3`, `drift`). Fourth chip = phase + round meta.
2. **Quote (only when expanded).** Render the quote *inside* the tonal-tinted message bubble of the agent who said it. Use serif italic (`--md-font-brand`), full card width, pill (`agent · round · verdict`) above on its own line.
3. **Subsequent turns.** Same bubble pattern, ordered chronologically: `raised` → `pushback` → `conceded` → `resolved`. Verdict vocabulary is fixed at six words: `raised`, `pushback`, `conceded`, `resolved`, `ghosted`, `drift`. Never abbreviate. See § 9 for the full canonical vocabulary.
4. **Resolved or drift footer.** A single dashed top-border line carrying a one-line summary (`resolved at round 3 · 2 turns to converge · hash match` / `drift · recorded with full history · does not block exit`).

**Sequence rule:** who → when → what → quote. In that order. Always.

**Anti-patterns** (codified by specs 0097 + 0098 to fix Notion issues 7 / 8 / 9 / 10):
- Duplicating the question/disagreement title both in the card header and inside the first bubble.
- Cryptic codes like `C1`, `D3` without a full-word badge.
- Status mismatch between the card header pill and the inner bubble pill.
- Showing the quote more than once on a single card.
- "Flagged by Claude · first seen in round 1 · last seen in round 2" lines that duplicate badge info.

### 4.3 — Consumption row

Three forms (spec 0100, polished by specs 0116, 0118, 0146):

**Collapsed:** header (provider icon + name + bracketed `(X.X% of 1M)` percentage, right-aligned to the bar end) → single `Total tokens` bar with `Xkt · $X.X` at the right. The percentage's closing `)` lands at the same x-coordinate as the right edge of the bar fill below it; the chevron lives at the card's right edge. Tokens and cost are not duplicated in the header — they're on the bar.

**Unfolded:** collapsed view + per-phase canonical input sub-rows (spec 0118 vocabulary) including the User-prompt row, whose per-attachment sub-rows (`Chat message` + one `Attachment · {title}` per attachment from spec 0145) auto-render as indented child rows when the card is in its unfolded state — no second click required. Under the input rows: single `Output` row. Below the rows: a `.ccx-totals` block with label-left / value-right lines: `input tokens · billed`, `input cost`, `web search · N queries` (when N > 0), `total input` (bold rule above, larger value). All card-internal cost displays use one-decimal precision (`fmtCost1` — `$0.2`, `$13.5`); the run-detail footer aggregate keeps 4-decimal precision (`$13.5110`) as the audit number.

**Capital-T section labels.** Bar-row section headers (`Total tokens`, `Output`) are title case. The `.ccx-totals` block uses lowercase labels (`input cost`, `total input`) — title case is reserved for bar-row section headers.

**Uniform across phases:** all cards share the same horizontal width across phases. Round label sits **above** the card as a small uppercase chip, not inside the header trio.

**Sticky bottom legend** (spec 0100 § 6.4) sits inside the consumption pane (not the viewport). Surface-container-high background, hairline top border, elevation-1.

### 4.4 — Timeline pane

Header chrome only — body is built from existing primitives. `.tl-phase` is a collapsible section per phase; `.tl-thread` is the timeline turn card (M3 chrome — see § 3 Primitives "Timeline card"). `.tl-turn--open` is the legacy expanded-card form, kept for inline expansion compatibility.

**Phase header anatomy** (spec 0164). Five-column grid: `marker · chevron · name · meta · chips`. The marker carries the full-word phase identity — `Phase 0` / `Phase 1` / `Phase 2` / `Phase 3` / `Phase 4` — rendered inside `.tl-phase__marker .lbl`. The earlier `.tl-phase__pcode` uppercase data-font phase code that sat between the chevron and the name was removed by spec 0164 §2.2; the marker is now the canonical identity.

**Phase pane gutter** (spec 0164). Both `.tl-phase__hd` and `.tl-phase__body` inset 16 px from the pane edges (`padding: 12px 16px` and `8px 16px 12px` respectively). Inter-card spacing is `gap: 6px` on the body.

**Phase indicators** (spec 0099) render outside the timeline column as a vertical rail. One marker per visible phase header, anchored to the header's vertical centre. Markers for phases with no data are hidden, not greyed.

**Turn card chrome** (spec 0164 §2.4). Filled M3 card on `--md-surface-container-high`, `1px solid --md-outline-variant`, 16 dp radius (`--md-shape-lg`). Card itself owns no padding — head / body / actions own theirs. **Provider stripe** (2 px left border, via native CSS `:has()`):
- `:has(.tl-card-head > .chip.tone-claude)` → `var(--p-sable)`
- `:has(.tl-card-head > .chip.tone-gpt)` → `var(--p-sage)`
- `:has(.tl-card-head > .chip.tone-neutral:not(.mono))` → `var(--p-idle)` (system cards — the `.tone-neutral` identity chip, distinguished from the mono activity chip that may also carry `.tone-neutral`)

States — four total, all driven by class on the card itself:
- **Rest** — chrome above, no shadow.
- **Hover** — background bumps to `--md-surface-container-highest`, border to `--md-outline`, `box-shadow: var(--md-elev-1)`.
- **Expanded** (`.is-open-expanded`) — background drops to `--md-surface-container-low`, `box-shadow: var(--md-elev-2)`. The `.tl-card-head` inside the expanded card carries `--md-surface-container-high` and a 1 px hairline bottom border so it reads as the still-visible row above the expanded body.
- **Expanded + hover** — combination of the two above.

Status colors (`is-open` / `is-resolved` / `is-drift`) inherited from `.qthread` are explicitly cleared on `.tl-thread` so the provider stripe shows through. Status info reads off the right-cluster status chip on timeline cards.

`overflow: hidden` is load-bearing — without it the expanded body's rounded corners clip incorrectly when the card lifts.

**REPAIR-round explainer** (spec 0099 § 7.4 / Notion issue 16): a REPAIR turn renders as a `.tl-thread` with the `REPAIR` tag inline; expanded body contains one explanatory sentence (e.g., *"GPT was silent this turn. Claude will reissue the same plan on the next round. No data lost."*).

**Double-divider on unfold** (Notion issue 11): when a turn card expands, render one dashed top border between the still-visible head and the body. No second solid divider.

**Header agent strips** (spec 0164 §2.5). Inside `.tl__head` / `.tl__tabs` (the `in-header` AgentStrip variant), the strip carries an 8 % `color-mix` tonal background matching the provider — `--p-sable` for `is-a`, `--p-sage` for `is-b`. The 2 px left-border and brand-mark icon stay.

**Responsive — narrow viewport ≤ 1799 px** (spec 0164 §2.6). Both `.as.in-header` instances inside `.rdvc__pane` (`.tl__head .as.in-header` + `.tl__tabs .as.in-header`) cap to 320 px and right-align to the same column. Without this, `.tl__tabs` (whose leading content is wider than `.tl__head`'s) overflows the pane edge by ~33 px at 1280 px viewport. The `.as-activity` text inside the capped strip falls back to `text-overflow: ellipsis` if it doesn't fit.

**Chip polish inside `.tl-card-head`** (spec 0165 §2.2–§2.3, §2.6). The M3 card surface from spec 0164 (`--md-surface-container-high`) swallows the chip primitive's tonal-container backgrounds, so timeline-card chips need scoped overrides. All rules below scope to `.tl-card-head` only — the global `.chip.tone-*` rules and the critique pane stay unchanged.

| Chip | Background | Text |
|---|---|---|
| `.chip.tone-claude` (Claude identity) | `color-mix(in srgb, var(--p-sable) 30%, transparent)` | inherits (default chip text colour) |
| `.chip.tone-gpt` (GPT identity) | `color-mix(in srgb, var(--p-sage) 30%, transparent)` | inherits |
| `.chip.tone-neutral:not(.mono)` (System identity) | `color-mix(in srgb, var(--p-idle) 20%, transparent)` — held at 20 % (vs. 30 %) because the idle palette is itself dimmer; 30 % reads too prominent | forced `var(--md-on-surface)` (neutral, not branded) |
| `.chip.tone-neutral.mono` (activity badge — `turn N` / `brief` / `plan` / `draft`) | `var(--md-surface-container-highest)` — one tier brighter than the card surface | inherits |

Light-mode chip-text backstop (spec 0165 §2.6). `body.light .tl-card-head .chip.tone-claude` and its `.chip-label` child carry an explicit `#3b2810` text colour; the `.tone-gpt` equivalents carry `#0a322d`. These match the canonical `--md-on-primary-container` / `--md-on-secondary-container` light values declared in `tokens-and-primitives.css` — they're declared as scoped backstops so timeline chips stay readable if a future change drifts the tokens again.

**Phase-header category bubble dim** (spec 0165 §2.4). Inside `.tl-phase__chips`, the `.cat-bubble` (Q / D / I / C knockout-white letter on a brand-tone fill) drops to 70 % alpha so the bubble doesn't dominate the chip's 18 %-tinted background. Letter remains knockout-white and legible on all four tones (info / warn / err / idle). Scoped to `.tl-phase__chips` so the critique-pane kind cluster (same `.cat-bubble` primitive, different visual budget) keeps its 100 % saturation.

**Cost chips inside expanded turn cards** (spec 0165 §2.5). The cost chip in `.tl-thread__actions` uses 2-decimal precision via the new `fmtCost2(value)` helper in `run-detail.jsx`. Sub-cent values render as `<$0.01` (so they don't round to `$0.00`). The run-detail footer aggregate continues to use `fmt.cost` (4-decimal) as the audit value — see §4.3.

### 4.5 — Agent input panel + PhaseRail + RoundScrubber

The agent input panel (spec 0074, extended by 0085, refreshed by 0101) is a 3-tier hierarchy:

```
▶ System prompt              (system)                       4,915 chars
▼ User prompt                                             245,378 chars
  │ From chat                                              3,142 chars
  │ External resources mentioned                          2 resources
▶ Child page: Notion ADR-014                              12,847 chars
▶ Child page: Internal RFC-2023-04                         4,512 chars
```

**PhaseRail** (`.phase-rail-*`, spec 0066) is the left-edge vertical timeline navigator. Dots per phase, current phase animated.

**RoundScrubber** (`.round-scrubber-*`) is the inline round navigator inside phase headers (R1 R2 R3 R4 …).

### 4.6 — Modal / dialog

Single primitive (`<ModalDialog>` in `shared.jsx`, spec 0096): scrim-backed centered dialog with two variants:
- **Basic** — `max-width: 560 px`, `--md-shape-xl` corners, elevation-3.
- **Rich** — `max-width: 1080 px`, otherwise identical chrome. Used for the turn-detail modal, the spec-view modal, the diagram-viewer modal.

Behaviors: ESC closes, scrim-click closes, focus trap, body overflow lock, theme-aware.

### 4.7 — Sources segment

Spec 0144. The per-evidence-record stack rendered immediately after the lifecycle footer on every critique card.

- **Label.** `Sources (N)` in `t-overline` style — 11 px uppercase, 0.06 em letter-spacing, `--md-on-surface-variant`.
- **Separator.** Dashed top border (`1px dashed var(--md-outline-hair)`) above the label.
- **Body.** Vertical stack of `<SourceRow>` instances, one per evidence record.
- **Empty-state behaviour.** When `N === 0`, **hide the entire segment** (no label, no border, no empty list). A SOURCES segment showing `(0)` on an item that never had source data would be misleading; the segment's presence is itself a signal.
- **Sources N header chip.** The card header carries a `Sources {N}` chip (when N > 0) that, on click, scrolls the SOURCES segment into view inside the card. Per-card-jump dispatch — consistent with the resolution of spec 0144 open-question #2.
- **Unverified chip placement.** The `⚠ unverified` chip lives **on the offending source row**, not on the card. A card with 3 sources where only 1 is flagged would mislead with a card-level chip. See spec 0144 open-question #3.

Canonical visual reference: [`audits/2026-05-19-badge-governance-iter3/mockup.html`](audits/2026-05-19-badge-governance-iter3/mockup.html).

### 4.8 — Critique card composition

Spec 0144. **All four critique-item kinds (Question, Disagreement, Issue, Comment) render with the same card primitive (`<ItemCard>` in `run-detail.jsx`).** This is the §1 invariant that closes B08 (Phase 4 cards missing Issue/Comment patches) and B14 (per-card sources) on the same primitive.

The stacking order, top to bottom:

1. **Header chip row.** `{id}` (mono) · kind · state · `raised by X` · `round N` · `Sources N` (only when N>0; clicking jumps the SOURCES segment).
2. **Body.** Item text. When `anchor_type !== 'none'`, a tinted blockquote follows.
3. **Evidence-needed helper.** Italic single line, rendered only when `evidence_required === true`: *Evidence needed — addresses must cite consulted sources.*
4. **Lifecycle timeline.** Vertical list of transitions; each row is `Round N — from → **to** (via) · by Actor` with the reason underneath in a muted block.
5. **Footer.** Single dashed-top line: `✓ {terminalState} at round N · M turns to converge`. Rendered when the item is in any terminal state (`resolved` / `acknowledged` / `withdrawn` / `capped`); never rendered when the item is still `open` or `addressed`.
6. **SOURCES (N).** The §4.7 segment.

Only the category chip in (1) varies between kinds. **No kind-specific card variant exists.** The legacy `<QuestionThread>` is retained as a fallback for pre-0114 archived runs (whose items have no `transitions` array) — see [§ 9.5 — Legacy critique renderer](#95--legacy-critique-renderer-pre-0114) if added later; until pre-0114 runs roll out of relevance, the fallback path stays alive.

---

## 5 — Page-level patterns

### 5.1 — Onboarding tour overlay

The 8-step tour (spec 0103, rewritten by spec 0125) is an **overlay over the live application**. It never re-creates the underlying UI; it mounts on top of the routed page and uses `data-tour-anchor` attributes on real components as spotlight anchors.

**Anatomy:** `<TourSpotlight>` is an SVG-based component with `<mask>` cutout around the anchor + radial-gradient halo + crisp info-toned outline ring. Callout card uses M3 elevation-2 + info-border + CSS arrow pointing at the anchor. Card placement uses an overflow-aware positioner (right → below → left → above with viewport clamp).

**Skip-on-missing-anchor:** if the anchor isn't on the page after 4×250 ms retries (~1 s), the step auto-skips with a bottom-right toast. Users are never stuck on a centered card with nothing to point at.

**Cross-route navigation:** steps 3, 5, 6, 7 (all anchor inside run-detail) navigate to the most-recent run before they fire.

**Server-persisted state:** spec 0125 introduced server-side onboarding state via `approved_emails` columns + `system_settings`. Per-user step + completion + force-reset tracking; admin can broadcast a reset.

### 5.2 — How-It-Works + Changelog

A full-page route at `#/how-it-works` (spec 0121 introduced as modal, spec 0123 promoted to route). Sticky 240 px side menu + content column up to `--md-content-max`. Tab strip in the header: How it works / Changelog.

**11 collapsible sections** (spec 0121): Protocol overview (open by default) → Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → How turns are reviewed → Item taxonomy & categories → Item lifecycle → Convergence & escape hatches → Cost & consumption. Side-menu navigation persists per-section collapse state to `localStorage`.

**14 diagrams** (7 light + 7 dark, spec 0121, authored via the diagram skill): pipeline, per-phase inputs, item lifecycle, categories, cost flow, convergence, modal anatomy. Click any diagram to enlarge it in a viewer modal (spec 0123).

**Changelog tab** opens spec entries in a full-view modal (spec 0126).

### 5.3 — Admin / Settings · ProgressSegs

Unified Admin + Settings page at `#/settings` (spec 0125). Sub-tabs: `[Allowlist] [Users]`. Users tab is a multi-user table backed by `/api/users`: select-checkbox · email · role · onboarding status (`✓ completed · v1.5.0` / `in progress · step 5/8` / `⊘ not started` / `reset pending`) · last seen · actions. Filter chips, search input, bulk-action bar.

**ProgressSegs** is an 8-segment track per user (one per onboarding step), used in the Users table to show onboarding progress.

---

## 6 — Themes (dark + light)

Token layer is theme-agnostic. Light mode flips a body class (`body.light`); every component re-resolves through the token registry.

**Components MUST NOT** hard-code colors in CSS. Components read `--md-*` role tokens, and the theme block defines what those tokens resolve to.

**Both themes ship together.** No spec is complete that only works in dark. The light-mode token block is the comparison reference.

**Surface tier swaps:**
- Dark: near-black canvas with rising tonal tiers (#08–#21 range).
- Light: cream canvas (`#faf9f6`) with rising tiers up to `#e3decf`. The cream lineage carries over from v1; the M3 surface scale gives more tiers to work with.

**Inks swap:**
- Dark: white-to-grey ladder (`#ffffff → #50545d`).
- Light: near-black-to-grey ladder (`#04060a → #a8aab0`).

**Elevation softens:**
- Dark: shadow opacity 0.30 / 0.15.
- Light: shadow opacity 0.10 / 0.06 (less aggressive against cream).

---

## 7 — Density + responsiveness

### 7.1 — Density modes

**Comfortable** (default) — M3 standard spacing. Targets wide displays (≥1700 px).

**Compact** (`body.compact`) — tightens paddings, row height, rail width; shrinks display + headline type. Applied automatically below ~1700 px and via a manual toggle.

The two modes share every component CSS rule; only token values change. No per-component compact styles.

### 7.2 — Responsiveness — three breakpoints

| Width | Layout |
|---|---|
| ≥ 1500 px | Full layout: rail open at 280 dp, comfortable density, full type scale. |
| 900–1499 px | Rail collapses to 80 dp icon-only. `--md-content-max` shrinks to 1200 px. Paddings tighten. Hero shrinks (`headline-l` instead of `display-s`). `.cols-3` / `.cols-4` collapse to 2 columns. |
| < 900 px | Single column. Rail hidden. `.cols-2` / `.cols-3` / `.cols-4` collapse to 1. Hero further shrinks (`headline-m`). |

Specs that touch layout must address all three buckets or explicitly defer them with a follow-up note.

---

## 8 — Accessibility

- **`:focus-visible` ring** on every interactive primitive — uses `--md-focus-ring` (3 px solid tertiary at 80% opacity). Applied at `--md-focus-offset` (2 px). Border-radius matches the element (`--md-shape-xs` minimum).
- **`prefers-reduced-motion`** honored everywhere — global CSS rule disables all transitions + animations. Spec-by-spec components that have animation (caret pulse, soft-pulse halo, streaming append) check the media query inline.
- **Semantic ARIA** — `aria-current="page"` on nav rail items, `aria-selected` on tabs / segmented options, `role="dialog"` + `aria-modal` on modals, `aria-label` required on icon-only buttons.
- **Color contrast** — surface + on-surface pairs target WCAG AA at minimum; agent containers tested against both surfaces; light mode independently verified.
- **Keyboard navigation** — every interactive element reachable via Tab. Modal focus trap (spec 0096). Search palette navigable via arrow keys (spec 0079).

---

## 9 — Badge governance (spec 0119)

The single chip primitive owns every badge / pill / verdict-label on every surface. The rules below are normative — surfaces consume them, they don't override them. Full implementation reference: [spec 0119](../specs/0119-badge-governance.md).

### 9.1 — One primitive

`<Chip>` (`shared.jsx`) is the only chip. Slot API:

```jsx
<Chip
  tone="info | ok | warn | err | idle | claude | gpt | neutral"
  shape="pill | square"          // pill is default; square only for identifiers
  size="default | lg"            // 22 px / 26 px
  mono dim iconOnly              // modifiers
  leadingDot leadingIcon={…} categoryBubble="Q"   // mutually exclusive
  label="…" value={N} add={N} sub={N} trailingSuffix="…"
  ariaLabel="…"                  // required when no label
  onClick={…}                    // implies button rendering
/>
```

Render order inside the chip: leading slot → label → value → add → sub → trailingSuffix → children. Absent slots emit no DOM.

### 9.2 — The nine canonical kinds

| Kind | Leading | Label | Value | Deltas | Where |
|---|---|---|---|---|---|
| **Provider** | AgentIcon | "Claude" / "GPT" | — | — | every card header, every lifecycle row, every filter |
| **Activity / round** | — | "brief" / "preflight" / "turn N" / "draft" / "review rN" | — | — | every timeline card |
| **Category counter (dense)** | category-bubble (Q/D/I/C) | — | standing | +raised, −closed | timeline turn cards; phase headers |
| **Category filter (legend)** | category-bubble | "Questions" / "Disagreements" / "Issues" / "Comments" | total | — | critique pane filter row only |
| **Status** | dot OR check | "running" / "agreed" / "queued" or none | — | — | every timeline card (right-aligned); critique card header |
| **Lifecycle verb** | — | "raised" / "addressed" / "resolved" / "acknowledged" / "withdrawn" / "capped" | — | — | lifecycle rows inside expanded critique cards |
| **Modifier** | optional glyph | "via hard cap" / "↻ closeout" / "⚠ ledger drift" / etc. | optional | — | timeline cards, critique card header |
| **Sources** | — | "Sources" | count | — | critique card header when item has evidence |
| **Identifier** | — | "Q-plan-c-04" | — | — | inline body text ONLY — never in card headers |

### 9.3 — Fixed mappings (never swap)

- **Category tones:** Q = info · D = warn · I = err · C = idle
- **Category bubble letters:** Q · D · I · C
- **Category order:** Q → D → I → C, left to right, always — enables down-column scanning

### 9.4 — Composition rules

1. Provider FIRST on every card header and every lifecycle row.
2. Activity / round SECOND.
3. Category chips THIRD, in fixed Q→D→I→C order.
4. Modifier chips FOURTH.
5. Status chip RIGHT-ALIGNED, always.
6. No public-ID chips in card headers. The orchestrator-assigned ID renders as small mono inline text inside the card body (`.crit-card-id`).
7. Status is never bare on a completed timeline card — every card carries one of `running` / `✓ agreed` / `✓` (icon-only, "completed without AGREED") / `queued`.
8. Zero-activity chips render dim (opacity 0.55) but stay present so category columns align across rounds.
9. The filter row at the top of the critique pane is the legend and the canonical disambiguator for every bubble + color combination on every other surface.

### 9.5 — Canonical vocabulary

| Context | Allowed | Forbidden |
|---|---|---|
| Categories | Questions · Disagreements · Issues · Comments | Claim · Claims · OQ · BD · OI · QCR1 |
| Lifecycle | raised · addressed · resolved · acknowledged · withdrawn · capped · "raised again" | conceded · answered · noted · accepted · non_blocking_limitation |
| Turn status | running · agreed (preceded by ✓) · queued · bare ✓ for completed | repair · NEGOTIATING · REVIEWING · APPROVED · BRIEF_OK · drafting · thinking |
| Modifier | "via hard cap" · "via ghost cap" · "⊘ N capped" · "↻ closeout" · "⚠ unverified" · "⚠ ledger drift" | "ghosted N rounds" · run-wide drift |

Enforcement: `tests/contract/test_ui_vocabulary.py` scans `src/dual_research/ui/static/` for the forbidden literals and fails CI if any chip-rendering surface drifts. Legitimate data-layer compat references carry a `// spec-0119:vocab-ok` marker.

### 9.6 — Letter-bubble rule

The 14 px filled circle with a knockout-white first letter (Q / D / I / C) is a **designed icon glyph**, not a raw abbreviation. The full word always appears in the critique-pane filter-row legend, one scroll away from any surface that uses the dense form. Color + bubble glyph + fixed Q→D→I→C order make the combination unambiguous given the legend is always visible.

On phase-header chip clusters (`.tl-phase__chips`), the bubble may be rendered at 70 % alpha so it doesn't dominate the chip's tonal background — the brand colour must remain the dominant hue and the knockout-white letter must stay legible (spec 0165 §2.4).

---

## 10 — Implementation map

| File | Owns |
|---|---|
| [`tokens.css`](../src/dual_research/ui/static/tokens.css) | All CSS custom properties (palette, type, spacing, motion, shape, elevation, state layers, density). Dark + light theme token sets. **Authoritative for token values.** |
| [`base.css`](../src/dual_research/ui/static/base.css) | Resets, typography defaults, M3 `.t-*` type role utilities, `.ms` Material Symbols sizing helpers, scrollbar styling, `:focus-visible` ring application. |
| [`components.css`](../src/dual_research/ui/static/components.css) | All component CSS — every `.md-*` primitive, every composed component, the M3 atoms catalogue. **Authoritative for visual rules.** |
| [`theme.css`](../src/dual_research/ui/static/theme.css) | Theme-level body class additives (`body.tint-secondary`, `body.compact`). |
| [`design-language.jsx`](../src/dual_research/ui/static/design-language.jsx) | Live in-app design system reference at `/#/language`. DNA one-pager (default) + Full reference (`?full=1`). Component Spotlights are mock representations — should match the production rendering. |
| [`shared.jsx`](../src/dual_research/ui/static/shared.jsx) | Function-component implementations of design system primitives: `<Chip>`, `<Card>`, `<Tab>`, `<TabGroup>`, `<AgentStrip>`, `<StatusBadge>`, `<CollapsibleSection>`, `<QuoteCallout>`, `<LoadingState>`, `<BrandMark>`, `<ModalDialog>`. **Application-logic helpers also live here** — pure design system contributors should only touch the primitive functions. |
| Per-surface JSX (`run-detail.jsx`, `run-list.jsx`, `how-it-works.jsx`, `compare.jsx`, `onboarding.jsx`, etc.) | Compose the primitives into surfaces. **Not part of the design system** — they consume it. Changes here are application work, not design system work. |
| [`assets/Design System v2.html`](assets/Design%20System%20v2.html) | Canonical visual reference — every primitive + composed component rendered in a single browsable document. Open in a browser to see what every spec section means visually. |
| [`assets/styles/tokens-and-primitives.css`](assets/styles/tokens-and-primitives.css) | Source-of-truth M3 token + primitive CSS. The live `tokens.css` + `components.css` mirror this file for the M3 layer. When values diverge, this is the authoritative reference. |
| [`assets/styles/composed-components.css`](assets/styles/composed-components.css) | Source-of-truth page-level + composed-component CSS that accompanies the canonical visual reference. |

---

## 11 — Versioning

This file (`SPEC.md`) is updated in lockstep with every design system change. Version history is captured by:

- **[`CHANGELOG.md`](CHANGELOG.md)** — human-readable change notes (date, descriptor, link to PR).
- **Git history of `SPEC.md`** — exact prior states, diff-able.
- **In-file SPEC-NNNN references** — every component row above cites the spec that introduced or last touched it.

There is no separate version file. The single living `SPEC.md` is authoritative; proposed future states live in PR descriptions until merged.

The deprecated v1 spec is preserved at [`_archive/v1/SPEC.md`](_archive/v1/SPEC.md) for code-archaeology purposes. The v2 seeding artifacts (the original Material 3 briefing + the prompt that landed it) are at [`_archive/seeding/`](_archive/seeding/).

---

## 12 — Open items

- **Diagram skill palette alignment.** ~~The vendored diagram skill at [`skills/diagram/`](skills/diagram/) uses a cream-and-indigo visual language independent of the dual-research palette (sable + sage). This is intentional today — the skill produces general-purpose architecture diagrams, not in-app UI. If we want the skill output to share visual DNA with the app, a follow-up spec aligns it to the M3 palette.~~ **Status:** done as of spec 0133 — the diagram skill became mode-aware (v2.0.0). The existing cream + indigo design system was preserved as **Pixel mode** (default, general-purpose, subject-agnostic) and a new **Material mode** was added alongside, modeled on this design system. Both modes ship light + dark variants; mode is part of the filename (`<slug>.<mode>.{light,dark}.svg`). The `diagrams/how-it-works/` set was regenerated in Material mode as part of the same spec. See [`skills/diagram/SKILL.md`](skills/diagram/SKILL.md) and [`skills/diagram/references/material/foundations.html`](skills/diagram/references/material/foundations.html) for the Material design system spec.
- **Responsive density gap** (laptop 1512 px vs. wide ≥ 2200 px) — original audit at [`audits/2026-05-18-responsive-audit/`](audits/2026-05-18-responsive-audit/). Partially addressed by `body.compact` + the 1500 px breakpoint introduced in spec 0092 + further by spec 0124. Watch for outstanding regressions at specific viewport widths.

# dual-research — Design System Spec

**Version:** snapshot of `main` as of `0fd9b95` (v0.69.12)
**Last sync:** 2026-05-18 — drift fixes for specs 0084 / 0085 / 0086 / 0087 brought into the in-app `design-language.jsx` reference
**Status:** canonical text reference — pair with [`../src/dual_research/ui/static/tokens.css`](../src/dual_research/ui/static/tokens.css), [`../src/dual_research/ui/static/components.css`](../src/dual_research/ui/static/components.css), and the live page at [`/#/language`](../src/dual_research/ui/static/design-language.jsx) for the implementation.

---

## 0 — Mission

> A calm, dense observability surface for a two-agent convergence loop.
> Read-only, terminal-adjacent, single user. Information density is a feature. Decoration that fights the signal is removed.

The whole design follows three rules: **never compete with the agent output, never compete with the terminal next to it, never hide the one number that matters.**

---

## 1 — Principles

1. **Read-only is a discipline.** No buttons that mutate state. Every affordance is a view filter, a tab, or a focus shift. If the user wants to act, they go to the terminal.
2. **One color per agent, everywhere.** Sable for Claude, sage for GPT. Status colors are the only other hues. A third hue in a wireframe gets cut.
3. **Mono for anything an agent produced.** Streaming output, tokens, costs, IDs, positions in the disagreements panel. Sans for prose the UI itself wrote.
4. **Density is a feature.** A run-list row fits eight columns at 1200px without ellipses below the topic. Padding is generous between panels and minimal within them.
5. **Calm transitions or none.** No bounces, no scale, no springs. Soft pulses for live states; everything else is opacity + position only.
6. **Show why a run is slow.** The disagreements panel always tells the operator which contested point is blocking convergence. No buried logs.
7. **Token-only colors.** No hex codes in components. Every color reads from `tokens.css` so theme changes propagate everywhere.
8. **Full-word vocabulary.** Labels use complete words, never abbreviated codes. "conceded by Claude", not "→ c". Codified in SPEC-0067.
9. **Brand fidelity.** Official Anthropic sunburst and OpenAI hexagonal rosette everywhere an agent is identified. No generic substitutes.
10. **Accessibility.** `:focus-visible` ring on every interactive primitive; `prefers-reduced-motion` honored on every animation; semantic ARIA where the markup needs it. Codified in SPEC-0087.

---

## 2 — Foundations

All foundation values are CSS custom properties defined in [`tokens.css`](../src/dual_research/ui/static/tokens.css). Components MUST read from these tokens; no hex codes anywhere in component CSS.

### 2.1 Palette

#### Agents (the two-color system)

| Token             | Hex       | Role                                                                                              |
|-------------------|-----------|---------------------------------------------------------------------------------------------------|
| `--agent-a`       | `#d4a574` | **Claude — Sable.** Track A. Output accents, agent-tagged borders, last-turn tags.                |
| `--agent-a-dim`   | `#8a6d4e` | Dimmed sable for muted states.                                                                    |
| `--agent-a-bg`    | rgba 0.08 | Background tint behind Claude content.                                                            |
| `--agent-a-bg-strong` | rgba 0.16 | Stronger tint (selected / focused Claude row).                                                |
| `--agent-a-border` | rgba 0.22 | Hairline border for Claude-tinted containers.                                                    |
| `--agent-b`       | `#7cc4b8` | **GPT — Sage.** Track B. Same roles, GPT side.                                                    |
| `--agent-b-dim`   | `#4f8079` | Dimmed sage.                                                                                       |
| `--agent-b-bg`    | rgba 0.08 | GPT bg tint.                                                                                       |
| `--agent-b-bg-strong` | rgba 0.16 | GPT bg tint (strong).                                                                          |
| `--agent-b-border` | rgba 0.22 | GPT hairline border.                                                                              |

Sable and sage sit on opposite sides of the warm/cool axis at near-identical L\*, so neither agent feels louder than the other.

#### Surfaces (5 levels, dark mode default)

| Token     | Hex       | Role                                |
|-----------|-----------|-------------------------------------|
| `--bg-0`  | `#08090b` | Page background, streaming body     |
| `--bg-1`  | `#0d0f12` | Default panel                       |
| `--bg-2`  | `#131519` | Elevated row / chip bg / modal header |
| `--bg-3`  | `#191c21` | Hover, active chip                  |
| `--bg-4`  | `#1f2329` | High-contrast surface (dropdown row) |

#### Borders (3 weights)

| Token        | Hex       | Role                                            |
|--------------|-----------|-------------------------------------------------|
| `--border-1` | `#1c1f24` | Hairline (default container border)             |
| `--border-2` | `#262a31` | Medium (cards, panels needing more definition)  |
| `--border-3` | `#343941` | Strong (focus + active states)                  |

#### Foreground (5 levels)

| Token    | Hex       | Role                                          |
|----------|-----------|-----------------------------------------------|
| `--fg-0` | `#ffffff` | Primary text, numbers, headings (pure white for max heading punch on dark) |
| `--fg-1` | `#b4bac4` | Body prose                                    |
| `--fg-2` | `#9aa0ac` | Secondary, meta, labels                       |
| `--fg-3` | `#7d8290` | Muted, column headers                         |
| `--fg-4` | `#50545d` | Decorative, dividers in copy                  |

#### Status (4 hues + idle)

Used only on state changes. Same dusty saturation as agent colors — reads as the same family, never marketing-grade.

| Token    | Hex       | Role                                  |
|----------|-----------|---------------------------------------|
| `--ok`   | `#6fb380` | resolved · converged · completed · approved |
| `--info` | `#6b9cf0` | running · current phase · live cursor · focus ring |
| `--warn` | `#d4a056` | approaching cap · deadlocked · drift  |
| `--err`  | `#d96a6a` | errored · halted                       |
| `--idle` | `#5e636d` | idle · paused · awaiting              |

Each status hue also has a `-bg` and `-border` rgba variant for banners and inline cards.

#### On-accent

`--on-accent: #14110a` — text/icon color atop solid agent-color fills.

#### Light mode

`body.light` (or `.light` class) swaps all the above to a cream + dark-text palette. Defined at the bottom of `tokens.css`. Spacing, type, and shape tokens are theme-independent.

### 2.2 Typography

Two families from the IBM Plex system. Designed together — same x-height, same proportions — so they blend visually while staying clearly distinct (sans vs serif). **No monospace family** — tabular figures via `font-feature-settings` on the sans.

| Family | Token       | Used for                                                                 |
|--------|-------------|--------------------------------------------------------------------------|
| Sans   | `--sans`    | UI chrome, body, labels, buttons, navigation, status pills, IDs, costs, tokens (with tabular-nums via `.num` utility). |
| Serif  | `--serif`   | Agent-produced prose, hero text, page-level headings, blockquotes, QuestionThread quotes. The agent's voice. |
| Mono   | `--mono`    | Aliased to `--sans` — the project does not ship a separate mono family.   |

Fallbacks: `--sans` → `ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif` · `--serif` → `ui-serif, "Iowan Old Style", Charter, Georgia, serif`.

#### Type scale (7 steps, exact pixel values)

| Token         | Size  | Role                                            |
|---------------|-------|-------------------------------------------------|
| `--t-display` | 28px  | Page hero (Landing, Design Language)            |
| `--t-title`   | 20px  | Section H2, modal title                         |
| `--t-h3`      | 16px  | Card title, panel title                         |
| `--t-body`    | 13px  | Default UI body                                 |
| `--t-meta`    | 12px  | Secondary body, table cells, subtitle           |
| `--t-mono`    | 11px  | Numbers, IDs, status labels, chips              |
| `--t-label`   | 10px  | UPPERCASE labels (letter-spacing 0.08em)        |

#### Line heights

| Token         | Value | Use                                          |
|---------------|-------|----------------------------------------------|
| `--lh-tight`  | 1.15  | Display / title                              |
| `--lh-snug`   | 1.30  | H3 / card titles                             |
| `--lh-body`   | 1.45  | Default UI body                              |
| `--lh-prose`  | 1.60  | Long-form prose (agent output, descriptions) |

#### Weights

| Token         | Value | Use                                                      |
|---------------|-------|----------------------------------------------------------|
| `--w-regular` | 400   | Body, prose                                              |
| `--w-medium`  | 500   | Labels, secondary emphasis                               |
| `--w-semi`    | 600   | Headings, primary emphasis, hero                         |
| `--w-bold`    | 700   | Uppercase section labels                                 |

### 2.3 Spacing & shape

**4px grid.** No values outside this scale; the tokens below are the only allowed spacings.

| Token    | Value | Common use                              |
|----------|-------|-----------------------------------------|
| `--s-1`  | 4px   | Tight gap inside a chip                 |
| `--s-2`  | 8px   | Gap between chips, between row siblings |
| `--s-3`  | 12px  | Card inner padding (compact)            |
| `--s-4`  | 16px  | Card inner padding (default)            |
| `--s-5`  | 20px  | Panel inner padding                     |
| `--s-6`  | 24px  | Gap between panels                      |
| `--s-8`  | 32px  | Section spacing                         |
| `--s-10` | 40px  | Hero spacing                            |
| `--s-12` | 48px  | Page padding                            |
| `--s-16` | 64px  | Hero top                                |
| `--s-20` | 80px  | Marketing-page hero                     |

#### Radii (4 named + pill)

| Token      | Value | Role                                                  |
|------------|-------|-------------------------------------------------------|
| `--r-1`    | 4px   | Status pills, mini chips, indicators                  |
| `--r-2`    | 6px   | Buttons, inputs, segments                             |
| `--r-3`    | 8px   | Cards, panels, modal body                             |
| `--r-4`    | 12px  | Modal frame, tweaks dev panel                         |
| `--r-pill` | 999px | Run ID, agent strip, true pills                       |

#### Border widths

| Token    | Value | Use                                              |
|----------|-------|--------------------------------------------------|
| `--bw-1` | 1px   | Hairlines                                        |
| `--bw-2` | 2px   | Streaming outline, modal accent stripe           |
| `--bw-3` | 3px   | Error card severity stripe (only)                |

### 2.4 Motion

Streaming should feel like a calm typewriter. State transitions should be **noticed, not announced.**

| Token       | Value                      | Use                                  |
|-------------|----------------------------|--------------------------------------|
| `--m-fast`  | 120ms                      | Hover / focus state changes          |
| `--m-base`  | 180ms                      | Default state transition             |
| `--m-slow`  | 400ms                      | Layout opacity transitions           |
| `--ease`    | `cubic-bezier(0.2, 0, 0, 1)` | Default ease-out                   |

**Rules:**
- **Streaming tokens:** 60–90 chars/sec, per-frame batch (16ms), no per-char layout thrash. A 0.9-opacity block caret pulses at 1.05s to anchor the eye.
- **State transitions:** 180ms ease-out, single property at a time (opacity, color, position). No `transform: scale`. No `transform: translate` unless replacing the entire element.
- **Loud states** (cap approaching, deadlock, error): slow 2.2s soft-pulse halo. Never a hard flash.
- **No success animations** on convergence — the document just renders.
- **No toast notifications** — this is a read-only surface.
- **The one loading visual** is `<LoadingState>` (SPEC-0084) — used at the page or panel level when no useful payload has arrived yet. **No spinners within the run document.**

#### Focus + accessibility

| Token             | Value                          | Use                                  |
|-------------------|--------------------------------|--------------------------------------|
| `--focus-ring`    | `2px solid var(--info)`        | `:focus-visible` ring                |
| `--focus-offset`  | `2px`                          | Outline offset                       |

`prefers-reduced-motion` is honored on every animation (caret pulse, soft-pulse halo, streaming append).

### 2.5 Layout

| Token            | Value | Role                                                       |
|------------------|-------|------------------------------------------------------------|
| `--chrome-h`     | 44px  | Height of the top chrome bar (All runs / Compare / Search) |
| `--content-max`  | 1400px | Max width of the main content column                      |

**Known limitation (responsive density audit, 2026-05-18):** the content cap and the spacing scale are tuned for a single viewport class (~2560px wide, single Samsung Odyssey G7). At 1512px (MacBook Pro 14" laptop logical resolution), the run-detail surface becomes cramped. Fix proposed in [`audits/2026-05-18-responsive-audit/`](audits/2026-05-18-responsive-audit/): add a `--density` token + `body.compact` class for content-density swaps below ~1700px.

---

## 3 — Components

Components are catalogued live in [`design-language.jsx`](../src/dual_research/ui/static/design-language.jsx) (served at `/#/language`). The full reference (at `/#/language?full=1`) preserves historical content. This section gives the markdown overview.

| Name                | Lives in                          | Purpose                                                                            | Introduced |
|---------------------|-----------------------------------|------------------------------------------------------------------------------------|------------|
| `<Chip>`            | `shared.jsx` + `.chip` CSS        | Compact labeled token with optional icon and count. Tones: info, ok, warn, neutral, agentA, agentB. |  early  |
| `<Card>`            | `shared.jsx` + `.card` CSS        | Expandable container for timeline entries and critique items.                       |  early  |
| `<Tab>` + `<TabGroup>` | `shared.jsx` + `.tab` CSS      | Three variants: bordered pill, minimal underline (`variant="line"`), segmented solid (`variant="solid"`). |  early  |
| `<AgentStrip>`      | `shared.jsx` + `.as` CSS          | Equal-width agent identifier with model, tokens, cost, and status. Both pills share width via `flex: 1 1 0`. Compact 4px vertical padding. | SPEC-0070 |
| `<StatusBadge>`     | `shared.jsx` + `.sb` CSS          | Fixed-width status pill with dot + label. Uniform 88px min-width.                   |  early  |
| `<CollapsibleSection>` | `shared.jsx` + `.cs-*` CSS     | Generic disclosure primitive. Persists open/closed state to `localStorage`.         |  early  |
| `<QuoteCallout>`    | `shared.jsx` + `.quote-callout` CSS | Styled callout for quote fields on critique cards. Left border + italic + muted bg. | SPEC-0073 |
| **Agent Input panel** | `run-detail.jsx` + `.agent-input-*` CSS | **3-tier hierarchy**: System Prompt (collapsed) → User Prompt (expanded, with nested 'From chat' + 'External resources mentioned' sub-sections) → Child Pages. | SPEC-0074, extended by SPEC-0085 |
| **Consumption row** | `run-detail.jsx` + `.consumption-*` CSS | **Phase header above the row** (not glued to cards). Below: paired agent cards — 3 zones each (data header, divider, bars zone). Equal-height via grid stretch. | SPEC-0075, reworked by SPEC-0086 |
| `<LoadingState>`    | `shared.jsx` + `.dr-loading-*` CSS | **Three sizes**: `inline` (14px spinner, row layout), `panel` (28px, column), `page` (44px, column). Spinner + label + optional hint. Default hint: "Just a moment, please." **The one loading visual everywhere.** | SPEC-0084 |
| `<PhaseRail>`       | `run-detail.jsx` + `.phase-rail-*` CSS | Left-edge vertical timeline navigator. Dots per phase, current phase animated.   | SPEC-0066 |
| `<RoundScrubber>`   | `run-detail.jsx` + `.round-scrubber-*` CSS | Inline round navigator inside phase headers (R1 R2 R3 R4 …).                |  early  |
| `<QuestionThread>`  | `run-detail.jsx` + `.qthread`, `.qt-*` CSS | Critique-card body: question, two agent positions, optional drift + resolution timeline. |  early  |
| `<ModalDialog>`     | `shared.jsx` + `.dr-modal-*` CSS  | Generic split-pane modal for inputs / attachments / searches.                       |  early  |
| `<BrandMark>`       | `shared.jsx`                      | Anthropic sunburst (Claude) / OpenAI rosette (GPT). Sizes: 48 / 32 / 24 / 16. Variants: solid, ghost. | SPEC-0087 |

Additional primitives in the design-language full reference (`?full=1`): `Pill`, `PhaseMini`, `Streaming box`, `Cap bar`, `Disagreement row`.

---

## 4 — Patterns (composed)

Patterns are how components compose into surfaces. These are conventions, not separate components.

### 4.1 Run-detail three-pane layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ chrome (All runs · Compare · Search                ⬤ v0.69 · etc.) │
├──────────────────────────────────────────────────────────────────────┤
│ run header: title + draft button | agent strip pair | reconcile chip │
├────────────┬──────────────────────────┬──────────────────────────────┤
│            │                          │                              │
│ Timeline   │   Conversation /         │   Critique pane              │
│ (artifacts)│   Consumption (main)     │   (questions / disagreements)│
│            │                          │                              │
└────────────┴──────────────────────────┴──────────────────────────────┘
```

Three columns. Left ~10% (Timeline), middle ~55% (main content), right ~35% (Critique). **Known density problem at viewports < 1700px** — see responsive audit.

### 4.2 Run-list table

Data table at `--content-max` (1400px). Columns: RUN ID, STATUS, TOPIC, PHASE, STARTED, DURATION, COST. Filter chips above ("Needs attention", "All", "running", "converged", "deadlocked", "errored", "completed").

### 4.3 Consumption phase group

A `.consumption-phase-group` contains a `.consumption-phase-header` (phase name + meta) ABOVE one or more `.consumption-row` entries. Each row is a 2-column grid (or 3-column with a leading round chip for phases with rounds) of paired agent cards.

### 4.4 Agent Input panel (3-tier hierarchy)

```
▶ System prompt              (system)                       4,915 chars
▼ User prompt                                             245,378 chars
  │ From chat                                              3,142 chars
  │ External resources mentioned                          2 resources
▶ Child page: Notion ADR-014                              12,847 chars
▶ Child page: Internal RFC-2023-04                         4,512 chars
```

---

## 4.5 — Badge governance (spec 0119)

The single chip primitive owns every badge / pill / verdict-label on every surface. The rules below are normative — surfaces consume them, they don't override them. Full implementation reference: [spec 0119](../specs/0119-badge-governance.md).

### 4.5.1 One primitive

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

### 4.5.2 The nine canonical kinds

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

### 4.5.3 Fixed mappings (never swap)

- **Category tones:** Q = info · D = warn · I = err · C = idle
- **Category bubble letters:** Q · D · I · C
- **Category order:** Q → D → I → C, left to right, always — enables down-column scanning

### 4.5.4 Composition rules

1. Provider FIRST on every card header and every lifecycle row.
2. Activity / round SECOND.
3. Category chips THIRD, in fixed Q→D→I→C order.
4. Modifier chips FOURTH.
5. Status chip RIGHT-ALIGNED, always.
6. No public-ID chips in card headers. The orchestrator-assigned ID renders as small mono inline text inside the card body (`.crit-card-id`).
7. Status is never bare on a completed timeline card — every card carries one of `running` / `✓ agreed` / `✓` (icon-only, "completed without AGREED") / `queued`.
8. Zero-activity chips render dim (opacity 0.55) but stay present so category columns align across rounds.
9. The filter row at the top of the critique pane is the legend and the canonical disambiguator for every bubble + color combination on every other surface.

### 4.5.5 Canonical vocabulary

| Context | Allowed | Forbidden |
|---|---|---|
| Categories | Questions · Disagreements · Issues · Comments | Claim · Claims · OQ · BD · OI · QCR1 |
| Lifecycle | raised · addressed · resolved · acknowledged · withdrawn · capped · "raised again" | conceded · answered · noted · accepted · non_blocking_limitation |
| Turn status | running · agreed (preceded by ✓) · queued · bare ✓ for completed | repair · NEGOTIATING · REVIEWING · APPROVED · BRIEF_OK · drafting · thinking |
| Modifier | "via hard cap" · "via ghost cap" · "⊘ N capped" · "↻ closeout" · "⚠ unverified" · "⚠ ledger drift" | "ghosted N rounds" · run-wide drift |

Enforcement: `tests/contract/test_ui_vocabulary.py` scans `src/dual_research/ui/static/` for the forbidden literals and fails CI if any chip-rendering surface drifts. Legitimate data-layer compat references carry a `// spec-0119:vocab-ok` marker.

### 4.5.6 Letter-bubble rule (evolution of 0115's "never abbreviate")

The 14 px filled circle with a knockout-white first letter (Q / D / I / C) is a **designed icon glyph**, not a raw abbreviation. The full word always appears in the critique-pane filter-row legend, one scroll away from any surface that uses the dense form. Color + bubble glyph + fixed Q→D→I→C order make the combination unambiguous given the legend is always visible.

---

## 5 — Implementation map

| File                                                          | Owns                                                                                   |
|---------------------------------------------------------------|----------------------------------------------------------------------------------------|
| [`tokens.css`](../src/dual_research/ui/static/tokens.css)     | All CSS custom properties (palette, type, spacing, motion, layout). Dark + light mode token sets. **Authoritative for token values.** |
| [`theme.css`](../src/dual_research/ui/static/theme.css)       | Theme-level overrides not covered by token swaps (e.g., elevation shadows tuned per theme). |
| [`base.css`](../src/dual_research/ui/static/base.css)         | Resets, typography defaults, `.num` utility for tabular figures, scrollbar styling, focus-visible ring application. |
| [`components.css`](../src/dual_research/ui/static/components.css) | All component CSS — `.chip`, `.card`, `.tab`, `.as`, `.sb`, `.cs-*`, `.quote-callout`, `.agent-input-*`, `.consumption-*`, `.dr-loading-*`, `.dr-modal-*`, `.phase-rail-*`, `.qthread` / `.qt-*`, `.round-scrubber-*`. **Authoritative for component visual rules.** |
| [`design-language.jsx`](../src/dual_research/ui/static/design-language.jsx) | Live in-app design system reference. DNA one-pager (default) + Full reference (`?full=1`). Component Spotlights are mock representations — should match the production rendering. |
| [`shared.jsx`](../src/dual_research/ui/static/shared.jsx)     | Function-component implementations of design system primitives: `Chip`, `Card`, `Tab`, `TabGroup`, `AgentStrip`, `StatusBadge`, `CollapsibleSection`, `QuoteCallout`, `LoadingState`, `BrandMark`, `ModalDialog`. **Application-logic helpers also live here** — pure design system contributors should only touch the primitive functions. |
| Per-surface JSX (`run-detail.jsx`, `runs-list.jsx`, `how-it-works.jsx`, `compare.jsx`, `onboarding.jsx`, etc.) | Compose the primitives into surfaces. **Not part of the design system** — they consume it. Changes here are application work, not design system work. |

---

## 6 — Versioning

This file (`SPEC.md`) is updated in lockstep with every design system change. Version history is captured by:

- **[`CHANGELOG.md`](CHANGELOG.md)** — human-readable change notes (date, descriptor, link to PR).
- **Git history of `SPEC.md`** — exact prior states, diff-able.
- **In-file SPEC-NNNN references** — every component row above cites the spec that introduced or last touched it.

There is no separate V1/V2 file. The single living `SPEC.md` is authoritative; proposed future states live in PR descriptions until merged.

---

## 7 — Open items

- **Responsive density gap** (laptop 1512px vs. wide ≥2200px) — full audit at [`audits/2026-05-18-responsive-audit/`](audits/2026-05-18-responsive-audit/). Proposed fix: add `--density` token + `body.compact` class. Not yet implemented; awaiting Claude Design's V1 to integrate.
- **Awaiting from Claude Design**: V1 deliverable based on the design brief packaged on 2026-05-17. Will land via PR through this folder once the two-way flow is set up.

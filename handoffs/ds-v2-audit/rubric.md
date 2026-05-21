# DS v2 Rubric

## 1. Token allow-list

### Color tokens (agent, status, palette source)

| Token | Value | Light | Purpose |
|---|---|---|---|
| `--agent-a` | `#d4a574` | (same) | Claude identity (warm sable) |
| `--agent-a-bg` | `rgba(212,165,116,0.08)` | `rgba(...,0.14)` | Claude background tint |
| `--agent-a-border` | `rgba(212,165,116,0.22)` | `rgba(...,0.42)` | Claude border/divider |
| `--agent-b` | `#7cc4b8` | (same) | GPT identity (cool sage) |
| `--agent-b-bg` | `rgba(124,196,184,0.08)` | `rgba(...,0.14)` | GPT background tint |
| `--agent-b-border` | `rgba(124,196,184,0.22)` | `rgba(...,0.42)` | GPT border/divider |
| `--ok` | `#6fb380` | (same) | Resolved / converged / completed |
| `--info` | `#6b9cf0` | (same) | Running / current phase / focus ring |
| `--warn` | `#d4a056` | (same) | Approaching cap / deadlocked / drift |
| `--err` | `#d96a6a` | (same) | Errored / halted |
| `--idle` | `#5e636d` | (same) | Idle / paused / awaiting |
| `--ok-bg` / `--ok-border` | `rgba(111,179,128,...)` | adjusted | Status background tints (rare) |
| `--info-bg` / `--info-border` | `rgba(107,156,240,...)` | adjusted | Status background tints |
| `--warn-bg` / `--warn-border` | `rgba(212,160,86,...)` | adjusted | Status background tints |
| `--err-bg` / `--err-border` | `rgba(217,106,106,...)` | adjusted | Status background tints |
| `--idle-bg` / `--idle-border` | `rgba(94,99,109,...)` | adjusted | Status background tints |

### M3 color roles (Material 3 canonical)

**Primary (sable).** Consumed by agent-A components, brand elements.

| Token | Dark | Light | Role |
|---|---|---|---|
| `--md-primary` | `#d4a574` | `#d4a574` | Agent A identity |
| `--md-on-primary` | `#1f1407` | `#1f1407` | Text on primary-filled |
| `--md-primary-container` | `rgba(212,165,116,0.18)` | `rgba(212,165,116,0.26)` | Agent A bg (tinted) |
| `--md-on-primary-container` | `#f3deca` | `#3b2810` | Text on primary-container |

**Secondary (sage).** Consumed by agent-B components, secondary actions.

| Token | Dark | Light | Role |
|---|---|---|---|
| `--md-secondary` | `#7cc4b8` | `#7cc4b8` | Agent B identity |
| `--md-on-secondary` | `#06201d` | `#06201d` | Text on secondary-filled |
| `--md-secondary-container` | `rgba(124,196,184,0.18)` | `rgba(124,196,184,0.26)` | Agent B bg (tinted) |
| `--md-on-secondary-container` | `#cfece6` | `#0a322d` | Text on secondary-container |

**Tertiary (info).** Used for focus ring, running phase, liveness.

| Token | Dark | Light | Role |
|---|---|---|---|
| `--md-tertiary` | `#6b9cf0` | `#6b9cf0` | Info / focus hue |
| `--md-on-tertiary` | `#061229` | `#061229` | Text on tertiary-filled |
| `--md-tertiary-container` | `rgba(107,156,240,0.18)` | `rgba(107,156,240,0.20)` | Info bg tint |
| `--md-on-tertiary-container` | `#d6e3ff` | `#0a1d44` | Text on tertiary-container |

**Error (err).** Standard M3 error hue.

| Token | Dark | Light | Role |
|---|---|---|---|
| `--md-error` | `#d96a6a` | `#d96a6a` | Error / halted |
| `--md-on-error` | `#2a0808` | `#2a0808` | Text on error-filled |
| `--md-error-container` | `rgba(217,106,106,0.16)` | `rgba(217,106,106,0.18)` | Error bg tint |
| `--md-on-error-container` | `#f3c8c5` | `#4a0e0e` | Text on error-container |

**Warning (warn).** Status hue.

| Token | Dark | Light | Role |
|---|---|---|---|
| `--md-warning` | `#d4a056` | `#d4a056` | Warning / drift / cap |
| (no on/container) | — | — | (used as status hue) |

**Success (ok).** Status hue.

| Token | Dark | Light | Role |
|---|---|---|---|
| `--md-success` | `#6fb380` | `#6fb380` | Success / resolved |
| (no on/container) | — | — | (used as status hue) |

### Surface tiers (M3 tonal elevation — dark + light mode paired)

| Token | Dark | Light | Role |
|---|---|---|---|
| `--md-surface-dim` | `#08090b` | `#ece8de` | Page bg / streaming body |
| `--md-surface` | `#0d0f12` | `#faf9f6` | Default surface |
| `--md-surface-bright` | `#21242a` | `#ffffff` | Bright (rare callouts) |
| `--md-surface-container-lowest` | `#0a0c0f` | `#ffffff` | Recessed tier |
| `--md-surface-container-low` | `#111317` | `#f5f3ec` | Default panel |
| `--md-surface-container` | `#14171c` | `#f0ede4` | Elevated row / chip bg / modal header |
| `--md-surface-container-high` | `#191c21` | `#e9e5d9` | Hover / active chip |
| `--md-surface-container-highest` | `#21252b` | `#e3decf` | Highest static tier |
| `--md-surface-1..5` | color-mix(tint 5%..14%) | color-mix(tint 5%..14%) | Tonal elevation (overlay) |

### On-surface inks (text / foreground)

| Token | Dark | Light | Role |
|---|---|---|---|
| `--md-on-surface` | `#ffffff` | `#04060a` | Primary text / numbers / headings |
| `--md-on-surface-variant` | `#b4bac4` | `#3a3f47` | Body prose |
| `--md-on-surface-muted` | `#9aa0ac` | `#4d5159` | Secondary / meta / labels |
| `--md-on-surface-faint` | `#7d8290` | `#6f7480` | Muted / column headers |
| `--md-on-surface-decor` | `#50545d` | `#a8aab0` | Decorative / inline dividers |

### Outlines (borders / dividers)

| Token | Dark | Light | Role |
|---|---|---|---|
| `--md-outline` | `#343941` | `#aaa599` | Strong outline (focus, active) |
| `--md-outline-variant` | `#262a31` | `#d2cdc0` | Medium (cards, panels) |
| `--md-outline-hair` | `#1c1f24` | `#e7e3d9` | Hairline (default border) |

### Typography — fonts

| Token | Value | Use |
|---|---|---|
| `--md-font-plain` | Roboto Flex + fallbacks | Chrome, body, labels, IDs, costs, data |
| `--md-font-brand` | Roboto Serif + fallbacks | Hero, headings, blockquotes, agent voice |
| `--md-font-data` | Roboto Flex + `font-variant-numeric: tabular-nums` | Numbers, IDs, alignment-critical data |

### Typography — type scale (15 roles: 5 categories × 3 sizes)

All roles have `--md-<role>-size`, `--md-<role>-lh` (line-height), and some track (letter-spacing).

**Display** (brand font, hero): `--md-display-{l,m,s}-size/lh` + `-track`
**Headline** (brand font, section heads): `--md-headline-{l,m,s}-size/lh`
**Title** (plain font, subsections): `--md-title-{l,m,s}-size/lh` + `-track` (m, s)
**Body** (plain font, default): `--md-body-{l,m,s}-size/lh`
**Label** (plain font, uppercase): `--md-label-{l,m,s}-size/lh` + `-track`

Corresponding utility classes: `.t-display-l`, `.t-title-m`, `.t-body-m`, `.t-label-s`, etc.

### Weights

| Token | Value | Use |
|---|---|---|
| `--md-w-regular` | 400 | Body text, standard weight |
| `--md-w-medium` | 500 | Secondary emphasis, tabs |
| `--md-w-semi` | 600 | Strong emphasis, labels |
| `--md-w-bold` | 700 | Primary emphasis, headings |

### Shape scale (border-radius)

| Token | Value | Use |
|---|---|---|
| `--md-shape-xs` | 4 px | Status pills, mini indicators |
| `--md-shape-sm` | 8 px | Chips, small cards |
| `--md-shape-md` | 12 px | **Default card/panel radius** |
| `--md-shape-lg` | 16 px | FAB, large frames |
| `--md-shape-xl` | 28 px | Dialogs, modals |
| `--md-shape-full` | 9999 px | Pills (buttons, run IDs, true pills) |

### Spacing (8 dp grid + 4 dp half-step)

All spacing is `--md-sp-<N>` where N ∈ {0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 20}.

Values: 0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 56, 64, 80 px.

### Elevation (6 levels — shadow recipes)

| Token | Recipe | Use |
|---|---|---|
| `--md-elev-0` | none | No elevation |
| `--md-elev-1` | Subtle 2-layer shadow | Resting card |
| `--md-elev-2` | Slightly stronger | Hover state |
| `--md-elev-3` | Moderate lift | Dialogs, modals, FAB |
| `--md-elev-4` | Strong | Drag / pick-up |
| `--md-elev-5` | Topmost | Sticky bars (rare) |

Light mode has softer (lower opacity) shadow recipes.

### State layer opacities

| Token | Opacity | Trigger |
|---|---|---|
| `--md-state-hover` | 0.08 | `:hover` |
| `--md-state-focus` | 0.10 | `:focus-visible` |
| `--md-state-pressed` | 0.12 | `:active` |
| `--md-state-dragged` | 0.16 | Drag state |

Applied as `currentColor` overlay.

### Motion

**Easings:**
- `--md-easing-emphasized`: default (0.2, 0, 0, 1)
- `--md-easing-standard`: state transitions (same)
- `--md-easing-emphasized-decel/accel`: entry/exit variants
- `--md-easing-standard-decel/accel`: subtle entry/exit

**Durations:**
- `--md-dur-short-{1,2,3,4}`: 50, 100, 150, 200 ms
- `--md-dur-medium-{1,2,4}`: 250, 300, 400 ms
- `--md-dur-long-2`: 500 ms

### Focus ring

| Token | Value |
|---|---|
| `--md-focus-ring` | 3px solid color-mix(in srgb, var(--md-tertiary) 80%, transparent) |
| `--md-focus-offset` | 2 px |

### Density

| Token | Comfortable | Compact |
|---|---|---|
| `--md-density` | 0 | 1 |
| `--md-pad-card` | 24 px | 16 px |
| `--md-pad-card-y` | 20 px | 12 px |
| `--md-gap-row` | 32 px | 20 px |
| `--md-gap-col` | 24 px | 16 px |
| `--md-row-h` | 56 px | 44 px |
| `--md-rail-w` | 280 px | 240 px |

### Layout constants

| Token | Value | Role |
|---|---|---|
| `--md-content-max` | 1440 px | Max width for page content |
| `--md-rail-w` | 280 px (comf) / 240 px (compact) | Navigation rail width |

### Legacy tokens (now retired — audit must reject if found)

**Retired in spec 0131:**

`--bg-0` through `--bg-4` · `--fg-0` through `--fg-4` · `--border-1` through `--border-3` · `--r-1` through `--r-3` (+ `--r-pill`, `--r-4`) · `--t-display`, `--t-title`, `--t-h3`, `--t-body`, `--t-meta`, `--t-mono`, `--t-label`, `--t-sm` · `--mono`, `--sans`, `--serif` · `--w-regular` through `--w-bold` (legacy, replaced by `--md-w-*`)

**Retired in spec 0132:**

`--w-regular`, `--w-medium`, `--w-semi`, `--w-bold`

---

## 2. Component catalog

Every component class in `components.css` (M3 and dual-research composed):

### Primitives

| Class(es) | Variants | Required structure | Intended use |
|---|---|---|---|
| `.md-btn` | `--filled`, `--tonal`, `--outlined`, `--text`, `--elevated`; `--sm`, `--lg` | `<button class="md-btn md-btn--filled">Label</button>` | Interactive buttons · primary / secondary / tertiary actions |
| `.md-chip` | `--selected`, `--filter-a`, `--sm` | `<button class="md-chip">Label</button>` or slots | Filters, input, suggestions, badges |
| `.md-card` | `--elevated`, `--filled`, `--outlined`, `--tonal-a`, `--tonal-b` | `<div class="md-card"><header class="md-card__hd">…</header><div class="md-card__title">…</div></div>` | Surfaces, content containers |
| `.md-tabs` / `.md-tab` | (segmented tabs: `.md-seg`, `.md-seg__opt`) | `<div class="md-tabs"><button class="md-tab">…</button></div>` | Navigation tabs, filter clusters |
| `.md-dialog` | `--icon`, `--title`, `--body`, `--actions` | `<div class="md-dialog"><header class="md-dialog__title">…</header><div class="md-dialog__body">…</div></div>` | Modal dialogs, rich modals |
| `.md-appbar` | `--title`, `--spacer` | `<header class="md-appbar"><span class="md-appbar__title">…</span></header>` | Top navigation bar |
| `.md-rail` | `--brand`, `--group-label` | `<nav class="md-rail"><a>…</a></nav>` | Side navigation rail |
| `.md-list` | `--item`, `--lead`, `--body`, `--headline`, `--support` | `<ul class="md-list"><li class="md-list__item">…</li></ul>` | List items (three-line anatomy) |
| `.md-divider` | `--inset` | `<hr class="md-divider">` | Hairline or inset divider |

### Dual-research composed / extended

| Class(es) | Variants | Required structure | Intended use |
|---|---|---|---|
| `.chip` | `.tone-{claude,gpt,info,ok,warn,err,idle,muted}`, `.no-dot`, `.mono`, `.dim` | Slots: `.chip-dot` / `.chip-leading-icon` / `.cat-bubble` / `.chip-value` / `.chip-add` / `.chip-sub` / `.chip-suffix` | Status pills, category badges, filter chips — **primary primitive on run-detail** |
| `.card` | `.tone-{claude,gpt,info}`, `.elevated` | `<div class="card"><div class="card-head"><span class="ttl">…</span></div><div class="card-body">…</div></div>` | Critique cards, timeline cards, item cards |
| `.tab` / `.tab-group` | `.phase-tab`, `.crit-filter-row`, `.kind-filter` | Nested structure: `<div class="tab-group"><button class="tab">…</button></div>` | Phase selector tabs, filter clusters |
| `.as` (AgentStrip) | `.as-timeline`, `.as-activity`, `.in-header` | `<div class="as as-timeline"><span class="ag-logo">…</span><span class="ag-model">…</span><span class="ag-tokens">…</span><span class="ag-cost">…</span><span class="ag-activity">…</span></div>` | Agent identity pill (Claude/GPT) in timeline, header, agent-bar |
| `.cs-*` (CollapsibleSection) | `.cs-open` | `<div class="cs-root"><button class="cs-toggle">…</button><div class="cs-body">…</div></div>` | Timeline phase disclosure, critique sections, How-It-Works sections |
| `.qthread` | (part of QuestionThread composite) | `.qthread-card` + `.qthread-bubble` + `.qthread-quote` | Question/disagreement thread rendering (spec 0097) |
| `.quote-callout` | (tinted by `.tone-*`) | `<div class="quote-callout tone-claude">…</div>` | Critique card quoted text callout |
| `.tl-*` (timeline) | `.tl-phase`, `.tl-turn`, `.tl-turn--open`, `.tl-card`, `.tl-card-head`, `.tl-card-head__right` | Per-phase: `<div class="tl-phase"><header>…</header><div class="tl-body">…</div></div>` | Timeline pane structure and turn cards |
| `.consumption-*` | `.consumption-row`, `.consumption-card`, `.consumption-bar`, `.consumption-legend` | `<div class="consumption-row"><div class="consumption-card">…</div></div>` | Token consumption visualization (spec 0100) |
| `.crit*` | `.crit2`, `.crit-card`, `.crit-card-head`, `.crit-filter-row`, `.crit-totals` | Per-phase: `<div class="crit2"><header class="bar1">…</header><header class="bar2 crit-filter-row">…</header><div class="crit-body">…</div></div>` | Critique pane two-bar header + body (spec 0098) |
| `.phase-rail-*` | `.phase-rail-root`, `.phase-rail-marker` | `<div class="phase-rail-root">{PHASES.map(p => <div class="phase-rail-marker">…</div>)}</div>` | Left-edge vertical phase navigator (spec 0066) |
| `.phase-progress` | `.phase-progress__seg` | `<div class="phase-progress">{PHASES.map(p => <span class="phase-progress__seg">…</span>)}</div>` | M3 segmented linear phase indicator (spec 0133) |
| `.round-scrubber-*` | `.round-scrubber-root`, `.round-scrubber-mark` | `<div class="round-scrubber-root">{rounds.map(r => <button class="round-scrubber-mark">…</button>)}</div>` | Inline round navigator in phase headers |
| `.md-modal-*` / `.dr-modal-*` | `.dr-modal-in` (animation) | `<div class="md-dialog dr-modal-root"><div class="dr-modal-scrim">…</div><div class="dr-modal-frame">…</div></div>` | Modal dialog with scrim, focus trap, M3 treatment |
| `.settings-*` | `.settings-input--search` | `<input class="settings-input--search" type="search">` | Settings / admin page inputs |
| `.dr-spinner` | (inline-styled sizing) | `<div class="dr-spinner" style="width: 28px; height: 28px; border-width: 2px;"></div>` | Loading spinner — three sizes via inline style |

---

## 3. Forbidden patterns (audit grep targets)

### Raw hex colors in JSX

**Pattern:** `#[0-9a-f]{3,8}` inside JSX `style={{ ... }}`

Acceptable in: CSS files only (via `--md-*` token consumption or explicit design decision documented via spec).

**Example violation:** `style={{ color: '#ffffff' }}` — must be `style={{ color: 'var(--md-on-surface)' }}`.

**Grep:** `grep -rn ":#[0-9a-f]" src/dual_research/ui/static/*.jsx`

### Raw rgb/rgba literals in JSX

**Pattern:** `rgba?\([0-9, .]+\)` or `rgb\([0-9, .]+\)` inside `style={{ ... }}`

Exception: Elevation shadows using raw `rgba(0,0,0,...)` recipes (those follow the `--md-elev-*` pattern and are pre-defined).

**Example violation:** `style={{ backgroundColor: 'rgba(212,165,116,0.08)' }}` — must use agent-color token or `color-mix(in srgb, var(...) N%, ...)`

**Grep:** `grep -rn "rgba?(" src/dual_research/ui/static/*.jsx | grep -v "elev\|md-elev"`

### Inline fontWeight as numeric

**Pattern:** `fontWeight: [0-9]{3}` (any 3-digit number like 400, 500, 600, 700)

**Example violation:** `style={{ fontWeight: 600 }}` — must be `style={{ fontWeight: 'var(--md-w-semi)' }}`

**Grep:** `grep -rn "fontWeight:\\s*[0-9]" src/dual_research/ui/static/*.jsx`

### Inline color / background as hex in JSX

**Pattern:** `color:.*#[0-9a-f]` or `background.*#[0-9a-f]` in `style={{ ... }}`

**Example violation:** `style={{ background: '#0d0f12' }}` — must be `style={{ background: 'var(--md-surface)' }}`

**Grep:** `grep -rn ":\s*['\"]#[0-9a-f]" src/dual_research/ui/static/*.jsx`

### Inline style={{ fontSize / padding / margin / gap / etc. }} with hardcoded px values

**Pattern:** `fontSize: "[0-9]+px"` or `padding: "[0-9]+px"` where a token exists

**Exception:** Deliberate micro-scale tweaks (9 px, 10.5 px, 1px adjustments) that don't fit M3 roles — those must be documented in a spec comment.

**Example violation:** `style={{ padding: '16px' }}` when component is inside a consistent spacing context — use `var(--md-sp-4)` instead.

**Grep:** `grep -rn "padding:\\s*['\"]?[0-9]+px" src/dual_research/ui/static/*.jsx | head -20`

### Inline border-radius with literal px or hardcoded 999px

**Pattern:** `borderRadius: "\\d+px"` or `border-radius: 999px;` in CSS

**Example violation:** `style={{ borderRadius: '12px' }}` — must be `style={{ borderRadius: 'var(--md-shape-md)' }}` or `.` CSS class

**Grep:** `grep -rn "borderRadius:\\s*['\"][0-9]" src/dual_research/ui/static/*.jsx` and `grep -rn "border-radius:\\s*999px" src/dual_research/ui/static/components.css`

### Inline font-family references to IBM Plex or custom legacy fonts

**Pattern:** `fontFamily: "IBM Plex"` or `font-family:.*IBM Plex` (retired in 0131)

**Pattern:** `fontFamily: ".*Mono"` or `fontFamily: ".*Serif"` (v1 aliases, should be `--md-font-*`)

**Grep:** `grep -rni "IBM Plex\|fontFamily.*Serif\|fontFamily.*Mono" src/dual_research/ui/static/*.jsx`

### Line-height raw numbers (should use `--md-*-lh` tokens)

**Pattern:** `lineHeight: [0-9.]+` (e.g., `lineHeight: 1.5` instead of `lineHeight: 'var(--md-body-m-lh)'`)

**Exception:** Common ratios (1, 1.2, 1.5) used in one-off contexts are acceptable if not repeatable.

**Grep:** `grep -rn "lineHeight:\\s*[0-9\.]" src/dual_research/ui/static/*.jsx`

### v1 token references (ALL now forbidden after spec 0131)

**Pattern:** `var(--bg-|--fg-|--border-|--r-|--t-|--mono|--sans|--serif|--w-)`

**Grep:** `grep -rn "var(--\(bg\|fg\|border\|r\|t\|mono\|sans\|serif\|w\)-" src/dual_research/ui/static/`

Result must be 0 matches everywhere.

### Hardcoded status colors that should use `--p-*` / `--ok/warn/err/info/idle`

**Pattern:** `#6fb380` or similar in JSX when a status token exists

**Example violation:** `style={{ color: '#d96a6a' }}` — must be `style={{ color: 'var(--err)' }}`

**Grep:** `grep -rn "#6fb380\|#d96a6a\|#d4a056\|#6b9cf0\|#5e636d" src/dual_research/ui/static/*.jsx`

---

## 4. Recommended replacement map

**If you find X (bespoke pattern), use Y (DS v2 equivalent):**

| Bespoke pattern | DS v2 equivalent | Context |
|---|---|---|
| Inline `style={{ color: '#...' }}` | `style={{ color: 'var(--md-on-surface)' }}` or agent/status token | Any JSX |
| Inline `style={{ background: '#...' }}` | `style={{ background: 'var(--md-surface-container)' }}` or appropriate tier | Any JSX |
| Raw `fontWeight: 400/500/600/700` | `fontWeight: 'var(--md-w-regular|medium|semi|bold)'` | JSX inline style |
| `fontSize: "14px"` | `.t-body-m` class or `fontSize: 'var(--md-body-m-size)'` | Type-role context |
| `padding: "16px"` | `padding: 'var(--md-sp-4)'` or `.md-pad-card` utility | Spacing context |
| `gap: "8px"` | `gap: 'var(--md-sp-2)'` | Flex/grid context |
| `border-radius: "12px"` | `border-radius: 'var(--md-shape-md)'` or `.md-shape-md` class | Any radius context |
| `border-radius: 999px` | `border-radius: 'var(--md-shape-full)'` or `.pill` class | Pill shapes |
| `color: 'rgba(0,0,0,0.12)'` | `color: 'color-mix(in srgb, currentColor 12%, transparent)'` or `--md-state-pressed` | State layer |
| Bespoke status pill | `.chip.tone-{ok,warn,err,info,idle}` + `.no-dot` | Status indicators |
| `fontFamily: var(--mono)` | `fontFamily: 'var(--md-font-data)'` | Data typography |
| `fontFamily: 'IBM Plex Sans'` | `fontFamily: 'var(--md-font-plain)'` | Any sans context |
| `fontFamily: 'IBM Plex Serif'` | `fontFamily: 'var(--md-font-brand)'` | Hero / quotes |
| Inline `style={{ box Shadow: '...' }}` | Use `.md-elev-{1,2,3,4,5}` class or `box-shadow: 'var(--md-elev-2)'` | Elevation |
| `line-height: 1.5` | `lineHeight: 'var(--md-body-m-lh)'` if applicable, else `.t-body-m` | Type role context |
| `letter-spacing: "..."` | Use `.t-title-m` / `.t-label-s` / etc. class which includes tracking | Type role context |

---

## 5. Audit classification rules

### ✅ **Compliant**

Element uses **only** M3 token variables or **only** DS-v2 component classes, with NO inline style overrides to bypass them.

**Indicators:**
- All colors via `var(--md-*)` or agent/status token
- All sizes via `var(--md-*-size)` or `.t-*` utility class
- All spacing via `var(--md-sp-*)` or `.md-pad-*` class
- All radius via `var(--md-shape-*)` or component base class
- All font via `var(--md-font-*)` with `font-weight: 'var(--md-w-*)'`
- All shadows via `var(--md-elev-*)` or elevation class
- Component structure matches documented `.md-*` anatomy

**Example:**
```jsx
<div className="card tone-info" style={{ padding: 'var(--md-sp-6)' }}>
  <h2 style={{ fontSize: 'var(--md-title-m-size)', fontWeight: 'var(--md-w-semi)', color: 'var(--md-on-surface)' }}>
    {title}
  </h2>
</div>
```

### ⚠️ **Token-drift**

Element uses a **correct DS-v2 component class** but has **inline style overrides** that:
- Hardcode colors instead of reading tokens
- Use wrong token for the context (e.g., `--md-on-surface-faint` for a heading instead of `--md-on-surface`)
- Hardcode spacing, radius, or sizing that contradicts the token layer

**Indicators:**
- `.card` + `style={{ color: '#ffffff' }}` (bypass via hex)
- `.chip` + `style={{ borderRadius: '8px' }}` (override radius via hardcoded px)
- `.tab` + `style={{ padding: '16px' }}` (override padding instead of consuming token)

**Fix:** Replace hardcoded value with appropriate `var(--md-*)` token.

### ❌ **Bespoke-bypass**

Element is **entirely custom** — not a documented DS-v2 component class — even though a **suitable component exists** in the catalog.

**Indicators:**
- Status indication via raw `<span style={{ color: '#6fb380' }}>✓</span>` when `.chip.tone-ok` exists
- Card via raw `<div style={{ border: '1px solid #...', borderRadius: '8px' }}>` when `.card` exists
- Type role via inline `style={{ fontSize: '14px', fontWeight: '600' }}` when `.t-title-m` exists
- Tab via custom `<button style={{ ... }}` when `.tab` class exists

**Fix:** Adopt the equivalent DS-v2 component. If the component's API is too rigid, file a follow-up to extend it — don't bypass.

### 🆕 **Gap-in-DS**

Element fills a **legitimate UI need** but has **no DS-v2 component** to cover it. The value is real; the token/component is missing.

**Indicators:**
- A new interactive pattern that doesn't fit any M3 primitive
- A specialized status indicator that needs its own tone vocabulary
- A layout pattern that requires new spacing / sizing conventions
- A text effect that needs new typography roles

**Action:** Flag for DS-v2 enhancement spec. Document the need in a follow-up PR comment. Meanwhile, the element is **acceptable as-is if it follows all token conventions** (uses `var(--md-*)` where tokens exist, documents its purpose in a comment).

**Example (acceptable gap):**
```jsx
<div className="custom-timeline-marker" style={{
  width: 'var(--md-sp-4)',
  height: 'var(--md-sp-4)',
  borderRadius: 'var(--md-shape-full)',
  backgroundColor: 'var(--md-tertiary)',
  // Custom: no M3 equivalent for timeline step indicator. See spec-0142 proposal.
}} />
```

---

## Summary

Use this rubric to classify every visual element on every page as one of the four verdicts. Each element should be independently auditable via:

1. **Is it using a `.md-*` or DS-v2 component class?** (Compliant / Token-drift / Bespoke-bypass)
2. **Are all token-consuming properties reading from `var(--md-*)`?** (If no → Token-drift)
3. **Does an equivalent DS-v2 component exist but isn't being used?** (If yes → Bespoke-bypass)
4. **Does this element fill a gap?** (If yes → Gap-in-DS; document why)

Audit agents must remain strict: every classification must be defensible via the rules above, not subjective aesthetics.

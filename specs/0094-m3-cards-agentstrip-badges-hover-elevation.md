---
spec: 0094
title: M3 cards + AgentStrip + badge inventory + hover elevation-2 rule + AgentStrip badge sizing/symmetry
label: bug
version-bump: PATCH
status: proposed
target-version: 0.72.3
created: 2026-05-19
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0094 — Cards, AgentStrip, badges + hover-elevation rule

> Ship bucket: **Primitives**
> Depends on: **0092, 0093**
> Complexity: **M**
> Targeted version bump: **PATCH** (bug-fix label resolves Issues 1 + 3-hover; not a new feature)

## 1. Goal

Replace the existing card / strip / badge anatomy with the M3 four
card variants (elevated · filled · outlined · agent-tonal), the
fixed-height AgentStrip primitive, and the full M3 badge inventory
(agent strip, qref, tone chip, phase chip, delta chip, drift chip).
Resolves Issue 1 (Claude vs GPT badge heights) and the hover-
elevation half of Issue 3 (hover lifts a card from elevation-1 to
elevation-2 in **both** the timeline and the critique sections —
but not on section headers).

After this spec, the run-detail right-cluster model badges read at
the same height, the AgentStrip primitive guarantees symmetry, and
the unified card hover rule is the single source of truth for the
timeline + critique elevation contract.

## 2. Files touched

- `src/dual_research/ui/static/components.css` — append the M3
  card block: `.md-card` base + `.md-card--{elevated,filled,outlined,tonal-a,tonal-b}`
  variants + `.md-card__hd`, `.md-card__title`, `.md-card__support`
  per [v2-m3.css:376-394](docs/design-system-v2/assets/styles/v2-m3.css);
  the AgentStrip primitive `.agent-strip` + `.agent-strip--{a,b}`
  + `.agent-strip .dot` per
  [v2-m3-page.css:117-128](docs/design-system-v2/assets/styles/v2-m3-page.css);
  the tiny `.ai` / `.ai-sm` / `.ai-{a,b}` agent-initial badge per
  [v2-m3-page.css:524-535](docs/design-system-v2/assets/styles/v2-m3-page.css);
  the qref pill family `.qref` + `.qref-k` + `.qref-by` + `.qref-by-n`
  + `.qref-round` + `.qref-sep` + `.qref[data-kind="Q|D|I|C"]`
  per [v2-m3-page.css:537-572](docs/design-system-v2/assets/styles/v2-m3-page.css);
  the `.delta-chip` (`+5 Q` / `−1`) per
  [v2-m3-page.css:595-605](docs/design-system-v2/assets/styles/v2-m3-page.css);
  the `.drift-chip` per
  [v2-m3-page.css:720-731](docs/design-system-v2/assets/styles/v2-m3-page.css);
  the `.bcard` badge-rich card container per
  [v2-m3-page.css:1055-1066](docs/design-system-v2/assets/styles/v2-m3-page.css).
  **New rule**: `.md-card[data-hoverable="true"]:hover { box-shadow:
  var(--md-elev-2); transition: box-shadow var(--md-dur-short-3)
  var(--md-easing-standard); }`. Card section headers (the
  `.tl-phase__hd`, `.crit-group__hd`, `.cr-group__hd`) never
  receive this attribute and so never lift.
- `src/dual_research/ui/static/shared.jsx` — refactor `Card`,
  `CardBody`, `AgentStrip`, `AgentIcon`, `QuestionRef`,
  `ChipCluster`, `RunIDChip`, `Pill` to the new class names.
  `Card` accepts a `hoverable` prop (default `false`) that sets
  `data-hoverable="true"` — Spec 0098 (critique) and Spec 0099
  (timeline) flip that to `true` on item cards but never on
  section headers. `AgentStrip` enforces a fixed 28 dp height and
  fixed 12 dp horizontal padding regardless of model-name length;
  any model name longer than the container truncates with
  `text-overflow: ellipsis` rather than pushing the height
  (Issue 1 resolution). Also export a new `<ModelBadge agent
  model={modelId} />` helper that renders a 56 dp tall right-
  cluster pill containing the AgentStrip + model id, with **both
  Claude and GPT pills rendered identically** — Issue 1's
  symmetry requirement.
- `src/dual_research/ui/static/run-detail.jsx` — refactor the
  right-cluster model badges (rendered around line 153
  `TimelineAgentPill`) to use `<ModelBadge />`. The two badges
  share a single CSS rule for height and horizontal padding;
  there is no per-agent override. Critique cards (around
  `CritiqueExplorer`, line 5700) wrap their item rows in `<Card
  hoverable variant="outlined" data-critique-status={…}>` so the
  hover-elevation contract fires (Issue 3-hover). Timeline turn
  cards (around `Timeline`, line 823, and `tlcard` renders inside
  it) similarly wrap each `.tl-turn` row in `hoverable` — the
  phase header `.tl-phase__hd` does NOT.
- `pyproject.toml` — `0.72.2` → `0.72.3`.

## 3. Material 3 anatomy

- `#cards` — four card variants (elevated · filled · outlined ·
  agent-tonal-a/b), shape-md (12 dp) corners, padding
  `--md-pad-card` (24 dp comfortable, 16 dp compact). Hover rule:
  elevation-1 → elevation-2 transition at
  `var(--md-dur-short-3) var(--md-easing-standard)`.
- `#elevation` — the hover transition is the single
  visible-interaction use of elevation-2 in the system; everything
  else (FAB, app bar, dialog) sits at its static elevation level.
- AgentStrip + badge inventory + qref family + delta chip + drift
  chip — all anchored in `#cards`.

Class-name contract (verbatim):

```
.md-card, .md-card--{elevated,filled,outlined,tonal-a,tonal-b}
.md-card__hd, .md-card__title, .md-card__support
.md-card[data-hoverable="true"]:hover  → elevation-1 → elevation-2

.agent-strip, .agent-strip--{a,b}, .agent-strip .dot
.ai, .ai-sm, .ai-{a,b}

.qref, .qref-k, .qref-n, .qref-sep, .qref-by, .qref-by-n, .qref-round
.qref[data-kind="Q|D|I|C"]

.delta-chip, .delta-chip .up, .delta-chip .down
.drift-chip
.bcard, .bcard__hd, .bcard__title, .bcard__body, .bcard__ft
```

## 4. Notion issues addressed

1. **Issue 1 — Model badges (Claude / GPT) have inconsistent
   heights.** Source: `docs/design-system-v2/notion-issues/screenshots/01-badge-heights.png`.
   The screenshot shows the Claude pill taller than the GPT pill
   because the `claude-sonnet-4-6` model name wraps and pushes
   the container upward; the GPT pill (`gpt-5.5`) is short and
   tight. Resolution: the new `<ModelBadge />` renders both at
   a fixed 56 dp height (M3 medium pill) with horizontal padding
   that fits the longest supported model name without wrapping.
   The model name truncates with ellipsis if a future name is
   longer than the pill width; height never changes.

2. **Issue 3 — Phase headers bigger than card headers + hover
   elevation on cards** (hover-elevation half).
   `docs/design-system-v2/notion-issues/screenshots/03-phase-headers-1.png`
   shows phase-0 cards at rest; the hover lift is the elevation
   contract. This spec adds the rule at the primitive level so
   it applies everywhere; Spec 0098 (critique) and Spec 0099
   (timeline) opt in by setting `hoverable` on item cards. The
   phase-header sizing half of Issue 3 is resolved in Spec 0098.

## 5. Acceptance criteria

- [ ] `<ModelBadge agent="claude" model="claude-sonnet-4-6" />`
      and `<ModelBadge agent="gpt" model="gpt-5.5" />` render
      with **identical height** (visually verified via DevTools
      computed style — both report 56 dp).
- [ ] The Claude model name `claude-sonnet-4-6` fits in the pill
      without wrapping at the default rail width; if forced
      narrower it truncates with ellipsis. Height stays 56 dp.
- [ ] Hovering an item card (timeline or critique) inside
      `#/runs/<id>` lifts the card from elevation-1 to elevation-2
      with a 150 ms transition. Hovering the phase section
      header (`.tl-phase__hd` / `.crit-group__hd`) does NOT lift.
- [ ] Hovering an agent-tonal card (claude or gpt) lifts the same
      way; the tonal background does not visually shift, only the
      shadow.
- [ ] AgentStrip renders identically tall regardless of model
      name length — feed it the longest realistic model name and
      verify the height is unchanged.
- [ ] `<QuestionRef id="Q-c-r1-04" />` renders `Q · 04`
      (compact) with kind colour-coded badge per the
      `qref[data-kind="Q"]` rule; never `C1` or other cryptic
      shorthand.
- [ ] All four card variants render correctly in dark and light;
      tonal-a uses `--md-primary-container` / `--md-on-primary-container`
      and tonal-b uses the secondary equivalents.

## 6. Visual verification matrix

- `2200×1300 dark` — route `#/runs/<latest>`; capture the
  run-detail header strip (both ModelBadges side by side) and
  the timeline pane at rest plus one card hovered.
- `2200×1300 light` — same.
- `1400×900 dark` — same route; verify ModelBadges still align
  and badge cluster wraps gracefully.
- `1400×900 light` — same.
- `820×1180 dark` — single-column collapse; ModelBadges stack
  vertically at identical width.
- `820×1180 light` — same.

All six required. Issue 1 is a regression-prone fix that needs
proof across every breakpoint.

## 7. Anti-pattern checks

- [ ] No cryptic IDs leaking the database — `QuestionRef` /
      `parseQId` are used wherever a q-id appears.
- [ ] No emoji as icons.
- [ ] No off-grid spacing — card padding reads `--md-pad-card`;
      AgentStrip height is 28 dp (M3 micro pill); ModelBadge is
      56 dp; gap inside `.bcard__hd` is 8 dp.
- [ ] No hex codes in component CSS.
- [ ] No per-theme overrides — agent-tonal cards read
      `--md-primary-container` / `--md-secondary-container` which
      already adapt to light/dark.
- [ ] Reduced-motion contract preserved — the hover-elevation
      `transition` becomes `none` under
      `prefers-reduced-motion: reduce`.
- [ ] Focus ring visible — `:focus-visible` outline on every
      interactive card (cards with `onClick` / `role="button"`).

## 8. Handover read

> *First task on running this spec: read `handoffs/<YYYY-MM-DD>-spec-0093-m3-atoms-buttons-chips-status-pills.md` end-to-end. (Created by the previous spec at its handover step — the queue convention.)*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that invalidates any acceptance criterion below, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift; this section is what makes that work.*

## 10. Backend touched?

**no.** Card / strip / badge anatomy is pure presentation. Issue 1
fix is a height contract on the AgentStrip + ModelBadge primitive,
not a model-id data shape change.

## 11. CSS class anchor list

```
.md-card                          → #cards (base)
.md-card--elevated                → #cards · #elevation (level-1 default; hover → level-2)
.md-card--filled                  → #cards (surface-container-high)
.md-card--outlined                → #cards (surface + 1 px outline)
.md-card--tonal-a, --tonal-b      → #cards (agent-tonal containers)
.md-card[data-hoverable="true"]:hover
                                  → #cards · #elevation (Issue 3 hover-lift rule)
.md-card__hd / __title / __support → #cards (anatomy)

.agent-strip / --a / --b           → #cards (badge inventory · AgentStrip)
.ai, .ai-sm, .ai-{a,b}             → #cards (initial badge)

.qref + family                     → #cards (decoded reference badge)
.delta-chip                        → #cards (turn deltas)
.drift-chip                        → #cards (run-wide drift indicator)

.bcard + family                    → #cards (badge-rich card composition)
```

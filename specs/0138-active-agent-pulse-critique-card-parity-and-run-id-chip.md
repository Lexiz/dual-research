---
spec: 0138
title: Active-agent gradient pulse · uniform critique card heights · run-id chip in header row 2
label: new-feature
version-bump: MINOR
status: ready
target-version: 1.9.0
created: 2026-05-21
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0138 — Active-agent gradient pulse, uniform critique card heights, run-id chip

> Ship bucket: **Run-detail polish — Timeline + Critique pane visual coherence + run-identity affordance.**
> Depends on: **0111** (`--dr-card-pad-*` tokens for unified card padding), **0119** (Critique card head anatomy + `.crit-card-id` introduction), **0124** (timeline / critique card height parity work), **0133** (`.as.in-header` AgentStrip placement in `.tl__head` / `.tl__tabs`, `composeAgentActivity` plumbing into the relocated chip).
> Complexity: **S** — four coordinated visual changes. CSS-heavy with one JSX line drop and one new chip in `RunDetailHeader`. No JS/contract/backend churn.
> Targeted version bump: **MINOR (1.7.x → 1.8.0)** — three of the four changes are user-visible polish; the run-id chip is additive. No behaviour contract changes.

---

## 1. Context

A live-mockup pass with the user during run `20260521-…-document-verification-service-…` (Document Verification Service · Backend Language Choice — the latest in-flight run) surfaced four coordinated changes to the run-detail surface. They cluster into three groups but share the same render path (CSS + a single JSX touch each), so one spec carries all four.

1. **The two `.as.in-header` AgentStrip badges (Claude in `.tl__head`, GPT in `.tl__tabs` — both placed by [spec 0133 §5.1](0133-run-detail-header-rework.md)) only signal "this model is busy doing something" through a 6 × 6 px dot that pulses inside their right cluster.** The dot lives at the far end of the right-side metrics row and is easy to miss in a crowded pane. The badge **itself** carries no signal of activity. When a round is in flight, the operator should be able to tell at a glance which model is currently doing work without scanning for the dot.
   - The existing `pulse-a` / `pulse-b` keyframes ([base.css:82-83](src/dual_research/ui/static/base.css)) ring the dot in an agent-tinted halo; the same halo applied to the full badge reads as a hard "alarm" pulse and competes with the in-pane activity-phrase animation. A gentler treatment is needed.
   - A side-by-side study of five candidate animations (soft halo pulse, gradient sweep, elevation breathing, border-tint glow, elevation + halo combination) was rendered against the real production Material 3 tokens in [`prototypes/active-agent-pulse/mockup.html`](../prototypes/active-agent-pulse/mockup.html). The user picked **Variant B — gradient sweep**: an agent-tinted soft-light gradient gently sweeps across the badge surface. The motion is felt before it's seen; it doesn't compete with the activity-phrase animation; it respects the M3 surface vocabulary (no new shadows, no scale, no translate); and it gracefully degrades to a static `surface-container-high` tint under `prefers-reduced-motion`.

2. **Critique-pane item cards (`QuestionThread`) render visibly taller than the timeline turn cards on the left side of the screen** even though both share the same `.qthread` shell and same `--dr-card-pad-*` padding tokens. The height difference traces to two sources:
   - `.qthread` has `gap: 12px` between children ([components.css:688](src/dual_research/ui/static/components.css)); `.qthread.tl-thread` (the timeline override) flattens that to `gap: 0` ([components.css:2305](src/dual_research/ui/static/components.css)). When a critique card is collapsed, that 12 px gap sits between the chip header and the next child.
   - The next child is `.crit-card-id` ([shared.jsx:1270](src/dual_research/ui/static/shared.jsx)) — a small mono line reading "id: D-plan-c-01" (or similar). It's always rendered when an id is present, in both the collapsed and expanded states.
   - Combined, every critique card carries `12 px gap + ~14 px crit-card-id + 2 px top padding` ≈ 28 px more vertical space than an equivalent timeline turn card. With ten or more cards stacked in the "Open · new this round" section, the cumulative height divergence pushes the critique pane noticeably past the timeline pane's content density at the same row count.
   - The id information itself is redundant: the `D` prefix is redundant with the Disagreement chip in the header, the agent suffix (`-c-` for Claude / `-g-` for GPT) is redundant with the leading agent icon chip, and the round counter is redundant with the "raised in r1" chip. The only unique fragment is the middle segment (`plan` — the phase the item originated from), and the surrounding `.crit-group` header (e.g. "Open · new this round · round 03") plus the Phase 2 / Phase 4 tab selection already disambiguate phase. Dropping `.crit-card-id` removes redundant signal and unlocks card-height parity in one move.

3. **The full run id (`20260521-103045-document-verification-service-backend-language-choice` or similar — produced by [`splitRunId`](src/dual_research/ui/static/live-data.jsx:440-445)) is not surfaced anywhere on the run-detail screen as a copyable affordance.** The 4-char hex prefix (`81cc`) is the only run identifier rendered in the run list, but the full session-directory name is what the operator needs to copy when referring to the run in chat, in commit messages, in `/dual-research-run`-replay invocations, or in `gh issue` filings. The two-row `RunDetailHeader` carries topic + cost + status badges in row 1 and phase progress + run metadata in row 2; row 2 is the natural home for a run-id affordance (it's already the "run-metadata row"), and the existing `.rid` chip primitive ([shared.jsx:844-852](src/dual_research/ui/static/shared.jsx), [components.css:280-296](src/dual_research/ui/static/components.css)) can carry it.

All four changes are CSS / JSX surface work. No protocol, queue, scheduler, contract, or backend touch.

---

## 2. Goals

1. **Variant B gradient sweep on active `.as.in-header` badges.** When `composeAgentActivity(agent, run).live` is true, the badge surface gently animates an agent-tinted soft-light gradient sweeping right-to-left, infinitely, over ~3.2 s. Both agents can be live simultaneously; their animations run with offset `animation-delay` so the two badges don't pulse in lockstep. When `live` is false, the badge has no animation and reverts to its current static `.as.in-header` treatment. Under `prefers-reduced-motion: reduce`, the live state degrades to a static `--md-surface-container-high` background tint so liveness stays legible without motion.

2. **Critique cards match timeline turn-card height when collapsed.** Drop the `.crit-card-id` line entirely from the `QuestionThread` markup. With `.crit-card-id` gone, the `gap: 12px` on `.qthread` (which only kicks in between children) is irrelevant for the collapsed state — the card has only one child (`.crit-card-head`), no gap applies, the card matches the timeline turn-card vertical footprint. The expanded state (gap applies between the header and the lifecycle/timeline body) is unchanged — the gap there is the desired visual separator between the header and the expanded sections. Net: collapsed critique cards become identical in height to collapsed timeline turn cards across all four kinds (Question · Disagreement · Issue · Comment).

3. **Run-id chip in `RunDetailHeader` row 2.** Add a new `.rid` chip rendering the full `run.id` to the run-metadata cluster on the right side of [`PhaseDotsRow`](src/dual_research/ui/static/run-detail.jsx:252-281). The chip is copyable on click (writes `run.id` to the clipboard, surfaces a brief tooltip confirmation), readable inline (font: existing `.rid` mono treatment), and sits to the *left* of the existing "started 01:06 · 9m 56s elapsed · round 0/6 (hard 12)" metadata so the visual hierarchy is **identity first → activity context second**. The chip stays at the row-2 height (28 px); it never grows the header row.

4. **No regressions on adjacent surfaces.** Phase-header chips, timeline turn cards, drafter callout pill, cost badge, reconcile chip, status/errors badge, search summary chip, M3 phase progress segments, conversation/consumption segmented tabs, and the Compare / Search / How-It-Works / Run-list pages all continue to render exactly as today. The four changes scope to: `.as.in-header.is-live`, `.qthread` (critique-pane variant only; the `.qthread.tl-thread` override is unchanged), and `RunDetailHeader` row 2.

The picked Variant B is visible in [`prototypes/active-agent-pulse/mockup.html`](../prototypes/active-agent-pulse/mockup.html) (the gradient-sweep block, second variant section). The user reviewed all five variants and committed to Variant B before this spec was written.

---

## 3. Non-goals

- **No change to `composeAgentActivity`** ([run-detail.jsx:53-92](src/dual_research/ui/static/run-detail.jsx)) — phrase logic and `live` derivation stay. The new gradient sweep listens to the same `live` boolean already plumbed into the chip.
- **No change to the inner activity dot** (`<Dot color={dotColor} pulse={live ? 'pulse-a' : null} size={6} />` at [run-detail.jsx:167](src/dual_research/ui/static/run-detail.jsx)). It keeps its existing dot-halo pulse — the new badge-level gradient is additive, not a replacement. The two animations run on different elements at different rhythms and read as one "this model is breathing" gesture in aggregate.
- **No change to `.as.in-header` layout, padding, font sizes, or min-width** ([components.css:363-378](src/dual_research/ui/static/components.css)). The gradient sweep is a pure overlay added via `::before`. The base `.as.in-header` rules are untouched.
- **No change to the non-`in-header` AgentStrip variants** (`.as.as-timeline`, plain `.as`). Those callsites continue to render exactly as today. The `is-live` class is only applied by `TimelineAgentPill` via its `className` prop, so it remains scoped to the timeline-header placement.
- **No change to `QuestionThread`'s expanded-state markup** ([shared.jsx:1275-1340](src/dual_research/ui/static/shared.jsx)) — lifecycle rows, source rows, footer, drift / resolved hints all unchanged. Only the always-rendered `.crit-card-id` div is removed.
- **No change to the `ReviewCard` id surface** (`.rp-item-card-id` at [run-detail.jsx:4828-4830](src/dual_research/ui/static/run-detail.jsx) + [components.css:3126-3131](src/dual_research/ui/static/components.css)). That's a different component (turn-modal review pane), the user is happy with it as-is, and the redundant-identifier argument doesn't apply at the same strength because the turn modal isn't grouped by phase-tab on entry. **Scope is critique-pane cards only.** If the operator later asks to harmonise, that's a follow-up spec.
- **No change to the run-id rendered elsewhere** (`run-list.jsx` two-line cell, the SSE-stream label at [run-detail.jsx:7227](src/dual_research/ui/static/run-detail.jsx), the error-banner `count` prop at [run-detail.jsx:7248](src/dual_research/ui/static/run-detail.jsx)). The new chip is an additional affordance, not a relocation of the existing copies.
- **No change to row 1 of `RunDetailHeader`.** The user explicitly preferred row 2 for the new chip ("probably in the second top bar, not in the first top bar"). The first row stays as Topic + CostBadge + ReconcileChip + RunSearchSummary + StatusErrorsBadge — unchanged.
- **No mobile / sub-900 px treatment.** Run-detail is desktop-only.
- **No new design tokens.** Every new colour reads from existing M3 / agent palette tokens (`--agent-a-rgb`, `--agent-b-rgb` added once if not present — see § 5.1).

---

## 4. Current-state audit

### 4.1 — Active-agent badges (Goal 1)

| Element | File | Lines | Current state |
|---|---|---|---|
| `<TimelineAgentPill>` JSX | [run-detail.jsx:152-188](src/dual_research/ui/static/run-detail.jsx) | 152–188 | Builds `<AgentStrip>` with `className="in-header"`. Right slot is `[Dot live=pulse-a/b][as-activity phrase]`. The `live` boolean derives from `composeAgentActivity(agent, run).live`. The chip element itself does NOT carry an `is-live` class today. |
| `.as.in-header` base CSS | [components.css:363-378](src/dual_research/ui/static/components.css) | 363–378 | `min-width: 600px; padding: 4px 24px; border-radius: var(--md-shape-full); background: var(--md-surface-container); border: 1px solid var(--md-outline-hair);` (last two inherited from base `.as`). Border-left tint comes from `.as.is-a` / `.as.is-b` (lines 320-321). |
| `pulse-a` / `pulse-b` keyframes | [base.css:82-91](src/dual_research/ui/static/base.css) | 82–91 | Halo box-shadow recipe at `2.2s ease-out infinite`. Applied to the 6 px dot via class on the `<Dot>` span. |
| `--agent-a` / `--agent-b` palette | [tokens.css:10-21](src/dual_research/ui/static/tokens.css) | 10–21 | Hex + dim + bg + bg-strong + border alphas; no `--agent-a-rgb` triple is published. Light-mode overrides at [tokens.css:301-307](src/dual_research/ui/static/tokens.css). |
| Reduced-motion contract | [base.css:121-131](src/dual_research/ui/static/base.css) | 121–131 | Global `*` selector zeros `animation-duration` + `transition-duration`. The existing `.pulse-a` / `.pulse-b` rules explicitly opt into `animation: none`. The new gradient must do the same. |

The `live` boolean is already in scope inside `TimelineAgentPill`; routing it onto the chip via an `is-live` class needs one line of JSX.

### 4.2 — Critique card height (Goal 2)

| Element | File | Lines | Current state |
|---|---|---|---|
| `QuestionThread` JSX | [shared.jsx:1128-1340](src/dual_research/ui/static/shared.jsx) | 1128–1340 | The `<article className="qthread is-{statusCss}">` body renders: header (chips) → `.crit-card-id` (if id present) → (open ? lifecycle + footer : nothing). Critically, `.crit-card-id` renders unconditionally on `{id && }` — i.e. always for items that have an id, regardless of open/closed state. |
| `.qthread` base CSS | [components.css:680-694](src/dual_research/ui/static/components.css) | 680–694 | `padding: var(--dr-card-pad-v) var(--dr-card-pad-h); display: flex; flex-direction: column; gap: 12px;` |
| `.qthread.tl-thread` override | [components.css:2298-2306](src/dual_research/ui/static/components.css) | 2298–2306 | `padding: var(--dr-card-pad-v) var(--dr-card-pad-h); margin: 0; gap: 0;` — gap flattened. |
| `.crit-card-id` CSS | [components.css:885-891](src/dual_research/ui/static/components.css) | 885–891 | `font-family: var(--md-font-data); font-size: 10.5px; color: var(--md-on-surface-faint); padding: 2px 0 0; user-select: text;` |
| `--dr-card-pad-v` / `-h` | [tokens.css:256-257](src/dual_research/ui/static/tokens.css) | 256–257 | `6px` / `12px` — shared across `.qthread` and `.tl-card`. |

When a `.qthread` is collapsed:
- Timeline (`.qthread.tl-thread`): the article contains just `.tl-card-head` (one child). With `gap: 0`, no inter-child gap applies. Card height = 6 + 6 + header content height = `12 + header`.
- Critique (`.qthread`, no override): the article contains `.crit-card-head` plus `.crit-card-id` (two children). With `gap: 12px`, a 12 px gap applies between them. Card height = 6 + 6 + header + 12 + (10.5px font + 2px top padding ≈ 14px) = `38 + header`.

Removing `.crit-card-id` collapses the gap (only one child remains → no gap engages) and removes the ~14 px id line. Net: **collapsed critique card height = `12 + header` = collapsed timeline card height.** No other CSS change needed.

### 4.3 — Run id surfacing (Goal 3)

| Element | File | Lines | Current state |
|---|---|---|---|
| `splitRunId` helper | [live-data.jsx:440-445](src/dual_research/ui/static/live-data.jsx) | 440–445 | Parses `20260521-103045-...` → `{ time: '10:30', slug: '...' }` |
| `RunIDChip` primitive | [shared.jsx:844-852](src/dual_research/ui/static/shared.jsx) | 844–852 | `<span className="rid">{id}</span>` with optional onClick — but currently used to render the 4-char hex prefix only. We extend it to render the full id (no API change). |
| `.rid` CSS | [components.css:280-296](src/dual_research/ui/static/components.css) | 280–296 | `height: 22px; padding: 0 10px; font-family: var(--md-font-plain); font-variant-numeric: tabular-nums; background: var(--md-surface-container); border: 1px solid var(--md-outline-hair); border-radius: var(--md-shape-full); font-size: var(--md-label-s-size); font-weight: var(--md-w-medium);` |
| `PhaseDotsRow` JSX | [run-detail.jsx:252-281](src/dual_research/ui/static/run-detail.jsx) | 252–281 | Row 2 layout: `[PhaseDots] [breadcrumb] [drafter pill] <spacer> [started · elapsed · round metadata]`. The new `.rid` chip sits in the right cluster, to the left of "started…". |
| `RunDetailHeader` row 1 | [run-detail.jsx:117-131](src/dual_research/ui/static/run-detail.jsx) | 117–131 | Topic + CostBadge + ReconcileChip + RunSearchSummary + StatusErrorsBadge. **Untouched.** |

The user noted ambiguity in their message about row 1 vs row 2 ("probably in the second top bar … Maybe also, as a batch in the right-hand corner [of row 1]"). The spec resolves to **row 2** based on the user's first phrasing ("probably the second top bar") and the semantic fit (row 2 is already the "run metadata" row). If row 1 is preferred at implementation review, swap by moving the JSX hunk from `PhaseDotsRow` to the row 1 `<div>` at [run-detail.jsx:120](src/dual_research/ui/static/run-detail.jsx) — pure JSX relocation, no CSS impact.

---

## 5. Proposed change

### 5.1 — Variant B gradient sweep on active `.as.in-header` (`run-detail.jsx` + `components.css` + `tokens.css`)

**Token addition** ([tokens.css](src/dual_research/ui/static/tokens.css), append immediately after the existing `--agent-a-border` / `--agent-b-border` definitions at lines 14 / 21):

```css
:root {
  /* Spec 0138 — RGB-triple variants of the agent palette. Needed by the
     `.as.in-header.is-live::before` gradient-sweep recipe, which uses
     `rgba(var(--agent-X-rgb), …)` to interpolate alpha at animation
     keyframes without committing to a static fill colour. Read by no
     other surface today; safe to add globally. */
  --agent-a-rgb: 212, 165, 116;
  --agent-b-rgb: 124, 196, 184;
}
```

(Both light and dark mode share the same RGB triples — only the surface
underneath changes; the gradient overlay reads identically on both.)

**JSX change** ([run-detail.jsx:177-186](src/dual_research/ui/static/run-detail.jsx) — `TimelineAgentPill` returns `<AgentStrip className={className} />`). The chip needs an `is-live` class when active. Two implementation options:

**Option A (recommended) — thread `live` into `className` at the call site.** Tiny, scoped, no API change to `AgentStrip`.

```jsx
// run-detail.jsx — TimelineAgentPill
return (
  <AgentStrip
    agent={slot}
    name={meta.name}
    model={modelId}
    tokens={totalTokens}
    cost={cost}
    costFormatter={fmt.costShort}
    right={activityRight}
    className={_cn(className, live && 'is-live')}
  />
);
```

(`_cn` is already imported from `shared.jsx`; check the existing imports at the top of `run-detail.jsx` and add it to the list if not already there.)

**Option B — add a `live` prop to `AgentStrip`** and append `is-live` to its internal classlist. Wider blast radius (every AgentStrip consumer would now have a `live` prop); only worth it if other surfaces need the same treatment. Recommend A.

**CSS change** ([components.css](src/dual_research/ui/static/components.css) — append immediately after the existing `.as.in-header` block at line 378):

```css
/* Spec 0138 — Variant B gradient sweep on active `.as.in-header`.
   Signals "this agent is currently doing work in the active round" by
   gently sweeping an agent-tinted soft-light gradient across the badge.
   The sweep is felt before it's seen: the gradient peak peaks at 18%
   alpha against the surface-container background, which on both the
   dark (#14171c) and light (#e8dec9) variants reads as a subtle warmth
   rather than as an explicit colour change.

   Why this recipe (vs the existing pulse-a/b halo on the dot):
   - The halo applied to the full badge reads as a hard alarm pulse and
     competes with the in-pane activity-phrase dot pulse.
   - A surface sweep avoids the halo's outward-pressure feel — the
     badge stays the same size at all keyframes; only the surface
     texture animates.
   - No new tokens, no new shadows, no translate / scale. Lives entirely
     in the surface-color space.

   The agent identity comes from `--agent-{a,b}-rgb` published in
   tokens.css (spec 0138 §5.1 token addition). Phase offset is set
   per-agent via animation-delay so two simultaneously-live agents
   don't pulse in lockstep. */
.as.in-header {
  /* Required for the absolutely-positioned ::before overlay to clip to
     the pill's rounded edge. */
  overflow: hidden;
  position: relative;
}
.as.in-header::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  z-index: -1;
  opacity: 0;
  background: linear-gradient(
    100deg,
    transparent 35%,
    rgba(var(--agent-rgb, 255, 255, 255), 0.18) 50%,
    transparent 65%
  );
  background-size: 220% 100%;
  background-position: 100% 0;
  transition: opacity 200ms ease;
}
.as.in-header.is-a { --agent-rgb: var(--agent-a-rgb); }
.as.in-header.is-b { --agent-rgb: var(--agent-b-rgb); }
.as.in-header.is-live::before {
  opacity: 1;
  animation: as-pulse-sweep 3.2s ease-in-out infinite;
}
/* When both agents are live simultaneously, offset the GPT animation
   so the two badges don't sweep in lockstep — sympathetic motion, not
   synchronised. The negative delay starts the animation mid-cycle on
   mount. */
.as.in-header.is-b.is-live::before { animation-delay: -1.6s; }

@keyframes as-pulse-sweep {
  0%   { background-position: 100% 0; }
  50%  { background-position: 0%   0; }
  100% { background-position: 100% 0; }
}

/* Reduced-motion contract — degrade to a static tint so liveness stays
   legible without motion. The base.css global @media block already zeros
   animation-duration on `*`, which would freeze the gradient at its
   starting position (transparent on the right) and effectively hide
   the signal entirely. Override here with an explicit non-animated
   background. */
@media (prefers-reduced-motion: reduce) {
  .as.in-header.is-live::before {
    animation: none;
    opacity: 0;
  }
  .as.in-header.is-live {
    background: var(--md-surface-container-high);
  }
}
```

(The `z-index: -1` on `::before` plus `isolation: isolate` is implicit because `.as.in-header` already establishes a stacking context via `border-radius` + `overflow: hidden`. Verify in DevTools that the agent border-left stripe at lines 320-321 still reads above the gradient — it should, because the stripe is rendered as a CSS border on the parent, not as a child element.)

### 5.2 — Critique card height parity — drop `.crit-card-id` (`shared.jsx` + `components.css`)

**JSX change** ([shared.jsx:1267-1270](src/dual_research/ui/static/shared.jsx)):

```diff
-      {/* Spec 0119 §8.4 — public ID renders as small mono inline text,
-          not as a chip in the header. Always visible (collapsed or
-          expanded) so it's copyable. */}
-      {id && <div className="crit-card-id">id: {id}</div>}
+      {/* Spec 0138 — the public ID is fully redundant with the
+          surrounding chip cluster: the `D`/`Q`/`I`/`C` prefix duplicates
+          the category chip, the `-c-` / `-g-` suffix duplicates the
+          provider icon chip, the trailing round counter duplicates the
+          `raised in r{N}` chip, and the phase fragment (`plan` / `draft`)
+          is disambiguated by the surrounding `.crit-group` header and
+          the Phase 2 / Phase 4 tab. Dropping the id line lets every
+          critique card collapse to the same vertical footprint as a
+          timeline turn card (Notion issue: critique pane reads visibly
+          taller than the timeline pane at the same item count). The
+          id remains addressable through the `{item.id}`-bearing key on
+          the article element if a future feature needs it in DOM.
+        */}
```

**CSS — `.crit-card-id` rule cleanup** ([components.css:885-891](src/dual_research/ui/static/components.css)). With no callers left, the rule is dead. Two options:

- **Option A (recommended)** — delete the rule outright. Single-spec lifecycle: removed in one commit. The selector has zero matches in the rest of the codebase (grep `crit-card-id` → only the deleted line and this CSS block).
- **Option B** — leave the rule as documentation of historical intent. Costs ~80 bytes minified.

Recommend A; cleaner diff and the spec block above explains why the class is gone.

**No change to `.qthread` `gap: 12px`.** With only one child in the collapsed state, the gap is inert. When the card is expanded and the lifecycle / sources sections render, the gap correctly separates the header from the expanded body — which is the desired visual behaviour. The `tl-thread`-style `gap: 0` is **not** copied over; the timeline override is for the timeline's tighter padding contract.

### 5.3 — Run-id chip in `RunDetailHeader` row 2 (`run-detail.jsx`)

**JSX change** ([run-detail.jsx:252-281](src/dual_research/ui/static/run-detail.jsx) — `PhaseDotsRow`).

The chip mounts in the right-side cluster, immediately to the left of the existing `started … elapsed … round …` mono metadata. Existing import: `RunIDChip` is already exported from `shared.jsx:1610` — add it to the `run-detail.jsx` import list if not already present (currently imports a curated subset).

```jsx
function PhaseDotsRow({ run, startedClock, elapsedLabel }) {
  // Spec 0138 — click-to-copy handler for the run-id chip. Mirrors the
  // pattern used in run-list.jsx's run-id rendering (see app.jsx:336
  // for the `splitRunId` helper). The toast surface is the existing
  // `aria-live` polite region (TBD — if none exists, fall back to a
  // `title` tooltip change as confirmation; the user explicitly OK'd
  // a low-fi confirmation in conversation).
  const [copied, setCopied] = React.useState(false);
  const copyRunId = (e) => {
    e.stopPropagation();
    if (!run.id) return;
    navigator.clipboard?.writeText(run.id).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    });
  };

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      paddingTop: 2,
    }}>
      <PhaseDots run={run} />
      <span className="mono" style={{
        fontSize: 9.5, color: 'var(--md-on-surface-faint)', letterSpacing: '0.03em',
      }}>
        preflight · drafts · negotiate · drafting · review
      </span>
      {run.drafter && <DrafterCalloutPill drafter={run.drafter} />}
      <span style={{ flex: 1 }} />

      {/* Spec 0138 — full run id, copyable. Sits to the LEFT of the
          existing started/elapsed/round metadata so the visual hierarchy
          reads identity first → activity context second. */}
      <RunIDChip
        id={run.id}
        onClick={copyRunId}
        title={copied ? 'copied!' : `${run.id} — click to copy`}
      />

      <span className="mono" style={{
        fontSize: 10.5, color: 'var(--md-on-surface-faint)',
        whiteSpace: 'nowrap',
      }}>
        started <span style={{ color: 'var(--md-on-surface-variant)' }}>{startedClock}</span>
        &nbsp;·&nbsp;<span style={{ color: 'var(--md-on-surface-variant)' }}>{elapsedLabel}</span> elapsed
        {run.status === 'running' && (run.phase === 2 || run.phase === 4) && run.round && (
          <>&nbsp;·&nbsp;round <span style={{ color: 'var(--md-on-surface-variant)' }}>
            {run.round.current}/{run.round.soft}
          </span><span style={{ color: 'var(--md-on-surface-faint)' }}>&nbsp;(hard {run.round.hard})</span></>
        )}
      </span>
    </div>
  );
}
```

**No CSS change.** The existing `.rid` rule sizes the chip at the 22 px height that already fits within the row-2 vertical contract. The `.rid` chip natural width grows with `run.id` length (e.g. ~42 chars at the long end → ~360 px); the row has flex spare capacity because Row 2 currently has only the breadcrumb + drafter pill on the left and the started/elapsed metadata on the right. If at very narrow viewports the row wraps, **the wrap is acceptable** — Row 2 is metadata, not chrome; a 2-line metadata row is fine. If the operator hates the wrap, a follow-up can collapse the breadcrumb labels (`preflight · drafts · negotiate · drafting · review`) below a width threshold.

### 5.4 — Cache bust

Bump the static-asset query string in [`app.jsx`](src/dual_research/ui/static/app.jsx) to `?v=0138a`. Same convention as spec 0133 §5.10.

---

## 6. Visual references

The picked Variant B gradient sweep is rendered in [`prototypes/active-agent-pulse/mockup.html`](../prototypes/active-agent-pulse/mockup.html) — the second variant section, titled "Variant B · Gradient sweep". The mockup renders against the real production Material 3 tokens (the page inlines the v1.7.x token block from `tokens.css`) and reproduces the `.tl__head` / `.tl__tabs` / `.as.in-header` markup verbatim, so what the user reviewed is what ships.

To re-open the mockup:

```bash
open prototypes/active-agent-pulse/mockup.html
# or
python3 -m http.server 8765 --bind 127.0.0.1 --directory prototypes/active-agent-pulse
# → http://127.0.0.1:8765/mockup.html
```

The mockup carries:
- Dark / light theme toggle (top-left toolbar)
- Reduced-motion preview toggle (top-left toolbar) — simulates `prefers-reduced-motion: reduce` without changing the OS setting
- Two configurations per variant: "one agent active" and "both active" so the offset-phase behaviour is visible

The implementer should produce side-by-side before/after screenshots (wide viewport, light + dark mode, both `one active` and `both active`) and attach to the PR per spec 0124 / 0133 precedent.

---

## 7. Out of scope (additions to §3)

- **The `RunIDChip` primitive's onClick contract.** The chip currently accepts an optional `onClick` but doesn't carry copy-to-clipboard semantics by default. Spec 0138 §5.3 wires the copy handler at the call site, not in the primitive. If multiple surfaces want copyable run-ids in the future, a follow-up can lift the handler into `RunIDChip` as a `copyable` prop. Not in this spec.
- **A toast / snackbar for the copy confirmation.** The current copy-success affordance is the `title` attribute swap ("copied!" for 1.4 s). Material 3's full snackbar primitive isn't introduced here — the title swap is sufficient for a low-frequency action. If the user reports that the confirmation feels invisible, a follow-up adds an M3 snackbar to the design system.
- **Critique card expand/collapse animation.** Not affected by §5.2; the `.qthread` transition for `box-shadow` on hover (line 689) stays. No new card transitions added.
- **Phase chip on critique cards** (`showPhaseChip={false}` at the CritiqueExplorer callsite — [run-detail.jsx:6148](src/dual_research/ui/static/run-detail.jsx)). That behaviour is unchanged. The card knows its phase from the surrounding `.crit-group` header.
- **Run-id chip on the run-list page.** The run list already renders a two-line cell with the time + slug ([run-list.jsx:410](src/dual_research/ui/static/run-list.jsx)). Not touched.
- **Variant B gradient outside the timeline-header placement.** The animation is keyed to `.as.in-header.is-live` only. Plain `.as` chips, `.as.as-timeline` chips (now unused per spec 0133 follow-up), and `.agent-strip` (the M3 `.agent-strip--{a,b}` modifier used by `ModelBadge` at [shared.jsx:921-940](src/dual_research/ui/static/shared.jsx)) are out of scope.

---

## 8. Test plan

- [ ] **Variant B — wide viewport (≥ 1800 px) — both agents active.**
  - [ ] Open a running run mid-Phase-2 (or use the in-flight run referenced in §1 once the next run starts).
  - [ ] Visually confirm both `.as.in-header` badges show a gentle right-to-left agent-tinted gradient sweep over their full surface.
  - [ ] DevTools: confirm the Claude badge has `is-a is-live` classes and the GPT badge has `is-b is-live`.
  - [ ] DevTools: confirm `::before` carries the `as-pulse-sweep` animation and the GPT badge's `::before` has `animation-delay: -1.6s` (sympathetic phase offset).
  - [ ] Visually confirm the inner activity dot (the 6 px dot in the right cluster) still pulses with its existing `pulse-a` / `pulse-b` halo — the badge-level gradient is additive.
  - [ ] Visually confirm the agent border-left tint stripe (`.as.is-a` / `.as.is-b` at components.css:320-321) still reads above the gradient overlay.
- [ ] **Variant B — single agent active.**
  - [ ] During Phase 1 (parallel drafts) confirm the appropriate single agent badge pulses while the other sits at the static `.as.in-header` baseline (no `is-live` class, no gradient).
  - [ ] Toggle agent activity by waiting for a turn boundary; confirm the gradient appears / disappears on the correct badge without a layout shift (the `::before` overlay uses `position: absolute`, so the parent height is unchanged).
- [ ] **Variant B — completed run.**
  - [ ] Open a completed run. Neither badge should carry `is-live` or animate.
- [ ] **Variant B — reduced motion.**
  - [ ] In DevTools rendering panel toggle `prefers-reduced-motion: reduce`.
  - [ ] Visually confirm both live badges show a static `surface-container-high` background tint (slightly elevated relative to surface-container) and no gradient animation.
  - [ ] Confirm the agent identity is still legible — the static tint plus the agent border-left stripe carries the active state.
- [ ] **Variant B — light mode parity.**
  - [ ] Toggle to light mode (`/theme` skill / `.light` body class). Confirm the gradient reads on the cream background — the 18% alpha agent tint creates a subtle warm patch without overpowering.
  - [ ] Confirm the reduced-motion fallback also reads on cream (the `--md-surface-container-high` light-mode value is `#e0d4bc`, which contrasts adequately against the row's `--md-surface-container` `#e8dec9`).
- [ ] **Critique card height parity.**
  - [ ] Open a run with critique items in Phase 2 (any post-round-1 negotiate).
  - [ ] Visually confirm the collapsed Questions / Disagreements / Issues / Comments cards in the critique pane render at the same vertical height as collapsed turn cards in the timeline pane.
  - [ ] DevTools: measure card heights (e.g. inspect `.qthread` and `.qthread.tl-thread`). They should agree to within 1 px.
  - [ ] Confirm `<div className="crit-card-id">` is not present in the DOM anywhere (grep DevTools tree).
  - [ ] Expand a card; confirm the lifecycle / sources / footer sections still render with appropriate spacing (the `gap: 12px` on `.qthread` engages between header and expanded body — that's desirable).
  - [ ] Confirm card heights are uniform across kind (Question vs Disagreement vs Issue vs Comment) and across phase (Phase 2 vs Phase 4 vs Σ Summary). The kind tone (info/warn/err/idle) only affects border-left tint, not height.
- [ ] **Run-id chip — wide viewport.**
  - [ ] On `RunDetailHeader` row 2, confirm the chip renders to the left of the "started 01:06 · 9m 56s elapsed · round …" metadata, using the existing `.rid` styling.
  - [ ] Hover the chip; confirm the tooltip reads the full run id (or `"<id> — click to copy"`).
  - [ ] Click the chip; confirm `run.id` is on the clipboard (paste into terminal or another field to verify).
  - [ ] Visually confirm the tooltip swaps to "copied!" for ~1.4 s and reverts.
- [ ] **Run-id chip — narrow viewport (≤ 1499 px).**
  - [ ] Resize. Confirm row 2 still fits or wraps to two lines without overlapping the row 1 chrome or being clipped.
  - [ ] If the row wraps, confirm the wrap is acceptable (each line still readable, metadata cluster stays right-aligned).
- [ ] **No regressions.**
  - [ ] Run list page: confirm the existing 4-char hex prefix renders unchanged.
  - [ ] Compare page: confirm no chip animates inappropriately.
  - [ ] How-it-works / changelog / settings pages: confirm no new animation appears anywhere outside `.as.in-header`.
  - [ ] ReviewCard turn-modal items (Phase 4): confirm `.rp-item-card-id` still renders (out-of-scope, unchanged).
- [ ] **Pytest / type-check suite.**
  - [ ] `uv run pytest tests/ -q` passes.
  - [ ] No frontend type-checker is configured today; manual JSX import audit covers the same ground.
- [ ] **Cache bust.**
  - [ ] After deploy, hard-reload the run-detail page; confirm the new gradient renders and the run-id chip is present (i.e. the `?v=0138a` cache-bust took effect).

---

## 9. Risks

- **Gradient overlay competing with the inner dot pulse.** Both animations now run on overlapping space inside the same badge. The mockup pass with the user concluded they read as one "this model is breathing" gesture — but on a long-running real run with a busy phrase ("negotiating · round 03"), the combination might feel noisy. **Mitigation:** the gradient is keyed off `.as.in-header.is-live`, which is set by exactly the same `live` boolean that controls the dot pulse, so toggling the inner dot off (by removing the `pulse-a` class from `<Dot>` at run-detail.jsx:167) is a one-line follow-up if needed. Don't preemptively remove — the user signed off on both running together.
- **`overflow: hidden` clipping the ring focus state.** The base `.as` does not currently set `overflow`. Adding `overflow: hidden` to `.as.in-header` (§5.1) clips child elements at the pill border. The badge has no children that extend past its border in normal use (logo, model, tokens, cost, activity — all sit inside), but a future focus-ring treatment that extends outside the pill would be clipped. **Mitigation:** the only outside-pill focus treatment in the design system today is `--md-focus-ring` which uses `outline`, not `box-shadow` — and `outline` is not clipped by `overflow: hidden` (CSS-level fact). Acceptable.
- **`.crit-card-id` removal might break a search/find feature that targets the rendered id text.** Grep confirms no other code reads the `.crit-card-id` class or scrapes the rendered "id: X" text. The id is still passed as the React `key` on the article and is recoverable from the item data structure. **Mitigation:** if a regression surfaces, the line can be re-added at the bottom of the expanded section (only visible when card is open) — a far smaller height impact than the always-rendered current placement.
- **Run-id chip natural width at long slugs.** Run ids can be 50+ chars (`20260520-170146-document-verification-service-backend-language-choice`). The chip will be ~430 px wide in that worst case, which pushes Row 2 toward wrap. **Mitigation:** acceptable per §5.3. If wrap is unacceptable, a follow-up can either truncate with ellipsis (`max-width: 280px; overflow: hidden; text-overflow: ellipsis;` on the `.rid` chip — but that breaks the click-to-copy intent since the user can't see what they're copying) or use a "Copy run id" button that copies but doesn't display the full id inline.
- **`navigator.clipboard.writeText` not available in non-HTTPS contexts.** The hosted run-detail page is served from `fly.dev` over HTTPS; the local dev server runs over `http://localhost:…`. On HTTP localhost the clipboard API is gated by the secure-context rule, which most browsers extend an exception to for localhost. **Mitigation:** if testing reveals the clipboard is unavailable, fall back to selecting the chip's text content (via `Range` / `Selection`) so the user can `Cmd+C` themselves. Defer until the gap appears in practice.
- **Cache bust forgotten.** Repeat of spec 0133's risk — without the `?v=` bump users see stale CSS and the changes don't appear. Test plan covers it explicitly.

---

## 10. Open questions

- **§5.1 placement** — the gradient sweep is keyed off `.as.in-header.is-live`. The chip could equally carry `data-live="true"` for cleaner CSS-attribute selection (`.as.in-header[data-live="true"]::before { … }`). Class is more idiomatic with the rest of the codebase (`is-a` / `is-b` / `is-open` / `is-active` are the existing patterns) — recommend class. Decide at implementation.
- **§5.3 chip placement — row 2 vs row 1.** The spec resolves to row 2 based on the user's first phrasing. If implementation review prefers row 1 (next to CostBadge), it's a JSX hunk relocation — no CSS change. Confirm before merging.
- **§5.3 copy-confirmation affordance.** Currently a `title`-attribute swap to "copied!" for 1.4 s. A small toast / snackbar would be more discoverable. Decide whether to invest in the toast pattern as part of this spec or punt to a future design-system addition.
- **§5.4 cache-bust suffix convention.** Spec 0133 used `?v=0133a`. This spec proposes `?v=0138a`. If a single bump should cover multiple specs in flight, coordinate at implementation time.
- **Dot pulse — keep or drop after this spec?** The inner activity dot's halo pulse becomes somewhat redundant once the full badge pulses via the gradient. The user said keep both for now (mockup pass). Revisit if the combination reads noisy in production.

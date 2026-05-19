---
spec: 0105
title: M3 chrome + run-detail header JSX wiring (plus restore live agent strip dropped by spec 0099)
label: bug
version-bump: PATCH
status: proposed
target-version: 0.76.2
created: 2026-05-19
pr: ""
---

# Spec 0105 — M3 chrome + run-detail header JSX wiring

> Ship bucket: **Cleanup / post-arc correction**
> Depends on: 0092 (tokens), 0094 (cards/AgentStrip CSS), 0095 (md-appbar CSS), 0099 (timeline rework)
> Complexity: **S**
> Targeted version bump: **PATCH** (bug — closes three visible regressions)

## 1. Goal

Three concrete defects survived the 0093 → 0104 autonomous arc.
Two are partial migrations — specs 0094/0095 added the M3 CSS but
never refactored the inline-styled JSX wrappers to USE the new
classes, so the page kept rendering with v1 inline styles. One is
a true regression — spec 0099's timeline rework dropped every call
site of `TimelineAgentPill` without putting an equivalent in the
new layout, so the live agent strip just disappeared.

After this spec lands, on `/#/runs/<id>`:

- The top chrome (All runs · Compare · Search · v0.76.x · How it
  works · theme toggle) renders inside `<header class="md-appbar">`
  with M3 surface-container-low + outline-hair tokens — no inline
  `var(--bg-*)` / `var(--border-*)` on the outer wrapper.
- The "Partner Vetting — Architecture Proposal" sub-header
  renders inside `<header class="run-detail__head">` with M3
  surface-container + outline-hair tokens — no inline v1 tokens
  on the outer wrapper.
- The Claude + GPT live agent strip is visible again above the
  timeline pane, using the existing `AgentStrip` class (`.as`,
  `.is-a` / `.is-b`) — one strip per agent with model id, token
  count, cost, and the live-activity sentence the v1 layout had
  before spec 0099 dropped it.

This is the smallest possible fix that restores visual continuity
with the Critique pane (specs 0098 + 0099 already landed cleanly
on the right side of the page).

## 2. Files touched

Group by file, one-line summary of what changes:

- `src/dual_research/ui/static/app.jsx` — `ChromeBar`
  (lines 237-291): replace the outer `<div style={{ height: 44,
  background: 'var(--bg-0)', borderBottom: '1px solid
  var(--border-1)', … }}>` with `<header className="md-appbar">`.
  The `.md-appbar` CSS already exists in components.css from spec
  0095; this commit wires it. Drop the inline `height`,
  `background`, `borderBottom`, `paddingLeft`, `gap` — they're
  baked into `.md-appbar`. Keep the `display: flex`, `alignItems`
  on the class. Leave inner `Tab` and `RightCluster` as-is.
- `src/dual_research/ui/static/run-detail.jsx` — `RunDetailHeader`
  (lines 103-147): replace the outer `<header style={{ display:
  'flex', flexDirection: 'column', padding: '12px 20px',
  borderBottom: '1px solid var(--border-1)', background:
  'var(--bg-0)', flexShrink: 0, gap: 6 }} data-tour-anchor="run-
  detail-header">` with `<header className="run-detail__head"
  data-tour-anchor="run-detail-header">`. The `data-tour-anchor`
  attribute MUST survive — spec 0103's onboarding tour anchors on
  it. The two child rows (Row 1 with Topic/CostBadge/etc., Row 2
  PhaseDotsRow) keep their existing inline styles for now — those
  drain in a follow-up spec.
- `src/dual_research/ui/static/run-detail.jsx` — `RunDetail`
  (the function that renders the run-detail page; find the call
  site of `RunDetailHeader` and add a sibling `<TimelineAgentBar
  run={run} />` immediately after the header and before the main
  two-pane split. The new `TimelineAgentBar` lives in the same
  file, renders `<div className="agent-bar"><TimelineAgentPill
  agent="claude" run={run} /><TimelineAgentPill agent="gpt"
  run={run} /></div>`, and the existing `TimelineAgentPill`
  function at line 153 is its only reader. Do **not** rewrite
  `TimelineAgentPill` — the v1 implementation already builds
  the right `AgentStrip` markup; spec 0099 just lost the call
  site.
- `src/dual_research/ui/static/components.css` — add a `.run-
  detail__head` rule block: M3 surface-container-low background,
  outline-hair bottom border, 12px / 20px padding (matches the
  v1 inline values verbatim), `flex-direction: column`, `gap:
  var(--md-sp-1)` (6px), `flex-shrink: 0`. Add a `.agent-bar`
  rule block: M3 surface-container background, outline-hair
  bottom border, two-column flex with `gap: var(--md-sp-6)`,
  `padding: var(--md-sp-2) var(--md-sp-5)`, `flex-shrink: 0`.
  Both rules respect the existing `body.light` override surface.
- `pyproject.toml` — bump `version = "0.76.1"` → `"0.76.2"`. Label
  is `bug` so the bump is PATCH.
- `src/dual_research/__init__.py` — bump `__version__ = "0.76.1"`
  → `"0.76.2"` so `/api/health` reports the new version after
  fly deploy.

Notably **not** touched in this spec: anything inside the Critique
pane, the Timeline pane internals (`.tl-phase`, `.tl-turn`,
`.tl__rail`), the run-list page, the consumption pane, the
onboarding tour. Those either already landed cleanly or are out of
scope for this correction.

## 3. Material 3 anatomy

Anchors implemented in this spec, with the canonical reference
file inlined as a pointer:

- `#system` — `.md-appbar` is the canonical M3 top-app-bar
  primitive. CSS already in
  [components.css](src/dual_research/ui/static/components.css)
  from spec 0095. This spec just wires the JSX.
- `#surfaces` — `.run-detail__head` reads
  `--md-surface-container-low` (so it sits one elevation level
  above the page surface) and `.agent-bar` reads
  `--md-surface-container` (one level above that). Mirrors the
  layered-surface pattern used by the Critique pane's `.bar1` /
  `.bar2` (see [run-detail.jsx:5938+5977](src/dual_research/ui/static/run-detail.jsx:5938)).
- `#elevation` — neither new surface adds a shadow; both use the
  hairline outline + a slightly lifted surface tier for separation
  (same pattern as `.tl__head`).

Exact CSS class anchors introduced (new selectors only — the
JSX wiring of existing classes doesn't introduce anchors):

```
.run-detail__head                → #surfaces (page sub-header surface)
.agent-bar                       → #surfaces (live agent strip surface)
```

`.md-appbar` and `.as` already exist; this spec wires their JSX.

## 4. Notion issues addressed

None directly. This is queue-debt cleanup from the autonomous
0093 → 0104 arc. The original Notion issues that 0094/0095/0099
were meant to close were marked resolved by those specs; this
spec closes the visible gap between what those specs promised and
what they shipped.

## 5. Acceptance criteria

> **DOM-level assertions, not just "renders without errors."** Each
> criterion is a fact about the rendered DOM at
> `http://127.0.0.1:6173/#/runs/20260516-035048-partner-vetting-
> arch-critique` (the canonical fixture, display id `3a4a`). This
> shape is what the 0093 → 0104 arc's verify steps missed.

- [ ] `document.querySelector('.md-appbar')` returns a non-null
      element whose computed `background-color` matches
      `getComputedStyle(document.body).getPropertyValue('--md-
      surface-container-low')` (i.e. the M3 class is applied and
      the M3 token resolves).
- [ ] `document.querySelector('header[data-tour-anchor="run-
      detail-header"]').classList.contains('run-detail__head')`
      is true. The element's outer `style` attribute is empty
      (inline styles dropped).
- [ ] `document.querySelectorAll('.agent-bar .as').length === 2`
      — one AgentStrip for Claude (`.is-a`) and one for GPT
      (`.is-b`), in that order.
- [ ] Each agent strip shows: agent monogram + name + model id +
      token count + cost + live-activity phrase. Text content of
      the first strip matches `/Claude.*claude-sonnet.*565.*\$7/`
      (Claude side of the canonical fixture); the second matches
      `/GPT.*gpt-5.5.*793.*\$2/`.
- [ ] `getComputedStyle(document.querySelector('.md-appbar')).
      borderBottomColor` resolves to the M3
      `--md-outline-hair` token's colour (not the v1
      `--border-1`).
- [ ] Visual regression check vs `main` at the commit immediately
      before this spec merges: the Critique pane (right side) and
      Timeline pane internals (`.tl-phase`, `.tl-turn`, `.tl__rail`)
      render pixel-identical. The chrome + sub-header + agent bar
      are *expected* to change.

## 6. Visual verification matrix

Three viewports × two themes = six shots, on the canonical fixture
`#/runs/20260516-035048-partner-vetting-arch-critique` with
onboarding pre-dismissed (`localStorage.setItem('dr.onboarding.
dismissed', '1')` before navigation):

- `2200×1300 dark` — full run-detail with chrome + sub-header +
  agent-bar visible above Timeline + Critique
- `2200×1300 light` — same, light theme
- `1400×900 dark` — laptop-bucket viewport; agent-bar two-column
  layout MUST still fit on one row (no wrapping)
- `1400×900 light` — same, light theme
- `820×1180 dark` — tablet-bucket viewport; agent-bar may wrap to
  two rows but must NOT overlap timeline
- `820×1180 light` — same, light theme

For each shot, side-by-side diff against `main` at HEAD~1. Pass
criteria: the three corrected surfaces (chrome, sub-header,
agent-bar) look intentionally different. The Critique pane and the
Timeline phase/turn rows look identical to HEAD~1 (regression
check).

## 7. Anti-pattern checks

- [ ] No inline `var(--bg-*)` / `var(--fg-*)` / `var(--border-*)`
      on the outer `ChromeBar` wrapper after the edit. (Inner
      children may still have them — that drains in follow-ups.)
- [ ] No inline `var(--bg-*)` / `var(--fg-*)` / `var(--border-*)`
      on the outer `RunDetailHeader` wrapper after the edit.
- [ ] `TimelineAgentPill` is NOT modified. It's reused as-is.
- [ ] The `data-tour-anchor="run-detail-header"` attribute on
      the `RunDetailHeader` element survives. Spec 0103's
      onboarding tour reads it.
- [ ] The `.tl__head`, `.tl__rail`, `.tl-phase`, `.tl-turn`,
      `.bar1`, `.bar2`, `.crit-group__hd` elements remain
      structurally and visually unchanged (regression check —
      these are the surfaces specs 0098 + 0099 landed cleanly).
- [ ] No new top-level files. CSS changes append to
      `components.css`; JSX changes are localised to two
      functions in two files.
- [ ] Reduced-motion contract preserved (no new animations
      introduced).

## 8. Handover read

> *First task on running this spec: read
> `handoffs/2026-05-19-spec-0104-loading-states.md` (or whichever
> handover is latest under handoffs/) end-to-end, then this spec
> file end-to-end. Verify the three defects still reproduce on
> the current `main` by loading
> `http://127.0.0.1:6173/#/runs/20260516-035048-partner-vetting-
> arch-critique` in a browser, dismissing the onboarding modal,
> and confirming: (a) the top bar has no `.md-appbar` class,
> (b) the sub-header has no className, (c) no `.as` elements
> appear above the Timeline pane. If any defect no longer
> reproduces, this spec's scope shrinks accordingly.*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that
> invalidates any acceptance criterion below, edit this file
> in-place to align before implementing. Document the edit
> verbatim in the handover written at the end of this spec.
> The queue's Read → Reason → Rewrite triad is the safety net
> for cross-spec drift; this section is what makes that work.*
>
> *Specific drift to watch for: if a subsequent ad-hoc commit
> on `main` has already added `.md-appbar` to ChromeBar OR
> already restored the `TimelineAgentPill` call sites, this
> spec's scope shrinks to whatever is still missing.*

## 10. Backend touched?

**no.** This spec changes only the static frontend JSX + CSS
layer plus version metadata. The backend exposes the same shapes
after this spec lands.

## 11. CSS class anchor list

```
.md-appbar                        → applied to <header> in app.jsx ChromeBar (CSS already exists)
.run-detail__head                 → applied to <header> in run-detail.jsx RunDetailHeader (CSS new in this spec)
.agent-bar                        → applied to wrapper <div> in run-detail.jsx TimelineAgentBar (CSS new in this spec)
.as / .is-a / .is-b               → reused inside .agent-bar via existing TimelineAgentPill → AgentStrip path
```

## 12. Notes for the autonomous-mode inner session

> Not a normal spec section — but the 0093 → 0104 arc taught the
> queue tooling that "renders without errors" is not the same as
> "renders the new design." For this spec specifically:
>
> 1. **The verify step's pass criterion is DOM-level**, not
>    visual-only. Run `document.querySelector('.md-appbar')` in
>    the preview console and confirm non-null BEFORE the
>    Playwright shots are captured. If it's null, the JSX wiring
>    didn't land — go back to Step 4.
> 2. **Dismiss the onboarding modal before capturing shots.**
>    The 0093 → 0104 verify shots were all dominated by the
>    onboarding modal because the capture script didn't dismiss
>    it. Add the localStorage setters (or click "Skip" /
>    "Continue") to the per-shot setup.
> 3. **Visual regression target is HEAD~1**, not HEAD~N. Diff
>    against the immediate predecessor commit on main, not
>    against some earlier baseline.

---
spec: 0098
title: Critique pane M3 rework — Bar 1 (title · phase tabs · totals · drift chip) + Bar 2 (kind tabs · agent · status filters) + collapsible status-grouped sections + Σ Summary state + phase-header sizing taller than card headers
label: bug
version-bump: MINOR
status: proposed
target-version: 0.73.1
created: 2026-05-19
pr: ""
---

# Spec 0098 — Critique pane M3 rework

> Ship bucket: **Composed**
> Depends on: **0092, 0093, 0094, 0095, 0097**
> Complexity: **L**
> Targeted version bump: **MINOR** (Issue 2 is a structural-IA fix to the critique pane chrome; user-visible navigation flow changes. MINOR per repo convention for visible-IA shifts.)

## 1. Goal

Replace the current critique-pane chrome with the M3 two-bar
canonical layout (Bar 1 = title + phase tabs + totals + drift
chip; Bar 2 = kind tabs with per-phase counts + agent / status
segmented filters). Body becomes **collapsible status-grouped
sections** (Open · new this round · info-strong tint; Open ·
carried over · warn; Resolved · ok, collapsed by default; Drift ·
err, collapsed by default). Selecting the Σ Summary phase tab
hides Bar 2 (summary is one read, not triage).

Resolves Issues 2 and 3 (the phase-header-sizing half of Issue 3
— phase headers are visibly **taller** than the card headers
inside them).

## 2. Files touched

- `src/dual_research/ui/static/components.css` — append the
  critique-pane chrome block: `.crit2` + `.crit2 .bar1` + `.crit2
  .bar2` + `.crit2 .ttl` + `.crit2 .vbar` + `.crit2 .right` +
  `.crit-totals` + `.crit-totals .n` + `.crit-totals .lbl` +
  `.crit-totals .n.is-{info,ok}` + `.drift-chip` per
  [v2-m3-page.css:664-731](docs/design-system-v2/assets/styles/v2-m3-page.css);
  the collapsible group `.crit-group` + `.crit-group__hd` +
  `.crit-group__chev` + `.crit-group__title` + `.crit-group__count`
  + `.crit-group__count.is-{info,warn,ok,err}` + `.crit-group__meta`
  + `.crit-group[data-collapsed="true"]` per
  [v2-m3-page.css:1146-1200](docs/design-system-v2/assets/styles/v2-m3-page.css);
  the short-form item card `.sc` + `.sc.is-{open,resolved,drift}`
  + `.sc-head` + `.sc-by` + `.sc-q` per
  [v2-m3-page.css:785-800](docs/design-system-v2/assets/styles/v2-m3-page.css);
  and the side-by-side critique pane chrome `.crv__head` +
  `.crv__phasetabs` + `.crv__ptab` + `.crv__filters` + `.crv__body`
  per
  [v2-m3-page.css:1597-1690](docs/design-system-v2/assets/styles/v2-m3-page.css).
  **Phase-header-sizing rule (Issue 3):** add to the rule for
  `.crit-group__title` (status-section heads) and any phase-
  grouping header used in this pane: `font: var(--md-w-medium)
  var(--md-title-m-size)/1 var(--md-font-plain);` — that's
  16 dp at the title-medium role. The card title inside each
  group reads body-medium (`var(--md-body-m-size)`, 14 dp). 16 dp
  > 14 dp visually; the title weight of `medium` (500) is heavier
  than the body weight of `regular` (400). That is the Issue 3
  sizing contract.
- `src/dual_research/ui/static/run-detail.jsx` — rewrite
  `CritiqueExplorer` (line 5700) to render the new chrome.
  Concretely:
  - The component renders a single `<section class="crit2">`
    root containing two header bars (`.bar1` and `.bar2`), a
    body container, and the status-grouped sections.
  - **Bar 1** carries: `<span class="ttl">Critique</span>` +
    `<span class="vbar">` + `<div class="phase-tabs">` with
    three buttons (`P2 Negotiate`, `P4 Review`, `Σ Summary` —
    the active one carries `.is-active`) + `<div class="right">`
    carrying `<span class="crit-totals">` (introduced · open
    [info-tinted] · resolved [ok-tinted]) and `<span class="drift-chip">`.
  - **Bar 2** carries: `<div class="kind-tabs">` with five
    buttons (`All`, `Issues`, `Comments`, `Questions`,
    `Disagreements`) each with a `.ct` count chip whose tone
    matches the kind (info / warn / err) per the design-system
    rule + `<div class="right">` with two `.tab-group-solid`
    segmented controls (agent: All / Claude / GPT; status: All
    / Open / Resolved / Drift).
  - **Σ Summary state**: when the active phase tab is `Σ Summary`,
    Bar 2 does not render (set `display: none` via JS state).
    The body in Σ Summary mode renders the three summary lines
    documented at
    [Design System v2.html · #critique state C](docs/design-system-v2/assets/Design%20System%20v2.html)
    lines 943-986: "Highest-leverage open thread", "Hottest
    disagreement", "Drift". Each is a one-line summary referencing
    a `<QuestionRef>` + a status chip + a short prose summary.
  - **Status-grouped sections** in P2 / P4 mode: render four
    `.crit-group` blocks in this fixed order, each only present
    if the count is > 0:
    1. **Open · new this round** — `data-tone="info"`,
       `.crit-group__count.is-info`, collapsed: false.
    2. **Open · carried over** — `data-tone="warn"`,
       `.crit-group__count.is-warn`, collapsed: false.
    3. **Resolved** — `data-tone="ok"`,
       `.crit-group__count.is-ok`, collapsed: **true by default**
       (click to expand).
    4. **Drift** — `data-tone="err"`,
       `.crit-group__count.is-err`, collapsed: **true by default**
       (does not block exit; included for the record).
    Each group's body is a vertical list of `<QuestionThread />`
    callsites (from Spec 0097), or — in compact mode — `<div
    class="sc">` short-form item cards for the section preview.
    The expanded form is the full QuestionThread.
  - **Issue 3 sizing contract**: the phase-section headers
    (`.crit-group__hd .crit-group__title`) render at
    title-medium (16 dp / 24 lh) with weight 500. The card titles
    inside each section (`.sc-q` or `<QuestionThread> .qt-head`'s
    chip cluster) render at body-medium (14 dp / 20 lh) with
    weight 400 for prose / 500 for chips. The phase-section
    header is visibly taller — the line-height alone is 24 vs
    20, a 4 dp delta the eye reads as "this is the section
    head."
  - **Filter wiring**: agent and status filters drive a single
    React state object; switching agents from `All` to `Claude`
    re-filters every section's items to those raised by Claude.
    Likewise for status. Counts on the `.kind-tab` chips reflect
    the **current filter** (not the unfiltered totals); the
    `crit-totals` strip in Bar 1 always shows run-wide totals
    so the user can see the big picture even with a narrow
    filter applied.
- `pyproject.toml` — `0.73.0` → `0.73.1`.

## 3. Material 3 anatomy

- `#critique` — verbatim source. Two-bar header, three states
  (P2 / P4 / Σ), collapsible status-grouped sections.
- `#tabs` — `.phase-tabs` and `.kind-tabs` from Spec 0095.
- `#thread` — `.crit-group` body renders `<QuestionThread />`
  instances from Spec 0097.
- `#elevation` — hover-elevation rule from Spec 0094 fires on
  each `.sc` / `.qthread` item card; the section headers
  (`.crit-group__hd`) never lift.
- `#a11y` — collapsible groups use `role="button" tabindex="0"`
  with Enter / Space toggling per the script in the design
  system HTML (lines 3289-3311).

**Inline HTML structure** (the implementer renders this exact
shape — copied from
[Design System v2.html · #critique state A](docs/design-system-v2/assets/Design%20System%20v2.html)
lines 754-893, normalised to the canonical anatomy):

```html
<section class="crit2">

  <!-- BAR 1 — Title · Phase tabs · Totals · Drift chip -->
  <header class="bar1">
    <span class="ttl">Critique</span>
    <span class="vbar"></span>
    <div class="phase-tabs">
      <button class="phase-tab"><span class="pcode">P2</span><span class="pname">Negotiate</span></button>
      <button class="phase-tab is-active"><span class="pcode">P4</span><span class="pname">Review</span></button>
      <button class="phase-tab"><span class="sigma">Σ</span><span class="pname">Summary</span></button>
    </div>
    <div class="right">
      <span class="crit-totals">
        <span><span class="n">164</span><span class="lbl">introduced</span></span>
        <span><span class="n is-info">5</span><span class="lbl">open</span></span>
        <span><span class="n is-ok">22</span><span class="lbl">resolved</span></span>
      </span>
      <span class="drift-chip"><!-- triangle svg -->1 drift</span>
    </div>
  </header>

  <!-- BAR 2 — Kind tabs · Agent filter · Status filter. Hidden in Σ state. -->
  <header class="bar2">
    <div class="kind-tabs">
      <button class="kind-tab is-active"><span>All</span><span class="ct">31</span></button>
      <button class="kind-tab is-zero"><span>Issues</span><span class="ct">0</span></button>
      <button class="kind-tab is-zero"><span>Comments</span><span class="ct">0</span></button>
      <button class="kind-tab"><span>Questions</span><span class="ct is-info">30</span></button>
      <button class="kind-tab"><span>Disagreements</span><span class="ct is-warn">1</span></button>
    </div>
    <div class="right">
      <div class="tab-group-solid">
        <button class="tab-solid is-active">All</button>
        <button class="tab-solid"><span class="dot" style="background:var(--p-sable)"></span>Claude</button>
        <button class="tab-solid"><span class="dot" style="background:var(--p-sage)"></span>GPT</button>
      </div>
      <div class="tab-group-solid">
        <button class="tab-solid is-active">All</button>
        <button class="tab-solid">Open</button>
        <button class="tab-solid">Resolved</button>
        <button class="tab-solid">Drift</button>
      </div>
    </div>
  </header>

  <!-- BODY — status-grouped collapsible sections -->
  <div class="crit2__body">

    <!-- Group 1: Open · new this round (info-strong) -->
    <section class="crit-group">
      <header class="crit-group__hd" role="button" tabindex="0">
        <span class="crit-group__chev"><span class="ms ms-20">expand_more</span></span>
        <span class="crit-group__title">Open · new this round<span class="crit-group__count is-info">3</span></span>
        <span class="crit-group__meta">raised in P4 · r5</span>
      </header>
      <div class="crit-group__body">
        <!-- short-form item cards · click to expand to <QuestionThread /> -->
        <article class="sc is-open">
          <header class="sc-head">
            <span class="qref" data-kind="Q">…</span>
            <span class="chip tone-info-strong">open · new</span>
            <span class="sc-by">by <span class="a">Claude</span> · r5</span>
            <span style="margin-left:auto"><span class="md-chip md-chip--sm">P4</span></span>
          </header>
          <div class="sc-q">What exact RLS controls do you think are mandatory beyond connection-pool reset…</div>
        </article>
        <!-- … more sc items … -->
      </div>
    </section>

    <!-- Group 2: Open · carried over (warn) -->
    <section class="crit-group">…</section>

    <!-- Group 3: Resolved (ok, collapsed by default) -->
    <section class="crit-group" data-collapsed="true">…</section>

    <!-- Group 4: Drift (err, collapsed by default) -->
    <section class="crit-group" data-collapsed="true">…</section>

  </div>
</section>
```

Toggle wiring (Enter / Space + click handler) lives in `shared.jsx`
as a small global delegate — same pattern the design system uses
at
[Design System v2.html](docs/design-system-v2/assets/Design%20System%20v2.html)
lines 3289-3311.

## 4. Notion issues addressed

1. **Issue 2 — Critique section structure is wrong (use the
   design-system layout).** Sources:
   `docs/design-system-v2/notion-issues/screenshots/02-critique-current.png`
   (current — wrong) and
   `docs/design-system-v2/notion-issues/screenshots/02-critique-target.png`
   (target — correct). Resolution: render exactly the target
   layout per § 2 and § 3 above. Two bars, three states,
   collapsible status-grouped sections.
2. **Issue 3 — Phase headers should be bigger than card headers**
   (phase-header sizing half). Source:
   `docs/design-system-v2/notion-issues/screenshots/03-phase-headers-1.png`
   shows the phase header at the same visual weight as the cards
   inside it. Resolution: section headers at title-medium
   (16 dp / weight 500), card titles at body-medium (14 dp /
   weight 400-or-500-on-chips). The 2 dp size delta + the
   uppercase letter-spacing on the section head create the
   visible hierarchy. The hover-elevation half of Issue 3 is
   already addressed in Spec 0094.

## 5. Acceptance criteria

- [ ] The critique pane renders exactly the markup shape in
      §3 — `.crit2 > .bar1 + .bar2 + .crit2__body > .crit-group …`.
      No legacy v1 wrappers remain in the DOM.
- [ ] Bar 1 contains: title chip + vbar + 3 phase tabs + totals
      cluster + drift chip. Verified by DOM query.
- [ ] Bar 2 contains: 5 kind tabs (All · Issues · Comments ·
      Questions · Disagreements) each with a count chip + 2
      segmented filter groups (agent + status). Verified by DOM
      query.
- [ ] Switching to `Σ Summary` removes Bar 2 from the DOM (or
      sets `display: none`). The body renders the three summary
      lines instead of grouped sections.
- [ ] Body renders four `.crit-group` sections (when each count
      is > 0) in this exact order: Open · new this round, Open
      · carried over, Resolved, Drift.
- [ ] Resolved and Drift groups have `data-collapsed="true"` on
      first render; clicking the header chevron toggles the
      attribute and the body shows / hides.
- [ ] **Issue 3 phase-header sizing**: computed `font-size` on
      `.crit-group__title` is `16px`; computed `font-size` on
      the card-header chip cluster is `12px` (chips) or `14px`
      (item title) — verified by DevTools computed style. The
      phase-section header is visibly the taller heading.
- [ ] Hover on any `.sc` or `.qthread` inside a section lifts
      to elevation-2 (from Spec 0094). Hover on the
      `.crit-group__hd` does NOT lift.
- [ ] Agent + status filter switches re-filter the section
      contents in place; the kind-tab counts reflect the
      filtered subset; the Bar 1 totals stay run-wide.
- [ ] All four kinds (Q · D · I · C) render via the
      `<QuestionThread />` callsite from Spec 0097 when expanded.

## 6. Visual verification matrix

- `2200×1300 dark` — route `#/runs/<a run with at least one of
  each kind across P2 and P4>`. Capture the pane in each of
  three states: P2 Negotiate active, P4 Review active, Σ
  Summary active.
- `2200×1300 light` — same three states.
- `1400×900 dark` — same three states. Verify Bar 2 wraps
  gracefully (filter clusters drop below the kind tabs if
  needed).
- `1400×900 light` — same.
- `820×1180 dark` — single-column; verify the bars stack and
  the filter clusters wrap.
- `820×1180 light` — same.

All six required. The critique pane is the highest-leverage
information surface on the page; regressions cascade.

## 7. Anti-pattern checks

- [ ] No cryptic IDs leaking the database (`QuestionRef` for
      every q-id).
- [ ] No emoji as icons.
- [ ] No off-grid spacing.
- [ ] No hex codes in component CSS.
- [ ] No per-theme overrides where token roles cover the case.
- [ ] Reduced-motion contract preserved — the chevron rotation
      reads `--md-easing-emphasized` at `--md-dur-short-3`;
      killed under `reduce`.
- [ ] Focus ring visible on every focusable (phase tab, kind
      tab, agent / status segmented option, section header).
- [ ] **Issue 2 anti-patterns:** no horizontal scroll of the
      kind-tab strip, no Bar 1 wrap into multiple lines at
      default width, no Σ-Summary state showing Bar 2.
- [ ] **Issue 3 anti-pattern:** no phase-section header
      rendered at the same font-size as the card title inside
      it.

## 8. Handover read

> *First task on running this spec: read `handoffs/<YYYY-MM-DD>-spec-0097-question-thread-unified-item-card-family.md` end-to-end. (Created by the previous spec at its handover step — the queue convention.)*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that invalidates any acceptance criterion below, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift; this section is what makes that work.*

## 10. Backend touched?

**no.** The critique pane composes data the backend already
emits (questions, disagreements, issues, comments, with raiser /
round / quote / status / phase fields). **Degrade gracefully:**
if the backend doesn't emit a particular sub-status (e.g. it
emits `open` but not `open-new` vs `open-carried`), the pane
should group under `Open · new this round` only when the
question was raised in the current visible round, else under
`Open · carried over`. The "current round" is the latest round
visible in the timeline. No backend field needs to be added.

## 11. CSS class anchor list

```
.crit2                                  → #critique (pane container)
.crit2 .bar1, .bar2                     → #critique (the two-bar header)
.crit2 .ttl, .vbar                      → #critique (Bar 1 title + divider)
.crit2 .right                           → #critique (Bar 1 right-aligned totals + drift)
.crit-totals, .crit-totals .n, .lbl     → #critique (totals cluster)
.crit-totals .n.is-{info,ok}            → #critique (info/ok-tinted counts)
.drift-chip                             → #critique (run-wide drift indicator)

.phase-tabs, .phase-tab + variants      → #critique (Bar 1 phase tabs; primitive from 0095)
.kind-tabs, .kind-tab + variants        → #critique (Bar 2 kind tabs; primitive from 0095)
.tab-group-solid, .tab-solid + variants → #critique (Bar 2 agent + status filters; primitive from 0095)

.crit-group                              → #critique (status-grouped collapsible section)
.crit-group__hd                          → #critique (section header — Issue 3 taller-than-card title-medium)
.crit-group__chev                        → #critique (rotating chevron)
.crit-group__title                       → #critique (section title)
.crit-group__count.is-{info,warn,ok,err} → #critique (status-tinted count chip)
.crit-group__meta                        → #critique (small right-aligned meta line)
.crit-group[data-collapsed="true"]       → #critique (collapsed state)
.crit-group__body                        → #critique (item list container)

.sc, .sc.is-{open,resolved,drift}        → #critique (short-form item card)
.sc-head, .sc-by, .sc-q                  → #critique (short-form anatomy)
```

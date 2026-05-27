---
spec: 0099
title: Timeline pane M3 rework — header chrome + vertical phase rail outside column anchored to header centers + tl-turn variants + single dashed top border on unfold + REPAIR row variant with explainer
label: bug
version-bump: PATCH
status: proposed
target-version: 0.73.2
created: 2026-05-19
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0099 — Timeline pane M3 rework

> Ship bucket: **Composed**
> Depends on: **0092, 0093, 0094**
> Complexity: **L**
> Targeted version bump: **PATCH** (label `bug` — resolves Issues 5, 11, 16; no new feature)

## 1. Goal

Rebuild the timeline pane chrome to match the M3 spec: `Timeline ·
count` title row, pill-style `Conversation / Consumption` tabs,
and — most importantly — the **vertical phase rail outside the
timeline column, anchored to each visible phase header's vertical
centre**. Each phase has exactly one marker; markers do not float
by index. Resolves Issue 5 (phase indicators anchoring), Issue 11
(double divider on unfold), and Issue 16 (REPAIR-round explainer).

After this spec, the timeline pane composes from existing
primitives — `tl-phase` collapsible sections + `tl-turn` one-line
rows + `tl-turn--open` expanded card — with one dashed top border
between row and body, and a clear REPAIR variant that explains
what happened.

## 2. Files touched

- `src/dual_research/ui/static/components.css` — append the
  timeline pane chrome block: `.tl__head` + `.tl__head .ttl` +
  `.tl__head .ct`; `.tl__tabs` + `.tl__tab` + `.tl__tab.is-active`;
  `.tl__body` (the 40 dp + 1 fr grid); `.tl__rail` + `.tl__rail
  .seg` + `.tl__rail .seg::before` (the connecting line) +
  `.tl__rail .seg .marker` + `.tl__rail .seg.is-{done,current}` +
  `.tl__rail .seg .lbl` per
  [v2-m3-page.css:1422-1487](docs/design-system-v2/assets/styles/v2-m3-page.css);
  `.tl__phases` container; `.tl-phase` + `.tl-phase__hd` +
  `.tl-phase__pcode` + `.tl-phase__name` + `.tl-phase__meta` +
  `.tl-phase[data-collapsed="true"]` per
  [v2-m3-page.css:1489-1526](docs/design-system-v2/assets/styles/v2-m3-page.css);
  `.tl-turn` + `.tl-turn__ai` + `.tl-turn__ai.is-{a,b}` +
  `.tl-turn__nm` + `.tl-turn__lbl` + `.tl-turn__deltas` +
  `.tl-turn__round` + `.tl-turn.is-current` per
  [v2-m3-page.css:1528-1561](docs/design-system-v2/assets/styles/v2-m3-page.css);
  `.tl-delta.up` / `.tl-delta.down` / `.tl-delta.rep` per
  [v2-m3-page.css:1563-1571](docs/design-system-v2/assets/styles/v2-m3-page.css);
  `.tl-turn--open` + `.tl-turn--open .tl-turn` + `.tl-turn--open
  .body` + `.tl-turn--open .actions` per
  [v2-m3-page.css:1573-1594](docs/design-system-v2/assets/styles/v2-m3-page.css).
  **Issue 11 fix** is baked into the `.tl-turn--open .body`
  rule: `border-top: 1px dashed var(--md-outline-hair);` is the
  **only** divider between the row and the body. The CSS
  contains no second `border-bottom` on `.tl-turn--open .tl-turn`
  and no second `border-top` on `.tl-turn--open .body`. Verify
  with a grep before merging.
  **Issue 5 anchoring contract** lives in the rail rules: the
  rail is a vertical flex container; each `.seg` is `flex: 1`,
  so exactly one marker renders per visible phase, vertically
  centred against the phase block on the right (the `.tl-phase`
  in `.tl__phases`). The rail and the phase list share the same
  CSS grid; markers track the phase header's `top` automatically.
- `src/dual_research/ui/static/run-detail.jsx` — rewrite the
  `Timeline` component (line 823) to render the new chrome and
  the rail-anchored structure. Concretely:
  - The pane root becomes `<div class="rdvc__pane"><div
    class="tl__head">…</div><div class="tl__tabs">…</div><div
    class="tl__body"><div class="tl__rail">…</div><div
    class="tl__phases">…</div></div></div>`.
  - `tl__head` renders `<span class="ttl">Timeline</span>` +
    `<span class="ct">{run.artifacts.length} artifacts</span>`.
  - `tl__tabs` renders two pill-tabs: `Conversation` (default
    active) and `Consumption`. Active state toggles the body
    between phase-grouped turn rows (Conversation) and the
    consumption cards (Consumption — feeds into Spec 0100).
  - **Phase rail rendering**: iterate the **visible** phases
    (phases that have at least one turn artifact AND are not
    collapsed-and-empty). Render one `<div class="seg">` per
    visible phase, with `.is-done` if all rounds completed,
    `.is-current` if the run is currently in this phase, neither
    class if queued. Phases not yet started (no artifacts)
    **do not get a marker** — they are hidden, not greyed. This
    is the Issue 5 anchor: no extra markers, no markers for
    phases that aren't yet on screen, and one marker per visible
    phase block, centred against it via CSS grid alone.
  - **Phase sections** (`.tl-phase`): each visible phase renders
    as `<section class="tl-phase" data-collapsed={!isExpanded}>`
    with a header (chevron + pcode + name + meta) and a body
    (list of `.tl-turn` rows).
  - **Turn row** (`.tl-turn`): each artifact renders as a one-
    line row with avatar + name + label + deltas + round chip.
    Click to expand swaps the row's container for the
    `.tl-turn--open` wrapper (single dashed top border between
    the header row and the body — Issue 11 contract).
  - **REPAIR variant (Issue 16)**: when the turn artifact has
    `repair: true` (the backend already emits this flag for
    repair rounds), the row renders an additional `<span
    class="tl-delta rep">REPAIR</span>` chip in the deltas slot,
    and the expanded body contains the canonical explainer
    sentence: *"GPT was silent this turn. Claude will reissue
    the same plan on the next round. No data lost."* The
    explainer renders in the `.tl-turn--open .body` slot in
    serif italic. If the silent agent is Claude instead, the
    sentence flips agent names. The card also renders the
    standard turn metadata (round chip + cost chip in the
    actions row) so the user sees that no tokens were spent
    on the silent agent's side this round.
- `pyproject.toml` — `0.73.1` → `0.73.2`.

## 3. Material 3 anatomy

- `#timeline` — verbatim source. Header chrome + collapsible
  phase sections + one-line turn rows + expanded turn cards.
- `#elevation` — turn cards use elevation-1 default, lift to
  elevation-2 on hover (Spec 0094 rule). Phase header never
  lifts.
- `#tabs` — `Conversation / Consumption` pill tabs are the
  `.tl__tab` variant defined in this spec; based on the
  segmented-pill primitive from Spec 0095.

**Inline HTML structure** (copied from
[Design System v2.html · #timeline](docs/design-system-v2/assets/Design%20System%20v2.html)
lines 1339-1437, normalised for the live app):

```html
<div class="rdvc__pane">

  <!-- HEAD — title + count -->
  <header class="tl__head">
    <span class="ttl">Timeline</span>
    <span class="ct">29 artifacts</span>
  </header>

  <!-- TABS — Conversation / Consumption -->
  <div class="tl__tabs">
    <button class="tl__tab is-active"><span class="ms ms-18">forum</span>Conversation</button>
    <button class="tl__tab"><span class="ms ms-18">stacked_bar_chart</span>Consumption</button>
  </div>

  <!-- BODY — rail + phases. Grid is `40px 1fr`. Markers anchor to phase header centres via flex. -->
  <div class="tl__body">

    <!-- RAIL — one .seg per VISIBLE phase. Markers track phase blocks via CSS grid alone. -->
    <div class="tl__rail" aria-hidden="true">
      <div class="seg is-done">    <span class="marker"></span><span class="lbl">P0</span></div>
      <div class="seg is-done">    <span class="marker"></span><span class="lbl">P1</span></div>
      <div class="seg is-current"> <span class="marker"></span><span class="lbl">P2</span></div>
      <div class="seg">            <span class="marker"></span><span class="lbl">P4</span></div>
    </div>

    <!-- PHASES — collapsible sections, one .tl-phase per visible phase -->
    <div class="tl__phases">

      <section class="tl-phase">
        <header class="tl-phase__hd" role="button" tabindex="0">
          <span class="chev"><span class="ms ms-18">expand_more</span></span>
          <span class="tl-phase__pcode">PHASE 2</span>
          <span class="tl-phase__name">Negotiate plan</span>
          <span class="tl-phase__meta">32m 31s · 12 rounds</span>
        </header>
        <div class="tl-phase__body">

          <!-- Compact one-line turn row -->
          <div class="tl-turn">
            <span class="tl-turn__ai is-a">C</span>
            <span class="tl-turn__nm">Claude</span>
            <span class="tl-turn__lbl">turn 2</span>
            <span class="tl-turn__deltas">
              <span class="tl-delta up">+4 questions</span>
              <span class="tl-delta down">−8 prior</span>
              <span class="tl-delta rep">REPAIR</span>
            </span>
            <span class="tl-turn__round">R2</span>
          </div>

          <!-- Expanded turn — single dashed border between row and body (Issue 11) -->
          <div class="tl-turn--open">
            <div class="tl-turn">
              <span class="tl-turn__ai is-a">C</span>
              <span class="tl-turn__nm">Claude</span>
              <span class="tl-turn__lbl">turn 5 · expanded</span>
              <span class="tl-turn__deltas">…</span>
              <span class="tl-turn__round">R5</span>
            </div>
            <div class="body">"Conceding D·01 (taxonomy not actionable). Regrouped sections by mitigation owner…"</div>
            <div class="actions">
              <button class="md-btn md-btn--tonal md-btn--sm">Open full view</button>
              <button class="md-btn md-btn--text md-btn--sm">Copy hash · b1c8…</button>
              <span style="flex:1"></span>
              <span class="md-chip md-chip--sm">18.4kt in</span>
              <span class="md-chip md-chip--sm">$0.0566</span>
            </div>
          </div>

          <!-- REPAIR-row variant — Issue 16. Body explains what happened. -->
          <div class="tl-turn--open">
            <div class="tl-turn">
              <span class="tl-turn__ai is-b">G</span>
              <span class="tl-turn__nm">GPT</span>
              <span class="tl-turn__lbl">turn 3 · silent</span>
              <span class="tl-turn__deltas"><span class="tl-delta rep">REPAIR</span></span>
              <span class="tl-turn__round">R3</span>
            </div>
            <div class="body">GPT was silent this turn. Claude will reissue the same plan on the next round. No data lost.</div>
            <div class="actions">
              <span class="md-chip md-chip--sm">0 tokens</span>
              <span class="md-chip md-chip--sm">$0.0000</span>
            </div>
          </div>

        </div>
      </section>

      <!-- Additional .tl-phase sections … -->
    </div>
  </div>
</div>
```

## 4. Notion issues addressed

1. **Issue 5 — Phase indicators on the timeline jump around / aren't
   anchored.** Sources:
   `docs/design-system-v2/notion-issues/screenshots/05-phase-indicators-1.png`,
   `…/05-phase-indicators-2.png`,
   `…/05-phase-indicators-3.png`. Resolution: the rail is a
   vertical flex container with one `.seg` per visible phase,
   and the phase column on the right is a vertical stack of
   `.tl-phase` blocks. Both columns share the same CSS grid row
   sizing, so each marker is centred against its phase block by
   layout alone — no JS anchoring. Phases that have not yet
   produced any artifact are hidden (no greyed marker); phases
   that have completed render `.is-done` (sage marker); the
   active phase renders `.is-current` (info marker with a glow
   ring). Verify across all three scenarios:
   (a) one visible phase, (b) two phases with one collapsed,
   (c) five phases with mixed open/closed. Each scenario must
   render exactly one marker per visible phase, anchored to its
   header centre.
2. **Issue 11 — Double divider line when unfolding the first
   card under Phase 4.** Source:
   `docs/design-system-v2/notion-issues/screenshots/11-double-divider.png`.
   Resolution: the only divider between the still-visible
   `.tl-turn` row and the `.body` block is `border-top: 1px
   dashed var(--md-outline-hair)` on `.tl-turn--open .body`.
   The `.tl-turn` itself has no `border-bottom`, and the
   `.tl-turn--open` wrapper has no second border-top. The CSS
   grep at PR time must show zero `border-bottom` rules on
   `.tl-turn` and zero rules adding a second separator inside
   `.tl-turn--open`.
3. **Issue 16 — REPAIR-round explainer card.** Source:
   `docs/design-system-v2/notion-issues/screenshots/16-repair-round.png`.
   Resolution: the REPAIR-tagged turn renders a `.tl-delta.rep`
   chip inline AND an expanded body containing the canonical
   one-sentence explainer (per § 2 above). The silent agent's
   side renders `0 tokens · $0.0000` so the user sees the
   round was free on that side.

## 5. Acceptance criteria

- [ ] **Issue 5 — three scenarios.** Capture three screenshots
      at `2200×1300 dark`:
      (a) a run currently in phase 0 only (one visible phase) —
          exactly one `.seg` marker renders, anchored to the
          single `.tl-phase` header centre.
      (b) a run with phases 0-2 visible, phase 1 collapsed —
          exactly three `.seg` markers; the marker for the
          collapsed phase 1 still anchors to its (collapsed)
          header centre, not to its body.
      (c) a run with all five phases (P0..P4) visible, mixed
          open/closed — exactly five markers, each anchored to
          its phase header centre regardless of collapse state.
- [ ] No `.seg` markers render for phases that have not yet
      produced an artifact (e.g. a run still in P0 does not show
      P1/P2/P3/P4 markers).
- [ ] The rail and the phase list visually align: each marker's
      vertical centre matches the corresponding phase header's
      vertical centre within ±2 px in all three scenarios.
- [ ] **Issue 11.** Open one collapsed `.tl-turn` to its
      `.tl-turn--open` state. Count divider lines between the
      header row and the body — exactly **one** dashed line, no
      solid divider beneath it.
- [ ] **Issue 16.** A REPAIR turn renders the `REPAIR` chip in
      the deltas slot AND, when expanded, the explainer
      sentence in the body. The silent agent's chips show
      `0 tokens` and `$0.0000`.
- [ ] Conversation / Consumption tab toggle swaps the body
      content; the chrome above stays intact.
- [ ] Phase sections collapse / expand via chevron click; the
      rail markers anchor follows automatically (Issue 5 again
      — verify dynamically by collapsing one phase and watching
      the markers re-anchor).
- [ ] Hover on any `.tl-turn` lifts to elevation-2; hover on
      `.tl-phase__hd` does NOT lift.
- [ ] All status / agent classes resolve correctly in dark and
      light.

## 6. Visual verification matrix

- `2200×1300 dark` — capture the three Issue-5 scenarios (one-
  visible-phase, two-visible-with-one-collapsed, five-visible
  mixed). Plus one `.tl-turn--open` expanded (Issue 11). Plus
  one REPAIR-row expanded (Issue 16).
- `2200×1300 light` — same.
- `1400×900 dark` — same. Verify the rail width does not change
  at this breakpoint (it stays 40 dp).
- `1400×900 light` — same.
- `820×1180 dark` — the rail collapses to a 24 dp gutter and
  the phase headers stack at full width. Verify markers still
  anchor in single-column mode.
- `820×1180 light` — same.

All six required.

## 7. Anti-pattern checks

- [ ] No cryptic IDs leaking the database.
- [ ] No emoji as icons.
- [ ] No off-grid spacing.
- [ ] No hex codes in component CSS.
- [ ] No per-theme overrides where token roles cover the case.
- [ ] Reduced-motion contract preserved — phase chevron
      rotation and turn expand reads
      `--md-easing-emphasized` at `--md-dur-short-3`; killed
      under `reduce`.
- [ ] Focus ring visible on every focusable (phase header
      chevron, turn row, action buttons).
- [ ] **Issue 5 anti-pattern:** no marker rendered for a phase
      with zero artifacts. No marker rendered by index without
      a corresponding `.tl-phase` block.
- [ ] **Issue 11 anti-pattern:** no second divider (solid or
      dashed) anywhere between `.tl-turn` and `.body`.
- [ ] **Issue 16 anti-pattern:** REPAIR turns must not be
      rendered as a separate side-card outside the row; they
      live INSIDE the `.tl-turn--open` expanded body.

## 8. Handover read

> *First task on running this spec: read `handoffs/<YYYY-MM-DD>-spec-0098-critique-pane-m3-rework.md` end-to-end. (Created by the previous spec at its handover step — the queue convention.)*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that invalidates any acceptance criterion below, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift; this section is what makes that work.*

## 10. Backend touched?

**no.** The timeline pane reads the existing run artifact stream
(phases · rounds · turns · deltas · repair flag) the backend
already emits. **Degrade gracefully:** if the backend doesn't
emit a `repair: true` flag for a silent-round artifact, the row
renders as a normal turn with `0 tokens` — the REPAIR explainer
sentence is omitted rather than fabricated. If `delta` counts are
missing for a turn, the `.tl-turn__deltas` slot is empty (not
rendered with `0` placeholders).

## 11. CSS class anchor list

```
.tl__head, .tl__head .ttl, .tl__head .ct      → #timeline (header chrome)
.tl__tabs, .tl__tab, .tl__tab.is-active        → #timeline (Conv / Consumption tabs)
.tl__body                                      → #timeline (grid container 40px + 1fr)

.tl__rail                                      → #timeline (vertical rail container)
.tl__rail .seg                                 → #timeline · Issue 5 (one marker per visible phase)
.tl__rail .seg::before                         → #timeline (connecting line between markers)
.tl__rail .seg .marker, .lbl                   → #timeline (marker + label)
.tl__rail .seg.is-{done,current}               → #timeline (state-tinted markers)

.tl__phases                                    → #timeline (phase list container)
.tl-phase, .tl-phase[data-collapsed="true"]    → #timeline (collapsible phase section)
.tl-phase__hd, __pcode, __name, __meta         → #timeline (phase header — does not lift on hover)
.tl-phase__body                                → #timeline (turn list)

.tl-turn                                       → #timeline · #elevation (turn row — lifts on hover via 0094)
.tl-turn__ai.is-{a,b}                          → #timeline (agent initial)
.tl-turn__nm, __lbl, __round                   → #timeline (turn metadata)
.tl-turn__deltas                               → #timeline (delta chip slot)
.tl-turn.is-current                            → #timeline (currently-running turn highlight)
.tl-delta.up, .down, .rep                      → #timeline · Issue 16 (delta + REPAIR chip)

.tl-turn--open                                 → #timeline · Issue 11 (expanded turn wrapper)
.tl-turn--open .tl-turn                        → #timeline (still-visible header row inside expanded)
.tl-turn--open .body                           → #timeline · Issue 11 (SINGLE dashed top border)
.tl-turn--open .actions                        → #timeline (action row at bottom)
```

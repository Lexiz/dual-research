---
spec: 0097
title: QuestionThread + unified item-card family (Q · D · I · C cards with one anatomy — who → when → what → quote, six-word verdict vocabulary, tonal bubble + quote inside bubble, dashed footer)
label: bug
version-bump: MINOR
status: proposed
target-version: 0.73.0
created: 2026-05-19
pr: ""
---

# Spec 0097 — QuestionThread + unified item-card family

> Ship bucket: **Composed**
> Depends on: **0092, 0093, 0094**
> Complexity: **L**
> Targeted version bump: **MINOR** (label `bug` ordinarily implies PATCH, but the unified item-card family is the user-visible information-architecture shift that resolves 4 Notion issues at once — a structural change in how questions / disagreements / issues / comments render. MINOR per repo convention for visible-IA shifts.)

## 1. Goal

Replace four separate card layouts (Question / Disagreement / Issue
/ Comment, each with its own header chrome and quote-rendering
pattern) with a single QuestionThread anatomy. The unified card:
- Starts the **card header (always visible)** with **agent who
  raised it → qref → status → phase/round**. No question/title
  text in the header.
- On unfold, shows turns in chronological order. Each turn renders
  inside a **tonal-tinted bubble** (sable for Claude, sage for
  GPT). The agent's quote lives **inside the bubble**, in serif
  italic, full card width — never duplicated outside.
- Uses the canonical **six-word verdict vocabulary**: `raised`,
  `pushback`, `conceded`, `resolved`, `ghosted`, `drift`. Never
  abbreviated, never substituted (`restated`, `noted`, `flagged
  by`, etc. become one of the six).
- Closes with a **single dashed top-border footer** for the
  resolution summary line.

Resolves Issues 7, 8, 9, 10 with one shared anatomy so the
implementer doesn't have to re-derive it per card kind.

## 2. Files touched

- `src/dual_research/ui/static/components.css` — append the
  reworked QuestionThread block: `.qthread` base + `.qthread.is-{open,resolved,drift}`
  + `.qt-head` + `.qt-timeline` + `.qt-row` + `.qt-row.is-{a,b,ghosted}`
  + `.qt-pill` + `.qt-agent` + `.qt-sep` + `.qt-round` +
  `.qt-verdict` + `.qt-quote` + `.qt-resolved-foot` + `.qt-drift`
  per
  [v2-m3-page.css:607-662](docs/design-system-v2/assets/styles/v2-m3-page.css)
  AND the single-column override per
  [v2-m3-page.css:1202-1212](docs/design-system-v2/assets/styles/v2-m3-page.css).
  Also append the inline expanded variant `.sci` + `.sci.is-{open,
  open-new,resolved,drift}` + `.sci__hd` + `.sci__q` + `.sci__thread`
  + `.sci__msg` + `.sci__msg.is-{a,b}` + `.sci__msg p` per
  [v2-m3-page.css:1238-1266](docs/design-system-v2/assets/styles/v2-m3-page.css),
  used by the critique pane's side-by-side mode (Spec 0098).
- `src/dual_research/ui/static/shared.jsx` — rewrite
  `QuestionThread` (currently around line 908). The new prop API:
  ```jsx
  <QuestionThread
    id={id}            // legacy "Q-c-r1-04" decoded via parseQId
    kind="question|disagreement|issue|comment"
    status="open|open-new|resolved|drift"
    raisedBy="claude|gpt"
    raisedRound={1}
    phase="P2|P4"
    turns={[
      { agent: "claude", round: 1, verdict: "raised",   quote: "..." },
      { agent: "gpt",    round: 2, verdict: "pushback", quote: "..." },
      { agent: "claude", round: 3, verdict: "conceded", quote: "..." },
    ]}
    footer="resolved at round 3 · 2 turns to converge · hash match"
  />
  ```
  Internal contract:
  - The card header (`<header class="qt-head">`) emits, in
    fixed order: AgentStrip (raiser) → `<QuestionRef>` (qref
    badge with kind code) → status chip
    (`<Chip tone="info-strong|warn|ok|err">open · new | open ·
    carried | resolved · r{N} | drift</Chip>`) → phase chip
    (`<span class="md-chip md-chip--sm">P{phase}</span>`).
    **No title / question / quote text in the header.**
    The header is the badge cluster, in the exact left-to-right
    order specified by `#cards`'s cluster contract.
  - The turn list (`<ol class="qt-timeline">`) emits one
    `<li class="qt-row is-{a|b|ghosted}">` per turn. Each row
    contains exactly two children: the `<span class="qt-pill">`
    (agent initial + name + round + verdict) and the `<p
    class="qt-quote">` (serif italic, full card width).
    **No quote outside the bubble. No agent-name outside the
    pill.**
  - The footer renders only when `status === "resolved"` or
    `status === "drift"`, as `<div class="qt-resolved-foot">` or
    `<div class="qt-drift">`. One dashed top border, one line of
    label-medium uppercase text.
  - Add a static `VERDICT_VOCAB = ['raised', 'pushback',
    'conceded', 'resolved', 'ghosted', 'drift']` constant; the
    component throws (in dev) if `t.verdict` is outside this
    set, so the implementer can't quietly re-introduce
    `restated` / `noted` / `flagged`.
  - `kind`-specific behaviour: the `qref-k` data attribute
    routes to colour per
    [v2-m3-page.css:555-557](docs/design-system-v2/assets/styles/v2-m3-page.css)
    (`Q` and `Cl` use tertiary, `D` and `I` use error,
    `C` uses primary). The header text is identical across all
    four kinds; only the qref-k letter changes.
- `src/dual_research/ui/static/run-detail.jsx` — replace the
  four separate card renderers inside `CritiqueExplorer` (around
  line 5700) with one call to `<QuestionThread … />` per item.
  Concretely:
  - **Issue 7 (questions)** — delete the duplicated question
    text that currently renders above the first turn-bubble.
    The header alone carries the qref + raiser; the quote
    lives inside the first turn-bubble.
  - **Issue 8 (disagreements)** — delete the duplicated
    "resolved" badge that currently renders at the top of the
    card. The status chip in the header is the only one. Also
    delete the standalone "resolved — Both agents agree …"
    summary line that currently sits above the turn list; that
    summary text now appears inside the agent's bubble who
    actually said it.
  - **Issue 9 (issues)** — delete the cryptic `C-1`/`D-3` etc.
    line that currently renders below the header. The
    `<QuestionRef>` in the header is the only reference badge.
    Delete the secondary "open" / "resolved" status pill that
    currently sits below the title — the header chip is
    canonical. Delete the "flagged by Claude · first seen R1 ·
    last seen R2" cluster — `raisedBy` + `raisedRound` are
    rendered via the AgentStrip + qref-round in the header.
    Delete the duplicated quote that currently appears both
    inline (in the prose paragraph) and again in a quoted
    callout below — the quote lives inside the agent's bubble,
    exactly once.
  - **Issue 10 (comments)** — apply the same anti-pattern
    deletions as Issue 9. Comments are the `kind="comment"`
    variant of the same card; no separate renderer.
  - Verify by grep: no `Question card`, `IssueCard`,
    `CommentCard`, `DisagreementCard` JSX renderers remain
    after this spec; only `<QuestionThread />`.
- `pyproject.toml` — `0.72.5` → `0.73.0`.

## 3. Material 3 anatomy

- `#thread` — verbatim source. The unified anatomy in §1 is the
  M3 standard for this component family.
- `#cards` — the card header reads the **cluster contract**:
  (1) agent attribution, (2) position (qref or phase chip),
  (3) status chip, (4) overflow on the right.
- `#atoms` — status pills (`Chip`), AgentStrip, qref are all
  primitives from prior specs.

**Inline HTML structure** (the implementer renders this exact DOM
shape — copied from
[Design System v2.html · #thread](docs/design-system-v2/assets/Design%20System%20v2.html)
lines 1006-1056, lightly normalised):

```html
<article class="qthread is-resolved" aria-labelledby="qt-1">

  <!-- HEADER — always visible. Badge cluster only. No title text. -->
  <header class="qt-head">
    <span class="qref" data-kind="Q">
      <span class="qref-k">Q</span>
      <span class="qref-sep">·</span>
      <span class="qref-n">03</span>
      <span class="qref-by is-b">
        <span class="ai ai-sm ai-b">G</span>
        <span class="qref-by-n">GPT</span>
      </span>
      <span class="qref-round">r1</span>
    </span>
    <span class="chip tone-ok">resolved · r3</span>
    <span class="right md-chip md-chip--sm">P2 · 2 turns to converge</span>
  </header>

  <!-- TIMELINE — chronological turns. Each turn = pill + quote, inside a tonal bubble. -->
  <ol class="qt-timeline" style="list-style:none;margin:0;padding:0;">

    <li class="qt-row is-b">
      <span class="qt-pill">
        <span class="ai ai-sm ai-b">G</span>
        <span class="qt-agent">GPT</span>
        <span class="qt-sep">·</span>
        <span class="qt-round">r1</span>
        <span class="qt-sep">·</span>
        <span class="qt-verdict">raised</span>
      </span>
      <p class="qt-quote">"Are tenant boundaries enforced at the connection-pool level or strictly via RLS policy?"</p>
    </li>

    <li class="qt-row is-a">
      <span class="qt-pill">
        <span class="ai ai-sm ai-a">C</span>
        <span class="qt-agent">Claude</span>
        <span class="qt-sep">·</span>
        <span class="qt-round">r2</span>
        <span class="qt-sep">·</span>
        <span class="qt-verdict">pushback</span>
      </span>
      <p class="qt-quote">"RLS alone is insufficient if pool re-use isn't reset on tenant switch. Both are required."</p>
    </li>

    <li class="qt-row is-b">
      <span class="qt-pill">
        <span class="ai ai-sm ai-b">G</span>
        <span class="qt-agent">GPT</span>
        <span class="qt-sep">·</span>
        <span class="qt-round">r3</span>
        <span class="qt-sep">·</span>
        <span class="qt-verdict">conceded</span>
      </span>
      <p class="qt-quote">"Concede the dual contract — pool reset + RLS — is required. Hash matches."</p>
    </li>

  </ol>

  <!-- FOOTER — single dashed top border. Only rendered for resolved or drift. -->
  <div class="qt-resolved-foot">resolved at round 3 · 2 turns to converge · hash match</div>

</article>
```

For drift, the footer becomes `<div class="qt-drift">drift ·
recorded with full history · does not block exit</div>` and the
container carries `class="qthread is-drift"`.

For ghosted turns inside an otherwise-open thread (the agent who
should have responded did not), the row carries an additional
class: `<li class="qt-row is-b is-ghosted">` and the verdict reads
`ghosted` — `r3-r5` in the round slot indicating the range of
silent rounds.

## 4. Notion issues addressed

1. **Issue 7 — Question card duplicates the question at the top.**
   `docs/design-system-v2/notion-issues/screenshots/07-question-card-duplicate.png`.
   The duplicate disappears because the header no longer renders
   the question text; only the qref + raiser badge cluster.
2. **Issue 8 — Disagreement card has the same duplication
   problem.** `docs/design-system-v2/notion-issues/screenshots/08-disagreement-card.png`.
   Same fix; the duplicate "resolved" badge at top is removed and
   the standalone resolved-summary line is rolled into the
   agent's bubble.
3. **Issue 9 — Issue card has too much info, illogical sequence,
   duplicated quote.**
   `docs/design-system-v2/notion-issues/screenshots/09-issue-card.png`.
   Per § 2: delete the cryptic `C-1` shorthand line; delete the
   secondary "open" status pill; delete the "flagged by Claude ·
   first seen R1 · last seen R2" cluster; render the quote
   exactly once, inside the agent's bubble. Sequence is enforced
   by the unified anatomy: who → when → what → quote.
4. **Issue 10 — Comments on the review tab have the same anti-
   patterns as Issue 9.** `docs/design-system-v2/notion-issues/screenshots/10-comments-card.png`.
   Same fix — comment is the `kind="comment"` variant; the
   unified anatomy is the same.

## 5. Acceptance criteria

- [ ] All four card kinds (Q · D · I · C) render via a single
      `<QuestionThread kind="…" />` callsite; no kind-specific
      JSX renderer remains.
- [ ] Header order is strictly: AgentStrip (raiser) → qref →
      status chip → phase chip. Verified by DOM query.
- [ ] No question / disagreement / issue / comment text appears
      in the card header. The quote appears exactly once, inside
      the bubble of the agent who said it.
- [ ] Issue 9: the literal string `C-1`, `D-3`, `C1`, `D1` does
      not appear anywhere in a rendered card. (Grep the DOM.)
- [ ] Issue 9: no "flagged by Claude · first seen R… · last seen
      R…" string appears. The raiser + first round are the
      AgentStrip + qref-round in the header.
- [ ] Verdict labels render verbatim from the six-word vocabulary
      (`raised`, `pushback`, `conceded`, `resolved`, `ghosted`,
      `drift`). The component throws in dev if asked to render
      a verdict outside this set.
- [ ] The card border-left tints by status: warn (open), ok
      (resolved), err (drift). Open-new and open-carried both
      keep the warn tint on the container; the in-bubble pill
      carries the tone-info-strong vs tone-warn distinction.
- [ ] The dashed footer appears only for `status="resolved"`
      or `status="drift"`; never for `status="open"`.
- [ ] Single-column override at <900 px (the
      [v2-m3-page.css:1202](docs/design-system-v2/assets/styles/v2-m3-page.css)
      rule) collapses the pill above the quote in a vertical
      stack; quote takes full width.
- [ ] Hover on the card lifts to elevation-2 (the rule landed in
      Spec 0094). The header alone never lifts.

## 6. Visual verification matrix

- `2200×1300 dark` — route `#/runs/<a run with at least one of
  each kind (Q, D, I, C) — pick from the fixture set>`. Expand
  one of each in the critique pane. Capture.
- `2200×1300 light` — same.
- `1400×900 dark` — same route. Verify the in-bubble pill
  remains left-aligned and the quote stays full-width-of-bubble.
- `1400×900 light` — same.
- `820×1180 dark` — single-column collapse; verify the pill is
  above the quote and the card pads inset 14 dp.
- `820×1180 light` — same.

All six required. The unified card is the canonical anatomy
referenced by Spec 0098 (critique pane composition); regressions
here block the next spec.

## 7. Anti-pattern checks

- [ ] No cryptic IDs leaking the database — `<QuestionRef>` is
      decoded via `parseQId`; the rendered text is `Q · 04`,
      never `Q-c-r1-04` (the raw legacy id).
- [ ] No emoji as icons.
- [ ] No off-grid spacing — card padding 16 / 20 dp, row gap
      12 dp, in-row gap 8 dp.
- [ ] No hex codes in component CSS — all colors via
      `var(--md-*)` and the `--p-*` palette source.
- [ ] No per-theme overrides — agent-tonal bubbles read
      `--md-primary-container` / `--md-secondary-container` which
      adapt to light/dark.
- [ ] Reduced-motion contract preserved — collapse/expand
      animation reads `--md-easing-emphasized` at
      `--md-dur-short-3`; killed under `reduce`.
- [ ] Focus ring visible on every focusable card (the article
      element is focusable for keyboard expansion).
- [ ] **Anti-pattern enforcement:** the rewrite deletes the
      forbidden patterns; the implementer **must not** silently
      re-introduce them under another markup form. The acceptance
      criteria explicitly forbid: duplicate title in header,
      duplicate quote outside bubble, cryptic `C-1`/`D-3` codes,
      "flagged by … first seen … last seen …" sentences, abbreviated
      verdicts.

## 8. Handover read

> *First task on running this spec: read `handoffs/<YYYY-MM-DD>-spec-0096-m3-modal-primitive.md` end-to-end. (Created by the previous spec at its handover step — the queue convention.)*

## 9. Spec rewrite mandate

> *If the previous implementation surfaces a constraint that invalidates any acceptance criterion below, edit this file in-place to align **before** implementing. Document the edit verbatim in the handover written at the end of this spec. The queue's Read → Reason → Rewrite triad is the safety net for cross-spec drift; this section is what makes that work.*

## 10. Backend touched?

**no.** The backend already emits questions, disagreements,
issues, and comments with raiser + round + verdict + quote
fields. The unified card consumes whatever subset is present.
**Degrade gracefully:** if `turns[i].verdict` is missing on a
backend record (legacy data), omit the verdict separator + label
rather than rendering a synthetic value. If a turn record is
missing entirely (e.g. ghost rounds), render a `qt-row.is-ghosted`
with a `range` of silent rounds in the qt-round slot; never
fabricate a quote.

## 11. CSS class anchor list

```
.qthread, .qthread.is-{open,resolved,drift}    → #thread (card container)
.qt-head                                       → #thread (badge cluster header)
.qt-timeline                                   → #thread (chronological turn list)
.qt-row, .qt-row.is-{a,b,ghosted}              → #thread (per-turn tonal bubble)
.qt-pill                                       → #thread (in-bubble agent · round · verdict pill)
.qt-agent, .qt-sep, .qt-round, .qt-verdict     → #thread (pill internals)
.qt-quote                                      → #thread (serif italic quote, full-width)
.qt-resolved-foot                              → #thread (dashed footer, resolved variant)
.qt-drift                                      → #thread (dashed footer, drift variant)

.sci, .sci.is-{open,open-new,resolved,drift}   → #thread (side-by-side inline variant for 0098)
.sci__hd, .sci__q, .sci__thread, .sci__msg     → #thread (side-by-side anatomy)
```

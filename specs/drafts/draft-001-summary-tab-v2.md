---
kind: draft
draft_id: "001"
slug: summary-tab-v2
title: Summary tab v2 — celebratory close-out with verdict, stats, critique outcomes, and markdown download
type: new-feature
status: draft
created: 2026-05-22
source_session: pre-lifecycle-bootstrap
parked_from: specs/0152-summary-tab-v2.md (untracked, never branched)
---


# Spec 0152 — Summary tab v2

> Ship bucket: **Run-detail close-out UX.**
> Depends on:
> **0046** D5 (per-kind × per-round critique tables — kept verbatim as
> the collapsed drill-down),
> **0057** D6 (highest-leverage open thread — kept and promoted on
> deadlocked runs),
> **0068** (brand-icon system — `BrandMark` / `AgentIcon` used in
> head-to-head cards and per-row),
> **0072** D7–D10 (three-sentence summary copy generator — reused
> verbatim, repositioned as a featured quote block),
> **0117** (artifact registry — `final.document` is the markdown the
> footer downloads),
> **0119** §7 (canonical "resolved" vocabulary — `resolved-claude` =
> Claude yielded; we honour that protocol but stop double-counting
> mutual resolutions),
> **0138** §5.3 (run-id pill click-to-copy — reused as the right-anchored
> id chip in the footer),
> **0141** (critique-aggregation integrity — same `_envelopesForKind` /
> `_buildKindRows` helpers feed the drill-down tables; the new
> per-agent tally lives next to them and stays consistent).
> Complexity: **M** — one large `CritiqueSummaryView` replacement, three
> new sibling sub-components, one `useEffect` for tab-jump-on-terminal,
> one small confetti primitive, no backend or protocol changes.
> Targeted version bump: **MINOR (1.12.x → 1.13.0)** — significant
> additive user-facing surface; no wire-format or schema change.

---

## Context

The Summary tab is the user's payoff after watching two agents argue
across rounds. The current implementation (spec 0046 D5) renders the
summary as four per-phase, per-kind HTML tables stacked under a
three-sentence verdict line. It's accurate but joyless: scanning the
tables doesn't tell you whether the run went well, who carried the
weight, what it cost, or how long it took. The first thing the user
sees at the end of a run is a wall of small mono digits.

The redesign keeps every datum the existing view already shows and
adds the headline framing the existing one omits: a verdict that reads
in one glance, the four numbers the user actually cares about (tokens,
cost, time, rounds), a head-to-head per-agent comparison, the
per-agent critique tally with an expandable per-kind drill-down, and a
download button for the final document. The legacy tables stay,
demoted under a collapsed disclosure for users who want the raw cut.

The redesign also closes three behaviour gaps with the current tab:

1. **The Summary tab is reachable only by manual click**, even at the
   moment the run finishes. We should auto-snap to it on the
   `running → terminal` transition.
2. **The tab is hidden during the run** but treats every terminal
   state identically once shown. `deadlocked` and `errored` runs need
   the same layout with status-specific framing in the hero band —
   not a separate page, not a degraded view.
3. **The current verdict double-counts `resolved-both` disagreements**
   in the per-agent rows of the proposed v1 mockup. The new tally
   excludes mutual resolutions from the per-agent rows and surfaces
   them as their own header stat.

Spec 0046's "no empty columns, drop empty kinds" structural decision
stays — the new per-agent tally inherits it (rows whose kind is empty
just stay at zero rather than vanishing) and the legacy tables under
the disclosure are byte-identical to today's render.

## Current-state audit

### What renders today (Summary tab body)

| File | Line | Role |
|---|---|---|
| `src/dual_research/ui/static/run-detail.jsx` | 7174 | `function CritiqueSummaryView({ run, questions, disagreements })` — the function this spec replaces. |
| `src/dual_research/ui/static/run-detail.jsx` | 7181 | `PHASE_KIND_ORDER` — which kinds each phase emits (Phase 2 → Q/D; Phase 4 → I/C/D). Reused verbatim by the drill-down. |
| `src/dual_research/ui/static/run-detail.jsx` | 7195–7249 | `renderPhase(label, pid)` — the per-phase section header + table list. Reused verbatim by the drill-down. |
| `src/dual_research/ui/static/run-detail.jsx` | 7251–7285 | `highestLeverageThread` `useMemo` — picks the question/issue with the most ghosted rounds. Reused verbatim. |
| `src/dual_research/ui/static/run-detail.jsx` | 7287–7349 | `summaryCopy` `useMemo` — generates the three-sentence summary string. The generator stays; we relocate the rendered copy from a plain `<Markdown>` line into a quote-style featured block. |
| `src/dual_research/ui/static/run-detail.jsx` | 7351–7392 | The current render body — `<Markdown text={summaryCopy} />` + the highest-leverage thread + two `renderPhase` calls. Replaced. |
| `src/dual_research/ui/static/run-detail.jsx` | 7400–7491 | `function SummaryKindTable(…)` — the per-round/per-agent table. Untouched; called by `renderPhase` inside the drill-down. |
| `src/dual_research/ui/static/run-detail.jsx` | 7095–7163 | `_envelopesForKind`, `_buildKindRows` — pure helpers that produce the row arrays the legacy tables consume. Untouched. |

### Tab gating + initial-tab logic

| File | Line | Role |
|---|---|---|
| `src/dual_research/ui/static/run-detail.jsx` | 6396–6398 | `isTerminal = run.status === 'completed' \|\| 'deadlocked' \|\| 'errored'`. Stays; we also treat `'converged'` as terminal (covered in the proposed change). |
| `src/dual_research/ui/static/run-detail.jsx` | 6402–6409 | `CritiqueExplorer.initial` — picks `selectedPhase` from `{0, 2, 4}` based on `run.phase` / `haveAny`. The new auto-jump effect overrides this once when the run transitions to a terminal state. |
| `src/dual_research/ui/static/run-detail.jsx` | 6410 | `const [selectedPhase, setSelectedPhase] = React.useState(initial)` — same state. The new effect calls `setSelectedPhase('summary')` exactly once per `(run.id, terminal-transition)` pair. |
| `src/dual_research/ui/static/run-detail.jsx` | 6423–6425 | Existing guard: `if (selectedPhase === 'summary' && !isTerminal) setSelectedPhase(initial)` — kicks the user out of summary if status reverts. Stays. |
| `src/dual_research/ui/static/run-detail.jsx` | 6731–6737 | The `phase-tab` button for `'summary'`, rendered only when `isTerminal`. Stays. |

### Run-level data the new layout consumes

| Field | Source | Used by |
|---|---|---|
| `run.agents.{claude,gpt}.tokens.{in,out}` | aggregator (models.py:75–96) | tokens-burned tile + agent cards |
| `run.agents.{claude,gpt}.cost` | aggregator | spent tile + agent cards |
| `run.phaseTimings` | per-phase wallclock | elapsed tile |
| `run.round.current` | run state | rounds tile (fallback when items list is empty) |
| `run.topic` | brief | hero topic line |
| `run.id` | run state | footer markdown URL + run-id chip |
| `run.status` | run state | hero variant selection |
| `run.questions / disagreements / issues / comments` | per-phase parsers | every tally on the page |
| `run.phaseLedgers[phase]` | spec 0043 / 0057 | drift count, highest-leverage thread |
| `SearchIndexContext` summary | spec 0036 / 0038 | web-searches tile (new) |
| `final.document` artifact | spec 0117 (artifact registry) | footer download button → `/api/runs/{id}/files/final.md` |

No new fields. Every value the v2 layout shows is already in the run
snapshot or the existing `SearchIndexContext`. The redesign is pure
re-presentation.

### Icon + primitive inventory available

| Primitive | Source | Used where |
|---|---|---|
| `Mdi name={…} size={…} color={…}` | `static/icons.jsx:100` | every glyph in the new layout |
| `AgentIcon agent={'claude'\|'gpt'} variant={'ghost'\|'solid'}` | `shared.jsx:80` | head-to-head cards, per-row in critique outcomes |
| `Dot color={…} size={…}` | `shared.jsx:22` | kept for the per-kind dots inside expansions only |
| `Markdown text={…}` | `shared.jsx:334` | the three-sentence story block |
| `QuestionThread …` | `shared.jsx` | highest-leverage thread (untouched call site) |
| `SmallStat label value color` | `run-detail.jsx:7533` | per-agent stats row inside head-to-head cards |
| `SummaryKindTable kind items rows totalOpen totalResolved` | `run-detail.jsx:7400` | drill-down tables only |
| `fmt.{tokens, cost, costShort, duration}` | `shared.jsx:584` | every numeric format on the page |
| `COLORS.{ok, warn, err, info, agentA, agentB}` | `shared.jsx:5` | tonal palette |

Available MDI names confirmed in `icons.jsx`: `shimmer`, `alert`,
`alert-circle`, `compare`, `help-circle`, `check`, `check-bold`,
`chevron-right`, `chevron-down`, `arrow-up`, `lightning`,
`currency-usd`, `timer`, `history`, `magnify`, `format-quote`,
`download`, `content-copy`, `chart-line`, `list`, `pause`. Every glyph
this spec uses is in that set.

## Proposed change

### 5.1 Component restructure

Replace `CritiqueSummaryView` (run-detail.jsx:7174–7393) with the new
implementation already staged as the v2 mockup. The new function
keeps the same `(run, questions, disagreements)` signature so the call
site at `run-detail.jsx:6831` is unchanged.

Three new sibling helpers live immediately after
`CritiqueSummaryView`, before the existing `SummaryKindTable`:

1. **`StatTile({ icon, label, value, hint })`** — one cell in the
   headline stat grid. Top-right corner glyph, big mono value, small
   uppercase label, optional mono hint underneath.

2. **`AgentSummaryCard({ agent, run, stats, items })`** — one cell in
   the head-to-head row. `AgentIcon` ghost tile + name + model id;
   four `SmallStat` chips for tokens, cost, raised, conceded; a 4-px
   horizontal bar showing this agent's share of total token spend.

3. **`CritiqueBreakdown({ questions, disagreements, issues, comments })`**
   — the four expandable rows.

The full source for these four functions is what's currently in the
working tree under the `SPEC-0152` marker; the spec captures the
behaviour and constraints rather than re-pasting the code.

### 5.2 Stat computation (deterministic, deduplicated)

A single `useMemo` inside `CritiqueSummaryView` derives every number
the layout needs. Pure function of `(run, questions, disagreements,
issues, comments)`:

```
cTok = (claude.tokens.in || 0) + (claude.tokens.out || 0)
gTok = (gpt.tokens.in    || 0) + (gpt.tokens.out    || 0)
totalTokens  = cTok + gTok
totalCost    = (claude.cost || 0) + (gpt.cost || 0)
elapsedTotal = sum(filter(truthy, run.phaseTimings.values()))      // seconds
roundCount   = max(round across all items) || run.round.current || 0

totalItems    = questions.length + disagreements.length + issues.length
totalResolved = #(q.status !== 'open') + #(d.status starts 'resolved') + #(i.status === 'resolved')
resolveRatio  = totalItems > 0 ? totalResolved / totalItems : 1

driftCount = Σ entries in run.phaseLedgers[*] with ghostedRounds > 0
driftRatio = totalItems > 0 ? driftCount / totalItems : 0
```

Verdict (tightened — `>= 0.85` is the new green threshold; see §5.6
for why):

```
totalItems === 0                              → 'Inconclusive'
resolveRatio >= 0.85 AND driftRatio < 0.2     → 'Mostly positive'
resolveRatio <  0.40 OR  driftRatio >= 0.40   → 'Mostly negative'
otherwise                                     → 'Mixed'
```

Disagreement outcome buckets (used by the per-agent "conceded" stat
in §5.3 and the mutual stat in §5.4):

```
claudeYielded = #(d.status === 'resolved-claude')
gptYielded    = #(d.status === 'resolved-gpt')
mutualAligned = #(d.status === 'resolved-both')
stillOpen     = #(d.status === 'open')
```

### 5.3 Critique outcomes — deduplicated per-agent tally

The single most-discussed change. The mockup v1 attributed
`resolved-both` to both agents' "solved" rows; this spec forbids that.

**Tally rule (locked):**

```
For each item:
  raised:
    raisedBy === 'claude'  →  claude.raised[kind]++
    raisedBy === 'gpt'     →  gpt.raised[kind]++
    raisedBy === 'both'    →  claude.raised[kind]++   (and gpt.raised[kind]++)

  solved (only when the item is closed):
    closer === 'claude'    →  claude.solved[kind]++
    closer === 'gpt'       →  gpt.solved[kind]++
    closer === 'both'      →  (NEITHER row increments — counted separately as mutualAligned)
```

Where `closer` is derived per-kind:

| Kind | Closer |
|---|---|
| Question | `answeredBy` (only when `status !== 'open'`) |
| Disagreement | `'claude'` / `'gpt'` / `'both'` extracted from `status === 'resolved-{X}'` (the yielder; spec 0119 §7) |
| Issue | `raisedBy` (always; per spec-0046 envelope code — raiser self-resolves) |
| Comment | never closed — not counted in `solved` |

`raisedBy === 'both'` (which only Disagreements ever produce) still
credits both agents on the **raised** side. That's intentional: both
co-raised the disagreement. On the **solved** side, the symmetric
case is `closer === 'both'` (i.e. `resolved-both`), and the spec
moves that count to its own surface (§5.4).

Section header copy:

```
CRITIQUE OUTCOMES    {totalRaised} raised · {claudeSolved + gptSolved} solved · {mutualAligned} aligned
```

The four-row totals now sum exactly to header `raised` and `solved` —
no double-counting, no hidden discrepancy. `aligned` is a third,
calm, mono stat right-aligned on the header line. Hover tooltip on
the word "aligned": _"Disagreements both agents shifted on — neither
yielded."_

`totalRaised` and `totalSolved` semantics for the header (and for
agreement with the hero's `resolveRatio`):

```
totalRaised = questions.length + disagreements.length + issues.length + comments.length
totalSolved = #(q.status !== 'open')
            + #(d.status starts 'resolved')          // includes resolved-both
            + #(i.status === 'resolved')
```

i.e. `totalSolved` keeps treating `resolved-both` as a closed
disagreement for the resolution-rate math (correct — it is closed),
but the per-agent rows below it count only single-agent closures.

**Per-row layout** (each independently expandable, default
collapsed):

| Row | Aggregate | Sub-rows when expanded |
|---|---|---|
| Claude · ↑ critique raised | sum of `claude.raised[q,d,i,c]` | one per kind, kind dots (info/warn/err/muted) |
| Claude · ✓ critique solved | sum of `claude.solved[q,d,i]` | one per kind; comments omitted (no closure) |
| GPT · ↑ critique raised | sum of `gpt.raised[q,d,i,c]` | one per kind |
| GPT · ✓ critique solved | sum of `gpt.solved[q,d,i]` | one per kind; comments omitted |

Row chrome: rotating `chevron-right` (90° on open) · `AgentIcon`
ghost tile (16 px) · agent name · agent dot of the action color ·
action icon (`arrow-up` for raised in warn / amber; `check` for
solved in ok / sage) · action label · right-aligned big mono count.

### 5.4 Hero — status-aware band

The hero band always renders for terminal runs. Its content varies
by `run.status` (treating `converged` as a synonym of `completed`):

| Status | Cheer line | Glyph | Verdict text | Explanation line |
|---|---|---|---|---|
| `completed` / `converged` | "Run complete · nice work" / "…plenty to chew on" / "Run complete" / "Run complete · with some loose ends" (driftCount > 0) | `shimmer` / `alert-circle` / `compare` / `help-circle`, color-keyed | computed verdict | `{N}% of critique items resolved · {drift} drifted` (drift suffix only if > 0) |
| `deadlocked` | "Run deadlocked · ran out of rounds" | `pause` in warn (amber) | computed verdict (typically Mixed/Mostly negative at this point) | `Hit the hard cap of {run.round.hard} rounds with {N} items still open.` |
| `errored` | "Run errored at {run.error.where}" | `alert` in err (red) | **`Incomplete`** (replaces computed verdict) | `{run.error.detail}` (verbatim) on its own line; `code: {run.error.code}` rendered as a small mono tag underneath. `run.error` is the structured `TopLevelError` payload (`{when, where, code, detail}`) the aggregator already attaches when `status === 'errored'` (`models.py:349, 704`). Stat tiles + agent cards + critique outcomes still render against whatever data was captured. |

The verdict-tone palette extends to include the errored case:

| State | Color | Bg | Border |
|---|---|---|---|
| Mostly positive | `COLORS.ok` (#6fb380) | `+ '1A'` | `+ '55'` |
| Mostly negative | `COLORS.warn` (#d4a056) | `+ '1A'` | `+ '55'` |
| Mixed | `COLORS.info` (#6b9cf0) | `+ '1A'` | `+ '55'` |
| Inconclusive | `var(--md-on-surface-muted)` | `var(--md-surface-container-low)` | `var(--md-outline-hair)` |
| Errored | `COLORS.err` (#d96a6a) | `+ '1A'` | `+ '55'` |

Topic line treatment is unchanged: `format-quote` glyph (alpha 0.55,
muted) + serif italic in `--md-font-brand`, max-width 760 px.

**Deadlocked promotion of highest-leverage thread.** When `run.status
=== 'deadlocked'`, the highest-leverage open item is rendered
immediately under the hero band (above the headline stat grid)
instead of in its default position between critique outcomes and the
per-round disclosure. The deadlock _is_ that item; show it where the
explanation lives.

### 5.5 Auto-jump on terminal transition

A new `useEffect` inside `CritiqueExplorer` watches `isTerminal`.
When it transitions `false → true`, the effect snaps the active tab
to summary unless the user has manually picked a different tab during
this session:

```js
const userPickedTabRef = React.useRef(false);
const wasTerminalRef   = React.useRef(isTerminal);

React.useEffect(() => {
  if (!wasTerminalRef.current && isTerminal && !userPickedTabRef.current) {
    setSelectedPhase('summary');
  }
  wasTerminalRef.current = isTerminal;
}, [isTerminal]);
```

`userPickedTabRef.current` flips to `true` whenever any phase-tab
button is clicked — wrap the four `onClick` handlers at lines
6716–6736 to set the ref before delegating to `setSelectedPhase`.

The ref resets on `run.id` change (handled by the existing
`useEffect(() => { setSelectedPhase(initial); … }, [run.id, initial])`
at line 6414 — extend it to also reset both refs).

Auto-jump fires at most once per `(run, browser-session)` pair. The
existing terminal-status-revert guard at line 6423 stays in place —
if the backend ever flips a `completed` run back to `running` (it
shouldn't, but) the user is yanked out of Summary as before.

### 5.6 Confetti

Single-shot animation triggered when **all four** of these hold on
first land:

1. `selectedPhase === 'summary'` (the user is on the tab)
2. `isTerminal === true`
3. `verdict === 'Mostly positive'` (i.e. `resolveRatio >= 0.85 AND
   driftRatio < 0.2`)
4. `localStorage.getItem('dr-confetti-' + run.id) !== '1'` (not yet
   played for this run in this browser)

On fire: set the localStorage flag, then run a ~600 ms particle
burst originating at the verdict glyph's screen position. Sage +
sable + cream particles to match the design tokens. No external
library — small `<canvas>` or DOM-span implementation, kept under
~80 lines and self-contained.

Respect `prefers-reduced-motion: reduce` — if the media query
matches, the localStorage flag is still set (so we don't fire later
either) and the burst is skipped.

### 5.7 Headline stat grid — five tiles

Auto-fit grid: `repeat(auto-fit, minmax(150px, 1fr))`. Collapses
5 → 3 → 2 → 1 as viewport narrows.

| Tile | Icon | Value | Hint |
|---|---|---|---|
| tokens burned | `lightning` | `fmt.tokens(totalTokens)` | `{fmt.tokens(cTok)} + {fmt.tokens(gTok)}` |
| spent | `currency-usd` | `fmt.costShort(totalCost)` | `{fmt.costShort(cCost)} · {fmt.costShort(gCost)}` |
| elapsed | `timer` | `fmt.duration(elapsedTotal)` or `—` | (none) |
| rounds | `history` | `R{roundCount}` or `—` | `{totalItems} items debated` (omit if 0) |
| web searches | `magnify` | `{queries}` or `—` | `{urls} URLs retrieved` |

Web search source: read `SearchIndexContext` (`run-detail.jsx:208`,
the `summary` Map already populated by `useSearchIndex`). Sum
`queries` and `consulted` across all entries. If the context has
nothing (legacy snapshots, web search disabled), render `—` for the
value and omit the hint — keeps the grid stable.

### 5.8 Footer

Top-border separator. Flex row, wraps on narrow viewports.

| Slot | Content |
|---|---|
| Primary | Verdict-colored button (`background: verdictTone.color`, white text). `download` icon + "Download final document (.md)". Hover lifts by 1 px. Click triggers a programmatic `<a download>` against `/api/runs/{run.id}/files/final.md`. |
| Secondary | Outlined button, `content-copy` icon + "Copy summary". On click: copies the plain-text version of `summaryCopy` (with `**` stripped) via `navigator.clipboard.writeText`. Swaps to `check` glyph + "Copied!" for 1.4 s then reverts. |
| Right-anchored | `run {run.id}` in mono, muted. |

**Final-doc-missing handling.** Deadlocked / errored runs may not
have produced `final.md`. On mount of the Summary tab, the footer
issues a `HEAD /api/runs/{id}/files/final.md` and stashes the result
in component state. If `404`, the primary button renders in disabled
state (opacity 0.5, `cursor: not-allowed`, no hover lift) with a
`title` tooltip: _"No final document was produced for this run."_

### 5.9 Per-round breakdown — collapsible drill-down

The legacy `SummaryKindTable`-driven view stays byte-identical, just
collapsed by default behind a single toggle button:

- Rotating `chevron-right` (90° on open)
- `chart-line` glyph
- Label "Per-round breakdown" + small mono subtitle
  "raised / resolved by round, per model"
- Body renders `renderPhase('Phase 2 — Negotiate', 2)` and
  `renderPhase('Phase 4 — Review', 4)` only when `showTables === true`.

No data behaviour changes inside the tables.

### 5.10 Icons inventory (locked names)

Every icon used in the spec, with intended placement:

| Where | Glyph | Notes |
|---|---|---|
| Hero cheer line lead | `check-bold` | small (12 px), verdict color |
| Hero verdict glyph | `shimmer` / `alert-circle` / `compare` / `help-circle` / `pause` / `alert` | 32 px, status-keyed (see §5.4 table) |
| Hero topic line lead | `format-quote` | 14 px, muted, alpha 0.55 |
| Stat tile (each) | `lightning` / `currency-usd` / `timer` / `history` / `magnify` | 16 px, top-right corner, opacity 0.6 |
| Agent card | `AgentIcon` brand tile (ghost) | 20 px |
| Story block lead | `format-quote` | 20 px, verdict color, alpha 0.7 |
| Critique outcomes header | `list` | 14 px, muted |
| Critique outcomes per-row | `AgentIcon` (16 px ghost) + `arrow-up` / `check` (12 px) | per row |
| Critique outcomes sub-row | `Dot` (6 px) | kept as a dot, not an icon |
| Highest-leverage header | `alert-circle` | 14 px, warn |
| Per-round toggle | `chevron-right` (rotating) + `chart-line` | both 14 px |
| Footer download | `download` | 14 px, white |
| Footer copy (idle) | `content-copy` | 14 px, currentColor |
| Footer copy (just-copied) | `check` | 14 px, currentColor |

## Edge cases & states

| Case | Behaviour |
|---|---|
| Run still running (any non-terminal) | Summary tab hidden by existing gate at line 6731. No change. |
| `completed` with 0 items raised | Hero → "Inconclusive" (Inconclusive palette). Stat tiles render normally. Critique outcomes section hidden (`stats.totalItems > 0` gate). Story line generator already handles this: "no critique items were raised in this run." |
| `completed` with items but 0 resolved | Verdict → "Mostly negative". Outcomes section renders with all four rows; per-kind sub-rows show `—` for the solved bucket. |
| `deadlocked`, items present | Hero → deadlocked variant. Highest-leverage thread promoted above the stat grid. Everything else renders normally. |
| `errored` mid-Phase | Hero → errored variant. Stat tiles + agent cards + outcomes still render against partial data. The error explanation line names the phase. |
| `final.md` missing | Download button disabled with tooltip (§5.8). Other actions unaffected. |
| Re-fetch / live snapshot updates | Every derived value lives in `useMemo`; recomputes on snapshot change. Confetti localStorage flag prevents re-fire on snapshot bumps. |
| Status reverts (terminal → running) | Existing guard at line 6423 yanks the user out of Summary. No regression. |
| User picks a non-summary tab while running, then run finishes | Auto-jump suppressed (`userPickedTabRef` set). Σ tab remains highlighted as available. |
| User reloads page after a green run | Confetti does not re-fire (localStorage flag). Page renders with verdict-colored hero. |
| `prefers-reduced-motion: reduce` | Confetti skipped; localStorage flag still written so the gate doesn't keep retrying. Hover transitions still fire (low-amplitude). |

## Accessibility

- Every expandable row is a `<button type="button" aria-expanded={isOpen}>`
  (already true in the mockup).
- Decorative glyphs in the hero, stat tiles, and section headers
  carry `aria-hidden="true"`. `AgentIcon` already emits `aria-label`
  for identification contexts — keep that, mark the rest decorative.
  Extend `Mdi` (icons.jsx:100) to accept an `ariaHidden` prop if it
  doesn't already; the new layout passes it on every decorative
  glyph.
- Verdict text is the accessible label — the glyph reinforces, not
  replaces.
- Focus order: hero → stat tiles (non-interactive) → agent cards
  (non-interactive) → story (non-interactive) → critique outcomes
  (each row focusable) → highest-leverage thread (existing focusable
  card) → per-round toggle → footer buttons.
- Confetti has no semantic content. The verdict text + cheer line
  carry the celebratory affordance for AT users.
- Color contrast: the verdict-tint backgrounds (`+ '1A'`, ~10 %
  alpha) must clear AA against the verdict-color foreground in both
  themes. Verify during the light-mode pass (§7).

## Responsive behaviour

- Inner container max-width: 980 px. Larger viewports get the
  whitespace, not a stretched layout.
- Stat grid: `auto-fit minmax(150px, 1fr)` → 5 → 3 → 2 → 1 cols.
- Agent cards: `auto-fit minmax(280px, 1fr)` → 2 → 1.
- Critique outcomes: single-column native. Sub-row indentation
  (`paddingLeft: 38`) stays at all widths.
- Hero band wraps cleanly: verdict glyph + text, then resolution
  stat, then topic on its own line.
- Footer wraps with `flex-wrap` — run-id chip drops to a new line
  on narrow viewports rather than overflowing.

Validate at 1280, 768, 375 px during implementation.

## Dark mode / light mode

Built and verified in dark. All colors are CSS-var-driven; the only
hard-coded values are the `COLORS.*` HEX bases (which work in both
themes by virtue of how the `+ '1A'` / `+ '55'` alpha extensions
composite onto whatever surface they sit on).

The light-mode pass needs to check, specifically:

- Hero verdict tint bg + border contrast against the bright surface
- Story block left-border + format-quote glyph against bright bg
- Stat tile glyph (opacity 0.6) against bright surface
- AgentIcon ghost variant readability (uses `meta.color + '1f'`
  background + `meta.color + '55'` border — verified dark, unchecked
  light)
- The download button's primary background (verdict color, white
  text) — white text on `COLORS.ok` (#6fb380) is the lowest-contrast
  combination; check AA.

Anything that fails contrast picks up a per-theme overrider via the
existing token system.

## Implementation order

1. Replace `CritiqueSummaryView` body + add `StatTile`,
   `AgentSummaryCard`, `CritiqueBreakdown` siblings.
   _(The working tree already has this as a v1 mockup; this step is
   a polish + dedup-tally fix, not a from-zero implementation.
   `Mdi` already emits `aria-hidden=true` on every SVG by default —
   `icons.jsx:105, 109, 122` — so no a11y prop extension is needed;
   the brand glyphs that need labels go through `AgentIcon`, which
   already emits `aria-label` correctly per `shared.jsx:67`.)_
2. Fix the `CritiqueBreakdown` tally per §5.3 — drop the `'both'`
   branch from the solved-side `bump`, surface `mutualAligned` in
   the header.
3. Add the web-searches stat tile (§5.7) — pull `SearchIndexContext`
   in the `CritiqueSummaryView` body.
4. Add the status-aware hero variants (§5.4) — extend
   `verdictTone`, add the deadlocked/errored cheer + glyph + bottom
   line. Read `run.error.{where, code, detail}` for the errored
   variant.
5. Promote highest-leverage thread above the stat grid when
   `run.status === 'deadlocked'`.
6. Add the auto-jump effect + `userPickedTabRef` (§5.5).
7. Add the final-doc HEAD check + disabled-state for the download
   button (§5.8).
8. Add the confetti primitive + first-land gate (§5.6).
9. Tighten the green-verdict threshold to `0.85` (§5.2).
10. Light-mode pass + mobile pass (375 px, 768 px).
11. Update `static/how-it-works.jsx` Summary description to reflect
    the new layout (the existing entry references the per-round
    table format).
12. Replace the `SPEC-0152` placeholder marker comments in
    `run-detail.jsx` with the canonical `Spec 0152` form used
    elsewhere in the file.

Each step is independently shippable; gate later steps behind earlier
ones in the PR.

## Testing

No backend changes → no contract tests touched. UI behaviour is
asserted via the existing pattern:

1. **Pure-function unit tests** for the new tally + verdict
   computation. Extract `_computeSummaryStats(run, questions,
   disagreements, issues, comments)` into a top-level helper so it's
   testable without a React tree. Cases:
   - all-resolved run (verdict = Mostly positive at ≥ 0.85, Mixed
     between 0.4–0.85)
   - all-open run (Mostly negative)
   - run with only `resolved-both` disagreements (rows show 0 in
     solved buckets; header shows mutualAligned correctly)
   - run with `raisedBy === 'both'` disagreements (both raised
     counts incremented)
   - drift-heavy run (≥ 40 % drift → Mostly negative even with high
     resolution)
   - errored mid-Phase 2 (verdict frozen to "Incomplete"
     downstream — but stats still compute against partial data)

2. **Snapshot test** of `CritiqueBreakdown` rendering for a fixed
   `(questions, disagreements, issues, comments)` fixture covering
   all three statuses on disagreements + a `'both'`-raiser case.

3. **Manual UAT** against the live preview at
   `http://localhost:6173/#/runs/{id}` for each terminal state:
   `completed`, `deadlocked`, `errored`. Verify auto-jump, confetti
   threshold, final-doc-missing handling, light-mode contrast.

4. **`how-it-works.jsx` content sync** — the changelog/feature
   description must match the shipped layout.

## Out of scope

Explicitly deferred to later specs:

- Cross-run analytics (streaks, personal records, "your N-th run on
  this topic").
- Postcard / poster mode for screenshot-sharing.
- Sentiment / cost / token sparklines under each stat tile.
- Final-draft preview teaser above the download button.
- v1-vs-final diff stat.
- "Share permalink" / "Branch from here" footer actions.
- Achievement badges ("Drift-free", "Mutual agreement").
- LLM-generated narrative blocks beyond the existing 3-sentence
  generator.

## Open ends (not blockers)

- **Deadlocked highest-leverage cardinality.** Currently the
  promoted thread is one item. For a deadlocked run with multiple
  drifted items, surfacing 2–3 in the promoted slot might explain
  the failure better. Defaulting to one for v2; revisit after first
  real deadlock screenshot.

- **`TopLevelError` field naming in the snake → camel transform.**
  `models.py` declares `error: TopLevelError | None` on `Run`
  (`models.py:704`); the existing snake-to-camel JSON serializer
  used elsewhere in the project would expose this as `run.error` on
  the JS side with `{when, where, code, detail}` already in the
  right shape. Verify on the first errored run snapshot during
  implementation; no code change expected.

---

End of spec.

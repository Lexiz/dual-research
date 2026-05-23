---
kind: dev
spec: "0175"
slug: summary-tab-v2
title: Summary tab v2 — celebratory close-out with verdict, stats, critique outcomes, and markdown download
type: new-feature
label: new-feature
version_bump: MINOR
target_version: 1.35.0
status: deployed
queue_position: 1
depends_on: ["0168", "0172"]
complexity: M
created: 2026-05-22
queued_at: "2026-05-22T22:30:00Z"
started_at: "2026-05-23T09:02:17Z"
merged_at: "2026-05-23T09:19:39Z"
deployed_at: "2026-05-23T09:23:44Z"
pr: "https://github.com/Lexiz/dual-research/pull/203"
handover: "handoffs/2026-05-23-spec-0175-summary-tab-v2.md"
failure_step: ""
source_session: pre-lifecycle-bootstrap
promoted_from_draft: "001"
---

# Spec 0175 — Summary tab v2 — celebratory close-out with verdict, stats, critique outcomes, and markdown download

> **Type:** new-feature  |  **Complexity:** M  |  **Depends on:** [spec 0168](specs/0168-critique-pane-item-card-refresh.md) (M3 card chrome + ID-chip-drop rule on item cards — same chrome language reused for stat tiles and agent cards), [spec 0172](specs/0172-critique-card-drop-id-chip-and-fix-markdown-title-rendering.md) (literal `**` markdown fix + ID-chip-drop applied — the new summary header chip pattern follows the same rule)
> **Bump:** MINOR — significant additive user-facing surface on the Summary tab; no wire-format / schema change.
> **Evidence:** the existing `CritiqueSummaryView` body in [`src/dual_research/ui/static/run-detail.jsx:7624`](src/dual_research/ui/static/run-detail.jsx) renders the per-phase × per-kind tables created by spec 0046 D5; this spec promotes the run close-out from "data dump" to "celebratory verdict + stats + drill-down". The structural pieces this spec inherits and respects: spec 0046 D5 (per-kind × per-round tables — kept verbatim as the drill-down), spec 0057 D6 (highest-leverage open thread — promoted on deadlocks), spec 0068 (`BrandMark` / `AgentIcon` primitive — reused per [DS SPEC §3 Primitives — BrandMark / AgentIcon](design-system/SPEC.md)), spec 0072 D7–D10 (three-sentence summary copy generator — relocated into a featured quote block), spec 0117 (artifact registry — `final.document` is the markdown the footer downloads), spec 0119 §7 (canonical `resolved-*` vocabulary — `resolved-claude` = Claude yielded), spec 0138 §5.3 (run-id pill click-to-copy — reused in the footer), spec 0141 (critique-aggregation integrity — same `_envelopesForKind` / `_buildKindRows` helpers feed the drill-down tables), spec 0165 §2.5 (`fmtCost2` — sub-cent display).

---

## 1. Context

The Summary tab is the user's payoff after watching two agents argue across rounds. The current implementation (spec 0046 D5) renders the summary as four per-phase, per-kind HTML tables stacked under a three-sentence verdict line. It's accurate but joyless: scanning the tables doesn't tell you whether the run went well, who carried the weight, what it cost, or how long it took. The first thing the user sees at the end of a run is a wall of small mono digits.

The redesign keeps every datum the existing view already shows and adds the headline framing the existing one omits: a verdict that reads in one glance, the four numbers the user actually cares about (tokens, cost, time, rounds), a head-to-head per-agent comparison, the per-agent critique tally with an expandable per-kind drill-down, and a download button for the final document. The legacy tables stay, demoted under a collapsed disclosure for users who want the raw cut.

The redesign also closes three behaviour gaps with the current tab:

1. **The Summary tab is reachable only by manual click**, even at the moment the run finishes. We should auto-snap to it on the `running → terminal` transition.
2. **The tab is hidden during the run** but treats every terminal state identically once shown. `deadlocked` and `errored` runs need the same layout with status-specific framing in the hero band — not a separate page, not a degraded view.
3. **The current verdict double-counts `resolved-both` disagreements** in the per-agent rows of the proposed v1 mockup. The new tally excludes mutual resolutions from the per-agent rows and surfaces them as their own header stat (per the [`resolved-both` semantics codified in spec 0119 §7](design-system/SPEC.md) and the [§9.5 canonical vocabulary](design-system/SPEC.md)).

Spec 0046's "no empty columns, drop empty kinds" structural decision stays — the new per-agent tally inherits it (rows whose kind is empty just stay at zero rather than vanishing) and the legacy tables under the disclosure are byte-identical to today's render.

### 1.1 — Current-state audit (after specs 0168 + 0172)

#### What renders today (Summary tab body)

| File | Line | Role |
|---|---|---|
| [`src/dual_research/ui/static/run-detail.jsx:7624`](src/dual_research/ui/static/run-detail.jsx) | function head | `function CritiqueSummaryView({ run, questions, disagreements })` — the function this spec replaces. |
| [`src/dual_research/ui/static/run-detail.jsx:7631`](src/dual_research/ui/static/run-detail.jsx) | const | `PHASE_KIND_ORDER` — which kinds each phase emits (Phase 2 → Q/D; Phase 4 → I/C/D). Reused verbatim by the drill-down. |
| [`src/dual_research/ui/static/run-detail.jsx:7545`](src/dual_research/ui/static/run-detail.jsx) | helper | `_envelopesForKind` — pure helper. Untouched. |
| [`src/dual_research/ui/static/run-detail.jsx:7595`](src/dual_research/ui/static/run-detail.jsx) | helper | `_buildKindRows` — pure helper feeding the drill-down. Untouched. |
| [`src/dual_research/ui/static/run-detail.jsx:7850`](src/dual_research/ui/static/run-detail.jsx) | function | `SummaryKindTable` — per-round/per-agent table. Untouched; called by `renderPhase` inside the drill-down. |
| [`src/dual_research/ui/static/run-detail.jsx:7283`](src/dual_research/ui/static/run-detail.jsx) | call site | `<CritiqueSummaryView … />` — the call site stays unchanged (same `(run, questions, disagreements)` signature). |

#### Tab gating + initial-tab logic

| File | Line | Role |
|---|---|---|
| [`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) ~6820–6822 | const | `isTerminal = run.status === 'completed' || 'deadlocked' || 'errored'`. Stays; this spec also treats `'converged'` as terminal (covered in §2.4). |
| [`src/dual_research/ui/static/run-detail.jsx:6823`](src/dual_research/ui/static/run-detail.jsx) | local | `initial` — picks `selectedPhase` from `{0, 2, 4}` based on `run.phase` / `haveAny`. (Note: this is a local variable inside `CritiqueExplorer`, not an object property.) The new auto-jump effect (§2.5) overrides this once when the run transitions to a terminal state. |
| [`src/dual_research/ui/static/run-detail.jsx:7133`](src/dual_research/ui/static/run-detail.jsx) | JSX | The `phase-tab` button for `'summary'`, rendered only when `isTerminal`. Stays. |

#### Run-level data the new layout consumes

| Field | Source | Used by |
|---|---|---|
| `run.agents.{claude,gpt}.tokens.{in,out}` | aggregator ([`models.py:75–96`](src/dual_research/models.py)) | tokens-burned tile + agent cards |
| `run.agents.{claude,gpt}.cost` | aggregator | spent tile + agent cards |
| `run.phaseTimings` | per-phase wallclock | elapsed tile |
| `run.round.current` | run state | rounds tile (fallback when items list is empty) |
| `run.topic` | brief | hero topic line |
| `run.id` | run state | footer markdown URL + run-id chip |
| `run.status` | run state | hero variant selection |
| `run.questions / disagreements / issues / comments` | per-phase parsers | every tally on the page |
| `run.phaseLedgers[phase]` | spec 0043 / 0057 | drift count, highest-leverage thread |
| `SearchIndexContext` summary | spec 0036 / 0038 | web-searches tile (new) |
| `final.document` artifact | spec 0117 (artifact registry) | footer download → `/api/runs/{id}/files/final.md` |
| `run.error` | aggregator ([`models.py:349`, `:704`](src/dual_research/models.py)) | errored-variant hero copy |

No new fields. Every value the v2 layout shows is already in the run snapshot or the existing `SearchIndexContext`. The redesign is pure re-presentation.

#### Primitive inventory available

| Primitive | Source | Used where in this spec |
|---|---|---|
| `Mdi name={…} size={…} color={…}` | [`src/dual_research/ui/static/icons.jsx:100`](src/dual_research/ui/static/icons.jsx) | every glyph in the new layout |
| `AgentIcon agent={'claude'\|'gpt'} variant={'ghost'\|'solid'}` | [`src/dual_research/ui/static/shared.jsx`](src/dual_research/ui/static/shared.jsx) | head-to-head cards, per-row in critique outcomes |
| `Dot color size` | [`src/dual_research/ui/static/shared.jsx`](src/dual_research/ui/static/shared.jsx) | per-kind dots inside expansions only |
| `Markdown text` | [`src/dual_research/ui/static/shared.jsx`](src/dual_research/ui/static/shared.jsx) | three-sentence story block (and verified safe per spec 0172's Markdown-renders-body fix) |
| `QuestionThread` | [`src/dual_research/ui/static/shared.jsx`](src/dual_research/ui/static/shared.jsx) | highest-leverage thread (untouched call site) |
| `SmallStat label value color` | [`src/dual_research/ui/static/run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) ~7533 | per-agent stats row inside head-to-head cards |
| `fmt.{tokens, cost, costShort, duration}` + `fmtCost2` | [`src/dual_research/ui/static/shared.jsx`](src/dual_research/ui/static/shared.jsx) + spec 0165 §2.5 | every numeric format on the page |
| `COLORS.{ok, warn, err, info, agentA, agentB}` | [`src/dual_research/ui/static/shared.jsx`](src/dual_research/ui/static/shared.jsx) | tonal palette aliases (each maps to a `--p-*` palette token) |

MDI names confirmed in [`icons.jsx`](src/dual_research/ui/static/icons.jsx): `shimmer`, `alert`, `alert-circle`, `compare`, `help-circle`, `check`, `check-bold`, `chevron-right`, `chevron-down`, `arrow-up`, `lightning`, `currency-usd`, `timer`, `history`, `magnify`, `format-quote`, `download`, `content-copy`, `chart-line`, `list`, `pause`. Every glyph this spec uses is in that set.

## 2. Proposed change

### 2.1 — Component restructure

Replace `CritiqueSummaryView` body at [`src/dual_research/ui/static/run-detail.jsx:7624`](src/dual_research/ui/static/run-detail.jsx) with the new implementation. The new function keeps the same `(run, questions, disagreements)` signature so the call site at [`run-detail.jsx:7283`](src/dual_research/ui/static/run-detail.jsx) is unchanged.

Three new sibling helpers live immediately after `CritiqueSummaryView`, before the existing `SummaryKindTable`:

1. **`StatTile({ icon, label, value, hint })`** — one cell in the headline stat grid. Top-right corner glyph, big mono value, small uppercase label, optional mono hint underneath. Renders on the M3 `--md-surface-container-high` surface — same chrome language spec 0168 §2.1 locked in for `.item-card`.

2. **`AgentSummaryCard({ agent, run, stats, items })`** — one cell in the head-to-head row. `AgentIcon` ghost tile + name + model id; four `SmallStat` chips for tokens, cost, raised, conceded; a 4-px horizontal bar showing this agent's share of total token spend. Provider stripe via the same `[data-raised-by]` attribute pattern spec 0168 §2.1 introduced (2 px `--p-sable` for Claude, `--p-sage` for GPT).

3. **`CritiqueBreakdown({ questions, disagreements, issues, comments })`** — the four expandable rows (each a `CollapsibleSection` per [DS SPEC §3 Primitives — CollapsibleSection](design-system/SPEC.md)).

### 2.2 — Stat computation (deterministic, deduplicated)

A single `useMemo` inside `CritiqueSummaryView` derives every number the layout needs. Pure function of `(run, questions, disagreements, issues, comments)`:

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

Verdict (tightened — `>= 0.85` is the new green threshold; see §2.6 for why):

```
totalItems === 0                              → 'Inconclusive'
resolveRatio >= 0.85 AND driftRatio < 0.2     → 'Mostly positive'
resolveRatio <  0.40 OR  driftRatio >= 0.40   → 'Mostly negative'
otherwise                                     → 'Mixed'
```

Disagreement outcome buckets (used by the per-agent "conceded" stat in §2.3 and the mutual stat in §2.4):

```
claudeYielded = #(d.status === 'resolved-claude')
gptYielded    = #(d.status === 'resolved-gpt')
mutualAligned = #(d.status === 'resolved-both')
stillOpen     = #(d.status === 'open')
```

### 2.3 — Critique outcomes — deduplicated per-agent tally

The single most-discussed change. The mockup v1 attributed `resolved-both` to both agents' "solved" rows; this spec forbids that.

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

`raisedBy === 'both'` (which only Disagreements ever produce) still credits both agents on the **raised** side. That's intentional: both co-raised the disagreement. On the **solved** side, the symmetric case is `closer === 'both'` (i.e. `resolved-both`), and the spec moves that count to its own surface (§2.4).

Section header copy:

```
CRITIQUE OUTCOMES    {totalRaised} raised · {claudeSolved + gptSolved} solved · {mutualAligned} aligned
```

The four-row totals now sum exactly to header `raised` and `solved` — no double-counting, no hidden discrepancy. `aligned` is a third, calm, mono stat right-aligned on the header line. Hover tooltip on the word "aligned": _"Disagreements both agents shifted on — neither yielded."_

`totalRaised` and `totalSolved` semantics for the header (and for agreement with the hero's `resolveRatio`):

```
totalRaised = questions.length + disagreements.length + issues.length + comments.length
totalSolved = #(q.status !== 'open')
            + #(d.status starts 'resolved')          // includes resolved-both
            + #(i.status === 'resolved')
```

i.e. `totalSolved` keeps treating `resolved-both` as a closed disagreement for the resolution-rate math (correct — it is closed), but the per-agent rows below it count only single-agent closures.

**Per-row layout** (each independently expandable, default collapsed):

| Row | Aggregate | Sub-rows when expanded |
|---|---|---|
| Claude · ↑ critique raised | sum of `claude.raised[q,d,i,c]` | one per kind, kind dots (info/warn/err/muted) |
| Claude · ✓ critique solved | sum of `claude.solved[q,d,i]` | one per kind; comments omitted (no closure) |
| GPT · ↑ critique raised | sum of `gpt.raised[q,d,i,c]` | one per kind |
| GPT · ✓ critique solved | sum of `gpt.solved[q,d,i]` | one per kind; comments omitted |

Row chrome: rotating `chevron-right` (90° on open) · `AgentIcon` ghost tile (16 px) · agent name · agent dot of the action color · action icon (`arrow-up` for raised in warn / amber; `check` for solved in ok / sage) · action label · right-aligned big mono count. Each row is a `<button type="button" aria-expanded={isOpen}>` per [DS SPEC §3 — CollapsibleSection](design-system/SPEC.md) and [§8 — Accessibility](design-system/SPEC.md).

### 2.4 — Hero — status-aware band

The hero band always renders for terminal runs. Its content varies by `run.status` (treating `converged` as a synonym of `completed`):

| Status | Cheer line | Glyph | Verdict text | Explanation line |
|---|---|---|---|---|
| `completed` / `converged` | "Run complete · nice work" / "…plenty to chew on" / "Run complete" / "Run complete · with some loose ends" (driftCount > 0) | `shimmer` / `alert-circle` / `compare` / `help-circle`, color-keyed | computed verdict | `{N}% of critique items resolved · {drift} drifted` (drift suffix only if > 0) |
| `deadlocked` | "Run deadlocked · ran out of rounds" | `pause` in warn (amber) | computed verdict (typically Mixed/Mostly negative at this point) | `Hit the hard cap of {run.round.hard} rounds with {N} items still open.` |
| `errored` | "Run errored at {run.error.where}" | `alert` in err (red) | **`Incomplete`** (replaces computed verdict) | `{run.error.detail}` (verbatim) on its own line; `code: {run.error.code}` rendered as a small mono tag underneath. `run.error` is the structured `TopLevelError` payload (`{when, where, code, detail}`) the aggregator attaches when `status === 'errored'` ([`models.py:349, 704`](src/dual_research/models.py)). Stat tiles + agent cards + critique outcomes still render against whatever data was captured. |

The verdict-tone palette extends to include the errored case. Every base hex comes from the [DS SPEC §2.1 Palette tokens](design-system/SPEC.md) (`--p-ok`, `--p-warn`, `--p-info`, `--p-err`) — the `COLORS.*` constants in [`shared.jsx`](src/dual_research/ui/static/shared.jsx) are JS-side aliases that resolve to those token base hexes:

| State | Color | Bg | Border |
|---|---|---|---|
| Mostly positive | `COLORS.ok` (= `--p-ok` base) | `+ '1A'` | `+ '55'` |
| Mostly negative | `COLORS.warn` (= `--p-warn` base) | `+ '1A'` | `+ '55'` |
| Mixed | `COLORS.info` (= `--p-info` base) | `+ '1A'` | `+ '55'` |
| Inconclusive | `var(--md-on-surface-muted)` | `var(--md-surface-container-low)` | `var(--md-outline-hair)` |
| Errored | `COLORS.err` (= `--p-err` base) | `+ '1A'` | `+ '55'` |

The `+ '1A'` / `+ '55'` alpha suffix pattern is the JS-side equivalent of the DS-canonical `color-mix(in srgb, var(--p-X) N%, transparent)` recipe used by spec 0168 §2.1 / spec 0165 §2.2; both produce visually-equivalent ~10 % / ~33 % tints. We accept the JS form here because the bg/border colours are derived from a runtime-picked verdict tone, not from a static class — the same pattern other in-`run-detail` tonal overlays use today.

Topic line treatment is unchanged: `format-quote` glyph (alpha 0.55, muted) + serif italic in `var(--md-font-brand)`, max-width 760 px — per [DS SPEC §2.5 Typography](design-system/SPEC.md): "hero text, page-level headings, blockquotes — anything that should read as 'the agent's voice'".

**Deadlocked promotion of highest-leverage thread.** When `run.status === 'deadlocked'`, the highest-leverage open item is rendered immediately under the hero band (above the headline stat grid) instead of in its default position between critique outcomes and the per-round disclosure. The deadlock _is_ that item; show it where the explanation lives.

### 2.5 — Auto-jump on terminal transition

A new `useEffect` inside `CritiqueExplorer` watches `isTerminal`. When it transitions `false → true`, the effect snaps the active tab to summary unless the user has manually picked a different tab during this session:

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

`userPickedTabRef.current` flips to `true` whenever any phase-tab button is clicked — wrap the four `onClick` handlers in the phase-tab cluster (anchored around [`run-detail.jsx:7133`](src/dual_research/ui/static/run-detail.jsx)) to set the ref before delegating to `setSelectedPhase`.

The ref resets on `run.id` change (handled by the existing `useEffect(() => { setSelectedPhase(initial); … }, [run.id, initial])` — extend it to also reset both refs).

Auto-jump fires at most once per `(run, browser-session)` pair. The existing terminal-status-revert guard stays in place — if the backend ever flips a `completed` run back to `running` (it shouldn't, but) the user is yanked out of Summary as before.

### 2.6 — Confetti

Single-shot animation triggered when **all four** of these hold on first land:

1. `selectedPhase === 'summary'` (the user is on the tab)
2. `isTerminal === true`
3. `verdict === 'Mostly positive'` (i.e. `resolveRatio >= 0.85 AND driftRatio < 0.2`)
4. `localStorage.getItem('dr-confetti-' + run.id) !== '1'` (not yet played for this run in this browser)

On fire: set the localStorage flag, then run a ~600 ms particle burst originating at the verdict glyph's screen position. Sage + sable + cream particles to match the [DS SPEC §2.1 Palette](design-system/SPEC.md) (`--p-sage`, `--p-sable`, `--md-surface`). No external library — small `<canvas>` or DOM-span implementation, kept under ~80 lines and self-contained.

Respect `prefers-reduced-motion: reduce` per [DS SPEC §8 Accessibility](design-system/SPEC.md) — if the media query matches, the localStorage flag is still set (so we don't fire later either) and the burst is skipped. Duration of 600 ms sits inside the [§2.11 Motion](design-system/SPEC.md) `medium-2` range; the verdict tone-flash uses the standard `--md-easing-emphasized` curve.

### 2.7 — Headline stat grid — five tiles

Auto-fit grid: `repeat(auto-fit, minmax(150px, 1fr))`. Collapses 5 → 3 → 2 → 1 as viewport narrows.

| Tile | Icon | Value | Hint |
|---|---|---|---|
| tokens burned | `lightning` | `fmt.tokens(totalTokens)` | `{fmt.tokens(cTok)} + {fmt.tokens(gTok)}` |
| spent | `currency-usd` | `fmt.costShort(totalCost)` | `{fmt.costShort(cCost)} · {fmt.costShort(gCost)}` |
| elapsed | `timer` | `fmt.duration(elapsedTotal)` or `—` | (none) |
| rounds | `history` | `R{roundCount}` or `—` | `{totalItems} items debated` (omit if 0) |
| web searches | `magnify` | `{queries}` or `—` | `{urls} URLs retrieved` |

Cost formatting reuses `fmt.costShort` for the headline and hint, **not** `fmt.cost` (4-decimal). For sub-cent values the `costShort` helper already renders `<$0.01` — symmetric with the spec 0165 §2.5 `fmtCost2` rule that the timeline cost chip uses.

Web search source: read `SearchIndexContext` (the `summary` Map already populated by `useSearchIndex` in [`run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx)). Sum `queries` and `consulted` across all entries. If the context has nothing (legacy snapshots, web search disabled), render `—` for the value and omit the hint — keeps the grid stable.

### 2.8 — Footer

Top-border separator. Flex row, wraps on narrow viewports. Each interactive element is the M3 button primitive per [DS SPEC §3 — Button](design-system/SPEC.md):

| Slot | Content |
|---|---|
| Primary | Verdict-colored filled button (`.md-btn .md-btn--filled`; `background: verdictTone.color`, white text). `download` icon + "Download final document (.md)". Hover lifts by 1 px via the standard `--md-elev-1` token. Click triggers a programmatic `<a download>` against `/api/runs/{run.id}/files/final.md`. |
| Secondary | Outlined button (`.md-btn .md-btn--outlined`), `content-copy` icon + "Copy summary". On click: copies the plain-text version of `summaryCopy` (with `**` stripped) via `navigator.clipboard.writeText`. Swaps to `check` glyph + "Copied!" for 1.4 s then reverts. |
| Right-anchored | `run {run.id}` in mono, muted — the spec 0138 §5.3 run-id pill reused. No ID-as-`<code>` chip (consistent with the [§4.8 ID-rendering rule](design-system/SPEC.md) and spec 0172's drop of the in-card-head ID chip). |

**Final-doc-missing handling.** Deadlocked / errored runs may not have produced `final.md`. On mount of the Summary tab, the footer issues a `HEAD /api/runs/{id}/files/final.md` and stashes the result in component state. If `404`, the primary button renders in disabled state (opacity 0.5, `cursor: not-allowed`, no hover lift) with a `title` tooltip: _"No final document was produced for this run."_

### 2.9 — Per-round breakdown — collapsible drill-down

The legacy `SummaryKindTable`-driven view stays byte-identical, just collapsed by default behind a single toggle button:

- Rotating `chevron-right` (90° on open) — same disclosure pattern spec 0168 §2.1 / DS §3 CollapsibleSection use
- `chart-line` glyph
- Label "Per-round breakdown" + small mono subtitle "raised / resolved by round, per model"
- Body renders `renderPhase('Phase 2 — Negotiate', 2)` and `renderPhase('Phase 4 — Review', 4)` only when `showTables === true`.

No data behaviour changes inside the tables.

### 2.10 — Icons inventory (locked names)

Every icon used in the spec, with intended placement. Material Symbols Outlined per [DS SPEC §2.12 Icons](design-system/SPEC.md):

| Where | Glyph | Notes |
|---|---|---|
| Hero cheer line lead | `check-bold` | small (12 px), verdict color |
| Hero verdict glyph | `shimmer` / `alert-circle` / `compare` / `help-circle` / `pause` / `alert` | 32 px, status-keyed (see §2.4 table) |
| Hero topic line lead | `format-quote` | 14 px, muted, alpha 0.55 |
| Stat tile (each) | `lightning` / `currency-usd` / `timer` / `history` / `magnify` | 16 px, top-right corner, opacity 0.6 |
| Agent card | `AgentIcon` brand tile (ghost) | 20 px — `BrandMark` per DS §3 Primitives |
| Story block lead | `format-quote` | 20 px, verdict color, alpha 0.7 |
| Critique outcomes header | `list` | 14 px, muted |
| Critique outcomes per-row | `AgentIcon` (16 px ghost) + `arrow-up` / `check` (12 px) | per row |
| Critique outcomes sub-row | `Dot` (6 px) | kept as a dot, not an icon |
| Highest-leverage header | `alert-circle` | 14 px, warn |
| Per-round toggle | `chevron-right` (rotating) + `chart-line` | both 14 px |
| Footer download | `download` | 14 px, white |
| Footer copy (idle) | `content-copy` | 14 px, currentColor |
| Footer copy (just-copied) | `check` | 14 px, currentColor |

### 2.11 — Design-system citations

This subsection collects every DS reference the rest of the spec already touches in line, for the [`/dev-next` step-15 DS gate](CLAUDE.md):

- **§1 — Principles.** Honours #2 (one color per agent — sable/sage on agent cards), #5 (calm transitions — confetti respects `prefers-reduced-motion`), #7 (token-only colors — all bgs/borders read from `--md-*` / `--p-*` or the `COLORS.*` JS aliases that resolve to palette tokens), #11 (one card primitive per surface — `StatTile` / `AgentSummaryCard` re-use the `--md-surface-container-high` chrome from spec 0168 §2.1, no new card variant).
- **§2.1 — Palette.** Verdict tones use `--p-ok` / `--p-warn` / `--p-info` / `--p-err`; confetti particles use `--p-sage` / `--p-sable` plus `--md-surface`.
- **§2.5 — Typography.** Hero topic line in `var(--md-font-brand)` (Roboto Serif) per principle #3. Numbers + labels in `var(--md-font-plain)` with tabular-nums.
- **§2.6 — Shape.** Stat tiles + agent cards at `--md-shape-md` (12 dp). Footer buttons at `--md-shape-full`. Hero band at `--md-shape-md`.
- **§2.7 — Spacing.** Internal padding on the new components reads from `--md-sp-N` tokens (no off-grid pixel values).
- **§2.9 — Elevation.** Hover on stat tiles + agent cards lifts to `--md-elev-1`. The footer primary button lifts +1 px on hover (matching the standard M3 button hover).
- **§2.10 — State layers.** All buttons + expandable rows use the standard `::before` state-layer pattern (no background-color swap).
- **§2.11 — Motion.** Confetti at `--md-dur-medium-2` (300 ms) ramp + `--md-easing-emphasized`. Tone-flash on verdict reveal at `--md-dur-short-3` (150 ms) + `--md-easing-standard`. All animations gated by `prefers-reduced-motion: reduce`.
- **§2.12 — Icons.** Every glyph from Material Symbols Outlined (loaded via `Mdi` primitive). Brand marks via `<AgentIcon>` / `<BrandMark>` only.
- **§3 — Primitives.** `Button` (filled + outlined for footer), `Chip` (per `SmallStat`), `Card` (M3 chrome on stat tiles + agent cards), `CollapsibleSection` (each expandable row in CritiqueBreakdown + the per-round drill-down toggle), `BrandMark` (agent identity on cards + outcome rows), `QuestionThread` (highest-leverage thread, unchanged).
- **§4.8 — Critique card composition.** The per-agent rows obey the ID-rendering rule reaffirmed by spec 0172: no compound IDs as visible chips. Items show via their kind dot + count, not their `item.id`.
- **§6 — Themes.** Both themes ship together. Light-mode pass mandatory before merge — see §6 Test plan.
- **§8 — Accessibility.** Every expandable row is `<button aria-expanded>`; decorative glyphs carry `aria-hidden="true"`; verdict text (not glyph) is the accessible label.
- **§9 — Badge governance.** `SmallStat` chips inside agent cards use the canonical chip primitive; no inline custom badge.

If a DS extension is needed during implementation (none anticipated), file it as a follow-up before landing the user-facing surface.

## 3. UX / Behavior

### 3.1 — Edge cases & states

| Case | Behaviour |
|---|---|
| Run still running (any non-terminal) | Summary tab hidden by existing gate at [`run-detail.jsx:7133`](src/dual_research/ui/static/run-detail.jsx). No change. |
| `completed` with 0 items raised | Hero → "Inconclusive" (Inconclusive palette). Stat tiles render normally. Critique outcomes section hidden (`stats.totalItems > 0` gate). Story line generator already handles this: "no critique items were raised in this run." |
| `completed` with items but 0 resolved | Verdict → "Mostly negative". Outcomes section renders with all four rows; per-kind sub-rows show `—` for the solved bucket. |
| `deadlocked`, items present | Hero → deadlocked variant. Highest-leverage thread promoted above the stat grid. Everything else renders normally. |
| `errored` mid-Phase | Hero → errored variant. Stat tiles + agent cards + outcomes still render against partial data. The error explanation line names the phase. |
| `final.md` missing | Download button disabled with tooltip (§2.8). Other actions unaffected. |
| Re-fetch / live snapshot updates | Every derived value lives in `useMemo`; recomputes on snapshot change. Confetti localStorage flag prevents re-fire on snapshot bumps. |
| Status reverts (terminal → running) | Existing guard yanks the user out of Summary. No regression. |
| User picks a non-summary tab while running, then run finishes | Auto-jump suppressed (`userPickedTabRef` set). Σ tab remains highlighted as available. |
| User reloads page after a green run | Confetti does not re-fire (localStorage flag). Page renders with verdict-colored hero. |
| `prefers-reduced-motion: reduce` | Confetti skipped; localStorage flag still written so the gate doesn't keep retrying. Hover transitions still fire (low-amplitude). |

### 3.2 — Responsive behaviour

- Inner container max-width: 980 px. Larger viewports get the whitespace, not a stretched layout.
- Stat grid: `auto-fit minmax(150px, 1fr)` → 5 → 3 → 2 → 1 cols.
- Agent cards: `auto-fit minmax(280px, 1fr)` → 2 → 1.
- Critique outcomes: single-column native. Sub-row indentation (`paddingLeft: 38`) stays at all widths.
- Hero band wraps cleanly: verdict glyph + text, then resolution stat, then topic on its own line.
- Footer wraps with `flex-wrap` — run-id chip drops to a new line on narrow viewports rather than overflowing.

Validate at 1280, 768, 375 px during implementation. The 1500 → ≤1799 px responsive band is the same one DS §4.4 calls out for the timeline pane; the Summary tab's layout collapses earlier (980 px container max), so there's no in-band overflow risk.

### 3.3 — Light + dark mode

Built and verified in dark. All colors are token-driven; the only hard-coded values are the `COLORS.*` palette aliases (which work in both themes because the `+ '1A'` / `+ '55'` alpha extensions composite onto whatever surface they sit on — same approach spec 0165 §2.2 took for timeline-card chip backgrounds).

The light-mode pass needs to check, specifically:

- Hero verdict tint bg + border contrast against the bright surface
- Story block left-border + format-quote glyph against bright bg
- Stat tile glyph (opacity 0.6) against bright surface
- AgentIcon ghost variant readability (uses `meta.color + '1f'` background + `meta.color + '55'` border — verified dark, unchecked light)
- The download button's primary background (verdict color, white text) — white text on `--p-ok` (#6fb380) is the lowest-contrast combination; check AA against [DS SPEC §8 Accessibility](design-system/SPEC.md).

Anything that fails contrast picks up a per-theme overrider via the existing token system — same backstop pattern as spec 0165 §2.6.

## 4. Data / Schema deltas

None. The redesign is pure re-presentation. No backend, no protocol, no schema, no migration.

## 5. Out of scope

Explicitly deferred to later specs:

- Cross-run analytics (streaks, personal records, "your N-th run on this topic").
- Postcard / poster mode for screenshot-sharing.
- Sentiment / cost / token sparklines under each stat tile.
- Final-draft preview teaser above the download button.
- v1-vs-final diff stat.
- "Share permalink" / "Branch from here" footer actions.
- Achievement badges ("Drift-free", "Mutual agreement").
- LLM-generated narrative blocks beyond the existing 3-sentence generator.
- Promoting more than one highest-leverage item on deadlocked runs (defaulting to one — revisit after first real deadlock screenshot).

## 6. Test plan

- [ ] **Unit — `_computeSummaryStats(run, questions, disagreements, issues, comments)`** extracted into a top-level pure helper. Cases:
  - All-resolved run (verdict = Mostly positive at ≥ 0.85; Mixed between 0.4–0.85).
  - All-open run (Mostly negative).
  - Run with only `resolved-both` disagreements — per-agent solved rows show 0; header `aligned` count is correct.
  - Run with `raisedBy === 'both'` disagreements — both raised counts incremented.
  - Drift-heavy run (≥ 40 % drift → Mostly negative even with high resolution).
  - Errored mid-Phase 2 — verdict frozen to "Incomplete" downstream; stats still compute against partial data.
- [ ] **Snapshot — `CritiqueBreakdown`** rendering for a fixed fixture covering all three disagreement statuses + a `'both'`-raiser case. Assert: no row's `textContent` contains the literal `item.id` value (consistent with spec 0172 ID-chip-drop rule); no stray `**` in any text node (consistent with spec 0172 Markdown render guarantee).
- [ ] **DOM — auto-jump effect** mounts in `running` state, transitions to `completed`, asserts `selectedPhase === 'summary'`. Repeat with a manual non-summary tab click before terminal transition — asserts no auto-jump.
- [ ] **DOM — confetti gating** verifies the localStorage flag write + first-land trigger, and that `prefers-reduced-motion` short-circuits the burst while still writing the flag.
- [ ] **Manual UAT** against the live preview at `http://localhost:6173/#/runs/{id}` for each terminal state (`completed`, `deadlocked`, `errored`): verify auto-jump, confetti threshold, final-doc-missing handling, light-mode contrast (DS §8 AA), reduced-motion honour.
- [ ] **`how-it-works.jsx` content sync** — the changelog/feature description must match the shipped layout.

## 7. Risks

- **Light-mode contrast on white-on-`--p-ok` download button.** Mitigation: the §3.3 audit catches it pre-merge; fall back to dark sable text if AA fails — same backstop spec 0165 §2.6 used for timeline chips.
- **`run.error` field naming in the snake → camel transform.** `models.py` declares `error: TopLevelError | None` on `Run`; the existing snake-to-camel JSON serializer should expose `run.error` with `{when, where, code, detail}` already in the right shape. Verify on the first errored run snapshot during implementation; no code change expected. If the field arrives snake-cased (`run.error.detail` vs `run.error.Detail`), normalise in the JSX layer with a one-line accessor.
- **Cross-pollination with spec 0168's expanded-card behaviour.** Spec 0168 added `data-expanded="false"` on `.item-card`. The new Summary tab does not mount `.item-card` directly — its CritiqueBreakdown rows are their own component family — so there is no class collision. Verify with a repo-grep before merge.
- **Confetti animation cost on weak hardware.** Mitigation: cap particle count at ~80; use CSS transform + opacity (compositor-only); reduced-motion is the cliff. If profiling shows jank on first paint, drop to a static verdict-color flash.
- **Resolved-both attribution regression.** Mitigation: unit tests in §6 lock the tally rule; manual UAT against a synthetic `resolved-both`-heavy run prior to merge.

## 8. Implementation order

Each step is independently shippable; gate later steps behind earlier ones in the PR.

1. Replace `CritiqueSummaryView` body + add `StatTile`, `AgentSummaryCard`, `CritiqueBreakdown` siblings. (`Mdi` already emits `aria-hidden=true` by default in [`icons.jsx`](src/dual_research/ui/static/icons.jsx); brand glyphs that need labels go through `AgentIcon`, which already emits `aria-label` correctly.)
2. Fix the `CritiqueBreakdown` tally per §2.3 — drop the `'both'` branch from the solved-side bump, surface `mutualAligned` in the header.
3. Add the web-searches stat tile (§2.7) — pull `SearchIndexContext` in the `CritiqueSummaryView` body.
4. Add the status-aware hero variants (§2.4) — extend `verdictTone`, add the deadlocked/errored cheer + glyph + bottom line. Read `run.error.{where, code, detail}` for the errored variant.
5. Promote highest-leverage thread above the stat grid when `run.status === 'deadlocked'`.
6. Add the auto-jump effect + `userPickedTabRef` (§2.5).
7. Add the final-doc HEAD check + disabled-state for the download button (§2.8).
8. Add the confetti primitive + first-land gate (§2.6).
9. Tighten the green-verdict threshold to `0.85` (§2.2).
10. Light-mode pass + mobile pass (375 px, 768 px).
11. Update [`src/dual_research/ui/static/how-it-works.jsx`](src/dual_research/ui/static/how-it-works.jsx) Summary description to reflect the new layout.
12. Replace any `SPEC-0175` placeholder marker comments in [`run-detail.jsx`](src/dual_research/ui/static/run-detail.jsx) with the canonical `Spec 0175` form used elsewhere in the file.

---

End of spec.

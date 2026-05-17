---
spec: 0044
title: Turn-input semantics + per-turn badges + side-by-side framing
label: new-feature
version-bump: MINOR
status: in-progress
target-version: 0.42.0
created: 2026-05-17
pr: ""
---

# Spec 0044 — Turn-input semantics + per-turn badge redesign + side-by-side framing

## Context

Three threads of UX work that all sit on top of spec 0043's
authoritative ledger but stayed out of scope while we landed the
data layer:

1. **Per-turn badges over-state activity and mis-read the protocol
   state.** Today every Phase 2 / Phase 4 turn card shows a
   `negotiating` (or `reviewing`) status pill alongside the count
   chips — but we already know we're in the negotiation/review
   phase from the phase-section header. The pill is noise. Worse,
   the `agreed` pill that shows up on individual rounds reflects
   that agent's per-turn `STATUS: AGREED` self-report, not the
   phase-wide convergence state. On the partner-vetting fixture
   Claude turn 3 reads `agreed` while GPT turn 3 still reads
   `negotiating` — which is misleading because the phase doesn't
   converge until R5. The user reads "agreed" as "we're done"
   when really it's "this agent is ready."

   The count chips themselves are also under-informative. Today
   they show `6 questions`, `5 questions ⤴ 1`, etc. — the `⤴`
   glyph is "closed N prior" but it sits behind a small symbol
   most users won't recognise. There's no explicit `+raised` /
   `−resolved` breakdown per kind, and disagreement / claim
   activity doesn't show round-deltas at all.

2. **Side-by-side modal left pane is mute about what the agent
   actually saw as input.** The
   [`NegotiateReviewModal`](../src/dual_research/ui/static/run-detail.jsx#L2531)
   today renders the "prior content" (other agent's draft for R1,
   other agent's previous turn for R2+, current draft for P4) on
   the left and review items on the right. But the agent's actual
   round-N input is `brief + own draft + other's draft + ALL prior
   Phase 2 turns` (verified during spec 0042 prep — see the user
   conversation for the trace). The single "Original" tab on the
   left flattens that into one file with no way to see what else
   the agent had in front of them.

   The Phase 1 plan-draft modal
   ([`DraftReviewModal`](../src/dual_research/ui/static/run-detail.jsx#L2457))
   has the inverse problem: it shows the brief on the left and the
   draft on the right, but the `brief` chips in the draft pane
   that should scroll the left pane to the referenced brief
   section don't fire (the click-to-highlight wiring landed for
   Phase 2/4 in spec 0034 but was never applied to the Phase 1
   modal).

3. **Right-pane "no anchored items" copy is identical for every
   reason it can show.** A turn that genuinely raised zero items
   reads the same as a turn that closed several prior items
   without raising any. The user can't tell whether the turn was
   silent (nothing happened) or just closed-only (productive but
   not introducing new things).

[Spec 0043](./0043-cross-round-ledger-and-conservative-convergence.md)
gave us the data shape to fix all three: the ledger has
per-transition history (`status_history` per entry), the wire
exposes `Run.phase_ledgers` keyed by phase, and per-turn round-deltas
can be derived without re-parsing. Spec 0044 wires this into the UI.

Prior context:
- [Spec 0027](./0027-side-by-side-review.md) — established the
  Phase 2 side-by-side modal pattern (left = prior content, right =
  review items).
- [Spec 0028](./0028-review-inline-comments.md) — extended to Phase
  4 with `current_draft_path` resolution.
- [Spec 0033](./0033-inputs-foundation-and-header.md) — added the
  per-turn input bundle (`Input` tab on the full-view modals) which
  IS the structured "what the agent saw" data; this spec surfaces
  it on the left pane semantically, not just as a raw tab.
- [Spec 0034](./0034-critique-navigation.md) — click-to-highlight on
  Phase 2/4 modals (anchored item → flash on the referenced left-pane
  block). Phase 1 plan-draft modal was not in scope.
- [Spec 0040](./0040-critique-rework.md) — compact cards, sentiment
  composer's existing per-phase branches.
- [Spec 0041](./0041-critique-classification-and-resilience.md) —
  sentiment composer's overall-sentiment-word lead (Positive /
  Cautious / Critical / etc.).
- [Spec 0042](./0042-critique-data-integrity.md) — per-phase chip
  allowlist; chip counts read from parsed-item arrays (this spec
  swaps that source to the ledger).
- [Spec 0043](./0043-cross-round-ledger-and-conservative-convergence.md) —
  the ledger this spec consumes.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Drop the per-turn `negotiating` / `reviewing` / `disagreed` status pill from `StatsChips`.** | The phase-section header (`PHASE 2 · Negotiate plan` / `PHASE 4 · Review`) already tells the user the phase. A per-turn pill repeating it is noise. The pill survives on the run-header chip (where it summarises overall run state, not per-turn) — that surface is unchanged. |
| D2  | **`agreed` pill only on the LAST turn of a converged phase.** | Per-turn "agreed" today reads each agent's per-turn `STATUS: AGREED` self-report, which can fire mid-phase before the other side agrees. Spec 0044 ties it to the phase-wide convergence state: the pill renders only on the per-turn card whose `turnKey` matches the final round AND only when `run.phaseLedgers[phase]` has zero open entries. Visual: green `✓ agreed` chip. Same logic for Phase 4's `approved`. |
| D3  | **Per-turn count chips render as explicit `+raised  −resolved` per kind.** | Replace the current `6 questions`, `5 questions ⤴ 1` shape with `+6 Q`, `+5 Q  −1 prior` etc. The values come from the ledger: `raised_this_turn` = entries with `raised_turn_key == turnKey`; `resolved_this_turn` = entries whose `status_history` contains a non-`open` transition with `turn_key == turnKey`. Zero-on-both-sides chips are omitted (the absence is information). |
| D4  | **Side-by-side modal left pane gets phase-aware tabs over the existing single "Original" view.** | Replace the implicit "Original" with explicit tabs naming what the agent saw: **P2 R1** = `[Other's draft \| Brief \| Your draft]` (default Other's draft); **P2 R≥2** = `[Other's prior turn \| Other's draft \| Brief \| Your draft]` (default Other's prior turn); **P4** = `[Current draft \| Brief \| Other's prior turn]` (default Current draft); **P1 plan-draft** = `[Brief]` (default Brief — the only input). The existing `Input` and `Web Search` sub-tabs stay nested under the active document tab (they're per-turn, not per-document). |
| D5  | **Right-pane empty-state copy is action-specific.** | Compute the per-turn ledger transitions (D3's `raised_this_turn` + `resolved_this_turn`) and pick the copy that matches: **no activity at all** → "This turn raised no new items and closed no prior ones. View the document modal for the full markdown body." **only-closed** → "This turn closed N prior {kinds}. No new items raised." **only-raised but unanchored** → "This turn raised N {kinds} but none had `> quote:` / `> after:` anchors. View the document modal for the inline detail." Three distinct cases instead of one. |
| D6  | **Click-to-highlight wired on `DraftReviewModal` (Phase 1 plan-draft).** | The Phase 1 modal already renders structured items on the right (via spec 0042 D3 — Phase 1 claims + questions now appear in `phase1_<agent>` ledger buckets). Wire `jumpToItem` from `NegotiateReviewModal` to `DraftReviewModal` using the brief as anchor source — chips with `quote` / `after` markers scroll the left pane to the referenced brief block + flash. Reuses the existing `scrollAndFlash` helper. |
| D7  | **Sentiment composer reads ledger round-deltas for richer per-turn synthesis.** | `composeSentiment` today picks sentiment cues from `stats.status` + `stats.openQuestions` etc. — agent self-reports. Spec 0044 extends it to pull `raised_this_turn` / `resolved_this_turn` from the ledger for the timeline turn-card body. Example pre-spec: `Cautious — Claude's round-1 difference inventory. Raised 6 new questions. Standing: 6 open questions.` Post-spec: `Cautious — Claude raised 6 questions + 10 claims in round 1. Standing across the phase: 6 questions, 10 claims open.` Ledger-derived activity instead of single-turn self-counts. |
| D8  | **`StatsChips` becomes the single rendering site for per-turn ledger consumption.** | Spec 0042 D4 already moved chip counts away from agent self-counters; spec 0044 D3 adds the per-turn round-delta semantics. To avoid scattered logic, all chip-derivation reads from `run.phaseLedgers[phase]` filtered by `raisedTurnKey === turnKey` for raised-counts and walked through `statusHistory` for resolved-counts. The legacy `run.questions` / `run.disagreements` / `run.claims` arrays are still wire-exposed and consumed by other surfaces (Critique pane); just not by chips anymore. |
| D9  | **The "agreed" pill placement uses a per-turn helper `isFinalConvergedTurn(item, run)`.** | The helper returns `true` iff the item is a Phase 2 / Phase 4 turn AND its round matches the highest round-key present in `run.phaseLedgers[phase]` AND that phase has zero open ledger entries AND the run has actually exited the phase (`run.phaseTimings[phase] != null`). Centralises the decision so the chip layer + the pane header + the sentiment composer all agree. |

## Proposed change

### 1. Frontend — `src/dual_research/ui/static/run-detail.jsx`

#### 1a. `StatsChips` per-turn round-delta derivation (D1, D3, D8)

The current implementation (spec 0042 D4 / D5) reads:

```js
const counts = {
  questions: (run.questions || []).filter(q => q.raisedTurnKey === turnKey).length,
  ...
};
```

Extend with ledger-derived round deltas:

```js
function computeChipDeltas(run, item) {
  // item.turnKey is e.g. "phase2_round3_claude"
  const phase = item.statsPhase || 2;
  const entries = (run.phaseLedgers && run.phaseLedgers[phase]) || [];

  const raised = (kind) => entries.filter(
    (e) => e.kind === kind && e.raisedTurnKey === item.turnKey
  ).length;

  const resolved = (kind) => entries.filter((e) => {
    if (e.kind !== kind) return false;
    // Any non-"open" transition whose turn_key matches.
    return (e.statusHistory || []).some(
      (t) => t.turnKey === item.turnKey && t.status !== 'open'
    );
  }).length;

  return {
    question:     { raised: raised('question'),     resolved: resolved('question') },
    disagreement: { raised: raised('disagreement'), resolved: resolved('disagreement') },
    claim:        { raised: raised('claim'),        resolved: resolved('claim') },
    issue:        { raised: raised('issue'),        resolved: resolved('issue') },
    comment:      { raised: raised('comment'),      resolved: 0 },  // terminal
  };
}
```

`StatsChips` rendered output (per allowed kind):

```jsx
{deltas.question.raised > 0 && (
  <StatChip
    label="Q"
    raised={deltas.question.raised}
    resolved={deltas.question.resolved}
    tint="info"
  />
)}
{deltas.question.raised === 0 && deltas.question.resolved > 0 && (
  <StatChip
    label="Q"
    raised={0}
    resolved={deltas.question.resolved}
    tint="ok"
  />
)}
```

`StatChip` renders as `+5 Q` for raised-only, `+5 Q  −1 prior` for both,
`−3 prior Q` for closed-only. Tints: raised=info, closed-only=ok.

The `status` pill block is removed entirely from `StatsChips`.

#### 1b. `isFinalConvergedTurn` helper + `agreed` chip (D2, D9)

```js
function isFinalConvergedTurn(item, run) {
  if (!(item.kind === 'turn' || item.kind === 'turn-live')) return false;
  if (!run.phaseTimings || run.phaseTimings[item.statsPhase] == null) return false;
  const entries = (run.phaseLedgers && run.phaseLedgers[item.statsPhase]) || [];
  const openCount = entries.filter((e) => e.currentStatus === 'open').length;
  if (openCount > 0) return false;
  // Must be the last round.
  const maxRound = entries.reduce(
    (acc, e) => Math.max(acc, e.raisedRound || 0), 0
  );
  return item.round >= maxRound;
}
```

Rendered chip (when true):

```jsx
{isFinalConvergedTurn(item, run) && (
  <span className="mono" style={{
    padding: '1px 8px',
    border: `1px solid ${COLORS.ok}55`,
    borderRadius: 4,
    color: COLORS.ok,
    fontSize: 10.5,
  }}>
    ✓ agreed
  </span>
)}
```

For Phase 4 the label is `✓ approved`.

#### 1c. `NegotiateReviewModal` left-pane phase-aware tabs (D4)

Replace the existing `NegotiateLeftPane` rendering with a tab-bar that
picks the documents based on `item.statsPhase + item.round`:

```js
function leftPaneTabsFor(item, otherAgent, run) {
  const phase = item.statsPhase || 2;
  const otherBe = otherAgent === 'gpt' ? 'openai' : otherAgent;
  const ownBe   = otherBe === 'openai' ? 'claude' : 'openai';
  const round   = Number(item.round) || 1;

  if (phase === 4) {
    return [
      { id: 'current',   label: 'Current draft',  path: run?.currentDraftPath },
      { id: 'prior',     label: "Other's prior turn",
        path: round >= 2 ? `phase4/round-${String(round-1).padStart(2,'0')}-${otherBe}.md` : null },
      { id: 'brief',     label: 'Brief',          path: 'brief.md' },
    ].filter((t) => t.path);
  }
  // Phase 2:
  const tabs = [
    { id: 'otherDraft', label: "Other's draft",   path: `phase1/draft-${otherBe}.md` },
    { id: 'brief',      label: 'Brief',           path: 'brief.md' },
    { id: 'ownDraft',   label: 'Your draft',      path: `phase1/draft-${ownBe}.md` },
  ];
  if (round >= 2) {
    tabs.unshift({
      id: 'priorTurn',
      label: "Other's prior turn",
      path: `phase2/round-${String(round-1).padStart(2,'0')}-${otherBe}.md`,
    });
  }
  return tabs;
}
```

The active tab is the first in the list (default = "what's being
responded to"). Tab content renders via the existing
`LazyMarkdownBody`. The right-pane review-items + `jumpToItem`
plumbing still resolves anchors against the FIRST tab (`tabs[0].path`)
— jumping to a quote highlights it in the current default surface;
switching tabs is a manual user action.

#### 1d. Right-pane empty-state copy (D5)

Replace the single-string copy in `NegotiateReviewModal` with a
small helper:

```js
function emptyStateCopy(item, run) {
  const deltas = computeChipDeltas(run, item);
  const raisedTotal = Object.values(deltas).reduce((s, d) => s + d.raised, 0);
  const resolvedTotal = Object.values(deltas).reduce((s, d) => s + d.resolved, 0);

  if (raisedTotal === 0 && resolvedTotal === 0) {
    return "This turn raised no new items and closed no prior ones. Open the document modal from the card header for the full markdown body.";
  }
  if (raisedTotal === 0 && resolvedTotal > 0) {
    const parts = [];
    for (const [kind, d] of Object.entries(deltas)) {
      if (d.resolved > 0) parts.push(`${d.resolved} ${kind}${d.resolved === 1 ? '' : 's'}`);
    }
    return `This turn closed ${parts.join(' + ')} from prior rounds. No new items raised.`;
  }
  // raisedTotal > 0 but none anchored — happens when the agent
  // didn't add `> quote:` / `> after:` markers to their items.
  return `This turn raised ${raisedTotal} item(s), but none had quote/after anchors for cross-reference. Open the document modal for the inline detail.`;
}
```

#### 1e. `DraftReviewModal` click-to-highlight (D6)

The Phase 1 plan-draft modal currently renders `[brief]` chips in
the right-pane draft view that don't fire on click. Wire the same
`jumpToItem` callback from `NegotiateReviewModal` — for each Phase 1
review-item (questions + claims now extracted via spec 0042 D1),
clicking the chip scrolls the left brief pane to the matching
block and flashes it.

```js
// Inside DraftReviewModal:
const items = reviewItemsFor(run, item);  // already returns Phase 1 ledger bucket
const leftRef = React.useRef(null);
const jumpToItem = React.useCallback((it) => {
  if (!leftRef.current) return;
  if (it.blockId) { ... } // same as NegotiateReviewModal
  if (it.quote)   { window.scrollAndFlash(leftRef.current, { text: it.quote }); }
  if (it.after)   { window.scrollAndFlash(leftRef.current, { afterHeading: it.after }); }
}, []);
```

Bind the callback to chip clicks in the draft pane's inline render.

#### 1f. `composeSentiment` ledger-aware (D7)

Extend the Phase 2 + Phase 4 branches to read per-turn deltas from
the ledger when `run.phaseLedgers` is populated. Falls back to the
self-counter path when the ledger isn't available (legacy runs).

Sentiment + body construction:

```js
function composeSentiment(item, run) {
  if (run && run.phaseLedgers && (item.statsPhase === 2 || item.statsPhase === 4)) {
    return _composeSentimentLedger(item, run);
  }
  return _composeSentimentLegacy(item, run);  // existing logic
}
```

`_composeSentimentLedger` builds the body from `computeChipDeltas`
+ per-phase open-count + the `agreed` finality check. Example:

```
**Cautious —** Claude raised 6 questions + 10 claims in round 1.
Standing across the phase: 6 questions open, 10 claims open.
```

vs end-of-phase:

```
**Positive —** Claude closed 3 questions and 1 disagreement in round 5.
Phase converged: 0 items open.
```

### 2. Tests

No frontend test runner exists; verification is manual via the
hosted UI + the partner-vetting fixture. Python-side coverage:

- `tests/ledger/test_build.py` extend:
  - `entries with raisedTurnKey == turnKey count` matches expected
    per-turn for the partner-vetting fixture (regression guard for
    the data the frontend now consumes).
- `tests/ui/test_aggregator_ledger.py` extend:
  - `phaseLedgers` entries carry `statusHistory` with `turnKey`
    fields populated (the chip layer's `resolved_this_turn` walker
    depends on this).

### 3. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.41.0 → 0.42.0.
- `CHANGELOG.md`: `## [0.42.0]` heading; new `[Unreleased]` placeholder.
- `VERSION_NOTES` entry at the top of `how-it-works.jsx`:
  > **0.42.0 — Turn-input semantics + per-turn badges + side-by-side
  > framing.** Per-turn badges now show explicit `+raised  −resolved`
  > deltas per kind, derived from spec 0043's ledger. The
  > `negotiating` / `reviewing` pill is removed (the phase header
  > already says it); `✓ agreed` / `✓ approved` appears only on the
  > final turn of a phase that converged with zero open ledger items.
  > Side-by-side modal left pane gains phase-aware tabs naming what
  > the agent actually saw (Brief / Your draft / Other's draft /
  > Other's prior turn / Current draft). Phase 1 plan-draft modal
  > now wires click-to-highlight on its brief chips. Right-pane
  > empty-state copy distinguishes "no activity" from "only closed
  > items" from "raised but unanchored." Sentiment paragraph reads
  > ledger deltas for richer per-turn synthesis.

### 4. Files touched

Frontend:
- `src/dual_research/ui/static/run-detail.jsx` — D1 (drop status
  pill), D2 (`agreed` chip), D3 (`+raised  −resolved` per kind),
  D4 (left-pane tabs), D5 (empty-state copy), D6 (DraftReviewModal
  click-to-highlight), D7 (sentiment ledger branch), D8 (`StatsChips`
  reads from ledger), D9 (`isFinalConvergedTurn` helper).
- `src/dual_research/ui/static/how-it-works.jsx` — VERSION_NOTES.

Tests:
- `tests/ledger/test_build.py` — extend with per-turn `raised_turn_key`
  + `status_history.turn_key` assertions.
- `tests/ui/test_aggregator_ledger.py` — extend with `statusHistory`
  wire-shape assertion.

Backend:
- No changes. All data the new UI surfaces is already exposed via
  spec 0043's `Run.phaseLedgers` + `Run.drifts` + the existing
  per-turn `item.turnKey` / `run.phaseTimings`.

## Out of scope

- **Critique panel header rework** (`Phase 2 / Phase 4 / Summary`
  buttons; counts moved out of "Critique" label; unified button
  design). Spec 0046.
- **Phase 4 card cryptic IDs cleanup** (`I-c-r1-01`, `R1→R2`,
  `**C-1**`). Spec 0046.
- **Critique filter chip relabeling** (per-phase context).
  Spec 0046.
- **Summary tab redesign** (per-round × per-model table). Spec 0046.
- **Consumption tab single-card model + web-search dedup + total
  cost.** Spec 0046.
- **Full-view shell standardisation** (consistent tab order across
  ALL full-view modals — `Content | Input | Web Search | Files`;
  hide-unused-sections; add a User-prompt section to the input view;
  equal-width Original vs Draft columns). Spec 0045. Spec 0044
  changes the SEMANTICS of the side-by-side modal's left-pane tabs
  (D4); 0045 standardises the SHELL across all full-views.
- **Model pill (timeline header) equal-width + alignment + size.**
  Spec 0045.
- **Per-card ghosted-N-rounds annotation in the critique pane.**
  Spec 0046 — wiring `GhostedAnnotation` (already-defined in spec
  0043) into `QuestionCard` / `IssueCard` / etc. lives with the
  visual rework.
- **Drift event drill-down UI** (clicking the `⚠ drift` chip
  opens an inspector). The chip + tooltip from spec 0043 is the v1
  surface. Drill-down is a follow-up if drift events become common
  enough to warrant a dedicated view.
- **Removing the `OPEN_QUESTIONS:` self-counter from the protocol
  prompts.** Same posture as spec 0043 — kept as sanity-signal,
  future deprecation candidate.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; spec adds a handful
      of regression-guard tests on the ledger's per-turn shape.
- [ ] Manual: open the partner-vetting Phase 2 timeline. Each turn
      card shows `+N Q  −M prior` style deltas per kind. No
      `negotiating` pill anywhere. The R5 cards (where the phase
      converged) show a `✓ agreed` chip (assuming the ledger
      open-count is 0 — note: on partner-vetting it's NOT 0 for
      questions because of spec 0043's drift signal, so the `✓
      agreed` will NOT appear on this run; verify the absence is
      correct given the drift state).
- [ ] Manual: open Claude turn 2 (or any P2 R≥2) side-by-side
      modal. Left pane shows tabs `[Other's prior turn | Other's
      draft | Brief | Your draft]` with Other's prior turn active.
      Click each tab to verify they all load. Click a right-pane
      review item to verify the jump-to-highlight fires on the
      currently-active left tab.
- [ ] Manual: open a Phase 4 turn modal. Left pane tabs
      `[Current draft | Other's prior turn | Brief]` with Current
      draft active.
- [ ] Manual: open a Phase 1 plan-draft modal (Claude). Right-pane
      claims (6 items) + questions (5 items) show. Click any item
      with a `> quote:` anchor — verify the left brief pane
      scrolls + flashes the matching block. This was dead before
      spec 0044.
- [ ] Manual: timeline card sentiment paragraph for Phase 2 turn
      cards reads ledger-derived activity (e.g. "Claude raised 6
      questions + 10 claims in round 1. Standing across the phase:
      6 questions open, 10 claims open."). Phase 1 / Phase 3 /
      Phase 5 sentiment is unchanged from spec 0041.
- [ ] Manual: a turn that genuinely closed prior items without
      raising new ones shows the corresponding `−N prior` chip and
      the right-pane empty-state copy reads "This turn closed N
      {kind}s from prior rounds. No new items raised."
- [ ] Preview-verified against partner-vetting fixture at
      `localhost:6173`.

## Risks

- **Dropping the `negotiating` pill removes a visual cue some users
  rely on at a glance.** Mitigation: the phase-section header is
  already visible and labels the phase; the pill was redundant.
  Watch for confusion in real-run feedback.
- **The `agreed` chip's "phase-wide zero open" requirement means
  it will rarely appear on real runs while spec 0043's ledger
  surfaces ghosted items.** This is the correct behaviour — pre-spec
  the pill mis-signalled convergence; post-spec it accurately
  reports it. On the partner-vetting fixture we expect NO `agreed`
  pill on any P2 turn (15 ledger-open questions = real drift).
  Once we tune the question-closure detection in a future spec,
  the pill will appear more frequently. The "no agreed pill" state
  IS the honest signal.
- **`+raised  −resolved` chip layout takes more horizontal space**
  than the current single-number chips. On narrow viewports the
  chip row may wrap or truncate. Mitigation: compact label format
  (`Q` / `D` / `Cl` / `I` / `C` instead of full words); zero-on-
  both-sides chips omitted (sparse rows on quiet turns).
- **D4's tab additions on the side-by-side modal expand the
  click-to-highlight surface — but the jump-target is fixed to
  the first tab.** Switching to "Brief" and clicking a review-item
  chip won't scroll the Brief pane (the anchor was resolved
  against Other's prior turn). Mitigation: v1 keeps the existing
  jump-against-first-tab semantics; rebinding anchors per active
  tab is a future enhancement.
- **D6's Phase 1 click-to-highlight assumes Phase 1 chips have
  resolvable anchors against the brief.** If the agent didn't add
  `> quote:` / `> after:` markers (common for Phase 1 claims that
  state positions rather than reference brief content), the click
  has nothing to scroll to. The chip simply doesn't fire scroll —
  same behaviour as `NegotiateReviewModal`'s "no anchor → nothing
  to jump to" branch.
- **D7's ledger-aware sentiment will read differently from the
  pre-spec body on every Phase 2 / Phase 4 card.** Backwards-
  compatible (the function returns a string either way) but
  visually the timeline cards re-read on next page-load. No data
  loss; cosmetic shift.

## Open questions

- Whether the `−resolved` count should distinguish "answered by
  this agent" from "answered by the other agent." Today
  `resolved_this_turn` counts any non-`open` transition with this
  turn_key — which means the addressing agent's turn gets credit.
  Could refine to show "Claude closed 3 of GPT's questions" vs
  "Claude's own claim escalated." Defer until real-run experience
  shows whether that nuance matters.
- Whether to add a per-card `⚠ N ghosted` annotation when this
  turn's still-open items have accumulated ghosted_rounds. Spec
  0043 already defines `GhostedAnnotation`; whether to wire it
  into `StatsChips` (this spec) or `QuestionCard` (spec 0046) is
  a placement call. v1 keeps it for 0046's visual rework so the
  chip strip stays minimal.
- Whether the side-by-side modal's tab default should be
  configurable (e.g. user preference for "always show Brief
  first"). v1 is hard-coded to the most-likely-relevant first
  tab; preference machinery deferred.

---
spec: 0041
title: Critique classification + load-time resilience + sentiment paragraph + tighter cards
label: bug
version-bump: MINOR
status: merged
target-version: 0.39.0
created: 2026-05-16
pr: ""
---

# Spec 0041 — Critique classification + resilience + sentiment

## Context

Four issues from a single review pass over the Phase 4 / critique
surface and the run-detail loading behaviour. They share enough surface
to ship together.

1. **Phase 4 conflates issues, comments, and questions under one
   "questions" bucket.** A real semantic bug. The Phase 4 review
   protocol uses three distinct markdown sections:
   - `## Open questions for {other}` — questions one reviewer asks
     the other reviewer (rare in Phase 4 review work; common in Phase 2).
   - `## Issue ledger (delta + currently open)` — items the reviewer
     found wrong with the *draft itself*. Stateful and self-managing:
     each round emits the delta + currently-open list; items
     disappear when the drafter incorporates the fix.
   - `## Comments on the current draft` — non-blocking commentary
     about the draft.

   The parser at
   [`protocol/parse.py:496-507`](../src/dual_research/protocol/parse.py)
   pulls items from **all three** sections and classifies every entry
   as `kind="question"` (with the comment "Classify as question so the
   UI groups them"). Phase 4 `reconstruct_questions` then walks those
   items and tries to thread answer linkage with the cross-round
   positional-match heuristic that was designed for actual questions.

   Two visible consequences on the partner-vetting run:
   - Timeline cards show `0 issues` (reading the literal
     `OPEN_ISSUES: 0` end-of-turn counter from the last round's turn
     file) and `APPROVED` status — the protocol's terminal state for
     a successful review.
   - Critique pane shows `74 Q · 61 open` — three sections combined,
     none of which are real Q&A linkages, and where "open" means
     "never positionally matched to an `## Answers to:` numbered
     line." Issues don't need that linkage because the drafter's
     revision is what closes them.

   The user-facing read: "run is approved with zero issues but 61
   things still open" — looks contradictory because the two counters
   are measuring different concepts that the UI calls by the same
   name.

2. **Transient `HTTP 502` flash on initial run load.** The user sees a
   full-page `Could not load run · runId=… · Error: HTTP 502` for a
   few seconds, then the page renders normally without intervention.

   Root cause:
   [`useLiveRun`](../src/dual_research/ui/static/live-data.jsx#L53)
   immediately stamps `error` on any non-2xx response and the
   `DetailScreen` short-circuits to the error screen. The first poll
   on a cold path (Fly machine wake, Supabase materialise-temp-dir
   for a 141-event run) sometimes 502s; the second poll 5s later
   succeeds. So the user sees the error screen for ~5s.

   Two compounding things:
   - The first failure goes straight to the error screen instead of
     waiting through a couple of retries.
   - Once `run` is non-null, a subsequent transient failure can still
     overwrite the screen with the error (the existing handler doesn't
     distinguish "we have stale data" from "we have never seen data").

3. **Question / disagreement card bodies are still too long.** Spec
   0040 D2 clamped the body to `WebkitLineClamp: 1` / `nowrap +
   ellipsis`, but the line itself fills the entire card width — which
   on a 1600px viewport is ~600px. The user wants the visible body
   tighter (≈70 chars / `…`) so the column reads less like a wall and
   more like a scannable list.

4. **Sentiment paragraph on timeline cards is terse / missing for
   most phases.** Spec 0034's `composeSentiment` returns:
   - Phase 0: nothing (falls back to `composeGist`).
   - Phase 1: nothing (`return ''` at line 1930 → falls back).
   - Phase 2: 2–3 short sentences (working as designed).
   - Phase 3 / Phase 5: nothing (no branch).
   - Phase 4: 1–2 short sentences (working, but no sentiment word).

   The user expects a real synthesised paragraph that leads with an
   overall sentiment cue (`Positive overall — approved.` /
   `Cautious overall — still negotiating.` /
   `Critical — issues outstanding.`) and then carries the counts.
   Today the per-turn card is two phases' worth of meta-data short
   of what was promised.

Prior context:
- [Spec 0028](./0028-review-inline-comments.md) — established the
  three Phase 4 sections (`Issue ledger`, `Comments on the current
  draft`, `Open questions for X`). At parse time they were all
  bucketed as `question` "so the UI groups them"; the consequence is
  this spec's first item.
- [Spec 0034](./0034-critique-navigation.md) — introduced the
  `composeSentiment` helper. Wrote Phase 2 + Phase 4 branches; Phase
  0 / 1 / 3 / 5 deferred.
- [Spec 0040](./0040-critique-rework.md) — compact cards, Summary
  tab, Phase 4 question linkage fix. The compact-card work didn't go
  far enough on visual width.

## Design decisions

| #   | Decision | One-liner |
| --- | -------- | --------- |
| D1  | **Parser separates `kind="issue"` / `kind="comment"` / `kind="question"` instead of bucketing all three under `question`.** | `protocol/parse.py::extract_review_items` returns three distinct kinds. `Issue ledger` → `issue`. `Comments on the current draft` → `comment`. `Open questions for {other}` → `question`. The wire schema gains the new kinds; older consumers that read `kind == "question"` for the conflated bucket get the literal `Open questions` items only (more accurate, fewer false-positive "open" rows). |
| D2  | **`reconstruct_questions` only consumes real questions.** | Reads the `kind == "question"` slice only — i.e. `## Open questions for {other}` items. Issues and comments get their own reconstruction paths (`reconstruct_issues` / `reconstruct_comments`). |
| D3  | **`Issue` is closed by the drafter's revision, not by a `## Answers to:` numbered line.** | An `Issue` is `open` iff it appears in the **latest** round's `Issue ledger (delta + currently open)` section. No cross-round positional match. This matches the protocol's stateful ledger semantics — and matches the timeline chip's `OPEN_ISSUES` counter, closing the gap that drove this spec. |
| D4  | **`Run` gains `issues` and `comments` arrays alongside `questions` / `disagreements`.** | Camelcased on the wire: `run.issues`, `run.comments`. Older transcripts (no Issue ledger / Comments sections) get empty arrays. |
| D5  | **CritiqueExplorer renders four typed groups: Issues, Questions, Disagreements, Comments.** | The existing `All / Questions / Disagreements` filter strip becomes `All / Issues / Questions / Disagreements / Comments`. Phase 2 has Questions + Disagreements + (rarely) Issues. Phase 4 has Issues (heavy) + Questions (rare) + Disagreements + Comments. Each kind has its own pill color: Issues = warn (matches the timeline `issues` chip), Questions = info, Disagreements = warn-amber, Comments = neutral-grey. Summary tab adds Issues + Comments rows alongside the existing Q + D columns. |
| D6  | **`useLiveRun` becomes stale-while-revalidate with retry-before-error.** | Internal state: `consecErrors: int`. On a polling failure, increment counter; only surface `error` to the consumer when `consecErrors >= 3`. Reset on first success. Additionally: never overwrite a successful `run` with a stale-error state — once we have data, a transient failure keeps showing the data with a "disconnected" tint (existing `connected` indicator suffices). The first-load path retries faster (1s, 2s, 4s) before settling into the 5s steady-state polling. |
| D7  | **Card body is hard-truncated at ≈70 characters before ellipsis.** | The CSS `text-overflow: ellipsis` at the line level works but lets the line stretch to whatever width the column has. Add a JS truncation: `body.length > 70 ? body.slice(0, 67).trimEnd() + '…' : body`. The full body lives in the expanded surface (unchanged from spec 0040). Card visual width drops; column scans cleaner. |
| D8  | **`composeSentiment` gains coverage for every phase, with an overall sentiment lead.** | Sentiment word selected by status + counts: `Positive — approved.` / `Solid — independent draft delivered.` / `Cautious — still negotiating.` / `Critical — issues outstanding.` / `Negative — brief flagged.` Sentence two carries the agent + activity counts (raised / answered / resolved / open). Sentence three carries the "standing" snapshot. Phase 0 + Phase 1 + Phase 3 + Phase 5 each get a branch. |
| D9  | **`composeGist` is the fallback only when sentiment returns ''.** | Sentiment is now richer for every phase; the gist line stays as a single-sentence summary that the collapsed-card view shows. The expanded card prefers sentiment over gist (current behaviour, unchanged). |
| D10 | **Card click toggling its colored left-rail behaviour stays unchanged.** | User confirmed: "I guess it's because you mark it as read. If that's the case, then you can keep it like this." So spec 0041 does NOT modify the post-click visual; only the body width per D7. |
| D11 | **No wire-format breaking changes.** | The wire shape adds `Run.issues` and `Run.comments` plus the new `kind` values on `ReviewItem`. Older readers that ignore unknown keys keep working. The cross-axis click-to-highlight logic on disagreements unchanged. |

## Proposed change

### 1. Parser — `src/dual_research/protocol/parse.py::extract_review_items`

Replace the three "treat as question" blocks with explicit kinds:

```python
# Was:
body_issues = extract_fenced_section(turn_text, "Issue ledger (delta + currently open)")
if body_issues:
    out.extend(_walk_section_questions(body_issues))   # → kind="question"

body_comments = extract_fenced_section(turn_text, "Comments on the current draft")
if body_comments:
    out.extend(_walk_section_questions(body_comments)) # → kind="question"

# Becomes:
body_issues = extract_fenced_section(turn_text, "Issue ledger (delta + currently open)")
if body_issues:
    out.extend(_walk_section_items(body_issues, kind="issue"))

body_comments = extract_fenced_section(turn_text, "Comments on the current draft")
if body_comments:
    out.extend(_walk_section_items(body_comments, kind="comment"))
```

Rename `_walk_section_questions` → `_walk_section_items` taking a
`kind` parameter (it's already structurally generic — only the kind
label is fixed). The "Open questions for X" path still calls it with
`kind="question"`.

### 2. Reconstructors — `src/dual_research/ui/`

- `questions.py::reconstruct_questions` filters review items to
  `kind == "question"` only. The answer-linkage logic is unchanged.
  Net result: Phase 4 turn files that don't have a literal "Open
  questions for X" section produce zero questions (correct).
- New `issues.py::reconstruct_issues(session_dir, phase)`:
  - Walks the turn files in chronological order.
  - For each round, parses `kind == "issue"` items from the latest
    snapshot of `Issue ledger (delta + currently open)`.
  - An Issue object: `id` (stable shape `I-{agent}-r{round}-{idx}`),
    `phase`, `agent` (the reviewer who flagged it), `round_first_seen`,
    `round_last_seen`, `body`, `quote`, `after`, `block_id`,
    `status: "open" | "resolved"`. An issue is `resolved` iff it is
    absent from the **latest** round's ledger by that agent (matched
    by body-prefix / quote-text — the same heuristic the timeline
    chip's `OPEN_ISSUES` counter uses on the protocol side).
  - Returns the ordered list.
- New `comments.py::reconstruct_comments(session_dir, phase)`:
  - Similar walker, kind-filtered to `comment`.
  - Comments don't have a closing protocol — they're non-blocking
    commentary. Status is always `"noted"`. We capture them so the
    UI can surface them on the Phase 4 tab without conflating them
    with issues.

### 3. Run model + aggregator — `src/dual_research/ui/`

- `models.py::Run` gains:
  ```python
  issues: list[Issue] = field(default_factory=list)
  comments: list[Comment] = field(default_factory=list)
  ```
  New `Issue` and `Comment` dataclasses mirror `Question` minus the
  answer-linkage fields. Camelcased on the wire.
- `aggregator.py::load_run_snapshot`:
  ```python
  run.issues   = reconstruct_issues(session_dir, phase=2) + reconstruct_issues(session_dir, phase=4)
  run.comments = reconstruct_comments(session_dir, phase=2) + reconstruct_comments(session_dir, phase=4)
  ```
  Same shape as the existing `run.questions` + `run.disagreements`.

### 4. CritiqueExplorer — `src/dual_research/ui/static/run-detail.jsx`

- Extend the type filter to `All / Issues / Questions / Disagreements / Comments`.
- Group rendering: open-items group + resolved-items group, each
  containing a mix of issue / question / disagreement / comment cards.
- Per-kind tab counts in the Phase 2 / Phase 4 tab labels: `Phase 4 · Review · 65 I · 0 Q · 0 D · 9 C` (when relevant) — falls back to `no items` when empty.
- Summary tab table gains columns for `Issues raised` / `Issues resolved` / `Issues still open` alongside the existing Q + D columns.
- New `IssueCard` + `CommentCard` components, mirroring `QuestionCard`'s
  compact-header + expandable-body shape from spec 0040.

### 5. Sentiment composer — `src/dual_research/ui/static/run-detail.jsx::composeSentiment`

Lead with an overall sentiment word selected by phase + status +
counts. Examples (one per phase):

```
Phase 0 (preflight per-agent):
  approved + 0 issues: "Positive — Claude approved the brief outright."
  approved + N minor:  "Mostly positive — Claude approved, flagged 3 minor issues."
  needs-input:         "Cautious — Claude flagged 2 blocking issues before drafting."

Phase 1 (independent draft):
  always:              "Solid — Claude wrote an independent Phase 1 draft."
                       (sentence two: "Surfaced N differences with GPT's draft, M open questions for the other agent.")

Phase 2 (negotiation):
  agreed:              "Positive — Claude endorsed the plan this round."
  negotiating R1:      "Cautious — Claude's round-1 difference inventory."
  negotiating R≥2 / no movement:  "Critical — still negotiating in round 3 with no movement."
  + sentences for movements + standing.

Phase 3 (drafter):
  always:              "Solid — Claude wrote v1 of the converged document."
                       (sentence two: "N total citations · M [V]-tagged · K [U]-tagged.")

Phase 4 (review):
  approved + 0 issues: "Positive — Claude approved the draft this round."
  approved + N issues: "Mostly positive — Claude approved with N minor issues noted."
  reviewing:           "Cautious — Claude still reviewing in round 3."
  not-approved:        "Critical — Claude did not approve; N open issues."

Phase 5 (final):
  always:              "Done — final document emitted by Claude."
```

The sentiment word is the lead; the rest of the sentence is the
existing per-phase content. Maintains the spec 0034 pattern (sentence
1 = identity, sentence 2 = movement, sentence 3 = standing).

### 6. useLiveRun — `src/dual_research/ui/static/live-data.jsx`

Replace the single-poll path with a retry-counter pattern:

```js
function useLiveRun(runId) {
  const [run, setRun] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [lastOk, setLastOk] = React.useState(0);
  const consecErrorsRef = React.useRef(0);

  React.useEffect(() => {
    if (!runId) return;
    setRun(null);
    setError(null);
    setLastOk(0);
    consecErrorsRef.current = 0;

    let cancelled = false;
    let attemptCount = 0;
    const tick = () => {
      authedFetch(`/api/runs/${encodeURIComponent(runId)}`)
        .then(r => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then(data => {
          if (cancelled) return;
          setRun(data);
          setLastOk(Date.now());
          setError(null);
          consecErrorsRef.current = 0;
        })
        .catch(e => {
          if (cancelled) return;
          consecErrorsRef.current += 1;
          // Spec 0041 D6 — never overwrite a successful run with the
          // error screen; only surface the error on initial-load
          // sequences AFTER 3 consecutive failures. Polling that
          // happens AFTER a successful fetch silently keeps the
          // existing data (the connected indicator dims on its own).
          if (!run && consecErrorsRef.current >= 3) {
            setError(String(e));
          }
        });
    };

    // First-load retry pace: 1s, 2s, 4s, then steady at DETAIL_POLL_MS.
    const schedule = () => {
      tick();
      attemptCount += 1;
      const next = attemptCount < 4
        ? Math.min(DETAIL_POLL_MS, 1000 * Math.pow(2, attemptCount - 1))
        : DETAIL_POLL_MS;
      timer = setTimeout(schedule, next);
    };
    let timer = setTimeout(schedule, 0);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [runId]);

  // ... connected indicator unchanged.
}
```

Note: `run` in the catch closure is stale — capture via a ref:
`const runRef = React.useRef(null); ...; if (!runRef.current && ...)`.
The fetch loop sets `runRef.current = data` alongside `setRun(data)`.

### 7. Card body truncation — `QuestionCard` / `DisagreementCard` (+ new `IssueCard` / `CommentCard`)

Helper at the top of `run-detail.jsx`:

```js
function truncateBody(s, max = 70) {
  if (!s) return s;
  const trimmed = s.trim();
  if (trimmed.length <= max) return trimmed;
  return trimmed.slice(0, max - 1).trimEnd() + '…';
}
```

Use in every compact-header body slot. Full text still in the
expanded surface + `title` attribute for hover-tooltip.

### 8. Tests

- `tests/protocol/test_parse.py` — new cases:
  - Phase 4 turn with all three sections → returns one ReviewItem
    per section with the correct `kind` (`issue` / `comment` /
    `question`).
  - Phase 2 turn with only `Open questions for X` → all items
    `kind="question"`.
- `tests/ui/test_issues.py` (new):
  - `reconstruct_issues` walks Phase 4 round files, returns issues
    only.
  - An issue absent from the latest round's ledger is `resolved`.
  - An issue still present in the latest round's ledger is `open`.
- `tests/ui/test_questions.py` — extend:
  - Phase 4 turn that has only an `Issue ledger` (no `Open questions
    for X`) → reconstructed questions is empty (was non-zero pre-spec).
- `tests/ui/test_aggregator.py` — extend:
  - `Run.issues` populated for a synthetic phase4 round file.
  - `Run.comments` populated for a `## Comments on the current
    draft` section.
- Frontend (`useLiveRun`, sentiment) — manual UI verification.

### 9. Versioning + release notes

- `pyproject.toml`, `__init__.py`: 0.38.0 → 0.39.0.
- CHANGELOG.md: `## [0.39.0]` under `### Fixed / Added`.
- VERSION_NOTES entry at the top of `how-it-works.jsx`.

### 10. Files touched

Backend:
- `src/dual_research/protocol/parse.py` — kind classifier (D1).
- `src/dual_research/ui/questions.py` — filter to `kind == "question"` only (D2).
- `src/dual_research/ui/issues.py` (new) — issue reconstruction (D3).
- `src/dual_research/ui/comments.py` (new) — comment reconstruction.
- `src/dual_research/ui/models.py` — `Issue`, `Comment` dataclasses; `Run.issues` + `Run.comments` (D4).
- `src/dual_research/ui/aggregator.py` — wire new lists into `load_run_snapshot`.
- `src/dual_research/ui/server.py` — `_to_camel` coverage for the new fields (auto, no code change).

Frontend:
- `src/dual_research/ui/static/run-detail.jsx` — type filter, group rendering, `IssueCard` + `CommentCard`, `composeSentiment` rewrite, card body truncation (D5 / D7 / D8).
- `src/dual_research/ui/static/live-data.jsx` — `useLiveRun` retry pattern (D6).
- `src/dual_research/ui/static/how-it-works.jsx` — VERSION_NOTES.

Tests:
- `tests/protocol/test_parse.py` — kind classification.
- `tests/ui/test_questions.py` — Phase 4 issue-only turn produces no questions.
- `tests/ui/test_issues.py` (new) — reconstruct_issues invariants.
- `tests/ui/test_aggregator.py` — issues + comments populate.

## Out of scope

- **Restructuring the protocol prompts to use clearer section names.**
  The current naming (`Issue ledger`, `Open questions for X`,
  `Comments on the current draft`) is the spec 0028 contract; this
  spec reads what's already written. A future spec could rationalise
  the section names (e.g. drop the "Open questions" section from
  Phase 4 entirely since reviewers rarely use it) but that's a
  separate prompt-engineering pass.
- **An LLM-based summariser for the sentiment paragraph.** D8's
  deterministic phrase-picker is honest and fast; an LLM call
  per-card would be slow + costly. Defer.
- **A "comments" tab/filter on the Phase 2 view.** Phase 2 doesn't
  emit comments in practice; carrying the filter chip on a
  zero-items tab would be noise. The filter shows on the type-filter
  strip only when at least one comment exists.
- **Backfilling the `Run.issues` / `Run.comments` arrays into the
  Supabase JSONB column on existing runs.** The aggregator
  reconstructs them from disk on every read; no migration needed.
  Hosted runs will produce the new fields automatically on next
  page-load.
- **Cross-tab navigation from Summary tab rows.** Same constraint as
  spec 0040 D5 — out of scope.
- **Audit visibility into which issue ledger entries closed in
  which round.** The current model captures `round_first_seen` /
  `round_last_seen`; deeper diff (which round's drafter revision
  closed an issue) would need parser support for the drafter's
  revision note. Future spec.

## Test plan

- [ ] `uv run pytest tests/ -q` stays green; this spec adds at least
      6 new tests across parse / questions / issues / aggregator.
- [ ] Manual: load partner-vetting Phase 4 tab. The critique pane
      shows:
  - Issues: 65 (or wherever the count lands after reconstruct), most
    closed by round 5.
  - Questions: 0 (no `## Open questions for X` sections were
    emitted in Phase 4 — confirmed against the turn files).
  - Disagreements: 0 (unchanged).
  - Summary tab: per-round Issues raised/resolved/open columns
    populated. The total reconciles with the timeline chip's `0
    issues` at end-of-run.
- [ ] Manual: navigate to a run on the hosted UI. If the first poll
      502s, the "Could not load run" screen does NOT appear; the
      "Loading run…" screen stays until the retry succeeds (1s / 2s
      / 4s backoff). After 3 consecutive failures, the error screen
      finally appears. Once the run renders successfully, a
      subsequent transient failure does NOT replace it with the
      error screen.
- [ ] Manual: critique cards on Phase 2 + Phase 4 read tighter — body
      truncates at ~70 characters with an ellipsis. Click expands
      shows the full body.
- [ ] Manual: timeline plan/turn card sentiment paragraph reads
      with an overall sentiment word as the lead:
  - Phase 0 cards lead with `Positive` / `Mostly positive` /
    `Cautious` depending on the brief-critique outcome.
  - Phase 1 cards lead with `Solid` + draft-shape facts.
  - Phase 2 cards lead with `Positive` (agreed) / `Cautious`
    (negotiating R1) / `Critical` (still negotiating + no movement).
  - Phase 3 / Phase 5 cards lead with `Solid` / `Done`.
  - Phase 4 cards lead with `Positive` (approved + 0 issues) /
    `Mostly positive` (approved + N issues) / `Cautious`
    (reviewing) / `Critical` (not-approved).

## Risks

- **D1 breaks an undocumented wire-format contract.** Any consumer
  that filtered `ReviewItem.kind === "question"` to find Phase 4
  issues will silently miss them after this change. Mitigation: the
  only known consumer is `reconstruct_questions` (in-tree) which
  this spec explicitly updates. No external consumers.
- **D3's "issue is closed iff absent from latest round's ledger"
  heuristic over-marks resolved.** If the drafter's revision note
  copies the issue into the next round's ledger verbatim, the
  matching is body-prefix-based. The risk: a slightly-edited
  re-statement of the same issue could fail the match and read as
  "newly raised." Mitigation: prefer the agent's own `OPEN_ISSUES: N`
  counter for the headline; the per-round list is a best-effort
  reconstruction. The timeline chip already used the literal counter
  and was correct; this spec aligns the Critique view with that
  counter rather than the other way around.
- **D6's retry-before-error masks a real outage.** A run that's
  permanently 502ing for 3 consecutive 5s polls is a 15s wait
  before the user sees the error. Mitigation: the 1s/2s/4s
  exponential backoff on the FIRST load means the user sees the
  error in ~7s of cumulative wait if 502s persist. Acceptable
  trade against the current "any 502 flashes the error screen"
  behaviour. Hosted-mode permanent 502s are extremely rare in
  practice.
- **D7's 70-char truncation hides meaningful context.** Some
  question bodies start with `**Location: X / Y / Z. Issue:
  description.**` — truncating at 70 chars yields `**Location: …`.
  Mitigation: hover tooltip carries the full body; expanded view
  carries it without truncation. The truncation is for scan
  density, not for hiding content.
- **D8's deterministic sentiment word can land jarringly when a
  round outcome doesn't fit cleanly into Positive/Cautious/Critical/
  Mostly positive.** Mitigation: a single `Neutral` fallback when
  the heuristic can't decide. Keeps the lead consistent without
  forcing a wrong cue.

## Open questions

- Whether `comments` should be hidden behind an "Advanced" filter
  toggle rather than the default `All` view. Phase 4 runs tend to
  have many — they could noise out the issues + questions. v1 shows
  them in `All` but they sit beneath issues + questions by sort
  order; tighter visual separation can land as a follow-up.
- Whether the sentiment word should be color-coded (positive →
  green, critical → red) on the timeline card. v1 keeps the body
  text neutral and uses bold for the sentiment word only; coloring
  the word would interact with the colored left-rail of the card
  in ways that might over-cue.
- Whether to log Anthropic / Supabase 502s when they occur (D6),
  for operational visibility. v1 swallows silently; if 502s become
  common, a `console.warn` line on each is a one-line follow-up.

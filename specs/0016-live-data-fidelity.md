---
spec: 0016
title: Live data fidelity — round counts, disagreement parsing, terminal-status pills, chip math
label: bug
version-bump: PATCH
status: merged
target-version: 0.16.1
created: 2026-05-15
pr: ""
---

# Spec 0016 — Live data fidelity

## Context

Spec 0015 closed v0.15.0 with a deliberate gap: the backend and the
frontend had each been verified in isolation, but never run concurrently.
Spec 0015's handoff section §11 of `frontend-state.md` enumerated the
surfaces most likely to break when a real `dual-research --prompt …` ran
while the UI was open.

The integration-kickoff session driven by that handoff has now done
exactly that — a 13-minute test-tier run (`Compare SQLite vs Postgres`,
APPROVED in Phase 4 round 3, $0.4228) — and produced a five-issue
prioritised catalogue. See `handoffs/integration-observations.md` for
the raw notes and the file-by-file trace.

The data-path mechanics work: SSE held for the full run, transcript →
watchfiles → snapshot → React all fire correctly. What is broken is the
**interpretation** layer: a handful of small bugs make the rendered
timeline disagree with what the run actually did.

Fix list, ranked P0 → P1:

| # | Surface |
|---|---|
| I1 | Phase 2/4 round enumeration uses `run.round.current` (global, overwritten by the next phase), so the timeline drops rounds whenever the run advances. |
| I2 | The disagreement parser misses every format the two agents prefer in practice — `### D-N`, `N) D-N:`, and entries that migrate to `## Resolved or non-blocking differences` once they terminate. Five disagreements rendered as zero. |
| I3 | Completed turn cards render a pill only for `AGREED` / `APPROVED`; `NEGOTIATING` / `REVIEWING` / `DISAGREED` / `NOT_APPROVED` are silently dropped, so a non-terminal round shows as `4 questions · r1` with no agreement signal. |
| I4 | The Phase 0 "needs input" chip sums `briefIssues` across both agents (claude 4 + openai 12 → 16) — meaningless because the lists overlap. |
| I5 | When the parser misses everything (see I2), the Disagreement Explorer renders the same empty state as a genuinely disagreement-free run. No way to tell the difference. |

The cosmetic cluster (`running`-forever stale status, currentTurn.body
duplication, "connected" pill on the All-runs view, final.md duration
miscount) is intentionally left out — see *Out of scope* below.

## Proposed change

### I1 — Per-phase round counts from `phaseStats`

`src/dual_research/ui/static/live-data.jsx::buildLiveTimeline` —
remove the use of `run.round.current` for round enumeration. Compute
each phase's round count from the `phaseStats` keys the aggregator
already publishes:

```js
const phase2Rounds = Object.keys(run.phaseStats?.phase2 || {}).length;
const phase4Rounds = Object.keys(run.phaseStats?.phase4 || {}).length;
```

Use these for both (a) the "Negotiate plan · N rounds" / "Cross-review ·
N review rounds" divider extra-text and (b) the static turn-card loop
in the `ph >= 3 || st === 'completed' || st === 'deadlocked'` branch.
The live-round branch (`ph === 2` and currently in flight) still uses
`cur` because in that case `cur` is genuinely the current phase's
counter — but assertion-narrow it to `ph === 2` instead of relying on
the implicit semantics.

### I2 — Disagreement format coverage (parser + prompt)

Two angles, both in scope.

**Parser (`src/dual_research/ui/disagreements.py`):**

- Broaden `_D_LINE_RE` to additionally accept:
  - `^\s*#{3,4}\s*D-N` — H3/H4 headings (Claude's preferred mid-negotiation form).
  - `^\s*\d+[\.\)]\s*D-N` — numbered list, optionally with a closing paren (OpenAI's preferred form).
- The existing dash form (`^\s*-\s*(?:\*\*)?D-N`) keeps working unchanged; the new alternatives sit alongside it as additional anchors.
- Loosen the colon requirement: when the anchor is heading- or
  numbered-list-form, the separator between the D-N and the label may
  also be `:` or ` —`. Capture the label in either case.

- Extend `_read_round_file` to read **three** sections instead of one:
  - `## Substantive disagreements I'm holding` (current behaviour)
  - `## Final-surfaced disagreements` (FSD list — drives the persistent
    "open after deadlock" set)
  - `## Resolved or non-blocking differences` (where Claude migrates
    resolved entries on later rounds)

  Entries from the resolved-or-non-blocking section are merged at the
  same D-N id; duplicates pick the highest-information record (longest
  `label` + `point`).

**Prompt (`src/dual_research/protocol/prompts.py`):**

- Add an *example block* to `negotiation_turn_prompt` showing the
  canonical line form:

  ```
  Each disagreement line MUST use exactly this format:
      - D-N: <short label> — status: <state>
      - **D-N (<label>):** `<terminal-state>` — note    (when terminal)

  where <state> ∈ {open, resolved, conceded, non_blocking_limitation, accepted}.
  ```

  Surgical addition — does NOT change `negotiation_round1_prompt` or the
  Phase 4 review prompt (different shape). Keep the existing protocol
  spec wording intact and append the example after it.

This is intentionally belt-and-braces: tightening the prompt closes the
common case, broadening the parser catches the long tail (and protects
against agents drifting back to numbered/heading forms in retries).

### I3 — Render every turn status as a pill

`src/dual_research/ui/static/run-detail.jsx::StatsChips` (and / or
adjacent helper, depending on where the pill is rendered) — replace the
conditional that only emits a pill for `AGREED` / `APPROVED` with a
full status → pill mapping:

| Status              | Pill text       | Tone          |
|---------------------|-----------------|---------------|
| `AGREED`            | `agreed`        | success-green |
| `NEGOTIATING`       | `negotiating`   | muted-grey    |
| `DISAGREED`         | `disagreed`     | warning-amber |
| `APPROVED`          | `approved`      | success-green |
| `REVIEWING`         | `reviewing`     | muted-grey    |
| `NOT_APPROVED`      | `not approved`  | warning-amber |

(Use existing palette tokens — `--ok`, `--idle`, `--warn` or whatever
the run-detail file already calls them.) Render the pill **after** the
count chips, separator dot between them.

### I4 — Phase 0 chip uses `max`, not sum

`src/dual_research/ui/static/live-data.jsx::attachItemStats` — change

```js
const total = cIssues + gIssues;
```

to

```js
const total = Math.max(cIssues, gIssues);
```

Rationale: the two agents critique the same brief, so their issue lists
overlap heavily; the larger of the two is a better proxy for "how much
of the brief is shaky" than the sum. (We considered showing both
per-agent — `claude 4 · gpt 12` — but the chip is already crowded and
the precise number is informational, not actionable.)

### I5 — Parser-failure footer in the Disagreement Explorer

`src/dual_research/ui/aggregator.py` — when `Run.disagreements` ends up
empty, do a cheap secondary scan: if any `phase2/round-NN-*.md` or
`phase4/round-NN-*.md` file in the session dir contains the literal
substring `D-` followed by a digit, set a new boolean
`Run.disagreements_parse_suspected_miss = true`. (Or similar field
name — keep it specific so it isn't conflated with "no disagreements
ever existed".)

`src/dual_research/ui/static/run-detail.jsx` — when that flag is set
AND `disagreements.length === 0`, render a single muted footer line at
the bottom of the explorer pane: "Couldn't reconstruct disagreements
from this run — open the round files directly." Hidden when the flag
is false (the genuine no-disagreement case stays clean).

## Out of scope

- **I6 (stale `running` runs)** — wants a liveness probe in
  `labels.py`; small but orthogonal. Defer to a follow-up spec.
- **I8 (`currentTurn.body` not cleared on RunCompleted)** — the
  duplication is wasteful but doesn't render incorrectly. Follow-up.
- **I9 (`connected` pill on the All-runs view)** — copy nit; defer.
- **I10 (`final.md` duration off)** — `finalize.py` bug; isolated to
  the artifact, not the live UI.
- **Per-token streaming inside `currentTurn.body`** — structural
  change requiring server-sent token deltas. Already flagged in spec
  0015's known limitations; out of scope for any incremental spec.
- **Disagreement Explorer redesign** — only the footer (I5) is in
  scope. The tabs, status grouping, and attribution heuristic all stay.

## Test plan

- [ ] **Unit tests for the broadened parser** (`tests/ui/test_disagreements.py`):
  - `### D-1: Label (qualifier)` matches with label captured.
  - `1) D-1: Label — open` matches with status=open captured.
  - `4. D-1: Label — resolved.` matches with status=resolved captured.
  - Entries in `## Resolved or non-blocking differences` participate in the same D-N timeline as entries from `## Substantive disagreements I'm holding`.
  - Existing two formats (dash + bold-paren resolved) continue passing.
- [ ] **Unit test for I1** (`tests/ui/test_aggregator.py` or a new JS-equivalent unit if any exists — Python side: confirm `phaseStats.phase2` has the right number of round keys; that's the contract the JS depends on. Already covered by existing tests; cross-check.).
- [ ] **Unit test for Phase 0 chip math (I4)** — add to `tests/ui/test_aggregator.py` or wherever `phaseStats.phase0` round-trip is tested: brief_issues `{claude:4, gpt:12}` should NOT roll up to 16 in any backend-facing field. (The actual math is in JS; we test the input shape.) The JS change itself is verified by a manual live-retest, not a JS unit suite (none exists).
- [ ] **Unit test for I5** (`tests/ui/test_aggregator.py`): a synthetic session dir with `D-1: ...` in a round file but no parseable entries → `Run.disagreements_parse_suspected_miss == True`.
- [ ] **Unit test for the prompt change** (`tests/protocol/`): the canonical-format example block is present in `negotiation_turn_prompt(...)` output.
- [ ] **Live re-test**: re-run the SQLite-vs-Postgres test-tier prompt, confirm at least one Phase 2 round shows ≥1 parsed disagreement, the timeline shows the correct round count (4 in this prompt's typical convergence), and every turn card has a status pill.

Total: ~8–10 new tests. 214 existing → ~222–224.

## Risks

- **Parser broadening risks false positives.** The numbered-list anchor
  pattern (`^\s*\d+[\.\)]\s*D-N`) is intentionally narrow — `D-` is
  uncommon outside the disagreement context, and we still require the
  digit and the structured tail. Mitigation: tests in
  `test_disagreements.py` include a "this prose mentioning D-1 in a
  paragraph shouldn't match" case.
- **Status-pill colour choices may clash with the existing palette.**
  Use already-defined tokens; do not introduce new colours. If
  `warning-amber` for `not approved` looks too loud next to `errored`
  in the all-runs list, tune in a follow-up.
- **Prompt change could affect convergence behaviour.** A worked
  example in a protocol prompt biases agent output; we have observed
  this with Phase 1 section names. The example is additive (does not
  contradict existing protocol-spec text) and is constrained to
  `negotiation_turn_prompt`. If a regression appears in the convergence
  rate on test-tier runs, roll back the prompt change and keep the
  parser broadening.

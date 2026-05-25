---
spec: "0217"
date: 2026-05-25
version: 1.44.22
pr: https://github.com/Lexiz/dual-research/pull/253
kind: deploy
---

# Spec 0217 — STATUS.RESOLVED_THIS_TURN authoritative for ledger closures

Shipped as v1.44.22. The phase-2 / phase-4 ledger reconstructors at
[src/dual_research/ui/disagreements.py](src/dual_research/ui/disagreements.py)
and [src/dual_research/ui/questions.py](src/dual_research/ui/questions.py)
now treat the `STATUS` action arrays as the canonical channel for both
closure and (necessarily) raising. The pre-fix behavior — section-tail
scanning only — was silently dropping closures any time agents ratified
via the `## Ratifying my own items` / `### RESOLVE D-N` block shape
instead of populating `## Resolved or non-blocking differences`. The
`20260525-135006-backend-language-choice` run burned three extra
administrative-closeout rounds because of this; that scenario now
converges at round 3 as the agents' STATUS arrays already promised.

## What landed

**Code (2 reconstructor edits):**

- `src/dual_research/ui/disagreements.py` — added per-turn STATUS pass
  in `reconstruct()`. For each turn, parse `RAISED_THIS_TURN`,
  `RESOLVED_THIS_TURN`, `WITHDRAWN_THIS_TURN` via the existing
  `RAISED_THIS_TURN_RE` / `RESOLVED_THIS_TURN_RE` / `WITHDRAWN_THIS_TURN_RE`
  patterns from `contract/markers.py` and the `list_ids` helper. New
  `_canonical_id` helper normalizes both numeric (`D-1` → `d-01`) and
  composite (`D-plan-c-01` → `d-plan-c-01`) IDs into a consistent
  cross-source key. Status-RAISED IDs seed minimal entries when the
  legacy body-section parser produced none — required for the new
  `### RAISE`-block protocol where item IDs only appear in STATUS
  arrays (the smoking-gun session's items live exclusively there).
  Status-RESOLVED / WITHDRAWN IDs flip the matching entry to
  `status: resolved` at that turn's round; STATUS wins on conflict
  with body-section state (§3.3). The `raised_ever` set tracks IDs
  ever-`raised` across all prior rounds so the §8 spurious-ID
  mitigation drops STATUS-listed IDs that were never `raised`
  silently. The legacy `_D_LINE_RE`-based section-tail scanning path
  is preserved verbatim as the fallback.

- `src/dual_research/ui/questions.py` — mirror of the same logic.
  `_canonical_id` and `_status_q_ids` extract canonical Q-prefixed
  IDs from STATUS arrays. Status-RAISED seeds stubs; status-RESOLVED /
  WITHDRAWN flips Question.status to `answered`. The `by_id`
  in-memory lookup table was renamed `by_canon` and now keys by
  canonical form so the existing answer-block ID-based linkage
  (spec 0090) continues to match. The positional-fallback path and
  verbatim-text confirmation heuristic are untouched.

Neither reconstructor parses `### RESOLVE D-N` blocks. §3.4 was
explicit: STATUS stays the canonical closure channel; introducing a
third parallel grammar would re-fragment the source of truth and
re-introduce the same class of bug the next time an agent invents
a fourth UI-prose variant.

Phase-4 coverage is automatic — `build_phase_ledger` at
[src/dual_research/ledger/build.py](src/dual_research/ledger/build.py)
reuses `_ingest_questions` / `_ingest_disagreements` for both phases.

**Tests (7 new):**

- New file `tests/test_spec_0217_ledger_status_authoritative.py`:
  - Test 5.1 — STATUS-only closure (disagreement): two-round synthetic;
    round 1 raises D-1 via STATUS, round 2 closes via STATUS only.
  - Test 5.2 — Legacy section-tail fallback (disagreement): no
    STATUS RESOLVED, but `## Resolved or non-blocking differences`
    body still closes D-1.
  - Test 5.3 — STATUS-wins on conflict (disagreement): STATUS says
    RESOLVED, body still lists D-1 as open under
    `## Substantive disagreements I'm holding`.
  - Test 5.4 — STATUS-only closure (question).
  - Test 5.5 — Legacy positional-match fallback (question).
  - Test 5.6 — STATUS-wins (question).
  - Test 5.7 — backend-language-choice regression replay (hermetic
    fixture under `tests/fixtures/spec_0217/phase2/` containing
    rounds 1–3 of the real session). All 5 D-items (`D-plan-c-01..05`)
    and 2 Q-items (`Q-plan-c-01..02`) close by round 3, not the
    round-5 hard cap.

Full suite: **1962 passed** (1955 baseline + 7 new).

## Implementation note — STATUS-RAISED seeding (small scope expansion)

Spec §3 describes the fix as the STATUS-pass for closures only. In
practice, the smoking-gun session's items appear in zero body sections
the legacy reconstructor reads — they live only in `### RAISE` blocks
under `## New items I'm raising` (a new-protocol grammar the
reconstructor didn't see before this spec). Without ALSO honoring
`STATUS.RAISED_THIS_TURN` as a raising channel, Test 5.7 cannot
replay against the real session — there would be no entries for the
closure pass to flip. The implementation extends the spec's principle
("STATUS is the canonical channel") symmetrically: closures from
`RESOLVED_THIS_TURN` + raises from `RAISED_THIS_TURN`, with body
sections as the legacy fallback for both halves. The §8 spurious-ID
mitigation still drops `RESOLVED`-but-never-`RAISED` IDs silently.

This means the openai-side items in the smoking-gun session
(`D-plan-g-*`, `Q-plan-g-*`) do NOT surface in the reconstructor
output — those were raised via a non-standard descriptive-string
array in round-1-openai's `RAISED_THIS_TURN`, not via the canonical
ID list. The reconstructor sees their RESOLVED closures but has no
matching raised entry, so they're dropped per §8. The spec's headline
regression (5 D + 2 Q items) is on the claude side, all properly
raised via canonical IDs; those all surface and close correctly.

## Deploy

`.github/workflows/deploy.yml` run
[26408366276](https://github.com/Lexiz/dual-research/actions/runs/26408366276)
succeeded on `main` commit `2b092de2492f5fb602aa3c0fa97c17f0d29c879f`.

**Note on deploy run history:** the first attempt of run 26408366276
failed at the Fly Machine API health-check polling step for machine
2/2 after a 5-minute timeout (`failed to get VM ... net/http: request
canceled`). Machine 1/2 had already passed smoke + machine checks
and reached a good state, and the new image was live on at least one
machine. A `gh run rerun --failed` retry passed cleanly on the
second attempt; the production endpoint at
`https://dual-research-alex.fly.dev/api/health` confirmed
`{"ok":true,"version":"1.44.22"}` between the two attempts and after.
The first-attempt failure was a transient Fly Machine API issue, not
a deploy-content regression.

## Empirical smoke

```
$ uv run python -c "
from pathlib import Path
from dual_research.ui.disagreements import reconstruct
from dual_research.ui.questions import reconstruct_questions
ds = reconstruct(Path('runs/20260525-135006-backend-language-choice'), phase=2)
qs = reconstruct_questions(Path('runs/20260525-135006-backend-language-choice'), phase=2)
print(f'disagreements: {len(ds)}')
for d in ds:
    print(f'  {d.id} status={d.status} closed_round={d.closed_round}')
print(f'questions: {len(qs)}')
for q in qs:
    print(f'  {q.id} status={q.status} answered_round={q.answered_round}')
"
disagreements: 5
  d-plan-c-01  status=resolved-gpt  closed_round=3
  d-plan-c-05  status=resolved-gpt  closed_round=3
  d-plan-c-02  status=resolved-gpt  closed_round=2
  d-plan-c-03  status=resolved-gpt  closed_round=2
  d-plan-c-04  status=resolved-gpt  closed_round=2
questions: 2
  q-plan-c-01  status=answered  answered_round=2
  q-plan-c-02  status=answered  answered_round=2
```

Pre-fix: both counts were `0`. Post-fix all 5+2 items surface with the
correct closure rounds, and `is_plan_agreed(..., ledger_open_count=0)`
would return True at round 3 instead of waiting for the additional
two administrative-closeout rounds the smoking-gun run burned through.

## Not done — explicitly out of scope

Per §7 of the spec:

- Phase-0 hash-drift escape (spec 0032) audit — separate spec.
- Per-phase runtime / round budget guardrail — separate spec.
- `### RESOLVE D-N` block parsing — explicitly NOT added (§3.4).
- UI / DS-token / design-system work.
- `is_plan_agreed` semantics — already correct.

## Deferred during implementation

- **OpenAI-side raise-channel hygiene.** The smoking-gun session's
  `round-01-openai.md` STATUS block emits `RAISED_THIS_TURN` as a
  multi-line array of descriptive strings (`"disagreement: Go #1 vs
  C# #1"`) rather than canonical IDs (`D-plan-g-01`). Result: the 5
  D-items + 1 Q-item openai later RESOLVEs in round 2 (`D-plan-g-01..05`,
  `Q-plan-g-02`) and 1 WITHDRAWs (`Q-plan-g-01`) never appear in the
  reconstructor output because no canonical ID was raised. The §8
  spurious-ID mitigation drops them correctly, but the ledger loses
  visibility into the negotiation that openai was tracking. Either
  (a) tighten the protocol prompt at `src/dual_research/protocol/prompts.py`
  to insist on canonical ID arrays in `RAISED_THIS_TURN`, OR (b)
  extend the reconstructor's STATUS pass to also walk ADDRESS / RESOLVE
  operation blocks for their `item_id` (the `parse_turn_v2` output
  already exposes these) so items raised via descriptive strings get
  retroactively assigned IDs from later operation blocks that reference
  them. Path (a) is the structurally correct fix — STATUS arrays
  should be ID-only by contract. Either way it's its own spec; not
  blocking 0217's headline regression.

"""Sample turn strings for parser/convergence tests."""

from __future__ import annotations

CANONICAL_AGREED_PLAN = """1. **Title:** Background
   **Key claims:**
   - Topic X has shifted in the last 18 months due to regulation Y.

2. **Title:** Analysis
   **Key claims:**
   - Approach A outperforms B on metric M for use-case U.

3. **Title:** Recommendation
   **Key claims:**
   - Adopt A with caveat C.
"""


CANONICAL_AGREED_PLAN_WITH_FSD = CANONICAL_AGREED_PLAN + """

## Final-surfaced disagreements (canonical)

### FSD-1: scope of caveat C

- Claude position: limited to enterprise tier
- GPT position: applies to all tiers
- Exact final-document treatment: state both positions; recommend enterprise-only as starting point
- Affects final recommendation? yes
"""


PLAN_TURN_AGREED = """## Answers to gpt's open questions
(none)

## What I researched since the last round
(none)

## Open questions for gpt
(none)

## Plan as I currently propose it
- Background, Analysis, Recommendation.

## Substantive disagreements I'm holding
(none)

## Resolved or non-blocking differences
1. D-1: <example>: status `resolved` — both agreed on metric M.

## Agreement check
- ENDORSEMENT: the plan covers the brief.
- MIND_CHANGED: none, my initial position survived review.
- REMAINING_UNCERTAINTY: confidence on caveat C is medium.
- STRONGEST_REMAINING_OBJECTION: caveat C could be overly cautious.
- WHY_NON_BLOCKING: caveat is disclosed in the recommendation section.

## AGREED_PLAN

""" + CANONICAL_AGREED_PLAN + """

## Drafter recommendation
- DRAFTER: claude (sentence why)
- DOMAIN_FIT_SELF: 4
- DOMAIN_FIT_OTHER: 4

## Status
STATUS: AGREED
OPEN_QUESTIONS: 0
BLOCKING_DISAGREEMENTS: 0
FINAL_SURFACED_DISAGREEMENTS: 0

## Sources
[1] https://example.com
"""


def plan_turn_agreed(drafter: str = "claude", fit_self: int = 4, fit_other: int = 4) -> str:
    return PLAN_TURN_AGREED.replace("DRAFTER: claude", f"DRAFTER: {drafter}").replace(
        "DOMAIN_FIT_SELF: 4", f"DOMAIN_FIT_SELF: {fit_self}"
    ).replace("DOMAIN_FIT_OTHER: 4", f"DOMAIN_FIT_OTHER: {fit_other}")


PLAN_TURN_NEGOTIATING = """## Answers to gpt's open questions
1. (answer)

## What I researched since the last round
1. Searched X, found Y.

## Open questions for gpt
1. What is your stance on Z?

## Plan as I currently propose it
- Background, Analysis, Recommendation.

## Substantive disagreements I'm holding
1. D-1: example — open

## Resolved or non-blocking differences
(none)

## Agreement check
(not ready) — waiting on D-1 resolution.

## AGREED_PLAN
(not agreed)

## Drafter recommendation
- DRAFTER: claude (sentence why)
- DOMAIN_FIT_SELF: 4
- DOMAIN_FIT_OTHER: 3

## Status
STATUS: NEGOTIATING
OPEN_QUESTIONS: 1
BLOCKING_DISAGREEMENTS: 1
FINAL_SURFACED_DISAGREEMENTS: 0

## Sources
[1] https://example.com
"""


PLAN_TURN_MALFORMED_MISSING_STATUS = """## Plan as I currently propose it
- Background, Analysis, Recommendation.

## Drafter recommendation
- DRAFTER: claude
- DOMAIN_FIT_SELF: 4
- DOMAIN_FIT_OTHER: 3

OPEN_QUESTIONS: 1
BLOCKING_DISAGREEMENTS: 0
FINAL_SURFACED_DISAGREEMENTS: 0
"""


REVIEW_TURN_APPROVED = """## Answers to gpt's prior comments
(none — first round)

## Issue ledger (delta + currently open)
1. I-1: ledger structure is clear, status `resolved`.

## Evidence checked this round
- New research performed: (none)
- Claims checked against existing sources: (none)
- Factual issues found: (none)
- No new research because: the draft cites well-vetted sources and no new claims emerged in this round.
- Corroboration on the other agent's claims:
  - Material [U] claims: (none)
  - Central [V] claims: (none)

## Comments on the current draft
(none)

## Disagreement carryover audit
- Final-surfaced disagreements from Phase 2: (none — full consensus)
- Resolved disagreements that re-emerged: (none)
- New disagreements raised during review: (none)

## Substantive disagreements I'm holding
(none)

## Drafter revision note
(reviewer — no draft edits)

## Approval check
- ENDORSEMENT: the draft satisfies the brief completely.
- NON_BLOCKING_LIMITATIONS: cite a tighter source if v3 emerges.
- STRONGEST_REMAINING_OBJECTION: minor wording in section 3.
- WHY_NON_BLOCKING: wording does not change reader decision.

## Status
STATUS: APPROVED
OPEN_ISSUES: 0
"""


REVIEW_TURN_REVIEWING = """## Answers to gpt's prior comments
1. (answer)

## Issue ledger (delta + currently open)
1. I-1: status `open` — citation broken.

## Evidence checked this round
- New research performed: (none)
- Claims checked against existing sources: source [2] returns 404
- Factual issues found: (none)
- No new research because: (n/a — sources checked)
- Corroboration on the other agent's claims:
  - Material [U] claims: (none)
  - Central [V] claims: (none)

## Comments on the current draft
1. Section 5: replace source [2] with a working URL.

## Disagreement carryover audit
- Final-surfaced disagreements from Phase 2: (none)
- Resolved disagreements that re-emerged: (none)
- New disagreements raised during review: (none)

## Substantive disagreements I'm holding
(none)

## Drafter revision note
(reviewer — no draft edits)

## Approval check
(not ready) — I-1 must be resolved.

## Status
STATUS: REVIEWING
OPEN_ISSUES: 1
"""


REVIEW_TURN_MISSING_EVIDENCE_SECTION = """## Answers to gpt's prior comments
(none)

## Issue ledger (delta + currently open)
(none)

## Comments on the current draft
(none)

## Approval check
- ENDORSEMENT: ok
- NON_BLOCKING_LIMITATIONS: none
- STRONGEST_REMAINING_OBJECTION: none
- WHY_NON_BLOCKING: n/a

## Status
STATUS: APPROVED
OPEN_ISSUES: 0
"""

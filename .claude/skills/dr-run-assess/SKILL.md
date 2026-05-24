---
name: dr-run-assess
description: |
  Diagnostic scorecard for a dual-research run on the
  backend-language-choice briefing. Scores six axes (F outcome + A–E + G
  diagnostics), diffs against the anchor run, attributes any F weakness
  to a specific diagnostic axis, and recommends the prompt or briefing
  edit that would move the needle on the next run. Use after a
  /dual-research-run on the backend-language-choice briefing completes.
---

# dr-run-assess

Diagnostic scorecard for a backend-language-choice dual-research run.
Not a report card — the point is to attribute outcome weakness to a
specific lever (a prompt section or a briefing section) so the next run
is a controlled experiment, not a re-roll.

## When to invoke

The user says one of:

- `/dr-run-assess <run-id>`
- `/dr-run-assess latest`
- "assess the latest backend-language run"
- "grade run `<run-id>`"

The argument is either a session-id slug
(`20260524-HHMMSS-backend-language-choice`) or `latest` (resolves to the
most recent `runs/*backend-language-choice*` directory).

## Causal model

The skill grades **one** outcome and **six** diagnostics. F is the
dependent variable; the others are independent variables, each tied to a
specific prompt or briefing section. If F is weak, the diagnostics tell
you *which lever* to tune on the next run.

| Axis | What it measures | Lever if weak |
|---|---|---|
| **F. Outcome quality** | Does the doc satisfy the brief on the brief's own terms? | (the dependent — moved by tuning A–E + G) |
| A. Recommendation structure | Required headings, sources block, confidence ledger | Phase 3 drafting prompt §required-structure; briefing's "Expected output shape" |
| B. Bias neutrality | Did the two named biases drive the ranking? | Phase 1 anti-hedging guardrail; briefing's "Known biases" |
| C. Disagreement health | Real P2 negotiation; D-Ns conceded with named evidence; FSDs justified | Phase 2 anti-sycophancy procedure; soft/hard caps; empty-turn invariant |
| D. Source hygiene | [V]/[U] discipline; citation round-trip | COMMON_PREAMBLE source-tagging contract; citation contract |
| E. Convergence machinery | AGREED/APPROVED clean; no cap-fallback; format-repair count low | Phase 2 hash-match procedure; force-verbatim-copy repair prompt |
| **G. Brief contribution** | Did brief ambiguity drag the outcome? | The Notion briefing pages |

## Anchor baseline

Reference run: `20260521-010637-dvs-backend-language-choice`. Anchor
scores are fixed at 5/5 across every axis until a future run beats it. If
this run scores above anchor on any axis, flag it in the verdict and
recommend promoting the anchor in the next assessment.

## Inputs to load

From `runs/<id>/`:

- `final.md` — Phase 3 drafted output (the document being graded)
- `state.json` — protocol state machine snapshot (round counts, FSDs, terminal STATUS values)
- `metrics.json` — token / timing / repair counts / warning sidecars
- `phase0/round-NN-<agent>.md` — preflight critiques (BRIEF_ISSUES counts)
- `phase1/round-NN-<agent>.md` — initial independent drafts
- `phase2/round-NN-<agent>.md` — negotiation turns
- `phase4/round-NN-<agent>.md` — review turns
- `transcript.jsonl` — full event stream (look for `phase2_hash_drift_detected`, `cited_url_not_in_consulted_sources`, format-repair events)

## Procedure

1. **Resolve run-id.** If `latest`, `ls -td runs/*backend-language-choice*/ | head -1` and strip the trailing slash.
2. **Verify run completed.** `runs/<id>/final.md` must exist. If not, report the failure mode and stop.
3. **Read all inputs.** Read every file listed above. Skim, don't full-quote.
4. **Score each axis 1–5** against the rubric below. For each axis, pull one verbatim quote (≤25 words) from the run artifacts as evidence.
5. **Compute delta vs anchor** (5/5 across the board). Δ is `this − anchor`.
6. **Attribute F.** Identify the diagnostic axis with the largest negative delta — that's the candidate cause. With only one or two comparison runs, attribution is suggestive, not causal — say "candidate cause", not "the cause".
7. **Write the recommended lever change.** Name the specific prompt or briefing section to edit on the next run. One change per next-run cycle; don't tune multiple knobs at once or attribution breaks.
8. **Print the scorecard, verdict paragraph, and top 3 evidence quotes.**

## Rubric — F. Outcome quality (headline)

Does the final document satisfy the brief on the brief's own terms?
Check, per the briefing's "Expected output shape" section:

- Single ranked recommendation present (one #1; the rest ranked or eliminated at Tier 1)
- Decision confidence stated (HIGH / MEDIUM / LOW + one-sentence reason + the single piece of evidence that would most shift confidence)
- Tier 1 pass/fail addressed for **every** candidate (7 candidates per the brief)
- Tier 2 scoring per candidate, with **2.1 (AI-coding-automation fitness) actually load-bearing** in the ranking — not just mentioned
- Flip criteria present and testable (conditions under which #2 would overtake #1)
- FSDs (if any) carry both positions + exact final-document treatment + materiality note

Score:

- **5** — all six bullets present and substantive
- **4** — five of six; missing piece is minor (e.g., flip criteria stated but not testable)
- **3** — single recommendation + confidence + Tier 1/2 present, but flip criteria missing OR Tier 2.1 mentioned but not load-bearing in the order
- **2** — recommendation present but Tier 1 not addressed per candidate, OR Tier 2 scoring vague
- **1** — no single recommendation, OR candidates not scored, OR hard constraints unaddressed

## Rubric — A. Recommendation structure (diagnostic)

Mechanical: does the Phase 3 output follow the required shape?

- Headings in the order specified by the Phase 3 drafting prompt (Summary → Findings → Disagreements left open → Open questions → Sources → Confidence ledger)
- Sources section numbered with URLs
- Confidence ledger table present with `Claim / Tag / Signal / Source notes` columns
- No mid-document `[V]/[U]` tags polluting body prose (confidence ledger is where confidence lives)

Score 1–5 by count of present-and-correct elements (5 = all four; 1 = none).

## Rubric — B. Bias neutrality (diagnostic)

Did the two named biases drive the ranking despite the briefing flagging them?

Search Phase 1 + Phase 2 turns for the bias phrases:

- "TypeScript on both sides" / "full-stack alignment"
- "more training data" / "training-data prevalence"

Check:

- Were the biases acknowledged-and-refuted, or absorbed silently?
- Did TypeScript or "training data" arguments appear in the **final ranking justification** above the Tier 2.1 floor?
- Did the agents explicitly cite the briefing's "Arguments that should not order candidates" when relevant?

Score:

- **5** — biases named and explicitly neutralised; final ranking unaffected
- **3** — biases acknowledged but absorbed into reasoning at a sub-attribute level
- **1** — bias drove the ranking; e.g., TS or "more training data" appears as a primary justification for #1

## Rubric — C. Disagreement health (diagnostic)

Was the negotiation real?

- `state.json` Phase 2 round count ≥ 2 (round 1 cannot agree per the protocol; ≥ 3 is healthier)
- At least one D-N item conceded with **named evidence** in a Phase 2 "What I researched since the last round" block (not "dropped as immaterial" — that's a no-op)
- FSDs (if any) carry "Why this could not be resolved this run" and "Why material" per the protocol
- Phase 4: drafter engaged in round 1 (per spec 0091); reviewer comments are addressed (accepted / rejected / resolved), not sidestepped
- Anti-sycophancy procedure visibly applied — at least one turn where an agent named the specific evidence that moved them

Score 1–5 by count of healthy signals.

## Rubric — D. Source hygiene (diagnostic)

- Every `[V]` tag in `final.md` resolves to a numbered row under `## Sources` with a real URL
- `metrics.json` (or `transcript.jsonl`) shows zero `cited_url_not_in_consulted_sources` warnings
- Material claims aren't all `[U]` — at least some live verification happened (count `[V]` tags in Phase 1 detailed-findings sections)
- No bare assertions of fact without `[V]` or `[U]` tags

Score 1–5 by count of clean signals.

## Rubric — E. Convergence machinery (diagnostic)

- Phase 2 hit `STATUS: AGREED` without hitting `hard_cap` (check `state.json`)
- Phase 4 hit `STATUS: APPROVED` without hitting `hard_cap`
- Format-repair count per phase ≤ 1 (search `transcript.jsonl` for `format_repair` events)
- No `phase2_hash_drift_detected` events that required `force_verbatim_copy` repair

Score 1–5 by count of clean signals.

## Rubric — G. Brief contribution (diagnostic)

Did the briefing itself drag the outcome?

- Sum `BRIEF_ISSUES` counts from `phase0/round-NN-{claude,openai}.md` preflight critiques
- Any framing concerns from Phase 0 that the briefing didn't address before Phase 1 fired?
- Did Phase 1 drafts reveal interpretation ambiguity that better briefing would have prevented? (look for material disagreement on what the brief was *asking*, distinct from disagreement on the answer)

Score:

- **5** — Phase 0 critiques flagged nothing material; no interpretation drift in Phase 1
- **3** — one or two minor concerns flagged; no impact on the answer
- **1** — Phase 0 flagged blockers that proceeded into Phase 1 anyway, OR the agents interpreted the question differently and that drove a disagreement that should have been a briefing fix

## Output format

Render exactly this:

```
# Run assessment — <run-id>

| Axis | This | Anchor | Δ | Evidence |
|---|---|---|---|---|
| **F. Outcome** | n/5 | 5/5 | ±n | "<≤25-word verbatim quote>" — phase N |
| A. Structure | n/5 | 5/5 | ±n | … |
| B. Bias neutrality | n/5 | 5/5 | ±n | … |
| C. Disagreement | n/5 | 5/5 | ±n | … |
| D. Source hygiene | n/5 | 5/5 | ±n | … |
| E. Convergence | n/5 | 5/5 | ±n | … |
| G. Brief | n/5 | 5/5 | ±n | … |

## Verdict

- **Decision-grade:** YES / PARTIAL / NO.
- **Protocol worked:** YES / PARTIAL / NO.

[One paragraph linking F to the weakest diagnostic. e.g. "F = 3/5 because
B = 2/5 — Phase 1 GPT draft absorbed the 'TS training data' argument
without surfacing it as a bias (quote, phase 1 GPT). With only one
comparison run this is a candidate cause, not the cause. Lever:
strengthen Phase 1 prompt's anti-hedging guardrail to explicitly require
acknowledging each named bias before scoring."]

## Recommended next-run tweak

- [Concrete prompt or briefing edit — name the file and the section]
- One change per cycle. If multiple axes are weak, pick the highest-delta one and ignore the rest until the next run.
- If F ≥ 4 and no diagnostic dragged it down, say "no change — this run is anchor-equivalent or better" and recommend promoting the anchor.

## Top evidence quotes

1. "<verbatim quote>" — phase N, agent X, round Y
2. "<verbatim quote>" — …
3. "<verbatim quote>" — …
```

## Scoring discipline

- **Score by the rubric, not by vibe.** If you can't quote evidence for a score, drop it by one notch.
- **Anchor stays fixed at 5/5** until a run scores higher. If this run scores above anchor on F, flag it and recommend promoting the anchor in the next run.
- **A 5 on F requires every "Expected output shape" bullet present.** Don't inflate.
- **Attribution is suggestive, not causal** with one or two comparison runs. Say "candidate cause", not "the cause".
- **One lever change per next-run cycle.** Tuning multiple knobs simultaneously destroys attribution.
- **The user sees the scorecard table first.** Don't bury it.

## Skill-versioning note

Project-local at `.claude/skills/dr-run-assess/SKILL.md`. Versions with
the code. If the briefing's "Expected output shape" section changes,
update Rubric F's checklist here in the same commit.

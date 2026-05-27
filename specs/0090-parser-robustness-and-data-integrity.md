---
spec: 0090
title: Parser robustness for cross-round Q/A/issue linkage + code-fence awareness (data-integrity overhaul)
label: new-feature
version-bump: MINOR
status: proposed
target-version: 0.71.0
created: 2026-05-19
pr: ""
disposition: archive
disposition_reason: "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy the new convention."
---

# Spec 0090 — Parser robustness for cross-round Q/A/issue linkage + code-fence awareness

## Context

A forensic dig into the two backend-language-choice runs (`2c4f` and
`27de`) — sparked by the user's observation that "an awful lot of open
questions are still being ghosted, and issues remain open" — uncovered
that **the system is asymmetrically blind to roughly half of what
Claude writes**. The agents are largely doing the right work; the
parsers can't see most of it.

### The headline finding

`_extract_answers_from_turn` in
[`ui/questions.py:63-110`](../src/dual_research/ui/questions.py) parses
the `## Answers to {other}'s open questions` section as **numbered
list items** (`1.`, `2.`, etc., column-anchored). The two vendor
models use systematically different formats:

- **OpenAI** uses `1. **C-1 / C-4 — title:** body` — numbered-list
  with the ID embedded in the bold label. Parser extracts cleanly.
- **Claude** uses `**Q-g-r1-01 — title**\n\nbody` — bold header per
  Q-N, no numbered list. Parser extracts **zero answers**.

I ran the extractor on the `claude r02` turn in both runs. Both
returned `0 answers` despite the turn bodies containing 5-8 fully-
written answers each to GPT's prior questions. The arithmetic works
out exactly:

For `2c4f` Phase 2 (24 total questions, 12 marked "answered", 12
"open" per the ledger):

| Direction | Round count | Format | Detected by parser |
|---|---|---|---|
| GPT's questions → Claude's answers | 8 (r1) + 4 (r2) = 12 | bold-header | **0** |
| Claude's questions → OpenAI's answers | 5 (r1) + 4 (r2) + 3 (r3) = 12 | numbered | up to 12 |
| Total | 24 | mixed | **12** |

Every "ghosted" question in both runs is a question GPT asked that
Claude actually answered in bold-header format. **The ledger's
"open question" count is structurally biased upward by exactly the
volume of Claude's answers.**

### Why this matters beyond the visualisation

The ledger's inflated open-count feeds the spec-0043-D7 cross-check
that blocks convergence. That's the underlying cause of the stuck-
AGREED loops spec 0089 § B's escape valve was designed to break.
After this fix:

- The ledger's open count becomes accurate.
- Spec 0089 § B's stuck-AGREED escape valve becomes a true safety
  net for genuine deadlocks rather than a workaround for invisible
  Claude answers.
- `STUCK_AGREED_K = 2` stays appropriate (no reason to tighten to
  K=1 once the false-positive cause is removed).

### Phase 4 has the same shape

`27de` Phase 4: 24 of 106 issues marked "open" after 6 review rounds.
Yet Claude's r3 Phase-4 turn explicitly resolves every one of GPT's
r1 issues: `**[I-g-r1-01]** — **resolved.** Inline [V]/[U] tags
added throughout the round-2 revised draft.` (etc., for I-g-r1-01
through I-g-r1-05). The issue-resolution parser in `ui/issues.py`
has its own format expectations and isn't matching Claude's
cross-round-ID-style references. Same root-cause class as P2.

The "Phase 4 Claude approves on r1 with 0 issues" pattern I flagged
earlier as possible sycophancy is now ambiguous — Claude may be doing
thorough review work that the parser can't see, then reporting
`OPEN_ISSUES: 0` based on his internal accounting. Re-investigate
post-fix; out of scope here.

### Plus an adjacent parser bug surfaced during spec 0089

`extract_fenced_section(text, "AGREED_PLAN")` doesn't respect ```` ``` ```` 
markdown code fences — it truncates at the first `## ` heading inside
the text, even if that heading appears inside a fenced code block.
For any FSD>0 turn (where the canonical `## Final-surfaced
disagreements (canonical)` sub-section sits inside the agents'
``` ```markdown ... ``` ``` fenced plan), this leaves `parsed.agreed_plan` as
just the fence opener (`` ```markdown ``). Spec 0089 § A worked
around this with the `compose_full_agreed_plan` helper. Fixing
`extract_fenced_section` properly removes the need for that
workaround and improves correctness elsewhere (notably Phase 3's
drafting prompt, which currently sees just the fence opener as the
"plan" for FSD>0 cases).

## Proposed change

Three coordinated sections, scoped to make the system reliable
against **model output variation** (the main reliability risk —
two different vendor models with different style preferences).

### § A — Answer-detection robustness (`ui/questions.py`, `ui/issues.py`)

Three changes to `_extract_answers_from_turn` and its issue-
resolution sibling:

1. **Accept both numbered-list AND bold-header formats.** Walk the
   "Answers to" section body line-by-line; an "answer block" starts
   at any of:
   - A numbered list item (`^\s*(\d+)[.)]\s+`) — today's pattern
   - A bold-header line where the bold body's first token looks like
     an ID (`^\*\*[A-Z][A-Z]?-[gcrop]?-?[rp]?\d+(-\d+)?\b`)
   - A markdown H3 heading where the title's first token looks like
     an ID (`^###\s+[A-Z]+-\d+`)

   Each block ends at the next block-start or the next H2 heading.

2. **ID-based primary matching.** For each extracted answer block,
   look for an ID token (`Q-c-r1-01`, `OAI-P4-1`, `C-2`, `I-g-r2-05`,
   `FSD-1`, `D-3`, etc. — accept the full ID alphabet the protocol
   uses) in the **first line** of the block. When present, match by
   ID against the open question/issue ledger. When absent, fall back
   to today's positional matching for backward compatibility.

3. **Scan beyond just `round_n + 1`.** Today the reconstruction only
   looks for answers in the IMMEDIATE next round (line 217 of
   `ui/questions.py`). If Claude doesn't answer in r2 but does in r3,
   r3's answers are lost. The new behaviour scans all subsequent
   rounds; an answer's `answered_round` field carries the round
   where it actually landed (might be > raised_round + 1).

   Open question: should we cap the look-ahead at N=3 rounds to
   protect against false matches in very long phases? Recommend
   yes; default N=5 (covers the soft cap with margin). Configurable
   via module constant.

Same three changes applied to the issue-resolution parser in
`ui/issues.py` (mutatis mutandis — different section header, same
ID-block structure). And to the question-reconstruction in Phase 4
(`## Answers to {other}'s prior comments`).

### § B — Prompt tightening with inline example (`protocol/prompts.py`)

Add an explicit, format-anchoring inline example to the `## Answers
to {other_name}'s open questions` section instruction in
`negotiation_turn_prompt`, and the symmetric `## Answers to
{other_name}'s prior comments` section in `review_turn_prompt`.

Current text (`prompts.py:320-321`):

```
## Answers to {other_name}'s open questions
Address every numbered question {other_name} listed in their most recent turn. If their last turn had none, write "(none)".
```

Proposed text:

```
## Answers to {other_name}'s open questions
Address every numbered question {other_name} listed in their most recent turn (and any prior-round question still open in the standing-items section below). One answer block per question. The first line of each answer block MUST start with the question's ID (e.g., `Q-g-r1-01`) so the system can link your answer to the originating question.

Use this exact format:

  1. **Q-g-r1-01 — short title:** your answer body…
  2. **Q-g-r1-02 — short title:** your answer body…

If {other_name}'s last turn had no open questions and the standing-items section is empty, write "(none)".
```

This:
- Names the exact ID format
- Names the cross-round expectation (answer items raised in prior rounds, not just last round)
- Provides a copy-pasteable example
- Stays compatible with whatever § A's parser accepts (the parser is the contract; the example anchors UI consistency)

Same treatment for the P4 "prior comments" answers section and for
the P4 `## Issue ledger (delta + currently open)` instruction
(which today doesn't specify the ID format for status transitions).

### § C — `extract_fenced_section` code-fence awareness (`protocol/parse.py`)

`extract_fenced_section(text, heading_name)` (`parse.py:51-66`)
uses a naive `^##\s+\S` regex to find the next `## ` heading after
the target heading and uses it as the section boundary. The regex
doesn't know about ```` ``` ```` markdown code fences, so a `## ` line
INSIDE a fenced code block falsely terminates the section.

Fix: pre-process the search-region by masking out the contents of
fenced code blocks before the boundary regex runs. Concrete
algorithm:

```python
def _next_h2_outside_fences(text: str) -> re.Match | None:
    """Return the first ``^##\\s+\\S`` match in ``text`` that is NOT
    inside a fenced code block. Recognises both ```` ``` ```` and
    ```` ~~~ ```` fences; supports a language tag after the opener.
    Doesn't recurse into nested fences (markdown doesn't allow
    them; we'd treat them as literal).
    """
    fence_re = re.compile(r"^(```|~~~)[^\n]*$", re.MULTILINE)
    in_fence = False
    h2_re = re.compile(r"^##\s+\S", re.MULTILINE)

    # Build a mask of positions inside fences.
    positions_in_fence: list[tuple[int, int]] = []
    fence_start: int | None = None
    for m in fence_re.finditer(text):
        if not in_fence:
            fence_start = m.end()
            in_fence = True
        else:
            positions_in_fence.append((fence_start or 0, m.start()))
            in_fence = False
    if in_fence and fence_start is not None:
        positions_in_fence.append((fence_start, len(text)))

    for m in h2_re.finditer(text):
        if not any(start <= m.start() < end for start, end in positions_in_fence):
            return m
    return None
```

`extract_fenced_section` swaps its inner `re.search(r"^##\s+\S", rest,
re.MULTILINE)` for `_next_h2_outside_fences(rest)`. Returns the body
between the target heading and the next REAL `## ` heading.

Downstream effects:
- `parse_turn`'s `agreed_plan` field now correctly contains the FULL
  fenced plan body, including the canonical FSD sub-section when
  agents emit it inside the fence (3a4a-style happy path).
- `extract_canonical_fsd_items` correctly finds canonical FSDs
  whether they're inside the fence or as sibling sections.
- `normalized_hash(agreed_plan)` now hashes meaningful plan content
  for FSD>0 turns — closing a hidden bug where every FSD>0 turn's
  plan was trivially hash-equal because they all extracted to the
  same fence opener.
- Spec 0089's `compose_full_agreed_plan` helper becomes unnecessary
  for fences-inside-plan turns (still useful for sibling-section
  turns); kept for backward compatibility, becomes a no-op for
  most cases.

### § D — Cache-bust + version bump

- `?v=0091` → `?v=0092` across `index.html` (defensive; no static
  asset changes here).
- Version `0.70.0` → `0.71.0` (MINOR per the `new-feature` label).

### § E — Regression / backfill considerations

This spec **changes the meaning of `state.agreed_plan` for FSD>0
runs after § C lands**. Previously: just the fence opener. After:
the full plan body. Existing runs persisted to Supabase have the
old (broken) value frozen in `runs.state` JSON. We do NOT backfill
those — the in-app run-detail page reads agreed_plan from
`session_files['state.json']`, which is also frozen. Old run pages
will keep showing the broken value; new runs benefit immediately.

A "rederive ledger / state.agreed_plan from on-disk turn files"
CLI is a future spec if we want to backfill. Out of scope here.

## Out of scope

- **Phase 4 sycophancy investigation** — needs to wait for post-fix
  data to distinguish "Claude is sycophantic" from "Claude does
  thorough review in a format the old parser couldn't see." Will
  be its own spec after a few clean runs.
- **`STUCK_AGREED_K = 1` evaluation** — defer. With the parser fixed
  the ledger's open count will be accurate; the escape valve fires
  on real stuck cases. Worth revisiting if we observe new genuine-
  stuck patterns in production data.
- **Backfilling old runs' ledgers + state.agreed_plan** — mechanical
  re-derivation from on-disk turn files; cheap but separate work.
- **Cross-round disagreement-resolution parser robustness** — the
  D-N resolution path uses a different parser
  (`ui/disagreements.py`) that may have its own format-brittleness.
  We didn't see evidence of disagreements being ghosted (both runs
  showed 9/9 disagreements resolved), so we're not extending § A
  to that parser preventatively. If post-fix data shows
  disagreements going stale, follow-up spec.
- **Standing-items section ordering / capping** — the
  `build_standing_items_section` helper already caps at 30 items /
  3000 chars; no changes here.
- **Vendor-specific prompt tuning** (e.g., a Claude-specific
  reminder to use numbered lists) — heavier than § B's universal
  inline example; saved for if § B doesn't move adherence enough
  on its own.

## Test plan

### Unit (`tests/`)

- [ ] `test_questions_extract_bold_headers.py` (new) — feed the
      parser the exact `claude r02` body from `2c4f` and assert it
      extracts 8 answers (currently returns 0). Same fixture, two
      formats (numbered + bold-header), assert ID matches.
- [ ] `test_questions_extract_id_based_matching.py` (new) — answer
      block lists IDs out of order from the originating questions;
      assert ID-based matching links them correctly.
- [ ] `test_questions_extract_multi_round_lookahead.py` (new) —
      raise Q-N in r1, leave r2 unanswered, address in r3 with
      explicit ID; assert `answered_round=3`. Cap at N=5 verified.
- [ ] `test_issues_extract_id_based_matching.py` (new) — same as
      questions but for `ui/issues.py`. Use `27de` Phase 4
      `claude r03` `**[I-g-r1-01]** — **resolved.**` style.
- [ ] `test_parse_extract_fenced_section_respects_fences.py` (new) —
      feed `extract_fenced_section` a turn with `## AGREED_PLAN`
      containing a fenced plan body that has internal `## Foo`
      headings; assert the section body includes the internal
      headings (today: truncated). Mixed ```` ``` ```` and ```` ~~~ ````
      fences. Unclosed-fence edge case.
- [ ] `test_prompts_answer_format_example.py` (new) — assert the
      inline example appears verbatim in `negotiation_turn_prompt`
      output. (Snapshot-style.)

### Integration / replay

- [ ] `test_2c4f_ledger_with_new_parser.py` (new) — re-run
      `build_phase_ledger` on the checked-in 2c4f fixture (the
      `tests/fixtures/spec0089/2c4f-r04-*.md` pair plus newly-added
      r02-r03 pairs) under the new parser. Assert the open-question
      count drops from 12 to ≤ 2 (the residual ghosted-by-other-
      means rate). Assert `is_plan_agreed(ledger_open_count=…)`
      now returns True at r4 with the corrected ledger.
- [ ] `test_27de_phase4_issues_with_new_parser.py` (new) — re-run
      `build_phase_ledger` on checked-in `27de` Phase 4 fixture
      slice. Assert the 5 OAI-P4-* issues raised in r1 are detected
      as resolved in claude's r3 issue ledger.
- [ ] **Regression**: 800 + 34 (spec 0089) + new tests, all green.

### Live smoke (post-deploy)

- [ ] Fire a fresh `dual-research run` via the `dual-research-run`
      skill on a multi-tradeoff brief that's likely to spark 5+
      cross-agent questions. Inspect the run-detail UI: every
      question raised should show an `answered` chip on the next
      round's turn, NOT `⚠ ghosted`.
- [ ] Confirm Phase 4 issue ghosting drops similarly.
- [ ] Spec 0089 § B stuck-AGREED escape should NOT fire on this run
      (the parser fix means agents fully aligned → ledger agrees →
      strict convergence at the natural round).

## Risks

- **Parser ambiguity from looser ID-token matching.** A narrative
  reference to "see Q-g-r1-01 above" in an answer body could be
  mis-detected as a new answer if our block-start regex isn't
  strict enough. Mitigation: ID must appear in the FIRST LINE of
  the block; bold-header blocks require the bold body to LEAD with
  the ID token; numbered-list blocks require the ID inside the
  bold label.
- **False positives from cross-round look-ahead.** If Claude
  re-references an old Q-N in a later-round answer block, we might
  incorrectly mark a follow-up answer as the original answer.
  Mitigation: first-ID-occurrence-wins; once a Q-N is marked
  answered with round N, later references don't overwrite. Plus
  the cap (N=5) protects against very-late false matches.
- **§ C code-fence parser misreads non-Markdown fences.** Some
  agents have occasionally emitted indented code blocks instead of
  fenced ones. The new fence-aware parser only handles ```` ``` ````
  and ```` ~~~ ```` fences; indented blocks aren't affected (their
  `## ` lines, if any, would still terminate the section). Behaviour
  for indented blocks is unchanged from today.
- **Persisted state.agreed_plan shape change.** § C makes
  `state.agreed_plan` carry the full plan body for FSD>0 turns. The
  Phase 3 drafting prompt receives the larger plan now — increases
  token usage slightly for those runs. Acceptable; the prompt
  budget has headroom and Phase 3 is single-shot.
- **Backward compatibility with old persisted runs.** The fix
  changes parser behaviour; runs already in Supabase keep their
  old `state.agreed_plan` value. The UI may render the old (broken)
  plan for those runs — but it was already broken, so no
  regression. New runs benefit immediately.
- **Spec 0089 § A's `compose_full_agreed_plan` becomes mostly a
  no-op.** That's fine — we keep it for runs where agents emit the
  canonical as a sibling section instead of inside the fence
  (defense in depth).

## Open questions

- **Look-ahead cap N**: recommend `MAX_ANSWER_LOOKAHEAD_ROUNDS = 5`.
  Will revisit if data shows answers landing further out.
- **Should the prompt example use bold-header or numbered-list
  form?** Recommend numbered-list (today's OpenAI style) because
  it survives a wider set of historical parsers and the UI renders
  it cleanly. The PARSER accepts both either way.
- **Spec 0089 `compose_full_agreed_plan` cleanup**: leave in place
  this spec, mark as "defense in depth" in the docstring. Remove
  in a future cleanup spec once we have post-fix data confirming §
  C handles all real-world cases.

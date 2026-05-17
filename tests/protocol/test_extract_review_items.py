"""Structured review-item extraction — spec 0027.

`extract_review_items` walks a Phase 2 turn body and pulls each
question / disagreement / resolved item into a structured `ReviewItem`,
with optional `quote` / `after` anchors lifted from `> quote: …` /
`> after: …` blockquote sub-lines under each item.
"""

from __future__ import annotations

from textwrap import dedent

from dual_research.protocol.parse import (
    ReviewItem,
    extract_review_items,
)


def test_extracts_open_questions_with_quotes() -> None:
    text = dedent(
        """
        ## Open questions for openai

        1. Why not Postgres for the read-heavy path?
           > quote: I recommend SQLite for the entire surface for simplicity
        2. What's your evidence for the 50 % write penalty claim?
           > quote: writes are roughly 50 % slower under contention

        ## Plan as I currently propose it
        - foo
        """
    ).strip()
    items = extract_review_items(text)
    questions = [i for i in items if i.kind == "question"]
    assert len(questions) == 2
    assert questions[0].body.startswith("Why not Postgres")
    assert questions[0].quote == "I recommend SQLite for the entire surface for simplicity"
    assert questions[1].quote == "writes are roughly 50 % slower under contention"
    assert all(q.after is None for q in questions)


def test_after_marker_for_missing_content() -> None:
    text = dedent(
        """
        ## Open questions for openai

        1. The draft never addresses backup strategy at all.
           > after: 4. Operations

        ## Plan as I currently propose it
        - foo
        """
    ).strip()
    items = extract_review_items(text)
    assert len(items) == 1
    assert items[0].after == "4. Operations"
    assert items[0].quote is None


def test_extracts_substantive_disagreements_with_anchor_id() -> None:
    text = dedent(
        """
        ## Substantive disagreements I'm holding

        - D-3: index strategy — status: open
          - (a) D-3 index strategy
          - (b) my position: composite (created_at, status) is sufficient
          - (c) openai's position: needs covering index
          > quote: Postgres can do composite without partial — fine for our scale

        - D-4: cache layer — status: open
          - (a) D-4 cache layer
          > after: 6. Cache layer

        ## Final-surfaced disagreements
        (none)
        """
    ).strip()
    items = extract_review_items(text)
    disagreements = [i for i in items if i.kind == "disagreement"]
    assert {d.item_id for d in disagreements} == {"D-3", "D-4"}
    d3 = next(d for d in disagreements if d.item_id == "D-3")
    assert "Postgres can do composite" in (d3.quote or "")
    d4 = next(d for d in disagreements if d.item_id == "D-4")
    assert d4.after == "6. Cache layer"


def test_resolved_section_is_classified_as_resolved() -> None:
    text = dedent(
        """
        ## Resolved or non-blocking differences

        - **D-1 (timezone handling):** `resolved` — both now agree on UTC.
        - **D-2 (HTTP/2 push):** `non_blocking_limitation` — minor, doesn't block.
        """
    ).strip()
    items = extract_review_items(text)
    resolved = [i for i in items if i.kind == "resolved"]
    assert {r.item_id for r in resolved} == {"D-1", "D-2"}


def test_round_1_diff_section_treated_as_claims() -> None:
    """Spec 0042 D6 — Round-1 difference inventory parses as ``claim``,
    not ``disagreement``. Pre-spec they bucketed as disagreement; the
    semantic shift is that R1 enumerates contested points being raised,
    only R≥2's ``## Substantive disagreements I'm holding`` holds them.
    """
    text = dedent(
        """
        ## Diff vs openai's Phase 1

        1. They propose SQLite, I propose Postgres for the write path.
           > quote: SQLite is fine end-to-end for our scale
        2. They omit any mention of failover.
           > after: 5. Reliability
        """
    ).strip()
    items = extract_review_items(text)
    assert [i.kind for i in items] == ["claim", "claim"]
    assert items[0].quote and "SQLite is fine" in items[0].quote
    assert items[1].after == "5. Reliability"


def test_un_anchored_items_still_extracted() -> None:
    text = dedent(
        """
        ## Open questions for openai

        1. Bare question with no anchor at all.
        2. Another question, also bare.

        ## Plan as I currently propose it
        - foo
        """
    ).strip()
    items = extract_review_items(text)
    assert len(items) == 2
    assert all(i.quote is None and i.after is None for i in items)


def test_empty_text_returns_empty_list() -> None:
    assert extract_review_items("") == []
    assert extract_review_items(None) == []  # type: ignore[arg-type]


def test_quote_marker_tolerates_extra_whitespace_and_backticks() -> None:
    text = dedent(
        """
        ## Open questions for claude

        1. Question about a specific span.
           >   quote:   `the exact phrase they used`
        """
    ).strip()
    items = extract_review_items(text)
    assert len(items) == 1
    assert items[0].quote == "the exact phrase they used"


def test_returns_review_item_dataclass() -> None:
    text = dedent(
        """
        ## Open questions for openai

        1. A question.
           > quote: a span
        """
    ).strip()
    items = extract_review_items(text)
    assert isinstance(items[0], ReviewItem)


# ─── Phase 4 sections (spec 0028) ────────────────────────────────────────────


def test_phase4_issue_ledger_extracted() -> None:
    text = dedent(
        """
        STATUS: REVIEWING

        ## Issue ledger (delta + currently open)

        1. I-1 status: open — Confidence ledger missing for the cohort baseline.
           > after: 6. Confidence ledger
        2. I-2 status: open — Sources section duplicates citation [4] and [7].
           > quote: [4] U.S. Census Bureau, "American Community Survey 2024"

        ## Evidence checked this round
        - foo
        """
    ).strip()
    items = extract_review_items(text)
    assert len(items) == 2
    assert items[0].after == "6. Confidence ledger"
    assert items[1].quote and "American Community Survey" in items[1].quote


def test_phase4_comments_on_draft_extracted() -> None:
    text = dedent(
        """
        STATUS: REVIEWING

        ## Comments on the current draft

        1. (a) Findings section, second paragraph; (b) framing reads as causal but
           the underlying evidence is correlational; (c) reframe as "associated with".
           > quote: density causes lower per-household retrofit cost
        2. (a) Disagreements section; (b) FSD-2 missing from the body; (c) add it.
           > after: 3. Disagreements left open

        ## Disagreement carryover audit
        - foo
        """
    ).strip()
    items = extract_review_items(text)
    assert len(items) == 2
    assert items[0].quote and "density causes lower" in items[0].quote
    assert items[1].after == "3. Disagreements left open"


def test_phase4_issue_ledger_and_comments_combine() -> None:
    text = dedent(
        """
        STATUS: REVIEWING

        ## Issue ledger (delta + currently open)

        1. I-1 status: open — One issue.
           > quote: claim under question

        ## Comments on the current draft

        1. (a) section x; (b) issue y; (c) change z.
           > after: 4. Operations

        ## Disagreement carryover audit
        """
    ).strip()
    items = extract_review_items(text)
    assert len(items) == 2
    # Order: Issue ledger before Comments (matches section order in the text).
    assert items[0].quote == "claim under question"
    assert items[1].after == "4. Operations"


def test_phase4_substantive_disagreements_extracted() -> None:
    """Phase 4 turns reuse the same `## Substantive disagreements I'm holding`
    section shape as Phase 2 — the existing parser path handles them."""
    text = dedent(
        """
        STATUS: REVIEWING

        ## Substantive disagreements I'm holding

        - D-5: cohort definition — status: open
          > quote: we limit the cohort to single-family households
        """
    ).strip()
    items = extract_review_items(text)
    assert len(items) == 1
    assert items[0].kind == "disagreement"
    assert items[0].item_id == "D-5"
    assert items[0].quote and "cohort to single-family" in items[0].quote


# ─── Spec 0042 — Phase 1 sections + Diff vs re-bucketing ──────────────


def test_spec0042_phase1_claims_section_extracted() -> None:
    """Phase 1 drafts use ``## N. Claims I Expect the Other Agent Might
    Dispute`` (with optional leading numeric prefix). Items extract as
    ``kind="claim"``."""
    text = dedent(
        """
        ## 4. Claims I Expect the Other Agent Might Dispute

        1. **First claim.** Body of first.

        2. **Second claim.** Body of second.

        ## 5. Open Questions

        **Q1: A question?**
        - Specific question: foo
        """
    ).strip()
    items = extract_review_items(text)
    claims = [i for i in items if i.kind == "claim"]
    qs = [i for i in items if i.kind == "question"]
    assert len(claims) == 2
    assert len(qs) == 1
    assert claims[0].body.startswith("**First claim.**")
    assert qs[0].body.startswith("**Q1:")


def test_spec0042_phase1_open_questions_without_for_suffix() -> None:
    """Phase 1 uses ``## Open Questions`` (no ``for X`` suffix). Numeric
    prefix tolerated. Falls back when Phase 2's ``Open questions for X``
    form is also present (avoids double-extracting)."""
    text = dedent(
        """
        ## Open Questions

        **Q1: First question?**
        - body
        **Q2: Second question?**
        - body
        """
    ).strip()
    items = extract_review_items(text)
    questions = [i for i in items if i.kind == "question"]
    assert len(questions) == 2


def test_spec0042_diff_vs_is_claim_not_disagreement() -> None:
    """Spec 0042 D6 — ``## Diff vs … Phase 1`` items bucket as ``claim``,
    not ``disagreement``. The R≥2 ``## Substantive disagreements I'm
    holding`` section is the only source of ``disagreement`` items."""
    text = dedent(
        """
        ## Diff vs openai's Phase 1

        **D-1** — **A contested point.** body.

        **D-2** — **Another contested point.** body.
        """
    ).strip()
    items = extract_review_items(text)
    assert len(items) == 2
    assert all(i.kind == "claim" for i in items)


def test_spec0042_substantive_disagreements_still_kind_disagreement() -> None:
    """R≥2 ``## Substantive disagreements I'm holding`` still produces
    ``kind="disagreement"`` (unchanged)."""
    text = dedent(
        """
        ## Substantive disagreements I'm holding

        - **D-1**: a contested point — status: open
          > quote: source
        """
    ).strip()
    items = extract_review_items(text)
    assert len(items) == 1
    assert items[0].kind == "disagreement"
    assert items[0].item_id == "D-1"

from __future__ import annotations

from dual_research.protocol import (
    extract_fenced_section,
    parse_preflight_turn,
    parse_turn,
)
from tests.protocol.fixtures import (
    PLAN_TURN_AGREED,
    PLAN_TURN_NEGOTIATING,
    REVIEW_TURN_APPROVED,
)


def test_parse_agreed_plan_turn() -> None:
    p = parse_turn(PLAN_TURN_AGREED)
    assert p.status == "AGREED"
    assert p.drafter == "claude"
    assert p.open_questions == 0
    assert p.blocking_disagreements == 0
    assert p.final_surfaced_disagreements == 0
    assert p.domain_fit_self == 4
    assert p.domain_fit_other == 4
    assert p.agreed_plan is not None
    assert "Title:" in p.agreed_plan
    assert p.strongest_remaining_objection is True
    assert p.why_non_blocking is True


def test_parse_negotiating_plan_turn() -> None:
    p = parse_turn(PLAN_TURN_NEGOTIATING)
    assert p.status == "NEGOTIATING"
    assert p.drafter == "claude"
    assert p.open_questions == 1
    assert p.blocking_disagreements == 1
    assert p.final_surfaced_disagreements == 0
    # The agreed_plan section exists but holds "(not agreed)" — this is by
    # design; convergence checks gate on STATUS != AGREED, not on plan content.
    assert p.agreed_plan == "(not agreed)"


def test_parse_review_approved_turn() -> None:
    p = parse_turn(REVIEW_TURN_APPROVED)
    assert p.status == "APPROVED"
    assert p.open_issues == 0
    assert p.evidence_checked_section is True
    assert p.carryover_audit_section is True
    assert p.strongest_remaining_objection is True
    assert p.why_non_blocking is True


def test_parse_preflight_turn_ok() -> None:
    text = "## Brief clarity\n\nOK\n\n## Status\nSTATUS: BRIEF_OK\nBRIEF_ISSUES: 0"
    p = parse_preflight_turn(text)
    assert p.status == "BRIEF_OK"
    assert p.brief_issues == 0


def test_parse_preflight_turn_needs_input() -> None:
    text = "## Status\nSTATUS: BRIEF_NEEDS_INPUT\nBRIEF_ISSUES: 3"
    p = parse_preflight_turn(text)
    assert p.status == "BRIEF_NEEDS_INPUT"
    assert p.brief_issues == 3


def test_extract_fenced_section_basic() -> None:
    text = "## Foo\n\nfoo body\n\n## Bar\n\nbar body\n"
    assert extract_fenced_section(text, "Foo") == "foo body"
    assert extract_fenced_section(text, "Bar") == "bar body"
    assert extract_fenced_section(text, "Missing") is None


def test_extract_fenced_section_with_indented_subheadings() -> None:
    text = "## Plan\n\n### Section\n\nbody1\n\n### Section 2\n\nbody2\n\n## Next\n\nignored\n"
    section = extract_fenced_section(text, "Plan")
    assert section is not None
    assert "body1" in section
    assert "body2" in section
    assert "ignored" not in section


def test_parser_tolerates_decoration() -> None:
    text = "> - `STATUS: AGREED`\n> - `OPEN_QUESTIONS: 0`\n> - `BLOCKING_DISAGREEMENTS: 0`\n> - `FINAL_SURFACED_DISAGREEMENTS: 0`\n> - `DRAFTER: claude`"
    p = parse_turn(text)
    assert p.status == "AGREED"
    assert p.open_questions == 0
    assert p.blocking_disagreements == 0
    assert p.final_surfaced_disagreements == 0
    assert p.drafter == "claude"


def test_missing_fields_parse_as_none() -> None:
    p = parse_turn("just some prose")
    assert p.status is None
    assert p.drafter is None
    assert p.open_questions is None
    assert p.open_issues is None
    assert p.blocking_disagreements is None
    assert p.final_surfaced_disagreements is None


# ─── Spec 0036 — parser fixes ────────────────────────────────────────────────


from dual_research.protocol.parse import (
    EVIDENCE_CHECKED_SECTION_RE,
    CARRYOVER_AUDIT_SECTION_RE,
    extract_revised_draft as _extract_revised_draft,
    extract_revised_draft_inclusive,
)


def test_evidence_checked_regex_matches_trailing_context() -> None:
    """Spec 0036: word-boundary fix lets the heading carry trailing text."""
    cases = [
        "## Evidence checked this round",
        "## Evidence checked this round (3 sources)",
        "## Evidence checked this round:",
        "## Evidence checked this round - notes follow",
    ]
    for text in cases:
        assert EVIDENCE_CHECKED_SECTION_RE.search(text), f"regex missed: {text!r}"


def test_evidence_checked_regex_does_not_false_positive_on_roundup() -> None:
    assert not EVIDENCE_CHECKED_SECTION_RE.search("## Evidence checked this roundup")
    assert not EVIDENCE_CHECKED_SECTION_RE.search("## Evidence checked this roundtable")


def test_carryover_audit_regex_matches_trailing_context() -> None:
    """Spec 0036: parallel fix to the evidence regex."""
    assert CARRYOVER_AUDIT_SECTION_RE.search("## Disagreement carryover audit")
    assert CARRYOVER_AUDIT_SECTION_RE.search("## Disagreement carryover audit (none)")


def test_extract_revised_draft_strips_horizontal_rule_only_body() -> None:
    """Spec 0036: body of just `----` reads as no draft."""
    text = "## Revised draft\n\n----\n\n## Next section\n\nbody\n"
    assert _extract_revised_draft(text) is None


def test_extract_revised_draft_strips_all_hr_forms() -> None:
    for sep in ("----", "____", "****", "---", "___", "***"):
        text = f"## Revised draft\n\n{sep}\n\n## Next\n"
        assert _extract_revised_draft(text) is None, f"failed for sep {sep!r}"


def test_extract_revised_draft_inclusive_absorbs_stray_sibling_heading() -> None:
    """Drafter emitted `## Plan summary` as a sibling instead of `### Plan summary`."""
    text = (
        "## Revised draft\n\n"
        "preamble line\n\n"
        "## Plan summary\n\n"  # NOT in the protocol allowlist → absorbed
        "absorbed body\n\n"
        "## Summary\n\n"  # allowlisted → terminates the draft
        "real summary\n"
    )
    body = extract_revised_draft_inclusive(text)
    assert body is not None
    assert "preamble line" in body
    assert "## Plan summary" in body
    assert "absorbed body" in body
    assert "real summary" not in body


def test_extract_revised_draft_inclusive_stops_at_first_allowlisted_heading() -> None:
    text = (
        "## Revised draft\n\n"
        "draft body\n\n"
        "## Evidence checked this round\n\n"
        "evidence body\n"
    )
    body = extract_revised_draft_inclusive(text)
    assert body == "draft body"


def test_extract_revised_draft_inclusive_returns_none_when_absent() -> None:
    text = "no revised draft here\n## Other\n"
    assert extract_revised_draft_inclusive(text) is None


def test_extract_revised_draft_inclusive_strips_hr_only_body() -> None:
    text = "## Revised draft\n\n----\n\n## Summary\n"
    assert extract_revised_draft_inclusive(text) is None


# ─── Spec 0140 — extractor retains ``## N. Section`` body sub-sections ─


def test_extract_revised_draft_inclusive_retains_numbered_sub_sections() -> None:
    """Spec 0140 — anchor-run shape. The drafter opened ``## Revised draft``
    then wrote the body with ``## 1. Executive Summary``, ``## 2. …`` etc.
    These are NOT in the protocol allowlist and must be absorbed into the
    draft body. The body terminates at ``## Phase artifact`` (Spec 0114
    sentinel, added to the allowlist by 0140)."""
    text = (
        "## Revised draft\n\n"
        "preamble paragraph.\n\n"
        "## 1. Executive Summary\n\n"
        "Findings overview.\n\n"
        "## 2. Version Baseline\n\n"
        "Baseline body.\n\n"
        "## 3. Tier 1 Pass/Fail\n\n"
        "Pass/fail body.\n\n"
        "## 4. Ranked Candidates\n\n"
        "Ranked body.\n\n"
        "## Phase artifact\n\n"
        "### AGREED_PLAN\nartifact body\n"
    )
    body = extract_revised_draft_inclusive(text)
    assert body is not None
    # All four numbered sub-sections retained.
    for heading in (
        "## 1. Executive Summary",
        "## 2. Version Baseline",
        "## 3. Tier 1 Pass/Fail",
        "## 4. Ranked Candidates",
    ):
        assert heading in body, f"missing {heading!r}"
    # Terminator and trailing artifact NOT included.
    assert "Phase artifact" not in body
    assert "AGREED_PLAN" not in body


def test_extract_revised_draft_inclusive_terminates_at_spec_0114_sentinel() -> None:
    """Spec 0140 — when the drafter emits a body sub-section that
    happens to be named ``## Status`` (a Spec 0114 protocol sentinel),
    the extractor terminates there. The allowlist must still bite for
    legitimate sibling protocol sections, not just the v1 set."""
    text = (
        "## Revised draft\n\n"
        "draft body line\n\n"
        "## Status\n"
        "STATUS: AGREED\n"
    )
    body = extract_revised_draft_inclusive(text)
    assert body == "draft body line"


def test_extract_revised_draft_inclusive_terminates_at_each_0114_sentinel() -> None:
    """Spec 0140 — every Spec 0114 v2 sentinel added to
    ``_PROTOCOL_TOP_HEADINGS`` must terminate the draft body."""
    sentinels = [
        "Stance",
        "Addressing items raised against me",
        "Ratifying my own items",
        "New items I'm raising",
        "Phase artifact",
        "Status",
        "Closeout constraints",
    ]
    for sentinel in sentinels:
        text = (
            "## Revised draft\n\n"
            "draft body line\n\n"
            f"## {sentinel}\n"
            "tail body\n"
        )
        body = extract_revised_draft_inclusive(text)
        assert body == "draft body line", (
            f"sentinel {sentinel!r} did not terminate; got {body!r}"
        )


def test_dr_run_does_not_import_strict_extractor() -> None:
    """Spec 0140 — the strict ``extract_revised_draft`` extractor must
    not be referenced from ``dr_run.py``. The Deep Research path now
    consumes only ``extract_revised_draft_inclusive`` (the strict
    variant remains for legacy callers and unit tests of itself)."""
    from pathlib import Path

    import dual_research.orchestrator.dr_run as dr_run_mod

    src = Path(dr_run_mod.__file__).read_text(encoding="utf-8")
    # Word-boundary match to allow the ``_inclusive`` form.
    import re as _re
    bare_calls = _re.findall(r"\bextract_revised_draft\b(?!_)", src)
    assert bare_calls == [], (
        f"dr_run.py still references the strict extractor: "
        f"{len(bare_calls)} occurrence(s)"
    )


def test_extract_revised_draft_inclusive_replays_anchor_run_round07() -> None:
    """Spec 0140 — replay against the on-disk anchor-run turn.

    Run ``20260521-010637-dvs-backend-language-choice``, phase 4,
    round-07-claude.md. Pre-fix the strict extractor returned a 76-byte
    stub (just the brief title). Post-fix the inclusive extractor must
    return the full draft body, including the ``## 4. Ranked Candidates``
    sub-section. The turn ends without a trailing protocol sentinel, so
    the inclusive walker absorbs through end-of-file."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    anchor_path = (
        repo_root
        / "runs"
        / "20260521-010637-dvs-backend-language-choice"
        / "phase4"
        / "round-07-claude.md"
    )
    if not anchor_path.exists():
        # The anchor-run artifacts live in the working tree but are not
        # required to be checked in. Skip when absent so CI stays green
        # on clones that haven't fetched the run directory.
        import pytest
        pytest.skip(f"anchor run not present at {anchor_path}")

    text = anchor_path.read_text(encoding="utf-8")
    body = extract_revised_draft_inclusive(text)
    assert body is not None
    # The pre-fix on-disk draft-v7.md was 76 bytes. Post-fix the body
    # spans rows 47..312 of the turn (the four numbered sub-sections).
    assert len(body) >= 25_000, (
        f"expected >= 25k chars, got {len(body)} — extractor still "
        "truncating the draft body"
    )
    assert "## 4. Ranked Candidates" in body


# ─── Spec 0231 — parser heading tolerance ──────────────────────────────


from dual_research.protocol import (
    EditSectionOp,
    RevisedDraftDeltas,
    apply_revised_draft_deltas,
    extract_revised_draft_deltas,
)


def test_extract_revised_draft_deltas_inline_edit_section_heading() -> None:
    """Spec 0231 §2.1 — `### EDIT_SECTION ## <heading>` (anchor inline on
    the H3 line, no newline) parses, normalises to the draft section, and
    binds. Anchor-fixture pattern from `20260527-054652-...` phase 4."""
    turn_text = (
        "## Stance\nstance.\n\n"
        "## Status\nSTATUS: REVIEWING\n\n"
        "## Revised draft\n\n"
        "### EDIT_SECTION ## 1. Summary\n\n"
        "ANCHOR: original line\n"
        "REPLACE_WITH: replaced line\n"
    )
    payload = extract_revised_draft_deltas(turn_text)
    assert isinstance(payload, RevisedDraftDeltas)
    assert len(payload.ops) == 1
    op = payload.ops[0]
    assert isinstance(op, EditSectionOp)
    # The heading argument literally is `## 1. Summary` — the H2 token
    # is preserved on the op object; normalisation happens at apply time.
    assert op.heading == "## 1. Summary"
    # Apply against a prior draft whose section is `## 1. Summary` —
    # the spec 0231 §2.1 normaliser strip of leading `## ` makes them bind.
    prior_draft = "## 1. Summary\n\noriginal line\n\nmore body\n"
    new_draft, violations = apply_revised_draft_deltas(
        prior_draft=prior_draft, payload=payload,
    )
    assert "replaced line" in new_draft
    assert "original line" not in new_draft
    assert violations == []


def test_extract_fenced_section_glued_heading_prose() -> None:
    """Spec 0231 §2.2 — `## <heading><glued prose>` (no newline between
    heading name and trailing prose) now matches. Anchor-fixture pattern
    from `20260527-054652-...` phase 2: claude wrote
    `## New items I'm raisingNow I have evidence...` and the section body
    must be recovered so the downstream `### RAISE` finder sees the blocks.
    """
    from dual_research.protocol import extract_fenced_section

    text = (
        "## Stance\nstance body\n\n"
        "## New items I'm raisingNow I have evidence for the key claims.\n\n"
        "### RAISE\n\n"
        "body of the first raise\n\n"
        "### RAISE\n\n"
        "body of the second raise\n\n"
        "## Phase artifact\n\nartifact.\n"
    )
    body = extract_fenced_section(text, "New items I'm raising")
    assert body is not None
    # Glued preamble is captured as part of the body — it's harmless
    # noise the downstream `### RAISE` walker skips over.
    assert "Now I have evidence" in body
    # The `### RAISE` blocks are present in the body.
    assert body.count("### RAISE") == 2
    # The next `## ` heading bounds the body — the artifact section is
    # not absorbed.
    assert "artifact." not in body


def test_extract_fenced_section_clean_heading_still_parses_unchanged() -> None:
    """Spec 0231 §2.2 — backwards-compatibility. Standalone clean headings
    (newline after heading name) continue to parse identically."""
    from dual_research.protocol import extract_fenced_section

    text = (
        "## New items I'm raising\n\n"
        "### RAISE\nclean body\n\n"
        "## Phase artifact\nartifact.\n"
    )
    body = extract_fenced_section(text, "New items I'm raising")
    assert body is not None
    assert body.startswith("### RAISE")
    assert "clean body" in body
    assert "artifact." not in body


def test_extract_fenced_section_partial_prefix_does_not_false_match() -> None:
    """Spec 0231 §2.2 — the boundary is "next char is end-of-line OR
    non-whitespace". A trailing space between the heading name and
    additional words is NOT a glued case — `## New items I'm` does not
    match heading `"New items"` because the next char is whitespace."""
    from dual_research.protocol import extract_fenced_section

    text = "## New items I'm raising\nbody\n## Phase artifact\nartifact.\n"
    # The heading_name "New items" must NOT match the line
    # "## New items I'm raising" — the next char after "items" is a
    # space, which fails both the `\s*$` (would need end-of-line) and
    # the `(?=\S)` (would need non-whitespace) branches.
    body = extract_fenced_section(text, "New items")
    assert body is None


def test_extract_revised_draft_deltas_standalone_anchor_still_parses() -> None:
    """Spec 0231 §2.1 — backwards-compatibility. Standalone-anchor
    `### EDIT_SECTION 1. Summary` (no glued `## ` token) continues to
    parse and bind identically."""
    turn_text = (
        "## Stance\nstance.\n\n"
        "## Status\nSTATUS: REVIEWING\n\n"
        "## Revised draft\n\n"
        "### EDIT_SECTION 1. Summary\n\n"
        "ANCHOR: original line\n"
        "REPLACE_WITH: replaced line\n"
    )
    payload = extract_revised_draft_deltas(turn_text)
    assert isinstance(payload, RevisedDraftDeltas)
    op = payload.ops[0]
    assert isinstance(op, EditSectionOp)
    assert op.heading == "1. Summary"
    prior_draft = "## 1. Summary\n\noriginal line\n\nmore body\n"
    new_draft, _ = apply_revised_draft_deltas(
        prior_draft=prior_draft, payload=payload,
    )
    assert "replaced line" in new_draft
    assert "original line" not in new_draft


def test_normalise_section_heading_strips_h2_token_then_numeric_prefix() -> None:
    """Spec 0231 §2.1 — direct unit test for the normaliser's new
    leading-``## `` strip, composed with the existing numeric strip."""
    from dual_research.protocol.parse import _normalise_section_heading

    assert _normalise_section_heading("## 1. Summary") == "summary"
    assert _normalise_section_heading("## Summary") == "summary"
    assert _normalise_section_heading("1. Summary") == "summary"
    assert _normalise_section_heading("Summary") == "summary"
    # Idempotent under whitespace + case.
    assert _normalise_section_heading("  ##   1. SUMMARY  ") == "summary"


def test_extract_revised_draft_deltas_replays_anchor_run_malformed_turn() -> None:
    """Spec 0231 — replay the actual anchor-run fixture turn that died.

    ``phase4/round-02-claude.malformed-1.md`` from
    ``20260527-054652-backend-language-choice`` died with
    ``revised_draft_body_missing_delta_op`` because the EDIT_SECTION
    headings were inline (`### EDIT_SECTION ## 1. Summary`). Post-fix
    the body parses as a non-trivial sequence of EditSectionOps.
    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    fixture_path = (
        repo_root
        / "tests"
        / "fixtures"
        / "anchor-runs"
        / "20260527-054652-backend-language-choice"
        / "phase4"
        / "round-02-claude.malformed-1.md"
    )
    text = fixture_path.read_text(encoding="utf-8")
    payload = extract_revised_draft_deltas(text)
    assert isinstance(payload, RevisedDraftDeltas)
    # The fixture's `## Revised draft` body contains 10 inline-anchor
    # EDIT_SECTION blocks (Summary ×1, Findings ×9 per the live-run grep).
    edit_ops = [op for op in payload.ops if isinstance(op, EditSectionOp)]
    assert len(edit_ops) >= 10, f"expected >= 10 EditSectionOps, got {len(edit_ops)}"


def test_extract_fenced_section_replays_anchor_run_glued_phase2_turn() -> None:
    """Spec 0231 — replay the actual anchor-run fixture turn.

    ``phase2/round-01-claude.md`` from
    ``20260527-054652-backend-language-choice`` glued the heading
    `## New items I'm raising` to the prose `Now I have evidence...`.
    Pre-fix, ``extract_fenced_section(text, "New items I'm raising")``
    returned ``None`` and six ``### RAISE`` blocks went unregistered.
    Post-fix the body is recovered with all six RAISEs intact.
    """
    from pathlib import Path

    from dual_research.protocol import extract_fenced_section

    repo_root = Path(__file__).resolve().parents[2]
    fixture_path = (
        repo_root
        / "tests"
        / "fixtures"
        / "anchor-runs"
        / "20260527-054652-backend-language-choice"
        / "phase2"
        / "round-01-claude.md"
    )
    text = fixture_path.read_text(encoding="utf-8")
    body = extract_fenced_section(text, "New items I'm raising")
    assert body is not None
    # The fixture has exactly six `### RAISE` blocks in this section.
    assert body.count("### RAISE") == 6, (
        f"expected 6 RAISE blocks, got {body.count('### RAISE')}"
    )

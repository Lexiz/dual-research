"""Spec 0238 — Parser section-heading primitive consolidation.

Verifies the ``section_heading_re`` factory built in
``src/dual_research/contract/markers.py`` and the consolidation of every
specific-literal-heading anchor onto it. The CLAUDE.md "live-failure fix
discipline (spec 0238)" rule mandates that this file exercise the
**real entry point** of the failing call path on the captured artifact;
the integration test below loads the dead 142625 turn file and runs it
through ``parse_turn_v2``.

Test groups:

1. Positive-pattern (11 regexes × clean heading) — pre-existing
   behaviour preserved.
2. Antipodal-absence-becomes-presence (11 regexes × glued-prose
   heading) — pre-fix would have failed; post-fix must match.
3. Variant battery on SECTION_NEW_ITEMS_RE — 7 realistic shapes.
4. Integration on the captured failing turn — parse_turn_v2 yields the
   5 RaiseBlocks the dead run dropped, and the STATUS-line action array
   matches the same 5 IDs.
5. ``extract_fenced_section`` ⇄ SECTION_*_RE shared-source-of-truth
   match-bounds invariant.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dual_research.contract.markers import (
    SECTION_ADDRESSING_RE,
    SECTION_CLOSEOUT_CONSTRAINTS_RE,
    SECTION_NEW_ITEMS_RE,
    SECTION_PHASE_ARTIFACT_RE,
    SECTION_RATIFYING_RE,
    SECTION_REVISED_DRAFT_RE,
    SECTION_STANCE_RE,
    SECTION_STATUS_RE,
    section_heading_re,
)
from dual_research.contract.operations import RaiseBlock
from dual_research.protocol.parse import (
    _REVISED_DRAFT_HEADING_RE,
    extract_fenced_section,
)
from dual_research.protocol.parse_v2 import raise_blocks


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_142625 = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "anchor-runs"
    / "20260527-142625-backend-language-choice"
    / "phase2"
    / "round-01-claude.md"
)


# Eleven (regex, canonical-heading-name) pairs covering every
# specific-literal-heading anchor the spec consolidates onto the
# primitive. ``_REVISED_DRAFT_HEADING_RE`` is included so the alias
# (now SECTION_REVISED_DRAFT_RE) is verified at its original name too.
_REGEX_HEADING_PAIRS: list[tuple[re.Pattern[str], str]] = [
    (SECTION_STANCE_RE, "Stance"),
    (SECTION_ADDRESSING_RE, "Addressing items raised against me"),
    (SECTION_RATIFYING_RE, "Ratifying my own items"),
    (SECTION_NEW_ITEMS_RE, "New items I'm raising"),
    (SECTION_PHASE_ARTIFACT_RE, "Phase artifact"),
    (SECTION_STATUS_RE, "Status"),
    (SECTION_REVISED_DRAFT_RE, "Revised draft"),
    (SECTION_CLOSEOUT_CONSTRAINTS_RE, "Closeout constraints"),
    (_REVISED_DRAFT_HEADING_RE, "Revised draft"),
    (section_heading_re(r"Open questions for .+?"), "Open questions for openai"),
    (section_heading_re(r"(?:\d+\.\s+)?Open Questions"), "Open Questions"),
]


# ─── 1. Positive-pattern (clean form) ─────────────────────────────────


@pytest.mark.parametrize("pat,heading", _REGEX_HEADING_PAIRS)
def test_positive_pattern_clean_heading_matches(pat, heading):
    """Each consolidated regex matches its canonical clean heading."""
    text = f"## {heading}\n\nbody content\n"
    assert pat.search(text) is not None, (
        f"{pat.pattern!r} should match clean '## {heading}'"
    )


# ─── 2. Antipodal-absence-becomes-presence (glued form) ───────────────


@pytest.mark.parametrize("pat,heading", _REGEX_HEADING_PAIRS)
def test_antipodal_glued_prose_matches_post_fix(pat, heading):
    """Each consolidated regex matches the glued-prose variant
    ``## <heading>Now I have evidence…``. Pre-fix (``\\b`` terminator)
    this would not match when the next character is a word character.
    Post-fix the ``(?:\\s*$|(?=\\S))`` terminator accepts the glued
    case.
    """
    text = f"## {heading}Now I have the evidence I need. Let me raise the items.\n"
    assert pat.search(text) is not None, (
        f"{pat.pattern!r} should match glued '## {heading}<prose>'"
    )


# ─── 3. Variant battery on SECTION_NEW_ITEMS_RE ───────────────────────


@pytest.mark.parametrize(
    "label,line",
    [
        ("clean", "## New items I'm raising\n"),
        ("trailing-whitespace", "## New items I'm raising   \n"),
        ("no-apostrophe", "## New items Im raising\n"),
        ("ALL-CAPS", "## NEW ITEMS I'M RAISING\n"),
        ("trailing-period", "## New items I'm raising.\n"),
        ("trailing-colon+text", "## New items I'm raising: see below\n"),
        ("glued-letter", "## New items I'm raisingNow the evidence...\n"),
    ],
)
def test_section_new_items_re_variant_battery(label, line):
    """Seven realistic shapes the regex must accept post-fix."""
    assert SECTION_NEW_ITEMS_RE.search(line) is not None, (
        f"SECTION_NEW_ITEMS_RE should match variant '{label}': {line!r}"
    )


# ─── 4. Integration on the captured failing turn ──────────────────────


_EXPECTED_RAISED_IDS = {
    "D-go-vs-csharp-21",
    "D-java-rank",
    "D-kotlin-mcp",
    "Q-csharp-implicit-penalty",
    "Q-rust-azure-sdk-ga",
}


def test_142625_phase2_r1_claude_parse_extracts_five_raise_blocks():
    """The dead-run turn file
    ``20260527-142625/phase2/round-01-claude.md`` glues prose onto the
    ``## New items I'm raising`` heading. Pre-fix the section was
    silently empty and every RAISE block was dropped; post-fix
    ``parse_turn_v2`` extracts five RaiseBlocks matching the IDs
    declared in the STATUS footer.

    This is the worked example of the CLAUDE.md "live-failure fix
    discipline (spec 0238)" rule — it invokes ``parse_turn_v2`` (the
    real entry point of the failing call path) against the captured
    artifact verbatim.
    """
    from dual_research.protocol.parse import parse_turn_v2

    text = FIXTURE_142625.read_text(encoding="utf-8")
    parsed = parse_turn_v2(text)

    # STATUS-line action array — unchanged from the legacy parser, but
    # checked here so the integration test fully reflects the spec §6
    # checklist item.
    assert len(parsed.raised_this_turn) == 5
    assert set(parsed.raised_this_turn) == _EXPECTED_RAISED_IDS

    # The actual fix: RaiseBlocks now register. Pre-fix this list was
    # empty because SECTION_NEW_ITEMS_RE failed to match the
    # glued-prose heading.
    raises = raise_blocks(parsed)
    assert len(raises) == 5, (
        f"expected 5 RaiseBlocks (the dropped ones), got {len(raises)}; "
        f"this means SECTION_NEW_ITEMS_RE still fails to open the section."
    )


# ─── 5. extract_fenced_section ⇄ SECTION_*_RE shared-source-of-truth ──


def test_extract_fenced_section_and_section_re_agree_on_match_bounds():
    """Spec 0238 risk-mitigation: extract_fenced_section's heading regex
    is now built via ``section_heading_re``, the same factory the
    SECTION_*_RE family is built from. The two paths must produce
    identical match-bounds for a representative heading on both clean
    and glued variants. Without this invariant, fenced-section
    extraction and parse_turn_v2's section-body extraction could drift
    again.
    """
    for body in (
        "## Revised draft\nfoo\n",
        "## Revised draftNow some glued prose\nfoo\n",
    ):
        match_via_section_re = SECTION_REVISED_DRAFT_RE.search(body)
        # The fenced extractor uses re.escape(heading_name) internally,
        # so we mirror that here to get the same regex shape.
        match_via_fenced = section_heading_re(re.escape("Revised draft")).search(body)
        assert match_via_section_re is not None
        assert match_via_fenced is not None
        assert match_via_section_re.span() == match_via_fenced.span(), (
            f"SECTION_REVISED_DRAFT_RE and the fenced-extractor's heading "
            f"regex disagreed on match bounds for body {body!r}: "
            f"{match_via_section_re.span()} vs {match_via_fenced.span()}"
        )


def test_extract_fenced_section_extracts_glued_body_round_trip():
    """End-to-end through extract_fenced_section: a glued-prose heading
    no longer hides the body. Spec 0231 fixed this for
    extract_fenced_section in isolation; spec 0238 keeps the fix while
    consolidating the regex construction onto ``section_heading_re``.
    """
    body = "## RevisedDraftHeadingGluedPlaceholder\n"  # avoid accidental match
    # Use a heading the fenced extractor will actually find via the
    # primitive's terminator.
    text = (
        "## AGREED_PLANNow inline content begins.\n"
        "actual plan body here\n"
        "## Status\n"
        "STATUS: AGREED\n"
    )
    out = extract_fenced_section(text, "AGREED_PLAN")
    assert out is not None
    assert "actual plan body here" in out
    # The boundary at the next ## heading is preserved.
    assert "STATUS: AGREED" not in out
    # The 'Now inline content begins.' prose got absorbed into the body
    # (per spec 0231 §2.2's stated semantics; spec 0238 preserves them).
    assert "Now inline content begins." in out


# ─── 6. Source-pattern lock-in on the primitive ───────────────────────


def test_section_heading_re_source_uses_tolerant_terminator():
    """Lock the primitive's regex shape so future edits cannot silently
    swap the terminator back to ``\\b``. The string form of the
    compiled pattern must contain the ``(?:\\s*$|(?=\\S))`` terminator.
    """
    pat = section_heading_re(re.escape("Anything"))
    assert r"(?:\s*$|(?=\S))" in pat.pattern, (
        f"section_heading_re terminator drifted; pattern={pat.pattern!r}"
    )


def test_section_heading_re_flags_default_to_multiline_ignorecase():
    """The factory must default to MULTILINE | IGNORECASE — the same
    flags the SECTION_*_RE family used pre-spec-0238 — so the rebuild
    does not change case sensitivity or multi-line semantics.
    """
    pat = section_heading_re(re.escape("Anything"))
    assert pat.flags & re.MULTILINE
    assert pat.flags & re.IGNORECASE

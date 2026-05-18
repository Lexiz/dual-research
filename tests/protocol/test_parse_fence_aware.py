"""Spec 0090 § C — `extract_fenced_section` respects fenced code blocks.

Prior behaviour: `extract_fenced_section` searched for the next ``##``
heading via a naive regex that didn't know about markdown fenced code
blocks. That falsely terminated a section's body at any ``## `` line
inside a fenced block — in particular, for the AGREED_PLAN block which
agents always emit as a ```` ```markdown ```` fence containing internal
``## Final-surfaced disagreements (canonical)`` sub-sections.

After § C: ``## `` lines inside ```` ``` ```` or ```` ~~~ ```` fences are
masked out before the boundary search.
"""

from __future__ import annotations

from dual_research.protocol.parse import (
    _fenced_ranges,
    _next_h2_outside_fences,
    extract_fenced_section,
)


class TestFencedRanges:
    def test_no_fences(self) -> None:
        assert _fenced_ranges("nothing here") == []
        assert _fenced_ranges("## heading\n\nbody") == []

    def test_single_backtick_fence(self) -> None:
        text = "before\n```\ninside\n```\nafter"
        ranges = _fenced_ranges(text)
        assert len(ranges) == 1
        start, end = ranges[0]
        # The fence opener `` ``` `` ends right after its newline; the
        # closer `` ``` `` starts at the position of the second ```.
        assert text[start:end].strip() == "inside"

    def test_fence_with_language_tag(self) -> None:
        text = "before\n```markdown\n## inside fence\n```\nafter"
        ranges = _fenced_ranges(text)
        assert len(ranges) == 1

    def test_tilde_fence(self) -> None:
        text = "x\n~~~\n## inside tilde\n~~~\ny"
        ranges = _fenced_ranges(text)
        assert len(ranges) == 1

    def test_unterminated_fence_runs_to_end(self) -> None:
        text = "x\n```\nno closer\nat all"
        ranges = _fenced_ranges(text)
        assert len(ranges) == 1
        assert ranges[0][1] == len(text)


class TestNextH2OutsideFences:
    def test_h2_outside_fence(self) -> None:
        text = "## one\n\n## two"
        m = _next_h2_outside_fences(text)
        # The H2 regex only matches up to the first \S char (`o`) — we
        # care about the match POSITION, not its captured length.
        assert m is not None and m.start() == 0

    def test_h2_inside_fence_skipped(self) -> None:
        text = "```\n## fake\n```\n## real"
        m = _next_h2_outside_fences(text)
        assert m is not None
        # The "real" heading must be picked, not the one inside the fence.
        assert text[m.start():m.start() + 20].startswith("## real")

    def test_no_h2_returns_none(self) -> None:
        assert _next_h2_outside_fences("body\n```\n## inside\n```\nmore") is None


class TestExtractFencedSectionRespectsFences:
    def test_basic_section_unchanged(self) -> None:
        text = "## Foo\n\nbody line\n\n## Bar\nx"
        assert extract_fenced_section(text, "Foo") == "body line"

    def test_internal_fenced_h2_no_longer_truncates(self) -> None:
        """Regression test for the bug spec 0090 § C closes.

        Pre-fix: the inner ``## Final-surfaced disagreements (canonical)``
        would terminate AGREED_PLAN early, returning just ``` ```markdown ```.
        Post-fix: the entire fenced body (including the inner heading
        as literal text) is returned.
        """
        text = (
            "## AGREED_PLAN\n\n"
            "```markdown\n"
            "1. Plan item\n\n"
            "## Final-surfaced disagreements (canonical)\n\n"
            "### FSD-1: title\n\n"
            "- Claude position: A\n"
            "- GPT position: B\n"
            "```\n\n"
            "## Next section\nx"
        )
        body = extract_fenced_section(text, "AGREED_PLAN")
        assert body is not None
        assert body.startswith("```markdown")
        assert "## Final-surfaced disagreements (canonical)" in body
        assert "FSD-1: title" in body
        # Critically: the section body terminates at the REAL `## Next section`,
        # NOT at the fake heading inside the fence.
        assert "Next section" not in body

    def test_tilde_fence_also_respected(self) -> None:
        text = (
            "## Outer\n\n"
            "~~~\n"
            "## inside tilde\n"
            "~~~\n\n"
            "## Real next\nx"
        )
        body = extract_fenced_section(text, "Outer")
        assert body is not None
        assert "## inside tilde" in body
        assert "Real next" not in body

    def test_section_with_no_terminator_returns_to_end(self) -> None:
        text = "## Tail\n\nfinal body"
        assert extract_fenced_section(text, "Tail") == "final body"

    def test_missing_heading_returns_none(self) -> None:
        assert extract_fenced_section("nothing", "Missing") is None

"""Summary extraction — spec 0025.

`extract_summary` pulls the body under the first `## Summary` / `## TL;DR`
heading from agent output. Used by the aggregator to populate
`Run.phase_summaries` so the UI can render TL;DR rows on every card.
"""

from __future__ import annotations

import pytest

from dual_research.protocol.parse import extract_summary, synthesise_brief_tldr


# ─── extract_summary ─────────────────────────────────────────────────────────


def test_extracts_body_under_summary_heading() -> None:
    text = (
        "STATUS: NEGOTIATING\n\n"
        "## Summary\n\n"
        "We disagree on the database choice. I prefer Postgres.\n\n"
        "## Open questions\n\n"
        "- foo\n"
    )
    assert (
        extract_summary(text)
        == "We disagree on the database choice. I prefer Postgres."
    )


def test_extracts_summary_of_my_position() -> None:
    text = (
        "# Round 3\n\n"
        "## Summary of my position\n\n"
        "I still object to the proposed indexes.\n"
    )
    assert extract_summary(text) == "I still object to the proposed indexes."


def test_extracts_tldr_alias() -> None:
    text = "## TL;DR\n\nThis is the short version."
    assert extract_summary(text) == "This is the short version."


def test_empty_section_returns_none() -> None:
    text = "## Summary\n\n   \n\n## Other\n\nfoo\n"
    assert extract_summary(text) is None


def test_missing_section_returns_none() -> None:
    text = "STATUS: AGREED\n\n## Open questions\n\n- none\n"
    assert extract_summary(text) is None


def test_body_ends_at_next_top_level_heading() -> None:
    text = (
        "## Summary\n\nLine one.\n\nLine two.\n\n## Next section\n\nignored\n"
    )
    out = extract_summary(text)
    assert out is not None
    assert out.startswith("Line one.")
    assert "Line two." in out
    assert "ignored" not in out
    assert "Next section" not in out


def test_h3_inside_summary_is_kept() -> None:
    text = (
        "## Summary\n\nIntro.\n\n### Subhead\n\nBody.\n\n## Done\n"
    )
    out = extract_summary(text)
    assert out is not None
    assert "Subhead" in out
    assert "Body." in out


def test_handles_empty_input() -> None:
    assert extract_summary("") is None
    assert extract_summary(None) is None  # type: ignore[arg-type]


# ─── synthesise_brief_tldr ───────────────────────────────────────────────────


def test_tldr_skips_headings_and_joins_two_sentences() -> None:
    brief = (
        "# Compare SQLite vs Postgres\n\n"
        "For a single-tenant API. We need real-world performance numbers. "
        "Specifically cold-start cost.\n"
    )
    out = synthesise_brief_tldr(brief)
    assert out is not None
    assert out.startswith("For a single-tenant API")
    assert "real-world performance numbers" in out


def test_tldr_truncates_at_max_chars() -> None:
    body = "Long sentence " * 60
    brief = f"# Heading\n\n{body}"
    out = synthesise_brief_tldr(brief, max_chars=80)
    assert out is not None
    assert len(out) <= 81  # one extra for the ellipsis
    assert out.endswith("…")


def test_tldr_returns_none_for_heading_only() -> None:
    assert synthesise_brief_tldr("# Just a heading\n") is None


def test_tldr_skips_code_fences() -> None:
    brief = (
        "# Brief\n\n"
        "```\nthis is code, not prose\n```\n\n"
        "Real prose continues here.\n"
    )
    out = synthesise_brief_tldr(brief)
    assert out is not None
    assert "Real prose continues here" in out
    assert "code, not prose" not in out

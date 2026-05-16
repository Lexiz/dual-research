"""Spec 0036 — validate_search_audit + normalize_url rules."""
from __future__ import annotations

from dual_research.audit.schema import (
    Citation,
    ConsultedSource,
    ToolEvent,
    TurnSearchAudit,
)
from dual_research.audit.validate import normalize_url, validate_search_audit


def _audit(*, tool_events: list[ToolEvent], citations: list[Citation]) -> TurnSearchAudit:
    return TurnSearchAudit(
        provider="anthropic",
        model="claude",
        turn_key="phase1_claude",
        phase="phase1",
        agent="claude",
        label="l",
        emitted_at="",
        tool_events=tool_events,
        citations=citations,
    )


# ─── normalize_url ──────────────────────────────────────────────────────────


def test_normalize_url_strips_utm_source():
    assert normalize_url("https://example.com/x?utm_source=openai") == "https://example.com/x"


def test_normalize_url_keeps_non_tracking_query_params():
    assert normalize_url("https://example.com/x?id=123") == "https://example.com/x?id=123"


def test_normalize_url_strips_trailing_slash_and_lowercases_host():
    assert normalize_url("https://Example.COM/Page/") == "https://example.com/Page"


def test_normalize_url_drops_fragment_implicitly():
    # urlparse splits fragment, our rebuild omits it.
    assert normalize_url("https://example.com/x#section") == "https://example.com/x"


# ─── validate_search_audit ──────────────────────────────────────────────────


def test_validator_marks_search_performed_when_tool_events_present():
    audit = _audit(
        tool_events=[ToolEvent(event_id="e", queries=["q"], consulted_sources=[
            ConsultedSource(url="https://a")
        ])],
        citations=[],
    )
    validate_search_audit(audit)
    assert audit.flags.search_performed is True
    assert audit.flags.cited_url_not_in_consulted_sources is False


def test_validator_flags_hallucinated_citation_when_url_not_in_consulted_set():
    audit = _audit(
        tool_events=[ToolEvent(event_id="e1", queries=["q"], consulted_sources=[
            ConsultedSource(url="https://real.example.com"),
        ])],
        citations=[
            Citation(url="https://real.example.com"),       # legit
            Citation(url="https://fabricated.invalid/x"),   # not in consulted set
        ],
    )
    validate_search_audit(audit)
    assert audit.flags.cited_url_not_in_consulted_sources is True
    assert audit.citations[0].matched_query_id == "e1"
    assert audit.citations[1].matched_query_id is None


def test_validator_matches_url_after_stripping_utm_source():
    audit = _audit(
        tool_events=[ToolEvent(event_id="e1", queries=["q"], consulted_sources=[
            ConsultedSource(url="https://example.com/x"),
        ])],
        citations=[
            Citation(url="https://example.com/x?utm_source=openai"),
        ],
    )
    validate_search_audit(audit)
    assert audit.flags.cited_url_not_in_consulted_sources is False
    assert audit.citations[0].matched_query_id == "e1"


def test_validator_does_not_flag_when_consulted_set_is_empty():
    """OpenAI without `include` — empty sources, citations present. No false positive."""
    audit = _audit(
        tool_events=[ToolEvent(event_id="e1", queries=["q"], consulted_sources=[])],
        citations=[Citation(url="https://anywhere")],
    )
    validate_search_audit(audit)
    # Search did happen → search_performed True. But we can't claim the URL
    # is not-in-consulted-set when consulted-set is empty.
    assert audit.flags.search_performed is True
    assert audit.flags.cited_url_not_in_consulted_sources is False


def test_validator_flags_citations_without_search_event():
    audit = _audit(tool_events=[], citations=[Citation(url="https://x")])
    validate_search_audit(audit)
    assert audit.flags.search_performed is False
    assert audit.flags.citations_without_search_event is True


def test_validator_flags_queries_missing_from_actions():
    audit = _audit(
        tool_events=[ToolEvent(event_id="e", action_type="search", queries=[])],
        citations=[],
    )
    validate_search_audit(audit)
    assert audit.flags.queries_missing_from_actions is True


def test_validator_does_not_flag_missing_queries_on_open_page_action():
    """`open_page` and `find_in_page` legitimately have no query string."""
    audit = _audit(
        tool_events=[ToolEvent(event_id="e", action_type="open_page", queries=[])],
        citations=[],
    )
    validate_search_audit(audit)
    assert audit.flags.queries_missing_from_actions is False

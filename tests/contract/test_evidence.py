"""Spec 0114 — evidence anti-hallucination tests."""

from __future__ import annotations

from dual_research.contract.evidence import (
    EvidenceRecord,
    MIN_CONTENT_EXCERPT_CHARS,
    validate_evidence,
)


def _record(**overrides):
    base = {
        "item_id": "D-plan-g-04",
        "url": "https://example.com/page",
        "title": "Example",
        "search_query": "example query",
        "fetched_at": "2026-05-19T12:00:00Z",
        "evidence_event_id": "srvtoolu_abc",
        "content_excerpt": "x" * (MIN_CONTENT_EXCERPT_CHARS + 50),
    }
    base.update(overrides)
    return EvidenceRecord(**base)


def _tool_events_with_content():
    """Tool events with encrypted_content matching the default excerpt."""
    return [
        {
            "event_id": "srvtoolu_abc",
            "type": "web_search",
            "action_type": "search",
            "queries": ["example query"],
            "consulted_sources": [
                {
                    "url": "https://example.com/page",
                    "title": "Example",
                    "encrypted_content": "x" * 1000,
                },
            ],
        },
    ]


def test_clean_record_no_flags():
    flags = validate_evidence(_record(), tool_events=_tool_events_with_content())
    assert flags == []


def test_fabricated_event_id_flagged():
    rec = _record(evidence_event_id="srvtoolu_nope")
    flags = validate_evidence(rec, tool_events=_tool_events_with_content())
    codes = {f.code for f in flags}
    assert "evidence_event_id_fabricated" in codes
    # Anti-hallucination should short-circuit when event_id is fabricated
    assert "evidence_url_not_consulted" not in codes


def test_url_not_in_consulted_flagged():
    rec = _record(url="https://other.com/elsewhere")
    flags = validate_evidence(rec, tool_events=_tool_events_with_content())
    codes = {f.code for f in flags}
    assert "evidence_url_not_consulted" in codes


def test_content_not_in_source_flagged():
    rec = _record(content_excerpt="y" * (MIN_CONTENT_EXCERPT_CHARS + 50))
    flags = validate_evidence(rec, tool_events=_tool_events_with_content())
    codes = {f.code for f in flags}
    assert "evidence_content_not_in_source" in codes


def test_content_too_short_flagged():
    rec = _record(content_excerpt="x" * (MIN_CONTENT_EXCERPT_CHARS - 1))
    flags = validate_evidence(rec, tool_events=_tool_events_with_content())
    codes = {f.code for f in flags}
    assert "evidence_content_too_short" in codes


def test_content_too_long_flagged():
    rec = _record(content_excerpt="x" * 2001)
    flags = validate_evidence(rec, tool_events=_tool_events_with_content())
    codes = {f.code for f in flags}
    assert "evidence_content_too_long" in codes


def test_no_encrypted_content_skips_content_check():
    """OpenAI doesn't expose source content — skip the content match check."""
    events = [
        {
            "event_id": "srvtoolu_abc",
            "type": "web_search",
            "action_type": "search",
            "queries": ["example query"],
            "consulted_sources": [
                {"url": "https://example.com/page", "title": "Example"},
            ],
        },
    ]
    rec = _record(content_excerpt="anything " * 30)
    flags = validate_evidence(rec, tool_events=events)
    codes = {f.code for f in flags}
    # URL is present in consulted, event_id matches; content match deferred
    assert "evidence_content_not_in_source" not in codes
    assert "evidence_url_not_consulted" not in codes
    assert "evidence_event_id_fabricated" not in codes


def test_content_excerpt_whitespace_normalized():
    """Excerpt with extra whitespace still matches a clean source."""
    # Needle (excerpt) uses normal spacing; haystack pads with extra
    # newlines and indentation. After normalization both collapse to the
    # same single-spaced form.
    needle = (
        "the canonical text the canonical text the canonical text "
        "the canonical text the canonical text the canonical text "
        "the canonical text the canonical text the canonical text"
    )
    haystack = needle.replace(" ", "\n   \t   ")
    events = [
        {
            "event_id": "srvtoolu_abc",
            "type": "web_search",
            "action_type": "search",
            "queries": ["q"],
            "consulted_sources": [
                {"url": "https://example.com/page", "encrypted_content": haystack},
            ],
        },
    ]
    rec = _record(content_excerpt=needle)
    flags = validate_evidence(rec, tool_events=events)
    codes = {f.code for f in flags}
    assert "evidence_content_not_in_source" not in codes

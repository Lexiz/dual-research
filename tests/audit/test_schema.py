"""Spec 0036 — TurnSearchAudit schema round-trip + sanity checks."""
from __future__ import annotations

from dual_research.audit.schema import (
    Citation,
    ConsultedSource,
    ToolEvent,
    TurnSearchAudit,
    TurnSearchFlags,
    audit_from_dict,
    audit_to_dict,
)


def _sample_audit() -> TurnSearchAudit:
    return TurnSearchAudit(
        provider="anthropic",
        model="claude-haiku-4-5",
        turn_key="phase1_claude",
        phase="phase1",
        agent="claude",
        label="phase1-claude",
        emitted_at="2026-05-16T13:00:00+00:00",
        tool_events=[
            ToolEvent(
                event_id="srvtool_1",
                action_type="search",
                queries=["bun production readiness 2026"],
                consulted_sources=[
                    ConsultedSource(
                        url="https://example.com/a",
                        title="A",
                        page_age="1 week",
                        encrypted_content="ENC_A",
                    ),
                    ConsultedSource(url="https://example.com/b", title="B"),
                ],
            )
        ],
        final_text="It's production-ready [1].",
        citations=[
            Citation(
                url="https://example.com/a",
                title="A",
                cited_text="It's production-ready.",
                text_span_start=0,
                text_span_end=26,
                encrypted_index="EI_A",
            )
        ],
        flags=TurnSearchFlags(search_performed=True),
    )


def test_audit_round_trip_preserves_all_fields():
    audit = _sample_audit()
    serialised = audit_to_dict(audit)
    restored = audit_from_dict(serialised)
    assert audit_to_dict(restored) == serialised


def test_audit_from_dict_tolerates_missing_optional_fields():
    minimal = {
        "provider": "openai",
        "model": "gpt-4.1",
        "turn_key": "phase0_gpt",
        "phase": "phase0",
        "agent": "openai",
        "label": "phase0-openai",
        "emitted_at": "2026-05-16T13:00:00+00:00",
    }
    audit = audit_from_dict(minimal)
    assert audit.tool_events == []
    assert audit.citations == []
    assert audit.final_text == ""
    assert audit.flags.search_performed is False


def test_audit_from_dict_filters_invalid_sources_and_citations():
    """Sources/citations missing URLs are dropped (defensive against malformed payloads)."""
    payload = {
        "provider": "anthropic",
        "model": "claude",
        "turn_key": "k",
        "phase": "phase1",
        "agent": "claude",
        "label": "l",
        "emitted_at": "",
        "tool_events": [
            {
                "event_id": "e1",
                "type": "web_search",
                "action_type": "search",
                "queries": ["q"],
                "consulted_sources": [
                    {"url": "https://ok"},
                    {"url": "", "title": "no url, drop"},
                    {"title": "still no url, drop"},
                ],
            }
        ],
        "citations": [],
    }
    audit = audit_from_dict(payload)
    assert len(audit.tool_events) == 1
    assert len(audit.tool_events[0].consulted_sources) == 1
    assert audit.tool_events[0].consulted_sources[0].url == "https://ok"

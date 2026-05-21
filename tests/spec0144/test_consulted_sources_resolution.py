"""Spec 0144 §9.5 — audit_lookup resolves search_N handles uniformly.

The model emits logical handles (``search_1``, ``search_2``, …) that
are NOT the provider's opaque physical ``event_id``. Both providers
persist their ``tool_events`` list in turn-order, so ``search_N``
maps to ``tool_events[N-1]`` regardless of whether the persisted
event_id is Anthropic's ``srvtoolu_…`` or OpenAI's ``ws_…``. We also
keep a physical-ID fallback for the case where the model happens to
emit the actual handle.

The ``encrypted_content`` field on consulted_sources is intentionally
stripped — it is multi-KB per source on Anthropic and the UI never
renders it (the contract validator consumed it server-side).
"""

from __future__ import annotations

from dual_research.ui.items import _resolve_consulted_sources
from dual_research.ui.models import ConsultedSource


_ANTHROPIC_AUDIT = {
    "tool_events": [
        {
            "event_id": "srvtoolu_01XVrn6QiQ2Ex2jHBwFibjr9",
            "type": "web_search",
            "queries": ["MCP server SDK Go Rust"],
            "consulted_sources": [
                {
                    "url": "https://github.com/modelcontextprotocol/rust-sdk",
                    "title": "Rust SDK",
                    "page_age": "March 9, 2026",
                    "encrypted_content": "X" * 8000,
                },
            ],
        },
        {
            "event_id": "srvtoolu_01AAHTDYSzKTb5mUzkTf7CoS",
            "type": "web_search",
            "queries": ["MCP SDK comparison"],
            "consulted_sources": [
                {
                    "url": "https://github.com/orgs/modelcontextprotocol/repositories",
                    "title": "MCP repos",
                    "page_age": "",
                    "encrypted_content": "Y" * 4000,
                },
            ],
        },
    ],
}


_OPENAI_AUDIT = {
    "tool_events": [
        {
            "event_id": "ws_07853c635082b822006a0e5e34eb28819398e0e807069d9a2f",
            "type": "web_search",
            "queries": ["Azure SDK for Rust"],
            "consulted_sources": [
                {
                    "url": "https://devblogs.microsoft.com/azure-sdk/rust/",
                    "title": None,
                    "page_age": None,
                    "encrypted_content": None,
                },
            ],
        },
    ],
}


def test_search_n_resolves_to_nth_tool_event_anthropic():
    """search_2 → tool_events[1] under Anthropic's opaque srvtoolu_ ids."""
    sources = _resolve_consulted_sources(
        evidence_event_id="search_2",
        audit=_ANTHROPIC_AUDIT,
    )
    assert len(sources) == 1
    assert sources[0].url == "https://github.com/orgs/modelcontextprotocol/repositories"
    assert sources[0].queries == ["MCP SDK comparison"]


def test_search_n_resolves_to_nth_tool_event_openai():
    """Same enumeration works for OpenAI's ws_ ids — provider symmetry."""
    sources = _resolve_consulted_sources(
        evidence_event_id="search_1",
        audit=_OPENAI_AUDIT,
    )
    assert len(sources) == 1
    assert sources[0].url == "https://devblogs.microsoft.com/azure-sdk/rust/"


def test_physical_event_id_fallback():
    """When the model emits the real opaque handle, the lookup still works
    via the physical-ID fallback path."""
    sources = _resolve_consulted_sources(
        evidence_event_id="srvtoolu_01XVrn6QiQ2Ex2jHBwFibjr9",
        audit=_ANTHROPIC_AUDIT,
    )
    assert len(sources) == 1
    assert sources[0].url == "https://github.com/modelcontextprotocol/rust-sdk"


def test_encrypted_content_is_stripped():
    """§5.2 / §9 — encrypted_content stays server-side and never lands on
    the wire payload. The UI doesn't render it and it bloats per-item
    payloads multi-KB."""
    sources = _resolve_consulted_sources(
        evidence_event_id="search_1",
        audit=_ANTHROPIC_AUDIT,
    )
    assert sources, "expected at least one consulted source"
    src = sources[0]
    # ConsultedSource has no encrypted_content field at all.
    assert not hasattr(src, "encrypted_content")


def test_search_n_out_of_bounds_returns_empty():
    """A logical handle beyond the persisted tool_events list returns []
    instead of throwing — the wire payload just stays slim."""
    sources = _resolve_consulted_sources(
        evidence_event_id="search_99",
        audit=_ANTHROPIC_AUDIT,
    )
    assert sources == []


def test_missing_audit_returns_empty():
    """No persisted audit (replay missing the searches file) → empty list.
    Pre-spec replay used to defer (no flag fires); we keep that behaviour
    here so cold replay never produces fabricated consulted_sources."""
    assert _resolve_consulted_sources(evidence_event_id="search_1", audit=None) == []
    assert _resolve_consulted_sources(evidence_event_id="search_1", audit={"tool_events": []}) == []


def test_empty_event_id_returns_empty():
    assert _resolve_consulted_sources(evidence_event_id="", audit=_ANTHROPIC_AUDIT) == []


def test_malformed_search_n_returns_empty():
    """``search_abc`` doesn't parse to an int — return empty, don't crash."""
    assert _resolve_consulted_sources(
        evidence_event_id="search_abc", audit=_ANTHROPIC_AUDIT,
    ) == []


def test_consulted_source_carries_no_encrypted_content_after_resolution():
    """Defensive check on the projection — even if we round-trip through
    the dataclass, no encrypted_content attribute should appear."""
    sources = _resolve_consulted_sources(
        evidence_event_id="search_1",
        audit=_ANTHROPIC_AUDIT,
    )
    assert all(isinstance(s, ConsultedSource) for s in sources)
    # Round-trip via dict to assert wire shape doesn't carry it.
    from dataclasses import asdict
    for s in sources:
        d = asdict(s)
        assert "encrypted_content" not in d

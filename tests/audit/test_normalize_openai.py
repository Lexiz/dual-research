"""Spec 0036 — OpenAI Responses API → TurnSearchAudit normaliser."""
from __future__ import annotations

from types import SimpleNamespace

from dual_research.audit.normalize import normalize_openai_search_audit


def _web_search_call(*, id_: str, query: str, sources: list[dict] | None, action_type: str = "search"):
    action = SimpleNamespace(
        type=action_type,
        query=query,
        queries=[query],
        sources=sources,
    )
    return SimpleNamespace(type="web_search_call", id=id_, action=action)


def _output_text(text: str, annotations: list[dict] | None = None):
    anns = []
    for a in annotations or []:
        anns.append(SimpleNamespace(**a))
    return SimpleNamespace(type="output_text", text=text, annotations=anns)


def _message_item(content):
    return SimpleNamespace(type="message", content=content)


def _response(output, *, model: str = "gpt-4.1"):
    return SimpleNamespace(model=model, output=output)


def test_normalize_openai_captures_sources_from_include():
    """With `include=["web_search_call.action.sources"]` the sources list comes back."""
    response = _response([
        _web_search_call(
            id_="ws_1",
            query="bun production",
            sources=[
                {"type": "url", "url": "https://a"},
                {"type": "url", "url": "https://b"},
                {"type": "url", "url": "https://c"},
            ],
        ),
        _message_item([
            _output_text(
                "Bun is solid.",
                annotations=[
                    {
                        "type": "url_citation",
                        "url": "https://a",
                        "title": "A",
                        "start_index": 0,
                        "end_index": 13,
                    }
                ],
            )
        ]),
    ])

    audit = normalize_openai_search_audit(
        response, turn_key="phase1_gpt", phase="phase1", agent="openai", label="phase1-openai",
    )
    assert audit.provider == "openai"
    assert audit.model == "gpt-4.1"
    assert len(audit.tool_events) == 1
    assert audit.tool_events[0].queries == ["bun production"]
    assert len(audit.tool_events[0].consulted_sources) == 3
    # OpenAI doesn't return titles or page_age — both stay None.
    assert audit.tool_events[0].consulted_sources[0].title is None
    assert audit.tool_events[0].consulted_sources[0].page_age is None
    assert audit.final_text == "Bun is solid."
    assert len(audit.citations) == 1
    cit = audit.citations[0]
    assert cit.url == "https://a"
    assert cit.title == "A"
    assert cit.cited_text is None  # OpenAI doesn't expose source-side snippet
    assert cit.text_span_start == 0
    assert cit.text_span_end == 13


def test_normalize_openai_handles_missing_sources_gracefully():
    """When `include` was omitted, action.sources is None — no consulted sources captured."""
    response = _response([
        _web_search_call(id_="ws_1", query="q", sources=None),
        _message_item([_output_text("Done.")]),
    ])
    audit = normalize_openai_search_audit(
        response, turn_key="k", phase="p", agent="openai", label="l",
    )
    assert audit.tool_events[0].consulted_sources == []
    assert audit.final_text == "Done."


def test_normalize_openai_preserves_action_types():
    """Reasoning models emit `open_page` / `find_in_page` actions; these survive."""
    response = _response([
        SimpleNamespace(
            type="web_search_call",
            id="ws_open",
            action=SimpleNamespace(type="open_page", query=None, queries=[], sources=None),
        ),
    ])
    audit = normalize_openai_search_audit(
        response, turn_key="k", phase="p", agent="openai", label="l",
    )
    assert audit.tool_events[0].action_type == "open_page"
    assert audit.tool_events[0].queries == []

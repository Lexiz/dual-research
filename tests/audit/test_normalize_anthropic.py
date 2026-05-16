"""Spec 0036 — Anthropic response → TurnSearchAudit normaliser."""
from __future__ import annotations

from types import SimpleNamespace

from dual_research.audit.normalize import normalize_anthropic_search_audit


def _block(type_: str, **kwargs):
    """Minimal SimpleNamespace block — what the SDK objects look like to .type / .text / .citations etc."""
    return SimpleNamespace(type=type_, **kwargs)


def _result_item(*, url: str, title: str, page_age: str | None = None, enc: str | None = None):
    """Web search result item — exposes both .type and the inner data via __dict__."""
    return SimpleNamespace(
        type="web_search_result",
        url=url,
        title=title,
        page_age=page_age,
        encrypted_content=enc,
        __dict__={
            "type": "web_search_result",
            "url": url,
            "title": title,
            "page_age": page_age,
            "encrypted_content": enc,
        },
    )


def _citation(*, url: str, title: str, cited_text: str, enc_index: str | None = None):
    return SimpleNamespace(
        url=url,
        title=title,
        cited_text=cited_text,
        encrypted_index=enc_index,
        type="web_search_result_location",
        __dict__={
            "url": url,
            "title": title,
            "cited_text": cited_text,
            "encrypted_index": enc_index,
            "type": "web_search_result_location",
        },
    )


def _message(content_blocks, *, model: str = "claude-haiku-4-5"):
    return SimpleNamespace(model=model, content=content_blocks)


def test_normalize_anthropic_captures_query_results_and_citations():
    msg = _message([
        _block(
            "server_tool_use",
            id="srvtool_1",
            name="web_search",
            input={"query": "bun production"},
        ),
        _block(
            "web_search_tool_result",
            tool_use_id="srvtool_1",
            content=[
                _result_item(url="https://a", title="A", page_age="1 week", enc="EA"),
                _result_item(url="https://b", title="B"),
            ],
        ),
        _block(
            "text",
            text="Bun is production-ready.",
            citations=[
                _citation(url="https://a", title="A", cited_text="It is production-ready.", enc_index="EI"),
            ],
        ),
    ])

    audit = normalize_anthropic_search_audit(
        msg, turn_key="phase1_claude", phase="phase1", agent="claude", label="phase1-claude",
    )

    assert audit.provider == "anthropic"
    assert audit.model == "claude-haiku-4-5"
    assert len(audit.tool_events) == 1
    ev = audit.tool_events[0]
    assert ev.event_id == "srvtool_1"
    assert ev.queries == ["bun production"]
    assert [s.url for s in ev.consulted_sources] == ["https://a", "https://b"]
    assert ev.consulted_sources[0].title == "A"
    assert ev.consulted_sources[0].page_age == "1 week"
    assert ev.consulted_sources[0].encrypted_content == "EA"
    assert audit.final_text == "Bun is production-ready."
    assert len(audit.citations) == 1
    cit = audit.citations[0]
    assert cit.url == "https://a"
    assert cit.cited_text == "It is production-ready."
    assert cit.encrypted_index == "EI"
    # Text-span offsets reflect the position of the containing text block.
    assert cit.text_span_start == 0
    assert cit.text_span_end == len("Bun is production-ready.")


def test_normalize_anthropic_handles_multiple_queries_and_unpaired_results():
    """Two queries in the same turn; a stray result block with no matching id is dropped."""
    msg = _message([
        _block("server_tool_use", id="t1", name="web_search", input={"query": "q1"}),
        _block(
            "web_search_tool_result",
            tool_use_id="t1",
            content=[_result_item(url="https://r1", title="R1")],
        ),
        _block("server_tool_use", id="t2", name="web_search", input={"query": "q2"}),
        _block(
            "web_search_tool_result",
            tool_use_id="t2",
            content=[_result_item(url="https://r2", title="R2")],
        ),
        # Stray result with no matching tool_use_id — silently dropped.
        _block(
            "web_search_tool_result",
            tool_use_id="ghost",
            content=[_result_item(url="https://stray", title="X")],
        ),
        _block("text", text="Done.", citations=[]),
    ])

    audit = normalize_anthropic_search_audit(
        msg, turn_key="phase1_claude", phase="phase1", agent="claude", label="l",
    )
    assert len(audit.tool_events) == 2
    assert audit.tool_events[0].queries == ["q1"]
    assert audit.tool_events[1].queries == ["q2"]
    urls = {s.url for ev in audit.tool_events for s in ev.consulted_sources}
    assert urls == {"https://r1", "https://r2"}


def test_normalize_anthropic_handles_empty_response():
    """No content blocks → empty audit."""
    msg = _message([])
    audit = normalize_anthropic_search_audit(
        msg, turn_key="phase1_claude", phase="phase1", agent="claude", label="l",
    )
    assert audit.tool_events == []
    assert audit.citations == []
    assert audit.final_text == ""

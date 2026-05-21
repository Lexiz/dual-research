"""Spec 0148 D13 / D14 — ``system.web_sources`` and
``system.tool_definitions`` rows on the prompt-pieces dict.

These pieces are emitted at the **agent layer** (not ``pieces_for_*``):
each agent stashes ``web_sources_text`` and ``tool_definitions_text``
in ``AgentResult.extras``; ``orchestrator/_call.py`` tokenises them
post-call and augments the ``prompt_pieces`` dict before emitting
``TurnEnded``. These tests validate the registry registration and
exercise the tokenisation arithmetic on synthetic inputs.
"""

from __future__ import annotations

from dual_research.contract.artifacts import REGISTRY, display_name
from dual_research.protocol.prompt_pieces import (
    Attachment,
    estimate_tokens,
    pieces_for_preflight,
    pieces_for_review,
)


def test_system_web_sources_registered() -> None:
    ids = [a.id_template for a in REGISTRY]
    assert "system.web_sources" in ids
    assert display_name("system.web_sources") == "Web search results"


def test_system_tool_definitions_registered() -> None:
    ids = [a.id_template for a in REGISTRY]
    assert "system.tool_definitions" in ids
    assert display_name("system.tool_definitions") == "Tool definitions"


def test_estimate_tokens_on_synthetic_search_result_text() -> None:
    # The agent layer produces a "title\nurl" line per result; assert
    # the estimator returns a stable non-zero token count for a
    # realistic 3-result concatenation.
    ws_text = "\n\n".join([
        "Result one title\nhttps://example.com/one",
        "Result two title\nhttps://example.com/two",
        "Result three title\nhttps://example.com/three",
    ])
    tokens = estimate_tokens(ws_text)
    # ~150 chars / 3.5 ≈ 43 tokens
    assert tokens > 0
    assert tokens >= 30  # not pathologically small
    assert tokens <= 100  # not pathologically large


def test_estimate_tokens_on_tool_definitions_json() -> None:
    # Realistic anthropic/openai web_search tool definitions are both
    # in the ~50-100 char range when JSON-serialised. Token estimate
    # should land in the ~10-30 token band.
    anthropic_json = '[{"max_uses": 10, "name": "web_search", "type": "web_search_20250305"}]'
    openai_json = '[{"search_context_size": "high", "type": "web_search"}]'
    a_tokens = estimate_tokens(anthropic_json)
    o_tokens = estimate_tokens(openai_json)
    assert 10 <= a_tokens <= 40
    assert 5 <= o_tokens <= 30


def test_pieces_for_preflight_unaffected_by_spec_0148() -> None:
    # Spec 0148 emits web_sources / tool_definitions in _call.py, not
    # pieces_for_*. Confirm pieces_for_preflight's output still has
    # exactly the spec-0145 shape — no new keys leak in.
    pieces = pieces_for_preflight(
        system_task="Do the thing.",
        user_prompt_message="Brief content.",
        attachments=(Attachment(id="att1", title="A", content="alpha"),),
    )
    assert "system.task.input" in pieces
    assert "user_prompt.message" in pieces
    assert "user_prompt.attachment.att1" in pieces
    # Spec-0148 keys do NOT come from pieces_for_*; they're added
    # post-call in _call.py.
    assert "system.web_sources" not in pieces
    assert "system.tool_definitions" not in pieces


def test_pieces_for_review_closeout_request_still_emitted() -> None:
    # Sanity for the D10 dependency — closeout.request lands in the
    # dict whenever the closeout_request kwarg is set. The aggregator
    # derives ``was_closeout`` from this key's presence.
    pieces = pieces_for_review(
        system_task="Review.",
        user_prompt_message="Brief.",
        current_draft="Draft body.",
        closeout_request="Please close out.",
    )
    assert pieces["closeout.request"] > 0

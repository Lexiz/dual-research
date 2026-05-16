"""Spec 0036 — TurnSearches event shape + serialisation round-trip."""
from __future__ import annotations

from dual_research.events import TurnSearches


def test_turn_searches_event_kind_and_fields():
    audit_dict = {
        "provider": "anthropic",
        "model": "claude-haiku-4-5",
        "turn_key": "phase1_claude",
        "phase": "phase1",
        "agent": "claude",
        "label": "phase1-claude",
        "emitted_at": "2026-05-16T13:00:00+00:00",
        "tool_events": [],
        "citations": [],
        "flags": {},
        "final_text": "",
    }
    ev = TurnSearches(
        agent="claude",
        phase="phase1",
        label="phase1-claude",
        turn_key="phase1_claude",
        audit=audit_dict,
    )
    assert ev.kind == "turn_searches"
    assert ev.agent == "claude"
    assert ev.audit["provider"] == "anthropic"
    # Frozen + serialisable via to_dict.
    payload = ev.to_dict()
    assert payload["kind"] == "turn_searches"
    assert payload["audit"]["turn_key"] == "phase1_claude"


def test_turn_searches_default_audit_is_empty_dict():
    ev = TurnSearches(agent="claude", phase="phase1", label="l", turn_key="k")
    assert ev.audit == {}

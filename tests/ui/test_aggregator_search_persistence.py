"""Spec 0036 — aggregator persists TurnSearches events to disk."""
from __future__ import annotations

import json
from pathlib import Path

from dual_research.ui.aggregator import apply_event
from dual_research.ui.models import Run, TurnTokenUsage


def _new_run() -> Run:
    return Run(id="r-1", display_id="r-1")


def _search_event(*, agent: str, phase: str, label: str, turn_key: str, audit: dict) -> dict:
    return {
        "event": "turn_searches",
        "agent": agent,
        "phase": phase,
        "label": label,
        "turn_key": turn_key,
        "audit": audit,
    }


def _audit_dict(*, has_hallucination: bool = False) -> dict:
    audit = {
        "provider": "anthropic",
        "model": "claude-haiku-4-5",
        "turn_key": "phase1_claude",
        "phase": "phase1",
        "agent": "claude",
        "label": "phase1-claude",
        "emitted_at": "2026-05-16T13:00:00+00:00",
        "tool_events": [
            {
                "event_id": "srvtool_1",
                "type": "web_search",
                "action_type": "search",
                "queries": ["bun production"],
                "consulted_sources": [
                    {"url": "https://example.com/a", "title": "A"},
                ],
            }
        ],
        "final_text": "Bun is solid.",
        "citations": [
            {
                "url": "https://fabricated.invalid/x" if has_hallucination else "https://example.com/a",
                "title": "A",
            }
        ],
        "flags": {},
    }
    return audit


def test_aggregator_writes_search_bundle_to_disk(tmp_path: Path):
    run = _new_run()
    event = _search_event(
        agent="claude",
        phase="phase1",
        label="phase1-claude",
        turn_key="phase1_claude",
        audit=_audit_dict(),
    )
    apply_event(run, event, tmp_path)

    bundle_path = tmp_path / "searches" / "phase1_claude.json"
    assert bundle_path.is_file()
    payload = json.loads(bundle_path.read_text())
    assert payload["provider"] == "anthropic"
    # Validator ran during persistence — flags populated.
    assert payload["flags"]["search_performed"] is True
    # And matched_query_id is stamped onto the citation.
    assert payload["citations"][0]["matched_query_id"] == "srvtool_1"

    # TurnTokenUsage gains a search_audit_path stub.
    usage = run.phase_token_usage["phase1_claude"]
    assert usage.search_audit_path == "searches/phase1_claude.json"


def test_aggregator_flags_hallucinated_citation_on_disk(tmp_path: Path):
    run = _new_run()
    event = _search_event(
        agent="claude",
        phase="phase1",
        label="phase1-claude",
        turn_key="phase1_claude",
        audit=_audit_dict(has_hallucination=True),
    )
    apply_event(run, event, tmp_path)
    payload = json.loads((tmp_path / "searches" / "phase1_claude.json").read_text())
    assert payload["flags"]["cited_url_not_in_consulted_sources"] is True
    assert payload["citations"][0]["matched_query_id"] is None


def test_aggregator_preserves_search_audit_path_through_turn_ended(tmp_path: Path):
    """search_audit_path stamped by _on_turn_searches must survive the
    subsequent _on_turn_ended handler (which would otherwise overwrite
    the row)."""
    run = _new_run()
    apply_event(run, _search_event(
        agent="claude",
        phase="phase1",
        label="phase1-claude",
        turn_key="phase1_claude",
        audit=_audit_dict(),
    ), tmp_path)
    # Now the TurnEnded event arrives.
    apply_event(run, {
        "event": "turn_ended",
        "agent": "claude",
        "phase": "phase1",
        "label": "phase1-claude",
        "input_tokens": 1000,
        "output_tokens": 500,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "cost_usd": 0.1,
        "duration_ms": 1234,
        "model_id": "claude-haiku-4-5",
        "searches": 1,
    }, tmp_path)
    usage = run.phase_token_usage["phase1_claude"]
    assert usage.in_ == 1000
    assert usage.search_audit_path == "searches/phase1_claude.json"


def test_aggregator_ignores_empty_audit_payload(tmp_path: Path):
    run = _new_run()
    apply_event(run, _search_event(
        agent="claude", phase="phase1", label="l", turn_key="k", audit={},
    ), tmp_path)
    assert not (tmp_path / "searches").exists()

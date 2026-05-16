"""Spec 0038 — unit coverage for the search-audit summary helpers.

The HTTP layer is exercised in :mod:`tests.ui.test_server`. This module
pins the helper's behaviour directly so a refactor of the response shape
doesn't have to touch the chip-layer counters too.
"""

from __future__ import annotations

import json
from pathlib import Path

from dual_research.ui.server import (
    _list_search_audit_keys_fs,
    _search_audit_summary_fs,
    _summarize_audit_payload,
)


def _write_audit(session: Path, key: str, payload: dict) -> None:
    searches = session / "searches"
    searches.mkdir(exist_ok=True)
    (searches / f"{key}.json").write_text(json.dumps(payload), encoding="utf-8")


def test_summarize_audit_payload_counts_events_and_consulted():
    payload = {
        "tool_events": [
            {
                "event_id": "e1",
                "queries": ["q1"],
                "consulted_sources": [
                    {"url": "https://a.example/x"},
                    {"url": "https://b.example/y"},
                ],
            },
            {
                "event_id": "e2",
                "queries": ["q2"],
                "consulted_sources": [{"url": "https://c.example/z"}],
            },
        ],
        "citations": [],
        "flags": {"cited_url_not_in_consulted_sources": False},
    }
    assert _summarize_audit_payload(payload) == {
        "queries": 2,
        "consulted": 3,
        "has_warning": False,
    }


def test_summarize_audit_payload_surfaces_hallucination_flag():
    payload = {
        "tool_events": [
            {"event_id": "e", "queries": [], "consulted_sources": []},
        ],
        "citations": [{"url": "https://elsewhere.invalid/x"}],
        "flags": {"cited_url_not_in_consulted_sources": True},
    }
    out = _summarize_audit_payload(payload)
    assert out["has_warning"] is True
    assert out["queries"] == 1
    assert out["consulted"] == 0


def test_summarize_audit_payload_tolerant_to_missing_fields():
    # Older transcripts may lack ``flags`` or ``tool_events``; the helper
    # must not raise — chip-layer absence is the right UI signal.
    assert _summarize_audit_payload({}) == {
        "queries": 0, "consulted": 0, "has_warning": False,
    }
    assert _summarize_audit_payload({"tool_events": None}) == {
        "queries": 0, "consulted": 0, "has_warning": False,
    }


def test_search_audit_summary_fs_only_summarises_listed_keys(tmp_path):
    session = tmp_path / "session"
    session.mkdir()
    _write_audit(
        session,
        "phase1_claude",
        {
            "tool_events": [
                {"event_id": "e", "queries": ["q"], "consulted_sources": [{"url": "https://a/"}]},
            ],
            "flags": {"cited_url_not_in_consulted_sources": False},
        },
    )
    _write_audit(
        session,
        "phase1_gpt",
        {
            "tool_events": [
                {
                    "event_id": "e",
                    "queries": ["q"],
                    "consulted_sources": [
                        {"url": "https://b/"},
                        {"url": "https://c/"},
                    ],
                }
            ],
            "flags": {"cited_url_not_in_consulted_sources": True},
        },
    )

    keys = _list_search_audit_keys_fs(session)
    assert sorted(keys) == ["phase1_claude", "phase1_gpt"]

    summary = _search_audit_summary_fs(session, keys)
    assert summary["phase1_claude"] == {
        "queries": 1, "consulted": 1, "has_warning": False,
    }
    assert summary["phase1_gpt"] == {
        "queries": 1, "consulted": 2, "has_warning": True,
    }


def test_search_audit_summary_fs_skips_unreadable(tmp_path):
    session = tmp_path / "session"
    (session / "searches").mkdir(parents=True)
    (session / "searches" / "broken.json").write_text("{not json", encoding="utf-8")

    keys = _list_search_audit_keys_fs(session)
    assert keys == ["broken"]
    summary = _search_audit_summary_fs(session, keys)
    # Unparseable file silently drops out of the summary; chip layer
    # gracefully renders nothing.
    assert summary == {}


def test_search_audit_summary_fs_returns_empty_when_no_dir(tmp_path):
    session = tmp_path / "noaudit"
    session.mkdir()
    assert _list_search_audit_keys_fs(session) == []
    assert _search_audit_summary_fs(session, []) == {}

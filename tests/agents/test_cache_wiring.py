from __future__ import annotations

import pytest

from dual_research.agents.anthropic_agent import _build_content
from dual_research.agents.base import cache_enabled
from dual_research.protocol import CACHE_BREAKPOINT


def test_cache_enabled_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DUAL_RESEARCH_NO_CACHE", raising=False)
    assert cache_enabled() is True


@pytest.mark.parametrize("val", ["1", "true", "yes", "TRUE", "Yes"])
def test_cache_disabled_by_env(monkeypatch: pytest.MonkeyPatch, val: str) -> None:
    monkeypatch.setenv("DUAL_RESEARCH_NO_CACHE", val)
    assert cache_enabled() is False


def test_build_content_splits_on_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DUAL_RESEARCH_NO_CACHE", raising=False)
    prompt = f"prefix here{CACHE_BREAKPOINT}dynamic part"
    content = _build_content(prompt)
    assert isinstance(content, list)
    assert len(content) == 2
    assert content[0]["text"] == "prefix here"
    assert content[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert content[1]["text"] == "dynamic part"
    assert "cache_control" not in content[1]


def test_build_content_passthrough_when_no_marker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DUAL_RESEARCH_NO_CACHE", raising=False)
    prompt = "no marker here"
    content = _build_content(prompt)
    assert content == "no marker here"


def test_build_content_strips_marker_when_cache_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DUAL_RESEARCH_NO_CACHE", "1")
    prompt = f"prefix{CACHE_BREAKPOINT}suffix"
    content = _build_content(prompt)
    assert content == "prefixsuffix"
    assert CACHE_BREAKPOINT not in content


def test_build_content_with_marker_at_end() -> None:
    # Marker right at the end leaves an empty suffix block; still valid.
    prompt = f"everything{CACHE_BREAKPOINT}"
    content = _build_content(prompt)
    assert isinstance(content, list)
    assert content[0]["text"] == "everything"
    assert content[1]["text"] == ""


def test_build_content_multiple_markers_spec_0149(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec 0149 §5.3 (D02) — Phase 2 / 3 / 4 prompts emit two markers
    (one after the brief, one after the drafts). Anthropic accepts up to
    four cache_control breakpoints and matches the longest stable
    prefix, so we apply cache_control to every chunk except the last.
    """
    monkeypatch.delenv("DUAL_RESEARCH_NO_CACHE", raising=False)
    prompt = (
        f"common preamble{CACHE_BREAKPOINT}"
        f"brief{CACHE_BREAKPOINT}"
        f"drafts{CACHE_BREAKPOINT}"
        f"per-turn suffix"
    )
    content = _build_content(prompt)
    assert isinstance(content, list)
    assert len(content) == 4
    # All chunks except the last carry cache_control.
    for i in range(3):
        assert content[i]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert "cache_control" not in content[3]
    # Chunk content preserves order.
    assert content[0]["text"] == "common preamble"
    assert content[1]["text"] == "brief"
    assert content[2]["text"] == "drafts"
    assert content[3]["text"] == "per-turn suffix"


def test_build_content_two_markers_phase4_shape() -> None:
    """Mirrors the Phase 4 review prompt's two-breakpoint shape: brief is
    always stable; current draft mutates between rounds; the brief-only
    prefix should still cache_read on draft revisions."""
    prompt = (
        f"common preamble + phase header{CACHE_BREAKPOINT}"
        f"brief block (stable across rounds){CACHE_BREAKPOINT}"
        f"draft block (mutates on revision) + per-turn suffix"
    )
    content = _build_content(prompt)
    assert isinstance(content, list)
    assert len(content) == 3
    assert content[0]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert content[1]["cache_control"] == {"type": "ephemeral", "ttl": "1h"}
    assert "cache_control" not in content[2]

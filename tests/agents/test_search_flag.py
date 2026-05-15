from __future__ import annotations

import pytest

from dual_research.agents.base import web_search_enabled


def test_web_search_enabled_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DUAL_RESEARCH_NO_WEB_SEARCH", raising=False)
    assert web_search_enabled() is True


@pytest.mark.parametrize("val", ["1", "true", "yes", "TRUE", "Yes"])
def test_web_search_disabled_by_truthy_env(monkeypatch: pytest.MonkeyPatch, val: str) -> None:
    monkeypatch.setenv("DUAL_RESEARCH_NO_WEB_SEARCH", val)
    assert web_search_enabled() is False


@pytest.mark.parametrize("val", ["", "0", "false", "no", "off"])
def test_web_search_enabled_by_falsy_env(monkeypatch: pytest.MonkeyPatch, val: str) -> None:
    monkeypatch.setenv("DUAL_RESEARCH_NO_WEB_SEARCH", val)
    assert web_search_enabled() is True

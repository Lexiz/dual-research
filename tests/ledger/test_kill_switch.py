"""Spec 0043 D9 — DR_LEDGER_MODE kill-switch tests."""

from __future__ import annotations

from dual_research.ledger import ledger_mode


def test_ledger_mode_defaults_to_enforce(monkeypatch) -> None:
    monkeypatch.delenv("DR_LEDGER_MODE", raising=False)
    assert ledger_mode() == "enforce"


def test_ledger_mode_legacy_when_env_set(monkeypatch) -> None:
    monkeypatch.setenv("DR_LEDGER_MODE", "legacy")
    assert ledger_mode() == "legacy"


def test_ledger_mode_case_insensitive(monkeypatch) -> None:
    monkeypatch.setenv("DR_LEDGER_MODE", "LEGACY")
    assert ledger_mode() == "legacy"
    monkeypatch.setenv("DR_LEDGER_MODE", "Legacy")
    assert ledger_mode() == "legacy"


def test_ledger_mode_unknown_value_falls_back_to_enforce(monkeypatch) -> None:
    monkeypatch.setenv("DR_LEDGER_MODE", "garbage")
    assert ledger_mode() == "enforce"

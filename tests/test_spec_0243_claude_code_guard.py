"""Spec 0243 — operational guard: dual-research refuses to run inside Claude Code.

Tests the CLI guard added in [`src/dual_research/cli.py`](src/dual_research/cli.py)
that hard-exits with code 2 + a canonical Terminal.app command in stderr when
any `CLAUDECODE` / `CLAUDE_CODE_*` env var is set, unless
`DUAL_RESEARCH_ALLOW_CLAUDE_P=1` opts out.

Test surface:
- `_running_inside_claude_code()` — detection rule (CLAUDECODE or CLAUDE_CODE_* prefix).
- `_maybe_refuse_claude_code_host()` — the refusal helper (raise SystemExit(2)).
- `main()` integration on the LLM-firing path (default + --resume) vs the
  read-only early-dispatch path (verify / serve / etc.).
- `dual-research --help` epilog mentions `DUAL_RESEARCH_ALLOW_CLAUDE_P`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research import cli
from dual_research.cli import (
    _maybe_refuse_claude_code_host,
    _running_inside_claude_code,
    main,
)


# Note: ``tests/conftest.py`` has an autouse ``_strip_claude_code_env``
# fixture that clears ``CLAUDECODE`` / ``CLAUDE_CODE_*`` /
# ``DUAL_RESEARCH_ALLOW_CLAUDE_P`` before every test. Each test below
# re-injects only what it needs via ``monkeypatch.setenv``.


# --- detection rule -----------------------------------------------------------


def test_detection_fires_on_CLAUDECODE(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDECODE", "1")
    assert _running_inside_claude_code() is True


def test_detection_fires_on_CLAUDE_CODE_ENTRYPOINT(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "claude-desktop")
    assert _running_inside_claude_code() is True


def test_detection_fires_on_CLAUDE_CODE_HOST_arbitrary_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Cowork sign-off's load-bearing case: the sandbox sets CLAUDE_CODE_HOST_*
    # variants without CLAUDECODE. The detection rule must widen on the prefix.
    monkeypatch.setenv("CLAUDE_CODE_HOST_FOO", "bar")
    assert _running_inside_claude_code() is True


def test_detection_clean_in_plain_terminal() -> None:
    assert _running_inside_claude_code() is False


# --- refusal helper -----------------------------------------------------------


def test_guard_refuses_when_CLAUDECODE_set(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("CLAUDECODE", "1")
    with pytest.raises(SystemExit) as excinfo:
        _maybe_refuse_claude_code_host()
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "refusing to run inside Claude Code" in err
    assert "caffeinate -i uv run dual-research" in err
    assert "DUAL_RESEARCH_ALLOW_CLAUDE_P=1" in err


def test_guard_refuses_when_CLAUDE_CODE_ENTRYPOINT_set(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "claude-desktop")
    with pytest.raises(SystemExit) as excinfo:
        _maybe_refuse_claude_code_host()
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "refusing to run inside Claude Code" in err
    assert "caffeinate -i uv run dual-research" in err


def test_guard_refuses_when_CLAUDE_CODE_HOST_set(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Load-bearing test for Cowork's "widen detection" guidance: Cowork's
    # sandbox sets CLAUDE_CODE_HOST_* without CLAUDECODE. A guard that only
    # checked CLAUDECODE would false-negative here and the H4 surface would
    # remain open from inside sandbox-mode invocations.
    monkeypatch.setenv("CLAUDE_CODE_HOST_FOO", "bar")
    with pytest.raises(SystemExit) as excinfo:
        _maybe_refuse_claude_code_host()
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "refusing to run inside Claude Code" in err


def test_guard_allows_with_escape_var(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("DUAL_RESEARCH_ALLOW_CLAUDE_P", "1")
    # No SystemExit raised; helper returns silently.
    _maybe_refuse_claude_code_host()
    assert capsys.readouterr().err == ""


def test_guard_escape_var_must_be_exactly_1(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Soft accidental-typo guard: DUAL_RESEARCH_ALLOW_CLAUDE_P=true / yes /
    # anything-but-"1" still refuses. The escape needs to be deliberate.
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("DUAL_RESEARCH_ALLOW_CLAUDE_P", "true")
    with pytest.raises(SystemExit) as excinfo:
        _maybe_refuse_claude_code_host()
    assert excinfo.value.code == 2


def test_guard_allows_in_plain_terminal(capsys: pytest.CaptureFixture[str]) -> None:
    # No SystemExit; helper returns silently.
    _maybe_refuse_claude_code_host()
    assert capsys.readouterr().err == ""


# --- CLI integration ----------------------------------------------------------


def test_main_refuses_when_CLAUDECODE_set(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # End-to-end: invoking the CLI with a prompt while CLAUDECODE=1 fails
    # fast (before any ingest or cred load).
    monkeypatch.setenv("CLAUDECODE", "1")
    with pytest.raises(SystemExit) as excinfo:
        main(["--prompt", "hello"])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "refusing to run inside Claude Code" in err


def test_main_refuses_on_resume_when_CLAUDECODE_set(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    # --resume also fires an LLM run; the guard must catch it before the
    # resume path's session-dir checks.
    monkeypatch.setenv("CLAUDECODE", "1")
    with pytest.raises(SystemExit) as excinfo:
        main(["--resume", str(tmp_path)])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    assert "refusing to run inside Claude Code" in err


def test_main_push_exempt_from_guard(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    # --push fires a Supabase upload (no LLM call). It is the only argparse
    # path that is exempt; setting CLAUDECODE=1 must NOT block --push.
    monkeypatch.setenv("CLAUDECODE", "1")
    fake_session = tmp_path / "fake-session"
    fake_session.mkdir()
    # main()'s _run_push errors out on missing Supabase creds or a malformed
    # session dir; either way the refusal message must not appear.
    try:
        main(["--push", str(fake_session)])
    except SystemExit:
        pass
    err = capsys.readouterr().err
    assert "refusing to run inside Claude Code" not in err


def test_main_does_not_block_verify_subcommand(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # `verify` is dispatched at the top of main() before the parser ever sees
    # its args. The guard sits after the parser, so verify never hits it.
    monkeypatch.setenv("CLAUDECODE", "1")
    invoked = {"called": False}

    def fake_verify(argv: list[str]) -> int:
        invoked["called"] = True
        return 0

    monkeypatch.setattr("dual_research.verifier_cli.main", fake_verify)
    rc = main(["verify"])
    assert rc == 0
    assert invoked["called"] is True
    err = capsys.readouterr().err
    assert "refusing to run inside Claude Code" not in err


def test_main_does_not_block_serve_subcommand(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("CLAUDECODE", "1")
    invoked = {"called": False}

    def fake_serve(argv: list[str]) -> int:
        invoked["called"] = True
        return 0

    monkeypatch.setattr("dual_research.ui.server.main", fake_serve)
    rc = main(["serve"])
    assert rc == 0
    assert invoked["called"] is True
    err = capsys.readouterr().err
    assert "refusing to run inside Claude Code" not in err


def test_main_does_not_block_validate_run_subcommand(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("CLAUDECODE", "1")
    invoked = {"called": False}

    def fake_validate(argv: list[str]) -> int:
        invoked["called"] = True
        return 0

    monkeypatch.setattr("dual_research.validate_cli.main", fake_validate)
    rc = main(["validate-run"])
    assert rc == 0
    assert invoked["called"] is True
    err = capsys.readouterr().err
    assert "refusing to run inside Claude Code" not in err


def test_main_does_not_block_recompute_costs_subcommand(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("CLAUDECODE", "1")
    invoked = {"called": False}

    def fake_recompute(argv: list[str]) -> int:
        invoked["called"] = True
        return 0

    monkeypatch.setattr(cli, "_run_recompute", fake_recompute)
    rc = main(["recompute-costs"])
    assert rc == 0
    assert invoked["called"] is True
    err = capsys.readouterr().err
    assert "refusing to run inside Claude Code" not in err


# --- help epilog --------------------------------------------------------------


def test_cli_help_mentions_escape_var(capsys: pytest.CaptureFixture[str]) -> None:
    # `dual-research --help` prints to stdout and argparse exits 0.
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "DUAL_RESEARCH_ALLOW_CLAUDE_P" in out


# --- CLAUDE.md + skill source-pattern guards ---------------------------------


def _repo_root() -> Path:
    # tests/test_spec_0243_claude_code_guard.py → repo root is two parents up.
    return Path(__file__).resolve().parent.parent


def test_claude_md_has_operational_section() -> None:
    text = (_repo_root() / "CLAUDE.md").read_text(encoding="utf-8")
    assert "## Operational" in text
    assert "DUAL_RESEARCH_ALLOW_CLAUDE_P" in text
    assert "caffeinate -i uv run dual-research" in text
    # Anchor to the spec so future edits can trace the origin.
    assert "spec 0243" in text or "0243" in text


def test_dual_research_run_skill_amended_for_0243() -> None:
    skill = _repo_root() / ".claude" / "skills" / "dual-research-run" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    # The skill must point the user at a plain Terminal.app session and
    # mention the spec-0243 guard. The canonical Terminal command pattern
    # is locked here so a future edit can't silently revert.
    assert "spec 0243" in text
    assert "caffeinate -i uv run dual-research" in text
    assert "Terminal.app" in text

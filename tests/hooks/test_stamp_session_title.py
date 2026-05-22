"""Regression test for spec 0155 — stamp-session-title.py.

Before spec 0155: no helper script existed, so the lifecycle skills
(``/spec-draft``, ``/spec-queue``, ``/spec-promote``, ``/dev-next``,
``/dev-queue-run``) hand-waved the title-stamping mechanics and most stamps
silently never happened (spec 0154's session was the live evidence).

After spec 0155: a single bash call hits ``~/.claude/hooks/stamp-session-title.py``
which writes ``[<prefix>] <body>`` into the CCD session metadata file via the
same atomic-write + retry-verify loop the auto-prefix hook uses.

This test is **host-bound**: it exercises the helper script installed at
``~/.claude/hooks/stamp-session-title.py``. CI runners (GitHub Actions) don't
have that path, so the test skips there. Locally it runs every time and is
the spec's regression guard.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

STAMP_SCRIPT = Path.home() / ".claude" / "hooks" / "stamp-session-title.py"
SESSION_METADATA_MODULE = Path.home() / ".claude" / "hooks" / "session_metadata.py"


pytestmark = pytest.mark.skipif(
    not STAMP_SCRIPT.exists() or not SESSION_METADATA_MODULE.exists(),
    reason="host-side ~/.claude/hooks/stamp-session-title.py not installed (spec 0155)",
)


def _write_meta(desktop_dir: Path, session_id: str, title: str = "untitled") -> Path:
    """Drop a CCD-style local_*.json under the given desktop dir."""
    desktop_dir.mkdir(parents=True, exist_ok=True)
    meta_path = desktop_dir / f"local_{session_id}.json"
    meta_path.write_text(json.dumps({
        "cliSessionId": session_id,
        "title": title,
        "titleSource": "auto",
    }))
    return meta_path


def _run_stamp(
    *,
    desktop_dir: Path,
    cache_path: Path,
    prefix_key: str,
    body: str,
    session_id: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(STAMP_SCRIPT),
            "--prefix-key", prefix_key,
            "--body", body,
            "--session-id", session_id,
            "--desktop-dir", str(desktop_dir),
            "--cache-path", str(cache_path),
            "--quiet",
        ],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "CLAUDE_SESSION_ID": ""},  # ensure CLI arg wins
    )


def test_stamp_writes_title_and_updates_cache(tmp_path: Path) -> None:
    """One invocation: metadata title becomes ``[prefix] body``, cache picks up the full prefix."""
    desktop = tmp_path / "ccd_sessions"
    cache_path = tmp_path / "session-prefixes.json"
    session_id = "test-sid-0155"
    meta_path = _write_meta(desktop, session_id)

    proc = _run_stamp(
        desktop_dir=desktop,
        cache_path=cache_path,
        prefix_key="DR · 0155 · O",
        body="x",
        session_id=session_id,
    )
    assert proc.returncode == 0, proc.stderr

    meta = json.loads(meta_path.read_text())
    assert meta["title"] == "[DR · 0155 · O] x"
    assert meta["titleSource"] == "user"
    assert meta["cliSessionId"] == session_id  # untouched

    cache = json.loads(cache_path.read_text())
    assert cache == {session_id: "DR · 0155 · O"}


def test_stamp_second_invocation_replaces_cache_entry(tmp_path: Path) -> None:
    """A second stamp with a different prefix updates the same cache key — no duplicates."""
    desktop = tmp_path / "ccd_sessions"
    cache_path = tmp_path / "session-prefixes.json"
    session_id = "test-sid-0155"
    _write_meta(desktop, session_id)

    _run_stamp(
        desktop_dir=desktop, cache_path=cache_path,
        prefix_key="DR · 0155 · O", body="y", session_id=session_id,
    )
    _run_stamp(
        desktop_dir=desktop, cache_path=cache_path,
        prefix_key="DR · 0155 · X", body="y", session_id=session_id,
    )

    cache = json.loads(cache_path.read_text())
    # Single entry per session_id, with the latest prefix winning.
    assert cache == {session_id: "DR · 0155 · X"}


def test_stamp_reports_no_meta_when_session_missing(tmp_path: Path) -> None:
    """Exit code 1 when no metadata file matches the session id (and no fallback)."""
    desktop = tmp_path / "ccd_sessions"
    desktop.mkdir()  # empty
    cache_path = tmp_path / "session-prefixes.json"

    proc = subprocess.run(
        [
            sys.executable, str(STAMP_SCRIPT),
            "--prefix-key", "DR · 0155 · O",
            "--body", "x",
            "--session-id", "nonexistent-sid",
            "--desktop-dir", str(desktop),
            "--cache-path", str(cache_path),
            "--quiet",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "CLAUDE_SESSION_ID": ""},
    )
    assert proc.returncode == 1
    # Cache must not be created when the stamp couldn't land.
    assert not cache_path.exists()


def test_build_title_caps_at_60_chars() -> None:
    """The shared build_title helper enforces the 60-char total cap."""
    # Import the shared module directly (not via subprocess) so we exercise
    # the same code the auto-prefix hook reuses.
    sys.path.insert(0, str(SESSION_METADATA_MODULE.parent))
    try:
        from session_metadata import build_title  # noqa: WPS433  (runtime import is the test)
    finally:
        sys.path.pop(0)

    short = build_title("DR · 0155 · O", "x")
    assert short == "[DR · 0155 · O] x"

    long = build_title("DR · 0155 · O", "y" * 200)
    assert len(long) == 60
    assert long.startswith("[DR · 0155 · O] ")

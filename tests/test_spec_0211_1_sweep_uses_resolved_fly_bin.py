"""Source-pattern test: scripts/sweep_stale_blues.sh resolves the Fly CLI
binary name once and uses the resolved variable at every invocation site
(spec 0211.1).

Spec 0211 moved the post-deploy sweep from `/dev-next` (local) into
`.github/workflows/deploy.yml`. The CI runner carries `flyctl` (installed
by `superfly/flyctl-actions/setup-flyctl@master`) but no `fly` binary, so
the script's bare `fly machine list` invocation failed immediately with
`command not found`, swallowed by `2>/dev/null`. Spec 0211.1 introduces
a `FLY_BIN` resolver that prefers `flyctl` and falls back to `fly` for
operator-local usage; every Fly CLI call site uses `"$FLY_BIN"`.
"""

from __future__ import annotations

import re
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "sweep_stale_blues.sh"


def _non_comment_lines() -> list[tuple[int, str]]:
    """Return (line_number, line) tuples for every non-blank, non-comment line
    of the script. Line numbers are 1-indexed."""
    out: list[tuple[int, str]] = []
    for idx, raw in enumerate(SCRIPT_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        out.append((idx, raw))
    return out


def test_no_bare_fly_invocation() -> None:
    """No bash line invokes the bare `fly` binary for machine/releases
    subcommands — spec 0211.1 requires every site to go through `$FLY_BIN`."""
    pattern = re.compile(r"^\s*fly\s+(machine|releases)\b")
    offenders = [
        f"line {lineno}: {line.strip()}"
        for lineno, line in _non_comment_lines()
        if pattern.search(line)
    ]
    assert offenders == [], (
        "scripts/sweep_stale_blues.sh still invokes the bare `fly` binary — "
        f"spec 0211.1 requires `$FLY_BIN`. Offenders: {offenders}"
    )


def test_fly_bin_resolver_present() -> None:
    """The script declares a `FLY_BIN` variable in a resolver block that
    probes both `flyctl` and `fly`, falling back to a non-fatal skip when
    neither is on PATH (matches the best-effort exit-0 contract of the
    script)."""
    body = SCRIPT_PATH.read_text(encoding="utf-8")
    assert re.search(r"^\s*FLY_BIN=", body, re.MULTILINE), (
        "scripts/sweep_stale_blues.sh is missing the `FLY_BIN=` assignment "
        "introduced by spec 0211.1."
    )
    assert "command -v flyctl" in body, (
        "FLY_BIN resolver must probe `flyctl` (the CI-runner binary name)."
    )
    assert "command -v fly" in body, (
        "FLY_BIN resolver must fall back to `fly` for operator-local usage."
    )
    assert "neither flyctl nor fly on PATH" in body, (
        "FLY_BIN resolver must surface a distinct skip log when neither "
        "binary is available (so a future PATH-less env doesn't look like a "
        "generic `fly machine list failed`)."
    )


def test_every_fly_call_site_uses_resolved_bin() -> None:
    """Every Fly CLI invocation site uses `"$FLY_BIN"`. Spec 0211.1 enumerates
    four sites — machine list (the primary tag filter), releases (the
    spec-0193 fallback's release lookup), and machine destroy x2 (primary
    + fallback destroy loops). Require ≥ 4 hits."""
    pattern = re.compile(r'"\$FLY_BIN"\s+(machine|releases)\b')
    body = SCRIPT_PATH.read_text(encoding="utf-8")
    hits = pattern.findall(body)
    assert len(hits) >= 4, (
        f'expected ≥ 4 `"$FLY_BIN"` invocation sites in '
        f"scripts/sweep_stale_blues.sh, found {len(hits)}"
    )

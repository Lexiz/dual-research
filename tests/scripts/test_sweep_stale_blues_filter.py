"""Regression test for spec 0162 — the jq filter in scripts/sweep_stale_blues.sh.

The filter is the load-bearing safety logic: it determines which machines
the sweep will destroy. If the filter drifts (Fly renames the metadata
key, or someone widens the selector), stale blues either accumulate
indefinitely or — far worse — a live green gets destroyed. This test
locks the contract by running the *same* `jq` expression against a
hand-rolled fixture that mixes:

- 2 live greens (no ``fly_bluegreen_deployment_tag``)
- 2 stale blues tagged ``safe_to_destroy`` (Fly's own verdict)
- 1 machine with an unrelated bluegreen tag value (``attached``)
- 1 machine with no ``metadata`` block at all

Expected: only the 2 stale-blue IDs come back. Skips automatically when
``jq`` isn't on PATH (e.g. in a stripped-down CI image).
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "sweep_stale_blues.sh"
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "fly_machine_list_bluegreen.json"


pytestmark = pytest.mark.skipif(
    shutil.which("jq") is None,
    reason="jq not installed on PATH",
)


def _extract_jq_filter() -> str:
    """Pull the JQ_FILTER assignment out of the sweep script.

    Locking the filter at the script-source level (not duplicating it in
    the test) means the test asserts the *actual* filter that runs in
    production. A drift in either direction surfaces immediately.
    """
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    m = re.search(r"JQ_FILTER=(['\"])(.*?)\1", text)
    assert m is not None, "sweep script must define JQ_FILTER='...'"
    return m.group(2)


def _run_filter(filter_expr: str, fixture: Path) -> list[str]:
    result = subprocess.run(
        ["jq", "-r", filter_expr, str(fixture)],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def test_filter_selects_exactly_the_safe_to_destroy_machines() -> None:
    """The filter must return the two stale-blue IDs and nothing else."""
    ids = _run_filter(_extract_jq_filter(), FIXTURE_PATH)
    assert sorted(ids) == sorted([
        "blue-stale-ccccccccccccc",
        "blue-stale-ddddddddddddd",
    ]), (
        "filter selected unexpected set — live greens or unrelated-tag "
        "machines may be at risk of destruction"
    )


def test_filter_excludes_live_greens() -> None:
    """The two live greens (no fly_bluegreen_deployment_tag) must NOT be selected."""
    ids = _run_filter(_extract_jq_filter(), FIXTURE_PATH)
    assert "green-aaaaaaaaaaaaaaa" not in ids
    assert "green-bbbbbbbbbbbbbbb" not in ids


def test_filter_excludes_machines_with_other_bluegreen_tags() -> None:
    """A machine tagged `attached` (mid-deploy, not safe to destroy) must
    NOT be selected."""
    ids = _run_filter(_extract_jq_filter(), FIXTURE_PATH)
    assert "blue-mid-deploy-eeeeeeee" not in ids


def test_filter_handles_missing_metadata_block() -> None:
    """A machine with no `metadata` block at all must NOT be selected and
    must not crash jq."""
    ids = _run_filter(_extract_jq_filter(), FIXTURE_PATH)
    assert "no-metadata-ffffffffff" not in ids


def test_filter_handles_empty_input() -> None:
    """An empty machine list must produce an empty result, not an error."""
    result = subprocess.run(
        ["jq", "-r", _extract_jq_filter()],
        input="[]",
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == ""


# ── End-to-end sweep-script tests using --input ────────────────────────────
#
# The `--input <file>` flag (spec 0162) lets us exercise the full bash flow
# without ever calling `fly machine list` or `fly machine destroy`. Two
# scenarios matter:
#   - Cluster has the expected count, filter matches nothing → quiet success.
#   - Cluster has more than expected AND filter matches nothing → diagnostic
#     dump on stderr so the next handoff captures evidence.


SWEEP_SCRIPT = REPO_ROOT / "scripts" / "sweep_stale_blues.sh"
FIXTURE_NO_STALE_EXTRA = REPO_ROOT / "tests" / "fixtures" / "fly_machine_list_no_stale_extra.json"


def _run_sweep(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SWEEP_SCRIPT), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def test_sweep_logs_no_stale_when_filter_misses(tmp_path: Path) -> None:
    """Cluster is exactly the expected size, filter matches nothing → quiet
    'no stale blues' log line, no metadata dump."""
    proc = _run_sweep(
        "--input", str(FIXTURE_PATH),  # the fixture also contains 2 safe_to_destroy entries,
        "--expected-count", "10",       # but we lift the threshold above the count so the
                                        # diagnostic branch doesn't fire — testing the no-extra path.
    )
    # The fixture has 2 safe_to_destroy entries, but with --input we don't
    # actually destroy anything (the script short-circuits when --input is
    # set). The destroy summary still gets logged.
    assert proc.returncode == 0
    assert "destroyed 2/2" in proc.stdout or "no stale blues" in proc.stdout
    # Spec 0193 renamed the diagnostic log line from "dumping metadata for
    # filter diagnosis" to "checking image-release fallback filter" because
    # the oversize-cluster branch now also runs the image-based fallback.
    # Both phrases would indicate the diagnostic branch fired.
    assert "checking image-release fallback filter" not in proc.stderr
    assert "dumping metadata for filter diagnosis" not in proc.stderr


def test_sweep_dumps_metadata_when_filter_misses_but_cluster_oversized() -> None:
    """When filter finds 0 stale AND cluster size > expected, the oversize-
    cluster diagnostic branch fires. Spec 0162 dumped metadata; spec 0193
    runs the image-based fallback first and dumps only on the gate-failure
    paths (skipped / refused / found-zero). With no sibling .release.json
    next to this fixture, gate 3 fails and the script dumps for triage."""
    proc = _run_sweep(
        "--input", str(FIXTURE_NO_STALE_EXTRA),  # 4 machines, none tagged safe_to_destroy
        "--expected-count", "2",
    )
    assert proc.returncode == 0
    assert "no stale blues" in proc.stdout
    # Spec 0193 — the oversize-cluster branch now logs the image-based
    # fallback check (which then skips because no sibling .release.json).
    assert "checking image-release fallback filter" in proc.stderr
    assert "could not determine current release image" in proc.stderr
    # Dump contains the suspect machines' IDs so a human can read them.
    assert "mystery-stale-cccccccccccccc" in proc.stderr
    assert "mystery-stale-dddddddddddddd" in proc.stderr


def test_sweep_no_dump_when_cluster_size_matches_expected() -> None:
    """When filter finds 0 stale AND cluster size == expected, no dump.
    Quiet success — nothing to investigate."""
    # Use the no-stale-extra fixture but pass --expected-count 4 so the
    # cluster size matches expected exactly.
    proc = _run_sweep(
        "--input", str(FIXTURE_NO_STALE_EXTRA),
        "--expected-count", "4",
    )
    assert proc.returncode == 0
    assert "no stale blues" in proc.stdout
    # Neither the old diagnostic phrase nor the new spec-0193 phrase fires.
    assert "dumping metadata for filter diagnosis" not in proc.stderr
    assert "checking image-release fallback filter" not in proc.stderr


def test_sweep_input_flag_does_not_call_fly() -> None:
    """The --input flag must short-circuit any fly CLI call. Verify by
    pointing at a fixture from inside an env where fly would fail loudly
    (we just trust that subprocess.run doesn't see a 'fly:' error in
    output)."""
    proc = _run_sweep("--input", str(FIXTURE_NO_STALE_EXTRA))
    # No fly-cli error strings on either stream.
    combined = proc.stdout + proc.stderr
    assert "fly machine list failed" not in combined
    assert "fly machine destroy" not in combined

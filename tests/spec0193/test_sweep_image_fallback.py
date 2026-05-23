"""Spec 0193 — image-based fallback filter for `scripts/sweep_stale_blues.sh`.

Spec 0162 added the `safe_to_destroy` tag filter to clean up stale blues
after a deploy. Spec 0186's deploy (and every deploy in today's queue drain)
demonstrated a second failure mode: Fly leaves blues hanging WITHOUT the
`safe_to_destroy` tag. The tag filter says "no stale blues" while the
cluster is still oversize.

Spec 0193 adds a fallback that runs only when the tag filter found nothing
AND the cluster is oversize. The fallback selects machines whose
`config.image` does not equal the current release image (queried from
`fly releases --app … --json` in live mode; from a sibling `.release.json`
fixture in test mode).

Four gates protect the fallback from ever destroying a live green:
  1. Tag filter returned 0.
  2. Cluster oversize per `--expected-count`.
  3. Current release image is determinable.
  4. At least one machine matches the current image.

These tests cover the canonical scenarios from spec §6 by running the
shell script as a subprocess against fixture JSON.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent.parent
SCRIPT = ROOT / "scripts" / "sweep_stale_blues.sh"
FIXTURES = Path(__file__).parent / "fixtures"


def _run_sweep(
    fixture_name: str,
    *,
    expected_count: int = 2,
) -> subprocess.CompletedProcess:
    """Run sweep_stale_blues.sh against a fixture and return the completed
    process. The script reads its release image from a sibling
    `<fixture>.release.json` file when present (per spec §2.1).
    """
    fixture_path = FIXTURES / fixture_name
    return subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--input",
            str(fixture_path),
            "--expected-count",
            str(expected_count),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_fallback_fires_on_documented_shape() -> None:
    """The exact shape spec 0186's deploy hit: 4 machines, none tagged
    `safe_to_destroy`, two on an old image and two on the current image.
    The fallback should identify the two off-image machines for destroy."""
    result = _run_sweep("two_off_image_two_green.json")
    assert result.returncode == 0
    # The "destroy" log line indicates the fallback identified the right
    # number of off-image machines. The actual `fly machine destroy` call
    # is skipped in test mode (--input present), so only the log fires.
    assert "spec-0193 fallback destroying 2 machine(s)" in result.stderr
    assert "fallback destroyed 2/2" in result.stdout
    # Tag-based filter should report empty since none were tagged.
    assert "no stale blues" in result.stdout


def test_fallback_does_not_fire_when_tag_filter_handles_it() -> None:
    """When Fly does correctly tag stale blues with `safe_to_destroy`,
    the spec-0162 path handles them and the fallback is never invoked."""
    result = _run_sweep("tag_filter_handles.json")
    assert result.returncode == 0
    # Tag filter fires for the 2 tagged machines.
    assert "destroyed 2/2 stale blues" in result.stdout
    # Fallback path never triggers.
    assert "spec-0193 fallback" not in result.stderr
    assert "spec-0193 fallback" not in result.stdout


def test_fallback_refuses_when_zero_machines_on_current_image() -> None:
    """If somehow no machine is on the current release image, the fallback
    refuses to destroy anything (would zero the cluster) and dumps for
    triage. This is gate 4 from spec §2.1."""
    result = _run_sweep("no_green_present.json")
    assert result.returncode == 0
    assert "spec-0193 fallback refused — zero machines on current image" in result.stderr
    # The image identifier appears in the refusal message so a human can
    # see which release the script thought was current.
    assert "v407" in result.stderr
    # No destroy log fires.
    assert "spec-0193 fallback destroying" not in result.stderr


def test_fallback_skipped_when_current_image_undeterminable() -> None:
    """When the sibling `.release.json` file is missing (in test mode) /
    `fly releases` fails (in live mode), the fallback skips itself and
    falls through to the diagnostic dump per gate 3."""
    result = _run_sweep("no_release_file.json")
    assert result.returncode == 0
    assert "spec-0193 fallback skipped — could not determine current release image" in result.stderr
    # The metadata dump still lands so the next handoff captures evidence.
    assert '"image"' in result.stderr  # the JSON dump includes the image field
    # No destroy log fires.
    assert "spec-0193 fallback destroying" not in result.stderr


def test_cluster_at_expected_size_neither_filter_fires() -> None:
    """When the cluster is at the expected size and nothing is tagged,
    the existing 'no stale blues' line fires and the fallback is gated
    out at step 2 (oversize check)."""
    result = _run_sweep("cluster_at_expected_size.json")
    assert result.returncode == 0
    assert "no stale blues" in result.stdout
    # Fallback never engaged — no oversize log line.
    assert "spec-0193 fallback" not in result.stderr
    assert "checking image-release fallback filter" not in result.stderr


def test_script_exit_code_is_always_zero() -> None:
    """Spec 0162 invariant restated: the sweep is best-effort hygiene,
    must never fail the caller. Even on the refusal / skip paths."""
    for fixture in (
        "two_off_image_two_green.json",
        "tag_filter_handles.json",
        "no_green_present.json",
        "no_release_file.json",
        "cluster_at_expected_size.json",
    ):
        result = _run_sweep(fixture)
        assert result.returncode == 0, (
            f"sweep returned exit {result.returncode} on fixture {fixture}; "
            f"stderr: {result.stderr!r}"
        )

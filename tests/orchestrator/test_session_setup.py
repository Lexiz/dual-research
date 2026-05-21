"""Spec 0142 — session-setup ``inputs/input.json`` persistence.

The orchestrator now writes the shared Phase-0 "Initial Brief" input
bundle to disk at session setup so the hosted UI's full-view modal
(``turnKey='input'``) hydrates from a real recorded row instead of
falling through to the spec-0085 synthesis path.
"""

from __future__ import annotations

import json
from pathlib import Path

from dual_research.orchestrator.run import _persist_initial_brief_bundle


def test_persist_initial_brief_bundle_writes_input_json(tmp_path: Path) -> None:
    brief = "# Brief\n\nDo a thing.\n"
    _persist_initial_brief_bundle(tmp_path, brief)

    path = tmp_path / "inputs" / "input.json"
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))

    # System source must be "recorded" — the whole point of the spec.
    assert payload["system_source"] == "recorded"
    # Spec 0145 — the brief is round-tripped verbatim under the
    # canonical `user_prompt.message` key (replacing legacy `brief`).
    assert payload["pieces"]["user_prompt.message"] == brief
    # The system prompt is non-empty — populated via preflight_input_bundle.
    assert payload["pieces"]["system.task.input"]
    # The shared bundle is tagged as cross-agent.
    assert payload["agent"] == "shared"
    assert payload["phase"] == "phase0"


def test_persist_initial_brief_bundle_is_idempotent(tmp_path: Path) -> None:
    """A resumed run that re-invokes setup must not stomp the existing file."""
    first_brief = "# Original brief\n"
    second_brief = "# Different brief (should not land)\n"

    _persist_initial_brief_bundle(tmp_path, first_brief)
    _persist_initial_brief_bundle(tmp_path, second_brief)

    payload = json.loads((tmp_path / "inputs" / "input.json").read_text(encoding="utf-8"))
    # Spec 0145 — canonical key replaces legacy `brief`.
    assert payload["pieces"]["user_prompt.message"] == first_brief


def test_persist_initial_brief_bundle_creates_inputs_dir(tmp_path: Path) -> None:
    """Helper must mkdir the inputs/ subdir on a fresh session-dir."""
    assert not (tmp_path / "inputs").exists()
    _persist_initial_brief_bundle(tmp_path, "brief")
    assert (tmp_path / "inputs").is_dir()

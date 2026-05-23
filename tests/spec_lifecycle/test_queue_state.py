"""Happy-path tests for scripts.spec_lifecycle.queue_state (spec 0202 §2.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.spec_lifecycle.queue_state import (
    QUEUE_STATE_REL_PATH,
    SCHEMA_VERSION,
    QueueState,
    append_event_to_state,
    read_state,
    update_state,
)


def test_read_state_empty_when_file_missing(tmp_path: Path) -> None:
    state = read_state(tmp_path)
    assert state.version == SCHEMA_VERSION
    assert state.updated_at == ""
    assert state.specs == {}


def test_update_state_creates_file_and_entry(tmp_path: Path) -> None:
    update_state(tmp_path, "0202", status="in_progress", started_at="2026-05-24T12:00:00Z")
    path = tmp_path / QUEUE_STATE_REL_PATH
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["version"] == SCHEMA_VERSION
    assert data["updated_at"]  # non-empty timestamp
    assert data["specs"]["0202"]["status"] == "in_progress"
    assert data["specs"]["0202"]["started_at"] == "2026-05-24T12:00:00Z"
    assert data["specs"]["0202"]["events"] == []


def test_update_state_preserves_other_specs(tmp_path: Path) -> None:
    update_state(tmp_path, "0201", status="deployed")
    update_state(tmp_path, "0202", status="in_progress")
    state = read_state(tmp_path)
    assert set(state.specs.keys()) == {"0201", "0202"}
    assert state.specs["0201"]["status"] == "deployed"


def test_update_state_field_merging(tmp_path: Path) -> None:
    update_state(tmp_path, "0202", status="in_progress", started_at="t1")
    update_state(tmp_path, "0202", status="merged", merged_at="t2", pr="https://x")
    entry = read_state(tmp_path).specs["0202"]
    assert entry["status"] == "merged"
    assert entry["started_at"] == "t1"  # preserved
    assert entry["merged_at"] == "t2"
    assert entry["pr"] == "https://x"


def test_update_state_rejects_unknown_field(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown queue-state field"):
        update_state(tmp_path, "0202", deployed_ts="oops")


def test_update_state_allows_failure_step_none(tmp_path: Path) -> None:
    update_state(tmp_path, "0202", status="failed", failure_step="deploy")
    update_state(tmp_path, "0202", status="in_progress", failure_step=None)
    entry = read_state(tmp_path).specs["0202"]
    assert entry["status"] == "in_progress"
    assert entry["failure_step"] is None


def test_append_event_to_state(tmp_path: Path) -> None:
    append_event_to_state(
        tmp_path, "0202", "cycle_started", {}, ts="2026-05-24T12:00:00Z"
    )
    append_event_to_state(
        tmp_path, "0202", "in_progress", {"foo": "bar"}, ts="2026-05-24T12:00:30Z"
    )
    events = read_state(tmp_path).specs["0202"]["events"]
    assert len(events) == 2
    assert events[0] == {"ts": "2026-05-24T12:00:00Z", "step": "cycle_started", "data": {}}
    assert events[1] == {"ts": "2026-05-24T12:00:30Z", "step": "in_progress", "data": {"foo": "bar"}}


def test_append_event_compatible_with_legacy_jsonl_shape(tmp_path: Path) -> None:
    """The event shape (ts, step, data) matches dashboard/events/NNNN.jsonl lines
    so the renderer's stage-derivation code works against both sources (§2.4)."""
    append_event_to_state(tmp_path, "0202", "branched", {"branch": "spec/0202-foo"})
    entry = read_state(tmp_path).specs["0202"]
    ev = entry["events"][0]
    assert set(ev.keys()) == {"ts", "step", "data"}


def test_update_state_with_events_append_kwarg(tmp_path: Path) -> None:
    update_state(
        tmp_path,
        "0202",
        status="in_progress",
        events_append=[
            {"ts": "t1", "step": "cycle_started", "data": {}},
            {"ts": "t2", "step": "in_progress", "data": {}},
        ],
    )
    entry = read_state(tmp_path).specs["0202"]
    assert [e["step"] for e in entry["events"]] == ["cycle_started", "in_progress"]


def test_state_round_trips_through_json(tmp_path: Path) -> None:
    """The QueueState dataclass round-trips through the on-disk JSON form."""
    update_state(tmp_path, "0202", status="deployed", deployed_at="t1")
    on_disk = json.loads((tmp_path / QUEUE_STATE_REL_PATH).read_text())
    state = QueueState.from_json(on_disk)
    assert state.to_json() == on_disk


def test_get_spec_creates_empty_entry(tmp_path: Path) -> None:
    state = read_state(tmp_path)
    entry = state.get_spec("0202")
    assert entry == {}
    assert "0202" in state.specs


def test_cli_set_subcommand(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.spec_lifecycle.queue_state import main as cli_main

    rc = cli_main(
        ["set", "0202", "status=in_progress", "started_at=2026-05-24T12:00:00Z",
         "--repo-root", str(tmp_path)]
    )
    assert rc == 0
    entry = read_state(tmp_path).specs["0202"]
    assert entry["status"] == "in_progress"
    out = capsys.readouterr().out
    assert "updated queue-state" in out


def test_cli_set_with_null_value(tmp_path: Path) -> None:
    from scripts.spec_lifecycle.queue_state import main as cli_main

    cli_main(["set", "0202", "failure_step=deploy", "--repo-root", str(tmp_path)])
    cli_main(["set", "0202", "failure_step=null", "--repo-root", str(tmp_path)])
    entry = read_state(tmp_path).specs["0202"]
    assert entry["failure_step"] is None


def test_cli_append_event_subcommand(tmp_path: Path) -> None:
    from scripts.spec_lifecycle.queue_state import main as cli_main

    rc = cli_main(
        ["append-event", "0202", "cycle_started", "{}", "--repo-root", str(tmp_path)]
    )
    assert rc == 0
    entry = read_state(tmp_path).specs["0202"]
    assert [e["step"] for e in entry["events"]] == ["cycle_started"]


def test_cli_show_one_spec(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.spec_lifecycle.queue_state import main as cli_main

    cli_main(["set", "0202", "status=in_progress", "--repo-root", str(tmp_path)])
    capsys.readouterr()  # drop the "set" output
    rc = cli_main(["show", "0202", "--repo-root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert json.loads(out)["status"] == "in_progress"


def test_cli_show_missing_spec_returns_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from scripts.spec_lifecycle.queue_state import main as cli_main

    rc = cli_main(["show", "0999", "--repo-root", str(tmp_path)])
    assert rc == 1
    assert "no entry for 0999" in capsys.readouterr().err


def test_cli_show_full_state_when_no_spec_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from scripts.spec_lifecycle.queue_state import main as cli_main

    cli_main(["set", "0202", "status=in_progress", "--repo-root", str(tmp_path)])
    capsys.readouterr()  # drop the "set" output
    cli_main(["show", "--repo-root", str(tmp_path)])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "0202" in data["specs"]
    assert data["version"] == SCHEMA_VERSION


def test_decimal_spec_ids_round_trip(tmp_path: Path) -> None:
    """Spec 0199 decimal IDs land as string keys without modification."""
    update_state(tmp_path, "0170.1", status="queued")
    update_state(tmp_path, "0170.2", status="queued")
    update_state(tmp_path, "0170", status="deployed")
    state = read_state(tmp_path)
    assert set(state.specs.keys()) == {"0170", "0170.1", "0170.2"}


def test_file_serialised_with_trailing_newline(tmp_path: Path) -> None:
    """POSIX text files end with a newline so `git diff` doesn't grumble."""
    update_state(tmp_path, "0202", status="in_progress")
    raw = (tmp_path / QUEUE_STATE_REL_PATH).read_text()
    assert raw.endswith("\n")

"""Spec 0150 §6 — idempotency pin for the D15 (Supabase JSONB → turn_prompt_pieces) backfill.

Drives `plan_pass1` + `execute_pass1` from
`scripts/backfill_legacy_shim.py` against an in-memory Supabase fake.
After the first execute, a re-plan must return zero candidates.
"""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "backfill_legacy_shim.py"


def _load_script_module():
    import sys
    name = "backfill_legacy_shim_test_module"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script_mod():
    return _load_script_module()


# ─── Minimal Supabase fake supporting select/eq/range/execute + upsert ─


@dataclass
class _FakeResult:
    data: list[dict[str, Any]]


class _FakeQuery:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows
        self._filters: list[tuple[str, Any]] = []
        self._range: tuple[int, int] | None = None
        self._select: tuple[str, ...] = ()

    def select(self, *cols: str) -> "_FakeQuery":
        self._select = cols
        return self

    def eq(self, col: str, val: Any) -> "_FakeQuery":
        self._filters.append((col, val))
        return self

    def range(self, start: int, end: int) -> "_FakeQuery":
        self._range = (start, end)
        return self

    def execute(self) -> _FakeResult:
        rows = self._rows
        for col, val in self._filters:
            rows = [r for r in rows if r.get(col) == val]
        if self._range is not None:
            start, end = self._range
            rows = rows[start:end + 1]
        if self._select:
            rows = [
                {k: r.get(k) for k in self._select if k in r}
                for r in rows
            ]
        return _FakeResult(data=rows)


class _FakeUpsertOp:
    def __init__(self, table: "_FakeTable", rows: list[dict[str, Any]], on_conflict: str):
        self._table = table
        self._rows = rows
        self._on_conflict = on_conflict

    def execute(self) -> _FakeResult:
        keys = self._on_conflict.split(",")
        for row in self._rows:
            pk = tuple(row[k] for k in keys)
            self._table._by_pk[pk] = dict(row)
        return _FakeResult(data=[])


class _FakeTable:
    def __init__(self, name: str):
        self.name = name
        self._by_pk: dict[tuple[Any, ...], dict[str, Any]] = {}
        self._extra_rows: list[dict[str, Any]] = []

    def add_row(self, row: dict[str, Any]) -> None:
        self._extra_rows.append(row)

    @property
    def rows(self) -> list[dict[str, Any]]:
        return list(self._by_pk.values()) + list(self._extra_rows)

    def select(self, *cols: str) -> _FakeQuery:
        return _FakeQuery(self.rows).select(*cols)

    def upsert(self, rows: list[dict[str, Any]], on_conflict: str) -> _FakeUpsertOp:
        return _FakeUpsertOp(self, rows, on_conflict)


class FakeSupabase:
    def __init__(self) -> None:
        self._tables: dict[str, _FakeTable] = {}

    def table(self, name: str) -> _FakeTable:
        if name not in self._tables:
            self._tables[name] = _FakeTable(name)
        return self._tables[name]


def _seed_run_with_events(
    client: FakeSupabase,
    run_id: str,
    events_payload: list[dict[str, Any]],
) -> None:
    client.table("runs").add_row({"id": run_id})
    for payload in events_payload:
        client.table("events").add_row({
            "run_id": run_id,
            "kind": "turn_ended",
            "payload": payload,
        })


def test_idempotency_round_trip(script_mod) -> None:
    """Plan → execute → plan again. Second plan must report zero candidates."""
    client = FakeSupabase()
    _seed_run_with_events(client, "run-A", [
        {
            "agent": "claude",
            "phase": "phase2",
            "label": "phase2-r1-claude",
            "prompt_pieces": {"brief": 500, "d1": 200, "draft": 300},
        },
        {
            "agent": "openai",
            "phase": "phase2",
            "label": "phase2-r1-openai",
            "prompt_pieces": {"brief": 500, "d2": 220},
        },
    ])
    _seed_run_with_events(client, "run-B", [
        {
            "agent": "claude",
            "phase": "phase4",
            "label": "phase4-r2-claude",
            "prompt_pieces": {"draft": 400, "histp": 800},
        },
    ])

    counts1, conflicts1, rows_by_run = script_mod.plan_pass1(client)
    assert counts1.total_runs_with_turn_ended == 2
    assert counts1.runs_already_backfilled == 0
    assert counts1.runs_to_backfill == 2
    # 3 turn_pairs total: 2 from run-A, 1 from run-B.
    assert counts1.turn_pairs_to_write == 3
    # Artifact rows: run-A turn1: 3, run-A turn2: 2, run-B turn1: 2.
    assert counts1.artifact_rows_to_write == 7

    runs_w, rows_w = script_mod.execute_pass1(client, rows_by_run)
    assert runs_w == 2
    assert rows_w == 7

    # Second plan: every (run_id, turn_key, artifact_id) row already exists.
    counts2, _, _ = script_mod.plan_pass1(client)
    assert counts2.total_runs_with_turn_ended == 2
    assert counts2.runs_already_backfilled == 2
    assert counts2.runs_to_backfill == 0
    assert counts2.turn_pairs_to_write == 0
    assert counts2.artifact_rows_to_write == 0


def test_post_0145_runs_are_skipped(script_mod) -> None:
    """A run whose events already carry canonical IDs still skips on
    re-run because the first execute populated turn_prompt_pieces."""
    client = FakeSupabase()
    _seed_run_with_events(client, "run-canon", [
        {
            "agent": "claude",
            "phase": "phase2",
            "label": "phase2-r1-claude",
            "prompt_pieces": {
                "system.task.plan_negotiation": 1100,
                "user_prompt.message": 500,
                "phase1.claude": 200,
            },
        },
    ])

    counts1, _, rows_by_run = script_mod.plan_pass1(client)
    assert counts1.runs_to_backfill == 1
    assert counts1.artifact_rows_to_write == 3

    script_mod.execute_pass1(client, rows_by_run)

    counts2, _, _ = script_mod.plan_pass1(client)
    assert counts2.runs_to_backfill == 0


def test_translated_rows_carry_attachment_id(script_mod) -> None:
    """Rows for `user_prompt.attachment.<id>` artifact IDs get the
    attachment_id column parsed out of the artifact ID."""
    client = FakeSupabase()
    _seed_run_with_events(client, "run-att", [
        {
            "agent": "claude",
            "phase": "phase0",
            "label": "phase0-r1-claude",
            "prompt_pieces": {
                "user_prompt.message": 500,
                "user_prompt.attachment.abc12345": 250,
            },
        },
    ])

    _, _, rows_by_run = script_mod.plan_pass1(client)
    rows = rows_by_run["run-att"]
    att_rows = [r for r in rows if r["artifact_id"].startswith("user_prompt.attachment.")]
    assert len(att_rows) == 1
    assert att_rows[0]["attachment_id"] == "abc12345"
    msg_rows = [r for r in rows if r["artifact_id"] == "user_prompt.message"]
    assert len(msg_rows) == 1
    assert msg_rows[0]["attachment_id"] is None


def test_run_without_turn_ended_events_is_silently_skipped(script_mod) -> None:
    """A run that exists but has no `turn_ended` events doesn't count
    as a candidate (the historical row population is intentional —
    crash-before-first-turn shouldn't pollute the counts)."""
    client = FakeSupabase()
    client.table("runs").add_row({"id": "run-empty"})
    counts, _, rows_by_run = script_mod.plan_pass1(client)
    assert counts.total_runs_with_turn_ended == 0
    assert rows_by_run == {}


def test_missing_phase_with_system_key_is_flagged(script_mod) -> None:
    """Events with `system` in prompt_pieces but no parseable phase
    field bump the events_with_missing_phase counter — operator
    surface from §5.2."""
    client = FakeSupabase()
    _seed_run_with_events(client, "run-no-phase", [
        {
            "agent": "claude",
            "phase": "garbage",  # parse_phase_num returns None
            "label": "phase2-r1-claude",
            "prompt_pieces": {"system": 1000, "brief": 500},
        },
    ])
    counts, _, _ = script_mod.plan_pass1(client)
    assert counts.events_with_missing_phase == 1


def test_limit_caps_runs_processed(script_mod) -> None:
    """The --limit flag clamps the number of candidate runs processed
    so an incremental rollout is possible."""
    client = FakeSupabase()
    for n in range(5):
        _seed_run_with_events(client, f"run-{n}", [
            {
                "agent": "claude",
                "phase": "phase2",
                "label": "phase2-r1-claude",
                "prompt_pieces": {"brief": 500},
            },
        ])

    counts, _, rows_by_run = script_mod.plan_pass1(client, limit=2)
    assert counts.runs_to_backfill == 2
    assert len(rows_by_run) == 2

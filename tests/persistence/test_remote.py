"""Unit tests for the Supabase push client (spec 0019).

The supabase-py client is replaced with an in-memory fake that records every
upsert call. This lets us verify push behaviour without depending on a live
Supabase project — see the integration tests in test_remote_integration.py
(gated by env vars) for end-to-end coverage.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dual_research.config import (
    MissingCredentialError,
    SupabaseCredentials,
    load_supabase_credentials,
)
from dual_research.persistence.remote import RemoteSession


class _FakeExecute:
    def __init__(self, parent: "_FakeTable", op: str, rows: list[dict[str, Any]], on_conflict: str):
        self._parent = parent
        self._op = op
        self._rows = rows
        self._on_conflict = on_conflict

    def execute(self) -> "_FakeExecute":
        self._parent.record_upsert(self._rows, self._on_conflict)
        return self


class _FakeUpdateBuilder:
    """Records a ``table(...).update({...}).eq(col, val).execute()`` chain.

    Spec 0252.2 — ``push_metrics_only`` issues a single-row update of the
    ``runs.metrics`` column via this builder shape (mirroring supabase-py's
    ``table().update().eq().execute()``). The fake records the values and the
    accumulated ``.eq()`` filters so tests can assert both the payload and the
    id filter without a live Supabase.
    """

    def __init__(self, parent: "_FakeTable", values: dict[str, Any]):
        self._parent = parent
        self._values = values
        self._filters: list[tuple[str, Any]] = []

    def eq(self, column: str, value: Any) -> "_FakeUpdateBuilder":
        self._filters.append((column, value))
        return self

    def execute(self) -> "_FakeUpdateBuilder":
        self._parent.record_update(self._values, self._filters)
        return self


class _FakeTable:
    def __init__(self, name: str, store: dict[tuple[Any, ...], dict[str, Any]]):
        self._name = name
        self._store = store
        self.calls: list[tuple[int, str]] = []  # (rows_inserted_or_replaced, on_conflict)
        # Spec 0252.2 — recorded (values, filters) per update().eq().execute().
        self.updates: list[tuple[dict[str, Any], list[tuple[str, Any]]]] = []

    def upsert(self, rows: list[dict[str, Any]], on_conflict: str) -> _FakeExecute:
        return _FakeExecute(self, "upsert", rows, on_conflict)

    def update(self, values: dict[str, Any]) -> _FakeUpdateBuilder:
        return _FakeUpdateBuilder(self, values)

    def record_upsert(self, rows: list[dict[str, Any]], on_conflict: str) -> None:
        keys = on_conflict.split(",")
        for row in rows:
            pk = tuple(row[k] for k in keys)
            self._store[pk] = row
        self.calls.append((len(rows), on_conflict))

    def record_update(
        self, values: dict[str, Any], filters: list[tuple[str, Any]]
    ) -> None:
        self.updates.append((values, filters))


class FakeSupabaseClient:
    def __init__(self) -> None:
        self.tables: dict[str, dict[tuple[Any, ...], dict[str, Any]]] = {}
        self._table_objs: dict[str, _FakeTable] = {}

    def table(self, name: str) -> _FakeTable:
        if name not in self.tables:
            self.tables[name] = {}
            self._table_objs[name] = _FakeTable(name, self.tables[name])
        return self._table_objs[name]

    def rows(self, table: str) -> list[dict[str, Any]]:
        return list(self.tables.get(table, {}).values())


def _make_session_dir(
    root: Path,
    *,
    id: str = "20260515-163105-live-integration-test",
    with_transcript: bool = True,
    with_final: bool = True,
    with_metrics: bool = True,
) -> Path:
    sd = root / id
    sd.mkdir(parents=True)
    (sd / "state.json").write_text(
        json.dumps(
            {
                "phase": "final",
                "drafter": "claude",
                "agreed_plan": "(redacted)",
                "final_surfaced_disagreements": [],
                "draft_round": 1,
                "final_emitted_to": None,
            }
        )
    )
    if with_metrics:
        (sd / "metrics.json").write_text(
            json.dumps(
                {
                    "started_at": "2026-05-15T16:31:05+00:00",
                    "ended_at": "2026-05-15T16:44:48+00:00",
                    "calls": [],
                    "totals_by_agent": {},
                    "total_cost_usd": 0.4228,
                }
            )
        )
    (sd / "brief.md").write_text("# Brief\n\nCompare X to Y.")
    if with_transcript:
        lines = [
            json.dumps({
                "ts": "2026-05-15T16:31:05+00:00",
                "event": "run_started",
                "session_dir": str(sd),
                "slug": "live-integration-test",
                "model_tier": "test",
                "claude_model": "claude-haiku-4-5",
                "openai_model": "gpt-5-mini",
                "soft_cap": 3,
                "hard_cap": 5,
            }),
            json.dumps({"ts": "2026-05-15T16:31:06+00:00", "event": "phase_entered", "phase": "phase0"}),
            json.dumps({"ts": "2026-05-15T16:31:42+00:00", "event": "turn_ended", "agent": "claude", "cost_usd": 0.012}),
            json.dumps({
                "ts": "2026-05-15T16:44:48+00:00",
                "event": "run_completed",
                "phase_reached": "done",
                "exit_code": 0,
                "total_cost_usd": 0.4228,
                "duration_ms": 772800,
            }),
        ]
        (sd / "transcript.jsonl").write_text("\n".join(lines) + "\n")
    phase2 = sd / "phase2"
    phase2.mkdir()
    (phase2 / "round-01-claude.md").write_text("# Round 1\n\nClaude content.")
    (phase2 / "round-01-openai.md").write_text("# Round 1\n\nOpenAI content.")
    if with_final:
        (sd / "final.md").write_text(
            "> ## How this document was produced\n"
            ">\n"
            "> Two agents (`claude-haiku-4-5` and `gpt-5-mini`) co-authored this.\n"
            ">\n"
            "> Read with **MODERATE confidence**.\n"
            "\n# Body\n\nConverged content here.\n"
        )
    return sd


def test_push_inserts_run_event_and_file_rows(tmp_path: Path) -> None:
    sd = _make_session_dir(tmp_path)
    fake = FakeSupabaseClient()
    summary = RemoteSession(fake).push_session_dir(sd)

    assert summary.runs_upserted == 1
    assert summary.events_upserted == 4
    assert summary.files_upserted >= 5

    runs = fake.rows("runs")
    assert len(runs) == 1
    run = runs[0]
    assert run["id"] == "20260515-163105-live-integration-test"
    assert run["slug"] == "live-integration-test"
    # phase_reached comes from run_completed (canonical), not state.phase.
    assert run["phase_reached"] == "done"
    assert run["exit_code"] == 0
    assert run["confidence"] == "MODERATE"
    assert run["model_tier"] == "test"
    assert run["claude_model"] == "claude-haiku-4-5"
    assert run["openai_model"] == "gpt-5-mini"
    assert run["total_cost_usd"] == 0.4228
    # run_completed.duration_ms wins over metrics-derived duration when present.
    assert run["duration_ms"] == 772_800

    events = fake.rows("events")
    assert [e["seq"] for e in events] == [0, 1, 2, 3]
    assert [e["kind"] for e in events] == [
        "run_started",
        "phase_entered",
        "turn_ended",
        "run_completed",
    ]
    assert events[2]["payload"]["agent"] == "claude"
    assert "ts" not in events[2]["payload"]  # ts is hoisted to a top-level column
    assert "event" not in events[2]["payload"]  # kind hoisted too

    files = {f["path"] for f in fake.rows("session_files")}
    assert "brief.md" in files
    assert "state.json" in files
    assert "metrics.json" in files
    assert "phase2/round-01-claude.md" in files
    assert "phase2/round-01-openai.md" in files
    assert "final.md" in files
    assert "transcript.jsonl" in files


def test_repush_replaces_not_duplicates(tmp_path: Path) -> None:
    sd = _make_session_dir(tmp_path)
    fake = FakeSupabaseClient()
    RemoteSession(fake).push_session_dir(sd)
    runs_before = len(fake.rows("runs"))
    events_before = len(fake.rows("events"))
    files_before = len(fake.rows("session_files"))

    RemoteSession(fake).push_session_dir(sd)
    assert len(fake.rows("runs")) == runs_before == 1
    assert len(fake.rows("events")) == events_before
    assert len(fake.rows("session_files")) == files_before


def test_run_failed_event_sets_exit_code_so_list_view_shows_errored(tmp_path: Path) -> None:
    """Regression for the 2026-05-20 list-vs-detail status mismatch.

    A run that ended via ``run_failed`` (not ``run_completed``) used to push
    with ``exit_code=None``. The list view's ``_status_from_columns``
    reads ``exit_code`` to decide errored / deadlocked / completed, so
    ``None`` fell through to the default "running" — even though the
    detail view (which materializes the transcript and runs the aggregator)
    correctly showed "errored". The fix synthesises ``exit_code=1`` from
    the ``run_failed`` event so the runs row carries the terminal signal."""
    sd = tmp_path / "20260520-141001-dvs-backend-language-choice"
    sd.mkdir()
    # Minimal state.json — like a real session-dir for a run that died in phase1.
    (sd / "state.json").write_text(json.dumps({
        "phase": "phase1",
        "drafter": None,
        "agreed_plan": None,
        "final_surfaced_disagreements": [],
        "draft_round": 1,
        "final_emitted_to": None,
    }))
    (sd / "brief.md").write_text("# Brief\n\nTesting.")
    # Transcript carrying a run_failed event (no run_completed).
    lines = [
        json.dumps({
            "ts": "2026-05-20T14:10:01+00:00",
            "event": "run_started",
            "session_dir": str(sd),
            "slug": "dvs-backend-language-choice",
            "model_tier": "prod",
            "claude_model": "claude-sonnet-4-6",
            "openai_model": "gpt-5.5",
            "soft_cap": 6,
            "hard_cap": 12,
        }),
        json.dumps({"ts": "2026-05-20T14:10:02+00:00", "event": "phase_entered", "phase": "phase0"}),
        json.dumps({
            "ts": "2026-05-20T14:36:25+00:00",
            "event": "run_failed",
            "phase_reached": "phase1",
            "error_type": "ReadError",
            "message": "",
        }),
    ]
    (sd / "transcript.jsonl").write_text("\n".join(lines) + "\n")

    fake = FakeSupabaseClient()
    RemoteSession(fake).push_session_dir(sd)
    runs = fake.rows("runs")
    assert len(runs) == 1
    row = runs[0]
    # exit_code must be a non-zero, non-51 value so derive_run_status returns
    # "errored" via _status_from_columns. The exact value isn't part of the
    # contract — only the presence of a "this run failed" signal is.
    assert row["exit_code"] is not None
    assert row["exit_code"] not in (0, 51)
    # phase_reached comes from the run_failed event payload.
    assert row["phase_reached"] == "phase1"


def test_missing_state_json_is_tolerated_and_pushes_in_flight_row(tmp_path: Path) -> None:
    """Spec 0032 regression — a session dir without state.json must still
    push (with default state.phase="phase0"), so --push-while-running can
    publish in-flight runs whose orchestrator hasn't yet reached its
    first phase-boundary save. Previously this raised FileNotFoundError
    and every tick failed for the entire phase-0 window."""
    sd = tmp_path / "20260515-163105-in-flight"
    sd.mkdir()
    (sd / "brief.md").write_text("just a brief")
    fake = FakeSupabaseClient()
    summary = RemoteSession(fake).push_session_dir(sd)
    assert summary.runs_upserted == 1
    runs = fake.rows("runs")
    assert len(runs) == 1
    assert runs[0]["id"] == "20260515-163105-in-flight"
    # No state.json on disk → default state.phase="phase0" supplies
    # phase_reached, so the hosted UI sees a "running, phase0" row.
    assert runs[0]["phase_reached"] == "phase0"
    assert runs[0]["state"] == {"phase": "phase0"}


def test_missing_transcript_pushes_zero_events(tmp_path: Path) -> None:
    sd = _make_session_dir(tmp_path, with_transcript=False)
    fake = FakeSupabaseClient()
    summary = RemoteSession(fake).push_session_dir(sd)
    assert summary.events_upserted == 0
    assert len(fake.rows("runs")) == 1
    assert fake.rows("events") == []


def test_empty_transcript_lines_are_skipped(tmp_path: Path) -> None:
    sd = _make_session_dir(tmp_path)
    transcript = sd / "transcript.jsonl"
    transcript.write_text(transcript.read_text() + "\n\n   \n")
    fake = FakeSupabaseClient()
    summary = RemoteSession(fake).push_session_dir(sd)
    assert summary.events_upserted == 4  # 4 real events, blank lines ignored


def test_duration_ms_is_null_when_no_source_provides_it(tmp_path: Path) -> None:
    sd = _make_session_dir(tmp_path, with_transcript=False)
    (sd / "metrics.json").write_text(
        json.dumps({"started_at": "2026-05-15T16:31:05+00:00", "ended_at": None, "calls": []})
    )
    fake = FakeSupabaseClient()
    RemoteSession(fake).push_session_dir(sd)
    assert fake.rows("runs")[0]["duration_ms"] is None


def test_no_metrics_file_still_pushes(tmp_path: Path) -> None:
    sd = _make_session_dir(tmp_path, with_metrics=False)
    fake = FakeSupabaseClient()
    RemoteSession(fake).push_session_dir(sd)
    run = fake.rows("runs")[0]
    assert run["metrics"] is None
    # duration_ms and total_cost_usd still come from run_completed in the transcript.
    assert run["duration_ms"] == 772_800
    assert run["total_cost_usd"] == 0.4228


def test_no_final_md_means_null_confidence(tmp_path: Path) -> None:
    sd = _make_session_dir(tmp_path, with_final=False)
    fake = FakeSupabaseClient()
    RemoteSession(fake).push_session_dir(sd)
    run = fake.rows("runs")[0]
    # Confidence comes from final.md prose — null without it.
    assert run["confidence"] is None
    # Models still resolved from the run_started transcript event.
    assert run["model_tier"] == "test"
    assert run["claude_model"] == "claude-haiku-4-5"
    assert run["openai_model"] == "gpt-5-mini"


def test_no_transcript_clears_model_fields_and_exit_code(tmp_path: Path) -> None:
    sd = _make_session_dir(tmp_path, with_transcript=False, with_final=False)
    fake = FakeSupabaseClient()
    RemoteSession(fake).push_session_dir(sd)
    run = fake.rows("runs")[0]
    assert run["model_tier"] is None
    assert run["claude_model"] is None
    assert run["openai_model"] is None
    assert run["exit_code"] is None
    assert run["confidence"] is None


def test_hidden_atomic_tempfiles_are_skipped(tmp_path: Path) -> None:
    sd = _make_session_dir(tmp_path)
    # Atomic-write detritus from `write_atomic` (dotfile in same dir as target).
    (sd / ".state.json.abc123").write_text("garbage")
    fake = FakeSupabaseClient()
    RemoteSession(fake).push_session_dir(sd)
    file_paths = {f["path"] for f in fake.rows("session_files")}
    assert not any(p.startswith(".") for p in file_paths)


def test_malformed_session_dir_name_raises(tmp_path: Path) -> None:
    sd = _make_session_dir(tmp_path, id="not-a-timestamp")
    fake = FakeSupabaseClient()
    with pytest.raises(ValueError, match="YYYYMMDD-HHMMSS"):
        RemoteSession(fake).push_session_dir(sd)


def test_attachments_json_and_blobs_are_pushed(tmp_path: Path) -> None:
    """Spec 0025 — `attachments.json` flows through session_files (as a
    `.json` artifact) and binary files under `<session>/attachments/`
    are upserted into the `attachment_blobs` table base64-encoded.
    """
    import base64

    sd = _make_session_dir(tmp_path)
    # Write the metadata index — picked up by SESSION_FILE_GLOBS automatically.
    (sd / "attachments.json").write_text(
        json.dumps({"attachments": [{"kind": "image", "source": "cli:foo.png",
                                      "rel_path": "attachments/abc-foo.png"}]}),
        encoding="utf-8",
    )
    att_dir = sd / "attachments"
    att_dir.mkdir()
    (att_dir / "abc-foo.png").write_bytes(b"\x89PNG-binary-data")
    (att_dir / "xyz-bar.pdf").write_bytes(b"%PDF-1.4")

    fake = FakeSupabaseClient()
    summary = RemoteSession(fake).push_session_dir(sd)

    assert summary.blobs_upserted == 2
    files = {f["path"] for f in fake.rows("session_files")}
    assert "attachments.json" in files
    # Binary blobs land in attachment_blobs, not session_files.
    blob_paths = {b["rel_path"] for b in fake.rows("attachment_blobs")}
    assert blob_paths == {"attachments/abc-foo.png", "attachments/xyz-bar.pdf"}
    png_row = next(b for b in fake.rows("attachment_blobs")
                   if b["rel_path"] == "attachments/abc-foo.png")
    assert png_row["mime"] == "image/png"
    assert png_row["size_bytes"] == len(b"\x89PNG-binary-data")
    assert base64.b64decode(png_row["content_b64"]) == b"\x89PNG-binary-data"


def test_attachments_directory_missing_pushes_zero_blobs(tmp_path: Path) -> None:
    """A run without any attachments still pushes cleanly — no rows in
    attachment_blobs, no errors."""
    sd = _make_session_dir(tmp_path)
    fake = FakeSupabaseClient()
    summary = RemoteSession(fake).push_session_dir(sd)
    assert summary.blobs_upserted == 0
    assert fake.rows("attachment_blobs") == []


def test_event_batching_respects_batch_size(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Force a tiny batch to verify chunking without writing 500+ events.
    from dual_research.persistence import remote

    monkeypatch.setattr(remote, "EVENT_BATCH_SIZE", 2)
    sd = _make_session_dir(tmp_path)
    fake = FakeSupabaseClient()
    RemoteSession(fake).push_session_dir(sd)
    # 4 events with batch size 2 → 2 upsert calls (sizes 2 + 2).
    events_table = fake.table("events")
    assert events_table.calls == [(2, "run_id,seq"), (2, "run_id,seq")]


# --- Supabase credential loader ---------------------------------------------


def test_load_supabase_credentials_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_publishable_x")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "sb_secret_y")
    creds = load_supabase_credentials()
    assert creds == SupabaseCredentials(
        url="https://abc.supabase.co",
        anon_key="sb_publishable_x",
        service_role_key="sb_secret_y",
    )


def test_load_supabase_credentials_rejects_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(MissingCredentialError) as ctx:
        load_supabase_credentials()
    msg = str(ctx.value)
    assert "SUPABASE_URL" in msg
    assert "SUPABASE_ANON_KEY" in msg
    assert "SUPABASE_SERVICE_ROLE_KEY" in msg


def test_load_supabase_credentials_partial_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://abc.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "sb_publishable_x")
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    with pytest.raises(MissingCredentialError, match="SUPABASE_SERVICE_ROLE_KEY"):
        load_supabase_credentials()


# ─── Spec 0252.2 — backfill-critique metrics-only push ────────────────────────
#
# The captured live failure was `backfill-critique --all --push` →
# push_session_dir → a Supabase 57014 statement timeout on the heavy
# events/files/blobs/pieces re-upload. The fix routes the backfill --push block
# through push_metrics_only, which issues a single-row update of runs.metrics and
# touches none of those four tables. Per spec 0238, the real-entry-point test
# below drives the CLI `_run_backfill_critique` --push path (not a helper in
# isolation) so a fix on the wrong function cannot pass.

_HEAVY_TABLES = ("events", "session_files", "attachment_blobs", "turn_prompt_pieces")


def test_push_metrics_only_updates_runs_column_and_skips_heavy_tables(tmp_path: Path) -> None:
    sd = _make_session_dir(tmp_path)
    fake = FakeSupabaseClient()

    summary = RemoteSession(fake).push_metrics_only(sd)

    assert summary.ok is True
    assert summary.run_id == "20260515-163105-live-integration-test"

    # A single update on runs, filtered to the run id via .eq("id", <run_id>).
    runs_updates = fake.table("runs").updates
    assert len(runs_updates) == 1
    _values, filters = runs_updates[0]
    assert filters == [("id", "20260515-163105-live-integration-test")]

    # The four heavy tables the 57014 timeout came from are never touched —
    # FakeSupabaseClient creates a table entry lazily on first `.table(name)`,
    # so their absence from `fake.tables` proves push_metrics_only never reached
    # them. (push_session_dir, by contrast, would populate events/session_files.)
    for table in _HEAVY_TABLES:
        assert table not in fake.tables, f"metrics-only push must not touch {table}"
    # And no upsert was issued on runs either — it's an update, not a re-push.
    assert fake.table("runs").calls == []


def test_push_metrics_only_payload_is_metrics_json_verbatim(tmp_path: Path) -> None:
    """Payload fidelity: the deployed card must read exactly what the backfill
    wrote, including the populated critique_by_agent sub-dict."""
    sd = tmp_path / "20260518-065852-backend-language-choice-briefing"
    sd.mkdir()
    metrics_payload = {
        "started_at": "2026-05-18T06:58:52+00:00",
        "ended_at": "2026-05-18T07:40:11+00:00",
        "calls": [],
        "totals_by_agent": {},
        "total_cost_usd": 8.66,
        "critique_by_agent": {
            "claude": {"questions": 5, "disagreements": 3, "issues": 2, "comments": 7},
            "openai": {"questions": 4, "disagreements": 1, "issues": 0, "comments": 9},
        },
    }
    (sd / "metrics.json").write_text(json.dumps(metrics_payload), encoding="utf-8")
    fake = FakeSupabaseClient()

    RemoteSession(fake).push_metrics_only(sd)

    values, filters = fake.table("runs").updates[0]
    assert values == {"metrics": metrics_payload}
    assert values["metrics"]["critique_by_agent"]["claude"]["questions"] == 5
    assert filters == [("id", "20260518-065852-backend-language-choice-briefing")]


def test_push_metrics_only_missing_metrics_raises(tmp_path: Path) -> None:
    sd = _make_session_dir(tmp_path, with_metrics=False)
    with pytest.raises(FileNotFoundError):
        RemoteSession(FakeSupabaseClient()).push_metrics_only(sd)


def test_backfill_critique_push_routes_through_metrics_only_not_full_repush(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real-entry-point regression for the captured 57014 (spec 0238 discipline).

    Drives the actual CLI `_run_backfill_critique` --push path — the exact
    call site that emitted the live `[push error] ... 57014` — against a fixture
    run with a mocked Supabase client. Before the fix the block called
    push_session_dir, which re-uploads events/session_files/etc.; after the fix
    it calls push_metrics_only, which issues only a runs.metrics update. The
    assertions fail on the pre-fix shape (heavy tables populated) and pass on the
    post-fix shape (heavy tables untouched, runs updated by id)."""
    from dual_research import config as config_mod
    from dual_research.cli import _run_backfill_critique
    from dual_research.persistence import remote as remote_mod

    run_id = "20260518-083618-backend-language-choice"
    _make_session_dir(tmp_path, id=run_id)

    fake = FakeSupabaseClient()
    monkeypatch.setattr(
        config_mod,
        "load_supabase_credentials",
        lambda: SupabaseCredentials(url="https://x.supabase.co", anon_key="a", service_role_key="s"),
    )
    monkeypatch.setattr(
        remote_mod.RemoteSession,
        "from_credentials",
        lambda url, service_role_key: RemoteSession(fake),
    )

    rc = _run_backfill_critique(["--run", run_id, "--push", "--runs-dir", str(tmp_path)])

    assert rc == 0
    # The repair reached Supabase as a single runs.metrics update filtered by id.
    runs_updates = fake.table("runs").updates
    assert len(runs_updates) == 1
    assert runs_updates[0][1] == [("id", run_id)]
    # None of the heavy tables that timed out were touched.
    for table in _HEAVY_TABLES:
        assert table not in fake.tables, f"backfill --push must not re-upload {table}"

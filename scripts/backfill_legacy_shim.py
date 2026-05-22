#!/usr/bin/env python3
"""Spec 0150 — backfill historical runs into the canonical schema.

Two passes:

  1. **(D15)** Read ``events.payload.prompt_pieces`` JSONB on Supabase for
     every run with at least one ``turn_ended`` event. Translate any
     legacy short keys (``system``, ``brief``, ``d1``, ...) to canonical
     artifact IDs and upsert one row per ``(artifact_id, tokens)`` pair
     into ``turn_prompt_pieces``. Idempotent: pairs that already exist
     are no-ops via the upsert's ``on_conflict`` clause.

  2. **(D05)** Walk ``runs/*/`` on the local filesystem. For each
     session-dir that has ``brief.md`` AND lacks ``inputs/input.json``,
     call ``_persist_initial_brief_bundle()`` to write the canonical
     bundle, then ``--push`` the session-dir to Supabase so the hosted
     UI's Initial-Brief modal sees ``system_source="recorded"`` instead
     of the synth-path ``"agent-default"`` caveat. Idempotent.

Flags::

    --dry-run     enumerate work but write nothing
    --pass=1      D15 only (Supabase JSONB → turn_prompt_pieces)
    --pass=2      D05 only (local input.json backfill + push)
    --limit=N     process at most N runs in the pass (incremental rollout)
    --runs-dir P  override the runs directory (default: ./runs)
    --no-push     pass-2 only: write inputs/input.json locally but skip
                  the dual-research --push step. Useful when running
                  pass-2 without Supabase credentials available.

Translation policy (D15):

  Each ``turn_ended`` event's ``prompt_pieces`` dict carries a mix of
  short and canonical keys depending on when the run was emitted. The
  translation table below mirrors ``LEGACY_KEY_TO_CANONICAL`` in
  ``src/dual_research/ui/static/artifacts.jsx`` exactly. For the
  phase-aware ``system`` key, the phase field on the event payload
  ("phase0".."phase4") resolves to the matching ``system.task.<phase>``
  canonical sibling.

  When BOTH a legacy key and its canonical sibling appear in the same
  dict, the canonical wins (prefer-canonical policy). The legacy
  count is silently dropped. The dry-run output flags any conflicting
  pair (legacy=X tokens, canonical=Y tokens, X != Y) so the operator
  can spot-check before the execute pass.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator


# Mirror of `LEGACY_KEY_TO_CANONICAL` in artifacts.jsx:169-178.
# The pin test in tests/scripts/test_backfill_legacy_shim_spec_0150.py
# asserts this table matches the JS source verbatim.
LEGACY_KEY_TO_CANONICAL: dict[str, str] = {
    "system": "system.task.input",  # phase-specific; see LEGACY_SYSTEM_BY_PHASE
    "brief":  "user_prompt.message",
    "d1":     "phase1.claude",
    "d2":     "phase1.openai",
    "plan":   "phase2.agreement.plan",
    "hist":   "prior_turns.phase2",
    "draft":  "current_draft",
    "histp":  "prior_turns.phase4",
}

# Mirror of `LEGACY_SYSTEM_BY_PHASE` in artifacts.jsx:185-191.
LEGACY_SYSTEM_BY_PHASE: dict[int, str] = {
    0: "system.task.input",
    1: "system.task.research_plan",
    2: "system.task.plan_negotiation",
    3: "system.task.drafting",
    4: "system.task.review",
}


def canonicalise_legacy_key(legacy_key: str, phase_num: int | None) -> str:
    """Translate a legacy short key to its canonical artifact ID.

    Mirrors ``canonicaliseLegacyKey`` in artifacts.jsx. Unknown keys
    (including already-canonical dotted IDs) pass through unchanged.
    """
    if not isinstance(legacy_key, str) or not legacy_key:
        return legacy_key
    if legacy_key == "system" and phase_num is not None:
        return LEGACY_SYSTEM_BY_PHASE.get(phase_num, "system.task.input")
    return LEGACY_KEY_TO_CANONICAL.get(legacy_key, legacy_key)


def parse_phase_num(phase_field: str) -> int | None:
    """Extract phase number from the event payload's ``phase`` string.

    Accepts the canonical ``"phase0"``..``"phase4"`` form and the bare
    integer-string form ``"0"``..``"4"``. Returns None on any other shape.
    """
    if not isinstance(phase_field, str) or not phase_field:
        return None
    s = phase_field.strip().lower()
    if s.startswith("phase") and len(s) >= 6:
        try:
            n = int(s[5:])
        except ValueError:
            return None
        return n if 0 <= n <= 4 else None
    try:
        n = int(s)
    except ValueError:
        return None
    return n if 0 <= n <= 4 else None


@dataclass(frozen=True)
class TranslatedPiece:
    artifact_id: str
    tokens: int
    came_from_legacy: bool
    original_key: str


@dataclass
class TranslationConflict:
    run_id: str
    turn_key: str
    legacy_key: str
    canonical_key: str
    legacy_tokens: int
    canonical_tokens: int


def translate_prompt_pieces(
    prompt_pieces: dict[str, Any],
    phase_num: int | None,
    *,
    conflicts: list[TranslationConflict] | None = None,
    run_id: str = "",
    turn_key: str = "",
) -> dict[str, int]:
    """Map a (possibly legacy-keyed) prompt_pieces dict to canonical IDs.

    Policy: prefer canonical when both a legacy key and its canonical
    sibling are present in the same dict. If ``conflicts`` is provided
    AND the two source tokens disagree, append a record to the list so
    the dry-run can surface it.

    Returns a new dict with canonical keys only.
    """
    out: dict[str, int] = {}
    legacy_seen: dict[str, int] = {}

    # First pass: capture every key's intent.
    canonical_present: set[str] = set()
    for k, raw in (prompt_pieces or {}).items():
        try:
            tokens = int(raw)
        except (TypeError, ValueError):
            continue
        if k in LEGACY_KEY_TO_CANONICAL:
            legacy_seen[k] = tokens
        else:
            canonical_present.add(k)
            out[k] = tokens

    # Second pass: translate legacy keys, deferring to canonical when present.
    for legacy_key, legacy_tokens in legacy_seen.items():
        canon = canonicalise_legacy_key(legacy_key, phase_num)
        if canon in canonical_present:
            if conflicts is not None and out.get(canon, 0) != legacy_tokens:
                conflicts.append(TranslationConflict(
                    run_id=run_id,
                    turn_key=turn_key,
                    legacy_key=legacy_key,
                    canonical_key=canon,
                    legacy_tokens=legacy_tokens,
                    canonical_tokens=out.get(canon, 0),
                ))
            continue
        out[canon] = legacy_tokens

    return out


# ─── Pass 1 (D15) — Supabase JSONB → turn_prompt_pieces ────────────────


@dataclass
class Pass1Counts:
    total_runs_with_turn_ended: int = 0
    runs_already_backfilled: int = 0
    runs_to_backfill: int = 0
    turn_pairs_to_write: int = 0
    artifact_rows_to_write: int = 0
    events_with_missing_phase: int = 0
    translation_conflicts: int = 0


def _load_existing_piece_run_ids(client: Any) -> set[str]:
    """Run IDs that already have at least one row in turn_prompt_pieces.

    Idempotency anchor: any run in this set is skipped on the execute
    pass (and counted as 'already_backfilled' on the dry-run).
    """
    out: set[str] = set()
    page_size = 1000
    offset = 0
    while True:
        res = (
            client.table("turn_prompt_pieces")
            .select("run_id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = (res.data if res else None) or []
        if not rows:
            break
        for r in rows:
            rid = r.get("run_id")
            if rid:
                out.add(rid)
        if len(rows) < page_size:
            break
        offset += page_size
    return out


def _iter_run_ids(client: Any) -> Iterator[str]:
    """All run IDs on the runs table, paginated."""
    page_size = 1000
    offset = 0
    while True:
        res = (
            client.table("runs")
            .select("id")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = (res.data if res else None) or []
        if not rows:
            return
        for r in rows:
            rid = r.get("id")
            if rid:
                yield rid
        if len(rows) < page_size:
            return
        offset += page_size


def _iter_turn_ended_events_for_run(
    client: Any, run_id: str
) -> Iterator[dict[str, Any]]:
    """All turn_ended event rows for the given run, paginated."""
    page_size = 1000
    offset = 0
    while True:
        res = (
            client.table("events")
            .select("payload")
            .eq("run_id", run_id)
            .eq("kind", "turn_ended")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = (res.data if res else None) or []
        if not rows:
            return
        for r in rows:
            yield r
        if len(rows) < page_size:
            return
        offset += page_size


def _derive_turn_key_from_payload(payload: dict[str, Any]) -> str | None:
    """Reuse the orchestrator's `_derive_turn_key` against the event payload."""
    from dual_research.orchestrator._call import _derive_turn_key

    agent_label = payload.get("agent") or ""
    phase = payload.get("phase") or ""
    label = payload.get("label") or ""
    if not (agent_label and phase and label):
        return None
    return _derive_turn_key(agent_label=agent_label, phase=phase, label=label)


def plan_pass1(
    client: Any,
    *,
    limit: int | None = None,
) -> tuple[
    Pass1Counts,
    list[TranslationConflict],
    dict[str, list[dict[str, Any]]],
]:
    """Compute the dry-run plan for pass 1. Returns counts, conflicts,
    and (for the execute path) the per-run row payloads ready to upsert."""
    counts = Pass1Counts()
    conflicts: list[TranslationConflict] = []
    rows_by_run: dict[str, list[dict[str, Any]]] = {}

    existing_run_ids = _load_existing_piece_run_ids(client)
    processed = 0

    for run_id in _iter_run_ids(client):
        if limit is not None and processed >= limit:
            break
        # Probe one turn_ended event before committing to the per-run scan.
        events = list(_iter_turn_ended_events_for_run(client, run_id))
        if not events:
            continue
        counts.total_runs_with_turn_ended += 1
        if run_id in existing_run_ids:
            counts.runs_already_backfilled += 1
            continue
        counts.runs_to_backfill += 1
        processed += 1

        per_run_rows: list[dict[str, Any]] = []
        for ev in events:
            payload = ev.get("payload") or {}
            pieces = payload.get("prompt_pieces") or {}
            if not pieces:
                continue
            turn_key = _derive_turn_key_from_payload(payload)
            if turn_key is None:
                continue
            phase_num = parse_phase_num(payload.get("phase") or "")
            if any(k == "system" for k in pieces) and phase_num is None:
                counts.events_with_missing_phase += 1
            translated = translate_prompt_pieces(
                pieces,
                phase_num,
                conflicts=conflicts,
                run_id=run_id,
                turn_key=turn_key,
            )
            if not translated:
                continue
            counts.turn_pairs_to_write += 1
            for artifact_id, tokens in translated.items():
                attachment_id: str | None = None
                if artifact_id.startswith("user_prompt.attachment."):
                    attachment_id = artifact_id[len("user_prompt.attachment."):]
                per_run_rows.append({
                    "run_id": run_id,
                    "turn_key": turn_key,
                    "artifact_id": artifact_id,
                    "tokens": int(tokens),
                    "attachment_id": attachment_id,
                    # display_title is best-effort; the JSONB source pre-dates
                    # the spec-0145 title-resolution path so we leave it null
                    # for historical rows. The hosted UI falls back to the
                    # artifact_id when display_title is null.
                    "display_title": None,
                })
                counts.artifact_rows_to_write += 1
        if per_run_rows:
            rows_by_run[run_id] = per_run_rows

    counts.translation_conflicts = len(conflicts)
    return counts, conflicts, rows_by_run


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse (run_id, turn_key, artifact_id) duplicates within a batch.

    Postgres rejects upserts that have duplicate constrained tuples
    within a single command. Retried turns can produce two
    ``turn_ended`` events with the same label → same turn_key →
    same artifact rows. Latest occurrence wins, matching the
    semantics the upsert would have if the rows were sent one-by-one.
    """
    seen: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["run_id"], row["turn_key"], row["artifact_id"])
        seen[key] = row
    return list(seen.values())


def execute_pass1(
    client: Any,
    rows_by_run: dict[str, list[dict[str, Any]]],
    *,
    log: Iterable[str] | None = None,
) -> tuple[int, int]:
    """Upsert all planned rows into turn_prompt_pieces. Returns
    (runs_written, rows_written)."""
    runs_written = 0
    rows_written = 0
    batch_size = 200
    for run_id, rows in rows_by_run.items():
        deduped = _dedupe_rows(rows)
        for i in range(0, len(deduped), batch_size):
            batch = deduped[i:i + batch_size]
            client.table("turn_prompt_pieces").upsert(
                batch, on_conflict="run_id,turn_key,artifact_id"
            ).execute()
            rows_written += len(batch)
        runs_written += 1
        print(
            f"  [{runs_written}/{len(rows_by_run)}] {run_id} "
            f"→ wrote {len(deduped)} rows (deduped from {len(rows)})"
        )
    return runs_written, rows_written


# ─── Pass 2 (D05) — local FS input.json backfill + push ───────────────


@dataclass
class Pass2Counts:
    total_session_dirs: int = 0
    dirs_with_brief: int = 0
    dirs_missing_input_json: int = 0
    dirs_skipped_no_brief: int = 0


def plan_pass2(runs_dir: Path) -> tuple[Pass2Counts, list[Path]]:
    counts = Pass2Counts()
    candidates: list[Path] = []
    if not runs_dir.is_dir():
        return counts, candidates
    for session_dir in sorted(runs_dir.iterdir()):
        if not session_dir.is_dir():
            continue
        counts.total_session_dirs += 1
        brief = session_dir / "brief.md"
        if not brief.is_file():
            counts.dirs_skipped_no_brief += 1
            continue
        counts.dirs_with_brief += 1
        input_json = session_dir / "inputs" / "input.json"
        if input_json.is_file():
            continue
        counts.dirs_missing_input_json += 1
        candidates.append(session_dir)
    return counts, candidates


def execute_pass2(
    candidates: list[Path],
    *,
    push: bool,
    limit: int | None = None,
    max_retries: int = 3,
    retry_delay_s: float = 10.0,
) -> tuple[int, int]:
    """Write inputs/input.json for each candidate session-dir and
    (when ``push=True``) push the session-dir to Supabase. Returns
    (dirs_written, dirs_pushed).

    Supabase statement timeouts on large file batches are retried with
    a delay — the push pipeline is idempotent so retries are safe.
    """
    import time

    from dual_research.config import load_supabase_credentials
    from dual_research.orchestrator.run import (
        _persist_initial_brief_bundle,
        _resolve_run_attachments,
    )

    remote = None
    if push:
        # Spec 0150 — historical runs can carry 10-15MB transcripts and
        # per-event payloads up to ~600KB, which blow past Supabase's
        # statement_timeout on a 500-event batch. Override the batch
        # sizes for the backfill push only.
        import dual_research.persistence.remote as _remote_mod
        from dual_research.persistence.remote import RemoteSession

        _remote_mod.EVENT_BATCH_SIZE = 5
        _remote_mod.FILE_BATCH_SIZE = 5
        creds = load_supabase_credentials()
        remote = RemoteSession.from_credentials(creds.url, creds.service_role_key)

    written = 0
    pushed = 0
    selected = candidates if limit is None else candidates[:limit]
    for idx, session_dir in enumerate(selected, start=1):
        brief = session_dir / "brief.md"
        brief_text = brief.read_text(encoding="utf-8")
        attachments = _resolve_run_attachments(session_dir)
        _persist_initial_brief_bundle(session_dir, brief_text, attachments=attachments)
        written += 1
        print(f"  [{idx}/{len(selected)}] {session_dir.name} → wrote input.json")
        if remote is not None:
            last_exc: Exception | None = None
            for attempt in range(1, max_retries + 1):
                try:
                    summary = remote.push_session_dir(session_dir)
                    pushed += 1
                    print(
                        f"      pushed: events={summary.events_upserted} "
                        f"files={summary.files_upserted} "
                        f"pieces={summary.prompt_pieces_upserted}"
                    )
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
                    print(
                        f"      push attempt {attempt}/{max_retries} failed: "
                        f"{type(exc).__name__}: {exc}"
                    )
                    if attempt < max_retries:
                        time.sleep(retry_delay_s)
            if last_exc is not None:
                raise last_exc
    return written, pushed


# ─── Pass 3 (D15, per-turn bundles) — translate inputs/*.json text dicts ──


@dataclass
class Pass3Counts:
    total_per_turn_files: int = 0
    legacy_files_to_translate: int = 0
    files_with_mixed_keys: int = 0
    files_without_phase_in_name: int = 0


_PHASE_IN_FILENAME_RE = re.compile(r"^phase(\d+)")


def _phase_num_from_filename(name: str) -> int | None:
    """Extract phase number from filenames like `phase2_round1_claude.json`
    or `phase0_claude.json`. Returns None when no phase prefix is present."""
    m = _PHASE_IN_FILENAME_RE.match(name)
    if not m:
        return None
    try:
        n = int(m.group(1))
    except ValueError:
        return None
    return n if 0 <= n <= 4 else None


def _translate_pieces_in_bundle(
    pieces: dict[str, Any], phase_num: int | None
) -> dict[str, Any]:
    """Per-turn bundle translation: keys only, preserving values verbatim.

    Same legacy → canonical translation policy as `translate_prompt_pieces`,
    but operates on string-valued pieces (the actual text the agent saw),
    not token counts. Prefer-canonical: if both a legacy key and its
    canonical sibling exist in the same dict, canonical wins.
    """
    out: dict[str, Any] = {}
    legacy_seen: dict[str, Any] = {}
    canonical_present: set[str] = set()
    for k, v in (pieces or {}).items():
        if k in LEGACY_KEY_TO_CANONICAL:
            legacy_seen[k] = v
        else:
            canonical_present.add(k)
            out[k] = v
    for legacy_key, legacy_value in legacy_seen.items():
        canon = canonicalise_legacy_key(legacy_key, phase_num)
        if canon in canonical_present:
            continue
        out[canon] = legacy_value
    return out


def plan_pass3(runs_dir: Path) -> tuple[Pass3Counts, list[Path]]:
    counts = Pass3Counts()
    candidates: list[Path] = []
    if not runs_dir.is_dir():
        return counts, candidates
    for session_dir in sorted(runs_dir.iterdir()):
        if not session_dir.is_dir():
            continue
        inputs_dir = session_dir / "inputs"
        if not inputs_dir.is_dir():
            continue
        session_needs_translation = False
        for input_file in sorted(inputs_dir.glob("*.json")):
            if input_file.name == "input.json":
                continue
            counts.total_per_turn_files += 1
            try:
                data = json.loads(input_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            pieces = data.get("pieces") or {}
            if not pieces:
                continue
            keys = set(pieces.keys())
            has_legacy = bool(keys & set(LEGACY_KEY_TO_CANONICAL))
            has_canonical = any("." in k for k in keys)
            if not has_legacy:
                continue
            if has_canonical:
                counts.files_with_mixed_keys += 1
            counts.legacy_files_to_translate += 1
            if _phase_num_from_filename(input_file.name) is None:
                counts.files_without_phase_in_name += 1
            session_needs_translation = True
        if session_needs_translation:
            candidates.append(session_dir)
    return counts, candidates


def _push_inputs_dir_only(
    client: Any, run_id: str, session_dir: Path
) -> int:
    """Minimal push: upsert just the `inputs/*.json` rows to session_files.

    The full push pipeline re-uploads multi-MB transcripts that
    overshoot Supabase's statement_timeout on these large historical
    runs. Since the only files this backfill changed are the per-turn
    input bundles, uploading just those is sufficient — and small
    enough to fit under the timeout.
    """
    rows: list[dict[str, Any]] = []
    inputs_dir = session_dir / "inputs"
    if not inputs_dir.is_dir():
        return 0
    for path in sorted(inputs_dir.glob("*.json")):
        content = path.read_text(encoding="utf-8")
        rows.append({
            "run_id": run_id,
            "path": str(path.relative_to(session_dir)),
            "content": content,
            "size_bytes": len(content.encode("utf-8")),
        })
    BATCH = 3
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i + BATCH]
        client.table("session_files").upsert(
            batch, on_conflict="run_id,path"
        ).execute()
    return len(rows)


def execute_pass3(
    candidates: list[Path],
    *,
    push: bool,
    limit: int | None = None,
    max_retries: int = 3,
    retry_delay_s: float = 10.0,
) -> tuple[int, int, int]:
    """For each session-dir with legacy per-turn bundles, translate keys
    in-place and (when push=True) push ONLY the `inputs/*.json` rows
    to Supabase via `_push_inputs_dir_only`. Returns
    (dirs_touched, files_translated, dirs_pushed)."""
    import time

    from dual_research.config import load_supabase_credentials
    from dual_research.persistence.state import write_atomic

    client = None
    if push:
        from supabase import create_client

        creds = load_supabase_credentials()
        client = create_client(creds.url, creds.service_role_key)

    dirs_touched = 0
    files_translated = 0
    dirs_pushed = 0
    selected = candidates if limit is None else candidates[:limit]
    for idx, session_dir in enumerate(selected, start=1):
        inputs_dir = session_dir / "inputs"
        translated_here = 0
        for input_file in sorted(inputs_dir.glob("*.json")):
            if input_file.name == "input.json":
                continue
            try:
                data = json.loads(input_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            pieces = data.get("pieces") or {}
            if not pieces:
                continue
            if not any(k in LEGACY_KEY_TO_CANONICAL for k in pieces):
                continue
            phase_num = _phase_num_from_filename(input_file.name)
            new_pieces = _translate_pieces_in_bundle(pieces, phase_num)
            if new_pieces == pieces:
                continue
            data["pieces"] = new_pieces
            write_atomic(input_file, json.dumps(data, indent=2))
            translated_here += 1
        files_translated += translated_here
        if translated_here > 0:
            dirs_touched += 1
            print(
                f"  [{idx}/{len(selected)}] {session_dir.name} "
                f"→ translated {translated_here} per-turn bundles"
            )
        if client is not None and translated_here > 0:
            last_exc: Exception | None = None
            for attempt in range(1, max_retries + 1):
                try:
                    n = _push_inputs_dir_only(
                        client, session_dir.name, session_dir
                    )
                    dirs_pushed += 1
                    print(f"      pushed: input files={n}")
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
                    print(
                        f"      push attempt {attempt}/{max_retries} failed: "
                        f"{type(exc).__name__}: {exc}"
                    )
                    if attempt < max_retries:
                        time.sleep(retry_delay_s)
            if last_exc is not None:
                raise last_exc
    return dirs_touched, files_translated, dirs_pushed


def _print_pass3_dryrun(counts: Pass3Counts, candidates: list[Path]) -> None:
    print("── Pass 3 (per-turn bundles) — inputs/*.json key translation ──")
    print(f"  total per-turn files (excl. input.json) : {counts.total_per_turn_files}")
    print(f"  legacy-keyed files to translate         : {counts.legacy_files_to_translate}")
    print(f"  files with mixed legacy+canonical keys  : {counts.files_with_mixed_keys}")
    print(f"  files lacking phase prefix in filename  : {counts.files_without_phase_in_name}")
    if candidates:
        print(f"  sessions needing translation: {len(candidates)}")
        for p in candidates[:5]:
            print(f"    {p.name}")


# ─── CLI ──────────────────────────────────────────────────────────────


def _build_client():
    from dual_research.config import load_supabase_credentials
    from supabase import create_client

    creds = load_supabase_credentials()
    return create_client(creds.url, creds.service_role_key)


def _print_pass1_dryrun(counts: Pass1Counts, conflicts: list[TranslationConflict]) -> None:
    print("── Pass 1 (D15) — Supabase JSONB → turn_prompt_pieces ──")
    print(f"  total runs with turn_ended events  : {counts.total_runs_with_turn_ended}")
    print(f"  runs already backfilled (skip)     : {counts.runs_already_backfilled}")
    print(f"  runs to backfill                   : {counts.runs_to_backfill}")
    print(f"  total (run_id, turn_key) pairs     : {counts.turn_pairs_to_write}")
    print(f"  total artifact rows to write       : {counts.artifact_rows_to_write}")
    print(f"  events with missing/invalid phase  : {counts.events_with_missing_phase}")
    print(f"  legacy/canonical translation conflicts: {counts.translation_conflicts}")
    if conflicts:
        print("  conflict details (first 10):")
        for c in conflicts[:10]:
            print(
                f"    run={c.run_id} turn={c.turn_key} "
                f"legacy={c.legacy_key}={c.legacy_tokens} "
                f"vs canonical={c.canonical_key}={c.canonical_tokens}"
            )


def _print_pass2_dryrun(counts: Pass2Counts, candidates: list[Path]) -> None:
    print("── Pass 2 (D05) — local input.json backfill ──")
    print(f"  total runs/*/ directories          : {counts.total_session_dirs}")
    print(f"  dirs with brief.md                 : {counts.dirs_with_brief}")
    print(f"  dirs lacking inputs/input.json     : {counts.dirs_missing_input_json}")
    print(f"  dirs skipped (no brief.md)         : {counts.dirs_skipped_no_brief}")
    if candidates:
        sample = candidates[:5]
        print("  sample candidates:")
        for p in sample:
            print(f"    {p.name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="enumerate work but write nothing")
    parser.add_argument("--pass", dest="which", choices=["1", "2", "3"],
                        help="run only pass 1 (D15 — turn_prompt_pieces), "
                             "2 (D05 — input.json), or 3 (per-turn bundles)")
    parser.add_argument("--limit", type=int, default=None,
                        help="process at most N runs in the selected pass")
    parser.add_argument("--runs-dir", type=Path, default=Path("runs"),
                        help="override the runs directory (default: ./runs)")
    parser.add_argument("--no-push", action="store_true",
                        help="pass-2: skip the dual-research --push step")
    args = parser.parse_args()

    run_pass1 = args.which in (None, "1")
    run_pass2 = args.which in (None, "2")
    run_pass3 = args.which in (None, "3")

    if run_pass1:
        try:
            client = _build_client()
        except Exception as exc:
            print(f"error: failed to build Supabase client: {exc}", file=sys.stderr)
            return 1
        counts, conflicts, rows_by_run = plan_pass1(client, limit=args.limit)
        _print_pass1_dryrun(counts, conflicts)
        if not args.dry_run:
            if counts.runs_to_backfill == 0:
                print("  nothing to write (already idempotent).")
            else:
                print(f"  writing rows for {len(rows_by_run)} runs ...")
                runs_w, rows_w = execute_pass1(client, rows_by_run)
                print(f"  done. runs={runs_w} rows={rows_w}")

    if run_pass2:
        counts2, candidates = plan_pass2(args.runs_dir)
        _print_pass2_dryrun(counts2, candidates)
        if not args.dry_run:
            if not candidates:
                print("  nothing to write (already idempotent).")
            else:
                print(f"  writing {len(candidates)} input.json files ...")
                written, pushed = execute_pass2(
                    candidates,
                    push=not args.no_push,
                    limit=args.limit,
                )
                print(f"  done. written={written} pushed={pushed}")

    if run_pass3:
        counts3, candidates3 = plan_pass3(args.runs_dir)
        _print_pass3_dryrun(counts3, candidates3)
        if not args.dry_run:
            if not candidates3:
                print("  nothing to translate (already idempotent).")
            else:
                print(f"  translating per-turn bundles in {len(candidates3)} sessions ...")
                dirs_t, files_t, pushed3 = execute_pass3(
                    candidates3,
                    push=not args.no_push,
                    limit=args.limit,
                )
                print(
                    f"  done. dirs_touched={dirs_t} files_translated={files_t} "
                    f"pushed={pushed3}"
                )

    return 0


if __name__ == "__main__":
    sys.exit(main())

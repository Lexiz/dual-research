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
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            client.table("turn_prompt_pieces").upsert(
                batch, on_conflict="run_id,turn_key,artifact_id"
            ).execute()
            rows_written += len(batch)
        runs_written += 1
        print(
            f"  [{runs_written}/{len(rows_by_run)}] {run_id} "
            f"→ wrote {len(rows)} rows"
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
) -> tuple[int, int]:
    """Write inputs/input.json for each candidate session-dir and
    (when ``push=True``) push the session-dir to Supabase. Returns
    (dirs_written, dirs_pushed)."""
    from dual_research.config import load_supabase_credentials
    from dual_research.orchestrator.run import (
        _persist_initial_brief_bundle,
        _resolve_run_attachments,
    )

    remote = None
    if push:
        from dual_research.persistence.remote import RemoteSession

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
            summary = remote.push_session_dir(session_dir)
            pushed += 1
            print(
                f"      pushed: events={summary.events_upserted} "
                f"files={summary.files_upserted} "
                f"pieces={summary.prompt_pieces_upserted}"
            )
    return written, pushed


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
    parser.add_argument("--pass", dest="which", choices=["1", "2"],
                        help="run only pass 1 (D15) or pass 2 (D05)")
    parser.add_argument("--limit", type=int, default=None,
                        help="process at most N runs in the selected pass")
    parser.add_argument("--runs-dir", type=Path, default=Path("runs"),
                        help="override the runs directory (default: ./runs)")
    parser.add_argument("--no-push", action="store_true",
                        help="pass-2: skip the dual-research --push step")
    args = parser.parse_args()

    run_pass1 = args.which in (None, "1")
    run_pass2 = args.which in (None, "2")

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

    return 0


if __name__ == "__main__":
    sys.exit(main())

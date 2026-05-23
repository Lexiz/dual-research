"""One-time backfill: spec frontmatter + sidecar events → queue-state.json (spec 0202 §2.6).

Run once during the implementation of spec 0202. Steps:

1. Read every ``specs/NNNN-*.md`` (and decimal ``NNNN.M-*.md`` per spec
   0199). Copy frontmatter status/timestamps/PR/handover/target_version
   into the new state entry.
2. Read every ``dashboard/events/*.jsonl``. Parse JSONL lines and inject
   as ``state.specs[NNNN].events``.
3. Write ``dashboard/queue-state.json``.
4. Move ``dashboard/events/NNNN.jsonl`` → ``dashboard/events/archive/NNNN.jsonl``.
5. Archive handoffs: call ``archive_old_handoffs(Path('handoffs'), cap=20)``
   — protects any in-flight L-spec checkpoint handoff from being moved.

Idempotent: re-running on an already-backfilled repo (``queue-state.json``
exists) is a no-op and exits 0 with a "nothing to do" message.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


def _stringify(value: Any) -> Any:
    """Coerce YAML-parsed dates/datetimes into ISO-format strings.

    PyYAML returns ``datetime.date`` / ``datetime.datetime`` for ``YYYY-MM-DD``
    and ``YYYY-MM-DDTHH:MM:SSZ`` literals; the JSON serialiser doesn't
    handle them. Round-tripping through ``isoformat`` gives us the same
    text shape the rest of the system uses."""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ") if value.tzinfo is None else value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value

from scripts.spec_lifecycle.archive_handoffs import archive_old_handoffs, _active_checkpoint_paths
from scripts.spec_lifecycle.frontmatter import parse as parse_frontmatter
from scripts.spec_lifecycle.pick_next_number import SPEC_ID_RE
from scripts.spec_lifecycle.queue_state import (
    QUEUE_STATE_REL_PATH,
    SCHEMA_VERSION,
    QueueState,
)

# Frontmatter fields copied verbatim into the state entry. Anything outside
# this set stays in the spec frontmatter as a queue-time snapshot — the
# renderer's fallback path covers it (spec 0202 §7 "Backfill misses fields
# the brief didn't anticipate").
COPIED_FRONTMATTER_FIELDS = (
    "status",
    "started_at",
    "merged_at",
    "deployed_at",
    "pr",
    "target_version",
    "handover",
    "failure_step",
    "queued_at",
)


def _spec_id_from_filename(name: str) -> str | None:
    m = SPEC_ID_RE.match(name)
    if not m:
        return None
    parent, child = m.group(1), m.group(2)
    return f"{parent}.{child}" if child else parent


def _read_sidecar(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            sys.stderr.write(f"build_queue_state: skipping malformed line in {path}\n")
    return out


def build_state_from_repo(repo_root: Path) -> QueueState:
    """Construct a QueueState by reading every spec + every sidecar.

    Pure function — does not write anything. The caller persists it via
    :func:`write_backfill` or its own glue.
    """
    state = QueueState(
        version=SCHEMA_VERSION,
        updated_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    specs_dir = repo_root / "specs"
    if specs_dir.exists():
        for entry in sorted(specs_dir.iterdir()):
            if not entry.is_file() or entry.suffix != ".md":
                continue
            spec_id = _spec_id_from_filename(entry.name)
            if spec_id is None:
                continue
            fm = parse_frontmatter(entry).frontmatter
            entry_state: dict[str, Any] = {}
            for key in COPIED_FRONTMATTER_FIELDS:
                v = fm.get(key)
                if v in (None, ""):
                    continue
                entry_state[key] = _stringify(v)
            entry_state.setdefault("events", [])
            state.specs[spec_id] = entry_state

    events_dir = repo_root / "dashboard" / "events"
    if events_dir.exists():
        for entry in sorted(events_dir.iterdir()):
            if not entry.is_file() or entry.suffix != ".jsonl":
                continue
            spec_id = entry.stem
            events = _read_sidecar(entry)
            spec_entry = state.specs.setdefault(spec_id, {})
            # Sidecar events become the authoritative event list for the
            # spec; backfill is one-shot, so there's no merge concern here.
            spec_entry["events"] = events

    return state


def _archive_sidecars(events_dir: Path) -> list[tuple[Path, Path]]:
    """Move every top-level ``*.jsonl`` into ``dashboard/events/archive/``."""
    if not events_dir.exists():
        return []
    archive_dir = events_dir / "archive"
    moved: list[tuple[Path, Path]] = []
    for entry in sorted(events_dir.iterdir()):
        if not entry.is_file() or entry.suffix != ".jsonl":
            continue
        archive_dir.mkdir(parents=True, exist_ok=True)
        dst = archive_dir / entry.name
        entry.rename(dst)
        moved.append((entry, dst))
    return moved


def _active_in_progress_specs(state: QueueState) -> set[str]:
    return {sid for sid, e in state.specs.items() if e.get("status") == "in_progress"}


def run_backfill(repo_root: Path, *, cap: int = 20) -> dict[str, Any]:
    """Execute the full §2.6 sequence. Returns a dict describing what changed.

    Idempotent: if ``dashboard/queue-state.json`` already exists, returns
    ``{"skipped": True, ...}`` and touches nothing.
    """
    state_path = repo_root / QUEUE_STATE_REL_PATH
    if state_path.exists():
        return {
            "skipped": True,
            "reason": f"{QUEUE_STATE_REL_PATH} already exists; nothing to do",
        }

    state = build_state_from_repo(repo_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(state.to_json(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    events_dir = repo_root / "dashboard" / "events"
    sidecars_moved = _archive_sidecars(events_dir)

    handoffs_dir = repo_root / "handoffs"
    active_specs = _active_in_progress_specs(state)
    protected = _active_checkpoint_paths(handoffs_dir, active_specs) if handoffs_dir.exists() else set()
    handoffs_moved = archive_old_handoffs(handoffs_dir, cap=cap, protect=protected)

    return {
        "skipped": False,
        "specs": len(state.specs),
        "sidecars_archived": len(sidecars_moved),
        "handoffs_archived": len(handoffs_moved),
        "protected_checkpoints": [str(p) for p in protected],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_queue_state",
        description="One-time backfill: spec frontmatter + sidecar events → queue-state.json.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root (default: cwd)")
    parser.add_argument(
        "--cap", type=int, default=20,
        help="Live handoff cap during the archive step (default: 20)",
    )
    args = parser.parse_args(argv)

    result = run_backfill(Path(args.repo_root), cap=args.cap)
    if result.get("skipped"):
        print(f"build_queue_state: {result['reason']}")
        return 0
    print(
        f"build_queue_state: backfilled {result['specs']} specs, "
        f"archived {result['sidecars_archived']} event sidecars, "
        f"archived {result['handoffs_archived']} handoffs "
        f"(protected {len(result['protected_checkpoints'])} in-flight checkpoints)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

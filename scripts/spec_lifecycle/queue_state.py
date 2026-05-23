"""Mutable cycle-state file for every spec (spec 0202).

Replaces per-spec frontmatter status writes and per-spec event sidecars
with a single document at ``dashboard/queue-state.json``. Spec frontmatter
becomes a queue-time snapshot; the authoritative cycle status, timestamps,
PR URL, handoff pointer, and event timeline all live here.

Schema (spec 0202 §2.1):

    {
      "version": 1,
      "updated_at": "2026-05-24T12:34:56Z",
      "specs": {
        "0152": {
          "status": "deployed",
          "started_at": "...",
          "merged_at": "...",
          "deployed_at": "...",
          "pr": "...",
          "target_version": "...",
          "handover": "...",
          "failure_step": null,
          "events": [{"ts": "...", "step": "...", "data": {}}]
        }
      }
    }

Concurrency: when ``push_to_main=True`` the write is committed to
``origin/main`` directly via the same ``GIT_INDEX_FILE`` plumbing that
``push_event_to_main`` uses (``append_event.py:124`` non-fast-forward
retry pattern). Up to 3 retries; events from a concurrent writer are
preserved on conflict by re-reading origin and re-applying the caller's
intent on top.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

QUEUE_STATE_REL_PATH = "dashboard/queue-state.json"
SCHEMA_VERSION = 1
DEFAULT_PUSH_RETRIES = 3

# Scalar fields a caller may set via ``update_state(**fields)``. Anything
# outside this set raises — keeps callers from silently writing typos like
# ``deployed_ts=`` and wondering why the dashboard didn't change.
ALLOWED_SCALAR_FIELDS = frozenset(
    {
        "status",
        "started_at",
        "merged_at",
        "deployed_at",
        "pr",
        "target_version",
        "handover",
        "failure_step",
        "queued_at",
    }
)


@dataclass
class QueueState:
    """In-memory view of ``dashboard/queue-state.json``.

    ``specs`` is keyed by spec ID (string, supporting decimal IDs per spec
    0199 — e.g. ``"0152"`` or ``"0170.1"``). Each value is a free-form dict
    so future fields land without a schema migration; the renderer reads
    defensively.
    """

    version: int = SCHEMA_VERSION
    updated_at: str = ""
    specs: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any] | None) -> "QueueState":
        if not data:
            return cls()
        return cls(
            version=int(data.get("version", SCHEMA_VERSION)),
            updated_at=str(data.get("updated_at", "")),
            specs=dict(data.get("specs") or {}),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "updated_at": self.updated_at,
            "specs": self.specs,
        }

    def get_spec(self, spec_id: str) -> dict[str, Any]:
        """Return the per-spec entry, creating an empty one if missing."""
        return self.specs.setdefault(spec_id, {})


def queue_state_path(repo_root: str | Path) -> Path:
    return Path(repo_root) / QUEUE_STATE_REL_PATH


def read_state(repo_root: str | Path) -> QueueState:
    """Load ``dashboard/queue-state.json``. Returns an empty state if missing."""
    path = queue_state_path(repo_root)
    if not path.exists():
        return QueueState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return QueueState()
    return QueueState.from_json(data)


def _serialise(state: QueueState) -> str:
    """Render the state as the canonical on-disk form (pretty JSON + trailing newline)."""
    return json.dumps(state.to_json(), indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def _apply_updates(
    state: QueueState,
    spec_id: str,
    *,
    fields: dict[str, Any],
    events_append: list[dict[str, Any]] | None,
    events_replace: list[dict[str, Any]] | None,
    now_iso: str,
) -> QueueState:
    """Merge ``fields`` and event updates onto ``state`` in place; return ``state``.

    Validation: ``events_replace`` cannot shrink the events array (spec
    0202 §2.1 — defends against concurrent-write clobber). ``events_append``
    is unconditionally additive.
    """
    entry = state.get_spec(spec_id)
    bad = set(fields) - ALLOWED_SCALAR_FIELDS
    if bad:
        raise ValueError(
            f"unknown queue-state field(s) for {spec_id}: {sorted(bad)}; "
            f"allowed: {sorted(ALLOWED_SCALAR_FIELDS)}"
        )
    for k, v in fields.items():
        entry[k] = v
    current_events: list[dict[str, Any]] = list(entry.get("events") or [])
    if events_replace is not None:
        if len(events_replace) < len(current_events):
            raise ValueError(
                f"refusing to shrink events for {spec_id}: on-disk has "
                f"{len(current_events)} entries, replacement has {len(events_replace)}"
            )
        current_events = list(events_replace)
    if events_append:
        current_events.extend(events_append)
    entry["events"] = current_events
    state.updated_at = now_iso
    return state


def update_state(
    repo_root: str | Path,
    spec_id: str,
    *,
    push_to_main: bool = False,
    events_append: list[dict[str, Any]] | None = None,
    events_replace: list[dict[str, Any]] | None = None,
    repo_dir: str | Path | None = None,
    now: datetime | None = None,
    **fields: Any,
) -> Path:
    """Read-modify-write ``dashboard/queue-state.json`` for one spec.

    ``fields`` may be any of :data:`ALLOWED_SCALAR_FIELDS`. Pass
    ``events_append=[...]`` to add new event entries (typical), or
    ``events_replace=[...]`` to set the full array (must not shrink).

    When ``push_to_main=True``, the write is committed to ``origin/main``
    directly via git plumbing; on success the local working copy is also
    updated. Up to 3 retries on non-fast-forward; on permanent failure
    the local file is left untouched and a RuntimeError is raised so the
    caller can halt cleanly.
    """
    repo_root_path = Path(repo_root)
    now_iso = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    target_path = queue_state_path(repo_root_path)

    if not push_to_main:
        # Local-only path: read + modify + write the working-tree file.
        state = read_state(repo_root_path)
        _apply_updates(
            state,
            spec_id,
            fields=fields,
            events_append=events_append,
            events_replace=events_replace,
            now_iso=now_iso,
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(_serialise(state), encoding="utf-8")
        return target_path

    # Push-to-main path: re-read origin on each retry to preserve concurrent
    # writes; reapply the caller's intent on top each time.
    def apply(origin_state: QueueState) -> QueueState:
        return _apply_updates(
            origin_state,
            spec_id,
            fields=fields,
            events_append=events_append,
            events_replace=events_replace,
            now_iso=now_iso,
        )

    rd = repo_dir if repo_dir is not None else repo_root_path
    success, new_content = _push_state_to_main(
        rel_path=QUEUE_STATE_REL_PATH,
        spec_id=spec_id,
        apply_update=apply,
        repo_dir=rd,
    )
    if not success:
        raise RuntimeError(
            f"queue_state.update_state: push to origin/main failed for {spec_id} "
            f"after {DEFAULT_PUSH_RETRIES} retries; on-disk file untouched"
        )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(new_content, encoding="utf-8")
    return target_path


def append_event_to_state(
    repo_root: str | Path,
    spec_id: str,
    step: str,
    data: dict[str, Any] | None = None,
    *,
    ts: str | None = None,
    push_to_main: bool = False,
    repo_dir: str | Path | None = None,
) -> Path:
    """Convenience wrapper: append one ``{ts, step, data}`` event to a spec.

    Shape matches the legacy ``dashboard/events/NNNN.jsonl`` line shape so
    the renderer's stage-derivation code reads both sources identically
    (spec 0202 §2.4).
    """
    if ts is None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    event = {"ts": ts, "step": step, "data": data or {}}
    return update_state(
        repo_root,
        spec_id,
        push_to_main=push_to_main,
        events_append=[event],
        repo_dir=repo_dir,
    )


# --- Git plumbing for push-to-main ------------------------------------------

def _push_state_to_main(
    *,
    rel_path: str,
    spec_id: str,
    apply_update: Callable[[QueueState], QueueState],
    repo_dir: str | Path,
    retries: int = DEFAULT_PUSH_RETRIES,
) -> tuple[bool, str]:
    """Push a new queue-state document to ``origin/main`` via git plumbing.

    Mirrors :func:`scripts.spec_lifecycle.append_event.push_event_to_main`
    but operates on a full JSON document (read-modify-write) instead of
    a line-append. On non-fast-forward, re-fetches origin/main and calls
    ``apply_update`` again so a concurrent writer's events are preserved.

    Returns ``(ok, serialised_content)``. The content is the final blob
    pushed (or attempted), so the caller can mirror it into the local
    working copy on success.
    """
    last_err: str | None = None
    last_content = ""
    for attempt in range(retries):
        try:
            _git(["fetch", "--quiet", "origin", "main"], repo_dir)
            cat = _git(
                ["cat-file", "-p", f"origin/main:{rel_path}"], repo_dir, check=False
            )
            if cat.returncode == 0:
                try:
                    origin_state = QueueState.from_json(json.loads(cat.stdout))
                except json.JSONDecodeError:
                    origin_state = QueueState()
            else:
                origin_state = QueueState()
            new_state = apply_update(origin_state)
            content = _serialise(new_state)
            last_content = content
            blob_sha = _git(
                ["hash-object", "-w", "--stdin"], repo_dir, input=content
            ).stdout.strip()
            new_tree = _build_tree_with_temp_index(rel_path, blob_sha, repo_dir)
            msg = f"spec({spec_id}): queue-state update"
            commit_sha = _git(
                ["commit-tree", new_tree, "-p", "origin/main", "-m", msg], repo_dir
            ).stdout.strip()
            push = _git(
                ["push", "origin", f"{commit_sha}:refs/heads/main"],
                repo_dir,
                check=False,
            )
            if push.returncode == 0:
                return True, content
            err_text = (push.stderr or push.stdout or "").lower()
            if "non-fast-forward" in err_text or "rejected" in err_text:
                last_err = f"non-fast-forward on attempt {attempt + 1}"
                continue
            last_err = (push.stderr or push.stdout or "").strip() or "unknown push failure"
            break
        except subprocess.CalledProcessError as e:
            last_err = str(e)
            break

    sys.stderr.write(
        f"warning: queue_state push failed for {spec_id}: {last_err}\n"
    )
    return False, last_content


def _git(
    args: list[str],
    cwd: str | Path | None = None,
    *,
    input: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        input=input,
        capture_output=True,
        text=True,
        check=check,
    )


def _build_tree_with_temp_index(
    rel_path: str, blob_sha: str, repo_dir: str | Path
) -> str:
    """Mirror of :func:`append_event._build_tree_with_temp_index`.

    Kept locally rather than imported to avoid coupling the queue-state
    module to the append-event module's internals — both call the same
    git plumbing but they're independent callers.
    """
    fd, index_path = tempfile.mkstemp(suffix=".index")
    os.close(fd)
    os.unlink(index_path)
    try:
        env = {**os.environ, "GIT_INDEX_FILE": index_path}
        cwd = str(repo_dir)
        subprocess.run(
            ["git", "read-tree", "origin/main"],
            cwd=cwd, env=env, capture_output=True, text=True, check=True,
        )
        subprocess.run(
            [
                "git", "update-index", "--add", "--cacheinfo",
                f"100644,{blob_sha},{rel_path}",
            ],
            cwd=cwd, env=env, capture_output=True, text=True, check=True,
        )
        return subprocess.run(
            ["git", "write-tree"],
            cwd=cwd, env=env, capture_output=True, text=True, check=True,
        ).stdout.strip()
    finally:
        if os.path.exists(index_path):
            os.unlink(index_path)


# --- CLI --------------------------------------------------------------------

def _parse_field_assignments(items: list[str]) -> dict[str, Any]:
    """Parse ``key=value`` CLI args into a dict of scalar fields.

    Values are kept as strings; the on-disk JSON serialises them as such.
    For ``failure_step=null`` the literal string ``"null"`` becomes JSON
    null so callers can clear a prior failure flag.
    """
    out: dict[str, Any] = {}
    for raw in items:
        if "=" not in raw:
            raise SystemExit(f"queue_state set: bad arg {raw!r}, expected key=value")
        k, v = raw.split("=", 1)
        if v == "null":
            out[k] = None
        else:
            out[k] = v
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="queue_state", description="Read/write dashboard/queue-state.json"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    set_p = sub.add_parser("set", help="Set scalar fields on one spec")
    set_p.add_argument("spec_id", help="Spec ID, e.g. 0202 or 0170.1")
    set_p.add_argument(
        "assignments",
        nargs="*",
        help="key=value pairs (status, started_at, deployed_at, pr, "
             "target_version, handover, failure_step, queued_at, merged_at). "
             "Use failure_step=null to clear.",
    )
    set_p.add_argument(
        "--push-to-main",
        action="store_true",
        help="Push the update to origin/main via git plumbing.",
    )
    set_p.add_argument(
        "--repo-root", default=".", help="Repository root (default: cwd)"
    )

    append_p = sub.add_parser(
        "append-event", help="Append one event to a spec's queue-state entry"
    )
    append_p.add_argument("spec_id")
    append_p.add_argument("step")
    append_p.add_argument("data_json", nargs="?", default="{}")
    append_p.add_argument("--push-to-main", action="store_true")
    append_p.add_argument("--repo-root", default=".")

    show_p = sub.add_parser("show", help="Print one spec's entry (or all if no id)")
    show_p.add_argument("spec_id", nargs="?", default=None)
    show_p.add_argument("--repo-root", default=".")

    args = parser.parse_args(argv)

    if args.cmd == "set":
        fields = _parse_field_assignments(args.assignments)
        path = update_state(
            args.repo_root,
            args.spec_id,
            push_to_main=args.push_to_main,
            **fields,
        )
        print(f"updated queue-state at {path}")
        return 0
    if args.cmd == "append-event":
        try:
            data = json.loads(args.data_json)
        except json.JSONDecodeError as e:
            raise SystemExit(f"queue_state append-event: bad data_json: {e}")
        path = append_event_to_state(
            args.repo_root,
            args.spec_id,
            args.step,
            data,
            push_to_main=args.push_to_main,
        )
        print(f"appended event to queue-state at {path}")
        return 0
    if args.cmd == "show":
        state = read_state(args.repo_root)
        if args.spec_id is None:
            print(json.dumps(state.to_json(), indent=2))
        else:
            entry = state.specs.get(args.spec_id)
            if entry is None:
                print(f"no entry for {args.spec_id}", file=sys.stderr)
                return 1
            print(json.dumps(entry, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Append an event to a spec's sidecar JSONL log.

Skills call this from the dev cycle (and the spec-creation flows for `queued`
events). Events on `main` get committed inline by the caller; events on a
feature branch buffer and flush at end-of-cycle — unless the caller passes
``--push-to-main`` (spec 0163), in which case each event is pushed live to
origin/main via git plumbing immediately after the local file write, so the
dashboard sees branch-phase progress in real time.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def event_log_path(events_dir: str | Path, spec_id: str) -> Path:
    p = Path(events_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{spec_id}.jsonl"


def append_event(
    events_dir: str | Path,
    spec_id: str,
    step: str,
    data: dict[str, Any] | None = None,
    *,
    ts: str | None = None,
    push_to_main: bool = False,
    repo_dir: str | Path | None = None,
) -> Path:
    """Append one event line. Returns the file path.

    When ``push_to_main`` is True (spec 0163), also pushes the new event
    directly to ``origin/main`` via git plumbing, so the dashboard sees the
    event in real time without waiting for the eventual squash-merge. The
    push is best-effort: failures are logged to stderr and never raise — the
    line is still safely in the local file and will reach main via the
    squash-merge anyway.
    """
    if ts is None:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = json.dumps(
        {"ts": ts, "step": step, "data": data or {}}, separators=(",", ":"), ensure_ascii=False
    )
    log = event_log_path(events_dir, spec_id)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    if push_to_main:
        push_event_to_main(events_dir, spec_id, line + "\n", repo_dir=repo_dir)
    return log


def push_event_to_main(
    events_dir: str | Path,
    spec_id: str,
    new_line: str,
    *,
    retries: int = 1,
    repo_dir: str | Path | None = None,
) -> bool:
    """Push a new event line directly to origin/main using git plumbing.

    Operates without disturbing the working tree or the main git index: a
    temporary index (``GIT_INDEX_FILE``) is populated from ``origin/main``,
    the events file is updated in place, a new commit is built atop
    ``origin/main``, and pushed as an atomic ref update.

    Returns True on successful push, False on graceful failure (the local
    events file still contains the line; the eventual squash-merge will
    carry it to main).

    Idempotent when the current branch is already ``main`` — the caller is
    already committing to main directly, so no push is needed.
    """
    if _current_branch(repo_dir) == "main":
        return False

    # The events file path must be repo-relative for `git update-index
    # --cacheinfo`. Callers commonly pass an absolute path (e.g. from
    # `tmp_path / "dashboard" / "events"`); convert it to repo-relative when
    # we know the repo root.
    events_path = Path(events_dir)
    if events_path.is_absolute() and repo_dir is not None:
        try:
            events_path = events_path.relative_to(Path(repo_dir).resolve())
        except ValueError:
            pass
    rel_path = f"{events_path.as_posix().rstrip('/')}/{spec_id}.jsonl"
    step = _extract_step(new_line)
    last_err: Exception | str | None = None

    for attempt in range(retries + 1):
        try:
            _git(["fetch", "--quiet", "origin", "main"], repo_dir)
            cat = _git(
                ["cat-file", "-p", f"origin/main:{rel_path}"], repo_dir, check=False
            )
            existing = cat.stdout if cat.returncode == 0 else ""
            new_content = existing + new_line
            blob_sha = _git(
                ["hash-object", "-w", "--stdin"], repo_dir, input=new_content
            ).stdout.strip()
            new_tree = _build_tree_with_temp_index(rel_path, blob_sha, repo_dir)
            msg = f"spec({spec_id}): event {step}"
            commit_sha = _git(
                ["commit-tree", new_tree, "-p", "origin/main", "-m", msg], repo_dir
            ).stdout.strip()
            push = _git(
                ["push", "origin", f"{commit_sha}:refs/heads/main"],
                repo_dir,
                check=False,
            )
            if push.returncode == 0:
                return True
            err_text = (push.stderr or push.stdout or "").lower()
            if "non-fast-forward" in err_text or "rejected" in err_text:
                last_err = f"non-fast-forward on attempt {attempt + 1}"
                continue
            last_err = (push.stderr or push.stdout or "").strip() or "unknown push failure"
            break
        except subprocess.CalledProcessError as e:
            last_err = e
            break

    sys.stderr.write(
        f"warning: push_event_to_main failed for {spec_id} ({step}): {last_err}\n"
    )
    return False


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


def _current_branch(repo_dir: str | Path | None) -> str:
    try:
        return _git(["rev-parse", "--abbrev-ref", "HEAD"], repo_dir).stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def _extract_step(new_line: str) -> str:
    try:
        return json.loads(new_line.strip()).get("step", "unknown")
    except Exception:
        return "unknown"


def _build_tree_with_temp_index(
    rel_path: str, blob_sha: str, repo_dir: str | Path | None
) -> str:
    """Build a new root tree atop ``origin/main`` with ``rel_path`` set to ``blob_sha``.

    Uses ``GIT_INDEX_FILE`` to isolate from the repo's main index. Equivalent
    to the ``ls-tree`` + ``mktree`` walk described in spec 0163 §2.1, but
    path-aware and substantially simpler (``update-index --add --cacheinfo``
    handles arbitrary nesting depth without a manual climb).
    """
    fd, index_path = tempfile.mkstemp(suffix=".index")
    os.close(fd)
    os.unlink(index_path)
    try:
        env = {**os.environ, "GIT_INDEX_FILE": index_path}
        cwd = str(repo_dir) if repo_dir else None
        subprocess.run(
            ["git", "read-tree", "origin/main"],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            [
                "git",
                "update-index",
                "--add",
                "--cacheinfo",
                f"100644,{blob_sha},{rel_path}",
            ],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return subprocess.run(
            ["git", "write-tree"],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    finally:
        if os.path.exists(index_path):
            os.unlink(index_path)


def read_events(
    events_dir: str | Path,
    spec_id: str,
    *,
    repo_root: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Read all events for a spec; returns [] if no source exists.

    Spec 0202 §2.4 — first tries ``dashboard/queue-state.json`` (inferred
    from ``events_dir`` as ``events_dir.parent.parent`` unless ``repo_root``
    is given explicitly), falls back to the legacy
    ``dashboard/events/NNNN.jsonl`` sidecar otherwise. Test fixtures that
    pass a bare ``tmp_path`` keep working through the fallback.
    """
    state_events = _events_from_queue_state(events_dir, spec_id, repo_root=repo_root)
    if state_events is not None:
        return state_events

    log = Path(events_dir) / f"{spec_id}.jsonl"
    if not log.exists():
        return []
    out: list[dict[str, Any]] = []
    for raw in log.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            # Skip malformed lines rather than crash the dashboard render
            continue
    return out


def _events_from_queue_state(
    events_dir: str | Path,
    spec_id: str,
    *,
    repo_root: str | Path | None,
) -> list[dict[str, Any]] | None:
    """Return events from queue-state.json, or ``None`` if the spec has no entry.

    Returning ``None`` (not ``[]``) means "no state-file entry exists, fall
    back to the sidecar." An empty list means "entry exists but has no
    events" — the sidecar is not consulted in that case.
    """
    if repo_root is None:
        ed = Path(events_dir)
        # Convention: events_dir = <repo_root>/dashboard/events. Walk up two
        # levels to find the repo root. If the structure doesn't match, the
        # state-file lookup will simply find nothing and the caller falls
        # back to the sidecar — no harm done.
        if ed.name == "events" and ed.parent.name == "dashboard":
            repo_root = ed.parent.parent
        else:
            return None
    state_path = Path(repo_root) / "dashboard" / "queue-state.json"
    if not state_path.exists():
        return None
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    entry = (data.get("specs") or {}).get(spec_id)
    if entry is None:
        return None
    events = entry.get("events")
    if events is None:
        return []
    return list(events)


def main(argv: list[str] | None = None) -> int:
    args = list(argv) if argv is not None else sys.argv[1:]
    push_to_main = False
    if "--push-to-main" in args:
        args.remove("--push-to-main")
        push_to_main = True
    if len(args) < 3 or args[0] in {"-h", "--help"}:
        print(
            "Usage: append_event.py [--push-to-main] <events_dir> <spec_id> <step> [data_json]"
        )
        return 1
    events_dir, spec_id, step = args[0], args[1], args[2]
    data = json.loads(args[3]) if len(args) > 3 else None
    path = append_event(events_dir, spec_id, step, data, push_to_main=push_to_main)
    print(f"wrote event to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

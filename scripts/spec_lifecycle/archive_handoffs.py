"""Handoff lifecycle: archive old files and clean superseded checkpoints (spec 0202 §2.3).

``handoffs/`` is capped at the most recent ``N = 20`` files; older files
move to ``handoffs/archive/YYYY-MM/`` keyed by the date prefix in the
filename (``YYYY-MM-DD-spec-NNNN-<slug>.md``). The archive folder is
git-tracked so history stays browsable (spec 0202 §2.3, brief's "four
baked-in decisions" item 2).

L-spec checkpoint handoffs (``kind: in-spec-checkpoint``) are cleaned up
when their parent spec writes its final post-deploy handoff. Both
predicates (``kind`` AND ``spec``) must match to fire — defends against
accidentally deleting an unrelated handoff that happens to share an ID.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from scripts.spec_lifecycle.checkpoint import CHECKPOINT_KIND, classify_handoff_kind
from scripts.spec_lifecycle.frontmatter import parse as parse_frontmatter

DEFAULT_CAP = 20
HANDOFF_FILENAME_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})-")


def _archive_target(handoffs_dir: Path, src: Path) -> Path | None:
    """Compute the archive destination for ``src``, or ``None`` if the name
    has no parseable date prefix (caller logs a warning and skips)."""
    m = HANDOFF_FILENAME_RE.match(src.name)
    if not m:
        return None
    year_month = m.group("date")[:7]  # "YYYY-MM"
    return handoffs_dir / "archive" / year_month / src.name


def _active_checkpoint_paths(handoffs_dir: Path, active_spec_ids: set[str]) -> set[Path]:
    """Identify checkpoint handoffs whose spec is still in flight; archive
    must skip these so the resume target isn't shuffled out from under
    ``/dev-next`` (spec 0202 §2.6 final paragraph)."""
    protected: set[Path] = set()
    if not active_spec_ids:
        return protected
    for entry in handoffs_dir.iterdir():
        if not entry.is_file() or entry.suffix != ".md":
            continue
        try:
            fm = parse_frontmatter(entry).frontmatter
        except OSError:
            continue
        if classify_handoff_kind(fm) != CHECKPOINT_KIND:
            continue
        if str(fm.get("spec", "")) in active_spec_ids:
            protected.add(entry)
    return protected


def archive_old_handoffs(
    handoffs_dir: str | Path,
    cap: int = DEFAULT_CAP,
    *,
    dry_run: bool = False,
    protect: set[Path] | None = None,
) -> list[tuple[Path, Path]]:
    """Move old handoffs out of the live folder into ``archive/YYYY-MM/``.

    Returns the list of ``(src, dst)`` pairs moved (or that would be moved
    when ``dry_run=True``). Sort key is the filename (date-prefixed →
    lexicographic = chronological); the newest ``cap`` files stay in place.

    Files whose names don't parse as ``YYYY-MM-DD-...`` are skipped and
    a warning is logged to stderr. Files passed in ``protect`` are kept
    in place regardless of cap (used to protect in-flight L-spec
    checkpoints — see ``_active_checkpoint_paths``).
    """
    d = Path(handoffs_dir)
    if not d.exists():
        return []
    protect = protect or set()
    candidates: list[Path] = []
    for entry in sorted(d.iterdir()):
        if not entry.is_file() or entry.suffix != ".md":
            continue
        if HANDOFF_FILENAME_RE.match(entry.name) is None:
            sys.stderr.write(
                f"archive_old_handoffs: skipping {entry.name} (no date prefix)\n"
            )
            continue
        candidates.append(entry)

    if len(candidates) <= cap:
        return []

    keep = set(candidates[-cap:])
    moved: list[tuple[Path, Path]] = []
    for src in candidates[:-cap] if cap > 0 else candidates:
        if src in keep or src in protect:
            continue
        dst = _archive_target(d, src)
        if dst is None:
            continue
        moved.append((src, dst))
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
    return moved


def cleanup_superseded_checkpoints(
    handoffs_dir: str | Path, spec_id: str
) -> list[Path]:
    """Delete in-spec-checkpoint handoffs for ``spec_id``.

    Both predicates must match: ``kind: in-spec-checkpoint`` AND
    ``spec: "<spec_id>"``. Returns the list of deleted paths. Called from
    ``/dev-next`` step 24a only after the final post-deploy handoff lands;
    a failed cycle that halts before step 24 leaves the checkpoint intact
    so the next ``/dev-next`` can resume from it (spec 0202 §2.3 last
    paragraph).
    """
    d = Path(handoffs_dir)
    if not d.exists():
        return []
    deleted: list[Path] = []
    for entry in sorted(d.iterdir()):
        if not entry.is_file() or entry.suffix != ".md":
            continue
        try:
            fm = parse_frontmatter(entry).frontmatter
        except OSError:
            continue
        if classify_handoff_kind(fm) != CHECKPOINT_KIND:
            continue
        if str(fm.get("spec", "")) != str(spec_id):
            continue
        sys.stderr.write(f"cleanup_superseded_checkpoints: deleting {entry}\n")
        entry.unlink()
        deleted.append(entry)
    return deleted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="archive_handoffs",
        description="Archive old handoffs into handoffs/archive/YYYY-MM/.",
    )
    parser.add_argument(
        "--handoffs-dir", default="handoffs", help="Live handoffs folder (default: handoffs)"
    )
    parser.add_argument(
        "--cap", type=int, default=DEFAULT_CAP,
        help=f"Number of files to keep in the live folder (default: {DEFAULT_CAP})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would move, but do not touch the filesystem.",
    )
    parser.add_argument(
        "--cleanup-spec", default=None,
        help="If set, also run cleanup_superseded_checkpoints for this spec ID.",
    )
    args = parser.parse_args(argv)

    moved = archive_old_handoffs(args.handoffs_dir, cap=args.cap, dry_run=args.dry_run)
    verb = "would move" if args.dry_run else "moved"
    for src, dst in moved:
        print(f"{verb} {src} -> {dst}")
    print(f"archive_handoffs: {verb} {len(moved)} files (cap={args.cap})")

    if args.cleanup_spec:
        if args.dry_run:
            print(f"archive_handoffs: --dry-run set, skipping cleanup for spec {args.cleanup_spec}")
        else:
            deleted = cleanup_superseded_checkpoints(args.handoffs_dir, args.cleanup_spec)
            for p in deleted:
                print(f"cleaned checkpoint {p}")
            print(f"archive_handoffs: cleaned {len(deleted)} checkpoints for spec {args.cleanup_spec}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

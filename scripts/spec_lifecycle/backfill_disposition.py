"""One-off backfill: add `disposition: archive` + `disposition_reason` to every
existing spec / draft that predates spec 0229's carve-out-disposition convention.

Run once during spec 0229.1's implementation:

    uv run python -m scripts.spec_lifecycle.backfill_disposition

The script is idempotent — files that already declare `disposition:` are left
untouched. It walks `specs/*.md` (top level) and `specs/drafts/*.md`. It does
NOT walk `specs/_templates/` (template refresh deferred per spec 0229.1 §5)
nor `specs/archive/` (archived specs are immutable historical record per the
same §5).

Insertion is text-level (locate the closing `---` of the frontmatter block and
insert the two new lines immediately before it). Avoids yaml round-trip churn
that would re-emit existing quoting/formatting choices.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .frontmatter import parse


BACKFILL_REASON = (
    "Pre-spec-0229 carve-out; disposition assigned retroactively to satisfy "
    "the new convention."
)


def _backfill_one(path: Path) -> bool:
    """Backfill a single spec/draft file.

    Returns True if the file was modified, False if it already declared
    `disposition` (idempotent skip).
    """
    parsed = parse(path)
    if not parsed.has_frontmatter:
        # No frontmatter at all → not a managed spec/draft; skip.
        return False
    if "disposition" in parsed.frontmatter:
        return False

    text = path.read_text()
    lines = text.splitlines(keepends=True)

    # Find the opening `---` then the closing `---` of the frontmatter block.
    if not lines or lines[0].rstrip("\n") != "---":
        return False
    closing_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\n") == "---":
            closing_idx = i
            break
    if closing_idx is None:
        return False

    new_lines = (
        lines[:closing_idx]
        + [
            "disposition: archive\n",
            f'disposition_reason: "{BACKFILL_REASON}"\n',
        ]
        + lines[closing_idx:]
    )
    path.write_text("".join(new_lines))
    return True


def _target_files(specs_root: Path) -> list[Path]:
    """Return the ordered set of files in scope.

    Top-level `specs/*.md` plus `specs/drafts/*.md`. `specs/_templates/` and
    `specs/archive/` are explicitly excluded per spec 0229.1 §5.
    """
    top = sorted(p for p in specs_root.glob("*.md") if p.is_file())
    drafts_dir = specs_root / "drafts"
    drafts = (
        sorted(p for p in drafts_dir.glob("*.md") if p.is_file())
        if drafts_dir.is_dir()
        else []
    )
    return top + drafts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--specs-root",
        default="specs",
        help="root of the specs tree (default: ./specs)",
    )
    args = parser.parse_args(argv)

    specs_root = Path(args.specs_root)
    if not specs_root.is_dir():
        print(f"error: specs root not found: {specs_root}", file=sys.stderr)
        return 2

    backfilled = 0
    skipped = 0
    for path in _target_files(specs_root):
        if _backfill_one(path):
            backfilled += 1
        else:
            skipped += 1

    print(
        f"backfilled {backfilled} files ({skipped} skipped — already had disposition)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

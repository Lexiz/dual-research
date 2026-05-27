"""Detect drift between a queued spec and the current `main`.

Called by `/dev-next` after pre-flight and before branching. Walks the spec body
for file:line citations and classifies whether each still resolves on disk.

Returns a `ReconcileReport` with four buckets:

- `clean`: citations that still point at existing files within range.
- `mechanical`: file path moved or line number past end-of-file; auto-patchable.
- `semantic`: file deleted entirely or absent under any plausible new path.
- `out_of_tree`: citation path begins with a configured skip-list prefix
  (default `cowork/`); not classified against the on-disk tree — informational
  only, does NOT contribute to `has_blocking_drift`. See spec 0230.

The skill consuming this decides whether to auto-patch (mechanical) or halt
with status: failed, failure_step: reconcile (semantic).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .frontmatter import parse

CITATION_RE = re.compile(
    r"(?P<path>[\w\-/.]+\.(?:py|jsx|tsx|js|ts|css|md|yaml|yml|toml|json)):(?P<line>\d+)"
)

LINK_DISPLAY_RE = re.compile(r"\[([^\]\n]*?)\]\(([^)\n]*?)\)")

# Spec 0230 §2.1 — citations whose path begins with any of these prefixes are
# treated as informational rather than fed into the clean/mechanical/semantic
# classifier. Cowork artefacts live outside the repo by CLAUDE.md convention
# (the "Cowork channel lives outside the repo" subsection); without this skip
# every spec body citing `cowork/briefs/...` trips a false-positive exit-3.
# Callers that need a different skip set pass `out_of_tree_prefixes=(...)` to
# `reconcile_spec`. The trailing slash is intentional — `cowork-design-system/`
# does NOT match `cowork/`.
OUT_OF_TREE_PREFIXES: tuple[str, ...] = ("cowork/",)


def _scrub_link_display_text(body: str) -> str:
    """Replace the display-text region of every `[display](href)` with spaces.

    Preserves byte offsets so downstream regex matches retain their original
    positions. Citations inside link display text — the structurally-redundant
    cosmetic shadow of the href — no longer match `CITATION_RE`; the href is
    the structurally authoritative location and remains matchable.
    """

    def _sub(m: re.Match[str]) -> str:
        display = m.group(1)
        href = m.group(2)
        return "[" + " " * len(display) + "](" + href + ")"

    return LINK_DISPLAY_RE.sub(_sub, body)


@dataclass
class Citation:
    raw: str
    path: str
    line: int
    classification: str = "unknown"  # clean | mechanical | semantic | out_of_tree
    note: str = ""


@dataclass
class ReconcileReport:
    spec_path: Path
    clean: list[Citation] = field(default_factory=list)
    mechanical: list[Citation] = field(default_factory=list)
    semantic: list[Citation] = field(default_factory=list)
    # Spec 0230 — informational bucket; does NOT contribute to has_blocking_drift.
    out_of_tree: list[Citation] = field(default_factory=list)

    @property
    def has_drift(self) -> bool:
        return bool(self.mechanical) or bool(self.semantic)

    @property
    def has_blocking_drift(self) -> bool:
        return bool(self.semantic)


def reconcile_spec(
    spec_path: str | Path,
    *,
    repo_root: str | Path,
    out_of_tree_prefixes: tuple[str, ...] = OUT_OF_TREE_PREFIXES,
) -> ReconcileReport:
    spec = Path(spec_path)
    root = Path(repo_root)
    parsed = parse(spec)
    report = ReconcileReport(spec_path=spec)

    citations = _extract_citations(parsed.body)
    for cit in citations:
        # Spec 0230 §2.3 — prefix-skip fires before on-disk classification.
        # Out-of-tree paths (default `cowork/`) cannot be verified against the
        # repo tree by construction (they live outside the repo); routing them
        # here keeps the clean/mechanical/semantic taxonomy honest and prevents
        # the recurring false-positive exit-3 class.
        if any(cit.path.startswith(p) for p in out_of_tree_prefixes):
            cit.classification = "out_of_tree"
            cit.note = "path begins with skip-list prefix; not classified against tree"
            report.out_of_tree.append(cit)
            continue
        target = root / cit.path
        if target.exists():
            try:
                line_count = sum(1 for _ in target.open("r", encoding="utf-8"))
            except (UnicodeDecodeError, OSError):
                line_count = 0
            if cit.line <= line_count:
                cit.classification = "clean"
                report.clean.append(cit)
            else:
                cit.classification = "mechanical"
                cit.note = f"line {cit.line} is past EOF ({line_count} lines)"
                report.mechanical.append(cit)
        else:
            # Try to locate the basename anywhere in the tree as a moved-file hint
            basename = Path(cit.path).name
            candidates = _find_candidates(root, basename)
            if candidates:
                cit.classification = "mechanical"
                cit.note = f"file moved? candidates: {', '.join(candidates[:3])}"
                report.mechanical.append(cit)
            else:
                cit.classification = "semantic"
                cit.note = "file not found anywhere in tree"
                report.semantic.append(cit)

    return report


def _extract_citations(body: str) -> list[Citation]:
    out: list[Citation] = []
    seen: set[tuple[str, int]] = set()
    scrubbed = _scrub_link_display_text(body)
    for m in CITATION_RE.finditer(scrubbed):
        path = m.group("path")
        line = int(m.group("line"))
        key = (path, line)
        if key in seen:
            continue
        seen.add(key)
        out.append(Citation(raw=m.group(0), path=path, line=line))
    return out


def _find_candidates(root: Path, basename: str) -> list[str]:
    """Use `git ls-files` to find candidate paths matching basename."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [line for line in out.splitlines() if line.endswith("/" + basename) or line == basename]


def format_report(report: ReconcileReport) -> str:
    lines: list[str] = []
    lines.append(f"Spec: {report.spec_path}")
    lines.append(f"  clean: {len(report.clean)}")
    lines.append(f"  out-of-tree (informational): {len(report.out_of_tree)}")
    for cit in report.out_of_tree:
        lines.append(f"    {cit.raw} — {cit.note}")
    lines.append(f"  mechanical drift: {len(report.mechanical)}")
    for cit in report.mechanical:
        lines.append(f"    {cit.raw} — {cit.note}")
    lines.append(f"  semantic drift: {len(report.semantic)}")
    for cit in report.semantic:
        lines.append(f"    {cit.raw} — {cit.note}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import sys

    args = argv or sys.argv[1:]
    if not args or args[0] in {"-h", "--help"}:
        print("Usage: reconcile.py <spec-path> [repo-root]")
        return 1
    spec_path = Path(args[0])
    repo_root = Path(args[1]) if len(args) > 1 else spec_path.resolve().parent.parent
    report = reconcile_spec(spec_path, repo_root=repo_root)
    print(format_report(report))
    if report.has_blocking_drift:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

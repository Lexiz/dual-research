"""Detect drift between a queued spec and the current `main`.

Called by `/dev-next` after pre-flight and before branching. Walks the spec body
for file:line citations and classifies whether each still resolves on disk.

Returns a `ReconcileReport` with these buckets:

- `clean`: citations that still point at existing files within range.
- `mechanical`: file path moved or line number past end-of-file; auto-patchable.
- `semantic`: file deleted entirely or absent under any plausible new path.
- `out_of_tree`: citation path begins with a configured skip-list prefix
  (default `cowork/`); not classified against the on-disk tree — informational
  only, does NOT contribute to `has_blocking_drift`. See spec 0230.
- `unreachable`: spec 0258 — a §2 citation that exists on disk (and stays in
  `clean`) but resolves to a Python function not reachable from the live entry
  points. An orthogonal WARN-level overlay flagging a possible dead-surface
  citation; informational only, never contributes to `has_blocking_drift`, and
  never changes the CLI exit code.

The skill consuming this decides whether to auto-patch (mechanical) or halt
with status: failed, failure_step: reconcile (semantic).
"""

from __future__ import annotations

import ast
import re
import subprocess
from collections import deque
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

# Spec 0258 §2 — live entry points for the citation-liveness reporting check.
# A spec's `## 2` citation to a Python function not transitively reachable
# (by coarse bare-name BFS) from one of these roots is surfaced as a WARN-level
# informational flag — possible dead-surface citation. Adding a future live
# root is a one-line edit here. The BFS is anchored to the package below.
LIVE_ENTRY_POINTS: tuple[str, ...] = ("run_dr_phase2", "run_dr_phase4")

# Package walked to build the name -> def index and the reachable-symbol set.
PACKAGE_ROOT_REL = "src/dual_research"

# Note attached to every citation copied into `ReconcileReport.unreachable`.
UNREACHABLE_NOTE = (
    "citation not reachable from live entry points — possible dead-surface citation"
)


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
    classification: str = "unknown"  # clean | mechanical | semantic | out_of_tree | unreachable
    note: str = ""


@dataclass
class ReconcileReport:
    spec_path: Path
    clean: list[Citation] = field(default_factory=list)
    mechanical: list[Citation] = field(default_factory=list)
    semantic: list[Citation] = field(default_factory=list)
    # Spec 0230 — informational bucket; does NOT contribute to has_blocking_drift.
    out_of_tree: list[Citation] = field(default_factory=list)
    # Spec 0258 — informational overlay: §2 citations that exist on disk (and
    # stay in `clean`) but resolve to a Python function unreachable from the
    # live entry points. Orthogonal to the clean/mechanical/semantic taxonomy;
    # does NOT contribute to has_drift / has_blocking_drift and never changes
    # the CLI exit code. Reporting, not gating.
    unreachable: list[Citation] = field(default_factory=list)

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

    # Spec 0258 — citation-liveness reporting overlay. Runs AFTER existence
    # classification; scoped to citations inside the spec's `## 2` section.
    section_2_keys = {
        (c.path, c.line) for c in _extract_citations(_extract_section_2(parsed.body))
    }
    _check_citation_liveness(report, repo_root=root, section_2_keys=section_2_keys)

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


# --- Spec 0258: citation-liveness reporting check -------------------------
#
# A coarse, name-based caller-chain heuristic — NOT a sound call graph. It
# ignores scoping, import resolution, and dynamic dispatch by design (see the
# spec's §5 Out of scope and §7 Risks). False positives (e.g. string-dispatched
# symbols) are accepted WARN noise; the check never gates.


class _RefCollector(ast.NodeVisitor):
    """Collect every bare ``Name`` and ``Attribute.attr`` identifier referenced."""

    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:  # noqa: N802
        self.names.add(node.id)

    def visit_Attribute(self, node: ast.Attribute) -> None:  # noqa: N802
        self.names.add(node.attr)
        self.generic_visit(node)


def _build_reachable_symbols(
    repo_root: Path, *, entry_points: tuple[str, ...] = LIVE_ENTRY_POINTS
) -> set[str]:
    """Bare-name BFS over ``src/dual_research`` from the live entry points.

    Walks every module with ``ast``, indexing each ``def`` / ``async def`` name
    against the set of identifiers its body references. A symbol is *reachable*
    if it is referenced (by bare name) transitively from any entry point.
    """
    pkg = repo_root / PACKAGE_ROOT_REL
    if not pkg.exists():
        return set(entry_points)

    refs: dict[str, set[str]] = {}
    defnames: set[str] = set()
    for py in sorted(pkg.rglob("*.py")):
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defnames.add(node.name)
                collector = _RefCollector()
                for child in node.body:
                    collector.visit(child)
                refs.setdefault(node.name, set()).update(collector.names)

    reachable: set[str] = set(entry_points)
    queue: deque[str] = deque(ep for ep in entry_points if ep in refs)
    while queue:
        cur = queue.popleft()
        for ref in refs.get(cur, ()):
            if ref in defnames and ref not in reachable:
                reachable.add(ref)
                queue.append(ref)
    return reachable


def _extract_section_2(body: str) -> str:
    """Return the text of the spec's ``## 2`` section (heading-exclusive).

    Spans from just after the ``## 2`` heading to the next level-2 numbered
    heading (``## 3`` …) or end-of-body. Returns ``""`` if there is no ``## 2``.
    """
    start_m = re.search(r"^##\s+2\b.*$", body, re.MULTILINE)
    if start_m is None:
        return ""
    start = start_m.end()
    next_m = re.search(r"^##\s+\d", body[start:], re.MULTILINE)
    end = start + next_m.start() if next_m else len(body)
    return body[start:end]


def _resolve_symbol_at_line(path: Path, line: int) -> str | None:
    """Name of the innermost ``def`` / ``async def`` enclosing ``line``.

    Returns ``None`` for module-level lines, class bodies without a method,
    or unparseable files — those are never flagged.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None
    best: tuple[int, str] | None = None  # (span, name); smallest span = innermost
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", start) or start
            if start <= line <= end:
                span = end - start
                if best is None or span < best[0]:
                    best = (span, node.name)
    return best[1] if best else None


def _check_citation_liveness(
    report: ReconcileReport,
    *,
    repo_root: str | Path,
    section_2_keys: set[tuple[str, int]],
) -> None:
    """Append a WARN-level copy of every dead-surface §2 citation.

    For each citation already classified ``clean`` whose ``(path, line)`` is in
    the spec's ``## 2`` section, resolves to a Python ``def`` / ``async def``,
    and whose name is NOT reachable from the live entry points, append a *copy*
    to ``report.unreachable``. The original stays in ``clean`` (it does exist on
    disk) — this is an orthogonal advisory overlay, not a reclassification.
    """
    if not section_2_keys:
        return
    root = Path(repo_root)
    reachable = _build_reachable_symbols(root)
    pkg_prefix = PACKAGE_ROOT_REL + "/"
    for cit in report.clean:
        if (cit.path, cit.line) not in section_2_keys:
            continue
        # Spec 0258 §5 — only `.py` citations UNDER `src/dual_research/` are
        # analysed. The reachability index covers that package alone, so a
        # citation to dev tooling (`scripts/…`), tests, or any path outside it
        # has no reachability data and must not be flagged (it would be a
        # systematic false positive for every tooling-touching spec).
        if not cit.path.endswith(".py") or not cit.path.startswith(pkg_prefix):
            continue
        target = root / cit.path
        if not target.exists():
            continue
        symbol = _resolve_symbol_at_line(target, cit.line)
        if symbol is None or symbol in reachable:
            continue
        report.unreachable.append(
            Citation(
                raw=cit.raw,
                path=cit.path,
                line=cit.line,
                classification="unreachable",
                note=UNREACHABLE_NOTE,
            )
        )


def format_report(report: ReconcileReport) -> str:
    lines: list[str] = []
    lines.append(f"Spec: {report.spec_path}")
    lines.append(f"  clean: {len(report.clean)}")
    lines.append(f"  out-of-tree (informational): {len(report.out_of_tree)}")
    for cit in report.out_of_tree:
        lines.append(f"    {cit.raw} — {cit.note}")
    # Spec 0258 — informational; never affects exit status.
    lines.append(f"  unreachable (informational): {len(report.unreachable)}")
    for cit in report.unreachable:
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

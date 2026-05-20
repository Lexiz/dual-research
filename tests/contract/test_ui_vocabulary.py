"""Spec 0119 §13 — vocabulary-scan acceptance test.

Walks ``src/dual_research/ui/static/`` and asserts that none of the
retired pre-0119 chip-label literals appear in chip-rendering surfaces.

The forbidden set:

  * verbs:       ``'conceded'`` · ``'answered'`` · ``'noted'``
  * categories:  ``'Claim'`` / ``'Claims'`` (capital-C, to avoid
                 false positives on the lowercase noun in comments)
  * abbreviations: ``'QCR1'`` · ``'OQ'`` · ``'BD'`` · ``'OI'``
  * cap aliases: ``'ghosted'`` (chip context only)
  * legacy status: ``'repair'`` (chip context only)

A few legitimate code sites need to reference the legacy verbs:

  * the action-string normaliser in ``run-detail.jsx`` (``_mapVerdict``)
    is the boundary where pre-0114 wire-format verbs canonicalise into
    the spec-0119 lifecycle vocabulary;
  * the ``_isResolvedStatus`` predicate compares against the
    data-layer's ``q.status === 'answered'`` for legacy runs;
  * the disagreement-explorer's progression sentence inspects
    ``myProg.includes('conceded')`` to surface a Phase-2 transition.

Those lines (and any future legitimate references) carry an
explicit ``// spec-0119:vocab-ok`` marker. The scan ignores
markers AND pure JS/CSS comment lines.

If a hit appears in this test's output:

  * if it's a CHIP LABEL (user-visible text), rewrite it to the
    canonical vocabulary (e.g. ``conceded → resolved``);
  * if it's a data-layer comparison / canonicalisation site,
    add ``// spec-0119:vocab-ok`` to the line.

Don't loosen the rule unilaterally — surface the case to the
spec-0119 author and update both the rule and the spec.
"""

from __future__ import annotations

import re
from pathlib import Path


STATIC_DIR = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "dual_research"
    / "ui"
    / "static"
)

# Forbidden quoted-string patterns. Each entry is ``(regex, label,
# also_match_no_quotes)`` — the third item controls whether the
# pattern is also matched without surrounding quotes (used for
# all-caps abbreviations like OQ / BD that can't appear as raw
# identifiers but might appear in chip text without quoting).
FORBIDDEN = [
    (r"['\"]conceded['\"]", "verb literal 'conceded'"),
    (r"['\"]answered['\"]", "verb literal 'answered'"),
    (r"['\"]noted['\"]", "verb literal 'noted'"),
    (r"['\"]Claim['\"]", "category label 'Claim'"),
    (r"['\"]Claims['\"]", "category label 'Claims'"),
    (r"['\"]QCR1['\"]", "legacy abbreviation 'QCR1'"),
    (r"\bOQ\b(?!\w)", "legacy abbreviation 'OQ'"),
    (r"\bBD\b(?!\w)", "legacy abbreviation 'BD'"),
    (r"\bOI\b(?!\w)", "legacy abbreviation 'OI'"),
    (r"['\"]ghosted['\"]", "cap-alias verb 'ghosted'"),
    # ``'repair'`` appears in legacy turn-key prefixes (``-repair``,
    # ``-hashdrift-repair``) that are data-layer keys, not chip
    # labels. Restrict the pattern to standalone quoted strings, not
    # substring matches inside other identifiers.
    (r"^[^a-zA-Z_-]*['\"]repair['\"]", "chip-label 'repair'"),
]

ALLOW_MARKER = "spec-0119:vocab-ok"


def _strip_line_comment(line: str) -> str:
    """Return the line with trailing ``// ...`` JS comments removed.

    Best-effort: doesn't try to handle ``//`` inside string literals;
    pre-0119 callsites never embed ``//`` inside chip-label strings
    so this is safe for the scan.
    """
    # Pure-comment line: nothing to scan.
    stripped = line.lstrip()
    if stripped.startswith("//") or stripped.startswith("*"):
        return ""
    # Inline trailing comment.
    idx = line.find("//")
    if idx >= 0:
        return line[:idx]
    return line


def _is_pure_block_comment(line: str) -> bool:
    s = line.strip()
    return s.startswith("/*") or s.startswith("*") or s == "*/"


def _strip_comments_for_scan(text: str) -> list[tuple[int, str]]:
    """Strip out every kind of comment so a line-level scan only sees
    code that could plausibly emit a user-visible label.

    Handles:
      • ``// trailing`` JS line comments
      • ``/* … */`` multi-line JS block comments (any extent)
      • ``{/* … */}`` JSX comments (any extent)
      • Full-line ``*`` continuation inside a block-comment body

    Returns ``[(lineno, stripped_line), …]`` for every non-empty
    stripped line. Lineno is 1-based and matches the original source.
    """
    out: list[tuple[int, str]] = []
    in_block = False  # inside /* ... */
    in_jsx = False    # inside {/* ... */}

    for lineno, raw in enumerate(text.splitlines(), start=1):
        s = raw
        cleaned_parts: list[str] = []
        i = 0
        while i < len(s):
            if in_block:
                end = s.find("*/", i)
                if end == -1:
                    i = len(s)
                else:
                    in_block = False
                    i = end + 2
            elif in_jsx:
                end = s.find("*/}", i)
                if end == -1:
                    i = len(s)
                else:
                    in_jsx = False
                    i = end + 3
            else:
                # Look for the earliest comment start.
                line_idx = s.find("//", i)
                blk_idx = s.find("/*", i)
                jsx_idx = s.find("{/*", i)
                candidates = [
                    (idx, kind) for idx, kind in (
                        (line_idx, "line"),
                        (blk_idx, "blk"),
                        (jsx_idx, "jsx"),
                    ) if idx >= 0
                ]
                if not candidates:
                    cleaned_parts.append(s[i:])
                    break
                candidates.sort()
                idx, kind = candidates[0]
                cleaned_parts.append(s[i:idx])
                if kind == "line":
                    i = len(s)
                elif kind == "jsx":
                    end = s.find("*/}", idx + 3)
                    if end == -1:
                        in_jsx = True
                        i = len(s)
                    else:
                        i = end + 3
                else:  # blk
                    end = s.find("*/", idx + 2)
                    if end == -1:
                        in_block = True
                        i = len(s)
                    else:
                        i = end + 2
        cleaned = "".join(cleaned_parts).strip()
        if cleaned:
            out.append((lineno, cleaned))
    return out


def _iter_static_files() -> list[Path]:
    files: list[Path] = []
    for ext in (".jsx", ".js", ".css", ".html"):
        files.extend(STATIC_DIR.rglob("*" + ext))
    return sorted(files)


def test_no_forbidden_chip_label_literals() -> None:
    failures: list[str] = []

    for path in _iter_static_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        raw_lines = text.splitlines()
        for lineno, scan_line in _strip_comments_for_scan(text):
            raw = raw_lines[lineno - 1] if lineno - 1 < len(raw_lines) else scan_line
            if ALLOW_MARKER in raw:
                continue
            for pattern, label in FORBIDDEN:
                if re.search(pattern, scan_line):
                    rel = path.relative_to(STATIC_DIR.parent.parent.parent.parent)
                    failures.append(
                        f"{rel}:{lineno}: {label}\n  {raw.rstrip()}"
                    )
                    break

    assert not failures, (
        "Spec 0119 §13 vocabulary scan found forbidden chip-label "
        "literals in chip-rendering surfaces:\n\n"
        + "\n".join(failures)
        + "\n\nEither rewrite to the canonical vocabulary, or — if "
        "the literal is a legitimate data-layer comparison / "
        "canonicalisation site — add ``// "
        + ALLOW_MARKER
        + "`` to the line."
    )


def test_claim_grep_in_run_detail_jsx() -> None:
    """Acceptance: ``git grep claim src/dual_research/ui/static/run-detail.jsx``
    returns 0 hits outside comments.

    Stricter than the generic forbidden-literal scan above — this is
    specifically the §13 acceptance criterion. Allows the same
    ``spec-0119:vocab-ok`` marker and pure comments.
    """
    path = STATIC_DIR / "run-detail.jsx"
    text = path.read_text(encoding="utf-8")
    raw_lines = text.splitlines()
    failures: list[str] = []
    claim_re = re.compile(r"\bclaim", re.IGNORECASE)
    for lineno, scan_line in _strip_comments_for_scan(text):
        raw = raw_lines[lineno - 1] if lineno - 1 < len(raw_lines) else scan_line
        if ALLOW_MARKER in raw:
            continue
        if claim_re.search(scan_line):
            failures.append(f"run-detail.jsx:{lineno}: {raw.rstrip()}")

    assert not failures, (
        "Spec 0119 §13 — ``claim`` references found in run-detail.jsx "
        "outside comments:\n\n" + "\n".join(failures)
    )

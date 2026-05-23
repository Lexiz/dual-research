"""Type-aware validator for dev specs and drafts.

A dev spec must pass `validate_dev_spec` before it can be queued or promoted.
Drafts pass a much weaker shape-only check via `validate_draft`.

Run from CLI for one-off checks:

    uv run python -m scripts.spec_lifecycle.validator specs/0156-foo.md
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .frontmatter import parse, ParsedFile

VALID_TYPES = {"new-feature", "bug", "refactoring", "test", "breaking"}
VALID_STATUSES = {"queued", "in_progress", "merged", "deployed", "failed", "cancelled"}

DEV_REQUIRED_FRONTMATTER = {
    "kind",
    "spec",
    "slug",
    "title",
    "type",
    "label",
    "version_bump",
    "status",
}

DRAFT_REQUIRED_FRONTMATTER = {"kind", "draft_id", "slug", "title", "status"}

# Citation: <path>.<ext>:<line> OR a plain repo path like src/dual_research/foo.py
# (without line number). The plain-path form counts as a citation when at least
# one explicit file:line citation is also present; this keeps the bar high while
# allowing specs that talk about whole modules.
CITATION_LINE_RE = re.compile(r"[\w\-/.]+\.(?:py|jsx|tsx|js|ts|css|md|yaml|yml|toml|json):\d+")
CITATION_PATH_RE = re.compile(r"\b(?:src|specs|scripts|tests|handoffs|dashboard|\.github)/[\w\-/.]+\.(?:py|jsx|tsx|js|ts|css|md|yaml|yml|toml|json|sh)\b")
CHECKBOX_RE = re.compile(r"^\s*-\s*\[[ x]\]\s*\S", re.MULTILINE)
# Spec 0198 §2.1 — bracketed unresolved-decision markers, widened beyond [TBD].
UNRESOLVED_MARKER_RE = re.compile(r"\[(TBD|TODO|FIXME)\]")
# Spec 0198 §2.1 — "???" followed by ≥ 3 characters (heuristic for left-over thinking-out-loud).
TRIPLE_QUESTION_RE = re.compile(r"\?{3,}[A-Za-z0-9_\-]{3,}")
# Spec 0198 §2.1 — heading-anchored regex for the five forbidden section names.
OPEN_QUESTIONS_HEADING_RE = re.compile(
    r"^#{1,6}\s+(?:\d+\.?\d*\.?\s+)?"
    r"(open\s+questions?|unresolved\s+questions?|to\s+decide|tbd|outstanding\s+decisions?)\b",
    re.MULTILINE | re.IGNORECASE,
)
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")

# Spec 0198 §2.2 — source-artifact traceability.
# Detect file-path references to source artifacts that demand a traceability table.
# Bare-word forms ("mockup", "canvas", "ideation doc") are too common in normal
# prose to enforce at the validator — those are checked by the spec-queue /
# spec-promote skills, which have full conversation context to disambiguate.
SOURCE_ARTIFACT_RE = re.compile(
    r"(?:"
    r"prototypes/[\w\-]+/NOTES\.md"
    r"|prototypes/[\w\-]+/V2-SNAPSHOT\.md"
    r"|prototypes/[\w\-]+/(?:[\w\-]+/)*[A-Za-z0-9_\-]+\.md"
    r")",
    re.IGNORECASE,
)
# Header signature for the traceability table: `source item | source quote/ref | spec section`.
TRACE_TABLE_HEADER_RE = re.compile(
    r"\|\s*source\s+item\s*\|\s*source\s+(?:quote|ref|quote/ref|quote\s*/\s*ref)\s*\|\s*spec\s+section\s*\|",
    re.IGNORECASE,
)
# A row's `spec section` cell must point to a §2.N body heading OR a §5 deferral.
TRACE_ROW_SECTION_OK_RE = re.compile(
    r"§\s*(?:2\.\d+|5\b|out\s+of\s+scope)",
    re.IGNORECASE,
)
# Spec 0198 §2.3 — UI specs need user stories + BDD acceptance criteria.
UI_PATH_RE = re.compile(r"(?:src/dual_research/ui/|design-system/assets/)")
USER_STORY_RE = re.compile(
    r"As\s+an?\s+[^,\n]+,\s*I\s+want\s+[^,\n]+,\s*so\s+that\s+[^\n]+",
    re.IGNORECASE,
)
BDD_SCENARIO_RE = re.compile(
    r"GIVEN[^\n]+\n[^\n]*WHEN[^\n]+\n[^\n]*THEN[^\n]+",
    re.IGNORECASE,
)


def _strip_code(body: str) -> str:
    """Remove fenced blocks and inline backtick spans — used for prose-only checks."""
    body = FENCED_CODE_RE.sub("", body)
    body = INLINE_CODE_RE.sub("", body)
    return body


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:  # convenience
        return self.ok


def validate_dev_spec(path: str | Path) -> ValidationResult:
    parsed = parse(path)
    fm = parsed.frontmatter
    body = parsed.body
    errors: list[str] = []
    warnings: list[str] = []

    # Frontmatter shape
    missing = DEV_REQUIRED_FRONTMATTER - set(fm.keys())
    if missing:
        errors.append(f"missing required frontmatter keys: {sorted(missing)}")

    if fm.get("kind") != "dev":
        errors.append(f"frontmatter `kind` must be 'dev', got {fm.get('kind')!r}")

    spec_type = fm.get("type")
    if spec_type not in VALID_TYPES:
        errors.append(f"frontmatter `type` must be one of {sorted(VALID_TYPES)}, got {spec_type!r}")

    if fm.get("status") not in VALID_STATUSES:
        errors.append(
            f"frontmatter `status` must be one of {sorted(VALID_STATUSES)}, got {fm.get('status')!r}"
        )

    label = fm.get("label")
    if label and label != spec_type:
        warnings.append(f"frontmatter `label` ({label!r}) does not mirror `type` ({spec_type!r})")

    # Body shape — strip code spans for prose-only checks
    prose = _strip_code(body)

    # Citations: count explicit file:line OR plain repo paths, require at least
    # 2 total AND at least 1 explicit file:line OR ≥3 plain paths.
    line_cites = CITATION_LINE_RE.findall(body)
    path_cites = CITATION_PATH_RE.findall(body)
    total_cites = len(line_cites) + len(path_cites)
    if len(line_cites) >= 1 and total_cites >= 2:
        pass  # OK
    elif len(path_cites) >= 3:
        pass  # OK — module-level spec without specific line refs
    else:
        errors.append(
            f"need ≥2 file:line citations in body (or ≥3 repo paths) "
            f"(found {len(line_cites)} file:line, {len(path_cites)} paths)"
        )

    # Spec 0198 §2.1 — bracketed unresolved-decision markers + ??? heuristic.
    unresolved_hits = UNRESOLVED_MARKER_RE.findall(prose)
    if unresolved_hits:
        seen = sorted({f"[{m}]" for m in unresolved_hits})
        errors.append(
            f"body contains unresolved-decision markers in prose ({', '.join(seen)}) "
            "— dev specs must ship with all decisions resolved. "
            "Move to a draft via /spec-draft, or fold into §5 Out of scope with an explicit deferral target."
        )
    if TRIPLE_QUESTION_RE.search(prose):
        errors.append(
            "body contains `???`-style thinking-out-loud markers in prose "
            "— resolve before queueing"
        )

    heading_match = OPEN_QUESTIONS_HEADING_RE.search(body)
    if heading_match:
        heading_text = heading_match.group(0).strip()
        errors.append(
            f"body contains an open-questions heading ('{heading_text}') "
            "— dev specs must ship with all decisions resolved. "
            "Move to a draft via /spec-draft, or fold into §5 Out of scope with an explicit deferral target."
        )

    # Spec 0198 §2.2 — source-artifact traceability.
    errors.extend(_check_source_traceability(body))

    # Spec 0198 §2.3 — UI specs require user stories + BDD scenarios.
    errors.extend(_check_user_stories_for_ui_specs(body))

    # Dangling questions (heuristic: lines ending in `?`) — warning only.
    # Strip code spans first to avoid false positives from inline doc text.
    danglers = [
        line for line in prose.splitlines()
        if line.strip().endswith("?") and not line.strip().startswith(">")
    ]
    if danglers:
        warnings.append(
            f"{len(danglers)} line(s) end with `?` — verify each is rhetorical or resolved in the next line"
        )

    # Type-specific checks
    type_errors = _type_specific_checks(spec_type, body)
    errors.extend(type_errors)

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def _check_source_traceability(body: str) -> list[str]:
    """Spec 0198 §2.2 — when §1 cites a source artifact, require a traceability table.

    The validator enforces table SHAPE (header + ≥ 1 row + each row's section cell
    points to §2.N or §5). It does NOT count atomic items in the cited source file —
    that's the authoring skill's job (it has the source open during /spec-queue /
    /spec-promote and the user's intent in conversation).
    """
    # Look in §1 Context section first — that's where the spec says to detect sources.
    context_match = re.search(
        r"^##\s+1[\.\s].*?(?=^##\s|\Z)",
        body,
        re.MULTILINE | re.DOTALL,
    )
    if not context_match:
        return []
    context = context_match.group(0)
    # File-path source artifacts are typically inside backticks (e.g.,
    # `prototypes/foo/NOTES.md`) — search the raw context, not the stripped one.
    src_match = SOURCE_ARTIFACT_RE.search(context)
    if not src_match:
        return []

    errors: list[str] = []
    cited = src_match.group(0)

    if not TRACE_TABLE_HEADER_RE.search(body):
        errors.append(
            f"source traceability table missing — body cites source artifact "
            f"({cited!r}) but no table with header "
            f"`source item | source quote/ref | spec section` was found. "
            f"Every atomic item must either ship in §2.N or defer to §5 "
            f"with a named follow-up spec."
        )
        return errors

    rows = _extract_traceability_rows(body)
    if not rows:
        errors.append(
            f"source traceability table for {cited!r} has no data rows — "
            f"add one row per atomic item in the source."
        )
        return errors
    bad = [r for r in rows if not TRACE_ROW_SECTION_OK_RE.search(r["spec_section"])]
    if bad:
        examples = "; ".join(repr(r["spec_section"]) for r in bad[:3])
        errors.append(
            f"source traceability table has {len(bad)} row(s) where the spec-section "
            f"cell does not reference §2.N or §5 deferral: {examples}"
        )
    return errors


def _extract_traceability_rows(body: str) -> list[dict[str, str]]:
    """Extract data rows under the source-traceability table header.

    Returns a list of {source_item, source_quote, spec_section} dicts.
    Stops at the first blank line or non-pipe line after the table starts.
    """
    lines = body.splitlines()
    rows: list[dict[str, str]] = []
    i = 0
    while i < len(lines):
        if TRACE_TABLE_HEADER_RE.search(lines[i]):
            # Skip the separator line (|---|---|---|) if present.
            j = i + 1
            if j < len(lines) and re.match(r"^\s*\|[\s\-:|]+\|\s*$", lines[j]):
                j += 1
            while j < len(lines):
                line = lines[j]
                if not line.strip() or "|" not in line:
                    break
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 3:
                    rows.append(
                        {
                            "source_item": cells[0],
                            "source_quote": cells[1],
                            "spec_section": cells[2],
                        }
                    )
                j += 1
            return rows
        i += 1
    return rows


def _check_user_stories_for_ui_specs(body: str) -> list[str]:
    """Spec 0198 §2.3 — UI-touching specs need ≥ 1 user story + ≥ 2 BDD scenarios."""
    if not UI_PATH_RE.search(body):
        return []
    stories = USER_STORY_RE.findall(body)
    scenarios = BDD_SCENARIO_RE.findall(body)
    if len(stories) >= 1 and len(scenarios) >= 2:
        return []
    return [
        f"UI-touching spec missing user stories or BDD acceptance criteria. "
        f"Need ≥ 1 'As a X, I want Y, so that Z' (found {len(stories)}) "
        f"and ≥ 2 'GIVEN/WHEN/THEN' scenarios (found {len(scenarios)})."
    ]


def _type_specific_checks(spec_type: str | None, body: str) -> list[str]:
    errors: list[str] = []
    if spec_type == "new-feature" or spec_type == "breaking":
        if not CHECKBOX_RE.search(body):
            errors.append("`new-feature`/`breaking` specs need a Test plan with ≥2 falsifiable checkboxes")
        else:
            n = len(CHECKBOX_RE.findall(body))
            if n < 2:
                errors.append(f"Test plan needs ≥2 checkboxes (found {n})")
    elif spec_type == "bug":
        if not re.search(r"^\*\*Expected:\*\*", body, re.MULTILINE):
            errors.append("bug spec missing `**Expected:**` line in Reproduction")
        if not re.search(r"^\*\*Actual:\*\*", body, re.MULTILINE):
            errors.append("bug spec missing `**Actual:**` line in Reproduction")
        if not re.search(r"Regression[- ]prevention test", body, re.IGNORECASE):
            errors.append("bug spec missing `Regression-prevention test` section")
    elif spec_type == "refactoring":
        # Out of scope must explicitly disclaim new features
        # Look for the Out of scope section and check for the disclaimer
        m = re.search(r"##\s+\d*\.?\s*Out of scope(.*?)(?=^##\s|\Z)", body, re.MULTILINE | re.DOTALL)
        if not m:
            errors.append("refactoring spec missing `Out of scope` section")
        elif not re.search(r"(does NOT|no new) feature", m.group(1), re.IGNORECASE):
            errors.append(
                "refactoring spec `Out of scope` must explicitly disclaim new features"
            )
        if not re.search(r"Behavior preservation", body, re.IGNORECASE):
            errors.append("refactoring spec missing `Behavior preservation` section")
    elif spec_type == "test":
        if not re.search(r"Coverage gap", body, re.IGNORECASE):
            errors.append("test spec missing `Coverage gap` section")
    return errors


def validate_draft(path: str | Path) -> ValidationResult:
    parsed = parse(path)
    fm = parsed.frontmatter
    errors: list[str] = []
    warnings: list[str] = []

    missing = DRAFT_REQUIRED_FRONTMATTER - set(fm.keys())
    if missing:
        errors.append(f"missing required frontmatter keys: {sorted(missing)}")

    if fm.get("kind") != "draft":
        errors.append(f"frontmatter `kind` must be 'draft', got {fm.get('kind')!r}")

    if fm.get("status") != "draft":
        warnings.append(f"frontmatter `status` is {fm.get('status')!r}, expected 'draft'")

    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def main(argv: list[str] | None = None) -> int:
    args = argv or sys.argv[1:]
    if not args or args[0] in {"-h", "--help"}:
        print("Usage: validator.py <path-to-spec-or-draft>")
        return 1
    path = Path(args[0])
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    fm = parse(path).frontmatter
    kind = fm.get("kind")
    if kind == "draft":
        result = validate_draft(path)
    else:
        result = validate_dev_spec(path)

    for err in result.errors:
        print(f"ERROR: {err}", file=sys.stderr)
    for warn in result.warnings:
        print(f"WARNING: {warn}", file=sys.stderr)
    if result.ok:
        print(f"OK: {path}")
        return 0
    return 3


if __name__ == "__main__":
    raise SystemExit(main())

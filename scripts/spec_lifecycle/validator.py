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
TBD_RE = re.compile(r"\[TBD\]")
OPEN_QUESTIONS_HEADING_RE = re.compile(
    r"^#+\s*(?:\d+\.\s*)?Open questions\b", re.MULTILINE | re.IGNORECASE
)
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")


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

    if TBD_RE.search(prose):
        errors.append("body contains `[TBD]` markers in prose — resolve before queueing")

    if OPEN_QUESTIONS_HEADING_RE.search(body):
        errors.append(
            "body contains an 'Open questions' section — dev specs must have all questions resolved"
        )

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

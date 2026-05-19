"""Step 1 helper — parse a spec file into a structured dict.

The 13 design-system specs share a fixed section template:

    ---
    spec: 0092
    title: ...
    label: refactoring
    version-bump: PATCH
    ...
    ---

    # Spec 0092 — ...

    ## 1. Goal
    ## 2. Files touched
    ## 3. Material 3 anatomy
    ## 4. Notion issues addressed
    ## 5. Acceptance criteria
    ## 6. Visual verification matrix
    ## 7. Anti-pattern checks
    ## 8. Handover read
    ## 9. Spec rewrite mandate
    ## 10. Backend touched?
    ## 11. CSS class anchor list

The queue cares about the bulleted lists inside §§ 2, 4, 5, 6, 11 and
the prose pointer inside § 8 (Handover read). The parser is tolerant:
section ordering doesn't matter, blank sections return empty lists,
and a missing optional section returns ``None`` instead of raising.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


YAML_FENCE = "---"
HEADER_RE = re.compile(r"^##\s+(?P<num>\d{1,2})\.\s+(?P<title>.+?)\s*$")
BULLET_RE = re.compile(r"^[-*]\s+(?P<body>.+?)\s*$")
PATH_RE = re.compile(r"`([^`]+)`")
SHOT_LINE_RE = re.compile(
    r"^[-*]\s*`?(?P<viewport>\d{3,4}\s*[x×]\s*\d{3,4})`?"
    r"\s*(?P<theme>dark|light)"
    r"(?:\s*[—\-:]\s*(?P<rest>.+))?",
    re.IGNORECASE,
)


@dataclass
class VisualShot:
    viewport: str           # "2200×1300"
    theme: str              # "dark" or "light"
    detail: str = ""        # whatever follows the viewport+theme on the line


@dataclass
class ParsedSpec:
    spec: str               # zero-padded e.g. "0092"
    slug: str               # from filename
    title: str
    label: str              # new-feature | bug | refactoring | test | breaking
    version_bump: str       # MAJOR | MINOR | PATCH
    target_version: str
    file_path: str
    handover_read_paths: list[str] = field(default_factory=list)
    files_touched: list[str] = field(default_factory=list)
    notion_issues: list[str] = field(default_factory=list)
    design_anchors: list[str] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    visual_matrix: list[VisualShot] = field(default_factory=list)
    css_anchors: list[str] = field(default_factory=list)
    backend_touched: bool = False
    raw_sections: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["visual_matrix"] = [asdict(s) for s in self.visual_matrix]
        return d


def parse(path: str | Path) -> ParsedSpec:
    p = Path(path)
    text = p.read_text()
    fm, body = _split_frontmatter(text)
    spec = str(fm.get("spec", _spec_from_filename(p)))
    spec = spec.zfill(4)
    slug = _slug_from_filename(p)
    sections = _split_sections(body)

    files_touched = _bullet_paths(sections.get("2", ""))
    css_anchors = _code_block_lines(sections.get("11", ""))
    visual_matrix = _parse_visual_matrix(sections.get("6", ""))
    acceptance = _bullet_lines(sections.get("5", ""))
    handover_read_paths = _handover_paths(sections.get("8", ""))
    notion_issues = _notion_issues(sections.get("4", ""))
    design_anchors = _design_anchors(sections.get("3", "") + "\n" + sections.get("11", ""))
    backend_touched = _backend_flag(sections.get("10", ""))

    return ParsedSpec(
        spec=spec,
        slug=slug,
        title=str(fm.get("title", "")).strip(),
        label=str(fm.get("label", "")).strip(),
        version_bump=str(fm.get("version-bump", "")).strip(),
        target_version=str(fm.get("target-version", "")).strip(),
        file_path=str(p.resolve()),
        handover_read_paths=handover_read_paths,
        files_touched=files_touched,
        notion_issues=notion_issues,
        design_anchors=design_anchors,
        acceptance=acceptance,
        visual_matrix=visual_matrix,
        css_anchors=css_anchors,
        backend_touched=backend_touched,
        raw_sections=sections,
    )


def write_parsed(parsed: ParsedSpec, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(parsed.to_dict(), indent=2) + "\n")
    return target


# -- internals -------------------------------------------------------------


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != YAML_FENCE:
        return {}, text
    fm_lines: list[str] = []
    i = 1
    while i < len(lines) and lines[i].strip() != YAML_FENCE:
        fm_lines.append(lines[i])
        i += 1
    body = "\n".join(lines[i + 1 :])
    fm: dict[str, Any] = {}
    for raw in fm_lines:
        if ":" not in raw:
            continue
        k, _, v = raw.partition(":")
        fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, body


def _split_sections(body: str) -> dict[str, str]:
    """Return a {section_number: section_body} dict.

    Keys are the leading numeric (``"2"``, ``"11"``); body strips the
    heading line itself but preserves everything until the next ``##``.
    """
    out: dict[str, str] = {}
    current_key: str | None = None
    current_buf: list[str] = []
    for line in body.splitlines():
        m = HEADER_RE.match(line)
        if m:
            if current_key is not None:
                out[current_key] = "\n".join(current_buf).strip("\n")
            current_key = m.group("num")
            current_buf = []
        else:
            if current_key is not None:
                current_buf.append(line)
    if current_key is not None:
        out[current_key] = "\n".join(current_buf).strip("\n")
    return out


def _bullet_paths(section_body: str) -> list[str]:
    """Pull every path occurrence inside `backticks` on bullet lines."""
    out: list[str] = []
    for raw in section_body.splitlines():
        m = BULLET_RE.match(raw)
        if not m:
            continue
        head = m.group("body").split("—", 1)[0].split("--", 1)[0]
        paths = PATH_RE.findall(head)
        for p in paths:
            p = p.strip()
            if "/" in p or p.endswith((".toml", ".lock", ".jsx", ".css", ".py", ".html", ".md")):
                out.append(p)
    return list(dict.fromkeys(out))


def _bullet_lines(section_body: str) -> list[str]:
    out: list[str] = []
    for raw in section_body.splitlines():
        m = BULLET_RE.match(raw.lstrip())
        if not m:
            # checked / unchecked acceptance boxes also match.
            stripped = raw.lstrip()
            if stripped.startswith("- [ ]") or stripped.startswith("- [x]"):
                out.append(stripped[5:].strip())
            continue
        body = m.group("body").strip()
        if body.startswith("[ ]") or body.startswith("[x]"):
            body = body[3:].strip()
        out.append(body)
    return out


def _code_block_lines(section_body: str) -> list[str]:
    out: list[str] = []
    inside = False
    for raw in section_body.splitlines():
        if raw.strip().startswith("```"):
            inside = not inside
            continue
        if inside and raw.strip():
            out.append(raw.strip())
    return out


def _parse_visual_matrix(section_body: str) -> list[VisualShot]:
    out: list[VisualShot] = []
    for raw in section_body.splitlines():
        m = SHOT_LINE_RE.match(raw.lstrip())
        if not m:
            continue
        vp = m.group("viewport").replace(" ", "").replace("×", "x").lower()
        # Normalise to canonical form `2200x1300`
        out.append(
            VisualShot(
                viewport=vp,
                theme=m.group("theme").lower(),
                detail=(m.group("rest") or "").strip(),
            )
        )
    return out


def _handover_paths(section_body: str) -> list[str]:
    out: list[str] = []
    for token in PATH_RE.findall(section_body):
        token = token.strip()
        if token.endswith(".md"):
            out.append(token)
    return list(dict.fromkeys(out))


def _notion_issues(section_body: str) -> list[str]:
    out: list[str] = []
    # Lines like "Issue 7" or "issues 12 / 13 / 14 / 15"
    for raw in section_body.splitlines():
        for m in re.finditer(r"[Ii]ssue[s]?\s+([0-9 /,and]+)", raw):
            for tok in re.split(r"[\s/,]|and", m.group(1)):
                tok = tok.strip()
                if tok.isdigit():
                    out.append(tok.zfill(2))
    return list(dict.fromkeys(out))


def _design_anchors(text: str) -> list[str]:
    out = list({m.group(1) for m in re.finditer(r"#([a-z][a-z0-9-]+)", text)})
    # Filter to the documented anchors only — README §3 lists 27 of them.
    KNOWN = {
        "identity", "principles", "palette", "type", "icons", "fmt", "shape",
        "elevation", "system", "atoms", "cards", "tabs", "critique", "thread",
        "consumption", "input", "timeline", "modal", "tour", "how", "admin",
        "loading", "states", "a11y", "light", "responsive", "changelog",
    }
    return sorted(a for a in out if a in KNOWN)


def _backend_flag(section_body: str) -> bool:
    body = section_body.lower()
    if "**no.**" in body or "**no**" in body or body.startswith("no"):
        return False
    if "**yes.**" in body or "**yes**" in body or body.startswith("yes"):
        return True
    return False


def _spec_from_filename(p: Path) -> str:
    stem = p.stem
    return stem.split("-", 1)[0]


def _slug_from_filename(p: Path) -> str:
    stem = p.stem
    parts = stem.split("-", 1)
    return parts[1] if len(parts) > 1 else stem


__all__ = ["ParsedSpec", "VisualShot", "parse", "write_parsed"]

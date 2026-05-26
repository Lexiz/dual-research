#!/usr/bin/env python3
"""Generate `src/dual_research/ui/static/version-notes.json` from `CHANGELOG.md`.

Single source of truth for the in-app Changelog tab (spec 0220). Parses
CHANGELOG.md top-to-bottom, prettifies each entry deterministically
(regex-only — no LLM), classifies user-facing vs internal by inspecting
the linked spec body, merges per-version overrides from
`version-notes-overrides.json`, and writes a newest-first JSON array.

CLI:
    uv run python scripts/build_version_notes.py
    uv run python scripts/build_version_notes.py --check     # CI guard
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
OVERRIDES_PATH = REPO_ROOT / "src/dual_research/ui/static/version-notes-overrides.json"
OUTPUT_PATH = REPO_ROOT / "src/dual_research/ui/static/version-notes.json"
SPECS_DIR = REPO_ROOT / "specs"

VERSION_HEADING = re.compile(
    r"^## \[(?P<version>\d+\.\d+\.\d+)\] [—-] (?P<date>\d{4}-\d{2}-\d{2})\s*$"
)
UNRELEASED_HEADING = re.compile(r"^## \[Unreleased\]\s*$")
SECTION_HEADING = re.compile(r"^### (?P<label>Added|Changed|Removed|Fixed)\s*$")
BULLET = re.compile(r"^- (?P<body>.+)$")
SPEC_LINK = re.compile(r"\[spec (?P<id>\d+(?:\.\d+)?)\]\(specs/[^)]+\)")
SPEC_SENTINEL = "\x00SPEC{0}\x00"

# Path-shape visible text: contains at least one `/` and ends in `.<ext>` with
# an optional `:line` or `:line-line` suffix. Catches `src/.../foo.py:42`,
# `tests/test_foo.py`, `design-system/assets/styles/x.css`, etc.
PATH_SHAPE = re.compile(r"^[A-Za-z0-9_./\-]+/[A-Za-z0-9_./\-]+\.[A-Za-z0-9]+(?::\d+(?:-\d+)?)?$")

GENERIC_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
BOLD = re.compile(r"\*\*([^*]+)\*\*")
INLINE_CODE = re.compile(r"`([^`]+)`")

# "Previously X; now Y" / "Previously X. Now Y" → Now/Was anatomy.
NOW_WAS_PREV_NOW = re.compile(
    r"^Previously\s+(?P<was>.+?)\s*[;.]\s*(?:now|now,)\s+(?P<now>.+?)\.?$",
    re.IGNORECASE | re.DOTALL,
)

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z<])")

SPLIT_AT_CHARS = 240
SUMMARY_MAX_CHARS = 180
MIN_FRAGMENT_CHARS = 30

UI_FACING_RE = re.compile(r"src/dual_research/ui/static/|design-system/")


def parse_changelog(text: str) -> list[dict]:
    """Walk CHANGELOG.md top-to-bottom. Returns entries in file order
    (newest-first). `[Unreleased]` is skipped."""
    entries: list[dict] = []
    cur: dict | None = None
    cur_section: dict | None = None
    in_unreleased = False
    for line in text.splitlines():
        if UNRELEASED_HEADING.match(line):
            in_unreleased = True
            cur = None
            cur_section = None
            continue
        m = VERSION_HEADING.match(line)
        if m:
            in_unreleased = False
            cur = {"version": m["version"], "date": m["date"], "sections": []}
            entries.append(cur)
            cur_section = None
            continue
        if cur is None or in_unreleased:
            continue
        m = SECTION_HEADING.match(line)
        if m:
            cur_section = {"label": m["label"], "bullets": []}
            cur["sections"].append(cur_section)
            continue
        m = BULLET.match(line)
        if m and cur_section is not None:
            cur_section["bullets"].append(m["body"])
    return entries


def infer_bump(version: str, prev_version: str | None) -> str:
    if prev_version is None:
        return "MINOR"
    a = [int(n) for n in version.split(".")]
    b = [int(n) for n in prev_version.split(".")]
    if a[0] != b[0]:
        return "MAJOR"
    if a[1] != b[1]:
        return "MINOR"
    return "PATCH"


def extract_spec_ids(bullet_bodies: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for body in bullet_bodies:
        for m in SPEC_LINK.finditer(body):
            sid = m["id"]
            if sid not in seen:
                seen.add(sid)
                out.append(sid)
    return out


def prettify(body: str) -> str:
    """Regex-only prettify pass. Idempotent on already-prettified output
    because the patterns only fire on raw markdown."""
    spec_links: list[str] = []

    def _stash_spec(m: re.Match) -> str:
        spec_links.append(m.group(0))
        return SPEC_SENTINEL.format(len(spec_links) - 1)

    body = SPEC_LINK.sub(_stash_spec, body)

    def _process_link(m: re.Match) -> str:
        visible = m.group(1)
        if PATH_SHAPE.match(visible):
            return ""
        return visible

    body = GENERIC_LINK.sub(_process_link, body)

    for i, raw in enumerate(spec_links):
        body = body.replace(SPEC_SENTINEL.format(i), raw)

    body = BOLD.sub(r"<strong>\1</strong>", body)
    body = INLINE_CODE.sub(r"<code>\1</code>", body)

    # Tidy up artefacts from dropped path-links. The lookbehind on the
    # empty-paren cleanup guards against eating legitimate `foo()` calls —
    # path-drop garbage is always preceded by whitespace or sentence-edge,
    # never by a word character.
    body = re.sub(r"(?<=\s)\(\s*[,;]?\s*\)", "", body)
    body = re.sub(r"\s+([.,;:])", r"\1", body)
    body = re.sub(r"\(\s+", "(", body)
    body = re.sub(r"\s{2,}", " ", body)
    return body.strip()


def reshape_now_was(text: str) -> str:
    """Detect explicit `Previously X; now Y` pattern; emit Now/Was anatomy.
    Conservative — only fires on this exact shape. Other passive
    constructions are left as-is per §7 risk mitigation."""
    m = NOW_WAS_PREV_NOW.match(text.strip())
    if m:
        was = m["was"].strip().rstrip(".;,")
        now = m["now"].strip().rstrip(".;,")
        return f"<strong>Now</strong> {now}. <strong>Was</strong> {was}."
    return text


def split_long_bullet(text: str) -> list[str]:
    if len(text) <= SPLIT_AT_CHARS:
        return [text]
    parts = SENTENCE_SPLIT.split(text)
    if len(parts) == 1:
        return [text]
    out: list[str] = []
    buf = ""
    for part in parts:
        if not buf:
            buf = part
        elif len(buf) < MIN_FRAGMENT_CHARS:
            buf = buf + " " + part
        else:
            out.append(buf)
            buf = part
    if buf:
        out.append(buf)
    return out


def _strip_markdown_for_summary(raw: str) -> str:
    """Reduce a raw CHANGELOG bullet to plain text suitable for the summary."""
    text = SPEC_LINK.sub(lambda m: f"spec {m['id']}", raw)
    text = GENERIC_LINK.sub(
        lambda m: "" if PATH_SHAPE.match(m.group(1)) else m.group(1), text
    )
    text = BOLD.sub(r"\1", text)
    text = INLINE_CODE.sub(r"\1", text)
    text = re.sub(
        r"\b[A-Za-z0-9_./\-]+/[A-Za-z0-9_./\-]+\.[A-Za-z0-9]+(?::\d+(?:-\d+)?)?\b",
        "",
        text,
    )
    text = re.sub(r"\(\s*[,;]?\s*\)", "", text)
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def derive_summary(sections: list[dict]) -> str:
    """First sentence of the first raw bullet → summary. If > 180 chars,
    fall back to `<label>: <first-6-words>…`."""
    for section in sections:
        bullets = section.get("bullets", [])
        if not bullets:
            continue
        plain = _strip_markdown_for_summary(bullets[0])
        m = re.match(r"^(.{20,180}?[.!?])(?:\s|$)", plain)
        if m:
            return m.group(1).strip()
        words = re.findall(r"\S+", plain)[:6]
        return f"{section['label']}: {' '.join(words)}…"
    return ""


def classify_user_facing(spec_ids: list[str]) -> bool:
    """True if any cited spec's body references `src/dual_research/ui/static/`
    or `design-system/`. Missing spec on disk → True (conservative — surface
    the entry rather than silently hide it)."""
    if not spec_ids:
        return True
    for sid in spec_ids:
        matches = list(SPECS_DIR.glob(f"{sid}-*.md"))
        if not matches:
            return True
        try:
            body = matches[0].read_text(encoding="utf-8")
        except OSError:
            return True
        if UI_FACING_RE.search(body):
            return True
    return False


def build_entries(changelog_text: str) -> list[dict]:
    raw = parse_changelog(changelog_text)
    if not raw:
        return []
    # Walk oldest-first to infer bump from the previous version.
    out_oldest_first: list[dict] = []
    prev_version: str | None = None
    for entry in reversed(raw):
        version = entry["version"]
        sections = entry["sections"]
        items: list[str] = []
        for section in sections:
            for i, bullet in enumerate(section["bullets"]):
                p = prettify(bullet)
                p = reshape_now_was(p)
                if i == 0 and len(sections) > 1:
                    p = f"<strong>{section['label']}.</strong> {p}"
                items.extend(split_long_bullet(p))
        spec_ids = extract_spec_ids(
            [b for s in sections for b in s["bullets"]]
        )
        out_oldest_first.append(
            {
                "version": version,
                "date": entry["date"],
                "bump": infer_bump(version, prev_version),
                "summary": derive_summary(sections),
                "items": items,
                "specs": spec_ids,
                "user_facing": classify_user_facing(spec_ids),
                "screenshots": [],
            }
        )
        prev_version = version
    out_oldest_first.reverse()
    return out_oldest_first


def merge_overrides(entries: list[dict], overrides: dict) -> list[dict]:
    by_version = {e["version"]: e for e in entries}
    for version, override in overrides.items():
        if version in by_version:
            replacement = dict(override)
            replacement.setdefault("version", version)
            replacement.setdefault("screenshots", [])
            by_version[version] = replacement
    return [by_version[e["version"]] for e in entries]


def load_overrides() -> dict:
    if not OVERRIDES_PATH.exists():
        return {}
    return json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))


def render(entries: list[dict]) -> str:
    return json.dumps(entries, indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if regeneration would differ from the on-disk JSON sidecar.",
    )
    args = parser.parse_args(argv)

    changelog_text = CHANGELOG_PATH.read_text(encoding="utf-8")
    overrides = load_overrides()
    entries = build_entries(changelog_text)
    entries = merge_overrides(entries, overrides)
    rendered = render(entries)

    if args.check:
        on_disk = OUTPUT_PATH.read_text(encoding="utf-8") if OUTPUT_PATH.exists() else ""
        if on_disk != rendered:
            sys.stderr.write(
                "version-notes.json is stale. Run: "
                "uv run python scripts/build_version_notes.py\n"
            )
            return 1
        return 0

    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    sys.stdout.write(
        f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} ({len(entries)} entries)\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

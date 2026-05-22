"""Tests for scripts.spec_lifecycle.frontmatter."""

from __future__ import annotations

from pathlib import Path

from scripts.spec_lifecycle.frontmatter import parse, parse_text, dump, update_frontmatter


def test_parse_simple(tmp_path: Path) -> None:
    p = tmp_path / "x.md"
    p.write_text("---\nkey: value\nnumber: 42\n---\n\nHello body\n")
    parsed = parse(p)
    assert parsed.frontmatter == {"key": "value", "number": 42}
    assert parsed.body.strip() == "Hello body"


def test_parse_no_frontmatter() -> None:
    parsed = parse_text("just a body\nno frontmatter here\n")
    assert parsed.frontmatter == {}
    assert parsed.body.startswith("just a body")


def test_parse_malformed_yaml_treats_as_no_frontmatter() -> None:
    # YAML safe_load actually accepts a lot. Use input it cannot parse:
    # a mapping with duplicate keys and unbalanced flow style.
    parsed = parse_text("---\n[unclosed: yaml: oh: dear\n---\nbody\n")
    assert parsed.frontmatter == {}


def test_dump_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "x.md"
    p.write_text("---\na: 1\nb: two\n---\nbody text\n")
    parsed = parse(p)
    parsed.frontmatter["c"] = "added"
    text = dump(parsed)
    assert "a: 1" in text
    assert "b: two" in text
    assert "c: added" in text
    assert "body text" in text


def test_update_frontmatter_persists(tmp_path: Path) -> None:
    p = tmp_path / "x.md"
    p.write_text('---\nspec: "0001"\nstatus: queued\n---\nbody\n')
    update_frontmatter(p, {"status": "in_progress", "started_at": "2026-05-22T00:00:00Z"})
    reparsed = parse(p)
    assert reparsed.frontmatter["status"] == "in_progress"
    assert reparsed.frontmatter["started_at"] == "2026-05-22T00:00:00Z"
    assert reparsed.frontmatter["spec"] == "0001"  # untouched

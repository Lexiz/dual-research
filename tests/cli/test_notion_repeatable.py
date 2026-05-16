"""Spec 0036 — `--notion` is repeatable and combines with --brief/--prompt."""
from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from dual_research.cli import _build_parser, _derive_slug
from dual_research.ingest import build_brief


def _parse(argv: list[str]) -> argparse.Namespace:
    return _build_parser().parse_args(argv)


def test_notion_argparse_accepts_multiple_occurrences() -> None:
    args = _parse(["--notion", "URL_A", "--notion", "URL_B"])
    assert args.notion == ["URL_A", "URL_B"]


def test_notion_argparse_defaults_to_empty_list_when_omitted() -> None:
    args = _parse(["--prompt", "hi"])
    assert args.notion == []


def test_notion_single_value_still_works() -> None:
    args = _parse(["--notion", "URL"])
    assert args.notion == ["URL"]


def test_notion_combines_with_prompt_and_brief(tmp_path: Path) -> None:
    brief = tmp_path / "b.md"
    brief.write_text("# Brief\n", encoding="utf-8")
    args = _parse(["--brief", str(brief), "--prompt", "extra", "--notion", "URL_A"])
    assert args.brief == str(brief)
    assert args.prompt == "extra"
    assert args.notion == ["URL_A"]


def test_derive_slug_uses_first_notion_url_when_only_notion_given() -> None:
    args = _parse(["--notion", "https://notion.so/Workspace/Cool-Page-abc123"])
    slug = _derive_slug(args)
    assert slug != "notion"  # picked from URL, not the fallback


@pytest.mark.asyncio
async def test_build_brief_concatenates_brief_and_prompt(tmp_path: Path) -> None:
    brief = tmp_path / "b.md"
    brief.write_text("# Brief content\n", encoding="utf-8")
    args = argparse.Namespace(
        prompt="follow-up question",
        brief=str(brief),
        notion=[],
        attach=[],
    )
    result = await build_brief(args, notion_token=None)
    assert result.source_kind == "combined"
    assert "Brief content" in result.content
    assert "follow-up question" in result.content
    assert "# Source: " in result.content
    assert "\n---\n" in result.content


@pytest.mark.asyncio
async def test_build_brief_concatenates_multiple_notion_roots(tmp_path: Path) -> None:
    """Two Notion roots → both contents end up in the brief, in CLI order."""
    args = argparse.Namespace(
        prompt=None,
        brief=None,
        notion=["URL_A", "URL_B"],
        attach=[],
    )
    fake_a = AsyncMock(return_value=type(
        "R", (), {"content": "ROOT_A_BODY\n", "attachments": []}
    )())
    fake_b = AsyncMock(return_value=type(
        "R", (), {"content": "ROOT_B_BODY\n", "attachments": []}
    )())
    # notion_to_brief is called once per --notion root; cycle through the mocks.
    calls = [fake_a, fake_b]
    async def _stub(url, *, token, limits=None):
        return await calls.pop(0)()
    with patch("dual_research.ingest.notion_to_brief", side_effect=_stub):
        result = await build_brief(args, notion_token="x")
    assert result.source_kind == "combined"
    assert "ROOT_A_BODY" in result.content
    assert "ROOT_B_BODY" in result.content
    # Order preserved.
    assert result.content.index("ROOT_A_BODY") < result.content.index("ROOT_B_BODY")
    # Each gets its own source divider.
    assert result.content.count("# Source: notion: URL_") == 2


@pytest.mark.asyncio
async def test_build_brief_single_source_has_no_divider(tmp_path: Path) -> None:
    """Single source falls through the legacy path — no `# Source:` header injected."""
    brief = tmp_path / "b.md"
    brief.write_text("# Brief\n\nbody\n", encoding="utf-8")
    args = argparse.Namespace(prompt=None, brief=str(brief), notion=[], attach=[])
    result = await build_brief(args, notion_token=None)
    assert result.source_kind == "markdown"
    assert "# Source: " not in result.content

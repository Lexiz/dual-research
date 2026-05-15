from __future__ import annotations

import argparse
from pathlib import Path

from dual_research.ingest.notion import (
    IngestLimits,
    NotionError,
    NotionIngestResult,
    notion_to_brief,
)
from dual_research.ingest.text import markdown_to_brief, prompt_to_brief


class IngestError(RuntimeError):
    pass


async def build_brief(
    args: argparse.Namespace,
    *,
    notion_token: str | None,
    limits: IngestLimits | None = None,
) -> "BriefResult":
    if args.prompt is not None:
        body = prompt_to_brief(args.prompt)
        return BriefResult(content=body, source_kind="prompt", source_ref="<inline>")
    if args.brief:
        path = Path(args.brief).expanduser().resolve()
        body = markdown_to_brief(path)
        return BriefResult(content=body, source_kind="markdown", source_ref=str(path))
    if args.notion:
        if not notion_token:
            raise IngestError("NOTION_TOKEN is required for --notion mode")
        result = await notion_to_brief(args.notion, token=notion_token, limits=limits)
        return BriefResult(
            content=result.content,
            source_kind="notion",
            source_ref=args.notion,
            notion=result,
        )
    raise IngestError("no input source set (CLI should have rejected this already)")


from dataclasses import dataclass, field


@dataclass
class BriefResult:
    content: str
    source_kind: str
    source_ref: str
    notion: NotionIngestResult | None = None

    @property
    def char_count(self) -> int:
        return len(self.content)

    @property
    def line_count(self) -> int:
        return self.content.count("\n") + (0 if self.content.endswith("\n") else 1)


__all__ = [
    "BriefResult",
    "IngestError",
    "IngestLimits",
    "NotionError",
    "build_brief",
]

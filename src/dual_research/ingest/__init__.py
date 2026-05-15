from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

from dual_research.ingest.attachments import (
    Attachment,
    AttachmentBundle,
    attach_local_file,
    attach_url,
    materialise_local_markdown_attachments,
    scan_markdown_attachments,
)
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
    """Build a `BriefResult` from CLI args.

    `args.attach` (added by spec 0025) is an optional list of strings;
    each value is a local path (copied into the session-dir at
    materialise time) or a URL (recorded as-is). Markdown bodies are
    additionally scanned for `![alt](url)` / `[label](url)` and bare
    URLs — relative local paths are kept as absolute references for
    later copying.
    """
    attach_args: list[str] = list(getattr(args, "attach", None) or [])
    if args.prompt is not None:
        body = prompt_to_brief(args.prompt)
        attachments = scan_markdown_attachments(body, base_dir=Path.cwd())
        attachments.extend(_attach_args_to_attachments(attach_args))
        return BriefResult(
            content=body,
            source_kind="prompt",
            source_ref="<inline>",
            attachments=attachments,
        )
    if args.brief:
        path = Path(args.brief).expanduser().resolve()
        body = markdown_to_brief(path)
        attachments = scan_markdown_attachments(body, base_dir=path.parent)
        attachments.extend(_attach_args_to_attachments(attach_args))
        return BriefResult(
            content=body,
            source_kind="markdown",
            source_ref=str(path),
            attachments=attachments,
        )
    if args.notion:
        if not notion_token:
            raise IngestError("NOTION_TOKEN is required for --notion mode")
        result = await notion_to_brief(args.notion, token=notion_token, limits=limits)
        attachments = list(result.attachments)
        attachments.extend(_attach_args_to_attachments(attach_args))
        return BriefResult(
            content=result.content,
            source_kind="notion",
            source_ref=args.notion,
            notion=result,
            attachments=attachments,
        )
    raise IngestError("no input source set (CLI should have rejected this already)")


def _attach_args_to_attachments(values: list[str]) -> list[Attachment]:
    """Convert `--attach VALUE` strings into Attachment objects.

    URLs are recorded as link/image/pdf attachments by their scheme +
    extension; local paths are stored as not-yet-materialised entries
    (rel_path = absolute path) which the cli later copies into the
    session dir via `materialise_local_markdown_attachments`.
    """
    out: list[Attachment] = []
    for value in values:
        v = (value or "").strip()
        if not v:
            continue
        if v.startswith("http://") or v.startswith("https://"):
            out.append(attach_url(v, source=f"cli:{v}"))
            continue
        p = Path(v).expanduser()
        # Resolved absolute path stays as a marker for materialise step.
        try:
            resolved = p.resolve(strict=False)
        except OSError:
            resolved = p
        out.append(
            Attachment(
                kind=_kind_for_local(resolved.name),
                source=f"cli:{resolved}",
                title=resolved.name,
                rel_path=str(resolved),
            )
        )
    return out


def _kind_for_local(name: str) -> str:
    from dual_research.ingest.attachments import kind_from_ext

    return kind_from_ext(name)


@dataclass
class BriefResult:
    content: str
    source_kind: str
    source_ref: str
    notion: NotionIngestResult | None = None
    attachments: list[Attachment] = field(default_factory=list)

    @property
    def char_count(self) -> int:
        return len(self.content)

    @property
    def line_count(self) -> int:
        return self.content.count("\n") + (0 if self.content.endswith("\n") else 1)


__all__ = [
    "Attachment",
    "AttachmentBundle",
    "BriefResult",
    "IngestError",
    "IngestLimits",
    "NotionError",
    "attach_local_file",
    "attach_url",
    "build_brief",
    "materialise_local_markdown_attachments",
    "scan_markdown_attachments",
]

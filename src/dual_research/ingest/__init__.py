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

    Spec 0036: input sources can be freely combined. ``--prompt``,
    ``--brief``, and one-or-more ``--notion`` roots concatenate in the
    order: brief → notion roots (in CLI order) → prompt. Adjacent sources
    are separated by ``\\n\\n---\\n\\n# Source: <descriptor>\\n\\n``.
    Single-source invocations are byte-identical to pre-0036 behaviour
    (no separator added).

    ``args.attach`` (added by spec 0025) is an optional list of strings;
    each value is a local path (copied into the session-dir at
    materialise time) or a URL (recorded as-is). Markdown bodies are
    additionally scanned for ``![alt](url)`` / ``[label](url)`` and bare
    URLs — relative local paths are kept as absolute references for
    later copying.
    """
    attach_args: list[str] = list(getattr(args, "attach", None) or [])

    # Build component (descriptor, body, attachments, optional NotionIngestResult).
    components: list[tuple[str, str, list[Attachment], NotionIngestResult | None]] = []

    if args.brief:
        path = Path(args.brief).expanduser().resolve()
        body = markdown_to_brief(path)
        atts = scan_markdown_attachments(body, base_dir=path.parent)
        components.append((str(path), body, atts, None))

    notion_list: list[str] = list(getattr(args, "notion", None) or [])
    if notion_list and not notion_token:
        raise IngestError("NOTION_TOKEN is required for --notion mode")
    notion_results: list[NotionIngestResult] = []
    for n_url in notion_list:
        result = await notion_to_brief(n_url, token=notion_token, limits=limits)
        notion_results.append(result)
        components.append((f"notion: {n_url}", result.content, list(result.attachments), result))

    if args.prompt is not None:
        body = prompt_to_brief(args.prompt)
        atts = scan_markdown_attachments(body, base_dir=Path.cwd())
        components.append(("inline prompt", body, atts, None))

    if not components:
        raise IngestError("no input source set (CLI should have rejected this already)")

    # Compose final content.
    if len(components) == 1:
        descriptor, body, atts, notion_res = components[0]
        attachments = list(atts)
        attachments.extend(_attach_args_to_attachments(attach_args))
        return BriefResult(
            content=body,
            source_kind=_source_kind_for(args, single=True),
            source_ref=descriptor,
            notion=notion_res,
            attachments=attachments,
        )

    # Multi-source: stitch with a divider naming each source.
    parts: list[str] = []
    combined_attachments: list[Attachment] = []
    combined_ref_pieces: list[str] = []
    primary_notion: NotionIngestResult | None = None
    for i, (descriptor, body, atts, notion_res) in enumerate(components):
        if i > 0:
            parts.append("\n\n---\n\n")
        parts.append(f"# Source: {descriptor}\n\n")
        parts.append(body.rstrip("\n"))
        parts.append("\n")
        combined_attachments.extend(atts)
        combined_ref_pieces.append(descriptor)
        if primary_notion is None and notion_res is not None:
            primary_notion = notion_res
    combined_attachments.extend(_attach_args_to_attachments(attach_args))

    return BriefResult(
        content="".join(parts),
        source_kind="combined",
        source_ref=" + ".join(combined_ref_pieces),
        notion=primary_notion,
        attachments=combined_attachments,
    )


def _source_kind_for(args: argparse.Namespace, *, single: bool) -> str:
    """Return the single-source kind label (legacy semantics)."""
    if not single:
        return "combined"
    if args.prompt is not None:
        return "prompt"
    if args.brief:
        return "markdown"
    if getattr(args, "notion", None):
        return "notion"
    return "unknown"


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

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionError(RuntimeError):
    pass


@dataclass(frozen=True)
class IngestLimits:
    max_depth: int = 5
    max_pages: int = 100
    request_timeout: float = 30.0


@dataclass
class NotionIngestResult:
    content: str
    root_page_id: str
    pages_fetched: int
    pages_failed: list[tuple[str, str]] = field(default_factory=list)
    max_depth_reached: int = 0
    truncated: bool = False


_HEX32 = re.compile(r"([0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.IGNORECASE)


def extract_page_id(url_or_id: str) -> str:
    s = url_or_id.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    match = None
    for m in _HEX32.finditer(s):
        match = m
    if not match:
        raise NotionError(f"could not extract Notion page ID from: {url_or_id!r}")
    raw = match.group(1).replace("-", "").lower()
    if len(raw) != 32:
        raise NotionError(f"extracted ID not 32 hex chars: {raw}")
    return f"{raw[0:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:32]}"


def _rich_text_to_md(rich: list[dict] | None) -> str:
    if not rich:
        return ""
    parts: list[str] = []
    for r in rich:
        text = r.get("plain_text", "")
        ann = r.get("annotations") or {}
        href = r.get("href")
        if ann.get("code"):
            text = f"`{text}`"
        if ann.get("bold"):
            text = f"**{text}**"
        if ann.get("italic"):
            text = f"*{text}*"
        if ann.get("strikethrough"):
            text = f"~~{text}~~"
        if href and not ann.get("code"):
            text = f"[{text}]({href})"
        parts.append(text)
    return "".join(parts)


def _extract_page_title(page: dict) -> str:
    props = page.get("properties") or {}
    for v in props.values():
        if isinstance(v, dict) and v.get("type") == "title":
            return _rich_text_to_md(v.get("title", [])) or "(untitled)"
    return "(untitled)"


class _Client:
    def __init__(self, token: str, timeout: float):
        self._client = httpx.AsyncClient(
            base_url=NOTION_API,
            headers={
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def __aenter__(self) -> "_Client":
        return self

    async def __aexit__(self, *_exc) -> None:
        await self._client.aclose()

    async def _get(self, path: str, params: dict | None = None) -> dict:
        for attempt in range(3):
            try:
                r = await self._client.get(path, params=params)
            except httpx.RequestError as e:
                if attempt == 2:
                    raise NotionError(f"network error at {path}: {e}") from e
                await asyncio.sleep(1 + attempt)
                continue
            if r.status_code == 429:
                retry_after = float(r.headers.get("Retry-After", "1"))
                await asyncio.sleep(min(retry_after, 10))
                continue
            if r.status_code == 404:
                raise NotionError(
                    f"404 at {path} — page does not exist or is not shared with the integration"
                )
            if r.status_code == 401:
                raise NotionError("401 unauthorized — NOTION_TOKEN is invalid or revoked")
            if not r.is_success:
                raise NotionError(f"HTTP {r.status_code} at {path}: {r.text[:300]}")
            return r.json()
        raise NotionError(f"retries exhausted at {path}")

    async def get_page(self, page_id: str) -> dict:
        return await self._get(f"/pages/{page_id}")

    async def get_block_children(self, block_id: str) -> list[dict]:
        out: list[dict] = []
        cursor: str | None = None
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            data = await self._get(f"/blocks/{block_id}/children", params)
            out.extend(data.get("results", []))
            if not data.get("has_more"):
                return out
            cursor = data.get("next_cursor")
            if not cursor:
                return out


async def _render_blocks(
    client: _Client,
    blocks: list[dict],
    *,
    depth: int,
    child_pages_out: list[tuple[str, str]],
    indent: int = 0,
) -> str:
    parts: list[str] = []
    numbered_idx = 0
    prev_type: str | None = None

    pad = "  " * indent

    for block in blocks:
        bt = block.get("type", "")
        c = block.get(bt) or {}
        rich = c.get("rich_text")
        text = _rich_text_to_md(rich)

        if prev_type == "numbered_list_item" and bt != "numbered_list_item":
            numbered_idx = 0

        md: str = ""

        if bt == "paragraph":
            md = text
        elif bt == "heading_1":
            md = f"# {text}" if text else ""
        elif bt == "heading_2":
            md = f"## {text}" if text else ""
        elif bt == "heading_3":
            md = f"### {text}" if text else ""
        elif bt == "bulleted_list_item":
            md = f"- {text}"
        elif bt == "numbered_list_item":
            numbered_idx += 1
            md = f"{numbered_idx}. {text}"
        elif bt == "to_do":
            done = c.get("checked", False)
            md = f"- [{'x' if done else ' '}] {text}"
        elif bt == "quote":
            md = "\n".join(f"> {line}" for line in (text or "").splitlines()) or "> "
        elif bt == "callout":
            emoji = ((c.get("icon") or {}).get("emoji")) or ""
            prefix = f"{emoji} " if emoji else ""
            md = "\n".join(f"> {prefix if i == 0 else ''}{line}" for i, line in enumerate((text or "").splitlines())) or f"> {prefix}"
        elif bt == "code":
            lang = c.get("language") or ""
            md = f"```{lang}\n{text}\n```"
        elif bt == "divider":
            md = "---"
        elif bt == "toggle":
            md = f"**{text}**" if text else ""
        elif bt == "child_page":
            title = c.get("title") or "(untitled)"
            page_id = block.get("id", "")
            if page_id:
                child_pages_out.append((page_id, title))
            md = f"_[→ child page: {title}]_"
        elif bt == "child_database":
            title = c.get("title") or "(untitled database)"
            md = f"_[→ child database: {title}] (not traversed)_"
        elif bt == "image":
            file = c.get("file") or c.get("external") or {}
            url = file.get("url", "")
            caption = _rich_text_to_md(c.get("caption", []))
            md = f"![{caption}]({url})" if url else f"_[image: {caption or 'no caption'}]_"
        elif bt in ("bookmark", "embed", "link_preview"):
            url = c.get("url") or ""
            md = f"[{url}]({url})" if url else ""
        elif bt == "equation":
            expr = c.get("expression") or ""
            md = f"$$\n{expr}\n$$"
        elif bt == "table_row":
            cells = c.get("cells") or []
            md = "| " + " | ".join(_rich_text_to_md(cell) for cell in cells) + " |"
        elif bt in ("table", "column_list", "column", "synced_block"):
            md = ""
        elif bt == "unsupported":
            md = "_[unsupported block]_"
        else:
            md = f"_[block type `{bt}` not rendered]_"

        if md:
            if indent > 0:
                md = "\n".join(pad + line for line in md.splitlines())
            parts.append(md)

        if block.get("has_children") and bt != "child_page":
            try:
                nested = await client.get_block_children(block["id"])
            except NotionError:
                nested = []
            inner = await _render_blocks(
                client,
                nested,
                depth=depth,
                child_pages_out=child_pages_out,
                indent=indent + 1,
            )
            if inner:
                parts.append(inner)

        prev_type = bt

    return "\n\n".join(p for p in parts if p)


async def notion_to_brief(
    url_or_id: str,
    *,
    token: str,
    limits: IngestLimits | None = None,
) -> NotionIngestResult:
    lims = limits or IngestLimits()
    root_id = extract_page_id(url_or_id)

    seen: set[str] = set()
    queue: list[tuple[str, int]] = [(root_id, 0)]
    sections: list[str] = []
    failed: list[tuple[str, str]] = []
    max_depth_reached = 0
    truncated = False

    async with _Client(token, timeout=lims.request_timeout) as client:
        while queue:
            if len(seen) >= lims.max_pages:
                truncated = True
                break

            page_id, depth = queue.pop(0)
            if page_id in seen:
                continue
            seen.add(page_id)
            max_depth_reached = max(max_depth_reached, depth)

            try:
                page = await client.get_page(page_id)
            except NotionError as e:
                failed.append((page_id, str(e)))
                sections.append(
                    f"## Source: [unfetchable — id `{page_id}`]\n\n_{e}_\n"
                )
                continue

            title = _extract_page_title(page)
            page_url = page.get("url") or ""
            child_pages: list[tuple[str, str]] = []

            try:
                blocks = await client.get_block_children(page_id)
            except NotionError as e:
                failed.append((page_id, f"blocks fetch failed: {e}"))
                blocks = []

            body = await _render_blocks(
                client, blocks, depth=depth, child_pages_out=child_pages
            )

            header = f"## Source: {title}\n\n{page_url}".rstrip()
            sections.append(f"{header}\n\n{body}\n" if body else f"{header}\n\n_(empty page)_\n")

            if depth < lims.max_depth:
                for child_id, _child_title in child_pages:
                    norm = extract_page_id(child_id)
                    if norm not in seen:
                        queue.append((norm, depth + 1))

        if truncated:
            sections.append(
                f"\n---\n\n## [ingest truncated]\n\n"
                f"Reached max_pages limit ({lims.max_pages}). "
                f"{len(queue)} descendant page(s) were not fetched.\n"
            )

    header_lines = [
        "# Research brief",
        "",
        f"_Compiled from {len(seen)} Notion page(s) rooted at `{root_id}`._",
        f"_Max depth reached: {max_depth_reached}. "
        f"{'Truncated at max_pages cap.' if truncated else 'Complete tree fetched.'}_",
    ]
    if failed:
        header_lines.append(f"_{len(failed)} page(s) failed to fetch — see entries below._")
    header_lines.append("")
    content = "\n".join(header_lines) + "\n\n---\n\n" + "\n\n---\n\n".join(sections)

    return NotionIngestResult(
        content=content,
        root_page_id=root_id,
        pages_fetched=len(seen) - len(failed),
        pages_failed=failed,
        max_depth_reached=max_depth_reached,
        truncated=truncated,
    )

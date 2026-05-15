"""Attachment ingest — spec 0025.

`Attachment` is the dataclass surfaced by `BriefResult.attachments` and
written to `session_dir/attachments.json`. Three entry points capture
the universe of attachment sources:

- `scan_markdown_attachments(text, *, base_dir)` — pulls `![alt](url)`,
  `[label](url)`, and bare HTTP(S) URLs out of a markdown body. Local
  relative paths resolve against `base_dir`.
- `attach_local_file(path, *, dest_dir)` — hashes a local file and
  copies it to `dest_dir/<sha8>-<basename>`, returning the dataclass.
- `attach_url(url, *, title, caption)` — wraps a remote URL.

Kind is inferred from extension (or mime when known):

- `.png/.jpg/.jpeg/.gif/.webp/.svg/.heic`            → image
- `.pdf`                                             → pdf
- anything else local                                → file
- anything else remote                               → link

The kind taxonomy drives UI grouping in the preflight modal's Files vs
Sources tabs.
"""

from __future__ import annotations

import hashlib
import mimetypes
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


IMAGE_EXTS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".heic", ".bmp"})
PDF_EXTS = frozenset({".pdf"})


@dataclass(frozen=True)
class Attachment:
    """A single image / pdf / file / link entry alongside the brief."""

    kind: str  # "image" | "pdf" | "file" | "link"
    source: str
    title: str | None = None
    caption: str | None = None
    url: str | None = None
    rel_path: str | None = None
    mime: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Attachment":
        # Drop unknown keys defensively so a future schema addition
        # doesn't blow up older readers.
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


# ─── Kind inference ───────────────────────────────────────────────────────────


def kind_from_ext(name: str) -> str:
    """Pick the attachment kind from a filename or URL path component."""
    p = Path(name).suffix.lower()
    if p in IMAGE_EXTS:
        return "image"
    if p in PDF_EXTS:
        return "pdf"
    return "file"


def kind_for_url(url: str) -> str:
    """Same as kind_from_ext, but if no clear extension match → 'link'."""
    parsed = urlparse(url)
    path = parsed.path or ""
    p = Path(path).suffix.lower()
    if p in IMAGE_EXTS:
        return "image"
    if p in PDF_EXTS:
        return "pdf"
    return "link"


def mime_for(path_or_url: str, *, kind: str | None = None) -> str | None:
    guess, _enc = mimetypes.guess_type(path_or_url)
    if guess:
        return guess
    if kind == "image":
        return "image/png"  # safe default
    if kind == "pdf":
        return "application/pdf"
    return None


# ─── Local file → Attachment ──────────────────────────────────────────────────


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def attach_local_file(
    path: Path,
    *,
    dest_dir: Path,
    title: str | None = None,
    caption: str | None = None,
    source: str | None = None,
) -> Attachment:
    """Hash, copy, and describe a local file.

    `dest_dir` is the attachments directory (typically
    `session_dir/attachments`). The destination filename is
    ``<sha8>-<basename>``; re-attaching the same file is idempotent.
    """
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"attachment not found: {path}")

    sha = _sha256_of(path)
    short = sha[:8]
    safe_basename = path.name.replace("/", "_")
    dest_name = f"{short}-{safe_basename}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / dest_name
    if not dest.exists():
        shutil.copy2(path, dest)
    size = dest.stat().st_size

    kind = kind_from_ext(path.name)
    mime = mime_for(path.name, kind=kind)

    return Attachment(
        kind=kind,
        source=source or f"cli:{path}",
        title=title or path.name,
        caption=caption,
        url=None,
        rel_path=f"attachments/{dest_name}",
        mime=mime,
        size_bytes=size,
        sha256=sha,
    )


# ─── URL → Attachment ─────────────────────────────────────────────────────────


def attach_url(
    url: str,
    *,
    title: str | None = None,
    caption: str | None = None,
    source: str | None = None,
    kind: str | None = None,
) -> Attachment:
    """Wrap a remote URL without downloading.

    Kind is inferred from the URL's path extension when not explicit.
    """
    k = kind or kind_for_url(url)
    mime = mime_for(url, kind=k)
    return Attachment(
        kind=k,
        source=source or f"url:{url}",
        title=title,
        caption=caption,
        url=url,
        rel_path=None,
        mime=mime,
        size_bytes=None,
        sha256=None,
    )


# ─── Markdown scanner ─────────────────────────────────────────────────────────


# Inline image:  ![alt](url "optional title")
_IMG_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)\s]+)(?:\s+\"(?P<title>[^\"]*)\")?\)")
# Inline link:   [label](url "optional title") — excludes the image case
# Use a negative-lookbehind to skip when preceded by `!`.
_LINK_RE = re.compile(
    r"(?<!\!)\[(?P<label>[^\]]+)\]\((?P<url>[^)\s]+)(?:\s+\"(?P<title>[^\"]*)\")?\)"
)
# Bare URL: best-effort. Avoid grabbing trailing punctuation.
_BARE_URL_RE = re.compile(r"(?<![\(\"\'\w])(https?://[^\s\)<>\"']+[^\s\)<>\"',.])")


def _is_remote(url: str) -> bool:
    return urlparse(url).scheme in ("http", "https")


def scan_markdown_attachments(
    text: str,
    *,
    base_dir: Path,
    include_bare_urls: bool = True,
) -> list[Attachment]:
    """Pull attachments out of a markdown body.

    For each `![alt](url)` and `[label](url)` match, classify by URL
    scheme and extension. Local relative paths are kept as relative
    references (caller decides whether to copy them — see
    `materialise_local_markdown_attachments` below). Remote URLs are
    wrapped as URL attachments.

    Dedup is by (kind, url-or-resolved-path).
    """
    seen: set[tuple[str, str]] = set()
    out: list[Attachment] = []

    def _push(a: Attachment) -> None:
        key = (a.kind, a.url or a.rel_path or a.source)
        if key in seen:
            return
        seen.add(key)
        out.append(a)

    for m in _IMG_RE.finditer(text or ""):
        url = m.group("url").strip()
        alt = (m.group("alt") or "").strip() or None
        title = (m.group("title") or "").strip() or None
        if _is_remote(url):
            _push(attach_url(url, title=alt or title, caption=title, source=f"markdown:{url}"))
        else:
            local = (base_dir / url).resolve() if not Path(url).is_absolute() else Path(url)
            kind = kind_from_ext(local.name) or "image"
            _push(
                Attachment(
                    kind=kind if kind in ("image", "pdf") else "image",
                    source=f"markdown:{url}",
                    title=alt or local.name,
                    caption=title,
                    url=None,
                    rel_path=str(local),  # caller resolves into session dir
                    mime=mime_for(local.name, kind=kind),
                )
            )

    for m in _LINK_RE.finditer(text or ""):
        url = m.group("url").strip()
        label = (m.group("label") or "").strip() or None
        title = (m.group("title") or "").strip() or None
        if _is_remote(url):
            _push(attach_url(url, title=label, caption=title, source=f"markdown:{url}"))
        else:
            local = (base_dir / url).resolve() if not Path(url).is_absolute() else Path(url)
            if local.exists() and local.is_file():
                kind = kind_from_ext(local.name)
                _push(
                    Attachment(
                        kind=kind,
                        source=f"markdown:{url}",
                        title=label or local.name,
                        caption=title,
                        url=None,
                        rel_path=str(local),
                        mime=mime_for(local.name, kind=kind),
                    )
                )

    if include_bare_urls:
        for m in _BARE_URL_RE.finditer(text or ""):
            url = m.group(1).strip()
            _push(attach_url(url, source=f"markdown:{url}"))

    return out


def materialise_local_markdown_attachments(
    attachments: list[Attachment],
    *,
    dest_dir: Path,
) -> list[Attachment]:
    """For every attachment whose rel_path is an absolute on-disk path
    (the marker `scan_markdown_attachments` uses for local refs), copy
    the file into `dest_dir` and replace with a real attachment-style
    rel_path. Drops entries pointing at missing files.
    """
    out: list[Attachment] = []
    for a in attachments:
        if a.rel_path and Path(a.rel_path).is_absolute() and Path(a.rel_path).exists():
            try:
                materialised = attach_local_file(
                    Path(a.rel_path),
                    dest_dir=dest_dir,
                    title=a.title,
                    caption=a.caption,
                    source=a.source,
                )
                out.append(materialised)
            except (FileNotFoundError, OSError):
                continue
        elif a.rel_path and Path(a.rel_path).is_absolute():
            # The relative-path marker pointed at a file that doesn't
            # exist — drop it rather than surface a broken entry.
            continue
        else:
            out.append(a)
    return out


# ─── Bundle utilities ─────────────────────────────────────────────────────────


@dataclass
class AttachmentBundle:
    """The on-disk shape of attachments.json."""

    attachments: list[Attachment] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"attachments": [a.to_dict() for a in self.attachments]}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AttachmentBundle":
        if not data:
            return cls()
        return cls(attachments=[Attachment.from_dict(a) for a in data.get("attachments", [])])


def kind_counts(attachments: list[Attachment]) -> dict[str, int]:
    counts: dict[str, int] = {"image": 0, "pdf": 0, "file": 0, "link": 0}
    for a in attachments:
        counts[a.kind] = counts.get(a.kind, 0) + 1
    return counts


__all__ = [
    "Attachment",
    "AttachmentBundle",
    "IMAGE_EXTS",
    "PDF_EXTS",
    "attach_local_file",
    "attach_url",
    "kind_counts",
    "kind_for_url",
    "kind_from_ext",
    "materialise_local_markdown_attachments",
    "mime_for",
    "scan_markdown_attachments",
]

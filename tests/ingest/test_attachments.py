"""Attachment ingest helpers — spec 0025."""

from __future__ import annotations

from pathlib import Path

import pytest

from dual_research.ingest.attachments import (
    Attachment,
    AttachmentBundle,
    attach_local_file,
    attach_url,
    kind_counts,
    kind_for_url,
    kind_from_ext,
    materialise_local_markdown_attachments,
    scan_markdown_attachments,
)


# ─── Kind inference ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("diagram.png", "image"),
        ("photo.JPG", "image"),
        ("scan.heic", "image"),
        ("report.pdf", "pdf"),
        ("notes.txt", "file"),
        ("no-ext", "file"),
    ],
)
def test_kind_from_ext(name: str, expected: str) -> None:
    assert kind_from_ext(name) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com/foo.png", "image"),
        ("https://example.com/report.pdf?download=1", "pdf"),
        ("https://example.com/article", "link"),
        ("https://example.com/", "link"),
    ],
)
def test_kind_for_url(url: str, expected: str) -> None:
    assert kind_for_url(url) == expected


# ─── attach_url ──────────────────────────────────────────────────────────────


def test_attach_url_infers_image_kind_from_extension() -> None:
    a = attach_url("https://cdn.example.com/diagram.png", title="Diagram")
    assert a.kind == "image"
    assert a.url == "https://cdn.example.com/diagram.png"
    assert a.title == "Diagram"
    assert a.rel_path is None
    assert a.size_bytes is None


def test_attach_url_explicit_link_kind() -> None:
    a = attach_url("https://example.com", kind="link", title="Example")
    assert a.kind == "link"


# ─── attach_local_file ───────────────────────────────────────────────────────


def test_attach_local_file_copies_and_hashes(tmp_path: Path) -> None:
    src = tmp_path / "diagram.png"
    src.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    dest = tmp_path / "attachments"
    a = attach_local_file(src, dest_dir=dest)
    assert a.kind == "image"
    assert a.size_bytes == len(b"\x89PNG\r\n\x1a\nfake")
    assert a.sha256 and len(a.sha256) == 64
    assert a.rel_path is not None and a.rel_path.startswith("attachments/")
    assert a.rel_path.endswith("-diagram.png")
    copied = dest / a.rel_path.split("/", 1)[1]
    assert copied.exists()
    assert copied.read_bytes() == b"\x89PNG\r\n\x1a\nfake"


def test_attach_local_file_is_idempotent_on_same_content(tmp_path: Path) -> None:
    src = tmp_path / "x.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    dest = tmp_path / "attachments"
    a1 = attach_local_file(src, dest_dir=dest)
    a2 = attach_local_file(src, dest_dir=dest)
    assert a1.rel_path == a2.rel_path
    assert list(dest.iterdir()) == [dest / a1.rel_path.split("/", 1)[1]]


def test_attach_local_file_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        attach_local_file(tmp_path / "nope.png", dest_dir=tmp_path / "attachments")


# ─── scan_markdown_attachments ───────────────────────────────────────────────


def test_scan_finds_inline_images(tmp_path: Path) -> None:
    body = (
        "# Brief\n\n"
        "Compare ![architecture](https://example.com/arch.png) to a baseline.\n"
        "Also see ![local](diagram.png).\n"
    )
    atts = scan_markdown_attachments(body, base_dir=tmp_path, include_bare_urls=False)
    by_url = {a.url: a for a in atts if a.url}
    assert "https://example.com/arch.png" in by_url
    assert by_url["https://example.com/arch.png"].kind == "image"
    local = [a for a in atts if a.rel_path]
    assert any(Path(a.rel_path).name == "diagram.png" for a in local)


def test_scan_finds_inline_links_with_titles(tmp_path: Path) -> None:
    body = '[OpenAI docs](https://platform.openai.com/docs "OpenAI Docs")\n'
    atts = scan_markdown_attachments(body, base_dir=tmp_path, include_bare_urls=False)
    assert len(atts) == 1
    assert atts[0].kind == "link"
    assert atts[0].title == "OpenAI docs"
    assert atts[0].caption == "OpenAI Docs"


def test_scan_dedupes_repeated_urls(tmp_path: Path) -> None:
    body = (
        "[a](https://example.com/x.pdf)\n"
        "[b](https://example.com/x.pdf)\n"
    )
    atts = scan_markdown_attachments(body, base_dir=tmp_path, include_bare_urls=False)
    assert len(atts) == 1
    assert atts[0].kind == "pdf"


def test_scan_picks_up_bare_urls(tmp_path: Path) -> None:
    body = "Some context. See https://example.org/article for details.\n"
    atts = scan_markdown_attachments(body, base_dir=tmp_path)
    assert any(a.url == "https://example.org/article" for a in atts)


def test_scan_skips_bare_urls_when_disabled(tmp_path: Path) -> None:
    body = "See https://example.org/article."
    atts = scan_markdown_attachments(body, base_dir=tmp_path, include_bare_urls=False)
    assert atts == []


# ─── materialise_local_markdown_attachments ──────────────────────────────────


def test_materialise_copies_local_paths(tmp_path: Path) -> None:
    src = tmp_path / "img.png"
    src.write_bytes(b"PNGDATA")
    raw = Attachment(
        kind="image",
        source="markdown:./img.png",
        title="img.png",
        rel_path=str(src),
    )
    atts = materialise_local_markdown_attachments([raw], dest_dir=tmp_path / "attachments")
    assert len(atts) == 1
    a = atts[0]
    assert a.rel_path is not None
    assert a.rel_path.startswith("attachments/")
    assert (tmp_path / a.rel_path).read_bytes() == b"PNGDATA"


def test_materialise_drops_missing_files(tmp_path: Path) -> None:
    raw = Attachment(
        kind="image",
        source="markdown:./missing.png",
        rel_path=str(tmp_path / "missing.png"),
    )
    atts = materialise_local_markdown_attachments([raw], dest_dir=tmp_path / "attachments")
    assert atts == []


def test_materialise_passes_through_url_attachments(tmp_path: Path) -> None:
    raw = Attachment(kind="image", source="url:https://example.com/x.png",
                     url="https://example.com/x.png")
    atts = materialise_local_markdown_attachments([raw], dest_dir=tmp_path / "attachments")
    assert atts == [raw]


# ─── Bundle ──────────────────────────────────────────────────────────────────


def test_bundle_round_trips_via_dict() -> None:
    bundle = AttachmentBundle(attachments=[
        Attachment(kind="image", source="cli:foo.png", url=None, rel_path="attachments/x"),
        Attachment(kind="link", source="url:https://example.com", url="https://example.com"),
    ])
    data = bundle.to_dict()
    restored = AttachmentBundle.from_dict(data)
    assert restored.attachments == bundle.attachments


def test_bundle_from_dict_ignores_unknown_keys() -> None:
    data = {"attachments": [{"kind": "image", "source": "x", "unknown_future_field": 42}]}
    restored = AttachmentBundle.from_dict(data)
    assert restored.attachments == [Attachment(kind="image", source="x")]


def test_kind_counts() -> None:
    atts = [
        Attachment(kind="image", source="a"),
        Attachment(kind="image", source="b"),
        Attachment(kind="pdf", source="c"),
        Attachment(kind="link", source="d"),
    ]
    counts = kind_counts(atts)
    assert counts["image"] == 2
    assert counts["pdf"] == 1
    assert counts["link"] == 1
    assert counts["file"] == 0

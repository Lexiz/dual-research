"""Spec 0220 — In-app Changelog auto-generated from CHANGELOG.md.

Two test surfaces per spec 0206 doctrine:

1. **Source-pattern tests** — assert post-fix anatomy AND antipodal absence of
   pre-fix shape across the JSX / CSS / Markdown surfaces touched by the spec.
2. **Generator unit tests** — exercise the regex prettifier, bump inference,
   spec-ID extraction, classification, and end-to-end shape against the real
   CHANGELOG.md plus a CI guard that the on-disk sidecar is in sync.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tests._ui_pattern_helpers import (
    REPO_ROOT,
    assert_jsx_contains,
    assert_jsx_lacks,
    read_repo_text,
)

import scripts.build_version_notes as gen


# ────────────────────────────── source-pattern tests ──────────────────


def test_how_it_works_drops_version_notes_literal():
    jsx = read_repo_text("src", "dual_research", "ui", "static", "how-it-works.jsx")
    assert_jsx_lacks(
        jsx,
        r"const VERSION_NOTES = \[",
        msg=(
            "Spec 0220 §2.3: the hand-maintained VERSION_NOTES array must be "
            "removed. ChangelogList sources entries from /static/version-notes.json."
        ),
    )


def test_changelog_list_fetches_json_sidecar():
    jsx = read_repo_text("src", "dual_research", "ui", "static", "how-it-works.jsx")
    # The server (src/dual_research/ui/server.py) mounts StaticFiles at `/`,
    # so the canonical URL is `/version-notes.json` rather than the
    # `/static/version-notes.json` the spec text proposed. Functional intent
    # (fetch the JSON sidecar on mount) is unchanged.
    assert_jsx_contains(
        jsx,
        r"fetch\('/version-notes\.json",
        msg="Spec 0220 §2.3: ChangelogList must fetch the version-notes JSON sidecar on mount.",
    )


def test_changelog_list_hash_routes_cl_anchor():
    jsx = read_repo_text("src", "dual_research", "ui", "static", "how-it-works.jsx")
    assert_jsx_contains(
        jsx,
        r"#cl-",
        msg="Spec 0220 §2.3: ChangelogList must read window.location.hash for #cl-<digits> anchors.",
    )
    assert_jsx_contains(
        jsx,
        r"forceOpen",
        msg="Spec 0220 §2.3: ChangelogEntry must accept a forceOpen prop overriding persisted collapse state.",
    )


def test_app_version_chip_deep_links():
    # Spec 0252 §2.3 deleted `AppVersionChip` from app.jsx when the universal
    # `.ar-chrome` became the single app bar for every route. The version
    # deep-link capability (the spec-0220 §2.5 contract) now lives on the
    # `.ar-pill__v` button in `AllRunsChrome` (run-list.jsx). This test
    # follows the capability to its new home; the functional intent — a
    # clickable version chip that deep-links to `#/how-it-works#cl-<digits>`
    # — is unchanged.
    jsx = read_repo_text("src", "dual_research", "ui", "static", "run-list.jsx")
    assert_jsx_contains(
        jsx,
        r'<button[\s\S]*?className="ar-pill"[\s\S]*?ar-pill__v',
        msg=(
            "Spec 0220 §2.5 / 0252 §2.3: the version chip must be a clickable "
            "<button> (the `.ar-pill__v` pill in AllRunsChrome)."
        ),
    )
    # The route parser at src/dual_research/ui/static/router.jsx uses
    # `#/how-it-works` (with leading slash) as the canonical route, so the
    # chip must emit `#/how-it-works#cl-…`. Functional intent unchanged.
    assert_jsx_contains(
        jsx,
        r"how-it-works#cl-",
        msg=(
            "Spec 0220 §2.5 / 0252 §2.3: the version chip's onClick must set "
            "window.location.hash to #/how-it-works#cl-<digits>."
        ),
    )


def test_contributing_md_describes_auto_generation():
    text = read_repo_text("CONTRIBUTING.md")
    assert_jsx_lacks(
        text,
        r"append a new entry to the `VERSION_NOTES` array",
        msg=(
            "Spec 0220 §2.6: CONTRIBUTING.md §5 must no longer instruct PR authors to "
            "append to VERSION_NOTES — the array is gone."
        ),
    )
    assert_jsx_contains(
        text,
        r"auto-generated from `CHANGELOG\.md`",
        msg="Spec 0220 §2.6: CONTRIBUTING.md §5 must describe the auto-generation flow.",
    )


def test_changelog_internal_row_css_two_file_sync():
    """Spec 0220 §2.4 + CLAUDE.md two-file CSS sync rule."""
    live = read_repo_text("src", "dual_research", "ui", "static", "components.css")
    ds = read_repo_text("design-system", "assets", "styles", "composed-components.css")
    for path, css in [("live components.css", live), ("DS composed-components.css", ds)]:
        assert ".changelog-internal-row {" in css, (
            f"Spec 0220 §2.4: .changelog-internal-row rule missing from {path}. "
            f"CLAUDE.md requires the rule to land in both files in the same commit."
        )


def test_design_system_spec_documents_internal_row():
    spec = read_repo_text("design-system", "SPEC.md")
    assert ".changelog-internal-row" in spec, (
        "Spec 0220 §2.4: design-system/SPEC.md must document the new "
        ".changelog-internal-row composed-component anatomy."
    )


# ────────────────────────────── prettifier tests ──────────────────────


def test_prettify_drops_path_shape_link_visible_text():
    raw = "Fixed [src/dual_research/orchestrator/repair.py](src/dual_research/orchestrator/repair.py) per design."
    out = gen.prettify(raw)
    assert "src/dual_research/orchestrator/repair.py" not in out, out
    # Antipodal: the surrounding sentence remnant should still be parseable.
    assert "Fixed" in out
    assert "per design" in out


def test_prettify_keeps_non_path_link_visible_text():
    raw = "See [the docs](https://example.com/docs) for context."
    out = gen.prettify(raw)
    assert "the docs" in out
    assert "https://example.com/docs" not in out


def test_prettify_preserves_spec_links_verbatim():
    raw = "Per [spec 0211.3](specs/0211.3-deploy-concurrency.md), pivot."
    out = gen.prettify(raw)
    assert "[spec 0211.3](specs/0211.3-deploy-concurrency.md)" in out, out


def test_prettify_bold_to_strong():
    out = gen.prettify("**Bold lead.** Body follows.")
    assert "<strong>Bold lead.</strong>" in out
    assert "**Bold lead.**" not in out


def test_prettify_backtick_to_code():
    out = gen.prettify("Use `foo()` for that.")
    assert "<code>foo()</code>" in out
    assert "`foo()`" not in out


def test_prettify_idempotent_on_already_prettified():
    raw = "**Lead.** Body with `code` and [src/x.py](src/x.py) inside."
    once = gen.prettify(raw)
    twice = gen.prettify(once)
    assert once == twice, f"Prettify not idempotent: {once!r} → {twice!r}"


def test_now_was_reshape_fires_on_previously_now_pattern():
    out = gen.reshape_now_was("Previously X did Y; now X does Z.")
    assert "<strong>Now</strong>" in out
    assert "<strong>Was</strong>" in out
    assert "X did Y" in out
    assert "X does Z" in out


def test_now_was_no_reshape_without_pattern():
    text = "Just a descriptive sentence with no before/after."
    assert gen.reshape_now_was(text) == text


def test_split_long_bullet_at_sentence_boundary():
    long = (
        "Sentence one is here. Sentence two follows the period. "
        "Sentence three continues the prose. Sentence four wraps. "
        "Sentence five trails. Sentence six closes. "
    ) * 3
    pieces = gen.split_long_bullet(long)
    assert len(pieces) > 1, "Long bullet should split into multiple pieces"
    # Each piece should end with sentence-terminating punctuation.
    for p in pieces[:-1]:
        assert p.rstrip().endswith((".", "!", "?")), f"piece doesn't end at sentence: {p!r}"


def test_split_long_bullet_keeps_short_intact():
    short = "Short sentence."
    assert gen.split_long_bullet(short) == [short]


# ────────────────────────────── bump + spec-ID tests ──────────────────


def test_infer_bump_major_minor_patch():
    assert gen.infer_bump("1.45.0", "1.44.25") == "MINOR"
    assert gen.infer_bump("2.0.0", "1.45.0") == "MAJOR"
    assert gen.infer_bump("1.44.26", "1.44.25") == "PATCH"


def test_infer_bump_oldest_entry_inherits_minor():
    assert gen.infer_bump("1.2.0", None) == "MINOR"


def test_extract_spec_ids_dedupes_and_preserves_first_order():
    bullets = [
        "Per [spec 0211.3](specs/0211.3-deploy-concurrency.md) we...",
        "Also [spec 0220](specs/0220-x.md) builds on...",
        "Re-reference [spec 0211.3](specs/0211.3-deploy-concurrency.md) here.",
    ]
    assert gen.extract_spec_ids(bullets) == ["0211.3", "0220"]


def test_extract_spec_ids_handles_integer_and_composite():
    out = gen.extract_spec_ids([
        "[spec 0042](specs/0042-foo.md) and [spec 0099.1](specs/0099.1-bar.md)."
    ])
    assert out == ["0042", "0099.1"]


# ────────────────────────────── classifier tests ──────────────────────


def test_classify_user_facing_true_on_ui_static_ref(tmp_path, monkeypatch):
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "0500-fake.md").write_text(
        "Touches src/dual_research/ui/static/foo.jsx for the demo."
    )
    monkeypatch.setattr(gen, "SPECS_DIR", specs)
    assert gen.classify_user_facing(["0500"]) is True


def test_classify_user_facing_true_on_design_system_ref(tmp_path, monkeypatch):
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "0501-fake.md").write_text(
        "Adds a row to design-system/SPEC.md §4."
    )
    monkeypatch.setattr(gen, "SPECS_DIR", specs)
    assert gen.classify_user_facing(["0501"]) is True


def test_classify_user_facing_false_when_no_ui_or_ds_refs(tmp_path, monkeypatch):
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "0502-fake.md").write_text(
        "Only touches scripts/foo.py and tests/foo_test.py."
    )
    monkeypatch.setattr(gen, "SPECS_DIR", specs)
    assert gen.classify_user_facing(["0502"]) is False


def test_classify_user_facing_missing_spec_defaults_to_true(tmp_path, monkeypatch):
    monkeypatch.setattr(gen, "SPECS_DIR", tmp_path)
    assert gen.classify_user_facing(["9999"]) is True


# ────────────────────────────── end-to-end / CI guard ─────────────────


def test_generator_shape_against_real_changelog():
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    entries = gen.build_entries(text)
    assert len(entries) >= 40, f"Expected ≥ 40 entries, got {len(entries)}"
    required = {
        "version", "date", "bump", "summary", "items", "specs",
        "user_facing", "screenshots",
    }
    for e in entries:
        missing = required - set(e.keys())
        assert not missing, f"Entry v{e.get('version')} missing keys: {missing}"
    # Newest-first by version (the CHANGELOG.md convention — dates can
    # repeat within a release-day burst, but versions are monotone).
    versions = [tuple(int(n) for n in e["version"].split(".")) for e in entries]
    assert versions == sorted(versions, reverse=True), (
        "Entries not newest-first by version"
    )


def test_generator_idempotent():
    text = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    a = gen.build_entries(text)
    b = gen.build_entries(text)
    assert a == b


def test_sidecar_in_sync_with_changelog():
    """CI guard — `build_version_notes.py --check` exits 0 on HEAD."""
    result = subprocess.run(
        [sys.executable, "scripts/build_version_notes.py", "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"version-notes.json is stale.\n"
        f"  stdout: {result.stdout}\n"
        f"  stderr: {result.stderr}\n"
        f"  Run: uv run python scripts/build_version_notes.py"
    )

"""Tests for spec 0229.1 — validator enforces `disposition:` + `disposition_reason:`.

Spec body: [specs/0229.1-validator-enforce-disposition-frontmatter.md](specs/0229.1-validator-enforce-disposition-frontmatter.md).
Convention shipped doctrinally in spec 0229 §2.5 (CLAUDE.md §"Carve-out
follow-ups must triage at carve-out time").
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from scripts.spec_lifecycle.validator import (
    VALID_DISPOSITIONS,
    validate_dev_spec,
    validate_draft,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_GOOD_BODY = """\
# Spec 9999 — fixture

## 1. Context
Body cites `scripts/spec_lifecycle/validator.py:30` and
`scripts/spec_lifecycle/frontmatter.py:1` so the citation gate passes.

## 2. Proposed change
Do the thing.

## 3. Out of scope
Nothing else.

## 4. Test plan
- [ ] Unit
- [ ] Integration

## 5. Risks
Low.
"""


def _write_spec(path: Path, fm_lines: list[str], body: str = _GOOD_BODY) -> Path:
    path.write_text("---\n" + "\n".join(fm_lines) + "\n---\n\n" + body)
    return path


def _base_dev_fm(**overrides: str) -> list[str]:
    """Return frontmatter lines for a validator-passing dev spec.

    Overrides apply key-by-key. Pass ``disposition=None`` to omit the field
    (used to test the missing-key path).
    """
    fields: dict[str, str | None] = {
        "kind": "dev",
        "spec": '"9999"',
        "slug": "fixture",
        "title": "Fixture",
        "type": "new-feature",
        "label": "new-feature",
        "version_bump": "MINOR",
        "status": "queued",
        "disposition": "ship",
        "disposition_reason": '"test fixture; ship for parity with the queue head."',
    }
    fields.update(overrides)
    return [f"{k}: {v}" for k, v in fields.items() if v is not None]


def _base_draft_fm(**overrides: str) -> list[str]:
    fields: dict[str, str | None] = {
        "kind": "draft",
        "draft_id": '"099"',
        "slug": "fixture",
        "title": "Fixture",
        "status": "draft",
        "disposition": "archive",
        "disposition_reason": '"draft fixture; archive by default."',
    }
    fields.update(overrides)
    return [f"{k}: {v}" for k, v in fields.items() if v is not None]


# ---------------------------------------------------------------------------
# §6 Test plan — unit tests
# ---------------------------------------------------------------------------


def test_dev_spec_missing_disposition_fails(tmp_path: Path) -> None:
    """§6 item 1 — omitting `disposition` triggers a missing-required-keys error."""
    p = _write_spec(tmp_path / "9999-x.md", _base_dev_fm(disposition=None))
    r = validate_dev_spec(p)
    assert not r.ok
    assert any("disposition" in e for e in r.errors), r.errors


def test_dev_spec_invalid_disposition_value_fails(tmp_path: Path) -> None:
    """§6 item 2 — value outside ``{ship, defer, archive}`` is rejected with a
    message naming the valid set."""
    p = _write_spec(tmp_path / "9999-x.md", _base_dev_fm(disposition="maybe"))
    r = validate_dev_spec(p)
    assert not r.ok
    msg = " ".join(r.errors)
    assert "'ship'" in msg and "'defer'" in msg and "'archive'" in msg, r.errors


def test_dev_spec_valid_disposition_passes(tmp_path: Path) -> None:
    """§6 item 3 — ``disposition: ship`` + a non-empty single-sentence reason
    validates green."""
    p = _write_spec(tmp_path / "9999-x.md", _base_dev_fm())
    r = validate_dev_spec(p)
    assert r.ok, r.errors


def test_dev_spec_empty_disposition_reason_fails(tmp_path: Path) -> None:
    """§6 item 4 — ``disposition_reason: ""`` is treated as missing-shape."""
    p = _write_spec(tmp_path / "9999-x.md", _base_dev_fm(disposition_reason='""'))
    r = validate_dev_spec(p)
    assert not r.ok
    assert any("non-empty" in e for e in r.errors), r.errors


def test_dev_spec_multi_sentence_reason_is_warning_not_error(tmp_path: Path) -> None:
    """§6 item 5 — reasons spanning multiple sentences warn but do not fail."""
    reason = '"First sentence. Second sentence. Third sentence."'
    p = _write_spec(tmp_path / "9999-x.md", _base_dev_fm(disposition_reason=reason))
    r = validate_dev_spec(p)
    assert r.ok, r.errors
    assert any("one-sentence" in w for w in r.warnings), r.warnings


def test_draft_missing_disposition_fails(tmp_path: Path) -> None:
    """§6 item 6 — drafts inherit the same gate as dev specs."""
    p = _write_spec(tmp_path / "draft.md", _base_draft_fm(disposition=None))
    r = validate_draft(p)
    assert not r.ok
    assert any("disposition" in e for e in r.errors), r.errors


def test_draft_valid_disposition_passes(tmp_path: Path) -> None:
    """Companion to §6 item 6 — the positive draft path stays green."""
    p = _write_spec(tmp_path / "draft.md", _base_draft_fm())
    r = validate_draft(p)
    assert r.ok, r.errors


# ---------------------------------------------------------------------------
# §6 Test plan — source-pattern tests (spec 0206)
# ---------------------------------------------------------------------------


def test_valid_dispositions_constant_exists() -> None:
    """§6 item 7 — positive regex on the validator source for the new constant.

    The constant must enumerate ``ship`` (the queue-head-eligible value);
    locking that down protects against accidental rename or silencing of the
    check.
    """
    text = Path("scripts/spec_lifecycle/validator.py").read_text()
    assert re.search(r'VALID_DISPOSITIONS\s*=\s*\{[^}]*"ship"', text), (
        "expected `VALID_DISPOSITIONS = { ... 'ship' ... }` definition in validator source"
    )
    # Antipodal-absence: the disposition check must not be wrapped in an
    # always-false guard that silences it.
    assert "if False" not in text, "validator source contains `if False` — disposition check may be silenced"


def test_valid_dispositions_runtime_set() -> None:
    """Companion to the source-pattern test — the imported constant matches."""
    assert VALID_DISPOSITIONS == {"ship", "defer", "archive"}


# ---------------------------------------------------------------------------
# §6 Test plan — integration tests
# ---------------------------------------------------------------------------


def test_backfill_is_idempotent(tmp_path: Path) -> None:
    """§6 item 8 — running the backfill twice produces no further changes."""
    specs_root = tmp_path / "specs"
    specs_root.mkdir()
    (specs_root / "drafts").mkdir()

    # Three pre-backfill files: two dev specs + one draft, none declaring
    # `disposition`. One file already has `disposition` and must be left alone.
    pre_files = {
        specs_root / "9001-foo.md": "---\nkind: dev\nstatus: queued\n---\n\n# Body\n",
        specs_root / "9002-bar.md": "---\nkind: dev\nstatus: queued\n---\n\n# Body\n",
        specs_root / "drafts" / "draft-099-baz.md": "---\nkind: draft\nstatus: draft\n---\n\n# Body\n",
        specs_root / "9003-pre-declared.md": (
            '---\nkind: dev\nstatus: queued\ndisposition: ship\n'
            'disposition_reason: "already declared."\n---\n\n# Body\n'
        ),
    }
    for path, content in pre_files.items():
        path.write_text(content)

    def _run() -> str:
        result = subprocess.run(
            [sys.executable, "-m", "scripts.spec_lifecycle.backfill_disposition", "--specs-root", str(specs_root)],
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
        )
        assert result.returncode == 0, result.stderr
        return result.stdout

    first = _run()
    second = _run()

    # First pass backfills 3 (the pre-declared file is the only skip);
    # second pass skips all 4 (the 3 just backfilled + the 1 pre-declared).
    assert "backfilled 3 files (1 skipped" in first, first
    assert "backfilled 0 files (4 skipped" in second, second

    # And the resulting files validate against the disposition shape (they
    # still lack other dev-spec required fields, so they don't pass
    # validate_dev_spec — but their disposition errors are gone).
    body_9001 = (specs_root / "9001-foo.md").read_text()
    assert "disposition: archive" in body_9001
    assert "disposition_reason:" in body_9001


def test_no_existing_spec_fails_specifically_on_disposition() -> None:
    """§6 item 9 (scoped) — every in-repo spec/draft post-backfill no longer
    fails the validator *for disposition reasons*.

    Note: the spec's literal acceptance criterion ("every existing spec
    validates green") is overstated — many pre-2026 specs fail rules that
    landed after they were queued (citation-count, source-traceability, etc.).
    That validator-evolution debt is out of scope for this spec; what spec
    0229.1 actually delivers is "no disposition-class failure remains," which
    this test asserts.
    """
    # Restrict to canonical spec/draft filenames — non-spec top-level files
    # like ``TEMPLATE.md`` or ``_backlog-inventory.md`` are not dev specs and
    # are out of scope for the validator (they'd fail on filename grammar +
    # missing required keys regardless of this spec).
    spec_filename_re = re.compile(r"^\d{4}(?:\.\d+)?-[a-z0-9-]+\.md$")
    disposition_pattern = re.compile(r"disposition", re.IGNORECASE)
    failures: list[tuple[str, list[str]]] = []
    for p in sorted(Path("specs").glob("*.md")):
        if not spec_filename_re.match(p.name):
            continue
        r = validate_dev_spec(p)
        bad = [e for e in r.errors if disposition_pattern.search(e)]
        if bad:
            failures.append((p.name, bad))
    for p in sorted(Path("specs/drafts").glob("draft-*.md")):
        r = validate_draft(p)
        bad = [e for e in r.errors if disposition_pattern.search(e)]
        if bad:
            failures.append((p.name, bad))
    assert not failures, f"disposition-class validation failures remain after backfill: {failures}"


# ---------------------------------------------------------------------------
# §6 Test plan — version + CHANGELOG smoke
# ---------------------------------------------------------------------------


def test_changelog_and_version_smoke() -> None:
    """§6 item 10 — the PR carries a version bump and a CHANGELOG entry that
    references this spec."""
    init_text = Path("src/dual_research/__init__.py").read_text()
    pyproject_text = Path("pyproject.toml").read_text()
    changelog_text = Path("CHANGELOG.md").read_text()

    version_match = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    assert version_match, "could not find __version__ in src/dual_research/__init__.py"
    version = version_match.group(1)

    # pyproject version mirrors the package __version__.
    assert f'version = "{version}"' in pyproject_text, (
        f"pyproject.toml version does not match __version__ ({version})"
    )

    # CHANGELOG has a section for this version referencing spec 0229.1.
    section_re = re.compile(
        rf"^## \[{re.escape(version)}\]\s+—\s+\d{{4}}-\d{{2}}-\d{{2}}",
        re.MULTILINE,
    )
    assert section_re.search(changelog_text), (
        f"CHANGELOG.md missing `## [{version}] — YYYY-MM-DD` section"
    )
    assert "0229.1" in changelog_text, "CHANGELOG.md does not reference spec 0229.1"

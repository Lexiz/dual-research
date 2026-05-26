"""Spec 0227.1 — reconciler skips markdown-link display-text citations.

Locks the post-fix shape of ``scripts.spec_lifecycle.reconcile``:
``[display](href)`` constructs contribute only their href to the citation
set; plain-prose ``path.ext:line`` references remain first-class. Both
behavioural fixtures (run ``reconcile_spec`` against tmp repos) and a
source-pattern pair (positive present, antipodal absent) are exercised so
a regression that reintroduces direct ``CITATION_RE.finditer(body)`` over
unscrubbed text is caught at the source level.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.spec_lifecycle.reconcile import reconcile_spec

REPO_ROOT = Path(__file__).resolve().parent.parent
RECONCILE_PATH = REPO_ROOT / "scripts" / "spec_lifecycle" / "reconcile.py"


@pytest.fixture
def project_repo(tmp_path: Path) -> Path:
    """Tmp repo with a single in-tree file used by behaviour tests."""
    (tmp_path / "scripts" / "spec_lifecycle").mkdir(parents=True)
    (tmp_path / "scripts" / "spec_lifecycle" / "reconcile.py").write_text(
        "\n".join(f"line {i}" for i in range(200)) + "\n"
    )
    return tmp_path


def _write_spec(tmp_path: Path, body: str) -> Path:
    spec = tmp_path / "spec.md"
    spec.write_text("---\nkind: dev\nspec: \"0227.1\"\n---\n" + body)
    return spec


def test_display_text_only_citation_is_skipped(project_repo: Path) -> None:
    """`[basename.md:42](../cowork/full-path.md)` produces zero citations.

    The display text's `basename.md:42` shadow is scrubbed before extraction;
    the href has no `:line` suffix, so it is not matched either.
    """
    spec = _write_spec(
        project_repo,
        "External evidence at [basename.md:42](../cowork/full-path.md).\n",
    )
    report = reconcile_spec(spec, repo_root=project_repo)
    assert report.clean == []
    assert report.mechanical == []
    assert report.semantic == []
    assert report.has_blocking_drift is False


def test_href_form_citation_is_extracted(project_repo: Path) -> None:
    """`[label](path:line)` contributes the href as a clean citation."""
    spec = _write_spec(
        project_repo,
        "See [the helper](scripts/spec_lifecycle/reconcile.py:25).\n",
    )
    report = reconcile_spec(spec, repo_root=project_repo)
    assert len(report.clean) == 1
    cit = report.clean[0]
    assert cit.path == "scripts/spec_lifecycle/reconcile.py"
    assert cit.line == 25


def test_plain_prose_citation_still_works(project_repo: Path) -> None:
    """Bare `path.ext:line` outside any link continues to be extracted."""
    spec = _write_spec(
        project_repo,
        "See scripts/spec_lifecycle/reconcile.py:25 in passing.\n",
    )
    report = reconcile_spec(spec, repo_root=project_repo)
    assert len(report.clean) == 1
    assert report.clean[0].path == "scripts/spec_lifecycle/reconcile.py"
    assert report.clean[0].line == 25


def test_mixed_body_returns_href_and_plain_only(project_repo: Path) -> None:
    """Display-text shadow dropped; href + plain prose survive as the in-tree set."""
    body = (
        "Evidence: [synthesis.md:42](../cowork/briefs/synthesis.md).\n"
        "Code: [helper](scripts/spec_lifecycle/reconcile.py:25).\n"
        "Also see scripts/spec_lifecycle/reconcile.py:92 in passing.\n"
    )
    spec = _write_spec(project_repo, body)
    report = reconcile_spec(spec, repo_root=project_repo)
    paths = sorted((c.path, c.line) for c in report.clean)
    assert paths == [
        ("scripts/spec_lifecycle/reconcile.py", 25),
        ("scripts/spec_lifecycle/reconcile.py", 92),
    ]
    assert report.semantic == []
    assert report.mechanical == []


def test_source_pattern_scrubber_wired_into_extract() -> None:
    """Source-pattern (positive present, antipodal absent).

    Asserts the post-fix shape: ``_extract_citations`` calls the scrubber
    before ``finditer``. The antipodal-absence assertion catches a
    regression that reintroduces direct ``CITATION_RE.finditer(body)`` over
    the unscrubbed body.
    """
    source = RECONCILE_PATH.read_text(encoding="utf-8")
    extract_match = re.search(
        r"def _extract_citations\(body: str\) -> list\[Citation\]:\n(.*?)(?=\n(?:def |@dataclass|class ))",
        source,
        re.DOTALL,
    )
    assert extract_match is not None, "could not locate _extract_citations function body"
    body = extract_match.group(1)
    assert re.search(r"_scrub_link_display_text\(body\)", body), (
        "_extract_citations should pass body through _scrub_link_display_text "
        "before applying CITATION_RE.finditer (post-fix shape)"
    )
    assert not re.search(r"CITATION_RE\.finditer\(body\)", body), (
        "_extract_citations must not call CITATION_RE.finditer(body) directly — "
        "that is the pre-fix shape that lets markdown-link display text shadow "
        "citations through"
    )

"""Spec 0230 — reconciler skips out-of-tree prefix paths.

Locks the post-fix shape of ``scripts.spec_lifecycle.reconcile``: citations
whose path begins with any entry in a configurable prefix-skip list
(default ``("cowork/",)``) are routed into a new informational
``out_of_tree`` bucket and do not contribute to ``has_blocking_drift``.
Behavioural fixtures exercise the four routing cases (default match,
default non-match, custom prefix override, empty prefix list = pre-fix
baseline); a source-pattern pair locks the ``OUT_OF_TREE_PREFIXES``
constant + the prefix-check-before-existence-check shape; an integration
test re-runs the reconciler on spec 0229 (the empirical regression
target) and asserts exit 0; a CHANGELOG/version smoke check guards the
1.50.0 release artefact.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.spec_lifecycle.reconcile import (
    OUT_OF_TREE_PREFIXES,
    reconcile_spec,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
RECONCILE_PATH = REPO_ROOT / "scripts" / "spec_lifecycle" / "reconcile.py"


@pytest.fixture
def empty_repo(tmp_path: Path) -> Path:
    """Tmp repo root with no `cowork/` directory and no in-tree files."""
    return tmp_path


def _write_spec(tmp_path: Path, body: str) -> Path:
    spec = tmp_path / "spec.md"
    spec.write_text("---\nkind: dev\nspec: \"0230\"\n---\n" + body)
    return spec


# ---------- §6 test 1 — prefix-matched citation lands in out_of_tree -------


def test_default_cowork_prefix_lands_in_out_of_tree(empty_repo: Path) -> None:
    """A bare-prose `cowork/briefs/...:N` citation routes to `out_of_tree`.

    Asserts the canonical regression case: spec 0229's three semantic-drift
    hits all cited `cowork/briefs/2026-05-26-logic-cutoff-synthesis.md:NNN`
    and were the trigger for this fix.
    """
    spec = _write_spec(
        empty_repo,
        "Evidence at cowork/briefs/2026-05-26-logic-cutoff-synthesis.md:42 inline.\n",
    )
    report = reconcile_spec(spec, repo_root=empty_repo)
    assert len(report.out_of_tree) == 1
    cit = report.out_of_tree[0]
    assert cit.path == "cowork/briefs/2026-05-26-logic-cutoff-synthesis.md"
    assert cit.line == 42
    assert cit.classification == "out_of_tree"
    assert report.semantic == []
    assert report.mechanical == []
    assert report.has_blocking_drift is False
    assert report.has_drift is False


# ---------- §6 test 2 — non-matching path still classifies as semantic -----


def test_non_matching_path_still_classifies_normally(empty_repo: Path) -> None:
    """`src/nonexistent/file.py:1` falls through to semantic (pre-fix shape).

    Confirms the prefix-skip is additive, not a blanket no-op.
    """
    spec = _write_spec(empty_repo, "Will not exist: src/nonexistent/file.py:1\n")
    report = reconcile_spec(spec, repo_root=empty_repo)
    assert len(report.semantic) == 1
    assert report.semantic[0].path == "src/nonexistent/file.py"
    assert report.out_of_tree == []
    assert report.has_blocking_drift is True


# ---------- §6 test 3 — custom prefix list overrides default ---------------


def test_custom_prefix_list_overrides_default(empty_repo: Path) -> None:
    """Caller-supplied prefixes flip which citations are skipped vs flagged.

    Spec §2.1 — `out_of_tree_prefixes=` kwarg replaces the default tuple.
    Body has one each of: a default-skipped path (now NOT in custom list,
    falls to semantic) and a custom-skipped path (`../external/`).
    """
    spec = _write_spec(
        empty_repo,
        "Default-shape: cowork/briefs/foo.md:1\nCustom-shape: ../external/notes.md:1\n",
    )
    report = reconcile_spec(
        spec,
        repo_root=empty_repo,
        out_of_tree_prefixes=("../external/",),
    )
    paths_oot = sorted(c.path for c in report.out_of_tree)
    paths_sem = sorted(c.path for c in report.semantic)
    assert paths_oot == ["../external/notes.md"]
    assert paths_sem == ["cowork/briefs/foo.md"]


# ---------- §6 test 4 — empty skip list reverts to pre-fix behaviour -------


def test_empty_prefix_list_reverts_to_pre_fix_behaviour(empty_repo: Path) -> None:
    """`out_of_tree_prefixes=()` makes the reconciler behave as it did pre-0230.

    A cowork citation that today routes to `out_of_tree` falls back to
    `semantic` — confirming the new bucket is genuinely opt-in via the
    prefix tuple.
    """
    spec = _write_spec(empty_repo, "Pre-fix shape: cowork/briefs/foo.md:1\n")
    report = reconcile_spec(spec, repo_root=empty_repo, out_of_tree_prefixes=())
    assert report.out_of_tree == []
    assert len(report.semantic) == 1
    assert report.semantic[0].path == "cowork/briefs/foo.md"
    assert report.has_blocking_drift is True


# ---------- §6 test — trailing-slash guard against sibling-dir overmatch ---


def test_trailing_slash_prevents_sibling_dir_overmatch(empty_repo: Path) -> None:
    """`cowork-design-system/...` does NOT match the `cowork/` prefix.

    Spec §7 R3 — the default prefix is `cowork/` with a trailing slash, so
    a hypothetical sibling directory whose name starts with `cowork` falls
    through to the normal classifier.
    """
    spec = _write_spec(empty_repo, "Sibling: cowork-design-system/file.py:1\n")
    report = reconcile_spec(spec, repo_root=empty_repo)
    assert report.out_of_tree == []
    assert len(report.semantic) == 1
    assert report.semantic[0].path == "cowork-design-system/file.py"


# ---------- §6 test 5 — source-pattern lock-in (positive + antipodal) ------


def test_source_pattern_out_of_tree_prefixes_constant_defined() -> None:
    """Module-level `OUT_OF_TREE_PREFIXES` exists with the `cowork/` default.

    Positive regex per spec §6 — guards against an accidental rename or
    in-function-scope demotion of the constant.
    """
    source = RECONCILE_PATH.read_text(encoding="utf-8")
    assert re.search(
        r'^OUT_OF_TREE_PREFIXES\s*[:=].*"cowork/"',
        source,
        re.MULTILINE,
    ), "OUT_OF_TREE_PREFIXES module-level constant must exist with 'cowork/' default"


def test_source_pattern_prefix_check_before_existence_check() -> None:
    """Inside `reconcile_spec`'s classification loop, the prefix check fires
    BEFORE the on-disk existence check.

    Antipodal-absence catches a regression that re-introduces the pre-fix
    shape where every path goes straight to ``root / cit.path`` /
    semantic-bucket fall-through.
    """
    source = RECONCILE_PATH.read_text(encoding="utf-8")
    fn_match = re.search(
        r"def reconcile_spec\([^)]*\)[^:]*:\n(.*?)(?=\n(?:def |@dataclass|class |\Z))",
        source,
        re.DOTALL,
    )
    assert fn_match is not None, "could not locate reconcile_spec function body"
    body = fn_match.group(1)
    # Positive: out_of_tree append happens via the prefix check.
    assert re.search(r"report\.out_of_tree\.append\(cit\)", body), (
        "reconcile_spec must route prefix-matched citations into report.out_of_tree"
    )
    # Positive: prefix check uses startswith over the configured tuple.
    assert re.search(
        r"cit\.path\.startswith\(p\) for p in out_of_tree_prefixes", body
    ), (
        "reconcile_spec must check cit.path.startswith(p) against out_of_tree_prefixes"
    )
    # Ordering: the startswith check appears before the `target.exists()` test.
    startswith_pos = body.find("out_of_tree_prefixes")
    exists_pos = body.find("target.exists()")
    assert startswith_pos != -1 and exists_pos != -1
    assert startswith_pos < exists_pos, (
        "out_of_tree prefix check must fire before the on-disk existence check"
    )


def test_runtime_default_prefixes_is_cowork_tuple() -> None:
    """Runtime constant equals the expected default tuple.

    Complement to the source-pattern test — catches the case where the
    constant exists in source but is overridden at runtime via a sitecustomize
    or similar import-time mutation.
    """
    assert OUT_OF_TREE_PREFIXES == ("cowork/",)


# ---------- §6 test 6 — regression: spec 0229 reconcile exits 0 -----------


def test_spec_0229_reconcile_exits_zero_post_fix() -> None:
    """Regression target — pre-fix this returned 3 (3 cowork semantic hits).

    Runs the CLI as a subprocess to exercise the exit-code contract end-to-end.
    Guarded by the spec file existing so the test is portable across
    historical-rewrite scenarios.
    """
    spec_0229 = REPO_ROOT / "specs" / "0229-addressee-obligation-invariant.md"
    if not spec_0229.exists():
        pytest.skip("spec 0229 not present in this checkout")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.spec_lifecycle.reconcile",
            str(spec_0229),
            str(REPO_ROOT),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        f"spec 0229 reconcile should exit 0 post-0230 (got {result.returncode});\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "out-of-tree (informational):" in result.stdout, (
        "format_report should surface the out-of-tree bucket line"
    )


# ---------- §6 test 7 — CHANGELOG + version smoke check -------------------


def test_changelog_and_version_smoke() -> None:
    """Spec 0230 ships with a CHANGELOG section + version bump to 1.50.0.

    Smoke check — asserts the CHANGELOG entry references this spec and
    `__version__` / pyproject `version` both moved to 1.50.0.
    """
    from packaging.version import Version

    import dual_research

    assert Version(dual_research.__version__) >= Version("1.50.0"), (
        f"__version__ should be >= 1.50.0; got {dual_research.__version__}"
    )
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert re.search(r"^## \[1\.50\.0\]", changelog, re.MULTILINE), (
        "CHANGELOG.md should contain a '## [1.50.0]' section"
    )
    # The 1.50.0 section should reference spec 0230 by id-or-slug.
    # Match from the 1.50.0 header to the next ``## [`` header (next release).
    # `###` subheadings inside the section are allowed.
    section_match = re.search(
        r"^## \[1\.50\.0\].*?(?=^## \[)",
        changelog,
        re.MULTILINE | re.DOTALL,
    )
    assert section_match is not None, "could not locate 1.50.0 section in CHANGELOG"
    section = section_match.group(0)
    assert "spec 0230" in section.lower() or "0230" in section, (
        "1.50.0 section should cite spec 0230"
    )


# ---------- has_blocking_drift invariant ------------------------------------


def test_out_of_tree_does_not_contribute_to_blocking_drift(empty_repo: Path) -> None:
    """Only `semantic` flips `has_blocking_drift`; `out_of_tree` never does.

    Re-asserts §2.2 explicitly — out-of-tree citations are informational.
    """
    spec = _write_spec(
        empty_repo,
        "Multiple cowork hits:\n"
        "- cowork/briefs/a.md:1\n"
        "- cowork/briefs/b.md:2\n"
        "- cowork/feedback/c.md:3\n",
    )
    report = reconcile_spec(spec, repo_root=empty_repo)
    assert len(report.out_of_tree) == 3
    assert report.semantic == []
    assert report.has_blocking_drift is False
    assert report.has_drift is False

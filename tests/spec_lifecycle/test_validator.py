"""Tests for scripts.spec_lifecycle.validator."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.spec_lifecycle.validator import (
    validate_dev_spec,
    validate_draft,
)


def _write(p: Path, fm: dict[str, str], body: str) -> Path:
    fm_lines = "\n".join(f"{k}: {v}" for k, v in fm.items())
    p.write_text(f"---\n{fm_lines}\n---\n\n{body}")
    return p


def _good_new_feature_body() -> str:
    """Minimal non-UI new-feature body. UI-touching tests use a separate fixture."""
    return """\
# Spec 0156 — Test

## 1. Context
We need to update `scripts/spec_lifecycle/validator.py:42` because it
duplicates logic from `scripts/spec_lifecycle/append_event.py:10`.

## 2. Proposed change
Refactor with helper.

## 3. Out of scope
Nothing.

## 4. Test plan
- [ ] Unit test for new helper
- [ ] Integration smoke

## 5. Risks
Low.
"""


GOOD_DEV_FM = {
    "kind": "dev",
    "spec": '"0156"',
    "slug": "thing",
    "title": "thing",
    "type": "new-feature",
    "label": "new-feature",
    "version_bump": "MINOR",
    "status": "queued",
}


def test_valid_new_feature_passes(tmp_path: Path) -> None:
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, _good_new_feature_body())
    r = validate_dev_spec(p)
    assert r.ok, r.errors


def test_missing_frontmatter_key_fails(tmp_path: Path) -> None:
    fm = dict(GOOD_DEV_FM)
    del fm["version_bump"]
    p = _write(tmp_path / "spec.md", fm, _good_new_feature_body())
    r = validate_dev_spec(p)
    assert not r.ok
    assert any("version_bump" in e for e in r.errors)


def test_insufficient_citations_fails(tmp_path: Path) -> None:
    body = "# x\n\n## 1. Context\n\nNo citations here.\n\n## 5. Risks\nlow.\n"
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert not r.ok
    assert any("citation" in e for e in r.errors)


def test_tbd_in_prose_fails(tmp_path: Path) -> None:
    body = _good_new_feature_body().replace("Refactor with helper.", "Refactor with [TBD].")
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert not r.ok
    assert any("TBD" in e for e in r.errors)


def test_tbd_in_inline_code_is_ignored(tmp_path: Path) -> None:
    body = _good_new_feature_body() + "\n\nDocumentation note: `[TBD]` markers are forbidden.\n"
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert r.ok, r.errors


def test_open_questions_section_fails(tmp_path: Path) -> None:
    body = _good_new_feature_body() + "\n\n## 6. Open questions\n- something\n"
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert not r.ok
    assert any("open-questions heading" in e for e in r.errors)


# ─── Spec 0198 §2.1 — widened open-questions + unresolved-marker checks ────────


@pytest.mark.parametrize(
    "heading",
    [
        "## Open questions",
        "### 6. Open question",
        "## Unresolved questions",
        "## Unresolved question",
        "## To decide",
        "## TBD",
        "#### Outstanding decisions",
        "## Outstanding decision",
    ],
)
def test_forbidden_heading_variants_fail(tmp_path: Path, heading: str) -> None:
    body = _good_new_feature_body() + f"\n\n{heading}\n- something\n"
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert not r.ok, f"heading {heading!r} should fail validation"
    assert any("open-questions heading" in e for e in r.errors), r.errors


@pytest.mark.parametrize("marker", ["[TBD]", "[TODO]", "[FIXME]"])
def test_bracketed_unresolved_markers_fail(tmp_path: Path, marker: str) -> None:
    body = _good_new_feature_body().replace(
        "Refactor with helper.", f"Refactor with {marker} helper."
    )
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert not r.ok
    assert any("unresolved-decision markers" in e for e in r.errors), r.errors


def test_triple_question_marker_fails(tmp_path: Path) -> None:
    body = _good_new_feature_body().replace(
        "Refactor with helper.", "Refactor with ???something helper."
    )
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert not r.ok
    assert any("???" in e for e in r.errors), r.errors


def test_bracketed_markers_inside_backticks_pass(tmp_path: Path) -> None:
    body = _good_new_feature_body() + (
        "\n\nDocumentation: `[TBD]`, `[TODO]`, and `[FIXME]` markers are forbidden.\n"
    )
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert r.ok, r.errors


# ─── Spec 0198 §2.2 — source-artifact traceability ────────────────────────────


def _ui_friendly_new_feature_body(ui_paths: bool = True) -> str:
    """A body that touches `src/dual_research/ui/` and ships user stories + BDD."""
    suffix = "_ui" if ui_paths else "_pure"
    ui_ref = (
        "Touches `src/dual_research/ui/static/components.css:42` and "
        "`src/dual_research/ui/static/app.jsx:10`."
        if ui_paths
        else "Touches `scripts/spec_lifecycle/validator.py:42` and "
        "`scripts/spec_lifecycle/append_event.py:10`."
    )
    return f"""\
# Spec 0156 — Test {suffix}

## 1. Context
We need a tweak. {ui_ref}

## 2. Proposed change
Make the tweak.

## 3. User stories & acceptance criteria

### 3.1 — User stories
> As a viewer, I want X, so that Y.

### 3.2 — Acceptance scenarios
> **Scenario 1:** thing
> GIVEN a page state
> WHEN the user clicks foo
> THEN the bar is visible

> **Scenario 2:** thing two
> GIVEN a different state
> WHEN the user types
> THEN the result is shown

## 4. Out of scope
Nothing.

## 5. Test plan
- [ ] Unit test for helper
- [ ] Integration smoke

## 6. Risks
Low.
"""


def test_source_artifact_without_table_fails(tmp_path: Path) -> None:
    body = _good_new_feature_body().replace(
        "## 1. Context",
        "## 1. Context\nSee `prototypes/critique-iteration/NOTES.md` for the source items.",
    )
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert not r.ok
    assert any("source traceability table missing" in e for e in r.errors), r.errors


def test_source_artifact_with_table_passes(tmp_path: Path) -> None:
    body = _good_new_feature_body().replace(
        "## 1. Context\nWe need to update",
        """## 1. Context
Source: `prototypes/critique-iteration/NOTES.md`.

| source item | source quote/ref | spec section |
|---|---|---|
| iter-1 | "rebrand bar" | §2.1 |
| iter-2 | "trim padding" | §5 (deferred to spec 9999 — follow-up) |

We need to update""",
    )
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert r.ok, r.errors


def test_source_artifact_table_with_bad_section_cell_fails(tmp_path: Path) -> None:
    body = _good_new_feature_body().replace(
        "## 1. Context\nWe need to update",
        """## 1. Context
Source: `prototypes/critique-iteration/NOTES.md`.

| source item | source quote/ref | spec section |
|---|---|---|
| iter-1 | "rebrand bar" | tbd later |

We need to update""",
    )
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert not r.ok
    assert any("does not reference §2.N or §5" in e for e in r.errors), r.errors


def test_source_artifact_mention_in_section2_does_not_fire(tmp_path: Path) -> None:
    """Detection is scoped to §1 Context — discussing a path in §2 is not a citation."""
    body = _good_new_feature_body().replace(
        "Refactor with helper.",
        "Refactor with helper. We do NOT consume `prototypes/foo/NOTES.md` here.",
    )
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert r.ok, r.errors


def test_source_artifact_bare_words_do_not_fire(tmp_path: Path) -> None:
    """Bare words 'mockup' / 'canvas' / 'ideation doc' are skill-level, not validator-level."""
    body = _good_new_feature_body().replace(
        "## 1. Context\nWe need to update",
        "## 1. Context\nWe rejected the bare-word mockup heuristic. We need to update",
    )
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert r.ok, r.errors


# ─── Spec 0198 §2.3 — UI specs need user stories + BDD scenarios ──────────────


def test_ui_spec_without_user_stories_fails(tmp_path: Path) -> None:
    body = _good_new_feature_body().replace(
        "scripts/spec_lifecycle/validator.py:42",
        "src/dual_research/ui/static/app.jsx:42",
    ).replace(
        "scripts/spec_lifecycle/append_event.py:10",
        "src/dual_research/ui/static/shared.jsx:120",
    )
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert not r.ok
    assert any("user stories" in e.lower() for e in r.errors), r.errors


def test_ui_spec_with_stories_and_scenarios_passes(tmp_path: Path) -> None:
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, _ui_friendly_new_feature_body(ui_paths=True))
    r = validate_dev_spec(p)
    assert r.ok, r.errors


def test_non_ui_spec_without_user_stories_passes(tmp_path: Path) -> None:
    body = """\
# Spec 0156 — Pure backend

## 1. Context
Refactor `scripts/spec_lifecycle/validator.py:42` and `scripts/spec_lifecycle/append_event.py:10`.

## 2. Proposed change
Tighten regex.

## 3. Out of scope
Nothing.

## 4. Test plan
- [ ] Unit test for helper
- [ ] Integration smoke

## 5. Risks
Low.
"""
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert r.ok, r.errors


def test_ui_spec_with_only_one_scenario_fails(tmp_path: Path) -> None:
    """≥ 2 scenarios required for UI specs — one is not enough."""
    body = _ui_friendly_new_feature_body(ui_paths=True)
    # Truncate the second scenario by removing its GIVEN/WHEN/THEN block.
    body = body.replace(
        "> **Scenario 2:** thing two\n"
        "> GIVEN a different state\n"
        "> WHEN the user types\n"
        "> THEN the result is shown\n",
        "",
    )
    p = _write(tmp_path / "spec.md", GOOD_DEV_FM, body)
    r = validate_dev_spec(p)
    assert not r.ok
    assert any("user stories" in e.lower() for e in r.errors)


# ─── Spec 0198 §6 — template smoke test ───────────────────────────────────────


@pytest.mark.parametrize(
    "template",
    [
        "specs/_templates/new-feature.md",
        "specs/_templates/bug.md",
        "specs/_templates/refactoring.md",
        "specs/_templates/breaking.md",
        "specs/_templates/test.md",
    ],
)
def test_template_does_not_trigger_new_guardrails(template: str) -> None:
    """Templates are placeholders (no real citations), so they're expected to fail the
    citation check. But the spec 0198 guardrails (open-questions heading, traceability
    table, user stories) MUST NOT fire spuriously on the template comment block or
    placeholder text."""
    from pathlib import Path as _P

    repo = _P(__file__).resolve().parents[2]
    p = repo / template
    assert p.exists(), p
    r = validate_dev_spec(p)
    forbidden_phrases = (
        "open-questions heading",
        "unresolved-decision markers",
        "source traceability table",
        "user stories",
    )
    for err in r.errors:
        for phrase in forbidden_phrases:
            assert phrase not in err.lower(), (
                f"template {template} spuriously triggered {phrase!r}: {err}"
            )


def test_bug_missing_expected_actual_fails(tmp_path: Path) -> None:
    fm = dict(GOOD_DEV_FM)
    fm["type"] = "bug"
    fm["label"] = "bug"
    body = """# x

## 1. Reproduction
Some steps but no Expected/Actual.
Cite `src/foo.py:10` and `src/bar.py:20`.

## 4. Regression-prevention test
- [ ] does something
"""
    p = _write(tmp_path / "spec.md", fm, body)
    r = validate_dev_spec(p)
    assert not r.ok
    assert any("Expected" in e for e in r.errors)
    assert any("Actual" in e for e in r.errors)


def test_refactoring_must_disclaim_features(tmp_path: Path) -> None:
    fm = dict(GOOD_DEV_FM)
    fm["type"] = "refactoring"
    fm["label"] = "refactoring"
    body = """# x

## 1. Current state
Cite `src/foo.py:10` and `src/bar.py:20`.

## 5. Out of scope
Adjacent code.

## 4. Behavior preservation
- [ ] existing tests pass

## 3. Stepwise migration
- step
"""
    p = _write(tmp_path / "spec.md", fm, body)
    r = validate_dev_spec(p)
    assert not r.ok
    assert any("new features" in e for e in r.errors)


def test_draft_passes_minimal(tmp_path: Path) -> None:
    p = _write(
        tmp_path / "draft.md",
        {"kind": "draft", "draft_id": '"007"', "slug": "x", "title": "t", "status": "draft"},
        "# Body\n",
    )
    r = validate_draft(p)
    assert r.ok, r.errors


def test_draft_missing_key_fails(tmp_path: Path) -> None:
    p = _write(tmp_path / "draft.md", {"kind": "draft"}, "# body\n")
    r = validate_draft(p)
    assert not r.ok

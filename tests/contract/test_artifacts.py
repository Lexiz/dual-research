"""Spec 0114 — phase artifact hashing tests.
Spec 0117 — artifact registry tests.
"""

from __future__ import annotations

import pytest

from dual_research.contract.artifacts import (
    REGISTRY,
    ArtifactKind,
    canonical_hash,
    display_name,
    hash_draft_content,
    is_known,
    kind_of,
)


def test_canonical_hash_stable_for_identical_text():
    a = "### AGREED_PLAN\n\n#### Sections\n1. Title: foo\n"
    b = "### AGREED_PLAN\n\n#### Sections\n1. Title: foo\n"
    assert canonical_hash(a) == canonical_hash(b)


def test_canonical_hash_tolerates_trailing_whitespace():
    a = "### AGREED_PLAN\n\nbody\n"
    b = "### AGREED_PLAN\n\nbody    \n\n"
    assert canonical_hash(a) == canonical_hash(b)


def test_canonical_hash_tolerates_line_endings():
    a = "line1\nline2"
    b = "line1\r\nline2"
    assert canonical_hash(a) == canonical_hash(b)


def test_canonical_hash_folds_smart_quotes():
    a = "hello 'world'"
    b = "hello ‘world’"
    assert canonical_hash(a) == canonical_hash(b)


def test_canonical_hash_distinguishes_real_diffs():
    a = "### AGREED_PLAN\n\nclaim A"
    b = "### AGREED_PLAN\n\nclaim B"
    assert canonical_hash(a) != canonical_hash(b)


def test_hash_draft_content_alias():
    assert hash_draft_content("foo") == canonical_hash("foo")


# ─── Spec 0117 — artifact registry ────────────────────────────────────


def test_registry_is_non_empty():
    assert len(REGISTRY) > 0


def test_every_registry_entry_has_non_empty_display_template():
    for defn in REGISTRY:
        assert defn.display_template, f"empty display_template for {defn.id_template!r}"


def test_every_registry_id_has_unique_template():
    seen = set()
    for defn in REGISTRY:
        assert defn.id_template not in seen, f"duplicate id_template {defn.id_template!r}"
        seen.add(defn.id_template)


@pytest.mark.parametrize(
    "artifact_id, expected",
    [
        ("system.preamble", "Methodology preamble"),
        ("system.task.input", "Preflight instructions"),
        ("system.task.closeout", "Closeout instructions"),
        ("user_prompt.message", "Chat message"),
        ("phase1.claude", "Claude's research plan"),
        ("phase1.openai", "GPT's research plan"),
        ("phase3.draft.v1", "Initial unified draft (v1)"),
        ("current_draft", "Current draft (latest version)"),
        ("phase0.agreement.interpretation", "Agreed interpretation"),
        ("phase2.agreement.plan", "Agreed plan"),
        ("phase2.agreement.drafter", "Drafter selection"),
        ("phase4.agreement.draft_acceptance", "Agreed draft acceptance"),
        ("all_carry_forward", "All carry-forward items"),
        ("final.document", "Final document"),
    ],
)
def test_display_name_static_ids(artifact_id: str, expected: str):
    assert display_name(artifact_id) == expected


@pytest.mark.parametrize(
    "artifact_id, expected",
    [
        # Examples produced by the rules — section "Naming rules" in spec 0117.
        ("phase0.claude.r3", "Preflight turn · Claude · round 3"),
        ("phase4.openai.r5", "Review turn · GPT · round 5"),
        ("phase4.draft.v7", "Revised draft v7"),
        # Additional template-substitution coverage.
        ("phase0.openai.r1", "Preflight turn · GPT · round 1"),
        ("phase2.claude.r2", "Negotiation turn · Claude · round 2"),
        ("phase2.openai.r4", "Negotiation turn · GPT · round 4"),
        ("phase4.claude.r1", "Review turn · Claude · round 1"),
        ("phase4.draft.v2", "Revised draft v2"),
    ],
)
def test_display_name_template_substitution(artifact_id: str, expected: str):
    assert display_name(artifact_id) == expected


def test_display_name_renders_openai_as_gpt():
    # In user-visible labels, 'openai' is rendered as 'GPT', not 'OpenAI'.
    assert "GPT" in display_name("phase1.openai")
    assert "OpenAI" not in display_name("phase1.openai")
    assert display_name("phase0.openai.r2") == "Preflight turn · GPT · round 2"


def test_display_name_attachment_with_title_lookup():
    raw_id = "notion:36099f3e507f818285b7e016638453e7"
    artifact_id = f"user_prompt.attachment.{raw_id}"
    titles = {raw_id: "Partner Vetting — Architecture Proposal (Proposal 2)"}
    assert display_name(artifact_id, title_for_id=titles) == (
        "Attachment · Partner Vetting — Architecture Proposal (Proposal 2)"
    )


def test_display_name_attachment_falls_back_to_raw_id_without_title():
    artifact_id = "user_prompt.attachment.notion:abc123"
    assert display_name(artifact_id) == "Attachment · notion:abc123"


def test_display_name_unknown_id_returns_id_unchanged():
    assert display_name("definitely.not.a.registered.artifact") == (
        "definitely.not.a.registered.artifact"
    )
    assert display_name("phase99.banana.r1") == "phase99.banana.r1"


def test_is_known_for_concrete_ids():
    assert is_known("system.preamble")
    assert is_known("phase1.claude")
    assert is_known("phase4.draft.v2")
    assert is_known("phase0.claude.r3")
    assert is_known("user_prompt.attachment.notion:abc")


def test_is_known_for_literal_template_strings():
    # Callers can probe templates directly without expanding placeholders.
    assert is_known("phase0.<agent>.r<N>")
    assert is_known("user_prompt.attachment.<id>")


def test_is_known_false_for_unregistered():
    assert not is_known("phase99.banana.r1")
    assert not is_known("definitely.not.registered")


@pytest.mark.parametrize(
    "artifact_id, expected_kind",
    [
        ("system.preamble", ArtifactKind.SYSTEM),
        ("user_prompt.message", ArtifactKind.USER),
        ("user_prompt.attachment.foo", ArtifactKind.USER),
        ("prior_turns.phase0", ArtifactKind.DERIVED),
        ("phase0.claude.r3", ArtifactKind.AGENT_OUTPUT),
        ("phase1.claude", ArtifactKind.AGENT_OUTPUT),
        ("phase2.openai.r2", ArtifactKind.AGENT_OUTPUT),
        ("phase3.draft.v1", ArtifactKind.DRAFT),
        ("phase4.draft.v3", ArtifactKind.DRAFT),
        ("current_draft", ArtifactKind.DRAFT),
        ("phase0.agreement.interpretation", ArtifactKind.AGREEMENT),
        ("phase2.agreement.plan", ArtifactKind.AGREEMENT),
        ("final.document", ArtifactKind.FINAL),
    ],
)
def test_kind_of(artifact_id: str, expected_kind: ArtifactKind):
    assert kind_of(artifact_id) == expected_kind


def test_kind_of_unknown_returns_none():
    assert kind_of("phase99.banana.r1") is None
    assert kind_of("nonexistent") is None


def test_every_registry_id_template_resolves_to_some_display():
    # Coverage smoke-test: every template, when probed with a synthesized
    # concrete ID (substituting claude/r1/sample-id for placeholders),
    # produces a non-empty display name that is NOT the raw ID. This
    # guards against typos in the template strings themselves.
    for defn in REGISTRY:
        concrete = (
            defn.id_template
            .replace("<agent>", "claude")
            .replace("<N>", "1")
            .replace("<id>", "sample-id")
        )
        rendered = display_name(concrete)
        assert rendered, f"empty render for {concrete!r}"
        assert rendered != concrete, (
            f"render of {concrete!r} should not equal raw ID — registry miss?"
        )


# ─── Spec 0117 step 2 — registry coverage / drift guards ─────────────


def test_spec_0117_normative_id_table_matches_registry():
    # Snapshot of the 35-row normative artifact registry table from
    # spec 0117. If a new artifact is added, both the spec table and
    # this list must be updated in lockstep. Order is preserved from
    # the spec.
    expected = (
        "system.preamble",
        "system.task.input",
        "system.task.research_plan",
        "system.task.plan_negotiation",
        "system.task.drafting",
        "system.task.review",
        "system.task.closeout",
        # Spec 0148 D13/D14 — agent-layer-emitted pieces.
        "system.web_sources",
        "system.tool_definitions",
        "user_prompt.message",
        "user_prompt.attachment.<id>",
        "prior_turns.phase0",
        "prior_turns.phase2",
        "prior_turns.phase4",
        "ledger.standing_items",
        "closeout.request",
        "phase0.<agent>.r<N>",
        "phase1.claude",
        "phase1.openai",
        "phase2.<agent>.r<N>",
        "phase3.draft.v1",
        "phase4.<agent>.r<N>",
        "phase4.draft.v<N>",
        "current_draft",
        "all_p2_turns",
        "phase0.agreement.interpretation",
        "phase2.agreement.plan",
        "phase2.agreement.drafter",
        "phase4.agreement.draft_acceptance",
        "carry_forward.phase0",
        "carry_forward.phase2",
        "carry_forward.phase4",
        "all_carry_forward",
        "final.document",
    )
    actual = tuple(defn.id_template for defn in REGISTRY)
    assert actual == expected


def test_no_unregistered_artifact_id_literals_in_src():
    """Scan src/dual_research/**.py for string literals that look like
    canonical artifact IDs but aren't registered.

    Forward-looking CI guard: spec 0114/0115 introduce code paths that
    will start emitting artifact IDs. If a future change hardcodes
    a string matching the registry's prefixes but the registry doesn't
    know about it, this test fails before the drift ships.
    """
    import ast
    import re
    from pathlib import Path

    from dual_research.contract.artifacts import is_known

    # Prefixes that uniquely identify "this string is meant to be an
    # artifact ID, not arbitrary prose." Narrow enough that docstring
    # fragments don't match by accident.
    _ID_PREFIX_RE = re.compile(
        r"^(?:"
        r"system\.preamble"
        r"|system\.task\.[a-z_]+"
        r"|user_prompt(?:\.message|\.attachment\.[^\s]+)?"
        r"|prior_turns\.phase[024]"
        r"|ledger\.standing_items"
        r"|closeout\.request"
        r"|phase[0-4]\.(?:claude|openai|draft\.v\d+|agreement\.[a-z_]+|<agent>\.r<N>|[a-z]+\.r\d+)"
        r"|current_draft"
        r"|all_p2_turns"
        r"|all_carry_forward"
        r"|carry_forward\.phase[024]"
        r"|final\.document"
        r")$"
    )

    src_root = Path(__file__).resolve().parents[2] / "src" / "dual_research"
    assert src_root.is_dir(), f"expected src tree at {src_root}"

    offenders: list[tuple[str, int, str]] = []
    for py_file in src_root.rglob("*.py"):
        # Skip the registry itself — its REGISTRY tuple is defined to
        # contain these literals.
        if py_file.name == "artifacts.py" and "contract" in py_file.parts:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            v = node.value
            if not _ID_PREFIX_RE.match(v):
                continue
            if is_known(v):
                continue
            offenders.append((str(py_file.relative_to(src_root)), node.lineno, v))

    assert not offenders, (
        "Unregistered artifact-ID-shaped string literals found in src/:\n"
        + "\n".join(f"  {path}:{lineno}  {value!r}" for path, lineno, value in offenders)
    )

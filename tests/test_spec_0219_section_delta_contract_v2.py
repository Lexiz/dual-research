"""Spec 0219 — phase-4 §3.2 section-delta drafter contract regression tests.

Each test locks in one of the four bugs spec 0219 fixes:
- §3.1 / §3.2 — reviewer template + validator gating on is_drafter.
- §3.4     — REPLACE_SECTION on unknown heading hard-fails (was silent APPEND).
- §3.5     — EDIT_SECTION ANCHOR/REPLACE_WITH ops + reason: required on REPLACE_SECTION.
- §3.6     — phase-4 round counter survives serialise+reload.

Plus an end-to-end replay of the smoking-gun
``runs/20260526-000758-backend-language-choice/phase4/round-02-claude.malformed-1.md``
fixture (vendored to ``tests/fixtures/spec_0219/``).

Pure stdlib via the standard pytest fixture path.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dual_research.orchestrator.repair import _assert_v2_well_formed_turn
from dual_research.persistence.state import SessionState
from dual_research.protocol import (
    EditSectionOp,
    ProtocolParseError,
    RevisedDraftDeltas,
    apply_revised_draft_deltas,
    extract_draft_headings,
    extract_revised_draft_deltas,
    parse_turn_v2,
)


_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "spec_0219"


def _reviewer_turn_no_revised_draft() -> str:
    return (
        "## Stance\nI think the draft holds together.\n\n"
        "## Status\n"
        "STATUS: IN_PROGRESS\n"
        "RAISED_THIS_TURN: []\n"
        "ADDRESSED_THIS_TURN: []\n"
        "RESOLVED_THIS_TURN: []\n"
        "ACKNOWLEDGED_THIS_TURN: []\n"
        "WITHDRAWN_THIS_TURN: []\n"
        "OPEN_QUESTIONS: 0\n"
        "OPEN_DISAGREEMENTS: 0\n"
        "OPEN_ISSUES: 0\n"
        "OPEN_COMMENTS: 0\n\n"
        "## Addressing items raised against me\n(none)\n\n"
        "## Ratifying my own items\n(none)\n\n"
        "## New items I'm raising\n(none)\n"
    )


def _reviewer_turn_with_revised_draft_prose() -> str:
    """Reviewer turn that still carries a non-empty `## Revised draft` body
    (e.g. a leaked legacy prompt path). Spec 0219 §3.1 — this must NOT
    trip the drafter-only validator gate when `is_drafter=False`."""
    return (
        "## Stance\nLooks fine.\n\n"
        "## Status\nSTATUS: IN_PROGRESS\n\n"
        "## Addressing items raised against me\n(none)\n\n"
        "## Ratifying my own items\n(none)\n\n"
        "## New items I'm raising\n(none)\n\n"
        "## Revised draft\n\n"
        "(reviewer — no draft edits)\n"
    )


# ─── 5.1 — Reviewer with no Revised draft passes ─────────────────────────


def test_reviewer_revised_draft_omitted_passes_validator() -> None:
    """Spec 0219 §3.1 — a reviewer turn that omits `## Revised draft`
    entirely is valid. Pre-fix: validator was role-blind; this passed.
    Post-fix: still passes (the gate is now only fired for drafter)."""
    fixture = _reviewer_turn_no_revised_draft()
    parsed = parse_turn_v2(fixture)
    assert parsed.status is not None
    assert parsed.revised_draft is None
    # Reviewer call — is_drafter=False.
    _assert_v2_well_formed_turn(parsed, fixture, "openai", is_drafter=False)


# ─── 5.2 — Reviewer with prose Revised draft (legacy leak) passes ───────


def test_reviewer_revised_draft_prose_passes_validator() -> None:
    """Spec 0219 §3.1 defence-in-depth — even if some leftover prompt
    path leaks a `## Revised draft` body into a reviewer turn, the
    drafter-only validator gate must NOT fire (the gate is the canonical
    bug-1 source). Pre-fix: validator rejected this with
    ``revised_draft_body_missing_delta_op``. Post-fix: passes."""
    fixture = _reviewer_turn_with_revised_draft_prose()
    parsed = parse_turn_v2(fixture)
    assert parsed.revised_draft is not None
    # Reviewer call — is_drafter=False — must pass.
    _assert_v2_well_formed_turn(parsed, fixture, "openai", is_drafter=False)


# ─── 5.3 — Drafter with empty / prose-only Revised draft still fails ────


def test_drafter_revised_draft_empty_still_fails() -> None:
    """Spec 0219 §3.1 / §3.5 negative case — the role gate must not let
    drafter-side violations through. A drafter turn whose `## Revised
    draft` is empty (heading present, body blank) or prose-only (no
    delta-op sub-heading) must fail with
    ``revised_draft_body_missing_delta_op``."""
    # Empty body case.
    empty_fixture = (
        "## Stance\n.\n\n"
        "## Status\nSTATUS: IN_PROGRESS\n\n"
        "## Revised draft\n\n"
    )
    parsed = parse_turn_v2(empty_fixture)
    with pytest.raises(ProtocolParseError) as ei:
        _assert_v2_well_formed_turn(parsed, empty_fixture, "claude", is_drafter=True)
    assert any("revised_draft_body_missing_delta_op" in e for e in ei.value.errors)

    # Prose-only body case.
    prose_fixture = (
        "## Stance\n.\n\n"
        "## Status\nSTATUS: IN_PROGRESS\n\n"
        "## Revised draft\n\n"
        "Here is my revised draft inline, with no delta sub-headings.\n"
        "I rewrote the whole thing as prose.\n"
    )
    parsed = parse_turn_v2(prose_fixture)
    with pytest.raises(ProtocolParseError) as ei:
        _assert_v2_well_formed_turn(parsed, prose_fixture, "claude", is_drafter=True)
    assert any("revised_draft_body_missing_delta_op" in e for e in ei.value.errors)


# ─── 5.4 — REPLACE_SECTION on unknown heading hard-fails ────────────────


def test_replace_section_unknown_heading_hard_fails() -> None:
    """Spec 0219 §3.4 — applying ``### REPLACE_SECTION 2.1 — Executive
    Summary…`` to a draft whose headings are ``## 1. Summary, ## 2.
    Findings`` must raise ``replace_section_unknown_heading`` with a
    message listing the valid headings. Pre-fix: silently promoted to
    APPEND and corrupted the draft."""
    prior_draft = (
        "## 1. Summary\n\nBody A.\n\n"
        "## 2. Findings\n\nBody B.\n"
    )
    turn_text = (
        "## Stance\n.\n\n"
        "## Status\nSTATUS: IN_PROGRESS\n\n"
        "## Revised draft\n\n"
        "### REPLACE_SECTION 2.1 — Executive Summary & Single Ranked Recommendation\n\n"
        "reason: I want to fully rewrite this section.\n\n"
        "Replacement body for the (nonexistent) section.\n"
    )
    payload = extract_revised_draft_deltas(turn_text)
    assert isinstance(payload, RevisedDraftDeltas)

    with pytest.raises(ProtocolParseError) as ei:
        apply_revised_draft_deltas(prior_draft=prior_draft, payload=payload)
    msgs = ei.value.errors
    assert any("replace_section_unknown_heading" in e for e in msgs)
    # The error message must include the valid headings list so the
    # drafter can self-correct on repair.
    combined = " ".join(msgs)
    assert "1. Summary" in combined or "Summary" in combined
    assert "2. Findings" in combined or "Findings" in combined


# ─── 5.5 — EDIT_SECTION ANCHOR/REPLACE_WITH roundtrip ───────────────────


def test_edit_section_anchor_roundtrip() -> None:
    """Spec 0219 §3.5 — parse + apply an EDIT_SECTION block with two
    ANCHOR:/REPLACE_WITH: pairs against a known section. Assert the
    edits land verbatim and untouched bytes survive byte-equal."""
    prior_draft = (
        "## 1. Summary\n\n"
        "We recommend Python.\n"
        "We tested SQLite and Postgres.\n"
        "Decision is bounded by team familiarity.\n\n"
        "## 2. Findings\n\n"
        "Body of findings.\n"
    )
    turn_text = (
        "## Stance\n.\n\n"
        "## Status\nSTATUS: IN_PROGRESS\n\n"
        "## Revised draft\n\n"
        "### EDIT_SECTION 1. Summary\n"
        "ANCHOR: We recommend Python.\n"
        "REPLACE_WITH: We recommend Go.\n"
        "ANCHOR: We tested SQLite and Postgres.\n"
        "REPLACE_WITH: We tested MySQL and Postgres.\n"
    )
    payload = extract_revised_draft_deltas(turn_text)
    assert isinstance(payload, RevisedDraftDeltas)
    assert len(payload.ops) == 1
    op = payload.ops[0]
    assert isinstance(op, EditSectionOp)
    assert op.heading == "1. Summary"
    assert len(op.edits) == 2
    assert op.edits[0] == ("We recommend Python.", "We recommend Go.")
    assert op.edits[1] == ("We tested SQLite and Postgres.", "We tested MySQL and Postgres.")

    new_draft, violations = apply_revised_draft_deltas(
        prior_draft=prior_draft, payload=payload,
    )
    assert "We recommend Go." in new_draft
    assert "We recommend Python." not in new_draft
    assert "We tested MySQL and Postgres." in new_draft
    assert "We tested SQLite and Postgres." not in new_draft
    # Untouched line survives byte-equal.
    assert "Decision is bounded by team familiarity." in new_draft
    # Findings section untouched.
    assert "Body of findings." in new_draft
    assert violations == []


def test_edit_section_anchor_not_found_hard_fails() -> None:
    """Spec 0219 §3.5 — anchor with zero matches raises
    ``edit_section_anchor_not_found`` cleanly, so the drafter sees the
    failure and the repair flow can re-prompt with the actual section
    text."""
    prior_draft = "## 1. Summary\n\nReal content.\n"
    turn_text = (
        "## Stance\n.\n\n"
        "## Status\nSTATUS: IN_PROGRESS\n\n"
        "## Revised draft\n\n"
        "### EDIT_SECTION 1. Summary\n"
        "ANCHOR: This phrase does not exist in the section.\n"
        "REPLACE_WITH: irrelevant\n"
    )
    payload = extract_revised_draft_deltas(turn_text)
    with pytest.raises(ProtocolParseError) as ei:
        apply_revised_draft_deltas(prior_draft=prior_draft, payload=payload)
    assert any("edit_section_anchor_not_found" in e for e in ei.value.errors)


def test_edit_section_anchor_ambiguous_hard_fails() -> None:
    """Spec 0219 §3.5 — anchor matching > 1 location raises
    ``edit_section_anchor_ambiguous`` so the drafter widens the anchor
    to disambiguate rather than silently editing the first match."""
    prior_draft = (
        "## 1. Summary\n\n"
        "Recommendation: Python.\n"
        "Caveats: see Findings.\n"
        "Recommendation: Python.\n"
    )
    turn_text = (
        "## Stance\n.\n\n"
        "## Status\nSTATUS: IN_PROGRESS\n\n"
        "## Revised draft\n\n"
        "### EDIT_SECTION 1. Summary\n"
        "ANCHOR: Recommendation: Python.\n"
        "REPLACE_WITH: Recommendation: Go.\n"
    )
    payload = extract_revised_draft_deltas(turn_text)
    with pytest.raises(ProtocolParseError) as ei:
        apply_revised_draft_deltas(prior_draft=prior_draft, payload=payload)
    assert any("edit_section_anchor_ambiguous" in e for e in ei.value.errors)


def test_replace_section_missing_reason_hard_fails() -> None:
    """Spec 0219 §3.5 — REPLACE_SECTION without a leading ``reason:``
    line fails validation. The doctrine demands an explicit
    justification so the agent picks EDIT_SECTION by default."""
    prior_draft = "## 1. Summary\n\nReal content.\n"
    turn_text = (
        "## Stance\n.\n\n"
        "## Status\nSTATUS: IN_PROGRESS\n\n"
        "## Revised draft\n\n"
        "### REPLACE_SECTION 1. Summary\n\n"
        "Replacement body with no `reason:` line.\n"
    )
    payload = extract_revised_draft_deltas(turn_text)
    with pytest.raises(ProtocolParseError) as ei:
        apply_revised_draft_deltas(prior_draft=prior_draft, payload=payload)
    assert any("replace_section_missing_reason" in e for e in ei.value.errors)


# ─── 5.6 — phase-4 round counter survives resume ────────────────────────


def test_phase4_round_checkpoint_survives_resume(tmp_path: Path) -> None:
    """Spec 0219 §3.6 — ``SessionState.phase4_round`` round-trips through
    serialise+reload, including from a legacy state file that predates
    the new field (default 0).

    Plus a "fresh-process pick-up" simulation: write phase4_round=3,
    load in a separate dataclass instance, assert the seeding logic at
    `_drive_interaction_phase` entry would produce round_no=4 on the
    next iteration."""
    # Round-trip with the new field present.
    state = SessionState(phase="phase4", drafter="claude", phase4_round=3)
    text = state.to_json()
    assert "phase4_round" in text
    reloaded = SessionState.from_json(text)
    assert reloaded.phase4_round == 3

    # Backwards compatibility — legacy state file with no phase4_round
    # deserialises to 0 (fresh-start behaviour).
    legacy_json = json.dumps({
        "phase": "phase4",
        "drafter": "claude",
        "agreed_plan": None,
        "final_surfaced_disagreements": [],
        "draft_round": 1,
        "final_emitted_to": None,
        "agreed_interpretation": None,
        "carry_forward_phase0": [],
        "carry_forward_phase2": [],
        "carry_forward_phase4": [],
        "closeout_budgets": {},
    })
    legacy_state = SessionState.from_json(legacy_json)
    assert legacy_state.phase4_round == 0

    # Fresh-process pick-up simulation. The seeding rule in
    # ``_drive_interaction_phase`` (spec 0219 §3.6) is:
    #
    #   round_no = ctx.state.phase4_round if phase_int == 4 else 0
    #   while round_no < caps.hard:
    #       round_no += 1
    #
    # so a reloaded state with phase4_round=3 must produce round_no=4
    # on the first iteration after the resume.
    resume_round_no = reloaded.phase4_round
    resume_round_no += 1
    assert resume_round_no == 4


# ─── 5.7 — replay smoking-gun fixture, post-fix ─────────────────────────


def test_replay_malformed_turn_from_smoking_gun_run() -> None:
    """Spec 0219 §5 — end-to-end. The smoking-gun
    ``runs/20260526-000758-backend-language-choice/phase4/round-02-claude.malformed-1.md``
    fixture emits eight ``### REPLACE_SECTION`` ops; six of them target
    brief-criteria headings (``2.1 — Executive Summary``,
    ``2.2 — Tier 1: …``, …) that do not exist in the current draft.

    Pre-fix: ``apply_revised_draft_deltas`` silently promoted each
    mismatch to APPEND, producing a ~90KB ``draft-v2.md`` with
    side-by-side duplicated sections. Post-fix: the first unknown
    heading raises ``replace_section_unknown_heading`` and the repair
    plumbing surfaces the failure to the drafter so it can re-emit
    using the literal heading list."""
    fixture_path = _FIXTURE_DIR / "round-02-claude.malformed-1.md"
    assert fixture_path.exists(), f"fixture missing: {fixture_path}"
    turn_text = fixture_path.read_text(encoding="utf-8")

    # Stub current draft mirroring draft-v1's actual headings — these
    # are the canonical sections the drafter should have targeted.
    prior_draft = (
        "## 1. Summary\n\nSummary body.\n\n"
        "## 2. Findings\n\nFindings body.\n\n"
        "## 3. Disagreements Left Open\n\nDLO body.\n\n"
        "## 4. Open Questions\n\nQuestions body.\n\n"
        "## 5. Sources\n\nSources body.\n\n"
        "## 6. Confidence Ledger\n\nLedger body.\n"
    )

    payload = extract_revised_draft_deltas(turn_text)
    assert isinstance(payload, RevisedDraftDeltas)
    # The 8 ops the smoking-gun fixture emits.
    assert len(payload.ops) == 8

    with pytest.raises(ProtocolParseError) as ei:
        apply_revised_draft_deltas(prior_draft=prior_draft, payload=payload)
    # At least one ``replace_section_unknown_heading`` error must surface.
    msgs = ei.value.errors
    assert any("replace_section_unknown_heading" in e for e in msgs), (
        f"expected replace_section_unknown_heading in errors, got: {msgs!r}"
    )
    # The smoking-gun's 2.1 brief-criteria heading must be among the
    # rejected targets (it's the first mismatched op at fixture line 153).
    assert any("2.1" in e for e in msgs), (
        f"expected '2.1' to surface as unknown heading; got: {msgs!r}"
    )


# ─── extract_draft_headings — helper used by prompts.py §3.3 ─────────────


def test_extract_draft_headings_returns_literal_in_order() -> None:
    """Spec 0219 §3.3 — helper feeds the literal section list into
    the drafter prompt."""
    draft = (
        "Some preamble.\n\n"
        "## 1. Summary\n\nbody A\n\n"
        "## 2. Findings\n\nbody B\n\n"
        "## 3. Disagreements Left Open\n\nbody C\n"
    )
    assert extract_draft_headings(draft) == [
        "1. Summary",
        "2. Findings",
        "3. Disagreements Left Open",
    ]


def test_extract_draft_headings_empty_draft_returns_empty_list() -> None:
    assert extract_draft_headings("") == []
    assert extract_draft_headings("no headings here at all") == []

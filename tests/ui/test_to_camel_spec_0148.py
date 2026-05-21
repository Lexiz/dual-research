"""Spec 0148 D16 — single-segment canonical-ID allowlist in ``_to_camel``.

The server-side ``_to_camel`` previously preserved only dotted canonical
IDs (spec 0146); single-segment IDs (``user_prompt``, ``current_draft``,
``all_p2_turns``, ``all_carry_forward``) were still camelCased on the
wire and inverted by the FE ``normalisePiecesRaw`` shim. Spec 0148
retires the shim by extending the guard with an import-time-derived
allowlist sourced from the artifact registry.
"""

from __future__ import annotations

from dual_research.ui.server import _CANONICAL_SINGLE_SEGMENT_IDS, _to_camel


def test_allowlist_contains_known_single_segment_canonical_ids() -> None:
    # Today the registry has exactly four single-segment IDs without
    # ``<>`` placeholders. New additions to the registry are picked up
    # automatically; this assertion regression-pins the present set.
    expected_minimum = {"user_prompt", "current_draft", "all_p2_turns", "all_carry_forward"}
    assert expected_minimum.issubset(_CANONICAL_SINGLE_SEGMENT_IDS), (
        f"missing canonical IDs: {expected_minimum - _CANONICAL_SINGLE_SEGMENT_IDS}"
    )


def test_single_segment_canonical_ids_pass_through_verbatim() -> None:
    out = _to_camel({
        "user_prompt": 1,
        "current_draft": 2,
        "all_p2_turns": 3,
        "all_carry_forward": 4,
        "phase_summary_0": 5,  # not a canonical ID — still camelCases
    })
    assert out["user_prompt"] == 1
    assert out["current_draft"] == 2
    assert out["all_p2_turns"] == 3
    assert out["all_carry_forward"] == 4
    # `_SNAKE_RE` matches `_<letter>` so `phase_summary_0` becomes
    # `phaseSummary_0` (the trailing `_0` survives because the regex
    # requires a letter to follow). The point of this assertion is that
    # the leading underscores DO transform — non-canonical keys aren't
    # caught by the allowlist guard.
    assert "phase_summary" not in out  # untouched form is gone
    assert any(k.startswith("phaseSummary") for k in out)


def test_dotted_keys_still_pass_through() -> None:
    out = _to_camel({
        "user_prompt.message": 10,
        "system.web_sources": 20,
        "system.tool_definitions": 30,
    })
    assert out == {
        "user_prompt.message": 10,
        "system.web_sources": 20,
        "system.tool_definitions": 30,
    }


def test_non_canonical_snake_case_still_camelcases() -> None:
    # Non-canonical keys retain the existing spec-0146 behaviour.
    out = _to_camel({"started_at": "2026-05-22", "phase_timings": {0: 12}})
    assert out == {"startedAt": "2026-05-22", "phaseTimings": {"0": 12}}


def test_canonical_id_inside_nested_dict_pass_through() -> None:
    # The recursive descent applies the guard at every level.
    out = _to_camel({"phase_token_usage": {"phase0_claude": {"user_prompt": 1}}})
    assert out == {"phaseTokenUsage": {"phase0Claude": {"user_prompt": 1}}}

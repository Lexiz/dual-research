"""Spec 0146 — dotted-key preservation in `_to_camel`.

Canonical artifact IDs (``user_prompt.message``, ``prior_turns.phase0``,
``system.task.research_plan``) are the Python source of truth for the
artifact registry; the wire payload must preserve them so the JS-side
Consumption card can look them up with the same key shape.
"""

from __future__ import annotations

from dual_research.ui.server import _to_camel


def test_dotted_keys_preserved_verbatim() -> None:
    out = _to_camel({"user_prompt.message": 100})
    assert out == {"user_prompt.message": 100}


def test_dotted_keys_with_multiple_underscores_preserved() -> None:
    # `system.task.research_plan` is canonical; the trailing underscore
    # MUST survive so JS lookups land. Pre-0146 this came across as
    # `system.task.researchPlan` and the lookup missed.
    out = _to_camel({"system.task.research_plan": 1})
    assert out == {"system.task.research_plan": 1}


def test_single_segment_snake_case_still_camelcased() -> None:
    # Plain snake_case (no dot) keeps the existing behaviour.
    out = _to_camel({"started_at": "2026-05-21", "phase_timings": {}})
    assert out == {"startedAt": "2026-05-21", "phaseTimings": {}}


def test_mixed_dotted_and_snake_case() -> None:
    out = _to_camel({
        "user_prompt.message": 100,
        "prior_turns.phase0": 50,
        "started_at": "x",
        "phase_timings": {"r1": 1, "r2": 2},
    })
    assert out == {
        "user_prompt.message": 100,
        "prior_turns.phase0": 50,
        "startedAt": "x",
        "phaseTimings": {"r1": 1, "r2": 2},
    }


def test_nested_dict_dotted_key_inside_phase_timings_preserved() -> None:
    # Nested dotted keys preserved at every depth.
    out = _to_camel({"phase_timings": {"system.task.input": 42}})
    assert out == {"phaseTimings": {"system.task.input": 42}}


def test_attachment_id_keys_preserved() -> None:
    out = _to_camel({
        "user_prompt.attachment.briefing": 1234,
        "user_prompt.attachment.abc123": 5678,
    })
    assert out == {
        "user_prompt.attachment.briefing": 1234,
        "user_prompt.attachment.abc123": 5678,
    }


def test_list_of_dicts_each_dotted_key_preserved() -> None:
    out = _to_camel([
        {"user_prompt.message": 1, "input_tokens": 10},
        {"prior_turns.phase2": 2, "output_tokens": 20},
    ])
    assert out == [
        {"user_prompt.message": 1, "inputTokens": 10},
        {"prior_turns.phase2": 2, "outputTokens": 20},
    ]


def test_int_keys_still_coerced_to_str() -> None:
    # Regression-pin on the existing non-string-key path.
    out = _to_camel({1: "a", 2: "b"})
    assert out == {"1": "a", "2": "b"}


def test_primitives_passed_through() -> None:
    assert _to_camel(42) == 42
    assert _to_camel("foo") == "foo"
    assert _to_camel(None) is None
    assert _to_camel([1, 2, 3]) == [1, 2, 3]

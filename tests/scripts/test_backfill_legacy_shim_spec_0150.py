"""Spec 0150 §6 — translation-table + edge-case pins for the legacy-shim backfill.

Pins the legacy → canonical key translation in
``scripts/backfill_legacy_shim.py`` against the JS-side
``LEGACY_KEY_TO_CANONICAL`` map in ``ui/static/artifacts.jsx`` so the two
surfaces can never drift. Without this pin, the backfill could write
data the post-deletion FE can't render correctly.
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "backfill_legacy_shim.py"
ARTIFACTS_JSX_PATH = REPO_ROOT / "src" / "dual_research" / "ui" / "static" / "artifacts.jsx"


def _load_script_module():
    import sys
    name = "backfill_legacy_shim_test_module"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def script_mod():
    return _load_script_module()


def _parse_js_translation_table(jsx_text: str) -> dict[str, str]:
    """Extract the LEGACY_KEY_TO_CANONICAL object literal from artifacts.jsx."""
    m = re.search(
        r"const\s+LEGACY_KEY_TO_CANONICAL\s*=\s*\{(.+?)\};",
        jsx_text, re.DOTALL,
    )
    assert m, "could not locate LEGACY_KEY_TO_CANONICAL in artifacts.jsx"
    body = m.group(1)
    out: dict[str, str] = {}
    for line in body.splitlines():
        line = line.split("//", 1)[0].strip()
        if not line:
            continue
        m2 = re.match(r"(\w+)\s*:\s*['\"]([^'\"]+)['\"],?", line)
        if m2:
            out[m2.group(1)] = m2.group(2)
    return out


def _parse_js_system_table(jsx_text: str) -> dict[int, str]:
    m = re.search(
        r"const\s+LEGACY_SYSTEM_BY_PHASE\s*=\s*\{(.+?)\};",
        jsx_text, re.DOTALL,
    )
    assert m, "could not locate LEGACY_SYSTEM_BY_PHASE in artifacts.jsx"
    body = m.group(1)
    out: dict[int, str] = {}
    for line in body.splitlines():
        line = line.split("//", 1)[0].strip()
        if not line:
            continue
        m2 = re.match(r"(\d+)\s*:\s*['\"]([^'\"]+)['\"],?", line)
        if m2:
            out[int(m2.group(1))] = m2.group(2)
    return out


def test_translation_table_matches_js_source(script_mod) -> None:
    """The Python translation table must mirror artifacts.jsx exactly."""
    jsx_text = ARTIFACTS_JSX_PATH.read_text(encoding="utf-8")
    js_table = _parse_js_translation_table(jsx_text)
    assert script_mod.LEGACY_KEY_TO_CANONICAL == js_table


def test_phase_aware_system_table_matches_js_source(script_mod) -> None:
    jsx_text = ARTIFACTS_JSX_PATH.read_text(encoding="utf-8")
    js_table = _parse_js_system_table(jsx_text)
    assert script_mod.LEGACY_SYSTEM_BY_PHASE == js_table


def test_legacy_keys_are_exactly_eight(script_mod) -> None:
    """The legacy bundle is 8 keys including the phase-aware `system`."""
    assert set(script_mod.LEGACY_KEY_TO_CANONICAL) == {
        "system", "brief", "d1", "d2", "plan", "hist", "draft", "histp",
    }


@pytest.mark.parametrize("legacy_key,canonical", [
    ("brief", "user_prompt.message"),
    ("d1", "phase1.claude"),
    ("d2", "phase1.openai"),
    ("plan", "phase2.agreement.plan"),
    ("hist", "prior_turns.phase2"),
    ("draft", "current_draft"),
    ("histp", "prior_turns.phase4"),
])
def test_canonicalise_single_legacy_key(script_mod, legacy_key, canonical) -> None:
    assert script_mod.canonicalise_legacy_key(legacy_key, phase_num=None) == canonical
    # Phase number is irrelevant for non-system keys.
    for phase_num in range(5):
        assert script_mod.canonicalise_legacy_key(legacy_key, phase_num=phase_num) == canonical


@pytest.mark.parametrize("phase_num,expected", [
    (0, "system.task.input"),
    (1, "system.task.research_plan"),
    (2, "system.task.plan_negotiation"),
    (3, "system.task.drafting"),
    (4, "system.task.review"),
])
def test_phase_aware_system_resolution(script_mod, phase_num, expected) -> None:
    assert script_mod.canonicalise_legacy_key("system", phase_num=phase_num) == expected


def test_system_without_phase_falls_back_to_default(script_mod) -> None:
    """If the event has no phase, the system key falls back to the
    Phase-0 sibling (matches the JS shim default behaviour)."""
    assert script_mod.canonicalise_legacy_key("system", phase_num=None) == "system.task.input"


def test_canonical_dotted_key_passes_through(script_mod) -> None:
    """Already-canonical IDs (dotted) must pass through unchanged."""
    assert script_mod.canonicalise_legacy_key("user_prompt.message", phase_num=2) == "user_prompt.message"
    assert script_mod.canonicalise_legacy_key("system.task.review", phase_num=4) == "system.task.review"
    assert script_mod.canonicalise_legacy_key("user_prompt.attachment.abc123", phase_num=None) == "user_prompt.attachment.abc123"


def test_unknown_key_passes_through(script_mod) -> None:
    """Unknown keys (not in the legacy map, not dotted) pass through unchanged."""
    assert script_mod.canonicalise_legacy_key("mystery", phase_num=None) == "mystery"


def test_translate_prompt_pieces_all_legacy(script_mod) -> None:
    """A legacy-only dict translates every key to its canonical sibling."""
    out = script_mod.translate_prompt_pieces({
        "system": 1000,
        "brief": 500,
        "d1": 200,
        "draft": 300,
    }, phase_num=2)
    assert out == {
        "system.task.plan_negotiation": 1000,
        "user_prompt.message": 500,
        "phase1.claude": 200,
        "current_draft": 300,
    }


def test_translate_prompt_pieces_all_canonical(script_mod) -> None:
    """An already-canonical dict round-trips unchanged."""
    src = {
        "system.task.review": 1100,
        "user_prompt.message": 500,
        "phase1.claude": 200,
        "current_draft": 300,
    }
    assert script_mod.translate_prompt_pieces(src, phase_num=4) == src


def test_translate_prompt_pieces_both_keys_prefer_canonical(script_mod) -> None:
    """Both legacy + canonical present: canonical wins, legacy silently dropped."""
    conflicts: list = []
    out = script_mod.translate_prompt_pieces(
        {"system": 1000, "system.task.preflight": 1100, "brief": 500},
        phase_num=0,
        conflicts=conflicts,
        run_id="r1", turn_key="phase0-r1-claude",
    )
    # Canonical wins for system; brief's canonical sibling is not present
    # so the legacy translates normally.
    # NOTE: 'system' translates to 'system.task.input' for phase 0; the
    # canonical-present check is against the dict's existing keys, not the
    # translated canonical-of-the-legacy. So 'system.task.preflight' (not a
    # sibling of any legacy key) survives untouched, and 'system' translates
    # to 'system.task.input' as if no conflict.
    assert out == {
        "system.task.preflight": 1100,
        "system.task.input": 1000,
        "user_prompt.message": 500,
    }


def test_translate_prompt_pieces_real_conflict_detected(script_mod) -> None:
    """When legacy `system` and canonical `system.task.<phase>` for the
    SAME phase are both present, the conflict is recorded and the
    canonical wins."""
    conflicts: list = []
    out = script_mod.translate_prompt_pieces(
        {"system": 1000, "system.task.plan_negotiation": 1100, "brief": 500},
        phase_num=2,
        conflicts=conflicts,
        run_id="r2", turn_key="phase2-r1-claude",
    )
    # Canonical wins for the conflicting pair.
    assert out == {
        "system.task.plan_negotiation": 1100,
        "user_prompt.message": 500,
    }
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c.run_id == "r2"
    assert c.turn_key == "phase2-r1-claude"
    assert c.legacy_key == "system"
    assert c.canonical_key == "system.task.plan_negotiation"
    assert c.legacy_tokens == 1000
    assert c.canonical_tokens == 1100


def test_translate_prompt_pieces_no_conflict_when_tokens_match(script_mod) -> None:
    """If legacy and canonical tokens agree, no conflict is recorded
    (the silent drop is benign)."""
    conflicts: list = []
    out = script_mod.translate_prompt_pieces(
        {"draft": 500, "current_draft": 500},
        phase_num=4,
        conflicts=conflicts,
        run_id="r3", turn_key="phase4-r1-claude",
    )
    assert out == {"current_draft": 500}
    assert conflicts == []


def test_translate_prompt_pieces_skips_invalid_token_values(script_mod) -> None:
    """Non-integer-coercible values are skipped (defensive)."""
    out = script_mod.translate_prompt_pieces(
        {"brief": 500, "draft": "not-a-number", "plan": None},
        phase_num=2,
    )
    assert out == {"user_prompt.message": 500}


def test_translate_prompt_pieces_attachment_id_preserved(script_mod) -> None:
    """Attachment-ID canonical artifact IDs pass through with the ID intact."""
    out = script_mod.translate_prompt_pieces(
        {"user_prompt.attachment.abc12345": 400},
        phase_num=0,
    )
    assert out == {"user_prompt.attachment.abc12345": 400}


@pytest.mark.parametrize("payload_phase,expected", [
    ("phase0", 0),
    ("phase4", 4),
    ("PHASE2", 2),
    ("phase1 ", 1),
    ("0", 0),
    ("4", 4),
])
def test_parse_phase_num_accepts_known_shapes(script_mod, payload_phase, expected) -> None:
    assert script_mod.parse_phase_num(payload_phase) == expected


@pytest.mark.parametrize("bad", ["", "final", "phase9", "phaseN", "garbage", "7", None, 4, []])
def test_parse_phase_num_rejects_bad_shapes(script_mod, bad) -> None:
    assert script_mod.parse_phase_num(bad) is None


# ── Pass 3: per-turn bundle translation (keys only, text values intact) ──


@pytest.mark.parametrize("name,expected", [
    ("phase0_claude.json", 0),
    ("phase2_round1_claude.json", 2),
    ("phase4_round12_gpt.json", 4),
    ("phase0_round3_gpt.json", 0),
])
def test_phase_num_from_filename_known_shapes(script_mod, name, expected) -> None:
    assert script_mod._phase_num_from_filename(name) == expected


@pytest.mark.parametrize("bad", ["input.json", "extra.json", "transcript.jsonl", ""])
def test_phase_num_from_filename_rejects_non_phase(script_mod, bad) -> None:
    assert script_mod._phase_num_from_filename(bad) is None


def test_translate_pieces_in_bundle_legacy_text(script_mod) -> None:
    """Per-turn bundle translation maps keys only; text values are
    preserved byte-identical."""
    out = script_mod._translate_pieces_in_bundle({
        "system": "TASK\n\nDo X.",
        "brief": "# Brief\n\nFull brief text here.",
        "d1": "Phase 1 claude draft body...",
        "draft": "Current Phase 4 draft body...",
    }, phase_num=4)
    assert out == {
        "system.task.review": "TASK\n\nDo X.",
        "user_prompt.message": "# Brief\n\nFull brief text here.",
        "phase1.claude": "Phase 1 claude draft body...",
        "current_draft": "Current Phase 4 draft body...",
    }


def test_translate_pieces_in_bundle_canonical_passthrough(script_mod) -> None:
    """An already-canonical bundle round-trips byte-identical."""
    src = {
        "system.task.plan_negotiation": "...",
        "user_prompt.message": "...",
        "phase1.claude": "...",
    }
    assert script_mod._translate_pieces_in_bundle(src, phase_num=2) == src


def test_translate_pieces_in_bundle_prefer_canonical(script_mod) -> None:
    """If a legacy key and its canonical sibling both appear, canonical
    wins and the legacy is silently dropped."""
    out = script_mod._translate_pieces_in_bundle({
        "system": "OLD",
        "system.task.review": "NEW",
        "brief": "B",
    }, phase_num=4)
    assert out == {
        "system.task.review": "NEW",
        "user_prompt.message": "B",
    }


def test_plan_pass3_identifies_legacy_files(script_mod, tmp_path) -> None:
    """plan_pass3 walks runs/*/inputs/ and flags legacy-keyed files."""
    run = tmp_path / "20260518-000000-historical-run"
    inputs = run / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "input.json").write_text(json.dumps({"pieces": {"user_prompt.message": "x"}}))
    (inputs / "phase2_round1_claude.json").write_text(json.dumps({
        "pieces": {"brief": "B", "d1": "D1", "draft": "DRAFT"}
    }))
    (inputs / "phase4_round3_gpt.json").write_text(json.dumps({
        "pieces": {"system": "S", "draft": "D"}
    }))
    counts, candidates = script_mod.plan_pass3(tmp_path)
    assert counts.total_per_turn_files == 2
    assert counts.legacy_files_to_translate == 2
    assert counts.files_with_mixed_keys == 0
    assert candidates == [run]


def test_plan_pass3_skips_canonical_files(script_mod, tmp_path) -> None:
    """plan_pass3 leaves already-canonical files alone."""
    run = tmp_path / "20260521-010637-anchor"
    inputs = run / "inputs"
    inputs.mkdir(parents=True)
    (inputs / "phase2_round1_claude.json").write_text(json.dumps({
        "pieces": {
            "system.task.plan_negotiation": "S",
            "user_prompt.message": "B",
            "phase1.claude": "D",
        }
    }))
    counts, candidates = script_mod.plan_pass3(tmp_path)
    assert counts.total_per_turn_files == 1
    assert counts.legacy_files_to_translate == 0
    assert candidates == []


def test_execute_pass3_no_push_translates_in_place(script_mod, tmp_path) -> None:
    """execute_pass3 with push=False writes back translated files only."""
    import json as _json

    run = tmp_path / "20260518-000000-historical-run"
    inputs = run / "inputs"
    inputs.mkdir(parents=True)
    f = inputs / "phase2_round1_claude.json"
    f.write_text(_json.dumps({
        "pieces": {"brief": "B", "d1": "D1", "draft": "DRAFT"}
    }, indent=2))
    _, candidates = script_mod.plan_pass3(tmp_path)
    assert candidates == [run]

    dirs_t, files_t, pushed = script_mod.execute_pass3(candidates, push=False)
    assert dirs_t == 1
    assert files_t == 1
    assert pushed == 0

    data = _json.loads(f.read_text(encoding="utf-8"))
    assert data["pieces"] == {
        "user_prompt.message": "B",
        "phase1.claude": "D1",
        "current_draft": "DRAFT",
    }

    # Idempotent: re-running translates nothing.
    _, candidates2 = script_mod.plan_pass3(tmp_path)
    assert candidates2 == []

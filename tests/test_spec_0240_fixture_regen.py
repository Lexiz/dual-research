"""Spec 0240 — fixture regeneration machinery unit tests.

Layer 1: regenerate_transcript produces the expected post-fix
item_raised counts on the two captured failing fixtures (142625 +
054652).

Layer 2: regen is idempotent — calling regenerate_baseline on the
three clean fixtures does NOT change their expected.json; calling
regenerate_transcript + regenerate_baseline twice in succession on a
tmp_path copy of either failing fixture produces byte-identical output
across the two passes.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tests._fixture_regen import regenerate_baseline, regenerate_transcript


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "anchor-runs"


def _item_raised_ids_for_turn(
    transcript_path: Path, *, phase: int, round_no: int, raiser: str
) -> set[str]:
    ids: set[str] = set()
    for line in transcript_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev.get("event") != "item_raised":
            continue
        if ev.get("phase") != phase or ev.get("round") != round_no:
            continue
        if ev.get("raiser") != raiser:
            continue
        ids.add(ev.get("id"))
    return ids


def _copy_fixture(src: Path, dst: Path) -> Path:
    shutil.copytree(src, dst)
    return dst


# ─── Layer 1 — regen produces expected post-fix counts ─────────────────


def test_fixture_regen_142625_yields_5_raised_events(tmp_path):
    """20260527-142625 phase-2 r1 claude: 5 RAISE blocks (the
    previously-dropped IDs declared in the turn's RAISED_THIS_TURN line
    as D-go-vs-csharp-21, D-java-rank, D-kotlin-mcp,
    Q-csharp-implicit-penalty, Q-rust-azure-sdk-ga).

    apply_turn assigns canonical IDs via format_id rather than echoing
    the agent's slug shapes (out of scope per spec 0240 §5 — no shape
    changes to apply_turn). The contract this test guards is the COUNT
    of registered item_raised events plus the turn coordinates; ID
    shape is verified to be canonical (3 disagreements + 2 questions
    matches the kind breakdown of the agent's declaration)."""
    rd = _copy_fixture(
        FIXTURES / "20260527-142625-backend-language-choice",
        tmp_path / "142625",
    )
    regenerate_transcript(rd)
    ids = _item_raised_ids_for_turn(
        rd / "transcript.jsonl", phase=2, round_no=1, raiser="claude"
    )
    assert len(ids) == 5, f"expected 5 raised ids, got {len(ids)}: {ids!r}"
    d_ids = {i for i in ids if i.startswith("D-plan-c-")}
    q_ids = {i for i in ids if i.startswith("Q-plan-c-")}
    assert len(d_ids) == 3, f"expected 3 D-plan-c-* ids, got {d_ids!r}"
    assert len(q_ids) == 2, f"expected 2 Q-plan-c-* ids, got {q_ids!r}"


def test_fixture_regen_054652_yields_6_raised_events(tmp_path):
    """20260527-054652 phase-2 r1 claude: 6 RAISE blocks. Mirrors the
    142625 contract (canonical apply_turn IDs); the agent declared 6 in
    RAISED_THIS_TURN."""
    rd = _copy_fixture(
        FIXTURES / "20260527-054652-backend-language-choice",
        tmp_path / "054652",
    )
    regenerate_transcript(rd)
    ids = _item_raised_ids_for_turn(
        rd / "transcript.jsonl", phase=2, round_no=1, raiser="claude"
    )
    assert len(ids) == 6, f"expected 6 raised ids, got {len(ids)}: {ids!r}"


# ─── Layer 2 — regen idempotency ───────────────────────────────────────


@pytest.mark.parametrize("fixture", [
    "20260521-010637-dvs-backend-language-choice",
    "20260525-135006-backend-language-choice",
    "20260526-102321-backend-language-choice",
])
def test_fixture_regen_idempotent_on_clean_fixtures(tmp_path, fixture):
    """regenerate_baseline on a clean fixture must NOT change
    expected.json — the verifier's view of the fixture is stable. Catches
    silent verifier drift before it bleeds into the corpus."""
    rd = _copy_fixture(FIXTURES / fixture, tmp_path / fixture)
    expected_pre = (rd / "expected.json").read_bytes()
    transcript_pre = (rd / "transcript.jsonl").read_bytes()

    regenerate_baseline(rd)

    expected_post = (rd / "expected.json").read_bytes()
    transcript_post = (rd / "transcript.jsonl").read_bytes()

    assert expected_pre == expected_post, (
        f"{fixture}: regenerate_baseline mutated expected.json"
    )
    assert transcript_pre == transcript_post, (
        f"{fixture}: regenerate_baseline mutated transcript.jsonl"
    )


@pytest.mark.parametrize("fixture", [
    "20260527-142625-backend-language-choice",
    "20260527-054652-backend-language-choice",
])
def test_fixture_regen_idempotent_on_regenerated_fixtures(tmp_path, fixture):
    """Two consecutive regen passes on the same captured fixture must
    produce byte-identical transcript.jsonl AND expected.json. Locks the
    gating-promotion precondition against silent non-determinism in
    parse_turn_v2 or apply_turn going forward."""
    rd = _copy_fixture(FIXTURES / fixture, tmp_path / fixture)

    regenerate_transcript(rd)
    regenerate_baseline(rd)
    transcript_first = (rd / "transcript.jsonl").read_bytes()
    expected_first = (rd / "expected.json").read_bytes()

    regenerate_transcript(rd)
    regenerate_baseline(rd)
    transcript_second = (rd / "transcript.jsonl").read_bytes()
    expected_second = (rd / "expected.json").read_bytes()

    assert transcript_first == transcript_second, (
        f"{fixture}: regenerate_transcript non-deterministic across passes"
    )
    assert expected_first == expected_second, (
        f"{fixture}: regenerate_baseline non-deterministic across passes"
    )

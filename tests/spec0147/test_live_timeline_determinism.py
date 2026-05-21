"""Spec 0147 §7 — buildLiveTimeline rendering contract (B04).

Two layers of guard:

1. **Structural** — `_roundHasInFlight` helper exists in `live-data.jsx`
   and each of the three multi-round live branches (Phase 0, Phase 2,
   Phase 4) consumes a `pXRunningFloor` value rather than the bare
   `Math.max(0, cur - 1)` floor. Catches an accidental revert of the
   spec's predicate swap.

2. **Behavioural** — a Python port of the `_roundHasInFlight` +
   `pXRunningFloor` math, exercised over a fixture array of three
   consecutive `run` snapshots (poll-frame-1 → poll-frame-2 →
   poll-frame-3). Asserts the rendered (round, agent) attribution is
   monotonic — every (round, agent) pair present in frame K shows up
   in frame K+1 with the same kind ("turn") or transitions one-way
   from "turn-live" → "turn".

The behavioural test is the heart of the determinism contract; the
structural test makes sure the JS-side stays in lockstep.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

LIVE_DATA = (
    Path(__file__).parent.parent.parent
    / "src"
    / "dual_research"
    / "ui"
    / "static"
    / "live-data.jsx"
)


# ───────────────────────────────────────────────────────────
# Structural guards over live-data.jsx
# ───────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def js() -> str:
    return LIVE_DATA.read_text()


def test_round_has_in_flight_helper_exists(js: str) -> None:
    """The shared predicate must live as a module-level function so
    each of the three phase branches references the same logic.
    """
    assert (
        re.search(r"function\s+_roundHasInFlight\s*\(slots,\s*round\)", js)
        is not None
    ), "spec 0147 _roundHasInFlight helper missing from live-data.jsx"


@pytest.mark.parametrize("phase_key", ["phase0", "phase2", "phase4"])
def test_phase_running_floor_uses_phasestats_predicate(
    js: str, phase_key: str
) -> None:
    """Each of the three multi-round live branches must compute its
    `pXRunningFloor` via `_roundHasInFlight(<phaseStats>, cur)`, not
    via the pre-spec `Math.max(0, cur - 1)` bare floor.
    """
    suffix = phase_key[-1]
    # Phase 0 uses `p0StatsRoundCount` for legacy reasons; Phase 2 / 4
    # use `pXStatsCount`. Match either form.
    pattern = re.compile(
        rf"p{suffix}RunningFloor\s*=\s*Math\.max\s*\(\s*0,\s*"
        rf"cur\s*-\s*1,\s*p{suffix}Stats(?:Round)?Count\s*-\s*"
        rf"\(\s*_roundHasInFlight\(\s*\w+,\s*cur\s*\)",
        re.DOTALL,
    )
    assert pattern.search(js) is not None, (
        f"Phase {suffix} live branch does not derive p{suffix}RunningFloor "
        f"from the phaseStats-based _roundHasInFlight predicate"
    )


def test_no_unconditional_live_card_in_phase_branches(js: str) -> None:
    """Pre-spec, each phase branch unconditionally emitted both
    `pX-rR-AGENT-live` cards when `cur > 0 && st === 'running'`,
    causing a flicker on the phase-completion poll. Post-spec, the
    live cards are gated on `cur > completedThrough && st === 'running'`
    and the per-agent presence in `phaseStats[phaseX][cur]`.
    """
    pre_spec_pattern = re.compile(
        r"if\s*\(\s*cur\s*>\s*0\s*&&\s*st\s*===\s*'running'\s*\)\s*\{"
        r"\s*items\.push\(\s*\{\s*id:\s*`p[024]-r\$\{cur\}-[a-z]+-live`"
    )
    assert pre_spec_pattern.search(js) is None, (
        "found pre-spec unconditional live-card emit; the per-agent gating "
        "in spec 0147 §5.2 has been reverted"
    )


def test_rendering_contract_comment_present(js: str) -> None:
    """The single documented rendering contract is the spec 0147
    contract block at the top of the live timeline builder. Catches
    an accidental delete.
    """
    assert "RENDERING CONTRACT (spec 0147)" in js, (
        "spec 0147 rendering contract comment block missing"
    )


# ───────────────────────────────────────────────────────────
# Behavioural — Python port of the JS predicate
# ───────────────────────────────────────────────────────────


def _round_has_in_flight(slots: dict, round_: int) -> bool:
    """Mirror of the JS `_roundHasInFlight` helper. A round is
    in-flight iff its slot exists AND at least one of {claude, gpt}
    is absent.
    """
    if round_ is None or round_ <= 0:
        return False
    slot = slots.get(round_)
    if slot is None:
        return False
    return slot.get("claude") is None or slot.get("gpt") is None


def _phase_running_floor(slots: dict, cur: int) -> int:
    """Mirror of the JS `pXRunningFloor` expression."""
    stats_count = len(slots)
    return max(
        0,
        cur - 1,
        stats_count - (1 if _round_has_in_flight(slots, cur) else 0),
    )


def _emit_phase2(run: dict) -> list[dict]:
    """Minimal port of the spec-0147 Phase 2 emit logic. Returns the
    ordered list of (id, kind, round, agent) entries this snapshot
    would render in the timeline.
    """
    items: list[dict] = []
    ph = run["phase"]
    st = run["status"]
    cur = run.get("round", {}).get("current") or 0
    if ph < 2:
        return items
    slots = run.get("phaseStats", {}).get("phase2", {})
    stats_count = len(slots)
    if ph == 2 and st in ("running", "deadlocked", "errored"):
        completed_through = (
            _phase_running_floor(slots, cur)
            if st == "running"
            else max(cur, stats_count)
        )
        for r in range(1, completed_through + 1):
            items.append({"id": f"p2-r{r}-claude", "kind": "turn",
                          "round": r, "agent": "claude"})
            items.append({"id": f"p2-r{r}-gpt", "kind": "turn",
                          "round": r, "agent": "gpt"})
        if cur > completed_through and st == "running":
            cur_slot = slots.get(cur, {})
            for agent in ("claude", "gpt"):
                if cur_slot.get(agent) is not None:
                    items.append({"id": f"p2-r{cur}-{agent}",
                                  "kind": "turn",
                                  "round": cur, "agent": agent})
                else:
                    items.append({"id": f"p2-r{cur}-{agent}-live",
                                  "kind": "turn-live",
                                  "round": cur, "agent": agent})
    elif ph >= 3 or st == "completed" or st == "deadlocked":
        for r in range(1, stats_count + 1):
            items.append({"id": f"p2-r{r}-claude", "kind": "turn",
                          "round": r, "agent": "claude"})
            items.append({"id": f"p2-r{r}-gpt", "kind": "turn",
                          "round": r, "agent": "gpt"})
    return items


def _stats(*rounds_completions: tuple[int, str]) -> dict:
    """Helper: build a phaseStats.phase2 dict from a list of
    (round, "both" | "claude" | "gpt" | "none") completions.
    """
    out: dict = {}
    for r, who in rounds_completions:
        if who == "both":
            out[r] = {"claude": {"status": "AGREED"},
                      "gpt": {"status": "AGREED"}}
        elif who == "claude":
            out[r] = {"claude": {"status": "NEGOTIATING"}}
        elif who == "gpt":
            out[r] = {"gpt": {"status": "NEGOTIATING"}}
    return out


def test_no_flicker_at_phase_completion_poll() -> None:
    """The dispositive case from the spec: phase-2-r2 card must
    not disappear when `run.phase` advances to 3.
    """
    # Frame K: P2 r2 complete, cur=2 (about to advance).
    frame_k = {
        "phase": 2,
        "status": "running",
        "round": {"current": 2},
        "phaseStats": {"phase2": _stats((1, "both"), (2, "both"))},
    }
    # Frame K+1: orchestrator advanced — ph=3, cur reset to 1 of P3.
    frame_kp1 = {
        "phase": 3,
        "status": "running",
        "round": {"current": 1},
        "phaseStats": {"phase2": _stats((1, "both"), (2, "both"))},
    }
    items_k = _emit_phase2(frame_k)
    items_kp1 = _emit_phase2(frame_kp1)

    # Both rounds must appear in both frames with the same id and kind.
    ids_k = {(it["id"], it["kind"]) for it in items_k}
    ids_kp1 = {(it["id"], it["kind"]) for it in items_kp1}
    expected = {
        ("p2-r1-claude", "turn"), ("p2-r1-gpt", "turn"),
        ("p2-r2-claude", "turn"), ("p2-r2-gpt", "turn"),
    }
    assert expected <= ids_k, (
        f"frame K missing expected cards. Got: {ids_k}"
    )
    assert expected <= ids_kp1, (
        f"frame K+1 missing expected cards. Got: {ids_kp1}"
    )


def test_three_frame_monotonic_replay() -> None:
    """Three consecutive poll snapshots:
    - frame 1: P2 r1 in flight (claude in, gpt pending)
    - frame 2: P2 r1 complete, r2 in flight
    - frame 3: P2 r2 complete, P3 just started.
    Every (round, agent) pair present in frame K must persist in
    frame K+1 (one-way: turn-live → turn allowed, turn → turn-live
    disallowed, turn → gone disallowed).
    """
    frames = [
        {
            "phase": 2, "status": "running", "round": {"current": 1},
            "phaseStats": {"phase2": _stats((1, "claude"))},
        },
        {
            "phase": 2, "status": "running", "round": {"current": 2},
            "phaseStats": {"phase2": _stats((1, "both"), (2, "claude"))},
        },
        {
            "phase": 3, "status": "running", "round": {"current": 1},
            "phaseStats": {"phase2": _stats((1, "both"), (2, "both"))},
        },
    ]
    rendered = [_emit_phase2(f) for f in frames]

    def by_pair(items):
        return {(it["round"], it["agent"]): it["kind"] for it in items}

    f1, f2, f3 = (by_pair(r) for r in rendered)

    # All (round, agent) pairs in frame 1 must persist into frame 2.
    for pair, kind in f1.items():
        assert pair in f2, (
            f"frame 1 pair {pair} disappeared in frame 2; got {f2}"
        )
        # turn-live may become turn; turn must stay turn.
        if kind == "turn":
            assert f2[pair] == "turn", (
                f"frame 1 turn {pair} regressed to {f2[pair]} in frame 2"
            )

    # All pairs in frame 2 must persist into frame 3.
    for pair, kind in f2.items():
        assert pair in f3, (
            f"frame 2 pair {pair} disappeared in frame 3; got {f3}"
        )
        if kind == "turn":
            assert f3[pair] == "turn", (
                f"frame 2 turn {pair} regressed to {f3[pair]} in frame 3"
            )

    # Specifically: r2 surfaces by frame 2 (claude-completed +
    # gpt-live) and locks in by frame 3.
    assert (2, "claude") in f2 and f2[(2, "claude")] == "turn", (
        f"r2 claude completed card missing/non-turn in frame 2: {f2}"
    )
    assert (2, "gpt") in f2 and f2[(2, "gpt")] == "turn-live", (
        f"r2 gpt should be live in frame 2: {f2}"
    )
    assert (2, "claude") in f3 and f3[(2, "claude")] == "turn", (
        f"r2 claude regressed in frame 3: {f3}"
    )
    assert (2, "gpt") in f3 and f3[(2, "gpt")] == "turn", (
        f"r2 gpt completion missing in frame 3: {f3}"
    )


def test_same_input_determinism() -> None:
    """Building the timeline twice from the same snapshot must yield
    byte-identical item arrays (sanity check on the predicate purity).
    """
    snap = {
        "phase": 2, "status": "running", "round": {"current": 3},
        "phaseStats": {
            "phase2": _stats((1, "both"), (2, "both"), (3, "claude")),
        },
    }
    a = _emit_phase2(snap)
    b = _emit_phase2(snap)
    assert a == b


def test_skipped_frame_safe() -> None:
    """If a poll frame is skipped (the spec-0140 / 0144 fly mid-deploy
    pattern), the timeline still surfaces every materialised round on
    the next successful poll without inventing rounds.
    """
    # Frame 1: in P2 r1, only claude done. Skip frame 2. Frame 3 lands
    # mid-P2-r3 with all three rounds in phaseStats (r1+r2 complete,
    # r3 partial).
    frame_1 = {
        "phase": 2, "status": "running", "round": {"current": 1},
        "phaseStats": {"phase2": _stats((1, "claude"))},
    }
    frame_3 = {
        "phase": 2, "status": "running", "round": {"current": 3},
        "phaseStats": {
            "phase2": _stats((1, "both"), (2, "both"), (3, "gpt")),
        },
    }
    items_1 = _emit_phase2(frame_1)
    items_3 = _emit_phase2(frame_3)
    pairs_3 = {(it["round"], it["agent"]) for it in items_3}
    # r1 claude survives (it was in frame 1; should still be present in
    # frame 3, now as completed).
    assert (1, "claude") in pairs_3
    # r2 and r3 surface despite never having been seen.
    assert (2, "claude") in pairs_3 and (2, "gpt") in pairs_3
    assert (3, "claude") in pairs_3 and (3, "gpt") in pairs_3
    # r3 gpt is completed (in phaseStats), claude is live.
    kinds = {(it["round"], it["agent"]): it["kind"] for it in items_3}
    assert kinds[(3, "gpt")] == "turn"
    assert kinds[(3, "claude")] == "turn-live"
    # No invented r4.
    assert all(r <= 3 for r, _ in pairs_3)
    # Frame 1 emitted claude-live for round 1; frame 3 must promote
    # it (no remount-to-live regression).
    kinds_1 = {(it["round"], it["agent"]): it["kind"] for it in items_1}
    assert kinds_1[(1, "claude")] == "turn"  # frame 1: claude completed
    assert kinds_1[(1, "gpt")] == "turn-live"  # frame 1: gpt live
    assert kinds[(1, "claude")] == "turn"
    assert kinds[(1, "gpt")] == "turn"

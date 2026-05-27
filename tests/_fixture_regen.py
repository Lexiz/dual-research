"""Spec 0240 — fixture regeneration machinery.

Two callables: ``regenerate_transcript`` replays the on-disk turn files
through the current ``parse_turn_v2`` + ``DeepResearchPhase.apply_turn``
and rewrites the fixture's ``transcript.jsonl`` so the parser-derived
event stream reflects post-fix semantics. ``regenerate_baseline`` then
recomputes ``expected.json`` via the live verifier.

The original ``transcript.jsonl`` is snapshotted to
``transcript.captured.jsonl`` before any overwrite (idempotent — never
overwrites an existing snapshot). Subsequent regen passes read from the
captured snapshot so multiple regens against the same fixture produce
byte-identical output.

Regenerated parser events carry no ``ts`` field — replay has no real
runtime timestamp and synthesising one would either drift across passes
(non-deterministic) or fabricate a time bracket. The verifier tolerates
missing ``ts`` on non-terminal events (I5.3 skips ``ts is None``).
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from dual_research.contract.caps import caps_for
from dual_research.contract.verifier import verify_run
from dual_research.orchestrator.deep_research import DeepResearchPhase
from dual_research.protocol.parse import parse_turn_v2


_ROUND_FILE_RE = re.compile(r"^round-(\d+)-(claude|openai)\.md$")
_RAISABLE_PHASES = (0, 2, 4)
_PARSER_EVENTS = frozenset({
    "item_raised",
    "item_transitioned",
    "closeout_urged",
    "closeout_violation",
    "protocol_violation",
    "empty_turn_detected",
})
_LABEL_ROUND_RE = re.compile(r"-r(\d+)-")


def _discover_rounds(phase_dir: Path) -> list[int]:
    if not phase_dir.is_dir():
        return []
    seen: set[int] = set()
    for entry in phase_dir.iterdir():
        if not entry.is_file() or not entry.name.endswith(".md"):
            continue
        if ".malformed" in entry.name:
            continue
        m = _ROUND_FILE_RE.match(entry.name)
        if m:
            seen.add(int(m.group(1)))
    return sorted(seen)


def _to_transcript_dict(event: Any) -> dict:
    """Mirror ``_install_transcript_bridge``'s serialization: pop ``kind``,
    set ``event``, omit ``ts`` (regen has no real runtime timestamp)."""
    payload = event.to_dict()
    name = payload.pop("kind", None)
    if not name:
        raise ValueError(f"event missing 'kind': {event!r}")
    return {"event": name, **payload}


def _drive_round(
    phase: DeepResearchPhase,
    phase_dir: Path,
    round_no: int,
    is_closeout_round: bool,
) -> tuple[list[dict], Any, bool]:
    parsed_claude = None
    parsed_openai = None
    raised_all: list = []
    transitions_all: list = []
    violations_all: list = []
    empty_turns_all: list = []

    for agent in ("claude", "openai"):
        path = phase_dir / f"round-{round_no:02d}-{agent}.md"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        parsed = parse_turn_v2(text)
        if agent == "claude":
            parsed_claude = parsed
        else:
            parsed_openai = parsed
        r, t, v, e = phase.apply_turn(
            text=text,
            parsed=parsed,
            agent=agent,
            round=round_no,
            is_closeout_round=is_closeout_round,
        )
        raised_all.extend(r)
        transitions_all.extend(t)
        violations_all.extend(v)
        empty_turns_all.extend(e)

    if parsed_claude is None and parsed_openai is None:
        return [], None, False

    rr = phase.process_round_end(
        parsed_claude=parsed_claude,
        parsed_openai=parsed_openai,
        round=round_no,
        is_closeout_round=is_closeout_round,
        raised_events=raised_all,
        transition_events=transitions_all,
        violation_events=violations_all,
        empty_turn_events=empty_turns_all,
    )

    # Mirror _publish_round_events ordering:
    # raised → transitions → violations → closeout_event → empty_turns.
    events: list[dict] = []
    events.extend(_to_transcript_dict(ev) for ev in raised_all)
    events.extend(_to_transcript_dict(ev) for ev in transitions_all)
    events.extend(_to_transcript_dict(ev) for ev in violations_all)
    if rr.closeout_event is not None:
        events.append(_to_transcript_dict(rr.closeout_event))
    events.extend(_to_transcript_dict(ev) for ev in empty_turns_all)

    return events, rr.closeout_event, rr.converged


def _regen_phase_events_by_round(run_dir: Path, *, phase: int) -> dict[int, list[dict]]:
    phase_dir = run_dir / f"phase{phase}"
    rounds = _discover_rounds(phase_dir)
    if not rounds:
        return {}

    from dual_research.orchestrator.dr_run import _evidence_validator_for_run
    dr_phase = DeepResearchPhase(
        phase=phase,
        agent_turn=lambda req: "",
        evidence_validator=_evidence_validator_for_run,
    )
    caps = caps_for(phase)

    out: dict[int, list[dict]] = {}
    is_closeout_round = False
    converged = False

    for round_no in rounds:
        if converged:
            break
        round_events, closeout_event, conv = _drive_round(
            dr_phase, phase_dir, round_no, is_closeout_round
        )
        out[round_no] = round_events
        if conv:
            converged = True
            continue
        if closeout_event is not None:
            if is_closeout_round and dr_phase.spend_failed_closeout_budget():
                out[round_no].extend(
                    _to_transcript_dict(ev)
                    for ev in dr_phase.ghost_cap_remaining_items(round=round_no)
                )
                converged = True
                continue
            is_closeout_round = True
        else:
            is_closeout_round = False

    if not converged and rounds and rounds[-1] >= caps.hard:
        last = rounds[-1]
        out.setdefault(last, []).extend(
            _to_transcript_dict(ev)
            for ev in dr_phase.hard_cap_remaining_items(round=last)
        )

    return out


def _phase_round_from_envelope(ev: dict) -> tuple[int | None, int | None]:
    phase_label = ev.get("phase", "")
    ph: int | None = None
    if isinstance(phase_label, str) and phase_label.startswith("phase"):
        try:
            ph = int(phase_label[5:])
        except ValueError:
            ph = None
    elif isinstance(phase_label, int):
        ph = phase_label
    label = ev.get("label", "")
    m = _LABEL_ROUND_RE.search(label) if isinstance(label, str) else None
    rnd = int(m.group(1)) if m else None
    return ph, rnd


def regenerate_transcript(run_dir: Path) -> None:
    """Replay turn files through the current parser; rewrite transcript.jsonl.

    Idempotent — snapshots the original to ``transcript.captured.jsonl``
    on first call and reads from the snapshot on subsequent calls.
    """
    transcript_path = run_dir / "transcript.jsonl"
    captured_path = run_dir / "transcript.captured.jsonl"

    if not captured_path.is_file():
        shutil.copy2(transcript_path, captured_path)

    source_text = captured_path.read_text(encoding="utf-8")

    envelope: list[dict] = []
    for line in source_text.splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        if ev.get("event") in _PARSER_EVENTS:
            continue
        envelope.append(ev)

    by_round: dict[tuple[int, int], list[dict]] = {}
    for ph in _RAISABLE_PHASES:
        for round_no, evs in _regen_phase_events_by_round(run_dir, phase=ph).items():
            by_round[(ph, round_no)] = evs

    last_turn_ended_idx: dict[tuple[int, int], int] = {}
    for idx, ev in enumerate(envelope):
        if ev.get("event") != "turn_ended":
            continue
        ph, rnd = _phase_round_from_envelope(ev)
        if ph is None or rnd is None:
            continue
        last_turn_ended_idx[(ph, rnd)] = idx

    splice_after: dict[int, list[dict]] = {}
    for key, idx in last_turn_ended_idx.items():
        events = by_round.get(key)
        if not events:
            continue
        splice_after.setdefault(idx, []).extend(events)

    out_events: list[dict] = []
    for idx, ev in enumerate(envelope):
        out_events.append(ev)
        if idx in splice_after:
            out_events.extend(splice_after[idx])

    lines = [json.dumps(ev, ensure_ascii=False) for ev in out_events]
    transcript_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def regenerate_baseline(run_dir: Path) -> None:
    """Recompute ``expected.json`` from the live verifier output."""
    report = verify_run(run_dir)
    payload = {
        "spec": "0225",
        "note": "Frozen LKG baseline of the lifecycle-trace verifier. Regenerate via "
                "tests.test_verifier.regenerate_baseline() when a verdict legitimately changes.",
        "results": [
            {"id": r.id, "severity": r.severity, "verdict": r.verdict}
            for r in report.results
        ],
    }
    (run_dir / "expected.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )

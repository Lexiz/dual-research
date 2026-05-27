"""Spec 0225 — lifecycle-trace verifier.

The contract from spec 0114 (plus synthesis §3 invariants from
``../cowork/briefs/2026-05-26-logic-cutoff-synthesis.md``) in runnable form.
Reads a finished run directory (transcript + state + metrics + turn files)
and emits a structured :class:`VerifierReport` of per-invariant verdicts.

22 invariants across 5 areas. Each has an ID, a severity
(``gating`` / ``reporting``), and a verdict (``pass`` / ``fail`` /
``not_applicable``). Failures carry :class:`Evidence` records (file +
line citation + human-readable detail).

The module imports the live contract definitions (``ID_PATTERN``,
``RAISABLE_IN``, ``PHASE_TOKEN``, op-block regexes) — the verifier asserts
runs against the **observed code's** contract, never a re-spelled copy.

I4.7 (capped-is-orchestrator-only) uses ``event.via in {"hard_cap",
"ghost_cap"}`` as its primary predicate, falling back to ``event.actor ==
"orchestrator"`` if the ``via`` field is missing at build time. The choice
is recorded in :data:`I47_PREDICATE_NAME`.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Iterable

from dual_research.contract.categories import (
    PHASE_TOKEN,
    RAISABLE_IN,
    TOKEN_TO_CATEGORY,
    Category,
)
from dual_research.contract.ids import ID_PATTERN
from dual_research.contract.markers import (
    OP_ACKNOWLEDGE_RE,
    OP_ADDRESS_RE,
    OP_RAISE_RE,
    OP_RESOLVE_RE,
    OP_WITHDRAW_RE,
    OPEN_COMMENTS_RE,
    OPEN_DISAGREEMENTS_RE,
    OPEN_ISSUES_RE,
    OPEN_QUESTIONS_RE,
    STATUS_RE,
)
from dual_research.events.types import ItemTransitioned

TERMINAL_STATES: frozenset[str] = frozenset(
    {"resolved", "acknowledged", "withdrawn", "capped"}
)

# Permitted edges per §2.2 I4.1. The destination-only set covers
# ``* → withdrawn`` / ``* → acknowledged`` / ``* → capped`` (any source).
_EDGE_ALLOWLIST: frozenset[tuple[str, str]] = frozenset(
    {("open", "addressed"), ("addressed", "resolved"), ("addressed", "open")}
)
_TERMINAL_DESTINATIONS_ANY_SOURCE: frozenset[str] = frozenset(
    {"withdrawn", "acknowledged", "capped"}
)

_TERMINAL_RUN_EVENTS: frozenset[str] = frozenset(
    {"run_completed", "run_failed", "run_aborted"}
)

_PHASE_STR_RE = re.compile(r"^phase(\d+)$")
_TURN_FILE_RE = re.compile(r"^round-(\d{2})-(claude|openai)\.md$")


# I4.7 — pick the predicate at module load and document the choice.
def _i47_via_predicate(event: dict) -> bool:
    return event.get("via") in {"hard_cap", "ghost_cap"}


def _i47_actor_predicate(event: dict) -> bool:
    return event.get("actor") == "orchestrator"


_HAS_VIA_FIELD = any(f.name == "via" for f in fields(ItemTransitioned))
I47_PREDICATE = _i47_via_predicate if _HAS_VIA_FIELD else _i47_actor_predicate
I47_PREDICATE_NAME = (
    "via_in_hard_or_ghost_cap" if _HAS_VIA_FIELD else "actor_equals_orchestrator"
)


@dataclass(frozen=True)
class Evidence:
    location: str
    detail: str


@dataclass(frozen=True)
class InvariantResult:
    id: str
    severity: str
    verdict: str
    evidence: tuple[Evidence, ...] = ()


@dataclass(frozen=True)
class VerifierReport:
    run_dir: str
    results: tuple[InvariantResult, ...]

    @property
    def has_gating_failure(self) -> bool:
        return any(
            r.severity == "gating" and r.verdict == "fail" for r in self.results
        )

    def to_dict(self) -> dict:
        return {
            "run_dir": self.run_dir,
            "i47_predicate": I47_PREDICATE_NAME,
            "results": [
                {
                    "id": r.id,
                    "severity": r.severity,
                    "verdict": r.verdict,
                    "evidence": [
                        {"location": e.location, "detail": e.detail}
                        for e in r.evidence
                    ],
                }
                for r in self.results
            ],
        }


@dataclass(frozen=True)
class _TurnOp:
    op: str
    item_id: str | None
    line: int


@dataclass(frozen=True)
class _TurnFile:
    path: Path
    phase: int
    round: int
    agent: str
    ops: tuple[_TurnOp, ...]
    counters: dict[str, int]
    status: str | None
    rel_path: str


def _phase_to_int(phase: object) -> int | None:
    if isinstance(phase, int):
        return phase
    if isinstance(phase, str):
        m = _PHASE_STR_RE.match(phase)
        if m:
            return int(m.group(1))
        if phase.isdigit():
            return int(phase)
    return None


def _read_events(run_dir: Path) -> list[dict]:
    transcript = run_dir / "transcript.jsonl"
    if not transcript.exists():
        return []
    out: list[dict] = []
    for line in transcript.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _read_metrics(run_dir: Path) -> dict | None:
    p = run_dir / "metrics.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _parse_turn_file(path: Path, phase: int, run_dir: Path) -> _TurnFile | None:
    m = _TURN_FILE_RE.match(path.name)
    if not m:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    rel = path.relative_to(run_dir).as_posix()
    ops: list[_TurnOp] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.startswith("### "):
            continue
        for op_name, op_re in (
            ("RAISE", OP_RAISE_RE),
            ("ADDRESS", OP_ADDRESS_RE),
            ("RESOLVE", OP_RESOLVE_RE),
            ("WITHDRAW", OP_WITHDRAW_RE),
            ("ACKNOWLEDGE", OP_ACKNOWLEDGE_RE),
        ):
            m2 = op_re.match(line)
            if not m2:
                continue
            item_id = None
            try:
                item_id = m2.group("id")
            except IndexError:
                item_id = None
            ops.append(_TurnOp(op=op_name, item_id=item_id, line=lineno))
            break
    counters: dict[str, int] = {}
    for name, rx in (
        ("OPEN_QUESTIONS", OPEN_QUESTIONS_RE),
        ("OPEN_DISAGREEMENTS", OPEN_DISAGREEMENTS_RE),
        ("OPEN_ISSUES", OPEN_ISSUES_RE),
        ("OPEN_COMMENTS", OPEN_COMMENTS_RE),
    ):
        m3 = rx.search(text)
        if m3 is None:
            continue
        try:
            counters[name] = int(m3.group(1))
        except (IndexError, ValueError):
            pass
    sm = STATUS_RE.search(text)
    status = sm.group(1) if sm else None
    return _TurnFile(
        path=path,
        phase=phase,
        round=int(m.group(1)),
        agent=m.group(2),
        ops=tuple(ops),
        counters=counters,
        status=status,
        rel_path=rel,
    )


def _collect_turn_files(run_dir: Path) -> list[_TurnFile]:
    out: list[_TurnFile] = []
    for phase in (0, 2, 4):
        phase_dir = run_dir / f"phase{phase}"
        if not phase_dir.exists():
            continue
        for f in sorted(phase_dir.iterdir()):
            if not f.is_file():
                continue
            tf = _parse_turn_file(f, phase, run_dir)
            if tf is not None:
                out.append(tf)
    return out


# ─── Area 1 — Phases ───────────────────────────────────────────────────

def _check_i1_1(events: list[dict]) -> InvariantResult:
    stack: list[tuple[int | None, int]] = []
    for idx, ev in enumerate(events):
        e = ev.get("event")
        if e == "phase_entered":
            stack.append((_phase_to_int(ev.get("phase")), idx))
        elif e == "phase_exited":
            phase = _phase_to_int(ev.get("phase"))
            if not stack:
                return InvariantResult(
                    "I1.1", "gating", "fail",
                    (Evidence(
                        f"transcript.jsonl:{idx + 1}",
                        f"phase_exited({phase}) without matching phase_entered",
                    ),),
                )
            head_phase, head_idx = stack.pop()
            if head_phase != phase:
                return InvariantResult(
                    "I1.1", "gating", "fail",
                    (Evidence(
                        f"transcript.jsonl:{idx + 1}",
                        f"phase_exited({phase}) mismatches phase_entered({head_phase}) at line {head_idx + 1}",
                    ),),
                )
    if stack:
        head_phase, head_idx = stack[-1]
        return InvariantResult(
            "I1.1", "gating", "fail",
            (Evidence(
                f"transcript.jsonl:{head_idx + 1}",
                f"phase_entered({head_phase}) without matching phase_exited",
            ),),
        )
    return InvariantResult("I1.1", "gating", "pass")


def _check_i1_2(events: list[dict]) -> InvariantResult:
    bad: list[Evidence] = []
    for idx, ev in enumerate(events):
        e = ev.get("event")
        if e not in ("item_raised", "item_transitioned"):
            continue
        ph = _phase_to_int(ev.get("phase"))
        if ph in (1, 3):
            bad.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"{e} in phase {ph}: id={ev.get('id')!r}",
            ))
    if bad:
        return InvariantResult("I1.2", "gating", "fail", tuple(bad))
    return InvariantResult("I1.2", "gating", "pass")


def _check_i1_3(events: list[dict]) -> InvariantResult:
    ledger: dict[int, dict[str, str]] = {}
    fail: list[Evidence] = []
    has_phase_exit = False
    for idx, ev in enumerate(events):
        e = ev.get("event")
        if e == "item_raised":
            ph = _phase_to_int(ev.get("phase"))
            if ph is None:
                continue
            ledger.setdefault(ph, {})[ev.get("id")] = "open"
        elif e == "item_transitioned":
            ph = _phase_to_int(ev.get("phase"))
            if ph is None:
                continue
            ledger.setdefault(ph, {})[ev.get("id")] = ev.get("to_state")
        elif e == "phase_exited":
            ph = _phase_to_int(ev.get("phase"))
            if ph is None:
                continue
            has_phase_exit = True
            for item_id, state in ledger.get(ph, {}).items():
                if state not in TERMINAL_STATES:
                    fail.append(Evidence(
                        f"transcript.jsonl:{idx + 1}",
                        f"phase {ph} exit: item {item_id} in non-terminal state {state!r}",
                    ))
    if not has_phase_exit:
        return InvariantResult("I1.3", "gating", "not_applicable")
    if fail:
        return InvariantResult("I1.3", "gating", "fail", tuple(fail))
    return InvariantResult("I1.3", "gating", "pass")


def _check_i1_4(events: list[dict]) -> InvariantResult:
    seen: list[int] = []
    for idx, ev in enumerate(events):
        if ev.get("event") != "phase_entered":
            continue
        ph = _phase_to_int(ev.get("phase"))
        if ph is None:
            continue
        if ph in seen:
            return InvariantResult(
                "I1.4", "gating", "fail",
                (Evidence(
                    f"transcript.jsonl:{idx + 1}",
                    f"phase {ph} re-entered after being seen at index {seen.index(ph)}",
                ),),
            )
        if seen and ph < seen[-1]:
            return InvariantResult(
                "I1.4", "gating", "fail",
                (Evidence(
                    f"transcript.jsonl:{idx + 1}",
                    f"phase {ph} entered after phase {seen[-1]} — loop-back",
                ),),
            )
        seen.append(ph)
    return InvariantResult("I1.4", "gating", "pass")


def _check_i1_5(events: list[dict]) -> InvariantResult:
    bad: list[Evidence] = []
    has_phase4_drafter = False
    for idx, ev in enumerate(events):
        if ev.get("event") != "turn_ended":
            continue
        if _phase_to_int(ev.get("phase")) != 4:
            continue
        has_phase4_drafter = True
        fr = ev.get("finish_reason")
        if fr in ("max_tokens", "length"):
            bad.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"phase 4 turn finish_reason={fr!r} (agent={ev.get('agent')!r}, label={ev.get('label')!r})",
            ))
    if not has_phase4_drafter:
        return InvariantResult("I1.5", "reporting", "not_applicable")
    if bad:
        return InvariantResult("I1.5", "reporting", "fail", tuple(bad))
    return InvariantResult("I1.5", "reporting", "pass")


# ─── Area 2 — Negotiations ─────────────────────────────────────────────


def _replay_ledger(
    events: list[dict],
) -> dict[int, dict[str, dict]]:
    """Build the final per-phase item ledger from event order.

    ``{phase_int → {item_id → {"raiser": str, "state": str,
    "addressed_by": set[str]}}}``.
    """
    ledger: dict[int, dict[str, dict]] = {}
    for ev in events:
        e = ev.get("event")
        if e == "item_raised":
            ph = _phase_to_int(ev.get("phase"))
            if ph is None:
                continue
            ledger.setdefault(ph, {})[ev.get("id")] = {
                "raiser": ev.get("raiser"),
                "state": "open",
                "addressed_by": set(),
            }
        elif e == "item_transitioned":
            ph = _phase_to_int(ev.get("phase"))
            if ph is None:
                continue
            entry = ledger.setdefault(ph, {}).setdefault(
                ev.get("id"),
                {"raiser": None, "state": "open", "addressed_by": set()},
            )
            entry["state"] = ev.get("to_state")
            if ev.get("to_state") == "addressed":
                actor = ev.get("actor")
                if actor in ("claude", "openai"):
                    entry["addressed_by"].add(actor)
    return ledger


def _check_i2_1(
    events: list[dict], turn_files: list[_TurnFile]
) -> InvariantResult:
    ledger = _replay_ledger(events)
    fail: list[Evidence] = []
    converged_count = 0
    for idx, ev in enumerate(events):
        if ev.get("event") != "phase_converged":
            continue
        converged_count += 1
        ph = _phase_to_int(ev.get("phase"))
        organic = not any(
            ev.get(k)
            for k in ("via_closeout", "via_ghost_cap", "via_hard_cap", "via_artifact_promotion")
        )
        if not organic:
            continue
        non_terminal = [
            (iid, s["state"])
            for iid, s in ledger.get(ph, {}).items()
            if s["state"] not in TERMINAL_STATES
        ]
        if non_terminal:
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"phase {ph} converged organically with non-terminal items: {non_terminal}",
            ))
        final_round = ev.get("final_round")
        claude_status = None
        openai_status = None
        for tf in turn_files:
            if tf.phase == ph and tf.round == final_round:
                if tf.agent == "claude":
                    claude_status = tf.status
                elif tf.agent == "openai":
                    openai_status = tf.status
        if claude_status != "AGREED" or openai_status != "AGREED":
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"phase {ph} organic convergence at round {final_round} but STATUS: claude={claude_status!r} openai={openai_status!r}",
            ))
    if converged_count == 0:
        return InvariantResult("I2.1", "gating", "not_applicable")
    if fail:
        return InvariantResult("I2.1", "gating", "fail", tuple(fail))
    return InvariantResult("I2.1", "gating", "pass")


def _check_i2_2(turn_files: list[_TurnFile]) -> InvariantResult:
    fail: list[Evidence] = []
    saw_r1 = False
    for tf in turn_files:
        if tf.round != 1 or tf.phase not in (0, 2, 4):
            continue
        saw_r1 = True
        if tf.status == "AGREED":
            fail.append(Evidence(
                f"{tf.rel_path}",
                f"phase {tf.phase} round 1 {tf.agent} emits STATUS: AGREED",
            ))
    if not saw_r1:
        return InvariantResult("I2.2", "gating", "not_applicable")
    if fail:
        return InvariantResult("I2.2", "gating", "fail", tuple(fail))
    return InvariantResult("I2.2", "gating", "pass")


def _check_i2_3(events: list[dict]) -> InvariantResult:
    fail: list[Evidence] = []
    converged_count = 0
    for idx, ev in enumerate(events):
        if ev.get("event") != "phase_converged":
            continue
        converged_count += 1
        flags = [
            bool(ev.get(k))
            for k in ("via_closeout", "via_ghost_cap", "via_hard_cap", "via_artifact_promotion")
        ]
        if sum(flags) > 1:
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"phase {ev.get('phase')} converged with {sum(flags)} via_* True flags: "
                f"closeout={flags[0]} ghost_cap={flags[1]} hard_cap={flags[2]} artifact_promotion={flags[3]}",
            ))
    if converged_count == 0:
        return InvariantResult("I2.3", "gating", "not_applicable")
    if fail:
        return InvariantResult("I2.3", "gating", "fail", tuple(fail))
    return InvariantResult("I2.3", "gating", "pass")


def _check_i2_4(
    events: list[dict], turn_files: list[_TurnFile]
) -> InvariantResult:
    """I2.4 — addressee-obligation invariant. An agent must not emit
    ``STATUS: AGREED`` while items raised by the OTHER agent remain
    ``open`` and un-ADDRESSed by this agent.

    Severity: ``gating`` since spec 0229 (was ``reporting`` from spec
    0225). The promotion is paired with a handled-vs-unhandled
    refactor mirroring the spec-0228 I4.4 pattern: every offending
    AGREED-while-owing turn is classified as either HANDLED (a
    matching ``agreed_with_open_addressed_items`` ProtocolViolation
    exists for the same ``(phase, round, agent)`` — the orchestrator
    demoted the AGREED) or UNHANDLED (no matching ProtocolViolation —
    the AGREED was not demoted). UNHANDLED instances fail.
    """
    fail: list[Evidence] = []
    saw_agreed = False
    # Index addressee-obligation PVs for scope-key lookup.
    handled_keys: set[tuple[int, int, str]] = set()
    for ev in events:
        if ev.get("event") == "protocol_violation" and (
            ev.get("violation_code") == "agreed_with_open_addressed_items"
        ):
            ph = _phase_to_int(ev.get("phase"))
            rd = ev.get("round")
            ag = ev.get("agent")
            if ph is not None and rd is not None and ag is not None:
                handled_keys.add((ph, rd, ag))
    for tf in turn_files:
        if tf.phase not in (0, 2, 4) or tf.status != "AGREED":
            continue
        saw_agreed = True
        sub_ledger: dict[str, dict] = {}
        for ev in events:
            if ev.get("event") not in ("item_raised", "item_transitioned"):
                continue
            ev_phase = _phase_to_int(ev.get("phase"))
            if ev_phase != tf.phase:
                continue
            ev_round = ev.get("round")
            if ev_round is None:
                include = True
            elif ev_round < tf.round:
                include = True
            elif ev_round == tf.round:
                agent_field = (
                    ev.get("raiser") if ev.get("event") == "item_raised" else ev.get("actor")
                )
                include = agent_field == tf.agent
            else:
                include = False
            if not include:
                continue
            if ev.get("event") == "item_raised":
                sub_ledger[ev.get("id")] = {
                    "raiser": ev.get("raiser"),
                    "state": "open",
                    "addressed_by": set(),
                }
            else:
                entry = sub_ledger.setdefault(
                    ev.get("id"),
                    {"raiser": None, "state": "open", "addressed_by": set()},
                )
                entry["state"] = ev.get("to_state")
                if ev.get("to_state") == "addressed":
                    actor = ev.get("actor")
                    if actor in ("claude", "openai"):
                        entry["addressed_by"].add(actor)
        # Spec 0229 §2.4 — HANDLED if a matching ProtocolViolation
        # exists for the (phase, round, agent) scope: the orchestrator
        # demoted the AGREED, the instance passes vacuously. Otherwise,
        # any offending addressed-at-me item makes this turn UNHANDLED.
        if (tf.phase, tf.round, tf.agent) in handled_keys:
            continue
        for item_id, entry in sub_ledger.items():
            raiser = entry["raiser"]
            if raiser is None or raiser == tf.agent:
                continue
            if entry["state"] == "open" and tf.agent not in entry["addressed_by"]:
                fail.append(Evidence(
                    f"{tf.rel_path}",
                    f"{tf.agent} AGREED in phase {tf.phase} r{tf.round} but item {item_id} "
                    f"(raised by {raiser}) still open and not addressed by {tf.agent}; "
                    f"no matching agreed_with_open_addressed_items ProtocolViolation",
                ))
    if not saw_agreed:
        return InvariantResult("I2.4", "gating", "not_applicable")
    if fail:
        return InvariantResult("I2.4", "gating", "fail", tuple(fail))
    return InvariantResult("I2.4", "gating", "pass")


def _open_count_by_kind(
    ledger_at_round: dict[str, dict], kind_letter: str
) -> int:
    n = 0
    for iid, entry in ledger_at_round.items():
        if entry["state"] != "open":
            continue
        if not iid:
            continue
        if iid[0] == kind_letter:
            n += 1
    return n


def _check_i2_5(
    events: list[dict], turn_files: list[_TurnFile]
) -> InvariantResult:
    fail: list[Evidence] = []
    saw_turn = False
    for tf in turn_files:
        if tf.phase not in (0, 2, 4):
            continue
        if not tf.counters:
            continue
        saw_turn = True
        sub_ledger: dict[str, dict] = {}
        for ev in events:
            if ev.get("event") not in ("item_raised", "item_transitioned"):
                continue
            if _phase_to_int(ev.get("phase")) != tf.phase:
                continue
            ev_round = ev.get("round")
            if ev_round is None:
                include = True
            elif ev_round < tf.round:
                include = True
            elif ev_round == tf.round:
                agent_field = (
                    ev.get("raiser") if ev.get("event") == "item_raised" else ev.get("actor")
                )
                include = agent_field == tf.agent
            else:
                include = False
            if not include:
                continue
            if ev.get("event") == "item_raised":
                sub_ledger[ev.get("id")] = {
                    "raiser": ev.get("raiser"),
                    "state": "open",
                    "addressed_by": set(),
                }
            else:
                entry = sub_ledger.setdefault(
                    ev.get("id"),
                    {"raiser": None, "state": "open", "addressed_by": set()},
                )
                entry["state"] = ev.get("to_state")
        for counter_name, kind_letter in (
            ("OPEN_QUESTIONS", "Q"),
            ("OPEN_DISAGREEMENTS", "D"),
            ("OPEN_ISSUES", "I"),
            ("OPEN_COMMENTS", "C"),
        ):
            if counter_name not in tf.counters:
                continue
            self_n = tf.counters[counter_name]
            ledger_n = _open_count_by_kind(sub_ledger, kind_letter)
            if self_n != ledger_n:
                fail.append(Evidence(
                    f"{tf.rel_path}",
                    f"phase {tf.phase} r{tf.round} {tf.agent}: {counter_name} self-reported {self_n}, "
                    f"ledger has {ledger_n}",
                ))
    if not saw_turn:
        return InvariantResult("I2.5", "reporting", "not_applicable")
    if fail:
        return InvariantResult("I2.5", "reporting", "fail", tuple(fail))
    return InvariantResult("I2.5", "reporting", "pass")


# ─── Area 3 — Categorisation ───────────────────────────────────────────


def _all_item_ids_from_events(events: list[dict]) -> list[tuple[str, int, str]]:
    """``[(item_id, event_index, source_event), …]`` — every ID referenced
    by ``item_raised`` / ``item_transitioned`` / ``protocol_violation`` /
    ``closeout_urged.affected_items``."""
    out: list[tuple[str, int, str]] = []
    for idx, ev in enumerate(events):
        e = ev.get("event")
        if e in ("item_raised", "item_transitioned", "protocol_violation"):
            iid = ev.get("id") or ev.get("item_id")
            if iid:
                out.append((iid, idx, e))
        elif e == "closeout_urged":
            for iid in ev.get("affected_items", []) or []:
                out.append((iid, idx, e))
    return out


def _check_i3_1(
    events: list[dict], turn_files: list[_TurnFile]
) -> InvariantResult:
    fail: list[Evidence] = []
    saw_any = False
    for iid, idx, source in _all_item_ids_from_events(events):
        saw_any = True
        if not ID_PATTERN.match(iid):
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"{source} id {iid!r} does not match ID_PATTERN ({ID_PATTERN.pattern})",
            ))
    # Also check op block IDs in turn files.
    for tf in turn_files:
        for op in tf.ops:
            if op.item_id is None:
                continue
            saw_any = True
            if not ID_PATTERN.match(op.item_id):
                fail.append(Evidence(
                    f"{tf.rel_path}:{op.line}",
                    f"{op.op} id {op.item_id!r} does not match ID_PATTERN",
                ))
    if not saw_any:
        return InvariantResult("I3.1", "gating", "not_applicable")
    if fail:
        return InvariantResult("I3.1", "gating", "fail", tuple(fail))
    return InvariantResult("I3.1", "gating", "pass")


def _check_i3_2(events: list[dict]) -> InvariantResult:
    # Items are identified by ID; an item raised with the same ID twice
    # would violate immutability. Same ID transitioning across phases is
    # also invalid. The contract reads "Item IDs are immutable across
    # rounds within a phase" — encoded as: an ID never appears in two
    # different phases.
    first_phase: dict[str, int] = {}
    fail: list[Evidence] = []
    saw_any = False
    for idx, ev in enumerate(events):
        e = ev.get("event")
        if e not in ("item_raised", "item_transitioned"):
            continue
        iid = ev.get("id")
        ph = _phase_to_int(ev.get("phase"))
        if iid is None or ph is None:
            continue
        saw_any = True
        if iid in first_phase and first_phase[iid] != ph:
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"item {iid} appeared in phase {first_phase[iid]} and phase {ph}",
            ))
        first_phase.setdefault(iid, ph)
    if not saw_any:
        return InvariantResult("I3.2", "gating", "not_applicable")
    if fail:
        return InvariantResult("I3.2", "gating", "fail", tuple(fail))
    return InvariantResult("I3.2", "gating", "pass")


def _check_i3_3(turn_files: list[_TurnFile]) -> InvariantResult:
    # The status-footer counter ARRAYS in turn files (RAISED_THIS_TURN etc.)
    # must contain only canonical IDs. The simpler proxy: every ID emitted
    # in an op block heading must be canonical (already checked by I3.1).
    # I3.3 adds a check: parse the bracketed ID-lists in status footers
    # and assert each is canonical.
    import re as _re
    bracket_lists_re = _re.compile(
        r"^[\s>*\-`#]*"
        r"(RAISED_THIS_TURN|RESOLVED_THIS_TURN|ADDRESSED_THIS_TURN|"
        r"WITHDRAWN_THIS_TURN|ACKNOWLEDGED_THIS_TURN):\s*\[(?P<ids>[^\]]*)\]",
        _re.MULTILINE,
    )
    fail: list[Evidence] = []
    saw_any = False
    for tf in turn_files:
        try:
            text = tf.path.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in bracket_lists_re.finditer(text):
            ids_raw = m.group("ids").strip()
            if not ids_raw:
                continue
            for raw in ids_raw.split(","):
                raw = raw.strip()
                if not raw:
                    continue
                saw_any = True
                if not ID_PATTERN.match(raw):
                    fail.append(Evidence(
                        f"{tf.rel_path}",
                        f"status footer {m.group(1)} contains non-canonical id {raw!r}",
                    ))
    if not saw_any:
        return InvariantResult("I3.3", "gating", "not_applicable")
    if fail:
        return InvariantResult("I3.3", "gating", "fail", tuple(fail))
    return InvariantResult("I3.3", "gating", "pass")


def _check_i3_4(events: list[dict]) -> InvariantResult:
    fail: list[Evidence] = []
    for idx, ev in enumerate(events):
        if ev.get("event") != "item_raised":
            continue
        if ev.get("item_kind") == "claim":
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"item {ev.get('id')} raised with kind=claim (removed at 0114)",
            ))
    if fail:
        return InvariantResult("I3.4", "gating", "fail", tuple(fail))
    return InvariantResult("I3.4", "gating", "pass")


def _check_i3_5(events: list[dict]) -> InvariantResult:
    fail: list[Evidence] = []
    saw_any = False
    for idx, ev in enumerate(events):
        if ev.get("event") != "item_raised":
            continue
        ph = _phase_to_int(ev.get("phase"))
        kind = ev.get("item_kind")
        if ph is None or kind is None:
            continue
        saw_any = True
        try:
            cat = Category(kind)
        except ValueError:
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"item {ev.get('id')} has unrecognised item_kind={kind!r}",
            ))
            continue
        if cat not in RAISABLE_IN.get(ph, frozenset()):
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"item {ev.get('id')} raised in phase {ph} with kind={kind} — not in RAISABLE_IN[{ph}]",
            ))
    if not saw_any:
        return InvariantResult("I3.5", "gating", "not_applicable")
    if fail:
        return InvariantResult("I3.5", "gating", "fail", tuple(fail))
    return InvariantResult("I3.5", "gating", "pass")


# ─── Area 4 — Resolution lifecycle ─────────────────────────────────────


def _edge_is_permitted(from_state: str, to_state: str) -> bool:
    if to_state in _TERMINAL_DESTINATIONS_ANY_SOURCE:
        return True
    return (from_state, to_state) in _EDGE_ALLOWLIST


def _check_i4_1(events: list[dict]) -> InvariantResult:
    fail: list[Evidence] = []
    saw_any = False
    for idx, ev in enumerate(events):
        if ev.get("event") != "item_transitioned":
            continue
        saw_any = True
        fs = ev.get("from_state")
        ts = ev.get("to_state")
        if not _edge_is_permitted(fs, ts):
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"item {ev.get('id')} transition {fs} → {ts} not in permitted edge table",
            ))
    if not saw_any:
        return InvariantResult("I4.1", "gating", "not_applicable")
    if fail:
        return InvariantResult("I4.1", "gating", "fail", tuple(fail))
    return InvariantResult("I4.1", "gating", "pass")


def _check_i4_2(events: list[dict]) -> InvariantResult:
    fail: list[Evidence] = []
    item_terminal_at: dict[str, int] = {}
    saw_any = False
    for idx, ev in enumerate(events):
        if ev.get("event") != "item_transitioned":
            continue
        saw_any = True
        iid = ev.get("id")
        if iid in item_terminal_at:
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"item {iid} transitioned after reaching terminal state at line {item_terminal_at[iid] + 1}",
            ))
            continue
        if ev.get("to_state") in TERMINAL_STATES:
            item_terminal_at[iid] = idx
    if not saw_any:
        return InvariantResult("I4.2", "gating", "not_applicable")
    if fail:
        return InvariantResult("I4.2", "gating", "fail", tuple(fail))
    return InvariantResult("I4.2", "gating", "pass")


def _check_i4_3(events: list[dict]) -> InvariantResult:
    fail: list[Evidence] = []
    saw_any = False
    for idx, ev in enumerate(events):
        if ev.get("event") != "item_transitioned":
            continue
        saw_any = True
        reason = (ev.get("reason") or "").strip()
        if not reason:
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"item {ev.get('id')} transition {ev.get('from_state')} → {ev.get('to_state')} has empty reason",
            ))
    if not saw_any:
        return InvariantResult("I4.3", "gating", "not_applicable")
    if fail:
        return InvariantResult("I4.3", "gating", "fail", tuple(fail))
    return InvariantResult("I4.3", "gating", "pass")


def _check_i4_4(
    events: list[dict], turn_files: list[_TurnFile]
) -> InvariantResult:
    """I4.4 — every op in the turn-file transcript has a corresponding
    ``item_transitioned`` or ``protocol_violation`` event in the run
    transcript.

    Severity: ``gating`` since spec 0228 (was ``reporting`` from spec 0225
    until ``apply_turn`` emitted ``ProtocolViolation`` on every silent-
    drop site — the missing emission was the documented promotion
    trigger). The check logic is unchanged from spec 0225; only the
    severity tightens.
    """
    fail: list[Evidence] = []
    saw_op = False
    transition_index: dict[tuple[int, int, str, str], bool] = {}
    for ev in events:
        if ev.get("event") == "item_transitioned":
            ph = _phase_to_int(ev.get("phase"))
            rd = ev.get("round")
            actor = ev.get("actor")
            iid = ev.get("id")
            if ph is None or rd is None or actor is None or iid is None:
                continue
            transition_index[(ph, rd, actor, iid)] = True
        elif ev.get("event") == "protocol_violation":
            ph = _phase_to_int(ev.get("phase"))
            rd = ev.get("round")
            agent = ev.get("agent")
            iid = ev.get("item_id")
            if ph is None or rd is None or agent is None or iid is None:
                continue
            transition_index[(ph, rd, agent, iid)] = True

    for tf in turn_files:
        if tf.phase not in (0, 2, 4):
            continue
        for op in tf.ops:
            if op.op not in ("RAISE", "ADDRESS", "RESOLVE", "WITHDRAW", "ACKNOWLEDGE"):
                continue
            if op.item_id is None:
                continue
            saw_op = True
            if op.op == "RAISE":
                key_iid = op.item_id
                found = False
                for ev in events:
                    if ev.get("event") != "item_raised":
                        continue
                    if (
                        _phase_to_int(ev.get("phase")) == tf.phase
                        and ev.get("round") == tf.round
                        and ev.get("raiser") == tf.agent
                        and ev.get("id") == key_iid
                    ):
                        found = True
                        break
                if not found:
                    fail.append(Evidence(
                        f"{tf.rel_path}:{op.line}",
                        f"RAISE {key_iid} in phase {tf.phase} r{tf.round} {tf.agent} has no corresponding item_raised event",
                    ))
                continue
            key = (tf.phase, tf.round, tf.agent, op.item_id)
            if key not in transition_index:
                fail.append(Evidence(
                    f"{tf.rel_path}:{op.line}",
                    f"{op.op} {op.item_id} in phase {tf.phase} r{tf.round} {tf.agent} "
                    f"has no corresponding item_transitioned or protocol_violation event",
                ))
    if not saw_op:
        return InvariantResult("I4.4", "gating", "not_applicable")
    if fail:
        return InvariantResult("I4.4", "gating", "fail", tuple(fail))
    return InvariantResult("I4.4", "gating", "pass")


def _check_i4_5(events: list[dict]) -> InvariantResult:
    fail: list[Evidence] = []
    saw_any = False
    for idx, ev in enumerate(events):
        if ev.get("event") != "item_transitioned":
            continue
        saw_any = True
        if ev.get("from_state") == "open" and ev.get("to_state") == "resolved":
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"item {ev.get('id')} has forbidden edge open → resolved",
            ))
    if not saw_any:
        return InvariantResult("I4.5", "gating", "not_applicable")
    if fail:
        return InvariantResult("I4.5", "gating", "fail", tuple(fail))
    return InvariantResult("I4.5", "gating", "pass")


def _check_i4_6(events: list[dict]) -> InvariantResult:
    # Each item that reaches `acknowledged` must have ACK from BOTH agents
    # in consecutive turns. We check: the transitions producing `acknowledged`
    # for a given item include both agents (claude + openai) — and they are
    # "consecutive" in the sense that no other ack-bearing event for the same
    # item interrupts them. The simpler invariant: an item reaches the
    # `acknowledged` state only after both agents have acknowledged it.
    # Implementation: scan transitions; for each item, collect actors of
    # ack-bearing transitions; if final state is acknowledged, both
    # {claude, openai} must be in the actor set.
    fail: list[Evidence] = []
    saw_any = False
    ack_actors: dict[str, set[str]] = {}
    final_acknowledged: dict[str, int] = {}
    for idx, ev in enumerate(events):
        if ev.get("event") != "item_transitioned":
            continue
        if ev.get("to_state") != "acknowledged":
            continue
        saw_any = True
        iid = ev.get("id")
        actor = ev.get("actor")
        # The orchestrator may emit a single ``actor="mutual"`` transition
        # representing a synthesised mutual ack — treat it as both agents
        # having acknowledged (the orchestrator only emits it after both
        # agents' turn files contained the required ACK ops).
        if actor in ("claude", "openai"):
            ack_actors.setdefault(iid, set()).add(actor)
        elif actor == "mutual":
            ack_actors.setdefault(iid, set()).update({"claude", "openai"})
        final_acknowledged[iid] = idx
    for iid, idx in final_acknowledged.items():
        actors = ack_actors.get(iid, set())
        if actors != {"claude", "openai"}:
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"item {iid} reached acknowledged with actors={sorted(actors)} (need both claude + openai)",
            ))
    if not saw_any:
        return InvariantResult("I4.6", "gating", "not_applicable")
    if fail:
        return InvariantResult("I4.6", "gating", "fail", tuple(fail))
    return InvariantResult("I4.6", "gating", "pass")


def _check_i4_7(events: list[dict]) -> InvariantResult:
    fail: list[Evidence] = []
    saw_any = False
    for idx, ev in enumerate(events):
        if ev.get("event") != "item_transitioned":
            continue
        if ev.get("to_state") != "capped":
            continue
        saw_any = True
        if not I47_PREDICATE(ev):
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"item {ev.get('id')} reached capped without {I47_PREDICATE_NAME} "
                f"(via={ev.get('via')!r}, actor={ev.get('actor')!r})",
            ))
    if not saw_any:
        return InvariantResult("I4.7", "gating", "not_applicable")
    if fail:
        return InvariantResult("I4.7", "gating", "fail", tuple(fail))
    return InvariantResult("I4.7", "gating", "pass")


# ─── Area 5 — Liveness / terminal events ───────────────────────────────


def _check_i5_1(events: list[dict]) -> InvariantResult:
    started = 0
    terminal_count = 0
    started_idx = None
    for idx, ev in enumerate(events):
        e = ev.get("event")
        if e == "run_started":
            started += 1
            started_idx = idx
        elif e in _TERMINAL_RUN_EVENTS:
            terminal_count += 1
    if started == 0:
        return InvariantResult("I5.1", "gating", "not_applicable")
    if terminal_count != 1:
        loc = f"transcript.jsonl:{(started_idx or 0) + 1}"
        return InvariantResult(
            "I5.1", "gating", "fail",
            (Evidence(
                loc,
                f"run_started events: {started}, terminal events: {terminal_count} (expected exactly 1)",
            ),),
        )
    return InvariantResult("I5.1", "gating", "pass")


def _check_i5_2(events: list[dict], metrics: dict | None) -> InvariantResult:
    has_started = any(ev.get("event") == "run_started" for ev in events)
    if not has_started:
        return InvariantResult("I5.2", "gating", "not_applicable")
    if metrics is None:
        return InvariantResult(
            "I5.2", "gating", "fail",
            (Evidence("metrics.json", "metrics.json missing"),),
        )
    ended_at = metrics.get("ended_at")
    if ended_at is None:
        return InvariantResult(
            "I5.2", "gating", "fail",
            (Evidence("metrics.json", "ended_at is null but transcript has run_started"),),
        )
    return InvariantResult("I5.2", "gating", "pass")


def _check_i5_3(events: list[dict]) -> InvariantResult:
    terminal_ts: str | None = None
    terminal_idx: int | None = None
    for idx, ev in enumerate(events):
        if ev.get("event") in _TERMINAL_RUN_EVENTS:
            terminal_ts = ev.get("ts")
            terminal_idx = idx
            break
    if terminal_ts is None:
        return InvariantResult("I5.3", "gating", "not_applicable")
    fail: list[Evidence] = []
    for idx, ev in enumerate(events):
        if ev.get("event") in _TERMINAL_RUN_EVENTS:
            continue
        ts = ev.get("ts")
        if ts is None:
            continue
        if ts > terminal_ts:
            fail.append(Evidence(
                f"transcript.jsonl:{idx + 1}",
                f"non-terminal event {ev.get('event')} at ts={ts} is later than terminal ts={terminal_ts}",
            ))
    if fail:
        return InvariantResult("I5.3", "gating", "fail", tuple(fail))
    return InvariantResult("I5.3", "gating", "pass")


def verify_run(run_dir: Path) -> VerifierReport:
    """Audit ``run_dir`` and return a :class:`VerifierReport`.

    Runs every invariant in §2.2; per-invariant verdict + evidence. The
    caller (CLI or test) decides exit code from
    :attr:`VerifierReport.has_gating_failure` and the baseline-regression
    comparison against ``expected.json``.
    """
    events = _read_events(run_dir)
    metrics = _read_metrics(run_dir)
    turn_files = _collect_turn_files(run_dir)
    results: list[InvariantResult] = [
        _check_i1_1(events),
        _check_i1_2(events),
        _check_i1_3(events),
        _check_i1_4(events),
        _check_i1_5(events),
        _check_i2_1(events, turn_files),
        _check_i2_2(turn_files),
        _check_i2_3(events),
        _check_i2_4(events, turn_files),
        _check_i2_5(events, turn_files),
        _check_i3_1(events, turn_files),
        _check_i3_2(events),
        _check_i3_3(turn_files),
        _check_i3_4(events),
        _check_i3_5(events),
        _check_i4_1(events),
        _check_i4_2(events),
        _check_i4_3(events),
        _check_i4_4(events, turn_files),
        _check_i4_5(events),
        _check_i4_6(events),
        _check_i4_7(events),
        _check_i5_1(events),
        _check_i5_2(events, metrics),
        _check_i5_3(events),
    ]
    return VerifierReport(run_dir=str(run_dir), results=tuple(results))


def baseline_regressions(
    report: VerifierReport, baseline: dict
) -> list[tuple[str, str, str]]:
    """Compare ``report`` to a frozen ``expected.json`` baseline.

    Returns ``[(invariant_id, baseline_verdict, current_verdict), …]`` for
    every invariant whose verdict regressed from ``pass`` → ``fail``. A
    regression on a reporting invariant still drives a non-zero exit per
    spec 0225 §2.1.
    """
    base = {item["id"]: item["verdict"] for item in baseline.get("results", [])}
    out: list[tuple[str, str, str]] = []
    for r in report.results:
        b = base.get(r.id)
        if b == "pass" and r.verdict == "fail":
            out.append((r.id, b, r.verdict))
    return out

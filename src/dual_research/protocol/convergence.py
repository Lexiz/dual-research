from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from dual_research.protocol.errors import ProtocolParseError, Status
from dual_research.protocol.parse import (
    ParsedTurn,
    extract_fenced_section,
    has_agreed_plan,
    parse_turn,
)


def normalized_hash(plan_block: str | None) -> str | None:
    """SHA-256 of an AGREED_PLAN block after tolerant normalization.

    Mirrors protocol.mjs normalizedHash() exactly:
    line endings → \\n, trailing whitespace stripped per line, list markers
    canonicalized (-, *, + → "- "), heading hashes lowercased, trailing
    punctuation removed per line, runs of 3+ blank lines collapsed to 2,
    final trim, then lowercase, then SHA-256 hex.
    """
    if plan_block is None:
        return None
    norm = plan_block.replace("\r\n", "\n")
    norm = re.sub(r"[ \t]+$", "", norm, flags=re.MULTILINE)
    norm = re.sub(r"^[-*+]\s+", "- ", norm, flags=re.MULTILINE)
    norm = re.sub(r"^#+\s*", lambda m: m.group(0).lower(), norm, flags=re.MULTILINE)
    norm = re.sub(r"[.,;:!?]+$", "", norm, flags=re.MULTILINE)
    norm = re.sub(r"\n{3,}", "\n\n", norm)
    norm = norm.strip().lower()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def _extract_fsd_ids(section_text: str | None) -> list[str]:
    if not section_text:
        return []
    matches = re.findall(r"^###\s+(FSD-\d+):", section_text, re.MULTILINE)
    return sorted(matches)


def _sets_equal(a: list[str], b: list[str]) -> bool:
    return sorted(a) == sorted(b)


def assert_well_formed_round1_turn(p: ParsedTurn, agent: str) -> None:
    """Round-1 of Phase 2 is exempt from the strict plan-turn check.

    Only STATUS, DRAFTER, OPEN_QUESTIONS are required; BLOCKING_DISAGREEMENTS,
    FINAL_SURFACED_DISAGREEMENTS, and AGREED_PLAN are not. (Round 1 cannot agree.)
    """
    errs: list[str] = []
    if p.status is None:
        errs.append("missing STATUS:")
    if p.drafter is None:
        errs.append("missing DRAFTER:")
    if p.open_questions is None:
        errs.append("missing OPEN_QUESTIONS:")
    if errs:
        raise ProtocolParseError(agent, errs)


def assert_well_formed_plan_turn(p: ParsedTurn, agent: str) -> None:
    errs: list[str] = []
    if p.status is None:
        errs.append("missing STATUS:")
    if p.drafter is None:
        errs.append("missing DRAFTER:")
    if p.open_questions is None:
        errs.append("missing OPEN_QUESTIONS:")
    if p.blocking_disagreements is None:
        errs.append("missing BLOCKING_DISAGREEMENTS:")
    if p.final_surfaced_disagreements is None:
        errs.append("missing FINAL_SURFACED_DISAGREEMENTS:")
    if p.status == Status.AGREED and not has_agreed_plan(p):
        errs.append("STATUS: AGREED without populated AGREED_PLAN block")
    if p.status == Status.AGREED and not p.strongest_remaining_objection:
        errs.append(
            "missing STRONGEST_REMAINING_OBJECTION: in Agreement check (required when STATUS: AGREED)"
        )
    if p.status == Status.AGREED and not p.why_non_blocking:
        errs.append(
            "missing WHY_NON_BLOCKING: in Agreement check (required when STATUS: AGREED)"
        )
    if errs:
        raise ProtocolParseError(agent, errs)


def assert_well_formed_review_turn(
    p: ParsedTurn, agent: str, *, round: int | None = None
) -> None:
    errs: list[str] = []
    if p.status is None:
        errs.append("missing STATUS:")
    if p.open_issues is None:
        errs.append("missing OPEN_ISSUES:")
    if not p.evidence_checked_section:
        errs.append("missing ## Evidence checked this round section")
    if (round == 1 or p.status == Status.APPROVED) and not p.carryover_audit_section:
        errs.append(
            "missing ## Disagreement carryover audit section "
            "(required in round 1 and in any turn emitting STATUS: APPROVED)"
        )
    if p.status == Status.APPROVED and not p.strongest_remaining_objection:
        errs.append(
            "missing STRONGEST_REMAINING_OBJECTION: in Approval check (required when STATUS: APPROVED)"
        )
    if p.status == Status.APPROVED and not p.why_non_blocking:
        errs.append(
            "missing WHY_NON_BLOCKING: in Approval check (required when STATUS: APPROVED)"
        )
    if errs:
        raise ProtocolParseError(agent, errs)


def is_plan_agreed(
    claude_turn: str,
    openai_turn: str,
    *,
    ledger_open_count: int | None = None,
) -> bool:
    """v3 convergence gate. Throws ProtocolParseError on malformed turns.

    Spec 0043 D7 — when ``ledger_open_count`` is provided (int), the
    convergence check additionally requires it to be 0. This is the
    conservative cross-check: agents must self-report AGREED + 0
    counters AND the system-derived ledger must also show 0 open
    items. If they disagree, convergence is blocked and the phase
    keeps running. When ``ledger_open_count`` is None (legacy mode
    or no ledger available), the ledger check is skipped — behaviour
    matches pre-spec.

    Spec 0089 — the canonical FSD sub-section lookup is now scoped to
    the FULL turn body, not the parsed ``agreed_plan`` field. ``parse_turn``
    extracts the AGREED_PLAN body up to the next ``## `` heading and the
    agent-emitted canonical sub-section is itself a ``## `` heading
    (per the protocol prompt) — so it never lives INSIDE the parsed
    agreed_plan. The standalone Final-surfaced disagreements section
    has always been scoped to the full turn, and is unchanged here.
    """
    c = parse_turn(claude_turn)
    o = parse_turn(openai_turn)
    assert_well_formed_plan_turn(c, "claude")
    assert_well_formed_plan_turn(o, "openai")

    if c.status != Status.AGREED or o.status != Status.AGREED:
        return False
    if c.drafter != o.drafter or c.drafter is None:
        return False
    if c.open_questions != 0 or o.open_questions != 0:
        return False
    if c.blocking_disagreements != 0 or o.blocking_disagreements != 0:
        return False
    if not has_agreed_plan(c) or not has_agreed_plan(o):
        return False
    if normalized_hash(c.agreed_plan) != normalized_hash(o.agreed_plan):
        return False
    if c.final_surfaced_disagreements != o.final_surfaced_disagreements:
        return False

    fsd_count = c.final_surfaced_disagreements or 0
    if fsd_count > 0:
        c_ids = _extract_fsd_ids(extract_fenced_section(claude_turn, "Final-surfaced disagreements"))
        o_ids = _extract_fsd_ids(extract_fenced_section(openai_turn, "Final-surfaced disagreements"))
        if not _sets_equal(c_ids, o_ids):
            return False
        # Spec 0089 — scope corrected from ``c.agreed_plan`` to the full
        # turn body. The canonical sub-section is structurally a sibling
        # ``##`` heading to ``## AGREED_PLAN``, not a child of it.
        canonical = extract_fenced_section(claude_turn, "Final-surfaced disagreements (canonical)")
        if not canonical:
            return False
        if not _sets_equal(c_ids, _extract_fsd_ids(canonical)):
            return False
        # And the OTHER agent must have emitted a canonical too.
        if not extract_fenced_section(openai_turn, "Final-surfaced disagreements (canonical)"):
            return False

    # Spec 0043 D7 — ledger cross-check. None means "ledger not
    # available or kill-switch active" → skip. Otherwise both signals
    # must agree the open-set is empty.
    if ledger_open_count is not None and ledger_open_count > 0:
        return False

    return True


def is_review_approved(
    claude_turn: str,
    openai_turn: str,
    *,
    round: int | None = None,
    ledger_open_count: int | None = None,
) -> bool:
    """Phase 4 termination check. Spec 0043 D7 adds an optional
    ledger cross-check — same semantics as ``is_plan_agreed``."""
    c = parse_turn(claude_turn)
    o = parse_turn(openai_turn)
    assert_well_formed_review_turn(c, "claude", round=round)
    assert_well_formed_review_turn(o, "openai", round=round)
    if not (
        c.status == Status.APPROVED
        and o.status == Status.APPROVED
        and c.open_issues == 0
        and o.open_issues == 0
    ):
        return False
    if ledger_open_count is not None and ledger_open_count > 0:
        return False
    return True


@dataclass(frozen=True)
class TiebreakCheck:
    passes: bool
    claude_drafter: str | None = None
    openai_drafter: str | None = None
    agreed_plan: str | None = None


@dataclass(frozen=True)
class PlanHashDrift:
    """Spec 0032 — describes the 'agreed on everything except the plan hash' state.

    Fires when both agents emit STATUS: AGREED with matching drafter / OQ=0
    / BD=0 / matching FSD count / both having a populated AGREED_PLAN block,
    but ``normalized_hash(claude.agreed_plan) != normalized_hash(openai.agreed_plan)``.
    The protocol prompt acknowledges this case explicitly — "Same-round
    AGREED with mismatched plans is a parse error and triggers a repair
    turn" — but the orchestrator didn't implement that branch before
    spec 0032.

    ``other_agent`` is the agent the orchestrator should re-call with a
    ``force_verbatim_copy_prompt``: by definition the non-drafter, since
    the drafter's plan is the one we canonicalise.
    """

    detected: bool
    drafter: str | None = None            # "claude" | "gpt"
    canonical_plan: str | None = None     # the drafter's AGREED_PLAN block
    other_agent: str | None = None        # "claude" | "gpt" — the one to repair
    canonical_hash: str | None = None     # short hash for telemetry
    other_hash: str | None = None         # short hash of the non-canonical plan


def all_substantive_gates_pass_except_drafter(
    claude_turn: str, openai_turn: str
) -> TiebreakCheck:
    """Detects the drafter-mismatch-only state so the orchestrator can run
    pick_drafter without consuming another protocol round."""
    try:
        c = parse_turn(claude_turn)
        o = parse_turn(openai_turn)
        assert_well_formed_plan_turn(c, "claude")
        assert_well_formed_plan_turn(o, "openai")
    except ProtocolParseError:
        return TiebreakCheck(passes=False)

    if c.status != Status.AGREED or o.status != Status.AGREED:
        return TiebreakCheck(passes=False)
    if c.open_questions != 0 or o.open_questions != 0:
        return TiebreakCheck(passes=False)
    if c.blocking_disagreements != 0 or o.blocking_disagreements != 0:
        return TiebreakCheck(passes=False)
    if c.final_surfaced_disagreements != o.final_surfaced_disagreements:
        return TiebreakCheck(passes=False)
    if not has_agreed_plan(c) or not has_agreed_plan(o):
        return TiebreakCheck(passes=False)
    if normalized_hash(c.agreed_plan) != normalized_hash(o.agreed_plan):
        return TiebreakCheck(passes=False)

    fsd_count = c.final_surfaced_disagreements or 0
    if fsd_count > 0:
        c_ids = _extract_fsd_ids(extract_fenced_section(claude_turn, "Final-surfaced disagreements"))
        o_ids = _extract_fsd_ids(extract_fenced_section(openai_turn, "Final-surfaced disagreements"))
        if not _sets_equal(c_ids, o_ids):
            return TiebreakCheck(passes=False)
        canonical = extract_fenced_section(c.agreed_plan or "", "Final-surfaced disagreements (canonical)")
        if not canonical or not _sets_equal(c_ids, _extract_fsd_ids(canonical)):
            return TiebreakCheck(passes=False)

    if c.drafter is None or o.drafter is None:
        return TiebreakCheck(passes=False)
    if c.drafter == o.drafter:
        return TiebreakCheck(passes=False)

    return TiebreakCheck(
        passes=True,
        claude_drafter=c.drafter,
        openai_drafter=o.drafter,
        agreed_plan=c.agreed_plan,
    )


@dataclass(frozen=True)
class FsdItem:
    id: str
    title: str
    claude_position: str
    gpt_position: str
    final_document_treatment: str
    affects_recommendation: str


def all_substantive_gates_pass_except_plan_hash(
    claude_turn: str, openai_turn: str
) -> PlanHashDrift:
    """Spec 0032 — detect the 'agreed except for plan-hash drift' state.

    Returns ``PlanHashDrift(detected=False)`` whenever any substantive
    gate fails. When all gates pass except the plan hash, returns a
    populated dataclass naming the canonical plan (the one written by the
    named drafter) and which agent needs to copy it verbatim.

    Distinct from ``all_substantive_gates_pass_except_drafter``: this one
    requires drafters to MATCH and hashes to DIFFER, vs that one which
    requires drafters to DIFFER and hashes to MATCH. Either failure mode
    has its own escape hatch.
    """
    try:
        c = parse_turn(claude_turn)
        o = parse_turn(openai_turn)
        assert_well_formed_plan_turn(c, "claude")
        assert_well_formed_plan_turn(o, "openai")
    except ProtocolParseError:
        return PlanHashDrift(detected=False)

    if c.status != Status.AGREED or o.status != Status.AGREED:
        return PlanHashDrift(detected=False)
    if c.open_questions != 0 or o.open_questions != 0:
        return PlanHashDrift(detected=False)
    if c.blocking_disagreements != 0 or o.blocking_disagreements != 0:
        return PlanHashDrift(detected=False)
    if c.final_surfaced_disagreements != o.final_surfaced_disagreements:
        return PlanHashDrift(detected=False)
    if not has_agreed_plan(c) or not has_agreed_plan(o):
        return PlanHashDrift(detected=False)
    if c.drafter is None or o.drafter is None or c.drafter != o.drafter:
        # Drafters MUST match for this state — the
        # all_substantive_gates_pass_except_drafter path handles the
        # opposite case.
        return PlanHashDrift(detected=False)

    c_hash = normalized_hash(c.agreed_plan)
    o_hash = normalized_hash(o.agreed_plan)
    if c_hash == o_hash:
        # Hashes match: this is the success path, not drift.
        return PlanHashDrift(detected=False)

    # We have the drift state. The drafter named in both turns picks
    # which plan is canonical.
    drafter = c.drafter
    canonical_plan = c.agreed_plan if drafter == "claude" else o.agreed_plan
    other_agent = "gpt" if drafter == "claude" else "claude"
    canonical_hash = c_hash if drafter == "claude" else o_hash
    other_hash = o_hash if drafter == "claude" else c_hash

    return PlanHashDrift(
        detected=True,
        drafter=drafter,
        canonical_plan=canonical_plan,
        other_agent=other_agent,
        canonical_hash=canonical_hash,
        other_hash=other_hash,
    )


def extract_canonical_fsd_items(agreed_plan_text: str | None) -> list[FsdItem]:
    """Pull the structured FSD items from the canonical FSD section of an AGREED_PLAN.

    Returns [] when the canonical section is absent. Used by Phase 3 to inject
    FSD context into the drafter's prompt without re-parsing the free-form
    Phase 2 sections (which can differ between agents).
    """
    if not agreed_plan_text:
        return []
    section = extract_fenced_section(agreed_plan_text, "Final-surfaced disagreements (canonical)")
    if not section:
        return []

    items: list[FsdItem] = []
    heading_re = re.compile(r"^###\s+(FSD-\d+):\s*(.*)$", re.MULTILINE)
    for m in heading_re.finditer(section):
        item_id = m.group(1)
        title = (m.group(2) or "").strip()
        start = m.end()
        next_m = re.search(r"^###\s+FSD-", section[start:], re.MULTILINE)
        content = section[start : start + next_m.start()] if next_m else section[start:]

        def _field(name: str, body: str = content) -> str:
            # Field-name separator is either ":" or "?" — the canonical FSD format
            # uses "Affects final recommendation? yes/no" with no colon.
            pat = re.compile(r"^-\s*" + re.escape(name) + r"[?:]\s*(.+)$", re.MULTILINE)
            fm = pat.search(body)
            return fm.group(1).strip() if fm else ""

        items.append(
            FsdItem(
                id=item_id,
                title=title,
                claude_position=_field("Claude position"),
                gpt_position=_field("GPT position"),
                final_document_treatment=_field("Exact final-document treatment"),
                affects_recommendation=_field("Affects final recommendation"),
            )
        )
    return items


def summarise_deadlock(claude_turn: str, openai_turn: str) -> dict:
    c = parse_turn(claude_turn)
    o = parse_turn(openai_turn)
    return {
        "claude": {
            "status": c.status,
            "drafter": c.drafter,
            "open_questions": c.open_questions,
            "open_issues": c.open_issues,
            "blocking_disagreements": c.blocking_disagreements,
            "final_surfaced_disagreements": c.final_surfaced_disagreements,
        },
        "openai": {
            "status": o.status,
            "drafter": o.drafter,
            "open_questions": o.open_questions,
            "open_issues": o.open_issues,
            "blocking_disagreements": o.blocking_disagreements,
            "final_surfaced_disagreements": o.final_surfaced_disagreements,
        },
    }


# ─── Spec 0089 — additional convergence escapes ────────────────────────────


class CanonicalFsdSynthesisError(Exception):
    """Raised when ``synthesize_canonical_fsd_section_from_standalone`` cannot
    construct a valid canonical block because the standalone Final-surfaced
    disagreements section is itself missing required fields. The orchestrator
    should treat this as a non-escape signal and let the negotiation loop
    continue normally.
    """


@dataclass(frozen=True)
class CanonicalFsdMissing:
    """Spec 0089 § A — describes the 'agreed except missing canonical FSD
    sub-section' state.

    Fires when both agents emit STATUS: AGREED with matching drafter /
    OQ=0 / BD=0 / matching FSD count (> 0) / matching plan hash /
    matching standalone FSD IDs, but neither agent's AGREED_PLAN
    contains a populated ``## Final-surfaced disagreements (canonical)``
    sub-section. The canonical sub-section is the single source of
    truth consumed by Phase 3 (per the protocol prompt) and is a
    strict subset of the standalone section both agents already wrote
    — the orchestrator can synthesise it without a repair turn.

    ``synthesized_section`` carries the ready-to-splice markdown block;
    the splice itself happens in ``splice_canonical_into_agreed_plan``.
    """

    detected: bool
    drafter: str | None = None
    canonical_plan: str | None = None          # drafter's plan (pre-splice)
    synthesized_section: str | None = None     # the ## ... (canonical) block
    fsd_ids: tuple[str, ...] = ()


def all_substantive_gates_pass_except_canonical_fsd(
    claude_turn: str, openai_turn: str
) -> CanonicalFsdMissing:
    """Spec 0089 § A — detect the 'agreed except missing canonical FSD
    sub-section' state.

    Returns ``CanonicalFsdMissing(detected=False)`` whenever any of the
    substantive gates this escape relies on fails. When all those gates
    pass AND the canonical sub-section is absent from at least one
    AGREED_PLAN, returns a populated dataclass naming the drafter (whose
    standalone section is the synthesis source), the FSD IDs at play, and
    a ready-to-splice canonical block.

    Distinct from ``all_substantive_gates_pass_except_plan_hash`` in
    that this one requires plan hashes to MATCH (and thus is mutually
    exclusive with the hash-drift escape). Also distinct from
    ``all_substantive_gates_pass_except_drafter`` (this one requires
    drafters to MATCH).
    """
    try:
        c = parse_turn(claude_turn)
        o = parse_turn(openai_turn)
        assert_well_formed_plan_turn(c, "claude")
        assert_well_formed_plan_turn(o, "openai")
    except ProtocolParseError:
        return CanonicalFsdMissing(detected=False)

    if c.status != Status.AGREED or o.status != Status.AGREED:
        return CanonicalFsdMissing(detected=False)
    if c.open_questions != 0 or o.open_questions != 0:
        return CanonicalFsdMissing(detected=False)
    if c.blocking_disagreements != 0 or o.blocking_disagreements != 0:
        return CanonicalFsdMissing(detected=False)
    if c.final_surfaced_disagreements != o.final_surfaced_disagreements:
        return CanonicalFsdMissing(detected=False)
    fsd_count = c.final_surfaced_disagreements or 0
    if fsd_count <= 0:
        # No FSDs means no canonical section is required — this escape
        # doesn't apply. (is_plan_agreed would have succeeded if every
        # other gate passed.)
        return CanonicalFsdMissing(detected=False)
    if c.drafter is None or o.drafter is None or c.drafter != o.drafter:
        return CanonicalFsdMissing(detected=False)
    if not has_agreed_plan(c) or not has_agreed_plan(o):
        return CanonicalFsdMissing(detected=False)
    if normalized_hash(c.agreed_plan) != normalized_hash(o.agreed_plan):
        return CanonicalFsdMissing(detected=False)

    # Standalone sections — both must exist and have matching IDs.
    c_standalone = extract_fenced_section(claude_turn, "Final-surfaced disagreements")
    o_standalone = extract_fenced_section(openai_turn, "Final-surfaced disagreements")
    if not c_standalone or not o_standalone:
        return CanonicalFsdMissing(detected=False)
    c_ids = _extract_fsd_ids(c_standalone)
    o_ids = _extract_fsd_ids(o_standalone)
    if not _sets_equal(c_ids, o_ids) or not c_ids:
        return CanonicalFsdMissing(detected=False)

    # Canonical section must be absent from BOTH turns for the escape
    # to be the relevant fix. (Spec 0089 — scope is the FULL turn body;
    # the canonical sub-section is structurally a sibling ``##`` heading
    # to ``## AGREED_PLAN``, not a child of it, so it lives at the top
    # of the turn body, not inside parsed.agreed_plan.)
    c_canonical = extract_fenced_section(claude_turn, "Final-surfaced disagreements (canonical)")
    o_canonical = extract_fenced_section(openai_turn, "Final-surfaced disagreements (canonical)")
    if c_canonical or o_canonical:
        return CanonicalFsdMissing(detected=False)

    drafter = c.drafter
    canonical_plan = c.agreed_plan if drafter == "claude" else o.agreed_plan
    drafter_standalone = c_standalone if drafter == "claude" else o_standalone

    try:
        synthesized = synthesize_canonical_fsd_section_from_standalone(
            drafter_standalone, fsd_ids=tuple(c_ids)
        )
    except CanonicalFsdSynthesisError:
        # Standalone section is also incomplete — caller falls through.
        return CanonicalFsdMissing(detected=False)

    return CanonicalFsdMissing(
        detected=True,
        drafter=drafter,
        canonical_plan=canonical_plan,
        synthesized_section=synthesized,
        fsd_ids=tuple(c_ids),
    )


_CANONICAL_FIELD_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Claude position", ("Claude position",)),
    ("GPT position", ("GPT position",)),
    ("Exact final-document treatment", ("Exact final-document treatment",)),
    (
        # The canonical block uses "Affects final recommendation?" while the
        # standalone block uses "Does this affect the final recommendation?".
        # We accept either spelling in the source and always emit the canonical
        # spelling in the output.
        "Affects final recommendation",
        ("Affects final recommendation", "Does this affect the final recommendation"),
    ),
)


def synthesize_canonical_fsd_section_from_standalone(
    standalone_section_text: str,
    *,
    fsd_ids: tuple[str, ...] | None = None,
) -> str:
    """Spec 0089 § A — pure-function synthesis of the ``## Final-surfaced
    disagreements (canonical)`` sub-section from the agent's standalone
    ``## Final-surfaced disagreements`` section.

    The canonical sub-section is a strict subset of the standalone (4
    required fields per FSD-N vs 8). This function copies the 4 needed
    field values out of the standalone and re-emits them in the canonical
    format documented in prompts.py:413-421.

    If ``fsd_ids`` is provided, only emits those IDs (in the given order).
    Otherwise emits every FSD-N found in source order.

    Raises ``CanonicalFsdSynthesisError`` when a required field is missing
    from any FSD-N entry in the standalone section. Idempotent: passing
    a canonical-style section back through this function returns an
    equivalent canonical section.
    """
    if not standalone_section_text or not standalone_section_text.strip():
        raise CanonicalFsdSynthesisError(
            "standalone Final-surfaced disagreements section is empty"
        )

    entries = _parse_standalone_fsd_entries(standalone_section_text)
    if not entries:
        raise CanonicalFsdSynthesisError(
            "no FSD-N entries found in standalone section"
        )

    by_id = {e["id"]: e for e in entries}
    target_ids = tuple(fsd_ids) if fsd_ids else tuple(e["id"] for e in entries)

    out_lines: list[str] = ["## Final-surfaced disagreements (canonical)", ""]
    for fid in target_ids:
        entry = by_id.get(fid)
        if entry is None:
            raise CanonicalFsdSynthesisError(
                f"requested FSD id {fid!r} not present in standalone section"
            )
        title = entry["title"]
        out_lines.append(f"### {fid}: {title}".rstrip())
        out_lines.append("")
        for canonical_label, source_labels in _CANONICAL_FIELD_PATTERNS:
            value = ""
            for src in source_labels:
                value = entry["fields"].get(src, "")
                if value:
                    break
            if not value:
                raise CanonicalFsdSynthesisError(
                    f"FSD {fid} is missing required field {canonical_label!r} "
                    f"(tried {list(source_labels)})"
                )
            # Affects-recommendation field uses '? yes / no' format in canonical
            if canonical_label == "Affects final recommendation":
                out_lines.append(f"- {canonical_label}? {value}")
            else:
                out_lines.append(f"- {canonical_label}: {value}")
        out_lines.append("")

    return "\n".join(out_lines).rstrip() + "\n"


def _parse_standalone_fsd_entries(section_text: str) -> list[dict]:
    """Internal helper. Parses ``### FSD-N: <title>`` entries from a
    Final-surfaced disagreements section (canonical or standalone format).

    Returns a list of dicts ``{"id": "FSD-1", "title": "...", "fields": {
    "Claude position": "...", ...}}`` in source order.
    """
    heading_re = re.compile(r"^###\s+(FSD-\d+):\s*(.*)$", re.MULTILINE)
    field_re = re.compile(r"^-\s*([^:?]+?)\s*[?:]\s*(.+)$", re.MULTILINE)

    entries: list[dict] = []
    matches = list(heading_re.finditer(section_text))
    for i, m in enumerate(matches):
        fid = m.group(1)
        title = (m.group(2) or "").strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(section_text)
        body = section_text[start:end]
        fields: dict[str, str] = {}
        for fm in field_re.finditer(body):
            label = fm.group(1).strip()
            value = fm.group(2).strip()
            if label and value and label not in fields:
                fields[label] = value
        entries.append({"id": fid, "title": title, "fields": fields})
    return entries


def compose_full_agreed_plan(turn_text: str, parsed_agreed_plan: str | None) -> str:
    """Spec 0089 — return the parsed AGREED_PLAN block with the canonical
    FSD sub-section appended when it appears at the top-level of the turn
    body.

    Background: ``parse_turn`` extracts the AGREED_PLAN body up to the
    next ``##`` heading. Because the protocol prompt asks agents to emit
    the canonical FSD sub-section as ``## Final-surfaced disagreements
    (canonical)`` (a sibling ``##`` heading to ``## AGREED_PLAN``), the
    canonical section never lives inside the parsed agreed_plan field.
    This helper recombines them so downstream consumers (Phase 3's
    drafting prompt, ``extract_canonical_fsd_items``) see a single
    self-contained plan-plus-canonical block.

    Used at every site in phase2.py that stores ``ctx.state.agreed_plan``
    on a converged path. Returns ``parsed_agreed_plan`` unchanged when no
    canonical sub-section is present in the turn body.
    """
    base = parsed_agreed_plan or ""
    canonical_body = extract_fenced_section(
        turn_text, "Final-surfaced disagreements (canonical)"
    )
    if not canonical_body:
        return base
    canonical_block = (
        "## Final-surfaced disagreements (canonical)\n\n"
        + canonical_body.rstrip()
        + "\n"
    )
    return splice_canonical_into_agreed_plan(base, canonical_block)


def splice_canonical_into_agreed_plan(
    plan_text: str, canonical_section: str
) -> str:
    """Spec 0089 § A — insert (or replace) the ``## Final-surfaced
    disagreements (canonical)`` sub-section inside an AGREED_PLAN block.

    If the plan already contains a canonical sub-section, it is replaced
    with ``canonical_section`` (idempotent: same canonical section in →
    same plan text out). Otherwise the section is appended after the
    plan's existing content with a separating blank line.

    Whitespace is normalised so the result still hashes equivalently
    under ``normalized_hash``.
    """
    if not plan_text:
        return canonical_section.rstrip() + "\n"

    canonical_norm = canonical_section.rstrip() + "\n"

    # Locate an existing canonical section and replace it.
    existing_re = re.compile(
        r"(^##\s+Final-surfaced disagreements \(canonical\)\s*\n)(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    if existing_re.search(plan_text):
        return existing_re.sub(canonical_norm, plan_text)

    # No existing canonical → append.
    trimmed = plan_text.rstrip()
    return f"{trimmed}\n\n{canonical_norm}"


# ─── Spec 0089 § B — lenient convergence checks (no ledger cross-check) ────


def is_plan_agreed_lenient(claude_turn: str, openai_turn: str) -> bool:
    """Spec 0089 § B — same shape as ``is_plan_agreed`` but with no
    ledger cross-check parameter and no ledger gate.

    Returns True when agents are fully aligned on protocol surface
    signals (status, drafter, OQ, BD, FSD count, plan hash, FSD canonical
    section presence and IDs). The orchestrator uses this together with
    the strict ``is_plan_agreed`` to detect the 'agents aligned, ledger
    disagrees' state and fire the stuck-AGREED escape valve after
    ``STUCK_AGREED_K`` consecutive blocked rounds.
    """
    c = parse_turn(claude_turn)
    o = parse_turn(openai_turn)
    assert_well_formed_plan_turn(c, "claude")
    assert_well_formed_plan_turn(o, "openai")

    if c.status != Status.AGREED or o.status != Status.AGREED:
        return False
    if c.drafter != o.drafter or c.drafter is None:
        return False
    if c.open_questions != 0 or o.open_questions != 0:
        return False
    if c.blocking_disagreements != 0 or o.blocking_disagreements != 0:
        return False
    if not has_agreed_plan(c) or not has_agreed_plan(o):
        return False
    if normalized_hash(c.agreed_plan) != normalized_hash(o.agreed_plan):
        return False
    if c.final_surfaced_disagreements != o.final_surfaced_disagreements:
        return False

    fsd_count = c.final_surfaced_disagreements or 0
    if fsd_count > 0:
        c_ids = _extract_fsd_ids(extract_fenced_section(claude_turn, "Final-surfaced disagreements"))
        o_ids = _extract_fsd_ids(extract_fenced_section(openai_turn, "Final-surfaced disagreements"))
        if not _sets_equal(c_ids, o_ids):
            return False
        # Spec 0089 — scope corrected to the full turn body (see
        # ``is_plan_agreed`` for the rationale).
        canonical = extract_fenced_section(claude_turn, "Final-surfaced disagreements (canonical)")
        if not canonical:
            return False
        if not _sets_equal(c_ids, _extract_fsd_ids(canonical)):
            return False
        if not extract_fenced_section(openai_turn, "Final-surfaced disagreements (canonical)"):
            return False

    return True


def is_review_approved_lenient(
    claude_turn: str,
    openai_turn: str,
    *,
    round: int | None = None,
) -> bool:
    """Spec 0089 § B — Phase 4 lenient termination check.

    Same shape as ``is_review_approved`` but skips the ledger cross-check.
    Used by the Phase 4 stuck-APPROVED escape valve.
    """
    c = parse_turn(claude_turn)
    o = parse_turn(openai_turn)
    assert_well_formed_review_turn(c, "claude", round=round)
    assert_well_formed_review_turn(o, "openai", round=round)
    return (
        c.status == Status.APPROVED
        and o.status == Status.APPROVED
        and c.open_issues == 0
        and o.open_issues == 0
    )

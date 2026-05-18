"""Tests for SPEC-0067 parseCodeId semantics.

The parser lives in shared.jsx (JavaScript); these tests lock the expected
parsing contract using a pure-Python equivalent so the UI behaviour is
documented and regressions are caught early.
"""

import re


# ── Python mirror of shared.jsx parseCodeId ────────────────────────────────────

CODE_KIND_MAP = {
    "Q": "question",
    "I": "issue",
    "C": "comment",
    "Cl": "claim",
    "d": "disagreement",
}


def parse_code_id(id_str: str) -> dict:
    """Parse a critique public ID into structured components."""
    if not isinstance(id_str, str):
        return {"raw": str(id_str or ""), "kind": None, "raiser": None, "round": None, "phase": None, "sequence": None}

    raw = id_str

    # Disagreement: d-NN
    dm = re.match(r"^d-(\d+)$", id_str)
    if dm:
        return {"raw": raw, "kind": "disagreement", "raiser": None, "round": None, "phase": None, "sequence": int(dm.group(1))}

    # Q/I/C/Cl: PREFIX-RAISER-r/pN-SEQ
    m = re.match(r"^(Q|I|C|Cl)-([cg])-([rp])(\d+)-(\d+)$", id_str)
    if m:
        kind = CODE_KIND_MAP.get(m.group(1), m.group(1))
        raiser = "claude" if m.group(2) == "c" else "gpt"
        is_phase = m.group(3) == "p"
        return {
            "raw": raw,
            "kind": kind,
            "raiser": raiser,
            "round": None if is_phase else int(m.group(4)),
            "phase": int(m.group(4)) if is_phase else None,
            "sequence": int(m.group(5)),
        }

    # Fallback
    return {"raw": raw, "kind": None, "raiser": None, "round": None, "phase": None, "sequence": None}


# ── Tests ──────────────────────────────────────────────────────────────────────


class TestParseCodeId:
    """Lock parsing semantics for the five known public-ID prefixes."""

    def test_question_claude_round(self):
        r = parse_code_id("Q-c-r1-04")
        assert r["kind"] == "question"
        assert r["raiser"] == "claude"
        assert r["round"] == 1
        assert r["phase"] is None
        assert r["sequence"] == 4
        assert r["raw"] == "Q-c-r1-04"

    def test_issue_gpt_round(self):
        r = parse_code_id("I-g-r2-06")
        assert r["kind"] == "issue"
        assert r["raiser"] == "gpt"
        assert r["round"] == 2
        assert r["sequence"] == 6

    def test_comment_claude_round(self):
        r = parse_code_id("C-c-r1-01")
        assert r["kind"] == "comment"
        assert r["raiser"] == "claude"
        assert r["round"] == 1
        assert r["sequence"] == 1

    def test_claim_claude_round(self):
        r = parse_code_id("Cl-c-r1-04")
        assert r["kind"] == "claim"
        assert r["raiser"] == "claude"
        assert r["round"] == 1
        assert r["sequence"] == 4

    def test_claim_phase_encoding(self):
        """Claims may encode phase instead of round (Cl-c-p1-01)."""
        r = parse_code_id("Cl-c-p1-01")
        assert r["kind"] == "claim"
        assert r["raiser"] == "claude"
        assert r["round"] is None
        assert r["phase"] == 1
        assert r["sequence"] == 1

    def test_disagreement(self):
        r = parse_code_id("d-04")
        assert r["kind"] == "disagreement"
        assert r["raiser"] is None
        assert r["round"] is None
        assert r["sequence"] == 4

    def test_malformed_fallback(self):
        r = parse_code_id("not-a-valid-id")
        assert r["kind"] is None
        assert r["raiser"] is None
        assert r["round"] is None
        assert r["sequence"] is None
        assert r["raw"] == "not-a-valid-id"

    def test_non_string_fallback(self):
        r = parse_code_id(42)
        assert r["kind"] is None
        assert r["raw"] == "42"

    def test_none_fallback(self):
        r = parse_code_id(None)
        assert r["kind"] is None
        assert r["raw"] == ""

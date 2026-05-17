"""Spec 0042 — claims reconstructor + parser coverage tests."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from dual_research.ui.claims import reconstruct_claims


def _seed_phase1(tmp_path: Path, agent: str, body: str) -> Path:
    path = tmp_path / "phase1" / f"draft-{agent}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def _seed_phase2_round(tmp_path: Path, round_n: int, agent: str, body: str) -> Path:
    rr = f"{round_n:02d}"
    path = tmp_path / "phase2" / f"round-{rr}-{agent}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_phase1_claims_section_extracted(tmp_path: Path) -> None:
    """Phase 1 draft with ``## 4. Claims I Expect…`` produces one Claim per
    numbered entry, all with ``phase=1`` and the no-round turn key."""
    _seed_phase1(tmp_path, "claude", dedent("""
        ## 1. Summary
        Body.

        ## 4. Claims I Expect the Other Agent Might Dispute

        1. **First contested claim.** Body of first.

        2. **Second contested claim.** Body of second.

        3. **Third contested claim.** Body of third.
    """).strip())

    claims = reconstruct_claims(tmp_path)
    p1_claude = [c for c in claims if c.phase == 1 and c.raised_by == "claude"]
    assert len(p1_claude) == 3
    assert p1_claude[0].id == "Cl-c-p1-01"
    assert p1_claude[0].raised_turn_key == "phase1_claude"
    assert p1_claude[0].raised_round == 0
    assert p1_claude[0].status == "open"
    assert p1_claude[0].body.startswith("**First contested claim.**")


def test_phase1_claims_tolerates_no_numeric_prefix(tmp_path: Path) -> None:
    """Heading ``## Claims I Expect the Other Agent Might Dispute`` (no
    leading number) also matches — the parser tolerates both forms."""
    _seed_phase1(tmp_path, "claude", dedent("""
        ## Claims I Expect the Other Agent Might Dispute

        1. **Only claim.** Body.
    """).strip())
    claims = reconstruct_claims(tmp_path)
    assert len(claims) == 1
    assert claims[0].body.startswith("**Only claim.**")


def test_phase2_r1_diff_inventory_is_claims_not_disagreements(tmp_path: Path) -> None:
    """Spec 0042 D6 — round-1 ``## Diff vs … Phase 1`` parses as ``claim``,
    not ``disagreement``. Disagreements only form in R≥2's
    ``## Substantive disagreements I'm holding``."""
    _seed_phase2_round(tmp_path, 1, "openai", dedent("""
        STATUS: NEGOTIATING

        ## Diff vs claude's Phase 1

        **D-1** — **First contested point**
        - *OpenAI said:* position A
        - *Claude said:* position B

        **D-2** — **Second contested point**
        - *OpenAI said:* position C
        - *Claude said:* position D
    """).strip())

    claims = reconstruct_claims(tmp_path)
    p2_gpt = [c for c in claims if c.phase == 2 and c.raised_by == "gpt"]
    assert len(p2_gpt) == 2
    assert p2_gpt[0].id == "Cl-g-r1-01"
    assert p2_gpt[0].raised_round == 1
    assert p2_gpt[0].raised_turn_key == "phase2_round1_gpt"


def test_phase2_r2_onward_does_not_produce_claims(tmp_path: Path) -> None:
    """``## Diff vs`` only appears in round-1 turns; later rounds use
    ``## Substantive disagreements I'm holding``. The claims reconstructor
    is round-1-only for Phase 2 to avoid bucketing held disagreements as
    fresh claims."""
    _seed_phase2_round(tmp_path, 2, "claude", dedent("""
        ## Substantive disagreements I'm holding

        **D-1** — open — first held disagreement body.
        - some-field: x
    """).strip())
    claims = reconstruct_claims(tmp_path)
    assert claims == []


def test_phase1_no_section_produces_no_claims(tmp_path: Path) -> None:
    """A Phase 1 draft that uses a different structure (no ``## Claims I
    Expect…`` section) returns no claims — that's an honest reflection
    of the agent not emitting them in protocol shape."""
    _seed_phase1(tmp_path, "openai", dedent("""
        ### A. What the architecture gets right
        Body.

        ### B. Where it undermines the constraint
        Body.
    """).strip())
    claims = reconstruct_claims(tmp_path)
    assert claims == []

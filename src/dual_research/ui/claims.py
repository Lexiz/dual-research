"""Spec 0042 D3 — reconstruct ``Claim`` objects across Phase 1 + Phase 2 R1.

Two protocol sources contribute:
- ``## N. Claims I Expect the Other Agent Might Dispute`` — Phase 1 draft.
  These are positions the agent expects to be challenged. Numbered entries
  inside the section.
- ``## Diff vs <other>'s Phase 1`` — Phase 2 round-1 turn file. Round-1
  difference inventory; D-N anchored entries enumerating contested points.

Both produce ``kind="claim"`` review items at parse time. This module walks
the relevant files and wraps them as ``Claim`` objects with stable IDs.

Claim status defaults to ``open``. Spec 0042 doesn't attempt cross-round
closure inference — that's spec 0043's authoritative ledger. A claim is
``resolved`` here only via explicit terminal markers if a future parser
update emits them.
"""

from __future__ import annotations

import re
from pathlib import Path

from dual_research.protocol.parse import extract_review_items
from dual_research.ui.labels import ui_agent
from dual_research.ui.models import Claim


_ROUND_FILE_RE = re.compile(r"^round-(\d{2})-(claude|openai)\.md$")
_PHASE1_DRAFT_RE = re.compile(r"^draft-(claude|openai)\.md$")


def _initial(agent_ui: str) -> str:
    return "c" if agent_ui == "claude" else "g"


def _extract_claims_from_turn(
    turn_text: str,
) -> list[tuple[str, str | None, str | None]]:
    items = extract_review_items(turn_text)
    return [
        (it.body, it.quote, it.after)
        for it in items
        if it.kind == "claim"
    ]


def reconstruct_claims(session_dir: Path) -> list[Claim]:
    """Build the ordered list of Claim objects across Phase 1 + Phase 2 R1.

    Phase 1: one entry per (agent, ``## Claims I Expect…`` list-index).
    Phase 2 R1: one entry per (agent, ``## Diff vs … Phase 1`` list-index).

    IDs:
    - ``Cl-{initial}-p1-{idx}`` for Phase 1 entries.
    - ``Cl-{initial}-r{round}-{idx}`` for Phase 2 R1 entries.
    """
    out: list[Claim] = []

    # Phase 1 — walk the per-agent draft files directly.
    phase1_dir = session_dir / "phase1"
    if phase1_dir.is_dir():
        for entry in sorted(phase1_dir.iterdir()):
            if not entry.is_file() or not entry.name.endswith(".md"):
                continue
            m = _PHASE1_DRAFT_RE.match(entry.name)
            if not m:
                continue
            backend_agent = m.group(1)
            try:
                text = entry.read_text(encoding="utf-8")
            except OSError:
                continue
            ui = ui_agent(backend_agent)
            items = _extract_claims_from_turn(text)
            for idx, (body, quote, after) in enumerate(items, start=1):
                out.append(
                    Claim(
                        id=f"Cl-{_initial(ui)}-p1-{idx:02d}",
                        phase=1,
                        raised_by=ui,
                        raised_round=0,
                        body=body,
                        quote=quote,
                        after=after,
                        block_id=None,
                        raised_turn_key=f"phase1_{ui}",
                    )
                )

    # Phase 2 R1 — Diff vs Phase 1 difference inventory.
    phase2_dir = session_dir / "phase2"
    if phase2_dir.is_dir():
        for entry in sorted(phase2_dir.iterdir()):
            if not entry.is_file() or not entry.name.endswith(".md"):
                continue
            if ".malformed" in entry.name:
                continue
            m = _ROUND_FILE_RE.match(entry.name)
            if not m:
                continue
            round_n = int(m.group(1))
            if round_n != 1:
                continue  # claim extraction is round-1-only for Phase 2
            backend_agent = m.group(2)
            try:
                text = entry.read_text(encoding="utf-8")
            except OSError:
                continue
            ui = ui_agent(backend_agent)
            items = _extract_claims_from_turn(text)
            for idx, (body, quote, after) in enumerate(items, start=1):
                out.append(
                    Claim(
                        id=f"Cl-{_initial(ui)}-r{round_n}-{idx:02d}",
                        phase=2,
                        raised_by=ui,
                        raised_round=round_n,
                        body=body,
                        quote=quote,
                        after=after,
                        block_id=None,
                        raised_turn_key=f"phase2_round{round_n}_{ui}",
                    )
                )

    return out

"""Spec 0144 §8.7 — wire payload size budget.

Densifying every evidence record with denormalised round/actor fields
plus a slim ``consulted_sources`` list grows the per-item payload from
~600 B to ~1.4 KB on the median item. The whole ``phaseStats.items``
slice for the anchor run grows roughly 32 KB → 52 KB. The cap exists
to prevent accidental re-inclusion of ``encrypted_content`` (multi-KB
per source, ~8 KB typical on Anthropic) — if a future refactor leaks
that field onto the wire, the budget snaps.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from dual_research.ui.items import (
    aggregate_items_from_transcript,
    build_session_audit_lookup,
)


_ANCHOR_RUN = (
    Path(__file__).resolve().parents[2]
    / "runs" / "20260521-010637-dvs-backend-language-choice"
)


def test_anchor_run_phase_stats_items_payload_within_budget():
    transcript = _ANCHOR_RUN / "transcript.jsonl"
    if not transcript.is_file():
        import pytest
        pytest.skip(f"anchor run not present at {_ANCHOR_RUN}")

    audit_lookup = build_session_audit_lookup(_ANCHOR_RUN)
    bundle = aggregate_items_from_transcript(transcript, audit_lookup=audit_lookup)
    items_dicts = [asdict(it) for it in bundle.items]
    serialised = json.dumps(items_dicts)
    size_kb = len(serialised) / 1024

    # Anchor-run baseline measured post-spec at ~184 KB — bulk is the
    # transition ``reason`` field (66 KB) + item bodies (42 KB), both
    # of which predate this spec. Spec 0144's additions account for
    # ~25 KB across 30 evidence records. Cap at 256 KB to catch the
    # real failure mode: ``encrypted_content`` (multi-KB per source ×
    # 30 records = many MB) leaking onto the wire.
    assert size_kb <= 256, (
        f"phaseStats.items payload is {size_kb:.1f} KB — over the 256 KB "
        "budget. Has encrypted_content leaked back into consulted_sources?"
    )
    # Belt-and-braces — also assert the literal key string
    # ``"encrypted_content":`` never appears in the serialised payload.
    # (The substring could appear inside a content_excerpt value, but
    # the JSON key form has the colon attached.)
    assert '"encrypted_content":' not in serialised, (
        "encrypted_content key leaked into the wire payload"
    )

"""Spec 0048 — PRICING_VERSION constant + table-bump regression."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict

from dual_research.agents.pricing import PRICING, PRICING_VERSION


def test_pricing_version_is_iso_date():
    """The constant exists and parses as YYYY-MM-DD."""
    assert isinstance(PRICING_VERSION, str)
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", PRICING_VERSION), (
        f"PRICING_VERSION must be YYYY-MM-DD, got {PRICING_VERSION!r}"
    )


def test_version_tracks_table():
    """Snapshot regression: any change to the ``PRICING`` table must be
    accompanied by a manual bump of ``PRICING_VERSION``.

    Mechanism: hash the serialized table; if the hash drifts, the
    captured snapshot below also has to change. The reviewer compares
    "did the version date change?" against "did the snapshot hash
    change?" — both move together or neither does.
    """
    serialised = json.dumps(
        {k: asdict(v) for k, v in sorted(PRICING.items())},
        sort_keys=True,
    )
    digest = hashlib.sha256(serialised.encode("utf-8")).hexdigest()

    # When you bump PRICING_VERSION, update this snapshot to the new hash.
    # The pair (version, snapshot) is the load-bearing invariant: each
    # rate-table edit must touch BOTH lines so reviewers can see the link.
    expected_versions_to_snapshots = {
        "2026-05-17": "438dde2011bb7f46a2781aad04249f81a114ca01d424475337dc5ce760ba4ffb",
        # Spec 0143 — bumped GPT-5.5 to verified OpenAI rates
        # ($5/$30/$0.50 input/output/cache, $0.010/call web_search).
        "2026-05-21": "9bfe60cd0febe31e75358669e424cd41a9dde1cc3e8591a24061e7f212aa519c",
    }

    assert PRICING_VERSION in expected_versions_to_snapshots, (
        f"PRICING_VERSION {PRICING_VERSION!r} is not in the snapshot map. "
        f"Did you bump the version without updating this test?"
    )
    expected = expected_versions_to_snapshots[PRICING_VERSION]
    if digest != expected:
        # Tell the reviewer exactly what to do next.
        raise AssertionError(
            f"PRICING table digest changed but PRICING_VERSION did not. "
            f"Bump PRICING_VERSION in src/dual_research/agents/pricing.py and "
            f"add an entry to expected_versions_to_snapshots with new digest: "
            f"{digest!r}"
        )

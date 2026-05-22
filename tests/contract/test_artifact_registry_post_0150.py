"""Spec 0150 §6 — post-deletion registry-shape pins.

Asserts the registry shape after the legacy `user_prompt` ArtifactDef
is dropped:

- ``REGISTRY`` contains ``user_prompt.message`` and the templated
  ``user_prompt.attachment.<id>`` but no bare ``user_prompt`` entry.
- The import-time-derived ``_CANONICAL_SINGLE_SEGMENT_IDS`` allowlist
  produces exactly the three remaining single-segment IDs:
  ``{current_draft, all_p2_turns, all_carry_forward}``.
"""
from __future__ import annotations

from dual_research.contract.artifacts import REGISTRY
from dual_research.ui.server import _CANONICAL_SINGLE_SEGMENT_IDS


def test_registry_has_no_bare_user_prompt_entry() -> None:
    ids = {a.id_template for a in REGISTRY}
    assert "user_prompt" not in ids
    assert "user_prompt.message" in ids
    assert "user_prompt.attachment.<id>" in ids


def test_canonical_single_segment_ids_post_deletion() -> None:
    """The allowlist is derived from REGISTRY at import time. Post-deletion
    it must contain exactly the three remaining single-segment IDs."""
    assert _CANONICAL_SINGLE_SEGMENT_IDS == {
        "current_draft",
        "all_p2_turns",
        "all_carry_forward",
    }

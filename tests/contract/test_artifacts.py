"""Spec 0114 — phase artifact hashing tests."""

from __future__ import annotations

from dual_research.contract.artifacts import canonical_hash, hash_draft_content


def test_canonical_hash_stable_for_identical_text():
    a = "### AGREED_PLAN\n\n#### Sections\n1. Title: foo\n"
    b = "### AGREED_PLAN\n\n#### Sections\n1. Title: foo\n"
    assert canonical_hash(a) == canonical_hash(b)


def test_canonical_hash_tolerates_trailing_whitespace():
    a = "### AGREED_PLAN\n\nbody\n"
    b = "### AGREED_PLAN\n\nbody    \n\n"
    assert canonical_hash(a) == canonical_hash(b)


def test_canonical_hash_tolerates_line_endings():
    a = "line1\nline2"
    b = "line1\r\nline2"
    assert canonical_hash(a) == canonical_hash(b)


def test_canonical_hash_folds_smart_quotes():
    a = "hello 'world'"
    b = "hello ‘world’"
    assert canonical_hash(a) == canonical_hash(b)


def test_canonical_hash_distinguishes_real_diffs():
    a = "### AGREED_PLAN\n\nclaim A"
    b = "### AGREED_PLAN\n\nclaim B"
    assert canonical_hash(a) != canonical_hash(b)


def test_hash_draft_content_alias():
    assert hash_draft_content("foo") == canonical_hash("foo")

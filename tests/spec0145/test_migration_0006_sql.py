"""Spec 0145 §7.1 — migration 0006 SQL surface.

The migration is run manually against the Supabase SQL editor; this
test pins the declared shape (column list, types, primary key, index)
against the on-disk SQL so reviewers can verify intent without running
the migration. The actual apply/rollback happens out-of-band.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "supabase" / "migrations" / "0006_turn_prompt_pieces.sql"
)


@pytest.fixture(scope="module")
def sql() -> str:
    assert MIGRATION_PATH.is_file(), f"Missing migration: {MIGRATION_PATH}"
    return MIGRATION_PATH.read_text(encoding="utf-8")


class TestTableShape:
    def test_table_uses_if_not_exists(self, sql: str) -> None:
        assert "CREATE TABLE IF NOT EXISTS turn_prompt_pieces" in sql

    def test_required_columns_declared(self, sql: str) -> None:
        for col in ("run_id", "turn_key", "artifact_id", "tokens"):
            assert re.search(rf"\b{col}\b", sql), f"missing column: {col}"

    def test_nullable_metadata_columns_present(self, sql: str) -> None:
        # attachment_id and display_title are nullable — they only
        # populate for `user_prompt.attachment.<id>` rows.
        for col in ("attachment_id", "display_title"):
            assert re.search(rf"\b{col}\b", sql), f"missing column: {col}"

    def test_primary_key_is_composite(self, sql: str) -> None:
        m = re.search(r"PRIMARY\s+KEY\s*\(([^)]+)\)", sql, re.IGNORECASE)
        assert m, "missing primary key declaration"
        pk_cols = {c.strip() for c in m.group(1).split(",")}
        assert pk_cols == {"run_id", "turn_key", "artifact_id"}

    def test_cascade_delete_against_runs(self, sql: str) -> None:
        # The runs row owns the prompt-pieces rows; deleting a run
        # should cascade.
        assert "REFERENCES runs" in sql
        assert "ON DELETE CASCADE" in sql

    def test_index_uses_if_not_exists(self, sql: str) -> None:
        assert "CREATE INDEX IF NOT EXISTS turn_prompt_pieces_run_idx" in sql

    def test_rollback_instructions_present(self, sql: str) -> None:
        # The header comment documents the rollback procedure so an
        # operator running the migration knows the un-do command.
        assert "DROP TABLE turn_prompt_pieces" in sql

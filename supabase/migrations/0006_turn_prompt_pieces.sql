-- Spec 0145 — per-piece token attribution, indexed by (run_id, turn_key, artifact_id).
--
-- Apply via Supabase Dashboard → SQL editor (single migration, idempotent).
-- Re-running is safe: IF NOT EXISTS guards both the table and the index.
--
-- The push CLI populates this table from the `prompt_pieces` payload on
-- every `turn_ended` event. Each (run_id, turn_key) gets one row per
-- artifact_id emitted by the protocol-side `pieces_for_*()` function.
-- For attachments, `artifact_id` carries the resolved canonical ID
-- (e.g. `user_prompt.attachment.abc123`); `attachment_id` (nullable)
-- is the raw attachment ID for joinability against `session_files` and
-- `attachment_blobs`; `display_title` is the resolved human-readable
-- title at push time (the value `display_name()` would return given
-- the contemporaneous `attachments.json`).
--
-- The UI server's consumption endpoint reads this table directly when
-- available; falls through to `events.payload.prompt_pieces` JSONB when
-- the table has no rows for the run (historical pre-spec runs).
--
-- Backfill of historical runs into this table is OUT OF SCOPE (per spec
-- §3 non-goals). New pushes from this version forward populate the
-- table; older runs continue to render via the legacy JSONB fallback
-- through the JS read-shim.
--
-- Rollback: `DROP TABLE turn_prompt_pieces;` — purely additive, no
-- changes to existing tables or constraints.

CREATE TABLE IF NOT EXISTS turn_prompt_pieces (
    run_id          TEXT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    turn_key        TEXT NOT NULL,
    artifact_id     TEXT NOT NULL,
    tokens          INT NOT NULL,
    attachment_id   TEXT,
    display_title   TEXT,
    PRIMARY KEY (run_id, turn_key, artifact_id)
);

CREATE INDEX IF NOT EXISTS turn_prompt_pieces_run_idx
    ON turn_prompt_pieces (run_id, turn_key);

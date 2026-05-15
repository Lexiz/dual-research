-- Spec 0025 — binary attachment blobs for the visualisation foundations.
--
-- Apply via Supabase Dashboard → SQL editor (single migration; no tooling).
-- Re-running is safe: IF NOT EXISTS guards the table.
--
-- The push CLI (`dual-research --push <session-dir>`) base64-encodes every
-- file under `session-dir/attachments/` and upserts a row here. The UI
-- server's attachment-blobs endpoint base64-decodes back to bytes on read.
--
-- attachments.json itself (the metadata index) flows through the existing
-- `session_files` table — it's a `.json` under the session-dir and picked
-- up by the file iterator without any schema change.

CREATE TABLE IF NOT EXISTS attachment_blobs (
    run_id      TEXT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    rel_path    TEXT NOT NULL,
    mime        TEXT NOT NULL,
    size_bytes  INT NOT NULL,
    content_b64 TEXT NOT NULL,
    PRIMARY KEY (run_id, rel_path)
);

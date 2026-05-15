-- Spec 0019 — initial schema for the hosted-deployment track.
--
-- Apply via Supabase Dashboard → SQL editor (single migration; no tooling).
-- Re-running is safe: every statement uses IF NOT EXISTS or CREATE OR REPLACE.
--
-- Three tables form the source of truth for a pushed run:
--   runs            — one row per session-dir; metadata + JSONB state/metrics
--   events          — append-only mirror of transcript.jsonl (one row per line)
--   session_files   — every text artifact in the session-dir (markdown, json)
--
-- The push CLI (`dual-research --push <session-dir>`) writes these tables via
-- upsert; re-pushing the same session-dir replaces its rows in place.

CREATE TABLE IF NOT EXISTS runs (
    id              TEXT PRIMARY KEY,
    slug            TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL,
    pushed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    model_tier      TEXT,
    claude_model    TEXT,
    openai_model    TEXT,
    phase_reached   TEXT,
    exit_code       INT,
    duration_ms     BIGINT,
    total_cost_usd  NUMERIC(10, 4),
    confidence      TEXT,
    state           JSONB,
    metrics         JSONB
);

CREATE INDEX IF NOT EXISTS runs_created_at_idx ON runs (created_at DESC);

CREATE TABLE IF NOT EXISTS events (
    run_id      TEXT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    seq         INT NOT NULL,
    ts          TIMESTAMPTZ NOT NULL,
    kind        TEXT NOT NULL,
    payload     JSONB NOT NULL,
    PRIMARY KEY (run_id, seq)
);

CREATE INDEX IF NOT EXISTS events_run_kind_idx ON events (run_id, kind);

CREATE TABLE IF NOT EXISTS session_files (
    run_id      TEXT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    path        TEXT NOT NULL,
    content     TEXT NOT NULL,
    size_bytes  INT NOT NULL,
    PRIMARY KEY (run_id, path)
);

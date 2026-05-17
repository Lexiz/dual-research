-- Spec 0048 — persisted reconciliation snapshots.
--
-- One row per UTC date that the `dual-research reconcile-costs` CLI has
-- successfully processed. The `payload` column carries the full
-- ReconcileReport JSON (the same shape the local
-- `reconcile/<date>.json` files use). Hosted server endpoint
-- `GET /api/reconcile/<date>` reads from this table; the UI's
-- run-detail verification chip and Consumption-tab provider-billed
-- annotation both consume that endpoint.
--
-- Re-running reconciliation for a date upserts the row, so the latest
-- snapshot always wins.

CREATE TABLE IF NOT EXISTS reconcile_results (
    date         DATE PRIMARY KEY,
    payload      JSONB NOT NULL,
    checked_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS reconcile_results_checked_at_idx
    ON reconcile_results (checked_at DESC);

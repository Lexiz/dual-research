-- Spec 0125 — Server-persisted onboarding state.
--
-- Adds per-user onboarding lifecycle state to the existing approved_emails
-- table + a single-row system_settings table for a global onboarding-required
-- flag. Pre-spec, onboarding state lived in per-browser localStorage and the
-- admin Users page could only show "current user only".
--
-- New columns on approved_emails:
--   onboarded_at         — NULL until the user completes (or skips) the tour
--   onboarded_at_version — the app version string at completion (so admins
--                          can see who completed before a major UX change)
--   tour_step            — the current step they're on (1..8); useful when
--                          the user resumes after a partial walk-through
--   tour_force_reset_at  — non-NULL means an admin pressed "reset onboarding"
--                          for this user. Computed rule: mustRestart =
--                          tour_force_reset_at IS NOT NULL AND
--                          (onboarded_at IS NULL OR tour_force_reset_at > onboarded_at)
--   last_seen_at         — updated on every /api/me call
--
-- The single-row system_settings table carries `onboarding_required` (when
-- true, the tour fires for every authed user who hasn't completed it).
--
-- Re-runnable: ALTER TABLE … IF NOT EXISTS is enforced by the column
-- existence check pattern (IF NOT EXISTS for each column) so dropping in
-- the migration twice is a no-op.

ALTER TABLE approved_emails
    ADD COLUMN IF NOT EXISTS onboarded_at        TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS onboarded_at_version TEXT NULL,
    ADD COLUMN IF NOT EXISTS tour_step           SMALLINT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS tour_force_reset_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS last_seen_at        TIMESTAMPTZ NULL;

CREATE TABLE IF NOT EXISTS system_settings (
    id                  INTEGER PRIMARY KEY CHECK (id = 1),
    onboarding_required BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          TEXT NULL
);

INSERT INTO system_settings (id, onboarding_required)
VALUES (1, FALSE)
ON CONFLICT (id) DO NOTHING;

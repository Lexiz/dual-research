-- Spec 0021 — email allowlist for Supabase-Auth-gated hosted UI.
--
-- One row per allowlisted email. `is_admin = true` rows can manage the
-- allowlist via the spec 0022 admin route. At least one admin row must
-- exist for the bootstrap to work; we seed the project owner.
--
-- Re-running is safe: ON CONFLICT keeps existing rows and only refreshes
-- the is_admin flag on the seeded row.

CREATE TABLE IF NOT EXISTS approved_emails (
    email      TEXT PRIMARY KEY,
    is_admin   BOOLEAN NOT NULL DEFAULT false,
    added_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO approved_emails (email, is_admin)
VALUES ('alex.lisitzky@gmail.com', true)
ON CONFLICT (email) DO UPDATE SET is_admin = EXCLUDED.is_admin;

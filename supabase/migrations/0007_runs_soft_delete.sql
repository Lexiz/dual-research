-- Spec 0245 — Soft-delete on runs.
--
-- Adds `deleted_at` + `deleted_by` columns plus a `runs_active` view that
-- becomes the canonical reader surface. RLS policies are defense-in-depth:
-- the server-side `/api/runs/{id}/archive` endpoint runs with the
-- service-role key (which bypasses RLS), and is the canonical write path;
-- the policies catch any future caller that bypasses the server.

ALTER TABLE public.runs
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS deleted_by TEXT NULL;

CREATE INDEX IF NOT EXISTS runs_deleted_at_idx
    ON public.runs (deleted_at)
    WHERE deleted_at IS NOT NULL;

CREATE OR REPLACE VIEW public.runs_active
    WITH (security_invoker = true)
AS SELECT * FROM public.runs WHERE deleted_at IS NULL;

ALTER TABLE public.runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS runs_select_active_or_admin ON public.runs;
CREATE POLICY runs_select_active_or_admin ON public.runs
    FOR SELECT
    USING (
        deleted_at IS NULL
        OR EXISTS (
            SELECT 1 FROM public.approved_emails
            WHERE email = auth.email() AND is_admin = true
        )
    );

DROP POLICY IF EXISTS runs_update_admin_only ON public.runs;
CREATE POLICY runs_update_admin_only ON public.runs
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM public.approved_emails
            WHERE email = auth.email() AND is_admin = true
        )
    );

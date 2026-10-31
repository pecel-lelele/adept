-- migrate:up
ALTER TABLE data_refresh_runs ADD COLUMN run_id uuid NOT NULL DEFAULT gen_random_uuid();
ALTER TABLE data_refresh_runs ADD CONSTRAINT data_refresh_runs_run_id_key UNIQUE (run_id);
ALTER TABLE data_refresh_runs ADD COLUMN steps jsonb NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE data_refresh_runs ALTER COLUMN finished_at DROP NOT NULL;
ALTER TABLE data_refresh_runs DROP CONSTRAINT data_refresh_runs_source_check;
ALTER TABLE data_refresh_runs ADD CONSTRAINT data_refresh_runs_source_check
    CHECK (source IN ('courses', 'jobs', 'labour', 'trends', 'automatic'));
ALTER TABLE data_refresh_runs DROP CONSTRAINT data_refresh_runs_status_check;
ALTER TABLE data_refresh_runs ADD CONSTRAINT data_refresh_runs_status_check
    CHECK (status IN ('queued', 'running', 'ok', 'failed'));

-- migrate:down
-- Preserve the audit trail. NOT VALID keeps historical automatic/running rows while
-- enforcing the older constraint for subsequent writes. Export/review them before validation.
ALTER TABLE data_refresh_runs DROP CONSTRAINT data_refresh_runs_status_check;
ALTER TABLE data_refresh_runs ADD CONSTRAINT data_refresh_runs_status_check
    CHECK (status IN ('ok', 'failed')) NOT VALID;
ALTER TABLE data_refresh_runs DROP CONSTRAINT data_refresh_runs_source_check;
ALTER TABLE data_refresh_runs ADD CONSTRAINT data_refresh_runs_source_check
    CHECK (source IN ('courses', 'jobs', 'labour', 'trends')) NOT VALID;
-- New columns remain to avoid deleting job identifiers and progress evidence on rollback.

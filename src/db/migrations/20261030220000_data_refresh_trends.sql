-- migrate:up
ALTER TABLE data_refresh_runs DROP CONSTRAINT data_refresh_runs_source_check;
ALTER TABLE data_refresh_runs ADD CONSTRAINT data_refresh_runs_source_check
    CHECK (source IN ('courses', 'jobs', 'labour', 'trends'));

-- migrate:down
-- Preserve existing trend audit rows; returning to the original constraint requires these
-- rows to be exported/reviewed rather than silently deleted during a rollback.
ALTER TABLE data_refresh_runs DROP CONSTRAINT data_refresh_runs_source_check;
ALTER TABLE data_refresh_runs ADD CONSTRAINT data_refresh_runs_source_check
    CHECK (source IN ('courses', 'jobs', 'labour')) NOT VALID;

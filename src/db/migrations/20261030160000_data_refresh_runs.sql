-- migrate:up
-- One row per in-app live data refresh (admin "Refresh now"): when it ran, how it ended and how
-- many rows it fetched, wrote and rejected. No credentials, request bodies or personal data.
CREATE TABLE data_refresh_runs (
    id            bigserial PRIMARY KEY,
    source        text NOT NULL CHECK (source IN ('courses', 'jobs', 'labour')),
    started_at    timestamptz NOT NULL,
    finished_at   timestamptz NOT NULL,
    status        text NOT NULL CHECK (status IN ('ok', 'failed')),
    rows_fetched  integer NOT NULL DEFAULT 0 CHECK (rows_fetched >= 0),
    rows_upserted integer NOT NULL DEFAULT 0 CHECK (rows_upserted >= 0),
    rows_rejected integer NOT NULL DEFAULT 0 CHECK (rows_rejected >= 0),
    error_code    text,
    detail        text NOT NULL DEFAULT ''
);
CREATE INDEX data_refresh_runs_source_idx ON data_refresh_runs (source, finished_at DESC);
REVOKE ALL ON data_refresh_runs FROM PUBLIC;

-- migrate:down
-- Removes only the refresh audit trail; refreshed reference data itself is untouched.
DROP TABLE data_refresh_runs;
